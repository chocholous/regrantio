# REMAINING.md — plán rozšiřování pokrytí

Živý plánovací dokument (verzovaný v gitu). Co je hotovo, co zbývá, v jakém pořadí.
Aktualizuj po každém přidaném zdroji. **JAK to dělat (zlatá pravidla, recept, pasti) viz
`docs/SESSION_PLAYBOOK.md`** + `CLAUDE.md`; data žijí v gitignored `data/`.

> **Status k 2026-06-30.** Větev `coverage-expansion-next`. **2749 záznamů / 127 poskytovatelů.**

## 🏭 Production-readiness pass 2026-06-30 (probíhá)
Posun od „dev cvičení" k produkčnímu provozu (data → produkt = web app). Hotovo tuto session:
- **KRITICKÝ FIX:** `routing.yaml` nešel parsovat (ASCII `"` uvnitř českého `„open"` na `ec.europa.eu`)
  → `scripts/routing.py` padal od commitu eu_ft. Opraveno; 70 sources / 23 families se načítají.
- **Produkční kontrakt** `docs/PRODUCT_API.md` + `scripts/export_api.py` rozšířen: `content_hash` per grant
  (inkrementální sync produktu: upsert dle `id`, re-index dle hash, delete chybějících `id`), pojistka
  `--min-ratio` proti kolapsu datasetu (rozbitý harvest nesmaže granty z produktu). schema 1.0→1.1.
- **Refresh strategie** `docs/REFRESH.md` + `scripts/refresh.py` (operační checklist zdroj→harvester→tier→
  počet + gap-check). Odhalen jediný reálný reprodukční gap = jednorázový nadační batch `h19_*` (viz §6 REFRESH).
- **Data audit:** dataset čistý (0 dup id, 0 date errors, 0 type errors, 0 mojibake); build tail
  (consolidate→fix_dataset→build_app→export) ověřen idempotentní. Nuly (amount 80 %, deadline 655) jsou
  dle doktríny správné (poctivý null > vymyšlené číslo).
- **Doc fixy:** CLAUDE.md prostředí macOS→Windows realita; headline počty (README/SESSION_PLAYBOOK) → 2749/127.

**Zbývá v produkčním passu (příští session):** dořešit `h19_*` nadační batch (per-web parsery nebo
ponechat jako poslední stav); zvážit registraci family-covered hostů do `routing.yaml sources:` pro
úplnost refresh-checklistu; pokračovat coverage (P-priority níže) až po kvalitě.

## ✅ Stav projektu: pokrytí dostupných zdrojů KOMPLETNÍ + dataset bez datových chyb
**2742 záznamů / 126 poskytovatelů; 718 otevřených grantů (26 %); integrita ověřena (0 bad_amount ·
0 bad_date · 0 open<deadline · 0 status_mismatch · 0 dup ids).** Včetně **EU Funding & Tenders Portal
(P6) = +341 OTEVŘENÝCH centrálních EU výzev** (Horizon/Erasmus+/Creative Europe/Digital/CEF/LIFE/CERV/
EDF…) přes SEDIA API, odemčeno lokálním Playwrightem (chrome) → HTTP replay BEZ Apify.

Co zbývá, NARÁŽÍ NA GENUINE BLOCKER nebo by ZHORŠILO kvalitu:

