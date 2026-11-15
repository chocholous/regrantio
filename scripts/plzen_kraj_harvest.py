#!/usr/bin/env python3
"""Plzeňský kraj, portál eDotace dotace.plzensky-kraj.cz — vrstva 1 BEZ MODELU (2026-11-14).

Proč: zdroj stál ve třídě C (čtení modelem), nikdy nebyl ověřen a katalog
z něj měl 1 živý záznam z 20, nejméně ze všech krajů (audit pokrytí 14. 11.).
Portál je táž rodina jako dotace.plzen.eu (`plzen_mesto_harvest.py`):
tabulka jqGrid se plní JSONem a detail titulu je serverem vykreslené HTML
se štítky. Nic se neobchází, je to týž požadavek, jaký posílá prohlížeč.

  výpis   GET /verejnost/dotacnitituly?_name=DotacniTituly&rows=…
          {records, rows:[{id, cell:{buttons, nazevodboru, nazevprogramu,
           nazevtitulu, roktitulu, zadostiod, zadostido}}]}
  detail  GET /verejnost/dotacnititul/<id>/
          Účel podpory · Důvod podpory · Potenciální žadatelé · Termíny
          (Zveřejnění, Žádosti od, Žádosti do) · Financování (celkový
          objem, maximální požadovaná částka) · Přílohy (odkazy ke stažení)

Bere se letošní a loňský ročník: loňský nese „loňské ročníky“ v aplikaci.
Typ žadatele a oblast se čtou slovníkem extraktoru JMK (táž slova, žádná
druhá kopie); co věty neříkají, zůstane prázdné.

Výstup: data/h_kraj_plzen.json ve tvaru pro `ingest_kraj.py`.
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")

import argparse
import html
import importlib.util
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util  # noqa: E402  jednotná TLS politika

BASE = "https://dotace.plzensky-kraj.cz"
# Server vrací nejvýš 25 řádků na stránku bez ohledu na `rows`: stránkuje se.
GRID = BASE + "/verejnost/dotacnitituly?_name=DotacniTituly&_search=false&rows=25&page={page}&sidx=zadostiod&sord=desc"
MAX_PAGES = 60  # pojistka proti zacyklení, ne strop pokrytí (996 titulů = 40 stránek)
SOURCE = "dotace.plzensky-kraj.cz"
KRAJ = "Plzeňský kraj"


def _jmk_dictionary():
    """Slovník typu žadatele a oblasti z extraktoru JMK (načtený podle cesty: jméno modulu koliduje se sběračem)."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extractors", "jmk_edotace.py")
    spec = importlib.util.spec_from_file_location("jmk_edotace_extractor", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.TYP, mod.OBLAST, mod.KDOKOLI


TYP, OBLAST, KDOKOLI = _jmk_dictionary()


def fetch(url, as_json=False):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; regrantio; +https://grantio.cz)"}
    if as_json:
        headers["X-Requested-With"] = "XMLHttpRequest"
        headers["Accept"] = "application/json"
    req = urllib.request.Request(url, headers=headers)
    raw = http_util.urlopen(req, timeout=40).read().decode("utf-8", "replace")
    return json.loads(raw) if as_json else raw


def text_of(page):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t)


def section(text, label, nxt):
    """Text mezi štítkem a nejbližším z dalších štítků."""
    m = re.search(rf"\n\s*{label}\s*\n(.*?)(?=\n\s*(?:{'|'.join(nxt)})\s*\n|$)", text, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def czk(s):
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", s.split("Kč")[0])
    return int(digits) if digits else None


def iso(s):
    s = (s or "").strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m[1]}-{m[2]}-{m[3]}"
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


ROLE = [
    (re.compile(r"pravidl", re.I), "pravidla_podminky"),
    (re.compile(r"vyhlášení|popis dotačního titulu", re.I), "vyzva"),
    (re.compile(r"vzor\w* (žádosti|smlouv)|formulář", re.I), "formular"),
    (re.compile(r"smlouv", re.I), "vzor_smlouvy"),
]


def documents(page, title_id):
    """Přílohy: odkaz ke stažení, jméno souboru, druh a popis z tabulky."""
    out = []
    for row in re.findall(r"<tr>(.*?)</tr>", page, re.S):
        a = re.search(rf'href="(/verejnost/dotacnititul/{title_id}/soubor/[^"]+)"', row)
        if not a:
            continue
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        popis = (cells[2] if len(cells) > 2 and cells[2] else cells[1] if len(cells) > 1 else "") or "Příloha"
        druh = cells[1] if len(cells) > 1 else ""
        role = next((r for rx, r in ROLE if rx.search(popis + " " + druh)), "priloha")
        out.append({"popis": popis[:200], "role": role, "url": BASE + a.group(1)})
    return out[:20]


