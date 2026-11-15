#!/usr/bin/env python3
"""Jihočeský kraj harvester — vyhlášené dotační výzvy (server-rendered HTML).

kraj-jihocesky.cz/cs/ku_dotace/vyhlasene = jedna stránka s accordionem
<dl class="ckeditor-accordion">. Každá výzva = <dt> (label "Datum zveřejnění:" + <b>název</b>,
s data-target="#NNNN") + <dd> (Charakteristika = popis, Kontakty, Harmonogram s
"Datum vyhlášení" → open_from a "Datum ukončení" → deadline). Strukturovaný parse, žádný LLM.

Listing nemá alokaci / oprávněné žadatele / kód → null (NEvymýšlet). Per-program detail
neexistuje (accordion), url = listing#NNNN. Status dopočítá ingest z termínů.

EU sekce (/cs/dotace-fondy-eu/aktualni-vyzvy-informace) je čistě informační (semináře,
metodiky, novinky Interreg) — žádné samostatné otevřené krajské výzvy → vynechána.

ROZŠÍŘENO 2026-11-15 (audit pokrytí: z kraje 5 živých záznamů):
  • `ku_dotace/ukoncene` („ve stadiu schvalování“) = tentýž accordion s ukončenými
    výzvami; nesou loňské ročníky.
  • Programové dotace (kultura, sport, venkov, SDH, …, kolem 25 programů a 365 mil. Kč)
    accordion nikdy neukazuje: kraj je přijímá přes Portál občana (GINIS, za
    přihlášením). Veřejně je jen „Tabulka – dotační programy Jčk <rok>“ (PDF) na stránce
    programových dotací: název, opatření, alokace, popis. Bere se nejnovější tabulka,
    jen když je její rok letošní nebo pozdější; termíny v ní nejsou, stav tedy zůstane
    `unknown` a v příštím roce ho uzavře rok v názvu.
  • Řádek tabulky a pozdější výzva téhož programu sdílí `klic`, takže upsert záznam
    posune z plánovaného na vyhlášený a nevznikne dvojice.
  Tabulku čte pymupdf podle čar tabulky (pdftotext sloupce slévá). Bez pymupdf se
  tabulka přeskočí s varováním a zbytek sběru běží dál.

Usage: python3 scripts/jihocesky_harvest.py [--out data/h_kraj_jihocesky.json]
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse, json, re, sys, unicodedata, urllib.request
from datetime import date
from urllib.parse import unquote, urljoin
import http_util   # jednotná TLS politika (audit #7/#32)

LISTING = "https://www.kraj-jihocesky.cz/cs/ku_dotace/vyhlasene"
CLOSED = "https://www.kraj-jihocesky.cz/cs/ku_dotace/ukoncene"
PROGRAMS = "https://www.kraj-jihocesky.cz/cs/dotace-fondy-eu/programove-dotace-jihoceskeho-kraje"
TABLE_LINK = re.compile(r'href="([^"]+\.pdf)"[^>]*>\s*Tabulka\s*[-–]\s*dotační programy Jčk (\d{4})\s*<', re.I)

# rozcestníky / awards / čistě informační položky, které nejsou otevřené výzvy
SKIP = re.compile(r"poskytnut|schválen|příjemc|registr příjemc|seznam příjemc|vyúčtování", re.I)


def fetch_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return http_util.urlopen(req, timeout=30).read()


def fetch(url):
    return fetch_bytes(url).decode("utf-8", "replace")


def unescape(s):
    return (s.replace("&#8211;", "–").replace("&#8212;", "—").replace("&nbsp;", " ")
            .replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
            .replace("&lt;", "<").replace("&gt;", ">"))


def detext(html):
    h = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(h)).strip()


def _iso(s):
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s or "")
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def _czk(s):
    """Vyparsuj int z '1 000 000 Kč' (mezery/nbsp jako oddělovače tisíců)."""
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None


def parse_block(dt_html, dd_html):
    rec = {"nazev": None, "open_from": None, "deadline": None, "status": None,
           "alokace_czk": None, "max_czk": None, "popis": None, "eligible": None,
           "kod": None, "url": None}

    mt = re.search(r"</span>\s*<b>(.*?)</b>", dt_html, re.S)
    if not mt:
        return None
    rec["nazev"] = detext(mt.group(1))

    mid = re.search(r'data-target="#(\d+)"', dt_html)
    rec["url"] = f"{LISTING}#{mid.group(1)}" if mid else LISTING

    # Charakteristika → popis
    mp = re.search(r"<h3>\s*Charakteristika\s*</h3>\s*<p>(.*?)</p>", dd_html, re.S)
    if mp:
        popis = detext(mp.group(1))
        rec["popis"] = popis or None

    # Harmonogram: Datum vyhlášení → open_from, Datum ukončení → deadline
    mo = re.search(r"Datum vyhlášení:\s*<b>(.*?)</b>", dd_html, re.S)
    if mo:
        rec["open_from"] = _iso(mo.group(1))
    md = re.search(r"Datum ukončení:\s*<b>(.*?)</b>", dd_html, re.S)
    if md:
        rec["deadline"] = _iso(md.group(1))

    # alokace / oprávnění žadatelé / kód se na listingu nevyskytují → null
    return rec


def accordion(listing, required=True):
    """Bloky <dt>/<dd> stránky výzev; adresa výzvy = stránka#id."""
    html = fetch(listing)
    m = re.search(r'<dl class="ckeditor-accordion">(.*?)</dl>', html, re.S)
    if not m:
        print(f"⚠ accordion <dl> nenalezen na {listing} — HTML struktura se změnila", file=sys.stderr)
        if required:
            sys.exit(2)
        return []
    pairs = re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", m.group(1), re.S)
    print(f"{listing}: {len(pairs)} bloků v accordionu", file=sys.stderr)
    out = []
    for dt_html, dd_html in pairs:
        rec = parse_block(dt_html, dd_html)
        if rec and rec["url"].startswith(LISTING + "#"):
            rec["url"] = listing + rec["url"][len(LISTING):]
        out.append(rec)
    return out


