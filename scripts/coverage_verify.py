#!/usr/bin/env python3
"""Verifikace COMPLETENESS harvestu (fáze 1) — odpovídá na „neunikla nám stránka?".

Dva nezávislé checky, oba bez ground-truth orákula, ale auditovatelné:

  #1 STRUKTURA (WP REST): když host běží WordPress, načti X-WP-Total pro posts/pages/CPT
     → kolik URL zdroj přes REST vůbec eviduje. Porovnej s počtem našich URL na tom hostu.
     (Pozn.: BFS bere jen grant-relevantní linky, takže harvested < total je OČEKÁVANÉ;
      smysl je vidět ŘÁD a velké propady.)

  #2 SITEMAP DIFF: stáhni sitemapy (robots.txt → /sitemap.xml, /wp-sitemap.xml, /sitemap_index.xml),
     posbírej VŠECHNY <loc>, odečti naše URL → SYROVÝ seznam nezachycených stránek (bez třídění;
     grant-relevanci posoudí pozdější classify) + obráceně naše-URL-mimo-sitemapu.

Síť: urllib (sdílí safe_url z dsw2_fetch). Runaway hlídá limits.safety.runaway_page_ceiling (loguje).
Žádný cap na data; sitemapy/REST se berou celé.

Spuštění:
  python3 scripts/coverage_verify.py data/h19_*.jsonl            # všechny zdroje
  python3 scripts/coverage_verify.py data/h19_nadacevia.jsonl    # jeden
  (report → data/files/_coverage_verify.jsonl, lidský souhrn na stdout)
"""
import argparse, gzip, json, os, re, sys
import urllib.request, urllib.error
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsw2_fetch import safe_url, UA
from limits import L

REPORT = "data/files/_coverage_verify.jsonl"
# WP infrastruktura (NE obsah) — vyřazeno z „content universe" počtu. Názvy jsou WP-protokol, ne byznys.
WP_INFRA = {"media", "users", "types", "taxonomies", "categories", "tags", "comments",
            "search", "blocks", "block-renderer", "navigation", "menu-items", "menus",
            "menu-locations", "settings", "plugins", "themes", "templates", "template-parts",
            "global-styles", "pattern-directory", "font-families", "sidebars", "widgets",
            "widget-types", "statuses", "redirection"}


