#!/usr/bin/env python3
"""marwel CMS (MŠMT a spol.) — vrstva 1: článek dotační výzvy → text + přílohy.

Marwel renderuje článek do <div id="article"> (article-perex + article-content);
přílohy jsou odkazy /file/NNNNN/ (handler bez přípony → univerzální doc/harvest_site
regex je nechytí, proto vlastní FILE_RE). <title> má tvar "Název článku, MŠMT ČR"
(název PRVNÍ → org suffix se odřízne). Přílohy se jen LISTUJÍ (lossless); stažení +
konverzi (pdftotext) dělá doc-store ve fázi 2 (build_extract_input → docstore.store_url).

Výstup (shodný tvar jako vismo/mv_cms → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění: python3 scripts/marwel.py --seeds <JSON list|soubor> --out data/marwel_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin, urlsplit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util   # jednotná TLS politika (audit #7/#32)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
# marwel příloha = handler /file/NNNNN (bez přípony) NEBO přímý odkaz na dokument (/uploads/*.pdf apod.)
FILE_RE = re.compile(r'<a[^>]+href="(/file/\d+[^"]*|[^"]*\.(?:pdf|docx?|xlsx?|odt|ods|pptx?|rtf|zip)(?:\?[^"]*)?)"[^>]*>(.*?)</a>', re.S | re.I)
ORG_SUFFIX = re.compile(r"\s*,\s*MŠMT(\s+ČR)?\s*$", re.I)   # "Název, MŠMT ČR" → "Název"
BARE_FILE = re.compile(r"^/file/\d+/?$")              # /file/NNNNN/ = HTML detail souboru, NE download
DL_IN_DETAIL = re.compile(r'href="([^"]*?/file/\d+_\d+_\d+[^"]*)"')   # skutečný download na detail-stránce (rel. i abs.)


def fetch(url, tries=3, timeout=30):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with http_util.urlopen(req, timeout=timeout) as r:
                return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace"), r.geturl()
        except Exception:  # noqa: BLE001
            time.sleep(1.0 * (i + 1))
    return None, None


def to_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def content_area(h):
    """Vrať vyvážený <div id="article">…</div> (perex + obsah). Depth-scan zvládne vnořené divy."""
    i = h.find('id="article"')
    if i < 0:
        i = h.find('class="main_content"')
    if i < 0:
        return h
    start = h.rfind("<div", 0, i)
    if start < 0:
        return h
    depth = 0
    for m in re.finditer(r"<div\b|</div>", h[start:]):
        depth += 1 if m.group() == "<div" else -1
        if depth == 0:
            return h[start:start + m.end()]
    return h[start:]


def title_of(h):
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    if not m:
        return None
    return ORG_SUFFIX.sub("", html.unescape(m.group(1)).strip()) or None


def resolve_file(url, label):
    """Bare /file/NNNNN/ je HTML detail souboru (ne download) → najdi skutečný
    /file/NNNNN_x_x/ + jméno souboru z <title>. Ostatní URL vrať beze změny."""
    if not BARE_FILE.match(urlsplit(url).path):
        return url, label
    h, _ = fetch(url, tries=2)
    if not h:
        return url, label
    m = DL_IN_DETAIL.search(h)
    t = re.search(r"<title>(.*?)</title>", h, re.S)
    name = ORG_SUFFIX.sub("", html.unescape(t.group(1)).strip()) if t else label
    return (urljoin(url, html.unescape(m.group(1))) if m else url), (name or label)


def process(url):
    h, final = fetch(url)
    if not h:
        return {"url": url, "error": "fetch_fail"}
    base = final or url
    host = re.match(r"https?://([^/]+)", base).group(1)
    ca = content_area(h)
    atts, seen = [], set()
    for href, label in FILE_RE.findall(ca):
        full = urljoin(base, html.unescape(href))   # robustní: relativní (/file/, /uploads/) i absolutní href
        full, label = resolve_file(full, to_text(label)[:120])   # bare /file/N/ → skutečný download
        if full in seen:
            continue
        seen.add(full)
        atts.append({"url": full, "label": (label or "")[:120]})
    return {"url": url, "host": host, "title": title_of(h),
            "body_text": to_text(ca),   # plný text článku, žádný ořez (limits.json acquisition.input_truncation=null)
            "attachments": atts, "n_attachments": len(atts)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, help="JSON list URL nebo soubor")
    ap.add_argument("--out", default="data/marwel_documents.jsonl")
    args = ap.parse_args()
    seeds = json.load(open(args.seeds, encoding="utf-8")) if os.path.exists(args.seeds) else json.loads(args.seeds)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    open(args.out, "w").close()
    for i, u in enumerate(seeds):
        rec = process(u)
        open(args.out, "a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{i+1}/{len(seeds)}] att={rec.get('n_attachments','-')} body={len(rec.get('body_text') or '')} :: {str(rec.get('title'))[:55]}", flush=True)
    print(f"MARWEL_DONE {len(seeds)} -> {args.out}")


if __name__ == "__main__":
    main()
