# CLAUDE.md — regrantio

Datový základ Grantia: sbírá dotační výzvy ze **135 zdrojů**, sjednocuje je do
jednoho katalogu a publikuje je **přímo do databáze produktu**. Neví nic
o uživatelích, organizacích ani o produktu; hranice vede přes data, ne přes kód.

> Recept a zdůvodnění architektury je v [`README.md`](README.md). Kontrakt
> publikovaných dat je [`docs/EXPORT.md`](docs/EXPORT.md). Kvalita datové
> základny je ČÍSLO, ne tvrzení: [`docs/QUALITY.md`](docs/QUALITY.md).

## Co tu je a co ne

| | |
|---|---|
| Katalog | `data/opportunities.jsonl` — **jediný zdroj pravdy, v gitu** (řádek = záznam, 12 polí včetně `provenance`, `extra`, `citations`) |
| Export | `docs/opportunities.json` — kurátorovaná podoba katalogu, kontrakt 1.2 (`export_api.py`) |
| Inventář zdrojů | `data/sources.json` — jméno, typ, třída obnovy, harvester, počty, stáří (`sources_inventory.py`) |
| Kvalita | `docs/QUALITY.md` + `data/quality.json` (`quality_report.py`) |
| Jazyk | Python 3.13 ve venv, bez frameworku; `pyyaml`; Playwright jen pro objev SPA |
| Testy | `tests/test_*.py`, všechny pouští `validate_release.py` (brána) i CI |
| Stažené dokumenty | `data/` mimo katalog je **gitignored** (~15 GB); obnova je re‑harvest nebo `data_bundle/` |

⚠ **Skripty se spouštějí z kořene repa** (cesty `data/...` jsou relativní).
⚠ **Windows:** `python`, `.venv\Scripts\activate`; konzole je cp1250, skripty si
vynucují UTF‑8 stdout; `pdftotext` jen s `-enc UTF-8`.

## Příkazy, které se používají

```bash
python scripts/refresh_run.py --list           # registr zdrojů po třídách A · B · C
python scripts/refresh_run.py                  # A: harvest → ingest → přepočet → brána → export
python scripts/refresh_run.py --tier extract   # B: + vlastní deterministické parsery
python scripts/refresh_run.py --tier model     # C: vrstva 2 přes model (chce ANTHROPIC_API_KEY)
python scripts/refresh_run.py --tier all --budget-min 60 --step-timeout-min 12 --publish-db   # týdenní obnova (A + B, C jen s klíčem)
python scripts/refresh_run.py --tail-only      # jen přepočet, brána, export, kvalita (bez sítě)

python scripts/publish_db.py --dry-run         # co by se zapsalo do databáze Grantia
python scripts/publish_db.py                   # zápis (PUBLIC_SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY v .env)

python scripts/validate_release.py             # brána: testy, kontrakt, kvalita, propad, vyschlý zdroj, stáří, inventář
python scripts/quality_report.py               # docs/QUALITY.md + data/quality.json
python scripts/sources_inventory.py            # přepočítá data/sources.json (kurátorovaná pole zachová)
```

Třídy obnovy (`data/sources.json`, sloupec `refresh`):

| třída | cesta | zdrojů |
|---|---|---:|
| A | harvest → strukturní ingest (`ingest_kraj`, `ingest_dotis`, rodiny vismo / dsw2 / kentico / plone) | 55 |
| B | harvest → `scripts/extractors/<slug>.py` → `ingest_rich` | 21 |
| C | harvest → `build_extract_input` → `extract_api.py` (model) → `ingest_rich` | 37 |
| T | „extraktor" opisuje červnová data, obnovu jen předstírá; bez harvesteru | 3 |
| F | zmrazený (zdroj za přihlášením nebo mrtvý) | 2 |
| ? | jednorázový sběr bez zapsané cesty k obnově | 17 |

## Pevná pravidla

1. **Status se počítá v kódu, ne modelem** (`opportunities.py:compute_status`).
   Uložený `status` je snímek; produkt si ho přepočítá k dnešku.
2. **Nehalucinovat.** `amount = null`, `deadline = null` zůstává null. Odvozené
   hodnoty (`derive_deadlines`, kontrakt 1.2 `scope` / `deadline_kind` /
   rodiny ročníků) jsou DOKLADOVANÉ a mimo `content_hash`.
3. **Jen jeden proces píše `opportunities.jsonl`.** Ingesty sekvenčně.
4. **Katalog je v gitu, data ne.** Export se v gitu commituje s obnovou
   (14 MB týdně; otevřené rozhodnutí, viz README §Data).
5. **Limity jen na sondy a pojistky** (`limits.json`); data se berou celá.
6. **Brána před publikací.** `validate_release.py` stojí v tailu obnovy PŘED
   exportem; co neprojde, ven nejde.
7. **Nemergovat do `main` z cizí větve bez brány**; CI pouští totéž.
8. **`source` je interní slug.** Jméno poskytovatele nese `provider`
   (`data/source_names.json`), člověku se slug neukazuje nikdy.

## Struktura

```
scripts/            harvestery (1 web nebo 1 rodina CMS = 1 skript), ingesty, tail
scripts/extractors/ deterministické parsery vrstvy 2 (třída B)
scripts/enrich.py   odvozená pole kontraktu 1.2 · dedup.py rodiny ročníků
workflows/          definice pro nástroj Workflow v Claude Code (extract_wf.js = prompt vrstvy 2)
prompts/            prompty vrstvy 2 a vytěžené záludnosti (pitfalls.md)
data/               katalog (v gitu), seeds, jména zdrojů, inventář, kvalita; zbytek gitignored
docs/               EXPORT (kontrakt) · REFRESH (obnova) · QUALITY (měření) · SESSION_PLAYBOOK · rodiny CMS
tests/              test_core · test_identity · test_notacall · test_publish · test_publish_db · test_enrich
```

## Rozcestník

| Téma | Soubor |
|---|---|
| Recept, architektura, data na disku | [`README.md`](README.md) |
| Kontrakt exportu (1.2) | [`docs/EXPORT.md`](docs/EXPORT.md) |
| Obnova: třídy, kadence, pojistky | [`docs/REFRESH.md`](docs/REFRESH.md) |
| Kvalita dat, stav zdrojů | [`docs/QUALITY.md`](docs/QUALITY.md) |
| Jak pracovat, pasti | [`docs/SESSION_PLAYBOOK.md`](docs/SESSION_PLAYBOOK.md) |
| Co zbývá, blokery | [`REMAINING.md`](REMAINING.md) |
| Rodiny CMS, detekce | [`docs/platform_playbook.md`](docs/platform_playbook.md) · [`docs/detection.md`](docs/detection.md) |
| Model dat | [`schema/opportunity_schema.md`](schema/opportunity_schema.md) |
