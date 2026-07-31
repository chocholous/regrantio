#!/usr/bin/env python3
"""Nadace na JS-renderovaných webech — layer-1 harvest přes Playwright.

PROČ SPOLEČNÝ HARVESTER (a ne 1 web = 1 parser): tyhle weby nespojuje CMS, ale PŘEKÁŽKA —
grantová nabídka je vyrenderovaná JS, takže `curl` vrátí prázdný shell (ověřeno: Nadace
Partnerství 203 kB HTML, ale jediný <a href>). Postup je proto u všech identický:
vyrenderuj stránku → vezmi text a odkazy → vyber grantové podstránky → vyrenderuj detaily.
Rozdíly mezi weby se vejdou do konfigurace (seed URL + pozitivní/negativní filtr), takže
per-web parser by byl jen kopie s jinými konstantami.

Rozsah (weby ověřené jako JS-renderované, 2026-07-31):
  nadacepartnerstvi.cz · osf.cz · nadacevodafone.cz · lpr.cz (Liga proti rakovině)
  nclf.cz (Český literární fond) · abakus.cz

LOSSLESS: ukládá se plný text stránky; datumy/částky NEparsuje (to je práce vrstvy 2).
Bounds jen safety (limits.json) — žádný cap na počet grantů.

Výstup (kontrakt jako ostatní *_documents.jsonl):
  data/nadace_spa_documents.jsonl  {host, web, nadace, title, url, kind, body_text,
                                    attachments[], n_attachments}

Prerekvizita: pip install playwright && playwright install chromium
Spuštění:  python scripts/nadace_spa.py [--nadace osf] [--headed]
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse
import json
import os
import re
import sys
from urllib.parse import urljoin, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limits import L  # noqa: E402

NADACE = {
    "partnerstvi": {
        "name": "Nadace Partnerství", "host": "nadacepartnerstvi.cz",
        "seeds": ["https://www.nadacepartnerstvi.cz/granty"],
        "pos": r"grant|vyzv|program|podpor|dotac",
        "neg": r"podporene-projekty|vysledky|archiv|newsletter|o-nas|kontakt|blog|clanek",
    },
    "osf": {
        "name": "Nadace OSF", "host": "osf.cz",
        "seeds": ["https://osf.cz/granty/", "https://osf.cz/programy/"],
        "pos": r"grant|vyzv|program|stipend|fond",
        "neg": r"podporene|vysledky|archiv|o-nas|kontakt|tym|novinky|clanek|vyrocni",
    },
    "vodafone": {
        "name": "Nadace Vodafone", "host": "nadacevodafone.cz",
        "seeds": ["https://www.nadacevodafone.cz/programy.html"],
        "pos": r"program|grant|vyzv|podpor",
        "neg": r"o-nadaci|kontakt|novinky|archiv|vysledky",
    },
    "lpr": {
        "name": "Liga proti rakovině Praha", "host": "lpr.cz",
        "seeds": ["https://www.lpr.cz/granty/"],
        "pos": r"grant|vyzv|projekt|podpor|nadacni",
        "neg": r"vysledky|archiv|o-nas|kontakt|novinky",
    },
    "nclf": {
        "name": "Nadace Český literární fond", "host": "nclf.cz",
        "seeds": ["https://www.nclf.cz/"],
        "pos": r"grant|vyzv|stipend|cena|podpor|program",
        "neg": r"o-nadaci|kontakt|historie|archiv|laureat",
    },
    "abakus": {
        "name": "Nadace Abakus", "host": "abakus.cz",
        "seeds": ["https://abakus.cz/vyzvy/", "https://abakus.cz/"],
        "pos": r"vyzv|grant|program|podpor",
        "neg": r"o-nas|kontakt|tym|pribeh|archiv",
    },
}
DOC_RE = re.compile(r"\.(pdf|docx?|xlsx?)(\?|$)", re.I)


def render(page, url, timeout_ms):
    """Vyrenderuj stránku → (text, [odkazy]). Vrací (None, []) při chybě."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(1500)          # doběh JS obsahu
        text = page.inner_text("body")
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        return text, hrefs
    except Exception as e:  # noqa: BLE001
        print(f"  [err] {url}: {type(e).__name__}", file=sys.stderr)
        return None, []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nadace", choices=sorted(NADACE), help="jen jedna nadace")
    ap.add_argument("--out", default="data/nadace_spa_documents.jsonl")
    ap.add_argument("--timeout", type=int, default=45000, help="ms na stránku")
    ap.add_argument("--headed", action="store_true", help="viditelný prohlížeč (ladění)")
    a = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("CHYBA: chybí playwright → pip install playwright && playwright install chromium",
              file=sys.stderr)
        sys.exit(2)

    ceiling = L("safety.runaway_page_ceiling") or 200
    recs = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not a.headed)
        ctx = browser.new_context(locale="cs-CZ", user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"))
        page = ctx.new_page()

        for key, cfg in NADACE.items():
            if a.nadace and key != a.nadace:
                continue
            pos, neg = re.compile(cfg["pos"], re.I), re.compile(cfg["neg"], re.I)
            seen, queue, n_site = set(), list(cfg["seeds"]), 0

            while queue and n_site < ceiling:
                url = queue.pop(0)
                if url in seen:
                    continue
                seen.add(url)
                text, hrefs = render(page, url, a.timeout)
                if not text or len(text) < 200:
                    continue
                n_site += 1
                atts = [{"url": h, "label": h.rsplit("/", 1)[-1][:120]}
                        for h in dict.fromkeys(hrefs) if DOC_RE.search(h)]
                title = (page.title() or "").strip() or url.rsplit("/", 1)[-1]
                recs.append({
                    "host": cfg["host"], "web": cfg["host"], "nadace": cfg["name"],
                    "kind": "vyzva", "title": re.sub(r"\s+", " ", title)[:250],
                    "url": url, "date": None,
                    "body_text": re.sub(r"\n{3,}", "\n\n", text).strip(),
                    "attachments": atts, "n_attachments": len(atts),
                })
                # z SEED stránky sbírej kandidáty na detaily (o úroveň níž)
                if url in cfg["seeds"]:
                    for h in dict.fromkeys(hrefs):
                        hp = urlsplit(h)
                        if cfg["host"] not in hp.netloc or h in seen:
                            continue
                        path = hp.path
                        if pos.search(path) and not neg.search(path) and len(path) > 6:
                            queue.append(urljoin(url, h.split("#")[0]))
            print(f"  [{key}] {cfg['name']}: {n_site} stránek", file=sys.stderr)
            if n_site >= ceiling:
                print(f"  ⚠ {key}: dosažen safety strop {ceiling} — prošetři", file=sys.stderr)
        browser.close()

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(json.dumps({"MARKER": "NADACE_SPA_HARVEST", "stran": len(recs),
                      "by_nadace": dict(Counter(r["nadace"] for r in recs)),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
