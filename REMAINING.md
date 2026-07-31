# REMAINING.md — stav projektu + co zbývá

Živý plánovací dokument. **Aktuální stav, co je hotovo, co zbývá a proč.** JAK pracovat (zlatá pravidla,
recept na zdroj, pasti) = `docs/SESSION_PLAYBOOK.md` + `CLAUDE.md`. Data žijí v gitignored `data/`.

> **Status k 2026-07-31, větev `coverage-expansion-next`.** Full-refresh + rozšíření hotovo: dataset
> **3049 záznamů / 132 poskytovatelů** (z 2749/127), refresh je nově JEDEN příkaz
> (`scripts/refresh_run.py`), html-tier poprvé reálně refreshovatelný (upsert_v2), repo uklizené
> (`scripts/legacy/` karanténa). Produkční kontrakt beze změny (schema 1.1), CI zelené.

---

## 📊 Aktuální stav datasetu (live `data/opportunities_v2.jsonl`, k 2026-07-31)

| metrika | hodnota (změna proti 2026-06-30) |
|---|---|
| **záznamů celkem** | **3049** (3024 grantů + 25 foundation_mission) — bylo 2749 (+300) |
| **poskytovatelů** | **132** (+5) |
| status grantů (k 2026-07-31) | **672 open** (22 %) · 33 announced · 1649 closed · 670 unknown (22 %) |
| typ poskytovatele | ministerstvo 854 · samosprava_kraj 843 · samosprava_obec 723 · evropska_komise 341 · nadacni_fond 63 · nadace 57 · statni_agentura 53 · statni_fond 47 · firemni_nadace 42 · zahranicni_fond 26 |
| vyplněnost grantů | deadline 2354 (77 %) · **amount 777 (25 %, bylo 20 %)** |
| integrita | **0 dup id · 0 null id · 0 bad amount · 0 grant bez title · 0 bez url** — `validate_release` ✓ |

„Open" počet přirozeně klesá, jak deadliny míjejí (status se počítá klientsky k reálnému dnešku);
při přepočtu k 31. 7. se 74 červnových open zavřelo a nové zdroje/refresh přidaly ~120 aktuálních výzev.
`amount=null`/`status=unknown` zůstávají VĚTŠINOU správné (částky jen v PDF; katalogové programy bez
jedné lhůty) — **raději poctivý null než vymyšlené číslo**.

---

## ✅ Session 2026-07-31 — co se stalo

**Nové zdroje (+~320 záznamů):**
- **esfcr (OPZ+/OPZ, esfcr.cz)**: 233 výzev ze strukturovaných Liferay polí, **16 aktuálně open**,
  100% vyplněnost dat i alokací. LZZ archiv 2007–13 vědomě mimo dataset (v harvestu zůstává).
- **mk (MK ČR)**: 53 výzev z centrálního HTML listingu (OD/DO deterministicky z tabulek).
- **msmt**: plný BFS harvest (189 stránek) nahradil statický 7-záznamový batch → 14 záznamů,
  jen aktuální cyklus (`--since-year`).
- **czechaid (ČRA)**: 9 výzev (1 open — Etiopie, deadline 3. 9. 2026); ZIP přílohy vč. rozbalení.
- **hzs (HZS ČR)**: 4 standing programy (obce/NNO); jednorázové 2022 výzvy vědomě mimo (šum).
- **plone_ostrava**: 5 aktuálních programů městských obvodů (132 stránek balastu odfiltrováno).
- **grantovydiar.cz**: harvester HOTOVÝ a funkční, ale NEingestováno — veřejné id okno je 100 %
  closed (probe 192 záznamů / 0 open), čerstvé výzvy za loginem. Kandidát na placený přístup.

**Full refresh (obsahový, ne jen status):** gacr 14 · tacr 9 · sfzp 19→21 · opzp 107 · opst 98→101 ·
opjak 8 · osf · mk/msmt/esfcr/czechaid/hzs/plone nové. **nsa ODLOŽENO** — WAF škrtí stahování příloh
na ~1 soubor/4 min (červnový stav 21 záznamů zůstává jako poslední známý; viz blockery).

**Infrastruktura:**
- `scripts/refresh_run.py` — **JEDEN příkaz na refresh kolo** (`--tier structured|html`, `--sources`),
  provede harvest→input→extract→ingest→tail vč. `--min-ratio` pojistky. Ověřeno reálným během.
- `scripts/upsert_v2.py` — html-tier ingesty (kraj/dotis/kentico/fondvysociny) nově UPSERTUJÍ do v2
  (dřív append-only do v1 → ~1300 záznamů krajů/měst fakticky nešlo refreshovat). Obohacené záznamy
  se přepisují jen ve faktech (datumy/status/částky).
