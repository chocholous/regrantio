# Agents — Orchestrátor + 13 sub-agentů

## Architektonický princip

**Orchestrátor = agent.** Řídí celý pipeline, dispatchi sub-agenty,
monitoruje průběh, reaguje na selhání. Viz `orchestrator.md`.

**Sub-agent = specializovaná funkce.** Dostane vstup, vrátí strukturovaný výstup.
Nerozhoduje o dalším kroku — to dělá orchestrátor agent.

**CLI command = prompt pro orchestrátor.** `grantio scout tacr` → orchestrátor
rozhodne, jaké sub-agenty spustit a v jakém pořadí.

**Source = projekt.** Každý zdroj (URL) je "projekt" à la claude.ai.
Každý běh sub-agenta = 1 "chat" (Agent SDK session) v rámci projektu.

**13 sub-agentů, asymetrické úrovně:** Každý existuje jen na úrovních,
kde dává smysl. Žádné zbytečné wrappery.

**Pravidlo:** Agent = potřebuješ úsudek. Kód = potřebuješ determinismus.

**Model:** Orchestrátor + config agenti = Sonnet. Extraction = Haiku (cost).

**Self-awareness:** Každý agent ví co umí a co potřebuje. Orchestrátor zná
schopnosti a požadavky všech agentů + umí se podívat do workspace a říct
"tyto runy existují, tyto mají relevantní data pro to co chceš".

---

## Agent Capabilities & Requirements

Každý agent má **deklarativní popis** svých schopností a požadavků.
Orchestrátor tyto popisy zná (jsou součástí orchestration SKILL.md)
a používá je k rozhodování.

### Proč to potřebujeme

Když se orchestrátora zeptám: *"co potřebuješ ke spuštění config-opportunity?"*
musí umět říct:

> Config-opportunity potřebuje:
> 1. **listing URLs** — výstup config-catalog runu (listing_urls.json)
> 2. **opportunity scout** — scouts/opportunity-sample.json (volitelné, zlepšuje kvalitu)
> 3. **catalog config** — configs/catalog.v{N}.yml (ví jak vypadá listing)
>
> V projektu tacr-cz máme:
> - config-catalog run `2026-03-09-001-cfg-cat` (v1, 100 URLs, approved)
> - config-catalog run `2026-03-10-003-cfg-cat` (v2, 102 URLs, approved)
> - opportunity scout z 2026-03-09
>
> Doporučuji použít nejnovější approved catalog run (v2, 102 URLs).

### Agent descriptor (v orchestration SKILL.md)

```yaml
agents:
  scout-source:
    produces:
      - scouts/{date}_source.json
      - memory/structure.md
    requires: []                           # nic — první agent
    description: "Analyzuje web, najde katalogy, určí typ zdroje"

  scout-catalog:
    produces:
      - scouts/{date}_catalog-{name}.json
    requires:
      - scouts/{date}_source.json          # musí vědět jaké katalogy existují
    description: "Zmapuje katalog — listing selektory, pagination, pole"

  scout-opportunity:
    produces:
      - scouts/{date}_opportunity-sample.json
    requires:
      - scouts/{date}_catalog-{name}.json  # sample detail URLs ze scout-catalog
    description: "Zmapuje detail výzvy — schema mapping, pole, přílohy"

  config-catalog:
    produces:
      - configs/catalog.v{N}.yml
      - runs/{run-id}/listing_urls.json
    requires:
      - scouts/{date}_source.json
      - scouts/{date}_catalog-{name}.json
    optional:
      - scouts/{date}_opportunity-sample.json
      - runs/{prev-run}/validation.json    # feedback z validatoru (attempt > 1)
    description: "Generuje listing YAML config, spouští scraper, získává URLs"

  validator-catalog:
    produces:
      - runs/{run-id}/validation.json
    requires:
      - runs/{run-id}/listing_urls.json    # co validovat
      - scouts/{date}_source.json          # expected count
    description: "Ověřuje listing URLs — existují? Počet sedí? Approve/feedback"

  config-opportunity:
    produces:
      - configs/opportunity.v{N}.yml
      - runs/{run-id}/items.json
      - runs/{run-id}/report.json
    requires:
      - runs/{cfg-cat-run}/listing_urls.json  # MUSÍ mít listing URLs
      - configs/catalog.v{N}.yml              # ví jak vypadá listing
    optional:
      - scouts/{date}_opportunity-sample.json  # zlepšuje první pokus
      - runs/{prev-run}/validation.json        # feedback z validatoru
    description: "Generuje detail config, staví na vzorku, ověřuje na všech"

  validator-opportunity:
    produces:
      - runs/{run-id}/validation.json
    requires:
      - runs/{run-id}/items.json           # co validovat
      - runs/{run-id}/report.json          # extraction stats
    description: "Typově specifická validace dat — approve/feedback"

  validator-source:
    produces:
      - runs/{run-id}/source-validation.json
    requires:
      - "alespoň 1 approved validator-opportunity run"
    description: "Agregovaná kvalita, trendy, cross-catalog porovnání"

  analyst-source:
    produces:
      - runs/{run-id}/analyst.json
      - hints.md (append)
    requires:
      - runs/{run-id}/items.json
      - runs/{run-id}/validation.json      # validator výsledek
    optional:
      - memory/*
      - hints.md
    description: "Obsahový review, gate-keeping, navrhuje hinty"
```

