# Grantio: Complete Architecture Package

---


---

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- FILE: INDEX.md -->
<!-- ═══════════════════════════════════════════════════════════ -->

# Grantio Architecture — Document Index

## Deliverables

| # | Dokument | Obsah | Status |
|---|----------|-------|--------|
| 1 | BRIEF.md | Project brief, rozhodnutí, tech stack, iterační plán | ✅ Final |
| 2 | ARCHITECTURE-REVIEW.md | Review prototypu, cílová architektura, Postgres schema, Agent SDK integrace, execution flows, roadmap 26 týdnů | ✅ Final |
| 3 | AGENT-GRANULARITY.md | 12 agentů, asymetrické úrovně, agent vs kód rozhodnutí | ✅ Final |
| 4 | UI-ARCHITECTURE.md | Screens, workspace pattern (source/catalog/opportunity), run detail, breadcrumbs | ✅ Final |
| 5 | CLI.md | Příkazy, výstup (stderr human / stdout JSON), iterační plán | ✅ Final |
| 6 | KNOWLEDGE-EXTRACTION.md | 80+ otázek pro knowledge extraction z prototypu | ✅ Final |
| 7 | src/schemas/grant.ts | Univerzální GrantOpportunity schéma (draft, bude revidováno po knowledge extraction) | ⚠️ Draft |
| 8 | src/agents/definitions.ts | Agent definice v1 (bude nahrazeno po knowledge extraction) | ⚠️ Draft |
| 9 | src/architecture-v2.ts | Typy, strategie, validation architecture (bude sloučeno) | ⚠️ Draft |
| 10 | .claude/CLAUDE.md | Globální agent instrukce (draft) | ⚠️ Draft |

## Pořadí čtení

1. BRIEF.md — co stavíme a proč
2. ARCHITECTURE-REVIEW.md — jak to postavíme
3. AGENT-GRANULARITY.md — jaké agenty a na jakých úrovních
4. UI-ARCHITECTURE.md — co uvidí uživatel
5. CLI.md — co uvidí developer
6. KNOWLEDGE-EXTRACTION.md — co potřebujeme vědět před implementací

## Další krok

Zodpovědět KNOWLEDGE-EXTRACTION.md → revidovat schema + agent definice → Phase 1 implementace.


---

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- FILE: BRIEF.md -->
<!-- ═══════════════════════════════════════════════════════════ -->

# Grantio — Project Brief

## Co to je

SaaS produkt. Automatizovaný scouting, scraping a matching grantových příležitostí
z 300+ českých a evropských zdrojů. Párování výzva↔klient/projekt.

## Rewrite

Existuje Python prototyp (Scrapy/Playwright + Claude Agent SDK) s fungujícím
scout, scraper, validation, matching, PDF parsing. Je to PoC — přepisujeme
na TypeScript, čistší architekturu, scale na 300+ zdrojů.

## Rozhodnutí

| # | Otázka | Odpověď |
|---|--------|---------|
| 1 | Vztah k Grantio | Samostatný produkt |
| 2 | Use case | Matching: výzva↔klient/projekt |
| 3 | Business model | SaaS |
| 4 | Počet zdrojů | 300+ |
| 5 | Budget | Kvalita first |
| 6 | Freshness | Monitoring denně/týdně |
| 7 | Existující kód | Python PoC (scout, scraper, validation, matching, PDF) |
| 8 | Právní | OK — veřejné portály státní správy |
| 9 | Přílohy | Extrakce dat z PDF (OCR/parsing) |
| 10 | Deployment | Apify (actors) + Hetzner (server) |
| 11 | Hinty | Malý tech tým |
| 12 | Notifikace | Telegram |
| 13 | Deduplikace | Reálný problém, řešit od začátku |
| 14 | Jazyk | Originál (CZ/EN) + normalizovaná klíčová pole |
| 15 | Storage | DB od začátku (ne filesystem) |

## Architektonické důsledky

### 300 zdrojů mění všechno

- **Auto-discovery**: Nemůžeš manuálně scoutovat 300 zdrojů. Potřebuješ
  meta-scout: dej mu seznam URL → sám kategorizuje, detekuje typ, navrhne strategii.
- **Self-healing**: Scraper se rozbije (web se změnil) → validator detekuje
  degradaci → fixer agent automaticky opraví → pokud neuspěje, eskaluj člověku.
- **Template scrapers**: Většina zdrojů spadne do 5-10 vzorů (WordPress listing,
  IS KP14+, custom CMS, PDF portál...). Agent generuje scraper z template,
  ne from scratch pro každý zdroj.
- **Priority queue**: Ne všech 300 naráz. Prioritizuj podle: počet otevřených
  výzev, relevance pro klienty, stáří dat, failure rate.
- **Hinty at scale**: Tech tým nedá hinty pro 300 zdrojů. Hinty jen pro
  problematické zdroje (quality < threshold). Většina musí jet automaticky.

### Matching jako primární use case

- **Schema bohatost je kritická**: Eligibility (kdo může žádat), sectors,
  regions, funding rozsahy — to vše je matching input. Čím víc polí, tím
  lepší matching.
- **Klientský profil**: Potřebuješ druhou stranu — kdo je klient, co hledá.
  Datový model pro klienta/projekt.
- **Scoring**: Výzva×klient → match score. Rule-based + semantic similarity.

### Apify + Hetzner

- **Apify**: Actor per source-type (ne per source). Actor přijímá config
  (URL, selektory, strategie) → generický actor, specifická konfigurace.
  Apify scheduler pro monitoring. Apify storage pro raw data.
- **Hetzner**: API server, DB (Postgres), matching engine, Telegram bot,
  budoucí UI. Agent SDK runtime pro scouting/fixer (ne pro každý scrape run).

### DB od začátku

- **Postgres** na Hetzner: sources, catalogs, opportunities, validations,
  runs, hints, match_scores
- **Apify storage**: Raw scraped data (dataset), scraper configs (key-value store)
- **Sync**: Apify actor → webhook → Hetzner API → Postgres

### PDF parsing pipeline

- Separátní concern od web scrapingu
- Apify actor pro PDF: stáhni → OCR (pokud scan) → extrakce tabulek/textu
- Claude pro strukturovanou extrakci z textu → GrantOpportunity fields
- Cache: PDF se nemění, parsuj jednou

### Deduplikace

- Title similarity (fuzzy match) + provider + deadline = candidate pairs
- Claude agent jako judge: "jsou tyto dvě příležitosti stejné?" na candidate pairs
- Merge strategy: nejúplnější záznam vyhrává, reference na všechny zdroje

### Telegram notifikace

- Nová výzva matchující klienta → Telegram zpráva
- Broken scraper (quality drop) → alert do dev kanálu
- Denní/týdenní digest: nové výzvy, expiring deadlines

## Tech Stack

```
┌────────────────────────────────────────────────────────┐
│  Apify Platform                                         │
│  ├── actor: web-scraper-static (httpx pattern)         │
│  ├── actor: web-scraper-dynamic (Playwright pattern)   │
│  ├── actor: pdf-extractor                              │
│  ├── actor: catalog-monitor (diff detection)           │
│  ├── scheduler: per-source cron                        │
│  └── storage: datasets + key-value (configs)           │
└──────────────────────┬─────────────────────────────────┘
                       │ webhook
┌──────────────────────▼─────────────────────────────────┐
│  Hetzner Server                                         │
│  ├── API (Node.js / Hono or Fastify)                   │
│  ├── Postgres (sources, opportunities, matches, hints) │
│  ├── Agent SDK runtime (scout, fixer, analyst agents)  │
│  ├── Matching engine (rule-based + Claude scoring)     │
│  ├── Telegram bot                                      │
│  └── CLI (grantio)                                     │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  Claude Agent SDK (na Hetzner)                          │
│  ├── Subagents: scout, fixer, analyst, dedup-judge     │
│  ├── Skills: grant-schemas, czech-parsing, validation  │
│  ├── Memory: per-source v Postgres (ne filesystem)     │
│  └── Sessions: pro long-running scout/fix workflows    │
└────────────────────────────────────────────────────────┘
```

## Co se mění oproti v2 návrhu

| v2 návrh | v3 (final) | Proč |
|----------|------------|------|
| Filesystem storage | Postgres | 300 zdrojů, concurrent access, UI |
| Scraper per source | Template actors + config | Scale |
| Manual scout per source | Auto-discovery meta-scout | 300 zdrojů |
| Manual hints | Auto-fix + eskalace | Scale |
| Git versioning | DB + Apify KV store | Deployment |
| CLI only | CLI + API + Telegram | Multi-user, notifikace |
| Standalone scrapers | Apify actors | Scheduling, proxy, monitoring |
| Agent SDK pro vše | Agent SDK pro intelligence, Apify pro execution | Cost + reliability |

## Klíčový insight

**Agent SDK ≠ scraping runtime.** Agent SDK je intelligence layer:
- Scouting nových zdrojů
- Generování scraper konfigurací (ne kódu — config pro template actor)
- Fixing broken scrapers
- Dedup judging
- Matching scoring
- Analýza dat

**Apify = execution layer:** Spouští scrapery, scheduling, proxy, retry,
storage. Deterministic, levný, scalable.

Agent SDK se volá když je potřeba *rozhodnutí*. Apify běží když je potřeba
*opakovaná práce*.

## Iterační plán (aktualizovaný)

```
Iter 0: Jeden zdroj, Agent SDK scout → Apify actor config → test scrape
Iter 1: Template actor pattern (static + dynamic) na 3 zdrojích
Iter 2: Postgres schema + API, validation pipeline
Iter 3: PDF extraction actor + Claude structured extraction
Iter 4: Monitoring (Apify scheduler + diff detection)
Iter 5: Matching engine (klient profil + scoring)
Iter 6: Telegram bot (nové výzvy, alerts)
Iter 7: Auto-discovery + self-healing (meta-scout, fixer)
Iter 8: Deduplikace
Iter 9: Scale na 50+ zdrojů, load testing
Iter 10: UI
```


