#!/usr/bin/env python3
"""Frýdek-Místek harvester — dotační programy statutárního města (WordPress, server-rendered).

Metoda: WP REST (/wp-json/wp/v2/pages). Web NEMÁ custom post type pro dotace — programy žijí
jako běžné WP `page` pod URL cestami `.../dotace/...` a `.../dotace-a-programy/...`. Konkrétní
ročník programu = leaf stránka se slugem končícím na rok (`-2026`, `-na-rok-2026`, `-pro-rok-2026`).

Filtry (data-driven, ne hardcoded ID):
  - jen leaf stránky pod /dotace/ nebo /dotace-a-programy/ se slugem na cílový rok (>= --year)
  - VYNECHÁNO `/schvalene-dotace/` = AWARDS (schválené/vyplacené dotace, ne otevřené výzvy)
  - VYNECHÁNO parent/listing stránky bez ročníku ve slugu

Lossless: ukládá plný text stránky + VŠECHNY dokumenty (PDF/DOC/XLS). Inline regexem vytěží
termíny ("Žádosti ... lze podávat od DD.MM.YYYY do DD.MM.YYYY"), max. částku ("nejvýše ... do výše
N Kč") a oprávněné žadatele, KDE jsou v těle. Část programů (sociální/životní prostředí) má termíny
jen v příloze "Podmínky" (PDF) → open_from/deadline zůstane null, dopočítá LLM vrstva 2 / ingest.
Status NEPOČÍTÁ harvester (počítá ingest z termínů).

Usage: python3 scripts/fm_harvest.py [--out data/h_mesto_fm.json] [--year 2026]
"""
import argparse, json, re, sys, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)

BASE = "https://www.frydekmistek.cz"
API = BASE + "/wp-json/wp/v2/pages"
UA = {"User-Agent": "Mozilla/5.0 (compatible; re-grantio-harvester)"}

# segmenty cesty, které značí dotační sekci
DOTACE_SEG = re.compile(r"/(dotace|dotace-a-programy)/", re.I)
# awards (schválené dotace) — výsledky, NE otevřené výzvy → vynechat
AWARDS_SEG = re.compile(r"/schvalene-dotace/", re.I)
# leaf slug s ročníkem: ...-2026, ...-na-rok-2026, ...-pro-rok-2026, .../rok-2026/
YEAR_SLUG = re.compile(r"(?:-|/|na-rok-|pro-rok-)(\d{4})/?$")

# generický titulek ("Dotační programy pro rok 2026") nepojmenovává program → odvoď z parent slugu
GENERIC_TITLE = re.compile(r"^Dotační programy\s+(?:pro|na)\s+rok\s+\d{4}$", re.I)

DATE_RANGE = re.compile(
    r"[Žž]ádost\w*\s+o\s+dotaci\s+(?:lze\s+podávat|je\s+možné\s+podat|podávejte)?\s*"
    r"od\s+(\d{1,2}\.\s?\d{1,2}\.\s?\d{4})\s+do\s+(\d{1,2}\.\s?\d{1,2}\.\s?\d{4})")
MAX_AMT = re.compile(r"nejvýše\s+(?:však\s+)?do\s+výše\s+([\d. \xa0]+)\s*Kč", re.I)
ELIGIBLE = re.compile(r"[Oo]právněn\w*\s+žadatel\w*[^.]*\.")


def fetch(url):
    return http_util.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()


def all_pages():
    out, page = [], 1
    while True:
        arr = json.loads(fetch(f"{API}?per_page=100&page={page}&_fields=id,link,title"))
        if not arr:
            break
        out.extend(arr)
        if len(arr) < 100:
            break
        page += 1
    return out


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    for a, b in (("&nbsp;", " "), ("&#8211;", "-"), ("&#8217;", "'"), ("&amp;", "&"), ("&#8220;", '"'), ("&#8221;", '"')):
        h = h.replace(a, b)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", h)).strip()


def _iso(s):
    m = re.match(r"(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})", (s or "").strip())
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def _num(s):
    d = re.sub(r"[^\d]", "", s or "")
    return int(d) if d else None


