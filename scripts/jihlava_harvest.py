#!/usr/bin/env python3
"""Jihlava (vismo) harvester — dotační programy statutárního města Jihlava.

ZDROJ: jihlava.cz, vismo CMS. Sekce "Dotační programy" (hub ms-103473) odkazuje na
8 tematických podsložek (ds-): Kultura, Sport, Sociální, Zdravé město, Památková péče,
Vzdělávání, Prevence kriminality, Volný čas. Program je publikován dvěma způsoby:
  (A) jako vismo článek (d-NNNN) s prozaickým detailem → parse popis/termín/alokace (rich),
  (B) jen jako stažitelný DOCX/DOC (File.ashx) když podsložka nemá d- článek (Sociální,
      Prevence kriminality, část Památkové) → program zaznamenán s null termíny.

Filtruje balast: awards ("přehled podpořených", "seznam podpořených", "vypořádání"),
formuláře žádostí, prezentace, vzory smluv/vyúčtování, obecné zásady.

curl (vismo neblokuje s UA), žádný Playwright nepotřeba. Lossless: ukládá parsed pole +
_text detailu. Status NEpočítá — dopočítá ingest_kraj z termínů (TODAY).

Usage: python3 scripts/jihlava_harvest.py --out data/h_mesto_jihlava.json
"""
import argparse, json, re, ssl, sys, time, html, urllib.request
from urllib.parse import urljoin

BASE = "https://www.jihlava.cz"
HUB = "/dotacni-programy/ms-103473/p1=103473"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
import http_util   # jednotná TLS politika (audit #7/#32)

# balast v .dok listingu — co NENÍ dotační program (awards, formuláře, vzory, zásady, prezentace)
SKIP = re.compile(
    r"přehled podpoř|seznam podpoř|podpoř.*projekt|vypořádán|finanční vypořádán"
    r"|prezentace|vzor (?:smlouvy|vyúčtován)|vyúčtován|podstatné náležitost"
    r"|formulář|příloha (?:č|formulář)|žádost o (?:zařazení|finanční dotaci|poskytnutí|mimořádný)"
    r"|obecné zásady|mechanismus přidělován|pravidla pro poskytnut|kontakty na",
    re.I,
)
# File.ashx dokument, který JE program (jen tehdy ho bereme jako B-typ)
ASHX_PROGRAM = re.compile(r"\bdotačn[íi].*program|\bprogram.*na podporu|aktualizace dotačn", re.I)


def fetch(url, tries=3, timeout=30):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with http_util.urlopen(req, timeout=timeout) as r:
                enc = r.headers.get_content_charset() or "utf-8"
                return r.read().decode(enc, "replace")
        except Exception as e:  # noqa: BLE001
            last = e; time.sleep(1.0 * (i + 1))
    print(f"  warn fetch {url[:70]}: {str(last)[:60]}", file=sys.stderr)
    return None


def content(h):
    m = re.search(r'id="hlobsah"(.*?)(?:id="pata"|<footer)', h, re.S)
    return m.group(1) if m else h


def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(t))).strip()


def detext(ca):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", ca, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", html.unescape(h))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", h)).strip()


