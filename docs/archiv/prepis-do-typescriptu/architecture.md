# Architecture Overview — v4 (agent-based orchestration)

## Celkový pohled

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLI (grantio)                                │
│  Parsuje args → prompt pro orchestrátor agenta                  │
│  "grantio scout tacr" → "Scout source tacr-cz"                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │ prompt
┌──────────────────────────────▼──────────────────────────────────┐
│                  ORCHESTRATOR AGENT (Claude)                      │
│  Skills: orchestration.md (state machine, rozhodovací pravidla)  │
│  Tools:                                                          │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │ dispatch_  │ │ read/write │ │ monitoring │ │ run_config   │ │
│  │ agent      │ │ _status    │ │ (logs,     │ │ (scraper +   │ │
│  │            │ │            │ │  stderr)   │ │  version)    │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────────┘ │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                  │
│  │ source_    │ │ hint_read  │ │ gate_check │                  │
│  │ memory     │ │ hint_write │ │ + notify   │                  │
│  └────────────┘ └────────────┘ └────────────┘                  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ dispatch_agent
          ┌────────────────────┼────────────────────┐
          │                    │                     │
┌─────────▼────────┐ ┌────────▼────────┐ ┌─────────▼────────┐
│  SUB-AGENTI      │ │ SCRAPING TOOLS  │ │   FILESYSTEM     │
│  (Agent SDK)     │ │                 │ │                   │
│                  │ │ · scrapy_run    │ │ sources/{slug}/   │
│ · scout (3)     │ │ · cheerio_run   │ │   scouts/         │
│ · config (2)    │ │ · playwright_run│ │   configs/        │
│ · validator (2) │ │ · apify_run     │ │   runs/           │
│ · analyst (1)   │ │                 │ │   memory/         │
│ · fixer (2) [f2]│ │ Config agenti   │ │   hints.md        │
│ · dedup (1) [f2]│ │ volají přímo.   │ │   status.json     │
│                  │ │ Orchestrátor    │ │                   │
│ Prompt Composer  │ │ volá přes       │ │ shared/           │
│ (7 vrstev)      │ │ run_config.     │ │   prompts/        │
│                  │ │                 │ │   skills/         │
└──────────────────┘ └─────────────────┘ └───────────────────┘
                               │
                          výhledově (fáze 2+)
                               ▼
          ┌────────────────────┼────────────────────┐
          │                    │                     │
┌─────────▼────────┐ ┌────────▼────────┐ ┌─────────▼────────┐
│   POSTGRES       │ │  APIFY PLATFORM │ │   UI (SvelteKit) │
│   (Hetzner)      │ │                 │ │                   │
│ · sources        │ │ Template actors │ │ Dashboard         │
│ · runs           │ │ Scheduler       │ │ Source workspace  │
│ · hints          │ │ Proxy & storage │ │ Run replay        │
│ · memory         │ │                 │ │                   │
└──────────────────┘ └─────────────────┘ └───────────────────┘
```

---

## Klíčová rozhodnutí

| Rozhodnutí | Volba | SDK primitiv |
|------------|-------|-------------|
| Runtime | Hetzner VPS | — (infra) |
| Orchestrátor | Claude agent | `query()` + `systemPrompt: { preset: "claude_code", append }` |
| CLI commands | Slash commands | `.claude/commands/*.md` |
| Sub-agenti | 13, asymetrické úrovně | `agents: { name: { description, prompt, tools, model } }` |
| Skills | SKILL.md | `.claude/skills/*/SKILL.md` + `settingSources` |
| Custom tools | MCP servers | `createSdkMcpServer()` + `tool()` |
| Model per agent | Sonnet/Haiku | `model: 'sonnet' \| 'haiku'` v agent definition |
| Session per run | SDK sessions | `session_id` + `resume` / `forkSession` |
| Permissions | Per-agent tool restriction | `tools: [...]` v agent definition |
| Workspace | Filesystem + built-in tools | Read, Write, Edit, Glob, Grep (SDK built-in) |
| Project context | CLAUDE.md | `settingSources: ["project"]` |
| Storage (fáze 2+) | Postgres + filesystem | — (custom tool) |
| Config format | YAML | — (filesystem) |
| Notifications | Telegram | — (custom MCP tool) |
| Kompatibilita s PoC | Clean break | — |

### SDK-Native: Žádné hacky

Celá architektura mapuje **1:1 na SDK primitiva**. Nepotřebujeme žádný
vlastní framework, state machine kód, nebo command parser. SDK dělá:
- Orchestrátor = hlavní `query()` session
- Sub-agenti = `agents` config (SDK je dispatchi, monitoruje, sbírá výstupy)
- Skills = automaticky discovered SKILL.md soubory
- Tools = MCP servery (in-process, TypeScript)
- CLI = slash commands s argumenty, allowed-tools, file references
- Sessions = persist, resume, fork

---

## SDK Implementation Map

### Orchestrátor = hlavní query()

```typescript
import { query, createSdkMcpServer, tool } from "@anthropic-ai/claude-agent-sdk";

