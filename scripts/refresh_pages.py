#!/usr/bin/env python3
"""Obnova zdroje bez sběrače: znovu se stáhnou stránky, které katalog už zná.

⚠ PROČ (2026-11-09). Sedmnáct zdrojů se do katalogu dostalo jednorázovým
během (třída „?“ a T v `data/sources.json`) a nemá sběrač: MŽP, MV, Česko-
německý fond budoucnosti, Sociální nadační fond Praha, nadace OKD, Agrofert,
Naše dítě… Jejich záznamy stárnou a nikdo neví, jestli ještě platí.

Napsat ke každému webu sběrač je drahé a stejně by se pak všechno četlo
modelem znovu. Tenhle skript jde opačně: vezme adresy, které katalog u zdroje
má, stáhne je a u každé zjistí, jestli se změnila:

  beze změny   citace lhůty (`citations`, doslovný úryvek, ze kterého vrstva 2
               lhůtu vzala) na stránce pořád stojí → údaje platí, nečte se znovu
  změněná      citace zmizela → stránka jde ke čtení
  bez citace   záznam citaci lhůty nemá → ke čtení, jen je-li živý
  nedostupná   HTTP chyba → jen se vypíše; stažení je vědomé rozhodnutí

Ke čtení zapíše `data/<zdroj>_documents.jsonl` ve tvaru `harvest_site`
s klíčem `catalog_id`: `build_extract_input` ho vezme za `id` dokumentu,
takže výstup se spojí s TÍMŽ záznamem (i když má `id` z názvu, ne z adresy)
a nevznikne duplicita. Dál stejně jako třída C:

    python scripts/refresh_pages.py --source fondbudoucnosti
    python scripts/build_extract_input.py data/fondbudoucnosti_documents.jsonl --source fondbudoucnosti \\
        --out-dir data/fondbudoucnosti_in --force-type grant --no-prefilter
    python scripts/extract_manual.py --in-dir data/fondbudoucnosti_in --out-dir data/fondbudoucnosti_out --tasks …
    python scripts/ingest_rich.py --out-dir data/fondbudoucnosti_out --src data/fondbudoucnosti_in …

Nové výzvy, které zdroj mezitím vypsal, tahle cesta nenajde; to umí jen
sběrač. Je to obnova toho, co katalog o zdroji tvrdí, ne objevování.
"""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest_site import clean, fetch, parse  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def norm(s):
    s = unicodedata.normalize("NFKC", s or "").replace("\xa0", " ").casefold()
    return re.sub(r"\s+", " ", s).strip()


def quote_on_page(quote, page_text):
    """Citace (i složená z kusů „ / “) na stránce stojí celá."""
    parts = [norm(p) for p in re.split(r"\s+/\s+|\s*…\s*|\.\.\.", quote or "") if len(norm(p)) >= 8]
    return bool(parts) and all(p in page_text for p in parts)


def deadline_quote(rec):
    for c in rec.get("citations") or []:
        if c.get("field") == "deadline" and c.get("quote"):
            return c["quote"]
    ev = (rec.get("extra") or {}).get("evidence") or {}
    return ev.get("deadline") if isinstance(ev, dict) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="slug zdroje v katalogu")
    ap.add_argument("--catalog", default="data/opportunities.jsonl")
    ap.add_argument("--out", help="výchozí data/<zdroj>_documents.jsonl")
    ap.add_argument("--all", action="store_true", help="ke čtení i stránky beze změny")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--stamp", action="store_true",
                    help="záznamům beze změny zapsat do katalogu dnešní `fetched_at` (ověřeno u zdroje)")
    a = ap.parse_args()
    out = a.out or f"data/{a.source}_documents.jsonl"

    recs = [r for r in map(json.loads, open(a.catalog, encoding="utf-8"))
            if r.get("source") == a.source and r.get("kind") == "grant" and (r.get("source_url") or "").startswith("http")]
    verdict, docs = {}, []
    for r in recs:
        url = r["source_url"]
        try:
            html = fetch(url, a.timeout)
        except urllib.error.HTTPError as e:
            verdict[r["id"]] = f"nedostupná ({e.code})"
            continue
        except Exception as e:  # síť, TLS
            verdict[r["id"]] = f"nedostupná ({type(e).__name__})"
            continue
        page = parse(url, html)
        text = norm(page["title"] + " " + page["text"] + " " + clean(html))
        q = deadline_quote(r)
        live = r.get("status") != "closed"
        if q and quote_on_page(q, text):
            v = "beze změny"
        elif q:
            v = "změněná"
        else:
            v = "bez citace"
        verdict[r["id"]] = v
        if a.all or v == "změněná" or (v == "bez citace" and live):
            page["catalog_id"] = r["id"]
            page["source"] = a.source
            docs.append(page)
        time.sleep(0.3)

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as o:
        for d in docs:
            o.write(json.dumps(d, ensure_ascii=False) + "\n")
    stamped = 0
    if a.stamp:
        # ⚠ Razítko „ověřeno dnes“ jen tam, kde citace lhůty na stránce dnes
        # opravdu stojí. Změněné stránky ho dostanou až s novým čtením (ingest).
        import upsert
        ok = {rid for rid, v in verdict.items() if v == "beze změny"}
        lines = open(a.catalog, encoding="utf-8").read().split("\n")
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("id") in ok:
                lines[i] = json.dumps(upsert.stamp(r), ensure_ascii=False)
                stamped += 1
        tmp = a.catalog + ".tmp"
        open(tmp, "w", encoding="utf-8", newline="").write("\n".join(lines))
        os.replace(tmp, a.catalog)
    counts = {}
    for v in verdict.values():
        k = v.split(" (")[0]
        counts[k] = counts.get(k, 0) + 1
    for rid, v in verdict.items():
        if v.startswith("nedostupná"):
            print(f"  ⚠ {v}: {rid[-70:]}", file=sys.stderr)
    print(json.dumps({"MARKER": "REFRESH_PAGES", "source": a.source, "records": len(recs),
                      "verdict": counts, "to_read": len(docs), "stamped": stamped, "out": out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
