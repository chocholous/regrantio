#!/usr/bin/env python3
"""Perzistuj výstup classify_wf.js do trvalého ledgeru data/classifications.jsonl.

Klasifikace (vč. ZDŮVODNĚNÍ v bodech = signals) je auditní stopa: PROČ byl dokument
zařazen do base_type — i pro zahozené (news/admin/other) a pro low-confidence případy
(„nic nesedí" → ruční kontrola). Klíč = url dokumentu (z per-doc JSON pole "id").
Napojuje se do provenance oportunity přes opportunities.py --classifications.

Vstup: JSON výstup classify_wf (pole [{path, classify:{base_type,confidence,signals}}])
       — buď přímý result, nebo {result:[...]} z task výstupu.
Použití:
  python3 scripts/save_classifications.py <classify_result.json> [--out data/classifications.jsonl]
"""
import argparse, json, os, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result")
    ap.add_argument("--out", default="data/classifications.jsonl")
    ap.add_argument("--reset", action="store_true", help="přepiš místo append+dedup")
    args = ap.parse_args()
    raw = json.load(open(args.result, encoding="utf-8"))
    items = raw["result"] if isinstance(raw, dict) and "result" in raw else raw

    # url → záznam (z per-doc JSON na path vezmeme "id"=url a "web"=source)
    out = {}
    for it in items:
        c = it.get("classify")
        p = it.get("path")
        if not c or not p or not os.path.exists(p):
            continue
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        url = d.get("id")
        if not url:
            continue
        out[url] = {"url": url, "source": d.get("web"),
                    "base_type": c.get("base_type"), "confidence": c.get("confidence"),
                    "reasoning": c.get("reasoning") or c.get("signals") or []}   # body, podle čeho se model rozhodl

    # merge s existujícím (dedup dle url; nový přepíše)
    merged = {}
    if not args.reset and os.path.exists(args.out):
        for l in open(args.out, encoding="utf-8"):
            try:
                e = json.loads(l); merged[e["url"]] = e
            except Exception:
                pass
    merged.update(out)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for e in merged.values():
            o.write(json.dumps(e, ensure_ascii=False) + "\n")
    import collections
    bt = collections.Counter(e["base_type"] for e in merged.values())
    lowc = sum(1 for e in merged.values() if e.get("confidence") == "low")
    print(json.dumps({"MARKER": "CLASSIFICATIONS", "written": len(merged), "new_this_run": len(out),
                      "by_type": dict(bt), "low_confidence": lowc, "out": args.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