---

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- FILE: ARCHITECTURE-REVIEW.md -->
<!-- ═══════════════════════════════════════════════════════════ -->

# Grantio: Architectural Review & Roadmap

## Kontext

Existuje "The Machine" — Python prototyp:
- 359 YAML konfigurací, 239+ zdrojů, 6 211 grantů
- Config-driven (YAML, ne kód per source)
- Multi-step field extraction (CSS → regex → transform → LLM fallback)
- Auto-detection strategie (html/js/api/file/single_page/crawl)
- Autonomní config generování (Claude agent loop)
- PDF parsing chain (docling → pymupdf → pdfplumber)
- Lifecycle-aware quality scoring
- Checkpoint & resume
- Karanténa místo zahazování
- Claude volaný přes `claude -p` subprocess

Cíl: Přepsat do TypeScript, migrovat na Agent SDK, postavit platformu
kde každý zdroj = projekt s agentic workspace.

---

## Architektonický Review stávajícího systému

### Co funguje a NESMÍ se ztratit

1. **YAML config pattern.** 359 configs > 359 scraperů. Toto je jádro systému.
   Rewrite musí zachovat config-driven přístup. Formát se může změnit
   (YAML → TypeScript schema, JSON Schema, nebo zůstat YAML), ale princip ne.

2. **Multi-step extraction pipeline.** CSS → regex → transform → LLM.
   Deterministic first, LLM last. Toto je správná hierarchie.
   Každý krok s confidence score a provenance tracking.

3. **Lifecycle-aware quality.** Aktivní výzva = 95%, archiv = 60%.
   +12 bodů kvality bez změny extrakce. Geniální. Zachovat.

4. **Karanténa.** Data se nezahazují. Viditelnost > čistota.

5. **Anti-fabrikační prompty + LLM agreement check.** Dual extraction
   (CSS + LLM) s porovnáním. Zachovat a rozšířit.

### Co je problém

1. **`claude -p` subprocess.** Pipe deadlock (65KB buffer), streaming
   idle timeout, CLAUDECODE env var workaround, error v stdout.
   Toto všechno odpadne s Agent SDK — nativní async, žádné subprocessy.

2. **Žádná persistence stavu agenta.** Config loop generuje, ale nemá
   memory — nezná historii pokusů, předchozí selhání, lidské hinty.
   Každý run začíná od nuly.

3. **Žádná kolaborace.** Hinty jsou v hlavě developera, ne v systému.
   Quality problémy vidí jen ten, kdo spustí batch.

4. **Monolitický batch.** `grant batch --sources x,y,z --parallel 4`
   je jeden velký job. Není viditelnost do jednotlivých kroků,
   žádné partial results, žádný resume na úrovni jednotlivého zdroje.

5. **Žádné UI.** Grant manažer nevidí nic. Data jsou v JSON souborech.

---

## Cílová architektura: Source Workspace

### Metafora

Každý zdroj = **projekt v Claude.ai**:
- **Chaty** = běhy agentů (scout run, scrape run, fix run)
- **Soubory** = konfigurace (YAML), data, quality reporty
- **Git link** = versované konfigurace s historií
- **Hinty** = lidské anotace per source/catalog/opportunity
- **Commands** = /scout, /scrape, /validate, /fix, /analyze

### Data model

```
┌────────────────────────────────────────────────────────────┐
│ Source Workspace                                            │
│                                                            │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│ │ Config       │  │ Runs         │  │ Knowledge        │  │
│ │              │  │              │  │                  │  │
│ │ config.yaml  │  │ run-001      │  │ hints/           │  │
│ │ ← git link   │  │  ├ agent log │  │  ├ source.md     │  │
│ │ ← version    │  │  ├ data out  │  │  ├ catalog-X.md  │  │
│ │ ← diff       │  │  ├ quality   │  │  └ opportunity.md│  │
│ │              │  │  └ session   │  │                  │  │
│ │ schema map   │  │ run-002      │  │ memory/          │  │
│ │ strategies   │  │  └ ...       │  │  ├ structure.md  │  │
│ │              │  │              │  │  ├ failures.md   │  │
│ └──────────────┘  └──────────────┘  │  └ decisions.md  │  │
│                                      └──────────────────┘  │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│ │ Data         │  │ Quality      │  │ Catalogs         │  │
│ │              │  │              │  │                  │  │
│ │ opportunities│  │ latest score │  │ catalog-1        │  │
│ │ attachments  │  │ history      │  │  ├ config        │  │
│ │ raw HTML     │  │ quarantine   │  │  ├ opportunities │  │
│ │              │  │ benchmark    │  │  └ quality       │  │
│ └──────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### Postgres schema (core tables)

```sql
-- Source = workspace
sources (
  id, slug, name, url, type,
  strategy, status,           -- active/paused/broken/archived
  config_git_path,            -- link do git repo s YAML
  config_version,             -- aktuální verze (git sha)
  created_at, updated_at
)

-- Catalog = sub-workspace
catalogs (
  id, source_id, name, url,
  strategy, pagination_type,
  config_json,                -- catalog-specific extraction config
  opportunity_count
)

-- Runs = chaty
runs (
  id, source_id, catalog_id?,
  type,                       -- scout/scrape/validate/fix/analyze
  status,                     -- running/completed/failed/cancelled
  agent_session_id,           -- Agent SDK session pro resume
  config_version,             -- jaká verze configu byla použita
  started_at, completed_at,
  summary_json,               -- agent summary
  token_usage, cost
)

-- Run messages = konverzace
run_messages (
  id, run_id,
  role,                       -- system/assistant/user/tool_use/tool_result
  content_json,
  timestamp
)

-- Hints = lidské anotace
hints (
  id, source_id, catalog_id?, opportunity_id?,
  level,                      -- source/catalog/opportunity
  text,
  author,
  resolved,                   -- hint vyřešen (fixer ho aplikoval)
  resolved_by_run_id,
  created_at
)

-- Agent memory = persistent knowledge
source_memory (
  id, source_id,
  topic,                      -- structure/failures/decisions
  content_md,
  updated_at, updated_by_run_id
)

-- Opportunities = scraped data
opportunities (
  id, source_id, catalog_id,
  url, title, description, provider, programme,
  funding_json, dates_json, eligibility_json,
  status, attachments_json, contact_json,
  meta_json,                  -- source-specific extensions
  scraped_at, config_version,
  quality_score, completeness_score,
  quarantine_reason,          -- null = OK, jinak důvod
  lifecycle_stage,            -- announced/ongoing/closed
  dedupe_cluster_id           -- pro deduplikaci
)

-- Quality history
quality_reports (
  id, source_id, run_id,
  overall_score, completeness_score,
  field_scores_json,          -- per-field completeness
  issues_json,                -- [{field, type, count}]
  benchmark_json,             -- holdout results
  created_at
)
```

---

## Agent SDK Integration

### Proč Agent SDK místo `claude -p`

| `claude -p` subprocess | Agent SDK nativně |
|------------------------|-------------------|
| Pipe deadlock na 65KB | Async stream, žádné pipes |
| Idle timeout hacks | Native timeout handling |
| CLAUDECODE env var strip | Žádný conflict |
| Error v stdout parsing | Typed message objects |
| Žádné subagents | Subagents s izolovaným kontextem |
| Žádná memory | Memory tool + filesystem |
| Žádné sessions | Session resume |
| Žádné skills | Skills auto-discovery |
| JSON extraction hacks | Structured outputs |

### Agent types

```typescript
// Subagents (definované programmaticky, ne .md soubory — protože
// potřebují přístup k DB a runtime config)

