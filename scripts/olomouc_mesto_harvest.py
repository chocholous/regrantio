#!/usr/bin/env python3
"""Statutární město Olomouc — harvester dotačních programů (server-rendered HTML).

ZDROJ: https://www.olomouc.eu/urad-online/dotace — veřejný katalog vyhlášených
dotačních programů města. (dotace.olomouc.eu je angular ŽÁDOSTNÍ portál, ne katalog —
veřejný listing programů žije na olomouc.eu jako server-rendered HTML, žádný XHR/login.)

Každý program je odkaz na PDF vyhlášení v repozitáři článku 17712. Klíčový trik:
NÁZEV SOUBORU kóduje termíny i kód programu — `YYYYMMDD-YYYYMMDD-{kod}.pdf`
= open_from-deadline-zkratka. Název programu je text odkazu (<a>). Filtrujeme jen
aktuální ročník (rok >= --year, default 2026). Plus "Individuální dotace" (průběžně, datumy null).

Strukturovaný parse, žádný LLM. Status dopočítá ingest z termínů.
Lossless: ukládá nazev + datumy + kod + URL PDF + krátký kontext. Ukládá průběžně.

Usage: python3 scripts/olomouc_mesto_harvest.py [--out data/h_mesto_olomouc.json] [--year 2026]
"""
import argparse, html, json, re, sys, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)

BASE = "https://www.olomouc.eu"
LISTING = "/urad-online/dotace"
# odkazy na PDF vyhlášení: /administrace/repository/gallery/articles/17_/17712/YYYYMMDD-YYYYMMDD-kod.pdf
PDF_RE = re.compile(
    r'<a\s+[^>]*href="(?P<href>[^"]*/17712/(?P<f>(?P<o>\d{8})-(?P<d>\d{8})-[^"]+\.pdf))"[^>]*>(?P<txt>.*?)</a>',
    re.S | re.I,
)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return http_util.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def _iso8(s):
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}" if s and len(s) == 8 else None


def _txt(raw):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))).strip()


def _kod(fname):
    # YYYYMMDD-YYYYMMDD-{kod}.pdf  →  {kod} (bez .cs apod.)
    m = re.match(r"\d{8}-\d{8}-(.+?)(?:\.cs)?\.pdf$", fname, re.I)
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_olomouc.json")
    ap.add_argument("--year", type=int, default=2026, help="ponech jen programy s open_from rokem >= year")
    a = ap.parse_args()

    out = {"source": "olomouc.eu", "kraj": "Olomoucký kraj", "obec": "Olomouc",
           "uroven": "obec", "platform": "olomouc_mesto", "programs": []}

    def flush():
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    html_listing = fetch(BASE + LISTING)
    seen = set()
    skipped_old = 0
    for m in PDF_RE.finditer(html_listing):
        of, dl = _iso8(m["o"]), _iso8(m["d"])
        if of and int(of[:4]) < a.year:
            skipped_old += 1
            continue
        nazev = _txt(m["txt"])
        href = m["href"]
        url = href if href.startswith("http") else BASE + href
        if url in seen:
            continue
        seen.add(url)
        if not nazev:
            continue
        out["programs"].append({
            "nazev": nazev, "open_from": of, "deadline": dl, "status": None,
            "alokace_czk": None, "max_czk": None, "popis": None, "eligible": None,
            "kod": _kod(m["f"]), "url": url,
        })
        flush()  # průběžné ukládání

    # Individuální dotace — průběžná možnost (bez termínů), pokud ji stránka zmiňuje
    if "Individuální dotace" in html_listing:
        url = BASE + LISTING + "#individualni"
        if url not in seen:
            out["programs"].append({
                "nazev": "Individuální dotace", "open_from": None, "deadline": None,
                "status": None, "alokace_czk": None, "max_czk": None,
                "popis": "Dotace na potřebu konkrétního subjektu, podávaná průběžně po celý rok.",
                "eligible": None, "kod": "individualni", "url": url,
            })
            flush()

    flush()
    print(json.dumps({"MARKER": "OLOMOUC_MESTO_HARVEST", "kept": len(out["programs"]),
                      "skipped_old": skipped_old, "out": a.out,
                      "source_url": BASE + LISTING}, ensure_ascii=False))


if __name__ == "__main__":
    main()
