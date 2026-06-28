# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Plný recept a zdůvodnění architektury je v `README.md` (česky, vyčerpávající). Tenhle soubor přidává jen to, co README neřeší: operační příkazy, závislost na rodičovském repu a netriviální pasti. Nečti to jako náhradu README — čti obojí.

## Soběstačnost & data (nejdůležitější fakt)

Repo je **samostatný a soběstačný** (osamostatněno z rodiče 2026-06-01). Všechny cesty jsou lokální:

- `pipeline.py` má `REPO = os.path.dirname(__file__)` → kořen **tohoto** repa. Importuje `dsw2_fetch` z lokálního `scripts/` (ne z `../extract/`).
- **Data žijí v `./data/`** (~1 GB, **gitignored** — viz `.gitignore`): `wp_full/` (127 souborů, WP reuse korpus), `vismo_files/` (1371 PDF→txt), `vismo_documents.jsonl`, `dsw2_files/`, `dsw2_programs.jsonl`, `dsw2_links.jsonl`, `merged_dataset.json`. Mapa host→platforma je `./platform_map.json` (root).
- **`scripts/*.py` používají relativní cesty `data/...`** (argparse defaulty) → spouštěj je **z kořene repa** (CWD = `opportunity_pipeline/`), jinak nenajdou data.
- Data jsou kopie z rodičovského `re-grantio/data/` k datu osamostatnění. Nejsou v gitu, takže **fresh clone je nemá** — refresh = znovu zkopírovat z rodiče nebo re-harvestovat (`scripts/*harvest*`).
- `platform_data/platform_map.json` je starší **snapshot**, ne to, co pipeline čte (autoritativní je `./platform_map.json` v rootu).

## Příkazy

Prostředí: macOS, **python3.13**, používej venv (`python3.13 -m venv .venv && source .venv/bin/activate`). Žádné build/test/lint — je to skriptová pipeline, ne aplikace.

