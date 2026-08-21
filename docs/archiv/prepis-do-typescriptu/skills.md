# Skills & Tools — SKILL.md pattern + MCP tools

## Princip

Dva typy "schopností" agentů:

1. **Skills (SKILL.md)** — znalostní soubory, instrukce, best practices.
   Agent je čte a řídí se jimi. Claude Code pattern.
2. **Tools** — akce, které agent volá. Standardní Agent SDK tools
   (Read, Write, Bash, WebFetch...) + custom tools.

---

## Skills (SKILL.md soubory)

```
.claude/skills/
├── grant-schemas/SKILL.md        # GrantOpportunity schema, povinná pole per typ
├── yaml-config/SKILL.md          # YAML config format, validace, best practices
├── czech-parsing/SKILL.md        # CZK, datumy, IČO, NUTS kódy, české formáty
├── extraction-pipeline/SKILL.md  # Multi-step extraction, confidence scoring
├── quality-scoring/SKILL.md      # Lifecycle-aware scoring, thresholds
└── anti-fabrication/SKILL.md     # Pravidla proti halucinaci
```

### grant-schemas
- Univerzální GrantOpportunity schema (všechna pole, typy, validace)
- Per-source-type field matrix (které pole kde čekat)
- Enumy: opportunity_type, status, lifecycle_stage, funding_type

### yaml-config
- YAML config format specification
- Template per strategy (html_catalog, js_catalog, api_catalog)
- Multi-step field extraction syntax (CSS → regex → transform → LLM)
- Validační pravidla pro YAML

### czech-parsing
- České datumy: "31. 3. 2026", "do 31. března", "31.3."
- Částky: "2 mil. Kč", "2 000 000 CZK", "2-50M", "max. 50 mil."
- IČO, ARES, NUTS kódy (CZ010, CZ020...)
- Právní formy: s.r.o., a.s., z.s., VŠ, obec...

### extraction-pipeline
- Hierarchie: deterministic first, LLM last
- CSS → regex → transform → LLM fallback
- Confidence scoring per krok
- Provenance tracking (odkud data pocházejí)

### quality-scoring
- Lifecycle-aware: aktivní výzva = 95%, archiv = 60%
- Per-field completeness scoring
- Anomaly detection pravidla
- Quarantine triggers

### anti-fabrication
- **Null > guess.** Chybějící pole = null, nikdy nevymýšlet.
- **Dual extraction.** CSS + LLM, porovnání výsledků.
  Shoda = vysoká confidence. Neshoda = flag + nižší score.
- **LLM agreement check.** Dva nezávislé LLM extrakce,
  porovnání. Při neshodě → null + warning.
- **Ceiling checks.** Částka > 50B? Deadline > +5 let? → karanténa.
- **Source attribution.** Každá hodnota musí mít zdroj (selector, URL).
  Hodnota bez zdroje = podezřelá.
- **Confidence thresholds.** Pod 0.6 → neukládat do produkce.

---

## Agent × Skill matrix

| Skill | sct-src | sct-cat | sct-opp | cfg-cat | cfg-opp | val-cat | val-opp | val-src | analyst |
|-------|:-------:|:-------:|:-------:|:-------:|:-------:|:-------:|:-------:|:-------:|:-------:|
| grant-schemas | ✓ | ✓ | ✓ | | ✓ | | ✓ | | ✓ |
| yaml-config | | | | ✓ | ✓ | | | | |
| czech-parsing | ✓ | | ✓ | ✓ | ✓ | | ✓ | | |
| extraction-pipeline | | | ✓ | | ✓ | | | | |
| quality-scoring | | | | | | ✓ | ✓ | ✓ | ✓ |
| anti-fabrication | | | | | ✓ | | ✓ | | |

Orchestrátor má vlastní **orchestration SKILL.md** (state machine, loop pravidla, gate podmínky).

Detailní zdůvodnění přiřazení viz `agents.md` sekce "Skills per agent".

---

## Tools per agent

### Orchestrátor tools

| Tool | Popis |
|------|-------|
| dispatch_agent | Spustí sub-agenta (type, input) → výstup |
| read_status / write_status | Čte/zapisuje sources/{slug}/status.json |
| read_run_log | Čte log sub-agenta (fallback monitoring) |
| read_run_output | Čte items.json, report.json |
| check_agent_status | Běží? Skončil? Failed? |
| tail_agent_log | Poslední N řádků logu (když selže stdout) |
| read_agent_stderr | Stderr sub-agenta (diagnostika) |
| run_config | Spustí scraper s konkrétní config_version |
| source_memory | Persistent knowledge per zdroj |
| hint_read / hint_write | Čte/píše hinty |
| gate_check | Kontrola gate podmínek |
| notify | Telegram notifikace |

