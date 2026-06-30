# Opportunity Pipeline — recept na extrakci dotačních/grantových oportunit ze všech zdrojů

Konsoliduje zjištění z mapování platforem re-grantio (2026-06-01) do použitelného postupu.
Claude řídí pipeline; **Apify** renderuje SPA/postback weby, **skripty** harvestují + konvertují
dokumenty + počítají status, **Sonnet** klasifikuje typ a měří kvalitu, **Haiku** masivně
paralelně extrahuje pole. **Maximálně využívá UŽ STAŽENÁ DATA** (viz `docs/data_reuse.md`).

---

## 🔎 Vyzkoušej & dokumentace

- **Živá aplikace (rozcestník větví + recept):** → **[chocholous.github.io/regrantio](https://chocholous.github.io/regrantio/)**
  Homepage = diagram logiky receptu + návod „jak přidat další data (Claude Code + Opus)" + seznam větví s merge-statusem. Každá větev má vlastní verzi appky — nejnovější je **`coverage-expansion-next`** (**2749 oportunit / 127 poskytovatelů** k 2026-06-30: 14 krajů + ~30 měst + ministerstva + státní fondy + agentury GAČR/TAČR/NSA + nadace + EU OP + EU Funding & Tenders Portal + LLM/deterministická vrstva 2 + Opus kategorie). Filtry: oblast · sektor/typ žadatele · cílová skupina · poskytovatel · kraj · forma · zdroj · spoluúčast · míra · typ dokumentu · status · výše. Detail nese doslovné citace (grounding) + odkazy na originály. Pages se nasazují per-branch přes GitHub Actions (`.github/workflows/pages.yml`). **Datový kontrakt pro produkt:** [docs/PRODUCT_API.md](docs/PRODUCT_API.md) · **refresh strategie:** [docs/REFRESH.md](docs/REFRESH.md).
- **Vygenerovat appku lokálně:** `python3 scripts/build_app.py` → `data/grants_app.html`
- **Dokumentace:** [docs/platform_playbook.md](docs/platform_playbook.md) (CMS rodiny) · [docs/detection.md](docs/detection.md) · [docs/coverage.md](docs/coverage.md) · [schema/opportunity_schema.md](schema/opportunity_schema.md) · [CLAUDE.md](CLAUDE.md) (operační)

## 📦 Data v repozitáři (reprodukovatelnost)

Raw data jsou komprimovaná v **`data_bundle/`** (~1,9 GB) — rozbal jedním příkazem:
```bash
brew install xz zstd      # potřebné kompresory
./scripts/unpack_data.sh  # data_bundle/*.tar.xz + originals.part-* → data/
```
- **core** (3 MB) — `opportunities.jsonl` (snapshot z doby zabalení; živý dataset je `data/opportunities_v2.jsonl`, 2749 oportunit), harvest jsonl, configy, app
- **doctext** (11 MB) — vytěžený TEXT z PDF/xls/doc (pipeline jede i bez originálů)
- **wpfull** (55 MB) — WordPress korpus
- **originals** (1,8 GB, split na 95 MB kvůli GitHub limitu 100 MB/soubor) — PDF/xls/doc originály (interně DEFLATE, nekomprimují se)

---

## Klíčové principy (proč to takhle)

1. **Dvouvrstvý model** — odděl ŠÍŘI od HLOUBKY:
   - **Vrstva 1 (harvest):** tenký parser per CMS-rodina → jen TEXT + DOKUMENTY (to, co se mezi CMS liší). ~12 rodin = ~12 tenkých harvesterů.
   - **Vrstva 2 (extrakce):** JEDEN univerzální LLM-extraktor próza+PDF → opportunity schema (to, co je společné napříč zdroji).
   - Přílohová pipeline (`dsw2_fetch.py`) je UNIVERZÁLNÍ — řeší všechny handlery (File.ashx, /soubor, /getmedia, přímé .pdf, dsw2).

2. **Dvě vrstvy obsahu:** nejdřív **TYP** (grant / projekt / news / mise-téma / administrativa / ostatní), pak **POLE typu**.

3. **STATUS se POČÍTÁ v kódu, ne v LLM.** open/closed (grant) i open/done (projekt) je VÝPOČET z dat, ne klasifikace — otevřená a uzavřená výzva jsou textově identické, liší se jen datem vs dnešek.

4. **Detaily strukturovaně (bez LLM) jen u 3-4 zdrojů** (dotacni.info šablona, IROP/dotaceEU Kentico inline, arcgis JSON). **Všude jinde = LLM na prózu/PDF** — a to je OK, vrstva 2 je jedna pro všechno.

5. **Nevěřit platform labelu** z detekce — ověřuj generátor / strukturální otisk (mv_legacy a gordic_ginis byly slité 3 CMS).

---

## RECEPT — 7 fází

### Fáze 0 — Detekce & routing (jednou per zdroj)
- `scripts/cms_similarity.py` — strukturální otisk (asset cesty + URL vzory + cookie/header) → **CMS rodina** (label-free, robustnější než generator meta).
- **Routing = `routing.yaml`** (jediný zdroj pravdy platforma→harvester): `scripts/routing.py --host <host>` vrátí platformu + harvester[] + metodu. `detect_family(host)` → `route(platforma)` → konkrétní skript (default = univerzální `harvest_site.py`). `docs/platform_playbook.md` = lidský popis rodin.
- **⓪ STRUKTURA PŘED PRÓZOU** (`docs/detection.md`): VŽDY nejdřív zkus strukturovaný endpoint (opendata/award API, inline JS var, šablona, list-XHR, WP REST) → parsuj deterministicky, skip LLM. LLM až když je detail neredukovatelně próza/PDF. **5. přístupová metoda:** SPA/grid se skrytým JSON-XHR → 1× odposlech Playwrightem (`scripts/lewis_discover.py`) → čistý HTTP replay bez Apify (`lewis_dynamo.py`). Ověř, CO endpoint dá (award-DB ≠ otevřené výzvy).

### Fáze 1 — Harvest (per rodina; PRVNÍ zkus REUSE už stažených dat)
- **REUSE:** `data/wp_full/` (WP, 73k zázn.), `data/vismo_documents.jsonl` + `data/vismo_files/` (vismo + 680 PDF→txt), `data/dsw2_*` , `data/dotacni_structured.json`. Viz `docs/data_reuse.md`.
- **Statické (skript):** WP→`scripts/wp_harvest.py` (lossless REST), vismo→`scripts/vismo.py`+`vismo_detail.py`, Kentico→`scripts/kentico_irop.py`, dsw2→`scripts/dsw2.py`, ASP.NET/clanek→`scripts/mv_cms.py`, Plone→folder→detail→.pdf. (Repo je osamostatněné — všechny harvestery žijí v `scripts/`, ne v rodičovském `extract/`.)
- **SPA / postback (Apify):** grantys (`ng-app`), aspnet_webforms (granty.praha/SFŽP), custom_spa, MV WebForms kapitoly → Apify `website-content-crawler` (JS rendering) → markdown. Viz `docs/apify_howto.md`.
- Výstup per zdroj: záznamy `{url, title, date, text/html, document_urls[]}`.

### Fáze 2 — Doc-store: dokumenty → text (= VRSTVA 1, fáze 2; univerzální, `scripts/docstore.py`)
> Mapování: **vrstva 1** = fáze 1 (harvest) + fáze 2 (dokumenty→text) · **vrstva 2** = fáze 3–4 (classify + extract). Viz `docs/phase2_runbook.md` pro běh v čisté session.
- **Vazba na vrstvu 1 = `documents[]` URL.** Harvester přílohy jen LISTUJE (lossless), doc-store je MATERIALIZUJE: `dsw2_fetch.sniff_ext()` + download + `convert()` (pdftotext/textutil) → `data/files/<source>/<sha>.{ext,txt}` + `manifest.jsonl` (keyed URL). Idempotentní.
- **Sjednocuje 2 cesty:** `--from-harvest` materializuje URL-only zdroje (eeagrants/praha); `--index` zaregistruje už stažené `data/vismo_files/`/`dsw2_files/` bez re-downloadu. Vše v jednom manifestu.
- Skenované PDF → flag na OCR.

### Fáze 2.5 — Strukturální pre-filtr (volitelné, `scripts/prefilter.py`) — 100% bezpečné
- **Broad harvest je OK, data se berou celá** — obsahový šum (news zmiňující dotace) filtruje až fáze 3 (classify) per-record. Pre-filtr smí odstranit **JEN strukturálně neextrahovatelné**: prázdné (text<`limits.prefilter_empty_text_max` & 0 dok), exact-dup, nav/archiv URL. **NIKDY content/keyword/density** — má false-negativy („veřejná soutěž / výběrové řízení = grant"). Šetří jen volání klasifikátoru (h19 batch: −24 % nula rizika).

### Fáze 3 — Klasifikace TYPU (Claude-workflow `scripts/classify_wf.js`, Haiku — `prompts/classify_type.md`)
- Mnou řízené workflow, 1 dokument = 1 Haiku agent, naslepo. Výstup: `base_type ∈ {grant, project, news, foundation_mission, administrative, other}`.
- **Status NEklasifikuj** — počítá se ve fázi 5.
- Pozor na záměny: **úřednědeskový obal** ≠ administrativa když obsah je dotační program; **„veřejná soutěž / výběrové řízení na poskytnutí prostředků" = grant** (regex by to splet → klasifikuj LLM, ne regexem). Viz `prompts/pitfalls.md`.

### Fáze 4 — Extrakce POLÍ per typ (Claude-workflow `scripts/extract_wf.js`, Haiku — `prompts/extract_grant.md`)
- Mnou řízené workflow, **1 oportunita = 1 agent**, plný text + plné přílohy z doc-store.
- **grant:** focus_area, amount, deadline, open_from, eligible_applicants, required_attachments, how_to_apply.
- **NEOŘEZÁVAT vstup** (kontext ~200k) — měřeno: ořez sráží `amount` 27 %→90 %. Limity jen v `limits.json`.
- **Aplikuj NEGATIVNÍ pravidla** (vytěžené záludnosti, `prompts/pitfalls.md`): `platnost:`/`realizace`/`vyhlášení výsledků`/`ZoR/ŽoP` ≠ deadline; `úvěr`/`jistina`/`úroky`/`odvod` ≠ dotace; `podpořen částkou` = projekt ne výzva; `cílová skupina` ≠ žadatel; soubory-ke-stažení ≠ povinné přílohy.
- **projekt:** grantee, amount, year. **mise:** mission, topics, regions.

### Fáze 5 — Úložiště + výpočet STATUSU (kód, ne LLM — `scripts/opportunities.py`)
- **Kanonické úložiště `data/opportunities.jsonl`** sjednocuje VŠECHNY zdroje (LLM extrakci i strukturované jako dsw2/lewis) do jednoho plochého schématu (`schema/opportunity_schema.md`).
- **Status v kódu** (`compute_status`, `--today`): grant `open` (open_from ≤ dnes ≤ deadline) / `announced` (dnes < open_from) / `closed` (dnes > deadline) / `unknown`. Rok v názvu ≠ rok podání → ber z `deadline`, ne z titulku.
- **`extra{}` lossless** (nic se nezahazuje) + **`provenance{}`** (harvest_file/url + `documents[].txt_path` z doc-store) → úplný řetězec pole → soubor.

### Fáze 6 — Dedup & grounding (cross-source — TODO)
- **Dedup:** stejná výzva napříč zdroji (primární + agregátor dotacni.info + úřední deska) → kanonická dle (číslo výzvy / IČO / normalizovaný title; `opportunities.py:canon_key` je první iterace).
- **Grounding:** křížově ověř deadline/amount napříč reprezentacemi i proti `provenance.documents[].txt_path` souborům; neshodu flagni. Široký základ = redundance = spolehlivost.

---

## Průběžně — Coverage & active learning (zlepšování promptů)
Cyklus, který je MĚŘENÝ (ne nora):
1. `scripts/diversity_finder.py` → nejodlišnější dosud nevzorkované zdroje (data-driven).
2. coverage workflow (`scripts/coverage_wf.js`, typ+pole) → vytěž nové formulace + záludnosti.
3. **diff proti minulému** → vyčísli zisk (39 divergentních dok = +144 formulací/+101 záludností).
4. Stop, až zisk klesne (saturace). Nové záludnosti → `prompts/pitfalls.md`.

---

## Kam co patří
| Nástroj | Role |
|---|---|
| **Skripty** | harvest (REST/HTML/inline-JS), doc-store (`docstore.py`), status+úložiště (`opportunities.py`), fingerprint. Limity jen v `limits.json`. |
| **Playwright** | JEDNORÁZOVÝ objev skrytého JSON-XHR u SPA/grid (`lewis_discover.py`) → pak čistý HTTP replay (`lewis_dynamo.py`) BEZ Apify |
| **Apify** | až poslední možnost — gated SPA (grantys API za session), antibot; ne automaticky pro WebForms (často jde HTTP replay) |
| **Claude-workflow (Haiku)** | mnou řízené: `classify_wf.js` (typ) + `extract_wf.js` (pole, 1 oportunita/agent, plný text) |
| **Sonnet** | měření coverage/kvality, detekce nových platforem |

## Soubory
- `docs/platform_playbook.md` — **definice VŠECH CMS rodin** → podpis/harvester/metoda/jdou-detaily-snadno
- `docs/detection.md` — **jak detekovat platformu + komu se podobá** (3 vrstvy: fingerprint / strukturální shlukování / Sonnet; lekce o slitých labelech)
- `docs/coverage.md` — coverage & active learning (typ+pole, saturace, diversity_finder)
- `docs/data_reuse.md` — index UŽ STAŽENÝCH dat (html/md/pdf/doc/xls) k reuse
- `docs/apify_howto.md` — kdy a jak Apify (SPA/postback zdroje)
- `platform_data/` — **datové mapy** (platform_map, cms_clusters, detect_platforms_result, diversity_candidates, *_cov_result)
- `scripts/` — detekce (cms_similarity, platform_refingerprint, detect_platforms_wf) + harvestery (wp/vismo/kentico/mv/dsw2/**eeagrants/praha_grants/lewis_dynamo**) + **doc-store** (`docstore.py`) + dsw2_fetch + coverage/diversity
- **`scripts/extract_wf.js` / `classify_wf.js`** — Claude-workflow vrstvy 2/1 (Haiku, 1 oportunita/agent, plný text)
- **`scripts/lewis_discover.py`** — Playwright objev skrytého XHR (SPA/grid) → endpoint pro HTTP replay
- **`scripts/opportunities.py`** — kanonické úložiště `data/opportunities.jsonl` (jednotné schéma + status + extra lossless + provenance)
- **`routing.yaml` + `scripts/routing.py`** — platforma→harvester (jediný zdroj pravdy; `--host`/`--platform`/`--all`)
- **`limits.json` + `scripts/limits.py`** — registr limitů (JEN sondy/safety; data se berou celá)
- `prompts/classify_type.md` / `extract_grant.md` / `pitfalls.md` — prompty vrstvy 1/2 + vytěžené záludnosti
- `pipeline.py` — starší in-process driver (reálné fáze 3-4 jedou přes workflow výše)
- `schema/opportunity_schema.md` — kanonický model (+ extra/provenance)