// Custom tools jako MCP server
const grantioTools = createSdkMcpServer({
  name: "grantio",
  version: "1.0.0",
  tools: [
    tool("list_runs", "Přehled runů v projektu", { source: z.string(), ... }, handler),
    tool("read_status", "Stav projektu", { source: z.string() }, handler),
    tool("write_status", "Update stavu", { source: z.string(), phase: z.string() }, handler),
    tool("scrapy_run", "Spustí Scrapy scraper", { config_path: z.string(), ... }, handler),
    tool("gate_check", "Kontrola gate podmínek", { source: z.string() }, handler),
    tool("notify", "Telegram notifikace", { channel: z.string(), message: z.string() }, handler),
    // ... source_memory, hint_read, hint_write, run_config
  ]
});

// Orchestrátor = hlavní session
for await (const message of query({
  prompt: "/scout tacr-cz",   // slash command → prompt
  options: {
    systemPrompt: { preset: "claude_code", append: orchestrationSkillContent },
    settingSources: ["project"],              // načte CLAUDE.md + skills + commands
    cwd: "/workspace",                        // workspace root
    mcpServers: { grantio: grantioTools },    // custom tools
    allowedTools: [
      "Read", "Write", "Edit", "Glob", "Grep", "Bash",
      "Skill", "Agent",                       // skills + subagenti
      "mcp__grantio__list_runs",
      "mcp__grantio__read_status",
      "mcp__grantio__write_status",
      "mcp__grantio__scrapy_run",
      // ...
    ],
    agents: {
      'scout-source': {
        description: 'Analyzuje grantový web, najde katalogy, určí typ zdroje',
        prompt: scoutSourcePrompt,            // L0+L2+L3 vrstvy
        tools: ['Read', 'Glob', 'Grep', 'mcp__grantio__source_memory',
                'WebFetch', 'WebSearch'],
        model: 'sonnet'
      },
      'config-catalog': {
        description: 'Generuje listing YAML config, spouští scraper, získává URLs',
        prompt: configCatalogPrompt,
        tools: ['Read', 'Write', 'Edit', 'Bash', 'WebFetch', 'Glob', 'Grep',
                'mcp__grantio__scrapy_run', 'mcp__grantio__source_memory'],
        model: 'sonnet'
      },
      'validator-catalog': {
        description: 'Ověřuje listing URLs — existují? Počet sedí? Approve/feedback',
        prompt: validatorCatalogPrompt,
        tools: ['Read', 'Bash', 'WebFetch', 'Glob', 'Grep'],
        model: 'sonnet'
      },
      // ... dalších 10 sub-agentů
    },
    maxTurns: 50,
    permissionMode: 'bypassPermissions',
  }
})) {
  handleMessage(message);
}
```

### Slash Commands = `.claude/commands/`

```
.claude/commands/
├── scout.md          → /scout <source>
├── build.md          → /build <source> [--step config-catalog|config-opportunity]
├── validate.md       → /validate <source>
├── analyze.md        → /analyze <source>
├── status.md         → /status [source]
├── runs.md           → /runs <source> [--agent X] [--status approved]
├── run.md            → /run <source> <config_version>
├── hint.md           → /hint <source> "text"
├── gate.md           → /gate approve|reject <source>
└── add.md            → /add <url> [--name slug]
```

#### Příklad: `.claude/commands/scout.md`

```markdown
---
description: Scout grantový zdroj — najdi katalogy, zmapuj strukturu
argument-hint: <source_slug>
allowed-tools: Agent, Read, Glob, Grep, mcp__grantio__read_status, mcp__grantio__write_status, mcp__grantio__list_runs
---

