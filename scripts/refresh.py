#!/usr/bin/env python3
"""refresh.py — operační přehled „co a jak re-harvestovat", aby dataset zůstal aktuální.

NEspouští harvestery sám (jsou různě drahé: WP REST = vteřiny, Playwright/seed-driven = minuty a ruční
údržba seedů). Místo toho je to **checklist generator**: spojí autoritativní registr zdrojů
(`routing.yaml` sekce `sources:`) s živým datasetem (`data/opportunities_v2.jsonl`) a vypíše pro každý
zdroj harvester, refresh-tier (jak drahé/automatické to je), počet záznamů a přesný příkaz k re-harvestu.

Tier (jak se zdroj obnovuje):
  structured  WP REST / inline-JS / JSON API — plně re-harvestovatelné, levné; --since/--year posune okno
  html        front-end HTML listing/detail — levné, ale parser citlivý na redesign
  seed        seed-driven landing pages (mpo/eagri/mmr/vlada…) — nový ročník = doplnit seed URL ručně
  browser     potřebuje Playwright/odposlech (eu_ft, lewis SPA) — drahé, dedikovaná obnova
  generic     univerzální harvest_site.py (zdroj bez dedikovaného parseru) — ověř ručně

Použití (z kořene repa):
  python scripts/refresh.py                 # přehledová tabulka + gap-check
  python scripts/refresh.py --commands      # + přesné harvest příkazy per zdroj
  python scripts/refresh.py --stale-days 30 # zvýrazni zdroje, jejichž harvest artefakt je starší než N dní
"""
import argparse, json, os, sys, time
from collections import Counter, defaultdict
import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# harvester script → refresh tier (default = html). Klíč = basename bez .py.
TIER = {
    # browser (Playwright / odposlech XHR)
    "eu_ft": "browser", "lewis_discover": "browser", "lewis_dynamo": "browser",
    # seed-driven (ručně udržované seed URL / ročníky)
    "mpo": "seed", "mmr": "seed", "eagri": "seed", "mpsv": "seed", "marwel": "seed",
    "vlada": "seed", "sfk": "seed",
    # structured (REST / inline-JS / JSON API)
    "wp_harvest": "structured", "harvest_site": "generic", "dsw2": "structured",
    "nadacevia": "structured", "osf": "structured", "nsa": "structured", "gacr": "structured",
    "tacr": "structured", "sfzp": "structured", "opzp": "structured", "opst": "structured",
    "opjak": "structured", "dotis_harvest": "structured", "kentico_irop": "structured",
}


def harvester_slug(path):
    b = os.path.basename(path)
    return b[:-3] if b.endswith(".py") else b


def tier_of(harvesters):
    slugs = [harvester_slug(h) for h in harvesters]
    if any(TIER.get(s) == "browser" for s in slugs):
        return "browser"
    if any(TIER.get(s) == "seed" for s in slugs):
        return "seed"
    if slugs and all(TIER.get(s) == "generic" for s in slugs):
        return "generic"
    if any(TIER.get(s) == "structured" for s in slugs):
        return "structured"
    return "html"


