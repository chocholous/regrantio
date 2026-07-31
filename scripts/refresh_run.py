#!/usr/bin/env python3
"""refresh_run.py — JEDEN příkaz na refresh kolo (doplněk checklistu refresh.py).

`refresh.py` říká CO a JAK ČASTO (checklist); TENHLE skript to SPUSTÍ. Pro každý zdroj
se známým plně-deterministickým řetězem provede REFRESH.md §3 smyčku:

    harvest → build_extract_input --no-prefilter → data/_<src>_extract.py → ingest_rich

a na konci (bez --no-tail) společný tail: consolidate → fix_dataset --today → build_app
(+ cp do docs/) → export_api (s --min-ratio pojistkou).

Zdroje mimo tenhle registr (seed-driven s ručními ročníky, browser/Playwright, html
kraje/města s vlastními ingesty) se refreshují ručně dle refresh.py --commands — sem
patří jen to, co jde bez lidského rozhodnutí.

Použití (z kořene repa, venv):
  python scripts/refresh_run.py --tier structured             # WP REST/JSON zdroje (týdně)
  python scripts/refresh_run.py --tier html                   # deterministické html zdroje (2 týdny)
  python scripts/refresh_run.py --sources gacr,tacr           # výběr
  python scripts/refresh_run.py --tier structured --no-tail   # bez závěrečného tailu
Selhání jednoho zdroje NEshodí kolo (loguje se a pokračuje se dalším); exit code = počet selhání.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr:
        sys.stderr.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

# Registr plně-deterministických refresh řetězů: slug → (harvest argv, tier).
# Slug = <src> v data/<src>_documents.jsonl + data/_<src>_extract.py + data/<src>_{in,out}.
SOURCES = {
    # structured (WP REST / JSON API / inline-JS) — týdně
    "gacr":  (["scripts/gacr.py"], "structured"),
    "tacr":  (["scripts/tacr.py"], "structured"),
    "nsa":   (["scripts/nsa.py"], "structured"),
    "sfzp":  (["scripts/sfzp.py"], "structured"),
    "opzp":  (["scripts/opzp.py"], "structured"),
    "opst":  (["scripts/opst.py"], "structured"),
    "opjak": (["scripts/opjak.py"], "structured"),
    "osf":   (["scripts/osf.py"], "structured"),
    # html (deterministické listing/detail parsery) — à 2 týdny
    "mk":            (["scripts/mk_harvest.py"], "html"),
    "msmt":          (["scripts/msmt_harvest.py"], "html"),
    "esfcr":         (["scripts/esfcr_harvest.py"], "html"),
    "czechaid":      (["scripts/czechaid_harvest.py"], "html"),
    "hzs":           (["scripts/hzs_harvest.py"], "html"),
    "plone_ostrava": (["scripts/plone_ostrava.py"], "html"),
    "sfa":   (["scripts/sfa.py"], "html"),
    "sfdi":  (["scripts/sfdi.py"], "html"),
    "sfpi":  (["scripts/sfpi.py"], "html"),
    "eeagrants": (["scripts/eeagrants.py"], "html"),
    # 2026-07-31: zdroje, které MĚLY kompletní řetěz (harvester + data/_<src>_extract.py),
    # ale chyběly v registru → refresh je míjel a hlásil je jako ORPHAN (147 záznamů).
    "nadacevia": (["scripts/nadacevia.py"], "html"),
    "mzcr":      (["scripts/harvest_site.py", "mzd.gov.cz"], "generic"),
    "mzp":       (["scripts/harvest_site.py", "mzp.cz"], "generic"),
    "mv":        (["scripts/mv_cms.py"], "html"),
    "opd":       (["scripts/opd.py"], "html"),   # OP Doprava — tabulka výzev na opd3.opd.cz
}


def run(argv, label):
    print(f"\n$ {' '.join(argv)}", flush=True)
    r = subprocess.run([PY] + argv, cwd=ROOT)
    if r.returncode != 0:
        print(f"!! {label} FAILED (exit {r.returncode})", file=sys.stderr)
    return r.returncode == 0


def refresh_source(src, today):
    harvest, _tier = SOURCES[src]
    docs = f"data/{src}_documents.jsonl"
    ok = run(harvest, f"{src} harvest")
    if not ok:
        return False
    if not os.path.exists(os.path.join(ROOT, docs)):
        print(f"!! {src}: {docs} po harvestu neexistuje", file=sys.stderr)
        return False
    if not run(["scripts/build_extract_input.py", docs, "--source", src,
                "--out-dir", f"data/{src}_in", "--force-type", "grant", "--no-prefilter"],
               f"{src} input"):
        return False
    if not run([f"data/_{src}_extract.py"], f"{src} extract"):
        return False
    return run(["scripts/ingest_rich.py", "--out-dir", f"data/{src}_out",
                "--src", f"data/{src}_in", "--existing", "data/opportunities_v2.jsonl",
                "--out", "data/opportunities_v2.jsonl", "--harvest-file", docs,
                "--today", today], f"{src} ingest")


def tail(today):
    ok = True
    ok &= run(["scripts/consolidate.py"], "consolidate")
    ok &= run(["scripts/fix_dataset.py", "--today", today], "fix_dataset")
    ok &= run(["scripts/build_app.py"], "build_app")
    app = os.path.join(ROOT, "data", "grants_app.html")
    if os.path.exists(app):
        shutil.copy2(app, os.path.join(ROOT, "docs", "grants_app.html"))
        print("cp data/grants_app.html -> docs/grants_app.html")
    ok &= run(["scripts/export_api.py"], "export_api")   # --min-ratio pojistka uvnitř
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["structured", "html"], help="refreshni celý tier")
    ap.add_argument("--sources", help="čárkou oddělené slugy (přebije --tier)")
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--no-tail", action="store_true", help="bez závěrečného consolidate/fix/app/export")
    a = ap.parse_args()

    if a.sources:
        srcs = [s.strip() for s in a.sources.split(",") if s.strip()]
        bad = [s for s in srcs if s not in SOURCES]
        if bad:
            ap.error(f"neznámé zdroje {bad}; registr: {sorted(SOURCES)}")
    elif a.tier:
        srcs = [s for s, (_h, t) in SOURCES.items() if t == a.tier]
    else:
        ap.error("zadej --tier nebo --sources")

    backup = os.path.join(ROOT, "data", "opportunities_v2.jsonl.pre-refresh.bak")
    live = os.path.join(ROOT, "data", "opportunities_v2.jsonl")
    if os.path.exists(live):
        shutil.copy2(live, backup)
        print(f"záloha datasetu -> {backup}")

    failed = []
    for src in srcs:
        print(f"\n=================== {src} ===================")
        if not refresh_source(src, a.today):
            failed.append(src)

    if not a.no_tail:
        tail(a.today)

    print(json.dumps({"MARKER": "REFRESH_RUN", "requested": srcs, "failed": failed,
                      "today": a.today}, ensure_ascii=False))
    sys.exit(len(failed))


if __name__ == "__main__":
    main()
