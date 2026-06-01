#!/usr/bin/env python3
"""mv_legacy_cms (ASP.NET MV ČR / HZS / radnice) — PoC extraktor.
/clanek/{slug}.aspx → title + obsah + /soubor přílohy. Přílohy přes dsw2_fetch.
"""
import argparse, hashlib, json, os, re, ssl, sys, time, html, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsw2_fetch as df

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
SOUBOR_RE = re.compile(r'<a[^>]+href="([^"]*/soubor/[^"]+)"[^>]*?(?:title="([^"]*)")?[^>]*>(.*?)</a>', re.S)


def fetch(url, tries=3, timeout=20):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace"), r.geturl()
        except Exception:  # noqa: BLE001
            time.sleep(1.0 * (i + 1))
    return None, None


def to_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</h[1-6]>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", t).strip()


def content_area(h):
    # ASP.NET MV šablona: <... id="content"> nebo id="main">
    m = re.search(r'id="content"[^>]*>(.*?)(?:id="(?:pata|footer|paticka)"|<footer)', h, re.S)
    if not m:
        m = re.search(r'id="main"[^>]*>(.*?)(?:id="(?:pata|footer)"|<footer)', h, re.S)
    return m.group(1) if m else h


def title_of(h):
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    if not m:
        return None
    t = html.unescape(m.group(1)).strip()
    # "Org - Sekce - Název článku" → poslední smysluplná část (název)
    parts = [p.strip() for p in t.split(" - ") if p.strip()]
    return parts[-1] if parts else t


def process(url, files_dir, do_attachments, timeout, max_bytes):
    h, final = fetch(url)
    if not h:
        return {"url": url, "error": "fetch_fail"}
    host = re.match(r"https?://([^/]+)", url).group(1)
    ca = content_area(h)
    rec = {"url": url, "host": host, "title": title_of(h), "body_text": to_text(ca)[:8000]}
    atts = []
    for href, titleattr, txt in SOUBOR_RE.findall(ca):
        full = html.unescape(href)
        att = {"url": full, "label": (titleattr or to_text(txt))[:120]}
        if do_attachments:
            ext = df.sniff_ext(full, timeout) or "bin"
            sha = hashlib.sha1(full.encode()).hexdigest()[:16]
            d = os.path.join(files_dir, df.host_of(full)); os.makedirs(d, exist_ok=True)
            fp, tp = os.path.join(d, f"{sha}.{ext}"), os.path.join(d, f"{sha}.txt")
            n, err = df.download(full, fp, timeout, max_bytes)
            if n and not err:
                chars, cerr = df.convert(fp, ext, tp, timeout)
                att.update({"ext": ext, "bytes": n, "txt_chars": chars})
                if chars:
                    att["text_excerpt"] = open(tp, encoding="utf-8", errors="replace").read()[:1200]
            else:
                att["download_err"] = err
        atts.append(att)
    rec["attachments"] = atts
    rec["n_attachments"] = len(atts)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, help="JSON list URL nebo soubor")
    ap.add_argument("--out", default="data/mv_documents.jsonl")
    ap.add_argument("--files-dir", default="data/mv_files")
    ap.add_argument("--no-attachments", action="store_true")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--max-mb", type=int, default=40)
    args = ap.parse_args()
    seeds = json.load(open(args.seeds)) if os.path.exists(args.seeds) else json.loads(args.seeds)
    os.makedirs(args.files_dir, exist_ok=True)
    open(args.out, "w").close()
    for i, u in enumerate(seeds):
        rec = process(u, args.files_dir, not args.no_attachments, args.timeout, args.max_mb * 1024 * 1024)
        open(args.out, "a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{i+1}/{len(seeds)}] att={rec.get('n_attachments','-')} :: {str(rec.get('title'))[:55]}", flush=True)
    print(f"MV_CMS_DONE {len(seeds)} → {args.out}")


if __name__ == "__main__":
    main()
