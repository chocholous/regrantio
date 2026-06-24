#!/usr/bin/env python3
"""Karlovarský kraj harvester přes WAYBACK MACHINE (web.archive.org).

www.kr-karlovarsky.cz je za WEDOS WAF (blokuje curl/Playwright/Apify → 301-loop). Wayback
Machine ale má archivované veřejné listingy dotačních programů per oblast (prošly přes WAF
dřív). To je legitimní fallback.

ZDROJ: kr-karlovarsky.cz/dotace/dotacni-programy-karlovarskeho-kraje{,/oblast-*,/socialni-oblast,
/individualni-dotace}. Každý listing je server-rendered HTML: program = <article> blok s
<h3><a href="/dotace/SLUG">NÁZEV</a>, <div class="details"> (Oblast: <oblast>; Příjem
elektronických žádostí: DD.MM.YYYY - DD.MM.YYYY) a status badge v article-tags. Alokace NENÍ
na listingu (jen na detailu) → alokace_czk=null (kontrakt: nevymýšlet).

POSTUP:
 1. CDX API → pro KAŽDOU oblast-stránku nejnovější snapshot (2025-2026).
 2. RAW archiv bez Wayback toolbaru: .../web/{TS}id_/{ORIG_URL} (gzip → dekomprese).
 3. Parse <article> bloků (nazev + oblast + open_from/deadline + url).
 4. Dedup dle url (parent index = featured cross-area výběr, překrývá se s oblastmi).

Status dopočítá ingest z termínů (kontrakt: status=null). Archiv je z 2025/2026 → mnohé
programy mají deadline leden–březen 2026 (= už uzavřené); to neřešíme.

Usage: python3 scripts/karlovarsky_wayback_harvest.py [--out data/h_kraj_karlovarsky.json]
"""
import argparse, gzip, json, re, sys, urllib.parse, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)

WB = "https://web.archive.org/web"
CDX = "http://web.archive.org/cdx/search/cdx"
SITE = "https://www.kr-karlovarsky.cz"
INDEX_PATH = "/dotace/dotacni-programy-karlovarskeho-kraje"
# CDX bere nejnovější snapshot v tomto okně (provoz: ~2025-2026 ročník programů)
CDX_FROM = "20250101"
CDX_TO = "20260605"
# safety pojistka proti runaway fetchům (NE coverage cap — při dosažení ⚠ log)
MAX_FETCHES = 60
# obsolete sloučená oblast (rozdělena na oblast-skolstvi + oblast-sportu) → přeskoč
SKIP_AREAS = {"oblast-skolstvi-sportu"}


def fetch(url, decode=True):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
    r = http_util.urlopen(req, timeout=60)
    data = r.read()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data.decode("utf-8", "replace") if decode else data


def cdx_areas():
    """CDX → {original_url: newest_timestamp} pro listing stránky (bez ?page/?utm)."""
    q = urllib.parse.urlencode({
        "url": "kr-karlovarsky.cz/dotace/dotacni-programy-karlovarskeho-kraje*",
        "from": CDX_FROM, "to": CDX_TO, "output": "json",
        "fl": "original,timestamp,statuscode", "filter": "statuscode:200",
    })
    rows = json.loads(fetch(f"{CDX}?{q}"))
    best = {}
    for row in rows[1:]:
        orig, ts = row[0], row[1]
        if "?" in orig:  # přeskoč ?page=N (2024 archiv) i ?utm varianty
            continue
        slug = orig.rstrip("/").rsplit("/", 1)[-1]
        if slug in SKIP_AREAS:
            continue
        if orig not in best or ts > best[orig]:
            best[orig] = ts
    return best


def detext_attr(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).replace("&nbsp;", " ").strip()


