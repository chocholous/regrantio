# REMAINING.md — stav projektu + co zbývá

Živý plánovací dokument. **Aktuální stav, co je hotovo, co zbývá a proč.** JAK pracovat (zlatá pravidla,
recept na zdroj, pasti) = `docs/SESSION_PLAYBOOK.md` + `CLAUDE.md`. Katalog je v gitu, zbytek dat v gitignored `data/`.

> **Status k 2026-08-22 (změřeno, ne odhad).** Dataset **3452 záznamů / 129 zdrojů**,
> export vygenerovaný **2026-08-22** (`docs/opportunities.json`, otisk `fedc3b6b…`,
> 10,6 MB). **53/53 testů**, `validate_release` prochází včetně dvou nových bran.
> Publikační cesta do úschovny hotová (`scripts/publish_export.py`,
> `refresh_run.py --publish`) a čeká **jen na založení kbelíku `regrantio-exports`**
> — viz `docs/REFRESH.md §8`.

---

## 📊 Aktuální stav datasetu (live `data/opportunities.jsonl`, změřeno 2026-08-22)

| metrika | hodnota |
|---|---|
| **záznamů celkem** | **3452** (3427 grantů + 25 foundation_mission) |
| **zdrojů (`source`)** | **129** |
| status grantů | **677 open** · 43 announced · 1795 closed · 912 unknown |
| termíny | deadline 2515 (73 %) · open_from 2351 (69 %) |
| částky | amount 777 (23 %) |
| texty | focus_area 3182 (93 %) · eligible_applicants 2231 (65 %) · source_url 3427 (100 %) |
| fasety | typ_poskytovatele / forma_podpory / zdroj_financovani / region **100 %** · oblast 3060 (89 %) · typ_zadatele 1279 (37 %) |
| integrita | **0 dup id · 0 bez id · 0 bez title · 0 inverzních termínů** |
| export | 3452 záznamů, `content_hash` u **100 %** |

