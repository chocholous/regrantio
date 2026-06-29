#!/usr/bin/env python3
"""Národní sportovní agentura (agenturasport.cz → nsa.gov.cz) — vrstva 1.

NSA = ústřední orgán pro podporu sportu; hlavní český poskytovatel dotací do sportu (miliardy/rok):
neinvestiční výzvy (Můj klub, Sportovní organizace olympijského/paralympijského hnutí, Významné
sportovní akce, reprezentace, parasport…) i investiční (Regiony, Standardizovaná/Movité sportovní
infrastruktura, obnova po povodních). agenturasport.cz redirektuje 301 → nsa.gov.cz.

WordPress + Elementor. Výzvy NEjsou CPT — jsou to WP `pages` na `/dotace/<slug>/` (+ pár pod
`/dotace-neinvesticni/…`). Na rozdíl od tacr/sfpi tady `content.rendered` STAČÍ (Elementor widgety
nesou strukturovaný blok: DATUM VYHLÁŠENÍ VÝZVY · ZAHÁJENÍ/UKONČENÍ PŘÍJMU ŽÁDOSTÍ · ALOKACE + prózu).
Discovery: REST `pages` → filtr na slug „výzva N/<rok>" (aktuální cyklus, vzor gacr/tacr --since-stylem
přes --year), jinak by se dataset zaplavil historickými ročníky (188 dotačních pages).

Výstup (shodný tvar jako tacr/sfdi → build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění z kořene repa: python3 scripts/nsa.py --out data/nsa_documents.jsonl --year 2026
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí české diagnostiky → UTF-8
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
B = "https://nsa.gov.cz"
HOST = "nsa.gov.cz"
# slug aktuálního cyklu: „vyzva-8-2026-…" / „vzva-202026-…" (číslo, pak rok, někdy slepené)
VYZVA_RE = re.compile(r"v[yz]?zva-?(\d+)-?(20\d\d)", re.I)
DOC_RE = re.compile(r'<a[^>]+href="([^"]+\.(?:pdf|docx?|xlsx?)[^"]*)"[^>]*>(.*?)</a>', re.I | re.S)


def fetch_json(url, timeout=45, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(retries):
        try:
            with http_util.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8", "replace")
            if body.lstrip()[:1] in ("[", "{"):
                return json.loads(body)
            last = f"očekáván JSON, dostal {body.lstrip()[:30]!r}"
        except Exception as e:
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch selhal po {retries} pokusech: {url} ({last})")


def clean_text(c):
    """Elementor content.rendered → čistý text; blok-tagy → newline (label/value na vlastní řádek)."""
    c = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", c or "")
    c = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>|</a>", "\n", c)
    t = html.unescape(re.sub(r"<[^>]+>", " ", c))
    t = re.sub(r"[ \t ]+", " ", t)
    t = "\n".join(ln.strip() for ln in t.split("\n") if ln.strip())
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def discover(year):
    """Vrať pages (id, slug, link, title) výzev daného roku (na /dotace…), nejnižší číslo dřív."""
    pages = []
    for pg in range(1, 12):
        d = fetch_json(f"{B}/wp-json/wp/v2/pages?per_page=100&page={pg}"
                       "&_fields=id,slug,link,title,date")
        pages += d
        if len(d) < 100:
            break
    out = {}
    for p in pages:
        if "/dotace" not in p.get("link", ""):
            continue
        m = VYZVA_RE.search(p.get("slug", ""))
        if not m or int(m.group(2)) != year:
            continue
        n = int(m.group(1))
        out.setdefault(n, p)  # první výskyt čísla (kanonická /dotace/ stránka má přednost)
    return [out[n] for n in sorted(out)]


def main():
    from datetime import date
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/nsa_documents.jsonl")
    ap.add_argument("--year", type=int, default=date.today().year,
                    help="ročník výzev (aktuální cyklus); default = letošek")
    args = ap.parse_args()

    calls = discover(args.year)
    print(f"  discovery: {len(calls)} výzev ročníku {args.year}", flush=True)
    # batch-fetch obsah JEDNÍM dotazem (include=) — 22 sekvenčních round-tripů přes WAF/proxy je pomalé
    ids = ",".join(str(p["id"]) for p in calls)
    full_by_id = {}
    for fp in fetch_json(f"{B}/wp-json/wp/v2/pages?include={ids}&per_page=100&_fields=id,link,title,content"):
        full_by_id[fp["id"]] = fp
    recs = []
    for p in calls:
        url = p["link"]
        full = full_by_id.get(p["id"], {})
        ctitle = html.unescape(re.sub(r"<[^>]+>", "", (p.get("title") or {}).get("rendered", ""))).strip()
        ctitle = re.sub(r"^Výzva\s+Výzva", "Výzva", ctitle)  # ojediněle zdvojený prefix (UNISPORT)
        raw = (full.get("content") or {}).get("rendered", "")
        body = clean_text(raw)
        if "PŘÍJMU ŽÁDOSTÍ" not in body and "ALOKACE" not in body:
            print(f"  ⚠ {p['slug']}: bez strukturního bloku → přeskakuji", flush=True)
            continue
        atts, seen = [], set()
        for href, label in DOC_RE.findall(raw):
            u = urljoin(B, html.unescape(href))
            lab = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", label))).strip()
            if u in seen:
                continue
            # přednost dokumentaci výzvy (znění výzvy / dodatek / pravidla), ne datové schránky apod.
            if re.search(r"znění|výzv|vyzv|dodatek|pravidl|příručk|priruck|zadáv|zadav", lab + u, re.I):
                seen.add(u)
                atts.append({"url": u, "label": lab or u.rsplit("/", 1)[-1]})
        recs.append({"url": url, "host": HOST, "title": ctitle, "body_text": body,
                     "attachments": atts[:4], "n_attachments": min(len(atts), 4)})

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  att={r['n_attachments']:2} body={len(r['body_text']):5} :: {r['title'][:62]}", flush=True)
    print(f"NSA_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
