#!/usr/bin/env python3
"""Export kurátorovaného veřejného datasetu pro externí produkt → opportunities.json.

Projekce `data/opportunities_v2.jsonl` (interní zdroj pravdy) na VEŘEJNÝ kontrakt:
  • jen kurátorovaná pole (žádné interní `provenance`/`extra`/`foundation_id`, žádné scrape-internals);
  • RAW `open_from`/`deadline` → konzument si přepočítá status (snapshot `status` je jen pohodlí,
    pravdivý je výpočet z dat dle scripts/opportunities.py:compute_status);
  • `meta` = schema_version + generated_at + count → freshness signál (re-sync jen když se změní).

Tvar: {"meta": {...}, "grants": [ {...}, … ]}. Default výstup = docs/opportunities.json (publikuje
se přes GitHub Pages vedle grants_app.html; gen_pages_index.py ho kopíruje do site/branches/<b>/).

Spuštění z kořene repa (po fix_dataset, jako součást tailu):
  python3 scripts/export_api.py [--in data/opportunities_v2.jsonl] [--out docs/opportunities.json]
"""
import argparse, json, os, sys
from datetime import datetime, timezone

SCHEMA_VERSION = "1.0"
# Veřejná pole (přítomná se převezmou; mission záznamy mají name/mission/support_topics/regions).
PUBLIC = ["id", "kind", "source", "source_url", "title", "focus_area",
          "open_from", "deadline", "status", "status_confidence",
          "amount", "eligible_applicants", "required_attachments", "how_to_apply", "source_doc",
          "facets", "citations",
          "name", "mission", "support_topics", "regions"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/opportunities_v2.jsonl")
    ap.add_argument("--out", default="docs/opportunities.json")
    a = ap.parse_args()
    grants = []
    for line in open(a.inp, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        grants.append({k: r[k] for k in PUBLIC if k in r})
    out = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "count": len(grants),
            "source": "regrantio pipeline",
            # status je build-time snapshot; pro freshness přepočítej z open_from/deadline:
            "status_rule": "open if today<=deadline (deadline 'průběžně'/null→open/unknown); "
                           "announced if today<open_from; closed if today>deadline. Viz compute_status.",
        },
        "grants": grants,
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    kb = os.path.getsize(a.out) // 1024
    print(json.dumps({"MARKER": "EXPORT_API", "grants": len(grants),
                      "schema_version": SCHEMA_VERSION, "out": a.out, "kb": kb}, ensure_ascii=False))


if __name__ == "__main__":
    main()
