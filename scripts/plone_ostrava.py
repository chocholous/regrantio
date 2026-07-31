#!/usr/bin/env python3
"""Plone (Ostrava městské obvody) — tenký harvester vrstvy 1.

CMS rodina »plone« = ~20 webů ostravských městských obvodů na sdíleném Plone
(generator Plone, custom ++theme++ova-theme, interní odkazy přes /resolveuid/<uid>).
ŽÁDNÉ REST/RSS/XML-sitemap → HTML crawl. /cs/sitemap (HTML mapa portálu) existuje,
ale je MĚLKÁ (jen horní úrovně) — slouží k DISCOVERY, ne ke coverage.

Struktura (ověřeno probe poruba/radvanice/svinov 2026-06):
  dotační sekce (folder, per web JINÁ cesta — /cs/obcan/ucelove-dotace,
  /cs/radnice/ucelove-dotace-granty, /cs/radnice/dary-a-dotace, …)
    → listing (template-listing / template-news-listing; položky div.info2 h3 a)
    → roční dokument „Zásady … na rok YYYY" (portaltype-article, document_view)
    → přímé odkazy na soubory v těle (.pdf/.doc/.xls/.fo 602XML; občas KŘÍŽEM do
      jiného ročního folderu téhož hostu — proto se přílohy berou dle přípony,
      ne dle cesty).
Jde o ROČNÍ RÁMCE (standing programy) — deadline strukturálně NENÍ, status=unknown
(reálné termíny jsou v PDF → vrstva 2, tu tenhle skript NEspouští).

Discovery dotační sekce: homepage + /cs/sitemap, linky jejichž href-path nebo
anchor-text matchuje (?i)dota[cč]|grant (diakritika!); /resolveuid/ se rozbalí
follow-redirectem. Crawl = BFS uvnitř subtree sekce (prefix cesty) + stránkování
b_start. Přílohy → download + text reuse scripts/dsw2_fetch (sniff_ext/convert).

LOSSLESS: plný body_text (bez ořezu), všechny přílohy, mimo-subtree linky
v _links_out. Bounds JEN safety/technical z limits.json (⚠ log při dosažení).

Výstup (kontrakt jako vismo_documents.jsonl):
  data/plone_ostrava_documents.jsonl   {host, title, url, date, body_text, attachments[]}
  data/plone_ostrava_files/<host>/<sha>.{ext,txt}

Usage:
  python3 scripts/plone_ostrava.py                       # všechny obvody z platform_map.json
  python3 scripts/plone_ostrava.py --hosts poruba.ostrava.cz --discover-only
"""
import argparse
import hashlib
import html as H
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsw2_fetch as df          # reuse: safe_url, sniff_ext, download, convert, DOC_EXT_RE
from limits import L
import http_util  # noqa: E402  (jednotna TLS politika + fallback)

PLATFORM_MAP = "platform_map.json"
OUT_DOCS = "data/plone_ostrava_documents.jsonl"
FILES_DIR = "data/plone_ostrava_files"
UA = df.UA

# Ne-ostravské plone hosty (univerzity apod.) — mimo cíl rodiny "Ostrava obvody".
NON_OSTRAVA_SKIP = {"gaju.jcu.cz"}
# ostrava.cz = hlavní portál města; jeho dotace žijí na dotace.ostrava.cz (WP,
# pokrývá scripts/ostrava_harvest.py) → tady neharvestujeme, jen obvody.
CITY_PORTAL_SKIP = {"ostrava.cz"}

