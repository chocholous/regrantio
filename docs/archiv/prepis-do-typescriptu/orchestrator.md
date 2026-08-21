# Orchestrator — Agent-based Orchestration

## Princip

**Orchestrátor JE agent.** Ne deterministický kód, ale Claude agent se skills
a tools, který dispatchi sub-agenty. Rozumí kontextu, umí reagovat na
neočekávané situace, čte logy když selže stdout/stderr.

**CLI commands = Agent SDK prompty/skills.** `grantio scout tacr` není Commander.js
command — je to prompt pro orchestrátor agenta, který spustí scout pipeline.

Metafora: **Claude.ai projects.** Zdroj = projekt. Agent run = chat (session).
Orchestrátor = hlavní agent v projektu, sub-agenti = specializované tasky.

**Filesystem je databáze.** Git je verzování. Server přijde později.

---

## Orchestrátor agent

```
Orchestrátor agent
├── SKILLS: orchestration SKILL.md (state machine, rozhodovací pravidla)
├── TOOLS:
│   ├── dispatch_agent(type, input)    # spustí sub-agenta
│   ├── read_status(source)            # čte status.json
│   ├── write_status(source, phase)    # updatne stav
│   ├── read_run_log(source, run_id)   # čte logy agentů (fallback monitoring)
│   ├── read_run_output(source, run_id)# čte výstupy (items.json, report.json)
│   ├── list_runs(source, filter?)      # přehled runů (filtr: agent, status, config_version)
│   ├── source_memory(...)             # persistent knowledge
│   ├── hint_read/hint_write           # hinty
│   ├── gate_check(source)             # kontrola gate podmínek
│   ├── notify(channel, message)       # Telegram notifikace
│   └── run_config(source, version)    # spustí scraper s danou config verzí
│
├── MONITORING TOOLS (když selže stdout/stderr):
│   ├── tail_agent_log(run_id, lines)  # poslední řádky logu sub-agenta
│   ├── check_agent_status(run_id)     # běží/skončil/failed?
│   └── read_agent_stderr(run_id)      # stderr sub-agenta
│
└── SUB-AGENTI: scout-*, config-*, validator-*, analyst-*
```

**Proč agent a ne kód:** Orchestrátor potřebuje úsudek — rozhoduje se na základě
kvality dat, obsahu logů, kontextu předchozích selhání. Deterministický kód
by potřeboval hardcoded pravidla pro každý edge case.

---

## Workspace filesystem

```
workspace/
├── .claude/
│   └── skills/                     # SKILL.md soubory (viz skills.md)
├── shared/
│   ├── templates/                  # YAML templates per strategy
│   │   ├── static-listing.yaml
│   │   ├── dynamic-listing.yaml
│   │   ├── api-backed.yaml
│   │   └── document-portal.yaml
│   └── prompts/                    # Prompt soubory (viz prompts.md)
└── sources/
    └── {slug}/                     # Jeden "projekt" per zdroj
        ├── scouts/
        │   ├── 2026-03-09_source.json
        │   ├── 2026-03-09_catalog-vyzvy.json
        │   └── 2026-03-09_opportunity-sample.json
        ├── configs/
        │   ├── catalog.yml          # Aktuální config
        │   ├── opportunity.yml
        │   └── history/             # Předchozí verze
        │       ├── catalog.v1.yml
        │       └── catalog.v2.yml
        ├── runs/
        │   └── {run-id}/
        │       ├── items.json       # Nascrapevaná data
        │       ├── report.json      # Validační report
        │       └── session.json     # Agent SDK session metadata
        ├── memory/
        │   ├── structure.md         # Co agent ví o struktuře webu
        │   ├── failures.md          # Historie selhání (append-only)
        │   └── decisions.md         # Rozhodnutí a důvody
        ├── hints.md                 # Hinty (source-level)
        └── status.json              # Stav projektu (state machine)
```

---

## Project Lifecycle (State Machine)

