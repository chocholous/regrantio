#!/usr/bin/env python3
"""vismo_modern — GAP-FILL: dotažení stránek, které BFS vrstvy 1 minul.

Completeness gate (coverage_verify) našel grant-relevantní URL mimo harvestovanou
sekci (výzvy, smlouvy o poskytnutí dotace = záznamy podpořených projektů, novinky).
Lossless princip: bere se VŠE, classify vrstva třídí později.

Vstup:  --extra-urls <file>  (1 URL/řádek; kandidáti z coverage_verify MISSED)
        --scan-sitemaps h1,h2 (hosty, kde coverage_verify narazil na loc-ceiling
        → stáhni sitemap CELOU, grant-keyword filtr, najdi URL nad rámec seznamu)
Dedup:  proti URL už v --out (normalizace: bez fragmentu/trailing-slash, klíč bez
        'www.' → malomerice.cz ≡ www.malomerice.cz; fetchuje se www varianta).
Výstup: APPEND do data/vismo_modern_documents.jsonl (stejný kontrakt — záznamy
        staví vismo_modern_detail.process; přílohy do data/vismo_modern_files/).
        Neúspěšné fetche se NEappendují (re-run je zkusí znovu), jen se reportují.

Usage:  python3 scripts/vismo_modern_gapfill.py --extra-urls /tmp/vismo_gap_urls.txt \
            --scan-sitemaps www.kr-ustecky.cz,www.teplice.cz,www.trinecko.cz,www.kutnahora.cz
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse, json, os, re, sys, threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from urllib.parse import urlparse, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vismo_modern_detail as vmd   # reuse: fetch, process (kontrakt záznamu + přílohy)
from limits import L

# grant-keyword filtr pro sitemap scan (zadání coverage gate; negativ = úřední
# deska stavebních řízení / zák. 106/1999 / výkresy — zjevně ne-grantové)
GRANT_POS = re.compile(r"dotac|grant|vyzv[ao]|prispevk|stipend|kotlik", re.I)
GRANT_NEG = re.compile(r"106-1999|uzemni-rozhodnut|stavebn|vykres", re.I)
LOC_RE = re.compile(r"<loc>([^<]+)</loc>")


def norm(u):
    return u.strip().split("#")[0].rstrip("/")


def dedup_key(u):
    """Klíč dedupu: bez fragmentu/trailing-slash, host bez 'www.'."""
    return norm(u).replace("://www.", "://", 1)


def prefer_www(cands, url):
    """Při kolizi klíče drž www variantu (oba vedou na totéž)."""
    k = dedup_key(url)
    if k not in cands or "://www." in url:
        cands[k] = norm(url)


def load_existing_keys(out_path):
    keys = set()
    if os.path.exists(out_path):
        for line in open(out_path, encoding="utf-8"):
            try:
                keys.add(dedup_key(json.loads(line)["url"]))
            except (json.JSONDecodeError, KeyError):
                continue
    return keys


def scan_sitemap(host):
    """Stáhni sitemap.xml CELOU (bez loc-ceilingu) → grant-like locs téhož hostu."""
    xml = vmd.fetch(f"https://{host}/sitemap.xml")
    if not xml:
        return None, []
    locs = LOC_RE.findall(xml)
    out = []
    for u in locs:
        u = norm(u)
        if urlparse(u).netloc.replace("www.", "") != host.replace("www.", ""):
            continue
        uq = unquote(u)
        if GRANT_POS.search(uq) and not GRANT_NEG.search(uq):
            out.append(u)
    return len(locs), out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extra-urls", required=True, help="soubor s kandidátními URL (1/řádek)")
    ap.add_argument("--scan-sitemaps", help="hosty s loc-ceilingem v coverage_verify (čárkami)")
    ap.add_argument("--out", default="data/vismo_modern_documents.jsonl")
    ap.add_argument("--files-dir", default="data/vismo_modern_files")
    ap.add_argument("--no-attachments", action="store_true")
    ap.add_argument("--timeout", type=int, default=None)
    ap.add_argument("--today", help="YYYY-MM-DD (default: dnešek)")
    ap.add_argument("--page-workers", type=int, default=None,
                    help="souběh stránek (default http.download_workers)")
    args = ap.parse_args()

    today = date.fromisoformat(args.today) if args.today else date.today()
    timeout = args.timeout or L("http.default_timeout_s")
    max_bytes = L("safety.doc_download_max_mb") * 1024 * 1024
    page_workers = args.page_workers or L("http.download_workers")
    # celkový souběh proti hostu ≈ http.download_workers: přílohy per stránka sériově,
    # pokud je page-pool plný (žádný nový limit, jen rozdělení existujícího)
    att_workers = max(1, L("http.download_workers") // page_workers)

    raw = [l.strip() for l in open(args.extra_urls, encoding="utf-8") if l.strip()]
    cands = {}
    for u in raw:
        prefer_www(cands, u)

    existing = load_existing_keys(args.out)

    # sitemap scan nad rámec seznamu (ceiling_hit v coverage_verify)
    extra_beyond, sitemap_fail = {}, []
    if args.scan_sitemaps:
        for host in args.scan_sitemaps.split(","):
            host = host.strip()
            n_locs, grantlike = scan_sitemap(host)
            if n_locs is None:
                sitemap_fail.append(host)
                print(f"⚠ sitemap fetch FAIL: {host}", file=sys.stderr)
                continue
            new = 0
            for u in grantlike:
                k = dedup_key(u)
                if k in cands or k in existing:
                    continue
                prefer_www(extra_beyond, u)
                new += 1
            print(f"sitemap {host}: locs={n_locs} grant-like={len(grantlike)} beyond-list={new}",
                  file=sys.stderr)
        cands.update(extra_beyond)

    todo = [u for k, u in cands.items() if k not in existing]
    skipped = len(cands) - len(todo)
    print(f"kandidátů={len(raw)} uniq={len(cands)} už-v-out={skipped} "
          f"extra_beyond_ceiling={len(extra_beyond)} → ke stažení {len(todo)}", file=sys.stderr)

    lock = threading.Lock()
    ok_by_host, fail_urls, attachments_ok = Counter(), [], 0
    done = 0

    def work(url):
        host = urlparse(url).netloc
        call = {"foundation_id": host.replace("www.", ""), "title": None, "url": url,
                "date": None, "section": None}
        rec = vmd.process(call, args.files_dir, not args.no_attachments,
                          timeout, max_bytes, today, workers=att_workers)
        if rec.get("error") == "fetch_fail":        # 2. šance na transientní chyby
            rec = vmd.process(call, args.files_dir, not args.no_attachments,
                              timeout, max_bytes, today, workers=att_workers)
        return url, host, rec

    with ThreadPoolExecutor(max_workers=page_workers) as ex, \
            open(args.out, "a", encoding="utf-8") as out:
        futs = [ex.submit(work, u) for u in todo]
        for f in as_completed(futs):
            url, host, rec = f.result()
            with lock:
                done += 1
                if rec.get("error"):
                    fail_urls.append(url)
                    print(f"[{done}/{len(todo)}] FAIL {url}", file=sys.stderr, flush=True)
                    continue
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                ok_by_host[host] += 1
                attachments_ok += sum(1 for a in rec.get("attachments", [])
                                      if a.get("bytes") and not a.get("download_err"))
                if done % 50 == 0 or done == len(todo):
                    print(f"[{done}/{len(todo)}] ok={sum(ok_by_host.values())} "
                          f"fail={len(fail_urls)} att_ok={attachments_ok}",
                          file=sys.stderr, flush=True)

    for u in fail_urls:
        print(f"FAILED_URL {u}", file=sys.stderr)
    print(json.dumps({"MARKER": "VISMO_GAPFILL", "candidates": len(raw),
                      "fetched_ok": sum(ok_by_host.values()), "failed": len(fail_urls),
                      "appended": sum(ok_by_host.values()), "attachments_ok": attachments_ok,
                      "by_host": dict(ok_by_host), "skipped_already_in_out": skipped,
                      "extra_beyond_ceiling": len(extra_beyond),
                      "sitemap_fail": sitemap_fail}, ensure_ascii=False))


if __name__ == "__main__":
    main()
