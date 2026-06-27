#!/usr/bin/env python3
"""Nadační fond Albert (nadacnifondalbert.cz) — vrstva 1: grantové stránky → text.

Symfony SSR web (build/ assety, ale OBSAH je server-rendered HTML, ne SPA-XHR).
Tenký seed-driven parser těží strukturu, ne nav-stripping:
  • Titulek je v `<h1>NÁZEV<span>podtitul</span></h1>` v banneru.
  • Obsah žije v jediném bloku `<div class="subpage-detail"> … </div>` před `<footer>`
    → izolujeme tenhle region (nav i footer ležící mimo něj se nepřilepí).
  • Inline base64 obrázky (`src="data:image/png;base64,…"`) se po de-tagování ztratí.
  • Případné PDF/doc přílohy (`/data/files/*.pdf`) se listují.

Výstup (shodný tvar jako veronica/nadace_adra → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění: python3 scripts/albert.py --seeds <JSON list|soubor> --out data/albert_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin, urlsplit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util   # jednotná TLS politika (audit #7/#32)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DOC_RE = re.compile(r'href="([^"]*\.(?:pdf|docx?|xlsx?|odt)(?:\?[^"]*)?)"', re.I)
ORG_SUFFIX = re.compile(r"\s*\|\s*Nadační fond Albert\s*$", re.I)
DETAIL_RE = re.compile(r'<div class="subpage-detail">(.*?)<footer', re.S | re.I)
H1_RE = re.compile(r"<h1>(.*?)</h1>", re.S | re.I)
DATA_IMG_RE = re.compile(r'<img[^>]*src="data:[^"]*"[^>]*>', re.I)


def fetch(url, tries=3, timeout=30):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with http_util.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace"), r.geturl()
        except Exception:  # noqa: BLE001
            time.sleep(1.0 * (i + 1))
    return None, None


def to_text(h):
    h = re.sub(r"(?is)<(script|style|svg)[^>]*>.*?</\1>", " ", h or "")
    h = DATA_IMG_RE.sub(" ", h)
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def detail_block(h):
    """Obsah = jediný blok <div class=subpage-detail> … </div> až po <footer>."""
    m = DETAIL_RE.search(h)
    return m.group(1) if m else h


def title_of(h):
    m = H1_RE.search(h)
    if m:
        raw = re.sub(r"(?is)<span[^>]*>.*?</span>", " ", m.group(1))  # podtitul pryč
        t = html.unescape(re.sub(r"<[^>]+>", " ", raw))
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            return t
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    return ORG_SUFFIX.sub("", html.unescape(m.group(1)).strip()) if m else None


def process(url):
    h, final = fetch(url)
    if not h:
        return {"url": url, "error": "fetch_fail"}
    base = final or url
    region = detail_block(h)
    atts, seen = [], set()
    for href in DOC_RE.findall(region):
        full = urljoin(base, html.unescape(href))
        if full not in seen:
            seen.add(full)
            atts.append({"url": full, "label": ""})
    return {"url": url, "host": urlsplit(base).netloc, "title": title_of(h),
            "body_text": to_text(region), "attachments": atts, "n_attachments": len(atts)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, help="JSON list URL nebo soubor")
    ap.add_argument("--out", default="data/albert_documents.jsonl")
    ap.add_argument("--delay", type=float, default=0.3)
    args = ap.parse_args()
    seeds = json.load(open(args.seeds, encoding="utf-8")) if os.path.exists(args.seeds) else json.loads(args.seeds)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    open(args.out, "w").close()
    for i, u in enumerate(seeds):
        rec = process(u)
        open(args.out, "a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{i+1}/{len(seeds)}] att={rec.get('n_attachments','-')} body={len(rec.get('body_text') or '')} :: {str(rec.get('title'))[:50]}", flush=True)
        time.sleep(args.delay)
    print(f"ALBERT_DONE {len(seeds)} -> {args.out}")


if __name__ == "__main__":
    main()
