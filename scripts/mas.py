#!/usr/bin/env python3
"""Výzvy místních akčních skupin z jejich webů — vrstva 1 pro čtení modelem (2026-11-15).

Proč a odkud: viz `mas_list.py`. Souhrnný výpis výzev MAS neexistuje, každá
MAS je vyhlašuje na svém webu a weby jsou různé (WordPress, iGalileo, Joomla,
Vismo, Webnode …; průzkum 15. 11.: 158 ze 189 má v menu odkaz na výzvy).
Termíny, alokace a oprávnění žadatelé jsou v textu výzvy, proto třída C:
sběrač jen najde a stáhne stránky výzev, čte je model nebo agent
(`extract_manual.py`).

Postup na webu jedné MAS:
  1. úvodní stránka → odkazy na rozcestníky výzev (slovo „výzv“ v textu nebo
     adrese), přednost má období 2021–2027, programy (IROP, OPZ+, OP TAK, SZP)
     a „aktuální / vyhlášené“; 2014–2020, archiv a ukončené se vynechají;
  2. rozcestník → odkazy na jednotlivé výzvy („3. výzva MAS …“, „výzva č.“);
  3. stránka výzvy se ponechá, jen když v textu stojí datum dnešní nebo
     pozdější: otevřená a ohlášená výzva ho má (konec příjmu), ukončená ne.
     Bez toho by se četly stovky ukončených výzev.
Rozcestník bez odkazů na výzvy, který sám nese budoucí datum, se ponechá
jako dokument (některé MAS píšou výzvy přímo do jedné stránky).

Výstup `data/mas_documents.jsonl` ve tvaru jako dotaceeu/gacr:
  {url, host, title, body_text, attachments, n_attachments, mas}
`mas` = jméno MAS z `data/mas_seeds.json`; podle něj ingest vymezí území výzvy
obcemi MAS.

Spuštění:  python scripts/mas.py [--seeds data/mas_seeds.json] [--only masck.cz] [--workers 8]
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")

import argparse
import concurrent.futures as cf
import html as H
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date
from urllib.parse import urljoin, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util  # noqa: E402
from harvest_site import clean, docs_in  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (compatible; regrantio; +https://grantio.cz)"}
CALLWORD = re.compile(r"výzv|vyzv", re.I)
OLD = re.compile(r"2014|2015|2016|2017|2018|2019|2014-2020|2014–2020|archiv|ukončen|ukoncen|\bprv\b|"
                 r"výsledk|vysledk|hodnocen|seznam|zápis|zapis|kontrol|změn[ay] výzv|metodik|šablon|"
                 r"plánovan|planovan|harmonogram", re.I)
GOOD = re.compile(r"2021|2027|aktuáln|aktualn|vyhlášen|vyhlasen|otevřen|otevren|irop|opz|op-?tak|szp|"
                  r"clld|leader|zemědělsk|zemedelsk", re.I)
SINGLE = re.compile(r"\d+\s*\.\s*výzv|výzva\s*(č\.|číslo|\d)|vyzva-?c?-?\d|\d+-vyzva", re.I)
DATE = re.compile(r"\b(\d{1,2})\.\s?(\d{1,2})\.\s?(20\d{2})\b")
MAX_INDEX, MAX_CALLS, PAUSE = 4, 30, 0.3


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with http_util.urlopen(req, timeout=25) as r:
        ctype = r.headers.get("Content-Type", "")
        if "html" not in ctype and ctype:
            return r.geturl(), ""
        return r.geturl(), r.read(1_500_000).decode("utf-8", "replace")


def links(base, page):
    """(text, absolutní adresa) odkazů na tomtéž webu."""
    host = urlparse(base).netloc.removeprefix("www.")
    out = []
    for href, text in re.findall(r'<a\b[^>]*href="([^"#]+)"[^>]*>(.*?)</a>', page, re.S | re.I):
        url = urljoin(base, H.unescape(href.strip()))
        if urlparse(url).netloc.removeprefix("www.") != host or re.search(r"\.(pdf|docx?|xlsx?|zip|jpe?g|png)$", url, re.I):
            continue
        out.append((clean(text), url.split("#")[0]))
    return list(dict.fromkeys(out))


def index_pages(home, page):
    scored = []
    for text, url in links(home, page):
        blob = f"{text} {url}"
        if not CALLWORD.search(blob) or OLD.search(blob):
            continue
        scored.append((len(GOOD.findall(blob)), text, url))
    scored.sort(key=lambda x: -x[0])
    return [url for _, _, url in scored][:MAX_INDEX]


# Menu bez slova „výzvy“ (24 webů z 180, 15. 11.): „Dotace“, „IROP“, „SZP“, „Programový rámec“.
HUB = re.compile(r"dotac|irop|\bszp\b|op[ -]?tak|\bopz|clld|leader|programov|grant|pro žadatele|pro-zadatele", re.I)


def hubs(home, page):
    return [u for t, u in links(home, page) if HUB.search(f"{t} {u}") and not OLD.search(f"{t} {u}")][:3]


# Datum je lhůta příjmu, jen když před ním stojí řeč o příjmu nebo podání;
# „realizace do 31. 5. 2027“ a „udržitelnost“ výzvu otevřenou nedělají.
INTAKE = re.compile(r"příj[em]|prij[em]|sběr|sber|podán|podani|podat|uzávěrk|uzaverk|žádost\w* (?:lze|je možné)|"
                    r"vyhlášen|zahájen|ve dnech|záměr|zamer", re.I)
NOT_INTAKE = re.compile(r"realizac|udržitel|udrzitel|platnost|způsobilost|zpusobilost|monitor|vyúčtov|proplac|"
                        r"komise|seminář|seminar|akce", re.I)
# Stránka o výzvě, která výzvou k podání není: uzavřena, výsledky, změna textu.
NOT_A_CALL = re.compile(r"uzavřen|uzavren|podán[oay] \d|podáno|vybrán|výsledk|změna č|zmena c|přehled podan", re.I)


def intake_dates(text, today):
    """Budoucí data, před kterými (do 90 znaků) stojí řeč o příjmu žádostí.
    Stojí-li tam i realizace nebo komise, rozhoduje slovo blíž k datu."""
    out = []
    for m in DATE.finditer(text):
        try:
            when = date(int(m[3]), int(m[2]), int(m[1]))
        except ValueError:
            continue
        if when < today:
            continue
        before = text[max(0, m.start() - 90):m.start()]
        yes = [x.end() for x in INTAKE.finditer(before)]
        no = [x.end() for x in NOT_INTAKE.finditer(before)]
        if yes and (not no or yes[-1] > no[-1]):
            out.append(when)
    return out


BLOCK = re.compile(r"<(?:p|li|h2|h3|h4|td|th|dt|dd)[^>]*>(.+?)</(?:p|li|h2|h3|h4|td|th|dt|dd)>", re.S)


def parse(url, page, boiler=frozenset()):
    """Stránka → dokument. `boiler` = bloky šablony webu (novinky, pozvánky v postranním
    panelu), které se opakují na stránkách téže MAS; do textu výzvy nepatří."""
    h1 = re.search(r"<h1[^>]*>(.+?)</h1>", page, re.S)
    title = clean(h1.group(1)) if h1 else clean((re.search(r"<title>([^<]+)", page) or [None, ""])[1])
    blocks = [t for t in (clean(b) for b in BLOCK.findall(page)) if len(t) > 2 and t not in boiler]
    text = "\n".join(dict.fromkeys(blocks))
    atts = [{"url": u, "label": u.rsplit("/", 1)[-1]} for u in docs_in(url, page)][:40]
    return {"url": url, "host": urlparse(url).netloc, "title": title, "body_text": f"{title}\n{text}"[:60_000],
            "attachments": atts, "n_attachments": len(atts)}


def boilerplate(pages):
    """Delší bloky (nad 40 znaků), které stojí na třech a více stránkách téhož webu.
    Krátké se nechávají: popisky tabulek („Datum ukončení příjmu“) jsou v každé
    výzvě stejné a bez nich by datum ztratilo souvislost."""
    from collections import Counter
    if len(pages) < 3:
        return frozenset()
    seen = Counter()
    for page in pages:
        seen.update({clean(b) for b in BLOCK.findall(page)})
    # Popisek lhůty („Datum ukončení příjmu Projektových záměrů na MAS … viz níže“) je
    # dlouhý a stojí ve všech výzvách MAS; bez něj ztratí datum souvislost (Telčsko 15. 11.).
    return frozenset(b for b, n in seen.items()
                     if n >= 3 and len(b) > 40 and not INTAKE.search(b) and not DATE.search(b))


def one_mas(mas, today):
    """Dokumenty výzev jedné MAS a čísla pro hlášení."""
    stats = {"mas": mas["mas"], "index": 0, "calls": 0, "kept": 0, "err": None}
    try:
        home, page = fetch(mas["web"])
    except Exception as e:  # noqa: BLE001
        stats["err"] = f"úvod: {str(e)[:60]}"
        return [], stats
    fetched, seen, lonely = [], set(), []   # (adresa, html) výzev; rozcestníky bez výzev
    indexes = index_pages(home, page)
    if not indexes:
        for hub in hubs(home, page):
            time.sleep(PAUSE)
            try:
                hub_url, hub_page = fetch(hub)
            except Exception:  # noqa: BLE001
                continue
            indexes += [u for u in index_pages(hub_url, hub_page) if u not in indexes] or [hub_url]
        indexes = indexes[:MAX_INDEX]

    def call_links(base, html_page):
        return [u for t, u in links(base, html_page)
                if u != base and SINGLE.search(f"{t} {u}") and not OLD.search(f"{t} {u}")
                and not NOT_A_CALL.search(t)][:MAX_CALLS]

    # Výzva jen v novinkách úvodní stránky (MAS Zlatá cesta, 15. 11.: „3. Výzva MAS –
    # IROP – HASIČI“ otevřená, v rozcestníku výzev ještě nebyla). Bere se jako první rozcestník.
    for idx in [home] + indexes:
        if idx == home:
            idx_url, idx_page = home, page
            calls = call_links(home, page)
            if not calls:
                continue
        else:
            time.sleep(PAUSE)
            try:
                idx_url, idx_page = fetch(idx)
            except Exception:  # noqa: BLE001
                continue
            stats["index"] += 1
            calls = call_links(idx_url, idx_page)
        for url in calls:
            if url in seen:
                continue
            seen.add(url)
            time.sleep(PAUSE)
            try:
                final, call_page = fetch(url)
            except Exception:  # noqa: BLE001
                continue
            stats["calls"] += 1
            fetched.append((final, call_page))
        if not calls and idx_url not in seen:
            seen.add(idx_url)
            lonely.append((idx_url, idx_page))
    boiler = boilerplate([p for _, p in fetched + lonely] + [page])
    docs = []
    for url, html_page in fetched + lonely:
        doc = parse(url, html_page, boiler)
        if NOT_A_CALL.search(doc["title"]) or not CALLWORD.search(doc["body_text"]):
            continue
        if intake_dates(doc["body_text"], today):
            docs.append({**doc, "mas": mas["mas"]})
    # Táž výzva pod dvěma rozcestníky (IROP i „aktuální výzvy“) jednou.
    docs = list({d["url"]: d for d in docs}.values())
    stats["kept"] = len(docs)
    return docs, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="data/mas_seeds.json")
    ap.add_argument("--out", default="data/mas_documents.jsonl")
    ap.add_argument("--only", help="jen MAS, jejíž web obsahuje tento řetězec")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--today", default=date.today().isoformat())
    a = ap.parse_args()
    today = date.fromisoformat(a.today)

    seeds = [m for m in json.load(open(a.seeds, encoding="utf-8")) if m.get("web")]
    if a.only:
        seeds = [m for m in seeds if a.only in m["web"]]
    docs, report = [], []
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for found, stats in ex.map(lambda m: one_mas(m, today), seeds):
            docs += found
            report.append(stats)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    errors = [r for r in report if r["err"]]
    for r in errors:
        print(f"  ⚠ {r['mas']}: {r['err']}", file=sys.stderr)
    print(json.dumps({"MARKER": "MAS_HARVEST", "mas": len(seeds), "with_docs": sum(1 for r in report if r["kept"]),
                      "no_index": sum(1 for r in report if not r["err"] and not r["index"]),
                      "calls_read": sum(r["calls"] for r in report), "docs": len(docs), "errors": len(errors),
                      "out": a.out}, ensure_ascii=False))
    return 0 if docs else 1


if __name__ == "__main__":
    sys.exit(main())
