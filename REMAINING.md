# REMAINING.md — plán rozšiřování pokrytí

Živý plánovací dokument (verzovaný v gitu). Co je hotovo, co zbývá, v jakém pořadí.
Aktualizuj po každém přidaném zdroji. Recept na přidání zdroje viz `CLAUDE.md` +
`docs/coverage.md`; data žijí v gitignored `data/`.

> **Status k 2026-06-28.** Větev `coverage-expansion-next`.

## Aktuální stav datasetu

| metrika | hodnota |
|---|---|
| záznamů celkem | **2202** |
| z toho granty / foundation_mission | 2177 / 25 |
| poskytovatelů | **116** |
| status grantů | ~342 open · ~39 announced · ~1064 closed · ~724 unknown (počítá se klientsky k dnešku) |
| typy poskytovatelů | samosprava_kraj 844 · samosprava_obec 798 · ministerstvo 335 · nadacni_fond 63 · nadace 56 · firemni_nadace 42 · statni_fond 36 · statni_agentura 14 |

Status se počítá KLIENTSKY k reálnému dnešku (build_app.py:computeStatus) → „open" číslo
přirozeně klesá jak deadliny míjejí; není to ztráta dat.

## Hotovo (stručně)

- **Pipeline**: harvest (vrstva 1) → build_extract_input → vrstva 2 (deterministická
  `data/_<src>_extract.py` nebo LLM workflow) → ingest_rich → consolidate → fix_dataset → build_app.
- **Samospráva**: 14 krajů + ~30 měst (vismo, DSW2/otevřená města, bespoke per-web harvestery —
  všechny registrované v `routing.yaml` sekce `sources`).
- **Ministerstva**: MŠMT (msmt), MV (mv), MŽP (mzp), MZe/eAGRI (eagri), MZČR (mzcr), MKČR (mkcr), **MPSV (mpsv)**.
- **Státní fondy**: **SFŽP (sfzp, 19)**, SFA – Státní fond audiovize (sfa, 8), **SFPI/SFRB (sfpi, 6)**, **SFDI (sfdi, 8)**.
- **Agentury**: **GA ČR (gacr, 14)** — typ `statni_agentura`.
- **EU/centrální**: IROP (irop.gov.cz), dotaceEU.
- **Nadace/fondy**: ~17 (nadacevia, nadacecez, nadaceokd, agrofert, albert, sirius, leontinka,
  partnerstvi, nadace_adra, veronica, hlavka, vinarskyfond, kellner, vdv, fondbudoucnosti,
  fondpaliativnipece, socialninadacnifond, …).

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
- [ ] **Státní fond kultury ČR** (spadá pod MK) — projektové dotace v kultuře. **← DALŠÍ.**

### P2 — Ministerstva (zbývající)
- [ ] **MPO — Ministerstvo průmyslu a obchodu** (`mpo.gov.cz`) — národní programy + OP TAK (viz P3).
- [ ] **MMR — Ministerstvo pro místní rozvoj** (`mmr.gov.cz`) — národní dotační programy (částečně IROP máme).
- [ ] **MD — Ministerstvo dopravy**.
- [ ] **MF — Ministerstvo financí**.

### P3 — EU operační programy (velký objem, strukturované systémy MS2021+/ISKP/esfcr)
- [ ] **OP TAK** (MPO) — podnikání a konkurenceschopnost.
- [ ] **OPŽP** — částečně pokryto přes SFŽP; doplnit přímé dotační výzvy.
- [ ] **OPZ+** — částečně pokryto přes MPSV (8 výzev 31_xx); doplnit zbytek z esfcr.cz.
- [ ] **OP JAK** (MŠMT) — vzdělávání, výzkum.
- [ ] **NPO — Národní plán obnovy** (průřezově napříč resorty).
- ⚠ Pozor: tyto běží na portálech MS2021+/ISKP21+/esfcr.cz — zkus STRUKTURU PŘED PRÓZOU
  (XHR/JSON endpoint výzev) než harvest HTML; ověř award-DB ≠ otevřené výzvy.

### P4 — Nadace: rozšířit ~17 → 40+
- [ ] Kandidáti k přidání: Nadace ČEZ (máme), Nadace OSF, Nadace Open Society Fund, Nadace Avast,
      Nadace Komerční banky Jistota, Nadace ČSOB, Nadace PPF, Nadace Charty 77 / Konto Bariéry (máme kontobariery),
      Nadace Vodafone (máme host), Nadace O2 (máme host), Nadace Karla Janečka, Nadace BLÍŽKSOBĚ,
      Nadace rozvoje občanské společnosti (NROS, máme host nros.cz), Nadace Taťány Kuchařové,
      Nadace Jistota, Výbor dobré vůle (vdv máme), Nadace Naše dítě (nasedite máme), atd.
- [ ] Postup: většinou WP/bespoke 1 web = 1 parser (vzor `scripts/nadacevia.py`, `albert.py`).

### P5 — Pod-harvestované kraje (prohloubit existující)
- [ ] **Jihočeský** (`kraj-jihocesky.cz`, nyní 7) — pravděpodobně víc dotačních programů.
- [ ] **Olomoucký** (`olkraj.cz`, nyní 10).
- [ ] **Zlínský** (`zlinskykraj.cz`, nyní 10).
- [ ] **Vysočina** (`fondvysociny.cz`, nyní 14) — Fond Vysočiny má desítky FV programů ročně.

## Známé problémy / vlajky pro příští sessions

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