agents: {
  // ── Scout agents (read-only, sonnet) ──────────────
  "scout-source": {
    description: "Analyzuj nový grantový zdroj",
    prompt: buildScoutSourcePrompt(sourceMemory, hints),
    tools: ["WebFetch", "WebSearch", "Read", "Write"],
    model: "sonnet",
  },
  "scout-catalog": { ... },
  "scout-opportunity": { ... },

  // ── Config agents (code-gen, sonnet) ──────────────
  "config-generator": {
    description: "Generuj YAML config pro zdroj na základě scout reportu",
    prompt: buildConfigGenPrompt(scoutReport, existingTemplates, hints),
    tools: ["Read", "Write", "Edit", "Bash", "WebFetch"],
    model: "sonnet",
  },

  // ── Quality agents (read-only, haiku/sonnet) ──────
  "validator": {
    description: "Validuj scraped data, měř kvalitu",
    tools: ["Read", "Bash"],
    model: "haiku",  // většina je deterministic checks
  },

  // ── Fix agents (code-gen, sonnet) ─────────────────
  "config-fixer": {
    description: "Oprav YAML config na základě quality reportu a hintů",
    prompt: buildFixerPrompt(qualityReport, hints, memory, failureLog),
    tools: ["Read", "Write", "Edit", "Bash", "WebFetch"],
    model: "sonnet",
  },

  // ── Analysis agents (read-only, sonnet) ───────────
  "analyst": { ... },
  "dedup-judge": { ... },
}
```

### Skills (SKILL.md, filesystem-based)

```
.claude/skills/
├── grant-schemas/SKILL.md      # GrantOpportunity schema, povinná pole per typ
├── yaml-config/SKILL.md        # YAML config format, validace, best practices
├── czech-parsing/SKILL.md      # CZK, datumy, IČO, NUTS kódy
├── extraction-pipeline/SKILL.md # Multi-step extraction, confidence scoring
├── quality-scoring/SKILL.md    # Lifecycle-aware scoring, thresholds
└── anti-fabrication/SKILL.md   # Pravidla proti halucinaci, null > guess
```

### Memory per source

Agent SDK memory tool → ukládá do Postgres (`source_memory` tabulka),
ne do filesystému. Custom memory tool wrapper:

```typescript
// Custom tool: source-memory
{
  name: "source_memory",
  description: "Čti/piš persistent knowledge o tomto zdroji",
  input_schema: {
    topic: "structure | failures | decisions",
    action: "read | append | replace",
    content: "string (for write)",
  },
  handler: async (input) => {
    // Read/write do source_memory tabulky v Postgres
  }
}
```

Agent na začátku každého runu automaticky čte memory.
Na konci updatuje decisions/failures.

### Session per run

Každý `run` v DB má `agent_session_id`. Pokud run selže uprostřed,
resume = nový query s `sessionId` → Agent SDK pokračuje kde skončil.

---

## Execution Architecture

### Co běží kde

```
┌─────────────────────────────────────────────────────────┐
│ Hetzner                                                  │
│                                                          │
│ ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│ │ API Server  │  │ Agent SDK    │  │ Postgres        │ │
│ │ (Hono/      │  │ Runtime      │  │                 │ │
│ │  Fastify)   │  │              │  │ sources         │ │
│ │             │  │ scout        │  │ catalogs        │ │
│ │ REST API    │←→│ config-gen   │←→│ opportunities   │ │
│ │ WebSocket   │  │ fixer        │  │ runs            │ │
│ │             │  │ analyst      │  │ hints           │ │
│ │ Telegram bot│  │ dedup-judge  │  │ quality_reports │ │
│ └─────────────┘  └──────────────┘  │ source_memory   │ │
│                                     └─────────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │ webhooks + Apify client
┌──────────────────────▼──────────────────────────────────┐
│ Apify Platform                                           │
│                                                          │
│ ┌───────────────┐  ┌───────────────┐  ┌──────────────┐ │
│ │ web-scraper   │  │ web-scraper   │  │ pdf-extractor│ │
│ │ -static       │  │ -dynamic      │  │              │ │
│ │ (httpx)       │  │ (Playwright)  │  │ docling →    │ │
│ │               │  │               │  │ pymupdf →    │ │
│ │ Vstup: YAML   │  │ Vstup: YAML   │  │ pdfplumber   │ │
│ │ config        │  │ config        │  │              │ │
│ └───────────────┘  └───────────────┘  └──────────────┘ │
│                                                          │
│ ┌───────────────┐  ┌───────────────┐                    │
│ │ catalog-      │  │ scheduler     │                    │
│ │ monitor       │  │ (per source   │                    │
│ │ (diff detect) │  │  cron)        │                    │
│ └───────────────┘  └───────────────┘                    │
└──────────────────────────────────────────────────────────┘
```

### Flow: Nový zdroj

```
1. UI/CLI: Přidej zdroj URL
2. API → creates source record (status: new)
3. API → triggers scout run
4. Agent SDK: scout-source subagent
   ├── čte hints (z DB), memory (z DB)
   ├── WebFetch + analyzuje web
   └── výstup: source report JSON
5. Agent SDK: scout-catalog (per nalezený katalog)
   └── výstup: catalog reports
6. Agent SDK: scout-opportunity (sample)
   └── výstup: schema mapping
7. Agent SDK: config-generator
   ├── čte scout reports + hints + existing templates
   ├── generuje YAML config
   ├── testuje na sample URL (Bash → httpx/playwright)
   └── výstup: config.yaml + test results
8. API → commits config do git, ukládá verzi
9. API → triggers Apify actor (static/dynamic dle strategie)
   ├── vstup: YAML config
   └── výstup: webhook s daty → API → Postgres
10. API → triggers validation run
    └── Agent SDK: validator → quality report
11. Pokud quality < threshold → auto-fix run
    └── Agent SDK: config-fixer → nová verze configu → go to 9
12. Pokud quality OK → source status: active
13. Apify scheduler: cron dle freshness požadavku
```

### Flow: Web se změnil (self-healing)

```
1. Apify scheduler → scrape run
2. Actor vrátí data → webhook → API
3. Validation: quality drop >10% vs. previous
4. API → creates alert (Telegram: "⚠️ tacr-cz: 85→42")
5. API → triggers fix run
6. Agent SDK: config-fixer
   ├── čte: quality report, failures memory, hints
   ├── WebFetch: kontroluje aktuální HTML
   ├── generuje nový config
   ├── testuje na sample
   └── výstup: config v2 + test results
7. Pokud test OK → git commit, update config_version
8. Re-trigger scrape s novým configem
9. Pokud test FAIL → eskalace (Telegram: "🔴 tacr-cz needs human")
```

---

## UI Architecture

### Screens

```
/dashboard
  ├── Source health overview (active/broken/paused counts)
  ├── Recent runs (timeline)
  ├── Quality trends (sparklines)
  └── Alerts (broken scrapers, new hints needed)

/sources
  ├── Source list (filterable: status, type, quality)
  └── Source card: name, quality badge, last run, opportunity count

/sources/:slug                      ← Source Workspace
  ├── Overview tab
  │   ├── Status, strategy, quality score
  │   ├── Config (YAML viewer, git history link)
  │   └── Quick actions: scout, scrape, validate
  │
  ├── Runs tab                      ← "Chaty"
  │   ├── Run list (type, status, duration, cost)
  │   └── Run detail: agent konverzace (message by message),
  │       data produced, quality delta
  │
  ├── Data tab
  │   ├── Opportunities list (searchable, filterable)
  │   ├── Opportunity detail: all fields, provenance,
  │   │   confidence per field, attachments
  │   └── Quarantine section
  │
  ├── Quality tab
  │   ├── Current scores (overall, per-field heatmap)
  │   ├── History chart
  │   └── Issues list with suggested fixes
  │
  ├── Hints tab                     ← Collaboration
  │   ├── Hint list per level (source/catalog/opportunity)
  │   ├── Add hint form
  │   └── Resolved/unresolved filter
  │
  └── Config tab
      ├── Current YAML (editable)
      ├── Git history (diffs)
      └── Schema mapping visualization

/opportunities
  ├── Global search across all sources
  ├── Filters: status, provider, deadline, funding range, region
  └── Dedup clusters view

/matching (future)
  ├── Client profiles
  ├── Match results (výzva × klient matrix)
  └── Notification rules
```

### Tech stack UI

```
Frontend:  SvelteKit (znáš ze Sandbox Chat Orchestrator)
           nebo Next.js — záleží na preferenci
Realtime:  WebSocket pro run streaming (agent messages live)
Styling:   Tailwind
Tables:    TanStack Table
Charts:    Recharts nebo Chart.js
YAML view: CodeMirror (YAML syntax highlighting)
```

---

## Git Integration

### Config repo

```
grantio-configs/
├── sources/
│   ├── tacr-cz/
│   │   ├── config.yaml          # Hlavní config
│   │   ├── catalog-vyzvy.yaml   # Per-catalog overrides
│   │   └── transforms.ts        # Custom transformace (pokud potřeba)
│   ├── dotaceeu-cz/
│   │   └── config.yaml
│   └── ...
├── templates/                   # Template configs per strategy
│   ├── static-listing.yaml
│   ├── dynamic-listing.yaml
│   ├── api-backed.yaml
│   └── document-portal.yaml
└── schemas/
    └── config-schema.json       # JSON Schema pro validaci YAML
```

- Agent generuje config → API commitne do repo
- UI zobrazuje git historii (diffs)
- Config fixer vytvoří novou verzi → nový commit
- Rollback = git revert + update config_version v DB

---

## CLI (developer interface)

Zůstává jako dev tool. Ale teď mluví s API, ne přímo s filesystémem:

```bash
# Setup
grantio login                          # Autentizace k API
grantio init                           # Lokální dev environment

# Source management
grantio add <url>                      # → POST /api/sources
grantio scout <source>                 # → POST /api/sources/:id/runs {type: scout}
grantio scrape <source>                # → POST /api/sources/:id/runs {type: scrape}
grantio validate <source>              # → POST /api/sources/:id/runs {type: validate}
grantio fix <source>                   # → POST /api/sources/:id/runs {type: fix}

# Collaboration
grantio hint <source> "text"           # → POST /api/sources/:id/hints
grantio hint <source> -c <cat> "text"  # → POST /api/catalogs/:id/hints
grantio hints <source>                 # → GET /api/sources/:id/hints

# Monitoring
grantio status                         # → GET /api/sources (summary)
grantio status <source>                # → GET /api/sources/:id (detail)
grantio log <source>                   # → GET /api/sources/:id/runs?last=1

# Dev/debug
grantio run <source> "<prompt>"        # → Ad-hoc agent prompt
grantio config <source>                # → zobrazí YAML config
grantio config <source> --edit         # → otevře v editoru, commitne po uložení

# Streaming: run progress live v terminálu
grantio scout tacr --follow            # streamy agent messages live
```

---

## Roadmap

### Phase 1: Foundation (4-6 týdnů)

**Cíl: TypeScript rewrite core engine + Postgres + API skeleton**

```
Week 1-2: Core extraction engine v TypeScript
  - YAML config parser + validator (JSON Schema)
  - Multi-step field extraction pipeline (CSS → regex → transform → LLM)
  - Content type detector
  - Czech parsing library (dates, amounts, IČO, NUTS)
  - Port transform registry
  - Tests: extraction accuracy na 10 known sources

Week 3-4: Agent SDK integration
  - Replace `claude -p` subprocess s native Agent SDK
  - Implement subagents: scout-source, scout-catalog, scout-opportunity
  - Implement config-generator agent
  - Skills: grant-schemas, yaml-config, czech-parsing, anti-fabrication
  - Memory: custom tool backed by Postgres
  - Session persistence
  - Tests: full scout pipeline na 3 sources