```bash
# Driver nad UŽ STAŽENÝMI daty (LLM fáze jsou stuby — viz níže)
python3 pipeline.py --source <host>                      # 1 zdroj
python3 pipeline.py --reuse-all --out data/opportunities.jsonl

# Harvestery (vrstva 1) — každý je samostatný CLI, spouští se z rodiče kvůli ../data
python3 scripts/wp_harvest.py        # WP REST, lossless
python3 scripts/vismo.py             # listing výzev
python3 scripts/vismo_detail.py      # detail + přílohy + status
python3 scripts/dsw2.py              # /explore/fonds + /explore/appeals (inline JSON)
python3 scripts/kentico_irop.py      # IROP/dotaceEU Kentico inline
python3 scripts/mv_cms.py            # ASP.NET /clanek/*.aspx (MV ČR mv.gov.cz)
python3 scripts/marwel.py --seeds <JSON>  # MŠMT (msmt.gov.cz) Marwel CMS — <div id=article> + /file/NNNNN přílohy

# gov.cz portálový CMS (server-rendered, NE SPA) — MZe + MPSV sdílí jeden harvester
python3 scripts/eagri.py --seeds <JSON>   # MZe/eAGRI národní dotace (ea-content-block + příloha Zásady)
python3 scripts/mpsv.py                    # MPSV (mpsv.gov.cz) — reuse eagri.process + rozcestník→detail discovery

# Nadace / nadační fondy + jednorázové bespoke zdroje — 1 web = 1 parser (host→parser je v routing.yaml `sources:`)
python3 scripts/nadacevia.py · albert.py · sirius.py · leontinka.py · partnerstvi.py  # Nadace Via, Albert, Sirius, Leontinka, Partnerství
python3 scripts/nadace_adra.py · veronica.py · hlavka.py · vinarskyfond.py · sfa.py    # ADRA, Veronica, Hlávkova nadace, Vinařský fond, SF audiovize
python3 scripts/sfzp.py              # SFŽP (sfzp.gov.cz) — WP REST výzva-* stránky (FN/PU půjčky) + Modernizační fond detail-vyzvy/?id=NN (RES+/HEAT/TRANSGov…)
python3 scripts/gacr.py              # GA ČR (gacr.cz) — WP posty „Vyhlášení veřejné soutěže" (Standardní/JUNIOR STAR/EXPRO/POSTDOC/…) + LA/bilaterální „Výzva pro podávání" (--since = aktuální roční kolo)
python3 scripts/sfpi.py              # SFPI/SFRB (sfpi.cz) — WP program-hub pages, bydlení (úvěry+dotace): Úsporné BD, Živel, Dostupné nájemní bydlení, BD bez bariér…
python3 scripts/sfdi.py              # SFDI (sfdi.gov.cz) — příspěvky na dopravu: cyklostezky, bezbariérové chodníky, bezpečnost silnic, letiště, ETCS… (FRONT-END HTML, /prispevky/<slug>/ jsou přes REST 401)
python3 scripts/sfk.py               # SFK – Státní fond kultury ČR (na mk.gov.cz; dedikovaná doména mrtvá) — projektové dotace v kultuře, 3 výzvy/rok přes DP MK. POZOR: mk.gov.cz = ASP.NET WebForms (NEstrip <form>)
python3 scripts/mpo.py               # MPO (mpo.gov.cz) — NÁRODNÍ programy (TREND/TRIO/TWIST/CFF/Obchůdek/Czech Rise Up/brownfieldy/strategické investice), seed-driven. OP TAK/PIK = P3 EU, MIMO
python3 scripts/mmr.py               # MMR (mmr.gov.cz) — NÁRODNÍ dotace /cs/narodni-dotace (PORR, euroregiony, hroby, bezbariérové obce, cestovní ruch, NNO…), Kentico. MIMO: IROP/EU (P3) + Podpora bydlení (=SFPI)
python3 scripts/eeagrants.py         # EHP a Norské fondy (eeagrants.cz; NKM = MF) — výzvy 2014–2021 (ukončené). typ_poskytovatele=zahranicni_fond, zdroj=ehp_norsko

# Univerzální doc→text (vrstva 2) — používají harvestery i pipeline
python3 scripts/dsw2_fetch.py        # sniff_ext + pdftotext/textutil (PDF/DOC/DOCX/XLS/ODT)

# Detekce platformy / coverage analýza (data-driven)
python3 scripts/cms_similarity.py        # strukturální shlukování otisků → 1 shluk = 1 parser
python3 scripts/platform_refingerprint.py
python3 scripts/diversity_finder.py      # nejodlišnější nevzorkované zdroje

# Deterministická vrstva 2 (strukturní část kolem LLM extrakce) — POŘADÍ: build_extract_input → extract_wf.js → ingest_rich → consolidate
python3 scripts/build_extract_input.py <layer1.jsonl> --source <slug> --out-dir <dir>   # → grant_NN.json: PLNÝ text + PLNÝ text příloh (žádný ořez) pro extract_wf.js
python3 scripts/ingest_rich.py --out-dir <extract_out> --src <ei_dir>                    # bohatá extrakce → data/opportunities_v2.jsonl (status v KÓDU, ne LLM)
python3 scripts/consolidate.py            # remap facet variant→kanon (oblast/typ_zadatele/cílová/kraj) dle data/consolidation_maps.json; --dry-run pro report

# Kvalita datasetu + build prohlížecí appky (nad data/opportunities_v2.jsonl)
python3 scripts/fix_dataset.py            # deterministická oprava: dedup (Ústí/variant) + reclasifikace null poskytovatele + přepočet statusu k --today (default dnešek); idempotentní, .bak
python3 scripts/build_app.py              # → data/grants_app.html (fasetový prohlížeč; STATUS se počítá KLIENTSKY k dnešku, nezastará)
```
> **Windows pozn.:** skripty tisknou diagnostiku s `→ · ⚠` — konzole cp1250 to neumí. Pipeline-skripty (`consolidate`, `fix_dataset`, `build_extract_input`, `routing`) si proto na startu vynutí UTF-8 stdout (`sys.stdout.reconfigure`); jinak `UnicodeEncodeError`.

**`scripts/*.js` NEJSOU node skripty** — jsou to **Claude Code Workflow** definice (`export const meta`, `agent()`, `parallel()`). Spouští se nástrojem Workflow uvnitř Claude Code, ne `node coverage_wf.js`. Jsou to LLM orchestrace pro coverage (`coverage_wf.js`, `type_coverage_wf.js`) a re-detekci platforem (`detect_platforms_wf.js`).

## Architektura — co vyžaduje přečíst víc souborů

**Dvouvrstvý model** (`README.md` + `schema/opportunity_schema.md`):
- **Vrstva 1 (harvest, `scripts/`):** ~12 tenkých parserů per CMS-rodina → jen TEXT + DOKUMENTY. Liší se mezi CMS.
- **Vrstva 2 (extrakce, LLM):** JEDEN univerzální extraktor próza+PDF → opportunity schema. Společné napříč zdroji. `dsw2_fetch.py` (doc→md) je taky univerzální napříč všemi handlery (`File.ashx`, `/soubor`, `/getmedia`, přímé `.pdf`).

