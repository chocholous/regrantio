#!/usr/bin/env python3
"""Pardubický kraj harvester — dotační programy (server-rendered Nuxt HTML).

dotace.pardubickykraj.cz/grants = veřejný katalog BEZ loginu. Nuxt 3 SSR: programy
jsou server-rendered přímo v DOMu jako `grant-card` (NE v __NUXT_DATA__ payloadu, ten
nese jen UI state) → stačí HTTP fetch HTML, žádný prohlížeč. Každá karta má:
  .grant-card__date-range   → "od DD. MM. YYYY do DD. MM. YYYY"  (open_from / deadline)
  .grant-card__programName  → název
  .grant-card__subprogramName → popis (volitelný)
  <a href="/grants/{uuid}"> → absolutní URL detailu
Programy jsou seskupené po odborech (12 odborů, ~105 programů). Archivované programy
se dotahují až po kliknutí na toggle (zde záměrně mimo scope — chceme aktivní s termíny).

⚠ SSL chain je neúplný ("unable to verify first certificate") → http_util auto-fallback (ověř, při cert chybě opakuj bez ověření).

Tenký harvester (vrstva 1): bere jen čistě strukturovaná pole z listingu. alokace_czk,
eligible, kod NEjsou v listingu strukturované (jen v próze detailu) → null, doplní vrstva 2.
Status dopočítá ingest z termínů (NE zde). Dedup dle URL.

Usage: python3 scripts/pardubicky_harvest.py [--out data/h_kraj_pardubicky.json]
"""
import argparse, json, re, ssl, sys, urllib.request

BASE = "https://dotace.pardubickykraj.cz"
LISTING = BASE + "/grants"

CARD_RE = re.compile(r'<div class="grant-card".*?href="(/grants/[0-9a-fA-F-]+)"', re.S)
DATE_RE = re.compile(r'grant-card__date-range"[^>]*>(.*?)</span></span>', re.S)
NAME_RE = re.compile(r'grant-card__programName"[^>]*>(.*?)</div>', re.S)
SUB_RE = re.compile(r'grant-card__subprogramName"[^>]*>(.*?)</span>', re.S)
RANGE_RE = re.compile(
    r'od\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\s*do\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})')


import http_util   # jednotná TLS politika (audit #7/#32)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return http_util.urlopen(req, timeout=60).read().decode("utf-8", "replace")


def clean(html_frag):
    """Strip tags/entities from a small HTML fragment → plain text."""
    t = re.sub(r"<[^>]+>", " ", html_frag or "")
    t = (t.replace("&nbsp;", " ").replace("&amp;", "&")
         .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
         .replace("&#39;", "'").replace("\xa0", " "))
    return re.sub(r"\s+", " ", t).strip()


def _iso(dd, mm, yyyy):
    return f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"


def parse_card(block):
    nm = NAME_RE.search(block)
    nazev = clean(nm.group(1)) if nm else None
    if not nazev:
        return None
    open_from = deadline = None
    dr = DATE_RE.search(block)
    if dr:
        m = RANGE_RE.search(clean(dr.group(1)))
        if m:
            open_from = _iso(m.group(1), m.group(2), m.group(3))
            deadline = _iso(m.group(4), m.group(5), m.group(6))
    sm = SUB_RE.search(block)
    popis = clean(sm.group(1)) if sm else None
    return {
        "nazev": nazev,
        "open_from": open_from,
        "deadline": deadline,
        "status": None,            # dopočítá ingest z termínů
        "alokace_czk": None,       # není strukturovaně v listingu → vrstva 2
        "max_czk": None,
        "popis": popis or None,
        "eligible": None,          # jen v próze detailu → vrstva 2
        "kod": None,               # kód programu není v listingu
        "url": None,               # doplněno níže (absolutní)
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_pardubicky.json")
    a = ap.parse_args()

    html = fetch(LISTING)
    # Rozsekej na bloky karet: od každého '<div class="grant-card"' k dalšímu.
    starts = [m.start() for m in re.finditer(r'<div class="grant-card"', html)]
    starts.append(len(html))
    progs, seen = [], set()
    for i in range(len(starts) - 1):
        block = html[starts[i]:starts[i + 1]]
        href = CARD_RE.search(block)
        url = BASE + href.group(1) if href else None
        rec = parse_card(block)
        if not rec:
            continue
        rec["url"] = url
        key = url or rec["nazev"]
        if key in seen:
            continue
        seen.add(key)
        progs.append(rec)

    out = {
        "source": "dotace.pardubickykraj.cz",
        "kraj": "Pardubický kraj",
        "platform": "pardubicky_html",
        "programs": progs,
    }
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with_dates = sum(1 for p in progs if p["open_from"] or p["deadline"])
    print(json.dumps({"MARKER": "PARDUBICKY_HARVEST", "kept": len(progs),
                      "with_dates": with_dates, "out": a.out}, ensure_ascii=False),
          file=sys.stderr)


if __name__ == "__main__":
    main()
