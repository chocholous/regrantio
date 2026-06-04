#!/usr/bin/env python3
"""Mid-run kvalitativní sonda nad /tmp/out — JEDEN řádek, bez zápisu (read-only).

NEopravuje (to dělá repair_out.py po doběhu) — jen MĚŘÍ: kolik souborů, kolik se rovnou
parsuje (raw json.loads — partial zápis = chvilkově ne), % s evidence, prům. vyplněných polí,
shoda tvaru region[] (klíče nazev/obec/okres/kraj/celostatni), low_fill, prázdné citace.
Partial/parse-fail NEní alarm během běhu (json_repair je až po). Usage: python3 scripts/probe_quality.py [outdir]
"""
import glob, json, os, sys

REGION_KEYS = {"nazev", "obec", "okres", "kraj", "celostatni"}


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/out"
    files = sorted(glob.glob(f"{outdir}/grant_*.json")) + sorted(glob.glob(f"{outdir}/mission_*.json"))
    n = len(files)
    parsed = with_ev = region_ok = region_tot = low_fill = 0
    fills, sizes = [], []
    parse_fail = []
    for fp in files:
        try:
            obj = json.loads(open(fp, encoding="utf-8").read())
        except Exception:
            parse_fail.append(os.path.basename(fp))
            continue
        parsed += 1
        sizes.append(os.path.getsize(fp))
        if obj.get("evidence"):
            with_ev += 1
        keys = [k for k in obj if k != "evidence"]
        filled = sum(1 for k in keys if obj[k] not in (None, "", [], {}))
        fills.append(filled)
        if keys and filled / len(keys) < 0.25:
            low_fill += 1
        for r in (obj.get("region") or []):
            region_tot += 1
            if isinstance(r, dict) and set(r.keys()) <= REGION_KEYS and r.keys():
                region_ok += 1
    avg_fill = round(sum(fills) / len(fills), 1) if fills else 0
    avg_sz = round(sum(sizes) / len(sizes)) if sizes else 0
    pct = lambda a, b: f"{round(100*a/b)}%" if b else "—"
    print(f"kvalita: {n} souborů | parse {pct(parsed,n)} ({len(parse_fail)} partial) | "
          f"evidence {pct(with_ev,parsed)} | prům {avg_fill} polí, {avg_sz}B | "
          f"region tvar {pct(region_ok,region_tot)} ({region_tot} obj) | low_fill {low_fill}"
          + (f" | partial: {' '.join(parse_fail[:6])}" if parse_fail else ""))


if __name__ == "__main__":
    main()
