#!/usr/bin/env python3
"""Vrstva 2 pro CzechAid / Českou rozvojovou agenturu (czechaid.gov.cz; harvester
scripts/czechaid_harvest.py).

DETERMINISTICKY z prózy detailu (web nemá žádná strukturovaná data od/do):
  • deadline   = „Lhůta pro podání žádosti … do D. M. RRRR včetně" / „stanovena do …" /
                 „se mění na: D.M.RRRR včetně" (při VÍCE výskytech vyhrává NEJPOZDĚJŠÍ
                 datum — prodloužení lhůty se publikuje jako další odstavec nad původní)
  • open_from  = „Česká rozvojová agentura vyhlašuje dne D. M. RRRR dotační výzvu"
  • ZRUŠENO/uzavřená výzva pro předem určené žadatele: slug/status_guess z harvestu jde
    do extra (status POČÍTÁ KÓD z dat; „cancelled" tu reprezentujeme deadline=None +
    zruseno=true v extra, ať se nefabrikuje časový status)
  • amount     = „Maximální výše dotace … Kč" / „alokace … Kč" jen když je v textu
    JEDNOZNAČNÉ číslo s Kč; jinak null
  • evidence   = doslovné věty (grounding)

Join: data/czechaid_in/grant_NN.json ↔ data/czechaid_documents.jsonl dle id (= url).
Skip: kind=listing (rozcestník /dotace) → out soubor se NEzapíše.

Spuštění (z kořene repa, po build_extract_input --no-prefilter):
  python data/_czechaid_extract.py
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

IN_DIR, OUT_DIR = "data/czechaid_in", "data/czechaid_out"
HARVEST = "data/czechaid_documents.jsonl"

CR_ZAHR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
D = r"(\d{1,2})\.\s*(\d{1,2})\s*\.\s*(20\d\d)|(\d{1,2})\.\s*(\d{1,2})\.(20\d\d)"

# lhůta: víc formulací, včetně „se mění na:" (prodloužení) a mezer uvnitř data („13. 2 .2026")
DEADLINE_RES = [
    # gap = [^\n] (NE [^.\n]): české zkratky s tečkou by utnuly větu (viz _msmt_extract)
    re.compile(r"[Ll]h[uů]ta pro pod[áa]n[íi] ž[áa]dost[íi][^\n]{0,120}?"
               r"(?:do|na:?)\s*(\d{1,2})\.\s*(\d{1,2})\s*\.\s*(20\d\d)"),
    re.compile(r"[Ll]h[uů]ta pro pod[áa]n[íi] ž[áa]dost[íi] o poskytnut[íi] dotace\s*"
               r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)\s*včetně"),
]
OPEN_RE = re.compile(r"vyhlašuje dne\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")
AMOUNT_RE = re.compile(r"(?:[Mm]axim[áa]ln[íi] výše dotace|[Cc]elkov[áa] alokace|[Aa]lokace výzvy)"
                       r"[^.\n]{0,60}?([\d][\d\s  .]{2,15})\s*(?:Kč|CZK)")

HOW = ("Žádost o dotaci se podává České rozvojové agentuře ve lhůtě uvedené ve znění výzvy "
       "(datovou schránkou, doporučeně poštou nebo osobně); závazné podmínky, formulář žádosti "
       "a přílohy jsou v přiloženém znění dotační výzvy.")


def _iso(d, m, y):
    d, m, y = int(d), int(m), int(y)
    if 1 <= d <= 31 and 1 <= m <= 12:
        return f"{y}-{m:02d}-{d:02d}"
    return None


def _sentence(text, pos, width=200):
    start = max(0, text.rfind("\n", 0, pos), text.rfind(". ", max(0, pos - width), pos))
    seg = text[start:pos + 120]
    return re.sub(r"\s+", " ", seg).strip(" .;\n")[:280]


def extract_deadline(text):
    """Všechny výskyty lhůty → (nejpozdější ISO, citace). Prodloužení lhůty = nový odstavec
    s pozdějším datem NAD původním → max() je správně (ověřeno na výzvách 2025/2026)."""
    best = None
    for rx in DEADLINE_RES:
        for m in rx.finditer(text):
            iso = _iso(m.group(1), m.group(2), m.group(3))
            if iso and (best is None or iso > best[0]):
                best = (iso, _sentence(text, m.start()))
    return best or (None, None)


def extract(rec, src):
    body = src.get("body") or rec.get("body_text") or ""
    title = re.sub(r"^\s*(ZRUŠENO|ÚPRAVA ZNĚNÍ)\s*:\s*", "", (rec.get("title") or "").strip())
    zruseno = rec.get("status_guess") == "cancelled" or "ZRUŠENO" in (rec.get("title") or "")

    deadline, dl_q = extract_deadline(body)
    open_from, of_q = None, None
    m = OPEN_RE.search(body)
    if m:
        open_from = _iso(m.group(1), m.group(2), m.group(3))
        of_q = _sentence(body, m.start())
    amount, am_q = None, None
    m = AMOUNT_RE.search(body)
    if m:
        digits = re.sub(r"\D", "", m.group(1))
        if digits and 10_000 <= int(digits) <= 500_000_000_000:
            amount = int(digits)
            am_q = _sentence(body, m.start())

    if zruseno:
        deadline = None      # zrušená výzva: nefabrikovat časový status z původní lhůty

    ev = {}
    if dl_q and deadline:
        ev["deadline"] = dl_q
    if of_q and open_from:
        ev["open_from"] = of_q
    if am_q:
        ev["vyse_hlavni_czk"] = am_q

    src_doc = None
    for a in rec.get("attachments") or []:
        lab = (a.get("label") or a.get("name") or "").lower()
        if "výzv" in lab or "vyzv" in lab or (a.get("ext") == "zip"):
            src_doc = a.get("url")
            break
    if not src_doc:
        for a in rec.get("attachments") or []:
            if (a.get("ext") or "") == "pdf":
                src_doc = a.get("url")
                break

    return {
        "title": title,
        "focus_area": ("Dotační výzva České rozvojové agentury (CzechAid) v rámci bilaterální "
                       "zahraniční rozvojové spolupráce ČR."),
        "oblast": ["mezinárodní spolupráce"],
        "open_from": open_from, "deadline": deadline,
        "castky": ([{"typ": "alokace", "hodnota": amount}] if amount else []),
        "vyse_hlavni_czk": amount, "spoluucast": None,
        "eligible_applicants": ("Oprávnění žadatelé dle znění konkrétní výzvy (typicky spolky, "
                                "o.p.s., ústavy, právnické osoby ve smyslu zákona o zahraniční "
                                "rozvojové spolupráci)."),
        "typ_zadatele": ["neziskovka"], "cilova_skupina": [],
        "region": CR_ZAHR,
        "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
        "rezim_prijmu": "jednorazova_vyzva" if deadline else "neuvedeno", "delka": None,
        "how_to_apply": HOW, "required_attachments": [],
        "source_doc": src_doc or rec.get("url"),
        "poskytovatel": "Česká rozvojová agentura (CzechAid)",
        "zruseno": zruseno or None,
        "status_guess_slug": rec.get("status_guess"),
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
        f = extract(rec, src)
        json.dump(f, open(os.path.join(OUT_DIR, os.path.basename(path)), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
    print(f"wrote {n} grants -> {OUT_DIR}/ (skipped {skipped}: listing/nespárováno)")


if __name__ == "__main__":
    main()