### Orchestrátor workspace awareness

Orchestrátor má tool `list_runs(source)` který vrací přehled všech runů
s meta.json. Na základě agent descriptorů + run přehledu umí:

1. **Odpovědět co potřebuje** — "ke spuštění X potřebuji Y"
2. **Najít relevantní runy** — "v projektu máme tyto runy s tímhle výsledkem"
3. **Doporučit vstupy** — "doporučuji použít run Z (nejnovější approved)"
4. **Detekovat chybějící závislosti** — "nemůžu spustit config-opportunity,
   chybí approved config-catalog run"

```
Příklad interakce:

Uživatel: grantio build tacr-cz --step config-opportunity

Orchestrátor:
  1. Přečte agent descriptor pro config-opportunity
     → requires: listing_urls.json, catalog config
  2. list_runs("tacr-cz") → najde runy
  3. Filtruje: runy agenta "config-catalog" se statusem "approved"
  4. Najde: run 2026-03-10-003-cfg-cat (v2, 102 URLs, approved)
  5. Sestaví prompt pro config-opportunity:
     "Workspace: sources/tacr-cz/
      Listing URLs: runs/2026-03-10-003-cfg-cat/listing_urls.json
      Catalog config: configs/catalog.v2.yml
      ..."
  6. Dispatchi config-opportunity

Alternativa — žádný approved catalog run:
  Orchestrátor: "Nemůžu spustit config-opportunity pro tacr-cz.
  Chybí approved config-catalog run. Máme:
  - run 2026-03-09-001-cfg-cat (v1, needs_fix — 3 broken URLs)
  Spustit config-catalog znovu? (grantio build tacr-cz --step config-catalog)"
```

---

## Agent mapa

```
AGENT              LEVEL        TOOLS                              NOTES
──────────────────────────────────────────────────────────────────────────────
ORCHESTRÁTOR       -            dispatch_agent,read/write_status,  Řídí pipeline
                                monitoring,run_config,notify,      CLI → prompt
                                source_memory,hints,gate_check

scout-source       source       WebFetch,WebSearch,Read            → katalogy, typ zdroje
scout-catalog      catalog      WebFetch,Read                      → listing URLs, pagination
scout-opportunity  opportunity  WebFetch,Read                      → schema mapping, pole

config-catalog     catalog      Read,Write,Edit,Bash,WebFetch,     → listing YAML config
                                scrapy_run,cheerio_run,            → MUSÍ získat VŠECHNY listings
                                playwright_run

config-opportunity opportunity  Read,Write,Edit,Bash,WebFetch,     → detail YAML config
                                scrapy_run,cheerio_run,            → staví na vzorku, ověřuje na všech
                                playwright_run

validator-catalog  catalog      Read,Bash,WebFetch                 → URL check, count vs scout,
                                                                    approve nebo feedback pro config
validator-opp      opportunity  Read,Bash,WebFetch                 → typově specifická kvalita,
                                                                    approve nebo feedback pro config
validator-source   source       Read,Bash                          → aggregate quality + trends

fixer-catalog      catalog      Read,Write,Edit,Bash,WebFetch,     → oprava listing [fáze 2]
                                scrapy_run,cheerio_run,
                                playwright_run
fixer-opportunity  opportunity  Read,Write,Edit,Bash,WebFetch,     → oprava detail [fáze 2]
                                scrapy_run,cheerio_run,
                                playwright_run

analyst-source     source       Read,Bash                          → kvalita, hinty, gate-keeping

dedup-opportunity  opportunity  Read                               → pair judgment [fáze 2]
──────────────────────────────────────────────────────────────────────────────
                                                                    1 orchestrátor + 13 sub-agentů
```