### Sub-agent × Tool matrix

| Tool | sct-src | sct-cat | sct-opp | cfg-cat | cfg-opp | val-cat | val-opp | val-src | analyst | fixer* | dedup* |
|------|---------|---------|---------|---------|---------|---------|---------|---------|---------|--------|--------|
| **Browsing** | | | | | | | | | | | |
| WebFetch | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | | ✓ | |
| WebSearch | ✓ | | | | | | | | | | |
| **Scraping** | | | | | | | | | | | |
| scrapy_run | | | | ✓ | ✓ | | | | | ✓ | |
| cheerio_run | | | | ✓ | ✓ | | | | | ✓ | |
| playwright_run | | | | ✓ | ✓ | | | | | ✓ | |
| apify_run | | | | ✓ | ✓ | | | | | ✓ | |
| **Filesystem** | | | | | | | | | | | |
| Read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Write | | | | ✓ | ✓ | | | | | ✓ | |
| Edit | | | | ✓ | ✓ | | | | | ✓ | |
| Bash | | | | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| **Custom** | | | | | | | | | | | |
| source_memory | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| hint_read | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | |
| hint_write | | | | | | | | | ✓ | | |

*fixer a dedup = fáze 2

### Scraping tools (NOVÉ — chyběly!)

```typescript
// scrapy_run — Scrapy spider (Python, hlavní engine)
{
  name: "scrapy_run",
  description: "Spustí Scrapy spider s YAML configem",
  input: {
    config_path: string;        // cesta k YAML configu
    config_version?: string;    // "v1", "v2"...
    max_items?: number;         // limit (default: all)
    output_path?: string;       // kam uložit items.json
  },
  output: { items: Item[]; stats: ScrapyStats; }
}

// cheerio_run — Apify Cheerio Scraper (lightweight HTTP)
{
  name: "cheerio_run",
  description: "Spustí Cheerio scraper (HTTP-only, bez JS)",
  input: {
    urls: string[];
    selectors: Record<string, string>;
    config_version?: string;
  },
  output: { items: Item[]; stats: { requests: number; failed: number; } }
}

// playwright_run — Apify Playwright Scraper (pro JS-heavy weby)
{
  name: "playwright_run",
  description: "Spustí Playwright scraper (s browser rendering)",
  input: {
    urls: string[];
    selectors: Record<string, string>;
    wait_for?: string;          // CSS selector to wait for
    config_version?: string;
  },
  output: { items: Item[]; stats: { requests: number; failed: number; } }
}

// apify_run — Generic Apify Actor
{
  name: "apify_run",
  description: "Spustí Apify Actor (pro produkční scheduled runy)",
  input: {
    actor_id: string;
    input: Record<string, any>;
    config_version?: string;
  },
  output: { dataset_id: string; items_count: number; }
}
```

---

## Custom tools (Agent SDK)

### source_memory

Čtení/zápis persistent knowledge o zdroji. Backed by filesystem
(`sources/{slug}/memory/`).

```typescript
{
  name: "source_memory",
  description: "Čti/piš persistent knowledge o tomto zdroji",
  input_schema: {
    topic: "structure | failures | decisions",
    action: "read | append | replace",
    content: "string (for write)",
  },
  handler: async (input) => {
    // Read/write do sources/{slug}/memory/{topic}.md
  }
}
```

Agent na začátku každého runu automaticky čte memory.
Na konci updatuje decisions/failures.

### hint_read / hint_write

```typescript
{
  name: "hint_read",
  description: "Přečti hinty pro tento zdroj/katalog",
  input_schema: {
    level: "source | catalog | opportunity",
    catalog_name?: "string",
  },
  handler: async (input) => {
    // Čte sources/{slug}/hints.md (nebo hints/{catalog}.md)
  }
}
```

`hint_write` má jen analyst-source — ostatní agenti čtou, nepisou.

### run_config (orchestrátor tool)

Orchestrátor spouští scraper s konkrétní config verzí.

```typescript
{
  name: "run_config",
  description: "Spusť scraper s danou config verzí (full run nebo test)",
  input_schema: {
    source: "string",
    config_version: "string",          // "v1", "v2", "latest"
    mode: "test | full",               // test = max 5 items, full = all
    scraper: "scrapy | cheerio | playwright",  // auto-detect from config
  },
  handler: async (input) => {
    // Spustí příslušný scraper, vrátí výsledky
    // Loguje do runs/{run-id}/
  }
}
```