# Diakritika-tolerantní podpis dotační sekce (dotace/dotační/grant; href i text).
GRANT_PAT = re.compile(r"(?i)dota[cč]|grant")
RESOLVEUID_RE = re.compile(r"/resolveuid/[0-9a-f]{32}", re.I)
# Přípony nad rámec dsw2_fetch.DOC_EXT_RE: .fo/.zfo = 602XML formuláře (EvAgend),
# .zip = balíky formulářů. Stahují se lossless, konverzi na text nemají.
EXTRA_DOC_RE = re.compile(r"\.(fo|zfo|zip)(?:$|\?)", re.I)
IMG_RE = re.compile(r"\.(jpe?g|png|gif|svg|webp|ico|css|js)(?:$|\?)", re.I)
A_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
BODY_CLS_RE = re.compile(r'<body[^>]*class="([^"]*)"')
TITLE_RE = re.compile(r'<h1 class="content-main__title">\s*(.*?)\s*</h1>', re.S)
DATE_RE = re.compile(r'<div class="news__date">\s*(.*?)\s*</div>', re.S)
PEREX_RE = re.compile(r'<div class="content-main__perex">\s*(.*?)\s*</div>', re.S)
B_START_RE = re.compile(r"b_start(?::int)?=(\d+)")
CONTENT_START = 'content-main__content'
CONTENT_ENDS = ('id="social-links-wrapper"', "<!-- end CONTENT -->", "<footer")


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def fetch(url, timeout, retries):
    """GET s retry; → (final_url, content_type, body:str|None). Follow redirects
    (resolveuid → kanonická cesta; *.cz → *.ostrava.cz)."""
    last_err = None
    for i in range(retries):
        try:
            req = urllib.request.Request(df.safe_url(url), headers={"User-Agent": UA})
            with http_util.urlopen(req, timeout=timeout) as r:
                ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                if ctype and "html" not in ctype:
                    return r.geturl(), ctype, None          # dokument, ne stránka
                charset = r.headers.get_content_charset() or "utf-8"
                return r.geturl(), ctype, r.read().decode(charset, "replace")
        except urllib.error.HTTPError as e:
            if e.code < 500 or i == retries - 1:            # 4xx definitivní; 5xx → retry
                return url, None, None
            last_err = e
            time.sleep(1 + i)
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(1 + i)
    log(f"  ⚠ fetch fail {url}: {type(last_err).__name__}: {str(last_err)[:60]}")
    return url, None, None


