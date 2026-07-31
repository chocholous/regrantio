#!/usr/bin/env python3
"""derive_deadlines.py — doplní `deadline` tam, kde termín JE ve zdroji, ale v jiném tvaru.

PROBLÉM: ~919 grantů má status=unknown, protože `deadline` je null. U části z nich ale termín
ve zdroji JE — jen se při extrakci uložil do `extra.deadliny[]` jako text, protože to není
jednorázové ISO datum:
    „každoročně 15.11."            → opakující se roční termín
    „31. ledna každého roku"       → totéž slovně
    „2025-03-31" (v deadliny[])    → hotové ISO, jen nepovýšené na top-level

TOHLE NENÍ HALUCINACE: datum pochází ze zdrojového textu (extra.deadliny nese i `kontext`
= doslovnou větu). Skript ho jen převádí do strojového tvaru a u opakujících se termínů
promítá na NEJBLIŽŠÍ BUDOUCÍ výskyt — což je přesně to, co uživatel potřebuje vědět
(„příští uzávěrka je …"). Neodvozuje se nic, co ve zdroji není.

Co skript NEDĚLÁ:
  • nesahá na záznamy, které už `deadline` mají
  • nehádá u vágních formulací („bude upřesněno", „průběžně během roku" bez data)
  • needituje `amount` ani jiná pole

Značení: odvozeným záznamům nastaví `status_confidence="derived"` a do
`extra.deadline_derived_from` uloží zdrojový text — v produktu i v appce je pak poznat,
že jde o odvozenou (byť doloženou) hodnotu.

Spuštění (mezi fix_dataset a build_app, nebo samostatně):
  python scripts/derive_deadlines.py --today 2026-07-31 [--dry-run]
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse
import collections
import datetime
import json
import os
import re
import shutil

MONTHS = {"ledna": 1, "února": 2, "unora": 2, "března": 3, "brezna": 3, "dubna": 4,
          "května": 5, "kvetna": 5, "června": 6, "cervna": 6, "července": 7, "cervence": 7,
          "srpna": 8, "září": 9, "zari": 9, "října": 10, "rijna": 10, "listopadu": 11,
          "prosince": 12}
MN = "|".join(MONTHS)

ISO = re.compile(r"\b(20\d\d)-(\d{2})-(\d{2})\b")
# „každoročně 15.11.", „každý rok 15.08.", „vždy 1. 3."
REC_NUM = re.compile(r"(?:každoročně|každ[ýéo]\w*\s+rok\w*|vždy|pravidelně)\s*"
                     r"(\d{1,2})\.\s*(\d{1,2})\.")
# „31. ledna každého roku", „15. listopadu každoročně"
REC_WORD = re.compile(r"(\d{1,2})\.\s*(" + MN + r")(?:\s+(?:každého\s+roku|každoročně))")
# holé „31. ledna" v poli datum (bez roku) — bereme jen když je to CELÁ hodnota
BARE_WORD = re.compile(r"^\s*(\d{1,2})\.\s*(" + MN + r")\s*$")


def next_occurrence(day, month, today):
    """Nejbližší budoucí výskyt opakujícího se dne/měsíce (dnes se počítá jako platný)."""
    y = today.year
    for cand_year in (y, y + 1):
        try:
            d = datetime.date(cand_year, month, day)
        except ValueError:
            return None
        if d >= today:
            return d.isoformat()
    return None


def derive(entry, today):
    """entry = {'datum': ..., 'kontext': ...} → (iso, důvod) nebo (None, None)."""
    raw = " ".join(str(entry.get(k) or "") for k in ("datum", "kontext"))
    if not raw.strip():
        return None, None

    # 1) hotové ISO datum → nejbližší budoucí (jinak nejpozdější, ať neztratíme info)
    isos = sorted({f"{m[1]}-{m[2]}-{m[3]}" for m in ISO.finditer(raw)})
    if isos:
        future = [d for d in isos if d >= today.isoformat()]
        return (future[0] if future else isos[-1]), "iso_v_deadliny"

    # 2) opakující se termín — číselný i slovní
    m = REC_NUM.search(raw)
    if m:
        iso = next_occurrence(int(m.group(1)), int(m.group(2)), today)
        if iso:
            return iso, "opakujici_cislo"
    m = REC_WORD.search(raw)
    if m:
        iso = next_occurrence(int(m.group(1)), MONTHS[m.group(2).lower()], today)
        if iso:
            return iso, "opakujici_slovne"
    m = BARE_WORD.match(str(entry.get("datum") or ""))
    if m:
        iso = next_occurrence(int(m.group(1)), MONTHS[m.group(2).lower()], today)
        if iso:
            return iso, "hole_datum_bez_roku"
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/opportunities_v2.jsonl")
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = datetime.date.fromisoformat(a.today)

    recs = [json.loads(l) for l in open(a.inp, encoding="utf-8") if l.strip()]
    stats = collections.Counter()
    examples = []

    for r in recs:
        if r.get("kind") != "grant" or r.get("deadline"):
            continue                                   # už má termín → nesahat
        dls = (r.get("extra") or {}).get("deadliny") or []
        if not isinstance(dls, list):
            continue
        best, why, src_text = None, None, None
        for e in dls:
            if not isinstance(e, dict):
                continue
            iso, reason = derive(e, today)
            if iso and (best is None or iso < best):   # nejbližší z nabídnutých
                best, why, src_text = iso, reason, (e.get("datum") or e.get("kontext"))
        if not best:
            continue
        stats[why] += 1
        if len(examples) < 8:
            examples.append((r.get("source"), (r.get("title") or "")[:44], src_text, best))
        if not a.dry_run:
            r["deadline"] = best
            r["status_confidence"] = "derived"
            extra = r.setdefault("extra", {}) or {}
            r["extra"] = extra
            extra["deadline_derived_from"] = src_text
            extra["deadline_derived_rule"] = why

    total = sum(stats.values())
    print(f"{'DRY-RUN ' if a.dry_run else ''}derive_deadlines (today={a.today}):")
    for k, v in stats.most_common():
        print(f"  {v:5}  {k}")
    print(f"  celkem doplněno: {total}")
    if examples:
        print("  ukázky:")
        for src, title, raw, iso in examples:
            print(f"    {str(src)[:18]:20} {title:46} „{str(raw)[:40]}\" → {iso}")

    if a.dry_run or not total:
        return
    shutil.copy2(a.inp, a.inp + ".bak")
    with open(a.inp, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  zapsáno → {a.inp} (záloha {os.path.basename(a.inp)}.bak)")


if __name__ == "__main__":
    main()
