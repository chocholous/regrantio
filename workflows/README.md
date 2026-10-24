# `workflows/` — agentní workflow, NE spustitelné skripty

⚠ **Tyhle soubory se nespouštějí Nodem.** Nemají `main()`, nevypisují nic na
výstup a `node workflows/extract_wf.js` s nimi neudělá nic užitečného. Jsou to
**definice workflow pro nástroj Workflow uvnitř Claude Code** — `export const meta`,
`agent()`, `parallel()`.

Do 2026-09-04 ležely v `scripts/` mezi 122 pythonními CLI a `CLAUDE.md` na to
muselo upozorňovat zvláštní větou. Varování v dokumentaci je náplast na
strukturu; složka je oprava.

## Co je produkční a co výzkumné

| soubor | role |
|---|---|
| `extract_wf.js` | **produkce** — vrstva 2: extrakce polí z plného textu + příloh. 1 oportunita = 1 agent. |
| `facet_wf.js` | **produkce** — vrstva 2: mapování do kontrolovaných číselníků (oblast, typ žadatele, forma podpory…). |
| `classify_wf.js` | **produkce** — vrstva 1: klasifikace `base_type` (grant / news / administrative / …). |
| `coverage_wf.js` | měření — jaká pole se v dokumentech vyskytují a jak se formulují; hlídá saturaci. |
| `type_coverage_wf.js` | měření — totéž dvouvrstvě: nejdřív typ obsahu, pak jeho pole. |
| `detect_platforms_wf.js` | výzkum — re-detekce platforem u webů označených `UNKNOWN`. |
| `classify_improve_wf.js` | výzkum — active-learning vylepšení klasifikačního promptu. |
| `verify_classify_wf.js` | audit — týž vzorek překlasifikují dva modely nezávisle, pro porovnání. |

Tři produkční se pouštějí při každém rozšíření katalogu o zdroj, který
nemá deterministický parser. Zbylých pět jsou nástroje na ladění promptů —
sáhne se po nich, když se mění `prompts/`.

## Proč to ještě není program

`extract_wf.js` je ruční cesta vrstvy 2: odklikává ji člověk v Claude Code.
Automatická náhrada už existuje: `scripts/extract_api.py`, kterou volá
`refresh_run.py --tier model` (třída C, 37 zdrojů v `data/sources.json`).
Chybí jen klíč `ANTHROPIC_API_KEY`; bez něj se třída C při obnově přeskočí
a deterministicky se obnovují třídy A a B. Rozpočet i model jsou spočítané
v `REMAINING.md`.

## Prompty

Vlastní zadání pro model nejsou tady, ale v [`prompts/`](../prompts/) —
`classify_type.md`, `extract_grant.md`, `pitfalls.md`. Workflow je jen
orchestrace: kdo, kolikrát, nad čím.
