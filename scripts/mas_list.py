#!/usr/bin/env python3
"""Seznam místních akčních skupin: web a obce, které pokrývají (2026-11-15).

Proč: MAS jsou podle mapy mezer (`docs/coverage.md`) největší díra katalogu.
Rozdělují peníze IROP, OPZ+, OP TAK a SZP (LEADER) malým obcím, spolkům
a zemědělcům, ale souhrnný výpis jejich výzev neexistuje: dotaceeu.cz (MS2021+)
nese jen nadřazené výzvy řídicích orgánů, SZIF výzvy MAS veřejně nevypisuje.
Každá MAS je vyhlašuje na svém webu. Výzva MAS navíc platí jen na jejím
území, a to je výčet obcí, ne kraj ani okres.

Dva veřejné zdroje, spojené podle jména:
  • Národní síť MAS ČR, „Členové NS MAS“: jméno a adresa webu (~189).
  • ČSÚ, „Data pro MAS“: každá obec (kód, název, okres) a její MAS v období
    2021–2027 (list posledního roku). Bez webu.

Výstup `data/mas_seeds.json` (sledovaný, vstup sběrače `mas.py`):
  [{"mas": "MAS Česká Kanada o.p.s.", "web": "https://www.masck.cz/",
    "cislo": 12, "kraje": ["Jihočeský kraj"], "obce": [{"kod": 546712, "nazev": "…"}]}]
MAS z ČSÚ bez webu v seznamu NS MAS zůstanou s "web": null (nejsou členy);
web z NS MAS bez páru v ČSÚ se vypíše jako varování.

Spuštění:  python scripts/mas_list.py [--out data/mas_seeds.json]
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")

import argparse
import difflib
import html
import io
import json
import os
import re
import sys
import unicodedata
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util  # noqa: E402

NSMAS = "https://www.nsmascr.cz/o-nas/clenove-ns-mas/"
CSU_PAGE = "https://csu.gov.cz/data_pro_mistni_akcni_skupiny_mas"
# Kraj podle kódu okresu (NUTS 3 = první čtyři znaky CZ0xx).
KRAJ = {
    "CZ010": "Hlavní město Praha", "CZ020": "Středočeský kraj", "CZ031": "Jihočeský kraj",
    "CZ032": "Plzeňský kraj", "CZ041": "Karlovarský kraj", "CZ042": "Ústecký kraj",
    "CZ051": "Liberecký kraj", "CZ052": "Královéhradecký kraj", "CZ053": "Pardubický kraj",
    "CZ063": "Kraj Vysočina", "CZ064": "Jihomoravský kraj", "CZ071": "Olomoucký kraj",
    "CZ072": "Zlínský kraj", "CZ080": "Moravskoslezský kraj",
}
SKIP_LINK = re.compile(r"nsmascr|facebook|igalileo|google|twitter|youtube|instagram|linkedin|mailto:")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; regrantio; +https://grantio.cz)"})
    return http_util.urlopen(req, timeout=120).read()


def norm(name):
    """Jméno MAS bez právní formy, slova „MAS“ a diakritiky: „MAS Česká Kanada o.p.s.“ → „ceska kanada“."""
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(z\.?\s?s\.?|o\.?\s?p\.?\s?s\.?|z\.?\s?u\.?|s\.?\s?r\.?\s?o\.?|spolek|obecne prospesna spolecnost)\b", " ", s)
    s = re.sub(r"\bmistni akcni skupin\w*\b|\bmas\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def webs():
    page = fetch(NSMAS).decode("utf-8", "replace")
    out = {}
    for href, text in re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', page, re.S):
        if SKIP_LINK.search(href):
            continue
        name = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text))).strip()
        if name and name not in out:
            out[name] = href.strip()
    return out


def csu_rows():
    import openpyxl
    page = fetch(CSU_PAGE).decode("utf-8", "replace")
    m = re.search(r'href="([^"]*data_podle_obci__roky_2021_\d{4}__s_ciselniky_mas\.xlsx[^"]*)"', page)
    if not m:
        sys.exit("✖ ČSÚ: soubor „data podle obcí … s číselníky MAS“ na stránce nenalezen")
    url = "https://csu.gov.cz" + html.unescape(m.group(1))
    wb = openpyxl.load_workbook(io.BytesIO(fetch(url)), read_only=True)
    year = max(ws.title for ws in wb.worksheets if re.fullmatch(r"20\d{2}", ws.title))
    rows = wb[year].iter_rows(values_only=True)
    head = [str(c or "").replace("\n", " ") for c in next(rows)]
    col = {k: next(i for i, h in enumerate(head) if h.startswith(k)) for k in
           ("Obec kód", "Název obce", "MAS název", "MAS  poř. číslo", "Okres kód")}
    for r in rows:
        if r[col["Obec kód"]] and r[col["MAS název"]]:
            yield {"kod": int(r[col["Obec kód"]]), "nazev": r[col["Název obce"]], "mas": r[col["MAS název"]].strip(),
                   "cislo": r[col["MAS  poř. číslo"]], "kraj": KRAJ.get(str(r[col["Okres kód"]])[:5])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/mas_seeds.json")
    a = ap.parse_args()

    groups = {}
    for r in csu_rows():
        g = groups.setdefault(r["mas"], {"mas": r["mas"], "web": None, "cislo": r["cislo"], "kraje": set(), "obce": []})
        g["obce"].append({"kod": r["kod"], "nazev": r["nazev"]})
        if r["kraj"]:
            g["kraje"].add(r["kraj"])

    by_norm = {norm(k): k for k in groups}
    unmatched = []
    for name, url in webs().items():
        n = norm(name)
        close = difflib.get_close_matches(n, by_norm, n=1, cutoff=0.85)
        key = by_norm.get(n) or (by_norm[close[0]] if close else None)
        if key and not groups[key]["web"]:
            groups[key]["web"] = url
        else:
            unmatched.append((name, url))

    out = sorted(({**g, "kraje": sorted(g["kraje"])} for g in groups.values()), key=lambda g: g["mas"])
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    for name, url in unmatched:
        print(f"  ⚠ web bez MAS v ČSÚ: {name} ({url})", file=sys.stderr)
    print(json.dumps({"MARKER": "MAS_LIST", "mas": len(out), "with_web": sum(1 for g in out if g["web"]),
                      "obce": sum(len(g["obce"]) for g in out), "unmatched_webs": len(unmatched), "out": a.out},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
