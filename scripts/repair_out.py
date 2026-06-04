#!/usr/bin/env python3
"""Batch json_repair nad výstupy vrstvy 2 (směr B).

Agenti (scripts/extract_wf.js) zapisují JSON do <outdir>/<basename>.json přes Write tool.
České verbatim citace v `evidence` občas nesou drobné escaping vady → tady je srovná json_repair.
Žádné ořezávání; jen kanonizace (loads → dumps, ensure_ascii=False).

Volitelný --fallback je dump návratové hodnoty workflow (pole {outpath|path, text}); když soubor
chybí nebo je prázdný, vezme se JSON z `text` (případně z ```json fence) a zapíše se.

Usage:
  python3 scripts/repair_out.py --outdir /tmp/out [--expect /tmp/mg2 --prefix grant --count 597] \
      [--fallback /tmp/wf_return.json] [--quiet]
"""
import argparse, glob, json, os, re, sys
import json_repair

FENCE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.S)


def extract_json_text(s):
    if not s:
        return None
    m = FENCE.search(s)
    if m:
        return m.group(1)
    i, j = s.find("{"), s.rfind("}")
    return s[i:j + 1] if (i != -1 and j > i) else s


def load_repaired(raw):
    """raw str → (obj, was_repaired) nebo (None, False)."""
    if raw is None:
        return None, False
    raw = raw.strip()
    if not raw:
        return None, False
    try:
        return json.loads(raw), False
    except Exception:
        pass
    txt = extract_json_text(raw)
    try:
        obj = json_repair.loads(txt)
        if isinstance(obj, (dict, list)) and obj:
            return obj, True
    except Exception:
        pass
    return None, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="/tmp/out")
    ap.add_argument("--expect")            # dir vstupů pro detekci chybějících
    ap.add_argument("--prefix", default="")
    ap.add_argument("--count", type=int)
    ap.add_argument("--fallback")          # dump workflow return (JSON pole)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    # fallback mapa basename -> text
    fb = {}
    if a.fallback and os.path.exists(a.fallback):
        arr = json.load(open(a.fallback))
        for r in arr:
            p = r.get("outpath") or r.get("path") or ""
            if p and r.get("text"):
                fb[os.path.basename(p)] = r["text"]

    # očekávané basenames
    if a.expect and a.count is not None:
        expected = [f"{a.prefix}_{i:04d}.json" for i in range(a.count)]
    elif a.expect:
        expected = sorted(os.path.basename(p) for p in glob.glob(f"{a.expect}/*.json"))
    else:
        expected = sorted(os.path.basename(p) for p in glob.glob(f"{a.outdir}/*.json"))

    def fill_ratio(obj):
        """podíl vyplněných top-level polí (mimo evidence): non-null/non-empty."""
        if not isinstance(obj, dict):
            return 0, 0
        keys = [k for k in obj if k != "evidence"]
        filled = sum(1 for k in keys if obj[k] not in (None, "", [], {}))
        return filled, len(keys)

    valid = repaired = from_fb = failed = missing = no_ev = 0
    fails, misses, noevs, lowfill = [], [], [], []
    sizes, fills = [], []
    for base in expected:
        fp = os.path.join(a.outdir, base)
        raw = None
        if os.path.exists(fp):
            raw = open(fp, encoding="utf-8", errors="replace").read()
        obj, was_rep = load_repaired(raw)
        src = "file"
        if obj is None and base in fb:           # fallback z text návratu (jen je-li --fallback dodán)
            obj, was_rep = load_repaired(fb[base])
            src = "fallback"
        if obj is None:
            if raw is None and base not in fb:
                missing += 1; misses.append(base)
            else:
                failed += 1; fails.append(base)
            continue
        # kanonizuj zpět do souboru
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        if src == "fallback":
            from_fb += 1
        elif was_rep:
            repaired += 1
        else:
            valid += 1
        ev = obj.get("evidence") if isinstance(obj, dict) else None
        if not ev:
            no_ev += 1; noevs.append(base)
        filled, ntot = fill_ratio(obj)
        sizes.append(os.path.getsize(fp))
        fills.append(filled)
        if ntot and filled / ntot < 0.25:        # podezřele prázdný výstup (mimo legitimně prázdné stuby)
            lowfill.append(f"{base}({filled}/{ntot})")

    tot = len(expected)
    ok = valid + repaired + from_fb
    avg_sz = round(sum(sizes) / len(sizes)) if sizes else 0
    avg_fl = round(sum(fills) / len(fills), 1) if fills else 0
    print(f"OK {ok}/{tot}  (valid={valid} repaired={repaired} fallback={from_fb})  "
          f"failed={failed} missing={missing}  no_evidence={no_ev}")
    print(f"velikost: prům {avg_sz} B (min {min(sizes) if sizes else 0} / max {max(sizes) if sizes else 0}); "
          f"vyplněno: prům {avg_fl} polí; low_fill={len(lowfill)}")
    if not a.quiet:
        if fails:   print("  FAILED :", " ".join(fails[:40]))
        if misses:  print("  MISSING:", " ".join(misses[:40]))
        if noevs:   print("  NO_EVID:", " ".join(noevs[:40]))
        if lowfill: print("  LOW_FILL:", " ".join(lowfill[:40]))
    sys.exit(0 if (failed == 0 and missing == 0) else 1)


if __name__ == "__main__":
    main()
