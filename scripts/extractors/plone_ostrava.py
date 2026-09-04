#!/usr/bin/env python3
"""Vrstva 2 pro Plone rodinu (ostravské městské obvody; harvester scripts/plone_ostrava.py).

Harvest je lossless (137 stránek), ale VĚTŠINA není dotační program: stránky EU projektů
obvodu („Rekonstrukce hasičské zbrojnice" = obvod je PŘÍJEMCE, ne poskytovatel), smlouvy
o poskytnutí dotace (award), formuláře/tiskopisy, staré ročníky. Do datasetu jdou jen
AKTUÁLNÍ ROČNÍ PROGRAMY obvodu (poskytovatel = obvod):

  TAKE:  titul ~ (Zásady pro poskytování|Program (pro|na) poskyt|Účelové dotace v oblasti|
                  Podmínky výběrového řízení) A ročník >= --since-year (z titulu/URL);
         bez ročníku se bere jen „evergreen" program-stránka s ≥1 přílohou.
  SKIP:  smlouva|formulář|tiskopis|vyúčtování|poskytnuté|výsledky|kotlík (kraj, ne obvod)
         |EU-projektové stránky (obvod jako příjemce)|čisté rozcestníky bez příloh.

Deadline: z těla „(žádost|žádosti)… do D. M. RRRR" / „od D. M. RRRR do D. M. RRRR";
jinak None (roční rámec, reálné lhůty v PDF zásad) → status unknown. STATUS POČÍTÁ KÓD.
amount=null (alokace obvodů v HTML nebývá). Nehalucinuje se.

Join: data/plone_ostrava_in/grant_NN.json ↔ data/plone_ostrava_documents.jsonl dle id (= url).
Spuštění: python data/_plone_ostrava_extract.py [--since-year 2025]
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

IN_DIR, OUT_DIR = "data/plone_ostrava_in", "data/plone_ostrava_out"
HARVEST = "data/plone_ostrava_documents.jsonl"

TAKE_RE = re.compile(r"Z[áa]sady pro poskytov|Program (pro|na) poskyt|[ÚU][čc]elov[ée] dotace v oblasti"
                     r"|Podm[íi]nky v[ýy]b[ěe]rov[ée]ho [řr][íi]zen[íi]", re.I)
SKIP_RE = re.compile(r"smlouv|formul[áa][řr]|tiskopis|vy[úu][čc]tov[áa]n[íi]|poskytnut[ée]"
                     r"|v[ýy]sledk|kotl[íi]k|zpracov[áa]n[íi]m osobn[íi]ch", re.I)
YEAR_RE = re.compile(r"\b(20\d\d)\b")
# lhůta v próze ročního programu (české datum s tečkami — date-aware, viz SESSION_PLAYBOOK)
RANGE_RE = re.compile(r"od\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)\s*do\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")
DO_RE = re.compile(r"[žŽ][áa]dost\w*[^\n.]{0,120}?do\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")

OBVOD = {"moap": "Moravská Ostrava a Přívoz", "ovajih": "Ostrava-Jih", "poruba": "Poruba",
         "polanka": "Polanka nad Odrou", "radvanice": "Radvanice a Bartovice", "plesna": "Plesná",
         "hrabova": "Hrabová", "petrkovice": "Petřkovice", "hostalkovice": "Hošťálkovice",
         "slezska": "Slezská Ostrava", "starabela": "Stará Bělá", "marianskehory": "Mariánské Hory a Hulváky",
         "svinov": "Svinov", "vitkovice": "Vítkovice", "lhotka": "Lhotka", "martinov": "Martinov",
         "pustkovec": "Pustkovec", "trebovice": "Třebovice"}


def _iso(d, m, y):
    d, m, y = int(d), int(m), int(y)
    if 1 <= d <= 31 and 1 <= m <= 12:
        return f"{y}-{m:02d}-{d:02d}"
    return None


def _sentence(text, pos, width=200):
    start = max(0, text.rfind("\n", 0, pos), text.rfind(". ", max(0, pos - width), pos))
    return re.sub(r"\s+", " ", text[start:pos + 120]).strip(" .;\n")[:280]


def obvod_name(host):
    return OBVOD.get(host.split(".")[0], host)


def relevant(rec, since_year):
    title = rec.get("title") or ""
    if SKIP_RE.search(title):
        return False
    if not TAKE_RE.search(title):
        return False
    years = [int(y) for y in YEAR_RE.findall(title + " " + (rec.get("url") or ""))]
    if years:
        return max(years) >= since_year
    return bool(rec.get("attachments"))     # evergreen program-stránka jen s přílohami


def build(rec, src):
    host = rec.get("host") or ""
    title = (rec.get("title") or "").strip()
    body = src.get("body") or rec.get("body_text") or ""
    ob = obvod_name(host)

    open_from = deadline = None
    ev = {}
    m = RANGE_RE.search(body)
    if m:
        open_from = _iso(m.group(1), m.group(2), m.group(3))
        deadline = _iso(m.group(4), m.group(5), m.group(6))
        ev["deadline"] = _sentence(body, m.start())
    else:
        m = DO_RE.search(body)
        if m:
            deadline = _iso(m.group(1), m.group(2), m.group(3))
            ev["deadline"] = _sentence(body, m.start())

    src_doc = None
    for a in rec.get("attachments") or []:
        if (a.get("ext") or "") == "pdf":
            src_doc = a.get("url")
            break

    return {
        "title": f"{title} (městský obvod {ob})",
        "focus_area": (f"Účelové dotace z rozpočtu městského obvodu {ob} (statutární město Ostrava) — "
                       f"roční dotační program; podmínky a lhůty jsou v zásadách/programu (příloha)."),
        "oblast": ["komunitní rozvoj"],
        "open_from": open_from, "deadline": deadline,
        "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
        "eligible_applicants": None,
        "typ_zadatele": [], "cilova_skupina": [],
        "region": [{"nazev": ob, "obec": "Ostrava", "okres": "Ostrava-město",
                    "kraj": "Moravskoslezský kraj", "celostatni": False}],
        "forma_podpory": ["dotace"], "zdroj_financovani": ["vlastni_zdroje"],
        "rezim_prijmu": None, "delka": "jednoleta",
        "how_to_apply": (f"Žádost se podává městskému obvodu {ob} dle zásad/programu pro daný rok "
                         f"(formuláře a lhůty v přílohách stránky)."),
        "required_attachments": [], "source_doc": src_doc or rec.get("url"),
        "poskytovatel": f"Statutární město Ostrava — městský obvod {ob}",
        "evidence": ev,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-year", type=int, default=2025, help="ročník programu >= (aktuální cyklus)")
    a = ap.parse_args()
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
        if not rec or not relevant(rec, a.since_year):
            skipped += 1
            continue
        f = build(rec, src)
        json.dump(f, open(os.path.join(OUT_DIR, os.path.basename(path)), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
    print(f"wrote {n} grants -> {OUT_DIR}/ (skipped {skipped}: EU projekty/awards/staré ročníky/rozcestníky)")


if __name__ == "__main__":
    main()
