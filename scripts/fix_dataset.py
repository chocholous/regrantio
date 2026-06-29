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
import argparse, json, os, shutil, collections, sys
from datetime import date
if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí →·⚠ v diagnostice → vynuť UTF-8 (no-op jinde)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opportunities import compute_status  # kanonický výpočet statusu (sdílený s pipeline)

# Zdroj, jehož KAŽDÝ záznam je duplicitní/nekonzistentní kopií jiného zdroje → smazat.
DROP_SOURCES = {
    "dotace.usti.cz",                      # = duplicitní Ústí (kind=program fonds + ne-extrahované appeals)
    "tacr.dsw2.otevrenamesta.cz",          # TEST/demo instance dsw2 (titulky kódy „PP1/TK01", deadliny 2021);
                                           # reálné TA ČR máme pod zdrojem „tacr" (9 veřejných soutěží)
}

# Varianta poskytovatele sklizená 2× (bohatší extract_wf pod bare-slug vs chudší apify pod <slug>.cz).
# Když TÝŽ (normalizovaný) titul existuje pod bare-slug, .cz kopie je duplicitní → drop.
# (Ostatní .cz varianty nesou DISTINKTNÍ granty — nemažou se; jen agrofert má překryv titulů.)
VARIANT_DEDUP = {"nadace-agrofert.cz": "nadace-agrofert"}

# Konkrétní stray/mis-filed záznamy (nesprávný zdroj nebo ne-grant) → drop pro čistotu.
DROP_STRAY = [
    # ČMZRB / Národní rozvojová banka = úvěry/záruky (ne dotace), navíc omylem jako mise pod mkcr.
    lambda r: r.get("source") == "mkcr" and "MZRB" in (r.get("name") or "").upper(),
]

