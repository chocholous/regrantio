#!/usr/bin/env python3
"""Harvester platformy Lewis/Dynamo GrantyPortal (aspnet_webforms rodina) — BEZ Apify.

Metoda: SPA grid, jehož řádky plní XHR `POST ODataSimpleFromSql/<idSeznamu>` s `postedJSON`.
Endpoint + payload template se OBJEVÍ jednorázově Playwrightem (scripts/lewis_discover.py),
samotný SBĚR pak jede čistým HTTP cookie-jar (stránkování přes skip/top). Vrací strukturovaný
JSON (NazevZadosti, NazevZadatele, IcZadatele, NazevOblasti, NazevStavuZadosti, PridelenaCastka…).

Ověřeno: granty.praha.eu, idSeznamu abad868e-… → 112 907 záznamů.
"""
import argparse, json, os, ssl, sys, time, urllib.parse, urllib.request, http.cookiejar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limits import L   # centrální registr limitů (root limits.json)

# payload template zachycený Playwrightem (scripts/lewis_discover.py); měň jen skip/top
TEMPLATE = {
    "filters": {"concatOperator": 0, "children": []},
    "orderBy": [{"fieldName": "RokOd", "direction": 2}],
    "totalSummary": [{"fieldName": "PridelenaCastka", "summaryType": 0, "valueFormat": "n0"}],
    "skip": 0, "top": 100, "inlineCount": True, "format": "json", "halt": False,
    "extraArguments": {"action": "get", "idSeznamu": None, "OblastDotace": "", "RokOd": "", "RokDo": "", "StavZadosti": ""},
    "keyField": "Id",
}

def opener():
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
                                     urllib.request.HTTPSHandler(context=ctx))
    op.addheaders = [("User-Agent", "Mozilla/5.0 (lewis-dynamo-harvest; re-grantio)")]
    return op

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://granty.praha.eu/GrantyPortal/")
    ap.add_argument("--id-seznamu", default="abad868e-1525-4d8c-8bdb-64d608f788fc")
    ap.add_argument("--out", default="data/granty_praha.jsonl")
    ap.add_argument("--page-size", type=int, default=L("acquisition.page_size"))
    ap.add_argument("--max", type=int, default=L("acquisition.lewis_max_records"), help="max záznamů (0=vše)")
    ap.add_argument("--delay", type=float, default=0.3)
    args = ap.parse_args()

    op = opener()
    grid = f"{args.base}LW/Views/Core/SeznamJS?action=get&idSeznamu={args.id_seznamu}"
    op.open(args.base.rstrip("/").rsplit("/", 1)[0] + "/", timeout=25).read()   # zahřej session
    op.open(grid, timeout=25).read()
    data_url = f"{args.base}ODataSimpleFromSql/{args.id_seznamu}"

    total = None; got = 0
    with open(args.out, "w", encoding="utf-8") as o:
        skip = 0
        while True:
            p = json.loads(json.dumps(TEMPLATE))
            p["skip"], p["top"] = skip, args.page_size
            p["extraArguments"]["idSeznamu"] = args.id_seznamu
            body = urllib.parse.urlencode({"postedJSON": json.dumps(p)}).encode()
            req = urllib.request.Request(data_url, data=body, headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest", "Referer": grid})
            d = json.loads(op.open(req, timeout=30).read().decode("utf-8", "replace"))
            if total is None:
                total = int(d.get("count", 0))
            rows = d.get("data", [])
            if not rows:
                break
            for r in rows:
                o.write(json.dumps(r, ensure_ascii=False) + "\n")
            got += len(rows); skip += args.page_size
            print(f"  skip={skip-args.page_size} +{len(rows)} → {got}/{total}", file=sys.stderr)
            if args.max and got >= args.max:
                break
            if skip >= total:
                break
            time.sleep(args.delay)
    print(json.dumps({"MARKER": "LEWIS_DYNAMO", "records": got, "total": total, "out": args.out}, ensure_ascii=False))

if __name__ == "__main__":
    main()