## Context
- Stav projektu: !`cat sources/$1/status.json 2>/dev/null || echo "NOT FOUND"`
- Existující scouts: !`ls sources/$1/scouts/ 2>/dev/null || echo "NONE"`

## Task
Spusť scout pipeline pro zdroj "$1".

1. Přečti status.json — ověř že projekt existuje
2. Dispatchi scout-source agenta (Workspace: sources/$1/)
3. Po scout-source: dispatchi scout-catalog per nalezený katalog (paralelně)
4. Po scout-catalog: dispatchi scout-opportunity na vzorku
5. Updatni status → SCOUTED
6. Vypiš shrnutí: kolik katalogů, kolik odhadovaných grantů, confidence
```

#### Příklad: `.claude/commands/runs.md`

```markdown
---
description: Zobraz přehled runů projektu — kdo běžel, kdy, s jakým výsledkem
argument-hint: <source_slug> [--agent config-catalog] [--status approved]
allowed-tools: Read, Glob, Grep, mcp__grantio__list_runs
---

## Task
Zobraz přehled runů pro zdroj "$1".
Použij list_runs tool. Pokud jsou zadané filtry, aplikuj je.
Vypiš tabulku: Run ID | Agent | Config | Status | Items | Quality | Cost | Datum
```

#### Příklad: `.claude/commands/build.md`

```markdown
---
description: Build pipeline — config-catalog + validator + config-opportunity + validator
argument-hint: <source_slug> [--step config-catalog|config-opportunity]
allowed-tools: Agent, Read, Write, Glob, Grep, mcp__grantio__read_status, mcp__grantio__write_status, mcp__grantio__list_runs, mcp__grantio__scrapy_run
---

## Context
- Status: !`cat sources/$1/status.json 2>/dev/null`
- Scouts: !`ls sources/$1/scouts/ 2>/dev/null`
- Configs: !`ls sources/$1/configs/ 2>/dev/null`
- Runy: !`ls sources/$1/runs/ 2>/dev/null`

## Task
Spusť build pipeline pro "$1".

Pokud --step je zadaný, spusť jen ten krok.
Jinak spusť celý build: config-catalog → validator-catalog → config-opportunity → validator-opportunity.

**Před každým krokem:**
1. Zkontroluj agent descriptor — co potřebuje jako vstup
2. list_runs("$1") — najdi existující approved runy
3. Pokud chybí závislost — řekni co chybí a jak to opravit

**Config-validate loop (max 3 pokusy):**
1. Dispatchi config agenta
2. Dispatchi validator agenta
3. IF approve → next step
4. IF needs_fix → re-dispatch config s feedbackem (nová verze)
```

### Sub-agenti = `.claude/agents/` (alternativa k programatické definici)

```
.claude/agents/
├── scout-source.md
├── scout-catalog.md
├── scout-opportunity.md
├── config-catalog.md
├── config-opportunity.md
├── validator-catalog.md
├── validator-opportunity.md
├── validator-source.md
├── analyst-source.md
├── fixer-catalog.md          # fáze 2
├── fixer-opportunity.md      # fáze 2
└── dedup-opportunity.md      # fáze 2
```

#### Příklad: `.claude/agents/config-catalog.md`

```markdown
---
name: config-catalog
description: Generuje listing YAML config, spouští scraper, získává listing URLs. Použij pro build pipeline.
tools: Read, Write, Edit, Bash, WebFetch, Glob, Grep, mcp__grantio__scrapy_run, mcp__grantio__source_memory
model: sonnet
---

## Kdo jsi
Config-catalog agent. Generuješ YAML config pro listing grantů.

## Co umíš (produces)
- configs/catalog.v{N}.yml — YAML listing config
- runs/{run-id}/listing_urls.json — všechny listing URLs

## Co potřebuješ (requires)
- scouts/{date}_source.json — typ zdroje, katalogy
- scouts/{date}_catalog-{name}.json — listing selektory, pagination

## Co ti pomůže (optional)
- scouts/{date}_opportunity-sample.json — detail mapping
- runs/{prev-run}/validation.json — feedback z validatoru (attempt > 1)

## Skills
Řiď se těmito SKILL.md:
- yaml-config — YAML config format, templates per strategie
- czech-parsing — české datumy, částky, formáty
- grant-schemas — GrantOpportunity schema, pole per typ

