#!/usr/bin/env python3
"""HZS ČR (hzscr.gov.cz, ASP.NET MV CMS) — harvest dotačního stromu, lossless.

Struktura webu (ověřeno živě 2026-06):
  - <base href="//hzscr.gov.cz/"> → relativní hrefy se resolvují od KOŘENE, ne od /clanek/
  - rubriky = /{slug}.aspx (root): <div id="articleList"> se seznamem článků
  - články  = /clanek/{slug}.aspx: <div id="content" class="documentDetail">
  - víceleté články mají ZÁLOŽKY ?q=base64("chnum=N") (roky 2026…2013) — harvestují se
    VŠECHNY a slévají do jednoho záznamu (body_text + union příloh; lossless)
  - přílohy = soubor/{slug}-pdf.aspx (typ v slugu, fallback sniff_ext z dsw2_fetch)
  - starý host www.hzscr.cz 301→ hzscr.gov.cz (kanonizuje se)

BFS pravidla (deterministická):
  - z RUBRIKY: všechny /clanek/*.aspx odkazy z content oblasti (článek v dotační rubrice
    = dotační článek, i bez klíčového slova ve slugu) + další rubriky jen grant-relevantní
  - z ČLÁNKU: další stránky jen grant-relevantní (GRANT regex jako harvest_site.py)
  - content oblast = id="content" … id="sidecol" (sidebar boilerplate se NEsleduje)
  - mv_cms.py nestačí: jeho SOUBOR_RE chce '/soubor/', ale kvůli <base> jsou hrefy 'soubor/…'
    (bez lomítka) a nezná záložky chnum → proto tenhle harvester (reuse dsw2_fetch beze změn)

Výstup (kontrakt ~vismo_documents.jsonl):
  data/hzs_documents.jsonl  {url, host, web, title, date, description, body_text, tabs[],
                             attachments[{url,label,ext,bytes,txt_chars,txt_path,text_excerpt}], n_attachments}
  data/hzs_files/<host>/<sha16>.<ext> + .txt

Spuštění (z kořene repa): python3 scripts/hzs_harvest.py
"""
import argparse, base64, hashlib, html, json, os, re, ssl, sys, time, urllib.request
from urllib.parse import urljoin, urlsplit, parse_qs, unquote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsw2_fetch as df
from limits import L

CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
# harvest_site.GRANT + tvary "výzev/vyzev" (archiv-vyzev.aspx) + "irop" (dotační program IROP pro IZS)
GRANT = re.compile(r"grant|dotac|výzv|vyzv|výzev|vyzev|žádost|zadost|podpor|pro-zadatele|irop", re.I)
SLUG_EXT = re.compile(r"-(pdf|docx?|xlsx?|rtf|odt|ods|pptx?|zip)(?:-\d+)?\.aspx$", re.I)
EXCERPT_CHARS = 1200   # jen convenience náhled v záznamu; PLNÝ text je v txt_path (lossless)

CANON_HOST = "hzscr.gov.cz"
ALIAS_HOSTS = {"hzscr.gov.cz", "www.hzscr.gov.cz", "hzscr.cz", "www.hzscr.cz"}

DEFAULT_SEEDS = [
    "https://hzscr.gov.cz/clanek/dotace-a-granty-dotace-dotace.aspx",   # hub Dotace
    "https://hzscr.gov.cz/nabidky-a-zakazky-dotace-a-granty.aspx",      # rubrika Dotace a granty
]


def canon(u):
    """Kanonizace: https, starý host → hzscr.gov.cz, bez fragmentu."""
    p = urlsplit(u)
    host = p.netloc.lower()
    if host in ALIAS_HOSTS:
        host = CANON_HOST
    return f"https://{host}{p.path}" + (f"?{p.query}" if p.query else "")


def fetch(url, timeout):
    retries = L("http.default_retries") or 3
    for i in range(retries):
        try:
            req = urllib.request.Request(df.safe_url(url), headers={"User-Agent": df.UA})
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace"), canon(r.geturl())
        except Exception:  # noqa: BLE001
            time.sleep(1.0 * (i + 1))
    return None, None


def to_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def base_href(h, page_url):
    m = re.search(r'<base[^>]+href="([^"]+)"', h, re.I)
    if m:
        b = m.group(1)
        if b.startswith("//"):
            b = "https:" + b
        return urljoin(page_url, b)
    return page_url


