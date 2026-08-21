# Knowledge Summary — Extrakce z Python PoC

Shrnutí 67 odpovědí z knowledge-extraction. Vstup pro TypeScript rewrite.

---

## Čísla

- 356 YAML configs, 239+ zdrojů, 6,211 grantů, ~673 katalogů
- 16 GB output dat, 12K LLM cache entries (49 MB)
- 52 registrovaných transformací, 68 hint souborů, 37 custom skriptů
- Náklady: $2-5 per source (discovery+config+extraction), $35-270 full batch extraction
- 86% HTTP, 14% Playwright. 30% WordPress (vždy API, nikdy Playwright)

---

## A. Datový model

### Enums (zachovat)
- `ContentClassification` (9): grant_call, support_topic, ongoing_program, news_announcement, form_template, completed_project, event, blog_article, administrative
- `GrantLifecycleStage` (7 extended): announced, planned, closed, evaluated, unknown, support_topic, ongoing_project
- `CallType` (4): normal, continuous, competitive, other
- `FundingType` (6): dotace, stipendium, verejna_zakazka, dar, podpora, jine
- `ExtractionMethod` (10): css, xpath, regex, llm, static, listing, document, merged, api, script
- `OrganizationType` (19 + 16 aliasů): ministry, state, regional, municipal, foundation, university, eu, ngo...
- `ScrapingStrategy` (9 + 5 aliasů): html_catalog_html_grants, js_catalog_html_grants, api_only, single_page, crawl...
- `PaginationType` (16, zredukovat na 5): none, page_param, query_param, next_link, load_more

### Povinná pole
- **Hard required:** title, url (jen 2!)
- **Core scoring (60% váha):** title, description, provider, url
- **Important scoring (40% váha):** deadline, amount_max, eligibility
- **Všechno ostatní:** nescorované

### Quality score formule
```
base = core_completeness * 0.6 + important_completeness * 0.4
validation = date_score * 0.4 + amount_score * 0.4 + enum_score * 0.2
content = 0.9 + 0.1 * content_pass_rate
final = base * (0.9 + 0.1 * validation) * content
```

### Lifecycle thresholds
announced: 95, support_topic: 70, ongoing_project: 80, planned: 75, closed: 85, evaluated: 85, unknown: 90

### Skip fields per type (union lifecycle × classification)
- support_topic: deadline, deadline_start, amount_min, how_to_apply, subsidy_rate
- news_announcement: deadline, amount_max, amount_min, eligibility, how_to_apply, ideal_grantee
- (viz agents/E1 pro kompletní tabulku)

---

## B. Extraction Pipeline

### 6-level fallback architektura
1. **Step pipeline:** css → xpath → regex → transform → default (sequential, each on previous output)
2. **CSS/LLM cross-method:** CSS non-empty → keep, LLM for comparison. CSS empty → LLM replaces. `prefer_llm`/`prefer_docs` override
3. **HTML vs Documents:** Single LLM call, combined markdown input
4. **Script:** Custom Python, runs before HTML extraction
5. **Listing-to-Detail merge:** detail > listing, type coercion
6. **Catalog inheritance:** provider, contact, lifecycle from catalog metadata

### FieldExtraction provenance (zachovat!)
```typescript
interface FieldExtraction {
  value: any;
  selector?: string;
  method: ExtractionMethod;
  confidence: number;       // CSS/XPath/Regex = 1.0, LLM = 0.9
  llm_value?: any;          // blind second opinion
  llm_matches?: boolean;
  doc_value?: any;
  raw_text?: string;
  source_url?: string;
}
```

### 52 transformací (port do TS)
- **Kritické (12 česko-specifických):** parse_czech_date (36+ variant), parse_czech_amount (mil/mld/tis), extract_deadline (22 keywords), extract_funding_range, detect_currency
- **Text (18):** normalize_text, html_to_markdown, strip_html, extract_email, extract_phone...
- **API (28):** wp_date, json_array_first, source-specific URL builders
- **Všechny** registrované by-name, volané ze YAML configu

---

## C. Config Loop

### Tři módy
- `create` — z discovery JSON
- `improve` — z existujícího configu + worst samples + diagnostic signals
- `re-discover` — URL → discovery → create

### Improve signály
- Content mix warning (non-grant items expected to miss fields)
- LLM vs CSS mismatches (selektory pravděpodobně špatné)
- LLM-only fields (broken/missing selektory)
- Weakest fields (<50% completeness)
- Previous attempt summaries (neopakovat failed přístupy)

### Config validace (7 úrovní)
1. YAML parse
2. Structural (source, catalogs, detail sections)
3. Pydantic model (URL, enums, aliases)
4. Selector syntax (offline CSS/XPath validation)
5. Live selector test (fetch page, test selektory)
6. Discovery validation (strategy-specific required fields)
7. Content classification gate (block all-non-grant sources)

