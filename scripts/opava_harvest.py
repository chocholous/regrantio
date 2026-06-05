#!/usr/bin/env python3
"""Opava harvester — dotační programy statutárního města Opava (Joomla, server-rendered HTML).

opava-city.cz/cz/nabidka-temat/dotace/dotacni-programy-<ROK>/ = listing odkazů na detailní
stránky jednotlivých programů (<rok>/<slug>.html). Detail je čistě prozaicky štítkovaný
v <article> elementu → strukturovaný parse, žádný LLM:
  - <h1>                                        → nazev
  - "Termín podáv(ání|í) žádostí: od D. M. YYYY do D. M. YYYY"
    nebo "Termín podání žádostí je stanoven od D. M. do D. M. YYYY."  → open_from / deadline
  - "Cílem programu je ..."                     → popis (fallback: 1. odstavec po termínu)
  - "(Schválená|Předpokládaná) alokace programu: N Kč"  → alokace_czk (Schválená > Předpokládaná)
  - "Maximální výše poskytnuté dotace ...: N Kč" (jen je-li jediná číselná hodnota) → max_czk

Rok se NEhardcoduje: zkusí se sestupně od příštího roku (latest existující listing = aktuální cyklus).
POZN.: programy "2026" měly okno podávání na podzim 2025 → status dopočítá ingest (zpravidla closed).
Žádný strop na počet programů (acquisition unbounded). Status NEsetuje (null) → dopočítá ingest_kraj.

Lossless: ukládá parsed pole + plný text <article>. Ukládá průběžně po každém programu.

Usage: python3 scripts/opava_harvest.py [--out data/h_mesto_opava.json] [--year 2026]
"""
import argparse, datetime, json, re, sys, urllib.request

BASE = "https://www.opava-city.cz"
LISTING = "/cz/nabidka-temat/dotace/dotacni-programy-{year}/"
# slugy, které NEJSOU dotační program (metodika/loga/podmínky)
SKIP_SLUG = re.compile(r"podminky-uziti-loga|podminky|manual|metodik|seminar", re.I)
TERM_RE = re.compile(
    r"Termín\s+pod[aá](?:v[aá])?n[ií]\s+žádostí[^\n:]*?(?:je\s+stanoven\s+)?:?\s*"
    r"od\s+(\d{1,2}\.\s*\d{1,2}\.(?:\s*\d{4})?)\s+do\s+(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})",
    re.I)
ALOK_RE = re.compile(r"(Schválená|Předpokládaná)\s+alokace\s+programu:\s*([\d., ]+)\s*Kč", re.I)
MAX_RE = re.compile(r"Maxim[aá]lní\s+výše\s+poskytnut[eé]\s+dotace[^\n:]*:\s*([\d., ]+)\s*Kč", re.I)
POPIS_RE = re.compile(r"((?:Cílem|Účelem)\s+(?:programu|dotačního\s+titulu)\s+je[:]?\s+.+?)(?:\n|$)",
                      re.I | re.S)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def strip_html(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in (("&nbsp;", " "), ("&ndash;", "-"), ("&scaron;", "š"),
                 ("&amp;", "&"), ("&quot;", '"'), ("&bdquo;", "„"), ("&ldquo;", "“"),
                 ("&sect;", "§"), ("&#47;", "/")):
        s = s.replace(a, b)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


def iso(s):
    """'1. 12. 2025' / '01.12.2025' / '17. 10.' (rok null) → ISO nebo (None, jen-d-m)."""
    m = re.match(r"\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})?", s or "")
    if not m:
        return None
    d, mo, y = int(m[1]), int(m[2]), m[3]
    if not y:
        return ("?", mo, d)          # marker: rok chybí, doplní se z deadline
    return f"{int(y):04d}-{mo:02d}-{d:02d}"


def num(s):
    d = re.sub(r"[^\d]", "", (s or "").split(",")[0])  # odřízni haléře za desetinnou čárkou
    return int(d) if d else None


def parse_detail(html, url):
    m = re.search(r"<article\b.*?</article>", html, re.S)
    body = m.group(0) if m else html
    text = strip_html(body)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    nazev = strip_html(h1.group(1)) if h1 else None

    open_from = deadline = None
    tm = TERM_RE.search(text)
    if tm:
        of, dl = iso(tm.group(1)), iso(tm.group(2))
        deadline = dl if isinstance(dl, str) else None
        if isinstance(of, tuple):        # open rok chybí → vezmi z deadline
            _, mo, d = of
            yr = deadline[:4] if deadline else None
            open_from = f"{yr}-{mo:02d}-{d:02d}" if yr else None
        else:
            open_from = of

    alok = None
    for label, val in ALOK_RE.findall(text):
        n = num(val)
        if n and (alok is None or label.lower().startswith("schvál")):
            alok = n                     # Schválená přebíjí Předpokládanou

    maxc = None
    mm = MAX_RE.search(text)
    if mm:
        maxc = num(mm.group(1))          # jen když je jediná částka (tabulkové se nezachytí)

    pm = POPIS_RE.search(text)
    popis = re.sub(r"\s+", " ", pm.group(1)).strip()[:1000] if pm else None

    return {
        "nazev": nazev, "open_from": open_from, "deadline": deadline, "status": None,
        "alokace_czk": alok, "max_czk": maxc, "popis": popis, "eligible": None,
        "kod": None, "url": url, "_text": text[:4000],
    }


def discover_links(year):
    html = fetch(BASE + LISTING.format(year=year))
    pat = re.compile(r'href="(/cz/nabidka-temat/dotace/dotacni-programy-%d/([a-z0-9-]+)\.html)"' % year)
    seen, links = set(), []
    for href, slug in pat.findall(html):
        if href in seen or SKIP_SLUG.search(slug):
            continue
        seen.add(href)
        links.append(BASE + href)
    return links


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_opava.json")
    ap.add_argument("--year", type=int, default=None,
                    help="rok listingu; default = nejnovější existující (sestupně od příštího roku)")
    a = ap.parse_args()

    out = {"source": "opava-city.cz", "kraj": "Moravskoslezský kraj", "obec": "Opava",
           "uroven": "obec", "platform": "opava_joomla", "programs": []}

    years = [a.year] if a.year else list(range(datetime.date.today().year + 1,
                                                datetime.date.today().year - 2, -1))
    links, used_year = [], None
    for y in years:
        try:
            links = discover_links(y)
        except Exception as e:
            print(f"  listing {y}: {str(e)[:60]}", file=sys.stderr); continue
        if links:
            used_year = y; break
    print(f"rok={used_year} nalezeno {len(links)} odkazů na programy", file=sys.stderr)

    def save():
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    seen_titles = set()
    for url in links:
        try:
            html = fetch(url)
        except Exception as e:
            print(f"  warn {url}: {str(e)[:60]}", file=sys.stderr); continue
        rec = parse_detail(html, url)
        if not rec["nazev"]:
            print(f"  skip (bez názvu): {url}", file=sys.stderr); continue
        key = rec["nazev"].lower().strip()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        out["programs"].append(rec)
        save()                            # průběžně
        print(f"  + {rec['nazev'][:55]}  [{rec['open_from']}–{rec['deadline']}]",
              file=sys.stderr)

    save()
    print(json.dumps({"MARKER": "OPAVA_HARVEST", "year": used_year,
                      "kept": len(out["programs"]), "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
