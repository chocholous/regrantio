#!/usr/bin/env python3
"""Nadace ADRA (nadace-adra.cz) — vrstva 1: grantové/příspěvkové stránky → text.

Statický multicms web (.html). Specifika vynucující vlastní (tenký) parser:
  • Každá stránka nese stejné rozsáhlé navigační MENU; obsah začíná až za markerem
    „CHCI DAROVAT" (poslední položka menu) → bez odříznutí by se menu opakovalo v každém
    body a tříštilo extrakci. Univerzální harvest_site by menu bral jako text.
  • <title> má tvar „<Název stránky>, Nadace ADRA" → org-suffix se odřízne.
  • Obsah je inline próza (žádné PDF přílohy).

Výstup (shodný tvar jako marwel/eagri → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění: python3 scripts/nadace_adra.py --seeds <JSON list|soubor> --out data/nadace_adra_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin, urlsplit
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util   # jednotná TLS politika (audit #7/#32)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
DOC_RE = re.compile(r'href="([^"]*\.(?:pdf|docx?|xlsx?|odt)(?:\?[^"]*)?)"', re.I)
ORG_SUFFIX = re.compile(r"\s*,\s*Nadace ADRA\s*$", re.I)


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
    """Obsah začíná za poslední položkou menu „CHCI DAROVAT"; ber text za posledním výskytem."""
    t = to_text(h)
    i = t.rfind("CHCI DAROVAT")
    return t[i + len("CHCI DAROVAT"):].strip() if i >= 0 else t


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
    ap.add_argument("--seeds", required=True, help="JSON list URL nebo soubor")
    ap.add_argument("--out", default="data/nadace_adra_documents.jsonl")
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
    print(f"NADACE_ADRA_DONE {len(seeds)} -> {args.out}")


if __name__ == "__main__":
    main()
