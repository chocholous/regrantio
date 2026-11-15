#!/usr/bin/env python3
"""Nadace rozvoje občanské společnosti (NROS), grantový kalendář — vrstva 1 BEZ MODELU (2026-11-15).

Proč: NROS spravuje grantové programy pro neziskovky (Pomozte dětem, Správný
start s Nadačním fondem Tesco, K budoucnosti) a katalog z ní měl jediný
záznam ze třídy P. Kalendář `/grantovy-harmonogram/` je jedna stránka, kde
každá výzva stojí jako blok se štítky:

  Program: Správný start · 5. kolo · 45 000 Kč · Oblast podpory: … ·
  Datum vyhlášení: … | Příjem žádostí do: … · Oprávnění žadatelé: … ·
  Stav výzvy / Stav programu: Uzavřená | Před otevřením | Příjem žádostí 18. 5. – 14. 6. 2026 …

Kola se opakují (Správný start dvakrát ročně), takže i uzavřená kola nesou
„loňské ročníky“. Stav „Před otevřením“ je ohlášená výzva bez termínu.
Typ žadatele čte slovník extraktoru JMK (jedna kopie, viz `plzen_kraj_harvest`).

Výstup: data/h_nros.json ve tvaru pro `ingest_kraj.py` s `uroven: "nadace"`.
Spuštění: python scripts/nros.py [--out data/h_nros.json]
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")

import argparse
import html
import json
import os
import re
import sys
import unicodedata
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util  # noqa: E402
from plzen_kraj_harvest import areas, kinds  # noqa: E402

URL = "https://www.nros.cz/grantovy-harmonogram/"
DATE = r"(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(20\d{2})"
LABELS = ("Oblast podpory", "Datum vyhlášení", "Příjem žádostí do", "Oprávnění žadatelé", "Stav výzvy", "Stav programu")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; regrantio; +https://grantio.cz)"})
    return http_util.urlopen(req, timeout=40).read().decode("utf-8", "replace")


def flat(page):
    """Text stránky na jednom řádku: data v kalendáři jsou rozdělená značkami („18</b>. 5. 2026“)."""
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.S)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s)


def iso(m):
    return f"{int(m[2]):04d}-{int(m[1]):02d}-{int(m[0]):02d}" if m else None


def field(block, label):
    """Text za štítkem do nejbližšího dalšího štítku."""
    others = "|".join(re.escape(x) for x in LABELS if x != label)
    m = re.search(rf"{re.escape(label)}\s*:?\s*(.*?)(?=(?:{others})\s*:|$)", block)
    return m.group(1).strip(" :") if m else None


def slug(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:50]


def czk(head):
    nums = [int(re.sub(r"\D", "", x)) for x in re.findall(r"\d[\d ]*\d", head or "")]
    return max(nums) if nums else None


def parse_block(head_html, block):
    """Jeden blok výzvy → program pro `ingest_kraj` (nebo None).
    Hlavička je v HTML značená (název programu, výzva, částka), zbytek se čte po štítcích."""
    def cls(name):
        m = re.search(rf'class="{name}"[^>]*>(.*?)</(?:h2|span)>', head_html, re.S)
        return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip() if m else ""
    program = re.sub(r"^Program\s*:\s*", "", cls("et_pb_pricing_title"))
    call, amount = cls("et_pb_best_value"), cls("et_pb_sum")
    if not program or not call:
        return None
    state = (field(block, "Stav výzvy") or field(block, "Stav programu") or "").strip()
    vyhl = re.search(DATE, field(block, "Datum vyhlášení") or "")
    until = re.search(DATE, field(block, "Příjem žádostí do") or "")
    window = re.search(r"(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*[–-]\s*" + DATE, state)
    open_from, deadline = None, iso(until.groups()) if until else None
    if window:
        open_from, deadline = iso((window.group(1), window.group(2), window.group(5))), iso(window.groups()[2:])
    status = None
    if re.search(r"před otevřením", state, re.I):
        status, open_from, deadline = "announced", None, None   # datum vyhlášení u ní bývá loňské
    elif not deadline and re.search(r"uzavřen|ukončen|v realizaci", state + block, re.I):
        status = "closed"
    if status != "announced":
        open_from = open_from or (iso(vyhl.groups()) if vyhl else None)
    year = (deadline or open_from or "")[:4]
    eligible = field(block, "Oprávnění žadatelé")
    eligible = re.sub(r"^(\w)\s+(\w)", r"\1\2", eligible or "") or None   # „S polek“ (rozdělené značkou)
    # „školská právnická osoba zřízená právnickou nebo fyzickou osobou“ fyzickou osobu žadatelem nedělá.
    who = re.sub(r"zřízen\w*\s+(?:\w+\s+){0,3}osob\w*", " ", eligible or "")
    nazev = f"{program}: {call}" + (f" ({year})" if year and year not in call else "")
    rec = {
        "nazev": nazev, "open_from": open_from, "deadline": deadline, "status": status,
        "alokace_czk": None, "max_czk": czk(amount), "popis": field(block, "Oblast podpory"),
        "eligible": eligible, "kod": None, "url": f"{URL}#{slug(program)}-{slug(call)}-{year or 'pristi'}",
        "klic": f"nros-{slug(program)}-{slug(call)}-{year or 'pristi'}",
        "typ_zadatele": kinds(who), "oblast": areas(f"{program} {call} {field(block, 'Oblast podpory') or ''}"),
    }
    if eligible and re.search(r"Středočesk", eligible):
        rec["kraj"] = "Středočeský kraj"
    return rec


def parse(page):
    start = page.find("Aktuální grantové výzvy")
    end = page.find("Kontaktujte nás", start)
    body = page[start:end if end > 0 else None]
    progs, seen = [], set()
    for chunk in re.split(r'(?=<h2 class="et_pb_pricing_title")', body)[1:]:
        rec = parse_block(chunk[:1500], flat(chunk))
        if rec and rec["klic"] not in seen:
            seen.add(rec["klic"])
            progs.append(rec)
    return progs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_nros.json")
    a = ap.parse_args()
    progs = parse(fetch(URL))
    out = {"source": "nros.cz", "kraj": None, "uroven": "nadace", "platform": "nros_kalendar", "programs": progs}
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "NROS_HARVEST", "kept": len(progs), "out": a.out}, ensure_ascii=False))
    return 0 if progs else 1


if __name__ == "__main__":
    sys.exit(main())
