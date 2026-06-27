#!/usr/bin/env python3
"""Tenký harvester platformy custom_php — eeagrants.cz (Fondy EHP a Norska).

Server-rendered, BEZ Apify. Strom: /cs/programy/<oblast> + podstránky (cíle/alokace/
harmonogram) + /cs/vyzvy. Vrstva 1: vytáhne {url, title, text, documents[]} → krmí
univerzální vrstvu 2 (extract_wf). BFS 1 úroveň pod /cs/programy/ a /cs/vyzvy/.

Spuštění: python3 scripts/eeagrants.py --out data/eeagrants.jsonl
"""
import argparse, html as H, json, os, re, ssl, sys, time, urllib.request
from urllib.parse import urljoin, urlparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limits import L   # centrální registr limitů (root limits.json)

BASE = "https://www.eeagrants.cz"
import http_util   # jednotná TLS politika (audit #7/#32)
UA = {"User-Agent": "Mozilla/5.0 (eeagrants-harvest; re-grantio)"}

def fetch(url, timeout):
    req = urllib.request.Request(url, headers=UA)
    return http_util.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")

def clean(s):
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def parse_page(url, html):
    h1 = re.search(r"<h1[^>]*>(.+?)</h1>", html, re.S)
    title = clean(h1.group(1)) if h1 else None
    # tělo = všechny odstavce + položky seznamů s podstatným textem
    blocks = re.findall(r"<(?:p|li|h2|h3)[^>]*>(.+?)</(?:p|li|h2|h3)>", html, re.S)
    text = "\n".join(t for t in (clean(b) for b in blocks) if len(t) > L("acquisition.min_text_block_chars"))
    # dokumenty (pdf/doc/xls) + interní odkazy pro BFS
    docs = sorted({urljoin(url, H.unescape(u))
                   for u in re.findall(r'href="([^"]+\.(?:pdf|docx?|xlsx?|pptx?|odt|ods|rtf|zip))"', html, re.I)})
    links = {urljoin(url, H.unescape(u)) for u in re.findall(r'href="(/cs/(?:programy|vyzvy)/[^"#?]+)"', html)}
    return {"url": url, "title": title, "text": text, "documents": docs}, links

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/eeagrants.jsonl")
    ap.add_argument("--timeout", type=int, default=L("http.default_timeout_s"))
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--max-pages", type=int, default=L("safety.runaway_page_ceiling"))
    args = ap.parse_args()

    # seed: výpis výzev + 9 programových oblastí (z homepage menu)
    seeds = [f"{BASE}/cs/vyzvy"] + [f"{BASE}/cs/programy/{p}" for p in (
        "vyzkum", "vzdelavani", "kultura", "zdravi", "radna-sprava", "obcanska-spolecnost",
        "socialni-dialog", "zivotni-prostredi", "lidska-prava", "spravedlnost", "vnitrni-veci")]
    seen, queue, recs = set(), list(seeds), []
    while queue:
        if len(recs) >= args.max_pages:        # runaway-pojistka, ne coverage cap — data celá
            print(f"  ⚠ RUNAWAY-pojistka {args.max_pages} dosažena (fronta {len(queue)}) — prošetři link-filtr/past", file=sys.stderr)
            break
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            html = fetch(url, args.timeout)
        except Exception as e:
            print(f"  ERR {url}: {type(e).__name__}", file=sys.stderr); continue
        rec, links = parse_page(url, html)
        recs.append(rec)
        for l in links:                      # BFS 1 úroveň (jen pod seed-stromem)
            if l not in seen and len(seen) + len(queue) < args.max_pages * 2:
                queue.append(l)
        print(f"  {url[len(BASE):]:55} title={(rec['title'] or '')[:30]!r:32} docs={len(rec['documents'])}", file=sys.stderr)
        time.sleep(args.delay)

    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    nd = sum(len(r["documents"]) for r in recs)
    print(json.dumps({"MARKER": "EEAGRANTS", "pages": len(recs), "documents": nd, "out": args.out}, ensure_ascii=False))

if __name__ == "__main__":
    main()
