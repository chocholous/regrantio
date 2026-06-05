#!/usr/bin/env python3
"""Krok 1 vrstvy 2 pro samosprávné harvesty: stáhni+konvertuj přílohy do kanonického doc-store.

Reuse scripts/docstore.store_url (idempotentní, dedup přes data/files/manifest.jsonl, sniff+convert).
Normalizuje heterogenní klíče příloh napříč městskými/krajskými harvesty (_attachments/_documents/
attachments/_files = list[str] | list[{url}]). Relativní URL spojí proti URL programu. Paralelně.

Vynecháno: JM (_attachments jsou session-bound GINIS → už extrahováno jm_pdf_enrich.py),
Děčín (_prilohy nesou jen id bez URL). Ostatní samosprávy s přímými URL.

Usage: python3 scripts/fetch_samosprava_docs.py [data/h_mesto_hk.json ...]   (default: auto-set)
"""
import argparse, glob, json, os, sys
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docstore

ATT_KEYS = ("_attachments", "_documents", "attachments", "_files", "documents")
SKIP = ("h_kraj_jm.json", "h_mesto_decin.json")   # session-bound / bez URL


def host_of(src):
    return (src or "").replace("www.", "").split("/")[0]


def doc_urls(prog):
    base = prog.get("url") or ""
    out = []
    for k in ATT_KEYS:
        v = prog.get(k)
        if not v or not isinstance(v, list):
            continue
        for it in v:
            u = it if isinstance(it, str) else (it.get("url") if isinstance(it, dict) else None)
            if u:
                out.append(urljoin(base, u))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="*")
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    files = a.inputs or [f for f in glob.glob("data/h_mesto_*.json") + glob.glob("data/h_kraj_*.json")
                         if os.path.basename(f) not in SKIP]

    manifest = docstore.load_manifest()
    # posbírej (url, source) napříč harvesty, dedup v rámci běhu
    jobs = {}
    for f in files:
        if os.path.basename(f) in SKIP:
            continue
        try:
            H = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        src = host_of(H.get("source") or os.path.basename(f))
        for p in H.get("programs", []):
            for u in doc_urls(p):
                jobs.setdefault(u, src)
    todo = [(u, s) for u, s in jobs.items() if u not in manifest]
    print(f"příloh celkem: {len(jobs)} | už v doc-store (dedup): {len(jobs)-len(todo)} | ke stažení: {len(todo)}",
          file=sys.stderr)

    def work(us):
        u, s = us
        e = docstore.store_url(u, s, manifest)
        return e.get("ok"), e.get("chars", 0), e.get("err")
    ok = fail = chars = 0
    errs = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for good, ch, err in ex.map(work, todo):
            if good:
                ok += 1; chars += ch
            else:
                fail += 1
                if err and len(errs) < 15:
                    errs.append(err)
    print(json.dumps({"MARKER": "FETCH_DOCS", "stahováno": len(todo), "ok": ok, "fail": fail,
                      "celkem_znaků": chars, "dedup_skip": len(jobs) - len(todo)}, ensure_ascii=False))
    if errs:
        print("vzorek chyb:", "; ".join(errs[:10]), file=sys.stderr)


if __name__ == "__main__":
    main()
