#!/usr/bin/env python3
"""Konsolidace facet hodnot v opportunities.jsonl dle data/consolidation_maps.json.

Otevřená extrakce tříští hodnoty (diakritika, varianty, hyperspecifika). Tady deterministický remap
varianta→kanon: exact mapa → diakritika-insensitivní → substring patterns → jinak ponech. Doplní
sektor_zadatele (rollup z kanon typ_zadatele) a normalizuje region.kraj. Reportuje singletony PŘED/PO.

Usage:
  python3 scripts/consolidate.py [--in data/opportunities_v2.jsonl] [--maps data/consolidation_maps.json] [--dry-run]
"""
import argparse, json, sys, unicodedata
from collections import Counter


def norm(s):
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    # _ a - na mezeru → substring patterny chytají i podtržítkové varianty (bytove_nouzi ~ "bytove nouzi")
    return s.lower().replace("_", " ").replace("-", " ").strip()


def make(m):
    return m, {norm(k): v for k, v in m.items()}


def remap(val, exact, norml, patterns=None):
    if val in exact:
        return exact[val]
    nv = norm(val)
    if nv in norml:
        return norml[nv]
    if patterns:
        for sub, canon in patterns:
            if norm(sub) in nv:
                return canon
    return val


def dedup(xs):
    seen, out = set(), []
    for x in xs:
        if x not in seen:
            seen.add(x); out.append(x)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/opportunities_v2.jsonl")
    ap.add_argument("--maps", default="data/consolidation_maps.json")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    M = json.load(open(a.maps, encoding="utf-8"))
    obl = make(M["oblast"]); typz = make(M["typ_zadatele"]); cil = make(M["cilova_skupina"])
    kraj = make(M["kraj"]); pats = M.get("cilova_patterns", []); sektor = M["sektor_of"]
    forma = make(M["forma_podpory"]); zdroj = make(M["zdroj_financovani"])
    rezim = make(M["rezim_prijmu"]); delka = make(M["delka"])

    recs = [json.loads(l) for l in open(a.inp, encoding="utf-8")]
    before = {k: Counter() for k in ("oblast", "typ_zadatele", "cilova_skupina", "kraj")}
    after = {k: Counter() for k in ("oblast", "typ_zadatele", "cilova_skupina", "kraj")}

    for r in recs:
        f = r.get("facets")
        if not f:
            continue
        # oblast
        ob = f.get("oblast") or []
        for v in ob: before["oblast"][v] += 1
        ob = dedup([remap(v, *obl) for v in ob])
        for v in ob: after["oblast"][v] += 1
        f["oblast"] = ob
        # typ_zadatele + sektor rollup
        tz = f.get("typ_zadatele") or []
        for v in tz: before["typ_zadatele"][v] += 1
        tz = dedup([remap(v, *typz) for v in tz])
        for v in tz: after["typ_zadatele"][v] += 1
        f["typ_zadatele"] = tz
        f["sektor_zadatele"] = dedup([sektor[v] for v in tz if v in sektor])
        # cilova_skupina (+ patterns)
        cs = f.get("cilova_skupina") or []
        for v in cs: before["cilova_skupina"][v] += 1
        cs = dedup([remap(v, cil[0], cil[1], pats) for v in cs])
        for v in cs: after["cilova_skupina"][v] += 1
        f["cilova_skupina"] = cs
        # forma_podpory / zdroj_financovani (array) — diakritika-insensitivní remap
        f["forma_podpory"] = dedup([remap(v, *forma) for v in (f.get("forma_podpory") or [])])
        f["zdroj_financovani"] = dedup([remap(v, *zdroj) for v in (f.get("zdroj_financovani") or [])])
        # rezim_prijmu / delka (scalar)
        if f.get("rezim_prijmu"):
            f["rezim_prijmu"] = remap(f["rezim_prijmu"], *rezim)
        if f.get("delka"):
            f["delka"] = remap(f["delka"], *delka)
        # region.kraj
        reg = f.get("region") or {}
        if reg.get("kraj"):
            before["kraj"][reg["kraj"]] += 1
            reg["kraj"] = remap(reg["kraj"], *kraj)
            after["kraj"][reg["kraj"]] += 1

    if not a.dry_run:
        with open(a.inp, "w", encoding="utf-8") as o:
            for r in recs:
                o.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"{'DRY-RUN ' if a.dry_run else ''}konsolidace {a.inp}:")
    for k in ("oblast", "typ_zadatele", "cilova_skupina", "kraj"):
        sb = sum(1 for v, n in before[k].items() if n == 1)
        sa = sum(1 for v, n in after[k].items() if n == 1)
        print(f"  {k:16}: variant {len(before[k])}→{len(after[k])}  singletonů {sb}→{sa}")
    # zbylé singletony cílové (kandidáti na ruční doladění)
    for k in ("cilova_skupina", "oblast"):
        sing = [v for v, n in after[k].most_common() if n == 1]
        if sing:
            print(f"  zbylé singletony {k} ({len(sing)}): {', '.join(sing[:25])}")


if __name__ == "__main__":
    main()
