#!/usr/bin/env python3
"""Fond Vysočiny harvester — dotační programy Kraje Vysočina (server-rendered HTML).

fondvysociny.cz/dotace/default/aktivni?kat=999 = listing aktivních programů s odkazy
/dotace/zadosti/{KÓD}. Detail je čistě štítkovaný (Program/ID/Popis/Alokace/Termín pro podání
žádosti DD.MM.YYYY-DD.MM.YYYY/Typ žadatele) → strukturovaný parse, žádný LLM. Filtruje TEST záznamy.

Lossless: ukládá parsed pole + plný text detailu. Status dopočítá ingest z termínů.

Usage: python3 scripts/fondvysociny_harvest.py --out data/h_fondvysociny.json [--listing aktivni]
"""
import argparse, json, re, sys, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)

BASE = "https://www.fondvysociny.cz"
SKIP = re.compile(r"\bTEST\b|NESLOUŽÍ K PODÁVÁNÍ|TEST\d|FV2024112233", re.I)
LABELS = {
    "nazev": r"Program:\s*(.+?)\s*(?:ID programu:|$)",
    "id": r"ID programu:\s*([A-Z]{2}\d+)",
    "popis": r"Popis:\s*(.+?)\s*(?:Alokace:|Kontaktní osoby:|Termín|Typ žadatele:)",
    "alokace": r"Alokace:\s*([\d  \xa0]+)\s*Kč",
    "termin": r"Termín pro podání žádosti:\s*([\d.]+)[\s\xa0]+[\d:]+\s*-\s*([\d.]+)",
    "typ_zadatele": r"Typ žadatele:\s*(.+?)\s*(?:Fáze zpracování:|Materiály:|$)",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return http_util.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " ")
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", h)).strip()


def parse_detail(text, code):
    seg = text[text.find("Program:"):] if "Program:" in text else text
    rec = {"id": code}
    for k, pat in LABELS.items():
        m = re.search(pat, seg, re.S)
        if m:
            if k == "termin":
                rec["open_from"] = _iso(m.group(1)); rec["deadline"] = _iso(m.group(2))
            else:
                rec[k] = re.sub(r"\s+", " ", m.group(1)).strip()
    return rec


def _iso(s):
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s or "")
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_fondvysociny.json")
    ap.add_argument("--listing", default="aktivni")
    a = ap.parse_args()

    lst = fetch(f"{BASE}/dotace/default/{a.listing}?kat=999")
    codes = []
    for m in re.finditer(r'href="(/dotace/zadosti/([A-Z]{2}\d+)[^"]*)"', lst):
        if m.group(2) not in [c for c, _ in codes]:
            codes.append((m.group(2), m.group(1)))
    print(f"nalezeno {len(codes)} unikátních kódů", file=sys.stderr)

    progs, skipped = [], 0
    for code, href in codes:
        try:
            html = fetch(BASE + href)
        except Exception as e:
            print(f"  warn {code}: {str(e)[:50]}", file=sys.stderr); continue
        text = detext(html)
        rec = parse_detail(text, code)
        nazev = rec.get("nazev") or ""
        if SKIP.search(nazev) or SKIP.search(code):
            skipped += 1; continue
        rec["url"] = BASE + href.split("?")[0]
        rec["_text"] = text[text.find("Program:"):text.find("Program:") + 3000] if "Program:" in text else ""
        progs.append(rec)

    out = {"source": "fondvysociny.cz", "kraj": "Kraj Vysočina", "programs": progs}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "FONDVYSOCINY_HARVEST", "kept": len(progs), "skipped_test": skipped,
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
