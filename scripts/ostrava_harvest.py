#!/usr/bin/env python3
"""Ostrava harvester — dotační programy/výzvy města Ostravy a jeho obvodů.

dotace.ostrava.cz běží na WP (téma dotace-v2), ale výzvy NEJSOU custom post type ani
v page contentu — front-end je app-shell, který tahá listing přes admin-ajax action
`get_appeals_data` (čistý JSON: provider/category/area/appeal/id_wp/from/url_vyzva).
Listing nemá termíny ani popis → ty bereme z server-renderovaného detailu
(`/vyzvy-k-dotaci-vyzva/?id_wp=...`), kde jsou štítky "Lhůta pro podání žádosti - Od/Do
DD.MM.YYYY" a próza "Informace pro žadatele ... Podmínky".

Vrstva 1, lossless: ukládá parsovaná pole + plný text detailu (_text). Status dopočítá
ingest z termínů (open_from/deadline). Cíl = vyhlášené výzvy/programy, NE awards
(awards žijí na samostatné page /prehled-poskytnutych-dotaci/, sem nesaháme).

Usage: python3 scripts/ostrava_harvest.py [--out data/h_mesto_ostrava.json]
"""
import argparse, json, re, sys, time, urllib.parse, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)

BASE = "https://dotace.ostrava.cz"
AJAX = BASE + "/wp-admin/admin-ajax.php"
LISTING_PAGE = BASE + "/vyzvy-k-dotaci/"       # nese window._appealsAjax s živým nonce
LISTING_ACTION = "get_appeals_data"
DETAIL_PATH = "/vyzvy-k-dotaci-vyzva/"
UA = "Mozilla/5.0"

# nonce je per-session, vázaný na admin-ajax (bez něj 403) → scrapujeme z listing page
RE_NONCE = re.compile(r'window\._appealsAjax\s*=\s*\{[^}]*"nonce"\s*:\s*"([a-f0-9]+)"')

# "Lhůta pro podání žádosti - Od 30.04.2026 00:00" / "... - Do 01.07.2026 23:59"
RE_OD = re.compile(r"Lh[uů]ta pro pod[aá]n[ií] [zž][aá]dosti\s*-\s*Od\s*(\d{1,2}\.\d{1,2}\.\d{4})")
RE_DO = re.compile(r"Lh[uů]ta pro pod[aá]n[ií] [zž][aá]dosti\s*-\s*Do\s*(\d{1,2}\.\d{1,2}\.\d{4})")


def fetch(url, data=None, ajax=False):
    headers = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "cs,en;q=0.8"}
    if ajax:
        # admin-ajax odmítá holý urllib request (403); browser posílá XHR hlavičky
        headers["X-Requested-With"] = "XMLHttpRequest"
        headers["Referer"] = BASE + "/vyzvy-k-dotaci/"
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    req = urllib.request.Request(url, data=data, headers=headers)
    return http_util.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    h = h.replace("&nbsp;", " ").replace("&#8211;", "-").replace("&#038;", "&")
    h = h.replace("&amp;", "&").replace("&quot;", '"').replace("&#8217;", "'")
    return re.sub(r"\s+", " ", h).strip()


def iso(s):
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s or "")
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def clean_url(u):
    """Listing URL je HTML-encoded (&#038;) a kategorie nese ne-ASCII v query → narovnej
    entity a percent-encoduj ne-ASCII, jinak urllib spadne na 'ascii' codec."""
    u = (u or "").replace("&#038;", "&").replace("&amp;", "&")
    return urllib.parse.quote(u, safe="%/:?=&#")


def parse_detail(text, title):
    """Z prózy detailu vytáhni termíny + popis. Vrací (open_from, deadline, popis)."""
    of = RE_OD.search(text)
    dl = RE_DO.search(text)
    open_from = iso(of.group(1)) if of else None
    deadline = iso(dl.group(1)) if dl else None

    # popis = blok "Informace pro žadatele ... " až do "Podmínky" (nebo do lhůty/příloh)
    popis = None
    i = text.find("Informace pro žadatele")
    if i >= 0:
        j = i + len("Informace pro žadatele")
        ends = [text.find(a, j) for a in ("Podmínky", "Přílohy ke stažení", "Lhůta pro podání")]
        ends = [e for e in ends if e > 0]
        end = min(ends) if ends else j + 2000
        popis = text[j:end].strip(" -–—") or None
    return open_from, deadline, popis


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_ostrava.json")
    a = ap.parse_args()

    # vrstva 1a: vytáhni živý nonce z listing page (bez něj admin-ajax vrací 403)
    m = RE_NONCE.search(fetch(LISTING_PAGE))
    if not m:
        print("⚠ nonce z listing page nenalezen — _appealsAjax chybí?", file=sys.stderr)
        sys.exit(1)
    nonce = m.group(1)
    print(f"nonce: {nonce}", file=sys.stderr)

    # vrstva 1b: listing přes admin-ajax (čistý JSON)
    payload = urllib.parse.urlencode({"action": LISTING_ACTION, "nonce": nonce}).encode()
    raw = json.loads(fetch(AJAX, data=payload, ajax=True))
    if not raw.get("success"):
        print(f"⚠ admin-ajax {LISTING_ACTION} nevrátil success: {str(raw)[:200]}", file=sys.stderr)
        sys.exit(1)
    rows = raw["data"]["rows"]
    print(f"listing: {len(rows)} výzev z {LISTING_ACTION}", file=sys.stderr)

    out = {"source": "dotace.ostrava.cz", "kraj": "Moravskoslezský kraj", "obec": "Ostrava",
           "uroven": "obec", "platform": "ostrava_wp", "programs": []}
    seen = set()
    for r in rows:
        idw = r.get("id_wp")
        if not idw or idw in seen:
            continue
        seen.add(idw)
        nazev = (r.get("appeal") or "").strip()
        region = r.get("provider_code") or ""
        # kanonická, stabilní URL (id_wp + region); k fetchi použij plnou listing URL
        url = f"{BASE}{DETAIL_PATH}?id_wp={idw}" + (f"&region={region}" if region else "")
        fetch_url = clean_url(r.get("url_vyzva")) or url

        open_from = deadline = popis = None
        text = ""
        try:
            html = fetch(fetch_url)
            text = detext(html)
            open_from, deadline, popis = parse_detail(text, nazev)
        except Exception as e:
            print(f"  ⚠ detail {idw}: {str(e)[:80]}", file=sys.stderr)

        rec = {
            "nazev": nazev,
            "open_from": open_from,
            "deadline": deadline,
            "status": None,                       # dopočítá ingest z termínů
            "alokace_czk": None,                  # v detailu se nevyskytuje strukturovaně
            "max_czk": None,
            "popis": popis,
            "eligible": None,
            "kod": idw,
            "url": url,
            # lossless extra (ingest_kraj ignoruje neznámé klíče, ale držíme grounding)
            "_provider": (r.get("provider") or "").strip() or None,
            "_provider_code": r.get("provider_code"),
            "_category": r.get("category"),
            "_area": r.get("area"),
            "_year": r.get("from"),
            "_text": text[:6000] if text else "",
        }
        out["programs"].append(rec)
        # ukládej průběžně
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(0.3)

    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with_dl = sum(1 for p in out["programs"] if p["deadline"])
    print(json.dumps({"MARKER": "OSTRAVA_HARVEST", "kept": len(out["programs"]),
                      "with_deadline": with_dl, "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
