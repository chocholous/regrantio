#!/usr/bin/env python3
"""vismo_modern — vrstva 1: DISCOVERY + LISTING (bez stahování příloh).

Vismo "modern" (webhouse minbase 4.x) má ÚPLNĚ jiný markup než vismo_classic:
  - slug URL (žádné /ds-NNN /ms-NNN /d-NNN), interní id jen v data-object-id
  - podsložky  = <ul class="tiles__list"> … <a class="tile__link" href="/slug">
  - dokumenty  = <ul class="list documents"> … <article class="document">
                 <a class="document__link" href="/slug"> + <time class="document__date" datetime="YYYY-MM-DD">
  - obsah      = <article class="article"> → article__text (text-component)
  - přílohy    = <ul class="list global-attachments"> → a.global-attachment__link href="/file/NNNN"
  - ŽÁDNÉ "Úřední deska od-do" / "Vytvořeno / změněno" metadata na stránce

Postup per web: najdi dotační sekci (homepage odkaz dota[cč]/grant → fallback
sitemap.xml), pak BFS přes strukturální odkazy (tiles + document-listy) v <main>
dotačního podstromu; prozaické odkazy v textu jen dotačně relevantní (DOC_RELEVANT).
Stránka = záznam listingu, když nese obsah (text ≥ prefilter_empty_text_max NEBO ≥1
příloha) — čisté tile-rozcestníky se nelistují. Bez stahování příloh (vrstva 2 =
vismo_modern_detail.py). Výstup: data/vismo_modern_listing.jsonl (kontrakt jako
vismo_listing.jsonl: foundation_id/title/url/date/section).

Bounds: depth = safety.vismo_bfs_depth_ceiling, pages = safety.runaway_page_ceiling
(obojí limits.json; dosažení se loguje ⚠ = bug, ne coverage cap).

Usage:  python3 scripts/vismo_modern.py --base https://www.teplice.cz
        python3 scripts/vismo_modern.py --base https://www.kr-ustecky.cz --start https://www.kr-ustecky.cz/dotace
"""
import argparse, json, re, ssl, sys, time, html, os, urllib.request
from urllib.parse import urljoin, urlparse, unquote
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limits import L

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
# POZOR: 'dotac' nematchuje 'dotační' (č≠c)! → dota[cč] chytí dotace i dotační
DOTACE_RE = re.compile(r"dota[cč]|grant|příspěv|prispev|fond", re.I)   # DISCOVERY (široké)
# prozaické odkazy v textu: jen úzce dotačně relevantní text (NE 'příspěv' — chytá
# příspěvkové organizace; NE roky — chytají všechno). Strukturální děti se neřídí textem.
DOC_RELEVANT = re.compile(r"dota[cč]|grant|výzv|vyzv|program|fond|stipend", re.I)
NAV_JUNK = re.compile(r"^(Hlavní|Vypnout|Přeskočit|Klikací rozpočet|Mapa webu|Úvodní strana)", re.I)

# CLASSIC fallback (hybridy v labelu vismo_modern, např. novabela.cz: markup classic):
# stránka bez <main> → obsah id="hlobsah"; podsložky ds-/ms- gateované RECURSE_RE textem
# (hlobsah obsahuje i nav!), d-NNNN + File.ashx jen dotačně relevantní.
RECURSE_RE = re.compile(r"dota[cč]|grant|výzv|vyzv", re.I)
SUBFOLDER_A = re.compile(r'<a\b[^>]*?\bhref="([^"]*/(?:ds|ms)-\d+[^"]*)"[^>]*>(.*?)</a>', re.S)
ASHX_A = re.compile(r'<a\b[^>]*?\bhref="([^"]*File\.ashx[^"]*)"[^>]*>(.*?)</a>', re.S | re.I)

TILE_A = re.compile(r'<a\b[^>]*?\bhref="([^"]+)"[^>]*\bclass="[^"]*tile__link[^"]*"[^>]*>(.*?)</a>', re.S)
DOCLI_A = re.compile(r'<a\b[^>]*?\bclass="[^"]*document__link[^"]*"[^>]*?\bhref="([^"]+)"[^>]*>(.*?)</a>'
                     r'(?:\s*<time[^>]*class="[^"]*document__date[^"]*"[^>]*datetime="(\d{4}-\d{2}-\d{2})")?', re.S)
