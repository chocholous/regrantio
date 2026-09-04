#!/usr/bin/env python3
"""Vrstva 2 pro ESF ČR / OPZ+ a OPZ (esfcr.cz; harvester scripts/esfcr_harvest.py).

DETERMINISTICKY ze STRUKTUROVANÝCH polí detailu (Liferay `<strong>Label:</strong>` bloky,
už rozparsované harvesterem): platnost_od/zahajeni_prijmu → open_from, platnost_do → deadline,
alokace_kc → částka, urceno_pro/specificky_cil/priorita → popisná pole. STATUS POČÍTÁ KÓD.

SCOPE: ingestují se jen kind=vyzva_opz_plus (2021–2027, aktuální program) a vyzva_opz
(2014–2020, uzavřené reference — jako eeagrants). kind=vyzva_archiv_sitemap (éra OP LZZ
2007–2013, bez strukturovaných dat) se do datasetu NEBERE (lossless zůstává v harvest
souboru) — 20 let staré výzvy bez dat by jen přidaly status=unknown šum.

POZOR: „Typ výzvy: uzavřená" = REŽIM (výzva pro předem určené žadatele), NE status —
ukládá se do extra.typ_vyzvy.

Join: data/esfcr_in/grant_NN.json ↔ data/esfcr_documents.jsonl dle id (= url).
Spuštění: python data/_esfcr_extract.py   (po build_extract_input --no-prefilter)
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

IN_DIR, OUT_DIR = "data/esfcr_in", "data/esfcr_out"
HARVEST = "data/esfcr_documents.jsonl"
CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
INGEST_KINDS = {"vyzva_opz_plus", "vyzva_opz"}

HOW = ("Žádost o podporu se zpracovává a podává elektronicky v IS KP21+ (OPZ+) resp. IS KP14+ (OPZ) "
       "ve lhůtě uvedené ve výzvě; podmínky jsou v textu výzvy a navazující dokumentaci.")


def cz_dt_iso(s):
    """'24. 09. 2026 12:00' / '30. 7. 2026 09:00' → '2026-09-24' (čas se zahazuje, den platí)."""
    if not s:
        return None
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)", s)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if 1 <= d <= 31 and 1 <= mo <= 12:
        return f"{y}-{mo:02d}-{d:02d}"
    return None


def num(s):
    if not s:
        return None
    d = re.sub(r"\D", "", s)
    if d and 10_000 <= int(d) <= 500_000_000_000:
        return int(d)
    return None


def build(rec):
    title = (rec.get("title") or "").strip()
    open_from = cz_dt_iso(rec.get("zahajeni_prijmu") or rec.get("platnost_od"))
    deadline = cz_dt_iso(rec.get("platnost_do") or rec.get("platnost_do_listing"))
    amount = num(rec.get("alokace_kc"))
    cislo = rec.get("cislo_vyzvy")
    program = rec.get("program") or ("OPZ+" if rec.get("kind") == "vyzva_opz_plus" else "OPZ")
    sc = (rec.get("specificky_cil") or "").strip()
    prio = (rec.get("priorita") or "").strip()

    focus = f"Výzva č. {cislo} {program}" if cislo else f"Výzva {program}"
    if prio:
        focus += f" – {prio}"
    if sc:
        focus += f". Specifický cíl: {sc[:220]}"

    ev = {}
    if deadline and rec.get("platnost_do"):
        ev["deadline"] = f"Platnost do: {rec['platnost_do']}"
    if open_from and (rec.get("zahajeni_prijmu") or rec.get("platnost_od")):
        ev["open_from"] = f"Zahájení příjmu žádostí o podporu: {rec.get('zahajeni_prijmu') or rec.get('platnost_od')}"
    if amount and rec.get("alokace_kc"):
        ev["vyse_hlavni_czk"] = f"Alokace v Kč: {rec['alokace_kc']}"

    src_doc = None
    for a in rec.get("attachments") or []:
        nm = (a.get("name") or "").lower()
        if "výzv" in nm or "vyzv" in nm:
            src_doc = a.get("url")
            break
    if not src_doc and rec.get("attachments"):
        src_doc = rec["attachments"][0].get("url")

    return {
        "title": title,
        "focus_area": focus,
        "oblast": ["sociální", "vzdělávání"] if program == "OPZ+" else ["sociální"],
        "open_from": open_from, "deadline": deadline,
        "castky": ([{"typ": "alokace", "hodnota": amount}] if amount else []),
        "vyse_hlavni_czk": amount, "spoluucast": None,
        "eligible_applicants": (rec.get("urceno_pro") or None),
        "typ_zadatele": [], "cilova_skupina": [],
        "region": CR,
        "forma_podpory": ["dotace"], "zdroj_financovani": ["eu_fondy"],
        "rezim_prijmu": None, "delka": None,
        "how_to_apply": HOW, "required_attachments": [],
        "source_doc": src_doc or rec.get("url"),
        "poskytovatel": rec.get("vyhlasovatel") or "MPSV (řídící orgán OPZ+)",
        "cislo_vyzvy": (f"{cislo} ({program})" if cislo else None),
        "operacni_program": rec.get("operacni_program"),
        "programove_obdobi": rec.get("programove_obdobi"),
        "typ_vyzvy": rec.get("typ_vyzvy"),      # REŽIM výzvy (otevřená/uzavřená), NE status!
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
        if not rec or rec.get("kind") not in INGEST_KINDS:
            skipped += 1        # LZZ archiv / listing → NEzapisovat out
            continue
        f = build(rec)
        json.dump(f, open(os.path.join(OUT_DIR, os.path.basename(path)), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
    print(f"wrote {n} grants -> {OUT_DIR}/ (skipped {skipped}: LZZ archiv/listing)")


if __name__ == "__main__":
    main()
