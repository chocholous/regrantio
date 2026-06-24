#!/usr/bin/env python3
"""Harvester pražských grantů (vrstva 1) napříč platformami — server-rendered, BEZ Apify/Playwright.

Centrální rozcestník = homepage granty.praha.eu → 6 oblastí:
  - Zdravotnictví = WordPress (zdravotni.praha.eu) → WP REST
  - Kultura/Školství/Cestovní ruch/Památky/Sociální = Liferay (praha.eu) → server-rendered HTML,
    grant-podstránky pod /web/<oblast>/ + dokumenty v doclib /documents/d/praha/
(Award DB granty.praha.eu portál = project, řeší lewis_dynamo.py — zde NE.)

Výstup: data/praha_grants.jsonl  {oblast, url, title, text, documents[]}
Spuštění: python3 scripts/praha_grants.py
"""
import argparse, html as H, json, os, re, ssl, sys, time, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limits import L   # centrální registr limitů (root limits.json)

import http_util   # jednotná TLS politika (audit #7/#32)
UA = {"User-Agent": "Mozilla/5.0 (praha-grants-harvest; re-grantio)"}
GRANT_SLUG = re.compile(r"dotac|grant|program|vyzva|individualni|granty|prispevek|pamatk", re.I)

def fetch(url, timeout):
    return http_util.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read().decode("utf-8", "replace")

def clean(s):
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def docs_in(url, html):
    return sorted({urljoin(url, H.unescape(u)) for u in
                   re.findall(r'href="([^"]+\.(?:pdf|docx?|xlsx?|odt))"', html, re.I)} |
                  {urljoin(url, H.unescape(u)) for u in
                   re.findall(r'href="(/documents/d/[^"#?]+)"', html)})

# ---------- WordPress (zdravotni) ----------
def harvest_wp(timeout):
    B = "https://zdravotni.praha.eu/wp-json/wp/v2"
    out, p = [], 1
    kw = re.compile(r"dotac|grant|výzv|program|žádost|příjem", re.I)
    while True:
        d = json.loads(fetch(f"{B}/pages?per_page=100&page={p}&_fields=title,link,content", timeout))
        if not d:
            break
        for pg in d:
            t = pg.get("title", {}).get("rendered", ""); h = pg.get("content", {}).get("rendered", "")
            if kw.search(t) or kw.search(h):   # celý obsah, ne prvních N znaků (žádný recall cap)
                out.append({"oblast": "zdravotnictvi", "url": pg["link"], "title": H.unescape(t),
                            "text": clean(h), "documents": docs_in(pg["link"], h)})
        if len(d) < 100:
            break
        p += 1
    return out

# ---------- Liferay (5 oblastí) ----------
def harvest_liferay(area, seed, timeout, delay, max_pages):
    seen, queue, done = set(), [seed], 0
    while queue:
        if done >= max_pages:                 # runaway-pojistka, ne coverage cap — data se berou celá
            print(f"  ⚠ [{area}] RUNAWAY-pojistka {max_pages} dosažena (fronta {len(queue)}) — prošetři link-filtr/past", file=sys.stderr)
            break
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            html = fetch(url, timeout)
        except Exception as e:
            print(f"  ERR {url}: {type(e).__name__}", file=sys.stderr); continue
        title = clean((re.search(r"<h1[^>]*>(.+?)</h1>", html, re.S) or [None, None])[1] or
                      (re.search(r"<title>([^<]+)", html) or [None, ""])[1])
        blocks = re.findall(r"<(?:p|li|h2|h3|td)[^>]*>(.+?)</(?:p|li|h2|h3|td)>", html, re.S)
        text = "\n".join(t for t in (clean(b) for b in blocks) if len(t) > L("acquisition.min_text_block_chars"))
        rec = {"oblast": area, "url": url, "title": title, "text": text, "documents": docs_in(url, html)}
        done += 1
        yield rec   # streamuj rovnou (main zapisuje inkrementálně)
        # BFS jen na grant-relevantní podstránky v téže oblasti
        path = re.search(r"/web/[^/]+", url)
        base = path.group(0) if path else ""
        for u in re.findall(r'href="((?:https://praha\.eu)?' + re.escape(base) + r'/[^"#?]+)"', html):
            full = urljoin(url, H.unescape(u))
            if full not in seen and GRANT_SLUG.search(full) and len(seen) + len(queue) < max_pages * 2:
                queue.append(full)
        print(f"  [{area}] {url.split('/web/')[-1][:42]:42} title={(title or '')[:24]!r} docs={len(rec['documents'])}", file=sys.stderr)
        time.sleep(delay)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/praha_grants.jsonl")
    ap.add_argument("--timeout", type=int, default=L("http.default_timeout_s"))
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--max-pages", type=int, default=L("safety.runaway_page_ceiling"),
                    help="runaway-pojistka (limits.json safety.runaway_page_ceiling); NE coverage cap — data celá")
    args = ap.parse_args()

    liferay = {"kultura": "https://praha.eu/web/kultura/dotace",
               "skolstvi": "https://praha.eu/skolstvi-granty",
               "cestovniruch": "https://praha.eu/web/cestovniruch/dotace",
               "pamatky": "https://praha.eu/web/pamatky/dotace",
               "socialni": "https://praha.eu/web/socialni/granty-a-dotace"}
    recs = []
    # INKREMENTÁLNÍ zápis — každý záznam hned na disk, ať timeout/pád nic neshodí
    with open(args.out, "w", encoding="utf-8") as o:
        for r in harvest_wp(args.timeout):
            recs.append(r); o.write(json.dumps(r, ensure_ascii=False) + "\n"); o.flush()
        print(f"  zdravotnictvi (WP): {len(recs)} stránek", file=sys.stderr)
        for area, seed in liferay.items():
            for r in harvest_liferay(area, seed, args.timeout, args.delay, args.max_pages):
                recs.append(r); o.write(json.dumps(r, ensure_ascii=False) + "\n"); o.flush()

    from collections import Counter
    nd = sum(len(r["documents"]) for r in recs)
    print(json.dumps({"MARKER": "PRAHA_GRANTS", "pages": len(recs), "documents": nd,
                      "per_oblast": dict(Counter(r["oblast"] for r in recs)), "out": args.out}, ensure_ascii=False))

if __name__ == "__main__":
    main()