TEXT_BLOCK = re.compile(r'class="text-component"[^>]*>(.*?)</div>', re.S)
GATT = re.compile(r'class="global-attachment__link"')
A_ANY = re.compile(r'<a\b[^>]*?\bhref="([^"]+)"[^>]*>(.*?)</a>', re.S)
PAGER = re.compile(r'rel="next"|class="[^"]*pag(?:er|ination)[^"]*"|[?&](?:page|stranka)=', re.I)


def fetch(url, tries=3, timeout=None):
    timeout = timeout or L("http.default_timeout_s")
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace"), r.geturl()
        except Exception as e:  # noqa: BLE001
            last = e; time.sleep(1.0 * (i + 1))
    return None, str(last)


def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(t or ""))).replace("\xa0", " ").strip()


def main_area(h):
    """→ (obsah, is_modern). Bez <main> = classic markup → hlobsah fallback."""
    m = re.search(r"<main\b[^>]*>(.*?)</main>", h, re.S)
    if m:
        return m.group(1), True
    m = re.search(r'id="hlobsah"(.*?)(?:id="pata"|<footer)', h, re.S)
    return (m.group(1) if m else h), False


def iso_to_cz(d):
    """'2026-05-13' → '13.5.2026' (kontrakt classic listingu)."""
    if not d:
        return None
    y, m, dd = d.split("-")
    return f"{int(dd)}.{int(m)}.{y}"


def find_starts(base):
    """Vrať [(url, how)] dotačních startů: homepage odkazy → fallback sitemap."""
    home, final = fetch(base)
    starts, seen = [], set()
    if home:
        host = urlparse(final or base).netloc
        for href, txt in A_ANY.findall(home):
            t = clean(txt)
            if not (DOTACE_RE.search(t) or DOTACE_RE.search(unquote(href))):
                continue
            full = urljoin((final or base) + "/", html.unescape(href)).split("#")[0]
            if urlparse(full).netloc != host or full in seen:
                continue
            seen.add(full)
            starts.append((full, "homepage"))
    if starts:
        return starts
    # fallback: sitemap.xml — sekce-like (nejkratší) dotační URL
    s, _ = fetch((final or base).rstrip("/") + "/sitemap.xml")
    if s:
        locs = re.findall(r"<loc>([^<]+)</loc>", s)
        cands = sorted({u for u in locs if DOTACE_RE.search(unquote(u))}, key=len)
        for u in cands:
            starts.append((u.split("#")[0], "sitemap"))
    return starts


