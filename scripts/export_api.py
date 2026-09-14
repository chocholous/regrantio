#!/usr/bin/env python3
"""Export kurátorovaného veřejného datasetu pro externí produkt → opportunities.json.

Projekce `data/opportunities.jsonl` (interní zdroj pravdy) na VEŘEJNÝ kontrakt:
  • jen kurátorovaná pole (žádné interní `provenance`/`extra`/`foundation_id`, žádné scrape-internals);
  • RAW `open_from`/`deadline` → konzument si přepočítá status (snapshot `status` je jen pohodlí,
    pravdivý je výpočet z dat dle scripts/opportunities.py:compute_status);
  • `content_hash` per grant = stabilní otisk VĚCNÝCH polí (BEZ volatilního statusu) → produkt umí
    inkrementální sync: upsert podle `id`, re-index jen když se změní `content_hash`, smaž `id`,
    které v exportu CHYBÍ (viz docs/EXPORT.md);
  • `meta` = schema_version + generated_at + count → freshness signál.

Tvar: {"meta": {...}, "grants": [ {...}, … ]}. Default výstup = docs/opportunities.json (publikuje
se přes GitHub Pages vedle grants_app.html; gen_pages_index.py ho kopíruje do site/branches/<b>/).

BEZPEČNOSTNÍ POJISTKA: pokud by nový export měl výrazně MÉNĚ záznamů než ten poslední (rozbitý
harvest by jinak smazal granty z produktu), `--min-ratio` (default 0.9) běh ZASTAVÍ. Vědomé velké
smazání povol `--force`.

Spuštění z kořene repa (po fix_dataset, jako součást tailu):
  python3 scripts/export_api.py [--in data/opportunities.jsonl] [--out docs/opportunities.json]
"""
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dedup    # noqa: E402  rodiny ročníků (variant_of, family)
import enrich   # noqa: E402  odvozená pole kontraktu 1.2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCHEMA_VERSION = "1.2"  # 1.1: + content_hash per grant; meta.generated_date + meta.content_hash_fields
# 1.2 (2026-09-14): + scope, deadline_kind, deadline_note, program_key, variant_of, family,
#     call_number, contact, documents, realization_period, field_provenance — viz docs/EXPORT.md §2b.
#     MINOR: nic se nepřejmenovalo ani neodebralo; konzument 1.1 nová pole ignoruje.
# Veřejná pole (přítomná se převezmou; mission záznamy mají name/mission/support_topics/regions).
# Jméno poskytovatele podle slugu zdroje (`data/source_names.json`). Katalog nese
# jen TYP (ministerstvo, kraj…); jméno je vlastnost ZDROJE, ne záznamu, a proto
# se dosazuje až tady. Mimo otisk: změna jména není změna výzvy.
SOURCE_NAMES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "source_names.json")
SOURCE_NAMES = {k: v for k, v in json.load(open(SOURCE_NAMES_PATH, encoding="utf-8")).items() if not k.startswith("_")}

PUBLIC = ["id", "kind", "source", "source_url", "provider", "title", "focus_area",
          "open_from", "deadline", "status", "status_confidence",
          "amount", "eligible_applicants", "required_attachments", "how_to_apply", "source_doc",
          "facets", "citations",
          "name", "mission", "support_topics", "regions",
          "fetched_at",
          # kontrakt 1.2 — obsah ze zdroje, který dřív zůstával v `extra`:
          "call_number", "contact", "documents", "realization_period",
          # kontrakt 1.2 — odvozeniny (mimo otisk, viz HASH_EXCLUDE):
          "scope", "deadline_kind", "deadline_note", "program_key", "variant_of", "family",
          "field_provenance"]

# Odvozeniny NEJSOU obsah výzvy. Změna pravidla v `enrich.py` nebo nový ročník
# v rodině nesmí každému záznamu přepnout otisk a v produktu vyrobit tisíce
# „změn" — otisk má hlásit jen to, co změnil poskytovatel.
DERIVED = {"scope", "deadline_kind", "deadline_note", "program_key", "variant_of", "family",
           "field_provenance"}

# content_hash = otisk VĚCNÝCH polí. Vyloučeno: `status`/`status_confidence` (derivovaný snapshot,
# mění se sám jak míjejí deadliny → jinak by hash „blikal" každý den), `id` (je to klíč, ne obsah)
# a `fetched_at` (den kontroly, ne obsah — jinak by po každé obnově vypadalo všech 3450 záznamů
# jako změněných a inkrementální sync by ztratil smysl, kvůli kterému existuje).
HASH_EXCLUDE = {"status", "status_confidence", "id", "fetched_at", "provider"} | DERIVED
HASH_FIELDS = [k for k in PUBLIC if k not in HASH_EXCLUDE]


def content_hash(rec):
    """Stabilní sha1 věcného obsahu záznamu (canonical JSON, seřazené klíče)."""
    payload = {k: rec[k] for k in HASH_FIELDS if k in rec}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/opportunities.jsonl")
    ap.add_argument("--out", default="docs/opportunities.json")
    ap.add_argument("--min-ratio", type=float, default=0.9,
                    help="Pojistka: zastav, pokud nový count < min-ratio * předchozí count (rozbitý harvest).")
    ap.add_argument("--force", action="store_true", help="Obejít pojistku --min-ratio (vědomé velké smazání).")
    a = ap.parse_args()
    grants = []
    raw_records = [json.loads(line) for line in open(a.inp, encoding="utf-8") if line.strip()]
    today = datetime.now(timezone.utc).date().isoformat()
    families = dedup.assign_families(raw_records, today)
    for r in raw_records:
        # `fetched_at` je uvnitř `provenance` (to se ven nepouští celé) — vytáhni ho nahoru.
        # Chybí u záznamů, kterých se od zavedení razítka nedotkla žádná obnova; ven jde
        # rovnou jako null, protože „nevíme" je pravdivější než vymyšlené datum.
        prov = r.get("provenance") or {}
        r = {**r, "fetched_at": prov.get("fetched_at"), "provider": SOURCE_NAMES.get(r.get("source"))}
        g = {k: r[k] for k in PUBLIC if k in r}
        # ⚠ KONTRAKT: `eligible_applicants` je string | null (EXPORT.md). Strukturní
        # ingesty krajů (lbc, stredoceskykraj, pardubice, ostrava…) tam dávaly SEZNAM
        # — 173 záznamů v rozporu s kontraktem, produkt to četl jako řetězec
        # a vypisoval `["obec"]`. Seznam se tu sklízí do jedné věty; typ hlídá
        # brána v `validate_release.py`.
        ea = g.get("eligible_applicants")
        if isinstance(ea, list):
            g["eligible_applicants"] = ", ".join(str(x).strip() for x in ea if str(x).strip()) or None
        elif isinstance(ea, str) and not ea.strip():
            g["eligible_applicants"] = None
        if g.get("kind") == "grant":
            g.update(enrich.enrich(r))
            fam = families.get(g["id"]) or {"variant_of": None, "family": None}
            g["variant_of"] = fam["variant_of"]
            g["family"] = fam["family"]
            # Rodina je DOKLAD opakování: program bez jedné lhůty, který zdroj
            # listuje ve dvou a víc ročnících, se vyhlašuje znovu.
            if g["deadline_kind"] == "unknown" and fam["family"] and len(fam["family"]["years"]) >= 2:
                g["deadline_kind"] = "recurring"
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
                          "hint": "rozbitý harvest? zkontroluj data/opportunities.jsonl; vědomě přepiš --force"},
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
