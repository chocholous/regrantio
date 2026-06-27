#!/usr/bin/env python3
"""MPSV (Ministerstvo práce a sociálních věcí) — vrstva 1: dotační výzvy → text + dokumenty.

PROČ TENHLE SKRIPT EXISTUJE (oprava historického bugu):
  Původní „harvest" MPSV (data/h19_mpsv.jsonl) sklidil JEN homepage `https://www.mpsv.cz` —
  což je dnes Nuxt SPA (po migraci na gov.cz jen redirect/rozcestník): žádná výzva, žádný
  dokument, jen theme-toggle JS a titulky novinek. Proto MPSV NIKDY nedoputoval do datasetu
  (a správně — ingestovat ten balast by znamenalo nasypat šum). Skutečná dotační sekce žije na
  `https://mpsv.gov.cz` — TÝŽ gov.cz portálový CMS jako mze.gov.cz/mzp.gov.cz, který už umí
  `scripts/eagri.py`. Tenhle skript proto eagri harvester REUSEuje a přidává jen MPSV-specifický
  rozcestník→detail discovery.

MODEL (shodný s eagri/mv/marwel → konzumuje build_extract_input --source-type harvest):
  1) seed rozcestníky (dotační řízení, výzvy NPO/OPZ+, rodina, sociální služby)
  2) discovery: z obsahu rozcestníků vytáhni odkazy na DETAIL výzev (slug obsahuje vyzva-c./dotac…)
  3) harvest každého detailu eagri.process() → {url,host,title,body_text,attachments,n_attachments}
  Přílohy (Metodika, Zásady, formuláře) jsou /cms/documents/<uuid>/<soubor>.pdf — chytá je univerzální
  doc regex; stažení+konverzi dělá doc-store ve fázi 2. Grantové podmínky (lhůta/částka/oprávnění)
  žijí převážně v příloze, ne v textu stránky — proto je lossless listujeme.

POZOR — tohle je VRSTVA 1 (jen text+dokumenty). Aby MPSV vstoupil do opportunities_v2.jsonl, musí
běžet VRSTVA 2 (LLM): build_extract_input → classify_wf/extract_wf → compute_status → ingest_rich →
consolidate. Tenhle skript sám o sobě dataset nemění (žádné fabrikované záznamy).

Spuštění z kořene repa:
   python3 scripts/mpsv.py                      # discovery + harvest → data/mpsv_documents.jsonl
   python3 scripts/mpsv.py --no-discover        # jen explicitní SEED_HUBS
"""
import argparse, json, os, re, sys, time
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eagri  # gov.cz portálový CMS harvester (fetch/content_area/process) — sdílený s mze/mzp

# Rozcestníky dotační sekce MPSV (mpsv.gov.cz). Z nich se discoverují detaily výzev.
SEED_HUBS = [
    "https://mpsv.gov.cz/dotacni-rizeni-pro-rok-2026",
    "https://mpsv.gov.cz/vyzvy1",
    "https://mpsv.gov.cz/narodni-dotacni-tituly",
    "https://mpsv.gov.cz/rodina-a-ochrana-prav-deti",
    "https://mpsv.gov.cz/socialni-prace-a-socialni-sluzby",
    "https://mpsv.gov.cz/vyhlaseni-dotacniho-rizeni-v-oblasti-poskytovani-socialnich-sluzeb-s-nadregionalni-ci-celostatni-pusobnosti-1",
]

# Detail výzvy/dotace: slug obsahuje tyto stopy (a NENÍ to metodika/FAQ/zákon/zpravodaj).
DETAIL_HINT = re.compile(r"(vyzva-c|dotac|dotacni|grant|narodni-plan|prispevek-na-vykon)", re.I)
DETAIL_SKIP = re.compile(r"(faq|casto-kladene|metodick|novela-zakona|zpravodaj|provoz-aplikace|stanovisk)", re.I)


def discover(hubs):
    """Z obsahu rozcestníků vytáhni interní odkazy na detail výzev (1-úrovňové slugy mpsv.gov.cz)."""
    found = {}
    for hub in hubs:
        h, final = eagri.fetch(hub)
        if not h:
            print(f"  ⚠ discover fail: {hub}", flush=True)
            continue
        ca = eagri.content_area(h)
        for m in re.finditer(r'href="([^"#?]+)"', ca):
            full = urljoin(final or hub, m.group(1))
            if "mpsv.gov.cz" not in full or "/cms/documents" in full:
                continue
            slug = full.split("mpsv.gov.cz/")[-1].strip("/")
            if not slug or slug.count("/") > 0:        # jen 1-úrovňové články, ne sekce/nav
                continue
            if DETAIL_HINT.search(slug) and not DETAIL_SKIP.search(slug):
                found.setdefault(full, hub)
    return list(found)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/mpsv_documents.jsonl")
    ap.add_argument("--no-discover", action="store_true", help="jen SEED_HUBS, bez discovery detailů")
    ap.add_argument("--delay", type=float, default=0.3)
    a = ap.parse_args()

    urls = list(SEED_HUBS)
    if not a.no_discover:
        det = discover(SEED_HUBS)
        print(f"discovery: {len(det)} detail stránek výzev", flush=True)
        for u in det:
            if u not in urls:
                urls.append(u)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    open(a.out, "w").close()
    ok = empty = 0
    for i, u in enumerate(urls):
        rec = eagri.process(u)
        rec["source"] = "mpsv"
        bt = len(rec.get("body_text") or "")
        if bt < 200 and not rec.get("attachments"):
            empty += 1
        else:
            ok += 1
        open(a.out, "a", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[{i+1}/{len(urls)}] att={rec.get('n_attachments','-')} body={bt} :: {str(rec.get('title'))[:55]}", flush=True)
        time.sleep(a.delay)
    print(f"MPSV_DONE {len(urls)} stránek (ok={ok} prázdných={empty}) -> {a.out}")
    print("⚠ VRSTVA 1 hotová. Pro vstup do datasetu spusť vrstvu 2: "
          "build_extract_input --source-type harvest → classify_wf/extract_wf → ingest_rich → consolidate.")


if __name__ == "__main__":
    main()
