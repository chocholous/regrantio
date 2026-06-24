#!/usr/bin/env python3
"""Havířov harvester — dotace z rozpočtu statutárního města Havířova (Drupal, server-rendered HTML).

ZDROJ: havirov-city.cz. Město neprovozuje SPA-grid ani per-program listing s vlastními
termíny. Má JEDEN sjednocený dotační režim ("Poskytování dotací z rozpočtu statutárního
města Havířova") řízený Zásadami (PDF), který se otevírá KAŽDOROČNĚ ve dvou řádných kolech:
  - 1. kolo: žádosti do 31. 10. (na následující kalendářní rok)
  - 2. kolo: žádosti do 31. 3. (na daný kalendářní rok)
Zásady (čl. IV) definují OBLASTI dotovaných činností s kódy (RS/S/TV/K/Š/P/PKD/IZS/Z/ŽP/BESIP).
Každá oblast = samostatný "program" (cíl = otevřené výzvy s termíny), všechny sdílejí oba termíny.

Metoda: curl HTML (landing = popis režimu + přílohy) + pdftotext Zásad (oblasti+kódy+eligible).
Playwright NENÍ potřeba — obsah je čistě statický server-rendered Drupal, žádný XHR/JS-grid.
Status dopočítá ingest z termínů (open_from/deadline). Awards ("Databáze schválených dotací")
ani půjčky ("Kotlíkové půjčky") se NEharvestují (NE dotace / NE otevřená výzva).

Lossless: ukládá parsed pole + plný text landing + plný text Zásad. Ukládá průběžně.

Usage: python3 scripts/havirov_harvest.py [--out data/h_mesto_havirov.json] [--today 2026-06-05]
"""
import argparse, json, os, re, subprocess, sys, tempfile, urllib.request, urllib.parse
import http_util   # jednotná TLS politika (audit #7/#32)
from datetime import date

BASE = "https://www.havirov-city.cz"
LANDING = BASE + "/zivotni-situace/dotace/poskytovani-dotaci-rozpoctu-statutarniho-mesta-havirova"

# Oblasti dotovaných činností dle čl. IV Zásad. nazev_oblasti = lidský název, kod = úřední kód.
# eligible/popis se doplní z textu Zásad níže (parse), tohle je kostra pořadí a názvů kódů.
OBLASTI = [
    ("RS", "Činnost registrovaných sociálních služeb", "sociální oblast"),
    ("S", "Projekty a Činnost na podporu aktivit související se sociální oblastí", "sociální oblast"),
    ("TV", "Sportovní oblast", "sportovní oblast"),
    ("K", "Kulturní oblast", "kulturní oblast"),
    ("Š", "Školská oblast", "školská oblast"),
    ("P", "Oblast partnerských vztahů", "partnerské vztahy"),
    ("PKD", "Prevence kriminality a protidrogová prevence", "prevence kriminality a protidrogová prevence"),
    ("IZS", "Integrovaný záchranný systém", "bezpečnost a ochrana zdraví"),
    ("Z", "Zdravotnictví", "bezpečnost a ochrana zdraví"),
    ("ŽP", "Ochrana životního prostředí", "bezpečnost a ochrana zdraví"),
    ("BESIP", "Bezpečnost v silničním provozu", "bezpečnost a ochrana zdraví"),
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return http_util.urlopen(req, timeout=30).read()


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    m = re.search(r"<main.*?</main>", h, re.S) or re.search(r"<article.*?</article>", h, re.S)
    seg = m.group(0) if m else h
    seg = re.sub(r"<[^>]+>", " ", seg).replace("&nbsp;", " ")
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", seg)).strip()


def pdf_to_text(raw):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(raw); p = f.name
    try:
        out = subprocess.run(["pdftotext", p, "-"], capture_output=True, timeout=60)
        return out.stdout.decode("utf-8", "replace")
    finally:
        os.unlink(p)


def next_deadlines(today):
    """Vrátí (open_from, deadline) pro nejbližší otevřené řádné kolo.
    1. kolo: deadline 31.10 (rok = letošní pokud ještě nebyl, jinak příští).
    2. kolo: deadline 31.3.
    Vrátíme to kolo, jehož deadline je nejblíž v budoucnu (>= today). open_from = den po
    deadlinu předchozího kola (tj. režim přijímá žádosti průběžně mezi koly)."""
    y = today.year
    cand = []
    for yy in (y, y + 1):
        cand.append((date(yy, 3, 31), date(yy - 1, 11, 1)))   # 2. kolo: po 1. kole loni
        cand.append((date(yy, 10, 31), date(yy, 4, 1)))        # 1. kolo: po 2. kole letos
    future = sorted([c for c in cand if c[0] >= today])
    if not future:
        return None, None
    dl, of = future[0]
    return of.isoformat(), dl.isoformat()


# Uniformní oprávněnost žadatele (z landing + Zásad — stejná pro všechny oblasti).
ELIGIBLE = ("Právnické i fyzické osoby splňující podmínky Zásad pro poskytování dotací "
            "z rozpočtu statutárního města Havířova.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_havirov.json")
    ap.add_argument("--today", default=str(date.today()))
    a = ap.parse_args()
    today = date.fromisoformat(a.today)

    out = {"source": "havirov-city.cz", "kraj": "Moravskoslezský kraj", "obec": "Havířov",
           "uroven": "obec", "platform": "havirov_drupal", "programs": []}

    def save():
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 1) landing — popis režimu + odkazy na přílohy (Zásady PDF)
    landing_html = fetch(LANDING).decode("utf-8", "replace")
    landing_text = detext(landing_html)
    out["_landing_text"] = landing_text[:6000]
    save()

    # najdi Zásady PDF mezi přílohami
    zasady_url, zasady_text = None, ""
    for m in re.finditer(r'href="(/sites/default/files/[^"]+\.pdf)"', landing_html):
        href = m.group(1)
        if re.search(r"Z[%C3a][^/]*sady", href, re.I) or "asady" in href:
            zasady_url = BASE + href
            break
    if zasady_url:
        try:
            zasady_text = pdf_to_text(fetch(urllib.parse.quote(zasady_url, safe=":/%")))
            out["_zasady_url"] = zasady_url
            out["_zasady_text"] = zasady_text[:20000]
        except Exception as e:
            print(f"  warn Zásady PDF: {str(e)[:80]}", file=sys.stderr)
    save()

    of, dl = next_deadlines(today)

    # popis režimu (společný úvod) z landing textu
    common_popis = ("Dotace z rozpočtu statutárního města Havířova dle Zásad; žádosti ve dvou "
                    "řádných kolech: 1. kolo do 31. 10. (na následující rok), 2. kolo do 31. 3. "
                    "Podání výhradně datovou schránkou (ID 7zhb6tn) na předepsaném formuláři "
                    "s kvalifikovaným el. podpisem.")

    seen = set()
    for kod, nazev, oblast_txt in OBLASTI:
        prog = {
            "nazev": f"Dotace z rozpočtu města Havířova — {nazev}",
            "open_from": of,
            "deadline": dl,
            "status": None,
            "alokace_czk": None,
            "max_czk": None,
            "popis": f"Oblast: {oblast_txt}. {common_popis}",
            "eligible": ELIGIBLE,
            "kod": kod,
            "url": LANDING,
        }
        key = (kod, prog["nazev"])
        if key in seen:
            continue
        seen.add(key)
        out["programs"].append(prog)
        save()

    print(json.dumps({"MARKER": "HAVIROV_HARVEST", "kept": len(out["programs"]),
                      "zasady_pdf": bool(zasady_text), "deadline": dl, "out": a.out},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
