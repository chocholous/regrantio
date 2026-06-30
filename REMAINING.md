# REMAINING.md — stav projektu + co zbývá

Živý plánovací dokument. **Aktuální stav, co je hotovo, co zbývá a proč.** JAK pracovat (zlatá pravidla,
recept na zdroj, pasti) = `docs/SESSION_PLAYBOOK.md` + `CLAUDE.md`. Data žijí v gitignored `data/`.

> **Status k 2026-06-30, větev `coverage-expansion-next`.** Projekt je **produkčně připravený**: pokrytí
> dostupných zdrojů kompletní (zbytek = genuine blockery, viz níže), dataset bez datových chyb, produkční
> kontrakt + refresh strategie + CI gate hotové, napojení na produkt grantio.cz naspecifikované.

---

## 📊 Aktuální stav datasetu (live `data/opportunities_v2.jsonl`, k 2026-06-30)

| metrika | hodnota |
|---|---|
| **záznamů celkem** | **2749** (2724 grantů + 25 foundation_mission) |
| **poskytovatelů** | **127** |
| status grantů (přepočet k dnešku) | **720 open** (26 %) · 47 announced · 1302 closed (47 %) · 655 unknown (24 %) |
| typ poskytovatele | samosprava_kraj 843 · samosprava_obec 718 · ministerstvo 568 · evropska_komise 341 · nadacni_fond 63 · nadace 57 · statni_fond 47 · statni_agentura 44 · firemni_nadace 42 · zahranicni_fond 26 |
| zdroj financování | krajsky 1482 · eu_fondy 380 · eu_primy 341 · narodni_rozpocet 309 · vlastni_zdroje 205 · ehp_norsko 28 · ostatní (modernizacni_fond/npo/…) |
| region | celostátní 1046 · konkrétní kraj 1678 (14 krajů) |
| vyplněnost grantů | focus_area 2512 · deadline/průběžně 2069 (75 %) · how_to_apply 2215 · eligible 1753 · **amount 543 (20 %)** |
| integrita | **0 dup id · 0 null id · 0 bad amount · 0 deadline<open · 0 grant bez title · 0 bez url** |

Status se počítá KLIENTSKY k reálnému dnešku (`build_app.py:computeStatus` / produkt) → „open" počet
přirozeně klesá, jak deadliny míjejí; není to ztráta dat.

**Proč nuly nejsou chyba:** `amount=null` (80 %) a `status=unknown` (24 %) jsou VĚTŠINOU správné — částky
bývají jen v PDF zadávací dokumentace a katalogové programy nemají jeden deadline. Vynutit je = halucinace.
**Raději poctivý null než vymyšlené číslo.** (Ověřeno: IROP alokace na stránce je nejednoznačná.)

---

## 🏭 Produkční připravenost — HOTOVO

- **Pipeline:** harvest (vrstva 1) → `build_extract_input` → vrstva 2 (deterministická `data/_<src>_extract.py`
  nebo LLM workflow) → `ingest_rich` → `consolidate` → `fix_dataset` → `build_app` → `export_api`.
- **Produkční kontrakt** (`docs/PRODUCT_API.md`): veřejný feed `docs/opportunities.json` (`export_api.py`),
  `content_hash` per grant pro inkrementální sync, pojistka `--min-ratio` proti kolapsu datasetu.
  Stabilní Pages URL `.../branches/<branch>/opportunities.json`. Referenční sync + důkaz =
  `scripts/product_sync_example.py`.
- **Refresh strategie** (`docs/REFRESH.md` + `scripts/refresh.py`): kadence per tier, gap-check.
- **CI gate** (`scripts/validate_release.py` + `.github/workflows/validate.yml`): na každý push ověří
  syntax, configy a kontrakt (schema/id/content_hash/sync selftest).
- **Status logika** konzistentní napříč `opportunities.py` / `build_app.py` JS / dokumentací.
- **Napojení na produkt grantio.cz** (`docs/INTEGRATION_GRANTIO_CZ.md`): mapování `opportunities.json` →
  jejich Supabase `public.grants`, sync job, status výpočet. Implementaci napíše jejich Claude Code.
- **Deploy:** `docs/grants_app.html` (appka přes `pages.yml` → gh-pages). **NEMERGOVAT do main bez pokynu.**

**Zbývá v produkčním passu:** dořešit `h19_*` nadační batch (`docs/REFRESH.md §6` — reprodukovatelné
generickým harvesterem + LLM, většina je `foundation_mission`; nech jako poslední stav nebo per-web parser
až při reálné výzvě). Zvážit registraci family-covered hostů do `routing.yaml sources:` pro úplný refresh-checklist.

---

## ✅ Pokrytí zdrojů — HOTOVO (stručně)

