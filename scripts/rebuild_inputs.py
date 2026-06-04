#!/usr/bin/env python3
"""Přestav attachments_md v /tmp/mg2 inputech z OPRAVENÝCH doc-store .txt (po scripts/fix_docs.py).

Inputy /tmp/mg2/grant_NNNN.json mají balast zapečený v attachments_md (stavěly se z rozbitých .txt).
fix_docs.py opravil .txt v doc-store; tady přegenerujeme attachments_md ze stejných txt_path (join
id→data/opportunities.jsonl→provenance.documents[]). Formát part = "[{basename}]\\n{text}", join "\\n\\n"
(shodně s build_extract_input.py). Body/title/id/web zůstávají. Detekuje dotčené (garbage>práh) sám.

Usage:
  python3 scripts/rebuild_inputs.py [--dir /tmp/mg2] [--opps data/opportunities.jsonl] [--threshold 0.15] [--dry-run]
Vypíše indexy dotčených (pro extract_wf.js {dir,prefix,indices:[...]}).
"""
import argparse, glob, json, os, re, sys

OK = set('.,;:%()[]-–—/+=@"\'§!?°×#&*<>|~`_')


def gratio(s):
    return sum(1 for c in s if not (c.isalnum() or c.isspace() or c in OK)) / len(s) if s else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="/tmp/mg2")
    ap.add_argument("--prefix", default="grant")
    ap.add_argument("--opps", default="data/opportunities.jsonl")
    ap.add_argument("--threshold", type=float, default=0.15)
    ap.add_argument("--min-len", type=int, default=2000)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    # index id → documents[]
    idx = {}
    for l in open(a.opps, encoding="utf-8"):
        try:
            r = json.loads(l)
            idx[r.get("id")] = (r.get("provenance", {}) or {}).get("documents", []) or []
        except Exception:
            pass

    affected, rebuilt, nojoin, still = [], 0, [], []
    for fp in sorted(glob.glob(f"{a.dir}/{a.prefix}_*.json")):
        d = json.load(open(fp, encoding="utf-8"))
        am = d.get("attachments_md") or ""
        if len(am) < a.min_len or gratio(am) <= a.threshold:
            continue
        n = int(re.search(r"_(\d+)\.json", fp).group(1))
        affected.append(n)
        docs = idx.get(d.get("id"))
        if docs is None:
            nojoin.append(n); continue
        parts = []
        for doc in docs:
            tp = doc.get("txt_path"); u = doc.get("url") or ""
            if tp and os.path.exists(tp):
                t = open(tp, encoding="utf-8", errors="replace").read()
                if t.strip():
                    parts.append(f"[{u.split('/')[-1][:40]}]\n{t}")
        new_am = "\n\n".join(parts)
        after = gratio(new_am)
        if after > a.threshold:
            still.append(n)
        if not a.dry_run:
            d["attachments_md"] = new_am
            json.dump(d, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        rebuilt += 1
        print(f"  {'DRY' if a.dry_run else 'REBUILD'} {os.path.basename(fp)}  {len(am)}→{len(new_am)}B  garbage {round(100*gratio(am))}%→{round(100*after)}%")

    print(f"\ndotčených {len(affected)}  přestavěno {rebuilt}  bez_joinu {len(nojoin)}  stále_balast {len(still)}")
    if nojoin: print("  BEZ JOINU (id není v opps):", nojoin)
    if still:  print("  STÁLE BALAST:", still)
    print("\nINDICES pro re-run:")
    print(json.dumps(affected))


if __name__ == "__main__":
    main()