def fetch(url, timeout=25, max_bytes=50 * 1024 * 1024):
    """→ (status:int|None, headers:dict, body:bytes|None, err:str|None).
    Retry na TRANSIENTNÍ chyby (timeout/URLError/5xx) — síť je nespolehlivá, jinak by přechodný
    výpadek vypadal jako „zdroj nemá sitemapu" (false no_sitemap). 4xx (404/403) se NEretryuje."""
    retries = L("http.default_retries") or 1
    last = (None, {}, None, "no-attempt")
    for _ in range(retries):
        try:
            req = urllib.request.Request(safe_url(url), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, dict(r.headers), r.read(max_bytes), None
        except urllib.error.HTTPError as e:
            err = f"http-{e.code}"
            if 400 <= e.code < 500:                       # definitivní — neretryuj
                return e.code, dict(getattr(e, "headers", {}) or {}), None, err
            last = (e.code, {}, None, err)                # 5xx → retry
        except Exception as e:  # noqa: BLE001
            last = (None, {}, None, f"{type(e).__name__}: {str(e)[:60]}")
    return last


def norm(u):
    """Normalizace pro diff: host+path(+query) bez schématu/fragmentu/koncového lomítka, host lowercase."""
    p = urlsplit(u.strip())
    host = p.netloc.lower()
    path = p.path.rstrip("/") or "/"
    return f"{host}{path}" + (f"?{p.query}" if p.query else "")


# ---------- #1 WP REST totals ----------
def wp_totals(host):
    st, _, body, _ = fetch(f"https://{host}/wp-json/wp/v2")
    if st != 200 or not body:
        return None
    try:
        idx = json.loads(body)
    except Exception:
        return None
    routes = idx.get("routes") or {}
    types = set()
    for rk in routes:
        m = re.match(r"^/wp/v2/([a-z0-9_-]+)$", rk)
        if m and m.group(1) not in WP_INFRA:
            types.add(m.group(1))
    types |= {"posts", "pages"}
    totals = {}
    for t in sorted(types):
        st, hdr, _, _ = fetch(f"https://{host}/wp-json/wp/v2/{t}?per_page=1")
        if st == 200:
            tot = hdr.get("X-WP-Total") or hdr.get("x-wp-total")
            if tot is not None:
                totals[t] = int(tot)
    return totals or None


# ---------- #2 sitemap collection ----------
def sitemap_seeds(host):
    seeds = []
    st, _, body, _ = fetch(f"https://{host}/robots.txt")
    if st == 200 and body:
        for line in body.decode("utf-8", "replace").splitlines():
            m = re.match(r"\s*sitemap\s*:\s*(\S+)", line, re.I)
            if m:
                seeds.append(m.group(1).strip())
    for cand in ("/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml"):
        u = f"https://{host}{cand}"
        if u not in seeds:
            seeds.append(u)
    return seeds


def collect_sitemap_urls(seeds, ceiling):
    """Rekurzivně projdi sitemap-index → child sitemapy → <loc> URL.
    Vrať (set urls, [navštívené sitemapy], hit_ceiling, [transient_errors]).
    transient_errors = sitemapy, co selhaly NE na 404 (timeout/5xx) → diff je nespolehlivý, re-run."""
    locs, visited, queue = set(), set(), list(seeds)
    hit = False
    errors = []
    while queue:
        sm = queue.pop(0)
        if sm in visited:
            continue
        visited.add(sm)
        if len(locs) >= ceiling or len(visited) > ceiling:
            hit = True
            break
        st, hdr, body, err = fetch(sm)
        if st != 200 or not body:
            if st is None or (isinstance(st, int) and st >= 500):   # NE 404 → transientní
                errors.append({"sitemap": sm, "err": err})
            continue
        if sm.endswith(".gz") or "gzip" in (hdr.get("Content-Type", "") or "").lower():
            try:
                body = gzip.decompress(body)
            except Exception:
                pass
        text = body.decode("utf-8", "replace")
        child = re.findall(r"<sitemap>.*?<loc>\s*(.*?)\s*</loc>.*?</sitemap>", text, re.S | re.I)
        if child:
            for c in child:
                if c not in visited:
                    queue.append(c)
        for loc in re.findall(r"<url>.*?<loc>\s*(.*?)\s*</loc>.*?</url>", text, re.S | re.I):
            locs.add(loc)
        if not child:  # plochá sitemapa bez <url> obalu — vezmi všechny <loc>
            for loc in re.findall(r"<loc>\s*(.*?)\s*</loc>", text, re.S | re.I):
                if loc not in visited and loc.endswith((".xml", ".xml.gz")):
                    queue.append(loc)
                else:
                    locs.add(loc)
    return locs, sorted(visited), hit, errors


def verify_source(path, ceiling):
    src = os.path.basename(path)[4:-6] if os.path.basename(path).startswith("h19_") else os.path.basename(path)[:-6]
    harvested = set()
    hosts = {}
    for l in open(path, encoding="utf-8"):
        try:
            r = json.loads(l)
        except Exception:
            continue
        u = r.get("url")
        if not u:
            continue
        harvested.add(norm(u))
        h = urlsplit(u).netloc.lower()
        hosts[h] = hosts.get(h, 0) + 1

    rep = {"source": src, "harvest_file": path, "harvested_urls": len(harvested),
           "hosts": {}, "wp": {}, "sitemap": {}}
    all_sitemap = set()
    sitemaps_seen = []
    fetch_errors = []
    for host in hosts:
        wt = wp_totals(host)
        if wt:
            rep["wp"][host] = {"totals": wt, "content_total": sum(wt.values())}
        locs, seen, hit, errs = collect_sitemap_urls(sitemap_seeds(host), ceiling)
        sitemaps_seen += seen
        fetch_errors += errs
        all_sitemap |= {norm(x) for x in locs if urlsplit(x).netloc.lower() == host}
        rep["hosts"][host] = {"harvested": hosts[host], "sitemap_locs": len(locs), "ceiling_hit": hit}
        if hit:
            print(f"  ⚠ {src}/{host}: runaway ceiling {ceiling} u sitemapy — prošetři (NEzvyšuj naslepo)", file=sys.stderr)

    missed = sorted(all_sitemap - harvested)            # v sitemapě, NEzachyceno
    extra = sorted(harvested - all_sitemap)             # zachyceno, mimo sitemapu (OK — hlubší crawl)
    rep["sitemap"] = {"total_locs": len(all_sitemap), "sitemaps_seen": sitemaps_seen,
                      "missed_count": len(missed), "missed": missed,
                      "harvested_not_in_sitemap": len(extra), "fetch_errors": fetch_errors}
    # VERDIKT stage 1 (strukturální). PASS != „neunikla oportunita" — to potvrdí až stage 2 (classify MISSED).
    if any(h.get("ceiling_hit") for h in rep["hosts"].values()):
        rep["verdict"] = "ceiling_hit_partial"          # sitemap > safety ceiling → diff useknutý, prošetři
    elif fetch_errors and len(all_sitemap) == 0:
        rep["verdict"] = "fetch_error_retry"             # sitemap nešla stáhnout (timeout/5xx) → NE „bez sitemapy", re-run
    elif len(all_sitemap) == 0:
        rep["verdict"] = "no_sitemap_inconclusive"       # check #2 neprůkazný → potřeba re-crawl saturace
    elif missed:
        rep["verdict"] = "needs_triage"                  # MISSED>0 → protáhnout classify (grant/project survivor = reálná díra)
    else:
        rep["verdict"] = "complete_structural"           # 0 missed v sitemapě (stále jen strukturálně)
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default=REPORT)
    ap.add_argument("--workers", type=int, default=L("http.download_workers"))
    args = ap.parse_args()
    ceiling = L("safety.runaway_page_ceiling")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        reps = list(ex.map(lambda f: verify_source(f, ceiling), args.files))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in reps:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"\n{'zdroj':22}{'harvested':>10}{'wp_content':>11}{'sitemap':>9}{'MISSED':>8}{'extra':>7}  verdikt")
    tot_missed = 0
    from collections import Counter
    verdicts = Counter()
    for r in sorted(reps, key=lambda x: -x["sitemap"]["missed_count"]):
        wpc = sum(w["content_total"] for w in r["wp"].values()) if r["wp"] else None
        sm = r["sitemap"]
        tot_missed += sm["missed_count"]
        verdicts[r["verdict"]] += 1
        print(f"{r['source']:22}{r['harvested_urls']:>10}{(wpc if wpc is not None else '-'):>11}"
              f"{sm['total_locs']:>9}{sm['missed_count']:>8}{sm['harvested_not_in_sitemap']:>7}  {r['verdict']}")
    print(json.dumps({"MARKER": "COVERAGE_VERIFY", "sources": len(reps),
                      "total_missed_in_sitemap": tot_missed, "out": args.out,
                      "verdicts": dict(verdicts),
                      "note": "MISSED = v sitemapě, námi NEzachyceno (syrové, bez grant-třídění → pozdější classify). "
                              "wp_content = X-WP-Total posts/pages/CPT (harvested<total je OK kvůli grant-only BFS)."},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
