#!/usr/bin/env python3
"""Nadace Via (nadacevia.cz) — vrstva 1: WP REST pages → grantové výzvy.

Velká komunitní nadace; grantové výzvy nejsou WP CPT ani posts (posts = blog),
ale samostatné WP *pages* pod fondy (Milion pro …, Fond JRD, T-Mobile aj.).
Tenký harvester: stáhne VŠECHNY /wp-json/wp/v2/pages a vybere skutečné grantové
výzvy = stránka s UZÁVĚRKOU/příjmem žádostí + grantovými signály; vyřadí
semináře/formuláře/stránky pro už podpořené.

Výstup (shodný tvar jako ostatní layer-1 → build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění: python scripts/nadacevia.py --out data/nadacevia_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin, urlsplit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util   # jednotná TLS politika (audit #7/#32)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
BASE = "https://www.nadacevia.cz"
DOC_RE = re.compile(r'href="([^"]*\.(?:pdf|docx?|xlsx?|odt)(?:\?[^"]*)?)"', re.I)
# grantový signál: uzávěrka / příjem žádostí / „žádost … do DD…"
CALL_SIG = re.compile(r"uzávěrk|příjem žádost|podávejte žádost|podání žádost|grantov[áé] výzv|žádost o (grant|podporu|nadační)", re.I)
GRANT_KW = re.compile(r"grant|žádost|podpor|výzv|nadační příspěv", re.I)
# vyřaď ne-granty: výsledky (podpořené projekty), FAQ, závěrečné zprávy, generické šablony
# přihlášek/formulářů, stránky pro účastníky/už-podpořené, semináře, akademie/kurzy, staré verze.
EXCLUDE = re.compile(
    r"seminář|seminare|webinar|akademie|kurz|"
    r"podpořené|podporene|časté ?otáz|caste-?otaz|závěrečná ?zpráv|zaverecna|"
    r"pro[- ]účast|pro-ucast|pro[- ]podpořen|pro-podporen|pro-vyucujici|"
    r"setkán|setkani|zájem o|zajem-o|-stare\b|stare$|"
    r"… ?přihláška|\.\.\. ?přihláška|^přihláška$|^formulář|přihláška dokážeme|formular", re.I)
# pozitivní gate na NÁZEV: musí nést programový/grantový klíč (vyřadí osamocené názvy obcí =
# staré duplikáty „Milion pro [obec]" bez programového kontextu).
INCLUDE_TITLE = re.compile(
    r"milion|fond|grant|projekt|zahrad|komunit|míst[oě]|mikrogrant|žádost|"
    r"výzv|diabet|předsudk|podnikání|udržiteln|duševní|příběh", re.I)
# stránka mise
ABOUT_SLUGS = ("o-nas", "o-nadaci", "kdo-jsme", "poslani-a-hodnoty")


def fetch_json(url, tries=4, timeout=30):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with http_util.urlopen(req, timeout=timeout) as r:
                return dict(r.headers), json.loads(r.read().decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            time.sleep(1.3 * (i + 1))
    return {}, None


def to_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def all_pages():
    pages, pg = [], 1
    while True:
        hdr, arr = fetch_json(f"{BASE}/wp-json/wp/v2/pages?per_page=100&page={pg}"
                              "&_fields=id,slug,link,title,content")
        if not arr:
            break
        pages += arr
        try:
            total = int(hdr.get("x-wp-totalpages") or hdr.get("X-WP-TotalPages") or pg)
        except ValueError:
            total = pg
        if pg >= total:
            break
        pg += 1
    return pages


def is_call(slug, title, text):
    if EXCLUDE.search(slug) or EXCLUDE.search(title):
        return False
    if not INCLUDE_TITLE.search(title):
        return False
    return bool(CALL_SIG.search(text) and GRANT_KW.search(text))


def shape(p):
    raw = (p.get("content") or {}).get("rendered", "") or ""
    body = to_text(raw)
    title = to_text((p.get("title") or {}).get("rendered", ""))
    url = p.get("link") or f"{BASE}/?p={p.get('id')}"
    atts, seen = [], set()
    for href in DOC_RE.findall(raw):
        full = urljoin(url, html.unescape(href))
        if full not in seen:
            seen.add(full)
            atts.append({"url": full, "label": ""})
    return {"url": url, "host": urlsplit(url).netloc, "title": title,
            "body_text": body, "attachments": atts, "n_attachments": len(atts)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/nadacevia_documents.jsonl")
    ap.add_argument("--include-about", action="store_true", default=True,
                    help="přidej stránku mise (o nás) jako záznam pro foundation_mission")
    args = ap.parse_args()
    pages = all_pages()
    out = []
    for p in pages:
        body = to_text((p.get("content") or {}).get("rendered", ""))
        title = to_text((p.get("title") or {}).get("rendered", ""))
        if is_call(p.get("slug", ""), title, body) and len(body) > 200:
            out.append(shape(p))
    calls = len(out)
    if args.include_about:
        for p in pages:
            if p.get("slug") in ABOUT_SLUGS:
                out.append(shape(p))
                break
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in out:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"MARKER": "NADACEVIA", "pages_total": len(pages), "calls": calls,
                      "records": len(out), "out": args.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
