# Memory & Storage — Jak si systém pamatuje

## Princip

**CLI first = filesystem first.** V první fázi všechno na disku.
Agent SDK sessions pro replay. Postgres přijde se server fází.

Dva typy paměti:
1. **Workspace filesystem** — configs, scouts, runs, memory, hints
2. **Agent SDK sessions** — plné konverzace, resumable

---

## Workspace filesystem (source of truth)

```
sources/{slug}/
├── scouts/                         # Scout výstupy
│   ├── 2026-03-09_source.json      # ScoutSourceOutput
│   ├── 2026-03-09_catalog-vyzvy.json
│   └── 2026-03-09_opportunity-sample.json
├── configs/                        # YAML configs
│   ├── catalog.yml                 # Aktuální
│   ├── opportunity.yml
│   └── history/                    # Předchozí verze
│       ├── catalog.v1.yml
│       └── catalog.v2.yml
├── runs/                           # Agent run výstupy
│   └── {run-id}/
│       ├── items.json              # Nascrapevaná data
│       ├── report.json             # Validační/quality report
│       └── meta.json               # session_id, agent, cost, timestamp
├── memory/                         # Agent persistent knowledge
│   ├── structure.md                # Co agent ví o struktuře webu
│   ├── failures.md                 # Historie selhání (append-only!)
│   └── decisions.md                # Rozhodnutí a důvody
├── hints.md                        # Hinty (source-level + catalog-level)
└── status.json                     # State machine stav
```

### status.json

```json
{
  "source_id": "tacr-cz",
  "url": "https://www.tacr.cz",
  "phase": "BUILDING",
  "source_type": "search_based",
  "catalogs": [
    {
      "name": "Veřejné soutěže",
      "url": "https://www.tacr.cz/vyzvy",
      "strategy": "html_catalog",
      "config_version": "v2"
    }
  ],
  "attempts": { "scout-source": 1, "config-catalog": 2 },
  "quality": { "overall": 82, "catalogs": { "vyzvy": 85 } },
  "last_run": { "agent": "config-catalog", "run_id": "abc123", "timestamp": "..." },
  "created_at": "2026-03-09T10:00:00Z",
  "updated_at": "2026-03-09T14:30:00Z"
}
```

---

## Agent SDK Sessions

Každý agent run ukládá `session_id` do `runs/{run-id}/meta.json`.

**Resume:** Pokud run selhal uprostřed, orchestrátor může resumovat
session → Agent SDK pokračuje kde skončil.

**Replay:** Pro budoucí UI — Agent SDK API vrátí celou konverzaci
(messages) pro danou session. Zobrazení jako "chat" v UI.

```typescript
// meta.json
{
  "run_id": "abc123",
  "agent": "scout-source",
  "session_id": "sdk-session-xyz",  // Agent SDK session
  "started_at": "2026-03-09T14:00:00Z",
  "completed_at": "2026-03-09T14:00:14Z",
  "status": "completed",
  "confidence": 0.9,
  "cost": { "tokens": 12500, "usd": 0.03 },
  "summary": "Nalezeny 3 katalogy, typ: search_based"
}
```

---

## Memory model pro agenty

### Jak agent čte kontext

Agent na začátku runu dostane (přes PromptComposer L6):
1. `memory/structure.md` — co ví o webu
2. `memory/failures.md` — co selhalo a proč
3. `memory/decisions.md` — jaká rozhodnutí byla udělána
4. `hints.md` — lidské/analytik hinty

### Jak agent píše

Přes custom tool `source_memory`:
- `append` do failures.md (vždy append-only, nikdy mazat)
- `replace` do structure.md (aktualizace po novém scouting)
- `append` do decisions.md (nová rozhodnutí s důvody)

### Příklad memory/decisions.md

```markdown
## 2026-03-09 scout-source (run abc123)
- Typ zdroje: search_based (TAČR nemá listing, jen vyhledávací formulář)
- 3 katalogy nalezeny přes navigaci, ne přes listing page

## 2026-03-09 config-catalog attempt 1 (run def456)
- CSS paginace selhala po str. 50 → přepnuto na API fallback
- Důvod: TAČR vrací 404 pro stránky >50, ale API endpoint funguje

## 2026-03-09 config-catalog attempt 2 (run ghi789)
- Deadline selector změněn z .deadline na .info-date (web redesign)
- cofin intentionally skipped — data v PDF příloze (viz hint)
```

---

## Cross-source learning

Orchestrátor může najít podobné zdroje na základě:
- `source_type` (stejný CMS, stejná strategie)
- Tag matching ("ministerstvo", "nadace", "eu_fond")