Poznámka: Config agenti (config-catalog, config-opportunity) volají
scraping tools přímo (scrapy_run, cheerio_run, playwright_run).
Orchestrátor volá run_config pro full production runy.

---

## Bezpečnostní pravidla

1. **Scout agenti nemají Write/Edit.** Jen pozorují, nemodifikují.
2. **Validator/analyst nemají Write.** Jen čtou a hodnotí.
3. **hint_write má jen analyst.** Ostatní čtou.
4. **source_memory je append-only** pro failures (agent nemůže smazat historii selhání).
5. **Bash je sandboxovaný** — žádný přístup mimo workspace.
6. **WebFetch respektuje robots.txt** a rate limiting.

---

## Poznatky z PoC — SKILL.md obsah

### grant-schemas SKILL.md musí obsahovat:

**Enums (kompletní seznamy z PoC):**
- ContentClassification (9): grant_call, support_topic, ongoing_program, news_announcement, form_template, completed_project, event, blog_article, administrative
- GrantLifecycleStage (7): announced, planned, closed, evaluated, unknown, support_topic, ongoing_project
- CallType (4): normal, continuous, competitive, other
- FundingType (6): dotace, stipendium, verejna_zakazka, dar, podpora, jine
- OrganizationType (19 + 16 aliasů)
- ScrapingStrategy (9 + 5 aliasů)

**Skip-field matice:** Content classification × lifecycle → union skipped fields.
(viz knowledge-summary.md sekce A)

**ContentClassification decision tree (ordered, use FIRST match):**
1. Has eligibility/deadline → grant_call
2. Support area without call → support_topic
3. Ongoing applications, no deadline → ongoing_program
4. Seminar/workshop → event
5. Forms/templates → form_template
6. Completed projects → completed_project
7. News → news_announcement
8. Blog → blog_article
9. GDPR/contacts → administrative

### czech-parsing SKILL.md musí obsahovat:

**52 transformací z PoC** (referenční seznam pro agenty):
- 12 česko-specifických: parse_czech_date, parse_czech_amount, extract_deadline (22 keywords), extract_funding_range, detect_currency, amount_min/max_from_range...
- 18 textových: normalize_text, html_to_markdown, strip_html, extract_email, extract_phone...
- 28 API/JSON: wp_date, json_array_first, source-specific URL builders
- Chaining: `transform: [normalize_text, extract_end_date]`

**České datumy (36+ variant):**
- 2 gramatické pády × 12 měsíců × s/bez diakritiky
- Formáty: `DD. MM. YYYY`, `DD.MM.YYYY`, `D. měsíce YYYY`, ISO, short (bez roku)
- Extra mezery z HTML: `<strong>30</strong> . dubna`

**České částky:**
- `mil.` = ×1M, `mld.` = ×1B (NE americký billion!), `tis.` = ×1K
- Non-breaking spaces `\u00a0`
- Decimal comma: `1.234,56` = 1234.56
- Sanity cap: 100B CZK (> reject)
- Kontroluj `mld` PŘED `mil` (prefix collision)

**Email:** `(zavinac)` = `@` (česká konvence)

### anti-fabrication SKILL.md:

**Z PoC — synthesize povoleno POUZE pro:**
- `ideal_grantee` (profil ideálního žadatele)
- `how_to_apply` (step-by-step guide)
- Všechno ostatní: null pokud nenalezeno

**CSS vs LLM blind comparison:**
- LLM NIKDY nevidí CSS hodnoty
- Interpretace: mismatch_fields = oprav selektory, llm_only > 0 = CSS broken, css_only > 0 = obvykle OK

### extraction-pipeline SKILL.md:

**6-level fallback (z PoC):**
1. Step pipeline (sequential): css → xpath → regex → transform → default
2. CSS/LLM (cross-method): CSS non-empty → keep + LLM comparison. CSS empty → LLM replaces
3. HTML vs Documents: combined markdown, single LLM call
4. Script: custom code, runs BEFORE HTML extraction
5. Listing-to-Detail merge: detail overrides listing
6. Catalog inheritance: provider, contact, lifecycle

**FieldConfig two syntaxes (zachovat!):**
- Legacy flat: selector, xpath, regex, transform, default, llm_prompt
- Steps pipeline: `steps[]` s typed kroky