**Pevná pravidla, která se snadno poruší:**
1. **STATUS se POČÍTÁ v kódu, ne LLM.** Otevřená a uzavřená výzva jsou textově identické — liší se jen datem vs. dnešek. LLM klasifikuje TYP, kód počítá status. Kanonická funkce je `scripts/opportunities.py:compute_status(open_from, deadline, today)` (pozor: `pipeline.py:compute_status(fields, rec)` je starší VARIANTA s jiným podpisem a natvrdo `date(2026,6,1)` — nepoužívej ji jako zdroj pravdy). Uložené `status` v `opportunities_v2.jsonl` je SNAPSHOT z build-time (`fix_dataset.py --today`, default dnešek); **appka ho ignoruje a počítá status KLIENTSKY k reálnému dnešku** (`build_app.py:computeStatus`, zrcadlí `opportunities.py`), takže badge/filtr nezastarají.
2. **Nevěř platform labelu** z detekce — ověř strukturální otisk (`cms_similarity.py`). Labely `mv_legacy`/`gordic_ginis` slévaly 3 různé CMS; ~65 grantových zdrojů bylo schováno v `UNKNOWN`. Příklad záměny: `mpsv.gov.cz` byl detekcí označen `custom_spa` (protože stará homepage `www.mpsv.cz` JE Nuxt SPA) — ve skutečnosti je dotační portál server-rendered gov.cz CMS jako MZe → opraveno na `eagri_portal` (harvestuje `eagri.py`/`mpsv.py`).
3. **Dvě vrstvy obsahu, v pořadí:** nejdřív TYP (`prompts/classify_type.md` → grant/project/news/foundation_mission/administrative/other), pak POLE typu (`prompts/extract_grant.md`).
4. **NEOŘEZÁVAT vstup do LLM** — plný markdown + přílohy (kontext ~200k).
5. **Negativní pravidla z `prompts/pitfalls.md`** patří do promptů — vytěžené záměny (`platnost:`/`realizace` ≠ deadline; `úvěr`/`jistina` ≠ dotace; `cílová skupina` ≠ žadatel; soubory-ke-stažení ≠ povinné přílohy).
6. **LIMITY JEN NA SONDY; DATA VŽDY CELÁ** (v každé vrstvě i fázi). Bounded smí být jen **probe** (detekce platformy, sniff typu, vzorek pro MĚŘENÍ kvality) a **safety** (runaway-pojistka, vysoko, při dosažení NAHLAS `⚠` log = bug, ne coverage cap). **Sběr dat = žádný strop na stránky/dokumenty/přílohy, žádný ořez textu, žádné vzorkování** (`acquisition.*` = null/unbounded). Vše v `limits.json` (root), NIKDY natvrdo; kód čte `scripts/limits.py` → `L('cesta.klic')`. Struktura: `probe` / `acquisition` (vše null) / `safety` (vysoké pojistky). Než zavedeš JAKÝKOLI limit, je to sonda nebo safety? Když ne → nepatří tam, ber data celá.
7. **STRUKTURA PŘED PRÓZOU** (`docs/detection.md` krok ⓪) — vždy nejdřív zkus strukturovaný endpoint (API/XHR/inline-JS/šablona/WP REST); LLM vrstva 2 až když je detail neredukovatelně próza/PDF. Ověř CO endpoint dá (award-DB ≠ otevřené výzvy).

**LLM vrstva 2 = Claude-řízené WORKFLOW s Haiku agenty** (NE stub): `scripts/classify_wf.js` (klasifikace base_type) + `scripts/extract_wf.js` (extrakce polí per typ, 1 oportunita = 1 agent, plný text). Spouští se nástrojem Workflow uvnitř Claude Code; status dopočítá kód po běhu. (`pipeline.py:llm_call` je starý in-process stub — driver ho zatím nevolá; reálná vrstva 2 jede přes workflow.) Empiricky: na plném textu ~88 % polí grantu; ořez vstupu sráží `amount` na 27 %.

**Přístupové metody vrstvy 1 (5 archetypů):** REST (WP) / inline-JS (dsw2) / HTML-listing (vismo, eeagrants statické HTTP) / SPA-postback (Apify) / **SPA-grid se skrytým JSON-XHR → 1× odposlech Playwrightem (`scripts/lewis_discover.py`) → čistý HTTP replay bez Apify (`lewis_dynamo.py`)**. `requirements.txt` = playwright (jen pro discover).

**Coverage je MĚŘENÝ cyklus, ne hádání** (`docs/coverage.md`): `diversity_finder.py` → coverage workflow → diff proti minulému běhu (vyčísli zisk) → stop při saturaci. Nové záludnosti jdou do `prompts/pitfalls.md`.

## Rozcestník dokumentace
- `REMAINING.md` (root) — **plán rozšiřování**: co je hotovo, co zbývá (priority P1–P5), stav datasetu, vlajky. Aktualizuj po každém přidaném zdroji.
- `docs/platform_playbook.md` — definice VŠECH CMS rodin → podpis/harvester/metoda
- `docs/detection.md` — 3 vrstvy detekce platformy + lekce o slitých labelech
- `docs/data_reuse.md` — index UŽ STAŽENÝCH dat k reuse (klíčové: harvest = REUSE-first)
- `docs/apify_howto.md` — kdy Apify (SPA/grantys, WebForms postback)
- `docs/coverage.md` — coverage & active learning
- `schema/opportunity_schema.md` — kanonický model + „kde které pole hledat" (HTML/md/doc-md)
