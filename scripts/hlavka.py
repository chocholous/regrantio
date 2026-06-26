#!/usr/bin/env python3
"""Hlávkova nadace (Nadání Josefa, Marie a Zdeňky Hlávkových, hlavkovanadace.cz) — vrstva 1.

Specifika, kvůli kterým je nutný VLASTNÍ parser (univerzální harvest_site selže):
  • Stránky jsou v kódování **windows-1250** (ne UTF-8) → harvest_site by je rozbil.
  • Hlavní menu je JS (Tigra Menu, scripts/menu_items_*.js) — homepage NEMÁ <a> odkazy na
    grantové podstránky, takže statický BFS je nenajde. → seed-driven (URL z menu configu).
  • <title> je vždy "Hlávkova nadace" → skutečný titul = první výrazný nadpis (<b>/<font size>)
    v obsahu (délka > 15, ne "Hlávkova nadace").
  • Obsah je čistá inline próza ve <table> buňkách; žádné PDF přílohy (grantové podmínky
    jsou přímo v textu stránky).

Výstup (shodný tvar jako marwel/eagri → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění: python3 scripts/hlavka.py --seeds <JSON list|soubor> --out data/hlavka_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util   # jednotná TLS politika (audit #7/#32)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DOC_RE = re.compile(r'href="([^"]*\.(?:pdf|docx?|xlsx?|rtf|odt)(?:\?[^"]*)?)"', re.I)


def fetch(url, tries=3, timeout=30):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with http_util.urlopen(req, timeout=timeout) as r:
                return r.read().decode("windows-1250", "replace"), r.geturl()   # web běží v cp1250
        except Exception:  # noqa: BLE001
            time.sleep(1.0 * (i + 1))
    return None, None


def to_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</td>|</tr>|</li>|</h[1-6]>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def title_of(h):
    """<title> je vždy 'Hlávkova nadace' → vezmi první výrazný nadpis v obsahu."""
    for m in re.finditer(r"<(?:b|strong|h[1-3])\b[^>]*>(.*?)</(?:b|strong|h[1-3])>|<font[^>]*size[^>]*>(.*?)</font>", h, re.S | re.I):
        t = to_text(m.group(1) or m.group(2) or "")
        if len(t) > 15 and "hlávkova nadace" not in t.lower():
            return t[:200]
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    return to_text(m.group(1)) if m else None


def process(url):
    h, final = fetch(url)
    if not h:
        return {"url": url, "error": "fetch_fail"}
    base = final or url
    host = re.match(r"https?://([^/]+)", base).group(1)
    atts, seen = [], set()
    for href in DOC_RE.findall(h):
        full = urljoin(base, html.unescape(href))
        if full not in seen:
            seen.add(full)
            atts.append({"url": full, "label": ""})
    return {"url": url, "host": host, "title": title_of(h),
            "body_text": to_text(h),   # plný text, žádný ořez (limits.json acquisition.input_truncation=null)
            "attachments": atts, "n_attachments": len(atts)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, help="JSON list URL nebo soubor")
    ap.add_argument("--out", default="data/hlavka_documents.jsonl")
    ap.add_argument("--delay", type=float, default=0.3)
    args = ap.parse_args()
    seeds = json.load(open(args.seeds, encoding="utf-8")) if os.path.exists(args.seeds) else json.loads(args.seeds)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    open(args.out, "w").close()
    for i, u in enumerate(seeds):
        rec = process(u)
        open(args.out, "a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{i+1}/{len(seeds)}] att={rec.get('n_attachments','-')} body={len(rec.get('body_text') or '')} :: {str(rec.get('title'))[:55]}", flush=True)
        time.sleep(args.delay)
    print(f"HLAVKA_DONE {len(seeds)} -> {args.out}")


if __name__ == "__main__":
    main()
