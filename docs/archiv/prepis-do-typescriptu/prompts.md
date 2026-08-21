# Prompts — Verzovaný composition systém

## Princip

Prompty jsou **verzované, skládané, a kontextově závislé**.
Ne jeden monolitický prompt, ale kompozice vrstev.

Prompty žijí jako **markdown soubory v gitu**. Agent dostane
složený prompt z relevantních vrstev.

---

## Architektura promptů — 7 vrstev

```
┌─────────────────────────────────────────────┐
│ Layer 0: System prompt (agent identity)      │  "Jsi scout-source agent..."
├─────────────────────────────────────────────┤
│ Layer 1: Task prompt (co dělej)              │  "Prozkoumej tento web..."
├─────────────────────────────────────────────┤
│ Layer 2: Domain knowledge                    │  "České granty mají..."
├─────────────────────────────────────────────┤
│ Layer 3: Source type context                 │  "WordPress listing vypadá..."
├─────────────────────────────────────────────┤
│ Layer 4: Hints (manuální/od analytika)       │  "Tento web má SPA..."
├─────────────────────────────────────────────┤
│ Layer 5: Attempt context                     │  "Předchozí pokus selhal na..."
├─────────────────────────────────────────────┤
│ Layer 6: Memory (naučené z historie)         │  "U tohoto zdroje funguje..."
└─────────────────────────────────────────────┘
```

### Kdy se která vrstva aktivuje

| Vrstva | Vždy | Podmíněně |
|--------|------|-----------|
| L0 System | ✓ | |
| L1 Task | ✓ | |
| L2 Domain | ✓ | |
| L3 Source type | | Pokud známe typ (po scout-source) |
| L4 Hints | | Pokud existují hinty (`hints.length > 0`) |
| L5 Attempt | | Pokud `attempt > 1` |
| L6 Memory | | Pokud existuje historie pro tento zdroj |

---

## Soubory promptů

```
prompts/
├── system/                         # L0: Agent identity
│   ├── scout-source.md
│   ├── scout-catalog.md
│   ├── scout-opportunity.md
│   ├── config-catalog.md
│   ├── config-opportunity.md
│   ├── validator-source.md
│   ├── validator-catalog.md
│   ├── analyst-source.md
│   ├── fixer-catalog.md            # fáze 2
│   ├── fixer-opportunity.md        # fáze 2
│   └── dedup-opportunity.md        # fáze 2
│
├── tasks/                          # L1: Konkrétní úkol
│   ├── scout_source.md             # "Prozkoumej zdrojový web"
│   ├── scout_catalog.md            # "Zmapuj katalog"
│   ├── scout_opportunity.md        # "Zmapuj detail výzvy"
│   ├── build_catalog_config.md     # "Vygeneruj YAML pro katalog"
│   ├── build_opportunity_config.md # "Vygeneruj YAML pro detail"
│   ├── validate_catalog.md         # "Zkontroluj kvalitu dat"
│   ├── validate_source.md          # "Agreguj kvalitu across katalogů"
│   ├── review_quality.md           # "Posud kvalitu dat pro produkci"
│   └── suggest_hints.md            # "Navrhni hinty pro zdroj"
│
├── domain/                         # L2: Doménová znalost
│   ├── czech_grants.md             # CZ granty, ministerstva, EU fondy
│   ├── eu_grants.md                # EU fondy specifika
│   ├── field_definitions.md        # Co znamená deadline, eligibility...
│   └── quality_standards.md        # Co je "kvalitní" grant záznam
│
├── source_types/                   # L3: Typ zdroje
│   ├── html_listing.md             # Statický HTML katalog
│   ├── spa_dynamic.md              # SPA / JavaScript-rendered
│   ├── pdf_portal.md               # PDF dokumenty ke stažení
│   ├── api_endpoint.md             # REST/GraphQL API
│   ├── search_based.md             # Vyhledávací formulář
│   └── cms_patterns.md             # WordPress, Drupal, custom CMS
│
├── templates/                      # L5, L6: Dynamické šablony
│   ├── attempt_retry.md            # "Předchozí pokus selhal na..."
│   └── memory_summary.md           # "Historie: co se naučilo..."
│
└── evals/                          # Testování promptů
    ├── scout_source/
    │   ├── wordpress_listing.json
    │   ├── spa_dynamic.json
    │   └── pdf_portal.json
    └── config_catalog/
        ├── simple_html.json
        └── paginated_api.json
```

---

## Prompt Composition Engine

