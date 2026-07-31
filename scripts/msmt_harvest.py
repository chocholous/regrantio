#!/usr/bin/env python3
"""MŠMT (msmt.gov.cz, CMS Marwel/QCM) — layer-1 lossless harvest dotačních/grantových sekcí.

STRUKTURA PŘED PRÓZOU — co Marwel dává strukturovaně (ověřeno sondou 2026-06-10):
  - ŽÁDNÉ veřejné JSON API; RSS (/rss/cs, RSSFit 1.5) = jen posledních ~30 článků, ne katalog.
  - sitemap_index → sitemap_marwel_0.xml (~17k URL vč. ?lang variant) = completeness katalog
    (využívá scripts/coverage_verify.py), ne obsah.
  - rubrika = šablonovaný listing: položky `<div class="  item"><h3><a href>` + pager
    `/modules/marwel/index.php?rewrite=<rubrika>&str=N` → deterministická enumerace článků.
  - článek: `#article` → `<h2>` titul, `.article-perex`, `.article-content`.
  - přílohy: `<span class="dw_item dw_<ext>"><a href="/file/<id>/">jméno</a></span>` →
    landing stránka → přímý link `/file/<id>_<v>_<l>/` → 302 `/download/` (binárka
    s Content-Disposition) → text přes dsw2_fetch (pdftotext/textutil/openpyxl).

Harvest = BFS z dotačních hubů po linkách v #article obsahu (NE sidebar nav):
  - listing položky (h3) a pager linky se berou VŠECHNY (rubrika už je grant-relevantní),
  - ostatní obsahové linky filtrem GRANT (diakritika: dota[cč], v[ýy]zv, \xa0 ošetřeno).
Data se berou CELÁ (žádný cap; runaway hlídá limits safety.runaway_page_ceiling, loguje ⚠).
Pozn.: robots.txt deklaruje Crawl-Delay: 30 — viz --delay (default mírnější, jednorázový harvest).

Výstup (kontrakt jako vismo_documents.jsonl):
  data/msmt_documents.jsonl  {host, title, url, date, kind, body_text, attachments[], n_attachments}
  data/msmt_files/<host>/<sha8>.<ext> + .txt

Spuštění (z kořene repa):
  python3 scripts/msmt_harvest.py                       # plný harvest
  python3 scripts/msmt_harvest.py --resume --extra-urls /tmp/missed.txt   # doplnění děr
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse
import hashlib
import html as H
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit, parse_qsl, urlencode, urlunsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsw2_fetch import (safe_url, sniff_ext, download, convert, ext_of,  # noqa: E402
                        UA, DOC_EXTS, DOC_EXT_RE)
from limits import L  # noqa: E402
import http_util  # noqa: E402  (jednotna TLS politika + fallback)

HOST = "msmt.gov.cz"
HOST_ALIASES = {"msmt.gov.cz", "www.msmt.gov.cz", "msmt.cz", "www.msmt.cz"}
SEEDS = ["https://msmt.gov.cz/dotacni-programy"]
# grant-relevance linku (URL slug NEBO text kotvy); diakritika v obou tvarech
GRANT = re.compile(r"grant|dota[cč]|v[ýy]zv|stipend|sout[ěe]ž|program|podpor|fond", re.I)
# cesty mimo obsah (infrastruktura Marwelu) — nikdy nenásledovat
SKIP_PATH = re.compile(r"^/(search\.php|user\.php|rss\b|o-webu|modules/marwel/(admin|js|images)|uploads/download/)", re.I)
FILE_LANDING = re.compile(r"^/file/(\d+)/?$")
FILE_DIRECT = re.compile(r"/file/(\d+(?:_\d+)+)/?$")


def fetch(url, timeout):
    """→ (html, final_url) — final_url = po redirectech (www.msmt.cz → msmt.gov.cz aj.)."""
    last = None
    for _ in range(L("http.default_retries") or 1):
        try:
            req = urllib.request.Request(safe_url(url), headers={"User-Agent": UA})
            with http_util.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace"), r.geturl()
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def norm_url(url, base):
    """Absolutizace + normalizace: aliasy hostu → msmt.gov.cz, pryč fragment a lang/source
    query (jazykové mutace a rss-tracking = duplicitní obsah)."""
    u = urljoin(base, H.unescape(url).strip())
    p = urlsplit(u)
    host = p.netloc.lower()
    if host in HOST_ALIASES:
        host = HOST
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
         if k not in ("lang", "source")]
    return urlunsplit(("https", host, p.path.rstrip("/") or "/", urlencode(q), ""))


def article_seg(page_html):
    """Vyřízne obsahovou část (#article … konec .middle) — bez sidebar navigace."""
    i = page_html.find('id="article"')
    if i < 0:
        return None
    i = page_html.find(">", i) + 1          # až ZA otvírací tag (jinak atributy v textu)
    j = page_html.find("<!-- /.middle -->", i)
    if j < 0:
        j = page_html.find('<div class="right"', i)
    return page_html[i:j] if j > 0 else page_html[i:]


def html_to_text(seg):
    """Plný text segmentu — lossless (žádný min-length filtr, jen kolaps whitespace)."""
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", seg, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|li|h\d|tr|table|ul|ol)>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = H.unescape(s).replace("\xa0", " ")
    lines = (re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n"))
    return "\n".join(ln for ln in lines if ln)


def parse_links(seg, url):
    """→ (queue_urls, attachment_links) z obsahového segmentu."""
    queue, atts = [], []
    items = {norm_url(u, url) for u in re.findall(r"<h3>\s*<a[^>]+href=\"([^\"]+)\"", seg)}
    for m in re.finditer(r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", seg, re.S):
        raw, anchor = m.group(1), H.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).replace("\xa0", " ").strip()
        if raw.startswith(("mailto:", "javascript:", "#", "tel:")):
            continue
        u = norm_url(raw, url)
        p = urlsplit(u)
        if p.netloc != HOST or SKIP_PATH.search(p.path):
            continue
        if (FILE_LANDING.match(p.path) or FILE_DIRECT.search(p.path)
                or DOC_EXT_RE.search(u) or "/uploads/" in p.path):
            atts.append({"url": u, "name": anchor or os.path.basename(p.path)})
            continue
        is_pager = "index.php" in p.path and "rewrite=" in p.query
        if u in items or is_pager or GRANT.search(p.path + "?" + p.query) or GRANT.search(anchor):
            queue.append(u)
    # dedup příloh dle URL; drž nejdelší jméno (Marwel generuje prázdné dvojče kotvy)
    seen = {}
    for a in atts:
        k = a["url"]
        if k not in seen or len(a["name"]) > len(seen[k]["name"]):
            seen[k] = a
    return queue, list(seen.values())


def parse_page(url, page_html):
    seg = article_seg(page_html)
    if seg is None:
        return None, [], []
    m = re.search(r"<h2[^>]*>(.*?)</h2>", seg, re.S)
    title = H.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).replace("\xa0", " ").strip() if m else None
    kind = "listing" if re.search(r'class="\s*item"|title_perex_img_info', seg) else "article"
    queue, atts = parse_links(seg, url)
    rec = {"host": HOST, "title": title, "url": url, "date": None,
           "kind": kind, "body_text": html_to_text(seg)}
    return rec, queue, atts


def resolve_landing(url, timeout):
    """Landing /file/<id>/ → (direct_url, jméno souboru). Jméno z kotvy přímého linku
    (obsahuje příponu), fallback <title>."""
    try:
        h, _ = fetch(url, timeout)
    except Exception:  # noqa: BLE001
        return None, None
    fid = FILE_LANDING.match(urlsplit(url).path).group(1)
    m = re.search(rf'href="([^"]*/file/{fid}(?:_\d+)+/?)"[^>]*>([^<]+)<', h)
    if not m:
        m2 = re.search(rf'href="([^"]*/file/{fid}(?:_\d+)+/?)"', h)
        if not m2:
            return None, None
        name = (re.search(r"<title>([^,<]+)", h) or [None, ""])[1].strip()
        return norm_url(m2.group(1), url), name
    return norm_url(m.group(1), url), H.unescape(m.group(2)).replace("\xa0", " ").strip()


def materialize(att, files_dir, timeout, max_bytes):
    """Stáhni + převeď přílohu → doplněný dict (lossless manifest pole)."""
    landing = att["url"]
    if FILE_LANDING.match(urlsplit(landing).path):
        direct, fname = resolve_landing(landing, timeout)
        if not direct:
            return {**att, "direct_url": None, "ext": None, "bytes": None,
                    "txt_chars": None, "txt_path": None, "file_path": None,
                    "status": "landing-parse-fail"}
        if fname and len(fname) > len(att.get("name") or ""):
            att = {**att, "name": fname}
    else:
        direct, fname = landing, att.get("name") or ""
    ext = ext_of(direct)
    if ext == "bin" or ext not in DOC_EXTS:
        m = re.search(r"\.(\w{2,5})$", (fname or att.get("name") or ""))
        ext = m.group(1).lower() if m and m.group(1).lower() in DOC_EXTS else (sniff_ext(direct, timeout) or ext)
    if ext not in DOC_EXTS:
        return {**att, "direct_url": direct, "ext": ext, "bytes": None,
                "txt_chars": None, "txt_path": None, "file_path": None, "status": "not-a-doc"}
    ddir = os.path.join(files_dir, HOST)
    os.makedirs(ddir, exist_ok=True)
    sha = hashlib.sha256(direct.encode()).hexdigest()[:16]
    fpath, tpath = os.path.join(ddir, f"{sha}.{ext}"), os.path.join(ddir, f"{sha}.txt")
    if not os.path.exists(fpath):
        nbytes, derr = download(direct, fpath, timeout, max_bytes)
        if not nbytes:
            return {**att, "direct_url": direct, "ext": ext, "bytes": None,
                    "txt_chars": None, "txt_path": None, "file_path": None,
                    "status": derr or "download-fail"}
    chars, cerr = (None, None)
    if os.path.exists(tpath):
        chars = len(open(tpath, encoding="utf-8", errors="replace").read())
    else:
        chars, cerr = convert(fpath, ext, tpath, timeout)
    return {**att, "direct_url": direct, "ext": ext, "bytes": os.path.getsize(fpath),
            "txt_chars": chars, "txt_path": tpath if chars else None,
            "file_path": fpath, "status": "ok" if chars else (cerr or "convert-fail")}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", nargs="*", default=SEEDS)
    ap.add_argument("--extra-urls", help="soubor s URL (1/řádek) k přidání do fronty (např. sitemap-diff doplnění)")
    ap.add_argument("--out", default="data/msmt_documents.jsonl")
    ap.add_argument("--files-dir", default="data/msmt_files")
    ap.add_argument("--resume", action="store_true", help="navaž: přeskoč URL už v --out, appenduj")
    ap.add_argument("--no-follow", action="store_true",
                    help="gap-fill režim: stáhni JEN dané URL (extra-urls/seeds), nefolow linky z obsahu; přílohy se materializují normálně")
    ap.add_argument("--timeout", type=int, default=L("http.default_timeout_s"))
    ap.add_argument("--delay", type=float, default=1.0,
                    help="pauza mezi page-fetchi (robots deklaruje Crawl-Delay 30; jednorázový harvest jede mírněji)")
    ap.add_argument("--max-pages", type=int, default=L("safety.runaway_page_ceiling"),
                    help="runaway-pojistka (limits.json safety.runaway_page_ceiling), NE coverage cap")
    ap.add_argument("--workers", type=int, default=L("http.download_workers"))
    args = ap.parse_args()
    max_bytes = L("safety.doc_download_max_mb") * 1024 * 1024

    seen, seen_paths, recs, att_by_page = set(), set(), [], {}
    if args.resume and os.path.exists(args.out):
        for ln in open(args.out, encoding="utf-8"):
            try:
                u = json.loads(ln)["url"]
                seen.add(u)
                seen_paths.add(urlsplit(u).path.rstrip("/") or "/")
            except Exception:  # noqa: BLE001
                pass
        print(f"  [resume] {len(seen)} URL už v {args.out}", file=sys.stderr)

    queue = [norm_url(s, s) for s in args.seeds]
    if args.extra_urls:
        queue += [norm_url(u.strip(), u.strip()) for u in open(args.extra_urls, encoding="utf-8") if u.strip()]

    n_fetched, n_failed, n_redir_dupe = 0, 0, 0
    while queue:
        url = queue.pop(0)
        if url in seen or (urlsplit(url).path.rstrip("/") or "/") in seen_paths:
            continue
        if n_fetched >= args.max_pages:
            print(f"  ⚠ RUNAWAY-pojistka {args.max_pages} stránek dosažena (fronta {len(queue)}) — "
                  f"prošetři link-filtr/past, NEzvyšuj naslepo", file=sys.stderr)
            break
        seen.add(url)
        seen_paths.add(urlsplit(url).path.rstrip("/") or "/")
        try:
            h, fin = fetch(url, args.timeout)
        except Exception as e:  # noqa: BLE001
            n_failed += 1
            print(f"  [err] {type(e).__name__}: {url[:90]}", file=sys.stderr)
            continue
        n_fetched += 1
        # finální (post-redirect) URL: dedup podle path, záznam pod finální URL
        fin = norm_url(fin, url)
        if fin != url:
            fpath = urlsplit(fin).path.rstrip("/") or "/"
            if fin in seen or fpath in seen_paths:
                n_redir_dupe += 1
                continue
            seen.add(fin)
            seen_paths.add(fpath)
            url = fin
        rec, links, atts = parse_page(url, h)
        if rec is None:
            continue
        recs.append(rec)
        att_by_page[url] = atts
        if not args.no_follow:
            queue.extend(u for u in links if u not in seen)
        if n_fetched % 25 == 0:
            print(f"  [{n_fetched}] fronta={len(queue)} přílohy={sum(len(a) for a in att_by_page.values())} {url[:80]}",
                  file=sys.stderr)
        time.sleep(args.delay)

    # materializace příloh — dedup přes všechny stránky (stejný /file/<id>/ z více článků)
    uniq = {}
    for atts in att_by_page.values():
        for a in atts:
            uniq.setdefault(a["url"], a)
    print(f"  materializace {len(uniq)} unikátních příloh…", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        done = dict(zip(uniq.keys(), ex.map(
            lambda a: materialize(a, args.files_dir, args.timeout, max_bytes), uniq.values())))
    for rec in recs:
        rec["attachments"] = [done[a["url"]] for a in att_by_page.get(rec["url"], [])]
        rec["n_attachments"] = len(rec["attachments"])

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a" if args.resume else "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")

    ok = sum(1 for a in done.values() if a["status"] == "ok")
    print(json.dumps({"MARKER": "MSMT_HARVEST", "pages": len(recs),
                      "articles": sum(1 for r in recs if r["kind"] == "article"),
                      "listings": sum(1 for r in recs if r["kind"] == "listing"),
                      "fetched_ok": n_fetched, "failed": n_failed, "redirect_dupes": n_redir_dupe,
                      "attachments_unique": len(uniq), "attachments_ok": ok,
                      "out": args.out, "files_dir": args.files_dir}, ensure_ascii=False))


if __name__ == "__main__":
    main()
