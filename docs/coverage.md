# Coverage & active learning — jak VĚDĚT, že pokrýváme formulace polí (a na co pozor)

Řeší napětí: nepřemíňovat (ruční slovník synonym = nora) vs nepodcenit (neznáme všechny formulace).
**Pokrytí se MĚŘÍ, nehádá.** Self-terminating (stop na saturaci).

## Cyklus (měřený, ne nekonečný)
1. **Najdi nejodlišnější zdroje** — `scripts/diversity_finder.py` skenuje korpus na doménové markery
   (věda/výzkum, půjčky/fin.nástroje, de-minimis, rolling, voucher; EU/SK mimo scope) → nejodlišnější
   DOSUD NEVZORKOVANÉ zdroje. Cílit divergentní >> náhodné.
2. **Vytěž formulace + záludnosti** — `scripts/type_coverage_wf.js` (dvouvrstvě: typ + per-typ pole).
   Sonnet čte stratifikovaný vzorek reálných dokumentů, hlásí (a) formulace jak viděl pole/typ,
   (b) confusably. Orchestrátor měří **saturační křivku** (distinct kumulativně po dávkách).
3. **Diff proti minulému** — kolik NOVÝCH formulací/záludností přibylo = informační zisk.
4. **Stop, až zisk klesne** (saturace). Nové záludnosti → `prompts/pitfalls.md`.

## Co se naměřilo (2026-06-01)
- 1. běh (41 dok, 6 typů): 129 formulací + 97 záludností — **žádné pole nenasyceno** (křivky rostou).
- active-learning běh (39 DIVERGENTNÍCH dok): **+144 formulací / +101 záludností** (~zdvojnásobení)
  → zacílení na odlišné domény je řádově efektivnější než náhoda.
- Dvouvrstvý výsledek: TYP (signály+záměny) + POLE per typ. Klíč: STATUS = výpočet, ne klasifikace.

## Dvě vrstvy
- **Vrstva 1 (typ):** signály co identifikují typ + záměny mezi typy (úřednědeskový obal, abstraktní názvy).
- **Vrstva 2 (pole):** per typ jeho pole + formulace (recall) + záludnosti (precision).

## Proč to není nora
| Nora | Tady |
|---|---|
| ruční slepý slovník synonym | silný model čte reálná data |
| „kdy přestat?" neznámo | saturační křivka + diff = stop-signál |
| jen recall | obě strany (recall+precision) |
| neměřené | měřené proti ground-truth (dotacni.info/IROP) |

LLM už zná běžné formulace — cenná je jen **bounded sada záludností** (negativní pravidla) + definice
polí + pár few-shot. Ne exhaustivní synonyma.

---

# Post-harvest completeness gate — „neunikla nám OPORTUNITA?" (POVINNÝ krok po fázi 1)

Pozn.: tohle je JINÁ otázka než pokrytí formulací výše. Tady: **dostal harvester ze zdroje všechno?**
**Kontrakt:** po každém harvestu zdroje agent SPUSTÍ `scripts/coverage_verify.py <harvest.jsonl>`
a NEPROHLÁSÍ zdroj za hotový, dokud gate neskončí PASS. Completeness se MĚŘÍ, nehádá.

## Dvě stage (struktura → oportunita)
- **Stage 1 — strukturální diff (deterministický, bez LLM):**
  - `#1 WP REST`: když host běží WordPress → `X-WP-Total` pro posts/pages/CPT = kolik URL zdroj eviduje.
  - `#2 sitemap diff`: robots.txt → `/sitemap.xml`/`/wp-sitemap.xml` → všechny `<loc>` − naše URL = **MISSED**.
  - Výstup `data/files/_coverage_verify.jsonl` + per-zdroj **verdikt**:
    `complete_structural` / `needs_triage` (MISSED>0) / `no_sitemap_inconclusive` / `ceiling_hit_partial`.
- **Stage 2 — triáž MISSED na OPORTUNITU (LLM, classify):**
  MISSED jsou většinou novinky → surový počet ≠ uniklé granty. „Nechybí oportunita" se potvrdí JEN tak,
  že se MISSED URL **stáhnou a protáhnou `classify_wf`**; každý `grant`/`project` survivor =
  **REÁLNĚ uniklá oportunita = bug harvestu** (špatný seed / link-filtr) → oprav a re-harvestuj tu URL (máme ji).

## Verdikt gate
**PASS** jen když Stage 2 nenajde v MISSED žádný grant/project. Jinak **NEEDS_FIX**.
- `complete_structural` → Stage 2 jen pro jistotu (MISSED=0).
- `needs_triage` → Stage 2 POVINNÁ.
- `no_sitemap_inconclusive` (zdroj bez sitemapy) → check #2 nestačí → **re-crawl saturace** (re-harvest → diff
  nových URL; 0 nových = nasyceno) NEBO externí cross-check (dotacni.info/IROP).
- `ceiling_hit_partial` → sitemap > `safety.runaway_page_ceiling` → diff useknutý → prošetři (NEzvyšuj naslepo;
  pro pouhé ČTENÍ sitemap-indexu lze vědomě zvednout bound — není to data cap).

## DŮLEŽITÉ — co gate negarantuje sám o sobě
Surový strukturální diff (Stage 1) říká „co jsme NEvzali", NE „uniklá výzva". Bez Stage 2 (classify)
NENÍ completeness doložená. A sitemap je jen lower-bound (může být neúplná/stará) — proto u no-sitemap
zdrojů re-crawl saturace.