### Proč toto rozdělení (ne 18 symetrických, ne 5 polymorfních)

| Agent × Level | Proč ANO | Proč NE |
|---------------|----------|---------|
| validator-catalog | Ověřuje listing URLs, count vs scout, feedback loop s config-catalog | — |
| validator-opportunity | Typově specifická kvalita (grant_call 80%, subsidy 70%), feedback loop s config-opportunity | — |
| config-source | — | Source "config" = metadata ze scouta, ne generovaný YAML |
| fixer-source | — | Source-level problém = re-scout, ne fix |
| analyst-catalog | — | Catalog analýza je podmnožina source analýzy |
| analyst-opportunity | — | Validator-opportunity to pokrývá |
| dedup-source/catalog | — | Deduplikace je per opportunity pair |

---

## Scout agenti (3)

### scout-source

**Účel:** Analyzuj nový grantový web, najdi katalogy, urči typ zdroje.

```typescript
interface ScoutSourceInput {
  url: string;
  project_context: ProjectContext;
  attempt: number;
}

interface ScoutSourceOutput {
  source_type: "static" | "spa" | "api" | "pdf_portal" | "search_based" | "crawl";
  catalogs: Array<{
    name: string;
    url: string;
    estimated_count: number;
    strategy_hint: string;
  }>;
  anti_bot: boolean;
  auth_required: boolean;
  language: "cs" | "en" | "sk" | "mixed";
  confidence: number;
  issues: string[];
  suggestions: string[];
}
```

### scout-catalog

**Účel:** Zmapuj katalog — listing pattern, počet položek, paginace.

```typescript
interface ScoutCatalogOutput {
  listing_selector: string;
  item_count: number;
  pagination: {
    type: "page_number" | "load_more" | "infinite_scroll" | "api" | "none";
    total_pages?: number;
  };
  fields_available: string[];     // pole viditelná v listingu
  detail_url_pattern: string;     // jak se konstruuje URL detailu
  strategy: "html_catalog" | "js_catalog" | "api_catalog";
  confidence: number;
}
```

### scout-opportunity

**Účel:** Zmapuj detail výzvy — schema mapping, dostupná pole, přílohy.

```typescript
interface ScoutOpportunityOutput {
  fields: Record<string, {
    selector: string;
    extraction_method: "css" | "regex" | "llm" | "attribute";
    sample_value: string;
    confidence: number;
  }>;
  attachments: Array<{
    type: "pdf" | "xlsx" | "doc";
    url_pattern: string;
    contains_data: boolean;       // má strukturovaná data?
  }>;
  schema_coverage: number;        // % polí z GrantOpportunity
  confidence: number;
}
```

---

## Config agenti (2)

### Sdílení dat: FILESYSTEM, ne zprávy

Agenti nesdílejí data přes strukturované I/O. Sdílejí přes filesystem:
- Orchestrátor v **promptu** předá cestu k workspace: `sources/{slug}/`
- Agent si sám **přečte** co potřebuje (scouts/, configs/, runs/)
- Agent **zapíše** výstupy na konvencí dané místo

