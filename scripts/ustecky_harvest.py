#!/usr/bin/env python3
"""Ústecký kraj harvester — dotační kalendář (vismo VISMO 6, id_org=450018).

www.kr-ustecky.cz blokuje ne-prohlížečové fetchery (detail/listing → 404 i s browser
hlavičkami). Portál dotací (portalobcana.kr-ustecky.cz) je jen autentizovaný formulářový
portál — žádné veřejné JSON-API se seznamem výzev (odposlech: jen language-file + Voiceflow
chat). Proto JEDINÁ cesta = Playwright na vismo dotačním kalendáři.

Zdroj: https://www.kr-ustecky.cz/dotacni-kalendar?parent=2 — JS-rendered grid (NE <table>):
  article.subsidy-programs-result > div[role=cell].subsidy-programs-result__{id,name,area,
  contact-people,financial-allocation,start-date,end-date}. Stránkování je JS (javascript:void),
  numerické odkazy 1..N → klikáme. Status NEpočítáme tady (kontrakt status=null) — dopočte ingest
  z open_from/deadline (pravidlo projektu: status = kód, ne page label).

Lossless: bereme VŠECHNY programy kalendáře (otevřené i ne) s plnými poli; openness plyne z dat.

Setup: playwright install chromium
Usage: python3 scripts/ustecky_harvest.py --out data/h_kraj_ustecky.json
"""
import argparse, json, re, sys
from playwright.sync_api import sync_playwright

URL = "https://www.kr-ustecky.cz/dotacni-kalendar?parent=2"
BASE = "https://www.kr-ustecky.cz"

CELL = {
    "kod": "subsidy-programs-result__id",
    "nazev": "subsidy-programs-result__name",
    "oblast": "subsidy-programs-result__area",
    "alokace": "subsidy-programs-result__financial-allocation",
    "start": "subsidy-programs-result__start-date",
    "end": "subsidy-programs-result__end-date",
}


def _iso(s):
    """'1. 8. 2025' / '16. 1. 2026' → 'YYYY-MM-DD'."""
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s or "")
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def _int_czk(s):
    """'17 000 000 Kč' → 17000000 (sjednotí mezery/NBSP)."""
    digits = re.sub(r"[^\d]", "", (s or "").replace("\xa0", " "))
    return int(digits) if digits else None


def extract_page(pg):
    """Vrátí list dict per article na aktuální stránce gridu."""
    out = []
    for art in pg.query_selector_all("article.subsidy-programs-result"):
        def cell(cls):
            el = art.query_selector(f".{cls}")
            return el.inner_text().strip() if el else ""
        name_a = art.query_selector(f".{CELL['nazev']} a")
        href = name_a.get_attribute("href") if name_a else None
        url = (BASE + href) if href and href.startswith("/") else (href or None)
        rec = {
            "nazev": cell(CELL["nazev"]) or None,
            "open_from": _iso(cell(CELL["start"])),
            "deadline": _iso(cell(CELL["end"])),
            "status": None,                       # dopočítá ingest z dat
            "alokace_czk": _int_czk(cell(CELL["alokace"])),
            "max_czk": None,
            "popis": None,
            "eligible": None,
            "kod": cell(CELL["kod"]) or None,
            "url": url,
            "_oblast": cell(CELL["oblast"]) or None,   # extra kontext, ingest si vybere
        }
        out.append(rec)
    return out


def click_page(pg, n):
    """Klikne numerický stránkovací odkaz n (javascript:void). True když nalezen."""
    for a in pg.query_selector_all("a"):
        if a.inner_text().strip() == str(n) and (a.get_attribute("href") or "").startswith("javascript"):
            a.click()
            return True
    return False


def harvest():
    progs, seen = [], set()
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        pg.goto(URL, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(4000)

        # zjisti max číslo stránky
        pages = {int(a.inner_text().strip()) for a in pg.query_selector_all("a")
                 if a.inner_text().strip().isdigit() and (a.get_attribute("href") or "").startswith("javascript")}
        # odhal i vyšší čísla přes "Na konec"
        for a in pg.query_selector_all("a"):
            if a.inner_text().strip() == "Na konec":
                a.click(); pg.wait_for_timeout(2500); break
        pages |= {int(a.inner_text().strip()) for a in pg.query_selector_all("a")
                  if a.inner_text().strip().isdigit() and (a.get_attribute("href") or "").startswith("javascript")}
        maxp = max(pages) if pages else 1
        print(f"stránek kalendáře: {maxp}", file=sys.stderr)

        for n in range(1, maxp + 1):
            if not click_page(pg, n):
                # stránka 1 je výchozí zobrazení; pokud odkaz není, spolehni na aktuální stav
                if n != 1:
                    print(f"  warn: odkaz na stránku {n} nenalezen", file=sys.stderr)
            pg.wait_for_timeout(2000)
            page_recs = extract_page(pg)
            new = 0
            for r in page_recs:
                key = r["url"] or (r["nazev"], r["kod"])
                if key in seen:
                    continue
                seen.add(key); progs.append(r); new += 1
            print(f"  stránka {n}: {len(page_recs)} článků, {new} nových", file=sys.stderr)
        b.close()
    return progs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_ustecky.json")
    a = ap.parse_args()

    progs = harvest()
    out = {
        "source": "kr-ustecky.cz",
        "kraj": "Ústecký kraj",
        "platform": "ustecky_vismo",
        "programs": progs,
    }
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "USTECKY_HARVEST", "method": "Playwright-vismo",
                      "kept": len(progs), "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