## Postup
1. Přečti scout findings
2. Generuj YAML config
3. scrapy_run(test, max=5) → ověř na 5 items
4. Pokud OK → scrapy_run(full) → všechny URLs
5. Pokud FAIL → oprav config, zkus znovu (max 3 interní pokusy)
6. Zapiš listing_urls.json + session metadata
```

---

## Data Flow: Nový zdroj end-to-end

```
1. /add https://www.tacr.cz
   → orchestrátor: vytvoří sources/tacr-cz/, status.json {phase: "CREATED"}

2. /scout tacr-cz
   → orchestrátor dispatchi:
   │
   ├─ scout-source → scouts/{date}_source.json
   ├─ scout-catalog (per katalog, paralelně) → scouts/{date}_catalog-{name}.json
   └─ scout-opportunity → scouts/{date}_opportunity-sample.json
   → status: SCOUTED

3. /build tacr-cz
   → orchestrátor: config-validate loop
   │
   ├─ CONFIG-CATALOG LOOP (max 3):
   │  ├─ config-catalog → configs/catalog.v{N}.yml + listing_urls.json
   │  ├─ validator-catalog → approve / needs_fix + feedback
   │  └─ (pokud needs_fix → nová verze, feedback v L5)
   │
   └─ CONFIG-OPPORTUNITY LOOP (max 3):
      ├─ orchestrátor: list_runs → najde approved cfg-cat run
      ├─ config-opportunity → configs/opportunity.v{M}.yml + items.json
      ├─ validator-opportunity → approve / needs_fix + feedback (type-specific)
      └─ (pokud needs_fix → nová verze)
   → status: BUILT

4. /analyze tacr-cz
   → analyst-source → obsahový review, verdict, hinty
   → status: REVIEWED

5. /gate approve tacr-cz
   → orchestrátor: gate_check (val-cat ✓, val-opp ✓, analyst ✓)
   → notify(telegram) → čeká na lidské schválení
   → status: PRODUCTION (config_version: v{N})

6. /run tacr-cz v1
   → produkční run (nebo Apify cron ve fázi 2+)

7. /status tacr-cz, /runs tacr-cz
   → orchestrátor: přehled stavu, runů, kvalit
```

---

## Flow: Web se změnil (fáze 2 — self-healing)

```
1. Apify scheduler → scrape run
2. Validator-catalog: quality drop >10%
3. Telegram alert: "⚠️ tacr-cz: 85→42"
4. fixer-catalog:
   ├─ čte: quality report, memory/failures.md, hints.md
   ├─ WebFetch: kontroluje aktuální HTML
   ├─ generuje nový config → configs/catalog.v3.yml
   └─ test run
5. Pokud OK → gate → deploy
6. Pokud FAIL → eskalace (Telegram: "🔴 tacr-cz needs human")
```

---

## Iterační plán

### Fáze 1: CLI + Core pipeline
- [ ] Workspace scaffold (`grantio init`)
- [ ] `grantio add` + filesystem layout
- [ ] Prompt composition engine (7 vrstev)
- [ ] Skills (SKILL.md soubory)
- [ ] scout-source, scout-catalog, scout-opportunity
- [ ] config-catalog, config-opportunity
- [ ] validator-catalog, validator-source
- [ ] analyst-source (gate-keeper)
- [ ] Production gate (Telegram + CLI)
- [ ] `grantio status`, `grantio hint`, `grantio log`
- [ ] Memory system (filesystem-based)
- [ ] Anti-fabrication checks
- [ ] **Cíl: 3 zdroje end-to-end**

### Fáze 2: Scale + automation
- [ ] Bulk operations (`grantio add --bulk`)
- [ ] fixer-catalog, fixer-opportunity (self-healing)
- [ ] dedup-opportunity
- [ ] Postgres migration (metadata)
- [ ] Apify integration (template actors, scheduler)
- [ ] Cross-source learning
- [ ] Monitoring + alerting
- [ ] **Cíl: 50+ zdrojů**

### Fáze 3: UI + full automation
- [ ] REST API (Hono)
- [ ] SvelteKit admin UI (viz ui.md)
- [ ] Session replay v UI
- [ ] Auto-discovery (meta-scout)
- [ ] Matching engine
- [ ] **Cíl: 300+ zdrojů, <20% lidský zásah**

---

## SDK Gaps & Solutions

### ⚠️ Gap 1: Skill scoping — skills se načítají globálně

**Problém:** Matice agents×skills definuje, že scout vidí grant-schemas + czech-parsing,
ale config vidí yaml-config + extraction-pipeline. SDK ale načítá VŠECHNY SKILL.md globálně
přes `settingSources`.

**Řešení: Plugin systém** — každá skupina agentů = plugin s vlastními skills:
```
plugins/
├── scout-agents/
│   ├── .claude-plugin/plugin.json
│   └── skills/
│       ├── grant-schemas/SKILL.md
│       └── czech-parsing/SKILL.md
├── config-agents/
│   ├── .claude-plugin/plugin.json
│   └── skills/
│       ├── yaml-config/SKILL.md
│       ├── extraction-pipeline/SKILL.md
│       └── czech-parsing/SKILL.md
└── validator-agents/
    ├── .claude-plugin/plugin.json
    └── skills/
        ├── quality-scoring/SKILL.md
        └── anti-fabrication/SKILL.md
