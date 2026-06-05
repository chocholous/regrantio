#!/usr/bin/env python3
"""Granularita & úklid opportunities.jsonl (po zjištění míchání program×výzva).

1) dsw2 PROGRAM-katalog (platform=dsw2 + harvester 'programs') → kind="program" (oddělit od výzev,
   neztrácet — je to referenční katalog; appeals zůstávají kind="grant" = skutečné výzvy).
2) DROP test záznamy (chyne 'testování rozpočtu', kromeriz 'test3') — NE reálné výzvy se slovem test.
3) DROP umbrella/overview/results (přehled programů, vyhlášení výsledků soutěže = awards).
4) DEDUP hodonin.eu: re-harvestované duplicity TÉHOŽ ročníku/termínu sloučit; RŮZNÉ ročníky nechat.
   yearkey = rok (20YY z deadline/open_from) | jinak normalizovaný raw termín | 'none'.
   V bucketu (source,normtitle,yearkey) nechat nejbohatší (ISO termín > víc vyplněných polí).

Usage: python3 scripts/cleanup_granularity.py [--apply]   (bez --apply = dry-run)
"""
import argparse, json, re, sys
from collections import defaultdict

PATH = "data/opportunities.jsonl"


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]", " ", (s or "").lower())).strip()


def is_dsw2_program(r):
    p = r.get("provenance") or {}
    return p.get("platform") == "dsw2" and "programs" in (p.get("harvester") or "")


DROP_TEST = re.compile(r"testování rozpočtu|^\s*test\d|^\s*test\b", re.I)
DROP_UMB = re.compile(r"a jejich vyhodnocení|přehled (dotačních|programů)|vyhlášení výsledk|"
                      r"výsledk[uy] .*soutěž|seznam (programů|dotačních)|\(přehled dotačních", re.I)


def yearkey(r):
    txt = (r.get("deadline") or "") + " " + (r.get("open_from") or "")
    m = re.search(r"20\d\d", txt)
    if m:
        return m.group(0)
    if r.get("deadline") or r.get("open_from"):
        return norm(r.get("deadline")) + "|" + norm(r.get("open_from"))
    return "none"


def richness(r):
    f = r.get("facets") or {}
    iso = 1 if re.match(r"\d{4}-\d\d-\d\d", r.get("deadline") or "") else 0
    nn = sum(1 for v in (r.get("deadline"), r.get("open_from"), r.get("amount"),
                         r.get("eligible_applicants"), r.get("focus_area"),
                         f.get("vyse_alokace_czk")) if v)
    return (iso, nn, len(r.get("focus_area") or ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(PATH, encoding="utf-8")]

    marked = dropped_test = dropped_umb = 0
    keep = []
    hod = defaultdict(list)
    for r in rows:
        title = r.get("title") or ""
        if DROP_TEST.search(title):
            dropped_test += 1; continue
        if DROP_UMB.search(title):
            dropped_umb += 1; continue
        if is_dsw2_program(r):
            if r.get("kind") != "program":
                r["kind"] = "program"; marked += 1
        if r.get("source") == "hodonin.eu":
            hod[(norm(title), yearkey(r))].append(r); continue   # dedup zvlášť
        keep.append(r)

    # dedup hodonin: nejbohatší per (normtitle, yearkey)
    hod_kept = dropped_dup = 0
    for grp in hod.values():
        best = max(grp, key=richness)
        keep.append(best); hod_kept += 1
        dropped_dup += len(grp) - 1

    print(json.dumps({"MARKER": "CLEANUP", "vstup": len(rows), "výstup": len(keep),
                      "dsw2_program_marked": marked, "drop_test": dropped_test,
                      "drop_umbrella": dropped_umb, "hodonin_kept": hod_kept,
                      "hodonin_dedup_dropped": dropped_dup, "applied": a.apply}, ensure_ascii=False))
    if a.apply:
        with open(PATH, "w", encoding="utf-8") as o:
            for r in keep:
                o.write(json.dumps(r, ensure_ascii=False) + "\n")
        print("zapsáno do", PATH)
    else:
        print("(dry-run — spusť s --apply)")


if __name__ == "__main__":
    main()
