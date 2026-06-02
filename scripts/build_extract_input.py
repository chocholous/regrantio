#!/usr/bin/env python3
"""Driver fáze 2 (deterministická část) — vrstva-1 jsonl → vstup pro extract_wf.js.

Konsoliduje dřívější ad-hoc /tmp lepidlo. Per layer-1 záznam:
  1) strukturální pre-filtr (prefilter.clean — 100% bezpečné, empty/dup/nav)
  2) stáhni VŠECHNY documents[] do doc-store (docstore.store_url → data/files/<source>/)
  3) sestav {id, web, force_type, title, body, attachments_md} = PLNÝ text + PLNÝ text VŠECH příloh
     (žádný ořez — limits.acquisition.input_truncation=null)
Výstup: <out-dir>/grant_NN.json + paths.json. Ty pak agent protáhne `extract_wf.js`,
výsledek → `opportunities.py --from-extraction … --link-docs`.

Spuštění:
  python3 scripts/build_extract_input.py data/h19_nadacecez.jsonl --source nadacecez --out-dir /tmp/ei_nadacecez
"""
import argparse, json, os, sys
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docstore, prefilter
from limits import L

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")                       # layer-1 jsonl {url,title,text,documents[]}
    ap.add_argument("--source", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--force-type", default="grant", choices=["grant", "project", "foundation_mission"])
    ap.add_argument("--no-prefilter", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    os.system(f"rm -f {args.out_dir}/grant_*.json")

    recs = [json.loads(l) for l in open(args.input, encoding="utf-8")]
    if not args.no_prefilter:
        recs, drop = prefilter.clean(recs, L("acquisition.prefilter_empty_text_max"))
        print(f"  pre-filtr: −{sum(drop.values())} (empty {drop['empty']}, dup {drop['dup']}, nav {drop['nav']})", file=sys.stderr)

    manifest = docstore.load_manifest()
    paths = []
    for i, r in enumerate(recs):
        parts = []
        for u in (r.get("documents") or []):
            u = urljoin(r.get("url", ""), u if isinstance(u, str) else u.get("url", ""))
            e = docstore.store_url(u, args.source, manifest)   # idempotentní download+convert
            sp = e.get("md_path") or e.get("txt_path")         # preferuj markdown (tabulky), fallback txt
            if sp and os.path.exists(sp):
                t = open(sp, encoding="utf-8", errors="replace").read()
                if t.strip():
                    parts.append(f"[{u.split('/')[-1][:40]}]\n{t}")
        doc = {"id": r.get("url"), "web": args.source, "force_type": args.force_type,
               "title": r.get("title"), "body": r.get("text") or "", "attachments_md": "\n\n".join(parts)}
        p = os.path.join(args.out_dir, f"grant_{i:02d}.json")
        json.dump(doc, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        paths.append(p)
    json.dump(paths, open(os.path.join(args.out_dir, "paths.json"), "w"), ensure_ascii=False)
    print(json.dumps({"MARKER": "EXTRACT_INPUT", "source": args.source, "docs": len(paths),
                      "harvest_file": args.input, "out_dir": args.out_dir,
                      "next": "agent → extract_wf.js(paths) → opportunities.py --from-extraction <result> "
                              f"--source {args.source} --src-dir {args.out_dir} --harvest-file {args.input} --link-docs"},
                     ensure_ascii=False))

if __name__ == "__main__":
    main()
