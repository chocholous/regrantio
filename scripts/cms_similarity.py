#!/usr/bin/env python3
"""Detekce PODOBNÝCH CMS shlukováním strukturálních otisků (label-free).
Otisk webu = množina tokenů: normalizované asset-cesty (script/css, bez hashů),
charakteristické URL vzory, cookie názvy, Server/X-Powered-By, generator.
Shlukování: union-find na Jaccard(otisk_i, otisk_j) >= práh.
Výstup: shluky s jejich SPOLEČNÝMI diskriminačními tokeny → 1 shluk = 1 parser.
"""
import json, re, ssl, urllib.request
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
import http_util   # jednotná TLS politika (audit #7/#32)
THRESH = 0.30   # Jaccard práh pro „stejná rodina"

# normalizace asset cesty: zahoď host, hash (8+ hex), cache-busting query, číslo verze
def norm_asset(u):
    u = re.sub(r"https?://[^/]+", "", u)            # host pryč
    u = u.split("?")[0]
    u = re.sub(r"[.-][0-9a-f]{6,}\b", ".HASH", u)   # hash
    u = re.sub(r"\b\d+\.\d+(\.\d+)?\b", "V", u)      # verze
    u = re.sub(r"/\d{3,}/", "/N/", u)
    return u.lower()

URL_PATTERNS = [r"/clanek/", r"/soubor/", r"/getmedia/", r"/ds-\d", r"/ms-\d", r"/d-\d",
                r"resolveuid", r"/aspinclude/vismoweb", r"\+\+resource\+\+", r"/wp-content",
                r"/wp-json", r"/sites/default", r"/typo3conf", r"/media/jui", r"/_next/",
                r"/_nuxt/", r"__doPostBack", r"ng-app", r"cmspages", r"/gordic/ginis",
                r"/api/frontend", r"/at_download", r"drupal\.settings", r"liferay"]


def fingerprint(base):
    try:
        req = urllib.request.Request(base, headers={"User-Agent": UA})
        with http_util.urlopen(req, timeout=12) as r:
            html = r.read(300000).decode("utf-8", "replace")
            hdrs = {k.lower(): v for k, v in r.headers.items()}
    except Exception:
        return None
    toks = set()
    for u in re.findall(r'<script[^>]+src="([^"]+)"', html, re.I)[:30]:
        toks.add("js:" + norm_asset(u))
    for u in re.findall(r'<link[^>]+href="([^"]+\.css[^"]*)"', html, re.I)[:30]:
        toks.add("css:" + norm_asset(u))
    g = re.search(r'name="generator"[^>]*content="([^";]+)', html, re.I)
    if g:
        toks.add("gen:" + g.group(1).strip().lower()[:25])
    for p in URL_PATTERNS:
        if re.search(p, html, re.I):
            toks.add("url:" + p.strip("\\").strip("/")[:18])
    for c in re.findall(r"(\w+)=", hdrs.get("set-cookie", "")):
        toks.add("ck:" + c.lower())
    if hdrs.get("x-powered-by"):
        toks.add("xpb:" + hdrs["x-powered-by"][:20].lower())
    sv = hdrs.get("server", "")
    if sv:
        toks.add("srv:" + sv.split("/")[0].lower()[:12])
    return toks


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    d = json.load(open("data/merged_dataset.json"))
    bases = sorted({f"{urlparse(r['url']).scheme}://{urlparse(r['url']).netloc}" for r in d})
    print(f"otisky {len(bases)} hostů…", flush=True)
    fps = {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        for base, fp in zip(bases, ex.map(fingerprint, bases)):
            if fp:
                fps[urlparse(base).netloc] = fp
    print(f"otisků získáno: {len(fps)}", flush=True)

    hosts = list(fps)
    parent = {h: h for h in hosts}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b):
        parent[find(a)] = find(b)
    # union-find: spoj páry s Jaccard >= práh (jen kde sdílí aspoň 1 silný token)
    for i in range(len(hosts)):
        for j in range(i + 1, len(hosts)):
            if jaccard(fps[hosts[i]], fps[hosts[j]]) >= THRESH:
                union(hosts[i], hosts[j])
    clusters = {}
    for h in hosts:
        clusters.setdefault(find(h), []).append(h)

    out = []
    for root, members in sorted(clusters.items(), key=lambda x: -len(x[1])):
        if len(members) < 2:
            continue
        common = set.intersection(*[fps[m] for m in members])
        shared = [t for t in common if t.startswith(("gen:", "url:", "js:", "css:", "xpb:"))]
        out.append({"size": len(members), "shared": shared[:6], "members": members})
    json.dump(out, open("cms_clusters.json", "w"), ensure_ascii=False, indent=1)
    singles = sum(1 for m in clusters.values() if len(m) == 1)
    print(f"\nMULTI-shluků: {len(out)} | samostatných: {singles}")
    for c in out:
        print(f"\n[{c['size']}] sdílí: {c['shared']}")
        print("   " + ", ".join(c["members"][:8]) + (" …" if c["size"] > 8 else ""))
    print("\nCMS_SIM_DONE")


if __name__ == "__main__":
    main()