- **Samospráva:** 14 krajů + ~30 měst (vismo, DSW2/otevřená města, bespoke per-web — vše v `routing.yaml`).
- **Ministerstva:** MŠMT, MV, MŽP, MZe/eAGRI, MZČR, MKČR, MPSV, MPO (9 prog.), MMR (9 dotací).
- **Státní fondy (100 %):** SFŽP (19), SFA (8), SFPI/SFRB (6), SFDI (8), SFK (1).
- **Státní agentury:** GA ČR (14), TA ČR (9), NSA (21).
- **EU operační programy (řízené z ČR):** OPŽP (107), OP ST (98), OP JAK (8) — `zdroj=eu_fondy`.
- **EU centrální (Brusel):** EU Funding & Tenders Portal — **341 otevřených výzev** (Horizon/Erasmus+/
  Creative Europe/Digital/CEF/LIFE/CERV/EDF) přes SEDIA API (Playwright→HTTP replay BEZ Apify).
- **Mezinárodní:** EHP/Norské fondy (26), Česko-německý fond budoucnosti (36).
- **Nadace/fondy:** ~17 (via, ČEZ, OKD, Agrofert, Albert, Sirius, Leontinka, Partnerství, ADRA, Veronica,
  Hlávkova, Kellner, VDV, OSF, fond paliativní péče, sociální nadační fond, …).
- **EU/centrální (řízené z ČR):** IROP (120), dotaceEU (13).

---

## ⛔ Co zbývá — vše naráží na GENUINE BLOCKER (Apify/WebForms/bespoke/WAF)

Cheap WP-REST výhry jsou vyčerpané. Zbylé zdroje vyžadují placené nástroje nebo těžkou bespoke práci —
**dedikovaná session s rozpočtem na Apify/WebForms**, nebo nízký čistý výnos:

| Zdroj | Blocker |
|---|---|
| OP TAK / `dotaceeu.cz` centrál | ASP.NET **WebForms** (postback listing, 0 statických href) → Apify/viewstate; + dedup riziko s tím, co máme |
| OPZ+ (`esfcr.cz`) | ne-WP Liferay listing → bespoke render-parse; překryv s MPSV (máme 8) |
| OPD / NPO / SZIF (PRV) | ne-WP (`opd.cz`/`narodniplanobnovy.cz`); **SZIF = WAF** (ConnectionReset) → proxy/Apify |
| Interreg ×5, Visegrad | ne-WP **bespoke** (per-site HTML/próza+PDF), roztříštěné |
| Zbylé velké nadace | převážně **ne-WP** (Yii/custom-PHP: ČEZ/OKD/Abakus/Neuron/Vodafone/AGEL…) → bespoke per-web, většinou jen `foundation_mission` |
| Chybějící města (ČB, Zlín, Šumperk, Třebíč) | **ověřeno Playwrightem: NEjsou čistě harvestovatelná** (víceúrovňová navigace + PDF, render vrátil ~0 programů) |
| MF / MO / MSp / MZV | tenké / spíš rozpočtové vztahy než soutěžní dotace (MD prověřeno: žádné přímé národní dotace) |

---

## 🎯 Priority, kdyby se otevřela coverage session (s rozpočtem na nástroje)

- **P2b:** SZIF (PRV/SZP — WAF, přes proxy/Apify), NRB (úvěry/záruky — ověřit, jestli vůbec dotace).
- **P3:** OP TAK / OPZ+ / OPD / NPO přes Apify/WebForms na `dotaceeu.cz` (pozor na dedup s IROP/OPŽP/OPST).
- **P4:** rozšířit nadace ~17 → 40+ (Abakus, Neuron, Karla Janečka, KB Jistota, ČSOB, Veolia, J&T, Tipsport,
  Proměny, AGEL, Český literární fond, Experientia, Vodafone/O2; komunitní nadace) — 1 web = 1 parser, většinou bespoke.
- **P5:** doplnit chybějící města v mělkých krajích (Jihočeský/Olomoucký/Zlínský/Vysočina) — reuse
  `vismo.py`/`dsw2.py`, ale ověřit harvestovatelnost (část je za víceúrovňovou navigací).
- **P6:** EU F&T Portal je hotový; doplnit jen nové programy při re-harvestu.
- **P7:** Visegrádský fond, Swiss-Czech — ne-WP bespoke, malé sady (spíš mission + pár výzev).

---

## ⚑ Stálé pasti (pro každou session)

1. **Windows cp1250 konzole** — non-ASCII v printu padá; každý skript má `sys.stdout.reconfigure(utf-8)` guard.
   Pozor i v YAML/JSON: ASCII `"` uvnitř českého `„…"` rozbije parser (kouslo to `routing.yaml`).
2. **Status počítá KÓD, ne LLM** (`opportunities.py:compute_status`); ukládej RAW `open_from`/`deadline`.
3. **WP fulltext discovery vrací všechny ročníky** — filtruj `--since`/`--year` na aktuální kolo (vzor `gacr.py`).
4. **`pipeline.py` = legacy stub** (natvrdo `date(2026,6,1)`) — NEpoužívat jako zdroj pravdy; kanonický
   status je `opportunities.py:compute_status`. Živý dataset = `opportunities_v2.jsonl`, ne `opportunities.jsonl`.
5. **Data gitignored** — fresh clone nemá `data/`; obnova = `scripts/unpack_data.sh` z `data_bundle/` nebo
   re-harvest. Vrstva-2 extraktory `data/_<src>_extract.py` jsou TRACKOVANÉ (jsou to kód, ne data).
6. **Nehalucinovat** — `amount=null`/`deadline=null` zůstává null; žádné fiktivní záznamy.
