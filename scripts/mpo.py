#!/usr/bin/env python3
"""Ministerstvo průmyslu a obchodu (mpo.cz → mpo.gov.cz) — vrstva 1, NÁRODNÍ programy.

MPO je obří víceagendový web (custom CMS, server-rendered). Dotace mají dvě vrstvy:
  • NÁRODNÍ programy (TENTO parser): vlastní programy MPO (TREND, TRIO, TWIST, The Country for
    the Future, Czech Rise Up, Obchůdek 2021+, podpora brownfieldů, strategické investice, …).
  • EU OP TAK / OP PIK (NE tady — patří do P3 EU; výzvy běží přes MS2021+/AIS, samostatně).

Programy = landing pages pod /cz/podnikani/… (seed-driven; web nemá strojový seznam jen národních
programů, OP TAK by zaplavil discovery). Landing page nese popis programu + news feed posledních
výzev. Konkrétní lhůty/alokace jsou v navázaných aktualitách (vrstva 2 + doménová znalost).
Status NEpočítá (kód z deadline).

Výstup (shodný tvar jako sfdi/sfk → build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění z kořene repa: python3 scripts/mpo.py --out data/mpo_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí české diagnostiky → UTF-8
    sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
B = "https://mpo.gov.cz"
HOST = "mpo.gov.cz"
# Národní programy MPO (seed = landing page). OP TAK/OP PIK schválně NEjsou (P3 EU).
SEEDS = [
    "/cz/podnikani/vnitrni-obchod/program-obchudek-2021/",
    "/cz/podnikani/podpora-vyzkumu-a-vyvoje/program-trend/program-trend--275263/",
    "/cz/podnikani/podpora-vyzkumu-a-vyvoje/program-trio/trio--282310/",
    "/cz/podnikani/podpora-vyzkumu-a-vyvoje/program-twist/program-twist--282314/",
    "/cz/podnikani/podpora-vyzkumu-a-vyvoje/program-the-country-for-the-future/program-na-podporu-inovaci-the-country-for-the-future--275246/",
    "/cz/podnikani/podpora-vyzkumu-a-vyvoje/technologicka-inkubace-startupu/technologicka-inkubace-start-upu--275257/",
    "/cz/podnikani/dotace-a-podpora-podnikani/program-czech-rise-up-3-0/",
    "/cz/podnikani/dotace-a-podpora-podnikani/program-strategicke-investice-pro-klimaticky-neutralni-hodpodarstvi/",
    "/cz/podnikani/dotace-a-podpora-podnikani/podpora-brownfieldu/default.htm",
]
DOC_RE = re.compile(r'href="([^"]+\.(?:pdf|docx?|xlsx?)[^"]*)"', re.I)


def fetch(url, timeout=35, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(retries):
        try:
            with http_util.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8", "replace")
            if body.strip():
                return body
            last = "prázdná odpověď"
        except Exception as e:
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch selhal po {retries} pokusech: {url} ({last})")


def to_text(h):
    h = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def content_region(h):
    for pat in (r"<main[^>]*>(.*?)</main>", r'<div[^>]*id="content"[^>]*>(.*?)</div>\s*</div>',
                r"<article[^>]*>(.*?)</article>"):
        m = re.search(pat, h, re.S)
        if m and len(m.group(1)) > 600:
            return m.group(1)
    return h


def title_of(h):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    if m:
        t = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
        if t:
            return t
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
    return re.sub(r"\s*[-–|]\s*MPO.*$", "", t).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/mpo_documents.jsonl")
    args = ap.parse_args()
    recs = []
    for path in SEEDS:
        url = urljoin(B, path)
        try:
            h = fetch(url)
        except Exception as e:
            print(f"  ⚠ {path}: fetch selhal → přeskakuji ({str(e)[:50]})", flush=True)
            continue
        reg = content_region(h)
        body = to_text(reg)
        if len(body) < 150:
            print(f"  ⚠ {path}: tělo {len(body)} zn → přeskakuji", flush=True)
            continue
        atts, seen = [], set()
        for href in DOC_RE.findall(reg):
            u = urljoin(B, html.unescape(href))
            if u not in seen:
                seen.add(u)
                atts.append({"url": u, "label": u.rsplit("/", 1)[-1]})
        recs.append({"url": url, "host": HOST, "title": title_of(h),
                     "body_text": body, "attachments": atts, "n_attachments": len(atts)})
        time.sleep(0.3)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  att={r['n_attachments']:2} body={len(r['body_text']):5} :: {r['title'][:58]}", flush=True)
    print(f"MPO_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
