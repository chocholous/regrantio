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
python3 scripts/mv_cms.py            # ASP.NET /clanek/*.aspx

# Univerzální doc→text (vrstva 2) — používají harvestery i pipeline
python3 scripts/dsw2_fetch.py        # sniff_ext + pdftotext/textutil (PDF/DOC/DOCX/XLS/ODT)

# Detekce platformy / coverage analýza (data-driven)
python3 scripts/cms_similarity.py        # strukturální shlukování otisků → 1 shluk = 1 parser
python3 scripts/platform_refingerprint.py
python3 scripts/diversity_finder.py      # nejodlišnější nevzorkované zdroje
```

**`scripts/*.js` NEJSOU node skripty** — jsou to **Claude Code Workflow** definice (`export const meta`, `agent()`, `parallel()`). Spouští se nástrojem Workflow uvnitř Claude Code, ne `node coverage_wf.js`. Jsou to LLM orchestrace pro coverage (`coverage_wf.js`, `type_coverage_wf.js`) a re-detekci platforem (`detect_platforms_wf.js`).

## Architektura — co vyžaduje přečíst víc souborů

**Dvouvrstvý model** (`README.md` + `schema/opportunity_schema.md`):
- **Vrstva 1 (harvest, `scripts/`):** ~12 tenkých parserů per CMS-rodina → jen TEXT + DOKUMENTY. Liší se mezi CMS.
- **Vrstva 2 (extrakce, LLM):** JEDEN univerzální extraktor próza+PDF → opportunity schema. Společné napříč zdroji. `dsw2_fetch.py` (doc→md) je taky univerzální napříč všemi handlery (`File.ashx`, `/soubor`, `/getmedia`, přímé `.pdf`).

**Pevná pravidla, která se snadno poruší:**
1. **STATUS se POČÍTÁ v kódu, ne LLM** (`pipeline.py:compute_status`). Otevřená a uzavřená výzva jsou textově identické — liší se jen datem vs. dnešek. LLM klasifikuje TYP, kód počítá status. `TODAY` je v `pipeline.py` natvrdo (`date(2026,6,1)`) — při reálném běhu vyřeš.
2. **Nevěř platform labelu** z detekce — ověř strukturální otisk (`cms_similarity.py`). Labely `mv_legacy`/`gordic_ginis` slévaly 3 různé CMS; ~65 grantových zdrojů bylo schováno v `UNKNOWN`.
3. **Dvě vrstvy obsahu, v pořadí:** nejdřív TYP (`prompts/classify_type.md` → grant/project/news/foundation_mission/administrative/other), pak POLE typu (`prompts/extract_grant.md`).
4. **NEOŘEZÁVAT vstup do LLM** — plný markdown + přílohy (kontext ~200k).
5. **Negativní pravidla z `prompts/pitfalls.md`** patří do promptů — vytěžené záměny (`platnost:`/`realizace` ≠ deadline; `úvěr`/`jistina` ≠ dotace; `cílová skupina` ≠ žadatel; soubory-ke-stažení ≠ povinné přílohy).

**LLM fáze v `pipeline.py` jsou STUBY** (`llm_call()` → `NotImplementedError`, `classify_type`/`extract_fields` vrací fallback). Deterministické fáze (reuse dat, doc-konverze, status, dedup) jsou plně funkční. Napojení modelu (Anthropic SDK / Apify) je TODO.

**Coverage je MĚŘENÝ cyklus, ne hádání** (`docs/coverage.md`): `diversity_finder.py` → coverage workflow → diff proti minulému běhu (vyčísli zisk) → stop při saturaci. Nové záludnosti jdou do `prompts/pitfalls.md`.

## Rozcestník dokumentace
- `docs/platform_playbook.md` — definice VŠECH CMS rodin → podpis/harvester/metoda
- `docs/detection.md` — 3 vrstvy detekce platformy + lekce o slitých labelech
- `docs/data_reuse.md` — index UŽ STAŽENÝCH dat k reuse (klíčové: harvest = REUSE-first)
- `docs/apify_howto.md` — kdy Apify (SPA/grantys, WebForms postback)
- `docs/coverage.md` — coverage & active learning
- `schema/opportunity_schema.md` — kanonický model + „kde které pole hledat" (HTML/md/doc-md)
