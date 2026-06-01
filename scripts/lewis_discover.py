#!/usr/bin/env python3
"""OBJEVOVACÍ metoda (jednorázově, Playwright headless) — odposlech XHR Lewis/Dynamo gridu.

Proč: WebForms/SPA grid (granty.praha.eu ap.) má data jen za XHR, který framework skládá
v JS bundlu (staticky nezjistitelné). Tento skript načte grid stránku, odchytí síťová volání
a vypíše DATA-endpoint + přesný `postedJSON` payload + idSeznamu. Ten se pak zadá do
`scripts/lewis_dynamo.py`, který už sbírá čistým HTTP (bez prohlížeče, bez Apify).

Setup: pip install playwright && playwright install chromium
Spuštění: python scripts/lewis_discover.py --url "<SeznamJS URL gridu>"
"""
import argparse, json, os, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limits import L   # centrální registr limitů (root limits.json)

def discover(url, wait_ms):
    found = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        def on_request(req):
            if req.method == "POST" and req.resource_type in ("xhr", "fetch"):
                found.append({"url": req.url, "post": req.post_data})
        page.on("request", on_request)
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(wait_ms)
        cookies = [c["name"] for c in ctx.cookies()]
        b.close()
    return found, cookies

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True, help="URL gridu (…/LW/Views/Core/SeznamJS?action=get&idSeznamu=…)")
    ap.add_argument("--wait", type=int, default=L("probe.discover_wait_ms"))
    args = ap.parse_args()
    calls, cookies = discover(args.url, args.wait)
    print(f"# session cookies: {cookies}")
    for c in calls:
        # data-volání pozná payload nesoucí stránkování/filtry
        if c["post"] and ("postedJSON" in c["post"] or "skip" in (c["post"] or "")):
            print("\n# DATA-ENDPOINT (zadej do lewis_dynamo.py):")
            print("url :", c["url"])
            import urllib.parse
            try:
                val = urllib.parse.parse_qs(c["post"])["postedJSON"][0]
                print("payload template:")
                print(json.dumps(json.loads(val), ensure_ascii=False, indent=1))
            except Exception:
                print("post:", c["post"][:400])

if __name__ == "__main__":
    main()
