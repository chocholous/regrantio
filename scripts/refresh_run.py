#!/usr/bin/env python3
"""refresh_run.py — JEDEN PŘÍKAZ, kterým se katalog skutečně obnoví.

`refresh.py` je checklist: řekne, CO by se dalo obnovit. Tenhle skript to UDĚLÁ —
pro zdroje, které to zvládnou bez jazykového modelu.

    python scripts/refresh_run.py --list          # co je v registru a čím se obnoví
    python scripts/refresh_run.py                 # obnov vše deterministické + tail
    python scripts/refresh_run.py --tier structured
    python scripts/refresh_run.py --tier extract   # deterministická vrstva 2 (21 zdrojů)
    python scripts/refresh_run.py --tier all       # obojí = všech 35 zdrojů bez modelu
    python scripts/refresh_run.py --only dotace.khk.cz,fondvysociny.cz
    python scripts/refresh_run.py --tail-only     # jen přepočet + export (bez sítě)
    python scripts/refresh_run.py --publish-db    # a rovnou zapiš do databáze produktu
    python scripts/refresh_run.py --dry-run       # ukaž příkazy, nic nespouštěj

TŘI TŘÍDY ZDROJŮ, a rozdíl je zásadní
─────────────────────────────────────
  A) strukturní    harvest → ingest_kraj/dotis/… Celá cesta je kód. 14 zdrojů,
                   běží ve výchozím `refresh_run.py`.
  B) deterministická vrstva 2
                   harvest → build_extract_input → `scripts/extractors/<slug>.py`
                   → ingest_rich. **TAKY BEZ MODELU** — ten extraktor je obyčejný
                   parser. 14 zdrojů; bere se výslovně `--tier extract`.
  C) modelové      harvest → build_extract_input → extract_wf.js (LLM) → ingest_rich.
                   Vyžaduje běh workflow uvnitř Claude Code, takže to není věc
                   cronu ani tohohle skriptu. Viz README a docs/REFRESH.md.

⚠ TŘÍDA B TU DO 2026-09-03 CHYBĚLA a skript o sobě kvůli tomu tvrdil nepravdu:
`--list` hlásil 14 obnovitelných zdrojů, přitom jich je 28. Zbylých 14 mělo
hotový harvester i deterministický parser a čekalo na modelovou vrstvu, kterou
vůbec nepotřebují.

⚠ A POZOR NA DRUHOU CHYBU, DO KTERÉ SE PŘITOM DÁ SPADNOUT. Souborů
`scripts/extractors/<slug>.py` je 42, ale jen 15 z nich vstup opravdu ČTE; zbytek má
data natvrdo (viz `TRANSCRIBED` níž). Počítat je všechny jako obnovitelné
znamená vyrobit běh, který se tváří jako obnova a nic neobnoví.

⚠ NOVÉ VÝZVY U TŘÍDY C TENHLE SKRIPT NEPŘINESE. Přinese je u tříd A a B
a u VŠECH srovná termíny a status k dnešku — což je ta část
zastarávání, která se děje sama od sebe každý den, i když nikdo nic nepublikoval.

⚠ JEDEN ZDROJ NESMÍ SHODIT CELÝ BĚH. Weby krajů padají, mění se a jsou pomalé.
Chyba se zaznamená, pokračuje se dál a shrnutí na konci ji přizná; návratový kód
je nenulový, aby si toho všiml i plánovač.

⚠ TAIL BĚŽÍ VŽDYCKY, i když všechny harvesty selžou. Přepočet statusu na síti
nezávisí a je to to nejlevnější, co se dá pro čerstvost udělat.
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr:
        sys.stderr.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

# -----------------------------------------------------------------------------
# REGISTR DETERMINISTICKÝCH ZDROJŮ
# -----------------------------------------------------------------------------
# host → (harvest argumenty, výstupní soubor, ingest argumenty, tier)
#
# Tier je jen VÝBĚROVÉ KRITÉRIUM, ne jiný postup: `structured` = JSON/REST API
# (rychlé, odolné), `html` = parsování stránek (levné, ale citlivé na redesign).
#
# Výstupní soubor je ZÁMĚRNĚ tentýž, jaký má harvester jako default: kdo pustí
# harvester ručně, dostane totéž co tenhle skript a ingest se nespleje.
SOURCES = {
    "dotace.khk.cz": (
        ["dotis_harvest.py", "--web", "https://dotace.khk.cz", "--source", "dotace.khk.cz",
         "--out", "data/h_dotis_khk.json"],
        "data/h_dotis_khk.json",
        ["ingest_dotis.py", "data/h_dotis_khk.json", "--kraj", "Královéhradecký kraj"],
        "structured",
    ),
    "fondvysociny.cz": (
        ["fondvysociny_harvest.py"], "data/h_fondvysociny.json",
        ["ingest_fondvysociny.py", "data/h_fondvysociny.json"],
        "html",
    ),
    "dotace.kraj-lbc.cz": (
        ["liberecky_harvest.py"], "data/h_kraj_liberecky.json",
        ["ingest_kraj.py", "data/h_kraj_liberecky.json"],
        "html",
    ),
    "dotace.pardubickykraj.cz": (
        ["pardubicky_harvest.py"], "data/h_kraj_pardubicky.json",
        ["ingest_kraj.py", "data/h_kraj_pardubicky.json"],
        "html",
    ),
    "kr-ustecky.cz": (
        ["ustecky_harvest.py"], "data/h_kraj_ustecky.json",
        ["ingest_kraj.py", "data/h_kraj_ustecky.json"],
        "html",
    ),
    "msk.cz": (
        ["msk_harvest.py"], "data/h_kraj_msk.json",
        ["ingest_kraj.py", "data/h_kraj_msk.json"],
        "html",
    ),
    "stredoceskykraj.cz": (
        ["stredocesky_harvest.py"], "data/h_kraj_stredocesky.json",
        ["ingest_kraj.py", "data/h_kraj_stredocesky.json"],
        "html",
    ),
    "kr-karlovarsky.cz": (
        ["karlovarsky_harvest.py"], "data/h_kraj_karlovarsky.json",
        ["ingest_kraj.py", "data/h_kraj_karlovarsky.json"],
        "html",
    ),
    "kr-jihomoravsky.cz": (
        ["jm_harvest.py"], "data/h_kraj_jm.json",
        ["ingest_kraj.py", "data/h_kraj_jm.json"],
        "html",
    ),
    "kraj-jihocesky.cz": (
        ["jihocesky_harvest.py"], "data/h_kraj_jihocesky.json",
        ["ingest_kraj.py", "data/h_kraj_jihocesky.json"],
        "html",
    ),
    "olkraj.cz": (
        ["olomoucky_harvest.py"], "data/h_kraj_olomoucky.json",
        ["ingest_kraj.py", "data/h_kraj_olomoucky.json"],
        "html",
    ),
    "zlinskykraj.cz": (
        ["zlinsky_harvest.py"], "data/h_kraj_zlinsky.json",
        ["ingest_kraj.py", "data/h_kraj_zlinsky.json"],
        "html",
    ),
    "praha.eu": (
        ["praha_harvest.py"], "data/h_kraj_praha.json",
        ["ingest_kraj.py", "data/h_kraj_praha.json"],
        "html",
    ),
    # ⚠ Brno je „mesto", ne „kraj" — jméno souboru se od ostatních liší.
    "dotace.brno.cz": (
        ["brno_harvest.py"], "data/h_mesto_brno.json",
        ["ingest_kraj.py", "data/h_mesto_brno.json"],
        "html",
    ),
}

# -----------------------------------------------------------------------------
# TŘETÍ TŘÍDA: HARVEST → DETERMINISTICKÝ EXTRAKTOR → ingest_rich
# -----------------------------------------------------------------------------
# ⚠ TAHLE TŘÍDA V REGISTRU CHYBĚLA A REPOZITÁŘ KVŮLI TOMU O SOBĚ TVRDIL NEPRAVDU.
#
# Do 2026-09-03 se svět dělil na „deterministické" (14 zdrojů výš) a „modelové"
# (všechno ostatní). Naměřeno: existuje **42** extraktorů, z toho **38** má i
# vlastní harvester. JEN 15 Z NICH ALE ČTE VSTUP — zbytek má data natvrdo
# a do registru nepatří (viz `TRANSCRIBED`). Mají v `data/`
# vlastní extraktor `scripts/extractors/<slug>.py` — a ten NENÍ model. Jsou to obyčejné
# parsery: „harvester už rozparsoval datum vyhlášení a datum ukončení příjmu,
# takže se tu nic nehádá" (hlavička `scripts/extractors/opd.py`).
#
# Po odečtení přepsaných zbývá 14 zdrojů, které jdou obnovit jedním příkazem už
# dnes, bez klíče k modelu — a nikdo o tom nevěděl, protože `--list` hlásil 14
# a tyhle mezi nimi nebyly.
#
# Ověřeno živě 2026-09-03 na `opd`: harvest 12 výzev → extrakce 12 → ingest 12,
# nula účasti modelu.
#
# CESTY SE NEOPISUJÍ, ODVOZUJÍ SE. Konvence je popsaná v `docs/REFRESH.md` §1–4:
#     harvest    → data/<slug>_documents.jsonl
#     vstup      → data/<slug>_in/
#     extraktor  → scripts/extractors/<slug>.py
#     výstup     → data/<slug>_out/
# Registr proto drží jen to, co se odvodit nedá: čím se harvestuje a jaký je tier.
#
# ⚠ VE VÝCHOZÍM BĚHU SE NESPOUŠTÍ. Je to 14 webů, tedy dlouhý běh po síti, a
# hlavně: každý z nich je ověřený jen do té míry, do jaké se pustil. Bere se
# výslovně — `--tier extract` nebo `--only <slug>` — dokud nebude odbytý celý.
def cte_vstup(slug):
    """Je `scripts/extractors/<slug>.py` PARSER, nebo přepis dat do literálů?

    ⚠ JEDINÁ DEFINICE. Ptá se na to registr, test i dokumentace — kdyby si
    každý nesl vlastní vzor, rozejdou se a jeden z nich začne tiše lhát.

    ⚠ PRVNÍ PODOBA TOHOHLE PRAVIDLA BYLA ŠPATNĚ a stálo to šest zdrojů.
    Hledala jen čtení ze složky `data/<slug>_in/`, jenže část extraktorů čte
    rovnou harvest (`data/<slug>_documents.jsonl`) a složku `_in` nepotřebuje.
    `opzp`, `opst`, `nsa`, `tacr`, `opjak` a `eeagrants` jsou plnohodnotné
    parsery — 272 záznamů — a byly vyřazené jako přepisy.

    Ptá se proto na to, co je podstatné: SÁHNE TEN SOUBOR NA NĚJAKÝ VSTUP?
    """
    p = os.path.join(ROOT, "scripts", "extractors", f"{slug}.py")
    if not os.path.exists(p):
        return False
    src = open(p, encoding="utf-8").read()
    # ⚠ HLEDÁ SE OTEVŘENÍ KONKRÉTNÍ CESTY, ne „čte a někde zmiňuje vstup".
    #
    # Volnější podoba pravidla se zkoušela a byla HORŠÍ: přepsané extraktory
    # svou vstupní složku běžně zmiňují (`shutil.copyfile("data/x_in/…")`),
    # takže se jich jedenáct začalo tvářit jako parsery. Přesnost je tu
    # důležitější než pohodlí — od toho pravidlo je.
    #
    # Cenou je, že extraktor musí cestu otevřít PŘÍMO, ne přes konstantu.
    # Je to konvence celého `data/`, ne omezení: všech 43 souborů ji drží.
    return bool(re.search(
        r"open\s*\(\s*[^)]*(_documents\.jsonl|_in/|_in\"|_in'|\.jsonl)"
        r"|json\.load\s*\(\s*open"
        r"|glob\.glob"
        r"|os\.listdir"
        r"|for\s+line\s+in\s+open",
        src,
    ))


EXTRACT_SOURCES = {
    # slug → (argumenty harvestu, tier)
    #
    # Roční filtry mají SMYSLUPLNÉ VÝCHOZÍ HODNOTY (`gacr --since` = dnes−300 dní,
    # `nsa --year` = letošek), takže holé spuštění bere aktuální cyklus, ne archiv.
    #
    # ⚠ `--seeds` NENÍ VOLITELNÝ. Osm harvesterů ho má jako POVINNÝ argument a bez
    # něj skončí kódem 2. Naměřeno 2026-09-03: takhle padlo 8 z 38 zdrojů, a nebyla
    # to chyba webu ani parseru — jen nikde nestálo, čím se ten skript krmí.
    # Soubory se seznamem URL jsou proto od téhož data sledované v gitu
    # (`.gitignore` výjimka 3).
    "czechaid": (["czechaid_harvest.py"], "html"),
    "esfcr": (["esfcr_harvest.py"], "html"),
    "eeagrants": (["eeagrants.py"], "html"),
    "eu_ft": (["eu_ft.py"], "structured"),
    "hzs": (["hzs_harvest.py"], "html"),
    "interreg": (["interreg.py"], "structured"),
    "intl_funds": (["intl_funds.py"], "html"),
    "mk": (["mk_harvest.py"], "html"),
    "msmt": (["msmt_harvest.py"], "html"),
    "nadace_spa": (["nadace_spa.py"], "html"),
    "nsa": (["nsa.py"], "structured"),
    "nadacevia": (["nadacevia.py"], "html"),
    "opd": (["opd.py"], "html"),
    "opjak": (["opjak.py"], "html"),
    "opst": (["opst.py"], "html"),
    "optak": (["harvest_site.py", "--base", "https://optak.gov.cz", "--source", "optak",
               "--out", "data/optak_documents.jsonl"], "html"),
    "opzp": (["opzp.py"], "html"),
    "osf": (["osf.py"], "html"),
    "plone_ostrava": (["plone_ostrava.py"], "html"),
    "tacr": (["tacr.py"], "structured"),
    "vlada": (["vlada.py"], "html"),
    # ⚠ BEZ VLASTNÍHO HARVESTERU. Extraktor v `data/` mají, sběrač ne — dostaly
    # se do katalogu jinou cestou (jednorázové běhy 2026-06). Zaregistrované
    # nejsou schválně: registr má říkat, co JDE pustit.
    #   mzcr (83 záznamů) · mzp (16) · mv (7) · nadacecs (2)
    #
    # ⚠ `mzcr` je přitom PLNOHODNOTNÝ PARSER (čte `data/mzcr_in/`) — chybí mu
    # jen sběrač. Nepatří tedy mezi přepsané; je to jediný zdroj, u kterého
    # stačí dopsat harvester a rovnou se zaregistruje.
}

# -----------------------------------------------------------------------------
# ⚠ EXTRAKTOR, KTERÝ NIC NEEXTRAHUJE — 27 souborů, a do registru NEPATŘÍ
# -----------------------------------------------------------------------------
# Naměřeno 2026-09-03: z 42 souborů `scripts/extractors/<slug>.py` jich jen **15**
# skutečně čte vstup (`json.load(open(... _in/ ...))`). Zbylých 27 má výsledek
# NAPSANÝ NATVRDO v kódu — jsou to přepisy jedné extrakce z 2026-06/07 do
# pythonních literálů, ne parsery.
#
# Vypadají ale úplně stejně: mají hlavičku, spustí se, vytisknou „wrote N grants"
# a skončí nulou. Kdo je pustí jako obnovu, dostane:
#   1. skutečný harvest po síti (stránka se opravdu stáhne),
#   2. přepis červnových dat přes cokoli čerstvějšího v katalogu,
#   3. hlášení „✓ ingest" a nulový návratový kód.
# Tedy běh, který se tváří jako obnova, data nezmění a ještě je orazítkuje jako
# ověřená. To je horší než zdroj, který se vůbec nepustí.
#
# STALO SE TO. První běh `--tier extract` orazítkoval 350 záznamů z těchhle
# zdrojů dnešním `fetched_at`; razítka byla odebrána a zdroje vyřazeny.
#
# Cesta ven je pro ně TÁŽ jako pro třídu C: modelová vrstva. Držet je tu jako
# seznam má smysl proto, aby je příště nikdo znovu „nenašel" jako hotové.
TRANSCRIBED = (
    "albert", "eagri", "gacr", "hlavka", "leontinka", "mmr", "mpo",
    "mpsv", "mv", "mzp", "nadace_adra", "nadacecs", "partnerstvi", "sfa", "sfdi", "sfk", "sfpi", "sfzp",
    "sirius", "veronica", "vinarskyfond",
)


def extract_chain(slug, harvest, today):
    """Čtyři kroky deterministické vrstvy 2 pro jeden zdroj (docs/REFRESH.md §1–4)."""
    docs = f"data/{slug}_documents.jsonl"
    return [
        (harvest, "harvest"),
        (["build_extract_input.py", docs, "--source", slug,
          "--out-dir", f"data/{slug}_in", "--force-type", "grant"], "příprava vstupu"),
        ([f"scripts/extractors/{slug}.py"], "extrakce (bez modelu)"),
        (["ingest_rich.py", "--out-dir", f"data/{slug}_out", "--src", f"data/{slug}_in",
          "--existing", "data/opportunities.jsonl", "--out", "data/opportunities.jsonl",
          "--harvest-file", docs, "--today", today], "ingest"),
    ]


# Přepočet a export. Na síti nezávisí, takže běží i po neúspěšném harvestu.
TAIL = [
    (["derive_deadlines.py"], "doplnění termínů z opakujících se lhůt"),
    (["fix_dataset.py"], "dedup, reklasifikace, přepočet statusu k dnešku"),
    (["consolidate.py"], "sjednocení variant faset na kanonické hodnoty"),
    # ⚠ BRÁNA PŘED PUBLIKACÍ, ne po ní. Export je to, co si stáhne produkt;
    # zveřejnit dataset s inverzním termínem nebo prázdným titulem a teprve
    # potom to zjistit znamená, že si vadu odnesou uživatelé.
    (["validate_release.py"], "kontrola kvality dat (brána)"),
    (["export_api.py"], "veřejný export docs/opportunities.json"),
]

# ⚠ PUBLIKACE JE ZVLÁŠŤ A JEN NA VYŽÁDÁNÍ (`--publish`).
#
# Export do `docs/` je levný a nikomu neublíží, takže patří do tailu vždycky.
# Nahrání do úschovny je ale okamžik, kdy se data stanou VIDITELNÁ PRO PRODUKT —
# a to nemá dělat nikdo omylem. Kdo publikuje, řekne si o to.
#
# Bez přístupů skript nepokračuje potichu: skončí s vysvětlením, co chybí.
PUBLISH = (["publish_export.py"], "publikace do úschovny (pro produkt)")

# ⚠ PŘÍMO DO DATABÁZE PRODUKTU. Do 2026-09-04 vedla tahle cesta přes druhý
# repozitář: export → GitHub → `node scripts/ingest-catalog.mjs` v
# `the-machine-app`. Dva příkazy ve dvou prostředích a stažení souboru po HTTP,
# přestože leží na disku vedle. Teď je to jeden krok — `scripts/publish_db.py`.
#
# Stejně jako `--publish` se bere VÝSLOVNĚ: je to okamžik, kdy se data stanou
# viditelná pro zákazníky, a to nemá udělat nikdo omylem.
PUBLISH_DB = (["publish_db.py"], "zápis do databáze produktu")


def run(args, label, dry):
    """Spustí krok. Vrací (ok, poslední řádek výstupu).

    `args[0]` je jméno skriptu ve `scripts/`, nebo cesta s lomítkem (pak se
    bere od kořene repa) — deterministické extraktory bydlí v `data/`.
    """
    first = args[0].replace("\\", "/")
    cmd = [PY, first if "/" in first else os.path.join("scripts", first)] + args[1:]
    if dry:
        print(f"    $ {' '.join(cmd[1:])}")
        return True, ""
    t = time.time()
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1800)
    except subprocess.TimeoutExpired:
        print(f"    ✖ {label}: překročen čas (30 min)")
        return False, ""
    tail = [l for l in (p.stdout or "").strip().splitlines() if l.strip()]
    last = tail[-1] if tail else ""
    if p.returncode != 0:
        print(f"    ✖ {label} (kód {p.returncode}) — {(p.stderr or last or '').strip()[:200]}")
        return False, last
    print(f"    ✓ {label}  {int(time.time() - t)}s  {last[:150]}")
    return True, last


def counts(path="data/opportunities.jsonl"):
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return 0
    with open(p, encoding="utf-8") as fh:
        return sum(1 for _ in fh)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="čárkou oddělené hosty z registru")
    ap.add_argument("--tier", choices=["structured", "html", "extract", "all"],
                    help="structured/html = strukturní ingest (třída A); extract = "
                         "deterministická vrstva 2 (třída B); all = obojí")
    ap.add_argument("--list", action="store_true", help="vypiš registr a skonči")
    ap.add_argument("--tail-only", action="store_true", help="jen přepočet a export, bez sítě")
    ap.add_argument("--skip-tail", action="store_true", help="jen harvest a ingest")
    ap.add_argument("--publish", action="store_true", help="po exportu nahraj do úschovny (pro produkt)")
    ap.add_argument("--publish-db", action="store_true", help="po exportu zapiš přímo do databáze produktu")
    ap.add_argument("--dry-run", action="store_true", help="ukaž příkazy, nic nespouštěj")
    a = ap.parse_args()

    if a.list:
        print(f"A) STRUKTURNÍ INGEST ({len(SOURCES)}) — harvest → ingest, bez modelu")
        print("   Běží ve výchozím `refresh_run.py`.\n")
        for host, (h, _out, i, tier) in sorted(SOURCES.items()):
            print(f"  {host:26} {tier:11} {h[0]:26} → {i[0]}")
        print(f"\nB) DETERMINISTICKÁ VRSTVA 2 ({len(EXTRACT_SOURCES)}) — harvest → vstup →"
              " scripts/extractors/<slug>.py → ingest_rich")
        print("   TAKY BEZ MODELU. Bere se výslovně: --tier extract nebo --only <slug>.\n")
        for slug, (h, tier) in sorted(EXTRACT_SOURCES.items()):
            print(f"  {slug:26} {tier:11} {h[0]:26} → extractors/{slug}.py")
        print("\nC) MODELOVÁ VRSTVA — zdroje bez vlastního extraktoru; potřebují"
              " extract_wf.js (LLM).\n   Viz docs/REFRESH.md. Tenhle skript je neumí.")
        return 0

    # Dva registry, dvě cesty. `--only` hledá v obou, aby uživatel nemusel vědět,
    # do které třídy zdroj patří — od toho je tenhle skript.
    # ⚠ VÝCHOZÍ BĚH JE JEN TŘÍDA A, a je to schválně. Třída B je dalších 21 webů,
    # tedy podstatně delší běh po síti — kdo chce obojí, řekne si `--tier all`.
    # Právě to dělá plánovaná obnova (`.github/workflows/refresh.yml`).
    chosen, chosen_extract = sorted(SOURCES), []
    if a.tier == "extract":
        chosen, chosen_extract = [], sorted(EXTRACT_SOURCES)
    elif a.tier == "all":
        chosen, chosen_extract = sorted(SOURCES), sorted(EXTRACT_SOURCES)
    elif a.tier:
        chosen = [h for h in chosen if SOURCES[h][3] == a.tier]
    if a.only:
        want = [s.strip() for s in a.only.split(",") if s.strip()]
        unknown = [w for w in want if w not in SOURCES and w not in EXTRACT_SOURCES]
        if unknown:
            print(f"✖ Neznámé zdroje: {', '.join(unknown)}")
            print(f"  Známé: {', '.join(sorted(set(SOURCES) | set(EXTRACT_SOURCES)))}")
            return 2
        chosen = [w for w in want if w in SOURCES]
        chosen_extract = [w for w in want if w in EXTRACT_SOURCES]

    before = counts()
    failed = []

    # ⚠ ZÁLOHA PŘED SÍTÍ, ne až ve `fix_dataset`. Ten dělá `.bak` až ze stavu PO
    # ingestu, takže rozbitý harvest, který katalog poškodí, se do ní stihne
    # propsat. Tahle kopie je poslední stav PŘED tím, než se čehokoli dotkla síť.
    src = os.path.join(ROOT, "data/opportunities.jsonl")
    if not a.tail_only and not a.dry_run and os.path.exists(src):
        shutil.copyfile(src, src + ".pre-refresh.bak")
        print(f"· záloha před během → data/opportunities.jsonl.pre-refresh.bak ({before} záznamů)\n")

    if not a.tail_only:
        print(f"═══ HARVEST + INGEST ({len(chosen)} zdrojů) ═══")
        for host in chosen:
            harvest, out, ingest, _tier = SOURCES[host]
            print(f"\n  {host}")
            ok, _ = run(harvest, "harvest", a.dry_run)
            if not ok:
                failed.append(f"{host} (harvest)")
                continue
            # Prázdný nebo chybějící výstup = ingest by tiše nic neudělal.
            if not a.dry_run and not os.path.exists(os.path.join(ROOT, out)):
                print(f"    ✖ harvest neuložil {out}")
                failed.append(f"{host} (bez výstupu)")
                continue
            ok, _ = run(ingest, "ingest", a.dry_run)
            if not ok:
                failed.append(f"{host} (ingest)")

    if not a.tail_only and chosen_extract:
        today = datetime.date.today().isoformat()
        print(f"\n═══ DETERMINISTICKÁ VRSTVA 2 ({len(chosen_extract)} zdrojů) ═══")
        for slug in chosen_extract:
            harvest, _tier = EXTRACT_SOURCES[slug]
            print(f"\n  {slug}")
            # ⚠ ŘETĚZ SE ZASTAVÍ NA PRVNÍM KROKU, KTERÝ NEPROŠEL. Pustit ingest
            # nad vstupem, který extrakce nevyrobila, znamená zapsat do katalogu
            # výsledek minulého běhu a tvářit se, že je dnešní.
            for args, label in extract_chain(slug, harvest, today):
                ok, _ = run(args, label, a.dry_run)
                if not ok:
                    failed.append(f"{slug} ({label})")
                    break

    if not a.skip_tail:
        print(f"\n═══ PŘEPOČET A EXPORT ═══")
        tail_ok = True
        for args, label in TAIL:
            ok, _ = run(args, label, a.dry_run)
            if not ok:
                failed.append(label)
                # Export bez přepočtu by vydal nesrovnaná data — dál nemá smysl.
                tail_ok = False
                break

        # ⚠ PUBLIKUJE SE JEN PO ČISTÉM TAILU. Nahrát do úschovny data, která
        # neprošla bránou kvality, znamená pustit je do produktu — tedy přesně
        # to, čemu ta brána má bránit.
        if a.publish and tail_ok:
            ok, _ = run(PUBLISH[0], PUBLISH[1], a.dry_run)
            if not ok:
                failed.append(PUBLISH[1])
        elif a.publish:
            print("    · publikace přeskočena — přepočet neprošel")

        # Táž podmínka a týž důvod: do databáze produktu se nesmí dostat data,
        # která neprošla bránou kvality.
        if a.publish_db and tail_ok:
            ok, _ = run(PUBLISH_DB[0], PUBLISH_DB[1], a.dry_run)
            if not ok:
                failed.append(PUBLISH_DB[1])
        elif a.publish_db:
            print("    · zápis do databáze přeskočen — přepočet neprošel")

    after = counts()
    print(f"\n═══ SHRNUTÍ ═══")
    print(f"  záznamů v katalogu: {before} → {after}  ({after - before:+d})")
    if failed:
        print(f"  ✖ selhalo: {', '.join(failed)}")
        print("  Ostatní zdroje proběhly; oprav a pusť znovu jen ty selhané (--only).")
        return 1
    print("  ✓ bez chyb")
    return 0


if __name__ == "__main__":
    sys.exit(main())