| Zbývající zdroj | Stav / proč ne |
|---|---|
| **EU F&T Portal (P6)** | ✅ **HOTOVO** — 341 otevřených výzev (SEDIA API, Playwright→HTTP replay) |
| **Úřad vlády ČR NNO** | ✅ **HOTOVO** — 7 národních programů (seed-driven, deadline z prózy) |
| OP TAK / dotaceeu.cz centrál | ASP.NET **WebForms** (postback listing) → Apify/viewstate; dedup riziko |
| OPD (opd.cz) | výzva-detail = JS, statické HTML jen nav; alokace jen **program-level** (4,9 mld EUR celá OPD) → jako IROP nejednoznačné. NEúčelné. |
| OPZ+ (esfcr.cz) | Liferay listing bez čisté tabulky → bespoke render-parse; překryv s MPSV (máme 8) |
| SZIF (PRV/SZP) | **WAF** (ConnectionReset) → jen přes proxy/Apify |
| Interreg ×5, Visegrad | ne-WP **bespoke** (per-site HTML/próza+PDF), roztříštěné |
| Nadace (zbylé velké) | převážně **ne-WP** (Yii/custom-PHP) → bespoke per-web, většinou jen `foundation_mission` |
| Města (ČB, Zlín, Šumperk, Třebíč) | **OVĚŘENO Playwrightem 2026-06-30: programy NEjsou čistě harvestovatelné** — schované za víceúrovňovou navigací („Programy → výzvy → sub-stránka → detail") + PDF; render vrátil ~0 reálných programů. Bez hluboké per-město bespoke práce s téměř nulovým čistým výnosem. |

**Doktrína kvality (proč nedoháníme nuly):** `amount=null` a `status=unknown` jsou VĚTŠINOU SPRÁVNÉ —
částky bývají jen v zadávací dokumentaci (PDF) a katalogové programy nemají jeden deadline. Vynutit je
= halucinace nebo špatná čísla (ověřeno: IROP alokace na stránce je nejednoznačná / min-velikost-projektu
vs alokace). **Raději poctivý null než špatné číslo.** Enrichment amount z PDF NEbezpečný → neprovádíme.

## Kvalitní pass 2026-06-29 (dedup + čištění)
Po expanzi proběhl quality pass (fix_dataset.py): **2491 → 2412** (−79). Odstraněno:
- **−74 re-snapshotů** (A3 dedup): stejný `(source, titul, deadline)` = redundantní katalog harvestovaný
  opakovaně přes ročníky (DSW2/QCM: Ústí n.L. 35, Hodonín 19, Mělník 11…). Necháváme NEJBOHATŠÍ kopii
  (s částkou/popisem). Záznamy s ODLIŠNÝM deadlinem (různé ročníky výzvy) zůstávají.
- **−1 stray** (DROP_STRAY): ČMZRB / Národní rozvojová banka (úvěry/záruky, ne dotace) omylem jako mise pod mkcr.
- **−4 test junk** (DROP_SOURCES): `tacr.dsw2.otevrenamesta.cz` = demo instance (titulky kódy „PP1/TK01",
  deadliny 2021); reálné TA ČR máme pod zdrojem `tacr`.
- Výsledek: **0 reziduálních exact dupů**, unknown 738 → 665, 0 mojibake (data čistá UTF-8), 0 broken titulků
  (prázdný `title` u foundation_mission je správně — mise nesou `name`).
- Pozn.: zbývající `amount=null` (≈75 %) a `status=unknown` (665) jsou VĚTŠINOU správné — částky bývají jen
  v PDF (zadávací dokumentace) a katalogové programy nemají jeden deadline (jsou opakující se). NEHALUCINUJEME.

## Co přibylo v session 2026-06-29 (přehled)
Od 2256 → **2412 záznamů** (po dedupu), 119 → **125 poskytovatelů**. Přidáno:
- **NSA** (Národní sportovní agentura, `nsa.gov.cz`) — 21 sportovních výzev (`statni_agentura`).
- **Nadace OSF** (`osf.cz`) — 1 `foundation_mission` (nemá otevřenou výzvu; donorské fondy/programy).
- **EU operační programy (P3) — nově 213 výzev:** **OPŽP** (`opzp.cz`, 107) · **OP ST** (`opst.cz`, 98) ·
  **OP JAK** (`opjak.cz`, 8). Vše `zdroj=eu_fondy`, `typ=ministerstvo`, status v kódu.
- **Infrastruktura:** reprodukční fix (vrstva-2 extraktory `data/_<src>_extract.py` nově TRACKOVANÉ);
  housekeeping dokumentace (README/PAGES_DESC/coverage_expansion/phase2 sjednoceny, smazán stale handoff).
- **Reuse asset:** `scripts/opzp.py:harvest_op(base,host,out)` = sdílený harvester „EU OP na WP s CPT `call`".

**Genuine blocker (kde session skončila):** WP-reuse na EU OP vyčerpán. Zbylé OP TAK/OPZ+/OPD/NPO = ne-WP;
centrál `dotaceeu.cz` = ASP.NET WebForms (postback listing → Apify/viewstate) + dedup riziko; Interreg ×5 a
Visegrad = ne-WP bespoke. Další postup chce Apify/WebForms NEBO P6 EU F&T API (dedikovaná session — viz
níže „Recon EU OP + Interreg").

## Aktuální stav datasetu

| metrika | hodnota |
|---|---|
| záznamů celkem | **2749** |
| z toho granty / foundation_mission | 2724 / 25 |
| poskytovatelů | **127** |
| status grantů | **~718 open** · ~50 announced · ~1301 closed · ~655 unknown (počítá se klientsky k dnešku) |
| typy poskytovatelů | samosprava_kraj 843 · samosprava_obec 718 · ministerstvo 561 · **evropska_komise 341** · nadacni_fond 63 · nadace 57 · statni_fond 47 · statni_agentura 44 · firemni_nadace 42 · zahranicni_fond 26 |

Status se počítá KLIENTSKY k reálnému dnešku (build_app.py:computeStatus) → „open" číslo
přirozeně klesá jak deadliny míjejí; není to ztráta dat.

## Hotovo (stručně)

- **Pipeline**: harvest (vrstva 1) → build_extract_input → vrstva 2 (deterministická
  `data/_<src>_extract.py` nebo LLM workflow) → ingest_rich → consolidate → fix_dataset → build_app.
- **Samospráva**: 14 krajů + ~30 měst (vismo, DSW2/otevřená města, bespoke per-web harvestery —
  všechny registrované v `routing.yaml` sekce `sources`).
- **Ministerstva**: MŠMT (msmt), MV (mv), MŽP (mzp), MZe/eAGRI (eagri), MZČR (mzcr), MKČR (mkcr), **MPSV (mpsv)**, **MPO (mpo, 9 národních programů)**, **MMR (mmr, 9 národních dotací)**.
- **Státní fondy**: **SFŽP (sfzp, 19)**, SFA – Státní fond audiovize (sfa, 8), **SFPI/SFRB (sfpi, 6)**, **SFDI (sfdi, 8)**, **SFK – Státní fond kultury (sfk, 1)**.
- **Státní agentury** (typ `statni_agentura`, 44 záznamů): **GA ČR (gacr, 14)**, **TA ČR (tacr, 9)**, **NSA (nsa, 21)**.
- **EU/centrální**: IROP (irop.gov.cz), dotaceEU.
- **Nadace/fondy**: ~17 (nadacevia, nadacecez, nadaceokd, agrofert, albert, sirius, leontinka,
  partnerstvi, nadace_adra, veronica, hlavka, vinarskyfond, kellner, vdv, fondbudoucnosti,
  fondpaliativnipece, socialninadacnifond, …).
- **Deploy & data API**: `docs/grants_app.html` (appka, deploy přes `pages.yml` → gh-pages) +
  `docs/opportunities.json` (veřejný kurátorovaný export pro produkt; `scripts/export_api.py`).
  Tail po každém běhu: `build_app` → cp do `docs/` · `export_api` → `docs/opportunities.json` · commit.
  Stabilní Pages URL: `.../branches/<branch>/opportunities.json`. **POZOR: NEMERGOVAT do main bez pokynu.**

## Vize: co musí mít konkurenceschopný český grantový portál

Aby dataset pokrýval VŠECHNY relevantní zdroje, kam může český žadatel (obec, NNO, firma, výzkumník,
fyzická osoba) sáhnout, potřebuje 7 vrstev. Hrubý odhad pokrytí dnes vs. cíl:

| Vrstva | Stav | Hlavní mezery |
|---|---|---|
| 1. Samospráva (14 krajů + města) | ~80 % | pod-harvestované kraje + chybějící města (P5) |
| 2. Ministerstva (národní dotace) | ~70 % | MD, MF, MO, MSp, MZV (P2) |
| 3. Státní fondy | **100 %** | — (P1 hotovo) |
| 4. Státní agentury | ~70 % | GA ČR + **TAČR + NSA hotovo**; chybí SZIF, Úřad vlády, NRB (P2b) |
| 5. EU operační programy (řízené z ČR) | ~40 % | **OPŽP (107) + OP ST (98) + OP JAK (8) hotovo**; chybí OP TAK/OPZ+/OPD/NPO/PRV/Interreg (P3) |
| 6. EU centrální (Brusel) | **~85 %** | **HOTOVO: 341 otevřených výzev z EU F&T Portal** (Horizon/Erasmus+/Creative Europe/Digital/CEF/LIFE/CERV/EDF). Chybí jen EuropeAid (externí akce, ne CZ granty) |
| 7. Nadace + mezinárodní donoři | ~40 % | 17→40+ nadací (P4); Norské/EHP, Visegrád, Swiss (P7) |

## Zbývá — v pořadí priority

### P1 — Státní fondy (vysoký objem, jasná struktura)
- [x] **SFRB / SFPI — Státní fond podpory investic** (`sfpi.cz`) — HOTOVO: 6 programů bydlení
      (Úsporné BD, Živel 3, Dostupné nájemní bydlení, BD bez bariér, Nájemní bydlení, Regenerace sídlišť).
      ⚠ Část programů (Program 150/600, Panel 2013+, Zateplování, Vlastní bydlení, Nájemní byty,
      Výstavba pro obce) je **page-builder** — tělo přes WP REST prázdné; doplnit přes front-end HTML
      parsing, jsou to ale převážně čisté úvěry (nižší priorita pro grantový dataset).
- [x] **SFDI — Státní fond dopravní infrastruktury** (`sfdi.gov.cz`) — HOTOVO: 8 příspěvkových programů
      (cyklostezky, bezbariérové chodníky, bezpečnost silnic II/III, křížení komunikací, zabezpečení letišť,
      multimodální překladiště, jednotky ETCS, nové technologie). Pozn.: programy jsou přes WP REST 401 →
      harvest front-end HTML. Cyklo/chodníky jsou „mezi ročníky" (Termín „-") → status unknown.
- [x] **Státní fond kultury ČR** (SFK) — HOTOVO: 1 záznam (dotace SFK 2026, 3 výzvy/rok přes DP MK).
      ⚠ Dedikované domény (sfkultury.cz, fondkultury.cz) MRTVÉ → fond žije na mk.gov.cz/statni-fond-kultury
      (ASP.NET WebForms – NEstrip `<form>`!). Tematické okruhy nejsou na webu (jen termíny) → z titulu fondu.
      Možné prohloubení: SFK Kinematografie je samostatně = SFA (už máme), ostatní okruhy jdou přes 1 výzvu.

**P1 hotovo.** P2 rozpracováno (MPO, MMR hotovo). Další: **MD — Ministerstvo dopravy.**

### P2 — Ministerstva (zbývající)
- [x] **MPO — Ministerstvo průmyslu a obchodu** (`mpo.gov.cz`) — HOTOVO: 9 národních programů (TREND, TRIO,
      TWIST, The Country for the Future, Technologická inkubace, Obchůdek 2021+, Czech Rise Up 3.0,
      Strategické investice/NZIA, brownfieldy). ⚠ Konkrétní lhůty výzev jsou v aktualitách (ne na landing)
      → 5/9 status unknown (program-level). **OP TAK / OP PIK (EU) ZÁMĚRNĚ MIMO → P3.** grant flag opraven
      (byl chybně False).
- [x] **MMR — Ministerstvo pro místní rozvoj** (`mmr.gov.cz`) — HOTOVO: 9 národních dotací (PORR, Obnova
      německých hrobů, euroregiony, bezbariérové obce, Pevnostní města, podpora výkonů stavebních úřadů,
      cestovní ruch – infrastruktura + DMO, NNO 2026). ⚠ MIMO: IROP/OP/EU (P3), kategorie „Podpora bydlení"
      (=SFPI, máme), administrativní/historické položky. Lhůty často jen ve Výzva PDF → 6/9 unknown.
- [~] **MD — Ministerstvo dopravy** (`mdcr.cz`) — **PROVĚŘENO 2026-06-28: ŽÁDNÉ přímé národní dotace.**
      Web (Kentico) nemá sekci Dotace/Granty/Programy; jediné „Programy" jsou CEF (EU, P6) a certifikované
      metodiky (ne granty). Dopravní granty jdou přes **SFDI (máme)** a **EU OPD/CEF (P3/P6)**; BESIP dělá
      kampaně, ne externí výzvy; příspěvek na dopravní obslužnost = transfer krajům, ne soutěžní dotace.
      → NEfabrikuji záznamy. `platform_map` grant=False je správně. Případně sledovat ad-hoc výzvy MD.
- [ ] **MF — Ministerstvo financí** (`mfcr.cz`) — spíše finanční vztahy s rozpočty obcí než klasické dotace;
      ověřit objem (pravděpodobně podobně tenké jako MD). **← ZVÁŽIT vs. vyšší hodnota P2b (TAČR/NSA) / P7 (eeagrants).**
- [ ] **MO — Ministerstvo obrany** (péče o válečné hroby, spolková činnost, branná výchova).
- [ ] **MSp — Ministerstvo spravedlnosti** (prevence kriminality, probace, oběti TČ) — nižší priorita.
- [ ] **MZV — Ministerstvo zahraničních věcí** (zahraniční rozvojová spolupráce ČRA, transformační spolupráce, krajané) — nižší priorita.

### P2b — Státní agentury a další ústřední poskytovatelé (VYSOKÁ priorita, velké objemy)
- [x] **TAČR — Technologická agentura ČR** (`tacr.gov.cz`) — HOTOVO: 9 veřejných soutěží aktuálního cyklu
      národních programů (PRODEF, SIGMA ×5 dílčí cíle, DOPRAVA 2030, Prostředí pro život 2, THÉTA 2);
      3 open / 6 closed, alokace 10 mil–5,46 mld Kč. WP CPT `call`+`programme`; strukturované info (Soutěžní
      lhůta/Alokace) jen ve front-end HTML → harvest HTML, program z URL. typ=statni_agentura.
      ⚠ MIMO: mezinárodní partnerství (Eurostars/CET/DUT/QuantERA — jiná struktura, P6/P7); TREND 13. VS
      „v přípravě/odložena" → vynechána. Při dalším cyklu re-harvest (--since posune okno).
- [x] **NSA — Národní sportovní agentura** (`agenturasport.cz` → `nsa.gov.cz`) — HOTOVO: 21 výzev cyklu 2026
      (neinvestiční: Můj klub, sportovní organizace olympijského/paralympijského hnutí, zastřešující/svazové
      organizace, UNISPORT, významné akce, reprezentace, parasport/handicap; investiční: Regiony pod/nad 10 mil,
      Standardizovaná infrastruktura, obnova po povodních 2024). 2 open / 19 closed (cyklus 2026 většinou uzavřen
      do led/úno 2026). Alokace 110 mil–1,7 mld Kč; vše s deadline i částkou. typ=statni_agentura, zdroj=narodni_rozpocet.
      WP+Elementor; výzvy = pages `/dotace/<slug>/`, `content.rendered` STAČÍ (strukturní blok DATUM VYHLÁŠENÍ /
      ZAHÁJENÍ+UKONČENÍ PŘÍJMU ŽÁDOSTÍ / ALOKACE). ⚠ batch-fetch content přes `include=` (22 sekvenčních fetchů přes
      WAF/proxy je extrémně pomalé). Výzva 19/2026 (Standardizovaná – výstavba) ZRUŠENÁ → extraktor ji skipuje (detekce
      „zrušen"). Výzva 9/2026 není publikována jako page (vynechána). Při dalším ročníku re-harvest (`--year`). **← HOTOVO.**
- [ ] **SZIF — Státní zemědělský intervenční fond** (`szif.cz`) — **CHYBÍ**: Program rozvoje venkova (PRV/SZP),
      národní dotace v zemědělství, lesnictví, potravinářství. (Souvisí s P3 – PRV.)
- [ ] **Úřad vlády ČR** (`vlada.cz`, Rada vlády pro NNO) — dotace pro NNO: lidská práva, rovné příležitosti
      žen a mužů, protidrogová politika, romská menšina, prevence korupce.
- [ ] **NRB — Národní rozvojová banka** (`nrb.cz`, dříve ČMZRB) — úvěry/záruky pro MSP (Expanze, INOSTART,
      NÚE – Nová úspora energie); spíše finanční nástroje než dotace, ověřit zařazení.

### P3 — EU operační programy (řízené z ČR; velký objem, MS2021+/ISKP/esfcr)
- [ ] **OP TAK** (MPO) — podnikání a konkurenceschopnost (Technologie, Inovace, Úspory energie, Aplikace…).
- [x] **OPŽP — OP Životní prostředí 2021–2027** (`opzp.cz`) — HOTOVO: **107 výzev** (12 open / 2 announced /
      93 closed). WP CPT `call` (121, z toho 14 AOPK sub-výzev jiné šablony skip) → discovery REST; STRUKTURNÍ
      blok (Stav · Druh výzvy · Podání žádosti od-do · Alokace) jen ve FRONT-END HTML (jako tacr) → harvest HTML,
      kotva breadcrumb „Detail výzvy". Oblast ze Specifického cíle 1.x (energetické úspory / OZE / adaptace na
      klima / voda / odpady / příroda). Vše s open_from+deadline+alokací, citace exact-grounded. zdroj=eu_fondy,
      typ=ministerstvo (řídící orgán MŽP). ⚠ Při dalších výzvách re-harvest (CPT `call` se rozšiřuje).
- [ ] **OPZ+** — částečně přes MPSV (8 výzev 31_xx); doplnit zbytek z `esfcr.cz`.
- [x] **OP JAK — OP Jan Amos Komenský 2021–2027** (`opjak.cz`) — HOTOVO: **8 aktuálních výzev** (vše open):
      MSCA Fellowships CZ, Teaming-CZ III, Smart Akcelerátor+ II, Open Science III, Akční plánování MAP II,
      Poradím se s AI, Technická pomoc ERDF/ESF+. Alokace 300 mil–2 mld Kč. WP, ale výzvy NEjsou v REST
      (privátní CPT) → harvest přes listing `/vyzvy/` (jen aktuální/otevřené) + front-end detail; datum
      ČESKÁ jména měsíců (konec rozpětí = deadline příjmu, potvrzeno countdownem). zdroj=eu_fondy, typ=ministerstvo.
      ⚠ Listing ukazuje jen otevřené — uzavřené historické výzvy nejsou veřejně listované (re-harvest pro nové).
- [x] **OP ST — OP Spravedlivá transformace 2021–2027** (`opst.cz`) — HOTOVO: **98 výzev** (13 open / 85 closed).
      TÁŽE WP platforma jako OPŽP (CPT `call`, front-end blok) → **REUSE `scripts/opzp.py:harvest_op`** (thin
      `scripts/opst.py` wrapper). Extraktor liší oblast (transformace) + REGION (kraj z názvu: Karlovarský/
      Ústecký/Moravskoslezský — 3 uhelné regiony). zdroj=eu_fondy, typ=ministerstvo (řídící orgán MŽP).
      ⚠ **Pattern „EU OP na WP s CPT `call`" = sdílený `harvest_op`** — aplikovatelný na další takové OP weby
      (opjak.cz = WP ale BEZ call CPT; opd.cz/esfcr.cz/agentura-api = ne-WP → jiný přístup).
- [ ] **OP Doprava (OPD)** + **OP Technická pomoc (OPTP)** + **OP Rybářství**.
- [ ] **NPO — Národní plán obnovy** (průřezově napříč resorty; portál `narodniplanobnovy.cz`).
- [ ] **Program rozvoje venkova / SZP** (SZIF) — viz P2b.
- [ ] **Interreg** (přeshraniční): Česko–Polsko, Sasko, Bavorsko, Rakousko, Slovensko + Interreg Europe /
      Central Europe / Danube.
- ⚠ Pozor: běží na MS2021+/ISKP21+/esfcr.cz — zkus STRUKTURU PŘED PRÓZOU (XHR/JSON endpoint výzev) než
  harvest HTML; ověř award-DB ≠ otevřené výzvy. Centrální zdroj výzev = `dotaceeu.cz` (máme jen 13 záznamů).

### P4 — Nadace: rozšířit ~17 → 40+
Máme ~17 (via, ČEZ, OKD, Agrofert, Albert, Sirius, Leontinka, Partnerství, ADRA, Veronica, Hlávkova,
Kellner, VDV, Č-N fond budoucnosti, fond paliativní péče, sociální nadační fond, Naše dítě, Krása pomoci,
Konto Bariéry…), ale několik je **podváženo** (ČEZ 16, Sirius 1, Terezy Maxové 1, Konto Bariéry 1) nebo jen
host bez sklizně (NROS, O2, Vodafone).
- [x] **Nadace OSF (Open Society Fund Praha)** (`osf.cz`) — HOTOVO: 1 `foundation_mission` (nadace).
      WP+Elementor REST. K 2026-06 BEZ otevřené žadatelské výzvy (Stronger Roots 2026–2027 už rozdělen
      11/2025; Fond pro moderní stát / Generace OSF / Daniela Anýže / Active Citizens Fund = donorské fondy,
      ne applicant-calls) → správná reprezentace = mise (jako NROS/VDV/O2). `scripts/osf.py` je FUTURE-PROOF:
      discoveruje slug „…vyzva…" aktuálního roku (--year), neuzavřené → re-harvest zachytí novou výzvu.
- [ ] **Velcí chybějící grantmakeři**: ~~Nadace OSF~~ ✓ · Nadace Abakus (dříve Avast) ·
      Nadační fond Neuron (věda) · Nadace Karla Janečka · Nadace Komerční banky Jistota · Nadace ČSOB ·
      Nadace České spořitelny (nadacecs 2 – podvážená) · Nadace Veolia · Nadace J&T · Nadace Tipsport ·
      Nadace Proměny Karla Komárka · Nadace Bakala · Nadace AGEL · Nadace Český literární fond ·
      Nadace Experientia · Nadace Vodafone / O2 (reálná sklizeň, ne jen host).
- [ ] **Komunitní nadace** (regionální): Ústecká KN, Jihočeská KN, KN Blanicko-otavská, KN Euroregionu Labe…
- [ ] Postup: většinou WP/bespoke, 1 web = 1 parser (vzor `scripts/nadacevia.py`, `albert.py`).

### P5 — Pod-harvestované kraje + chybějící města
Kraje máme všechny (14), ale 4 jsou „mělké" a chybí v nich statutární/okresní města:
- [ ] **Jihočeský** (`kraj-jihocesky.cz` 7) — chybí **České Budějovice**, Písek, Strakonice, J. Hradec, Č. Krumlov. (Tábor máme.)
- [ ] **Olomoucký** (`olkraj.cz` 10; Olomouc/Přerov/Prostějov máme) — chybí Šumperk, Hranice, Jeseník, Zábřeh.
- [ ] **Zlínský** (`zlinskykraj.cz` 10; Kroměříž máme) — chybí **Zlín (město)**, Uherské Hradiště, Vsetín, Val. Meziříčí.
- [ ] **Vysočina** (`fondvysociny.cz` 14, Jihlava 11) — Fond Vysočiny má desítky FV programů/rok; chybí Třebíč,
      Havl. Brod, Žďár n. S., Pelhřimov.
- [x] **Bonus HOTOVO (2026-06-29): facet `region.kraj` doplněn.** `fix_dataset.py` sekce D: samosprávě se
  kraj odvodí z hostu (naučeno majoritou + ruční override pro all-null hosty), národním poskytovatelům se
  nastaví `celostatni=true`. Výsledek: 1667 záznamů s konkrétním krajem · 530 celostátních · 0 „neuvedeno".
  Filtr „dle kraje" v produktu teď funguje. (Zbývá doplnit chybějící MĚSTA výše — to je o pokrytí, ne o facetu.)

### P6 — Evropská komise / centrálně řízené programy (Brusel) — ZCELA CHYBÍ, vysoká hodnota
Pro české žadatele (univerzity, firmy, NNO, města, umělci) klíčové; centrální zdroj = **EU Funding & Tenders
Portal** (`ec.europa.eu/info/funding-tenders`). Strukturovaný (REST/JSON API výzev) → STRUKTURA PŘED PRÓZOU.
- [ ] **Horizon Europe** (věda a výzkum, ERC, MSCA, klastry).
- [ ] **Erasmus+** (vzdělávání, mládež, sport).
- [ ] **Kreativní Evropa / Creative Europe** (kultura, audiovize – MEDIA).
- [ ] **LIFE** (životní prostředí, klima).
- [ ] **CERV** (Citizens, Equality, Rights and Values – občanská společnost, rovnost, hodnoty).
- [ ] **EU4Health** (zdraví) · **Digital Europe (DIGITAL)** · **CEF** (Connecting Europe – doprava/energie/digital) ·
      **Single Market Programme (COSME-nástupce)** · **European Solidarity Corps** · **Innovation Fund** ·
      **Just Transition (JTF)** · **URBACT / ESPON** (města/územní).
- ⚠ Filtr: brát jen výzvy s relevancí pro CZ žadatele (open calls, ne tendry); pozor na objem (portál má tisíce).

### P7 — Mezinárodní donoři a bilaterální fondy v ČR
- [x] **EHP a Norské fondy** (`eeagrants.cz`) — HOTOVO: 26 výzev období 2014–2021 (NKM = Ministerstvo financí),
      napříč programy (Lidská práva, Kultura, Zdraví, Životní prostředí, Spravedlnost, Řádná správa…).
      typ_poskytovatele=**zahranicni_fond** (nový typ), zdroj=`ehp_norsko`, celostátní, vše closed (období ukončeno).
      Vrstva 2 vyčistila JS/nav z těla harvestu; deadline parsován z prózy + year-end fallback z URL.
      ⚠ Až bude vyhlášeno nové období 2021–2028, re-harvest pro čerstvé otevřené výzvy.
- [ ] **Mezinárodní visegrádský fond (IVF)** (`visegradfund.org`) — V4 granty (kultura, vzdělávání, výzkum, mládež).
- [ ] **Fondy švýcarsko-české spolupráce** (Swiss-Czech Cooperation Programme, 2. období).
- [x] **Česko-německý fond budoucnosti** (fondbudoucnosti, 36) — máme.
- [ ] Další: **Visegrad+**, **International Visegrad Fund scholarships**, programy velvyslanectví (US Embassy
      small grants, atd.) — nižší priorita.

## Známé problémy / vlajky pro příští sessions

0. **[VYŘEŠENO 2026-06-29] eeagrants (Norské/EHP fondy) ingestováno** → 26 výzev (zahranicni_fond,
   ehp_norsko, vše closed). Viz P7.

1. **723 grantů má status=unknown** — chybí parsovatelný deadline (hodně DSW2 „programů" bez lhůty
   + část OPZ+/historických výzev). Zlepšení = lepší extrakce „datum ukončení příjmu žádostí".
2. **amount=null** je časté u výzkumných/úvěrových programů (GA ČR, část SFŽP) — konkrétní strop bývá
   jen v Zadávací dokumentaci/PDF, ne v oznámení. NEHALUCINOVAT — null je správně.
3. **[VYŘEŠENO 2026-06-29 housekeeping]** `README.md` + `docs/PAGES_DESC.txt` přepsány na aktuální počty
   (~2280 / 122, větev coverage-expansion-next) a opraveny staré `extract/` cesty → `scripts/`.
   Pozn.: README „Fáze 5" stále konceptuálně mluví o `data/opportunities.jsonl` (LLM-workflow cesta);
   živý produkční dataset je `data/opportunities_v2.jsonl` (deterministická ingest_rich cesta). Operační
   pravda je v `CLAUDE.md` + `docs/SESSION_PLAYBOOK.md` (oba aktuální).
4. **Data jsou gitignored** — fresh clone nemá `data/`; obnova = `scripts/unpack_data.sh` z `data_bundle/`
   nebo re-harvest. **[OPRAVENO 2026-06-29 housekeeping]** Per-source vrstva-2 extraktory
   `data/_<src>_extract.py` jsou nově TRACKOVANÉ (`.gitignore`: `/data/*` + `!/data/_*_extract.py`) —
   jsou to KÓD, ne data; dřív gitignored = fresh clone neuměl reprodukovat vrstvu 2. Harvester (`scripts/<src>.py`)
   + extraktor (`data/_<src>_extract.py`) jsou teď oba v gitu.
5. **pipeline.py = legacy stub** (`compute_status` natvrdo `date(2026,6,1)`) — NEpoužívat jako zdroj
   pravdy; kanonický status je `scripts/opportunities.py:compute_status`.
6. **Windows cp1250 konzole** — pipeline skripty (consolidate/fix_dataset/build_extract_input/routing)
   i nové harvestery (sfzp/gacr) mají `sys.stdout.reconfigure(utf-8)` guard. Každý NOVÝ harvester ho přidej.
7. **WP fulltext discovery vrací všechny ročníky** — u WP zdrojů (gacr) filtruj `--since` na aktuální
   roční kolo, jinak dataset zaplaví 6× tentýž program (viz `scripts/gacr.py`).

## Recon 2026-06-29 (úspora času příští session — co je čisté vs. zeď)
Proběhla sonda kandidátů; čisté WP-REST výhry (typ NSA) jsou z velké části vyčerpané. Zjištění:
- **osf.cz** = WP ✓ (HOTOVO, mise). **nadacetipsport.cz** = WP ✓ (bez grant-CPT — k prozkoumání, má-li výzvy).
- **WP NEjsou / blokují:** czechaid.cz (404), nadacevodafone.cz (404), nadaceagel.cz (404), nadacepromeny.cz
  (403), nadacecez.cz / nadaceokd.cz (Yii „CHttpException"), nadacejt.cz (statické HTML), abakus.cz (HTML,
  ne REST), nadaceneuron.cz / nadacekj.cz / nadacecsob.cz (RemoteDisconnected/reset).
- **vlada.gov.cz (Úřad vlády, NNO dotace)** = REÁLNÝ gap, ale ZEĎ pro rychlý harvest: custom PHP CMS,
  programy roztříštěné po radách (rovne-prilezitosti, vvozp, romske-komunity, protidrogova, lidska-prava…),
  NEkonzistentní URL (`/cz/ppov/…` i `/ppov/…`, časté 404), bez sitemap, search vrací 0, alokace jen v PDF,
  deadline v próze. Detaily = próza+PDF → vrstva 2 LLM. Chce dedikovanou session + mapování rad ručně.
- **szif.cz** = ConnectionReset (WAF) → potřeba jiný přístup. vlada/szif = vysoká hodnota, vysoké úsilí.
- **Doporučení dalšího pořadí:** (a) P6 **EU Funding & Tenders Portal** — STRUKTUROVANÉ JSON API výzev =
  nejlepší ROI (1 harvester → stovky programů, Horizon/Erasmus+/CERV/LIFE/Kreativní Evropa); (b) vlada.gov.cz
  jako dedikovaná próza+PDF session; (c) P5 chybějící města reuse `vismo.py`/`dsw2.py` (nulový nový kód).

### Recon EU OP + Interreg (2026-06-29, pokr.) — kde končí WP-reuse pattern
„EU OP na WP s CPT `call`" (`opzp.harvest_op`) cracknul OPŽP+OP ST; OP JAK měl jiný WP (listing /vyzvy/).
Zbylé OP/Interreg už do reuse NEpadají — **ZEĎ (vyžaduje Apify/WebForms/bespoke, ne rychlý harvest):**
- **OP TAK** (`agentura-api.org`) = ne-WP; **OPZ+** (`esfcr.cz`) = ne-WP; **OPD** (`opd.cz`) = ne-WP;
  **NPO** (`narodniplanobnovy.cz`) = ne-WP.
- **dotaceeu.cz** (centrální MMR portál, agreguje VŠECHNY OP po složkách `01-OP-TAK`/`03-OPZ+`/…) =
  **ASP.NET WebForms**: listing řádky jsou postback (0 statických href), stránkování přes `WebForm_DoPostBack`
  → potřeba **Apify postback** nebo viewstate emulace. Navíc DEDUP riziko (překryv s IROP/OPŽP/OPST/OPJAK,
  co už máme). POZOR: NEharvestovat naivně celé dotaceeu → duplicity.
- **Interreg** (at-cz.eu, by-cz.eu, sn-cz2027.eu, cz-pl.eu, sk-cz.eu) = všechny ne-WP, bespoke (per-site
  HTML parser, prózové výzvy). `comerto` vendor (at-cz/sn-cz) = 1 parser na 2, ale stále bespoke.
- **Visegrad Fund** (`visegradfund.org`, P7) = ne-WP, bespoke (malá konečná sada grantů → spíš mission+pár).
- **Tipsport** (`nadacetipsport.cz`) = WP ale bez grant-CPT (jen `portfolio`) → výzvy nestrukturované.
→ **Závěr:** P3 EU OP přes WP-reuse vyčerpáno (OPŽP+OPST+OPJAK = 213 záznamů). Další P3 (OP TAK/OPZ+/OPD)
  = Apify/WebForms session NEBO per-OP bespoke; P6 EU F&T API zůstává nejlepší strukturovaný ROI.