def head_resolve(url, timeout, retries):
    """Rozbal /resolveuid/ (nebo jiný redirect) bez čtení těla → (final_url, content_type)."""
    for i in range(retries):
        try:
            req = urllib.request.Request(df.safe_url(url), headers={"User-Agent": UA})
            with http_util.urlopen(req, timeout=timeout) as r:
                return r.geturl(), (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        except urllib.error.HTTPError:
            return None, None
        except Exception:  # noqa: BLE001
            time.sleep(1 + i)
    return None, None


def to_text(h):
    """HTML → plain text; bloky oddělené \n. ŽÁDNÝ ořez délky."""
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>", "\n", h)
    t = H.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def norm_url(u, base):
    """Absolutizace + unescape entit + drop fragmentu."""
    u = H.unescape(u.strip())
    if not u or u.startswith(("#", "mailto:", "javascript:", "tel:")):
        return None
    full = urljoin(base, u)
    p = urlsplit(full)
    if p.scheme not in ("http", "https"):
        return None
    return p._replace(fragment="").geturl()


def content_slice(html_page):
    """Vyřízne hlavní obsahový sloupec (content-main__content … social-links/end CONTENT/footer)."""
    i = html_page.find(CONTENT_START)
    if i < 0:
        return ""
    i = html_page.find(">", i) + 1                          # až ZA otevírací tag divu
    ends = [html_page.find(m, i) for m in CONTENT_ENDS]
    ends = [e for e in ends if e > 0]
    return html_page[i:min(ends)] if ends else html_page[i:]


def is_doc_url(u):
    return bool(df.DOC_EXT_RE.search(u) or EXTRA_DOC_RE.search(u))


def in_subtree(url, roots):
    p = urlsplit(url)
    key = p.netloc.lower() + p.path
    for r in roots:
        rp = urlsplit(r)
        rkey = rp.netloc.lower() + rp.path.rstrip("/")
        if key == rkey or key.startswith(rkey + "/"):
            return True
    return False


# ---------------------------------------------------------------- discovery
def discover_sections(host, timeout, retries):
    """→ (canonical_base, [section_url, …]) — kandidáti dotačních sekcí z homepage
    + /cs/sitemap (HTML mapa portálu; mělká, ale na discovery stačí)."""
    final, _, body = fetch(f"https://{host}/", timeout, retries)
    if body is None:
        return None, []
    base = f"{urlsplit(final).scheme}://{urlsplit(final).netloc}"
    chost = urlsplit(final).netloc.lower()

    pages = [body]
    _, _, smap = fetch(f"{base}/cs/sitemap", timeout, retries)
    if smap:
        pages.append(smap)

    cands = {}
    for page in pages:
        for href, txt in A_RE.findall(page):
            text = re.sub(r"<[^>]+>", "", txt)
            text = re.sub(r"\s+", " ", H.unescape(text)).strip()
            u = norm_url(href, base + "/")
            if not u:
                continue
            if not (GRANT_PAT.search(urlsplit(u).path) or GRANT_PAT.search(text)):
                continue
            if urlsplit(u).netloc.lower() != chost:
                # externí (dotace.ostrava.cz=WP už pokryto, app.* …) → mimo
                continue
            cands[u] = text
    # rozbal resolveuid kandidáty na kanonické cesty
    resolved = {}
    for u, text in cands.items():
        if RESOLVEUID_RE.search(u):
            fu, ctype = head_resolve(u, timeout, retries)
            if not fu or (ctype and "html" not in ctype):
                continue
            u = fu
        if urlsplit(u).netloc.lower() == chost:
            resolved.setdefault(u.rstrip("/"), text)
    # zahoď kořeny vnořené pod jiným kořenem (duplikoval by se subtree)
    roots = sorted(resolved)
    keep = [r for r in roots
            if not any(r != o and (urlsplit(r).path + "/").startswith(urlsplit(o).path.rstrip("/") + "/")
                       and urlsplit(r).netloc == urlsplit(o).netloc for o in roots)]
    return base, [(r, resolved[r]) for r in keep]


# ---------------------------------------------------------------- attachments
# MIME typy mimo dsw2_fetch.MIME_EXT, které Plone Ostrava servíruje (602XML formuláře)
EXTRA_MIME_EXT = {"text/x-xslfo": "fo", "application/zip": "zip",
                  "application/x-zip-compressed": "zip"}


def harvest_attachment(url, name, files_dir, cache, timeout, max_bytes, ext_hint=None):
    """Stáhni + převeď na text (reuse dsw2_fetch). Cache per URL (soubory se
    křížově odkazují mezi ročními stránkami). → dict do attachments[]."""
    if url in cache:
        return cache[url]
    ext = ext_hint or df.ext_of(url)
    if ext == "bin" or (not ext_hint and not df.DOC_EXT_RE.search(url) and not EXTRA_DOC_RE.search(url)):
        sniffed = df.sniff_ext(url, timeout)
        if sniffed:
            ext = sniffed
    host = df.host_of(url)
    sha = hashlib.sha1(url.encode()).hexdigest()[:16]
    d = os.path.join(files_dir, host)
    os.makedirs(d, exist_ok=True)
    fpath = os.path.join(d, f"{sha}.{ext}")
    tpath = os.path.join(d, f"{sha}.txt")
    att = {"url": url, "name": name or None, "ext": ext}
    if os.path.exists(fpath):                               # idempotence při re-runu
        att["bytes"] = os.path.getsize(fpath)
        if os.path.exists(tpath):
            txt = open(tpath, encoding="utf-8", errors="replace").read()
            att.update({"txt_chars": len(txt), "txt_path": tpath, "convert_err": None})
        else:
            chars, cerr = df.convert(fpath, ext, tpath, timeout)
            att.update({"txt_chars": chars, "txt_path": tpath if chars else None, "convert_err": cerr})
    else:
        n, derr = df.download(url, fpath, timeout, max_bytes)
        if derr == "too-big":
            log(f"  ⚠ SAFETY doc_download_max_mb dosažen: {url}")
        if n and not derr:
            att["bytes"] = n
            chars, cerr = df.convert(fpath, ext, tpath, timeout)
            att.update({"txt_chars": chars, "txt_path": tpath if chars else None, "convert_err": cerr})
        else:
            att["download_err"] = derr
    cache[url] = att
    return att


# ---------------------------------------------------------------- crawl
def crawl_host(host, files_dir, timeout, retries, ceiling, max_bytes, delay,
               discover_only=False):
    base, sections = discover_sections(host, timeout, retries)
    rec0 = {"host_requested": host, "canonical_base": base,
            "sections": [{"url": u, "label": t} for u, t in sections]}
    if base is None:
        log(f"== {host}: FETCH FAIL (homepage)")
        return rec0, []
    chost = urlsplit(base).netloc.lower()
    log(f"== {host} → {chost}: {len(sections)} sekcí " + str([u for u, _ in sections]))
    if discover_only or not sections:
        return rec0, []

    roots = [u for u, _ in sections]
    visited, records = set(), []
    att_cache = {}
    queue = [(u, u, None) for u in roots]                    # (url, section_root, parent_rec_idx)
    while queue:
        url, root, parent = queue.pop(0)
        key = urlsplit(url).netloc.lower() + urlsplit(url).path + (
            "?" + urlsplit(url).query if urlsplit(url).query else "")
        if key in visited:
            continue
        visited.add(key)
        if len(visited) > ceiling:
            log(f"  ⚠ SAFETY runaway_page_ceiling {ceiling} na {host} — prošetři (bug, ne coverage cap)")
            break
        time.sleep(delay)
        final, ctype, page = fetch(url, timeout, retries)
        if page is None:
            if ctype:                # URL bez přípony je ve skutečnosti dokument (např. 602XML .fo)
                hint = EXTRA_MIME_EXT.get(ctype) or df.MIME_EXT.get(ctype)
                if hint is None and not ctype.startswith(("application/", "text/")):
                    log(f"  (asset, skip) {final} [{ctype}]")   # obrázky za /image_large view
                    continue
                att = harvest_attachment(final, None, files_dir, att_cache, timeout, max_bytes,
                                         ext_hint=hint)
                if parent is not None:                       # lossless: přivěs k rodičovské stránce
                    records[parent]["attachments"].append(att)
                    records[parent]["n_attachments"] += 1
                log(f"  (doc za page-URL → příloha) {final} [{ctype}]")
            else:
                log(f"  ⚠ page fail {url}")
            continue
        m = BODY_CLS_RE.search(page)
        body_cls = m.group(1) if m else ""
        template = next((c for c in body_cls.split() if c.startswith("template-")), None)
        ptype = next((c for c in body_cls.split() if c.startswith("portaltype-")), None)
        seg = content_slice(page)
        mt = TITLE_RE.search(page)
        title = re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", mt.group(1)))).strip() if mt else None
        md = DATE_RE.search(page)
        date = to_text(md.group(1)) or None if md else None
        mp = PEREX_RE.search(page)
        perex = to_text(mp.group(1)) or None if mp else None

        attachments, links_out, n_children = [], [], 0
        for href, txt in A_RE.findall(seg):
            text = re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", txt))).strip()
            u = norm_url(href, final)
            if not u:
                continue
            if urlsplit(u).netloc.lower() != chost:
                links_out.append({"url": u, "text": text[:200]})
                continue
            if RESOLVEUID_RE.search(u):
                fu, rctype = head_resolve(u, timeout, retries)
                if not fu:
                    links_out.append({"url": u, "text": text[:200], "err": "resolveuid_fail"})
                    continue
                if rctype and "html" not in rctype:          # resolveuid → soubor
                    attachments.append(harvest_attachment(fu, text, files_dir, att_cache,
                                                          timeout, max_bytes))
                    continue
                u = fu
            if IMG_RE.search(urlsplit(u).path):
                continue                                    # asset, ne dokument/stránka
            if is_doc_url(u):
                attachments.append(harvest_attachment(u, text, files_dir, att_cache,
                                                      timeout, max_bytes))
            elif in_subtree(u, roots):
                queue.append((u, root, len(records)))       # len(records) = index TÉTO stránky
                n_children += 1
            elif B_START_RE.search(urlsplit(u).query) and urlsplit(u).path == urlsplit(final).path:
                queue.append((u, root, len(records)))       # stránkování listingu
            else:
                links_out.append({"url": u, "text": text[:200]})

        body_text = to_text(seg)
        records.append({
            # kontrakt vismo_documents.jsonl:
            "host": chost, "title": title, "url": final, "date": date,
            "body_text": body_text, "attachments": attachments,
            # roční rámce: termíny strukturálně nejsou → status unknown, deadline nic
            "status": "unknown", "status_source": "plone_annual_framework", "deadline": None,
            # lossless extras:
            "perex": perex, "template": template, "portal_type": ptype,
            "section_root": root, "host_requested": host,
            "n_attachments": len(attachments), "_links_out": links_out,
        })
        log(f"  [{len(visited):>3}] {template or '?':<28} att={len(attachments):<2} "
            f"child={n_children:<2} {final}")
    return rec0, records


def default_hosts():
    m = json.load(open(PLATFORM_MAP, encoding="utf-8"))["final"]
    return sorted(h for h, v in m.items()
                  if v.get("plat") == "plone"
                  and h not in NON_OSTRAVA_SKIP and h not in CITY_PORTAL_SKIP)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hosts", help="čárkou oddělené hosty (default: plone obvody z platform_map.json)")
    ap.add_argument("--out", default=OUT_DOCS)
    ap.add_argument("--files-dir", default=FILES_DIR)
    ap.add_argument("--discover-only", action="store_true", help="jen najdi dotační sekce, necrawluj")
    ap.add_argument("--workers", type=int, default=L("http.download_workers"),
                    help="paralelismus PŘES hosty (uvnitř hostu serial + polite delay)")
    args = ap.parse_args()

    hosts = args.hosts.split(",") if args.hosts else default_hosts()
    timeout = L("http.default_timeout_s")
    retries = L("http.default_retries")
    ceiling = L("safety.runaway_page_ceiling")
    max_bytes = L("safety.doc_download_max_mb") * 1024 * 1024
    delay = L("http.polite_delay_s")

    os.makedirs(args.files_dir, exist_ok=True)
    with ThreadPoolExecutor(max_workers=min(args.workers, len(hosts))) as ex:
        results = list(ex.map(lambda h: crawl_host(
            h, args.files_dir, timeout, retries, ceiling, max_bytes, delay,
            discover_only=args.discover_only), hosts))

    all_records = []
    summary = []
    for (disc, recs) in results:
        n_att = sum(r["n_attachments"] for r in recs)
        n_txt = sum(1 for r in recs for a in r["attachments"] if a.get("txt_path"))
        summary.append({"host": disc["host_requested"], "canonical": disc["canonical_base"],
                        "sections": disc["sections"], "pages": len(recs),
                        "attachments": n_att, "att_with_text": n_txt})
        all_records.extend(recs)

    if not args.discover_only:
        with open(args.out, "w", encoding="utf-8") as f:
            for r in all_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(json.dumps({"MARKER": "PLONE_OSTRAVA", "hosts": len(hosts),
                      "pages": len(all_records),
                      "attachments": sum(s["attachments"] for s in summary),
                      "att_with_text": sum(s["att_with_text"] for s in summary),
                      "out": args.out, "per_host": summary}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
