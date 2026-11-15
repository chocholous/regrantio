#!/usr/bin/env python3
"""Olomoucký kraj, olkraj.cz — krajské dotační programy, vrstva 1 BEZ MODELU.

Proč přepsáno (2026-11-15): sběrač četl jen stránku „aktuální“ roku 2026
a z ní spároval nadpis programu s prvním odkazem. Tituly pod jedním
programem (06_01_01, 06_01_02 …) tím ztratil a ukončené programy nečetl
vůbec, takže katalog měl z kraje 4 živé záznamy z 11 (audit pokrytí 14. 11.).
Web přitom nese po ročnících stránku aktuálních i ukončených programů
a každý titul má detail se štítky.

  výpis   /dotace-granty-prispevky-krajske-dotacni-programy-<rok>/aktualni-dotacni-programy
          /dotace-granty-prispevky-krajske-dotacni-programy-<rok>/ukoncene-dotacni-programy
          odkaz na detail = <rok>/<KÓD-slug>-prijem-zadosti-<od>-<do>
  detail  tabulka `.grant-detail`: Název (s kódem) · Anotace · Termín příjmu
          žádostí · Oprávnění žadatelé (PDF) · Pravidla · Vzory smluv · Žádost vzor

Bere se letošní a příští ročník (příští se vyhlašuje na podzim, sport už
v září). Ukončené tituly letošního roku nesou „loňské ročníky“ v aplikaci:
kraj je vyhlašuje každý rok v podobném termínu. Oprávnění žadatelé jsou
krátké PDF; jeho text je `eligible` a slovník extraktoru JMK z něj čte typ
žadatele (táž slova jako u Plzeňského kraje, žádná druhá kopie).

Výstup: data/h_kraj_olomoucky.json ve tvaru pro `ingest_kraj.py`.
Usage: python scripts/olomoucky_harvest.py [--out data/h_kraj_olomoucky.json] [--years 2]
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
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util  # noqa: E402  jednotná TLS politika
from plzen_kraj_harvest import areas, kinds  # noqa: E402  slovník JMK, jedna kopie

BASE = "https://www.olkraj.cz"
YEAR_PREFIX = BASE + "/dotace-granty-prispevky-krajske-dotacni-programy-{year}"
PAGES = {"aktualni-dotacni-programy": None, "ukoncene-dotacni-programy": "closed"}
SOURCE = "olkraj.cz"
KRAJ = "Olomoucký kraj"
CODE_RE = re.compile(r"^(\d{2}(?:_\d{2}){1,2})_?\s*(.+)$")
MAX_ELIGIBLE = 1500


def fetch_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; regrantio; +https://grantio.cz)"})
    return http_util.urlopen(req, timeout=40).read()


def fetch(url):
    return fetch_bytes(url).decode("utf-8", "replace")


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).replace("\xa0", " ").strip()


def iso(d, m, y):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def dates_from_slug(url):
    """Termíny zakódované v adrese: …-prijem-zadosti-[od-]<čísla> s rokem na konci.
      DD-MM-DD-MM-YYYY        od i do sdílí rok
      DD-MM-YYYY-DD-MM-YYYY   každé má vlastní rok
      DD-DD-MM-YYYY           od i do sdílí měsíc (12-26-1-2026)
    Vrací (open_from, deadline); bez termínu v adrese (None, None)."""
    m = re.search(r"prijem-(?:zadosti|dotaci)-(?:od-)?(.+)$", url)
    if not m:
        return None, None
    nums = re.findall(r"\d+", m.group(1).replace("-do-", "-"))
    if len(nums) == 5:
        return iso(nums[0], nums[1], nums[4]), iso(nums[2], nums[3], nums[4])
    if len(nums) == 6:
        return iso(nums[0], nums[1], nums[2]), iso(nums[3], nums[4], nums[5])
    if len(nums) == 4:
        return iso(nums[0], nums[2], nums[3]), iso(nums[1], nums[2], nums[3])
    return None, None


def dates_from_text(s):
    """„7.4. - 17.4.2026 do 12:00“ → (2026-04-07, 2026-04-17); rok od se bere z konce."""
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})?\s*[-–]\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s or "")
    if not m:
        return None, None
    return iso(m[1], m[2], m[3] or m[6]), iso(m[4], m[5], m[6])


ROLE = {
    "Pravidla": "pravidla_podminky",
    "Vzory smluv": "vzor_smlouvy",
    "Žádost vzor": "formular",
    "Oprávnění žadatelé": "pravidla_podminky",
    "Způsob podání žádosti": "priloha",
}


def rows(page):
    """Řádky tabulky `.grant-detail` (jen první tabulka: druhá je vyhodnocení ukončeného titulu)."""
    m = re.search(r'<div class="grant-detail">\s*<table>(.*?)</table>', page, re.S)
    out = {}
    for tr in re.findall(r"<tr\s*>(.*?)</tr>", m.group(1) if m else "", re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(cells) >= 2:
            out[clean(cells[0])] = cells[1]
    return out


def pdf_text(url):
    raw = fetch_bytes(url)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(raw)
        path = f.name
    try:
        done = subprocess.run(["pdftotext", "-enc", "UTF-8", path, "-"], capture_output=True, timeout=60)
        return done.stdout.decode("utf-8", "replace")
    finally:
        os.unlink(path)


def tidy_name(name):
    """Název bez opakovaného termínu a poznámek v závorce, bez úvodní pomlčky a bez VERZÁLEK.
    „Dotační program 10_02_Program …“ → „10_02_Program …“ (kód pak přečte CODE_RE)."""
    name = re.sub(r"^Dotační (?:program|titul)\s+(?=\d{2}_)", "", name or "")
    name = re.sub(r"\s*\((?:příjem|výsledky)[^)]*\)?\s*$", "", name, flags=re.I)
    code = CODE_RE.match(name)
    kod, rest = (code.group(1), code.group(2)) if code else (None, name)
    rest = rest.strip(" –-_").strip()
    if rest.isupper():
        rest = re.sub(r"\bolomouck", "Olomouck", rest[:1] + rest[1:].lower())
    return kod, rest or None


def parse_detail(page):
    r = rows(page)
    kod, nazev = tidy_name(clean(r.get("Název")))
    eligible = docs_of_row(r, "Oprávnění žadatelé")
    return {
        "kod": kod,
        "nazev": nazev,
        "popis": clean(r.get("Anotace")) or None,
        "termin": clean(r.get("Termín příjmu žádostí")) or None,
        "eligible_pdf": eligible[0]["url"] if eligible else None,
        "dokumenty": [d for label in ROLE for d in docs_of_row(r, label)],
    }


def docs_of_row(r, label):
    return [{"popis": clean(text)[:200] or label, "role": ROLE[label],
             "url": href if href.startswith("http") else BASE + href}
            for href, text in re.findall(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', r.get(label, ""), re.S)]


def eligible_of(url):
    """Text PDF „Okruh oprávněných žadatelů“; jiný soubor v řádku (web se splete) = nic."""
    t = re.sub(r"\s+", " ", pdf_text(url)).strip()
    if not re.search(r"Žadatelem (?:\w+ )?(?:může|mohou)|oprávněn\w* žadatel", t, re.I):
        return None
    return t[:MAX_ELIGIBLE] or None


# Výluka: co následuje, jsou ti, kdo žádat NEsmí („Žadatelem nemůže být: fyzická osoba …“).
EXCLUSION = re.compile(r"nemůže být|nemohou být|nejsou oprávněn|není oprávněn", re.I)
# Obecná právnická osoba vymezená jen předmětem činnosti („právnická osoba, jejímž předmětem
# činnosti je sport …“) = spolky, ústavy i obchodní společnosti; obec se vyjmenovává zvlášť.
GENERIC_LEGAL = re.compile(r"právnick\w+ osob\w*[,:]?\s*(?:I\.\s*)?(?:jejímž|jejíž)", re.I)


def applicant_kinds(text):
    included = EXCLUSION.split(text or "", maxsplit=1)[0]
    found = set(kinds(included))
    if GENERIC_LEGAL.search(included):
        found |= {"neziskovka", "firma"}
    return sorted(found)


def listing(year, page):
    """Odkazy na detaily titulů ročníku v pořadí stránky; chybějící stránka = prázdno."""
    prefix = YEAR_PREFIX.format(year=year)
    try:
        body = fetch(f"{prefix}/{page}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    found = re.findall(r'href="(' + re.escape(prefix) + r'/\d{2}-[^"]+)"', body)
    return list(dict.fromkeys(found))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_olomoucky.json")
    ap.add_argument("--years", type=int, default=2, help="letošní a kolik dalších ročníků celkem")
    ap.add_argument("--pause", type=float, default=0.3)
    a = ap.parse_args()

    this_year = date.today().year
    links = []  # (url, explicitní status)
    for year in range(this_year, this_year + a.years):
        for page, status in PAGES.items():
            links += [(u, status) for u in listing(year, page)]

    programs, seen, keys = [], set(), {}
    for url, status in links:
        if url in seen:
            continue
        seen.add(url)
        rec = {"url": url, "status": status, "alokace_czk": None, "max_czk": None, "eligible": None}
        try:
            d = parse_detail(fetch(url))
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ detail {url[-60:]}: {str(e)[:80]}", file=sys.stderr)
            d = {}
        slug = re.search(r"/(\d{2}(?:-\d{2}){1,2})-", url)
        rec["kod"] = d.get("kod") or (slug.group(1).replace("-", "_") if slug else None)
        rec["nazev"] = d.get("nazev")
        if not rec["nazev"]:
            print(f"  ⚠ bez názvu, vynecháno: {url[-60:]}", file=sys.stderr)
            continue
        rec["popis"] = d.get("popis")
        of, dl = dates_from_slug(url)
        if not dl:
            of, dl = dates_from_text(d.get("termin"))
        rec["open_from"], rec["deadline"] = of, dl
        # Ukončený bez termínu zůstane „closed“; s termínem stav dopočítá ingest z dat.
        if dl:
            rec["status"] = None
        if d.get("eligible_pdf"):
            try:
                rec["eligible"] = eligible_of(d["eligible_pdf"])
            except Exception as e:  # noqa: BLE001
                print(f"  ⚠ žadatelé {rec['kod']}: {str(e)[:80]}", file=sys.stderr)
        rec["dokumenty"] = d.get("dokumenty") or []
        rec["typ_zadatele"] = applicant_kinds(rec["eligible"])
        rec["oblast"] = areas(f"{rec['nazev']} {rec['popis'] or ''}")
        # Stálá identita = ročník + kód titulu: název ani termín v adrese ji nemění.
        year = re.search(r"dotacni-programy-(\d{4})/", url)
        if rec["kod"] and year:
            klic = f"olk-{year.group(1)}-{rec['kod']}"
            # Dvě kola pod jedním kódem (stipendium 1. a 2. kolo) dostanou pořadí na stránce.
            keys[klic] = keys.get(klic, 0) + 1
            rec["klic"] = klic if keys[klic] == 1 else f"{klic}-{keys[klic]}"
        programs.append(rec)
        time.sleep(a.pause)

    out = {"source": SOURCE, "kraj": KRAJ, "uroven": "kraj", "platform": "olomoucky_html", "programs": programs}
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "OLOMOUCKY_HARVEST", "kept": len(programs), "links": len(links),
                      "years": [this_year, this_year + a.years - 1], "out": a.out}, ensure_ascii=False))
    return 0 if programs else 1


if __name__ == "__main__":
    sys.exit(main())