# Ruční mapa zdroj→typ poskytovatele pro all-null zdroje (ověřeno z titulků/URL záznamů).
# slovník hodnot = canon facet vocab (ministerstvo / statni_fond / nadace / firemni_nadace / nadacni_fond).
PROVIDER_TYPE = {
    # ministerstva (gov.cz portály)
    "mzp": "ministerstvo",            # Ministerstvo životního prostředí (mzp.gov.cz)
    "eagri": "ministerstvo",          # Ministerstvo zemědělství (mze.gov.cz)
    "mpsv": "ministerstvo",           # Ministerstvo práce a sociálních věcí (mpsv.gov.cz)
    "mpo": "ministerstvo",            # Ministerstvo průmyslu a obchodu (mpo.gov.cz) — národní programy
    "mmr": "ministerstvo",            # Ministerstvo pro místní rozvoj (mmr.gov.cz) — národní dotace
    "opzp": "ministerstvo",           # OP Životní prostředí 2021–2027 (opzp.cz) — EU OP, řídící orgán MŽP
    "opst": "ministerstvo",           # OP Spravedlivá transformace 2021–2027 (opst.cz) — EU OP, řídící orgán MŽP
    "opjak": "ministerstvo",          # OP Jan Amos Komenský 2021–2027 (opjak.cz) — EU OP MŠMT (vzdělávání+výzkum)
    # státní fondy
    "vinarskyfond": "statni_fond",    # Vinařský fond
    "sfa": "statni_fond",             # Státní fond audiovize (sfa.gov.cz)
    "sfzp": "statni_fond",            # Státní fond životního prostředí (sfzp.gov.cz)
    "sfpi": "statni_fond",            # Státní fond podpory investic / SFRB (sfpi.cz) — bydlení
    "sfdi": "statni_fond",            # Státní fond dopravní infrastruktury (sfdi.gov.cz) — doprava
    "sfk": "statni_fond",             # Státní fond kultury ČR (na mk.gov.cz) — kultura
    # státní grantové agentury (účelová podpora výzkumu)
    "gacr": "statni_agentura",        # Grantová agentura ČR (gacr.cz) — základní výzkum
    "tacr": "statni_agentura",        # Technologická agentura ČR (tacr.gov.cz) — aplikovaný výzkum
    "nsa": "statni_agentura",         # Národní sportovní agentura (nsa.gov.cz) — dotace do sportu
    # zahraniční / mezinárodní donorské fondy
    "eeagrants": "zahranicni_fond",   # EHP a Norské fondy (eeagrants.cz; NKM = Ministerstvo financí)
    # nadace
    "nadacevia": "nadace",            # Nadace Via
    "osf": "nadace",                  # Nadace OSF (Open Society Fund Praha)
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
    ap.add_argument("--today", default=date.today().isoformat(), help="práh pro výpočet statusu (default dnešek)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = date.fromisoformat(a.today)

    recs = load(a.inp)
    n0 = len(recs)
    src0 = len({r.get("source") for r in recs})

    # ---- A) DROP duplicitních zdrojů + stray ----
    dropped = [r for r in recs if r.get("source") in DROP_SOURCES]
    recs = [r for r in recs if r.get("source") not in DROP_SOURCES]
    stray_dropped = [r for r in recs if any(f(r) for f in DROP_STRAY)]
    recs = [r for r in recs if not any(f(r) for f in DROP_STRAY)]

    # ---- A2) variant dedup (agrofert: .cz apify kopie překrývající bohatší bare-slug) ----
    def ntitle(r):
        return "".join((r.get("title") or "").lower().split())
    variant_dropped = []
    for cz, bare in VARIANT_DEDUP.items():
        bare_titles = {ntitle(r) for r in recs if r.get("source") == bare and r.get("title")}
        keep = []
        for r in recs:
            if r.get("source") == cz and ntitle(r) in bare_titles:
                variant_dropped.append(r)
            else:
                keep.append(r)
        recs = keep

    # ---- A3) dedup re-snapshotů: stejný (source, title, deadline) = redundantní (program/výzva
    #      harvestovaná opakovaně — typicky katalog DSW2/QCM přes ročníky, BEZ odlišného deadline).
    #      Necháme NEJBOHATŠÍ kopii (částka > délka popisu > délka titulku). Záznamy s ODLIŠNÝM
    #      deadlinem (skutečně různé ročníky výzvy) zůstávají — liší se klíčem. ----
    def _rich(r):
        return (1 if r.get("amount") else 0, len(r.get("focus_area") or ""), len(r.get("title") or ""))
    _groups = collections.OrderedDict()
    for r in recs:
        _groups.setdefault((r.get("source"), ntitle(r), r.get("deadline")), []).append(r)
    resnapshot_dropped, _kept = [], []
    for (_src, _nt, _dl), grp in _groups.items():
        if len(grp) > 1 and _nt:                      # _nt neprázdný titulek → kolaps re-snapshotů
            best = max(grp, key=_rich)
            _kept.append(best)
            resnapshot_dropped += [r for r in grp if r is not best]
        else:
            _kept.extend(grp)
    recs = _kept

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

    # ---- C) přepočet statusu k dnešku (status v KÓDU, ne LLM) ----
    # jen kind=grant; foundation_mission nemá časový status (zůstává None).
    transitions = collections.Counter()
    st_before = collections.Counter(r.get("status") for r in recs)
    for r in recs:
        if r.get("kind") != "grant":
            continue
        old = r.get("status")
        new, conf = compute_status(r.get("open_from"), r.get("deadline"), today)
        if new != old:
            transitions[f"{old}→{new}"] += 1
        r["status"], r["status_confidence"] = new, conf
    st_after = collections.Counter(r.get("status") for r in recs)

    # ---- D) doplnění region.kraj (samospráva) + celostátní (národní zdroje) ----
    # Filtr „dle kraje" v produktu vyžaduje vyplněný kraj. Samosprávě doplníme kraj z HOSTU
    # (naučeno majoritou z ne-null záznamů + ruční override pro all-null hosty); národní
    # poskytovatele (ministerstva/fondy/agentury/nadace) označíme celostatni=true (ne „neuvedeno").
    NATIONAL = {"ministerstvo", "statni_fond", "statni_agentura", "nadace", "firemni_nadace", "nadacni_fond", "zahranicni_fond"}
    SOURCE_KRAJ_MANUAL = {"loket.dsw2.otevrenamesta.cz": "Karlovarský kraj"}  # all-null host → ruční
    cnt = collections.defaultdict(collections.Counter)
    for r in recs:
        f = r.get("facets") or {}
        if f.get("typ_poskytovatele") in ("samosprava_kraj", "samosprava_obec"):
            k = (f.get("region") or {}).get("kraj")
            if k:
                cnt[r.get("source")][k] += 1
    learned_kraj = {h: c.most_common(1)[0][0] for h, c in cnt.items()}
    learned_kraj.update(SOURCE_KRAJ_MANUAL)
    kraj_filled = celost_filled = 0
    for r in recs:
        if r.get("kind") != "grant":
            continue
        f = r.setdefault("facets", {}) or {}
        r["facets"] = f
        reg = f.get("region")
        if not isinstance(reg, dict):
            reg = {"nazev": None, "obec": None, "okres": None, "kraj": None, "celostatni": False, "_conf": "low"}
            f["region"] = reg
        if reg.get("kraj"):
            continue
        pt = f.get("typ_poskytovatele")
        src = r.get("source")
        if pt in ("samosprava_kraj", "samosprava_obec") and src in learned_kraj:
            reg["kraj"] = learned_kraj[src]
            reg["_conf"] = reg.get("_conf") or "high"
            kraj_filled += 1
        elif pt in NATIONAL and not reg.get("celostatni"):
            reg["celostatni"] = True
            celost_filled += 1

    # ---- report ----
    print("=== A) ÚSTÍ / duplicitní zdroje ===")
    dd = collections.Counter(r.get("source") for r in dropped)
    for s, c in dd.most_common():
        print(f"  DROP {s}: {c} záznamů")
    print(f"  celkem smazáno: {len(dropped)}")
    if variant_dropped:
        print("\n=== A2) variant dedup (.cz apify kopie) ===")
        for s, c in collections.Counter(r.get("source") for r in variant_dropped).most_common():
            print(f"  DROP {s}: {c} (duplicitní titul existuje pod bohatším bare-slug)")
    if resnapshot_dropped:
        print(f"\n=== A3) dedup re-snapshotů (stejný source+titul+deadline): −{len(resnapshot_dropped)} ===")
        for s, c in collections.Counter(r.get("source") for r in resnapshot_dropped).most_common(10):
            print(f"  −{c:3}  {s}")
    print("\n=== B) reclasifikace typ_poskytovatele=null ===")
    for k, c in sorted(filled.items()):
        print(f"  +{c:3}  {k}")
    print(f"  celkem doplněno: {sum(filled.values())}")
    if unresolved:
        print("  ⚠ NEVYŘEŠENO (chybí v mapě i v majoritě):")
        for s, c in unresolved.most_common():
            print(f"      {s}: {c}")

    print(f"\n=== C) přepočet statusu k {today.isoformat()} ===")
    for k, c in sorted(transitions.items(), key=lambda x: -x[1]):
        print(f"  {k}: {c}")
    print(f"  před:  " + " · ".join(f"{k}={v}" for k, v in st_before.most_common()))
    print(f"  po:    " + " · ".join(f"{k}={v}" for k, v in st_after.most_common()))

    print(f"\n=== D) region.kraj ===")
    print(f"  samospráva kraj doplněn z hostu: +{kraj_filled} · národní celostatni=true: +{celost_filled}")

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
