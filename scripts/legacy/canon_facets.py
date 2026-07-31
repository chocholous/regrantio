#!/usr/bin/env python3
"""Vynuť řízené facety ∈ kanonický slovník (consolidation_maps). Co není kanon → zahodit.

Po consolidate (variant→kanon) tohle smete zbylý free-text ocas (např. služby/mise nadací
v forma_podpory, mis-zařazené hodnoty). LIST facety: filtr+dedup; SCALAR: None když ne-kanon.
Spouštět PO consolidate.py.

Usage: python3 scripts/canon_facets.py [--maps data/consolidation_maps.json] [--in data/opportunities.jsonl]
"""
import argparse, json
from collections import Counter

LIST_FACETS = ("oblast", "typ_zadatele", "cilova_skupina", "forma_podpory", "zdroj_financovani")
SCALAR_FACETS = ("rezim_prijmu", "delka")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--maps", default="data/consolidation_maps.json")
    ap.add_argument("--in", dest="inp", default="data/opportunities.jsonl")
    a = ap.parse_args()
    maps = json.load(open(a.maps, encoding="utf-8"))
    CAN = {f: set(maps[f].values()) for f in LIST_FACETS + SCALAR_FACETS if f in maps}
    rows = [json.loads(l) for l in open(a.inp, encoding="utf-8")]
    dropped = Counter()
    for r in rows:
        f = r.get("facets") or {}
        for facet in LIST_FACETS:
            canon = CAN.get(facet)
            if canon is None:
                continue
            before = f.get(facet) or []
            seen = set(); after = [v for v in before if v in canon and not (v in seen or seen.add(v))]
            dropped[facet] += len(before) - len(after)
            f[facet] = after
        for facet in SCALAR_FACETS:
            canon = CAN.get(facet)
            if canon is None:
                continue
            v = f.get(facet)
            if v is not None and v not in canon:
                f[facet] = None; dropped[facet] += 1
    with open(a.inp, "w", encoding="utf-8") as o:
        for r in rows:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    # ověření: 0 ne-kanon
    nonc = Counter()
    for r in rows:
        f = r.get("facets") or {}
        for facet in LIST_FACETS + SCALAR_FACETS:
            canon = CAN.get(facet)
            if canon is None:
                continue
            v = f.get(facet)
            for x in (v if isinstance(v, list) else [v]):
                if x and x not in canon:
                    nonc[facet] += 1
    print(json.dumps({"MARKER": "CANON_FACETS", "dropped": dict(dropped), "ne_kanon_zbylo": dict(nonc)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
