#!/usr/bin/env python3
"""Deterministické opravy nad data/opportunities.jsonl (po-ingest, před build_app).

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
import argparse
import re, json, os, re, shutil, collections, sys
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
# Když TÝŽ (normalizovaný) titul existuje pod kanonickým zdrojem, kopie je duplicitní → drop.
# (Ostatní .cz varianty nesou DISTINKTNÍ granty — nemažou se; jen agrofert má překryv titulů.)
# 2026-07-31: + mkcr→mk — starý jednorázový h19 batch MK ČR vs nový deterministický
# mk_harvest.py (data z listing tabulek, aktuální ročník); 14/47 titulů se překrývalo.
VARIANT_DEDUP = {"nadace-agrofert.cz": "nadace-agrofert", "mkcr": "mk"}

# Záznamy, které NEJSOU výzva, ale oznámení, JAK ta výzva dopadla.
# =============================================================================
# ⚠ NAMĚŘENO 2026-09-01 v produktu, na katalogu 3 440 záznamů. Jedenáct z nich
# se tvářilo jako výzva, o kterou lze žádat, a přitom to byla oznámení výsledků:
#
#     Výsledky výběrových dotačních řízení na rok 2026
#     Výsledky grantového řízení 2026 | Nadace OKD
#     Vyhlášení výsledků VES 2008 – 2011 na základě rozhodnutí ministra
#     Výsledky stipendijního programu MSPP 2025 (NEWS, NE výzva)
#
# Poslední řádek je ten, který to shrnuje: extrakce SAMA do titulku napsala
# „NE výzva" a záznam přesto vyšel jako `kind=grant`. Anotace bez brány není
# rozhodnutí, je to poznámka.
#
# Škodí to víc, než těch 0,3 % napovídá. Všech jedenáct nemá deadline, takže
# v produktu spadnou mezi průběžné programy — tedy mezi to, co se nabízí jako
# „můžete žádat kdykoli". Kdo klikne na „Výsledky grantového řízení 2026"
# v očekávání, že podá žádost, ztratí důvěru v celý katalog, ne v ten řádek.
#
# ⚠ ROZHODUJE TITULEK, NE TĚLO. Řádná výzva o výsledcích minulých kol běžně
# mluví („výsledky loňského ročníku najdete…"), takže hledat to v textu by
# zahazovalo platné výzvy. Titulek, který ZAČÍNÁ výsledky, je oznámení.
#
# ⚠ PRVNÍ PODOBA PRAVIDLA BYLA PŘEPÁLENÁ. Stálo v ní `^(vyhlášení )?výsledk\w*`,
# což sedne i na „Výsledkem projektu má být studie proveditelnosti" — tedy na
# větu z popisu řádné výzvy. Chytil to test (`tests/test_notacall.py`), který
# zkouší OBĚ strany: co se má chytit i co se chytit nesmí. Pravidlo, které nic
# nepropustí, je stejně špatné jako pravidlo, které nic nechytí.
#
# Proto první pádový tvar, ne kmen: oznámení se jmenují „Výsledky …", kdežto
# „Výsledkem …" je začátek věty o obsahu projektu.
NOT_A_CALL = re.compile(
    r"^\s*výsledky\b"                            # „Výsledky výběrových dotačních řízení…"
    r"|^\s*(vyhlášení|oznámení)\s+výsledk\w*"     # „Vyhlášení výsledků VES…"
    r"|^\s*informace\s+o\s+(ne)?přijetí"          # „Informace o nepřijetí…"
    r"|\(\s*news\s*,\s*ne\s+výzva\s*\)",          # anotace samotné extrakce
    re.IGNORECASE,
)

# KÓD PROGRAMU V TITULKU DOTIS ZÁZNAMU — „Program obnovy venkova (26POVU1)".
# Je to klíč hlubokého odkazu `/grantProgram/:memo`; viz sekce A5 v `main()`.
DOTIS_MEMO = re.compile(r"\(([0-9A-Za-z]{4,12})\)\s*$")

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
    "vlada": "ministerstvo",          # Úřad vlády ČR (vlada.gov.cz) — národní dotace NNO (rady/zmocněnci vlády)
    "opzp": "ministerstvo",           # OP Životní prostředí 2021–2027 (opzp.cz) — EU OP, řídící orgán MŽP
    "opst": "ministerstvo",           # OP Spravedlivá transformace 2021–2027 (opst.cz) — EU OP, řídící orgán MŽP
    "opjak": "ministerstvo",          # OP Jan Amos Komenský 2021–2027 (opjak.cz) — EU OP MŠMT (vzdělávání+výzkum)
    "opd": "ministerstvo",            # OP Doprava 2021–2027 (opd3.opd.cz) — EU OP, řídící orgán MD
    "mk": "ministerstvo",             # Ministerstvo kultury (mk.gov.cz) — dotační řízení (mk_harvest)
    "esfcr": "ministerstvo",          # OPZ+/OPZ (esfcr.cz) — EU OP, řídící orgán MPSV
    "hzs": "ministerstvo",            # HZS ČR (hzscr.gov.cz) — MV, generální ředitelství HZS
    "czechaid": "statni_agentura",    # Česká rozvojová agentura / CzechAid (czechaid.gov.cz)
    "plone_ostrava": "samosprava_obec",  # ostravské městské obvody (sdílený Plone)
    "eu_ft": "evropska_komise",       # EU Funding & Tenders Portal (ec.europa.eu) — centrálně řízené programy EU
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
    "intl_funds": "zahranicni_fond",   # Visegrad Fund + ERSTE Foundation (mezinárodní)
    "interreg": "zahranicni_fond",     # Interreg SK-CZ — přeshraniční program (EFRR)
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
    "nadace_spa": "nadace",           # JS-renderované nadace (Partnerství/OSF/Vodafone/LPR/ČLF/Abakus)
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
    ap.add_argument("--in", dest="inp", default="data/opportunities.jsonl")
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

    # ---- A1) oznámení výsledků nejsou výzvy (viz NOT_A_CALL) ----
    def _oznameni(r):
        return r.get("kind") == "grant" and bool(NOT_A_CALL.search(r.get("title") or ""))

    notcall_dropped = [r for r in recs if _oznameni(r)]
    recs = [r for r in recs if not _oznameni(r)]

    # ---- A5) DOTIS: odkaz na program, ne na rozcestník portálu ----
    #
    # ⚠ NAMĚŘENO 2026-09-02: 148 záznamů (4,3 % katalogu) mělo `source_url`
    # nastavené na `https://dotace.khk.cz/`, tedy na úvodní stránku portálu.
    # Produkt u každé výzvy slibuje odkaz na originál; tenhle ho formálně
    # splňuje a věcně ne — žadatel skončí na rozcestníku a hledá znovu.
    #
    # Hluboký odkaz `/grantProgram/<kód>` existuje (cesta je v SPA bundlu)
    # a kód je v titulku každého záznamu jako `(26POVU1)`. Opravu dělá
    # `ingest_dotis.py` už při sběru; tohle je doplnění pro záznamy, které
    # v katalogu leží z dřívějších běhů — a zároveň pojistka, kdyby se
    # harvester vrátil zpátky.
    dotis_fixed = 0
    for r in recs:
        if (r.get("provenance") or {}).get("platform") != "dotis":
            continue
        src = r.get("source") or ""
        mm = DOTIS_MEMO.search(r.get("title") or "")
        if not src or not mm:
            continue
        deep = f"https://{src}/grantProgram/{mm.group(1)}"
        for field in ("source_url", "source_doc"):
            if (r.get(field) or "").rstrip("/") == f"https://{src}":
                r[field] = deep
                dotis_fixed += 1

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

    # ---- A4) sanitizace polí: amount→int|null, deadline/open_from→ISO|„průběžně"|null,
    #      oprava deadline<open (typo roku). Garantuje typovou čistotu pro status + appku. ----
    CZM = {"ledna": 1, "února": 2, "unora": 2, "března": 3, "brezna": 3, "dubna": 4, "května": 5,
           "kvetna": 5, "června": 6, "cervna": 6, "července": 7, "cervence": 7, "srpna": 8,
           "září": 9, "zari": 9, "října": 10, "rijna": 10, "listopadu": 11, "prosince": 12}
    _AMT_OK = re.compile(r"^[\d  .,]+(\s*(?:Kč|kč|korun)\.?)?$")

    def _coerce_amount(a):
        if isinstance(a, bool) or a is None:
            return None
        if isinstance(a, (int, float)):
            return int(a) if 1000 <= a <= 500_000_000_000 else (int(a) if 0 <= a < 1000 else None)
        if isinstance(a, str) and _AMT_OK.match(a.strip()) and re.search(r"\d", a):
            digits = re.sub(r"\D", "", re.sub(r",\d+$", "", a.strip()))   # tečky/mezery = tisíce; čárka = desetinné
            n = int(digits) if digits else None
            return n if n and 1000 <= n <= 500_000_000_000 else None
        return None  # próza/rozsah/„nestanoveno" → null (nehádáme)

    def _coerce_date(v, year):
        if v is None:
            return None
        s = str(v).strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return s
        if re.sub(r"[^a-zěšč]", "", s.lower()) in ("průběžně", "prubezne", "rolling", "průběžne"):
            return "průběžně"
        cur = bool(re.search(r"aktu[áa]ln[íi]ho|b[ěe][žz]n[ée]ho", s, re.I))  # „aktuálního/běžného roku" = letošek
        m = re.match(r"(\d{1,2})\.\s*([A-Za-zÁ-ž]+)", s)
        if m and m.group(2).lower() in CZM and cur:
            return f"{year}-{CZM[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
        m = re.match(r"(\d{1,2})\.\s*(\d{1,2})\.", s)
        if m and cur and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(1)) <= 31:
            return f"{year}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        return None  # neparsovatelné/nejednoznačné → null (status unknown, ne špatné datum)

    san = collections.Counter()
    for r in recs:
        a0 = r.get("amount")
        a1 = _coerce_amount(a0)
        if a1 != a0:
            r["amount"] = a1
            san["amount"] += 1
        for f in ("open_from", "deadline"):
            d0 = r.get(f)
            d1 = _coerce_date(d0, today.year)
            if d1 != d0:
                r[f] = d1
                san["date"] += 1
        of, dl = r.get("open_from"), r.get("deadline")
        if of and dl and re.fullmatch(r"\d{4}-\d{2}-\d{2}", of) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", dl) and dl < of:
            bumped = f"{int(dl[:4]) + 1}{dl[4:]}"   # deadline < open = typo roku → +1
            from datetime import date as _d
            try:
                if of <= bumped and (_d.fromisoformat(bumped) - _d.fromisoformat(of)).days <= 550:
                    r["deadline"] = bumped
                else:
                    r["deadline"] = None
                san["deadline_fix"] += 1
            except Exception:
                r["deadline"] = None

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
    if notcall_dropped:
        print(f"\n=== A1) oznámení výsledků (ne výzvy): −{len(notcall_dropped)} ===")
        for r in notcall_dropped:
            print(f"  −  {(r.get('source') or '?')[:24]:24}  {(r.get('title') or '')[:64]}")
    if dotis_fixed:
        print(f"\n=== A5) DOTIS hluboký odkaz: {dotis_fixed} polí opraveno z rozcestníku na /grantProgram/<kód> ===")
    if variant_dropped:
        print("\n=== A2) variant dedup (.cz apify kopie) ===")
        for s, c in collections.Counter(r.get("source") for r in variant_dropped).most_common():
            print(f"  DROP {s}: {c} (duplicitní titul existuje pod bohatším bare-slug)")
    if resnapshot_dropped:
        print(f"\n=== A3) dedup re-snapshotů (stejný source+titul+deadline): −{len(resnapshot_dropped)} ===")
        for s, c in collections.Counter(r.get("source") for r in resnapshot_dropped).most_common(10):
            print(f"  −{c:3}  {s}")
    if san:
        print(f"\n=== A4) sanitizace: amount→int|null {san['amount']}× · date→ISO|průběžně|null "
              f"{san['date']}× · deadline<open oprava {san['deadline_fix']}× ===")
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
