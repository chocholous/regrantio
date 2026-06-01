#!/usr/bin/env python3
"""Kentico (IROP/dotaceEU) PoC — výzvy listing → detail se strukturovanými poli
+ status z dat + /getmedia/ přílohy (reuse dsw2_fetch). Staticky, bez postbacku.
"""
import argparse, hashlib, json, os, re, ssl, sys, time, html, urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsw2_fetch as df

TODAY = date(2026, 6, 1)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
DATE_RE = r"(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})"
FIELDS = {
    "open_from": r"Zah[áa]jen[íi] p[řr][íi]jmu\s+[žz][áa]dost[íi]:?\s*" + DATE_RE,
    "deadline": r"Ukon[čc]en[íi] p[řr][íi]jmu\s+[žz][áa]dost[íi]:?\s*" + DATE_RE,
    "announced": r"Datum vyhl[áa][šs]en[íi]:?\s*" + DATE_RE,
    "eligible": r"Opr[áa]vn[ěe]n[íi] [žz]adatel[ée]:?\s*([^|]{5,180})",
    "support_rate": r"M[íi]ra podpory:?\s*([^|]{2,80})",
    "allocation": r"(?:Celkov[áa] )?[Aa]lokace[^:]{0,20}:?\s*([^|]{2,80})",
}
GETMEDIA = re.compile(r'href="(/getmedia/[^"]+)"[^>]*>(.*?)</a>', re.S)


def fetch(url, tries=3, timeout=25):
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
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).replace("\xa0", " ").strip()


def pdate(s):
    m = re.match(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s or "")
    return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def discover(base, listing_path, enumerate_n):
    urls = set()
    h = fetch(base + listing_path)
    if h:
        for hr in re.findall(r'href="([^"]*[Vv]yzva?IROP[^"]*|[^"]*/[Vv]yzvy/[^"]+)"', h):
            if re.search(r"vyzvaIROP|/Vyzvy/", hr):
                urls.add(base + hr.split("?")[0] if hr.startswith("/") else hr)
    # doplň enumerací N..1 (IROP detail = /Vyzvy-2021-2027/Vyzvy/{N}vyzvaIROP)
    for n in range(enumerate_n, 0, -1):
        urls.add(f"{base}/Vyzvy-2021-2027/Vyzvy/{n}vyzvaIROP")
    return sorted(urls)


def process(url, files_dir, do_att, timeout, max_bytes):
    h = fetch(url)
    if not h:
        return {"url": url, "error": "fetch_fail"}
    txt = to_text(h)
    rec = {"url": url}
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    rec["title"] = to_text(h1.group(1)) if h1 else None
    for k, pat in FIELDS.items():
        m = re.search(pat, txt, re.I)
        rec[k] = m.group(1).strip()[:180] if m else None
    # status z dat
    of, dl = pdate(rec.get("open_from")), pdate(rec.get("deadline"))
    if dl:
        if TODAY > dl:
            rec["status"], rec["status_conf"] = "closed", "high"
        elif of and TODAY < of:
            rec["status"], rec["status_conf"] = "announced", "high"
        else:
            rec["status"], rec["status_conf"] = "open", "high"
    else:
        rec["status"], rec["status_conf"] = "unknown", "low"
    # přílohy /getmedia/
    atts = []
    seen = set()
    for href, name in GETMEDIA.findall(h):
        full = "https://" + re.match(r"https?://([^/]+)", url).group(1) + html.unescape(href)
        if full in seen:
            continue
        seen.add(full)
        att = {"url": full, "name": to_text(name)[:100]}
        if do_att and len(atts) < 8:  # cap na PoC
            ext = df.sniff_ext(full, timeout) or "bin"
            sha = hashlib.sha1(full.encode()).hexdigest()[:16]
            d = os.path.join(files_dir, df.host_of(full)); os.makedirs(d, exist_ok=True)
            fp, tp = os.path.join(d, f"{sha}.{ext}"), os.path.join(d, f"{sha}.txt")
            n, err = df.download(full, fp, timeout, max_bytes)
            if n and not err:
                chars, _ = df.convert(fp, ext, tp, timeout)
                att.update({"ext": ext, "txt_chars": chars})
        atts.append(att)
    rec["n_attachments"] = len(atts)
    rec["attachments"] = atts
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://irop.gov.cz")
    ap.add_argument("--listing", default="/Vyzvy-2021-2027")
    ap.add_argument("--enumerate", type=int, default=0, help="doplnit N..1 výzev enumerací")
    ap.add_argument("--out", default="data/kentico_irop.jsonl")
    ap.add_argument("--files-dir", default="data/kentico_files")
    ap.add_argument("--no-attachments", action="store_true")
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--max-mb", type=int, default=40)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    urls = discover(args.base, args.listing, args.enumerate)
    if args.limit:
        urls = urls[:args.limit]
    os.makedirs(args.files_dir, exist_ok=True)
    open(args.out, "w").close()
    ok = 0
    for i, u in enumerate(urls):
        rec = process(u, args.files_dir, not args.no_attachments, args.timeout, args.max_mb * 1024 * 1024)
        if rec.get("error") or not rec.get("title"):
            continue  # neexistující enumerovaná výzva
        open(args.out, "a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
        ok += 1
        print(f"[{i+1}/{len(urls)}] {rec.get('status')}({rec.get('status_conf')}) "
              f"dl={rec.get('deadline')} att={rec['n_attachments']} :: {str(rec.get('title'))[:45]}", flush=True)
    print(f"KENTICO_DONE {ok} výzev → {args.out}")


if __name__ == "__main__":
    main()