Week 5-6: Postgres + API
  - Schema migration (tables above)
  - REST API (Hono or Fastify): sources, runs, hints CRUD
  - Git integration: config commit/read/diff
  - CLI: add, scout, status, hint (talking to API)
  - Import existing 359 YAML configs
```

### Phase 2: Execution (3-4 týdny)

**Cíl: Apify actors + scraping pipeline + validation**

```
Week 7-8: Apify actors
  - web-scraper-static (httpx + cheerio, config-driven)
  - web-scraper-dynamic (Playwright, config-driven)
  - pdf-extractor (parser chain)
  - Webhook integration: actor → API → Postgres
  - Config deployment: git → Apify key-value store

Week 9-10: Validation + self-healing
  - Validator agent (schema + quality + lifecycle scoring)
  - Quality history tracking
  - Quarantine system
  - Config-fixer agent
  - Regression detection (quality drop alert)
  - Benchmark on holdout set
```

### Phase 3: Monitoring & Collaboration (2-3 týdny)

**Cíl: Scheduling + Telegram + hints workflow**

```
Week 11-12: Monitoring
  - Apify scheduler per source (configurable cron)
  - Catalog-monitor actor (diff detection: nové/smazané příležitosti)
  - Telegram bot: alerts (broken), digests (nové výzvy), status
  - Self-healing loop: detect → fix → test → deploy (or escalate)

Week 13: Collaboration
  - Hints CRUD in API (source/catalog/opportunity level)
  - Hint resolution tracking (which run resolved which hint)
  - CLI hint workflow
  - Memory sharing across runs (decisions propagate)
```

### Phase 4: UI (4-6 týdnů)

**Cíl: Web UI pro grant manažery**

```
Week 14-16: Core UI
  - Dashboard (health, recent runs, alerts)
  - Source list + Source workspace
  - Run viewer (agent conversation stream)
  - Data browser (opportunities, search, filter)

Week 17-19: Advanced UI
  - Quality dashboard (heatmaps, trends, per-field breakdown)
  - Hints UI (add, resolve, discuss)
  - Config viewer (YAML + git history + diffs)
  - Real-time run streaming (WebSocket)
```

### Phase 5: Intelligence (3-4 týdny)

**Cíl: Matching + deduplikace + analytics**

```
Week 20-21: Deduplication
  - Fuzzy matching (title + provider + deadline)
  - Dedup-judge agent (Claude as judge on candidate pairs)
  - Cluster management, merge strategy

Week 22-23: Matching engine
  - Client/project profile data model
  - Rule-based matching (eligibility, regions, sectors, funding)
  - Semantic similarity scoring (Claude)
  - Match results in UI
  - Telegram notifications on new matches
