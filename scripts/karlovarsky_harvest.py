#!/usr/bin/env python3
"""Karlovarský kraj harvester — dotační programy z www.kr-karlovarsky.cz/dotace.

POZOR — WAF: www.kr-karlovarsky.cz běží za WEDOS Global Protection + F5 BIG-IP.
Každá cesta vrací HTTP 301 self-redirect na sebe sama (prázdné tělo, rotující cookie
TS01de5df3) → klasická redirect-loop „challenge". Empiricky (2026-06-05) NEPROŠLO:
curl, curl_cffi (Chrome JA3/JA4 impersonate), Playwright headless Chromium, Playwright
headed+stealth, ani Playwright channel="chrome" (reálný systémový Chrome) — všechny
dostanou ERR_TOO_MANY_REDIRECTS. Blok není JS/TLS-fingerprint (challenge HTML se NIKDY
nepošle), je IP-reputační (datacentrum/serverová IP). Z residenční IP reálný prohlížeč
projde → proto je Playwright metoda ZACHOVÁNA jako primární (poběží, až bude síť OK).

Dvě metody (auto-detekce, --method volí ručně):
  1. playwright : projde WAF (jen z residenční IP) → render listingu /dotace + detailů.
     Listing /dotace = dlaždice programů (odkaz /dotace/<slug>, název, stav příjmu žádostí).
     Detail = próza se štítky termínů příjmu žádostí (od–do) → open_from/deadline.
  2. edesky     : FALLBACK z edesky.cz/desky/76 (HTML mirror úřední desky, HTTP 200).
     Úřední deska kraje obsahuje SPRÁVNÍ akty (vyhlášky, záměry), NE vyhlášené dotační
     programy → reálně 0 použitelných programů. Ponecháno dle zadání jako poslední záchrana.

Status NEPOČÍTÁ harvester — dopočítá ingest_kraj.py z open_from/deadline (CLAUDE.md pravidlo 1).
Nezjištěná pole = null. Žádné domýšlení termínů.

Usage:
  python3 scripts/karlovarsky_harvest.py                      # auto: playwright→edesky
  python3 scripts/karlovarsky_harvest.py --method playwright
  python3 scripts/karlovarsky_harvest.py --method edesky
"""
import argparse, json, re, sys, urllib.parse, urllib.request

HOST = "kr-karlovarsky.cz"
KRAJ = "Karlovarský kraj"
BASE = "https://www.kr-karlovarsky.cz"
LISTING = BASE + "/dotace"
EDESKY = "https://edesky.cz/dokumenty?zdroj=76"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# titul, který na úřední desce vypadá jako dotační PROGRAM (ne už uzavřená individuální smlouva)
EDESKY_GRANT = re.compile(
    r"dota[čc]n[íi]\s+program|program\s+na\s+podporu|vyhlá[šs]en[íi]\s+(?:dota|program)"
    r"|výzv[ay]\s+k\s+(?:podán[íi]|předklád)|grantov", re.I)
DATE_RE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")


def _iso(d, m, y):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " ").replace("&quot;", '"')
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", h)).strip()


# ---------------------------------------------------------------- metoda 1: Playwright

def _new_page(pw):
    b = pw.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(locale="cs-CZ", user_agent=UA, viewport={"width": 1366, "height": 900},
                        extra_http_headers={"Accept-Language": "cs-CZ,cs;q=0.9"})
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    return b, ctx, ctx.new_page()


