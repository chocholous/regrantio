# Opportunity model — jednoduché oddělené entity + extraction hints

Princip: **oddělené podle druhu, plochá pole, status je organizační osa.**
Žádná mega-tabulka s diskriminátorem, žádné `*_preview/_text/_month` varianty,
žádná „LLM vrstva" v schématu (čím se pole naplní = věc pipeline, ne modelu).

Kořen je **foundation (zdroj)** — existuje vždy. grant/project/news/event visí
volitelně (0..N). Malá nadace = jen foundation s posláním a tématy.

**Sloupec „kde hledat"** je podložen reálnými daty:
- **dsw2/Otevřená města**: data jsou inline JSON `var fonds={id:{name,description}}` + `var treeData=[...]`
- **vismo_classic**: `.dok` bloky, `.dok-nazev` / `.dok-datum` / `.dok-slozka`
- **the-machine (mpsv)**: easy pole na stránce; **částka/žadatel/region jen v doc-markdownu PDF**
- doc-md příklad: „Plánovaná alokace výzvy 228 mil. Kč", „Žadatel o podporu je poskytovatelem služeb"

---

## 1. foundation  (zdroj — vždy existuje)

| pole | význam | HTML | markdown | doc-markdown |
|---|---|---|---|---|
| id | slug zdroje | — | — | — |
| name | název organizace | `<title>`, `og:site_name`, logo alt | `# H1` | hlavička dok. |
| url | homepage | kanonická doména | — | — |
| source_type | druh zdroje (viz source_types.md) | odvozeno z domény/obsahu | — | — |
| mission | poslání / čemu se věnují | sekce „O nás/Poslání", `<meta description>` | odstavec pod `## O nás` | — |
| support_topics[] | oblasti podpory | nav/menu, `.tag`, výčty | bullet list pod „Co podporujeme" | — |
| regions[] | území působnosti | footer, „kraj/region" | — | — |

> Zdroj bez opportunit = jen tahle entita. Časté u malých nadací.

---

## 2. grant  (výzva — co nadace NABÍZÍ žadatelům)

| pole | význam | HTML | markdown | doc-markdown |
|---|---|---|---|---|
| foundation_id | → zdroj | — | — | — |
| title | název výzvy | dsw2: `fonds[].name` · vismo: `.dok-nazev` · obecně `<h1>/<h2>`, `<a>` v listingu | `#`/`##` nadpis, odkaz v seznamu | nadpis 1. strany |
| url | odkaz na detail | `<a href>` položky listingu | `[text](url)` | — |
| focus_area | tematická oblast | vismo: `.dok-slozka` · dsw2: kategorie ve `treeData` | nadřazená sekce | „Komponenta/Oblast …" |
| amount | částka / max podpora | **zřídka na stránce**; tabulka, `.castka` | `**Alokace:**`, `Kč`/`mil. Kč` | **ZDE**: „alokace … Kč", „míra podpory %" |
| deadline | uzávěrka příjmu | vismo: `.dok-datum`, `<time>` | `**Uzávěrka:** DD.MM.RRRR`, `**Termín**` | **ZDE často**: „Termín …", „Datum ukončení příjmu" |
| status | announced \| open \| closed | odvozeno z deadline/začátku | — | — |
| _(hard)_ eligible_applicants | kdo může žádat | **skoro nikdy na stránce** | — | **ZDE**: „Žadatel o podporu je …", „Oprávnění žadatelé" |

**status (odvozený z dat, NE z LLM):**
- `announced` — oznámený/vyhlášený (zveřejněn, příjem ještě nezačal / deadline v budoucnu)
- `open` — otevřený (probíhá příjem)
- `closed` — uzavřený (po uzávěrce)

---

## 3. project  (co nadace FINANCOVALA — strana příjemce)

| pole | význam | HTML | markdown | doc-markdown |
|---|---|---|---|---|
| foundation_id | → zdroj | — | — | — |
| title | název projektu | `.dok-nazev`, `<h2>`, karta v galerii | `##` nadpis | — |
| grantee | příjemce | „realizátor/příjemce", karta | `**Příjemce:**` | „Příjemce dotace" |
| amount | přidělená částka | tabulka výsledků | `Kč` | seznam podpořených v PDF |
| period | období realizace | „2023–2024" u položky | `start–end` | „Doba realizace" |
| status | open \| closed | odvozeno z period/end_date | — | — |