```
Orchestrátor prompt pro config-catalog:
  "Workspace: sources/dotace-example-cz/
   Přečti si scout findings v scouts/.
   Zapiš config do configs/catalog.v1.yml.
   Listing URLs ulož do runs/{run-id}/listing_urls.json."

Orchestrátor prompt pro config-opportunity:
  "Workspace: sources/dotace-example-cz/
   Přečti configs/catalog.v1.yml a runs/{run-id}/listing_urls.json.
   Vyber vzorek 5-10 URLs, stav detail config.
   Zapiš do configs/opportunity.v1.yml."
```

### config-catalog

**Účel:** Vygeneruj YAML config pro listing, získej VŠECHNY listing URLs.

**Prompt dostane:** cestu k workspace `sources/{slug}/`
**Agent čte:** `scouts/*.json` (scout findings)
**Agent píše:** `configs/catalog.v{N}.yml`, `runs/{run-id}/listing_urls.json`

**Flow:**
1. Read(`sources/{slug}/scouts/`) → scout findings
2. Generuje YAML config → Write(`configs/catalog.v1.yml`)
3. **Spustí listing scraper** (scrapy_run/cheerio_run/playwright_run)
4. Iteruje dokud listing nefunguje (test → fix → test)
5. Listing URLs → Write(`runs/{run-id}/listing_urls.json`)

### config-opportunity

**Účel:** Vygeneruj YAML config pro detail výzvy. Ověř na plném datasetu.

**Prompt dostane:** cestu k workspace `sources/{slug}/` + run-id z config-catalog
**Agent čte:** `scouts/opportunity-sample.json`, `configs/catalog.v1.yml`, `runs/{run-id}/listing_urls.json`
**Agent píše:** `configs/opportunity.v{N}.yml`, `runs/{run-id}/items.json`, `runs/{run-id}/report.json`

**Flow:**
1. Read(`runs/{run-id}/listing_urls.json`) → VŠECHNY URLs z config-catalog
2. Vybere vzorek (5-10 URLs), staví detail config
3. **Ověření:** Spustí na VŠECH URLs
4. Kontroluje kvalitu → iteruje nebo odevzdává
5. Write(`configs/opportunity.v1.yml`) + Write(`runs/{run-id}/items.json`)

---

## Validator agenti (3)

### validator-catalog

**Účel:** Ověří výstup config-catalog. Kontroluje listing URLs — existují? Počet sedí se scoutem?
Buď odsouhlasí, nebo vrátí config-catalog agentovi konkrétní zpětnou vazbu.

**Loop:** Orchestrátor pouští config-catalog → validator-catalog v cyklu (max 3 pokusy).
Validator buď schválí, nebo vrátí feedback. Orchestrátor předá feedback config-catalog v dalším pokusu (L5 vrstva).

```typescript
interface ValidatorCatalogOutput {
  verdict: "approve" | "needs_fix";
  checks: {
    urls_exist: { passed: number; failed: number; errors: string[] };
    count_vs_scout: { expected: number; actual: number; delta_pct: number };
    pagination_complete: boolean;    // dosáhli jsme poslední stránky?
    duplicates: number;              // duplicitní URLs
  };
  // Pokud needs_fix — konkrétní feedback pro config-catalog:
  feedback?: {
    summary: string;                 // "3 URLs vracejí 404, chybí stránky 8-10"
    broken_urls: string[];           // konkrétní nefunkční URLs
    missing_pages: number[];         // čísla stránek co chybí
    suggestions: string[];           // "Zkus jiný pagination selektor"
  };
}
```

### validator-opportunity

**Účel:** Ověří kvalitu extrahovaných opportunity dat. Pravidla se liší podle typu opportunity.
Buď odsouhlasí, nebo vrátí config-opportunity agentovi zpětnou vazbu.

**Loop:** Orchestrátor pouští config-opportunity → validator-opportunity v cyklu (max 3 pokusy).

**Typově specifická pravidla:**

| Typ opportunity | Povinná pole | Quality threshold | Speciální pravidla |
|-----------------|-------------|-------------------|-------------------|
| grant_call | title, provider, deadline, amount | 80% | deadline musí být v budoucnosti (nebo explicitně archiv) |
| subsidy_program | title, provider, description | 70% | může nemít deadline (průběžné) |
| news_announcement | — | — | QUARANTINE, jen basic check |
| completed_project | — | — | QUARANTINE, jen basic check |