def _iso(s):
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", (s or "").strip())
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def parse_dates(details_text):
    """Z 'Příjem elektronických žádostí: DD.MM.YYYY - DD.MM.YYYY' → (open_from, deadline).
    Varianty: 'DD.MM.YYYY -' (jen start), 'DD.MM.YYYY' (jen jeden); preferuj elektronické."""
    m = re.search(r"Příjem elektronických žádostí:\s*([\d.]+)\s*(?:-\s*([\d.]+)?)?", details_text)
    if not m:
        m = re.search(r"Příjem (?:tištěných )?žádostí:\s*([\d.]+)\s*(?:-\s*([\d.]+)?)?", details_text)
    if not m:
        return None, None
    return _iso(m.group(1)), _iso(m.group(2)) if m.group(2) else None


def parse_oblast(details_text):
    m = re.search(r"Oblast:\s*(.+?)\s*(?:Příjem|$)", details_text)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def parse_listing(html):
    """Vrátí list programů z <article> bloků listingu."""
    out = []
    for a in re.findall(r"<article>.*?</article>", html, re.S):
        href_m = re.search(r'<h3>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', a, re.S)
        if not href_m:
            continue
        href = href_m.group(1)
        nazev = detext_attr(href_m.group(2))
        if not nazev:
            continue
        # absolutní URL na původní web (kontrakt to dovoluje bez wayback prefixu)
        url = href if href.startswith("http") else urllib.parse.urljoin(SITE, href)
        # zahoď wayback prefix kdyby se v hrefu vyskytl
        url = re.sub(r"^https?://web\.archive\.org/web/\d+\w*/", "", url)
        det_m = re.search(r'<div class="details">(.*?)</div>', a, re.S)
        det = detext_attr(det_m.group(1)) if det_m else ""
        open_from, deadline = parse_dates(det)
        out.append({
            "nazev": nazev,
            "open_from": open_from,
            "deadline": deadline,
            "status": None,
            "alokace_czk": None,   # alokace není na listingu, jen na detailu
            "max_czk": None,
            "popis": parse_oblast(det),   # oblast → pomůže klasifikaci
            "eligible": None,
            "kod": None,
            "url": url,
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_karlovarsky.json")
    a = ap.parse_args()

    areas = cdx_areas()
    print(f"CDX: {len(areas)} oblast-stránek se snapshotem 2025+", file=sys.stderr)
    newest_ts = max(areas.values()) if areas else None

    programs, seen, fetches = [], set(), 0
    out = {"source": "kr-karlovarsky.cz", "kraj": "Karlovarský kraj",
           "platform": "karlovarsky_wayback", "programs": programs}

    def save():
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # nejdřív parent index (featured cross-area výběr), pak jednotlivé oblasti
    for orig in sorted(areas, key=lambda u: (u != f"{SITE}{INDEX_PATH}", u)):
        if fetches >= MAX_FETCHES:
            print(f"⚠ MAX_FETCHES ({MAX_FETCHES}) dosažen — možný runaway/uniklé oblasti", file=sys.stderr)
            break
        ts = areas[orig]
        try:
            html = fetch(f"{WB}/{ts}id_/{orig}")
            fetches += 1
        except Exception as e:
            print(f"  warn {orig.rsplit('/',1)[-1]}: {str(e)[:60]}", file=sys.stderr)
            continue
        progs = parse_listing(html)
        added = 0
        for p in progs:
            if p["url"] in seen:
                continue
            seen.add(p["url"])
            programs.append(p)
            added += 1
        print(f"  {orig.split('/dotace/')[-1]} [{ts}]: {len(progs)} článků, {added} nových",
              file=sys.stderr)
        save()  # průběžné ukládání

    save()
    with_terms = sum(1 for p in programs if p["open_from"] or p["deadline"])
    print(json.dumps({"MARKER": "KARLOVARSKY_WAYBACK_HARVEST", "kept": len(programs),
                      "oblasti": len(areas), "with_terms": with_terms,
                      "newest_snapshot": newest_ts, "fetches": fetches, "out": a.out},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
