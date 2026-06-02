# Runbook pro novou session — Vrstva 1 / fáze 2 (dokumenty→text) + Vrstva 2 (extrakce)

Model: **Vrstva 1** = fáze 1 (harvest: `{url,title,text,documents[]}`) + fáze 2 (dokumenty→text).
**Vrstva 2** = LLM extrakce (classify + extract → `data/opportunities.jsonl`).
Tahle session: vrstva 1 už má **fázi 1 hotovou** (`data/h19_*.jsonl` + další); zbývá **fáze 2 vrstvy 1**, pak **vrstva 2**.

## Co předat čerstvé session (handoff)
1. **cwd = `opportunity_pipeline/`** → `CLAUDE.md` se načte sám (architektura, konvence, pravidla 1–7,
   limits doktrína, routing, schéma + `extra`/`provenance`/`citations`). Většina kontextu je v repu.
2. **Seznam vstupů** (layer-1 fáze 1): `data/h19_*.jsonl` (19 nadací/zdrojů), `data/socialninadacnifond.jsonl`,
   `data/praha_grants.jsonl`, … (lokálně, gitignored).
3. **Tenhle runbook.** `classify_wf.js`/`extract_wf.js` jsou **Workflow** (přes Workflow tool) → session musí být agent.
4. `.venv` (playwright, pyyaml) — `pip install -r requirements.txt`.

---

## ČÁST A — Vrstva 1 / fáze 2: dokumenty → text (deterministické, bez LLM, paralelizovatelné)
Pro každý vstup: strukturální pre-filtr (`prefilter`, 100% bezpečné) + materializace VŠECH `documents[]`
do doc-store (`docstore.py`, idempotentní) → `data/files/<source>/<sha>.{ext,txt}` + manifest.
```bash
python3 scripts/prefilter.py data/h19_*.jsonl --inplace        # empty/dup/nav (loguje)
for f in data/h19_*.jsonl; do
  src=$(basename "$f" .jsonl | sed 's/^h19_//')
  python3 scripts/docstore.py --from-harvest "$f" --source "$src"
done
# stávající převody (vismo/dsw2) jen zaregistruj bez re-downloadu:
python3 scripts/docstore.py --index data/vismo_documents.jsonl --source vismo
```
Výsledek fáze 2 vrstvy 1: všechny podklady jako text v `data/files/`, navázané přes URL na vrstvu 1.

---

## ČÁST B — Vrstva 2: extrakce (per zdroj; paralelizovatelné přes zdroje)
1. **Vstup pro extrakci** (čte už zmaterializované dokumenty z části A):
```bash
python3 scripts/build_extract_input.py data/h19_nadacecez.jsonl \
        --source nadacecez --out-dir /tmp/ei_nadacecez
#   → /tmp/ei_nadacecez/grant_NN.json + paths.json
```
2. **(volitelně) classify** — MIXED/neznámé zdroje: `classify_wf.js` (Workflow) → nech jen grant/project.
   Známé grantové zdroje (nadace): přeskoč, `build_extract_input` dává `force_type=grant`.
3. **extrakce** — agent spustí `scripts/extract_wf.js` (Workflow tool), `args` = pole cest z `paths.json`.
   1 oportunita = 1 Haiku agent, plný text, vrací pole + `evidence` (verbatim citace per pole).
   Rate-limit → `resumeFromRunId`.
4. **uložení**:
```bash
python3 scripts/opportunities.py --from-extraction <result.json> \
        --source nadacecez --src-dir /tmp/ei_nadacecez \
        --harvest-file data/h19_nadacecez.jsonl --link-docs
```

### Obohacení STRUKTURNÍCH zdrojů LLM extrakcí (vismo / dsw2 výzvy)
Strukturní zdroj má část polí spolehlivě (vismo: dokumenty+tělo; dsw2 výzvy: open_from/deadline/status z `/explore/appeals`).
LLM doplní zbytek; **strukturní datumy mají přednost** (precedence řeší `opportunities.py:ingest_enriched`).
`build_extract_input.py --source-type` zapíše do vstupu stabilní join-`id` (vismo=url, dsw2-appeals=`foundation_id|title`).
```bash
# VISMO (úřední deska): dokumenty = už převedené attachments[].txt_path (bez re-downloadu)
python3 scripts/build_extract_input.py data/vismo_documents.jsonl \
        --source-type vismo --source vismo --out-dir /tmp/ei_vismo
# … extract_wf.js(paths) → <result> ; selhané (obří přílohy) re-run na Sonnetu ({paths,model:'sonnet'}), výsledky slij do jednoho result.json …
python3 scripts/opportunities.py --enrich vismo --structured data/vismo_documents.jsonl \
        --from-extraction <result.json> --src-dir /tmp/ei_vismo --link-docs

# DSW2 VÝZVY: nejdřív re-harvest appeals (struktura: deadline/status 100%), pak doc-enrich
python3 scripts/dsw2.py --no-opendata --no-csu          # → data/dsw2_appeals.jsonl (+ programs/links)
python3 scripts/build_extract_input.py data/dsw2_appeals.jsonl \
        --source-type dsw2-appeals --source dsw2 --out-dir /tmp/ei_appeals   # stáhne jen reálné dokumenty (odt/pdf/doc); web listingy skip
# … extract_wf.js(paths) → <result> …
python3 scripts/opportunities.py --enrich dsw2-appeals --structured data/dsw2_appeals.jsonl \
        --from-extraction <result.json> --src-dir /tmp/ei_appeals --link-docs
```
> dsw2 KATALOG programů (`--from-dsw2-programs`) je bezdokumentový (title+focus); akční info (deadline) je až ve VÝZVÁCH výše.

## Konvence (vynucené, viz CLAUDE.md)
- **Status NIKDY z LLM** (`opportunities.py:compute_status --today`). **NEOŘEZÁVAT** (limity jen sondy/safety).
- **1 oportunita = 1 agent.** Obsahový šum → classify (per-record); strukturální → prefilter. NIKDY content/density.
- **citations**: `match=exact|fragment` lokalizováno; `none` = LLM drift → člověk zkontroluje. Grounding = na lidech.

## Výstup
`data/opportunities.jsonl` — append per zdroj (dedup `canon_key`). Kontrola statusů:
`python3 -c "import json,collections;print(collections.Counter(json.loads(l)['status'] for l in open('data/opportunities.jsonl')))"`
