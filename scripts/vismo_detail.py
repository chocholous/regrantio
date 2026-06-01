#!/usr/bin/env python3
"""vismo_classic — VRSTVA 2: detail d-NNNN stránek + File.ashx přílohy.

Pro každou výzvu (vismo_calls.json): stáhne detail, vyparsuje text + metadata
(Vytvořeno/změněno, Úřední deska od-do) + přílohy (File.ashx, li.typsouboru),
stáhne a převede přílohy na text (reuse extract/dsw2_fetch). Spočítá PŘESNÝ
status proti dnešku z 'Úřední deska od-do' (jinak deadline z těla / title fallback).
Výstup: data/vismo_documents.jsonl + data/vismo_files/<host>/<sha>.{ext,txt}.
"""
import argparse, hashlib, json, os, re, ssl, sys, time, html, urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsw2_fetch as df  # reuse: sniff_ext, download, convert, host_of, MIME_EXT

TODAY = date(2026, 5, 30)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
ATT_RE = re.compile(r'class="(t\w+)\s+typsouboru"[^>]*>\s*<strong>\s*<a[^>]*?href="([^"]+)"[^>]*>(.*?)</a>(.*?)</li>', re.S)
UREDNI_RE = re.compile(r'Úřední deska od-do:\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})\s*-\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})')
VYTV_RE = re.compile(r'Vytvořeno\s*/\s*změněno:\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})\s*/\s*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})')
ZODP_RE = re.compile(r'Zodpovídá:\s*([^\n<|]{2,50})')
DEADLINE_RE = re.compile(r'(?:žádost\w*|termín\w*|uzávěrk\w*|podáv\w*|lhůt\w*)[^.]{0,60}?\bdo\s+(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})', re.I)
SIZE_RE = re.compile(r'\[(\w+),\s*([\d.,]+\s*\wB)\]')


def fetch(url, tries=3, timeout=20):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
        except Exception:  # noqa: BLE001
            time.sleep(1.0 * (i + 1))
    return None


def to_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</h[1-6]>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", t).strip()


def parse_date(s):
    m = re.match(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s or "")
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def compute_status(uredni, body_text):
    """Vrátí (status, source, confidence, deadline)."""
    if uredni:
        d1, d2 = parse_date(uredni[0]), parse_date(uredni[1])
        if d2:
            if TODAY > d2:
                return "closed", "uredni_deska", "high", uredni[1]
            if d1 and TODAY < d1:
                return "announced", "uredni_deska", "high", uredni[1]
            return "open", "uredni_deska", "high", uredni[1]
    m = DEADLINE_RE.search(body_text)
    if m:
        dd = parse_date(m.group(1))
        if dd:
            return ("open" if dd >= TODAY else "closed"), "telo_text", "medium", m.group(1)
    return None, None, "low", None


def content_area(h):
    m = re.search(r'id="hlobsah"(.*?)(?:id="pata"|<footer)', h, re.S)
    return m.group(1) if m else h


def process(call, files_dir, do_attachments, timeout, max_bytes):
    h = fetch(call["url"])
    rec = dict(call)
    if not h:
        rec["error"] = "fetch_fail"
        return rec
    ca = content_area(h)
    body = to_text(ca)
    u = UREDNI_RE.search(body)
    v = VYTV_RE.search(body)
    z = ZODP_RE.search(body)
    uredni = (u.group(1).replace(" ", ""), u.group(2).replace(" ", "")) if u else None
    status, src, conf, deadline = compute_status(uredni, body)
    if not status:                       # fallback na title-guess z workflow
        status, src, conf = call.get("status_guess"), "title_guess", "low"
    rec.update({
        "status": status, "status_source": src, "status_confidence": conf, "deadline": deadline,
        "uredni_od": uredni[0] if uredni else None, "uredni_do": uredni[1] if uredni else None,
        "vytvoreno": v.group(1).replace(" ", "") if v else None,
        "zmeneno": v.group(2).replace(" ", "") if v else None,
        "zodpovida": z.group(1).strip() if z else None,
        "body_text": body[:8000],
    })
    # přílohy
    atts = []
    for typ, href, name, rest in ATT_RE.findall(ca):
        href = html.unescape(href)
        full = href if href.startswith("http") else (re.match(r"(https?://[^/]+)", call["url"]).group(1) + href)
        sm = SIZE_RE.search(rest)
        att = {"type": typ, "url": full, "name": to_text(name)[:120],
               "size": sm.group(2) if sm else None}
        if do_attachments:
            ext = df.sniff_ext(full, timeout) or df.ext_of(full)
            host = df.host_of(full)
            sha = hashlib.sha1(full.encode()).hexdigest()[:16]
            d = os.path.join(files_dir, host); os.makedirs(d, exist_ok=True)
            fp = os.path.join(d, f"{sha}.{ext}")
            tp = os.path.join(d, f"{sha}.txt")
            n, err = df.download(full, fp, timeout, max_bytes)
            if n and not err:
                chars, cerr = df.convert(fp, ext, tp, timeout)
                att.update({"ext": ext, "bytes": n, "txt_chars": chars,
                            "txt_path": tp if chars else None, "convert_err": cerr})
                if chars:
                    att["text_excerpt"] = open(tp, encoding="utf-8", errors="replace").read()[:1500]
            else:
                att["download_err"] = err
        atts.append(att)
    rec["attachments"] = atts
    rec["n_attachments"] = len(atts)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calls", default="vismo_calls.json")
    ap.add_argument("--out", default="data/vismo_documents.jsonl")
    ap.add_argument("--files-dir", default="data/vismo_files")
    ap.add_argument("--only-status", help="filtruj na status_guess (např. open)")
    ap.add_argument("--no-attachments", action="store_true")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--max-mb", type=int, default=40)
    args = ap.parse_args()
    calls = json.load(open(args.calls, encoding="utf-8"))
    if args.only_status:
        calls = [c for c in calls if c.get("status_guess") == args.only_status]
    os.makedirs(args.files_dir, exist_ok=True)
    open(args.out, "w").close()
    done = 0
    for i, c in enumerate(calls):
        rec = process(c, args.files_dir, not args.no_attachments, args.timeout, args.max_mb * 1024 * 1024)
        with open(args.out, "a", encoding="utf-8") as o:
            o.write(json.dumps(rec, ensure_ascii=False) + "\n")
        done += 1
        st = rec.get("status"); na = rec.get("n_attachments", 0)
        print(f"[{i+1}/{len(calls)}] {c['web']:14s} status={st}({rec.get('status_confidence')}) att={na} :: {c['title'][:40]}", flush=True)
    print(f"VISMO_DETAIL_DONE {done} dokumentů → {args.out}")


if __name__ == "__main__":
    main()
