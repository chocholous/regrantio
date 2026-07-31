#!/usr/bin/env python3
"""Vrstva 2 pro MŠMT (msmt.gov.cz, Marwel; harvester scripts/msmt_harvest.py).

Nahrazuje původní ručně psaný statický batch (7 záznamů z marwel seedů, git history) —
teď je extrakce DETERMINISTICKÁ a reprodukovatelná nad plným msmt_documents.jsonl:

  • FILTR NA AKTUÁLNÍ CYKLUS (zlaté pravidlo — fulltext discovery vrací všechny ročníky):
    bere se článek s grant-titulem (výzva/dotační/rozvojový program), který má ročník >=
    --since-year v titulu NEBO v próze parsovatelný deadline >= --since-year. Starší ročníky
    zůstávají lossless v harvest souboru, do datasetu nejdou (šum status=unknown).
  • deadline  = „žádost/lhůta/termín … do D. M. RRRR" (date-aware regex, česká tečková data)
  • open_from = „od D. M. RRRR do D. M. RRRR" když je rozpětí
  • amount    = „Celková alokace … Kč" jen s jednoznačným číslem; jinak null (nehalucinovat)
  • oblast    = vzdělávání (default); 8K/výzkumné infrastruktury → věda a výzkum
  • STATUS POČÍTÁ KÓD (ingest_rich → compute_status).

Join: data/msmt_in/grant_NN.json ↔ data/msmt_documents.jsonl dle id (= url).
Spuštění: python data/_msmt_extract.py [--since-year 2025]
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

IN_DIR, OUT_DIR = "data/msmt_in", "data/msmt_out"
HARVEST = "data/msmt_documents.jsonl"
CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]

GRANT_TITLE = re.compile(r"v[ýy]zv|dotačn|rozvojov[ýy] program|dotace", re.I)
TITLE_YEAR = re.compile(r"(?:rok[u]?|pro rok|na rok|na období)\s*(20\d\d)|–\s*rok\s*(20\d\d)")
# gap = [^\n] (NE [^\n.]): české zkratky „tzn./č./resp." obsahují tečku a utnuly by větu
# („Žádost musí být podána, tzn. doručena … do 31. 10. 2025" by jinak nematchovalo)
DEADLINE = re.compile(r"(?:[žŽ][áa]dost[^\n]{0,160}?|lh[uů]t[aě][^\n]{0,120}?|term[íi]n[^\n]{0,120}?)"
                      r"do\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")
AMOUNT = re.compile(r"(?:[Cc]elkov[áa] alokace|[Aa]lokace v[ýy]zvy|alokovan[áa] částka)"
                    r"[^\n.]{0,60}?([\d][\d\s  .]{4,15})\s*Kč")
RESEARCH = re.compile(r"\b8K\d|v[ýy]zkumn[ýy]ch infrastruktur|bilaterální spoluprác", re.I)

HOW = ("Žádost se podává MŠMT způsobem a ve lhůtě uvedenou v textu výzvy (typicky informační "
       "systém MŠMT — ISPROM/IS Integrace — a datová schránka); závazné podmínky jsou v textu "
       "výzvy a přílohách.")


def _iso(d, m, y):
    d, m, y = int(d), int(m), int(y)
    if 1 <= d <= 31 and 1 <= m <= 12:
        return f"{y}-{m:02d}-{d:02d}"
    return None


def _sentence(text, pos, width=200):
    start = max(0, text.rfind("\n", 0, pos), text.rfind(". ", max(0, pos - width), pos))
    return re.sub(r"\s+", " ", text[start:pos + 120]).strip(" .;\n")[:280]


def current_cycle(rec, body, since_year):
    """→ {'deadline': iso|None, 'dl_match': m|None} když článek patří do aktuálního cyklu."""
    t = rec.get("title") or ""
    if rec.get("kind") != "article" or not GRANT_TITLE.search(t):
        return None
    ty = TITLE_YEAR.search(t)
    year = int(ty.group(1) or ty.group(2)) if ty else None
    m = dl = None
    for cand in DEADLINE.finditer(body):
        # pitfalls: „žádostí … dotace NA OBDOBÍ od … do …" = doba REALIZACE, ne lhůta podání
        if re.search(r"obdob[íi]|realizac", body[cand.start():cand.end()], re.I):
            continue
        m = cand
        dl = _iso(cand.group(1), cand.group(2), cand.group(3))
        break
    if (year and year >= since_year) or (dl and dl >= f"{since_year}-01-01"):
        return {"deadline": dl, "dl_match": m}
    return None


def build(rec, src, cur):
    title = re.sub(r"\s+", " ", (rec.get("title") or "")).strip()
    body = src.get("body") or rec.get("body_text") or ""
    # POZOR (prompts/pitfalls.md): „od D.M.RRRR do D.M.RRRR" v próze MŠMT je běžně OBDOBÍ
    # REALIZACE/dotace („dotace na období od 1. 9. 2022 do 31. 8. 2025"), NE lhůta podání →
    # žádný range-parse; open_from se nehádá (None), deadline jen z DEADLINE regexu (žádost/
    # lhůta/termín … do D.M.RRRR).
    ev = {}
    open_from = None
    deadline = cur["deadline"]
    if cur["dl_match"]:
        ev["deadline"] = _sentence(body, cur["dl_match"].start())
    amount = None
    m = AMOUNT.search(body)
    if m:
        digits = re.sub(r"\D", "", m.group(1))
        if digits and 100_000 <= int(digits) <= 500_000_000_000:
            amount = int(digits)
            ev["vyse_hlavni_czk"] = _sentence(body, m.start())

    research = bool(RESEARCH.search(title + " " + body[:2000]))
    src_doc = None
    for a in rec.get("attachments") or []:
        if (a.get("ext") or "") in ("pdf", "docx", "doc"):
            src_doc = a.get("url")
            break

    return {
        "title": title,
        "focus_area": ("Dotační výzva MŠMT" + (" (mezinárodní spolupráce ve výzkumu)" if research
                                               else " v oblasti vzdělávání/mládeže") + "."),
        "oblast": (["věda a výzkum", "mezinárodní spolupráce"] if research else ["vzdělávání"]),
        "open_from": open_from, "deadline": deadline,
        "castky": ([{"typ": "alokace", "hodnota": amount}] if amount else []),
        "vyse_hlavni_czk": amount, "spoluucast": None,
        "eligible_applicants": None,      # oprávnění žadatelé jsou v textu výzvy → neparafrázovat
        "typ_zadatele": [], "cilova_skupina": [],
        "region": CR,
        "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
        "rezim_prijmu": "jednorazova_vyzva" if deadline else "neuvedeno", "delka": None,
        "how_to_apply": HOW, "required_attachments": [],
        "source_doc": src_doc or rec.get("url"),
        "poskytovatel": "Ministerstvo školství, mládeže a tělovýchovy",
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
        body = (src.get("body") or (rec or {}).get("body_text") or "")
        cur = current_cycle(rec, body, a.since_year) if rec else None
        if not cur:
            skipped += 1
            continue
        f = build(rec, src, cur)
        json.dump(f, open(os.path.join(OUT_DIR, os.path.basename(path)), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
    print(f"wrote {n} grants -> {OUT_DIR}/ (skipped {skipped}: listing/ne-grant/starý ročník)")


if __name__ == "__main__":
    main()