```typescript
interface PromptComposer {
  compose(params: {
    agent: AgentType;             // scout-source, config-catalog...
    project: ProjectContext;
    attempt: number;
  }): string;
}

function compose({ agent, project, attempt }: ComposeParams): string {
  const parts: string[] = [];

  // L0: Vždy
  parts.push(loadPrompt(`system/${agent}.md`));

  // L1: Vždy
  parts.push(loadPrompt(`tasks/${agentToTask(agent)}.md`));

  // L2: Vždy
  parts.push(loadPrompt("domain/czech_grants.md"));
  parts.push(loadPrompt("domain/field_definitions.md"));

  // L3: Podmíněně — pokud známe typ zdroje
  if (project.source_type) {
    const typeFile = sourceTypeToFile(project.source_type);
    if (exists(`source_types/${typeFile}`)) {
      parts.push(loadPrompt(`source_types/${typeFile}`));
    }
  }

  // L4: Podmíněně — pokud existují hinty
  if (project.hints.length > 0) {
    parts.push(`\n## Hinty\n${project.hints.map(h => `- ${h.content}`).join("\n")}`);
  }

  // L5: Podmíněně — pokud retry
  if (attempt > 1) {
    const prev = project.runs[project.runs.length - 1];
    parts.push(renderTemplate("templates/attempt_retry.md", {
      attempt,
      previous_errors: prev.errors,
      previous_output: prev.summary,
      analyst_feedback: prev.analyst_feedback,
    }));
  }

  // L6: Podmíněně — pokud existuje memory
  if (project.memory.length > 0) {
    parts.push(renderTemplate("templates/memory_summary.md", {
      entries: project.memory,
    }));
  }

  return parts.join("\n\n---\n\n");
}
```

---

## Verzování

Prompty žijí v **gitu** jako markdown soubory.

| Proč git | Proč ne DB | Proč ne inline v kódu |
|----------|------------|----------------------|
| Diff, blame, history zdarma | Lokální vývoj bez DB | Prompty se mění častěji než kód |
| Review přes PR | | Non-programátor může editovat |
| Rollback = git revert | | Testování nezávisle na kódu |

---

## Testování promptů (Evals)

Každý prompt má eval sadu — sada vstupů s očekávanými výstupy:

```json
// evals/scout_source/wordpress_listing.json
{
  "input": {
    "url": "https://example.com/grants",
    "html_snapshot": "...",
  },
  "expected": {
    "source_type": "static",
    "catalogs_count_min": 1,
    "confidence_min": 0.7,
    "must_detect": ["listing_selector", "pagination"]
  }
}
```

Eval run: spusť agenta s eval vstupem, porovnej výstup s expected.
Metriky: field coverage, confidence, false positives.

---

## Poznatky z PoC — jak prompty fungují dnes

### System prompt assembly (aktuální PoC)
```
SKILL.md
+ shared/extraction.md
+ shared/taxonomy.md
+ shared/output-format.md
+ dynamic context (enum values from items.py + field_definitions.yml + strategy_requirements.yml)
+ per-source hints (16 KB max, truncated)
```
→ Mapuje se na naše L0 + L1 + L2 + L3 + L4 vrstvy.

### Co PoC NEMÁ (a my přidáváme)
- **L5 (attempt context):** PoC má `config_creation_log.json` s attempt číslem + previous decisions, ale NENÍ propojeno s prompt systémem. History formatter je DEAD CODE.
- **L6 (memory):** PoC má `events.jsonl` s `get_history_summary()`, ale format_history_for_prompt() se NIKDY nevolá.
- **Cross-source learning:** Neexistuje v PoC.

### Improve mode (L5 ekvivalent — zachovat!)
Config agenti v improve mode dostávají:
- Aktuální config
- 5 worst samples (title, url, quality_score, missing_fields, content_classification)
- Diagnostic signals:
  - Content mix warning (non-grant items → expected missing fields)
  - LLM vs CSS mismatches (selektory pravděpodobně špatné)
  - LLM-only fields (CSS broken ale data existují)
  - Weakest fields (<50% completeness)
  - Previous attempt summaries (neopakovat failed přístupy)

### Anti-fabrication v promptech (zachovat!)
- Discovery: "Never report catalog without verifying listing selector finds >0 items"
- Config: "Never invent selectors without checking actual HTML"
- Extraction: "Use null for fields you cannot find." Synthesize ONLY ideal_grantee + how_to_apply
- Institution enrichment (nejpřísnější): "NEVER invent or estimate data"

### LLM extraction prompt — single call per grant
Vstup: combined markdown (`# Detail stranky\n\n{html_md}\n\n---\n\n# Prilohy a dokumenty\n\n{doc_md}`)
Výstup: JSON se všemi poli najednou
Document size limit: 30K chars (retry 15K na timeout)
Per-source override: `llm_prompt` field v YAML config

### Hint format (68 souborů v PoC)
Standard template:
- Source info (ID, name, type, URL)
- Quality history (best run, score, grants count)
- Catalog page (URL, CMS type, pagination, Playwright requirements)
- Verified selectors (table: field / selector / transform / notes)
- Detail pages (HTML structure with DOM snippets)
- Fields NOT available in HTML
- Important Notes (operational knowledge)

Truncated at 16 KB. Write-once lifecycle (generated once, never auto-updated).
Biggest impact: "encyclopedia" hints (10+ KB, full DOM snippets — Praha, OPZP, IROP).
