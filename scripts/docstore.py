#!/usr/bin/env python3
"""Kanonický DOC-STORE — perzistuje stažené podklady (PDF/DOC/XLS → text) na jedno místo.

   data/files/<source>/<sha8>.<ext>   originál
   data/files/<source>/<sha8>.txt     extrahovaný text
   data/files/manifest.jsonl          index: {url, source, sha, ext, raw_path, txt_path, bytes, chars, ok}

IDEMPOTENTNÍ (podle sha url → 1× stáhne). Tím vzniká úplný řetězec
oportunita → provenance.documents[].txt_path → konkrétní soubor (grounding/audit).
Stávající převody (data/vismo_files, dsw2_files) lze zaregistrovat bez re-downloadu (--index).

Použití:
  python3 scripts/docstore.py --from-harvest data/praha_grants.jsonl --source praha
  python3 scripts/docstore.py --index data/vismo_documents.jsonl --source vismo \
        --url-path attachments[].url --txt-path attachments[].txt_path
  python3 scripts/docstore.py --lookup "<url>"
"""
import argparse, hashlib, json, os, sys, threading
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsw2_fetch as df
from limits import L

ROOT = "data/files"
MANIFEST = os.path.join(ROOT, "manifest.jsonl")
_LOCK = threading.Lock()   # serializuje mutaci manifestu (dict + append) při paralelním stahování

def sha_of(url):
    return hashlib.sha1((url or "").encode("utf-8")).hexdigest()[:16]

def load_manifest():
    idx = {}
    if os.path.exists(MANIFEST):
        for l in open(MANIFEST, encoding="utf-8"):
            try:
                e = json.loads(l); idx[e["url"]] = e
            except Exception:
                pass
    return idx

def _append(entry):
    os.makedirs(ROOT, exist_ok=True)
    with open(MANIFEST, "a", encoding="utf-8") as o:
        o.write(json.dumps(entry, ensure_ascii=False) + "\n")

def store_url(url, source, manifest, timeout=25):
    """Idempotentně stáhni+konvertuj url do data/files/<source>/. Vrať manifest entry.
    Thread-safe: pomalá část (sniff/download/convert) běží bez zámku, mutace manifestu pod _LOCK."""
    if url in manifest:
        return manifest[url]
    sha = sha_of(url)
    d = os.path.join(ROOT, source); os.makedirs(d, exist_ok=True)
    ext = df.sniff_ext(url, 15) or df.ext_of(url) or "bin"
    raw = os.path.join(d, f"{sha}.{ext}"); txt = os.path.join(d, f"{sha}.txt")
    entry = {"url": url, "source": source, "sha": sha, "ext": ext,
             "raw_path": raw, "txt_path": None, "bytes": 0, "chars": 0, "ok": False}
    try:
        nb, derr = df.download(url, raw, timeout, L("safety.doc_download_max_mb") * 1024 * 1024)
        entry["bytes"] = nb or 0
        if not derr:
            chars, cerr = df.convert(raw, ext, txt, 60)   # NEignoruj návrat: konverze může selhat
            real = 0
            if os.path.exists(txt):
                try: real = len(open(txt, encoding="utf-8", errors="ignore").read().strip())
                except Exception: real = 0
            if real > 0:                                   # audit #30: měř SKUTEČNÝ text (ne getsize) — sken→pdftotext
                entry["txt_path"] = txt; entry["chars"] = real; entry["ok"] = True   # dá jen \f → 0 znaků → ok:False → ⚠
            elif cerr:                                     # surface chybu, ne ji maskovat jako 'prázdný převod'
                entry["err"] = cerr
        else:
            entry["err"] = derr
    except Exception as e:
        entry["err"] = f"{type(e).__name__}: {str(e)[:60]}"
    if not entry["ok"]:   # audit #32: nestažený/prázdný dokument NAHLAS, ne jen tiché ok:false
        print(f"⚠ doc-store: {url} → {entry.get('err') or 'prázdný převod (0 znaků)'}", file=sys.stderr)
    with _LOCK:
        manifest[url] = entry; _append(entry)
    return entry

def from_harvest(harvest_file, source, manifest, only_urls=None, workers=None):
    workers = workers or L("http.download_workers")
    seen, urls = set(), []
    for l in open(harvest_file, encoding="utf-8"):
        try: r = json.loads(l)
        except Exception: continue
        if only_urls is not None and r.get("url") not in only_urls:
            continue
        for u in (r.get("documents") or r.get("attachments") or []):   # harvest_site=documents, marwel/eagri/mv=attachments
            u = u.get("url") if isinstance(u, dict) else u
            if u and u not in seen:
                seen.add(u); urls.append(u)
    todo = [u for u in urls if u not in manifest]   # idempotence: přeskoč už zmaterializované
    cached = len(urls) - len(todo)
    n_ok = n_skip = 0
    def work(u):
        e = store_url(u, source, manifest)
        print(f"  {'OK ' if e['ok'] else 'ERR'} {e['chars']:>7}z {u[-55:]}", file=sys.stderr)
        return e["ok"]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for ok in ex.map(work, todo):
            n_ok += int(ok); n_skip += int(not ok)
    if cached:
        print(f"  (cached: {cached} už v manifestu, přeskočeno)", file=sys.stderr)
    return n_ok, n_skip

def index_existing(jsonl, source, manifest):
    """Zaregistruj UŽ převedené soubory (vismo/dsw2 attachments) bez re-downloadu."""
    n = 0
    for l in open(jsonl, encoding="utf-8"):
        try: r = json.loads(l)
        except Exception: continue
        for a in (r.get("attachments") or []):
            u, tp = a.get("url"), a.get("txt_path")
            if u and u not in manifest:
                e = {"url": u, "source": source, "sha": sha_of(u), "ext": a.get("ext"),
                     "raw_path": None, "txt_path": tp if tp and os.path.exists(tp) else None,
                     "bytes": int(a.get("bytes") or 0), "chars": int(a.get("txt_chars") or 0),
                     "ok": bool(tp and os.path.exists(tp))}
                manifest[u] = e; _append(e); n += 1
    return n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-harvest"); ap.add_argument("--source", default="?")
    ap.add_argument("--only-urls", help="soubor s URL (1/řádek) — stáhni jen dokumenty těchto stránek")
    ap.add_argument("--index"); ap.add_argument("--lookup")
    ap.add_argument("--workers", type=int, default=L("http.download_workers"),
                    help="paralelních vláken na stahování (default limits.json http.download_workers)")
    args = ap.parse_args()
    manifest = load_manifest()
    if args.lookup:
        print(json.dumps(manifest.get(args.lookup, {}), ensure_ascii=False, indent=1)); return
    if args.index:
        n = index_existing(args.index, args.source, manifest)
        print(json.dumps({"MARKER": "DOCSTORE_INDEX", "registered": n, "source": args.source})); return
    if args.from_harvest:
        only = None
        if args.only_urls:
            only = set(l.strip() for l in open(args.only_urls) if l.strip())
        ok, skip = from_harvest(args.from_harvest, args.source, manifest, only, args.workers)
        print(json.dumps({"MARKER": "DOCSTORE", "stored_ok": ok, "failed": skip,
                          "source": args.source, "manifest": MANIFEST}, ensure_ascii=False))

if __name__ == "__main__":
    main()