def load_routing():
    with open(os.path.join(ROOT, "routing.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_platform_map():
    p = os.path.join(ROOT, "platform_map.json")
    if not os.path.exists(p):
        return {}
    return json.load(open(p, encoding="utf-8")).get("final", {})


def load_dataset_sources():
    p = os.path.join(ROOT, "data", "opportunities_v2.jsonl")
    c = Counter()
    if not os.path.exists(p):
        return c
    for line in open(p, encoding="utf-8"):
        if line.strip():
            c[json.loads(line).get("source")] += 1
    return c


def artifact_age_days(slug):
    """Best-effort: stáří data/<slug>_documents.jsonl (nebo None)."""
    p = os.path.join(ROOT, "data", f"{slug}_documents.jsonl")
    if os.path.exists(p):
        return (time.time() - os.path.getmtime(p)) / 86400
    return None


def match_count(src_counts, host, harvesters):
    """Best-effort přiřazení počtu záznamů ze živého datasetu k registrovanému zdroji.
    Dataset `source` bývá buď host (dotace.brno.cz) nebo slug parseru (nsa, eagri)."""
    if host in src_counts:
        return src_counts[host], host
    for h in harvesters:
        slug = harvester_slug(h).replace("_harvest", "")
        if slug in src_counts:
            return src_counts[slug], slug
    return 0, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commands", action="store_true", help="vypiš přesné harvest příkazy per zdroj")
    ap.add_argument("--stale-days", type=int, default=0, help="zvýrazni zdroje s harvest artefaktem starším než N dní")
    a = ap.parse_args()

    R = load_routing()
    sources = R.get("sources") or {}
    src_counts = load_dataset_sources()

    rows = []
    matched_ds = set()
    for host, entry in sources.items():
        harvesters = entry.get("harvester") or []
        tier = tier_of(harvesters)
        cnt, ds_key = match_count(src_counts, host, harvesters)
        if ds_key:
            matched_ds.add(ds_key)
        slug = harvester_slug(harvesters[0]).replace("_harvest", "") if harvesters else host
        age = artifact_age_days(harvester_slug(harvesters[0])) if harvesters else None
        rows.append((tier, -cnt, host, harvesters, cnt, age))

    order = {"structured": 0, "html": 1, "seed": 2, "browser": 3, "generic": 4}
    rows.sort(key=lambda r: (order.get(r[0], 9), r[1], r[2]))

    print(f"# REFRESH PŘEHLED — {len(sources)} registrovaných zdrojů · dataset {sum(src_counts.values())} záznamů\n")
    tier_tot = Counter()
    tier_recs = Counter()
    cur = None
    for tier, _, host, harvesters, cnt, age in rows:
        if tier != cur:
            cur = tier
            print(f"\n## tier: {tier}")
        tier_tot[tier] += 1
        tier_recs[tier] += cnt
        agestr = ""
        if age is not None:
            flag = " ⚠STALE" if a.stale_days and age > a.stale_days else ""
            agestr = f"  [artefakt {age:.0f}d{flag}]"
        print(f"  {host:28} {cnt:5}  ←  {','.join(harvester_slug(h) for h in harvesters)}{agestr}")
        if a.commands:
            for h in harvesters:
                print(f"        python {h}")

    print("\n# SOUHRN PER TIER (kolik zdrojů / záznamů)")
    for t in sorted(tier_tot, key=lambda x: order.get(x, 9)):
        print(f"  {t:12} {tier_tot[t]:3} zdrojů  {tier_recs[t]:6} záznamů")

    # GAP-CHECK: zdroje v živém datasetu bez dedikovaného `sources:` záznamu. Rozliš:
    #  • family-covered — host JE v platform_map → kryje ho FAMILY harvester (vismo/dsw2/kentico),
    #    re-harvestovatelné, jen ne per-host registrované (OK, ale REFRESH.md to musí pokrýt);
    #  • ORPHAN — slug bez host-matche (h19 nadace batch, ministerstva-slugy) → reprodukce nejistá.
    pm = load_platform_map()
    families = R.get("families") or {}
    gap = {s: n for s, n in src_counts.items() if s and s not in matched_ds}
    if gap:
        covered, orphan = [], []
        for s, n in gap.items():
            plat = (pm.get(s) or {}).get("plat")
            if plat:
                fam = families.get(plat) or {}
                hv = ",".join(harvester_slug(h) for h in (fam.get("harvester") or [])) or "?"
                covered.append((s, n, plat, hv))
            else:
                orphan.append((s, n))
        print(f"\n# GAP — {len(gap)} zdrojů v datasetu bez per-host záznamu v routing.yaml `sources:`")
        if covered:
            print(f"\n  ## family-covered ({len(covered)}) — kryje FAMILY harvester (re-harvestovatelné):")
            for s, n, plat, hv in sorted(covered, key=lambda x: -x[1]):
                print(f"    {s:40} {n:5}  [{plat} → {hv}]")
        if orphan:
            print(f"\n  ## ⚠ ORPHAN ({len(orphan)}) — slug bez host-matche; reprodukce ověř RUČNĚ:")
            for s, n in sorted(orphan, key=lambda x: -x[1]):
                print(f"    {s:40} {n:5}")


if __name__ == "__main__":
    main()
