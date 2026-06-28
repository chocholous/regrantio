# REMAINING.md — plán rozšiřování pokrytí

Živý plánovací dokument (verzovaný v gitu). Co je hotovo, co zbývá, v jakém pořadí.
Aktualizuj po každém přidaném zdroji. Recept na přidání zdroje viz `CLAUDE.md` +
`docs/coverage.md`; data žijí v gitignored `data/`.

> **Status k 2026-06-28.** Větev `coverage-expansion-next`.

## Aktuální stav datasetu

| metrika | hodnota |
|---|---|
| záznamů celkem | **2221** |
| z toho granty / foundation_mission | 2196 / 25 |
| poskytovatelů | **119** |
| status grantů | ~342 open · ~39 announced · ~1064 closed · ~724 unknown (počítá se klientsky k dnešku) |
| typy poskytovatelů | samosprava_kraj 844 · samosprava_obec 798 · ministerstvo 353 · nadacni_fond 63 · nadace 56 · statni_fond 51 · firemni_nadace 42 · statni_agentura 14 |

Status se počítá KLIENTSKY k reálnému dnešku (build_app.py:computeStatus) → „open" číslo
přirozeně klesá jak deadliny míjejí; není to ztráta dat.

## Hotovo (stručně)

- **Pipeline**: harvest (vrstva 1) → build_extract_input → vrstva 2 (deterministická
  `data/_<src>_extract.py` nebo LLM workflow) → ingest_rich → consolidate → fix_dataset → build_app.
- **Samospráva**: 14 krajů + ~30 měst (vismo, DSW2/otevřená města, bespoke per-web harvestery —
  všechny registrované v `routing.yaml` sekce `sources`).
- **Ministerstva**: MŠMT (msmt), MV (mv), MŽP (mzp), MZe/eAGRI (eagri), MZČR (mzcr), MKČR (mkcr), **MPSV (mpsv)**, **MPO (mpo, 9 národních programů)**, **MMR (mmr, 9 národních dotací)**.
- **Státní fondy**: **SFŽP (sfzp, 19)**, SFA – Státní fond audiovize (sfa, 8), **SFPI/SFRB (sfpi, 6)**, **SFDI (sfdi, 8)**, **SFK – Státní fond kultury (sfk, 1)**.
- **Agentury**: **GA ČR (gacr, 14)** — typ `statni_agentura`.
- **EU/centrální**: IROP (irop.gov.cz), dotaceEU.
- **Nadace/fondy**: ~17 (nadacevia, nadacecez, nadaceokd, agrofert, albert, sirius, leontinka,
  partnerstvi, nadace_adra, veronica, hlavka, vinarskyfond, kellner, vdv, fondbudoucnosti,
  fondpaliativnipece, socialninadacnifond, …).

## Vize: co musí mít konkurenceschopný český grantový portál

Aby dataset pokrýval VŠECHNY relevantní zdroje, kam může český žadatel (obec, NNO, firma, výzkumník,
fyzická osoba) sáhnout, potřebuje 7 vrstev. Hrubý odhad pokrytí dnes vs. cíl:

| Vrstva | Stav | Hlavní mezery |
|---|---|---|
| 1. Samospráva (14 krajů + města) | ~80 % | pod-harvestované kraje + chybějící města (P5) |
| 2. Ministerstva (národní dotace) | ~70 % | MD, MF, MO, MSp, MZV (P2) |
| 3. Státní fondy | **100 %** | — (P1 hotovo) |
| 4. Státní agentury | ~30 % | **TAČR, NSA (sport), SZIF, Úřad vlády** (P2!) |
| 5. EU operační programy (řízené z ČR) | ~10 % | OP TAK/OPŽP/OPZ+/OP JAK/OPD/NPO/PRV/Interreg (P3) |
| 6. EU centrální (Brusel) | **0 %** | Horizon, Erasmus+, Kreativní Evropa, LIFE, CERV… (P6) |
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
- [ ] **MD — Ministerstvo dopravy** (`mdcr.cz` / `md.gov.cz`). **← DALŠÍ.** (Pozn.: velkou část dopravy
      kryje SFDI, máme; MD má vlastní národní programy + bezpečnost provozu/BESIP.)
- [ ] **MF — Ministerstvo financí** (`mfcr.cz`) — spíše finanční vztahy s rozpočty obcí než klasické dotace; ověřit objem.
- [ ] **MO — Ministerstvo obrany** (péče o válečné hroby, spolková činnost, branná výchova).
- [ ] **MSp — Ministerstvo spravedlnosti** (prevence kriminality, probace, oběti TČ) — nižší priorita.
- [ ] **MZV — Ministerstvo zahraničních věcí** (zahraniční rozvojová spolupráce ČRA, transformační spolupráce, krajané) — nižší priorita.

### P2b — Státní agentury a další ústřední poskytovatelé (VYSOKÁ priorita, velké objemy)
- [ ] **TAČR — Technologická agentura ČR** (`tacr.cz`, `starfos.tacr.gov.cz`) — **CHYBÍ ÚPLNĚ, miliardy/rok**:
      programy SIGMA, TREND (TAČR ho administruje – my máme jen MPO landing), DOPRAVA 2030, THÉTA 2, ZÉTA,
      Národní centra kompetence, GAMA 2, Prostředí pro život, ÉTA, KAPPA, DELTA 2. Veřejné soutěže jako GA ČR.
