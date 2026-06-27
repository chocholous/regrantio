#!/usr/bin/env python3
"""Nadace Veronica (nadace.veronica.cz) — vrstva 1: grantová stránka → text.

Statický webbuilder web (.php, UTF-8). Tenký seed-driven parser:
  • Každá stránka nese stejné rozsáhlé navigační MENU končící položkou „Kontakt"; obsah
    (včetně mise „je největší moravská nadace…") začíná až za ním → odřízneme nav.
  • <title> má tvar „<Název stránky> | Nadace Veronica" / „…, Nadace Veronica" → suffix off.
  • Obsah je inline próza; přílohy (formuláře .doc/.docx) se listují.

Výstup (shodný tvar jako marwel/eagri → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění: python3 scripts/veronica.py --seeds <JSON list|soubor> --out data/veronica_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin, urlsplit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util   # jednotná TLS politika (audit #7/#32)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DOC_RE = re.compile(r'href="([^"]*\.(?:pdf|docx?|xlsx?|odt)(?:\?[^"]*)?)"', re.I)
ORG_SUFFIX = re.compile(r"\s*[|,]\s*Nadace Veronica\s*$", re.I)


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
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def content_after_menu(h):
    """Menu končí položkou „Kontakt"; obsah (vč. mise) je za jejím PRVNÍM výskytem."""
    t = to_text(h)
    i = t.find("Kontakt")
    return t[i + len("Kontakt"):].strip() if i >= 0 else t


def title_of(h):
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    return ORG_SUFFIX.sub("", html.unescape(m.group(1)).strip()) if m else None


def process(url):
    h, final = fetch(url)
    if not h:
        return {"url": url, "error": "fetch_fail"}
    base = final or url
    atts, seen = [], set()
    for href in DOC_RE.findall(h):
        full = urljoin(base, html.unescape(href))
        if full not in seen:
            seen.add(full)
            atts.append({"url": full, "label": ""})
    return {"url": url, "host": urlsplit(base).netloc, "title": title_of(h),
            "body_text": content_after_menu(h), "attachments": atts, "n_attachments": len(atts)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", default="data/veronica_documents.jsonl")
    ap.add_argument("--delay", type=float, default=0.3)
    args = ap.parse_args()
    seeds = json.load(open(args.seeds, encoding="utf-8")) if os.path.exists(args.seeds) else json.loads(args.seeds)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    open(args.out, "w").close()
    for i, u in enumerate(seeds):
        rec = process(u)
        open(args.out, "a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{i+1}/{len(seeds)}] att={rec.get('n_attachments','-')} body={len(rec.get('body_text') or '')} :: {str(rec.get('title'))[:48]}", flush=True)
        time.sleep(args.delay)
    print(f"VERONICA_DONE {len(seeds)} -> {args.out}")


if __name__ == "__main__":
    main()
