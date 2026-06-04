# Handoff — re-extrakce vrstvy 2 (čistá session)

CWD = `opportunity_pipeline/`. Přečti `CLAUDE.md` + `~/.claude/.../memory/MEMORY.md` (zejm. `classify-design-vrstva2.md`). Tohle je stav rozpracované **re-extrakce** novým bohatým promptem a **nevyřešený serializační problém**, který je třeba dotáhnout.

## Cíl
Re-extrahovat všechny granty/mise novým vysvětlujícím promptem (`scripts/extract_wf.js`) z PLNÉHO textu+příloh do bohatého schématu (multi cílová skupina / region-geo / částky / kontakt / role dokumentů / sběrače `dalsi_datumy`/`dalsi_castky` / `prijemci[]` pro výsledkové listiny / `evidence`). Status NEřeší LLM (počítá kód). Pak napojit do `data/opportunities.jsonl`, zkonsolidovat slovníky, přegenerovat appku `scripts/build_app.py`.

## JÁDRO PROBLÉMU (nutno vyřešit jako první)
`agent(prompt, {schema})` vnutí subagentovi harness-tool **StructuredOutput** (schéma = jeho input_schema; NENÍ to náš tool). Na našem **bohatém vnořeném schématu** (8× `array-of-objects`: deadliny/castky/region/dokumenty/kontakt/prijemci/dalsi_datumy/dalsi_castky + `evidence` objekt + union typy) se **XML kódování tool-argumentu láme**: model vygeneruje plnou odpověď (~1305 output tokenů), ale do `input` dorazí **prázdné `{}`** → validace „missing required property" → **nekonečný re-prompt (270×–1699×)**. Ověřeno (transkripty): model sám hlásí *„parameters not passed / XML tool call strips them"*.
- NENÍ to velikost vstupu (padá i na 1,8k zn), NENÍ to prompt (model uvažuje správně), NENÍ to harvest (dsw2 zdroj ověřen — prázdné popisy jsou prázdné i na zdroji; `/api/*` je rickroll).
- `required:[]` smyčku nevyřeší (prázdné `{}` se přijme → model po „success" dál volá → re-call spirála 1699×). `required:['title']` → reject-loop.
- **Text-režim** (bez schématu, agent vrátí ```json blok) smyčku ODSTRANÍ, ale ~50 % výstupů má **drobně nevalidní JSON** (zdvojené/neescapované uvozovky v českých verbatim citacích v `evidence`). `json_repair` (Python) je **opravil 4/4**.

## ROZHODNUTÝ SMĚR (uživatel)
Nic nevypouštět (evidence ZŮSTÁVÁ). Vyřešit serializaci jedním z:
- **(A) Agent si JSON opraví SÁM před odesláním** — subagent má Bash/Python; po sestavení JSON spustí `json_repair` na svůj výstup a vrátí už validní JSON (text). Náš parse je pak triviální.
- **(B) Předání přes SOUBOR** — agent zapíše výsledek do `/tmp/out/<id>.json` (Write tool, plochý string content je robustnější než vnořený StructuredOutput-arg); po doběhu VŠECH oportunit uděláme **batch `json_repair`** nad soubory.
> Pozn.: „```json blok v textu" je slabé (escaping); StructuredOutput s bohatým schématem je rozbitý. Pokud zkusíš StructuredOutput, jedině s PLOCHÝM schématem (vše string / array-of-string, žádné array-of-objects, žádné union) — ale (A)/(B) drží evidence i strukturu.

## STAV DAT / VSTUPŮ (vše /tmp, gitignored mimo skripty)
- `/tmp/mg2/grant_0000..0596.json` = **597 obsahových grantů** (id=canon_key uvnitř, tělo+přílohy, capnuto na 150k safety).
- `/tmp/mm2/mission_0000..0022.json` = **23 misí**.
- `/tmp/empty_ids.json` = **102 prázdných stubů** (dsw2 katalog bez popisu) → do LLM NEposílat, deterministicky: oblast z focus_area, region z poskytovatele.
- `/tmp/reext_big.json` = **56 velkých** (>150k) → na konec, chytře (jen relevantní dokument, ne všechny přílohy).
- Vstupy stavěné z `data/opportunities.jsonl` (tělo z harvestu/extra, přílohy z doc-store txt_path); builder logika viz níže.

## SKRIPTY
- `scripts/extract_wf.js` — vrstva 2 extraktor. AKTUÁLNĚ text-režim (vrací `{path,type,text}`, bez schématu). 2 typy (grant/mission, dle `mission_` v názvu). ARG: pole cest | `{paths,model}` | `{dir,prefix,count}`. MODEL='sonnet' (Haiku malformuje na bohatém schématu). **Uprav dle (A)/(B).**
- `scripts/opportunities.py` — kanonické úložiště: `compute_status` (TODAY=date(2026,6,1)), `canon_key` (ID-based: /d-NNNNNN, program_id, jinak plný titulek), `resolve_citations` (evidence→grounding), `opp_from_fields`, `ingest_extraction`/`ingest_enriched`/`ingest_dsw2`/`_programs`/`_vismo`. Provider→typ tabulka `data/provider_types.json`.
- `scripts/build_extract_input.py` — `--source-type {harvest,vismo,dsw2-appeals}`, doc-store materializace, zapisuje join-`id`.
- `scripts/build_app.py` — generovátko appky (`data/grants_app.html`): fasety + hierarchie (sektor→typ, poskytovatel→konkrétní, kraj) + detail (pole, facety, klasifikace, grounding, **dokumenty: originál/stažený/md/text**, raw JSON). Čte `data/opportunities.jsonl`.
- `scripts/facet_wf.js` — samostatný facet pass (PŘEDCHŮDCE; nová bohatá extrakce ho z velké části nahrazuje — facety lze odvodit z extrakce + deterministicky).

## KONSOLIDACE SLOVNÍKŮ (na konci, mapy hotové — reuse)
Otevřený režim tříští hodnoty (diakritika, cyrilice „obcanска", varianty „sport*", „Moravskoslezský" vs „…kraj"). Deterministický remap: oblast/typ_zadatele variant→kanon + cyrilice-fix + kraj-fix + sektor-rollup (z typ_zadatele) + provider→typ_poskytovatele z `provider_types.json`. (Kód viz git/commit historie; aplikováno na současné facety v opportunities.jsonl — singletony 0.)

## POŘADÍ DALŠÍCH KROKŮ
1. **Vyřeš serializaci** (A nebo B) → otestuj na ~8 vč. dřív spirálujících (`/tmp/mg2/grant_0057.json`, `grant_0079.json`) + 2 mise. Kritérium: 0 smyček, 8/8 validní JSON, evidence přítomná.
2. **Plný běh:** 597 grantů (`{dir:/tmp/mg2,prefix:grant,count:597,model:sonnet}`) + 23 misí (`/tmp/mm2`).
3. **Napoj do opportunities.jsonl** novým schématem (multi→hlavní+sběrače; region→geo-objekt; doc-role). Merge dle `id`.
4. **102 prázdných** deterministicky · **56 velkých** chytře (relevantní dokument).
5. **Konsolidace slovníků** (reuse mapy).
6. **`build_app.py`** → app; přidej nové fasety (cílová skupina, spoluúčast, míra %, typ dokumentu, výsledková listina, období realizace, multi-region).

## STANDARDY (vynucené)
- Status v kódu, NE LLM. NEOŘEZÁVAT vstup (jen safety cap 150k, logováno). Prompty = NÁVOD (jak pozná člověk), ne slovník. Evidence = grounding. 1 oportunita = 1 agent.
- **OVĚŘUJ VÝSTUP PŘED PŘEDÁNÍM** (kontroluj reálná data, ne jen tvrzení — fasety/smyčky/prázdné).
- Limity jen v `limits.json` přes `L()`. Data gitignored; commituj jen kód.
