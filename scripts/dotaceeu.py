#!/usr/bin/env python3
"""dotaceeu.cz (MMR, výzvy z MS2021+) — vrstva 1 (2026‑11‑10).

Proč: zdroj `dotaceeu.cz` byl v katalogu jen z jednorázového sběru (červen),
bez sběrače; 9 ze 13 záznamů bylo po lhůtě. Portál přitom nese výzvy všech
operačních programů přímo z monitorovacího systému. Většinu programů čtou
vlastní zdroje (IROP, OP TAK, OPZ+, OP JAK, OP ŽP, OP D, OP ST), takže se
odtud bere jen to, co jinde není:

  08 OP Rybářství · 12 OP AMIF · 13 OP FVB · 14 OP NSHV (fondy MV, mezi
  žadateli neziskové organizace pro migraci a integraci) · finanční nástroje.

Výpis: `/cs/ajax-pages/vyzvyfeeddotace?&count=5&page=N` a
`…/vyzvyfeedfinanc` (týž požadavek, který posílá tlačítko „Načíst další“).
Detail má řádky „štítek: hodnota“ (číslo výzvy, druh, oprávnění žadatelé,
zahájení a ukončení příjmu, stav).

Výstup (tvar jako gacr/npzp): {url, host, title, body_text, attachments, n_attachments}
Spuštění: python scripts/dotaceeu.py --out data/dotaceeu.cz_documents.jsonl
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.request
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

B = "https://www.dotaceeu.cz"
HOST = "www.dotaceeu.cz"
UA = "Mozilla/5.0 (compatible; regrantio; +https://grantio.cz)"
FEEDS = ("vyzvyfeeddotace", "vyzvyfeedfinanc")
# Programy, které jiný zdroj nečte (viz hlavička). Klíč = začátek složky v adrese.
KEEP = re.compile(r"/Obdobi-2021-2027/(08|12|13|14)-|/Financni-nastroje/")


def fetch(url, retries=3):
    # Adresy nesou „–“ a „—“ (OP Rybářství, OP ŽP); urllib chce ASCII.
    url = quote(url, safe=":/?&=%,()+")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(retries):
        try:
            with http_util.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch selhal: {url} ({last})")


def listing():
    out = []
    for feed in FEEDS:
        for page in range(1, 120):
            h = fetch(f"{B}/cs/ajax-pages/{feed}?&count=5&page={page}")
            links = [html.unescape(x) for x in re.findall(r'href="(/Jak-ziskat-dotaci/Vyzvy/[^"]+)"', h)]
            new = [x for x in dict.fromkeys(links) if x not in out]
            if not new:
                break
            out += new
            time.sleep(0.15)
    return [u for u in out if KEEP.search(u)]


def to_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>|</dt>|</dd>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def body_of(page):
    """Obsah od nadpisu výzvy po přihlašovací okno odběru (dál je jen patička)."""
    i = page.find("<h1")
    s = page[i:] if i >= 0 else page
    for stop in ("Odebírejte aktualizace", "<footer"):
        j = s.find(stop)
        if j > 0:
            s = s[:j]
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/dotaceeu.cz_documents.jsonl")
    args = ap.parse_args()
    recs = []
    for path in listing():
        url = B + path
        page = fetch(url)
        content = body_of(page)
        m = re.search(r"(?is)<h1[^>]*>(.*?)</h1>", content)
        title = to_text(m.group(1)) if m else path.rsplit("/", 1)[-1]
        text = to_text(content)
        # „Přidat do svého kalendáře“ a sdílení jsou ovládání, ne obsah.
        text = "\n".join(ln.strip() for ln in text.split("\n")
                         if ln.strip() and not re.match(r"^(Přidat do svého kalendáře|Created with Sketch\.?)$", ln.strip()))
        atts, seen = [], set()
        for href, label in re.findall(r'(?is)<a[^>]*href="([^"]+\.(?:pdf|docx?|xlsx?)[^"]*)"[^>]*>(.*?)</a>', content):
            u = html.unescape(href if href.startswith("http") else B + href)
            if u not in seen:
                seen.add(u)
                atts.append({"url": u, "label": to_text(label) or u.rsplit("/", 1)[-1]})
        more = re.search(r'(?is)Více informací na:.*?<a[^>]*href="([^"]+)"', content)
        if more:
            text += f"\nOdkaz na výzvu u poskytovatele: {html.unescape(more.group(1))}"
        recs.append({"url": url, "host": HOST, "title": title, "body_text": text,
                     "attachments": atts, "n_attachments": len(atts)})
        time.sleep(0.2)
    if not recs:
        print("✖ dotaceeu: výpis nedal žádnou výzvu (změna portálu?)", file=sys.stderr)
        sys.exit(1)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  body={len(r['body_text']):5} :: {r['title'][:72]}", flush=True)
    print(f"DOTACEEU_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