```
                    ┌──────────────┐
         CLI:add    │   CREATED    │  Nový projekt (URL zadána)
                    └──────┬───────┘
                           │ auto / CLI:scout
                    ┌──────▼───────┐
                    │  SCOUTING    │  scout-source → scout-catalog(s)
                    │              │  → scout-opportunity (sample)
                    └──────┬───────┘
                           │ scouts done
                    ┌──────▼───────┐
                    │  BUILDING    │  config-catalog + config-opportunity
                    │              │  + test run + validation
                    └──────┬───────┘
                           │ configs ready + tested
                    ┌──────▼───────┐
                    │  REVIEWING   │  analyst-source posuzuje kvalitu
                    │              │  (gate-keeper)
                    └──────┬───────┘
                           │ analyst approved
                    ┌──────▼───────┐
                    │ PENDING_GATE │  Čeká na lidské schválení
                    │              │  (Telegram + CLI)
                    └──────┬───────┘
                           │ human approved
                    ┌──────▼───────┐
                    │  PRODUCTION  │  Config ready, scheduler připraven
                    │              │
                    └──────────────┘
```

### Chybové přechody (z jakéhokoli stavu)

```
Jakýkoli stav
  ├── confidence < threshold ──→ RETRY (s upraveným promptem, L5 vrstva)
  ├── attempt > max_retries ──→ ESCALATED (čeká na člověka)
  ├── cost > budget ──→ PAUSED
  ├── human reject ──→ RETRY nebo ABANDONED
  └── fatal error ──→ FAILED
```

---

## CLI = Slash commands (Agent SDK native)

Každý CLI command je **slash command** — `.claude/commands/*.md` soubor.
Slash command = prompt s kontextem pro orchestrátor agenta.

```bash
# === Toto JSOU .claude/commands/*.md soubory ===
# === Orchestrátor je čte jako prompty s argumenty ===

/add <url> [--name tacr]                  # → vytvoř projekt
/add --bulk urls.txt                      # → vytvoř N projektů

/scout <source>                           # → spusť scout pipeline
/build <source> [--step X]                # → spusť build pipeline (nebo jen krok X)
/validate <source>                        # → spusť validaci
/analyze <source>                         # → spusť analyst review

/run <source> <config_version>            # → spusť scraper s config verzí
/runs <source> [--agent X] [--status Y]   # → přehled runů (workspace awareness)
/hint <source> "text"                     # → přidej hint
/status [source]                          # → zobraz stav
/gate approve|reject <source>             # → gate rozhodnutí
```

### Slash command = prompt + kontext

Každý `.claude/commands/*.md` obsahuje:
- **frontmatter**: `allowed-tools`, `description`, `argument-hint`
- **!`shell`**: inline shell pro aktuální kontext (status.json, seznam scouts...)
- **@file**: reference na soubory
- **$1, $2**: argumenty od uživatele
- **Task**: instrukce co orchestrátor má dělat

Viz `architecture.md` pro kompletní příklady slash commands.

### Výstup: dual-stream

```bash
# stderr: progress, emoji, human-readable
# stdout: JSON (pipeable)

$ grantio scout tacr
🔍 Scouting tacr.cz...
  ✅ 3 katalogy nalezeny
  ✅ 47 příležitostí v katalogu "Veřejné soutěže"
  ✅ Schema mapping: 14/18 polí
📄 Report: sources/tacr-cz/scouts/2026-03-09_source.json

$ grantio scout tacr --json | jq '.catalogs | length'
3

$ grantio status
 Source       Catalogs  Grants  Complete  Quality  Config  Last Run
 tacr-cz      3         47     82%       91%      v2      2h ago
 dotaceeu-cz  7         312    74%       85%      v1      1d ago
 mzp-cz       1         23     58% ⚠    72% ⚠   v1      3d ago
```

---

## Orchestrátor rozhodovací logika

Orchestrátor je agent — má SKILL.md s těmito pravidly, ale rozhoduje se
sám na základě kontextu. Níže je popis LOGIKY, ne kódu:

### Build pipeline (správný flow)

Orchestrátor předává sub-agentům **cestu k workspace**, ne data.
Sub-agenti si čtou/píšou na filesystem. Orchestrátor ví kde hledat výstupy.

**Orchestrátor zná schopnosti a požadavky** každého agenta (viz agents.md,
"Agent Capabilities & Requirements"). Před dispatchem:
1. Přečte agent descriptor → ví co agent potřebuje jako vstup
2. `list_runs(source)` → najde existující runy s relevantními výstupy
3. Vybere nejlepší vstupy (nejnovější approved) → předá cesty v promptu

```
1. SCOUT
   Orchestrátor → scout-source:
     prompt: "Workspace: sources/{slug}/. Prozkoumej {url}."
     agent čte: nic (první run)
     agent píše: scouts/{date}_source.json, memory/structure.md

   Orchestrátor čte: scouts/source.json → katalogy nalezeny
   Orchestrátor → scout-catalog (per katalog, paralelně):
     prompt: "Workspace: sources/{slug}/. Zmapuj katalog {catalog_url}."
     agent čte: scouts/{date}_source.json
     agent píše: scouts/{date}_catalog-{name}.json

   Orchestrátor → scout-opportunity:
     prompt: "Workspace: sources/{slug}/. Zmapuj detail na vzorku z scouts/."
     agent čte: scouts/{date}_catalog-*.json (vybere sample URL)
     agent píše: scouts/{date}_opportunity-sample.json

2. CONFIG-CATALOG + VALIDATOR LOOP (max 3 attempts)
   Orchestrátor → config-catalog:
     prompt: "Workspace: sources/{slug}/. Scout findings v scouts/.
              Zapiš config do configs/catalog.v{N}.yml.
              Listing URLs do runs/{run-id}/listing_urls.json."
     (attempt > 1): "Předchozí pokus selhal. Feedback: runs/{prev}/validation.json"
     agent čte: scouts/*.json, (případně předchozí feedback)
     agent píše: configs/catalog.v{N}.yml, runs/{run-id}/listing_urls.json
     agent volá: scrapy_run / cheerio_run / playwright_run

   Orchestrátor → validator-catalog:
     prompt: "Workspace: sources/{slug}/. Zkontroluj runs/{run-id}/."
     agent čte: runs/{run-id}/listing_urls.json, scouts/{date}_source.json
     agent píše: runs/{run-id}/validation.json

   → IF approve: pokračuj
   → IF needs_fix: zpět na config-catalog s feedbackem (L5), nová config verze

3. CONFIG-OPPORTUNITY + VALIDATOR LOOP (max 3 attempts)
   Orchestrátor:
     → list_runs(source, agent="config-catalog", status="approved")
     → najde nejnovější approved run s listing_urls.json
     → předá cestu config-opportunity agentovi

   Orchestrátor → config-opportunity:
     prompt: "Workspace: sources/{slug}/.
              Listing URLs: runs/{approved-cfg-cat-run}/listing_urls.json
              Catalog config: configs/catalog.v{N}.yml
              Scout opportunity: scouts/{date}_opportunity-sample.json
              Zapiš config do configs/opportunity.v{M}.yml.
              Full run výsledky do runs/{run-id}/."
     (attempt > 1): "Feedback: runs/{prev}/validation.json"
     agent čte: listing_urls.json, scouts/opportunity-sample.json
     agent píše: configs/opportunity.v{M}.yml, runs/{run-id}/items.json, report.json

   Orchestrátor → validator-opportunity:
     prompt: "Workspace: sources/{slug}/. Zkontroluj runs/{run-id}/."
     agent čte: runs/{run-id}/items.json, report.json
     agent píše: runs/{run-id}/validation.json

   → IF approve: pokračuj
   → IF needs_fix: zpět na config-opportunity s feedbackem, nová config verze

4. ANALYST REVIEW
   Orchestrátor → analyst-source:
     prompt: "Workspace: sources/{slug}/. Posud kvalitu."
     agent čte: runs/{run-id}/*.json, memory/, hints.md
     agent píše: runs/{run-id}/analyst.json, hints.md (append)

5. PRODUCTION GATE
   Orchestrátor čte: runs/{run-id}/analyst.json → verdict
   Zkontroluje: val-cat ✓, val-opp ✓, analyst ✓
   → gate_check → notify → čeká na lidské schválení
```

