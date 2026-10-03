#!/usr/bin/env python3
"""Národní program Životní prostředí (narodniprogramzp.cz) — vrstva 1.

Národní dotační program MŽP, administruje SFŽP. Menší, tematicky cílené výzvy
(čistírny odpadních vod, péče o přírodu, recyklace, návštěvnická střediska,
renovační pasy z NPO). Přidáno 2026-10-03: konkurence (grantlo.cz) z něj má
15 výzev a v katalogu nebyl vůbec.

Web je WordPress, výzvy ale nejsou v REST API: výpis `/nabidka-dotaci/` nese
odkazy `./detail-vyzvy/?id=<číslo>` na AKTUÁLNÍ nabídku (uzavřené z výpisu
mizí, upsert v katalogu je nechá dožít). Detail má štítky na samostatných
řádcích („Příjem žádostí:“, „Alokace:“, „Kdo může žádat“, „Výše příspěvku“,
„Termíny“), proto se text NEslévá do odstavců jako v `harvest_site.py`
(ten zahazuje krátké bloky a se štítky by přišel o strukturu).

Výstup (tvar pro build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění z kořene repa: python scripts/npzp.py --out data/npzp_documents.jsonl
"""
import argparse
import html
import os
import re
import sys
import time
import urllib.request
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util  # noqa: E402
from jsonl_out import write_jsonl  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (regrantio-harvest)"
BASE = "https://www.narodniprogramzp.cz"
LIST = f"{BASE}/nabidka-dotaci/"
HOST = "narodniprogramzp.cz"
DETAIL = re.compile(r'href="(\.?/?(?:nabidka-dotaci/)?detail-vyzvy/\?id=\d+)"')
DOC_RE = re.compile(r'<a[^>]+href="([^"]+\.(?:pdf|docx?|xlsx?)[^"]*)"[^>]*>(.*?)</a>', re.I | re.S)


def fetch(url, timeout=30, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(retries):
        try:
            with http_util.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 — síť: zkusit znovu, pak přeskočit
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch selhal: {url} ({last})")


def clean(h):
    """HTML → řádky. Bloky a buňky končí řádkem, takže štítek a hodnota stojí
    na vlastních řádcích a parser je najde (`extractors/npzp.py`)."""
    h = re.sub(r"(?is)<(script|style|noscript|template)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</h[1-6]>|</div>|</td>|</th>|</dt>|</dd>|</strong>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    t = re.sub(r"[ \t ]+", " ", t)
    lines = [ln.strip() for ln in t.split("\n") if ln.strip()]
    return "\n".join(lines)


def detail_block(text, title):
    """Obsah výzvy: od nadpisu po patičku resortu („Resort životního prostředí“)."""
    start = text.find(title)
    if start < 0:
        start = 0
    end = text.find("Resort životního prostředí", start)
    return text[start:end if end > start else None].strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/npzp_documents.jsonl")
    ap.add_argument("--delay", type=float, default=0.5)
    args = ap.parse_args()

    listing = fetch(LIST)
    urls = []
    for rel in DETAIL.findall(listing):
        u = urljoin(LIST, html.unescape(rel))
        if u not in urls:
            urls.append(u)
    print(f"  výpis: {len(urls)} výzev @ {HOST}", flush=True)

    recs = []
    for url in urls:
        try:
            h = fetch(url)
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠ {url}: {str(e)[:60]} → přeskakuji", flush=True)
            continue
        m = re.search(r"<h1[^>]*>(.+?)</h1>", h, re.S)
        title = html.unescape(re.sub(r"<[^>]+>|\s+", " ", m.group(1))).strip() if m else ""
        title = re.sub(r"\s+", " ", title)
        body = detail_block(clean(h), title)
        if "Příjem žádostí" not in body and "Kdo může žádat" not in body:
            print(f"  ⚠ {url}: bez strukturního bloku → přeskakuji", flush=True)
            continue
        atts, seen = [], set()
        for href, label in DOC_RE.findall(h):
            u = urljoin(url, html.unescape(href))
            lab = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", label))).strip()
            if u in seen:
                continue
            seen.add(u)
            atts.append({"url": u, "label": lab or u.rsplit("/", 1)[-1]})
        recs.append({"url": url, "host": HOST, "title": title, "body_text": body,
                     "attachments": atts[:3], "n_attachments": min(len(atts), 3)})
        time.sleep(args.delay)

    # Prázdná sklizeň nepřepíše předchozí (výpadek webu ≠ žádné výzvy).
    write_jsonl(args.out, recs)
    print(f"NPZP_DONE {len(recs)}/{len(urls)} -> {args.out}")


if __name__ == "__main__":
    main()
