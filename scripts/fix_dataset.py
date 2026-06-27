#!/usr/bin/env python3
"""Deterministické opravy nad data/opportunities_v2.jsonl (po-ingest, před build_app).

Dvě nezávislé opravy, obě plně data-driven a idempotentní (lze pustit opakovaně):

A) ÚSTÍ DEDUP — Ústí nad Labem byl sklizen DVAKRÁT pod dvěma hostnames téže DSW2 instance:
     • dotace.usti-nad-labem.cz : 105 fonds + 2 appeals, VŠE kind=grant, přes extract_wf (bohatší)
                                  → SHODNÉ s reprezentací VŠECH ostatních DSW2 měst (fonds i appeals = grant)
     • dotace.usti.cz           : 105 fonds jako kind=PROGRAM (jediné program-záznamy v celém datasetu)
                                  + 2 appeals bez extract_wf (chudší, amount=null tam kde druhý má 30000)
   Stejné pid (pid448…) v obou; appeals mají identické tituly/deadliny. usti.cz je tedy duplicitní
   a nekonzistentní kopie → DROP celá usti.cz (107 záznamů). Zůstává jeden poskytovatel, 107 záznamů,
   konzistentní se sourozenci, a zmizí anomální kind=program.

B) RECLASIFIKACE typ_poskytovatele=null — facet_wf (LLM) nechal u 195 záznamů poskytovatele null,
   včetně reálných ministerstev (mzp, eagri) a státního fondu (vinarskyfond, sfa) → sektorové rollupy
   v appce je podhodnocují / míchají do „neuvedeno". Oprava: kanonická mapa zdroj→typ. Pro každý zdroj
   buď (1) ruční override z níže uvedené tabulky (autoritativní pro all-null zdroje), nebo (2) doplnění
   z většinové NE-null hodnoty téhož zdroje (kellner→firemni_nadace, mkcr→ministerstvo, …). Nemění žádnou
   existující ne-null hodnotu.

Spuštění z kořene repa:
   python3 scripts/fix_dataset.py            # in-place, vytvoří .bak
   python3 scripts/fix_dataset.py --dry-run  # jen report
"""
import argparse, json, os, shutil, collections

# Zdroj, jehož KAŽDÝ záznam je duplicitní/nekonzistentní kopií jiného zdroje → smazat.
DROP_SOURCES = {"dotace.usti.cz"}  # = duplicitní Ústí (kind=program fonds + ne-extrahované appeals)

# Ruční mapa zdroj→typ poskytovatele pro all-null zdroje (ověřeno z titulků/URL záznamů).
# slovník hodnot = canon facet vocab (ministerstvo / statni_fond / nadace / firemni_nadace / nadacni_fond).
PROVIDER_TYPE = {
    # ministerstva (gov.cz portály)
    "mzp": "ministerstvo",            # Ministerstvo životního prostředí (mzp.gov.cz)
    "eagri": "ministerstvo",          # Ministerstvo zemědělství (mze.gov.cz)
    # státní fondy
    "vinarskyfond": "statni_fond",    # Vinařský fond
    "sfa": "statni_fond",             # Státní fond audiovize (sfa.gov.cz)
    # nadace
    "nadacevia": "nadace",            # Nadace Via
    "partnerstvi": "nadace",          # Nadace Partnerství
    "leontinka": "nadace",            # Nadace Leontinka
    "veronica": "nadace",             # Nadace Veronica
    "sirius": "nadace",               # Nadace Sirius
    "nadace_adra": "nadace",          # Nadace ADRA
    "hlavka": "nadace",               # Nadání Josefa, Marie a Zdeňky Hlávkových
    "nadacetm": "nadace",             # Nadace Terezy Maxové dětem
    "voracek": "nadace",              # Nadace Jakuba Voráčka
    # firemní nadace / nadační fondy
    "nadacecs": "firemni_nadace",     # Nadace České spořitelny
    "albert": "firemni_nadace",       # Nadační fond Albert (Ahold)
    "kontobariery": "nadacni_fond",   # Konto Bariéry (Nadace Charty 77)
}


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def majority_types(recs):
    """zdroj → většinová NE-null hodnota typ_poskytovatele (pro doplnění zbylých nullů)."""
    by = collections.defaultdict(collections.Counter)
    for r in recs:
        t = (r.get("facets") or {}).get("typ_poskytovatele")
        if t:
            by[r.get("source")][t] += 1
    return {s: c.most_common(1)[0][0] for s, c in by.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/opportunities_v2.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    recs = load(a.inp)
    n0 = len(recs)
    src0 = len({r.get("source") for r in recs})

    # ---- A) DROP duplicitních zdrojů ----
    dropped = [r for r in recs if r.get("source") in DROP_SOURCES]
    recs = [r for r in recs if r.get("source") not in DROP_SOURCES]

    # ---- B) reclasifikace typ_poskytovatele=null ----
    maj = majority_types(recs)
    filled = collections.Counter()
    unresolved = collections.Counter()
    for r in recs:
        f = r.setdefault("facets", {}) or {}
        r["facets"] = f
        if f.get("typ_poskytovatele"):
            continue
        s = r.get("source")
        t = PROVIDER_TYPE.get(s) or maj.get(s)
        if t:
            f["typ_poskytovatele"] = t
            filled[f"{s}→{t}"] += 1
        else:
            unresolved[s] += 1

    # ---- report ----
    print("=== A) ÚSTÍ / duplicitní zdroje ===")
    dd = collections.Counter(r.get("source") for r in dropped)
    for s, c in dd.most_common():
        print(f"  DROP {s}: {c} záznamů")
    print(f"  celkem smazáno: {len(dropped)}")
    print("\n=== B) reclasifikace typ_poskytovatele=null ===")
    for k, c in sorted(filled.items()):
        print(f"  +{c:3}  {k}")
    print(f"  celkem doplněno: {sum(filled.values())}")
    if unresolved:
        print("  ⚠ NEVYŘEŠENO (chybí v mapě i v majoritě):")
        for s, c in unresolved.most_common():
            print(f"      {s}: {c}")

    nulls_after = sum(1 for r in recs if not (r.get("facets") or {}).get("typ_poskytovatele"))
    print("\n=== souhrn ===")
    print(f"  záznamů: {n0} → {len(recs)}  (−{n0-len(recs)})")
    print(f"  poskytovatelů: {src0} → {len({r.get('source') for r in recs})}")
    print(f"  zbývající null typ_poskytovatele: {nulls_after}")

    if a.dry_run:
        print("\n(dry-run: nic nezapsáno)")
        return
    shutil.copy2(a.inp, a.inp + ".bak")
    with open(a.inp, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nzapsáno → {a.inp}  (záloha {a.inp}.bak)")


if __name__ == "__main__":
    main()
