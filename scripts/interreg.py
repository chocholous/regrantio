#!/usr/bin/env python3
"""Interreg (přeshraniční programy) — layer-1 harvest výzev. DVA REŽIMY.

STRUKTURA PŘED PRÓZOU: české/slovenské Interreg weby běží na WordPressu.
  mode="rest" (sk-cz.eu): výzvy jsou POSTY v dotačních KATEGORIÍCH →
      /wp-json/wp/v2/posts?categories=<id> dá titul, datum, content i přílohy.
      Kategorie se NEhardkódují podle id (mění se) — hledají se přes /categories podle
      SLUGU (regex `vyzv|call`), takže nová kategorie na webu se propíše sama. (13 postů)
  mode="html" (cz-pl.eu): tentýž WP, ale REST je ZAVŘENÝ (HTTPError na /wp-json) →
      fallback na HTML listing /vyzvy + detailové stránky. (2 výzvy)

POZOR: oba weby vracejí 403 na default urllib User-Agent → posílají se realistické
prohlížečové hlavičky (HDR).

POZOR na scope: Interreg Central Europe a Danube vyhlašují výzvy centrálně (nadnárodní
sekretariát) — ty NEJSOU v tomhle harvesteru; kandidát na samostatný zdroj.
Creative Europe se NEharvestuje: jeho výzvy vyhlašuje EACEA a v datasetu už jsou přes
EU Funding & Tenders Portal (source `eu_ft`) — jinak by vznikly duplicity.

Výstup (kontrakt jako ostatní *_documents.jsonl):
  data/interreg_documents.jsonl  {host, web, program, title, url, date, kind, body_text,
                                  attachments[], n_attachments, kategorie}

Spuštění (z kořene repa):
  python scripts/interreg.py                 # všechny programy
  python scripts/interreg.py --program sk-cz
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse
import html as H
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util  # noqa: E402  (jednotná TLS politika)

PROGRAMS = {
    # WP REST (kategorie výzev) — plná cesta
    "sk-cz": {"base": "https://www.sk-cz.eu", "name": "Interreg SK-CZ (Slovensko–Česko)",
              "mode": "rest"},
    # cz-pl má REST ZAVŘENÝ (HTTPError na /wp-json) → HTML listing /vyzvy + detaily
    "cz-pl": {"base": "https://www.cz-pl.eu", "name": "Interreg CZ-PL (Česko–Polsko)",
              "mode": "html", "listing": "/vyzvy", "item_re": r'href="(/[^"?#]*(?:vyzv|nabor)[^"?#]*)"'},
}
CAT_RE = re.compile(r"vyzv|výzv|call", re.I)
DOC_RE = re.compile(r"\.(pdf|docx?|xlsx?|zip)(\?|$)", re.I)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HDR = {"User-Agent": UA, "Accept-Language": "cs,sk,en;q=0.9", "Accept-Encoding": "identity"}


def _get(url, timeout=45):
    import urllib.request
    req = urllib.request.Request(url, headers=HDR)
    with http_util.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), r.url


def api(url, timeout=45):
    return json.loads(_get(url, timeout)[0])


def harvest_html(slug, cfg, timeout):
    """Weby se ZAVŘENÝM WP REST (cz-pl): HTML listing výzev → detaily."""
    base = cfg["base"]
    try:
        page, _ = _get(base + cfg["listing"], timeout)
    except Exception as e:  # noqa: BLE001
        print(f"  [err] {slug} listing: {type(e).__name__}", file=sys.stderr)
        return []
    items = sorted(set(re.findall(cfg["item_re"], page, re.I)))
    items = [i for i in items if i.rstrip("/") != cfg["listing"].rstrip("/")]
    print(f"  [{slug}] HTML listing: {len(items)} položek", file=sys.stderr)
    out = []
    for path in items:
        url = urllib.parse.urljoin(base, path)
        try:
            detail, final = _get(url, timeout)
        except Exception as e:  # noqa: BLE001
            print(f"  [err] {slug} {path}: {type(e).__name__}", file=sys.stderr)
            continue
        body = strip_tags(detail)
        if len(body) < 200:
            continue
        title = ""
        m = re.search(r"<h1[^>]*>(.*?)</h1>", detail, re.S | re.I)
        if m:
            title = strip_tags(m.group(1))
        atts, seen = [], set()
        for mm in re.finditer(r'href="([^"]+)"', detail):
            u = urllib.parse.urljoin(final, H.unescape(mm.group(1)))
            if DOC_RE.search(u) and u not in seen:
                seen.add(u)
                atts.append({"url": u, "label": urllib.parse.unquote(u.rsplit("/", 1)[-1])[:120]})
        out.append({
            "host": base.split("//")[-1], "web": base.split("//")[-1],
            "program": cfg["name"], "kind": "vyzva",
            "title": (title or path.strip("/").replace("-", " "))[:300],
            "url": final, "date": None, "body_text": body,
            "attachments": atts, "n_attachments": len(atts), "kategorie": [],
        })
    return out


def strip_tags(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s or "", flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</div>|</li>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[ \t]+", " ", H.unescape(s)).strip()


def harvest(slug, cfg, timeout):
    base = cfg["base"]
    try:
        cats = api(f"{base}/wp-json/wp/v2/categories?per_page=100&_fields=id,slug,name,count", timeout)
    except Exception as e:  # noqa: BLE001
        print(f"  [err] {slug} kategorie: {type(e).__name__}", file=sys.stderr)
        return []
    wanted = [c for c in cats if CAT_RE.search(c.get("slug", "") or "") and c.get("count")]
    if not wanted:
        print(f"  [{slug}] žádná dotační kategorie", file=sys.stderr)
        return []
    ids = ",".join(str(c["id"]) for c in wanted)
    print(f"  [{slug}] kategorie: {', '.join(c['slug'] for c in wanted)}", file=sys.stderr)

    out, page = [], 1
    while True:
        url = (f"{base}/wp-json/wp/v2/posts?categories={ids}&per_page=100&page={page}"
               f"&_fields=id,link,date,title,content,categories")
        try:
            posts = api(url, timeout)
        except Exception as e:  # noqa: BLE001
            if page > 1:
                break                       # WP vrací 400 za poslední stránkou
            print(f"  [err] {slug} posts: {type(e).__name__}", file=sys.stderr)
            return out
        if not posts:
            break
        for p in posts:
            content = (p.get("content") or {}).get("rendered", "")
            atts, seen = [], set()
            for m in re.finditer(r'href="([^"]+)"', content):
                u = H.unescape(m.group(1))
                if DOC_RE.search(u) and u not in seen:
                    seen.add(u)
                    atts.append({"url": u, "label": urllib.parse.unquote(u.rsplit("/", 1)[-1])[:120]})
            out.append({
                "host": base.split("//")[-1], "web": base.split("//")[-1],
                "program": cfg["name"], "kind": "vyzva",
                "title": strip_tags((p.get("title") or {}).get("rendered", ""))[:300],
                "url": p.get("link"), "date": (p.get("date") or "")[:10],
                "body_text": strip_tags(content),
                "attachments": atts, "n_attachments": len(atts),
                "kategorie": [c["slug"] for c in wanted if c["id"] in (p.get("categories") or [])],
            })
        if len(posts) < 100:
            break
        page += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--program", choices=sorted(PROGRAMS), help="jen jeden program")
    ap.add_argument("--out", default="data/interreg_documents.jsonl")
    ap.add_argument("--timeout", type=int, default=45)
    a = ap.parse_args()

    recs = []
    for slug, cfg in PROGRAMS.items():
        if a.program and slug != a.program:
            continue
        recs += (harvest_html(slug, cfg, a.timeout) if cfg.get("mode") == "html"
                 else harvest(slug, cfg, a.timeout))

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(json.dumps({"MARKER": "INTERREG_HARVEST", "vyzvy": len(recs),
                      "by_program": dict(Counter(r["program"] for r in recs)),
                      "with_attachments": sum(1 for r in recs if r["n_attachments"]),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
