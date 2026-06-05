#!/usr/bin/env python3
"""Chomutov harvester — dotační programy statutárního města Chomutova.

ZDROJ: granty.chomutov.cz = dedikovaný grantový portál (WordPress 6.9.4, WP REST
otevřené na /wp-json/wp/v2/posts). Každý dotační program 2026 = jeden WP post.
Veřejný web mesto/www.chomutov.cz na granty.* odkazuje; chomutov.cz (bare) je login
portál (NE veřejný web). ACF pole jsou prázdná → strukturovaná data (alokace, výše,
termíny) žijí v próze content.rendered → konzervativní regex parse, žádný LLM.

STRUKTURA PŘED PRÓZOU (CLAUDE.md ⑦): zdroj je REST listing, ne scraping HTML.
Lossless: ukládá plný text postu (_text) + parsed pole. Status dopočítá ingest z termínů.
Termíny jsou u většiny programů jen v přiloženém PDF "Pravidla"/formuláři (NE v próze) →
deadline=null tam, kde web v próze datum neuvádí (kontrakt: co nezjistíš = null).

Usage: python3 scripts/chomutov_harvest.py --out data/h_mesto_chomutov.json
"""
import argparse, json, re, ssl, sys, urllib.request

BASE = "https://granty.chomutov.cz"
REST = BASE + "/wp-json/wp/v2/posts"
# granty.* běží na cert, který curl bez -k odmítá (self-signed v řetězci) → vlastní ctx
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# kategorie → krátký lidský štítek oblasti (jen pro popis/log; faceting řeší ingest_kraj)
CAT = {20: "cestovní ruch", 2: "kultura", 10: "ostatní", 13: "památková péče",
       21: "podnikání", 9: "sociální projekty", 7: "sport", 8: "životní prostředí"}

# "Nezařazené"/"Testovací"/"Reklamní smog" = ne-grantové kategorie portálu
SKIP_CAT = {1, 12, 19}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (re-grantio harvester)"})
    return urllib.request.urlopen(req, timeout=40, context=CTX).read().decode("utf-8", "replace")


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    h = (h.replace("&nbsp;", " ").replace("&#8211;", "-").replace("&#8217;", "'")
          .replace("&amp;", "&").replace("&#8230;", "..."))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", h)).strip()


def _iso(s):
    m = re.match(r"\s*(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})", s or "")
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


_DATE = r"\d{1,2}\.\s?\d{1,2}\.\s?\d{4}"


def parse_dates(txt):
    """Konzervativně: open_from JEN když je explicitní rozpětí 'DATE do DATE'
    (etapy podávání, 1104). Jinak deadline = nejpozdější nalezené datum (např. dvě
    nezávislé uzávěrky pro různé oblasti v 1114 → bereme tu pozdější jako deadline,
    open_from=null). Žádné min/max přes celý text → nehrozí záměna oblasti za 'otevření'."""
    ranges = re.findall(rf"({_DATE})\s*(?:do|-|–|až)\s*({_DATE})", txt)
    if ranges:
        starts = sorted({_iso(s) for s, _ in ranges})
        ends = sorted({_iso(e) for _, e in ranges})
        return starts[0], ends[-1]
    found = sorted({_iso(m.group(0)) for m in re.finditer(_DATE, txt)})
    found = [d for d in found if d]
    return (None, found[-1]) if found else (None, None)


_NUM_WORD = {"tisíc": 1000, "tis": 1000, "mil": 1_000_000, "milion": 1_000_000, "milionů": 1_000_000}


def _money_to_int(num_str, unit):
    """'400' + 'tisíc' -> 400000 ; '50.000' + 'Kč' -> 50000."""
    base = re.sub(r"[^\d]", "", num_str)
    if not base:
        return None
    n = int(base)
    u = (unit or "").lower()
    for w, mult in _NUM_WORD.items():
        if u.startswith(w):
            return n * mult
    return n


def parse_money(txt):
    """alokace_czk = celkový rozpočet programu ('vyčleněno X tisíc/Kč'),
    max_czk = strop na žadatele ('žadatel může získat až X', 'maximální výše ... X').
    Konzervativní: bere jen explicitní fráze, jinak null."""
    alok = mx = None
    # alokace programu: JEN explicitní rozpočtová fráze (vyčleněno / v rozpočtu).
    # Pozor: 'MAX. VÝŠE ... 50.000 Kč' je strop na žadatele, NE alokace → sem nepatří.
    m = re.search(r"(?:vyčleněn[oa]|v rozpočtu[^.]{0,40}?)\s*(?:je\s*)?([\d  .,\xa0]+)\s*(tisíc|tis\.?|mil\.?|milion[ůu]?|Kč|korun)", txt, re.I)
    if m:
        alok = _money_to_int(m.group(1), m.group(2))
    # max na žadatele
    m = re.search(r"(?:žadatel\D{0,40}?|jednotliv\D{0,30}?)(?:získat|obdržet|max\D{0,15}?)\s*(?:až\s*)?([\d  .,\xa0]+)\s*(tisíc|tis\.?|mil\.?|milion[ůu]?|Kč|korun)", txt, re.I)
    if m:
        mx = _money_to_int(m.group(1), m.group(2))
    if mx is None:
        m = re.search(r"až\s*([\d  .,\xa0]+)\s*(tisíc|tis\.?|Kč|korun)\s*(?:korun)?", txt, re.I)
        if m:
            mx = _money_to_int(m.group(1), m.group(2))
    return alok, mx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_chomutov.json")
    ap.add_argument("--source", default="granty.chomutov.cz")
    a = ap.parse_args()

    raw = json.loads(fetch(REST + "?per_page=100"))
    print(f"WP REST vrátil {len(raw)} postů", file=sys.stderr)

    progs, seen = [], set()
    for p in raw:
        cats = set(p.get("categories") or [])
        if cats & SKIP_CAT and not (cats - SKIP_CAT):
            continue  # čistě ne-grantová kategorie
        title = detext(p.get("title", {}).get("rendered", "")).strip()
        url = p.get("link") or f"{BASE}/?p={p.get('id')}"
        if not title or url in seen:
            continue
        seen.add(url)
        body = detext(p.get("content", {}).get("rendered", ""))
        excerpt = detext(p.get("excerpt", {}).get("rendered", ""))
        full = (body or excerpt)
        of, dl = parse_dates(full)
        alok, mx = parse_money(full)
        popis = (excerpt or body)[:600].strip() or None
        # eligible: věty s 'určen'/'žadatel musí'/'pro' jako hrubý signál; jinak null (kód facetuje)
        elig = None
        m = re.search(r"((?:Program (?:je )?určen|Podpora je určen|Žadatel musí|Program je otevřený)[^.]{0,300}\.)", full)
        if m:
            elig = re.sub(r"\s+", " ", m.group(1)).strip()
        cat_labels = [CAT[c] for c in cats if c in CAT]
        progs.append({
            "nazev": title,
            "open_from": of,
            "deadline": dl,
            "status": None,
            "alokace_czk": alok,
            "max_czk": mx,
            "popis": popis,
            "eligible": elig,
            "kod": None,
            "url": url,
            "_kategorie": cat_labels,
            "_text": full[:4000],
        })

    out = {"source": a.source, "kraj": "Ústecký kraj", "obec": "Chomutov",
           "uroven": "obec", "platform": "chomutov_wordpress", "programs": progs}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "CHOMUTOV_HARVEST", "kept": len(progs),
                      "with_deadline": sum(1 for x in progs if x["deadline"]),
                      "with_alokace": sum(1 for x in progs if x["alokace_czk"]),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
