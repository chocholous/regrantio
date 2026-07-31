#!/usr/bin/env python3
"""Interreg (přeshraniční programy) — layer-1 harvest výzev přes WP REST.

STRUKTURA PŘED PRÓZOU: české/slovenské Interreg weby běží na WordPressu a výzvy publikují
jako POSTY v dotačních KATEGORIÍCH → `/wp-json/wp/v2/posts?categories=<id>` dá titul, datum,
plný `content.rendered` i odkazy na přílohy. Žádný scraping HTML, žádný LLM.

Programy (per web = vlastní kategorie; slugy ověřeny živě 2026-07-31):
  sk-cz.eu  (Interreg SK-CZ)  kategorie: vyzvynapredkladaniezonfp, vyzvy_oh, vyzvy_skcz,
                              vyzva-na-dotaciu-zo-statneho-rozpoctu-cr   (13 postů)
  cz-pl.eu  (Interreg CZ-PL)  kategorie se hledají automaticky (slug obsahuje 'vyzv')

Kategorie se NEhardkódují podle id (mění se) — hledají se přes /wp-json/wp/v2/categories
podle slugu (regex `vyzv|call`), takže přidání nové kategorie na webu se propíše samo.

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
    "sk-cz": {"base": "https://www.sk-cz.eu", "name": "Interreg SK-CZ (Slovensko–Česko)"},
    "cz-pl": {"base": "https://www.cz-pl.eu", "name": "Interreg CZ-PL (Česko–Polsko)"},
}
CAT_RE = re.compile(r"vyzv|výzv|call", re.I)
DOC_RE = re.compile(r"\.(pdf|docx?|xlsx?|zip)(\?|$)", re.I)
UA = "Mozilla/5.0 (compatible; regrantio/1.0)"


def api(url, timeout=45):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with http_util.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


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
        recs += harvest(slug, cfg, a.timeout)

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