### Stagnation detection
- 3+ iterations within 0.1% tolerance = plateau
- Alternating up-down pattern over 4 iterations = oscillation
- 0 grants = always stagnation
- Regression > 5% = auto-rollback to best config

---

## D. Anti-fabrication (5 vrstev z PoC)

1. **Null > guess:** "Use null for fields you cannot find." Synthesize allowed ONLY for ideal_grantee, how_to_apply
2. **CSS vs LLM blind comparison:** LLM never sees CSS values. Mismatches flagged → selektory se opraví
3. **Content quality checks:** title < 10 chars, generic titles, description < 100 chars, HTML remnants, encoding artifacts, amount_min > amount_max, stale deadlines
4. **Ceiling checks:** amount > 50B CZK → NULL, date outside 2020-2032 → NULL
5. **Institution enrichment (nejpřísnější):** "NEVER invent or estimate." Per-field rules

### Karanténa triggers (jen 2!)
- Blocked content type (form_template, news, completed_project, event, blog_article)
- Missing title or url

---

## E. Infrastruktura

### Aktuální stav
- Vše běží lokálně na Mac M3, žádný Docker/cloud/cron
- LLM = 100% operational cost
- Models: Discovery/config = Sonnet, extraction = Haiku
- 4 paralelní workers, CONCURRENT_REQUESTS=1, DOWNLOAD_DELAY=2s

### Co nepřepisovat (zachovat jako Python microservice)
- **Document parsers:** Docling (ML, GPU) → PyMuPDF → pdfplumber → Unstructured. Docling nemá TS ekvivalent!
- **68 hint souborů** — format-agnostic text
- **SKILL.md prompty** — language-agnostic
- **356 YAML configs** — přebrat formát

### Co přepsat do TS
- Czech transforms (508 řádků, jen re + datetime, 40+ testů)
- Quality analyzer logika
- LLM prompts/schema
- Merge pipeline

### Scale bottlenecks při 500+ zdrojích
1. Run duration (serial) → in-process orchestration, browser reuse
2. Config maintenance (human) → automated health checks
3. LLM rate limits (AnthropicClient vrací None na RateLimitError — SILENT DATA LOSS!) → exponential backoff
4. Disk growth (no GC) → retention policy
5. Event log reads (O(n) per call) → indexed reads

---

## F. Czech specifika

- **Datumy:** 36+ variant (2 gramatické pády × 12 měsíců × s/bez diakritiky), `DD. MM. YYYY` s variabilním spacing
- **Částky:** `mil.` = M, `mld.` = B (NE americký billion!), tis. = K. Non-breaking spaces `\u00a0`
- **Email:** `(zavinac)` = `@` (česká konvence, několik variant)
- **PDF surrogáty:** 10-15% českých gov PDF má broken font encoding (U+D800-U+DFFF). 4 defense vrstvy
- **Lifecycle slovník:** Neexistuje standard. "Otevrena" (IROP) vs "Prijem zadosti probiha" (OPZP) vs "Schvalena dotace" (Praha) = vše "active"
- **22 deadline keywords:** uzaverka, nejpozdeji_do, termin_podani, konec_prijmu...

---

## G. Matching (už v produkci)

### Dva tier systém
- **Tier 1 (SQL):** text similarity na ideal_grantee (0-40), region overlap (0-25), target group overlap (0-25), deadline freshness (0-10). Max 100 bodů.
- **Tier 2 (LLM Haiku):** mission alignment (0-20), eligibility (yes=20/unknown=10/no=-30), geographic fit (0-20), capacity (0-20), strategic value (0-20). Max 100 bodů.
- **Thresholds:** High ≥ 70 (zelený), Medium ≥ 45 (žlutý), Low < 45 (šedý)
- **Klíčové pole pro matching:** `ideal_grantee` (nejdůležitější, LLM-syntetizované)

---

## H. Rewrite rozhodnutí z L1

1. **Direct Anthropic SDK** — žádné CLI subprocess wrappery
2. **Rozdělit god command** (2,592 řádků loop_create_config.py) na nezávislé moduly
3. **Framework-agnostic pipelines** — pure funkce, Scrapy je jen jeden entrypoint
4. **Jednodušší data model** — oddělit interní (provenance) od output (flat)
5. **Strict config validation** — žádné `extra="allow"`, redukovat pagination typy
6. **Single config path** — verze/stage metadata uvnitř configu
7. **PageFetcher abstrakce** — vrací (url, html, metadata) bez ohledu na httpx/Playwright
8. **In-process orchestrace** — asyncio místo subprocess spawn
