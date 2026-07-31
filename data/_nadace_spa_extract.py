#!/usr/bin/env python3
"""Vrstva 2 pro JS-renderované nadace (harvester scripts/nadace_spa.py).

FILTR OBSAHU — crawl seed→detail nabere i stránky, které NEJSOU grantová příležitost:
  SKIP  softwarové/produktové stránky (Grantys = software nadace, ne grant),
        „Známe vítěze / výsledky", archivy, obecné info pro žadatele, stránky pro firmy/dárce
  SKIP  duplicitní tituly (crawl potká tutéž stránku z víc cest)
  SKIP  ročníky STARŠÍ než --since-year (Sázíme budoucnost 2024/2025 vs aktuální 2026)
  TAKE  konkrétní grantová výzva/program s termínem nebo aspoň s grantovým titulem

deadline = české datum ve větě s uzávěrkou/termínem; „průběžně do D.M.RRRR" se bere jako
deadline (konec průběžného příjmu). Když datum chybí → None (status unknown), NEfabrikuje se.
amount = jen z titulu typu „granty do 100 tisíc" (jednoznačné); jinak null.

Join: data/nadace_spa_in/grant_NN.json ↔ data/nadace_spa_documents.jsonl dle id (= url).
Spuštění: python data/_nadace_spa_extract.py [--since-year 2026]
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse
import glob
import json
import os
import re

IN_DIR, OUT_DIR = "data/nadace_spa_in", "data/nadace_spa_out"
HARVEST = "data/nadace_spa_documents.jsonl"
CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]

SKIP_TITLE = re.compile(
    r"grantys|známe vítěze|vítěz\w*|výsledk\w*|archiv|pro firmy|pro dárce|všeobecné informace"
    r"|o nadaci|kontakt|newsletter|přehled programů|informace pro žadatele"
    # LISTINGY (nesou VÍC výzev najednou → jeden záznam by z nich udělal chiméru:
    # osf.cz/granty má 5 různých uzávěrek) + default WP titulky + retrospektivy
    r"|^granty$|^grants$|^programy$|^výzvy$|^oblasti podpor$|^žádosti o granty$"
    r"|další web používající wordpress|historie podpory|^nadace \w+$", re.I)
TAKE_TITLE = re.compile(r"grant|výzv|vyzv|program|stipend|podpor|cena|fond", re.I)
DL = re.compile(
    r"(?:uz[áa]v[ěe]rk\w*|term[íi]n\w*|do dne|žádost\w*[^\n]{0,40}?do|průběžně do|deadline)"
    r"[^\n]{0,60}?(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)", re.I)
AMOUNT_TITLE = re.compile(r"do\s*(\d{1,3})\s*(tis[íi]c|000)", re.I)
YEAR_TITLE = re.compile(r"\b(20\d\d)\b")


def _iso(d, m, y):
    d, m, y = int(d), int(m), int(y)
    return f"{y}-{m:02d}-{d:02d}" if 1 <= d <= 31 and 1 <= m <= 12 else None


def _sentence(text, pos, width=180):
    start = max(0, text.rfind("\n", 0, pos), text.rfind(". ", max(0, pos - width), pos))
    return re.sub(r"\s+", " ", text[start:pos + 120]).strip(" .;\n")[:260]


def build(rec, src, deadline, ev):
    title = re.sub(r"\s*[–|-]\s*(Nadace|Liga)[^|–-]*$", "", rec.get("title") or "").strip()
    nadace = rec.get("nadace") or ""
    amount = None
    m = AMOUNT_TITLE.search(title)
    if m:
        n = int(m.group(1))
        amount = n * 1000 if "tis" in m.group(2).lower() else n * 1000
        ev["vyse_hlavni_czk"] = m.group(0)

    return {
        "title": f"{title} ({nadace})" if nadace and nadace.split()[0].lower() not in title.lower() else title,
        "focus_area": f"Grantový program — {nadace}.",
        "oblast": ["komunitní rozvoj"],
        "open_from": None, "deadline": deadline,
        "castky": ([{"typ": "strop na projekt", "hodnota": amount}] if amount else []),
        "vyse_hlavni_czk": amount, "spoluucast": None,
        "eligible_applicants": None,
        "typ_zadatele": ["neziskovka"], "cilova_skupina": [],
        "region": CR,
        "forma_podpory": ["dotace"], "zdroj_financovani": ["vlastni_zdroje"],
        "rezim_prijmu": "kolova" if deadline else "neuvedeno", "delka": None,
        "how_to_apply": (f"Žádost se podává způsobem uvedeným na stránce programu "
                         f"({nadace}); u řady programů přes online systém Grantys."),
        "required_attachments": [], "source_doc": rec.get("url"),
        "poskytovatel": nadace,
        "evidence": ev,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-year", type=int, default=2026)
    a = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    for p in glob.glob(os.path.join(OUT_DIR, "grant_*.json")):
        os.remove(p)
    by_id = {}
    for line in open(HARVEST, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            by_id[r.get("url")] = r

    n, skipped, seen = 0, 0, set()
    for path in sorted(glob.glob(os.path.join(IN_DIR, "grant_*.json"))):
        src = json.load(open(path, encoding="utf-8"))
        rec = by_id.get(src.get("id"))
        if not rec:
            skipped += 1
            continue
        raw_title = rec.get("title") or ""
        # ořízni suffix webu („Granty - Nadace OSF" → „Granty"), ať listing-filtr chytí
        title = re.sub(r"\s*[–|-]\s*(Nadace|Liga|LPR\.cz|Abakus)[^|–-]*$", "", raw_title).strip()
        if SKIP_TITLE.search(title) or not TAKE_TITLE.search(title):
            skipped += 1
            continue
        yr = YEAR_TITLE.search(title)
        if yr and int(yr.group(1)) < a.since_year:      # starý ročník programu
            skipped += 1
            continue
        key = re.sub(r"\W+", "", title.lower())[:60]
        if key in seen:
            skipped += 1
            continue

        body = src.get("body") or rec.get("body_text") or ""
        deadline, ev = None, {}
        m = DL.search(body)
        if m:
            deadline = _iso(m.group(1), m.group(2), m.group(3))
            if deadline:
                ev["deadline"] = _sentence(body, m.start())
        seen.add(key)
        f = build(rec, src, deadline, ev)
        json.dump(f, open(os.path.join(OUT_DIR, os.path.basename(path)), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
    print(f"wrote {n} grants -> {OUT_DIR}/ (skipped {skipped}: software/výsledky/archiv/staré ročníky/dupl.)")


if __name__ == "__main__":
    main()