def norm(name):
    """Jméno programu k porovnání: bez diakritiky, roku, „dotační program“ a jména kraje."""
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(?:dotacni (?:program|titul)|v jihocesk\w* kraj\w*|jihocesk\w* kraj\w*|pro rok|v roce|na rok)\b", " ", s)
    s = re.sub(r"\b20\d{2}\b|[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def slug(name):
    return re.sub(r"\s+", "-", norm(name))[:60].strip("-")


def cell_text(page, rect):
    """Text buňky s mezerami podle odstupu znaků: PDF mezery jako znaky často nemá."""
    import pymupdf
    lines = []
    for block in page.get_text("rawdict", clip=pymupdf.Rect(rect))["blocks"]:
        for line in block.get("lines", []):
            s, prev = "", None
            for span in line["spans"]:
                for ch in span["chars"]:
                    if prev is not None and ch["bbox"][0] - prev > 0.18 * span["size"] and not s.endswith(" "):
                        s += " "
                    s += ch["c"]
                    prev = ch["bbox"][2]
            lines.append(s)
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def table_programs(pdf_bytes):
    """Řádky tabulky programů: název, opatření, alokace, popis. Záhlaví a součet se vynechají."""
    import pymupdf
    out = []
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            for table in page.find_tables().tables:
                for row in table.rows:
                    cells = [cell_text(page, c) if c else "" for c in row.cells]
                    if len(cells) < 5 or not cells[4].startswith("Cílem"):
                        continue
                    amount = re.sub(r"\D", "", cells[3])
                    out.append({"nazev": cells[1], "opatreni": cells[2],
                                "alokace": int(amount) if amount else None, "popis": cells[4]})
    return out


def planned(today):
    """Programy z nejnovější tabulky, je-li její rok letošní nebo pozdější."""
    links = [(int(y), urljoin(PROGRAMS, unescape(u))) for u, y in TABLE_LINK.findall(fetch(PROGRAMS))]
    if not links:
        print("⚠ tabulka programových dotací na stránce nenalezena", file=sys.stderr)
        return []
    year, url = max(links)
    if year < today.year:
        return []
    try:
        rows = table_programs(fetch_bytes(url))
    except ImportError:
        print("⚠ pymupdf chybí: tabulka programových dotací přeskočena", file=sys.stderr)
        return []
    progs = []
    for r in rows:
        name = r["nazev"] if re.search(r"\b20\d{2}\b", r["nazev"]) else f"{r['nazev']} {year}"
        measures = r["opatreni"] if r["opatreni"] and not r["opatreni"].startswith("Nemá") else ""
        progs.append({
            "nazev": name, "open_from": None, "deadline": None, "status": None,
            "alokace_czk": r["alokace"], "max_czk": None,
            "popis": " ".join(x for x in (r["popis"], measures) if x) or None,
            "eligible": None, "kod": None, "url": f"{unquote(url)}#{slug(r['nazev'])}",
            "klic": f"jck-{year}-{slug(r['nazev'])}", "_rok": year,
        })
    print(f"tabulka {year}: {len(progs)} programů", file=sys.stderr)
    return progs


def same_program(a, b):
    x, y = norm(a), norm(b)
    return len(min(x, y, key=len)) >= 12 and (x in y or y in x)


def same_year(call, year):
    y = str(year)
    return y in call["nazev"] or any((call[k] or "").startswith(y) for k in ("open_from", "deadline"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_jihocesky.json")
    ap.add_argument("--listing", default=LISTING)
    ap.add_argument("--today", default=date.today().isoformat())
    a = ap.parse_args()

    calls = accordion(a.listing) + accordion(CLOSED, required=False)
    progs, seen, skipped = [], set(), 0
    for rec in calls:
        if not rec or not rec["nazev"]:
            continue
        if SKIP.search(rec["nazev"]):
            skipped += 1
            continue
        key = (rec["nazev"], rec["deadline"])
        if key in seen:
            continue
        seen.add(key)
        progs.append(rec)

    # Plánovaný program, který už kraj vyhlásil, předá výzvě klíč, alokaci a popis.
    merged = 0
    for plan in planned(date.fromisoformat(a.today)):
        year = plan.pop("_rok")
        call = next((c for c in progs if not c.get("klic") and same_program(c["nazev"], plan["nazev"])
                     and same_year(c, year)), None)
        if call:
            call["klic"] = plan["klic"]
            call["alokace_czk"] = call["alokace_czk"] or plan["alokace_czk"]
            call["popis"] = call["popis"] or plan["popis"]
            merged += 1
        else:
            progs.append(plan)

    out = {"source": "kraj-jihocesky.cz", "kraj": "Jihočeský kraj",
           "platform": "jihocesky_html", "programs": progs}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "JIHOCESKY_HARVEST", "kept": len(progs), "merged_with_table": merged,
                      "planned": sum(1 for p in progs if p.get("klic") and not p["deadline"]),
                      "skipped_awards": skipped, "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
