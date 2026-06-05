#!/usr/bin/env python3
"""Generický XHR-discovery (Playwright headless) — pro JAKÉKOLI SPA (ne jen Lewis).

SPA app-portály krajů (KHK React, fondvysociny, GINIS, edotace) mají výzvy jen za JSON-XHR,
který JS skládá za běhu (staticky nezjistitelné). Tenhle skript načte stránku, odchytí VŠECHNY
JSON odpovědi a vypíše endpoint + velikost + ukázku → identifikuješ grant-API → pak čistý HTTP
replay (bez prohlížeče). Zobecnění lewis_discover.py.

Setup: playwright install chromium
Usage: python3 scripts/xhr_discover.py --url "https://dotace.khk.cz/verejnost/vyzvy" [--wait 6000] [--min 200]
"""
import argparse, json, sys
from playwright.sync_api import sync_playwright


def discover(url, wait_ms, min_bytes):
    hits = []

    def on_response(resp):
        try:
            ct = (resp.headers.get("content-type") or "").lower()
            body = resp.body()
            if len(body) < min_bytes:
                return
            txt = body.decode("utf-8", "replace")
            s = txt.lstrip()[:1]
            is_json = ("json" in ct) or (s in "{[")     # i ne-json content-type s JSON tělem
            if not is_json:
                return
            hits.append({"url": resp.url, "status": resp.status, "bytes": len(body),
                         "method": resp.request.method, "snippet": txt[:180].replace("\n", " ")})
        except Exception:
            pass

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        pg.on("response", on_response)
        try:
            pg.goto(url, wait_until="networkidle", timeout=45000)
        except Exception as e:
            print(f"  (goto warn: {str(e)[:60]})", file=sys.stderr)
        pg.wait_for_timeout(wait_ms)
        b.close()
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--wait", type=int, default=6000)
    ap.add_argument("--min", type=int, default=200, help="min bajtů JSON odpovědi (filtr drobných)")
    a = ap.parse_args()
    hits = discover(a.url, a.wait, a.min)
    # největší JSON odpovědi první (data bývají velká)
    hits.sort(key=lambda h: -h["bytes"])
    print(f"=== {len(hits)} JSON XHR odpovědí na {a.url} ===")
    for h in hits[:25]:
        print(f"  {h['bytes']:>8}B {h['method']} {h['status']}  {h['url'][:95]}")
        print(f"           {h['snippet'][:100]}")


if __name__ == "__main__":
    main()