def content_area(h):
    """id="content" … id="sidecol" (sidebar má boilerplate odkazy — nesledovat)."""
    m = re.search(r'id="content"[^>]*>(.*?)(?:<div[^>]+id="sidecol"|id="(?:pata|footer|paticka)"|<footer)', h, re.S)
    return m.group(1) if m else h


def links_of(ca, base):
    """[(abs_url, label)] z content oblasti, share/mailto/print pryč."""
    out = []
    for href, txt in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', ca, re.S):
        href = html.unescape(href)
        if href.startswith(("mailto:", "javascript:", "#")):
            continue
        full = canon(urljoin(base, href))
        if urlsplit(full).netloc != CANON_HOST:
            continue
        out.append((full, to_text(txt)[:120]))
    return out


def q_decoded(u):
    """Dekóduj ASP.NET ?q= parametr (base64) → 'chnum=2' / 'prn=1' / None."""
    q = parse_qs(urlsplit(u).query).get("q", [None])[0]
    if not q:
        return None
    try:
        return base64.b64decode(unquote(q) + "==").decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None


def title_of(h, ca):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", ca, re.S)
    if m and to_text(m.group(1)):
        return to_text(m.group(1))
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    if not m:
        return None
    parts = [p.strip() for p in html.unescape(m.group(1)).split(" - ") if p.strip()]
    return parts[0] if parts else None


def article_meta_desc(h):
    descs = re.findall(r'<meta\s+name="description"\s+content="([^"]*)"', h, re.I)
    return html.unescape(descs[-1]) if len(descs) > 1 else None   # první je sitewide boilerplate


def harvest_article(url, timeout):
    """Článek vč. VŠECH chnum záložek → (record_bez_příloh, [(att_url,label)], discovered_links)."""
    pages = []          # [(tab_label, final_url, html)]
    seen_q = set()
    queue = [(None, url)]
    path = urlsplit(url).path
    discovered = []
    atts, att_seen = [], set()
    while queue:
        label, u = queue.pop(0)
        key = q_decoded(u) or "_main"
        if key in seen_q:
            continue
        seen_q.add(key)
        h, final = fetch(u, timeout)
        if not h:
            continue
        pages.append((label, final or u, h))
        b = base_href(h, final or u)
        ca = content_area(h)
        for full, lab in links_of(ca, b):
            sp = urlsplit(full)
            dq = q_decoded(full)
            if sp.path == path and dq and dq.startswith("chnum="):
                queue.append((lab, full))                       # další záložka (rok) téhož článku
            elif dq and dq.startswith("prn="):
                continue                                        # tisková verze
            elif "/soubor/" in sp.path:
                if full not in att_seen:
                    att_seen.add(full); atts.append((full, lab))
            else:
                discovered.append(full)
    if not pages:
        return None, [], []
    h0 = pages[0][2]
    ca0 = content_area(h0)
    bodies, tabs = [], []
    for label, fu, h in pages:
        t = to_text(content_area(h))
        if label:
            tabs.append({"label": label, "url": fu})
            bodies.append(f"=== záložka: {label} ===\n{t}")
        else:
            bodies.append(t)
    rec = {"url": canon(url), "host": CANON_HOST, "web": CANON_HOST,
           "title": title_of(h0, ca0), "date": None,
           "description": article_meta_desc(h0),
           "body_text": "\n\n".join(bodies), "tabs": tabs}
    return rec, atts, discovered