def harvest_listing(base, starts):
    depth_ceiling = L("safety.vismo_bfs_depth_ceiling")
    page_ceiling = L("safety.runaway_page_ceiling")
    min_text = L("acquisition.prefilter_empty_text_max")
    _, final = fetch(base)
    host = urlparse(final or base).netloc
    fid = host.replace("www.", "")

    def same_host(u):
        return urlparse(u).netloc.replace("www.", "") == fid
    seen_pages, rows, row_urls = set(), [], {}
    q = deque((u, "", 0) for u, _ in starts)
    pages = 0
    warns = []

    def norm(u):
        return u.split("#")[0].rstrip("/")

    def add_row(url, title, date=None, section=None):
        url = norm(url)
        t = clean(title)
        if not t or NAV_JUNK.match(t) or not same_host(url):
            return
        if url in row_urls:                     # doplň date/section, nedupluj
            r = row_urls[url]
            r["date"] = r["date"] or date
            r["section"] = r["section"] or section
            return
        r = {"foundation_id": fid, "title": t, "url": url, "date": date, "section": section}
        row_urls[url] = r
        rows.append(r)

    while q:
        url, section, depth = q.popleft()
        url = norm(url)
        if url in seen_pages:
            continue
        seen_pages.add(url)
        if pages >= page_ceiling:
            warns.append(f"⚠ {fid}: runaway_page_ceiling {page_ceiling} dosažen — prošetři (bug, ne cap)")
            break
        h, fin = fetch(url)
        if not h:
            continue
        pages += 1
        ma, is_modern = main_area(h)
        hm = re.search(r"<h1[^>]*>(.*?)</h1>", ma, re.S) or re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S) \
            or re.search(r"<title[^>]*>(.*?)</title>", h, re.S)
        page_title = (clean(hm.group(1)) if hm else "") or section
        if PAGER.search(ma):
            warns.append(f"⚠ {fid}: paginace na {url} — vismo_modern.py paginaci nečte, ověř ručně")

        if not is_modern:
            # CLASSIC markup: stránka = row, když má dotačně relevantní File.ashx / je d-NNNN
            ashx = [(hr, clean(tx)) for hr, tx in ASHX_A.findall(ma)
                    if DOC_RELEVANT.search(clean(tx)) or re.search(r"žádost|zadost", clean(tx), re.I)]
            if ashx or re.search(r"/d-\d+", url):
                add_row(url, page_title or section, section=section or page_title)
            if depth < depth_ceiling:
                for href, txt in SUBFOLDER_A.findall(ma):
                    t = clean(txt)
                    if not RECURSE_RE.search(t):
                        continue
                    full = norm(urljoin(url, html.unescape(href)))
                    if same_host(full) and full not in seen_pages:
                        q.append((full, t, depth + 1))
                for href, txt in A_ANY.findall(ma):
                    if re.search(r"/d-\d+", href) and DOC_RELEVANT.search(clean(txt)):
                        full = norm(urljoin(url, html.unescape(href)))
                        if same_host(full):
                            add_row(full, txt, section=page_title)
            elif depth >= depth_ceiling:
                warns.append(f"⚠ {fid}: depth_ceiling {depth_ceiling} na {url} — prošetři (bug, ne cap)")
            continue

        # obsahová stránka? (text-component s textem ≥ min_text NEBO přílohy)
        text_len = sum(len(clean(b)) for b in TEXT_BLOCK.findall(ma))
        n_att = len(GATT.findall(ma))
        if text_len >= min_text or n_att:
            add_row(url, page_title, section=section or page_title)

        if depth >= depth_ceiling:
            warns.append(f"⚠ {fid}: depth_ceiling {depth_ceiling} na {url} — prošetři (bug, ne cap)")
            continue

        # strukturální děti: tiles (podsložky) + document-listy (dokumenty s datem)
        for href, txt in TILE_A.findall(ma):
            t = clean(txt)
            full = norm(urljoin(url, html.unescape(href)))
            if same_host(full) and full not in seen_pages and not NAV_JUNK.match(t):
                q.append((full, page_title, depth + 1))
        for href, txt, dt in DOCLI_A.findall(ma):
            full = norm(urljoin(url, html.unescape(href)))
            if not same_host(full):
                continue
            add_row(full, txt, date=iso_to_cz(dt), section=page_title)
            if full not in seen_pages:
                q.append((full, page_title, depth + 1))
        # prozaické odkazy v text-component — jen dotačně relevantní text
        for block in TEXT_BLOCK.findall(ma):
            for href, txt in A_ANY.findall(block):
                t = clean(txt)
                if not DOC_RELEVANT.search(t):
                    continue
                full = norm(urljoin(url, html.unescape(href)))
                if href.startswith("/file/") or not same_host(full):
                    continue
                if full not in seen_pages:
                    q.append((full, page_title, depth + 1))
    for w in warns:
        print(w, file=sys.stderr)
    return rows, pages, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--start", action="append", help="známé dotační URL (opakovatelné; jinak discovery)")
    ap.add_argument("--out", default="data/vismo_modern_listing.jsonl")
    args = ap.parse_args()
    if args.start:
        starts = [(s, "known") for s in args.start]
    else:
        starts = find_starts(args.base)
    if not starts:
        print(json.dumps({"MARKER": "VISMO_MODERN", "base": args.base, "discovery": "FAIL", "docs": 0},
                         ensure_ascii=False))
        return
    rows, pages, warns = harvest_listing(args.base, starts)
    with open(args.out, "a", encoding="utf-8") as o:
        for r in rows:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"MARKER": "VISMO_MODERN", "base": args.base,
                      "starts": [u for u, _ in starts][:8], "how": starts[0][1],
                      "pages_crawled": pages, "docs": len(rows), "warns": len(warns)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
