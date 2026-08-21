# UI Architecture — Workspace Pattern (fáze 3)

> CLI first. Tento dokument je vize pro budoucí UI. Implementace až ve fázi 3.

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

Tři úrovně workspace, každá se **stejným vzorem**:
**overview + runs + hints + quality + config**

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

Breadcrumbs:
```
Dashboard > Sources > tacr-cz > Veřejné soutěže > SIGMA – Průmyslový výzkum
                      (source)   (catalog)          (opportunity)
```

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
│ Config version: v2 (3d ago)                              │
│ Memory: 3 topics (structure, failures, decisions)        │
│ Hints: 2 unresolved                                      │
│                                                          │
│ ═══ Catalogs ════════════════════════════════════════════│
│                                                          │
│ ┌───────────────────────────────────────────────────┐   │
│ │ Veřejné soutěže         32 grants  85%  🟢      │   │
│ │ Programy                12 grants  78%  🟢      │   │
│ │ Archiv                   3 grants  65%  🟡      │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ ═══ Recent Runs ═════════════════════════════════════════│
│                                                          │
│ ┌──────────────────────────────────────────────────┐    │
│ │ #47 scout     2h ago    ✅ 14s   $0.03         │    │
│ │ #46 build     1d ago    ✅ 2m    $0.12  +3 new │    │
│ │ #45 validate  1d ago    ✅ 8s    $0.01         │    │
│ │ #44 fix       3d ago    ✅ 45s   $0.08  v1→v2  │    │
│ └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Run Detail (session replay)

```
┌─────────────────────────────────────────────────────────┐
│ ← tacr-cz    Run #44: fixer-catalog    ✅ completed     │
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
│ │    Previous: CSS pagination → failed >50           │   │
│ │                                                    │   │
│ │ 🔧 Generating new config v2...                     │   │
│ │    - Changed: pagination → api_fallback            │   │
│ │    - Changed: deadline → ".info-date"              │   │
│ │    - Unchanged: cofin (hint says "in PDF")         │   │
│ │                                                    │   │
│ │ 🧪 Testing on 5 samples...                        │   │
│ │    ✅ 5/5 title    ✅ 5/5 deadline (was 0/5)      │   │
│ │    ✅ pagination: 52 URLs (was 50 max)             │   │
│ │                                                    │   │
│ │ ✅ Config v2 committed. Quality: 72% → 85%.        │   │
│ └───────────────────────────────────────────────────┘   │
│                                                          │
│ Config diff: [View v1 → v2 diff]                        │
│ Quality delta: +13% completeness, +8% quality            │
│ Resolved hints: 1                                        │
└─────────────────────────────────────────────────────────┘
```

Data pro run detail: Agent SDK session replay API.

### Opportunity Detail

```
┌─────────────────────────────────────────────────────────┐
│ ← Veřejné soutěže    SIGMA – Průmyslový výzkum         │
│                                                          │
│ Field              Value                  Source   Conf  │
│ ─────────────────────────────────────────────────────── │
│ title              SIGMA – Průmyslový...  css      0.99 │
│ description        Program podporuje...   css+llm  0.95 │
│ provider           TAČR                   css      0.99 │
│ funding.min        2,000,000 CZK          css      0.90 │
│ funding.max        50,000,000 CZK         css      0.90 │
│ funding.cofin      —                      missing  —    │
│ dates.deadline     2026-03-31             regex    0.95 │
│ eligibility.types  [s.r.o., a.s., VŠ]    llm      0.80 │
│                                                          │
│ Quality: 88%  |  Lifecycle: announced  |  14/16 fields  │
│                                                          │
│ Attachments:                                             │
│ 📄 Zadávací dokumentace.pdf     [parsed ✅]              │
│ 📄 Příloha 1 – Rozpočet.xlsx   [not parsed]             │
│                                                          │
│ Dedup: Cluster #127 (also at dotaceeu.cz, 91% match)   │
└─────────────────────────────────────────────────────────┘
```

---

## Workspace komponenta (vzor)

Všechny tři úrovně sdílejí stejný UI pattern:

```typescript
interface WorkspaceProps {
  entity: Source | Catalog | Opportunity;
  level: "source" | "catalog" | "opportunity";

  // Společné tabs (všechny úrovně)
  tabs: {
    overview:  true;       // vždy
    runs:      true;       // vždy (session replay)
    hints:     true;       // vždy
    quality:   true;       // vždy
    config:    boolean;    // source: meta, catalog: YAML, opportunity: ne
  };

  // Level-specific
  children?: {
    source:      "catalogs tab";
    catalog:     "opportunities tab";
    opportunity: "provenance tab, attachments tab, dedup tab";
  };
}
```

---

## Tech stack (budoucí)

```
Frontend:  SvelteKit (existující app na grantio.cz, rozšíření)
Realtime:  WebSocket pro run streaming (agent messages live)
Styling:   Tailwind + shadcn/svelte
Tables:    TanStack Table
Charts:    Chart.js
YAML:      CodeMirror (syntax highlighting)
Data:      Agent SDK session replay API + Postgres
```