def parse_program(pid, link, title_html):
    full = json.loads(fetch(f"{API}/{pid}?_fields=content"))
    html = full["content"]["rendered"]
    text = detext(html)
    title = detext(title_html)

    # generický titulek → odvoď název z parent slugu cesty (segment před leaf ročníkem)
    if GENERIC_TITLE.match(title):
        segs = [s for s in link.split("/") if s]
        if len(segs) >= 2:
            parent = segs[-2]
            name = parent.replace("-", " ").strip()
            ym0 = YEAR_SLUG.search(link)
            yr = ym0.group(1) if ym0 else ""
            title = name[:1].upper() + name[1:] + (f" {yr}" if yr else "")

    of = dl = None
    m = DATE_RANGE.search(text)
    if m:
        of, dl = _iso(m.group(1)), _iso(m.group(2))

    max_czk = None
    ma = MAX_AMT.search(text)
    if ma:
        max_czk = _num(ma.group(1))

    eligible = None
    me = ELIGIBLE.search(text)
    if me:
        eligible = re.sub(r"\s+", " ", me.group(0)).strip()

    # popis = první věta těla, pokud to není rovnou výčet příloh
    popis = None
    first = text.split("Příloha")[0].split("Podmínky")[0].strip()
    if 20 < len(first) < 600:
        popis = re.sub(r"\s+", " ", first)

    docs = []
    for h in re.findall(r'href="([^"]+)"', html):
        if re.search(r"\.(pdf|docx?|xlsx?)(\?|$)", h, re.I) and h not in docs:
            docs.append(h if h.startswith("http") else BASE + h)

    ym = YEAR_SLUG.search(link)
    return {
        "nazev": title,
        "open_from": of,
        "deadline": dl,
        "status": None,
        "alokace_czk": None,        # celková alokace není na stránce (jen v rozpočtu města)
        "max_czk": max_czk,
        "popis": popis,
        "eligible": eligible,
        "kod": None,
        "url": link,
        "_year": int(ym.group(1)) if ym else None,
        "_documents": docs,
        "_text": text[:6000],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_fm.json")
    ap.add_argument("--year", type=int, default=2026, help="minimální ročník programu (cílí na aktuální cyklus)")
    a = ap.parse_args()

    pages = all_pages()
    print(f"WP REST: {len(pages)} stránek celkem", file=sys.stderr)

    # kandidáti: leaf v dotační sekci, se slugem ročníku >= year, NE awards
    cands = []
    for p in pages:
        link = p["link"]
        if not DOTACE_SEG.search(link) or AWARDS_SEG.search(link):
            continue
        ym = YEAR_SLUG.search(link)
        if not ym or int(ym.group(1)) < a.year:
            continue
        cands.append(p)
    print(f"kandidátů (leaf programy roku >= {a.year}): {len(cands)}", file=sys.stderr)

    programs, seen_urls = [], set()
    for p in cands:
        if p["link"] in seen_urls:
            continue
        try:
            rec = parse_program(p["id"], p["link"], p["title"]["rendered"])
        except Exception as e:
            print(f"  warn id={p['id']}: {str(e)[:80]}", file=sys.stderr)
            continue
        if not rec["nazev"]:
            continue
        seen_urls.add(p["link"])
        programs.append(rec)
        print(f"  + {rec['nazev'][:60]} | open={rec['open_from']} dl={rec['deadline']} max={rec['max_czk']} docs={len(rec['_documents'])}", file=sys.stderr)
        # průběžné ukládání
        out = {"source": "frydekmistek.cz", "kraj": "Moravskoslezský kraj", "obec": "Frýdek-Místek",
               "uroven": "obec", "platform": "fm_wp", "programs": programs}
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    out = {"source": "frydekmistek.cz", "kraj": "Moravskoslezský kraj", "obec": "Frýdek-Místek",
           "uroven": "obec", "platform": "fm_wp", "programs": programs}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "FM_HARVEST", "method": "wp_rest_pages",
                      "kept": len(programs), "with_deadline": sum(1 for p in programs if p["deadline"]),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
