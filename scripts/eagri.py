#!/usr/bin/env python3
"""eAGRI portál (Ministerstvo zemědělství, mze.gov.cz / eagri.cz) — vrstva 1: dotační program → text + dokumenty.

eAGRI běží na vlastním portálovém CMS (design-systém `ea-*`, server-rendered; pozn.: routing.yaml
ho detekoval jako custom_spa — MÝLKA, je plně server-rendered). Specifika, kvůli kterým je nutný
VLASTNÍ parser (univerzální harvest_site by selhal):
  • Obsah stránky je v `<div class="ea-content-block …">` blocích PO `<h1>` (zbytek `<main>` je
    rozsáhlé menu — 300+ nav odkazů; harvest_site by je bral jako text i jako fronta BFS).
  • Přílohy (Zásady, Informace pro žadatele, formuláře) NEJSOU odkazy s příponou, ale handler
    `/public/portal/mze/-aNNNNN---HASH/<slug>?_linka=aNNNNNN` (bez .pdf/.docx → univerzální doc
    regex je nechytí). Typ se zjistí až z Content-Type/Content-Disposition (doc-store sniff_ext);
    download vrací application/pdf | …wordprocessingml… apod. ZÁSADNÍ: grantové podmínky (lhůta,
    částka, oprávnění žadatelé) žijí v příloze Zásady (docx/pdf), ne v textu stránky.
  • <h1> má `<span class="insite-only">` (in-site fulltext zvýrazňovač) — titul je uvnitř.

Přílohy se jen LISTUJÍ (lossless); stažení + konverzi (pdftotext/python-docx) dělá doc-store ve
fázi 2 (build_extract_input → docstore.store_url). sniff_ext zvládne extensionless `-aNNNN` handler.

Výstup (shodný tvar jako marwel/mv_cms → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění: python3 scripts/eagri.py --seeds <JSON list|soubor> --out data/eagri_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util   # jednotná TLS politika (audit #7/#32)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
# eAGRI příloha = handler /public/portal/mze/-aNNNNN---HASH/… (bez přípony) NEBO přímý dokument
FILE_RE = re.compile(
    r'href="(/public/portal/mze/-a\d+---[^"]+|[^"]*\.(?:pdf|docx?|xlsx?|odt|ods|pptx?|rtf|zip)(?:\?[^"]*)?)"',
    re.I)
ORG_SUFFIX = re.compile(r"\s*\|\s*(MZe|Ministerstvo zemědělství.*)$", re.I)   # "<title> | MZe"


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


def _balanced_div(h, start):
    """Vrať vyvážený <div …>…</div> od pozice start (depth-scan zvládne vnořené divy)."""
    depth = 0
    for m in re.finditer(r"<div\b|</div>", h[start:]):
        depth += 1 if m.group() == "<div" else -1
        if depth == 0:
            return h[start:start + m.end()]
    return h[start:]


def content_area(h):
    """Spoj VŠECHNY `ea-content-block` divy PO <h1> (vlastní obsah stránky: úvodní próza +
    výpis dokumentů). Zbytek <main> je menu → vynecháno. Fallback: <main>, pak celé."""
    hi = h.find("<h1")
    parts = []
    for m in re.finditer(r'<div class="ea-content-block', h):
        if m.start() > hi:
            parts.append(_balanced_div(h, h.rfind("<div", 0, m.start() + 5)))
    if parts:
        return "\n".join(parts)
    mn = re.search(r"<main\b[^>]*>(.*?)</main>", h, re.S)
    return mn.group(1) if mn else h


def title_of(h):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    if m:
        t = to_text(m.group(1))
        if t:
            return t
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    return ORG_SUFFIX.sub("", html.unescape(m.group(1)).strip()) if m else None


def _label_near(ca, href):
    """Titulek přílohy = nejbližší <div class="insite-only">…</div> v rámci stejné položky."""
    i = ca.find(href)
    if i < 0:
        return ""
    win = ca[i:i + 1200]
    m = re.search(r'class="insite-only">([^<]+)</div>', win)
    return html.unescape(m.group(1)).strip()[:120] if m else ""


def process(url):
    h, final = fetch(url)
    if not h:
        return {"url": url, "error": "fetch_fail"}
    base = final or url
    host = re.match(r"https?://([^/]+)", base).group(1)
    ca = content_area(h)
    atts, seen = [], set()
    for href in FILE_RE.findall(ca):
        full = urljoin(base, html.unescape(href))
        if full in seen:
            continue
        seen.add(full)
        atts.append({"url": full, "label": _label_near(ca, href)})
    return {"url": url, "host": host, "title": title_of(h),
            "body_text": to_text(ca),   # plný text obsahu, žádný ořez (limits.json acquisition.input_truncation=null)
            "attachments": atts, "n_attachments": len(atts)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, help="JSON list URL nebo soubor")
    ap.add_argument("--out", default="data/eagri_documents.jsonl")
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
    print(f"EAGRI_DONE {len(seeds)} -> {args.out}")


if __name__ == "__main__":
    main()
