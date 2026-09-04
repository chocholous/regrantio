#!/usr/bin/env python3
"""Vrstva 2 pro Interreg (harvester scripts/interreg.py).

POZOR NA OBSAH: dotační kategorie na Interreg webech míchají tři různé věci a jen JEDNA
z nich je grantová příležitost pro žadatele:
  TAKE  — vyhlášení výzvy na předkládání žádostí o NFP / o dotaci (skutečná výzva)
  SKIP  — „výzva na odborných hodnotiteľov" = NÁBOR hodnotitelů, ne dotace pro žadatele
  SKIP  — indikativní harmonogram, aktualizace, změna postupu = informační aktuality

Deadline: z prózy „do D. M. RRRR" ve větě s uzávěrkou/termínem; jinak None (status unknown).
STATUS POČÍTÁ KÓD. amount = null (alokace bývá jen v přiložené dokumentaci výzvy).

Join: data/interreg_in/grant_NN.json ↔ data/interreg_documents.jsonl dle id (= url).
Spuštění: python data/_interreg_extract.py   (po build_extract_input --no-prefilter)
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

IN_DIR, OUT_DIR = "data/interreg_in", "data/interreg_out"
HARVEST = "data/interreg_documents.jsonl"

# přeshraniční program → region obou stran (pro filtr „dle kraje" to není jeden kraj)
REGION = [{"nazev": "přeshraniční region ČR–SR", "obec": None, "okres": None,
           "kraj": None, "celostatni": True}]

TAKE_RE = re.compile(
    r"v[ýy]zv\w*\s+na\s+predklad|v[ýy]zv\w*\s+na\s+p[řr]edklád|vyhl[áa][sš]en\w*\s+v[ýy]z"
    r"|v[ýy]zva\s+na\s+dotaci|žiadost\w*\s+o\s+NFP|vyhlasujeme\s+nov[ée]\s+v[ýy]zv", re.I)
SKIP_RE = re.compile(
    r"hodnotite[ľl]|hodnotitel|harmonogram|aktualiz|zmena\s+postupu|změna\s+postupu"
    r"|seminá|webin|školen", re.I)
DL_RE = re.compile(
    r"(?:uz[áa]vierk\w*|uz[áa]v[ěe]rk\w*|term[íi]n\w*|do d[ňn]a|najnesk[ôo]r|nejpozd[ěe]ji)"
    r"[^\n]{0,80}?(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)", re.I)

HOW = ("Žádost se předkládá způsobem a ve lhůtě uvedené ve vyhlášení výzvy programu Interreg "
       "(monitorovací systém programu / Společný sekretariát); závazné podmínky jsou v textu "
       "výzvy a jejích přílohách.")


def _iso(d, m, y):
    d, m, y = int(d), int(m), int(y)
    return f"{y}-{m:02d}-{d:02d}" if 1 <= d <= 31 and 1 <= m <= 12 else None


def _sentence(text, pos, width=200):
    start = max(0, text.rfind("\n", 0, pos), text.rfind(". ", max(0, pos - width), pos))
    return re.sub(r"\s+", " ", text[start:pos + 130]).strip(" .;\n")[:280]


def relevant(rec):
    t = rec.get("title") or ""
    if SKIP_RE.search(t):
        return False
    return bool(TAKE_RE.search(t))


def build(rec, src):
    title = re.sub(r"\s+", " ", rec.get("title") or "").strip()
    body = src.get("body") or rec.get("body_text") or ""
    deadline, ev = None, {}
    for m in DL_RE.finditer(body):
        iso = _iso(m.group(1), m.group(2), m.group(3))
        if iso and (deadline is None or iso > deadline):
            deadline = iso
            ev["deadline"] = _sentence(body, m.start())

    src_doc = None
    for a in rec.get("attachments") or []:
        if (a.get("url") or "").lower().endswith(".pdf"):
            src_doc = a["url"]
            break

    return {
        "title": title,
        "focus_area": (f"Výzva programu {rec.get('program') or 'Interreg'} — přeshraniční "
                       f"spolupráce (EFRR)."),
        "oblast": ["mezinárodní spolupráce", "přeshraniční spolupráce"],
        # POZOR: `date` z WP je datum PUBLIKACE článku, NE začátek příjmu žádostí —
        # dosadit ho do open_from by byla fabrikace (a u oznámení o už uzavřené výzvě
        # vyrábělo deadline < open_from). Datum publikace jde do extra jako `publikovano`.
        "open_from": None, "deadline": deadline,
        "publikovano": rec.get("date") or None,
        "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
        "eligible_applicants": None,
        "typ_zadatele": [], "cilova_skupina": [],
        "region": REGION,
        "forma_podpory": ["dotace"], "zdroj_financovani": ["eu_fondy"],
        "rezim_prijmu": "kolova" if deadline else "neuvedeno", "delka": None,
        "how_to_apply": HOW, "required_attachments": [],
        "source_doc": src_doc or rec.get("url"),
        "poskytovatel": rec.get("program") or "Interreg",
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
        if not rec or not relevant(rec):
            skipped += 1
            continue
        f = build(rec, src)
        json.dump(f, open(os.path.join(OUT_DIR, os.path.basename(path)), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
    print(f"wrote {n} grants -> {OUT_DIR}/ (skipped {skipped}: nábory hodnotitelů/harmonogramy/aktuality)")


if __name__ == "__main__":
    main()
