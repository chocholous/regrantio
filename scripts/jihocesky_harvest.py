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

Usage: python3 scripts/jihocesky_harvest.py [--out data/h_kraj_jihocesky.json]
"""
import argparse, json, re, sys, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)

LISTING = "https://www.kraj-jihocesky.cz/cs/ku_dotace/vyhlasene"

# rozcestníky / awards / čistě informační položky, které nejsou otevřené výzvy
SKIP = re.compile(r"poskytnut|schválen|příjemc|registr příjemc|seznam příjemc|vyúčtování", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return http_util.urlopen(req, timeout=30).read().decode("utf-8", "replace")


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_jihocesky.json")
    ap.add_argument("--listing", default=LISTING)
    a = ap.parse_args()

    html = fetch(a.listing)
    m = re.search(r'<dl class="ckeditor-accordion">(.*?)</dl>', html, re.S)
    if not m:
        print("⚠ accordion <dl> nenalezen — HTML struktura se změnila", file=sys.stderr)
        sys.exit(2)
    body = m.group(1)

    # rozdělit na <dt>...</dt> a následné <dd>...</dd>
    pairs = re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", body, re.S)
    print(f"nalezeno {len(pairs)} bloků v accordionu", file=sys.stderr)

    progs, seen, skipped = [], set(), 0
    for dt_html, dd_html in pairs:
        rec = parse_block(dt_html, dd_html)
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

    out = {"source": "kraj-jihocesky.cz", "kraj": "Jihočeský kraj",
           "platform": "jihocesky_html", "programs": progs}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "JIHOCESKY_HARVEST", "kept": len(progs),
                      "skipped_awards": skipped, "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
