#!/usr/bin/env python3
"""vismo_classic — vrstva 1: DISCOVERY + LISTING (bez detailů/příloh).

Pro každý web: najdi dotační sekci (homepage odkaz 'dotac'/'grant' → fallback
sitemap.xml), pak BFS přes ds-/ms- podsložky v dotačním podstromu a sesbírej
dokumenty (d-NNNN) z `.dok > ul.ui > li` = {title, url, date, section}.
Bez stahování detailů/příloh (to je vrstva 2). Výstup data/vismo_listing.jsonl.
"""
import argparse, json, re, ssl, sys, time, html, urllib.request
from urllib.parse import urljoin, urlparse
from collections import deque

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util   # jednotná TLS politika (audit #7/#32)
from limits import L
# POZOR: 'dotac' nematchuje 'dotační' (č≠c)! → dota[cč] chytí dotace i dotační
DOTACE_RE = re.compile(r"dota[cč]|grant|příspěv|prispev|fond", re.I)   # pro DISCOVERY (široké)
RECURSE_RE = re.compile(r"dota[cč]|grant|výzv|vyzv", re.I)             # pro REKURZI (úzké — ne 'příspěvkové org')
# dokumentový listing = <div class="dok">…<ul class="ui">…</ul> (NE levé nav menu, to je taky ul.ui!)
DOK_BLOCK = re.compile(r'class="dok"[^>]*>(.*?)</ul>', re.S)
LI = re.compile(r'<li[^>]*>(.*?)</li>', re.S)
LI_A = re.compile(r'<a\b[^>]*?\bhref="([^"]+)"[^>]*>(.*?)</a>', re.S)
SUBFOLDER_A = re.compile(r'<a\b[^>]*?\bhref="([^"]*/(?:ds|ms)-\d+[^"]*)"[^>]*>(.*?)</a>', re.S)
DATE_RE = re.compile(r'\((\d{1,2}\.\s*\d{1,2}\.\s*\d{4})\)')


def fetch(url, tries=3, timeout=15):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with http_util.urlopen(req, timeout=timeout) as r:
                return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace"), r.geturl()
        except Exception as e:  # noqa: BLE001
            last = e; time.sleep(1.0 * (i + 1))
    return None, str(last)


def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(t))).strip()


def content_area(h):
    m = re.search(r'id="hlobsah"(.*?)(?:id="pata"|<footer)', h, re.S)
    return m.group(1) if m else h


def find_dotace(base):
    """Vrať URL dotační sekce: známá / homepage odkaz / sitemap fallback."""
    home, _ = fetch(base)
    if home:
        anchors = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>', home)
        # 1) preferuj kanonickou vismo sekci (ds/ms/d-NNNN) s dotačním textem
        for href, txt in anchors:
            if DOTACE_RE.search(txt) and re.search(r"/(ds|ms|d)-\d+", href):
                return urljoin(base + "/", href), "homepage"
        # 2) fallback: sluggovaný hub (BEZ ds/ms/d čísla) — některé vismo weby migrovaly
        #    na slug URL (např. letnany /dotace-granty-1). Ber jen když dotační je
        #    text I href (úzké → nevybere náhodný odkaz se slovem „dotace" v textu).
        for href, txt in anchors:
            if DOTACE_RE.search(txt) and DOTACE_RE.search(href):
                return urljoin(base + "/", href), "homepage-slug"
    # fallback: sitemap.xml
    for sm in ("/sitemap.xml", "/mapa-webu", "/mapa-stranek"):
        s, _ = fetch(base + sm)
        if s:
            locs = re.findall(r"<loc>([^<]+)</loc>", s) or re.findall(r'href="([^"]+)"', s)
            cands = [u for u in locs if DOTACE_RE.search(u) and re.search(r"/(ds|ms)-\d+", u)]
            if cands:
                cands.sort(key=len)
                return urljoin(base + "/", cands[0]), "sitemap"
    return None, None


NAV_JUNK = re.compile(r"^(Hlavní|Vypnout|Přeskočit|Klikací rozpočet|Realizované projekty)", re.I)
# pro d- dokumenty MIMO .dok blok (obsah obsahuje i nav) — ber jen dotačně relevantní názvy
DOC_RELEVANT = re.compile(r"dota[cč]|grant|výzv|vyzv|příspěv|prispev|program|fond|stipend|\b20\d\d\b", re.I)
# slug-režim (vismo migrované na slug URL, např. letnany): dotačně relevantní CESTA bez d-čísla
SLUG_DOC_HREF = re.compile(r"dota[cč]|grant|vyzv|výzv|stipend", re.I)


