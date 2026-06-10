#!/usr/bin/env python3
"""CzechAid / Česká rozvojová agentura (czechaid.gov.cz, NETservis CMS) — layer-1 lossless harvest.

STRUKTURA PŘED PRÓZOU — co web dává strukturovaně (recon docs/recon_ministerstva.md §3 + sonda 2026-06-10):
  - ŽÁDNÉ veřejné JSON API. Sitemap (https://czechaid.gov.cz/sitemap.xml, 1709 loc) detailní
    stránky výzev /dotace/<slug> NEOBSAHUJE (0 záznamů) — completeness check jen přes listing.
  - Listing https://czechaid.gov.cz/dotace = JEDINÁ stránka (žádná paginace ani archiv —
    ověřeno: žádný pager element, „Zobrazit další" v HTML je jen nav/search boilerplate).
    Obsahuje: aktuality k výzvám, odkazy na detaily /dotace/<slug>, per-výzva soubory
    (FAQ/webinář/prezentace), výsledky řízení (award PDF → entity project, ne výzva)
    a formuláře pro příjemce. Vše se bere lossless jako záznam listingu + detaily.
  - Detail /dotace/<slug>: obsah v <main>, titul <div class="likeh1">, próza v .editorBox.
    ŽÁDNÉ strukturované pole od/do (žádné <time>, žádná meta data) — lhůta je jen v próze
    („Lhůta pro podání žádosti … do 17. 3. 2025 včetně") → NEparsuje se magicky, ukládá se
    plný text (deadline=None, vytěží vrstva 2). Jediná struktura = SLUG nese stav
    (zruseno-…, uzavrena-…, uprava-zneni-uzavrena-…) → status_guess počítá KÓD ze slugu.
  - Přílohy: /cs/file/<md5>/<id>/<název> i /file/<md5>/<id>/<název>, část odkazů absolutně
    přes alias hosty (www.czechaid.cz → gov.cz). Názvy percent-encoded s diakritikou a \xa0.
    Výzva samotná bývá v ZIP („Vyzva a prilohy.zip") → ZIP se ROZBALUJE a členové se
    konvertují na text (jinak by jádro výzvy bylo ztracené); media (mp4 webináře) se
    nestahují — manifest drží url+label (precedens msmt_harvest „not-a-doc").

Harvest = BFS z /dotace po odkazech v <main> s cestou /dotace[/…] (detaily se křížově
odkazují — zruseno-stránky → původní výzvy). Data se berou CELÁ (žádný cap; runaway hlídá
limits safety.runaway_page_ceiling, loguje ⚠). Doc→text přes scripts/dsw2_fetch.py.

Výstup (kontrakt jako vismo_documents.jsonl):
  data/czechaid_documents.jsonl  {web, host, title, url, requested_url, alias_urls?, slug,
                                  date, kind,
                                  status_guess, status, status_source, status_confidence,
                                  deadline, body_text,
                                  attachments[{url,label,name,ext,bytes,txt_chars,txt_path,
                                               file_path,text_excerpt,status,zip_members?}],
                                  n_attachments}
  data/czechaid_files/<host>/<sha16>.<ext> (+ .txt; ZIP navíc <sha16>_zip/<member>)

Spuštění (z kořene repa): python3 scripts/czechaid_harvest.py
"""
import argparse
import hashlib
import html as H
import json
import os
import re
import sys
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dsw2_fetch as df  # noqa: E402  (safe_url, sniff_ext, download, convert, DOC_EXTS, UA)
from limits import L  # noqa: E402

HOST = "czechaid.gov.cz"
HOST_ALIASES = {"czechaid.gov.cz", "www.czechaid.gov.cz", "czechaid.cz", "www.czechaid.cz"}
SEEDS = ["https://czechaid.gov.cz/dotace"]
FILE_PATH_RE = re.compile(r"^/(?:[a-z]{2}/)?file/[0-9a-f]{32}/\d+/", re.I)
EXCERPT_CHARS = 1200   # jen convenience náhled v záznamu; PLNÝ text je v txt_path (lossless)


def canon(u, base=None):
    """Absolutizace + kanonizace: https, alias hosty → czechaid.gov.cz, bez fragmentu."""
    if base:
        u = urljoin(base, H.unescape(u).strip())
    p = urlsplit(u)
    host = p.netloc.lower()
    if host in HOST_ALIASES:
        host = HOST
    return f"https://{host}{p.path}" + (f"?{p.query}" if p.query else "")


