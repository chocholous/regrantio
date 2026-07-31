#!/usr/bin/env python3
"""CzechAid gap-fill — historické dotační výzvy v /aktivity/aktuality/ (completeness gate).

KONTEXT: czechaid_harvest.py bere BFS jen sekci /dotace. Completeness gate (coverage_verify)
našel v sitemap další grant-relevantní stránky — historické výzvy publikované jako aktuality
(slugy dotacni-vyzva-*, dotacni-rizeni-*, dotacni-vyberove-rizeni-*, vyhlaseni-*, vyzva-*…).

Tenhle skript NENÍ nový harvester — IMPORTUJE funkce z czechaid_harvest (fetch, canon,
main_area, title_of, links_of, to_text, slug_status, materialize, FILE_PATH_RE) a drží
STEJNÝ výstupní kontrakt (data/czechaid_documents.jsonl + data/czechaid_files/<host>/).

Triáž kandidátů (DETERMINISTICKY podle slugu; lossless princip = hraniční případy SE BEROU,
vrstva classify je vytřídí později):
  - SKIP_JOB_RE  — náborové inzeráty na pozice ČRA („vyhlašuje výběrové řízení na pozici…",
                   „na obsazení pozice…", slug začínající názvem pozice). NE granty.
  - SKIP_NEWS_RE — čistě retrospektivní PR články bez výzvy („ČR podpořila vznik…",
                   „S podporou programu B2B se firma…"). Jen tyhle dva vzory; všechno
                   ostatní (oznámení, prodloužení lhůt, výsledky řízení, webináře,
                   formuláře, tendry na experty) se bere — radši vzít než zahodit.

Záznam: kind="aktualita" (nová hodnota vedle vyzva/listing — stránka je novinka, ne detail
výzvy; classify dostane plný text). Dedup podle KANONICKÉ final URL proti záznamům už
v --out (url + requested_url + alias_urls) — APPEND only, nic se nemaže ani nepřepisuje.

Spuštění (z kořene repa): .venv/bin/python scripts/czechaid_gapfill.py --extra-urls /tmp/czechaid_gap_urls.txt
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse
import json
import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import czechaid_harvest as ch  # noqa: E402  (fetch, canon, links_of, materialize, …)
import dsw2_fetch as df  # noqa: E402  (DOC_EXTS)
from limits import L  # noqa: E402

# Náborové inzeráty (pracovní pozice v ČRA) — jediný jednoznačný balast dle slugu.
SKIP_JOB_RE = re.compile(
    r"(na-pozici|na-obsazeni-pozice|^pracovnik-|personalist|office-manager)", re.I)
# Retrospektivní PR články (žádná výzva/řízení, jen story o hotové podpoře).
SKIP_NEWS_RE = re.compile(
    r"^(ceska-republika-podporila-|s-podporou-)", re.I)
# Legacy WordPress upload cesty — staré aktuality linkují přílohy přes /wp-content/uploads/
# (web byl dřív WP; nový CMS staré cesty zachoval). FILE_PATH_RE (/file/<md5>/<id>/) je nechytí.
WP_UPLOAD_RE = re.compile(r"^/wp-content/uploads/", re.I)
ATT_EXTS = set(df.DOC_EXTS) | {"zip"}


def materialize_gap(att, files_dir, timeout, max_bytes):
    """ch.materialize + NFC fallback: hrefy legacy wp-content souborů jsou v HTML v NFD
    (rozložená diakritika, artefakt staré WP migrace), server ale servíruje jen NFC tvar
    → NFD URL = http-404. Identita záznamu zůstává původní href (lossless), skutečně
    stažené URL jde do fetched_url."""
    out = ch.materialize(att, files_dir, timeout, max_bytes)
    nfc = unicodedata.normalize("NFC", att["url"])
    if out.get("status") == "http-404" and nfc != att["url"]:
        retry = ch.materialize({**att, "url": nfc}, files_dir, timeout, max_bytes)
        if retry.get("status") != "http-404":
            return {**retry, "url": att["url"], "fetched_url": nfc}
    return out


def is_attachment(path):
    """Příloha = nový /file/ handler ∪ legacy /wp-content/uploads/ ∪ přímý link na dokument."""
    if ch.FILE_PATH_RE.match(path) or WP_UPLOAD_RE.match(path):
        return True
    return os.path.splitext(path)[1].lstrip(".").lower() in ATT_EXTS


def triage(url):
    """→ 'job' | 'news' | 'take' — deterministicky podle posledního segmentu cesty."""
    slug = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
    if SKIP_JOB_RE.search(slug):
        return "job"
    if SKIP_NEWS_RE.search(slug):
        return "news"
    return "take"


def known_urls(out_path):
    """Všechny URL identity už v datasetu (final + requested + aliasy) → dedup množina."""
    seen = set()
    if not os.path.exists(out_path):
        return seen
    with open(out_path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            seen.add(r["url"])
            if r.get("requested_url"):
                seen.add(r["requested_url"])
            seen.update(r.get("alias_urls") or [])
    return seen


def harvest_extra(url, timeout):
    """Jako ch.harvest_page, ale bez omezení na /dotace a bez BFS (seznam je daný).
    → (record_bez_příloh | None, [(att_url, label)])."""
    h, final = ch.fetch(url, timeout)
    if h is None:
        return None, []
    path = urlsplit(final).path
    ma = ch.main_area(h)
    slug = path.rstrip("/").rsplit("/", 1)[-1] or None
    atts, att_seen = [], set()
    for full, label in ch.links_of(ma, final):
        if is_attachment(urlsplit(full).path) and full not in att_seen:
            att_seen.add(full)
            atts.append((full, label))
    sg = ch.slug_status(slug) if slug else None
    rec = {"web": ch.HOST, "host": ch.HOST, "title": ch.title_of(h, ma), "url": final,
           "requested_url": url if url != final else None,
           "slug": slug, "date": None,
           # redirect na /dotace/<slug> = detail výzvy (kontraktní kind), jinak aktualita
           "kind": "vyzva" if path.startswith("/dotace/") else "aktualita",
           "status_guess": sg, "status": sg or "unknown",
           "status_source": "slug_guess" if sg else None,
           "status_confidence": "low" if sg else None,
           "deadline": None,                       # jen v próze → vrstva 2, NE magie tady
           "body_text": ch.to_text(ma)}
    return rec, atts


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extra-urls", required=True, help="soubor s kandidátními URL (1/řádek)")
    ap.add_argument("--out", default="data/czechaid_documents.jsonl")
    ap.add_argument("--files-dir", default="data/czechaid_files")
    ap.add_argument("--no-attachments", action="store_true")
    ap.add_argument("--timeout", type=int, default=L("http.default_timeout_s"))
    ap.add_argument("--delay", type=float, default=L("http.polite_delay_s"))
    ap.add_argument("--workers", type=int, default=L("http.download_workers"))
    args = ap.parse_args()
    max_bytes = L("safety.doc_download_max_mb") * 1024 * 1024
    os.makedirs(args.files_dir, exist_ok=True)

    cands = [ln.strip() for ln in open(args.extra_urls, encoding="utf-8") if ln.strip()]
    skipped = {"job": [], "news": []}
    queue = []
    for u in cands:
        t = triage(u)
        (queue if t == "take" else skipped[t]).append(ch.canon(u).split("#")[0])
    for kind, urls in skipped.items():
        for u in urls:
            print(f"  SKIP[{kind}] {urlsplit(u).path.rsplit('/', 1)[-1]}", file=sys.stderr)

    existing = known_urls(args.out)
    records, att_by_page, by_final = [], {}, {}
    n_dedup = n_err = 0
    for i, url in enumerate(queue, 1):
        if url in existing:
            n_dedup += 1
            continue
        rec, atts = harvest_extra(url, args.timeout)
        if rec is None:
            n_err += 1
            continue
        if rec["url"] in existing:                 # redirect na už harvestnutou stránku
            n_dedup += 1
            continue
        if rec["url"] in by_final:                 # duplicitní slug v kandidátech (301)
            by_final[rec["url"]].setdefault("alias_urls", []).append(url)
            continue
        by_final[rec["url"]] = rec
        records.append(rec)
        att_by_page[rec["url"]] = atts
        print(f"  [{len(records)}/{len(queue)}] {rec['kind']:9} att={len(atts)} "
              f"status={rec['status']:9} :: {str(rec['title'])[:70]}", file=sys.stderr)
        time.sleep(args.delay)

    # materializace příloh — unikátní URL jednou (sdílené soubory už na disku se nestahují znovu)
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
                lambda a: materialize_gap(a, args.files_dir, args.timeout, max_bytes),
                uniq.values())))
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

    with open(args.out, "a", encoding="utf-8") as o:   # APPEND — lossless, nic se nepřepisuje
        for r in records:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(json.dumps({"MARKER": "CZECHAID_GAPFILL",
                      "candidates": len(cands), "taken": len(queue),
                      "skipped_jobs": len(skipped["job"]), "skipped_news": len(skipped["news"]),
                      "appended": len(records), "dedup_existing": n_dedup, "fetch_err": n_err,
                      "attachments_unique": len(uniq), "attachments_ok": n_att_ok,
                      "attachments_media_skipped": n_att_media, "attachments_err": n_att_err,
                      "out": args.out, "files_dir": args.files_dir}, ensure_ascii=False))


if __name__ == "__main__":
    main()
