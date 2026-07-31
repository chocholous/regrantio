#!/usr/bin/env python3
"""Vrstva 2 pro mezinárodní fondy (harvester scripts/intl_funds.py).

Visegrad Fund a ERSTE Foundation = STÁLÉ programy s opakovanými uzávěrkami, ne jednorázové
výzvy. Proto:
  • deadline = NEJBLIŽŠÍ BUDOUCÍ datum z textu (Visegrad má pevné termíny 1. 2. / 1. 6. / 1. 10.;
    text uvádí „Opens Oct 1, 2026" apod.). Když je nalezené datum v minulosti nebo žádné,
    deadline zůstává None → status unknown (stálý program bez aktuálně vyhlášené lhůty).
  • amount = strop na projekt, jen když je v textu jednoznačně („up to €10,000") → převod
    EUR→CZK se NEDĚLÁ (kurz se mění; částka jde do extra.castka_eur, amount zůstává null).
  • ERSTE stránky nemají strojově čitelné termíny → deadline None, jde o mission-like programy.

Join: data/intl_funds_in/grant_NN.json ↔ data/intl_funds_documents.jsonl dle id (= url).
Spuštění: python data/_intl_funds_extract.py   (po build_extract_input --no-prefilter)
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import datetime
import glob
import json
import os
import re

IN_DIR, OUT_DIR = "data/intl_funds_in", "data/intl_funds_out"
HARVEST = "data/intl_funds_documents.jsonl"
TODAY = os.environ.get("REGRANTIO_TODAY") or datetime.date.today().isoformat()

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}
MONTHS.update({m[:3].lower(): i for m, i in list(MONTHS.items())})

D1 = re.compile(r"(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d\d)")          # 1 February 2027
D2 = re.compile(r"([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(20\d\d)")        # Oct 1, 2026
AMOUNT_EUR = re.compile(r"(?:up to|max(?:imum)?(?: of)?)\s*€\s?([\d][\d,\. ]{2,12})", re.I)

REGION = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW_V = ("Žádost se podává online v My Visegrad (my.visegradfund.org) do uzávěrky programu; "
         "žadatelem bývá konsorcium organizací z více zemí V4.")
HOW_E = ("ERSTE Foundation vyhlašuje výzvy a programy průběžně; přihlášky se podávají přes "
         "web nadace nebo partnerské organizace konkrétního programu.")


def _iso(d, mon, y):
    m = MONTHS.get(str(mon).lower())
    try:
        d, y = int(d), int(y)
    except ValueError:
        return None
    if not m or not (1 <= d <= 31):
        return None
    return f"{y}-{m:02d}-{d:02d}"


def next_deadline(text):
    """Nejbližší BUDOUCÍ datum v textu (stálé programy mají opakované uzávěrky)."""
    found = set()
    for m in D1.finditer(text):
        iso = _iso(m.group(1), m.group(2), m.group(3))
        if iso:
            found.add(iso)
    for m in D2.finditer(text):
        iso = _iso(m.group(2), m.group(1), m.group(3))
        if iso:
            found.add(iso)
    future = sorted(d for d in found if d >= TODAY)
    return (future[0] if future else None), found


def build(rec, src):
    body = src.get("body") or rec.get("body_text") or ""
    title = (rec.get("title") or "").strip()
    fond = rec.get("fond") or ""
    visegrad = "Visegrad" in fond

    deadline, all_dates = next_deadline(body)
    ev = {}
    if deadline:
        i = body.find(deadline[8:].lstrip("0"))    # hrubá lokalizace pro citaci
        ctx = rec.get("deadline_raw") or (body[max(0, i - 60):i + 60] if i > 0 else None)
        if ctx:
            ev["deadline"] = re.sub(r"\s+", " ", ctx).strip()[:200]

    eur = None
    m = AMOUNT_EUR.search(body)
    if m:
        digits = re.sub(r"[^\d]", "", m.group(1))
        if digits:
            eur = int(digits)
            ev["castka_eur"] = re.sub(r"\s+", " ", m.group(0))[:80]

    return {
        "title": f"{title} ({fond})" if fond and fond not in title else title,
        "focus_area": (("Grantový program Mezinárodního visegrádského fondu — přeshraniční "
                        "spolupráce zemí V4 (ČR, SK, PL, HU) a jejich partnerů.") if visegrad else
                       ("Program nadace ERSTE Foundation — podpora občanské společnosti, kultury "
                        "a sociálních inovací ve střední a jihovýchodní Evropě.")),
        "oblast": (["mezinárodní spolupráce", "komunitní rozvoj"] if visegrad
                   else ["občanská společnost", "kultura", "sociální"]),
        "open_from": None, "deadline": deadline,
        "castky": [], "vyse_hlavni_czk": None,   # EUR se NEpřevádí na CZK (kurz) → jen extra
        "castka_eur": eur,
        "spoluucast": None,
        "eligible_applicants": ("Neziskové organizace, obce, školy a další subjekty ze zemí V4 "
                                "a partnerských zemí (dle podmínek programu)." if visegrad else
                                "Organizace občanské společnosti a instituce ve střední "
                                "a jihovýchodní Evropě (dle konkrétního programu)."),
        "typ_zadatele": ["neziskovka"], "cilova_skupina": [],
        "region": REGION,
        "forma_podpory": ["dotace"], "zdroj_financovani": ["zahranicni"],
        "rezim_prijmu": "kolova" if deadline else "prubezna", "delka": None,
        "how_to_apply": HOW_V if visegrad else HOW_E,
        "required_attachments": [], "source_doc": rec.get("url"),
        "poskytovatel": fond,
        "vsechna_data_v_textu": sorted(all_dates)[:6] or None,
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
    seen_titles = set()
    for path in sorted(glob.glob(os.path.join(IN_DIR, "grant_*.json"))):
        src = json.load(open(path, encoding="utf-8"))
        rec = by_id.get(src.get("id"))
        if not rec:
            skipped += 1
            continue
        f = build(rec, src)
        key = f["title"].lower()
        if key in seen_titles:        # ERSTE calls/programs vrací tutéž stránku
            skipped += 1
            continue
        seen_titles.add(key)
        json.dump(f, open(os.path.join(OUT_DIR, os.path.basename(path)), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
    print(f"wrote {n} grants -> {OUT_DIR}/ (skipped {skipped})")


if __name__ == "__main__":
    main()
