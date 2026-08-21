# Anti-Fabrication — Pravidla proti halucinaci

## Proč je to kritické

LLM agenti extrahují data z webů. Riziko: agent "vymyslí" data která
na stránce nejsou. U grantových dat je to fatální — špatný deadline,
špatná částka, špatná eligibility = klient podá žádost špatně nebo ji vůbec nepodá.

**Princip: Null > guess. Chybějící pole je lepší než vymyšlené pole.**

---

## 5 obranných vrstev

### 1. Dual Extraction (CSS + LLM)

Každé pole se extrahuje dvakrát:
- **CSS path:** Deterministický selektor → přesná hodnota
- **LLM:** Volná extrakce z HTML kontextu

Porovnání:
- **Shoda** → confidence 0.95+
- **Částečná shoda** (formát se liší, hodnota stejná) → confidence 0.85
- **Neshoda** → flag, confidence 0.5, lidský review
- **CSS najde, LLM ne** → confidence 0.8 (CSS je pravda)
- **LLM najde, CSS ne** → confidence 0.6 (podezřelé, možná halucinace)

### 2. LLM Agreement Check

Pro kritická pole (deadline, funding amount, eligibility):
- Dva nezávislé LLM cally se stejným HTML ale jiným promptem
- Shoda → OK
- Neshoda → null + warning

```yaml
# V YAML configu
deadline:
  selector: ".deadline-text"
  steps:
    - method: css
    - method: llm
      prompt: "Extrahuj datum uzávěrky"
    - method: llm_verify
      prompt: "Ověř, že tento deadline je správný: {previous_value}"
  agreement_required: true
```

### 3. Null > Guess (prompt instrukce)

V každém agent promptu (L0 vrstva):

```markdown
## Kritické pravidlo: NIKDY nevymýšlej data

- Pokud pole na stránce NENÍ → vrať null
- Pokud si NEJSI JISTÝ → vrať null + nízká confidence
- NIKDY neodhaduj deadline z kontextu ("asi do konce roku")
- NIKDY neodhaduj částku ("pravděpodobně miliony")
- NIKDY neodhaduj eligibility ("typicky pro obce")
- Chybějící pole s null je VŽDY lepší než vymyšlené pole
- Pokud najdeš pole jen v příloze (PDF), zapiš "v příloze" jako zdroj, ne hodnotu
```

### 4. Ceiling & Sanity Checks

Deterministické kontroly v validátoru:

```typescript
const SANITY_CHECKS = {
  // Finanční
  "funding.max > 50_000_000_000": "karanténa",     // >50B CZK
  "funding.min > funding.max": "karanténa",
  "funding.min < 0": "karanténa",
  "funding.cofinancing > 100": "karanténa",         // >100%

  // Datumové
  "deadline < today - 365": "warning",               // Starší než rok
  "deadline > today + 1825": "karanténa",            // Za víc než 5 let
  "start_date > deadline": "karanténa",

  // Textové
  "title.length > 500": "warning",
  "description.length < 10": "warning",
  "title contains HTML tags": "karanténa",
};
```

### 5. Provenance Tracking

Každé extrahované pole má metadata:

```typescript
interface FieldProvenance {
  value: any;
  source: "css" | "regex" | "llm" | "transform" | "attribute" | "pdf";
  confidence: number;
  selector?: string;           // CSS selektor (pokud CSS)
  raw_text?: string;           // původní text před transformací
  extraction_step: number;     // kolikátý krok v pipeline
  verified_by?: "llm_agreement" | "dual_extraction" | "manual";
}
```

Pole bez provenance = podezřelé → nízká confidence → review.

---

## Karanténa

Data se **nikdy nezahazují**. Podezřelé záznamy jdou do karantény:

```typescript
interface QuarantineEntry {
  item: GrantItem;
  reason: string;              // "funding.max > ceiling"
  detected_by: string;         // "sanity_check" | "fabrication_check"
  detected_at: Date;
  resolved: boolean;
  resolution?: "approved" | "fixed" | "deleted";
}
```

V UI: karanténa sekce v Quality tabu. Člověk může:
- Schválit (false positive)
- Opravit (manuální edit)
- Smazat (skutečná halucinace)

---

## Metriky

| Metrika | Cíl | Měření |
|---------|-----|--------|
| Fabrication rate | <1% | Manuální audit sample per source |
| Dual extraction agreement | >90% | Automatické — CSS vs LLM shoda |
| Null rate (kritická pole) | <20% | Automatické — % null v deadline, funding |
| Karanténa rate | <5% | Automatické — % záznamů v karanténě |
| False karanténa | <10% | Manuální — kolik karanténních je OK |
