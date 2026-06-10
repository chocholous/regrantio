#!/usr/bin/env python3
"""ESF ČR (esfcr.cz, Liferay 6 + portlet esfportalportletapplication) — layer-1 lossless harvest výzev.

STRUKTURA PŘED PRÓZOU — co Liferay dává strukturovaně (ověřeno sondou 2026-06-10, viz
docs/recon_ministerstva.md #2):
  - DVA AssetPublisher listingy výzev (jediné na webu, ověřeno homepage navigací i sitemapou):
      OPZ+ (2021–2027):  https://www.esfcr.cz/prehled-vyzev-opz-plus   instance 101_INSTANCE_SfUza2tXdZGm
      OPZ (2014–2020):   https://www.esfcr.cz/prehled-vyzev-opz        instance 101_INSTANCE_kOxpUSCnz5Jf
    Položka = blok `div.article`: titul+href, „Číslo výzvy:", „Platnost do:" (= DEADLINE
    příjmu žádostí — na esfcr je to oficiální sloupec uzávěrky, NENÍ to obecná past
    `platnost:` z prompts/pitfalls.md), publish-date, „Určeno pro".
    Stránkování: `?p_p_id=101_INSTANCE_<iid>&p_p_lifecycle=0&_101_INSTANCE_<iid>_delta=D
    &_101_INSTANCE_<iid>_cur=N` (delta ∈ {5,10,20,30,50,75} → limits acquisition.liferay_delta);
    text „z celkového počtu N." v pageru = kontrola úplnosti v kódu.
  - RSS change-feed AssetPublisheru (pro inkrementální re-check, NE pro plný harvest —
    vrací jen poslední položky):
      OPZ+: https://www.esfcr.cz/prehled-vyzev-opz-plus/-/asset_publisher/SfUza2tXdZGm/rss?p_p_cacheability=cacheLevelFull
      OPZ:  https://www.esfcr.cz/prehled-vyzev-opz/-/asset_publisher/kOxpUSCnz5Jf/rss?p_p_cacheability=cacheLevelFull
  - SITEMAP (robots.txt → /sitemap.xml): obsahuje i ~118 výzvových stránek BEZ listingu —
    éra OP LZZ 2007–2013 (slugy /vyzva-c-*, /vyzva-na-* … bez suffixu -opz/-opz-plus,
    „klubové" stránky s portletem Dokumenty). Bereme i ty (lossless, archiv neškodí).
  - Detail výzvy (server-rendered): segment id="main-content"…<footer>. OPZ/OPZ+ detail má
    strukturovaná pole `<p><strong>Label:</strong> hodnota</p>` (Číslo, Platnost od/do,
    Zahájení příjmu žádostí o podporu, Alokace v Kč, Specifický cíl, Priorita, Operační
    program, Programové období, Vyhlašovatel, Typ výzvy) + „Soubory ke stažení" s přímými
    linky /documents/… (Liferay Document Library, bez přípony → sniff_ext).
    LZZ klubová stránka má strom dokumentů s linky /<slug>/-/dokument/<id> → landing page
    → href s `downloadRevision` = přímý binární download.
  - POZOR: „Typ výzvy: uzavřená" = REŽIM výzvy (uzavřená/otevřená výzva pro předem určené
    žadatele), NENÍ to status! Status počítá VÝHRADNĚ kód z dat vs. --today.

Status (počítá kód, ne LLM): deadline = „Platnost do" (detail > listing fallback),
open_from = „Zahájení příjmu žádostí o podporu" (fallback „Platnost od").
today > deadline → closed; today < open_from → announced; jinak open. Bez dat → null.

Data se berou CELÁ (žádný cap; runaway hlídá limits safety.runaway_page_ceiling, loguje ⚠).
Pozor na \xa0 v datech („30. 9. 2026\xa014:00") a HTML-entity-encodované Liferay URL parametry.

Výstup (kontrakt jako vismo_documents.jsonl + open_from/deadline/status):
  data/esfcr_documents.jsonl  {host, web, title, url, date, kind, program, cislo_vyzvy,
      open_from, deadline, status, status_source, status_confidence, …strukturovaná pole…,
      body_text, attachments[], n_attachments}
  data/esfcr_files/<host>/<sha16>.<ext> + .txt

Spuštění (z kořene repa, .venv):
  python3 scripts/esfcr_harvest.py                          # plný harvest
  python3 scripts/esfcr_harvest.py --today 2026-06-10       # explicitní dnešek pro status
  python3 scripts/esfcr_harvest.py --resume                 # navaž (skip URL už v --out)
Po harvestu: python3 scripts/coverage_verify.py data/esfcr_documents.jsonl
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
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.parse import urljoin, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dsw2_fetch import (safe_url, sniff_ext, download, convert, ext_of,  # noqa: E402
                        UA, DOC_EXTS, DOC_EXT_RE)
from limits import L  # noqa: E402

HOST = "esfcr.cz"
BASE = "https://www.esfcr.cz"
# (label, listing path, AssetPublisher instance id) — jediné dva přehledy výzev na webu
LISTINGS = [
    ("OPZ+", f"{BASE}/prehled-vyzev-opz-plus", "SfUza2tXdZGm"),
    ("OPZ", f"{BASE}/prehled-vyzev-opz", "kOxpUSCnz5Jf"),
]
RSS_NOTE = {  # change-feedy (dokumentace; harvest jde přes plný listing)
    "OPZ+": f"{BASE}/prehled-vyzev-opz-plus/-/asset_publisher/SfUza2tXdZGm/rss?p_p_cacheability=cacheLevelFull",
    "OPZ": f"{BASE}/prehled-vyzev-opz/-/asset_publisher/kOxpUSCnz5Jf/rss?p_p_cacheability=cacheLevelFull",
}
SITEMAP = f"{BASE}/sitemap.xml"

CZ_DATE = r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})"
CZ_DATETIME = rf"{CZ_DATE}(?:\s*(\d{{1,2}}:\d{{2}}))?"
KLUB_DOC = re.compile(r"/-/dokument/(\d+)")
# strukturovaná pole detailu (label → klíč záznamu); hodnota = zbytek řádku / další řádek
DETAIL_FIELDS = [
    ("Číslo", "cislo_vyzvy"),
    ("Platnost od", "platnost_od"),
    ("Platnost do", "platnost_do"),
    ("Zahájení příjmu žádostí o podporu", "zahajeni_prijmu"),
    ("Alokace v Kč", "alokace_kc"),
    ("Specifický cíl", "specificky_cil"),
    ("Priorita", "priorita"),
    ("Investiční priorita", "investicni_priorita"),
    ("Operační program", "operacni_program"),
    ("Programové období", "programove_obdobi"),
    ("Vyhlašovatel", "vyhlasovatel"),
    ("Typ výzvy", "typ_vyzvy"),       # POZOR: režim výzvy, NE status
]


def fetch(url, timeout):
    last = None
    for _ in range(L("http.default_retries") or 1):
        try:
            req = urllib.request.Request(safe_url(url), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.0)
    raise last


def html_to_text(seg):
    """Plný text segmentu — lossless (žádný min-length filtr, jen kolaps whitespace + \xa0)."""
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", seg, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|li|h\d|tr|table|ul|ol|dd|dt)>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = H.unescape(s).replace("\xa0", " ")
    lines = (re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n"))
    return "\n".join(ln for ln in lines if ln)


def clean(s):
    return re.sub(r"\s+", " ", H.unescape(s).replace("\xa0", " ")).strip() if s else None


def parse_cz_date(s):
    """'30. 9. 2026 14:00' / '30. 09. 2026' → datetime.date | None."""
    m = re.search(CZ_DATE, s or "")
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
    except ValueError:
        return None


def compute_status(open_from, deadline, today):
    """→ (status, confidence). Den deadline včetně = ještě open."""
    dl, of = parse_cz_date(deadline), parse_cz_date(open_from)
    if not dl:
        return None, "low"
    if today > dl:
        return "closed", "high"
    if of and today < of:
        return "announced", "high"
    return "open", "high"


# ---------- listing ----------
def page_url(path, iid, delta, cur):
    return (f"{path}?p_p_id=101_INSTANCE_{iid}&p_p_lifecycle=0"
            f"&_101_INSTANCE_{iid}_delta={delta}&_101_INSTANCE_{iid}_cur={cur}"
            f"&p_r_p_564233524_resetCur=false")


def parse_listing_page(h):
    """→ (items[], total|None) z jedné stránky AssetPublisheru."""
    items = []
    for chunk in re.split(r'<div class="article">', h)[1:]:
        m = re.search(r'<h3 class="article-heading">\s*<a href="([^"]+)"[^>]*>(.*?)</a>', chunk, re.S)
        if not m:
            continue
        it = {"url": urljoin(BASE, H.unescape(m.group(1))), "title": clean(m.group(2))}
        mc = re.search(r"Číslo výzvy:\s*([^\s<]+)", chunk)
        it["cislo_vyzvy"] = clean(mc.group(1)) if mc else None
        mp = re.search(rf"Platnost do:\s*({CZ_DATETIME})", chunk.replace("\xa0", " "))
        it["platnost_do_listing"] = clean(mp.group(1)) if mp else None
        md = re.search(r'class="publish-date">([^<]+)', chunk)
        it["date"] = clean(md.group(1)) if md else None
        mu = re.search(r"Určeno pro:\s*<strong>([^<]*)", chunk)
        it["urceno_pro"] = clean(mu.group(1)) if mu else None
        items.append(it)
    mt = re.search(r"z\s+celkového\s+počtu\s+(\d+)", h)
    return items, (int(mt.group(1)) if mt else None)


def harvest_listing(label, path, iid, delta, timeout, polite):
    """Projde VŠECHNY stránky listingu → (items[], total_declared|None)."""
    items, seen, total = [], set(), None
    cur = 0
    while True:
        cur += 1
        if cur > L("safety.runaway_page_ceiling"):
            print(f"  ⚠ RUNAWAY listing {label}: cur={cur} — prošetři pager, NEzvyšuj naslepo",
                  file=sys.stderr)
            break
        h = fetch(page_url(path, iid, delta, cur), timeout)
        page_items, page_total = parse_listing_page(h)
        total = total or page_total
        new = [it for it in page_items if it["url"] not in seen]
        if not new:
            break
        for it in new:
            seen.add(it["url"])
        items.extend(new)
        print(f"  [{label}] strana {cur}: +{len(new)} (celkem {len(items)}"
              f"{f' / deklarováno {total}' if total else ''})", file=sys.stderr)
        if total and len(items) >= total:
            break
        time.sleep(polite)
    if total and len(items) != total:
        print(f"  ⚠ {label}: posbíráno {len(items)} ≠ deklarováno {total}", file=sys.stderr)
    return items, total


# ---------- gap-fill (--extra-urls: stránky ze sitemapy uniklé slug-filtru) ----------
# pořadí testů = priorita; hodnoty kind jsou jen hrubý hint, classify (vrstva 2) třídí později
GAP_METODIKA = re.compile(
    r"formulare|pokyny|hodnoceni|vyberova-komise|seminar|monitorovani|administrace|"
    r"jak-(podat|postupovat|zazadat|ziskat)|partnerstvi-v-projektech|podklady|vzor-|"
    r"evaluace|pruvodce|prirucka|verejna-podpora|misto-a-cas|podporovane-aktivity|"
    r"co-by-mel|zadosti-o-prezkum|zmena-v-osobe")
GAP_PROGRAM_HINTS = [  # substring slugu → program (nejdřív specifičtější)
    ("opz-plus", "OPZ+"), ("opzplus", "OPZ+"), ("opz_plus", "OPZ+"),
    ("oplzz", "OP LZZ"), ("op-lzz", "OP LZZ"), ("oprlz", "OP RLZ"), ("jpd3", "JPD3"),
    ("opz", "OPZ"),
]


def gapfill_kind(url):
    """Hrubá kategorizace gap-fill stránky podle slugu (lossless — vše se bere)."""
    slug = urlsplit(url).path.lower()
    if "klub" in slug:
        return "klub_vyzvy"
    if "/pribehy/" in slug:
        return "pribeh_projektu"
    if GAP_METODIKA.search(slug):
        return "metodika_gapfill"
    if "vyzv" in slug or re.search(r"\d{2}_\d{2}_\d{3}", slug):
        return "vyzva_gapfill"      # skutečná výzva s netypickým slugem → strukturovaná pole z detailu
    if "projekt" in slug:
        return "projekty_info"
    return "ostatni_gapfill"


def gapfill_program(url):
    slug = urlsplit(url).path.lower()
    for sub, prog in GAP_PROGRAM_HINTS:
        if sub in slug:
            return prog
    return None


# ---------- sitemap (loose LZZ-éra výzvy mimo listingy) ----------
def sitemap_vyzvy(timeout):
    xml = fetch(SITEMAP, timeout)
    return sorted({H.unescape(m.group(1)) for m in
                   re.finditer(r"<loc>(https://www\.esfcr\.cz/vyzva[^<]*)</loc>", xml)})


# ---------- detail ----------
def main_content(h):
    i = h.find('id="main-content"')
    if i < 0:
        return None
    j = h.find("<footer", i)
    return h[i:j] if j > 0 else h[i:]


def parse_detail(url, h):
    """→ (rec_fields, attachments[]) z detailu výzvy."""
    seg = main_content(h)
    if seg is None:
        return None, []
    body = html_to_text(seg)
    fields = {}
    for label, key in DETAIL_FIELDS:
        # 'Label:' + hodnota na témže nebo dalším řádku (prázdné řádky to_text zahodil)
        m = re.search(rf"(?m)^{re.escape(label)}:\s*$\n(.+)$", body) or \
            re.search(rf"(?m)^{re.escape(label)}:\s+(.+)$", body)
        fields[key] = clean(m.group(1)) if m else None
    mt = (re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
          or re.search(r'class="header-title"[^>]*>(.*?)</h3>', seg, re.S)
          or re.search(r"<title>(.*?)(?:\s*-\s*www\.esfcr\.cz)?</title>", h, re.S))
    title = clean(re.sub(r"<[^>]+>", " ", mt.group(1))) if mt else None
    # přílohy: přímé /documents/ + dokumenty s příponou + klubové /-/dokument/<id>
    atts = []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', seg, re.S):
        raw = H.unescape(m.group(1))
        if raw.startswith(("mailto:", "javascript:", "#", "tel:")):
            continue
        u = urljoin(url, raw)
        if urlsplit(u).netloc not in ("www.esfcr.cz", "esfcr.cz"):
            continue
        if "/documents/" in u or KLUB_DOC.search(u) or DOC_EXT_RE.search(u):
            name = clean(re.sub(r"<[^>]+>", " ", m.group(2))) or os.path.basename(urlsplit(u).path)
            atts.append({"url": u, "name": name})
    dedup = {}
    for a in atts:  # dedup dle URL, drž nejdelší jméno
        k = a["url"]
        if k not in dedup or len(a["name"] or "") > len(dedup[k]["name"] or ""):
            dedup[k] = a
    return {"title": title, "body_text": body, **fields}, list(dedup.values())


# ---------- přílohy ----------
def att_key(url):
    """Dedup-klíč: klubový dokument je týž napříč slugy stránek."""
    m = KLUB_DOC.search(url)
    return f"dokument:{m.group(1)}" if m else url


def resolve_klub_landing(url, timeout):
    """Landing /<slug>/-/dokument/<id> → přímý downloadRevision URL | None."""
    try:
        h = fetch(url, timeout)
    except Exception:  # noqa: BLE001
        return None
    m = re.search(r'href="([^"]*downloadRevision[^"]*)"', h)
    return urljoin(url, H.unescape(m.group(1))) if m else None


def materialize(att, files_dir, timeout, max_bytes):
    """Stáhni + převeď přílohu → doplněný manifest dict (lossless)."""
    fail = {"direct_url": None, "ext": None, "bytes": None,
            "txt_chars": None, "txt_path": None, "file_path": None}
    if KLUB_DOC.search(att["url"]):
        direct = resolve_klub_landing(att["url"], timeout)
        if not direct:
            return {**att, **fail, "status": "landing-parse-fail"}
    else:
        direct = att["url"]
    ext = ext_of(direct)
    if ext == "bin" or ext not in DOC_EXTS:
        m = re.search(r"\.(\w{2,5})$", att.get("name") or "")
        ext = m.group(1).lower() if m and m.group(1).lower() in DOC_EXTS \
            else (sniff_ext(direct, timeout) or ext)
    if ext not in DOC_EXTS and ext not in ("zip", "rar", "7z"):
        return {**att, **fail, "direct_url": direct, "ext": ext, "status": "not-a-doc"}
    ddir = os.path.join(files_dir, HOST)
    os.makedirs(ddir, exist_ok=True)
    sha = hashlib.sha256(att_key(att["url"]).encode()).hexdigest()[:16]
    fpath, tpath = os.path.join(ddir, f"{sha}.{ext}"), os.path.join(ddir, f"{sha}.txt")
    if not os.path.exists(fpath):
        nbytes, derr = download(direct, fpath, timeout, max_bytes)
        if not nbytes:
            return {**att, **fail, "direct_url": direct, "ext": ext,
                    "status": derr or "download-fail"}
    if ext not in DOC_EXTS:                                   # archiv (zip…): ulož bez konverze
        return {**att, "direct_url": direct, "ext": ext, "bytes": os.path.getsize(fpath),
                "txt_chars": None, "txt_path": None, "file_path": fpath, "status": "archive-no-convert"}
    if os.path.exists(tpath):
        chars, cerr = len(open(tpath, encoding="utf-8", errors="replace").read()), None
    else:
        chars, cerr = convert(fpath, ext, tpath, timeout)
    return {**att, "direct_url": direct, "ext": ext, "bytes": os.path.getsize(fpath),
            "txt_chars": chars, "txt_path": tpath if chars else None,
            "file_path": fpath, "status": "ok" if chars else (cerr or "convert-fail")}


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/esfcr_documents.jsonl")
    ap.add_argument("--files-dir", default="data/esfcr_files")
    ap.add_argument("--today", default=date.today().isoformat(),
                    help="referenční den pro výpočet statusu (YYYY-MM-DD, default dnešek)")
    ap.add_argument("--resume", action="store_true", help="navaž: přeskoč URL už v --out, appenduj")
    ap.add_argument("--extra-urls", default=None, metavar="FILE",
                    help="gap-fill režim: jen URL ze souboru (1/řádek), bez listingů/sitemapy; "
                         "dedup proti --out, APPEND, MARKER=ESFCR_GAPFILL")
    ap.add_argument("--no-sitemap-extra", action="store_true",
                    help="bez LZZ-éra výzev ze sitemapy (jen oba listingy)")
    ap.add_argument("--timeout", type=int, default=L("http.default_timeout_s"))
    ap.add_argument("--delay", type=float, default=L("http.polite_delay_s"))
    ap.add_argument("--workers", type=int, default=L("http.download_workers"))
    args = ap.parse_args()
    today = date.fromisoformat(args.today)
    delta = L("acquisition.liferay_delta")
    max_bytes = L("safety.doc_download_max_mb") * 1024 * 1024

    append = args.resume or bool(args.extra_urls)
    done_urls = set()
    if append and os.path.exists(args.out):
        for ln in open(args.out, encoding="utf-8"):
            try:
                done_urls.add(json.loads(ln)["url"])
            except Exception:  # noqa: BLE001
                pass
        print(f"  [dedup] {len(done_urls)} URL už v {args.out}", file=sys.stderr)

    work, listing_totals, n_loose, n_candidates = [], {}, 0, None
    if args.extra_urls:
        # gap-fill: jen URL ze souboru — stejný detail parser + materializace jako hlavní harvest
        urls = sorted({ln.strip() for ln in open(args.extra_urls, encoding="utf-8") if ln.strip()})
        n_candidates = len(urls)
        for u in urls:
            work.append({"url": u, "title": None, "cislo_vyzvy": None,
                         "platnost_do_listing": None, "date": None, "urceno_pro": None,
                         "program": gapfill_program(u), "kind": gapfill_kind(u)})
        print(f"  [gap-fill] {n_candidates} kandidátů z {args.extra_urls}", file=sys.stderr)
    else:
        # 1) listingy (OPZ+ i OPZ archiv) — VŠECHNY stránky
        listed_urls = set()
        for label, path, iid in LISTINGS:
            items, total = harvest_listing(label, path, iid, delta, args.timeout, args.delay)
            listing_totals[label] = {"declared": total, "collected": len(items)}
            for it in items:
                listed_urls.add(it["url"])
                kind = "vyzva_opz_plus" if label == "OPZ+" else "vyzva_opz"
                work.append({**it, "program": label, "kind": kind})

        # 2) sitemap → výzvové stránky mimo oba listingy (éra OP LZZ 2007–2013)
        if not args.no_sitemap_extra:
            for u in sitemap_vyzvy(args.timeout):
                if u not in listed_urls:
                    n_loose += 1
                    work.append({"url": u, "title": None, "cislo_vyzvy": None,
                                 "platnost_do_listing": None, "date": None, "urceno_pro": None,
                                 "program": "OP LZZ/starší (mimo listing)", "kind": "vyzva_archiv_sitemap"})
            print(f"  [sitemap] +{n_loose} výzev mimo listingy (LZZ éra)", file=sys.stderr)

    # 3) detaily — plný text lossless + strukturovaná pole + sběr příloh
    recs, att_by_page = [], {}
    for i, it in enumerate(w for w in work if w["url"] not in done_urls):
        try:
            h = fetch(it["url"], args.timeout)
        except Exception as e:  # noqa: BLE001
            print(f"  [err] {type(e).__name__}: {it['url'][:90]}", file=sys.stderr)
            recs.append({**it, "host": HOST, "web": HOST, "error": "fetch_fail"})
            continue
        det, atts = parse_detail(it["url"], h)
        rec = {"host": HOST, "web": HOST, **it}
        if det:
            det["title"] = det["title"] or it.get("title")
            rec.update(det)
        else:
            rec["error"] = "no-main-content"
        # status — POČÍTÁ KÓD: deadline = Platnost do (detail > listing), open_from = zahájení příjmu
        deadline = rec.get("platnost_do") or rec.get("platnost_do_listing")
        open_from = rec.get("zahajeni_prijmu") or rec.get("platnost_od")
        status, conf = compute_status(open_from, deadline, today)
        rec.update({"deadline": deadline, "open_from": open_from, "status": status,
                    "status_source": ("platnost_do_detail" if rec.get("platnost_do")
                                      else "platnost_do_listing" if deadline else None),
                    "status_confidence": conf})
        recs.append(rec)
        att_by_page[it["url"]] = atts
        if (i + 1) % 25 == 0:
            print(f"  [detail {i + 1}] {it['url'][:80]}", file=sys.stderr)
        time.sleep(args.delay)

    # 4) materializace příloh — dedup přes stránky (klubový dokument dle id)
    uniq = {}
    for atts in att_by_page.values():
        for a in atts:
            uniq.setdefault(att_key(a["url"]), a)
    print(f"  materializace {len(uniq)} unikátních příloh…", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        manifests = dict(zip(uniq.keys(), ex.map(
            lambda a: materialize(a, args.files_dir, args.timeout, max_bytes), uniq.values())))
    for rec in recs:
        atts = att_by_page.get(rec["url"], [])
        rec["attachments"] = [{**manifests[att_key(a["url"])], "url": a["url"], "name": a["name"]}
                              for a in atts]
        rec["n_attachments"] = len(rec["attachments"])

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a" if append else "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")

    ok = sum(1 for a in manifests.values() if a["status"] == "ok")
    by = lambda f: {k: sum(1 for r in recs if r.get(f) == k)  # noqa: E731
                    for k in sorted({r.get(f) for r in recs}, key=str)}
    if args.extra_urls:
        failed = sum(1 for r in recs if r.get("error") == "fetch_fail")
        print(json.dumps({"MARKER": "ESFCR_GAPFILL", "today": args.today,
                          "candidates": n_candidates, "fetched_ok": len(recs) - failed,
                          "failed": failed, "appended": len(recs),
                          "attachments_unique": len(uniq), "attachments_ok": ok,
                          "by_kind": by("kind"), "by_status": by("status"),
                          "out": args.out, "files_dir": args.files_dir},
                         ensure_ascii=False))
        return
    print(json.dumps({"MARKER": "ESFCR_HARVEST", "today": args.today,
                      "vyzvy": len(recs), "by_kind": by("kind"), "by_status": by("status"),
                      "listing_totals": listing_totals, "sitemap_extra": n_loose,
                      "attachments_unique": len(uniq), "attachments_ok": ok,
                      "rss": RSS_NOTE, "out": args.out, "files_dir": args.files_dir},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
