#!/usr/bin/env python3
"""100%-BEZPEČNÝ strukturální pre-filtr (mezi vrstvou 1 a fází 2).

Odstraní JEN to, co PROKAZATELNĚ nejde extrahovat / je doslova duplicitní — NIKDY
podle obsahu/keywords/density (to má false-negativy: „veřejná soutěž = grant" → fáze 2 LLM).
  - prázdné: text < limits prefilter_empty_text_max A 0 dokumentů
  - exact-dup: bajtově stejný obsah (text+documents)
  - nav/archiv URL: /tag|category|author|page/N|feed|attachment/ , ?paged=
Loguje, CO zahodil (nahlas, ne tiše). Obsahový šum (news zmiňující dotace) NEČISTÍ — to je fáze 2.

Spuštění: python3 scripts/prefilter.py data/h19_mzcr.jsonl [--out data/h19_mzcr.clean.jsonl]
          python3 scripts/prefilter.py data/h19_*.jsonl --inplace
"""
import argparse, hashlib, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limits import L

NAV = re.compile(r"/(tag|category|author|page/\d+|feed|attachment|rubrika|stitek|comment-page-\d+)/|[?&](paged|replytocom)=", re.I)

def clean(records, empty_max):
    seen, out = set(), []
    drop = {"empty": 0, "dup": 0, "nav": 0}
    for r in records:
        text = (r.get("text") or "").strip()
        docs = r.get("documents") or []
        if len(text) < empty_max and not docs:
            drop["empty"] += 1; continue
        if NAV.search(r.get("url") or ""):
            drop["nav"] += 1; continue
        h = hashlib.sha1((text + "".join(sorted(str(d) for d in docs))).encode("utf-8")).hexdigest()
        if h in seen:
            drop["dup"] += 1; continue
        seen.add(h); out.append(r)
    return out, drop

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", help="výstup (jen pro 1 soubor); jinak --inplace")
    ap.add_argument("--inplace", action="store_true")
    args = ap.parse_args()
    empty_max = L("acquisition.prefilter_empty_text_max")
    tot_in = tot_out = 0; tot_drop = {"empty": 0, "dup": 0, "nav": 0}
    for fp in args.files:
        recs = [json.loads(l) for l in open(fp, encoding="utf-8")]
        out, drop = clean(recs, empty_max)
        tot_in += len(recs); tot_out += len(out)
        for k in tot_drop: tot_drop[k] += drop[k]
        dropped = len(recs) - len(out)
        if dropped:
            print(f"  {os.path.basename(fp):28} {len(recs)} → {len(out)}  (−{dropped}: empty {drop['empty']}, dup {drop['dup']}, nav {drop['nav']})", file=sys.stderr)
        dest = args.out or (fp if args.inplace else None)
        if dest:
            with open(dest, "w", encoding="utf-8") as o:
                for r in out:
                    o.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"MARKER": "PREFILTER", "in": tot_in, "out": tot_out,
                      "dropped": tot_in - tot_out, "by": tot_drop,
                      "note": "JEN strukturální (empty/dup/nav); obsahový šum řeší fáze 2 (classify)"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
