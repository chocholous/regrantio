#!/usr/bin/env python3
"""MSK harvester — dotační programy Moravskoslezského kraje (vlastní PHP CMS, server-rendered HTML).

Rozcestník /temata/dotace/index.html odkazuje na 9 oblastí přes legacy URL
/scripts/detail.php?pgid=N (249 Sociální, 250 Zdravotnictví, 251 Prevence, 252 Rozvoj/inovace,
253 Cestovní ruch, 254 Kultura, 255 Vzdělávání, 256 Sport, 258 Životní prostředí). Každá oblast =
stránka se seznamem programů (<article class="NewsArticle">): titulek + friendly detail URL + perex
("Lhůta pro podání žádostí je od DD. M. YYYY do DD. M. YYYY ..."). Strukturovaný parse, žádný LLM.

pgid oblastí se NEhardcodují — vyparsují se z index.html (anchor `?pgid=` se štítkem oblasti).
Status NEpočítá harvester (dopočítá ingest z open_from/deadline vs. dnešek).

Usage: python3 scripts/msk_harvest.py [--out data/h_kraj_msk.json]
"""
import argparse, json, re, sys, urllib.request

BASE = "https://www.msk.cz"
INDEX = BASE + "/temata/dotace/index.html"

# Oblasti dotací = JEN anchory v hlavním obsahu rozcestníku s class="ListBox-more"
# a title="další informace – <oblast>". Globální nav používá ?pgid= taky, ale BEZ ListBox-more,
# takže ho tahle kotva přesně odfiltruje. Pgid se NEhardcodují, čtou se odsud.
AREA_RE = re.compile(
    r'<a href="(/scripts/detail\.php\?pgid=(\d+))"\s+class="ListBox-more"\s+'
    r'title="dal[^–]*–\s*([^"]+)"',
    re.I,
)

# Jeden program = <article> ... <h2 class="NewsArticle-title"><a href="URL">TITUL</a></h2> PEREX <time...>
ART_RE = re.compile(
    r'class="NewsArticle-title"[^>]*>\s*<a href="([^"]+)">([^<]+)</a>\s*</h2>(.*?)</article>',
    re.S,
)
# perex končí před <time class="NewsArticle-date"> (datum publikace, NE deadline)
PEREX_END_RE = re.compile(r'<time\b', re.I)

# "od DD. M. YYYY" a "do DD. M. YYYY" (mezery mohou být &nbsp;, hellip ořezává truncated perexy)
DATE_FROM_RE = re.compile(r'\bod\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})')
DATE_TO_RE = re.compile(r'\bdo\s+(?:dne\s+)?(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})')


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def detext(html):
    h = html.replace("&nbsp;", " ").replace("&hellip;", "…")
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", h).strip()


def _iso(d, m, y):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def parse_area(html, area_url, area_name):
    progs = []
    for href, title, body in ART_RE.findall(html):
        title = re.sub(r"\s+", " ", title.replace("&nbsp;", " ")).strip()
        # perex = text od konce titulku po <time>
        cut = PEREX_END_RE.search(body)
        perex = detext(body[: cut.start()] if cut else body)
        open_from = deadline = None
        mf = DATE_FROM_RE.search(perex)
        if mf:
            open_from = _iso(*mf.groups())
        mt = DATE_TO_RE.search(perex)
        if mt:
            deadline = _iso(*mt.groups())
        url = href if href.startswith("http") else BASE + href
        popis = area_name + (" — " + perex if perex else "")
        progs.append({
            "nazev": title, "open_from": open_from, "deadline": deadline,
            "status": None, "alokace_czk": None, "max_czk": None,
            "popis": popis.strip(), "eligible": None, "kod": None, "url": url,
        })
    return progs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_msk.json")
    a = ap.parse_args()

    idx = fetch(INDEX)
    # mapuj pgid -> název oblasti (první výskyt s textovým popiskem = oblast)
    areas = {}
    for href, pgid, label in AREA_RE.findall(idx):
        label = re.sub(r"\s+", " ", label).strip()
        if pgid not in areas and label:
            areas[pgid] = (BASE + href, label)
    print(f"oblastí z rozcestníku: {len(areas)} -> {sorted(int(p) for p in areas)}", file=sys.stderr)

    seen, programs, per_area = set(), [], {}
    for pgid, (area_url, area_name) in areas.items():
        try:
            html = fetch(area_url)
        except Exception as e:
            print(f"  warn pgid={pgid}: {str(e)[:60]}", file=sys.stderr); continue
        kept = 0
        for rec in parse_area(html, area_url, area_name):
            key = rec["url"]  # friendly URL je per-program unikátní (id v slugu)
            if key in seen:
                continue
            seen.add(key); programs.append(rec); kept += 1
        per_area[area_name] = kept

    out = {
        "source": "msk.cz", "kraj": "Moravskoslezský kraj", "platform": "msk_html",
        "programs": programs,
    }
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "MSK_HARVEST", "programs": len(programs),
                      "per_area": per_area, "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
