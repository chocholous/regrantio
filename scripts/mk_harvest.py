#!/usr/bin/env python3
"""MK (mk.gov.cz, bespoke CMS slug-id `…-cs-NNNN`) — layer-1 lossless harvest dotačních výzev.

STRUKTURA PŘED PRÓZOU (recon docs/recon_ministerstva.md §1, 2026-06-10):
  - Centrální listing `https://mk.gov.cz/zadosti-o-dotace-cs-2023` = 8 HTML tabulek
    seskupených per oblast (Profesionální umění, Literatura a knihovny, …).
    Řádek = NÁZEV DOTAČNÍ VÝZVY (link na detail) | PŘÍJEM ŽÁDOSTÍ (OD) | (DO) | ZPŮSOB PODÁNÍ.
    → deadline/open_from DETERMINISTICKY z buněk, BEZ LLM. STATUS POČÍTÁ KÓD (od/do vs --today).
  - Formáty dat kolísají: `23. 3. 2026`, `01.09.2025 (od 15.00)`, `29.9.2025 od 12:00 hod`,
    kola `1.10.2025 (1. kolo) 1. 4. 2026 (2. kolo)`, `30. 4. 2026(2. kolo)` (bez mezery),
    `duben 2026` (jen měsíc — neparsovat numericky, nechat raw), `bude upřesněno`, prázdná buňka.
    Lossless: raw buňky se VŽDY ukládají (open_from_raw/deadline_raw); parse = min(OD)/max(DO).
  - Detail výzvy = server-rendered stránka, obsah v `<div class="main col-md-9">` … `id="footer"`.
    Přílohy = přímé `/doc/cms_library/*.pdf|docx|…` (nový web NEMÁ /getmedia — recon; pattern
    /getmedia/ přesto pokryt pro případ legacy odkazů). Stažení+konverze přes dsw2_fetch.

Výstup (kontrakt jako vismo_documents.jsonl + navíc deterministická pole z tabulky):
  data/mk_documents.jsonl   {host, title, url, date, kind, body_text, attachments[], n_attachments,
                             area, listing_url, detail_url, submission,
                             open_from_raw, deadline_raw, open_from, deadline,
                             open_from_dates[], deadline_dates[], status, status_source}
  data/mk_files/<host>/<sha16>.<ext> + .txt

Spuštění (z kořene repa):
  python3 scripts/mk_harvest.py                      # plný harvest, --today = dnešek
  python3 scripts/mk_harvest.py --today 2026-06-10   # reprodukovatelný status
"""
import argparse
import hashlib
import html as H
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.parse import urljoin, urlsplit, urlunsplit
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsw2_fetch import (safe_url, sniff_ext, download, convert, ext_of,  # noqa: E402
                        UA, DOC_EXTS, DOC_EXT_RE)
from limits import L  # noqa: E402

HOST = "mk.gov.cz"
HOST_ALIASES = {"mk.gov.cz", "www.mk.gov.cz", "mkcr.cz", "www.mkcr.cz"}
LISTING_URL = "https://mk.gov.cz/zadosti-o-dotace-cs-2023"
# přílohy: nový web = /doc/cms_library/…; /getmedia/ legacy pattern (dsw2_fetch handler umí)
ATT_PATH = re.compile(r"/doc/cms_library/|/getmedia/", re.I)
# české numerické datum D. M. RRRR (mezery kolem teček volitelné; čas/kolo v okolí ignorováno)
CZ_DATE = re.compile(r"(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{4})")


