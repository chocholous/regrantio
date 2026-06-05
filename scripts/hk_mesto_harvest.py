#!/usr/bin/env python3
"""Hradec Králové (město) — harvester dotačních programů z portálu dotace.mmhk.cz.

dotace.mmhk.cz = DOTIS/ProDos dotační portál města (NE vismo). Server-rendered HTML.
Homepage GrantPrograms.aspx odkazuje na kategorie ProjectList.aspx?Id=N (Sport, Kultura, ...).
Každá kategorie = stránka s bloky <div class="gpitem"> (1 blok = 1 dotační program):
  Program: <název>  /  Popis programu: <popis>  /  attachments (PDF)  /  info ul:
    "Datum zahájení výzvy: D.M.RRRR HH:MM"  -> open_from
    "Datum ukončení výzvy: D.M.RRRR HH:MM"  -> deadline
    "Výzva byla ukončena."                  -> status=closed (explicitní)
    "Datum schválení programu: D.M.RRRR"     -> jen approval, neukládá se jako termín

Strukturovaný parse, žádný LLM. Alokace/max/kód/eligible NEJSOU na listingu (jen v PDF) -> null.
URL programu = URL kategorie (DOTIS nemá per-program detail page); dedup dle (kategorie, název).
Cíl = OTEVŘENÉ výzvy; uzavřené ponecháváme (status se dopočítá v ingestu z termínů / explicitního flagu).

curl/urllib stačí (žádný WAF). Playwright fallback dostupný přes --playwright, pokud by fetch selhal.

Usage: python3 scripts/hk_mesto_harvest.py --out data/h_mesto_hk.json
"""
import argparse, json, re, sys, urllib.request, html as _html

BASE = "https://dotace.mmhk.cz/Modules/DOTISMMHK/Pages/Public"
HOME = BASE + "/GrantPrograms.aspx"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def fetch_pw(url):
    """Playwright fallback (vismo/DOTIS někdy blokuje ne-prohlížečové fetchery)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(user_agent=UA)
        pg.goto(url, wait_until="networkidle", timeout=45000)
        c = pg.content()
        b.close()
        return c


def clean(s):
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _iso(s):
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s or "")
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def categories(home_html):
    """Mapa Id -> název kategorie z homepage."""
    cats = {}
    for m in re.finditer(r'<a[^>]+href="ProjectList\.aspx\?Id=(\d+)"[^>]*>(.*?)</a>', home_html, re.S):
        name = clean(m.group(2))
        if name:
            cats[m.group(1)] = name
    return cats


def parse_blocks(html, cat_name, cat_url):
    """Vytáhni programy (gpitem bloky) z HTML kategorie."""
    progs = []
    for block in re.findall(r'<div class="gpitem">(.*?)(?=<div class="gpitem">|<div class="Archiv|</div>\s*</div>\s*</div>\s*</div>\s*<div id="Footer)', html, re.S):
        nm = re.search(r'<div class="label">\s*Program:\s*</div>\s*<div class="value">(.*?)</div>', block, re.S)
        if not nm:
            continue
        nazev = clean(nm.group(1))
        if not nazev:
            continue
        d = re.search(r'<div class="description">(.*?)</div>', block, re.S)
        popis = clean(d.group(1)) if d else None

        info = block[block.find('class="info"'):] if 'class="info"' in block else block
        closed = "Výzva byla ukončena" in info
        of = dl = None
        mo = re.search(r"Datum zah[aá]jen[ií] v[yý]zvy:\s*</label>\s*([\d.]+)", info)
        md = re.search(r"Datum ukon[čc]en[ií] v[yý]zvy:\s*</label>\s*([\d.]+)", info)
        if mo:
            of = _iso(mo.group(1))
        if md:
            dl = _iso(md.group(1))

        atts = [{"label": clean(la), "url": _html.unescape(u), "name": clean(nm2)}
                for la, u, nm2 in re.findall(
                    r'<label>(.*?)</label>\s*<span>\s*<a href="([^"]+)">(.*?)</a>', block, re.S)]

        progs.append({
            "nazev": nazev,
            "open_from": of,
            "deadline": dl,
            "status": "closed" if closed else None,  # jen explicitní; jinak dopočítá ingest
            "alokace_czk": None,
            "max_czk": None,
            "popis": popis,
            "eligible": None,
            "kod": None,
            "url": cat_url,
            "_kategorie": cat_name,
            "_attachments": atts,
        })
    return progs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_hk.json")
    ap.add_argument("--playwright", action="store_true", help="vynutí Playwright fetch")
    a = ap.parse_args()
    get = fetch_pw if a.playwright else fetch

    try:
        home = get(HOME)
    except Exception as e:
        if not a.playwright:
            print(f"curl selhal ({str(e)[:60]}) -> Playwright fallback", file=sys.stderr)
            get = fetch_pw
            home = get(HOME)
        else:
            raise
    cats = categories(home)
    print(f"nalezeno {len(cats)} kategorií: {sorted(cats.values())}", file=sys.stderr)

    out = {"source": "dotace.mmhk.cz", "kraj": "Královéhradecký kraj", "obec": "Hradec Králové",
           "uroven": "obec", "platform": "hk_vismo", "programs": []}
    seen = set()
    for cid, cname in sorted(cats.items(), key=lambda x: int(x[0])):
        url = f"{BASE}/ProjectList.aspx?Id={cid}"
        try:
            h = get(url)
        except Exception as e:
            print(f"  warn kategorie {cid} ({cname}): {str(e)[:60]}", file=sys.stderr)
            continue
        blocks = parse_blocks(h, cname, url)
        added = 0
        for p in blocks:
            key = (p["_kategorie"], p["nazev"])
            if key in seen:
                continue
            seen.add(key)
            out["programs"].append(p)
            added += 1
        print(f"  {cname} (Id={cid}): {added} programů", file=sys.stderr)
        # průběžné ukládání
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    by_st = Counter("closed" if p["status"] == "closed" else
                    ("dated" if p["deadline"] else "nodate") for p in out["programs"])
    print(json.dumps({"MARKER": "HK_MESTO_HARVEST", "kept": len(out["programs"]),
                      "categories": len(cats), "by_kind": dict(by_st), "out": a.out},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
