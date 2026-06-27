#!/usr/bin/env python3
"""Driver fáze 2 (deterministická část) — strukturní zdroj → vstup pro extract_wf.js.

Konsoliduje dřívější ad-hoc /tmp lepidlo. Per layer-1 záznam:
  1) (jen harvest) strukturální pre-filtr (prefilter.clean — 100% bezpečné, empty/dup/nav)
  2) materializace dokumentů do doc-store (docstore.store_url → data/files/<source>/)
     — pro vismo se použijí UŽ převedené attachments[].txt_path (bez re-downloadu)
  3) sestav {id, web, force_type, title, body, attachments_md} = PLNÝ text + PLNÝ text dokumentů
     (žádný ořez — limits.acquisition.input_truncation=null)
Výstup: <out-dir>/grant_NN.json + paths.json. `id` = STABILNÍ klíč pro join zpět
(harvest/vismo = url; dsw2-appeals = foundation_id|title, protože appeal url je sdílená).
Ty pak agent protáhne `extract_wf.js`, výsledek → `opportunities.py` (--from-extraction
nebo --enrich vismo|dsw2-appeals).

Spuštění:
  python3 scripts/build_extract_input.py data/h19_nadacecez.jsonl --source nadacecez --out-dir /tmp/ei_nadacecez
  python3 scripts/build_extract_input.py data/vismo_documents.jsonl --source-type vismo --source vismo --out-dir /tmp/ei_vismo
  python3 scripts/build_extract_input.py data/dsw2_appeals.jsonl --source-type dsw2-appeals --source dsw2 --out-dir /tmp/ei_appeals
"""
import argparse, glob, json, os, re, sys
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docstore, prefilter
from dsw2_fetch import DOC_EXT_RE
from limits import L

def _host(u):
    return re.sub(r"^https?://(www\.)?", "", u or "").split("/")[0]

def _shape(r, source_type, source):
    """Vrať (id, web, title, body, [(doc_url, txt_path|None), …]) per tvar zdroje.
    txt_path != None = už převedeno (vismo) → doc-store se přeskočí."""
    if source_type == "vismo":
        docs = [(a.get("url"), a.get("txt_path")) for a in (r.get("attachments") or [])
                if isinstance(a, dict) and a.get("url")]
        return r.get("url"), (r.get("web") or _host(r.get("url"))), r.get("title"), r.get("body_text") or "", docs
    if source_type == "dsw2-appeals":
        docs = [(u, None) for u in (r.get("links") or []) if DOC_EXT_RE.search(u)]  # jen reálné dokumenty
        key = f"{r.get('foundation_id')}|{r.get('title')}"                          # appeal url je sdílená /explore/appeals
        return key, _host(r.get("url")), r.get("title"), r.get("description") or "", docs
    # harvest (default) — tolerantní k variantám klíčů napříč VŠEMI layer-1 harvestery
    # (wp_harvest, harvest_site, eeagrants, mv_cms, kentico_irop), aby žádný neemitoval prázdný title/body:
    #   title: kanonický `title` (string); fallback `title_text` u legacy wp_full snapshotu (title = raw objekt)
    #   body:  `text` (wp/harvest_site/eeagrants) | `body_text` (mv_cms/kentico) | `content_text` (legacy wp)
    #   docs:  `documents[]` (url string nebo dict) | `attachments[]` (dict s url + volitelným txt_path)
    title = r.get("title")
    if not isinstance(title, str):
        title = r.get("title_text")
    body = r.get("text") or r.get("body_text") or r.get("content_text") or ""
    docs = []
    for u in (r.get("documents") or r.get("attachments") or []):
        du, tp = (u.get("url"), u.get("txt_path")) if isinstance(u, dict) else (u, None)
        if du:
            docs.append((urljoin(r.get("url", ""), du), tp))
    return r.get("url"), source, title, body, docs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--source", required=True)
    ap.add_argument("--source-type", default="harvest", choices=["harvest", "vismo", "dsw2-appeals"])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--force-type", default="grant", choices=["grant", "project", "foundation_mission"])
    ap.add_argument("--no-prefilter", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    for _p in glob.glob(os.path.join(args.out_dir, "grant_*.json")):  # audit #6: portable + bezpečné (ne os.system shell glob)
        os.remove(_p)

    recs = [json.loads(l) for l in open(args.input, encoding="utf-8")]
    # pre-filtr JEN u harvest (strukturní zdroje jsou už čisté)
    if args.source_type == "harvest" and not args.no_prefilter:
        recs, drop = prefilter.clean(recs, L("acquisition.prefilter_empty_text_max"))
        print(f"  pre-filtr: −{sum(drop.values())} (empty {drop['empty']}, dup {drop['dup']}, nav {drop['nav']})", file=sys.stderr)

    manifest = docstore.load_manifest()
    paths = []
    for i, r in enumerate(recs):
        sid, web, title, body, docs = _shape(r, args.source_type, args.source)
        parts = []
        for u, txt_path in docs:
            if txt_path and os.path.exists(txt_path):          # vismo: už převedeno
                sp = txt_path
            else:                                              # harvest/appeals: doc-store (download+convert, idempotentní)
                e = docstore.store_url(u, args.source, manifest)
                sp = e.get("md_path") or e.get("txt_path")
            if sp and os.path.exists(sp):
                t = open(sp, encoding="utf-8", errors="replace").read()
                if t.strip():
                    parts.append(f"[{(u or '').split('/')[-1][:40]}]\n{t}")
        doc = {"id": sid, "web": web, "force_type": args.force_type,
               "title": title, "body": body, "attachments_md": "\n\n".join(parts)}
        p = os.path.join(args.out_dir, f"grant_{i:02d}.json")
        json.dump(doc, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        paths.append(p)
    json.dump(paths, open(os.path.join(args.out_dir, "paths.json"), "w"), ensure_ascii=False)

    nxt = (f"opportunities.py --enrich {args.source_type} --structured {args.input} "
           f"--from-extraction <result> --src-dir {args.out_dir} --link-docs"
           if args.source_type in ("vismo", "dsw2-appeals") else
           f"opportunities.py --from-extraction <result> --source {args.source} "
           f"--src-dir {args.out_dir} --harvest-file {args.input} --link-docs")
    print(json.dumps({"MARKER": "EXTRACT_INPUT", "source": args.source, "source_type": args.source_type,
                      "docs": len(paths), "harvest_file": args.input, "out_dir": args.out_dir,
                      "next": f"agent → extract_wf.js(paths) → {nxt}"}, ensure_ascii=False))

if __name__ == "__main__":
    main()