def fetch(url, timeout):
    last = None
    for _ in range(L("http.default_retries") or 1):
        try:
            req = urllib.request.Request(safe_url(url), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def norm_url(url, base):
    """Absolutizace + normalizace: aliasy hostu → mk.gov.cz, https, pryč fragment."""
    u = urljoin(base, H.unescape(url).strip())
    p = urlsplit(u)
    host = p.netloc.lower()
    if host in HOST_ALIASES:
        host = HOST
    return urlunsplit(("https", host, p.path.rstrip("/") or "/", p.query, ""))


def strip_tags(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = H.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def html_to_text(seg):
    """Plný text segmentu — lossless (žádný min-length filtr, jen kolaps whitespace)."""
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", seg, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|li|h\d|tr|table|ul|ol)>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = H.unescape(s).replace("\xa0", " ")
    lines = (re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n"))
    return "\n".join(ln for ln in lines if ln)


def parse_dates(cell_text):
    """→ [date, …] všechna numerická česká data v buňce (kola → víc dat), v pořadí výskytu."""
    out = []
    for d, m, y in CZ_DATE.findall(cell_text or ""):
        try:
            out.append(date(int(y), int(m), int(d)))
        except ValueError:  # 31. 2. apod. — nech raw, neparsuj
            pass
    return out


def compute_status(open_from, deadline, today):
    """STATUS POČÍTÁ KÓD (pravidlo 1 CLAUDE.md): od/do z tabulky vs. today.
    open_from = první datum OD buňky (start 1. kola), deadline = poslední datum DO buňky
    (konec posledního kola)."""
    if deadline and today > deadline:
        return "closed"
    if open_from and today < open_from:
        return "upcoming"
    if open_from and deadline:
        return "open"          # open_from <= today <= deadline
    if deadline:
        return "open"          # bez OD, deadline v budoucnu (např. průběžný příjem do …)
    return "unknown"           # žádné parsovatelné datum (bude upřesněno / jen měsíc slovy)


def parse_listing(page_html):
    """8 tabulek → [{title, detail_url, area, open_from_raw, deadline_raw, submission}, …].
    Heading oblasti = poslední barevný nadpis (#0070c0) před tabulkou."""
    rows = []
    tpos = [m.start() for m in re.finditer(r"<table", page_html)]
    for ti, start in enumerate(tpos):
        end = page_html.find("</table>", start)
        tbl = page_html[start:end]
        prev = page_html[(tpos[ti - 1] if ti else 0):start]
        heads = re.findall(r'<span style="color:#0070c0">(.*?)</span>', prev, re.S)
        area = strip_tags(heads[-1]) if heads else None
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, re.S):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
            if len(cells) < 4:
                continue
            texts = [strip_tags(c) for c in cells]
            if "NÁZEV" in texts[0].upper():       # hlavičkový řádek
                continue
            if not texts[0]:                      # prázdný řádek
                continue
            m = re.search(r'href="([^"]+)"', cells[0])
            rows.append({
                "title": texts[0],
                "detail_url": norm_url(m.group(1), LISTING_URL) if m else None,
                "area": area, "table_index": ti + 1,
                "open_from_raw": texts[1] or None,
                "deadline_raw": texts[2] or None,
                "submission": texts[3] or None,
            })
    return rows, len(tpos)


def content_seg(page_html):
    """Obsahový sloupec detailu: <div class="main col-md-9"> … id="footer" (bez nav menu)."""
    i = page_html.find('<div class="main col-md-9">')
    if i < 0:
        i = page_html.find('id="content"')       # fallback: celý content row
        if i < 0:
            return None
    j = page_html.find('id="footer"', i)
    return page_html[i:j] if j > 0 else page_html[i:]


def page_title(page_html):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", page_html, re.S)
    return strip_tags(m.group(1)) if m else None


def parse_attachments(seg, base_url):
    """Přílohy z obsahového segmentu: /doc/cms_library/ + /getmedia/ + přímé doc-přípony."""
    atts = []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', seg, re.S):
        raw, anchor = m.group(1), strip_tags(m.group(2))
        if raw.startswith(("mailto:", "javascript:", "#", "tel:")):
            continue
        u = norm_url(raw, base_url)
        p = urlsplit(u)
        if p.netloc != HOST:
            continue
        if ATT_PATH.search(p.path) or DOC_EXT_RE.search(u):
            atts.append({"url": u, "name": anchor or os.path.basename(p.path)})
    seen = {}                                     # dedup dle URL, drž nejdelší jméno
    for a in atts:
        k = a["url"]
        if k not in seen or len(a["name"]) > len(seen[k]["name"]):
            seen[k] = a
    return list(seen.values())


def materialize(att, files_dir, timeout, max_bytes):
    """Stáhni + převeď přílohu → doplněný manifest dict (lossless)."""
    url = att["url"]
    ext = ext_of(url)
    if ext == "bin" or ext not in DOC_EXTS:
        m = re.search(r"\.(\w{2,5})$", att.get("name") or "")
        ext = m.group(1).lower() if m and m.group(1).lower() in DOC_EXTS \
            else (sniff_ext(url, timeout) or ext)
    if ext not in DOC_EXTS:
        return {**att, "ext": ext, "bytes": None, "txt_chars": None,
                "txt_path": None, "file_path": None, "status": "not-a-doc"}
    ddir = os.path.join(files_dir, HOST)
    os.makedirs(ddir, exist_ok=True)
    sha = hashlib.sha256(url.encode()).hexdigest()[:16]
    fpath, tpath = os.path.join(ddir, f"{sha}.{ext}"), os.path.join(ddir, f"{sha}.txt")
    if not os.path.exists(fpath):
        nbytes, derr = download(url, fpath, timeout, max_bytes)
        if not nbytes:
            return {**att, "ext": ext, "bytes": None, "txt_chars": None,
                    "txt_path": None, "file_path": None, "status": derr or "download-fail"}
    chars, cerr = (None, None)
    if os.path.exists(tpath):
        chars = len(open(tpath, encoding="utf-8", errors="replace").read())
    else:
        chars, cerr = convert(fpath, ext, tpath, timeout)
    return {**att, "ext": ext, "bytes": os.path.getsize(fpath),
            "txt_chars": chars, "txt_path": tpath if chars else None,
            "file_path": fpath, "status": "ok" if chars else (cerr or "convert-fail")}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listing", default=LISTING_URL)
    ap.add_argument("--out", default="data/mk_documents.jsonl")
    ap.add_argument("--files-dir", default="data/mk_files")
    ap.add_argument("--today", default=None,
                    help="referenční den pro status (YYYY-MM-DD, default dnešek)")
    ap.add_argument("--timeout", type=int, default=L("http.default_timeout_s"))
    ap.add_argument("--workers", type=int, default=L("http.download_workers"))
    args = ap.parse_args()
    today = date.fromisoformat(args.today) if args.today else date.today()
    max_bytes = L("safety.doc_download_max_mb") * 1024 * 1024

    listing_html = fetch(args.listing, args.timeout)
    rows, n_tables = parse_listing(listing_html)
    print(f"  listing: {n_tables} tabulek, {len(rows)} výzev", file=sys.stderr)

    # detail stránky — unikátní URL (víc řádků sdílí 1 detail, např. oborová řízení)
    detail_urls = sorted({r["detail_url"] for r in rows if r["detail_url"]})
    details, att_by_detail, detail_errors = {}, {}, {}
    for u in detail_urls:
        try:
            h = fetch(u, args.timeout)
        except Exception as e:  # noqa: BLE001
            print(f"  [err] detail {type(e).__name__}: {e} {u[:90]}", file=sys.stderr)
            details[u] = None
            att_by_detail[u] = []
            detail_errors[u] = f"{type(e).__name__}: {str(e)[:80]}"
            continue
        seg = content_seg(h)
        details[u] = {"title": page_title(h),
                      "body_text": html_to_text(seg) if seg else html_to_text(h)}
        att_by_detail[u] = parse_attachments(seg or h, u)
    n_det_ok = sum(1 for v in details.values() if v)
    print(f"  detaily: {n_det_ok}/{len(detail_urls)} OK", file=sys.stderr)

    # materializace příloh — dedup přes všechny detaily
    uniq = {}
    for atts in att_by_detail.values():
        for a in atts:
            uniq.setdefault(a["url"], a)
    print(f"  materializace {len(uniq)} unikátních příloh…", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        done = dict(zip(uniq.keys(), ex.map(
            lambda a: materialize(a, args.files_dir, args.timeout, max_bytes), uniq.values())))

    recs = []
    for r in rows:
        od = parse_dates(r["open_from_raw"])
        do = parse_dates(r["deadline_raw"])
        open_from = min(od).isoformat() if od else None
        deadline = max(do).isoformat() if do else None
        det = details.get(r["detail_url"]) if r["detail_url"] else None
        atts = [done[a["url"]] for a in att_by_detail.get(r["detail_url"], [])]
        recs.append({
            "host": HOST, "title": r["title"],
            "url": r["detail_url"] or args.listing,
            "date": None, "kind": "vyzva",
            "area": r["area"], "listing_url": args.listing,
            "detail_url": r["detail_url"], "detail_title": det["title"] if det else None,
            "detail_fetch_error": detail_errors.get(r["detail_url"]),
            "submission": r["submission"],
            "open_from_raw": r["open_from_raw"], "deadline_raw": r["deadline_raw"],
            "open_from_dates": [d.isoformat() for d in od],
            "deadline_dates": [d.isoformat() for d in do],
            "open_from": open_from, "deadline": deadline,
            "status": compute_status(min(od) if od else None,
                                     max(do) if do else None, today),
            "status_source": "listing_table_dates", "status_ref_date": today.isoformat(),
            "body_text": det["body_text"] if det else None,
            "attachments": atts, "n_attachments": len(atts),
        })
    # + záznam samotného listingu (lossless: plný text stránky vč. úvodní prózy)
    recs.append({
        "host": HOST, "title": page_title(listing_html) or "Žádosti o dotace",
        "url": args.listing, "date": None, "kind": "listing",
        "area": None, "listing_url": args.listing, "detail_url": None,
        "detail_title": None, "detail_fetch_error": None,
        "submission": None, "open_from_raw": None, "deadline_raw": None,
        "open_from_dates": [], "deadline_dates": [], "open_from": None, "deadline": None,
        "status": None, "status_source": None, "status_ref_date": today.isoformat(),
        "body_text": html_to_text(content_seg(listing_html) or listing_html),
        "attachments": [], "n_attachments": 0,
    })

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for rec in recs:
            o.write(json.dumps(rec, ensure_ascii=False) + "\n")

    from collections import Counter
    st = Counter(r["status"] for r in recs if r["kind"] == "vyzva")
    ok = sum(1 for a in done.values() if a["status"] == "ok")
    print(json.dumps({"MARKER": "MK_HARVEST", "tables": n_tables,
                      "vyzvy": sum(1 for r in recs if r["kind"] == "vyzva"),
                      "status": dict(st), "today": today.isoformat(),
                      "details_unique": len(detail_urls), "details_ok": n_det_ok,
                      "attachments_unique": len(uniq), "attachments_ok": ok,
                      "out": args.out, "files_dir": args.files_dir}, ensure_ascii=False))


if __name__ == "__main__":
    main()
