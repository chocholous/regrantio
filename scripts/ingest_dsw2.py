#!/usr/bin/env python3
"""DSW2 / Otevřená města → katalog: UPSERT výzev i programů (2026‑10‑09).

    python scripts/dsw2.py --no-opendata --no-csu            # sklizeň 28 portálů
    python scripts/ingest_dsw2.py                            # upsert do data/opportunities.jsonl
    python scripts/ingest_dsw2.py --dry-run                  # jen spočítej

⚠ PROČ VLASTNÍ SKRIPT. Do 2026‑10‑09 šly DSW2 portály do katalogu přes
`opportunities.py --from-dsw2`, který APPENDUJE a existující `id` přeskočí:
re-harvest se změněnou lhůtou se do katalogu nikdy nepropsal. 22 obecních
portálů proto v katalogu stálo s daty z 31. 7. a v inventáři zdrojů bez
data sběru. Tenhle skript bere TYTÉŽ převodníky (`ingest_dsw2`,
`ingest_dsw2_programs` z `opportunities.py`) a zapisuje přes sdílený
`upsert` (nový záznam přidá, existující aktualizuje, nic nemaže, obohacený
záznam přepíše jen ve faktech, každému dá razítko `fetched_at`).

⚠ PRÁZDNÁ SKLIZEŇ NIC NEZAPÍŠE. Když portál v sklizni chybí úplně (výpadek),
jeho záznamy v katalogu zůstanou, jak byly; upsert nemaže.
"""
import argparse
import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
from opportunities import ingest_dsw2, ingest_dsw2_programs  # noqa: E402
import upsert  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--appeals", default="data/dsw2_appeals.jsonl")
    ap.add_argument("--programs", default="data/dsw2_programs.jsonl")
    ap.add_argument("--out", default="data/opportunities.jsonl")
    ap.add_argument("--today", help="referenční datum YYYY-MM-DD (default dnes)")
    ap.add_argument("--dry-run", action="store_true", help="upsert do kopie, katalog se nezmění")
    a = ap.parse_args()

    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    recs = []
    if os.path.exists(a.appeals):
        recs += list(ingest_dsw2(a.appeals, today))
    if os.path.exists(a.programs):
        recs += list(ingest_dsw2_programs(a.programs, today))
    if not recs:
        print(json.dumps({"MARKER": "INGEST_DSW2", "error": "prázdná sklizeň, nic se nezapisuje"}, ensure_ascii=False))
        return 1

    target = a.out
    if a.dry_run:
        target = a.out + ".dsw2-dry"
        shutil.copyfile(a.out, target)
    stats = upsert.upsert(target, recs, today.isoformat())
    if a.dry_run:
        os.remove(target)
    by_source = {}
    for r in recs:
        by_source[r.get("source")] = by_source.get(r.get("source"), 0) + 1
    print(json.dumps({"MARKER": "INGEST_DSW2", "records": len(recs), "dry_run": a.dry_run, **stats,
                      "sources": len(by_source)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