def _iso(s):
    m = re.match(r"\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s or "")
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def parse_term(text):
    """Vrať (open_from, deadline) z věty o podávání žádostí. Termín doručení vyúčtování
    NENÍ deadline (pitfall) — kotvíme na 'Žádosti lze podávat'."""
    seg = ""
    m = re.search(r"Žádost(?:i)? (?:lze podávat|je možné podávat|přijím\w+)(.{0,120})", text, re.I | re.S)
    if m:
        seg = m.group(1)
    if not seg:
        return None, None
    # "od DD.M.YYYY do DD.M.YYYY" nebo jen "do DD.M.YYYY"
    mr = re.search(r"od\s+(\d{1,2}\.\s*\d{1,2}\.\s*\d{4}).{0,15}?do\s+(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})", seg, re.S)
    if mr:
        return _iso(mr.group(1)), _iso(mr.group(2))
    md = re.search(r"do\s+(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})", seg)
    return None, (_iso(md.group(1)) if md else None)


def parse_amount(text):
    """max výše dotace na žadatele: 'do maximální výše N Kč' / 'max. N Kč'."""
    m = re.search(r"(?:do (?:maximální )?výše|max\.?(?:imální)?(?: výše)?)\s*([\d  .\xa0]+)\s*Kč", text, re.I)
    if m:
        d = re.sub(r"[^\d]", "", m.group(1))
        return int(d) if d else None
    return None


def parse_popis(text):
    """První věcný odstavec detailu (focus_area). Bere text od začátku do 'Odkazy'/'Žádosti lze'."""
    body = text
    for cut in ("\n Odkazy", "Odkazy\n", "Žádosti lze podávat", "Zodpovídá:"):
        i = body.find(cut)
        if i > 80:
            body = body[:i]
    # odstraň úvodní nadpis + 'Zpět na:'
    body = re.sub(r"^[>\s]*", "", body)
    body = re.sub(r"Zpět na:[^\n]*", "", body)
    body = re.sub(r"\s+", " ", body).strip(" -–\n")
    return body[:1500] or None


def dok_links(ca):
    """(href, title, date_str) z .dok > ul > li bloků."""
    out = []
    for blk in re.findall(r'class="dok"[^>]*>(.*?)</ul>', ca, re.S):
        for li in re.findall(r"<li[^>]*>(.*?)</li>", blk, re.S):
            a = re.search(r'<a\b[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', li, re.S)
            if not a:
                continue
            d = re.search(r"\((\d{1,2}\.\s*\d{1,2}\.\s*\d{4})\)", li)
            out.append((html.unescape(a.group(1)), clean(a.group(2)),
                        d.group(1).replace(" ", "") if d else None))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_jihlava.json")
    a = ap.parse_args()

    progs, seen_urls = [], set()

    def save():
        out = {"source": "jihlava.cz", "kraj": "Kraj Vysočina", "obec": "Jihlava",
               "uroven": "obec", "platform": "jihlava_vismo", "programs": progs}
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 1) hub → tematické ds- podsložky (z obsahu, ne z globální nav)
    hub = fetch(BASE + HUB)
    if not hub:
        print(json.dumps({"MARKER": "JIHLAVA", "ERROR": "hub fetch failed"}, ensure_ascii=False)); return
    ca = content(hub)
    body = ca[:ca.find("Sdílet na Facebooku")] if "Sdílet na Facebooku" in ca else ca
    themes = []
    for href, txt in re.findall(r'<a\b[^>]*?href="([^"]*ds-\d+[^"]*)"[^>]*>(.*?)</a>', body, re.S):
        full = urljoin(BASE + "/", html.unescape(href))
        if full not in [t[0] for t in themes]:
            themes.append((full, clean(txt)))
    print(f"hub → {len(themes)} tematických podsložek", file=sys.stderr)

    # 2) každá podsložka → d- programy (rich) + File.ashx programy (B-typ)
    for turl, tname in themes:
        th = fetch(turl)
        if not th:
            continue
        tca = content(th)
        for href, title, dstr in dok_links(tca):
            full = urljoin(turl, href)
            is_d = bool(re.search(r"/d-\d+", full))
            is_ashx = "File.ashx" in full
            if not (is_d or is_ashx):
                continue
            if SKIP.search(title):
                continue
            if full in seen_urls:
                continue

            if is_d:
                dh = fetch(full)
                if not dh:
                    continue
                dt = detext(content(dh))
                of, dl = parse_term(dt)
                rec = {
                    "nazev": title, "open_from": of, "deadline": dl, "status": None,
                    "alokace_czk": None, "max_czk": parse_amount(dt),
                    "popis": parse_popis(dt), "eligible": None, "kod": None,
                    "url": full.split("?")[0],
                    "_oblast": tname, "_listed_date": dstr,
                    "_text": dt[:3500],
                }
            else:  # File.ashx — jen pokud název vypadá jako program (ne formulář/awards)
                if not ASHX_PROGRAM.search(title):
                    continue
                rec = {
                    "nazev": title, "open_from": None, "deadline": None, "status": None,
                    "alokace_czk": None, "max_czk": None, "popis": None, "eligible": None,
                    "kod": None, "url": turl.split("?")[0],
                    "_oblast": tname, "_listed_date": dstr, "_doc_url": full, "_text": "",
                }
            seen_urls.add(full)
            progs.append(rec)
            save()  # průběžné ukládání
            print(f"  + [{tname}] {title[:60]}", file=sys.stderr)

    save()
    print(json.dumps({"MARKER": "JIHLAVA", "themes": len(themes), "programs": len(progs),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