def _render(page, url, settle_ms=6000):
    """goto + nech proběhnout WAF challenge. Vrací (ok, html). ok=False při redirect-loopu."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except Exception as e:
        if "ERR_TOO_MANY_REDIRECTS" in str(e):
            return False, ""
        # jiná chyba — zkus přesto přečíst, co je v DOM
    page.wait_for_timeout(settle_ms)
    if page.url.startswith("chrome-error"):
        return False, ""
    return True, page.content()


def harvest_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("WARN playwright nenainstalován", file=sys.stderr)
        return None
    with sync_playwright() as pw:
        b, ctx, page = _new_page(pw)
        try:
            ok, html = _render(page, LISTING)
            if not ok:
                print("WAF: /dotace redirect-loop (Playwright neprošel)", file=sys.stderr)
                return None
            # dlaždice programů: <a href="/dotace/<slug>"> v listingu
            progs, seen = [], set()
            for href, label in re.findall(
                    r'href="(/dotace/[a-z0-9][a-z0-9\-/]+)"[^>]*>(.*?)</a>', html, re.S):
                url = BASE + href.split("?")[0].split("#")[0]
                if url in seen or href.rstrip("/") == "/dotace":
                    continue
                seen.add(url)
                nazev = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", label)).strip()
                if not nazev or len(nazev) < 4:
                    continue
                progs.append({"nazev": nazev, "url": url})
            print(f"listing: {len(progs)} programů", file=sys.stderr)
            # detail každého programu → termíny příjmu žádostí
            for p in progs:
                ok, dh = _render(page, p["url"], settle_ms=3500)
                of = dl = None
                popis = None
                if ok and dh:
                    txt = detext(dh)
                    # interval příjmu žádostí: "od DD.MM.YYYY ... do DD.MM.YYYY"
                    win = re.search(
                        r"(?:příjem|podán[íi]|termín)[^.]{0,80}?"
                        r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})[^.]{0,40}?(?:do|–|-)\s*"
                        r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})", txt, re.I)
                    if win:
                        m1 = DATE_RE.search(win.group(1)); m2 = DATE_RE.search(win.group(2))
                        if m1: of = _iso(*m1.groups())
                        if m2: dl = _iso(*m2.groups())
                    p["_text"] = txt[:4000]
                p.update({"open_from": of, "deadline": dl, "status": None, "alokace_czk": None,
                          "max_czk": None, "popis": popis, "eligible": None, "kod": None})
            return _wrap(progs, "karlovarsky_html")
        finally:
            b.close()


# ---------------------------------------------------------------- metoda 2: edesky fallback

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def harvest_edesky(pages=10):
    progs, seen = [], set()
    for pg in range(1, pages + 1):
        try:
            html = fetch(f"{EDESKY}&page={pg}")
        except Exception as e:
            print(f"  edesky page {pg}: {str(e)[:60]}", file=sys.stderr); continue
        items = re.findall(
            r'href="(/dokument/\d+[^"]*)"[^>]*>\s*<span itemprop=.name.>\s*(.+?)\s*</span>',
            html, re.S)
        if not items:
            break
        for href, name in items:
            nazev = re.sub(r"\s+", " ", name).strip()
            if not EDESKY_GRANT.search(nazev):
                continue
            url = "https://edesky.cz" + urllib.parse.unquote(href)
            if url in seen:
                continue
            seen.add(url)
            progs.append({"nazev": nazev, "open_from": None, "deadline": None, "status": None,
                          "alokace_czk": None, "max_czk": None, "popis": None,
                          "eligible": None, "kod": None, "url": url})
    print(f"edesky: {len(progs)} dotačních položek z úřední desky", file=sys.stderr)
    return _wrap(progs, "karlovarsky_edesky")


# ----------------------------------------------------------------

def _wrap(progs, platform):
    return {"source": HOST, "kraj": KRAJ, "platform": platform, "programs": progs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_karlovarsky.json")
    ap.add_argument("--method", choices=["auto", "playwright", "edesky"], default="auto")
    a = ap.parse_args()

    out = None
    if a.method in ("auto", "playwright"):
        out = harvest_playwright()
        if out and not out["programs"]:
            out = None
    if out is None and a.method in ("auto", "edesky"):
        out = harvest_edesky()

    if out is None:
        print(json.dumps({"MARKER": "KARLOVARSKY_HARVEST", "status": "FAILED",
                          "reason": "WAF neprošel (Playwright) a žádná fallback metoda nedala data"},
                         ensure_ascii=False))
        sys.exit(2)

    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "KARLOVARSKY_HARVEST", "method": out["platform"],
                      "programs": len(out["programs"]), "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