```

### Phase 6: Scale (2-3 týdny)

**Cíl: 300+ zdrojů, auto-discovery**

```
Week 24-25: Auto-discovery
  - Meta-scout agent: given list of URLs → batch scout + categorize
  - Template matching: new source → closest template → generate config
  - Priority queue: which sources to scrape first (relevance, staleness)
  - Parallel config generation (batch, like trik #4)

Week 26: Ops
  - Cost tracking per source (API tokens + Apify CUs)
  - Performance dashboard
  - Bulk operations (pause/resume/re-scout)
```

---

## Klíčová rozhodnutí k udělání

| # | Rozhodnutí | Doporučení | Proč |
|---|-----------|------------|------|
| 1 | YAML zůstane jako config formát? | Ano | 359 existujících configs, proven pattern, human-readable |
| 2 | Frontend framework | SvelteKit | Znáš ho, lightweight, SSR |
| 3 | API framework | Hono | Lightweight, TypeScript native, edge-ready |
| 4 | Agent SDK TS nebo Python? | TypeScript | Rewrite je do TS, SDK podporuje oboje |
| 5 | Apify actors v čem? | TypeScript | Konzistence se zbytkem stacku |
| 6 | Config git repo = monorepo s app? | Separátní repo | Configs mají vlastní lifecycle, agenti commitují |
| 7 | DB migrace | Drizzle ORM | TS native, lightweight, good Postgres support |
| 8 | Auth (UI) | Clerk nebo Lucia | Multi-user ready from start |
| 9 | Zachovat Python extraction? | Ne, port do TS | Jinak dual runtime na serveru |
| 10 | PDF parsing v Apify | Zachovat Python actor | docling/pymupdf nemají TS ekvivalent, jeden Python actor je OK |


---

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- FILE: AGENT-GRANULARITY.md -->
<!-- ═══════════════════════════════════════════════════════════ -->

# Agent Granularity: Source vs Catalog vs Opportunity

## Tři možnosti

### A) Všechny agenty × 3 úrovně (source/catalog/opportunity)

```
scout-source          scout-catalog          scout-opportunity
config-source         config-catalog         config-opportunity
validator-source      validator-catalog      validator-opportunity
fixer-source          fixer-catalog          fixer-opportunity
analyst-source        analyst-catalog        analyst-opportunity
                                             dedup-opportunity
```
18 agentů. Symetrické, ale je to potřeba?

### B) Každý agent jen na úrovních kde dává smysl

```
scout:      source ✓    catalog ✓    opportunity ✓
config:     source ✗    catalog ✓    opportunity ✓
validator:  source ✓    catalog ✓    opportunity ✓
fixer:      source ✗    catalog ✓    opportunity ✓
analyst:    source ✓    catalog ✓    opportunity ✗
dedup:      source ✗    catalog ✗    opportunity ✓
```
14 agentů. Asymetrické, ale přirozené.

### C) Jeden agent per typ, level jako parametr

```
scout(level: source|catalog|opportunity, target: url|id)
config(level: catalog|opportunity, target: ...)
validator(level: source|catalog|opportunity, target: ...)
fixer(level: catalog|opportunity, target: ...)
analyst(level: source|catalog, target: ...)
dedup(target: opportunity[])
```
6 agentů, polymorfní. Prompt se skládá dynamicky.

---

## Detailní rozbor per agent

### Scout

| Level | Co dělá | Dává smysl? |
|-------|---------|-------------|
| source | Analyzuje web, najde katalogy, detekuje typ | ✅ Vždy potřeba |
| catalog | Analyzuje katalog, najde příležitosti, pagination | ✅ Vždy potřeba |
| opportunity | Analyzuje detail, schema mapping, přílohy | ✅ Vždy potřeba |

**Verdict: 3 úrovně.** Každá má zásadně jiný úkol, jiný výstup, jiný kontext.
Source scout vrací katalogy. Catalog scout vrací URL. Opportunity scout vrací schema mapping.
Sloučit do jednoho = obří prompt, horší výsledky.

### Config generator

| Level | Co dělá | Dává smysl? |
|-------|---------|-------------|
| source | Generuje "meta-config" pro celý zdroj? | ⚠️ Sporné |
| catalog | Selektory pro listing, pagination pattern | ✅ Jasně definovaný úkol |
| opportunity | Selektory pro detail, field mapping | ✅ Jasně definovaný úkol |

**source-level config:** Co by obsahoval? Strategii (static/dynamic/api),
rate limiting, auth. Ale tohle je výstup scouta, ne config generátoru.
Config generator potřebuje konkrétní HTML k analýze.

**Verdict: 2 úrovně (catalog + opportunity).** Source-level "config" je
spíš metadata ze scouta, ne generovaný YAML.

### Validator

| Level | Co dělá | Dává smysl? |
|-------|---------|-------------|
| source | Aggregate quality across katalogů, trend detection | ✅ "Jak je na tom celý zdroj?" |
| catalog | Quality per katalog, per-field completeness | ✅ "Který katalog má problém?" |
| opportunity | Validace jednoho záznamu, field-level checks | ✅ "Je tento grant OK?" |

**Ale:** Source-level validace není nový agent — je to agregace catalog-level výsledků.
A opportunity-level validace je deterministic (schema check), ne agent.

**Realita:**
- opportunity-level: deterministický kód (JSON Schema, range checks) — NE agent
- catalog-level: agent (quality scoring, anomaly detection, LLM agreement check)
- source-level: kód (agregace) + agent (trend analysis, cross-catalog porovnání)

**Verdict: 1-2 úrovně jako agent (catalog, source). Opportunity = kód.**

### Fixer

| Level | Co dělá | Dává smysl? |
|-------|---------|-------------|
| source | Opravuje source-level problémy (strategie, auth)? | ⚠️ Rare |
| catalog | Opravuje listing selektory, pagination | ✅ Časté (web redesign) |
| opportunity | Opravuje detail selektory, field mapping | ✅ Časté |

**source-level fix:** Stane se, ale je to "web přešel z static na SPA" — celý
re-scout, ne fix. Nebo "přidali CAPTCHA" — to fixer agent nevyřeší.

**Verdict: 2 úrovně (catalog + opportunity).** Source-level = re-scout.

### Analyst

| Level | Co dělá | Dává smysl? |
|-------|---------|-------------|
| source | Statistiky jednoho zdroje, trendy, doporučení | ✅ "Jak si vede TAČR?" |
| catalog | Statistiky katalogu, srovnání s jinými katalogy | ✅ Ale překryv se source |
| opportunity | Analýza jedné příležitosti? | ❌ To je detail view, ne analýza |

**catalog vs source:** Catalog-level analýza je podmnožina source-level.
Rozumný analyst dostane source + jeho katalogy a analyzuje vše naráz.

**Verdict: 1 úroveň (source).** Případně cross-source analyst jako bonus.

### Dedup judge

| Level | Co dělá | Dává smysl? |
|-------|---------|-------------|
| source | Deduplikace uvnitř jednoho zdroje? | ⚠️ Rare (ale stane se) |
| catalog | Deduplikace uvnitř katalogu? | ⚠️ Rare |
| opportunity | "Jsou tyto dvě příležitosti stejné?" | ✅ Core function |

**Verdict: 1 úroveň (opportunity pair).** Candidate pair selection je kód,
judge je agent.

---

## Srovnání

```
                    Option A        Option B        Option C
                    (všechny×3)     (asymetrické)   (polymorfní)

Počet agentů        18              14              6
Prompt specifita    Vysoká          Vysoká          Střední
Údržba promptů      18 promptů      14 promptů      6 promptů + builder
Testovatelnost      Snadná          Snadná          Těžší (kombinatorika)
Kontext izolace     Nejlepší        Dobrá           Záleží na implementaci
Zbytečné agenty     4 zbytečné      0               0
Nový level          Přidej agenta   Přidej agenta   Přidej if/case
Konzistence API     Jednotná        Nejednotná      Jednotná
```

### Option A: Plošně 3 úrovně

**Pro:** Konzistentní mental model. `grantio scout tacr --level source`,
`grantio validate tacr --level catalog --name vyzvy`. Vždy víš co existuje.

**Proti:** 4 agenty které nemají reálný úkol (config-source, fixer-source,
analyst-opportunity, analyst-catalog jako separátní od source). Buď budou
mít vymyšlený úkol, nebo budou thin wrappery.

### Option B: Jen kde dává smysl

**Pro:** Každý agent má jasný, distinktní úkol. Žádné redundance.

**Proti:** Nekonzistentní API. "Proč můžu fixovat catalog ale ne source?"
Musíš to dokumentovat / vysvětlovat v UI.

### Option C: Polymorfní

**Pro:** Nejméně kódu. Jeden agent type, level jako parametr.
Prompt builder skládá prompt z bloků per level.

**Proti:** Prompt pro source-level scout vs opportunity-level scout je
zásadně jiný. "Polymorfní" = obří switch/case v prompt builderu.
Horší pro Agent SDK subagent pattern (subagent = fixní prompt + tools).
Testování = kombinatorická exploze.

---

## Doporučení: Option B s konzistentním API

Použij Option B (asymetrické), ale s konzistentním interface:

```typescript
// Každý agent typ má explicitní levels
const AGENT_LEVELS = {
  scout:     ["source", "catalog", "opportunity"],
  config:    ["catalog", "opportunity"],
  validator: ["source", "catalog"],  // opportunity = kód, ne agent
  fixer:     ["catalog", "opportunity"],
  analyst:   ["source"],             // cross-source jako bonus
  dedup:     ["opportunity"],
} as const;

// CLI/API je konzistentní:
// grantio <command> <source> [--level <level>] [--target <name|url>]

// Pokud level není podporovaný:
// "fixer nepodporuje source level. Source-level problémy řeší re-scout."
```

### Výsledná agent mapa

```
AGENT              LEVEL        TOOLS                   MODEL     NOTES
─────────────────────────────────────────────────────────────────────────
scout-source       source       WebFetch,WebSearch,Read  sonnet    → katalogy
scout-catalog      catalog      WebFetch,Read            sonnet    → opportunity URLs
scout-opportunity  opportunity  WebFetch,Read            sonnet    → schema mapping

config-catalog     catalog      Read,Write,Edit,Bash     sonnet    → listing YAML
config-opportunity opportunity  Read,Write,Edit,Bash     sonnet    → detail YAML

validator-source   source       Read,Bash                sonnet    → aggregate + trends
validator-catalog  catalog      Read,Bash,WebFetch       haiku     → quality scoring

fixer-catalog      catalog      Read,Write,Edit,Bash,Web sonnet    → oprava listing
fixer-opportunity  opportunity  Read,Write,Edit,Bash,Web sonnet    → oprava detail

analyst-source     source       Read,Bash                sonnet    → statistiky, doporučení

dedup-opportunity  opportunity  Read                     haiku     → pair judgment
─────────────────────────────────────────────────────────────────────────
                                                          12 agentů total
```

### Co NENÍ agent (je to kód)

```
- Opportunity-level validace     → JSON Schema + range checks + encoding
- Catalog-level data aggregace   → SQL queries
- Source-level quality agregace  → SQL over catalog scores
- Dedup candidate selection      → fuzzy matching algorithm
- Scheduling                     → Apify cron
- Config git operations          → git CLI
- Notification routing           → Telegram API
```

Pravidlo: **Agent = potřebuješ úsudek. Kód = potřebuješ determinismus.**


---

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- FILE: UI-ARCHITECTURE.md -->
<!-- ═══════════════════════════════════════════════════════════ -->

# UI Architecture v2 — s katalogy

## Navigace

```
/dashboard
/sources
/sources/:slug                    ← Source Workspace
/sources/:slug/catalogs/:id       ← Catalog Workspace
/sources/:slug/catalogs/:id/opportunities/:id  ← Opportunity Detail
/opportunities                    ← Global search
/matching                         ← Future
```

## Hierarchie workspace

```
Source Workspace
├── overview, config, runs, hints, quality, memory
└── catalogy (seznam)
    └── Catalog Workspace
        ├── overview, config, runs, hints, quality
        └── příležitosti (seznam)
            └── Opportunity Detail
                ├── všechna pole, provenance, confidence
                ├── přílohy
                ├── quality per field
                └── dedup cluster
```

Tři úrovně workspace, každá se stejným vzorem:
**config + runs + hints + quality + data**

---

## Screens

### /dashboard

```
┌─────────────────────────────────────────────────────────┐
│ Grantio Dashboard                                        │
│                                                          │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────────┐  │
│ │ 239     │ │ 847     │ │ 6,211   │ │ 12 broken     │  │
│ │ sources │ │ catalogs│ │ grants  │ │ ⚠ alerts      │  │
│ └─────────┘ └─────────┘ └─────────┘ └───────────────┘  │
│                                                          │
│ Recent Runs          Quality Trends     Alerts           │
│ ┌──────────────┐     ┌────────────┐    ┌──────────────┐ │
│ │ tacr scout ✅│     │ ▁▃▅▇█▇▅▃▁│    │ mzp: 85→42  │ │
│ │ mzp fix ❌  │     │ avg: 78%   │    │ sfdi: timeout│ │
│ │ irop scrape ✅│    └────────────┘    └──────────────┘ │
│ └──────────────┘                                         │
└─────────────────────────────────────────────────────────┘
```

### /sources

```
┌─────────────────────────────────────────────────────────┐
│ Sources                              [+ Add Source]      │
│                                                          │
│ Filter: [All ▾] [Active ▾] [Quality ▾] [Search...]     │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🟢 tacr-cz          3 catalogs  47 grants   82% ▓▓░│ │
│ │    TAČR              last: 2h ago            v2     │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ 🟢 dotaceeu-cz      7 catalogs  312 grants  74% ▓▓░│ │
│ │    DotaceEU          last: 1d ago            v1     │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ 🔴 mzp-cz           1 catalog   23 grants   42% ▓░░│ │
│ │    Min. živ. prostředí  last: 3d ago  BROKEN        │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### /sources/:slug — Source Workspace

```
┌─────────────────────────────────────────────────────────┐
│ ← Sources    tacr-cz                    [Scout] [Fix]   │
│ TAČR — Technologická agentura ČR                        │
│ https://www.tacr.cz  •  search-based  •  🟢 active     │
│                                                          │
│ ┌──────────────────────────────────────────────────────┐│
│ │ Overview │ Catalogs │ Runs │ Hints │ Quality │ Config ││
│ └──────────────────────────────────────────────────────┘│
│                                                          │
│ ═══ Overview ════════════════════════════════════════════│
│                                                          │
│ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────┐│
│ │ 3 catalogs│ │ 47 grants │ │ 82%       │ │ 91%      ││
│ │           │ │           │ │ complete  │ │ quality  ││
│ └───────────┘ └───────────┘ └───────────┘ └──────────┘│
│                                                          │
│ Strategy: search-based → html-detail                     │
│ Config version: v2 (git: a3f8c21, 2d ago)               │
│ Memory: 3 topics (structure, failures, decisions)        │
│ Hints: 2 unresolved                                      │
│                                                          │
│ ═══ Catalogs ════════════════════════════════════════════│
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Veřejné soutěže         32 grants  85% ▓▓▓░  🟢 │   │
│ │ Programy                12 grants  78% ▓▓░░  🟢 │   │
│ │ Archiv                   3 grants  65% ▓▓░░  🟡 │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ ═══ Recent Runs ═════════════════════════════════════════│
│                                                          │
│ ┌──────────────────────────────────────────────────┐    │
│ │ #47 scout     2h ago    ✅ 14s   $0.03         │    │
│ │ #46 scrape    1d ago    ✅ 2m    $0.12  +3 new │    │
│ │ #45 validate  1d ago    ✅ 8s    $0.01         │    │
│ │ #44 fix       3d ago    ✅ 45s   $0.08  v1→v2  │    │
│ └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### /sources/:slug/catalogs/:id — Catalog Workspace

```
┌─────────────────────────────────────────────────────────┐
│ ← tacr-cz    Veřejné soutěže          [Scrape] [Fix]   │
│ https://www.tacr.cz/vyzvy  •  paginated-list  •  🟢    │
│                                                          │
│ ┌──────────────────────────────────────────────────────┐│
│ │ Overview │ Opportunities │ Runs │ Hints │ Quality │   ││
│ │          │               │      │       │         │Config│
│ └──────────────────────────────────────────────────────┘│
│                                                          │
│ ═══ Overview ════════════════════════════════════════════│
│                                                          │
│ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────┐│
│ │ 32 grants │ │ 85%       │ │ 92%       │ │ v2       ││
│ │ (5 new)   │ │ complete  │ │ quality   │ │ config   ││
│ └───────────┘ └───────────┘ └───────────┘ └──────────┘│
│                                                          │
│ Pagination: page_number, 10/page, 4 pages                │
│ Strategy: paginated-list → html-detail                   │
│ Listing selector: .grant-card                            │
│ Last scrape: 1d ago (run #46)                            │
│                                                          │
│ ═══ Opportunities ═══════════════════════════════════════│
│                                                          │
│ Filter: [Open ▾] [Deadline ▾] [Quality ▾] [Search...]  │
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ ✅ SIGMA – Průmyslový výzkum                      │   │
│ │    deadline: 31.3.2026  amount: 2-50M CZK  95%   │   │
│ ├───────────────────────────────────────────────────┤   │
│ │ ✅ THÉTA – Energetický výzkum                      │   │
│ │    deadline: 15.4.2026  amount: 1-30M CZK  88%   │   │
│ ├───────────────────────────────────────────────────┤   │
│ │ ⚠️ ÉTA – Společenské výzvy                        │   │
│ │    deadline: ???  amount: ???  52% ← incomplete    │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ ═══ Config ══════════════════════════════════════════════│
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ catalog:                                           │   │
│ │   url: "https://www.tacr.cz/vyzvy"               │   │
│ │   strategy: html_catalog                           │   │
│ │   listing_selector: ".grant-card"                  │   │
│ │   fields:                                          │   │
│ │     title:                                         │   │
│ │       selector: "h3.card-title"                    │   │
│ │     deadline:                                      │   │
│ │       selector: ".deadline"                        │   │
│ │       steps:                                       │   │
│ │         - method: regex                            │   │
│ │           pattern: "(\d{1,2}\.\s*\d..."           │   │
│ │                                                    │   │
│ │ [Edit] [Git History ↗] [v2 ← v1 diff]            │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ ═══ Hints ═══════════════════════════════════════════════│
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ 🔵 Pavel, 2d ago:                                  │   │
│ │ "Paginace je broken po str.50, fallback na API"   │   │
│ │ → Resolved by run #44 (fix)                        │   │
│ │                                                    │   │
│ │ 🟡 Martin, 1h ago:                                 │   │
│ │ "Nová sekce 'Mimořádné výzvy' se nesbírá"         │   │
│ │ → Unresolved                     [Mark Resolved]  │   │
│ └───────────────────────────────────────────────────┘   │
│ [+ Add Hint]                                             │
│                                                          │
│ ═══ Quality ═════════════════════════════════════════════│
│                                                          │
│ Per-field completeness:                                  │
│ title         ████████████████████ 100%                  │
│ description   ████████████████░░░░  80%                  │
│ deadline      ████████████████████ 100%                  │
│ funding.max   ████████████░░░░░░░░  60%                  │
│ funding.cofin ████░░░░░░░░░░░░░░░░  20% ← problém      │
│ eligibility   ████████████████░░░░  80%                  │
│ attachments   ████████████████████ 100%                  │
│                                                          │
│ Issues:                                                  │
│ ⚠ funding.cofinancingRate missing in 80% records        │
│   → Hint: "Spolufinancování je v PDF příloze"           │
│ ⚠ 3 records in quarantine (amount > 50B ceiling)        │
└─────────────────────────────────────────────────────────┘
```

### /sources/:slug/catalogs/:id/opportunities/:id — Opportunity Detail

```
┌─────────────────────────────────────────────────────────┐
│ ← Veřejné soutěže    SIGMA – Průmyslový výzkum         │
│ https://www.tacr.cz/vyzvy/sigma-123  •  🟢 open        │
│                                                          │
│ ═══ Data ════════════════════════════════════════════════│
│                                                          │
│ Field              Value                  Source   Conf  │
│ ─────────────────────────────────────────────────────── │
│ title              SIGMA – Průmyslový...  css      0.99 │
│ description        Program podporuje...   css+llm  0.95 │
│ provider           TAČR                   css      0.99 │
│ programme          SIGMA                  css      0.99 │
│ funding.min        2,000,000 CZK          css      0.90 │
│ funding.max        50,000,000 CZK         css      0.90 │
│ funding.cofin      —                      missing  —    │
│ dates.deadline     2026-03-31             regex    0.95 │
│ dates.deadlineType fixed                  llm      0.85 │
│ eligibility.types  [s.r.o., a.s., VŠ]    llm      0.80 │
│ eligibility.region [CZ0]                  llm      0.75 │
│ status             open                   css      0.95 │
│                                                          │
│ Quality: 88%  (14/16 fields)                             │
│ Lifecycle: announced  →  threshold: 95%  →  ⚠ below    │
│                                                          │
│ ═══ Attachments ═════════════════════════════════════════│
│                                                          │
│ 📄 Zadávací dokumentace.pdf     2.3 MB   [parsed ✅]    │
│ 📄 Příloha 1 – Rozpočet.xlsx   156 KB   [not parsed]   │
│ 📄 Příloha 2 – Hodnocení.pdf   890 KB   [parsed ✅]    │
│                                                          │
│ ═══ Provenance ══════════════════════════════════════════│
│                                                          │
│ Scraped: 2026-03-08T14:30 (run #46)                     │
│ Config: v2 (git: a3f8c21)                                │
│ Extraction log:                                          │
│   title: css(".grant-title") → "SIGMA – Průmyslový..."  │
│   deadline: css(".deadline") → "31. 3. 2026"             │
│             regex → match "31. 3. 2026"                  │
│             transform(parse_czech_date) → "2026-03-31"   │
│   funding.cofin: css(".cofin") → empty                   │
│                   llm(haiku) → null (not on page)        │
│                   ⚡ Hint: "je v PDF příloze"             │
│                                                          │
│ ═══ Dedup ═══════════════════════════════════════════════│
│                                                          │
│ Cluster: #127 (2 records)                                │
│ Also found at: dotaceeu.cz/vyzvy/sigma-2026 (91% match) │
│ This record is PRIMARY (higher completeness)             │
│                                                          │
│ ═══ Hints ═══════════════════════════════════════════════│
│                                                          │
│ No opportunity-level hints.  [+ Add Hint]                │
└─────────────────────────────────────────────────────────┘
```

### Run Detail (shared across all levels)

```
┌─────────────────────────────────────────────────────────┐
│ ← tacr-cz    Run #44: fix-catalog    ✅ completed       │
│ 3d ago  •  45s  •  $0.08  •  config v1→v2              │
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ 🤖 Reading quality report...                       │   │
│ │                                                    │   │
│ │ 📋 validator-catalog report: 3 issues              │   │
│ │    - .deadline selector returns empty on 5 pages   │   │
│ │    - pagination breaks after page 50               │   │
│ │    - .cofin selector not found                     │   │
│ │                                                    │   │
│ │ 💡 Loading hints...                                │   │
│ │    Pavel: "Paginace broken po str.50, zkus API"    │   │
│ │                                                    │   │
│ │ 🧠 Reading memory: failures.md                     │   │
│ │    Previous attempt: CSS pagination → failed >50   │   │
│ │                                                    │   │
│ │ 🔧 Generating new config v2...                     │   │
│ │    - Changed: pagination strategy → api_fallback   │   │
│ │    - Changed: deadline selector → ".info-date"     │   │
│ │    - Unchanged: cofin (hint says "in PDF")         │   │
│ │                                                    │   │
│ │ 🧪 Testing on 5 sample URLs...                     │   │
│ │    ✅ 5/5 title extracted                          │   │
│ │    ✅ 5/5 deadline extracted (was 0/5)             │   │
│ │    ✅ pagination: 52 URLs found (was 50 max)       │   │
│ │                                                    │   │
│ │ 📝 Updated memory: decisions.md                    │   │
│ │    "Switched to API fallback for pagination.       │   │
│ │     Deadline selector changed after site redesign. │   │
│ │     cofin intentionally skipped — data in PDF."    │   │
│ │                                                    │   │
│ │ ✅ Config v2 committed. Quality: 72% → 85%.        │   │
│ │    Hint "Paginace broken" marked as resolved.      │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ Config diff: [View v1 → v2 diff]                        │
│ Quality delta: +13% completeness, +8% quality            │
│ Resolved hints: 1                                        │
└─────────────────────────────────────────────────────────┘
```

---

## Vzor: Workspace komponenta

Všechny tři úrovně sdílejí stejný UI vzor:

```typescript
interface WorkspaceProps {
  entity: Source | Catalog | Opportunity;
  level: "source" | "catalog" | "opportunity";

  // Společné tabs (všechny úrovně)
  tabs: {
    overview:  true;       // vždy
    runs:      true;       // vždy (chaty)
    hints:     true;       // vždy
    quality:   true;       // vždy
    config:    boolean;    // source: meta, catalog: YAML, opportunity: ne
  };

  // Level-specific tabs
  children?: {
    source:      "catalogs tab";
    catalog:     "opportunities tab";
    opportunity: "provenance tab, attachments tab, dedup tab";
  };
}
```

Tím dostaneš **konzistentní UX** — uživatel se naučí vzor jednou
(overview + runs + hints + quality) a naviguje ho na všech úrovních.

---

## Navigační breadcrumbs

```
Dashboard > Sources > tacr-cz > Veřejné soutěže > SIGMA – Průmyslový výzkum
                      (source)   (catalog)          (opportunity)
```

Každý level je klikatelný, vždy víš kde jsi v hierarchii.


---

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- FILE: CLI.md -->
<!-- ═══════════════════════════════════════════════════════════ -->

# Grantio CLI

## Princip

CLI = přímý přístup k Agent SDK. Žádný server, žádná DB.
Filesystem je databáze. Git je verzování. Stdout je API.

## Příkazy

```bash
grantio init                              # Vytvoří workspace (.claude/, shared/, sources/)
grantio add <url> [--name tacr]           # Nový zdroj → sources/{slug}/

grantio scout <source>                    # Scout celý zdroj (3 subagenty)
grantio scout <source> --catalog <url>    # Scout jen konkrétní katalog
grantio scout <source> --opportunity <url> # Scout jen jednu příležitost

grantio scrape <source>                   # Generuj scrapery + spusť
grantio scrape <source> --catalog-only    # Jen katalogový scraper
grantio scrape <source> --dry-run         # Generuj ale nespouštěj

grantio validate <source>                 # Validace
grantio validate <source> --benchmark     # + holdout test
grantio analyze <source>                  # Analýza dat
grantio analyze --all                     # Cross-source

grantio hint <source> "text"              # Hint pro source úroveň
grantio hint <source> -c <catalog> "text" # Hint pro katalog
grantio hint <source> -o "text"           # Hint pro opportunity

grantio status                            # Tabulka všech zdrojů
grantio status <source>                   # Detail jednoho

grantio run <source> "<prompt>"           # Ad-hoc agent prompt
grantio log <source> [--last]             # Poslední run log
```

## Výstup

Vždy dvě úrovně:
- **stderr**: progress, emoji, human-readable (to co vidíš v terminálu)
- **stdout**: JSON (pipeable, parsovatelné)

```bash
# Human mode (default)
$ grantio scout tacr
🔍 Scouting tacr.cz...
  ✅ 3 catalogy nalezeny
  ✅ 47 příležitostí v katalogu "Veřejné soutěže"
  ✅ Schema mapping pro detail: 14/18 polí
📄 Report: sources/tacr-cz/scouts/2026-03-09T14-00_source.json

# Pipe mode (JSON na stdout)
$ grantio scout tacr --json | jq '.catalogs | length'
3

# Compose
$ grantio scout tacr && grantio scrape tacr && grantio validate tacr
```

## Status výstup

```
$ grantio status

 Source       Catalogs  Opportunities  Complete  Quality  Scraper  Last Run
 tacr-cz      3         47            82%       91%      v2       2h ago
 dotaceeu-cz  7         312           74%       85%      v1       1d ago
 mzp-cz       1         23            58% ⚠    72% ⚠   v1       3d ago

$ grantio status tacr

 tacr-cz
 URL:        https://www.tacr.cz
 Strategy:   search-based → html-detail
 Catalogs:   3 (Veřejné soutěže, Programy, Archiv)
 Scrapers:   catalog v2, opportunity v1
 Data:       47 opportunities, 82% complete, 91% quality
 Hints:      2 (1 source, 1 catalog)
 Last scout: 2026-03-09T14:00
 Last scrape: 2026-03-09T15:30
 Issues:     funding.cofinancingRate missing in 60% records
```

## Co CLI NENÍ

- Není webserver (to přijde později jako `grantio serve`)
- Není scheduler (to přijde jako cron + `grantio scrape --all`)
- Není notification system (to přijde s UI)
- Není multi-user (hinty přes CLI, git push pro sdílení)

## Iterační plán CLI

```
Iterace 0:  grantio run <url> "<prompt>"     ← jen wrapper nad Agent SDK
Iterace 1:  grantio scout <source>           ← scout pipeline
Iterace 2:  grantio scrape <source>          ← scraper generation
Iterace 3:  grantio validate <source>        ← validation
Iterace 4:  grantio hint + status            ← collaboration basics
Iterace 5:  grantio analyze                  ← analytics
Iterace 6:  --json flag, piping, compose     ← unix philosophy
```

## Implementace

Jeden `src/cli.ts` s command router.
Každý command = funkce co volá Agent SDK `query()`.
Parsování args: minimální (yargs nebo commander).

```
src/
├── cli.ts              # Entry point, command router
├── commands/
│   ├── init.ts         # Scaffold workspace
│   ├── add.ts          # Add source
│   ├── scout.ts        # Scout pipeline
│   ├── scrape.ts       # Scraper gen + run
│   ├── validate.ts     # Validation
│   ├── analyze.ts      # Analysis
│   ├── hint.ts         # Add hint
│   ├── status.ts       # Status display
│   ├── run.ts          # Ad-hoc prompt
│   └── log.ts          # View logs
├── lib/
│   ├── agent.ts        # Agent SDK wrapper (query + logging)
│   ├── project.ts      # Source project filesystem ops
│   └── output.ts       # Stderr (human) + stdout (JSON) formatting
└── ...
```


---

<!-- ═══════════════════════════════════════════════════════════ -->
<!-- FILE: KNOWLEDGE-EXTRACTION.md -->
<!-- ═══════════════════════════════════════════════════════════ -->

# Grantio: Knowledge Extraction z prototypu

Tento dokument je interview guide. Cíl: extrahovat všechno co prototyp
ví — architektonická rozhodnutí, edge cases, co fungovalo, co ne, jaká
data existují, jaké jsou typy a strategie. Odpovědi budou vstupem pro
rewrite do TypeScript.

Odpovídej detailně. Kód, YAML ukázky, příklady z reálných zdrojů.
Čím konkrétnější, tím lepší. U každé odpovědi uveď příklad z praxe.

---

## A. Datový model a schéma

### A1. Opportunity typy
Jaké typy příležitostí rozlišuješ? (výzva, program, dotační titul,
podprogram, opatření, grantová soutěž, průběžná výzva, mimořádná výzva...)
Které typy mají zásadně jiná pole? Uveď příklady z reálných zdrojů.

### A2. Povinná vs. volitelná pole
Jaká pole jsou povinná pro VŠECHNY příležitosti?
Jaká pole jsou povinná jen pro určitý typ zdroje?
Jaká pole jsou "nice to have" ale většinou chybí?
Existuje matice: typ zdroje × povinnost pole?

### A3. Funding model varianty
Jak se liší finanční údaje across zdrojů?
- Fixní částka vs. rozsah (min-max)
- Celková alokace vs. per-projekt
- Spolufinancování: procento, absolutní, "dle pravidel OP"
- Měna: CZK, EUR, mix
- "Částka není uvedena" vs. "částka je v příloze" vs. "rozpočet neomezen"

### A4. Eligibility varianty
Jak strukturuješ způsobilost?
- Typy žadatelů: jaký je slovník? (s.r.o., obec, VŠ, FO, NNO...)
- Regiony: NUTS kódy? Volný text? Výčet krajů?
- Sektory/obory: existuje číselník? Nebo volný text?
- Podmínky: strukturované nebo jen text?

### A5. Datum model
Jaké datumy reálně existují across zdrojů?
- Vyhlášení, zahájení příjmu, uzávěrka, hodnocení, zahájení projektu, konec
- Průběžná výzva (žádný deadline) — jak to modeluješ?
- Vícekol. hodnocení (deadline 1. kolo, 2. kolo...)
- "Do vyčerpání alokace" — deadline nebo status?

### A6. Status model
Jaké stavy příležitosti rozlišuješ?
Jak se liší status na webu vs. tvůj interní status?
Příklad: web říká "aktivní" ale deadline byl včera.

### A7. Přílohy
Jaké typy příloh existují?
Které přílohy obsahují strukturovaná data (rozpočet, hodnotící kritéria)?
Jak odlišuješ "informační PDF" od "vyplnitelného formuláře"?
Stahují se přílohy vždy, nebo jen selektivně?

### A8. Meta / extensions
Jaká source-specific pole existují mimo univerzální schéma?
Příklady: TAČR má "programové období", IROP má "prioritní osu",
nadace mají "účel nadace". Jak to modeluješ?

---

## B. Source a Catalog typy

### B1. Taxonomie zdrojů
Jaké typy zdrojů rozlišuješ? (ministerstvo, agentura, nadace, kraj,
EU program, mezinárodní...) Kolik zdrojů je v každé kategorii?
Které kategorie mají zásadně jiné chování?

### B2. Catalog typy
Jaké typy katalogů existují?
- HTML listing (stránkovaný, infinite scroll, load more)
- Search-based (formulář → výsledky)
- API endpoint
- RSS/Atom feed
- PDF/Excel se seznamem
- Sitemap
- Single page (všechny výzvy na jedné stránce)

Kolik z 359 konfigurací spadá do které kategorie?

### B3. Opportunity detail typy
Jaké typy detail stránek existují?
- Strukturovaná HTML stránka
- Multi-tab/multi-page
- Data primárně v PDF
- API JSON response
- Iframe (IS KP14+)
- Kombinace

### B4. Strategie detekce
Jak ContentDetector rozhoduje o strategii?
Jaká je přesná logika (4 vrstvy z blog postu)? Je to v kódu, nebo v configu?
Jak často detekce selže a musíš strategii nastavit ručně?

### B5. Problematické zdroje
Které zdroje jsou nejproblematičtější? Top 10 "nightmare sources".
Co je na nich problematického? (anti-bot, JS rendering, nestandardní
formáty, časté redesigny, broken HTML...)

### B6. Template configs
Zmínil jsi že většina zdrojů spadá do vzorů. Kolik template configs máš?
Jak vypadají? Jaká je distribuce zdrojů per template?

---

## C. Extraction pipeline

### C1. Step typy
Jaké step typy existují v multi-step extraction?
(css, regex, xpath, transform, llm, fallback, composite...)
Jsou nějaké step typy co v blogu nezmínil?

### C2. Transform registr
Jaké transformace existují? Kompletní seznam.
Které jsou nejpoužívanější?
Které jsou source-specific vs. universal?

### C3. LLM extraction
Jaké prompty používáš pro LLM extraction?
Liší se per pole? Per typ zdroje?
Jak řešíš anti-fabrikaci — kompletní prompt?
Jaký je formát LLM odpovědi (JSON schema, volný text, structured output)?

### C4. Confidence scoring
Jak počítáš confidence score per field?
- CSS hit = jaký default confidence?
- Regex hit?
- LLM extraction?
- LLM agreement check zvyšuje/snižuje o kolik?
- Jak se confidence promítá do quality score?

### C5. Field extraction provenance
Co přesně ukládáš per extracted field?
(method, raw_text, selector, confidence, llm_agreement, timestamp...)
Jaká je datová struktura FieldExtraction?

### C6. Fallback chains
Jak řešíš fallback když primární metoda selže?
Je fallback per-field, per-page, nebo per-source?
Příklad kompletní fallback chain pro "deadline" pole.

---

## D. Config generování (autonomní loop)

### D1. Config loop architektura
Jak přesně funguje config loop z triku #4?
- Jaký je vstup? (URL? Scout report? Template?)
- Kolik iterací typicky potřebuje?
- Jaká je stop condition? (80% detail URLs + 95% field completeness)
- Jak měří completeness během generování?
- Jak vypadá prompt pro config generátor?

### D2. Config validace
Jak validuješ vygenerovaný config PŘED spuštěním?
(Selector syntax check, required fields, schema validation...)
Co všechno může být špatně?

### D3. Config diffing
Jak porovnáváš dvě verze configu?
Co je "breaking change" vs. "improvement"?
Jak rozhoduješ jestli nová verze je lepší?

### D4. Config debugging
Když scraper vrátí špatná data, jak zjistíš KTERÝ step v extraction
pipeline selhal? Máš debug mode? Jak vypadá debug výstup?

---

## E. Quality a validace

### E1. Quality score formula
Jak přesně počítáš overall quality score?
Je to vážený průměr? Jaké jsou váhy?
Jak se liší formula pro různé lifecycle stages?

### E2. Validační pravidla — kompletní seznam
Všechna pravidla co karanténují nebo flagují record.
(Amount range, date range, URL reachability, encoding, duplicity,
field length, HTML in text, ...)

### E3. Quality regression detection
Jak přesně funguje SyncDetector?
Co je threshold pro alert? (10% drop z blogu — je to konfigurovaitelné?)
Jak řešíš false positives? (Legitimní pokles — zdroj smazal výzvy.)

### E4. Lifecycle scoring detail
Kompletní tabulka lifecycle stages × quality thresholds.
Jak se detekuje lifecycle stage? (Z webu? Z dat? Manuálně?)
Jak řešíš přechod mezi stages? (announced → open → closed)

### E5. Karanténa workflow
Co se děje s karanténovanými záznamy?
Kdo je reviewuje? Jak se uvolní?
Kolik % záznamů typicky skončí v karanténě?

---

## F. Agent loop a prompty

### F1. Scout prompty
Kompletní prompt pro scout-source. Jak se liší pro scout-catalog
a scout-opportunity? Jaký kontext dostává? (HTML? Jen URL? Ořezaný HTML?)

### F2. Config generator prompt
Kompletní prompt. Jak předáváš scout report? Schema mapping?
Jak říkáš agentovi "vygeneruj YAML"? Jaký formát odpovědi vyžaduješ?

### F3. LLM extraction prompty per pole
Jak vypadají prompty pro individual field extraction?
(Title, description, deadline, amount, eligibility, status...)
Jsou per-source customizované, nebo univerzální?

### F4. Anti-fabrikace kompletní
Kompletní sada anti-fabrikačních pravidel.
Které prompty to mají? Jak se liší per agent?
Co je nejčastější fabrikace? (Z blogu: MK ČR rozpočet.)

### F5. Enrichment prompty
Jak vypadá enrichment institucí (trik #21 zmíněný v kontextu pipe deadlock)?
Co je enrichment vs. extraction? Jaká data enrichment přidává?

### F6. Agreement check prompt
Jak vypadá prompt pro LLM agreement check (trik #15)?
Dostává LLM jen raw text, nebo i CSS-extrahovanou hodnotu?
Jak formuluješ otázku aby LLM neznal "správnou odpověď"?

---

## G. Agent loop logika

### G1. Main loop
Jak vypadá hlavní smyčka jednoho scrape runu?
1. Načti config → 2. ??? → ... → N. Ulož výsledky
Kompletní flow diagram.

### G2. Retry a error handling
Jak se liší chování na různé chyby?
- Network timeout → ?
- 403 → ?
- 429 → ?
- 404 → ?
- Selector vrátí prázdný výsledek → ?
- LLM hallucination detected → ?
- Billing error → ?

### G3. Paralelizace
Jak běží batch na 50 zdrojů?
- Kolik paralelně?
- Jak se sdílí LLM client (billing error je globální)?
- Jak se izolují chyby jednoho zdroje od ostatních?

### G4. Checkpoint granularita
Jaké jsou přesně checkpointovací body?
(catalog_complete, details_batch_0, ...) Jak se určuje batch size?
Co se děje když spadne uprostřed batche?

### G5. Rate limiting per source
Jak řešíš rate limiting?
- Globální vs. per-source?
- Konfigurovatelné v YAML?
- Jak zjistíš co je "safe" rate? (robots.txt? Trial and error?)

---

## H. Memory a hints

### H1. Co si agent pamatuje
Jaké informace se dnes předávají mezi runy?
(Config history? Předchozí chyby? Scout reports?)
Co se NEPŘEDÁVÁ a mělo by?

### H2. Hint format v praxi
Jak vypadají reálné hinty co jsi psal?
Top 20 nejužitečnějších hintů. Jaký pattern mají?
Které hinty vedly k biggest quality improvement?

### H3. Hint resolution
Jak poznaš že hint byl "vyřešen"?
Je to manuální, nebo automatické? (Fixer aplikoval → hint resolved?)

### H4. Failure knowledge
Jaké "failures" stojí za zapamatování?
(Selektor X nefunguje od redesignu Y. Web Z má rate limit 1req/5s.
PDF z webu W je vždy corrupt.)
Kde to dnes žije? (V hlavě? V kódu? V komentářích?)

### H5. Decisions knowledge
Jaká rozhodnutí stojí za zapamatování?
("Pro TAČR používáme API místo HTML protože paginace je broken.")
Jak se dnes rozhodnutí propagují do dalších runů?

---

## I. Infrastruktura a operace

### I1. Apify zkušenosti
Už používáš Apify? Pokud ne, jak dnes scrapery běží?
(Lokálně? Cron? Docker?)

### I2. Storage
Kde žijí scraped data?
(JSON soubory? SQLite? Postgres? Apify dataset?)
Jak velká je DB? (6211 grantů × kolik KB per grant?)

### I3. Git workflow
Jak dnes verzuješ YAML configs?
Auto-commit? Manuální? Jaký commit message format?
Jak řešíš merge conflicts (dva běhy změní stejný config)?

### I4. Monitoring dnes
Jak dnes víš že scraper je broken?
(Manuální check? Alerting? Vůbec nevíš dokud se nepodíváš?)

### I5. Cost tracking
Kolik stojí jeden full run?
- Tokens per source (scout, config gen, extraction, agreement check)
- Apify CUs (pokud relevantní)
- Jaký je poměr LLM cost vs. "zbytek"?

---

## J. Edge cases a triky

### J1. Nezmíněné triky
Jsou triky co se do blog postu nedostaly?
Anti-bot obcházení? Proxy? Cookie handling? Session management?

### J2. Největší WTF momenty
Top 5 věcí co tě nejvíc překvapily/frustrovaly.
Edge cases co žádný tutorial nepokryje.

### J3. Čeština specifika
Mimo datumy a částky — co dalšího je česko-specifické?
(Diakritika v selektorech? Encoding? Pravopis vs. úřední jazyk?)

### J4. PDF specifika
Mimo parser chain — co dalšího?
Jak řešíš password-protected PDF? Scanned (OCR needed) vs native?
Tabulky v PDF — jaký je success rate?

### J5. JavaScript specifika
20% webů renderuje JS. Ale kolik z nich renderuje SPECIFICKY
grant data JSem vs. jen navigaci/layout?
Které konkrétní frameworky/CMS jsi potkal? (React, Vue, Next, WordPress, custom...)

---

## K. Výstupy a struktury

### K1. Scout report structure
Jak přesně vypadá výstup scout-source? Scout-catalog? Scout-opportunity?
Reálný příklad z TAČR.

### K2. Config YAML structure
Kompletní YAML schema. Všechny možné pole, všechny step typy,
všechny strategie. Nejkomplikovanější config co máš.

### K3. FieldExtraction structure
Kompletní datová struktura. Všechna metadata per extracted field.

### K4. Quality report structure
Jak vypadá quality report? Per-source, per-field breakdown.

### K5. Quarantine record structure
Kompletní. S reálným příkladem.

### K6. Run log structure
Co se loguje per run? Jak vypadá log jednoho complete runu?

---

## L. Rozhodnutí pro rewrite

### L1. Co by sis přál udělat jinak
Kdybys začínal znovu, co bys změnil v architektuře?
Co je "technický dluh" co tě nejvíc brzdí?

### L2. Co nerewritovat
Co z Pythonu funguje tak dobře, že to přepisovat nemá smysl?
(PDF parsing? Specific transforms? Specific prompts?)

### L3. Co přidat
Co v prototypu chybí a víš že to potřebuješ?
Prioritizované od "bez toho nemůžu" po "nice to have".

### L4. Scale obavy
Co se rozbije při přechodu z 239 na 500+ zdrojů?
Kde vidíš bottleneck? (LLM cost? Doba runu? Config maintenance?)

### L5. Matching requirements
Jak si představuješ matching?
Jaký je klientský profil? Jaká data o klientovi potřebuješ?
Jaká je definice "dobrý match"?