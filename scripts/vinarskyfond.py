#!/usr/bin/env python3
"""Vinařský fond ČR (vinarskyfond.cz) — vrstva 1: tematické okruhy podpory → text + Pravidla PDF.

WordPress + Divi page-builder. Specifika vynucující vlastní parser:
  • Stránka /podpory/ je postavená v Divi → obsah `wp/v2/pages` je zaplevelen shortcody
    `[et_pb_*]` a `@ET-DC@...@` tokeny (univerzální WP harvest by je vzal jako text).
  • Jednotlivé OKRUHY podpory (A–F) jsou samostatné opportunities, ale leží na JEDNÉ stránce
    jako odkazy `Pravidla – okruh X` na PDF (31662_2026_Pravidla_okruh_X.pdf). Grantové podmínky
    (předmět, výše/míra podpory, žadatel) jsou v tom PDF, ne v textu stránky → tady rozdělíme
    stránku na 1 záznam per okruh (sdílený kontext stránky + okruh-PDF jako příloha).

Výstup (shodný tvar jako marwel/eagri → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}
  — 1 záznam „podpory" (fond celkově) + 1 záznam per okruh (url = okruh-PDF, title z labelu).

Spuštění: python3 scripts/vinarskyfond.py --page https://vinarskyfond.cz/podpory/ --out data/vinarskyfond_documents.jsonl
"""
import argparse, json, os, re, sys, html, urllib.request
from urllib.parse import urljoin, urlsplit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util   # jednotná TLS politika (audit #7/#32)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
OKRUH_RE = re.compile(r'<a[^>]+href="([^"]*Pravidla_okruh_([A-F])[^"]*\.pdf)"[^>]*>(.*?)</a>(.*?)(?=<a\b|Pravidla\s*[–-]\s*okruh|\Z)', re.S | re.I)


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with http_util.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), r.geturl()


def strip_divi(h):
    h = re.sub(r"\[/?et_pb_[^\]]*\]", " ", h)         # Divi shortcody
    h = re.sub(r"@ET-DC@[^@]*@", " ", h)              # Divi dynamic-content tokeny
    return h


def to_text(h):
    h = strip_divi(h)
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def page_content(page_url):
    """Stáhni obsah stránky přes WP REST (čistší než HTML), fallback na HTML."""
    host = urlsplit(page_url).netloc
    slug = [s for s in page_url.rstrip("/").split("/") if s][-1]
    try:
        d = json.loads(fetch(f"https://{host}/wp-json/wp/v2/pages?slug={slug}&_fields=content,link", 30)[0])
        if d:
            return d[0]["content"]["rendered"], d[0].get("link", page_url)
    except Exception:  # noqa: BLE001
        pass
    h, final = fetch(page_url)
    return h, final


def process(page_url):
    raw, base = page_content(page_url)
    host = urlsplit(base).netloc
    shared = to_text(raw)                              # sdílený kontext (termíny, kdo, jak podat)
    recs = []
    # 1) okruhy A–F (každý = 1 opportunity; url = okruh-PDF)
    seen = set()
    for m in OKRUH_RE.finditer(raw):
        pdf, letter = urljoin(base, html.unescape(m.group(1))), m.group(2).upper()
        if pdf in seen:
            continue
        seen.add(pdf)
        label = to_text(m.group(3) + " " + m.group(4))           # "Pravidla – okruh C – Školení…"
        label = re.sub(r"^Pravidla\s*[–-]\s*okruh\s*[A-F]\s*[–-]?\s*", "", label).strip()[:120]
        recs.append({"url": pdf, "host": host,
                     "title": f"Vinařský fond – okruh {letter}" + (f" – {label}" if label else ""),
                     "body_text": shared, "attachments": [{"url": pdf, "label": f"Pravidla okruh {letter}"}],
                     "n_attachments": 1})
    # 2) fond celkově (mission) — sdílený text + případné základní pokyny PDF
    pokyny = [urljoin(base, html.unescape(u)) for u in re.findall(r'href="([^"]*pokyny[^"]*\.pdf)"', raw, re.I)]
    recs.insert(0, {"url": base, "host": host, "title": "Vinařský fond České republiky",
                    "body_text": shared,
                    "attachments": [{"url": u, "label": "Základní pokyny"} for u in pokyny[:1]],
                    "n_attachments": min(len(pokyny), 1)})
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default="https://vinarskyfond.cz/podpory/")
    ap.add_argument("--out", default="data/vinarskyfond_documents.jsonl")
    args = ap.parse_args()
    recs = process(args.page)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  att={r['n_attachments']} body={len(r['body_text'])} :: {r['title'][:60]}", flush=True)
    print(f"VINARSKYFOND_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