```typescript
interface ValidatorOpportunityOutput {
  verdict: "approve" | "needs_fix";
  quality_score: number;
  items_by_type: Record<string, { count: number; quality: number }>;
  field_coverage: Record<string, number>;
  anomalies: string[];
  quarantine: { count: number; reasons: string[] };
  fabrication_check: {
    css_vs_llm_agreement: number;
    suspicious_fields: string[];
  };
  // Pokud needs_fix — konkrétní feedback pro config-opportunity:
  feedback?: {
    summary: string;                 // "deadline parsování selhává u 30% items"
    weakest_fields: Array<{ field: string; coverage: number; issue: string }>;
    sample_failures: Array<{ url: string; field: string; expected: string; got: string }>;
    suggestions: string[];           // "Zkus jiný date format regex"
  };
}
```

### validator-source

**Účel:** Agregovaná kvalita across katalogů, trend detection, cross-catalog porovnání.

```typescript
interface ValidatorSourceOutput {
  overall_score: number;
  catalog_scores: Record<string, number>;
  trends: {
    direction: "improving" | "stable" | "degrading";
    delta: number;
  };
  cross_catalog_issues: string[];
  recommendations: string[];
}
```

---

## Analyst agent (1)

### analyst-source

**Účel:** Obsahový expert na grantová data. Gate-keeper. Navrhuje hinty.

```typescript
interface AnalystSourceInput {
  action: "review" | "compare" | "suggest_hints" | "gate_check";
  items: GrantItem[];
  source_metadata: SourceMetadata;
  project_context: ProjectContext;
  quality_thresholds: QualityThresholds;
}

interface AnalystSourceOutput {
  verdict: "approve" | "needs_work" | "reject";
  quality_score: number;
  issues: QualityIssue[];         // konkrétní problémy
  hints: string[];                // navržené hinty pro zdroj
  field_analysis: Record<string, FieldQuality>;
  content_assessment: string;     // obsahová stránka dat
  recommendations: string[];
}
```

**Zodpovědnosti:**
- Kontrola kvality (úplnost, konzistence, smysluplnost)
- **Obsahové** posouzení — rozumí grantovým datům, ne jen technice
- Navrhování hintů pro problematické zdroje
- Gate-keeping: "tato data jsou dostatečně kvalitní pro produkci"

---

## Fixer agenti (2) — fáze 2

### fixer-catalog / fixer-opportunity

**Účel:** Automatická oprava broken scraperů. Delegován monitorem.

> Tento agent je plánovaný pro fázi 2.

**Trigger:** Monitor detekuje quality drop nebo scraper failure.
**Flow:** Analyzuj co se rozbilo → čti memory (failures, decisions) →
čti hinty → WebFetch aktuální HTML → generuj nový config → otestuj →
předlož ke schválení.

---

## Dedup judge (1) — fáze 2

### dedup-opportunity

**Účel:** Rozhodnutí "jsou tyto dvě příležitosti stejné?" na candidate pairs.

> Plánován pro fázi 2. Candidate pair selection = deterministický kód
> (fuzzy match na title + provider + deadline). Judge = agent.

```typescript
interface DedupJudgeInput {
  pair: [GrantItem, GrantItem];
  context: { source_a: string; source_b: string };
}

interface DedupJudgeOutput {
  is_duplicate: boolean;
  confidence: number;
  primary: "a" | "b";            // který záznam je úplnější
  reasoning: string;
}
```

---

## Co NENÍ agent (je to kód / tool)

```
- Scrapy/Cheerio/Playwright run  → tool volaný config agenty a orchestrátorem
- Opportunity-level validace     → JSON Schema + range checks + encoding
- Catalog-level data agregace    → SQL queries
- Source-level quality agregace  → SQL over catalog scores
- Dedup candidate selection      → fuzzy matching algorithm
- Scheduling                     → cron
- Config git operations          → git CLI
- Notification routing           → Telegram API (tool pro orchestrátor)
```

---

## Orchestrátor (JE agent)

Orchestrátor JE Claude agent se skills a tools. Viz `orchestrator.md`.