- Windows robustnost: UTF-8 guardy (76 skriptů), TLS přes `http_util` všude, MAX_PATH guard (ZIP).
- Konsolidace: +37 oblast variant, `EU dotace` marker se DROPuje (mapa→null), 129→78 variant.
- **`scripts/legacy/`** — karanténa 16 v1/jednorázových skriptů (viz tamní README).

---

## ✅ Pokrytí zdrojů — souhrn

- **Samospráva:** 14 krajů + ~30 měst + 18 ostravských obvodů (vismo, DSW2, bespoke, plone).
- **Ministerstva:** MŠMT (plný), MV, MŽP, MZe, MZČR, **MK (plný)**, MPSV, MPO, MMR, Úřad vlády, **HZS**.
- **Státní fondy (100 %):** SFŽP (21), SFA, SFPI, SFDI, SFK.
- **Agentury:** GA ČR (14), TA ČR (9), NSA (21), **CzechAid (9)**.
- **EU OP řízené z ČR:** OPŽP (107), OP ST (101), OP JAK (8), **OPZ+/OPZ (233)**, IROP (120), dotaceEU (13).
- **EU centrální:** EU F&T Portal 341 (Horizon/Erasmus+/LIFE/CERV/…).
- **Mezinárodní:** EHP/Norsko (26), Česko-německý fond budoucnosti (36).
- **Nadace/fondy:** ~17 (via, ČEZ, OKD, Agrofert, Albert, Sirius, Leontinka, ADRA, Hlávka, Kellner, VDV, OSF…).

---

## ⛔ Co zbývá — GENUINE BLOCKERY (stav 2026-07-31)

| Zdroj | Blocker |
|---|---|
| **NSA refresh** | WAF škrtí přílohy (~1/4 min) → refresh přes `refresh_run.py --sources nsa` pustit přes noc / z jiné sítě; data z 06/2026 zatím platná |
| OP TAK / `dotaceeu.cz` centrál | ASP.NET **WebForms** postback → Apify/viewstate (mosty připravené v `scripts/legacy/*apify*`); dedup riziko s IROP/OPŽP/OPST/OPZ+ |
| OPD / NPO / SZIF (PRV) | ne-WP; **SZIF = WAF** (ConnectionReset) → proxy/Apify |
| grantovydiar.cz aktuální výzvy | login-gate (placený účet svetneziskovek.cz) — harvester hotový, stačí session cookie |
| Interreg ×5, Visegrad | ne-WP bespoke, roztříštěné, malý výnos |
| Zbylé velké nadace (ČEZ/OKD detail, Abakus, Neuron, Vodafone…) | ne-WP bespoke per-web; většinou jen `foundation_mission` |
| Chybějící města (ČB, Zlín, Šumperk, Třebíč) | ověřeno Playwrightem: NEjsou čistě harvestovatelná |
| `h19_*` nadační batch | jednorázová v1 LLM cesta (REFRESH.md §6); nechat jako poslední stav, per-web parser až při reálné výzvě |

## 🎯 Priority příští coverage session (s rozpočtem na nástroje)
P3 OP TAK/dotaceeu (Apify/WebForms) · P2b SZIF (proxy) · P4 nadace 17→40+ · grantovydiar login.

---

## ⚑ Stálé pasti (pro každou session)

1. **Windows cp1250 konzole** — každý skript s non-ASCII printem má `sys.stdout.reconfigure(utf-8)` guard
   (od 2026-07-31 plošně). Pozor i v YAML/JSON: ASCII `"` uvnitř českého `„…"` rozbije parser.
2. **Status počítá KÓD, ne LLM** (`opportunities.py:compute_status`); ukládej RAW `open_from`/`deadline`.
3. **Deadline-regexy:** gap `[^\n]`, NIKDY `[^\n.]` (české zkratky tzn./č. mají tečku);
   „dotace NA OBDOBÍ od…do…" = realizace, NE lhůta podání (negativní guard).
4. **WP fulltext discovery vrací všechny ročníky** — filtruj `--since`/`--since-year` na aktuální kolo.
5. **`pipeline.py` = legacy stub** — nepoužívat; živý dataset = `opportunities_v2.jsonl`.
6. **Soubory otvírej s `encoding="utf-8"`** — default Windows open() píše cp1250 mojibake
   (kouslo grantovydiar harvest 2026-07-31).
7. **Data gitignored** — fresh clone nemá `data/`; obnova = `data_bundle/` nebo re-harvest.
8. **Nehalucinovat** — `amount=null`/`deadline=null` zůstává null; žádné fiktivní záznamy.
9. **Jen jeden proces smí psát `opportunities_v2.jsonl`** — ingesty pouštěj sekvenčně
   (`refresh_run.py` to garantuje; ad-hoc paralelní loops ne).
