#!/usr/bin/env python3
"""Univerzální layer-1 harvester server-rendered grantových webů (zobecňuje eeagrants/praha_grants).

Per zdroj: re-detekce živě (WP REST? statický? SPA?) → sběr grant-relevantních podstránek
{url, title, text, documents[]}. SPA (nízký statický obsah) se NEHARVESTUJE — označí na headless.
Limity z limits.json (max_pages se LOGuje, ne tiše). Žádný strop natvrdo.

Spuštění: python3 scripts/harvest_site.py --base https://www.nadacecs.cz --source nadacecs
"""
import argparse, html as H, json, os, re, ssl, sys, time, urllib.request
from urllib.parse import urljoin, urlparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limits import L

import http_util       # jednotná TLS politika (audit #7/#32)
UA = {"User-Agent": "Mozilla/5.0 (regrantio-harvest)"}
GRANT = re.compile(r"grant|dotac|výzv|vyzv|program|žádost|zadost|podpor|nadační příspěv|nadacni-prispev|jak-zadat|jak-ziskat|pro-zadatele|kdo-muze", re.I)

def fetch(url, timeout):
    return http_util.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read().decode("utf-8", "replace")

def clean(s):
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def docs_in(url, html):
    return sorted({urljoin(url, H.unescape(u)) for u in re.findall(r'href="([^"]+\.(?:pdf|docx?|xlsx?|odt))"', html, re.I)}
                  | {urljoin(url, H.unescape(u)) for u in re.findall(r'href="([^"]*/documents/d/[^"#?]+)"', html)})

def parse(url, html):
    h1 = re.search(r"<h1[^>]*>(.+?)</h1>", html, re.S)
    title = clean(h1.group(1)) if h1 else clean((re.search(r"<title>([^<]+)", html) or [None, ""])[1])
    blocks = re.findall(r"<(?:p|li|h2|h3|td)[^>]*>(.+?)</(?:p|li|h2|h3|td)>", html, re.S)
    text = "\n".join(t for t in (clean(b) for b in blocks) if len(t) > L("acquisition.min_text_block_chars"))
    return {"url": url, "title": title, "text": text, "documents": docs_in(url, html)}

def is_spa(html):
    body = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
    txt = clean(body.group(1)) if body else clean(html)
    spa_mark = re.search(r"__NEXT_DATA__|__NUXT__|ng-app|id=\"root\"|id=\"app\"", html)
    return bool(spa_mark) and len(txt) < 800   # JS marker + skoro prázdné tělo = SPA

def wp_pages(base, timeout):
    """Pokud běží WP REST → vrať pages+posts s grant-relevancí."""
    host = urlparse(base).netloc
    out = []
    for rest in ("pages", "posts"):
        try:
            p = 1
            while True:
                d = json.loads(fetch(f"{base}/wp-json/wp/v2/{rest}?per_page=100&page={p}&_fields=title,link,content", timeout))
                if not d: break
                for r in d:
                    t = (r.get("title") or {}).get("rendered", ""); ht = (r.get("content") or {}).get("rendered", "")
                    if GRANT.search(t) or GRANT.search(ht[:800]):
                        out.append({"url": r.get("link"), "title": H.unescape(t), "text": clean(ht), "documents": docs_in(r.get("link", base), ht)})
                if len(d) < 100: break
                p += 1
        except Exception:
            return None   # REST nedostupné
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--source", required=True)
    ap.add_argument("--out"); ap.add_argument("--timeout", type=int, default=L("http.default_timeout_s"))
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--max-pages", type=int, default=L("safety.runaway_page_ceiling"),
                    help="runaway-pojistka (limits.json safety.runaway_page_ceiling); NE coverage cap — data se berou celá")
    args = ap.parse_args()
    out = args.out or f"data/{args.source}.jsonl"
    host = urlparse(args.base).netloc

    # 0) homepage + SPA detekce
    try:
        home = fetch(args.base, args.timeout)
    except Exception as e:
        print(json.dumps({"MARKER": "HARVEST_SITE", "source": args.source, "status": f"ERR_fetch:{type(e).__name__}"})); return
    if is_spa(home):
        print(json.dumps({"MARKER": "HARVEST_SITE", "source": args.source, "status": "SPA_needs_headless", "out": None})); return

    # 1) WP REST?
    method = "static_bfs"
    recs = wp_pages(args.base, args.timeout)
    if recs is not None:
        method = "wp_rest"
    else:
        # 2) statický BFS po grant-podstránkách (same host)
        recs = []
        seen, queue = set(), [args.base]
        for u in re.findall(r'href="([^"]+)"', home):
            full = urljoin(args.base, H.unescape(u))
            if urlparse(full).netloc == host and GRANT.search(full):
                queue.append(full.split("#")[0])
        while queue:
            if len(recs) >= args.max_pages:
                print(f"  ⚠ [{args.source}] RUNAWAY-pojistka {args.max_pages} dosažena (fronta {len(queue)}) — prošetři link-filtr/past, NEzvyšuj naslepo", file=sys.stderr); break
            url = queue.pop(0)
            if url in seen: continue
            seen.add(url)
            try:
                h = fetch(url, args.timeout)
            except Exception:
                continue
            recs.append(parse(url, h))
            for u in re.findall(r'href="([^"]+)"', h):
                full = urljoin(url, H.unescape(u)).split("#")[0]
                if urlparse(full).netloc == host and GRANT.search(full) and full not in seen and len(seen) + len(queue) < args.max_pages * 2:
                    queue.append(full)
            time.sleep(args.delay)

    for r in recs:
        r["source"] = args.source
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    nd = sum(len(r["documents"]) for r in recs)
    print(json.dumps({"MARKER": "HARVEST_SITE", "source": args.source, "status": "ok", "method": method,
                      "pages": len(recs), "documents": nd, "out": out}, ensure_ascii=False))

if __name__ == "__main__":
    main()