def kinds(text):
    if not text:
        return []
    found = [t for rx, t in TYP if re.search(rx, text, re.I)]
    if KDOKOLI.search(text):
        found += ["fyzicka_osoba", "neziskovka", "firma"]
    return sorted(set(found))


def areas(text):
    return sorted({a for rx, a in OBLAST if re.search(rx, text or "", re.I)})


def parse_detail(page, title_id):
    t = text_of(page)
    labels = ["Účel podpory", "Důvod podpory", "Potenciální žadatelé", "Termíny", "Financování", "Administrátoři", "Přílohy"]
    ucel = section(t, "Účel podpory", labels[1:])
    duvod = section(t, "Důvod podpory", labels[2:])
    zadatele = section(t, "Potenciální žadatelé", labels[3:])
    objem = re.search(r"Předpokládaný celkový objem[^\n]*\n\s*([\d\s\xa0.,]+Kč)", t)
    maximum = re.search(r"Maximální požadovaná částka[^\n]*\n\s*([\d\s\xa0.,]+Kč)", t)
    zverejneni = re.search(r"Zveřejnění\s*\n\s*([\d.]+)", t)
    return {
        "popis": " ".join(x for x in (ucel, duvod) if x) or None,
        "eligible": zadatele,
        "alokace_czk": czk(objem.group(1)) if objem else None,
        "max_czk": czk(maximum.group(1)) if maximum else None,
        "zverejneno": iso(zverejneni.group(1)) if zverejneni else None,
        "dokumenty": documents(page, title_id),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_plzen.json")
    ap.add_argument("--years", type=int, default=2, help="kolik posledních ročníků (letošní = 1)")
    ap.add_argument("--pause", type=float, default=0.3, help="přestávka mezi detaily (s)")
    a = ap.parse_args()

    first_year = date.today().year - a.years + 1
    rows, records = [], 0
    for page in range(1, MAX_PAGES + 1):
        grid = fetch(GRID.format(page=page), as_json=True)
        part = grid.get("rows", [])
        records = int(grid.get("records") or records)
        rows += part
        years = [int(r.get("cell", {}).get("roktitulu") or 0) for r in part]
        # Seřazeno od nejnovějšího příjmu: stránka bez letošních ani loňských končí výpis.
        if not part or page >= int(grid.get("total") or 0) or (years and max(years) < first_year):
            break
        time.sleep(a.pause)

    programs, seen = [], set()
    for r in rows:
        c = r.get("cell", {})
        try:
            year = int(c.get("roktitulu") or 0)
        except ValueError:
            year = 0
        if year and year < first_year:
            continue
        m = re.search(r'href="/verejnost/dotacnititul/(\d+)/"', c.get("buttons") or "")
        if not m or m.group(1) in seen:
            continue
        title_id = m.group(1)
        seen.add(title_id)
        program = (c.get("nazevprogramu") or "").strip()
        titul = (c.get("nazevtitulu") or "").strip()
        nazev = titul if not program or titul == program or program in titul else f"{program}: {titul}"
        url = f"{BASE}/verejnost/dotacnititul/{title_id}/"
        rec = {
            "nazev": nazev,
            "open_from": iso(c.get("zadostiod")),
            "deadline": iso(c.get("zadostido")),
            "status": None,
            "kod": title_id,
            "url": url,
            "_odbor": (c.get("nazevodboru") or "").strip() or None,
        }
        try:
            d = parse_detail(fetch(url), title_id)
            rec.update({k: v for k, v in d.items() if v not in (None, [], "")})
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ detail {title_id}: {str(e)[:80]}", file=sys.stderr)
        rec["typ_zadatele"] = kinds(rec.get("eligible"))
        rec["oblast"] = areas(" ".join(str(rec.get(k) or "") for k in ("nazev", "popis", "_odbor")))
        programs.append(rec)
        time.sleep(a.pause)

    out = {"source": SOURCE, "kraj": KRAJ, "uroven": "kraj", "platform": "plzen_kraj_edotace", "programs": programs}
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "PLZEN_KRAJ_HARVEST", "kept": len(programs), "records_reported": records,
                      "years_from": first_year, "out": a.out}, ensure_ascii=False))
    return 0 if programs else 1


if __name__ == "__main__":
    sys.exit(main())
