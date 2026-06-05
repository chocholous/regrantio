#!/usr/bin/env python3
"""Teplice harvester — dotační programy statutárního města Teplice (Vismo, server-rendered HTML).

Zdroj: teplice.cz (Vismo). Kanonické programy = položky menu „Dotace" na titulní stránce
(/ → odkazy /dotace-*). Jsou to kurátorované landing pages aktuálních dotačních programů
(NE awards „Projekty z…", NE login). Listing-of-programs odvozujeme z titulní navigace, ne
z paginovaného hubu /dotacni-programy-* (ten míchá programy + Pravidla + Smlouvy + Žádosti).

Detail každé landing page je próza: „Lhůta pro podání žádosti: od D. M. do D. M. [RRRR]"
+ občas alokace („uvolněno N Kč"). Status dopočítá ingest z termínů.

Termíny: ROK je v textu jen někdy explicitní (jinde „aktuálního roku"). open_from/deadline
emitujeme JEN s explicitním 4místným rokem; jinak null (raw lhůta zůstává v popisu) — žádné
hádání roku (viz pravidlo o hardcoded hodnotách).

Lossless: ukládá parsed pole + plný text detailu (_text). Ukládá průběžně.

Vismo někdy blokuje fetchery → fallback Playwright (--render).

Usage:
  python3 scripts/teplice_harvest.py --out data/h_mesto_teplice.json
  python3 scripts/teplice_harvest.py --out data/h_mesto_teplice.json --render
"""
import argparse, json, re, sys, time
import html as H
import urllib.request

BASE = "https://www.teplice.cz"
HOME = BASE + "/"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# kanonický listing = menu „Dotace" na titulní (curated programy), ne paginovaný hub
PROG_HREF = re.compile(r'href="(/[^"#]*dotac[^"#]*)"', re.I)
# anchor text typické pro PROGRAM (ne Pravidla/Smlouva/Žádost/Projekty)
PROG_TXT = re.compile(r'^(Dotace|Stipend|Podpora)\b', re.I)
SKIP_TXT = re.compile(r'^(Pravidla|Smlouva|Žádost|Projekt|Projekty|Celkový|PŘÍLOHA|Příloha|Finanční)', re.I)

# „od D. M. [RRRR] do D. M. [RRRR]"  (rok u kterékoli strany volitelný)
LHUTA = re.compile(
    r"Lhůta pro podání žádosti[:\s]*od\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})?\s*do\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})?",
    re.I)
ALOKACE = re.compile(r"uvolněno\s*([\d  \xa0]+)\s*Kč", re.I)


def fetch_curl(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "cs"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def fetch_render(url, _pw=[]):
    """Playwright fallback (Vismo občas blokuje urllib)."""
    if not _pw:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        br = pw.chromium.launch()
        _pw.append((pw, br))
    br = _pw[0][1]
    pg = br.new_page(user_agent=UA)
    pg.goto(url, wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(800)
    html = pg.content()
    pg.close()
    return html


def main_content(html):
    m = re.search(r"<main\b.*?</main>", html, re.S)
    return m.group(0) if m else html


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = H.unescape(re.sub(r"<[^>]+>", " ", h))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", h)).strip()


def _num(s):
    d = re.sub(r"[^\d]", "", s or "")
    return int(d) if d else None


def _iso(d, mth, y):
    if not (d and mth and y):
        return None
    return f"{int(y):04d}-{int(mth):02d}-{int(d):02d}"


def discover(get):
    """Listing programů = menu Dotace na titulní stránce (dedup, jen PROGRAM landing pages)."""
    home = get(HOME)
    out, seen = [], set()
    for m in re.finditer(r'<a\b[^>]*href="(/[^"#]*)"[^>]*>(.*?)</a>', home, re.S):
        href = m.group(1)
        if not re.search(r"dotac", href, re.I):
            continue
        txt = H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        if len(txt) < 5 or SKIP_TXT.match(txt) or not PROG_TXT.match(txt):
            continue
        if href in seen:
            continue
        seen.add(href)
        out.append((href, txt))
    return out


def parse_detail(text):
    rec = {}
    m = LHUTA.search(text)
    if m:
        y_start, y_end = m.group(3), m.group(6)
        y = y_start or y_end  # rok je často jen u jedné strany rozsahu → sdílí ho oba konce
        of = _iso(m.group(1), m.group(2), y_start or y)
        dl = _iso(m.group(4), m.group(5), y_end or y)
        rec["open_from"], rec["deadline"] = of, dl
        rec["_lhuta_raw"] = re.sub(r"\s+", " ", m.group(0)).strip()
    am = ALOKACE.search(text)
    if am:
        rec["alokace_czk"] = _num(am.group(1))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_teplice.json")
    ap.add_argument("--render", action="store_true", help="použij Playwright místo urllib")
    a = ap.parse_args()
    get = fetch_render if a.render else fetch_curl

    def save(progs):
        out = {"source": "teplice.cz", "kraj": "Ústecký kraj", "obec": "Teplice",
               "uroven": "obec", "platform": "teplice_vismo", "programs": progs}
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    try:
        links = discover(get)
    except Exception as e:
        print(f"discover přes {'render' if a.render else 'curl'} selhalo: {str(e)[:80]}", file=sys.stderr)
        if not a.render:
            print("→ zkouším Playwright fallback", file=sys.stderr)
            get = fetch_render
            links = discover(get)
        else:
            raise
    print(f"nalezeno {len(links)} programových landing pages", file=sys.stderr)

    progs = []
    for href, nazev in links:
        url = BASE + href
        try:
            html = get(url)
        except Exception as e:
            print(f"  warn {href}: {str(e)[:60]}", file=sys.stderr)
            continue
        text = detext(main_content(html))
        rec = {"nazev": nazev, "open_from": None, "deadline": None, "status": None,
               "alokace_czk": None, "max_czk": None, "popis": None, "eligible": None,
               "kod": None, "url": url}
        rec.update(parse_detail(text))
        # popis = úvodní próza (Text rubriky), bez navigace; fallback raw lhůta
        body = text
        for marker in ("Text rubriky", nazev):
            i = body.find(marker)
            if i >= 0:
                body = body[i + len(marker):]
                break
        rec["popis"] = re.sub(r"\s+", " ", body[:600]).strip() or None
        rec["_text"] = text[:4000]
        progs.append(rec)
        save(progs)  # průběžné ukládání
        time.sleep(0.3)

    save(progs)
    n_dl = sum(1 for p in progs if p.get("deadline"))
    n_alok = sum(1 for p in progs if p.get("alokace_czk"))
    print(json.dumps({"MARKER": "TEPLICE_HARVEST", "kept": len(progs),
                      "with_deadline": n_dl, "with_alokace": n_alok, "out": a.out},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
