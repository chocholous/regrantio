#!/usr/bin/env python3
"""Vrstva 2 pro OP Doprava 2021–2027 (opd3.opd.cz; harvester scripts/opd.py).

DETERMINISTICKY z tabulky výzev — harvester už rozparsoval `Datum vyhlášení` (open_from)
a `Datum ukončení příjmu žádostí` (deadline), takže se tu nic nehádá. STATUS POČÍTÁ KÓD.

Oblast = doprava → kanonicky `bydleni_infrastruktura` (viz consolidation_maps: doprava→…).
zdroj_financovani = eu_fondy (EFRR/FS), typ_poskytovatele doplní fix_dataset (ministerstvo).
amount = null — alokace je až v textu výzvy (PDF), nefabrikujeme.

Join: data/opd_in/grant_NN.json ↔ data/opd_documents.jsonl dle id (= url).
Spuštění: python data/_opd_extract.py   (po build_extract_input --no-prefilter)
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import glob
import json
import os
import re

IN_DIR, OUT_DIR = "data/opd_in", "data/opd_out"
HARVEST = "data/opd_documents.jsonl"
CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]

HOW = ("Žádost o podporu se podává elektronicky v IS KP21+ (MS2021+) ve lhůtě uvedené ve výzvě; "
       "podmínky jsou v textu výzvy a Pravidlech pro žadatele a příjemce OP Doprava.")

# tematické zaměření dle názvu výzvy (kanonizuje consolidate.py)
KW = [
    (r"železnič|drá[hž]|ETCS|trať", ["doprava", "železniční doprava"]),
    (r"silnic|dálnic|TEN-T", ["doprava"]),
    (r"městsk|drážní|tramvaj|trolejbus|metro", ["doprava", "komunitní rozvoj"]),
    (r"cyklo", ["doprava", "sport/volný čas"]),
    (r"alternativn|dobíjec|vodík", ["doprava", "životní prostředí"]),
    (r"multimodáln|překladi|vnitrozemsk|vodní", ["doprava"]),
]


def build(rec, src):
    title = re.sub(r"\s+", " ", rec.get("title") or "").strip()
    body = src.get("body") or rec.get("body_text") or ""
    ctx = f"{title} {body[:1500]}"
    oblast = []
    for pat, obs in KW:
        if re.search(pat, ctx, re.I):
            for o in obs:
                if o not in oblast:
                    oblast.append(o)
    if not oblast:
        oblast = ["doprava"]

    ev = {}
    if rec.get("deadline") and rec.get("deadline_raw"):
        ev["deadline"] = f"Datum ukončení příjmu žádostí o podporu: {rec['deadline_raw']}"
    if rec.get("open_from") and rec.get("open_from_raw"):
        ev["open_from"] = f"Datum vyhlášení výzvy: {rec['open_from_raw']}"

    src_doc = None
    for aatt in rec.get("attachments") or []:
        if (aatt.get("url") or "").lower().endswith(".pdf"):
            src_doc = aatt["url"]
            break

    return {
        "title": title,
        "focus_area": ("Výzva Operačního programu Doprava 2021–2027 (EFRR/Fond soudržnosti) — "
                       "podpora dopravní infrastruktury a udržitelné mobility."),
        "oblast": oblast,
        "open_from": rec.get("open_from"), "deadline": rec.get("deadline"),
        "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
        "eligible_applicants": None,     # oprávnění žadatelé jsou v textu výzvy (PDF)
        "typ_zadatele": [], "cilova_skupina": [],
        "region": CR,
        "forma_podpory": ["dotace"], "zdroj_financovani": ["eu_fondy"],
        "rezim_prijmu": "prubezna" if rec.get("deadline") else "neuvedeno", "delka": None,
        "how_to_apply": HOW, "required_attachments": [],
        "source_doc": src_doc or rec.get("url"),
        "poskytovatel": "Ministerstvo dopravy (řídící orgán OP Doprava)",
        "cislo_vyzvy": (f"{rec.get('cislo_vyzvy')} (OP Doprava)" if rec.get("cislo_vyzvy") else None),
        "evidence": ev,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for p in glob.glob(os.path.join(OUT_DIR, "grant_*.json")):
        os.remove(p)
    by_id = {}
    for line in open(HARVEST, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            by_id[r.get("url")] = r
    n, skipped = 0, 0
    for path in sorted(glob.glob(os.path.join(IN_DIR, "grant_*.json"))):
        src = json.load(open(path, encoding="utf-8"))
        rec = by_id.get(src.get("id"))
        if not rec or rec.get("kind") != "vyzva":
            skipped += 1
            continue
        f = build(rec, src)
        json.dump(f, open(os.path.join(OUT_DIR, os.path.basename(path)), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
    print(f"wrote {n} grants -> {OUT_DIR}/ (skipped {skipped})")


if __name__ == "__main__":
    main()