def fetch(url, timeout):
    """→ (html, final_canon_url). Přejmenované výzvy dělají 301 starý slug → nový
    (zruseno-…/uprava-zneni-…) — final URL je kanonická identita záznamu (dedup)."""
    last = None
    for i in range(L("http.default_retries") or 1):
        try:
            req = urllib.request.Request(df.safe_url(url), headers={"User-Agent": df.UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return (r.read().decode(r.headers.get_content_charset() or "utf-8", "replace"),
                        canon(r.geturl()).split("#")[0])
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.0 * (i + 1))
    print(f"  ERR fetch {url}: {type(last).__name__}: {str(last)[:60]}", file=sys.stderr)
    return None, None


def to_text(h):
    """HTML → plain text, lossless co do obsahu (\xa0 → mezera, entity rozbalené)."""
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>", "\n", h)
    t = H.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def main_area(h):
    """Obsah stránky = <main>…</main> (header/nav/footer boilerplate pryč)."""
    m = re.search(r"<main[^>]*>(.*?)</main>", h, re.S | re.I)
    return m.group(1) if m else h


def title_of(h, ma):
    m = re.search(r'<div class="likeh1">(.*?)</div>', ma, re.S)
    if m and to_text(m.group(1)):
        return to_text(m.group(1))
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    if not m:
        return None
    t = H.unescape(m.group(1)).replace("\xa0", " ").strip()
    return re.split(r"\s+-\s+CZECH AID", t)[0].strip() or None


def links_of(ma, base):
    """[(abs_canon_url, label)] z obsahu; mailto/js/anchor pryč, jen naše hosty."""
    out = []
    for href, txt in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', ma, re.S):
        href = H.unescape(href).strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        full = canon(href, base)
        if urlsplit(full).netloc != HOST:
            continue
        out.append((full.split("#")[0], to_text(txt)[:160] or None))
    return out


def slug_status(slug):
    """Status POČÍTÁ KÓD z jediné dostupné struktury — prefixu slugu (jako vismo title_guess).
    zruseno-… → cancelled, …uzavrena-… → closed; jinak neznámý (lhůta je jen v próze)."""
    if re.match(r"zrusen", slug, re.I):
        return "cancelled"
    if re.search(r"(^|-)uzavren", slug, re.I):
        return "closed"
    return None


# ---------------------------------------------------------------- attachments
def _zipname(info):
    """Jméno člena s opravou kódování: bez UTF-8 flagu dekóduje zipfile jako cp437
    (→ „P²ílohy ºádosti"). České Windows ZIPy mají OEM cp852; zkus utf-8, pak cp852."""
    if info.flag_bits & 0x800:
        return info.filename
    raw = info.filename.encode("cp437", "replace")
    for enc in ("utf-8", "cp852"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return info.filename


def _zip_members_text(fpath, xdir, timeout, max_bytes, depth=0):
    """Rozbal ZIP (rekurzivně i ZIP-v-ZIPu), členy s doc příponou konvertuj na text
    → (combined_text, members[]). Výzva samotná i její přílohy bývají v (zanořeném) ZIPu —
    bez rozbalení by jádro harvestu bylo ztracené. Hloubku hlídá safety limit (zip-bomba)."""
    if depth >= L("safety.zip_nesting_depth_ceiling"):
        print(f"  ⚠ ZIP nesting ceiling {depth} u {fpath} — prošetři (zip-bomba?)", file=sys.stderr)
        return None, [{"name": None, "status": "zip-depth-ceiling"}]
    members, parts = [], []
    os.makedirs(xdir, exist_ok=True)
    try:
        zf = zipfile.ZipFile(fpath)
    except Exception as e:  # noqa: BLE001
        return None, [{"name": None, "status": f"zip-open: {type(e).__name__}"}]
    total = sum(i.file_size for i in zf.infolist())
    if total > max_bytes:   # zip-bomb pojistka = stejný strop jako download (safety)
        zf.close()
        print(f"  ⚠ ZIP rozbalený přes safety strop ({total} B) u {fpath}", file=sys.stderr)
        return None, [{"name": None, "status": f"zip-too-big-{total}"}]
    for info in zf.infolist():
        if info.is_dir():
            continue
        name = _zipname(info)
        ext = os.path.splitext(name)[1].lstrip(".").lower()
        safe = re.sub(r"[^\w.\-]+", "_", name)[-120:]
        mpath = os.path.join(xdir, safe)
        with zf.open(info) as src, open(mpath, "wb") as dst:
            dst.write(src.read())
        mrec = {"name": name, "ext": ext, "bytes": info.file_size, "file_path": mpath}
        if ext == "zip":                                       # zanořený ZIP (Prilohy vyzvy.zip)
            ntext, nmembers = _zip_members_text(mpath, mpath[:-4] + "_zip",
                                                timeout, max_bytes, depth + 1)
            mrec.update({"members": nmembers,
                         "status": "ok" if ntext else "zip-no-text"})
            if ntext:
                mrec["txt_chars"] = len(ntext)
                parts.append(f"=== {name} ===\n{ntext}")
        elif ext in df.DOC_EXTS:
            chars, cerr = df.convert(mpath, ext, mpath + ".txt", timeout)
            mrec.update({"txt_chars": chars, "status": "ok" if chars else (cerr or "convert-fail")})
            if chars:
                parts.append(f"=== {name} ===\n" + open(mpath + ".txt", encoding="utf-8", errors="replace").read())
        else:
            mrec["status"] = "not-a-doc"
        members.append(mrec)
    zf.close()
    return ("\n\n".join(parts) if parts else None), members


def materialize(att, files_dir, timeout, max_bytes):
    """Stáhni + převeď přílohu → doplněný manifest dict (lossless: url+label vždy)."""
    url = att["url"]
    name = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
    ext = os.path.splitext(name)[1].lstrip(".").lower() or None
    if not ext:
        ext = df.sniff_ext(url, L("probe.sniff_ext_bytes"))
    att = {**att, "name": name, "ext": ext}
    if not ext or (ext not in df.DOC_EXTS and ext != "zip"):
        return {**att, "bytes": None, "txt_chars": None, "txt_path": None,
                "file_path": None, "status": "not-a-doc"}     # mp4/ppt-video apod.: url+label v manifestu
    ddir = os.path.join(files_dir, HOST)
    os.makedirs(ddir, exist_ok=True)
    sha = hashlib.sha1(url.encode()).hexdigest()[:16]
    fpath, tpath = os.path.join(ddir, f"{sha}.{ext}"), os.path.join(ddir, f"{sha}.txt")
    if not os.path.exists(fpath):                              # idempotence při re-runu
        nbytes, derr = df.download(url, fpath, timeout, max_bytes)
        if not nbytes:
            return {**att, "bytes": None, "txt_chars": None, "txt_path": None,
                    "file_path": None, "status": derr or "download-fail"}
    out = {**att, "bytes": os.path.getsize(fpath), "file_path": fpath}
    if os.path.exists(tpath):
        chars, cerr = len(open(tpath, encoding="utf-8", errors="replace").read()), None
        if ext == "zip":
            out["zip_members"] = json.load(open(tpath + ".members.json", encoding="utf-8")) \
                if os.path.exists(tpath + ".members.json") else None
    elif ext == "zip":
        text, members = _zip_members_text(fpath, os.path.join(ddir, f"{sha}_zip"), timeout, max_bytes)
        out["zip_members"] = members
        json.dump(members, open(tpath + ".members.json", "w", encoding="utf-8"), ensure_ascii=False)
        chars, cerr = (len(text), None) if text else (None, "zip-no-text")
        if text:
            open(tpath, "w", encoding="utf-8").write(text)
    else:
        chars, cerr = df.convert(fpath, ext, tpath, timeout)
    out.update({"txt_chars": chars, "txt_path": tpath if chars else None,
                "status": "ok" if chars else (cerr or "convert-fail")})
    if chars:
        out["text_excerpt"] = open(tpath, encoding="utf-8", errors="replace").read()[:EXCERPT_CHARS]
    return out


# ---------------------------------------------------------------- BFS
def harvest_page(url, timeout):
    """→ (record_bez_příloh, [(att_url, label)], [další /dotace stránky]).
    rec['url'] = FINAL URL po redirectu (kanonická identita), požadovaná v rec['requested_url']."""
    h, final = fetch(url, timeout)
    if h is None:
        return None, [], []
    path = urlsplit(final).path
    if not (path == "/dotace" or path.startswith("/dotace/")):
        return None, [], []                                    # redirect mimo sekci (ne výzva)
    ma = main_area(h)
    slug = path[len("/dotace/"):] if path.startswith("/dotace/") else None
    atts, att_seen, more = [], set(), []
    for full, label in links_of(ma, final):
        p = urlsplit(full).path
        if FILE_PATH_RE.match(p):
            if full not in att_seen:
                att_seen.add(full)
                atts.append((full, label))
        elif p == "/dotace" or p.startswith("/dotace/"):
            more.append(full)                                  # detail/paginace — křížové odkazy
    sg = slug_status(slug) if slug else None
    rec = {"web": HOST, "host": HOST, "title": title_of(h, ma), "url": final,
           "requested_url": url if url != final else None,
           "slug": slug, "date": None,
           "kind": "vyzva" if slug else "listing",
           "status_guess": sg, "status": sg or "unknown",
           "status_source": "slug_guess" if sg else None,
           "status_confidence": "low" if sg else None,
           "deadline": None,                                   # jen v próze → vrstva 2, NE magie tady
           "body_text": to_text(ma)}
    return rec, atts, more


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", nargs="+", default=SEEDS)
    ap.add_argument("--out", default="data/czechaid_documents.jsonl")
    ap.add_argument("--files-dir", default="data/czechaid_files")
    ap.add_argument("--no-attachments", action="store_true")
    ap.add_argument("--timeout", type=int, default=L("http.default_timeout_s"))
    ap.add_argument("--delay", type=float, default=L("http.polite_delay_s"))
    ap.add_argument("--workers", type=int, default=L("http.download_workers"))
    args = ap.parse_args()
    os.makedirs(args.files_dir, exist_ok=True)
    ceiling = L("safety.runaway_page_ceiling")
    max_bytes = L("safety.doc_download_max_mb") * 1024 * 1024

    seen, records, att_by_page, by_final = set(), [], {}, {}
    queue = [canon(s) for s in args.seeds]
    while queue:
        if len(seen) >= ceiling:
            print(f"  ⚠ RUNAWAY-pojistka {ceiling} stránek dosažena (fronta {len(queue)}) — "
                  f"prošetři, NEzvyšuj naslepo", file=sys.stderr)
            break
        url = queue.pop(0).split("#")[0]
        if url in seen:
            continue
        seen.add(url)
        rec, atts, more = harvest_page(url, args.timeout)
        if rec is None:
            continue
        if rec["url"] in by_final:                             # starý slug 301 → už harvestnutý článek
            by_final[rec["url"]].setdefault("alias_urls", []).append(url)
            continue
        seen.add(rec["url"])
        by_final[rec["url"]] = rec
        records.append(rec)
        att_by_page[rec["url"]] = atts
        print(f"  [{len(records)}] {rec['kind']:7} att={len(atts)} status={rec['status']:9} "
              f":: {str(rec['title'])[:70]}", file=sys.stderr)
        for m in more:
            if m not in seen:
                queue.append(m)
        time.sleep(args.delay)

    # materializace příloh — unikátní URL jednou (listing i detaily sdílejí soubory)
    uniq = {}
    for atts in att_by_page.values():
        for u, lab in atts:
            if u not in uniq or (lab and not uniq[u]["label"]):
                uniq[u] = {"url": u, "label": lab}
    n_att_ok = n_att_err = n_att_media = 0
    done = {}
    if not args.no_attachments and uniq:
        print(f"  materializace {len(uniq)} unikátních příloh…", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            done = dict(zip(uniq.keys(), ex.map(
                lambda a: materialize(a, args.files_dir, args.timeout, max_bytes), uniq.values())))
        for a in done.values():
            if a["status"] == "ok":
                n_att_ok += 1
            elif a["status"] == "not-a-doc":
                n_att_media += 1
            else:
                n_att_err += 1
    for rec in records:
        rec["attachments"] = [done.get(u, {"url": u, "label": lab})
                              for u, lab in att_by_page.get(rec["url"], [])]
        rec["n_attachments"] = len(rec["attachments"])

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in records:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"MARKER": "CZECHAID_HARVEST", "pages": len(records),
                      "vyzvy": sum(1 for r in records if r["kind"] == "vyzva"),
                      "attachments_unique": len(uniq), "attachments_text_ok": n_att_ok,
                      "attachments_media_skipped": n_att_media, "attachments_err": n_att_err,
                      "out": args.out, "files_dir": args.files_dir}, ensure_ascii=False))


if __name__ == "__main__":
    main()