**Princip:** Data tečou přes filesystem. Prompt obsahuje cesty, ne data.
Orchestrátor **ví co každý agent potřebuje** a **najde to** ve workspace.

### Monitoring / fallback

Orchestrátor má monitoring tools pro případ, kdy sub-agent selže
nebo stdout/stderr nefunguje:

```
orchestrátor:
  1. dispatch_agent("config-catalog", input)
  2. ... čeká na výsledek ...
  3. POKUD stdout selže:
     → tail_agent_log(run_id, 50)     # čti log přímo
     → check_agent_status(run_id)      # běží? spadl?
     → read_agent_stderr(run_id)       # co se stalo?
  4. Na základě logů rozhodne: retry / escalate / jiný přístup
```

---

## Workspace Awareness

Orchestrátor je konverzační agent — umí odpovídat na otázky o stavu projektu.
Díky agent descriptorům (co každý agent potřebuje/produkuje) + `list_runs` toolu
umí:

### "Co potřebuješ ke spuštění X?"

```
Uživatel: grantio build tacr-cz --step config-opportunity

Orchestrátor:
  → Čte agent descriptor pro config-opportunity:
    requires: listing_urls.json (z config-catalog), catalog config
    optional: opportunity scout, předchozí feedback
  → list_runs("tacr-cz", agent="config-catalog")
  → Najde: 2026-03-10-003-cfg-cat (v2, 102 URLs, approved)
  → Dispatchne config-opportunity s cestou k tomuto runu
```

### "Jaké runy máme?"

```
Uživatel: grantio status tacr-cz --runs

Orchestrátor → list_runs("tacr-cz"):

 Run ID                       Agent            Config  Status      Items  Quality
 2026-03-09-001-cfg-cat       config-catalog   v1      needs_fix   73     —
 2026-03-09-002-val-cat       validator-catalog v1     needs_fix   —      —
 2026-03-10-003-cfg-cat       config-catalog   v2      approved    102    —
 2026-03-10-004-val-cat       validator-catalog v2     approved    —      —
 2026-03-10-005-cfg-opp       config-opportunity v1    approved    98     82%
 2026-03-10-006-val-opp       validator-opp    v1      approved    —      82%
 2026-03-10-007-analyst       analyst-source   —       approved    —      82%
```

### "Můžu znovu spustit config-opportunity?"

```
Orchestrátor:
  → Ke spuštění config-opportunity potřebuji approved config-catalog run.
  → V projektu tacr-cz mám:
    - cfg-cat v2 (102 URLs, approved 2026-03-10) ← doporučuji
    - cfg-cat v1 (73 URLs, needs_fix — nepoužívat)
  → Chceš spustit s cfg-cat v2?
```

### "Chybí mi závislost"

```
Uživatel: grantio build novy-zdroj --step config-opportunity

Orchestrátor:
  → Nemůžu spustit config-opportunity pro novy-zdroj.
  → Chybí approved config-catalog run.
  → Máme: 0 config-catalog runů.
  → Nejdřív spusť: grantio build novy-zdroj --step config-catalog
```

### list_runs tool

```typescript
{
  name: "list_runs",
  description: "Přehled všech runů v projektu, s filtrováním",
  input_schema: {
    source: string,
    filter?: {
      agent?: string,          // "config-catalog", "validator-*", ...
      status?: string,         // "approved", "needs_fix", "completed"
      config_version?: string, // "v1", "v2"
      after?: string,          // ISO date
    }
  },
  handler: async (input) => {
    // Přečte runs/*/meta.json, filtruje, seřadí dle data
    // Vrátí: [{ run_id, agent, config_version, status, items_count, quality, cost, date }]
  }
}
```

