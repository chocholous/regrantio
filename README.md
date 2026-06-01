# Opportunity Pipeline — recept na extrakci dotačních/grantových oportunit ze všech zdrojů

Konsoliduje zjištění z mapování platforem re-grantio (2026-06-01) do použitelného postupu.
Claude řídí pipeline; **Apify** renderuje SPA/postback weby, **skripty** harvestují + konvertují
dokumenty + počítají status, **Sonnet** klasifikuje typ a měří kvalitu, **Haiku** masivně
paralelně extrahuje pole. **Maximálně využívá UŽ STAŽENÁ DATA** (viz `docs/data_reuse.md`).

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
- `scripts/detect_family.py` — strukturální otisk (asset cesty + URL vzory + cookie/header) → **CMS rodina** (label-free, robustnější než generator meta).
- Vyhledej rodinu v `docs/platform_playbook.md` → **harvester + přístupová metoda** (REST / inline-JS / HTML-listing / SPA-headless / WebForms-postback).

### Fáze 1 — Harvest (per rodina; PRVNÍ zkus REUSE už stažených dat)
- **REUSE:** `data/wp_full/` (WP, 73k zázn.), `data/vismo_documents.jsonl` + `data/vismo_files/` (vismo + 680 PDF→txt), `data/dsw2_*` , `data/dotacni_structured.json`. Viz `docs/data_reuse.md`.
- **Statické (skript):** WP→`extract/wp_harvest.py` (lossless REST), vismo→`extract/vismo.py`+`vismo_detail.py`, Kentico→`extract/kentico_irop.py`, dsw2→`extract/dsw2.py`, ASP.NET/clanek→`extract/mv_cms.py`, Plone→folder→detail→.pdf.
- **SPA / postback (Apify):** grantys (`ng-app`), aspnet_webforms (granty.praha/SFŽP), custom_spa, MV WebForms kapitoly → Apify `website-content-crawler` (JS rendering) → markdown. Viz `docs/apify_howto.md`.
- Výstup per zdroj: záznamy `{url, title, date, text/html, document_urls[]}`.

### Fáze 2 — Dokumenty → markdown (univerzální)
- `extract/dsw2_fetch.py`: `sniff_ext()` (rozpozná typ za handlerem bez přípony) + download + `convert()` (pdftotext pro PDF, textutil pro DOC/DOCX/XLS/ODT na macOS).
- **REUSE:** už převedené `.txt` v `data/vismo_files/`, `data/dsw2_files/`.
- Skenované PDF → flag na OCR.

### Fáze 3 — Klasifikace TYPU (Sonnet/Haiku — `prompts/classify_type.md`)
- Vstup: title + text + úryvky dokumentů. Výstup: `base_type ∈ {grant, project, news, foundation_mission, administrative, other}`.
- **Status NEklasifikuj** — počítá se ve fázi 5.
- Pozor na záměny: **úřednědeskový obal** (úřední deska/MěÚ metadata) ≠ administrativa když obsah je dotační program; abstraktní název programu vs mise.

### Fáze 4 — Extrakce POLÍ per typ (Haiku, masivně paralelně — `prompts/extract_grant.md`)
- **grant:** focus_area, amount, deadline, open_from, eligible_applicants, required_attachments, how_to_apply.
- **NEOŘEZÁVAT vstup** (kontext ~200k) — dávat plný markdown obsahu + markdown příloh.
- **Aplikuj NEGATIVNÍ pravidla** (vytěžené záludnosti, `prompts/pitfalls.md`): `platnost:`/`realizace`/`vyhlášení výsledků`/`ZoR/ŽoP` ≠ deadline; `úvěr`/`jistina`/`úroky`/`odvod` ≠ dotace; `podpořen částkou` = projekt ne výzva; `cílová skupina` ≠ žadatel; soubory-ke-stažení ≠ povinné přílohy.
- **projekt:** grantee, amount, year. **mise:** mission, topics, regions.

### Fáze 5 — Výpočet STATUSU (kód, ne LLM — `scripts/compute_status.py`)
- grant: `open` když open_from ≤ dnes ≤ deadline; `announced` když dnes < open_from; `closed` když dnes > deadline; `unknown` bez data.
- Preferuj okno „Úřední deska od-do" kde je (high confidence).
- projekt: `done` když je vyúčtovaná částka / signál dokončení; jinak `open`.

### Fáze 6 — Dedup & grounding (cross-source — `scripts/dedup_ground.py`)
- **Dedup:** stejná výzva napříč zdroji (primární + agregátor dotacni.info + úřední deska) → kanonická dle (číslo výzvy / IČO / normalizovaný title).
- **Grounding:** křížově ověř deadline/amount napříč reprezentacemi; neshodu flagni. Široký základ = redundance = spolehlivost.

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
| **Apify** | render SPA (grantys) + WebForms postback (aspnet_webforms, MV kapitoly, custom_spa) → markdown |
| **Skripty** | harvest (REST/HTML/inline-JS), doc→md (pdftotext/textutil), status, dedup, fingerprint |
| **Sonnet** | klasifikace TYPU, měření coverage/kvality, detekce nových platforem |
| **Haiku** | masivně paralelní extrakce POLÍ (bulk) |

## Soubory
- `docs/platform_playbook.md` — **definice VŠECH CMS rodin** → podpis/harvester/metoda/jdou-detaily-snadno
- `docs/detection.md` — **jak detekovat platformu + komu se podobá** (3 vrstvy: fingerprint / strukturální shlukování / Sonnet; lekce o slitých labelech)
- `docs/coverage.md` — coverage & active learning (typ+pole, saturace, diversity_finder)
- `docs/data_reuse.md` — index UŽ STAŽENÝCH dat (html/md/pdf/doc/xls) k reuse
- `docs/apify_howto.md` — kdy a jak Apify (SPA/postback zdroje)
- `platform_data/` — **datové mapy** (platform_map, cms_clusters, detect_platforms_result, diversity_candidates, *_cov_result)
- `scripts/` — detekce (cms_similarity, platform_refingerprint, detect_platforms_wf) + harvestery (wp/vismo/kentico/mv/dsw2) + dsw2_fetch + coverage/diversity
- `prompts/classify_type.md` — prompt vrstvy 1 (typ)
- `prompts/extract_grant.md` — prompt vrstvy 2 (pole grantu) s negativními pravidly
- `prompts/pitfalls.md` — vytěžené záludnosti per pole (do promptů)
- `pipeline.py` — driver: spojí fáze nad existujícími daty
- `schema/` → `../schema/opportunity_schema.md` (kanonický model)
