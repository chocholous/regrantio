#!/usr/bin/env python3
"""Vrstva 2 pro HZS ČR (hzscr.gov.cz; harvester scripts/hzs_harvest.py).

HZS publikuje dotace jako VÍCELETÉ rámcové články (záložky per rok, slité do jednoho
záznamu) + jednotlivé výzvy. DETERMINISTICKY:

  TAKE:  články s dotačním titulem (účelová/neinvestiční/investiční dotace, výzva k podání),
         které jsou BUĎ standing víceleté programy (mají ročníkové záložky, tabs >= 2 —
         Účelová (ne)investiční dotace obcím, dotace NNO…), NEBO mají aktuální deadline
         (>= --since-year) v próze.
  SKIP:  awards („Rozhodnutí o poskytnutí podpory", „Vybrány obce…"), info stránky
         („Možnosti financování…"), EU/IROP stránky (kryje irop.gov.cz zdroj), hub „Dotace",
         a JEDNORÁZOVÉ historické výzvy bez aktuální lhůty (povodně 2022, Zázemí UA…) —
         přidaly by jen status=unknown šum.

  deadline = NEJPOZDĚJŠÍ datum roku >= --since-year ve větě s žádost/lhůta/termín
             (víceletý článek obsahuje lhůty všech ročníků → bez year-guardu by se
             vzala stará; když aktuální lhůta není, zůstává None → status unknown,
             roční rámec — NEfabrikovat).
  amount   = null (alokace jsou v PDF výzvách per rok).
  STATUS POČÍTÁ KÓD (ingest_rich → compute_status).

Join: data/hzs_in/grant_NN.json ↔ data/hzs_documents.jsonl dle id (= url).
Spuštění: python data/_hzs_extract.py [--since-year 2025]
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

IN_DIR, OUT_DIR = "data/hzs_in", "data/hzs_out"
HARVEST = "data/hzs_documents.jsonl"
CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]

TAKE_RE = re.compile(r"dotace|v[ýy]zva k pod[áa]n[íi]", re.I)
SKIP_RE = re.compile(r"rozhodnut[íi] o poskytnut|vybr[áa]ny obce|mo[žz]nosti financov[áa]n[íi]"
                     r"|\bIROP\b|^Dotace$", re.I)
# gap = [^\n] (NE [^\n.]): české zkratky „tzn./č./resp." obsahují tečku (viz _msmt_extract)
DL_RE = re.compile(r"(?:[žŽ][áa]dost[^\n]{0,160}?|lh[uů]t[aě][^\n]{0,120}?|term[íi]n[^\n]{0,120}?)"
                   r"do\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")

HOW = ("Žádost o dotaci se podává HZS ČR (resp. generálnímu ředitelství HZS) způsobem a ve lhůtě "
       "dle výzvy pro daný rok; podmínky a formuláře jsou v přílohách článku (výzva, zásady).")

NNO = re.compile(r"nest[áa]tn[íi]m? neziskov", re.I)
OBCE = re.compile(r"obc[íi]m|obce|jednotk[aá]m? sboru dobrovoln", re.I)


def _iso(d, m, y):
    d, m, y = int(d), int(m), int(y)
    if 1 <= d <= 31 and 1 <= m <= 12:
        return f"{y}-{m:02d}-{d:02d}"
    return None


def _sentence(text, pos, width=200):
    start = max(0, text.rfind("\n", 0, pos), text.rfind(". ", max(0, pos - width), pos))
    return re.sub(r"\s+", " ", text[start:pos + 120]).strip(" .;\n")[:280]


def build(rec, src, since_year):
    title = re.sub(r"\s+", " ", (rec.get("title") or "")).strip()
    body = src.get("body") or rec.get("body_text") or ""
    deadline, ev = None, {}
    for m in DL_RE.finditer(body):
        iso = _iso(m.group(1), m.group(2), m.group(3))
        if iso and int(iso[:4]) >= since_year and (deadline is None or iso > deadline):
            deadline = iso
            ev["deadline"] = _sentence(body, m.start())

    eligible = None
    typ_z = []
    if NNO.search(title):
        eligible = "Nestátní neziskové organizace působící na úseku požární ochrany, IZS a ochrany obyvatelstva."
        typ_z = ["neziskovka"]
    elif OBCE.search(title):
        eligible = "Obce (typicky zřizovatelé jednotek sboru dobrovolných hasičů obcí)."
        typ_z = ["obec_verejny_subjekt"]

    src_doc = None
    for a in rec.get("attachments") or []:
        if (a.get("ext") or "") == "pdf":
            src_doc = a.get("url")
            break

    return {
        "title": title,
        "focus_area": ("Dotace HZS ČR (Ministerstvo vnitra — generální ředitelství Hasičského "
                       "záchranného sboru) na úseku požární ochrany, IZS a ochrany obyvatelstva."),
        "oblast": ["bezpečnost"],
        "open_from": None, "deadline": deadline,
        "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
        "eligible_applicants": eligible,
        "typ_zadatele": typ_z, "cilova_skupina": ["dobrovolní hasiči"] if OBCE.search(title) else [],
        "region": CR,
        "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
        "rezim_prijmu": "kolova" if deadline else "neuvedeno", "delka": "jednoleta",
        "how_to_apply": HOW, "required_attachments": [],
        "source_doc": src_doc or rec.get("url"),
        "poskytovatel": "HZS ČR (MV — generální ředitelství HZS)",
        "evidence": ev,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-year", type=int, default=2025)
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
        t = (rec or {}).get("title") or ""
        if not rec or SKIP_RE.search(t) or not TAKE_RE.search(t):
            skipped += 1
            continue
        f = build(rec, src, a.since_year)
        standing = len(rec.get("tabs") or []) >= 2      # víceletý rámcový program (ročníkové záložky)
        if not standing and not f["deadline"]:
            skipped += 1                                 # jednorázová historická výzva bez aktuální lhůty
            continue
        json.dump(f, open(os.path.join(OUT_DIR, os.path.basename(path)), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
    print(f"wrote {n} grants -> {OUT_DIR}/ (skipped {skipped}: awards/info/hub/IROP)")


if __name__ == "__main__":
    main()
