#!/usr/bin/env python3
"""vismo_modern — VRSTVA 2: detail stránek + /file/NNNN přílohy.

Pro každý záznam listingu (vismo_modern_listing.jsonl): stáhne detail, vyparsuje
plný text <main> + přílohy (a.global-attachment__link href="/file/NNNN" — bez
přípony v URL → dsw2_fetch.sniff_ext), stáhne a převede přílohy na text.

Vismo modern NEMÁ "Úřední deska od-do" ani "Vytvořeno / změněno" → status se
počítá z termínů v těle ("Lhůta pro podání žádosti: od D. M. do D. M. RRRR",
"žádosti … do D. M. RRRR"), jinak zůstává None (dopočítá vrstva 2 z příloh).
STATUS JE VÝPOČET V KÓDU (TODAY), ne LLM.

Výstup: data/vismo_modern_documents.jsonl (stejný kontrakt jako
vismo_documents.jsonl) + data/vismo_modern_files/<host>/<sha>.{ext,txt}.

Usage:  python3 scripts/vismo_modern_detail.py
        python3 scripts/vismo_modern_detail.py --listing data/vismo_modern_listing.jsonl --no-attachments
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse, hashlib, json, os, re, ssl, sys, time, html, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsw2_fetch as df  # reuse: sniff_ext, ext_of, download, convert, host_of
from limits import L

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
ATT_RE = re.compile(
    r'<a\b[^>]*?\bhref="([^"]+)"[^>]*\bclass="[^"]*global-attachment__link[^"]*"[^>]*>'
    r'(?:.*?<strong[^>]*class="[^"]*global-attachment__title[^"]*"[^>]*>(.*?)</strong>)?'
    r'(?:.*?<span[^>]*class="[^"]*global-attachment__type[^"]*"[^>]*>(.*?)</span>)?'
    r'(?:.*?<span[^>]*class="[^"]*global-attachment__size[^"]*"[^>]*>(.*?)</span>)?'
    r'.*?</a>', re.S)
# CLASSIC fallback (hybridní weby v labelu vismo_modern, např. novabela.cz):
# stránka bez <main> → obsah id="hlobsah"; přílohy = anchory na File.ashx;
# metadata "Úřední deska od-do" / "Vytvořeno / změněno" jako vismo_detail.py.
ASHX_A = re.compile(r'<a\b[^>]*?\bhref="([^"]*File\.ashx[^"]*)"[^>]*>(.*?)</a>', re.S | re.I)
SIZE_RE = re.compile(r'\[(\w+),\s*([\d.,]+\s*\wB)\]')
UREDNI_RE = re.compile(r'Úřední deska od-do:\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})\s*-\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})')
VYTV_RE = re.compile(r'Vytvořeno\s*/\s*změněno:\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})\s*/\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})')
DATE = r'\d{1,2}\.\s*\d{1,2}\.\s*\d{4}'
# "od D. M. [RRRR] do D. M. RRRR" v okolí lhůta/žádost/termín/uzávěrka/podávání/příjem.
# Mezera-gap smí obsahovat tečky JEN za číslicí (data), ne větné tečky → nepřeteče do další věty.
GAP = r'(?:[^.!?<]|(?<=\d)\.)'
DEADLINE_RE = re.compile(
    r'(?:žádost\w*|termín\w*|uzávěrk\w*|podáv\w*|lhůt\w*|příjem)' + GAP + r'{0,100}?'
    r'\bdo\s+(' + DATE + r')', re.I)
OPENFROM_RE = re.compile(
    r'(?:žádost\w*|termín\w*|podáv\w*|lhůt\w*|příjem)' + GAP + r'{0,100}?'
    r'\bod\s+(' + DATE + r')', re.I)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)


def fetch(url, tries=3, timeout=None):
    timeout = timeout or L("http.default_timeout_s")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
        except Exception:  # noqa: BLE001
            time.sleep(1.0 * (i + 1))
    return None


def main_area(h):
    m = re.search(r"<main\b[^>]*>(.*?)</main>", h, re.S)
    if m:
        return m.group(1)
    m = re.search(r'id="hlobsah"(.*?)(?:id="pata"|<footer)', h, re.S)   # classic fallback
    return m.group(1) if m else h


def to_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</h[1-6]>|</div>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def clean(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(t or ""))).replace("\xa0", " ").strip()


def parse_date(s):
    m = re.match(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", (s or "").replace("\xa0", " "))
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def compute_status(body_text, today):
    """→ (status, source, confidence, deadline). Modern nemá Úřední desku; classic
    fallback ji má → vyšší konfidence (stejná logika jako vismo_detail.py)."""
    u = UREDNI_RE.search(body_text)
    if u:
        d1, d2 = parse_date(u.group(1)), parse_date(u.group(2))
        dl = u.group(2).replace(" ", "")
        if d2:
            if today > d2:
                return "closed", "uredni_deska", "high", dl
            if d1 and today < d1:
                return "announced", "uredni_deska", "high", dl
            return "open", "uredni_deska", "high", dl
    m = DEADLINE_RE.search(body_text)
    if m:
        dl = m.group(1).replace(" ", "").replace("\xa0", "")
        dd = parse_date(m.group(1))
        if dd:
            o = OPENFROM_RE.search(body_text)
            od = parse_date(o.group(1)) if o else None
            if today > dd:
                return "closed", "telo_text", "medium", dl
            if od and today < od:
                return "announced", "telo_text", "medium", dl
            return "open", "telo_text", "medium", dl
    return None, None, "low", None


def process(call, files_dir, do_attachments, timeout, max_bytes, today, workers=None):
    h = fetch(call["url"], timeout=timeout)
    rec = {"web": call.get("foundation_id"), "title": call.get("title"), "url": call["url"],
           "date": call.get("date"), "kind": None, "status_guess": None, "section": call.get("section")}
    if not h:
        rec["error"] = "fetch_fail"
        return rec
    ma = main_area(h)
    hm = H1_RE.search(ma)
    if hm:
        rec["title"] = clean(hm.group(1)) or rec["title"]
    body = to_text(ma)
    status, src, conf, deadline = compute_status(body, today)
    u = UREDNI_RE.search(body)
    v = VYTV_RE.search(body)
    rec.update({
        "status": status, "status_source": src, "status_confidence": conf, "deadline": deadline,
        "uredni_od": u.group(1).replace(" ", "") if u else None,
        "uredni_do": u.group(2).replace(" ", "") if u else None,
        "vytvoreno": v.group(1).replace(" ", "") if v else None,
        "zmeneno": v.group(2).replace(" ", "") if v else None,
        "zodpovida": None,
        "body_text": body,
    })
    origin = re.match(r"(https?://[^/]+)", call["url"]).group(1)
    found = [(href, name, typ, size) for href, name, typ, size in ATT_RE.findall(ma)]
    if not found:        # classic fallback: File.ashx anchory (jen dotačně relevantní názvy — hlobsah obsahuje i nav)
        for href, txt in ASHX_A.findall(ma):
            nm = clean(txt)
            if not re.search(r"dota[cč]|grant|výzv|vyzv|program|žádost|zadost", nm, re.I):
                continue
            sm = SIZE_RE.search(nm)
            found.append((href, nm, sm.group(1).lower() if sm else "", sm.group(2) if sm else ""))
    def fetch_att(item):
        href, name, typ, size = item
        href = html.unescape(href)
        full = href if href.startswith("http") else origin + href
        att = {"type": clean(typ) or None, "url": full, "name": clean(name)[:120] or None,
               "size": clean(size) or None}
        if do_attachments:
            ext = (clean(typ).lower() or None) or df.sniff_ext(full, L("probe.sniff_ext_bytes")) or df.ext_of(full)
            host = df.host_of(full)
            sha = hashlib.sha1(full.encode()).hexdigest()[:16]
            d = os.path.join(files_dir, host); os.makedirs(d, exist_ok=True)
            fp = os.path.join(d, f"{sha}.{ext}")
            tp = os.path.join(d, f"{sha}.txt")
            if os.path.exists(fp) and os.path.getsize(fp) and os.path.exists(tp):   # idempotence (sha=URL)
                att.update({"ext": ext, "bytes": os.path.getsize(fp),
                            "txt_chars": os.path.getsize(tp), "txt_path": tp, "convert_err": None})
                return att
            n, err = df.download(full, fp, timeout, max_bytes)
            if n and not err:
                chars, cerr = df.convert(fp, ext, tp, timeout)
                att.update({"ext": ext, "bytes": n, "txt_chars": chars,
                            "txt_path": tp if chars else None, "convert_err": cerr})
            else:
                att["download_err"] = err
        return att

    uniq, seen = [], set()
    for it in found:
        full = html.unescape(it[0])
        full = full if full.startswith("http") else origin + full
        if full not in seen:
            seen.add(full)
            uniq.append(it)
    with ThreadPoolExecutor(max_workers=workers or L("http.download_workers")) as ex:
        atts = list(ex.map(fetch_att, uniq))
    rec["attachments"] = atts
    rec["n_attachments"] = len(atts)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listing", default="data/vismo_modern_listing.jsonl")
    ap.add_argument("--out", default="data/vismo_modern_documents.jsonl")
    ap.add_argument("--files-dir", default="data/vismo_modern_files")
    ap.add_argument("--only-host", help="filtruj na foundation_id")
    ap.add_argument("--no-attachments", action="store_true")
    ap.add_argument("--timeout", type=int, default=None)
    ap.add_argument("--today", help="YYYY-MM-DD (default: dnešek)")
    ap.add_argument("--workers", type=int, default=None, help="souběh stahování příloh (default http.download_workers)")
    args = ap.parse_args()
    today = date.fromisoformat(args.today) if args.today else date.today()
    timeout = args.timeout or L("http.default_timeout_s")
    max_bytes = L("safety.doc_download_max_mb") * 1024 * 1024
    calls, seen = [], set()
    for line in open(args.listing, encoding="utf-8"):
        c = json.loads(line)
        if args.only_host and c.get("foundation_id") != args.only_host:
            continue
        if c["url"] in seen:
            continue
        seen.add(c["url"])
        calls.append(c)
    os.makedirs(args.files_dir, exist_ok=True)
    open(args.out, "w").close()
    for i, c in enumerate(calls):
        rec = process(c, args.files_dir, not args.no_attachments, timeout, max_bytes, today, args.workers)
        with open(args.out, "a", encoding="utf-8") as o:
            o.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{i+1}/{len(calls)}] {rec.get('web',''):22s} status={rec.get('status')}({rec.get('status_confidence')}) "
              f"att={rec.get('n_attachments',0)} :: {str(rec.get('title'))[:48]}", flush=True)
    print(f"VISMO_MODERN_DETAIL_DONE {len(calls)} dokumentů → {args.out}")


if __name__ == "__main__":
    main()