Zodpovědnosti:
1. Přijímá CLI commands jako prompty
2. Dispatchi sub-agenty a monitoruje průběh
3. Čte logy když stdout/stderr selže (fallback monitoring)
4. Rozhoduje na základě kontextu (ne hardcoded pravidla)
5. Aplikuje quality gates
6. Spouští scraper s konkrétní config verzí (`run_config` tool)

---

## Verzování souborů

Každý soubor ve workspace je verzovaný nebo append-only. Žádné tiché přepsání.

```
sources/{slug}/
  scouts/
    {YYYY-MM-DD}_source.json              # datované, re-scout = nový soubor s novým datem
    {YYYY-MM-DD}_catalog-{name}.json      # totéž
    {YYYY-MM-DD}_opportunity-sample.json

  configs/
    catalog.v1.yml                        # IMMUTABLE — nová verze = nový soubor
    catalog.v2.yml                        # v2 = po feedback loop z validatoru
    opportunity.v1.yml
    opportunity.v2.yml

  runs/
    {YYYY-MM-DD}-{seq}-{agent}/           # "2026-03-09-001-cfg-cat"
      meta.json                           # KDO: agent, config_version, attempt, parent_run
      listing_urls.json                   # config-catalog výstup
      items.json                          # config-opportunity výstup
      report.json                         # extraction stats
      validation.json                     # validator verdict + feedback
      analyst.json                        # analyst verdict
      session.json                        # Agent SDK session (cost, duration)
      log.txt                             # stdout/stderr (pro monitoring fallback)

  memory/
    structure.md                          # REPLACE — aktuální porozumění
    failures.md                           # APPEND-ONLY — nikdy nesmazat
    decisions.md                          # APPEND-ONLY — důvody rozhodnutí

  status.json                             # aktuální stav + state history array
  hints.md                                # APPEND-ONLY (jen analyst píše, ostatní čtou)
```

### Run ID formát

`{date}-{seq}-{agent}` — např. `2026-03-09-001-cfg-cat`, `2026-03-09-002-val-cat`

Agent zkratky: `sct-src`, `sct-cat`, `sct-opp`, `cfg-cat`, `cfg-opp`,
`val-cat`, `val-opp`, `val-src`, `analyst`, `fixer-cat`, `fixer-opp`, `dedup`

### meta.json (každý run)

```json
{
  "run_id": "2026-03-09-002-val-cat",
  "agent": "validator-catalog",
  "config_version": "v1",
  "attempt": 1,
  "parent_run": "2026-03-09-001-cfg-cat",
  "started_at": "2026-03-09T10:01:00Z",
  "finished_at": "2026-03-09T10:01:10Z",
  "status": "completed",
  "cost": "$0.03"
}
```

### Config verze = immutable

Config `v1` se nikdy nepřepisuje. Pokud validator řekne `needs_fix`,
config agent zapíše `v2`. Orchestrátor ví, že `v2` existuje díky
validator feedbacku a meta.json linkům.

---

## Decision log — kam agenti zapisují rozhodnutí

Každý agent zapisuje na **dvě místa**:

### 1. Run-level (strukturovaný, per-run)

```
runs/{run-id}/
  meta.json          ← KDO, KDY, ZA KOLIK, ATTEMPT číslo
  validation.json    ← validator verdict + feedback (pokud needs_fix)
  analyst.json       ← analyst verdict + content assessment
  report.json        ← extraction stats (field coverage, quarantine)
```

### 2. Source-level (persistent, across-runs)

```
memory/decisions.md  ← APPEND-ONLY log (kdo rozhodl co a proč)
memory/failures.md   ← APPEND-ONLY (co selhalo, proč, jak se to řešilo)
hints.md             ← APPEND-ONLY (analyst navrhuje, orchestrátor/člověk řeší)
status.json          ← aktuální stav + state_history pole
```

### Příklad decisions.md

