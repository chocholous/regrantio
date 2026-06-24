#!/usr/bin/env python3
"""Liberecký kraj harvester — dotační programy z dotace.kraj-lbc.cz (server-rendered HTML).

Homepage má odkazy na ~20 oblastních podstránek (/regionalni-rozvoj, /skolstvi-a-mladez, …).
Každá oblast je listing s bloky `grants-list-item opened|closed`: item-label (název),
item-state (Otevřen/Uzavřen), <a href> (absolutní URL detailu). Status web UVÁDÍ explicitně →
mapuje se Otevřen→open, Uzavřen→closed (žádný dopočet z dat).

Detail (-dNNNNNN.htm) má prózu se štítky `Vyhlášení: / Zahájení: / Ukončení: DD.MM.YYYY`:
Zahájení = open_from, Ukončení = deadline. Plný text detailu se ukládá do _text (lossless).
Oblasti se NEhardcodují — parsují se z odkazů homepage. Dedup napříč oblastmi dle URL.

Usage: python3 scripts/liberecky_harvest.py [--out data/h_kraj_liberecky.json] [--no-detail]
"""
import argparse, html as htmllib, json, re, sys, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)

BASE = "https://dotace.kraj-lbc.cz"
# Oblastní podstránky = relativní odkazy /slug bez tečky/dvojtečky (ne getFile, ne externí, ne kotva).
AREA_HREF = re.compile(r'href="(/[a-z0-9][a-z0-9-]+)"')
# Co NENÍ dotační oblast (servisní/info stránky z homepage menu).
AREA_SKIP = {"akce-podporovane-libereckym-krajem", "zastity-bez-financni-podpory",
             "zastity-s-financni-podporou", "krizovy-fond"}
ITEM = re.compile(
    r'grants-list-item\s+(opened|closed)"(.*?)</a>', re.S)
STATE_MAP = {"otevřen": "open", "uzavřen": "closed"}
DATE_LABELS = {"open_from": r"Zahájení:\s*([\d.]+)", "deadline": r"Ukončení:\s*([\d.]+)"}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return http_util.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " ").replace("&quot;", '"')
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", h)).strip()


def _iso(s):
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", (s or "").strip())
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def find_areas(home_html):
    seen, areas = set(), []
    for m in AREA_HREF.finditer(home_html):
        slug = m.group(1).lstrip("/")
        if slug in AREA_SKIP or slug in seen:
            continue
        seen.add(slug)
        areas.append(BASE + m.group(1))
    return areas


def parse_area(html):
    """Vrátí seznam (status, nazev, url) ze všech grants-list-item bloků oblasti."""
    out = []
    for m in ITEM.finditer(html):
        blk = m.group(2)
        st = re.search(r'item-state">\s*(.*?)\s*</div>', blk, re.S)
        label = re.search(r'item-label">\s*(.*?)\s*</div>', blk, re.S)
        href = re.search(r'<a href="([^"]+)"', blk)
        if not (st and label and href):
            continue
        raw = re.sub(r"\s+", " ", st.group(1)).strip()
        status = STATE_MAP.get(raw.lower())
        if status is None:
            print(f"  ⚠ neznámý status {raw!r} u {label.group(1)[:40]!r}", file=sys.stderr)
            continue
        nazev = re.sub(r"\s+", " ", htmllib.unescape(label.group(1))).strip()
        out.append((status, nazev, href.group(1).strip()))
    return out


def enrich_detail(url):
    """Z detailu vytáhne datumy + plný text (lossless)."""
    rec = {"open_from": None, "deadline": None, "_text": None}
    try:
        text = detext(fetch(url))
    except Exception as e:
        print(f"  warn detail {url[-40:]}: {str(e)[:50]}", file=sys.stderr)
        return rec
    for k, pat in DATE_LABELS.items():
        m = re.search(pat, text)
        if m:
            rec[k] = _iso(m.group(1))
    rec["_text"] = text[:4000]
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_liberecky.json")
    ap.add_argument("--no-detail", action="store_true",
                    help="přeskoč fetch detailů (bez datumů, rychlé)")
    a = ap.parse_args()

    home = fetch(BASE + "/")
    areas = find_areas(home)
    print(f"nalezeno {len(areas)} oblastí", file=sys.stderr)

    seen_urls, programs = set(), []
    for area_url in areas:
        try:
            html = fetch(area_url)
        except Exception as e:
            print(f"  warn oblast {area_url}: {str(e)[:50]}", file=sys.stderr)
            continue
        items = parse_area(html)
        print(f"  {area_url[len(BASE):]}: {len(items)} programů", file=sys.stderr)
        for status, nazev, url in items:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            rec = {"nazev": nazev, "open_from": None, "deadline": None, "status": status,
                   "alokace_czk": None, "max_czk": None, "popis": None,
                   "eligible": None, "kod": None, "url": url}
            if not a.no_detail:
                d = enrich_detail(url)
                rec["open_from"] = d["open_from"]
                rec["deadline"] = d["deadline"]
                if d["_text"]:
                    rec["_text"] = d["_text"]
            programs.append(rec)

    out = {"source": "dotace.kraj-lbc.cz", "kraj": "Liberecký kraj",
           "platform": "liberecky_html", "programs": programs}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n_open = sum(1 for p in programs if p["status"] == "open")
    print(json.dumps({"MARKER": "LIBERECKY_HARVEST", "areas": len(areas),
                      "programs": len(programs), "open": n_open,
                      "closed": len(programs) - n_open, "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