```

Orchestrátor spouští sub-agenta s `plugins: [{ type: "local", path: "./plugins/scout-agents" }]`
→ agent vidí JEN relevantní skills. Namespaced commands + skills = přesná kontrola.

**Alternativa:** Vložit skill obsah přímo do `prompt` pole sub-agenta (L2/L3 vrstva).
Jednodušší, ale duplikuje obsah a zvyšuje token count.

### ⚠️ Gap 2: Sub-agent monitoring — synchronní, bez průběžného sledování

**Problém:** Agent tool je fire-and-wait. Orchestrátor nemůže sledovat progress
sub-agenta, nemůže přerušit po timeoutu, nevidí mezivýsledky.

**Řešení: Hybridní architektura** — TypeScript wrapper obaluje `query()`:
```typescript
// Orchestrátor = Claude agent PRO ROZHODOVÁNÍ
// Spouštěcí vrstva = TypeScript kód s timeoutem a hooks

async function dispatchAgent(type: string, prompt: string, opts: AgentOptions) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), opts.timeoutMs ?? 300_000);

  for await (const msg of query({
    prompt,
    options: {
      agents: agentRegistry[type],
      hooks: {
        PreToolUse: [monitoringHook],   // loguje akce do runs/{id}/progress.json
      },
      signal: controller.signal,
    }
  })) {
    if (msg.type === 'result') {
      clearTimeout(timeout);
      return msg;
    }
  }
}
```

Sub-agent zapisuje mezivýsledky na filesystem. Orchestrátor je čte až po dokončení,
ale monitoring hook loguje průběžně.

### ⚠️ Gap 3: Dynamic prompt composition vs statické `.claude/agents/*.md`

**Problém:** 7-vrstvá prompt architektura vyžaduje dynamické sestavení na základě
kontextu (feedback z validátoru, workspace stav, memory). `.claude/agents/*.md` je statický.

**Řešení: Programmatic agent definitions** — factory funkce:
```typescript
function createConfigAgent(
  source: string,
  type: 'catalog' | 'opportunity',
  feedback?: ValidationFeedback
): AgentDefinition {
  const layers = [
    L0_SYSTEM,
    L1_SKILL_CONTENT[type],              // z SKILL.md souboru
    L2_AGENT_IDENTITY[`config-${type}`], // kdo jsi
    L3_SOURCE_CONTEXT(source),           // source memory + hints
    L4_TASK_SPECIFICS(source, type),     // co máš udělat teď
  ];
  if (feedback) {
    layers.push(L5_FEEDBACK(feedback));  // validátor řekl...
  }
  layers.push(L6_GUARDRAILS);

  return {
    description: `Config-${type} agent for ${source}`,
    prompt: layers.join('\n\n---\n\n'),
    tools: TOOL_MATRIX[`config-${type}`],
    model: 'sonnet',
  };
}
```

`.claude/agents/*.md` slouží jako **dokumentace/šablona** (L2 vrstva).
Runtime vždy programmatic config s dynamickým prompt compose.

### ⚠️ Gap 4: Session tracking per sub-agent

**Problém:** Agent tool vrátí jen výsledek, ne `session_id`. Nelze `resume`
sub-agenta po feedback loop.

**Řešení: Kontext přes filesystem.** Sub-agenti jsou short-lived. Každý run je nový.
Kontext se předává přes:
- `runs/{prev-run}/items.json` — předchozí výsledky
- `runs/{prev-run}/validation.json` — feedback
- `memory/decisions.md` — persistent knowledge

Resume nepotřebujeme — nový run s plným kontextem je spolehlivější
než resume staré session.

### ✅ Gap 5: Structured output — NEVYUŽÍVÁME (snadné přidat)

**Řešení:** `outputFormat` pro validátory a scouty:
```typescript
'validator-catalog': {
  // ...
  outputFormat: {
    type: 'json_schema',
    schema: {
      type: 'object',
      properties: {
        verdict: { enum: ['approve', 'needs_fix'] },
        urls_checked: { type: 'number' },
        urls_alive: { type: 'number' },
        feedback: { type: 'string' },
        field_issues: { type: 'array', items: { type: 'object', ... } },
      },
      required: ['verdict', 'urls_checked', 'urls_alive']
    }
  }
}
```

Eliminuje parsování volného textu. Orchestrátor dostane strojově čitelný výsledek.

### ✅ Gap 6: Hooks pro gate checking — NEVYUŽÍVÁME

**Řešení:** `PreToolUse` hooks jako safety net:
```typescript
hooks: {
  PreToolUse: [{
    matcher: 'mcp__grantio__scrapy_run',
    hooks: [async (input) => {
      if (input.mode === 'full' && !hasApprovedConfig(input.source)) {
        return { permissionDecision: 'deny',
                 reason: 'No approved config — run validator first' };
      }
      return {};
    }],
  }]
}
```

### ✅ Gap 7: Cost tracking — NEVYUŽÍVÁME

**Řešení:** SDK `total_cost_usd` v result message → logovat do `runs/{id}/meta.json`.
Orchestrátor může odmítnout spuštění pokud source přesáhne budget.

### ✅ Gap 8: canUseTool sandboxing — NEVYUŽÍVÁME

**Řešení:** Druhá vrstva ochrany nad `tools: [...]`:
```typescript
canUseTool: async (toolName, input) => {
  const agentType = currentAgentContext();
  const rules = SECURITY_MATRIX[agentType];

  // Scout nemůže psát (ani přes Bash)
  if (rules.readOnly && isWriteOperation(toolName, input)) {
    return { behavior: 'deny', message: `${agentType} is read-only` };
  }
  // Config nemůže spustit full run (jen test)
  if (toolName === 'mcp__grantio__scrapy_run' &&
      input.mode === 'full' && !rules.canFullRun) {
    return { behavior: 'deny', message: 'Only test runs allowed' };
  }

  return { behavior: 'allow', updatedInput: input };
}
```

### Prioritizace

| Gap | Severity | Fáze 1? | Effort |
|-----|----------|---------|--------|
| G1 Skill scoping | Medium | Prompt-inline (jednoduché) | Low |
| G2 Monitoring | High | Hybridní wrapper | Medium |
| G3 Dynamic prompts | Critical | Factory funkce | Medium |
| G4 Session tracking | Low | Filesystem = OK | — (ne-problém) |
| G5 Structured output | High | Přidat outputFormat | Low |
| G6 Hooks gates | Medium | Přidat PreToolUse | Low |
| G7 Cost tracking | Low | Log to meta.json | Low |
| G8 canUseTool | Medium | Security matrix | Low |

**Fáze 1 minimum:** G3 (dynamic prompts) + G5 (structured output) + G2 (monitoring wrapper).
Zbytek je nice-to-have a přidá se iterativně.

---

## Vztah k existujícímu kódu

**Clean break.** Python PoC (the-machine) slouží jako **reference**.

Co se přebírá:
- YAML config formát (zachovat kompatibilitu)
- Doménové znalosti (pro SKILL.md soubory a L2/L3 prompty)
- Existující scrapevaná data (migrace do nové workspace)
- Naučené patterns (transform pipeline logika → extraction-pipeline SKILL)
- Anti-fabrication pravidla
- Lifecycle-aware quality scoring

Co se nepřebírá:
- Python kód
- Filesystem-based storage layout (nový workspace format)
- ClaudeCliRunner / AnthropicClient (→ Agent SDK)
- Batch orchestrátor