```markdown
## 2026-03-09 config-catalog v1 (run 2026-03-09-001-cfg-cat)
- 100 listing URLs, pagination 10 pages
- validator-catalog: APPROVE (100 URLs, 10/10 HTTP 200)

## 2026-03-09 config-opportunity v1 (run 2026-03-09-003-cfg-opp)
- 100 items extracted, quality 82%
- 97 grant_call, 2 news (Q), 1 unknown (Q)
- validator-opportunity: APPROVE (grant_call 82% > 80%)
- analyst: APPROVE — castky realne, hint: eligibility z PDF

## 2026-03-09 PRODUCTION GATE
- val-cat ✓, val-opp ✓, analyst ✓
- human approved at 11:15
```

---

## Config loop — orchestrátor řídí retry

Orchestrátor pouští config + validator v cyklu. Loop logika je v
**orchestration SKILL.md** — orchestrátor je agent, ne hardcoded kód.

### Pravidla (z SKILL.md)

```
CONFIG-VALIDATE LOOP (per level: catalog, opportunity):
  max_attempts = 3
  FOR attempt = 1 to max_attempts:

    1. DISPATCH config-{level} agent
       Prompt obsahuje:
       - L1: workspace path, kam číst/psát
       - L4: hints (pokud existují)
       - L5 (attempt > 1): cesta k předchozí validation.json s feedbackem
       - L6: memory/ (failures, decisions)

    2. WAIT for config agent to finish
       → config agent zapíše: configs/{level}.v{attempt}.yml + runs/{run-id}/

    3. DISPATCH validator-{level} agent
       Prompt: workspace path + run-id z kroku 2

    4. READ validator verdict (runs/{run-id}/validation.json)

    5. IF verdict == "approve":
       → LOG to memory/decisions.md
       → CONTINUE to next phase
       → BREAK loop

    6. IF verdict == "needs_fix":
       → LOG feedback to memory/decisions.md
       → LOG to memory/failures.md
       → INCREMENT attempt
       → CONTINUE loop (config agent gets feedback path in L5)

  IF all attempts exhausted:
    → write_status(ESCALATED)
    → notify(telegram, "source {slug} needs human help after {max_attempts} attempts")
    → LOG to memory/failures.md
```

### Co je v L5 (attempt > 1)

```
## L5: Předchozí pokus selhal
Attempt: 2 / 3
Předchozí validation feedback: runs/2026-03-09-002-val-cat/validation.json

Validator říká:
- 3 URLs vracejí 404 (broken_urls v JSONu)
- Stránky 8-10 chybí (pagination nedoběhla)
- Návrh: "Zkus jiný pagination selektor"

NEOPAKUJ stejný přístup. Přečti předchozí feedback a zkus jinak.
```

### Orchestrátor rozhoduje, ne kód

Loop pravidla jsou v SKILL.md, ale orchestrátor (Claude agent) JE
rozhodovatel. Může:
- Po 1 selhání validator-catalog rovnou přeskočit na jiný scraping tool
  (scrapy → playwright) pokud pozná z feedbacku, že web potřebuje JS
- Rozhodnout, že 2 pokusy stačí (pokud feedback ukazuje fundamentální problém)
- Číst logy když sub-agent selže (monitoring tools)

---

## Skills per agent

Každý agent dostane v promptu relevantní SKILL.md soubory.
Orchestrátor má vlastní orchestration SKILL.md.

```
SKILL                    AGENT                           PROČ
─────────────────────────────────────────────────────────────────────
orchestration            orchestrátor                    state machine, loop pravidla,
                                                        gate podmínky, escalation rules

grant-schemas            scout-source                    ví co hledat (typy zdrojů, katalogů)
                         scout-catalog                   ví jaká pole očekávat v listingu
                         scout-opportunity               mapuje na GrantOpportunity schema
                         config-opportunity              field definitions pro extraction config
                         validator-opportunity            type-specific povinná pole + thresholds
                         analyst-source                  obsahové posouzení (reálné castky?)

yaml-config              config-catalog                  generuje YAML config
                         config-opportunity              generuje YAML config

czech-parsing            scout-source                    rozpozná CZ formáty na webu
                         scout-opportunity               parsuje vzorkové hodnoty
                         config-catalog                  nastavuje transforms v YAML
                         config-opportunity              nastavuje transforms v YAML
                         validator-opportunity            ověřuje parsované hodnoty

extraction-pipeline      scout-opportunity               rozumí 6-level fallback hierarchii
                         config-opportunity              implementuje extraction pipeline v YAML

quality-scoring          validator-catalog               URL check thresholds, count tolerance
                         validator-opportunity            type-specific thresholds (grant 80%, subsidy 70%)
                         validator-source                 aggregate scoring, trends
                         analyst-source                  gate-keeping thresholds

anti-fabrication         config-opportunity              Null > guess, dual extraction, synthesize rules
                         validator-opportunity            fabrication check (CSS vs LLM agreement)
─────────────────────────────────────────────────────────────────────
```