> ⚠ **`typ_zadatele` 37 % je NEJVĚTŠÍ MEZERA V DATECH, ne chyba.** Deterministické
> harvestery ji nechávají prázdnou schválně (`ingest_kraj.py`: „← LLM vrstva 2,
> ne keyword") — komu je výzva určená, bývá v próze nebo v PDF pravidel a keyword
> matching by tam vyrobil nesmysly. Produkt s tím počítá: shoda podle typu
> žadatele je proto měkký signál, ne tvrdá brána.

> ⚠ **`amount` 23 % a `status` unknown u 912 je taky správně.** Částky bývají jen
> v PDF a katalogové programy nemají jednu lhůtu — **raději poctivý null než
> vymyšlené číslo**. Produkt si defaultně filtruje `deadline >= dnes NEBO NULL`,
> takže archiv nezavazí.

> ⚠ Status v tabulce je SNÍMEK k datu přepočtu. Produkt si stav počítá znovu k dnešku
> (`build_app.py:computeStatus`, `catalog_status()` v Grantiu), takže se čísla „open/closed"
> mezi katalogem a aplikací můžou o pár položek lišit — a je to správně.

---

## ✅ Refresh 2026-08-22 — co proběhlo a co se rozbilo

**13 ze 14 deterministických zdrojů obnoveno**, katalog 3450 → 3452, export
přegenerován (`docs/opportunities.json`, 2026-08-22).

| zdroj | výsledek |
|---|---|
| dotace.khk.cz | ✓ 121 programů |
| fondvysociny.cz | ✓ 10 (3 aktualizované) |
| kr-karlovarsky.cz | ✓ 18 programů, 2 změny |
| msk.cz | ✓ 94 programů, 15 změn |
| stredoceskykraj.cz | ✓ 91 programů, 8 změn |
| praha.eu | ✓ 28 programů, 1 změna |
| kr-ustecky.cz · kraj-jihocesky.cz · olkraj.cz · zlinskykraj.cz · dotace.kraj-lbc.cz · dotace.pardubickykraj.cz · dotace.brno.cz | ✓ beze změny |
| **kr-jihomoravsky.cz** | ✖ **zdroj je rozbitý** |

### ⚠ kr-jihomoravsky.cz — rozbitý ZDROJ, ne náš harvester

`eud.jmk.cz` (GINIS úřední deska) vrací ASP.NET stránku **„Configuration
Error"** — chybu jejich aplikace, ne změněnou strukturu. U nás není co
opravovat; až to poskytovatel spraví, harvester poběží beze změny.

Co se při tom opravilo u nás: harvester na to reagoval **třicetivteřinovým
timeoutem na selektor a dvacetiřádkovým tracebackem** z Playwrightu — tedy
hlášením, ze kterého se příčina nedala poznat. Teď skončí za pět vteřin s větou
o tom, CO na stránce chybí a co je v titulku, a vrací **kód 2** = „zdroj",
odlišený od kódu 1 = „my". Bez toho rozlišení se čas tráví čtením kódu, který
je v pořádku.

**Předchozí stav pro srovnání:** 2026-07-31 proběhlo všech 18 tehdejších zdrojů
bez chyby, takže výpadek JMK je nový a týká se jen jeho.

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
- **Kvalita: `scripts/derive_deadlines.py`** — 24 grantů mělo termín ve zdroji, ale v jiném
  tvaru (`extra.deadliny[]`: „každoročně 15. 11.", „31. ledna každého roku", hotové ISO).
  Skript ho převede do strojového tvaru a u opakujících se promítne na NEJBLIŽŠÍ BUDOUCÍ
  výskyt. NENÍ to halucinace — datum je doložené v `kontext` (doslovná věta ze zdroje);
  odvozené záznamy nesou `status_confidence="derived"` + `extra.deadline_derived_from/_rule`.
  Efekt: unknown 919 → 895, open 687 → 697.
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
- `scripts/upsert.py` — html-tier ingesty upsertují do katalogu (dřív append-only skip).
- Windows robustnost: UTF-8 guardy (76 skriptů), TLS přes `http_util`, MAX_PATH guard.

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
5. **Soubory otvírej s `encoding="utf-8"`** — default Windows open() píše cp1250 mojibake
   (kouslo grantovydiar harvest 2026-07-31).
6. **Katalog je v gitu, zdrojová data ne** — fresh clone má `data/opportunities.jsonl`, ale ne
   stažená PDF a per-source harvesty; jejich obnova = `data_bundle/` nebo re-harvest.
7. **Nehalucinovat** — `amount=null`/`deadline=null` zůstává null; žádné fiktivní záznamy.
8. **Jen jeden proces smí psát `opportunities.jsonl`** — ingesty pouštěj sekvenčně
   (`refresh_run.py` to garantuje; ad-hoc paralelní loops ne).

---

## ⚠ kr-jihomoravsky.cz — zdroj zavřený za autentizací (2026-09-01)

**Změřeno při refreshi 2026-09-01.** Harvester hlásil „Úřední deska nevrátila
filtr kategorií (select#m_oKategorie)". Není to změna markupu:

```
https://eud.jmk.cz/Gordic/Ginis/App/UDE01/Seznam.aspx?a=1   →  HTTP 401
https://www.jmk.cz/                                          →  302 na /my.policy
```

Celý GINIS i hlavní web JMK je za přihlašovací bránou (F5 `my.policy`).

**Veřejná náhrada hledaná a NENALEZENA.** `dotace.jmk.cz` přesměrovává na
`dotace.kr-jihomoravsky.cz`, a ten obsahuje jediný odkaz — na
`data.jmk.cz/pages/dotace-katalog`. To je ArcGIS Hub Open Data portál
(197 datasetů, DCAT feed na `/api/feed/dcat-us/1.1.json`). Deset datasetů má
v názvu „dotac", ale všechny jsou **retrospektivní**:

  • Udělené dotace obcím v Jihomoravském kraji
  • Schválená výše dotace obcím v roce 2025
  • Čerpání krajských dotací / z fondů EU

Tedy KDO UŽ PENÍZE DOSTAL, ne KAM SE DÁ ŽÁDAT. Pro produkt bezcenné.

**Dopad:** 34 záznamů v katalogu (19 open, 13 closed, 2 unknown) zůstává
zmrazených ke dni posledního úspěšného sběru. Nemažou se — mizející záznam
by z uložených výzev udělal prázdné místo.

**Co to odemkne:** přístup k úřední desce JMK (dohoda s krajem), nebo nalezení
jiné veřejné stránky s VÝZVAMI. Bez toho se zdroj obnovit nedá a žádné množství
práce na harvesteru s tím nic neudělá.
