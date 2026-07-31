#!/usr/bin/env python3
"""Bridge: Apify website-content-crawler markdown → extract_wf vstupy.

Apify dataset (stažený REST → data/h_apify_*.json: [{url, markdown, metadata.title}]) → per grantová
stránka soubor {id, web, title, body, attachments_md} do out-dir, který protáhne scripts/extract_wf.js
(stejně jako /tmp/mg2). Filtruje grant-relevantní stránky (skóre klíčových slov, ne WAF-reject, délka).
Zapíše i sidecar data/apify_meta.json (id→{web, kategorie}) pro ingest (facety: kraj/nadace).

Usage: python3 scripts/build_apify_input.py data/h_apify_kraje.json:kraj data/h_apify_nadace.json:nadace --out-dir /tmp/apify_in
"""
import argparse, json, os, re, sys

KW = re.compile(r"dotac|grant|výzv|příspěv|žadatel|uzávěrk|termín podání|alokac|podpor|stipend", re.I)


def host(u):
    m = re.match(r"https?://(www\.)?([^/]+)", u or "")
    return m.group(2).lower() if m else "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help="soubor.json:kategorie")
    ap.add_argument("--out-dir", default="/tmp/apify_in")
    ap.add_argument("--min-score", type=int, default=3)
    ap.add_argument("--min-len", type=int, default=400)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    os.system(f"rm -f {a.out_dir}/grant_*.json")

    meta, n = {}, 0
    for spec in a.inputs:
        path, _, cat = spec.partition(":")
        for x in json.load(open(path, encoding="utf-8")):
            url = x.get("url"); md = x.get("markdown") or ""
            title = x.get("metadata.title") or (x.get("metadata", {}) or {}).get("title") or ""
            if not url or not md or "Request Rejected" in md:
                continue
            if len(md) < a.min_len or len(KW.findall(title + " " + md[:2500])) < a.min_score:
                continue
            base = f"grant_{n:04d}.json"
            gid = f"grant:{host(url)}:{re.sub(r'[^a-z0-9]+', '', url.split('/')[-1].lower())[:40] or 'home'}"
            json.dump({"id": gid, "web": host(url), "title": title.strip() or url,
                       "body": md, "attachments_md": ""},
                      open(os.path.join(a.out_dir, base), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            meta[base] = {"id": gid, "web": host(url), "url": url, "kategorie": cat}
            n += 1
    json.dump(meta, open("data/apify_meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "APIFY_INPUTS", "written": n, "out_dir": a.out_dir,
                      "by_cat": {c: sum(1 for v in meta.values() if v["kategorie"] == c)
                                 for c in set(v["kategorie"] for v in meta.values())}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
