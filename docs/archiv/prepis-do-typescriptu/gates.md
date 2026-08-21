# Gates — Quality Gates & Approval Flow

## Princip

Gate = checkpoint, kde se orchestrátor zastaví a buď automaticky
schválí (dev), nebo čeká na lidské schválení (production).

**Default: gate před produkcí.** Vše ostatní běží automaticky.

---

## Gate Types

### 1. Production Gate (povinný)

**Kdy:** Před zápisem dat do produkční DB / deploy configu.
**Kdo schvaluje:** Člověk (Telegram notifikace + CLI potvrzení).
**Co se kontroluje:**

```typescript
interface ProductionGateCheck {
  // Automatické kontroly (musí projít všechny)
  auto: {
    min_items: number;           // alespoň N položek
    field_coverage: number;      // % vyplněných povinných polí > threshold
    no_validation_errors: boolean;
    test_run_passed: boolean;
    analyst_verdict: "approve";  // analyst-source musí schválit
    fabrication_check_passed: boolean; // anti-halucinace
  };
  // Prezentováno člověku k rozhodnutí
  human_review: {
    sample_items: Item[];        // 3-5 vzorových položek
    quality_score: number;
    analyst_report: string;
    diff_vs_previous: string;    // co se změnilo od posledního runu
  };
}
```

**Akce po schválení:** Deploy config, aktivace scheduleru.
**Akce po zamítnutí:** Zpět k orchestrátoru s feedbackem → retry / abandon.

---

### 2. Destructive Gate (povinný)

**Kdy:** Agent chce přepsat/smazat existující produkční data.
**Kdo schvaluje:** Člověk.
**Příklady:**
- Přepis konfigurace, která už produkčně běží
- Smazání zdroje z produkce
- Bulk update existujících grantů (merge/dedup)

---

### 3. Cost Gate (automatický s eskalací)

**Kdy:** Běh agenta překročí cost threshold.
**Default:** Auto-stop po konfigurovaném limitu.
**Eskalace:** Telegram alert + čeká na potvrzení.

```typescript
interface CostGate {
  max_tokens_per_run: number;     // default: 100k
  max_cost_per_run_usd: number;   // default: $2
  max_retries_per_task: number;   // default: 3
  action_on_exceed: "pause" | "abort" | "escalate";
}
```

---

### 4. Confidence Gate (automatický)

**Kdy:** Agent vrátí confidence < threshold.

```typescript
interface ConfidenceGate {
  thresholds: {
    proceed: 0.8;     // > 0.8 → pokračuj automaticky
    retry: 0.6;       // 0.6-0.8 → retry s upraveným promptem
    escalate: 0.3;    // 0.3-0.6 → eskaluj člověku
    abort: 0.0;       // < 0.3 → zastav
  };
}
```

---

### 5. Attempt Gate (automatický)

**Kdy:** Agent selhal N-krát na stejném úkolu.
**Default:** Po 3 selháních → eskaluj člověku.
**Kontext:** Předchozí chyby + co se zkoušelo → člověk rozhodne.

---

## Gate Flow v orchestrátoru

```
scout-source
  → [Confidence Gate]
scout-catalog(s) (parallel)
  → [Confidence Gate]
scout-opportunity (sample)
  → [Confidence Gate]
config-catalog + config-opportunity
  → [Confidence Gate] + [Attempt Gate]
  → test run + validation
validator-catalog
  → quality scoring
analyst-source (gate-keeper)
  → [Analyst verdict: approve/needs_work/reject]
  → [Cost Gate]
★ PRODUCTION GATE ★ (lidské schválení)
  → Deploy to production
```

---

## Fabrication Detection (součást gates)

V rámci validator-catalog a analyst-source se kontroluje:

1. **Dual extraction agreement:** CSS extrakce vs LLM extrakce.
   Pokud se liší → flag, snížení confidence.
2. **Null > guess:** Agent nesmí vymýšlet data. Chybějící pole = null,
   ne "pravděpodobně XY".
3. **Provenance tracking:** Každé pole má zdroj (css, regex, llm, attribute).
   Pole bez provenance = podezřelé.
4. **Ceiling checks:** Částka > 50B CZK? Deadline v roce 2090? → karanténa.

Viz `anti-fabrication.md` v sekci Skills.

---

## Per-source gate override

```yaml
# Důvěryhodný zdroj — mírnější gates
source_id: dotace_eu
gates:
  confidence_threshold: 0.5
  max_retries: 5
  auto_approve_production: false  # nikdy auto-approve produkci

# Nový neznámý zdroj — přísnější
source_id: unknown_nadace
gates:
  confidence_threshold: 0.9
  max_retries: 2
  require_human_review_always: true
```

---

## Eskalační kanály

| Priorita | Kanál | Příklad |
|-----------|-------|---------|
| INFO | Log (filesystem) | "Scout dokončen, confidence 0.85" |
| WARNING | Telegram (dev channel) | "Builder selhal 2x, zkouším alternativu" |
| ACTION_REQUIRED | Telegram (direct) + CLI prompt | "Production gate čeká na schválení" |
| CRITICAL | Telegram (direct) | "Cost gate exceeded, runy zastaveny" |

---

## Metriky gates

Každý gate loguje:

```typescript
interface GateLog {
  gate_type: GateType;
  source_id: string;
  run_id: string;
  timestamp: Date;
  decision: "pass" | "fail" | "escalate" | "override";
  decided_by: "auto" | "human";
  context: Record<string, any>;
  duration_ms: number;           // jak dlouho gate trval (čekání na člověka)
}
```

Cíl: >80% runů projde bez lidského zásahu.

---

## Poznatky z PoC — konkrétní pravidla

### Validační pravidla (kompletní z PoC)

**Level 1 — Scraping time:**
- UTF-8 surrogate sanitization (U+D800-U+DFFF → U+FFFD). 10-15% českých gov PDF!
- HTML tag stripping na všech string polích (mimo url, website)
- Type coercion: datumy via dateutil s `dayfirst=True`
- Required defaults: title="Untitled", url=""

**Level 2 — Quality analysis (non-blocking):**
- Date parseable (40% validation weight)
- Amount non-negative (40% weight)
- Enum in allowed set (20% weight)
- Content checks: title < 10 chars, generic titles ("granty", "dotace", "novinky", "aktuality", "hlavni stranka"), description < 100 chars, HTML remnants, encoding artifacts, amount_min > amount_max, stale deadline

**Level 3 — Sync cleaning:**
- Blocked types (QUARANTINE): form_template, news_announcement, completed_project, event, blog_article
- Amount ceiling: > 50B CZK → NULL
- Date range: outside 2020-01-01 to 2032-12-31 → NULL
- String length caps: lifecycle_stage:30, provider:200, category:100, focus_area:200...
- Missing title or url → QUARANTINE

**Level 4 — Sync quality gates:**
- `required_null_threshold: 5.0%` (max NULL title/url rate)
- `max_quarantine_percent: 20.0%`
- `max_unknown_taxonomy_percent: 30.0%`
- `min_grants_count: 1`

### Stagnation detection (z PoC)
- 3+ iterations within 0.1% tolerance = plateau
- Alternating up-down over 4 iterations = oscillation
- Quality regression > 5% = auto-rollback to best config
- 0 grants = always stagnation
- `--allow-regression` flag pro precision fixes

### Karanténa (z PoC)
- **Jen 2 triggers:** blocked content type NEBO missing title/url
- **Žádný retry/release.** Fix config → re-scrape → re-sync je jediná cesta zpět
- Non-quarantine corrections pass through: HTML strip, amount cap, date cap, string length
