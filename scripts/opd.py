#!/usr/bin/env python3
"""OP Doprava 2021–2027 (opd3.opd.cz) — layer-1 harvest výzev.

STRUKTURA PŘED PRÓZOU: `https://opd3.opd.cz/stranka/vyzvy` je jedna HTML TABULKA, kde
řádek = výzva se sloupci:
    Číslo | Název výzvy | Datum vyhlášení | Datum zpřístupnění v MS2021+ |
    Datum ukončení příjmu žádostí | (odkaz na detail /stranka/vyzva-NN)
→ open_from/deadline se berou DETERMINISTICKY z buněk, žádný LLM. Status počítá kód.

Pozn.: v REMAINING byl OP Doprava veden jako blocker („ne-WP, opd.cz") — web mezitím
přešel na opd3.opd.cz se server-rendered tabulkou, takže je normálně harvestovatelný
(ověřeno 2026-07-31: 13 výzev v tabulce).

Detail výzvy = server-rendered stránka s prózou + přílohami (texty výzvy v PDF).

Výstup (kontrakt jako ostatní *_documents.jsonl):
  data/opd_documents.jsonl  {host, title, url, kind, cislo_vyzvy, open_from, deadline,
                             open_from_raw, deadline_raw, ms2021_od, body_text,
                             attachments[], n_attachments}

Spuštění (z kořene repa):
  python scripts/opd.py                    # plný harvest
  python scripts/opd.py --no-detail        # jen tabulka (rychlé)
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse
import html as H
import json
import os
import re
import sys
from urllib.parse import urljoin

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util  # noqa: E402  (jednotná TLS politika)

BASE = "https://opd3.opd.cz"
LISTING = f"{BASE}/stranka/vyzvy"
HOST = "opd.cz"
UA = "Mozilla/5.0 (compatible; regrantio/1.0)"
DOC_RE = re.compile(r"\.(pdf|docx?|xlsx?|zip)(\?|$)", re.I)


def fetch(url, timeout=60):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with http_util.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def strip_tags(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</div>|</tr>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[ \t]+", " ", H.unescape(s)).strip()


def cz_iso(s):
    """'30. 06. 2029' / '5.10.2022' → ISO; jinak None."""
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)", s or "")
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{y}-{mo:02d}-{d:02d}" if 1 <= d <= 31 and 1 <= mo <= 12 else None


def parse_listing(page):
    """Tabulka výzev → [{cislo, title, url, vyhlaseni, ms2021, deadline}]."""
    start = page.find("<table")
    end = page.find("</table>", start)
    if start < 0 or end < 0:
        return []
    table = page[start:end]
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S | re.I):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)
        if len(cells) < 5:
            continue
        vals = [strip_tags(c) for c in cells]
        if not re.fullmatch(r"\d{1,3}", vals[0].strip()):   # hlavička / neplatný řádek
            continue
        href = None
        m = re.search(r'href="([^"]+)"', tr)
        if m:
            href = urljoin(BASE, H.unescape(m.group(1)))
        out.append({
            "cislo": vals[0].strip(),
            "title": re.sub(r"\s+", " ", vals[1]).strip(),
            "url": href or LISTING,
            "vyhlaseni_raw": vals[2].strip(),
            "ms2021_raw": vals[3].strip(),
            "deadline_raw": vals[4].strip(),
        })
    return out


def parse_detail(page, url):
    """Detail výzvy: hlavní text + přílohy (PDF/DOCX texty výzvy)."""
    body = page
    for marker in ('<main', '<div id="content"', '<article'):
        i = body.find(marker)
        if i > 0:
            body = body[i:]
            break
    j = body.find("<footer")
    if j > 0:
        body = body[:j]
    atts = []
    seen = set()
    for m in re.finditer(r'href="([^"]+)"[^>]*>(.*?)</a>', body, re.S | re.I):
        u = urljoin(url, H.unescape(m.group(1)))
        if DOC_RE.search(u) and u not in seen:
            seen.add(u)
            atts.append({"url": u, "label": re.sub(r"\s+", " ", strip_tags(m.group(2)))[:120]})
    return strip_tags(body), atts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/opd_documents.jsonl")
    ap.add_argument("--no-detail", action="store_true", help="jen tabulka, bez stahování detailů")
    ap.add_argument("--timeout", type=int, default=60)
    a = ap.parse_args()

    rows = parse_listing(fetch(LISTING, a.timeout))
    print(f"  listing: {len(rows)} výzev", file=sys.stderr)

    recs, det_ok = [], 0
    for r in rows:
        body, atts = "", []
        if not a.no_detail and r["url"] != LISTING:
            try:
                body, atts = parse_detail(fetch(r["url"], a.timeout), r["url"])
                det_ok += 1
            except Exception as e:  # noqa: BLE001
                print(f"  [err] detail {r['cislo']}: {type(e).__name__}", file=sys.stderr)
        recs.append({
            "host": HOST, "web": HOST, "kind": "vyzva",
            "title": f"Výzva č. {r['cislo']} OP Doprava – {r['title']}" if r["title"] else f"Výzva č. {r['cislo']} OP Doprava",
            "url": r["url"], "date": None,
            "cislo_vyzvy": r["cislo"],
            "open_from": cz_iso(r["vyhlaseni_raw"]),
            "deadline": cz_iso(r["deadline_raw"]),
            "open_from_raw": r["vyhlaseni_raw"],
            "deadline_raw": r["deadline_raw"],
            "ms2021_od": cz_iso(r["ms2021_raw"]),
            "body_text": body,
            "attachments": atts, "n_attachments": len(atts),
        })

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"MARKER": "OPD_HARVEST", "vyzvy": len(recs), "details_ok": det_ok,
                      "with_deadline": sum(1 for r in recs if r["deadline"]),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
