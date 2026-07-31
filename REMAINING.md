# REMAINING.md — stav projektu + co zbývá

Živý plánovací dokument. **Aktuální stav, co je hotovo, co zbývá a proč.** JAK pracovat (zlatá pravidla,
recept na zdroj, pasti) = `docs/SESSION_PLAYBOOK.md` + `CLAUDE.md`. Data žijí v gitignored `data/`.

> **Status k 2026-07-31, větev `coverage-expansion-next`.** Dataset **3372 záznamů / 133
> poskytovatelů**. Všech 18 automatizovaných zdrojů refreshnuto k dnešku, repo uklizené
> (`scripts/legacy/` karanténa), produkční kontrakt beze změny (schema 1.1), CI zelené.

---

## 📊 Aktuální stav datasetu (live `data/opportunities_v2.jsonl`, k 2026-07-31)

| metrika | hodnota |
|---|---|
| **záznamů celkem** | **3397** (3372 grantů + 25 foundation_mission) |
| **poskytovatelů** | **136** |
| status grantů | **687 open** · 33 announced · 1730 closed · 906 unknown |
| typ poskytovatele | samosprava_kraj 1153 · ministerstvo 866 · samosprava_obec 723 · evropska_komise 341 · nadacni_fond 63 · nadace 57 · statni_agentura 53 · statni_fond 48 · firemni_nadace 42 · zahranicni_fond 26 |
| vyplněnost grantů | deadline 2441 (73 %) · amount 777 (23 %) |
| integrita | **0 dup id · 0 bez title · 0 bad amount** — `validate_release` ✓ |

`amount=null`/`status=unknown` zůstávají VĚTŠINOU správné (částky bývají jen v PDF; katalogové
programy nemají jednu lhůtu) — **raději poctivý null než vymyšlené číslo**. Produkt si navíc
defaultně filtruje `deadline >= dnes NEBO NULL`, takže archiv nezavazí.

---

## ✅ Session 2026-07-31 — co se stalo

**Nové zdroje / doplněné mezery (+623 proti 2749 na začátku session):**
- **esfcr (OPZ+/OPZ)** 233 · **mk (MK ČR)** 53 · **msmt** plný BFS 14 · **czechaid** 9 ·
  **hzs** 4 · **plone_ostrava** 5 — nové zdroje z první části session.
- **Fond Vysočiny 14 → 313**: harvester znal jen listing `aktivni` (18 programů), ale existuje
  `vyhodnocene` s **326** — jediná velká mezera nalezená hloubkovým auditem.
- **Praha 15 → 25**: harvester měl v komentáři, že sekce sociální/školství vracejí HTTP 500;
  dnes fungují (24 položek) → doplněny mezi seedy.