**status:** `open` = probíhající · `closed` = uzavřený/dokončený.
> Časté u malých nadací: mají jen `closed` projekty a žádné granty.

---

## 4. news  (aktuality)

| pole | význam | HTML | markdown | doc-markdown |
|---|---|---|---|---|
| foundation_id | → zdroj | — | — | — |
| title | titulek | `<article> h2/h3`, WP REST `title.rendered` | `##` v sekci Aktuality | — |
| url | odkaz | `<a>` | `[…](url)` | — |
| date | datum publikace | `<time datetime>`, `.date`, WP REST `date` | `*DD.MM.RRRR*` u položky | — |

> WordPress: nejlépe přes REST `/wp-json/wp/v2/posts` (uniformní napříč 85 weby).

---

## 5. event  (události)

| pole | význam | HTML | markdown | doc-markdown |
|---|---|---|---|---|
| foundation_id | → zdroj | — | — | — |
| title | název akce | JSON-LD `Event.name`, `.event-title` | `##` v sekci Kalendář | — |
| url | odkaz | `<a>` | `[…](url)` | — |
| date | datum konání | JSON-LD `startDate`, iCal, `<time>` | datum u položky | — |

---

## Vztahy

```
foundation (1, vždy)
 ├── grant   (0..N)   status: announced | open | closed
 ├── project (0..N)   status: open | closed
 ├── news    (0..N)
 └── event   (0..N)
```

## Klíčové poznatky z reálných dat (the-machine)

- **easy pole** (title/url/deadline/date) — spolehlivě ve stránce/listingu (~100 % napříč ministerstvy).
- **hard pole** (amount, eligible_applicants, regions) — **na stránce skoro nikdy; žijí v doc-markdownu PDF.** Proto je stahování dokumentů nutné, ne volitelné.
- **status** se počítá z dat (deadline/period). LLM si status vymýšlí (ověřeno: 20 halucinací na jednom zdroji) → nikdy ho nenechávat na modelu.
- **dsw2/Otevřená města + vismo_classic** = nejsnazší (strukturovaná data v HTML/JSON, jedna šablona pokryje 43 webů).

## Pravidla (ať to zůstane jednoduché)

1. Oddělené podle druhu (grant/project/news/event/foundation), ne jeden záznam s `content_classification`.
2. Status = jedno enum pole, organizační osa pro granty i projekty.
3. Plochá pole — jeden údaj = jedno pole; datum `date | null`, ne 5 variant.
4. Model neřeší, čím se pole naplnilo (parser vs LLM) — to je věc pipeline.
5. Zdroj smí být prázdný na opportunity — foundation s mission/topics a nulou grantů je validní stav.

## Dvě POVINNÁ systémová pole na každé oportunitě (úložiště `data/opportunities.jsonl`)

Oportunita je **PROJEKCE**, ne jediná kopie dat. Proto každý záznam navíc nese:

- **`extra{}` — LOSSLESS přetékací pole.** Cokoliv ze zdroje, co se nevejde do plochých polí schématu, se uloží sem (dsw2 `related_programs`/`published_note`/`links`, lewis `CisloProjektu`/`CastkaVycerpana`, vismo `uredni_od/do`…). **Nic se nezahazuje** — co schéma neumí, jde do `extra`. Zdroj pravdy zůstává lossless vrstva 1.
- **`provenance{}` — VAZBA na zdroj** (grounding/audit): `harvest_file` (který `data/*.jsonl` nese raw), `harvest_url` (klíč = web stránka), `documents[].{url, txt_path}` (stažené podklady přes doc-store), `layer` (1=strukturované / 2=LLM), `harvester`.

Řetězec: `pole` → `provenance.documents[].txt_path` → konkrétní soubor v `data/files/<source>/` → kdykoliv ověřitelný původ. Plní `scripts/opportunities.py` (+ `--link-docs` z doc-store manifestu). Status se i zde POČÍTÁ (`compute_status`, `--today`), ne z LLM.