---

## Bulk Operations

```bash
/add --bulk urls.txt         # vytvoří N projektů
/scout --all                 # scout pro všechny v CREATED stavu
/status                      # přehled všech zdrojů
```

V CLI fázi: sekvenční zpracování (nebo `--parallel N` s rate limitem).
V server fázi: true parallelism s concurrency limitem.

---

## Agent SDK Integration

Viz `architecture.md` sekce "SDK Implementation Map" pro kompletní příklad.

Klíčové body:
- Orchestrátor = `query()` s `preset: "claude_code"` + orchestration skill append
- Sub-agenti = `agents` config NEBO `.claude/agents/*.md` soubory
- Custom tools = `createSdkMcpServer()` → MCP tools (in-process)
- CLI = `.claude/commands/*.md` → slash commands s $1, $2 argumenty
- Skills = `.claude/skills/*/SKILL.md` → auto-discovered
- Sessions = SDK `session_id` + `resume` per sub-agent run

Každý sub-agent run uloží:
- `runs/{run-id}/meta.json` — kdo, kdy, za kolik, attempt, parent_run
- `runs/{run-id}/session.json` — Agent SDK session metadata
- `runs/{run-id}/items.json` — výstupní data (pokud relevantní)
- `runs/{run-id}/log.txt` — stdout/stderr (pro monitoring fallback)

---

## Implementace (src/ layout)

```
src/
├── index.ts                # Entry point — setup query() + MCP server + agents
├── tools/
│   ├── server.ts           # createSdkMcpServer — všechny custom tools
│   ├── workspace.ts        # read_status, write_status, list_runs, source_memory
│   ├── scraping.ts         # scrapy_run, cheerio_run, playwright_run, apify_run
│   ├── monitoring.ts       # tail_agent_log, check_agent_status, read_agent_stderr
│   └── notify.ts           # Telegram notifikace, gate_check
├── agents/
│   ├── definitions.ts      # 13 sub-agent definic (AgentDefinition objects)
│   └── prompts.ts          # Prompt builder (7-layer composition per agent)
├── workspace/
│   ├── project.ts          # Filesystem operations (create project, read/write)
│   ├── runs.ts             # Run management (create run-id, meta.json, list/filter)
│   └── config.ts           # YAML config versioning (v1 → v2 → ...)
├── lib/
│   └── output.ts           # CLI output formatting
└── skills/                 # Copied to workspace .claude/skills/ on init
    ├── grant-schemas/SKILL.md
    ├── yaml-config/SKILL.md
    └── ...
```

---

## Iterační plán CLI

```
Iterace 0:  grantio run <url> "<prompt>"     ← jen wrapper nad Agent SDK
Iterace 1:  grantio add + scout              ← scout pipeline (3 subagenty)
Iterace 2:  grantio build                    ← config gen + test + validate
Iterace 3:  grantio analyze + gate           ← analyst + production gate
Iterace 4:  grantio hint + status            ← collaboration basics
Iterace 5:  grantio add --bulk               ← bulk operations
Iterace 6:  --json flag, piping              ← unix philosophy
```

---

## Evoluce: CLI → Server

Až bude potřeba:

```
CLI (fáze 1)                    Server (fáze 2+)
────────────────────────────    ────────────────────────────
Filesystem storage       →      Postgres + filesystem
Sequential execution     →      Parallel with concurrency
Manual triggers (CLI)    →      Scheduler (cron) + webhooks
No API                   →      REST API (Hono)
Telegram via CLI         →      Telegram bot
No UI                    →      SvelteKit admin dashboard
Agent SDK direct         →      Agent SDK via queue/worker
```

Klíč: **Slash commands se stanou API endpointy.** Logika zůstane stejná,
změní se jen transport (filesystem → DB, slash command → HTTP request).