- [ ] **NSA — Národní sportovní agentura** (`agenturasport.cz`) — **CHYBÍ, velký objem**: investiční i
      neinvestiční dotace na sport (Můj klub, Provoz a údržba, Movité investice, Standardizovaná infrastruktura).
- [ ] **SZIF — Státní zemědělský intervenční fond** (`szif.cz`) — **CHYBÍ**: Program rozvoje venkova (PRV/SZP),
      národní dotace v zemědělství, lesnictví, potravinářství. (Souvisí s P3 – PRV.)
- [ ] **Úřad vlády ČR** (`vlada.cz`, Rada vlády pro NNO) — dotace pro NNO: lidská práva, rovné příležitosti
      žen a mužů, protidrogová politika, romská menšina, prevence korupce.
- [ ] **NRB — Národní rozvojová banka** (`nrb.cz`, dříve ČMZRB) — úvěry/záruky pro MSP (Expanze, INOSTART,
      NÚE – Nová úspora energie); spíše finanční nástroje než dotace, ověřit zařazení.

### P3 — EU operační programy (řízené z ČR; velký objem, MS2021+/ISKP/esfcr)
- [ ] **OP TAK** (MPO) — podnikání a konkurenceschopnost (Technologie, Inovace, Úspory energie, Aplikace…).
- [ ] **OPŽP** — částečně přes SFŽP; doplnit přímé dotační výzvy.
- [ ] **OPZ+** — částečně přes MPSV (8 výzev 31_xx); doplnit zbytek z `esfcr.cz`.
- [ ] **OP JAK** (MŠMT) — výzkum, vývoj, vzdělávání.
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
- [ ] **Velcí chybějící grantmakeři**: Nadace OSF (Open Society Fund Praha) · Nadace Abakus (dříve Avast) ·
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
- ⚠ Bonus: facet `region.kraj` je u většiny záznamů **null** (570+) → filtr „dle kraje" v appce nefunguje
  pořádně; stojí za to doplnit geo-odvození kraje z `source` hostu (samospráva = znám kraj/obec).

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
- [ ] **EHP a Norské fondy** (`eeagrants.org` / `eeagrants.cz`) — **JIŽ SKLIZENO do `data/eeagrants.jsonl` (308 KB),
      ale NEINGESTOVÁNO** (0 záznamů v datasetu!). **Rychlá výhra**: vrstva 2 + ingest existujícího harvestu.
      Operátoři v ČR (NROS – Active Citizens Fund, MF – Norské fondy).
- [ ] **Mezinárodní visegrádský fond (IVF)** (`visegradfund.org`) — V4 granty (kultura, vzdělávání, výzkum, mládež).
- [ ] **Fondy švýcarsko-české spolupráce** (Swiss-Czech Cooperation Programme, 2. období).
- [x] **Česko-německý fond budoucnosti** (fondbudoucnosti, 36) — máme.
- [ ] Další: **Visegrad+**, **International Visegrad Fund scholarships**, programy velvyslanectví (US Embassy
      small grants, atd.) — nižší priorita.

## Známé problémy / vlajky pro příští sessions

0. **eeagrants (Norské/EHP fondy) sklizeno, ale NEingestováno** → `data/eeagrants.jsonl` (308 KB) má data,
   v datasetu 0 záznamů. Rychlá výhra (vrstva 2 + ingest). Viz P7.

1. **723 grantů má status=unknown** — chybí parsovatelný deadline (hodně DSW2 „programů" bez lhůty
   + část OPZ+/historických výzev). Zlepšení = lepší extrakce „datum ukončení příjmu žádostí".
2. **amount=null** je časté u výzkumných/úvěrových programů (GA ČR, část SFŽP) — konkrétní strop bývá
   jen v Zadávací dokumentaci/PDF, ne v oznámení. NEHALUCINOVAT — null je správně.
3. **Stale county mimo 4 hlavní konfigy**: `README.md` (l.13: „2129 oportunit") a `docs/PAGES_DESC.txt`
   („778 → 2129") nesou starý počet. Kosmetické; aktualizovat při příští velké revizi README.
4. **Data jsou gitignored** — fresh clone nemá `data/`; obnova = `scripts/unpack_data.sh` z `data_bundle/`
   nebo re-harvest. Extrakční skripty `data/_<src>_extract.py` jsou taky gitignored (konvence).
5. **pipeline.py = legacy stub** (`compute_status` natvrdo `date(2026,6,1)`) — NEpoužívat jako zdroj
   pravdy; kanonický status je `scripts/opportunities.py:compute_status`.
6. **Windows cp1250 konzole** — pipeline skripty (consolidate/fix_dataset/build_extract_input/routing)
   i nové harvestery (sfzp/gacr) mají `sys.stdout.reconfigure(utf-8)` guard. Každý NOVÝ harvester ho přidej.
7. **WP fulltext discovery vrací všechny ročníky** — u WP zdrojů (gacr) filtruj `--since` na aktuální
   roční kolo, jinak dataset zaplaví 6× tentýž program (viz `scripts/gacr.py`).
