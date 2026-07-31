#!/usr/bin/env python3
"""AZV ČR + program-life.cz (WP posts/pages z data/wp_full/) → vstup vrstvy 2 (classify/extract).

Z PLNÝCH wp_harvest záznamů (content_text plný, documents[] zachované) sestaví JSONL
záznamy ve formátu build_extract_input.py / build_samosprava_extract_input.py:
  {id, web, title, body, attachments_md}
  - id   = url záznamu (stabilní join klíč)
  - body = PLNÝ content_text (žádný ořez — limits.acquisition.input_truncation=null)
  - attachments_md = PLNÝ text VŠECH dokumentů, materializace přes doc-store
    (docstore.store_url → data/files/<source>/, idempotentní, manifest.jsonl)

Filtr JEN strukturální (prefilter.clean: empty/exact-dup/nav) — žádný sémantický
pre-filtr, obsahový šum rozhodne classify (fáze 3). Dedup je GLOBÁLNÍ přes všechny
vstupní soubory (post a page se stejným obsahem = 1 vstup).

Spuštění (z kořene repa):
  python3 scripts/azv_life_build_input.py            # default 4 soubory → data/extract_input_azv_life.jsonl
  python3 scripts/azv_life_build_input.py --inputs data/wp_full/azvcr-cz__posts.jsonl ... --out ...
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docstore, prefilter
from limits import L

DEFAULT_INPUTS = [
    "data/wp_full/azvcr-cz__posts.jsonl",
    "data/wp_full/azvcr-cz__pages.jsonl",
    "data/wp_full/program-life-cz__posts.jsonl",
    "data/wp_full/program-life-cz__pages.jsonl",
]


def host_of(url):
    return re.sub(r"^https?://(www\.)?", "", url or "").split("/")[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", nargs="+", default=DEFAULT_INPUTS)
    ap.add_argument("--out", default="data/extract_input_azv_life.jsonl")
    args = ap.parse_args()

    # 1) načti vše + namapuj na prefilter tvar (text/documents) — LOSSLESS, jen aliasy
    recs = []
    for f in args.inputs:
        for l in open(f, encoding="utf-8"):
            r = json.loads(l)
            r["text"] = r.get("content_text") or ""          # alias pro prefilter
            r["_harvest_file"] = f
            recs.append(r)
    n_in = len(recs)

    # 2) strukturální pre-filtr (100% bezpečný: empty/exact-dup/nav) — GLOBÁLNĚ přes soubory
    recs, drop = prefilter.clean(recs, L("acquisition.prefilter_empty_text_max"))
    print(f"  pre-filtr: {n_in} → {len(recs)} (−{sum(drop.values())}: empty {drop['empty']}, "
          f"dup {drop['dup']}, nav {drop['nav']})", file=sys.stderr)

    # 3) materializace dokumentů do doc-store (idempotentní, paralelně per harvest soubor)
    manifest = docstore.load_manifest()
    for f in sorted({r["_harvest_file"] for r in recs}):
        source = host_of(json.loads(open(f, encoding="utf-8").readline()).get("url", "")) or "wp"
        ok, fail = docstore.from_harvest(f, source, manifest)
        print(f"  doc-store {os.path.basename(f)} ({source}): ok {ok}, fail {fail}", file=sys.stderr)

    # 4) sestav vstupy {id, web, title, body, attachments_md} — PLNÉ texty, žádný ořez.
    # Dedup podle id (URL): WP post+page se stejným slugem sdílí permalink → 1 kanonická
    # stránka = 1 vstup; vyhrává bohatší varianta (delší body+přílohy). Strukturální, ne obsahový.
    n_att = 0
    by_id = {}
    for r in recs:
        parts = []
        for u in (r.get("documents") or []):
            e = manifest.get(u)
            sp = (e or {}).get("md_path") or (e or {}).get("txt_path")
            if sp and os.path.exists(sp):
                t = open(sp, encoding="utf-8", errors="replace").read()
                if t.strip():
                    parts.append(f"[{u.split('/')[-1][:40]}]\n{t}")
                    n_att += 1
        doc = {"id": r.get("url"), "web": host_of(r.get("url")),
               "title": r.get("title_text"), "body": r.get("content_text") or "",
               "attachments_md": "\n\n".join(parts)}
        prev = by_id.get(doc["id"])
        if prev is None or len(doc["body"]) + len(doc["attachments_md"]) > len(prev["body"]) + len(prev["attachments_md"]):
            by_id[doc["id"]] = doc
    n_id_dup = len(recs) - len(by_id)
    if n_id_dup:
        print(f"  id-dedup (post+page stejný permalink): −{n_id_dup}", file=sys.stderr)
    n_att_nonempty = sum(1 for d in by_id.values() if d["attachments_md"])
    with open(args.out, "w", encoding="utf-8") as o:
        for doc in by_id.values():
            o.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(json.dumps({"MARKER": "EXTRACT_INPUT_AZV_LIFE", "in": n_in, "out_records": len(by_id),
                      "dropped": drop, "id_dedup": n_id_dup, "with_attachments_md": n_att_nonempty,
                      "attachment_texts": n_att, "out": args.out,
                      "next": "agent → classify_wf.js → extract_wf.js (orchestrátor)"},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