Při scout/build nového zdroje → orchestrátor načte memory z podobných
zdrojů → přidá do kontextu (L6 vrstva v promptu).

```bash
# V praxi
grantio add https://www.mzp.cz
# Orchestrátor: "mzp.cz je ministerstvo, podobné jako tacr.cz"
# → načte memory z tacr-cz → přidá jako kontext pro scout
```

---

## Hints

```markdown
<!-- sources/tacr-cz/hints.md -->

## Source-level
- [unresolved] Martin, 2026-03-08: Nová sekce 'Mimořádné výzvy' se nesbírá
- [resolved by run ghi789] Pavel, 2026-03-06: Paginace broken po str.50, fallback na API

## Catalog: Veřejné soutěže
- [unresolved] Pavel, 2026-03-09: Spolufinancování je v PDF příloze, ne na webu
```

Analyst agent může psát nové hinty. Fixer agent (fáze 2) je může markovat
jako resolved.

---

## Retence dat

| Typ dat | Retence | Důvod |
|---------|---------|-------|
| status.json | Vždy | State machine |
| configs/ (aktuální) | Vždy | Produkční reference |
| configs/history/ | 90 dní | Debug, rollback |
| scouts/ | 30 dní | Většinou stačí latest |
| runs/ (items, reports) | 30 dní | Po schválení nepotřeba |
| runs/ (meta.json) | Vždy | Audit trail |
| memory/ | Vždy | Akumulace znalostí |
| hints.md | Vždy | Kolaborace |

---

## Evoluce: Filesystem → Postgres

Až přijde server fáze:

```
Filesystem (fáze 1)              Postgres (fáze 2+)
────────────────────────────    ────────────────────────────
status.json              →      sources tabulka
runs/{id}/meta.json      →      runs tabulka
hints.md                 →      hints tabulka
memory/*.md              →      source_memory tabulka
scouts/*.json            →      zůstane na disku (velké)
configs/*.yml            →      configs tabulka + git
runs/{id}/items.json     →      zůstane na disku (velké)
```

Klíč: **Metadata do DB, velká data na disku.** Queryable stav +
neomezený storage.

---

## Poznatky z PoC — 8 memory vrstev (aktuální stav)

PoC má 8 memory mechanismů, většina nefunguje dobře:

| # | Vrstva | Stav | Akce pro rewrite |
|---|--------|------|------------------|
| 1 | Event log (events.jsonl) | ✅ Funguje | Zachovat pattern (append-only JSONL) |
| 2 | History formatter | ❌ DEAD CODE | Implementovat v L5/L6 prompt vrstvě |
| 3 | Config creation log | ✅ Funguje | Zachovat (attempt tracking) |
| 4 | Source hints (68 files) | ✅ Funguje | Zachovat formát, přidat resolution tracking |
| 5 | Quality reports | ✅ Funguje | Zachovat + propojit s improve mode |
| 6 | Config diff | ⚠️ Loguje, nepropaguje | Propojit do agent kontextu |
| 7 | Stagnation detection | ✅ Funguje | Zachovat logiku |
| 8 | Signal files (DONE.md) | ✅ Funguje | Nahradit status.json |

### Klíčové gapy v PoC memory (řešíme v rewrite)
- **Žádné cross-source learning** — každý WordPress zdroj nezávisle objevuje REST API pattern
- **Žádná failure pattern agregace** — opakující se chyby se nekorelují
- **Hints write-once** — nikdy se neaktualizují, 16 KB truncation (může odříznout nejnovější info)
- **Žádné temporal awareness** — systém neví kdy se web změnil
- **History formatter je dead code** — `format_history_for_prompt()` existuje, nikdy se nevolá

### Hint kategorie (z PoC, seřazeny dle dopadu)
1. **Encyclopedia (10+ KB):** Full DOM snippets, selector tables, quality history. Nejvyšší dopad (Praha, OPZP, IROP)
2. **Gotcha warnings:** Kritická operational knowledge (MPSV Playwright, MK annual URL suffix)
3. **Non-grant warnings:** Quality ceiling documentation (Dobry andel 73.3%, Nevypust dusi 61%)
4. **Failed/incomplete:** Zero-quality zdroje s dokumentací struktury

### Caching (3 vrstvy z PoC — zachovat!)
1. **Raw files cache** (`raw_cache/`) — SHA256 content-addressed, 7.7 GB. IROP: 80+ grantů sdílí application forms
2. **Document parsing cache** (`document_cache/`) — cached markdown by file hash, 150 MB. Docling = 5-30s per PDF
3. **LLM cache** — content-addressed (SHA256 of markdown[:30K] + schema). 12K entries, 49 MB. Redukuje re-run cost ~90%
