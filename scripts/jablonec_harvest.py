#!/usr/bin/env python3
"""Jablonec nad Nisou harvester — dotační programy statutárního města (Nette, server-rendered HTML).

mestojablonec.cz vede dotační programy jako "životní situace" v kategorii
/zivotni-situace/kategorie/dotace-a-dary (čistě server-rendered, žádný JS/Playwright nutný).
Detail = štítkovaná próza: perex (popis), "Kdo je oprávněn ... jednat" (eligible),
a termín podání v sekci "zahájit řešení" ve tvaru "v období od D. měsíce YYYY do D. měsíce YYYY".
Datumy jsou v českém slovním tvaru → parse na ISO. Programy bez období (individuální dotace,
peněžité dary, programy s odkazem "viz příloha") → open_from/deadline=null, status dopočítá ingest.

Cíl = OTEVŘENÉ/vyhlášené výzvy, NE awards, NE login. Lossless: ukládá parsed pole + plný text detailu.

Usage: python3 scripts/jablonec_harvest.py --out data/h_mesto_jablonec.json
"""
import argparse, json, re, sys, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)

BASE = "https://www.mestojablonec.cz"
CATEGORY = "/zivotni-situace/kategorie/dotace-a-dary"

MONTHS = {
    "ledna": 1, "února": 2, "unora": 2, "března": 3, "brezna": 3, "dubna": 4,
    "května": 5, "kvetna": 5, "června": 6, "cervna": 6, "července": 7, "cervence": 7,
    "srpna": 8, "září": 9, "zari": 9, "října": 10, "rijna": 10, "listopadu": 11,
    "prosince": 12,
}
# detail-slug musí obsahovat dotační/dar/program klíč, ne navigační kategorie
DETAIL_RE = re.compile(r'href="(/zivotni-situace/(?!kategorie/)[a-z0-9-]+)"')


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return http_util.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " ")
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", h)).strip()


def _iso(day, month_word, year):
    mo = MONTHS.get(month_word.lower())
    if not mo:
        return None
    return f"{int(year):04d}-{mo:02d}-{int(day):02d}"


def parse_period(text):
    """Vrať (open_from, deadline) z 'v období od D. měsíce YYYY do D. měsíce YYYY'.
    Zvládá i zkrácený start 'od 2. do 16. března 2026' (měsíc/rok jen u konce)."""
    # plný tvar: od D. MĚSÍC YYYY do D. MĚSÍC YYYY
    m = re.search(
        r"v\s+období\s+od\s+(\d{1,2})\.\s*([a-zžěščřďťňáíéúů]+)\s+(\d{4})"
        r"\s+do\s+(\d{1,2})\.\s*([a-zžěščřďťňáíéúů]+)\s+(\d{4})",
        text, re.I,
    )
    if m:
        return _iso(m[1], m[2], m[3]), _iso(m[4], m[5], m[6])
    # zkrácený start: od D. do D. MĚSÍC YYYY  (měsíc/rok sdílený)
    m = re.search(
        r"v\s+období\s+od\s+(\d{1,2})\.\s+do\s+(\d{1,2})\.\s*([a-zžěščřďťňáíéúů]+)\s+(\d{4})",
        text, re.I,
    )
    if m:
        return _iso(m[1], m[3], m[4]), _iso(m[2], m[3], m[4])
    return None, None


def extract_perex(html):
    """Perex = poslední <p> blok těsně před id=zakladni-informace (lead popis programu)."""
    i = html.find('id="zakladni-informace"')
    if i < 0:
        return None
    head = html[:i]
    ps = re.findall(r"<p[^>]*>(.*?)</p>", head, re.S)
    if not ps:
        return None
    txt = re.sub(r"<[^>]+>", "", ps[-1]).replace("&nbsp;", " ")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt or None


def parse_detail(html, url):
    text = detext(html)
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    nazev = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else None
    of, dl = parse_period(text)
    me = re.search(
        r"Kdo je oprávněn v této věci jednat\s*(.+?)\s*(?:Podmínky|Vyřízení|Kde, s kým)",
        text, re.S,
    )
    eligible = re.sub(r"\s+", " ", me.group(1)).strip()[:600] if me else None
    return {
        "nazev": nazev, "open_from": of, "deadline": dl, "status": None,
        "alokace_czk": None, "max_czk": None, "popis": extract_perex(html),
        "eligible": eligible, "kod": None, "url": url,
        "_text": text[:5000],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_jablonec.json")
    a = ap.parse_args()

    cat = fetch(BASE + CATEGORY)
    slugs = []
    for m in DETAIL_RE.finditer(cat):
        href = m.group(1)
        if href not in slugs:
            slugs.append(href)
    print(f"nalezeno {len(slugs)} odkazů na programy", file=sys.stderr)

    out = {"source": "mestojablonec.cz", "kraj": "Liberecký kraj",
           "obec": "Jablonec nad Nisou", "uroven": "obec",
           "platform": "jablonec_nette", "programs": []}
    seen = set()
    for href in slugs:
        url = BASE + href
        try:
            html = fetch(url)
        except Exception as e:
            print(f"  warn {href}: {str(e)[:60]}", file=sys.stderr)
            continue
        rec = parse_detail(html, url)
        if not rec["nazev"] or rec["url"] in seen:
            continue
        seen.add(rec["url"])
        out["programs"].append(rec)
        # průběžné ukládání
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with_dl = sum(1 for p in out["programs"] if p["deadline"])
    print(json.dumps({"MARKER": "JABLONEC_HARVEST", "kept": len(out["programs"]),
                      "with_deadline": with_dl, "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