def harvest_listing(base, start_url, max_pages=None, max_depth=2, slug_mode=False):
    """BFS přes ds-/ms- dotační podsložky (do max_depth), sesbírej d- dokumenty
    z .dok listingu I z obsahu (#hlobsah) — některé weby nelistují přes .dok.
    slug_mode=True: web migroval na slug URL (bez d-čísla) → ber i dotačně-sluggované
    odkazy (zapíná se jen pro discovery 'homepage-slug', aby se neměnily d- weby)."""
    host = urlparse(base).netloc
    seen_pages, seen_docs = set(), {}
    docs = []
    if max_pages is None:                        # audit #16: strop z limits.json (safety), ne natvrdo 40
        max_pages = L("safety.runaway_page_ceiling")
    q = deque([(start_url, "", 0)])
    pages = 0
    while q and pages < max_pages:
        url, section, depth = q.popleft()
        if url in seen_pages:
            continue
        seen_pages.add(url)
        h, _ = fetch(url)
        if not h:
            continue
        pages += 1
        ca = content_area(h)
        hm = re.search(r"<h1[^>]*>(.*?)</h1>", ca, re.S)
        sec_title = clean(hm.group(1)) if hm else section

        def add_doc(full, title, li_html, allow_slug=False):
            t = clean(title)
            if not t or NAV_JUNK.match(t) or full in seen_docs:
                return
            if urlparse(full).netloc != host:
                return
            if not re.search(r"/d-\d+", full) and not (allow_slug and SLUG_DOC_HREF.search(urlparse(full).path)):
                return
            dm = DATE_RE.search(li_html)
            seen_docs[full] = 1
            docs.append({"foundation_id": host.replace("www.", ""), "title": t,
                         "url": full, "date": dm.group(1).replace(" ", "") if dm else None,
                         "section": sec_title})

        # 1) dokumenty z .dok listingu (s daty)
        for ul in DOK_BLOCK.findall(ca):
            for li in LI.findall(ul):
                am = LI_A.search(li)
                if am:
                    add_doc(urljoin(url, html.unescape(am.group(1))), am.group(2), li)
        # 1b) dokumenty (d-) kdekoli v obsahu #hlobsah (weby bez .dok listingu: krnov/melnik…)
        #     POZOR obsah obsahuje i nav d- odkazy → ber jen dotačně relevantní názvy
        for href, txt in LI_A.findall(ca):
            if re.search(r"/d-\d+", href) and DOC_RELEVANT.search(clean(txt)):
                add_doc(urljoin(url, html.unescape(href)), txt, "")
        # 1c) SLUG režim (jen homepage-slug discovery): dotace dokumenty bez d-čísla —
        #     ber odkazy s dotačním SLUGEM a dotačně relevantním textem (results/smlouvy
        #     se mohou přibrat → odfiltruje je vrstva 2 klasifikace, stejně jako u d- webů).
        if slug_mode:
            for href, txt in LI_A.findall(ca):
                if SLUG_DOC_HREF.search(href) and DOC_RELEVANT.search(clean(txt)):
                    add_doc(urljoin(url, html.unescape(href)), txt, "", allow_slug=True)
        # 2) podsložky (ds-/ms-) k rekurzi — do max_depth, scan CELÉ stránky (vč. submenu),
        #    jen úzce dotačně relevantní text (vyřadí globální nav i 'příspěvkové organizace')
        if depth >= max_depth:
            continue
        for href, txt in SUBFOLDER_A.findall(h):
            t = clean(txt)
            if not RECURSE_RE.search(t):
                continue
            full = urljoin(url, html.unescape(href))
            if urlparse(full).netloc == host and full not in seen_pages:
                q.append((full, t, depth + 1))
    if pages >= max_pages:                       # audit #16: runaway strop dosažen → NAHLAS (bug, ne tiché uříznutí)
        print(f"⚠ vismo: dosažen strop {max_pages} stran u {base} — prošetři (NEzvyšuj naslepo)", file=sys.stderr)
    return docs, pages, len(seen_pages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--start")  # známá dotační URL (jinak discovery)
    ap.add_argument("--out", default="data/vismo_listing.jsonl")
    args = ap.parse_args()
    if args.start:
        start, how = args.start, "known"
    else:
        start, how = find_dotace(args.base)
    if not start:
        print(json.dumps({"MARKER": "VISMO", "base": args.base, "discovery": "FAIL", "docs": 0}, ensure_ascii=False))
        return
    docs, pages, npages = harvest_listing(args.base, start, slug_mode=(how == "homepage-slug"))
    with open(args.out, "a", encoding="utf-8") as o:
        for d in docs:
            o.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(json.dumps({"MARKER": "VISMO", "base": args.base, "start": start, "how": how,
                      "pages_crawled": pages, "docs": len(docs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
