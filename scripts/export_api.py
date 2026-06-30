#!/usr/bin/env python3
"""Export kurátorovaného veřejného datasetu pro externí produkt → opportunities.json.

Projekce `data/opportunities_v2.jsonl` (interní zdroj pravdy) na VEŘEJNÝ kontrakt:
  • jen kurátorovaná pole (žádné interní `provenance`/`extra`/`foundation_id`, žádné scrape-internals);
  • RAW `open_from`/`deadline` → konzument si přepočítá status (snapshot `status` je jen pohodlí,
    pravdivý je výpočet z dat dle scripts/opportunities.py:compute_status);
  • `content_hash` per grant = stabilní otisk VĚCNÝCH polí (BEZ volatilního statusu) → produkt umí
    inkrementální sync: upsert podle `id`, re-index jen když se změní `content_hash`, smaž `id`,
    které v exportu CHYBÍ (viz docs/PRODUCT_API.md);
  • `meta` = schema_version + generated_at + count → freshness signál.

Tvar: {"meta": {...}, "grants": [ {...}, … ]}. Default výstup = docs/opportunities.json (publikuje
se přes GitHub Pages vedle grants_app.html; gen_pages_index.py ho kopíruje do site/branches/<b>/).

BEZPEČNOSTNÍ POJISTKA: pokud by nový export měl výrazně MÉNĚ záznamů než ten poslední (rozbitý
harvest by jinak smazal granty z produktu), `--min-ratio` (default 0.9) běh ZASTAVÍ. Vědomé velké
smazání povol `--force`.

Spuštění z kořene repa (po fix_dataset, jako součást tailu):
  python3 scripts/export_api.py [--in data/opportunities_v2.jsonl] [--out docs/opportunities.json]
"""
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCHEMA_VERSION = "1.1"  # 1.1: + content_hash per grant; meta.generated_date + meta.content_hash_fields
# Veřejná pole (přítomná se převezmou; mission záznamy mají name/mission/support_topics/regions).
PUBLIC = ["id", "kind", "source", "source_url", "title", "focus_area",
          "open_from", "deadline", "status", "status_confidence",
          "amount", "eligible_applicants", "required_attachments", "how_to_apply", "source_doc",
          "facets", "citations",
          "name", "mission", "support_topics", "regions"]

# content_hash = otisk VĚCNÝCH polí. Vyloučeno: `status`/`status_confidence` (derivovaný snapshot,
# mění se sám jak míjejí deadliny → jinak by hash „blikal" každý den) a `id` (je to klíč, ne obsah).
HASH_EXCLUDE = {"status", "status_confidence", "id"}
HASH_FIELDS = [k for k in PUBLIC if k not in HASH_EXCLUDE]


def content_hash(rec):
    """Stabilní sha1 věcného obsahu záznamu (canonical JSON, seřazené klíče)."""
    payload = {k: rec[k] for k in HASH_FIELDS if k in rec}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/opportunities_v2.jsonl")
    ap.add_argument("--out", default="docs/opportunities.json")
    ap.add_argument("--min-ratio", type=float, default=0.9,
                    help="Pojistka: zastav, pokud nový count < min-ratio * předchozí count (rozbitý harvest).")
    ap.add_argument("--force", action="store_true", help="Obejít pojistku --min-ratio (vědomé velké smazání).")
    a = ap.parse_args()
    grants = []
    for line in open(a.inp, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        g = {k: r[k] for k in PUBLIC if k in r}
        g["content_hash"] = content_hash(g)
        grants.append(g)

    # Pojistka proti kolapsu datasetu (rozbitý harvest → produkt by smazal granty).
    prev = 0
    if os.path.exists(a.out):
        try:
            prev = json.load(open(a.out, encoding="utf-8")).get("meta", {}).get("count", 0)
        except Exception:
            prev = 0
    if prev and len(grants) < a.min_ratio * prev and not a.force:
        print(json.dumps({"MARKER": "EXPORT_API_ABORT", "reason": "count_collapse",
                          "new": len(grants), "prev": prev, "min_ratio": a.min_ratio,
                          "hint": "rozbitý harvest? zkontroluj data/opportunities_v2.jsonl; vědomě přepiš --force"},
                         ensure_ascii=False))
        sys.exit(2)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    out = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": now.isoformat(),
            "generated_date": now.date().isoformat(),
            "count": len(grants),
            "source": "regrantio pipeline",
            "content_hash_fields": HASH_FIELDS,
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
    print(json.dumps({"MARKER": "EXPORT_API", "grants": len(grants), "prev_count": prev,
                      "schema_version": SCHEMA_VERSION, "out": a.out, "kb": kb}, ensure_ascii=False))


if __name__ == "__main__":
    main()
