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