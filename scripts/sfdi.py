#!/usr/bin/env python3
"""Státní fond dopravní infrastruktury (sfdi.cz → sfdi.gov.cz) — vrstva 1.

SFDI poskytuje „příspěvky" (dotace) z rozpočtu na dopravní infrastrukturu obcí/krajů:
cyklostezky, bezbariérové chodníky, bezpečnost silnic II./III. třídy, křížení komunikací,
zabezpečení letišť, multimodální překladiště, jednotky ETCS, nové technologie, povodňové škody.

Vlastní parser: programy jsou WP sub-pages pod /prispevky/ které jsou přes WP REST 401
(neautorizováno) → harvestujeme FRONT-END HTML. Každá stránka má strukturovaný blok
„Základní údaje o příspěvku" (Výše příspěvku · Výše podpory SFDI · Termín pro žádosti ·
Oprávnění žadatelé) + „Co lze financovat" + Pravidla PDF. Status NEpočítá (kód z „Termín").

Discovery: /prispevky/ → odkazy /prispevky/<slug>/ (year-agnostic). Tělo ořezáno před sekcí
„Nejnovější aktuality" (to jsou news, ne podmínky výzvy).

Výstup (shodný tvar jako sfzp/sfpi → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění z kořene repa: python3 scripts/sfdi.py --out data/sfdi_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí české diagnostiky → UTF-8
    sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
B = "https://sfdi.gov.cz"
HOST = "sfdi.gov.cz"
HUB = f"{B}/prispevky/"
NEWS_MARK = "Nejnovější aktuality"          # konec podmínek, začátek news → ořež
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
    h = re.sub(r"(?is)<(script|style|nav|footer|header|form)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def content_region(h):
    """Hlavní obsahová výseč stránky (main/article/entry-content)."""
    for pat in (r"<main[^>]*>(.*?)</main>", r"<article[^>]*>(.*?)</article>",
                r'<div[^>]*class="[^"]*entry-content[^"]*"[^>]*>(.*?)</div>\s*</div>'):
        m = re.search(pat, h, re.S)
        if m and len(m.group(1)) > 500:
            return m.group(1)
    return h


def discover():
    """Slugy programů z /prispevky/ (vyloučit feed/hub samotný)."""
    h = fetch(HUB)
    slugs = []
    for s in re.findall(r'href="https?://sfdi\.gov\.cz/prispevky/([a-z0-9-]+)/"', h, re.I):
        if s not in slugs and s not in ("feed", "rss2"):
            slugs.append(s)
    return slugs


def title_of(h, slug):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    if m:
        t = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
        if t:
            return t
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else slug
    return re.sub(r"\s*[-–|]\s*SFDI.*$", "", t).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sfdi_documents.jsonl")
    args = ap.parse_args()
    recs = []
    for slug in discover():
        url = f"{B}/prispevky/{slug}/"
        try:
            h = fetch(url)
        except Exception as e:
            print(f"  ⚠ {slug}: fetch selhal → přeskakuji ({str(e)[:50]})", flush=True)
            continue
        reg = content_region(h)
        body = to_text(reg)
        cut = body.find(NEWS_MARK)               # ořež news sekci (Nejnovější aktuality)
        if cut > 200:
            body = body[:cut].strip()
        if len(body) < 150 or "Základní údaje" not in body and "Oprávnění žadatelé" not in body:
            print(f"  ⚠ {slug}: bez bloku Základní údaje ({len(body)} zn) → přeskakuji", flush=True)
            continue
        # tělo nese VŠECHNY podmínky (Výše/Termín/žadatelé/Co financovat) → z příloh stačí
        # autoritativní Pravidla/Výzva (ne desítky formulářových šablon); fallback: první 3.
        all_docs, seen = [], set()
        for href in DOC_RE.findall(reg):
            u = urljoin(B, html.unescape(href))
            if u not in seen:
                seen.add(u)
                all_docs.append({"url": u, "label": u.rsplit("/", 1)[-1]})
        key = [d for d in all_docs if re.search(r"pravidl|vyzv|výzv", d["label"], re.I)]
        atts = key or all_docs[:3]
        recs.append({"url": url, "host": HOST, "title": title_of(h, slug),
                     "body_text": body, "attachments": atts, "n_attachments": len(atts)})
        time.sleep(0.3)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  att={r['n_attachments']:2} body={len(r['body_text']):5} :: {r['title'][:58]}", flush=True)
    print(f"SFDI_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