### Proč toto přiřazení

**grant-schemas** je nejrozšířenější — kdo pracuje s grantovými daty, potřebuje znát
schema. Config-catalog ho NEMÁ — pracuje jen s listing selektory, ne s obsahem.
Validator-catalog ho NEMÁ — kontroluje jen URLs a počty.

**yaml-config** mají JEN config agenti — nikdo jiný negeneruje YAML.

**czech-parsing** mají agenti co parsují CZ obsah. Validator-catalog ho NEMÁ —
kontroluje jen URLs, ne textový obsah.

**extraction-pipeline** mají jen opportunity-level agenti — listing je jednoduchý
(CSS selektory), nepotřebuje 6-level fallback.

**quality-scoring** mají jen validátoři a analyst — config agenti se soustředí
na generování, ne na posuzování.

**anti-fabrication** má config-opportunity (aplikuje pravidla při generování)
a validator-opportunity (ověřuje, že pravidla byla dodržena). Nikdo jiný.

---

## Poznatky z PoC (knowledge extraction)

### Co PoC dělá jinak a proč to funguje

**1. Jeden discovery agent, ne 3 scout agenti.**
PoC má single-pass discovery: URL → jeden Claude call → vrátí source info
+ katalogy + sample opportunity mapping. Funguje, ale výstup je příliš velký
pro jeden kontext. Naše 3-agent dekompozice je lepší.

**2. Config loop = 2,592 řádků god command.**
`loop_create_config.py` dělá vše: discovery, create, improve, test, quality,
stagnation. L1 doporučení: rozdělit na ConfigGenerator, TestExecutor,
QualityEvaluator, CatalogAssembler. → Mapuje se na naše config-catalog +
config-opportunity + validator-catalog + analyst-source.

**3. Improve mode signály (pro config agenty):**
- Content mix warning (non-grant items expected to miss fields)
- LLM vs CSS mismatches (selektory asi špatné)
- LLM-only fields (broken/missing selektory)
- Weakest fields (<50% completeness)
- Previous attempt summaries (neopakovat failed přístupy)

**4. Multi-catalog bug:**
11 bugů, 4 critical. IROP stuck at 84.9% for 11 runs. Příčina: config loop
testoval proti wrong/old config. Single-catalog (86%) fungoval, maskoval
problém. → V nové architektuře: per-catalog izolace od začátku.

**5. Pipeline priorities (zachovat pořadí):**
```
100: ValidationPipeline (stub v PoC — implementovat!)
150: ContentHashFilesPipeline (SHA256 cache)
160: DocumentProcessingPipeline (PDF → markdown)
170: LlmExtractionPipeline (1 LLM call per grant)
200: MergePipeline (detail > listing, type coercion)
210: CatalogInheritancePipeline (provider, contact, lifecycle)
220: LifecycleDetectionPipeline
300: StoragePipeline
```

**6. Extraction je framework-agnostic.**
Engine používá `parsel.Selector`, ne Scrapy API. Port do TS je straightforward.

**7. LLM extraction = 1 call per grant, ALL fields at once.**
Ne per-field calls. Kombinovaný markdown: HTML + document přílohy.
Synthesized fields (ideal_grantee, how_to_apply) povoleny.

**8. Aktuální náklady:**
- Discovery: $0.60-$1.50 (Sonnet)
- Config creation: $1.50-$3.00 (Sonnet × 3-10 attempts)
- Extraction: $0.10-$0.75 per source (Haiku)
- Full batch 359 zdrojů: $35-$270 extraction only