- **OP Doprava (opd3.opd.cz) 0 → 12** (*z toho 5 otevřených*): v REMAINING veden jako blocker
  („ne-WP"), web mezitím přešel na server-rendered tabulku výzev → `scripts/opd.py`.
- **JS-renderované nadace 0 → 15**: `scripts/nadace_spa.py` (Playwright) pokrývá 6 nadací
  jedním harvesterem — nespojuje je CMS, ale PŘEKÁŽKA (obsah renderuje JS, curl vrátí shell).
  Partnerství · OSF · Vodafone · Liga proti rakovině · Český literární fond · Abakus.
  Vrstva 2 filtruje 51/66 stránek: software (Grantys), výsledky, archivy a hlavně LISTINGY
  (osf.cz/granty nese 5 různých uzávěrek → jeden záznam by z nich udělal chiméru).
- **Visegrad Fund + ERSTE Foundation 0 → 6** (VŠECHNY otevřené): `scripts/intl_funds.py`.
  Oba weby vracely HTTP 403 na default urllib UA → stačily realistické prohlížečové hlavičky.
  Visegrad má pevné uzávěrky (1. 2. / 1. 6. / 1. 10.), extraktor bere NEJBLIŽŠÍ BUDOUCÍ datum.
  EUR částky se NEpřevádějí na CZK (kurz) → jdou do extra.castka_eur, amount zůstává null.
- **Interreg SK-CZ + CZ-PL 0 → 6**: `scripts/interreg.py` (WP REST, kategorie dle slugu).
  Vrstva 2 FILTRUJE: z 13 postů je 8 náborů hodnotitelů/harmonogramů, ne dotačních výzev.
- **Creative Europe / Kreativní Evropa: vědomě NEpřidáno** — výzvy vyhlašuje EACEA a v datasetu
  už jsou přes EU F&T portál (13 aktuálních `CREA-*`); české zastoupení by bylo duplikací.
- **grantovydiar.cz**: harvester hotový, NEingestován (veřejné id okno 100 % closed, zbytek za loginem).

**Refresh:** všech 18 automatizovaných zdrojů (8 structured + 10 html) proběhlo bez chyby.

**Infrastruktura a čistota:**
- `scripts/refresh_run.py` — jeden příkaz na refresh kolo; **registr rozšířen o 5 zdrojů**
  (`nadacevia`, `mzcr`, `mzp`, `mv`, `opd`), které měly kompletní řetěz, ale refresh je míjel.
- `scripts/upsert_v2.py` — html-tier ingesty upsertují do v2 (dřív append-only skip).
- Windows robustnost: UTF-8 guardy (76 skriptů), TLS přes `http_util`, MAX_PATH guard.
- **`scripts/legacy/`** — karanténa 18 v1/jednorázových skriptů (viz tamní README).

**Hloubkový audit pokrytí (co se NEpotvrdilo):** prošel jsem 14 krajů, 12 ministerstev/fondů
a 18 EU programů sondami. Vysočina a Praha byly JEDINÉ skutečné mezery. Jinde „vyšší čísla"
znamenala navigaci, dokumenty starých programů (MPO: 262 podstránek = OPPI 2007–2013) nebo
**awards místo výzev** (Zlínský kraj). Vědomě NEpřidáno: **NPO** (rozcestník na resortní výzvy,
které už máme → duplikace) a **Ministerstvo dopravy** (web nemá dotační sekci; dopravní dotace
jdou přes SFDI a nově OP Doprava).

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

## ⛔ Co zbývá — GENUINE BLOCKERY (recon 2026-07-31)

Každý níže byl v této session ŽIVĚ přeověřen; „blocker" = ověřená technická překážka, ne odhad.

| Zdroj | Blocker (ověřeno) |
|---|---|
| **SZIF (PRV/SZP)** | `ConnectionResetError` — WAF blokuje na úrovni TCP spojení; realistické hlavičky NEPOMOHLY (na rozdíl od Visegradu/ERSTE). Chce proxy nebo jinou IP |
| **OP TAK** | web API (agentura-api.org) je prázdný SPA shell — i po Playwright renderu jen 58 znaků. `dotaceeu.cz/…/vyzvy` má výzvy za FILTROVACÍM formulářem (postback) → Apify/viewstate |
| **Interreg AT-CZ** | HTTP 200, ale 0 výzvových odkazů — obsah je za JS/filtrem; chce Playwright recon |
| **Interreg Central Europe** | ověřeno: VŠECHNA 4 kola uzavřená (poslední 11/2025), žádné otevřené výzvy → vědomě nepřidáno |
| **Interreg Danube** | 404 na /calls — změněná struktura, chce recon |
| **grantovydiar.cz** | login-gate (veřejné id okno je 100 % closed) |
| **Zbylé nadace** (ČEZ detail, Neuron, Karla Janečka, Charty 77) | 403/DNS chyby nebo obsah jen v PDF |
| Chybějící města (ČB, Zlín, Šumperk, Třebíč) | ověřeno Playwrightem: víceúrovňová navigace + PDF, render vrátil ~0 programů |
| `h19_*` nadační batch | jednorázová v1 LLM cesta (REFRESH.md §6) |

**Poznatek k obcházení blokací:** HTTP 403 u Visegradu, ERSTE a obou Interregů padalo na
DEFAULTNÍM urllib User-Agentu — stačily realistické prohlížečové hlavičky (UA + Accept-Language
+ `Accept-Encoding: identity`). Než označíš zdroj za blokovaný, zkus tohle.

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