def store_attachment(att_url, label, files_dir, timeout):
    ext_m = SLUG_EXT.search(urlsplit(att_url).path)
    ext = ext_m.group(1).lower() if ext_m else (df.sniff_ext(att_url, L("probe.sniff_ext_bytes")) or "bin")
    sha = hashlib.sha1(att_url.encode()).hexdigest()[:16]
    d = os.path.join(files_dir, df.host_of(att_url)); os.makedirs(d, exist_ok=True)
    fp, tp = os.path.join(d, f"{sha}.{ext}"), os.path.join(d, f"{sha}.txt")
    att = {"url": att_url, "label": label or None, "ext": ext}
    max_bytes = L("safety.doc_download_max_mb") * 1024 * 1024
    if os.path.exists(fp) and os.path.exists(tp):               # idempotence při re-runu
        att.update({"bytes": os.path.getsize(fp), "txt_chars": os.path.getsize(tp), "txt_path": tp})
        att["text_excerpt"] = open(tp, encoding="utf-8", errors="replace").read()[:EXCERPT_CHARS]
        return att
    n, err = df.download(att_url, fp, timeout, max_bytes)
    if n and not err:
        chars, cerr = df.convert(fp, ext, tp, timeout)
        att.update({"bytes": n, "txt_chars": chars, "txt_path": tp if chars else None})
        if cerr:
            att["convert_err"] = cerr
        if chars:
            att["text_excerpt"] = open(tp, encoding="utf-8", errors="replace").read()[:EXCERPT_CHARS]
    else:
        att["download_err"] = err
    return att


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", nargs="+", default=DEFAULT_SEEDS)
    ap.add_argument("--out", default="data/hzs_documents.jsonl")
    ap.add_argument("--files-dir", default="data/hzs_files")
    ap.add_argument("--no-attachments", action="store_true")
    ap.add_argument("--timeout", type=int, default=L("http.default_timeout_s"))
    ap.add_argument("--delay", type=float, default=0.3)
    args = ap.parse_args()
    os.makedirs(args.files_dir, exist_ok=True)
    ceiling = L("safety.runaway_page_ceiling")

    seen, records = set(), []
    queue = [canon(s) for s in args.seeds]
    n_att_ok = n_att_err = 0
    while queue:
        if len(seen) >= ceiling:
            print(f"  ⚠ RUNAWAY-pojistka {ceiling} stránek dosažena (fronta {len(queue)}) — prošetři, NEzvyšuj naslepo", file=sys.stderr)
            break
        url = queue.pop(0).split("#")[0]
        if url in seen:
            continue
        is_article = urlsplit(url).path.startswith("/clanek/")
        dq0 = q_decoded(url)
        if dq0 and (is_article or not (dq0.startswith("strana=") or dq0.startswith("chnum="))):
            continue                                            # článkové záložky řeší harvest_article; print/jiné q ne
        seen.add(url)
        if is_article:
            rec, atts, discovered = harvest_article(url, args.timeout)
            if rec is None:
                print(f"  ERR fetch {url}", file=sys.stderr)
                continue
            if not args.no_attachments:
                stored = []
                for au, lab in atts:
                    a = store_attachment(au, lab, args.files_dir, args.timeout)
                    stored.append(a)
                    if a.get("txt_path"):
                        n_att_ok += 1
                    else:
                        n_att_err += 1
                rec["attachments"] = stored
            else:
                rec["attachments"] = [{"url": au, "label": lab} for au, lab in atts]
            rec["n_attachments"] = len(rec["attachments"])
            records.append(rec)
            print(f"  [{len(records)}] att={rec['n_attachments']} tabs={len(rec['tabs'])} :: {str(rec['title'])[:60]}", file=sys.stderr)
            for full in discovered:
                if GRANT.search(full) and full.split("#")[0] not in seen:
                    queue.append(full)
        else:                                                   # rubrika
            h, final = fetch(url, args.timeout)
            if not h:
                print(f"  ERR fetch {url}", file=sys.stderr)
                continue
            b = base_href(h, final or url)
            for full, _lab in links_of(content_area(h), b):
                sp = urlsplit(full)
                dq = q_decoded(full)
                if dq and dq.startswith("prn="):
                    continue
                if dq and (dq.startswith("strana=") or dq.startswith("chnum=")) and sp.path == urlsplit(url).path:
                    queue.append(full)                          # stránkování rubriky (q=strana/chnum)
                    continue
                base_u = full.split("#")[0]
                if sp.path.startswith("/clanek/"):
                    if base_u not in seen:
                        queue.append(base_u)                    # článek v dotační rubrice = vzít VŽDY
                elif GRANT.search(full) and base_u not in seen:
                    queue.append(base_u)                        # další rubrika jen grant-relevantní
        time.sleep(args.delay)

    with open(args.out, "w", encoding="utf-8") as o:
        for r in records:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_docs = sum(r["n_attachments"] for r in records)
    print(json.dumps({"MARKER": "HZS_HARVEST", "articles": len(records), "pages_visited": len(seen),
                      "attachments": n_docs, "attachments_text_ok": n_att_ok, "attachments_err": n_att_err,
                      "out": args.out, "files_dir": args.files_dir}, ensure_ascii=False))


if __name__ == "__main__":
    main()
