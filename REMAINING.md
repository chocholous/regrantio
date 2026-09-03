# REMAINING.md — stav projektu + co zbývá

Živý plánovací dokument. **Aktuální stav, co je hotovo, co zbývá a proč.** JAK pracovat (zlatá pravidla,
recept na zdroj, pasti) = `docs/SESSION_PLAYBOOK.md` + `CLAUDE.md`. Katalog je v gitu, zbytek dat v gitignored `data/`.

> **Status k 2026-09-03 (změřeno, ne odhad).** Dataset **3525 záznamů / 134 zdrojů**,
> export vygenerovaný **2026-09-03** (`docs/opportunities.json`, 11,1 MB).
> **74/74 testů**, `validate_release` prochází přes **deset** bran.
> Publikační cesta do úschovny hotová (`scripts/publish_export.py`,
> `refresh_run.py --publish`) a čeká **jen na založení kbelíku** — viz
> `docs/REFRESH.md §8`. Jméno kbelíku se doladí spolu s přejmenováním
> repozitáře (`regrantio` → `grantio-data`), aby se nezakládal dvakrát.

---

## 📊 Aktuální stav datasetu (live `data/opportunities.jsonl`, změřeno 2026-09-03)

| metrika | hodnota |
|---|---|
| **záznamů celkem** | **3525** (3500 grantů + 25 foundation_mission) |
| **zdrojů (`source`)** | **134** |
| **obnovitelných bez modelu** | **28** (14 strukturních + 14 s vlastním parserem) |
| status grantů | **755 open** · 38 announced · 1794 closed · 913 unknown |
| termíny | deadline 2587 (74 %) · open_from 2438 (70 %) |
| částky | amount 778 (22 %) |
| texty | focus_area 3243 (93 %) · eligible_applicants 2304 (66 %) · source_url 3500 (100 %) |
| **známé stáří** | **1457 (41 %)** — `provenance.fetched_at`, viz níž |
| integrita | **0 dup id · 0 bez id · 0 bez title · 0 inverzních termínů** |
| export | 3525 záznamů, `content_hash` u **100 %** |

> ⚠ **NOVÁ METRIKA: ZNÁMÉ STÁŘÍ.** Do 2026-09-03 katalog neuměl říct, kdy
> byl který záznam naposled ověřen u zdroje — `provenance` datum nenesla.
> Bez modelu obnovit jde **28 zdrojů ze 134** (14 strukturních + 14 s vlastním
> deterministickým parserem — viz `refresh_run.py --list`); u zbylých čeká
> obnova na modelovou vrstvu, takže razítko nemají a jejich stáří je neznámé.
>
> ⚠ Do 2026‑09‑03 tu stálo „14 z 134" a bylo to vedle na obě strany: třída B
> v žádném registru nebyla, a 28 „extraktorů" má naopak data natvrdo, takže
> obnovu jen předstírají (`refresh_run.TRANSCRIBED`).
>
> `null` znamená **„nevíme"**, ne „staré". Štítek „neaktuální" by u čtyř pětin
> katalogu tvrdil něco, co o něm nevíme. Číslo poroste s každou obnovou; hlídá
> ho brána `známé stáří záznamů`, aby razítko nikdo tiše nezahodil.

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

## ✅ Refresh 2026-09-03 — co proběhlo

**13 ze 14 deterministických zdrojů obnoveno**, katalog 3441 → 3450 (+9),
po vyčištění 3448. Brána prošla přes devět kontrol.

| zdroj | výsledek |
|---|---|
| dotace.brno.cz | ✓ 32 programů, 19 změn |
| dotace.khk.cz | ✓ 17 programů / 861 podprojektů, 4 změny |
| dotace.kraj-lbc.cz | ✓ 104 programů (25 otevřených), 4 změny |
| msk.cz | ✓ 91 programů, 13 změn |
| stredoceskykraj.cz | ✓ 91 programů, 8 změn |
| praha.eu | ✓ 33 programů, 7 změn |
| fondvysociny.cz | ✓ 10 programů, 3 změny |
| kr-karlovarsky.cz | ✓ 18 programů, 2 změny |
| kr-ustecky.cz · kraj-jihocesky.cz · olkraj.cz · zlinskykraj.cz · dotace.pardubickykraj.cz | ✓ beze změny |
| **kr-jihomoravsky.cz** | ✖ **HTTP 401 Unauthorized** |

### kr-jihomoravsky.cz — potvrzeno, že je to zdroj

2026-08-22 vracel „Configuration Error", 2026-09-01 se zavřel za autentizaci,
dnes vrací **`401 - Unauthorized: Access is denied due to invalid credentials`**.
Tři různé chyby v řadě za sebou, všechny na jejich straně. U nás není co
opravovat a harvester to hlásí kódem 2 („zdroj"), ne kódem 1 („my").

### ⚠ Co se u téhle obnovy naučilo

`fetched_at` se doplnilo **až po** běhu, tedy druhým průchodem ingestů nad
už staženými soubory. Ukázalo to pořadí, na které je potřeba dát pozor:
ingest zapisuje syrová fakta z listingu, `fix_dataset` je pak přepočítá.
Kdo pustí ingest znovu PO přepočtu, přepíše přepočtené syrovým a musí dojet
`refresh_run.py --tail-only`. Samotný `refresh_run` to pořadí drží správně.

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

### Živé přeověření 2026-09-03 (realistické hlavičky, přímý HTTP)

Blokery výš jsou z 2026-07-31. Dnes přeověřeno, protože „blocker" starý pět
týdnů je odhad, ne měření:

| zdroj | dnes | závěr |
|---|---|---|
| **SZIF** | `ConnectionResetError` na `szif.cz` i `szif.gov.cz` | blocker **potvrzen** — WAF řeže TCP spojení, hlavičky nepomáhají. Chce proxy nebo jinou IP |
| **Interreg Danube** | `/calls` = 404, ale **`/calls-for-proposals` vrací 200** | adresa v tabulce výš je **mrtvá**; nová funguje. Obsah jsou ale kola z 2022–2024, **žádná otevřená výzva** → nepřidáno, ale příště se na 404 neztrácí čas |
| **Interreg Central Europe** | 200, `/calls-for-proposals/` | verdikt „všechna kola uzavřená" **platí dál** — na stránce jsou jen výsledky (first/second/third/strategic call) |

⚠ **Poznámka k měření:** první pokus počítal výskyty vzorů v Node.js a hlásil
nulu tam, kde data byla. `\b` v JavaScriptu nezná `ů` (slovní znak je jen
`[A-Za-z0-9_]`), takže `programů\b` nikdy nesedlo. V Pythonu je `\b`
unicode-aware a vzor sedí. **Vzory nad českým textem měř tím jazykem,
ve kterém pak poběží.**

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

---

## ⚠ Kolik zdrojů funguje? Repozitář na to neumí odpovědět (2026-09-01)

**Vazba mezi `routing.yaml` a `source` v datech neexistuje nikde v repozitáři.**

Tři mechanické pokusy o spočítání funkčních zdrojů daly tři různé odpovědi:

| jak | výsledek | proč je špatně |
| --- | --- | --- |
| klíče v `routing.yaml` | **81** | klíčuje se doménami (`esfcr.cz`), data krátkými id (`esfcr`) |
| normalizace jmen | **51 spárováno** | heuristika; `msmt.gov.cz` ≠ `msmt`, `nadace-adra.cz` ≠ `nadace_adra` |
| `source` vyčtený z harvesteru | **33** | u 48 zdrojů se nenajde, včetně těch se 148 záznamy |

A `docs/PREHLED.md` v Grantiu tvrdilo **136** — počet různých hodnot `source`
v datasetu, tedy zase něco jiného.

**Příčina.** Sdílené harvestery berou `source` jako argument:

```
python3 scripts/dotis_harvest.py --web https://dotace.khk.cz \
        --source dotace.khk.cz --out data/h_dotis_khk.json
```

`routing.yaml` u toho záznamu nese jen `harvester` a `note`. Identifikátor,
pod kterým se záznamy do datasetu zapíšou, tedy nestojí ve skriptu ani
v routeru — je jen ve způsobu, jakým se skript spustí. Jeden skript
(`dotis_harvest.py`) přitom obsluhuje víc krajů, takže „jeden skript = jeden
zdroj" neplatí a odvodit to nejde.

**Důsledek.** Na otázku „který zdroj vyschl" se dnes odpovídá ručním
procházením 81 položek. Vyschlý zdroj se tím pádem pozná až tehdy, když si
někdo všimne, že v katalogu chybí kraj — což je pozdě.

### ✅ VYŘEŠENO 2026-09-02 — ale jinak, než navrhoval předchozí odstavec

Navrhovaná oprava zněla „přidat do `routing.yaml` pole `source:`". S daty v ruce
se ukázalo, že by nestačila:

| | |
|---|---|
| položek v `routing.yaml` | **81** |
| hodnot `source` v datasetu | **136** |
| z toho routing pokrývá (spárováno podle hostu ze `source_url`) | **74** |

⚠ **`routing.yaml` NENÍ INVENTÁŘ ZDROJŮ A NIKDY JÍM NEBYL.** Je to směrovník
„platforma → čím to harvestovat". Přes šedesát skutečně sbíraných zdrojů v něm
položku nemá vůbec, protože jedou přes rodinu (`families:`) nebo přes vlastní
skript. Doplnit tam `source:` by vyrobilo inventář, který o dvou třetinách sběru
mlčí — a to je horší než žádný, protože se podle něj rozhoduje. K tomu jedna
položka (`mk.gov.cz`) zapisuje **tři** různá `source` id, takže jedno pole
by na ni stejně nestačilo.

**Inventář už existuje a je jím dataset.** Každý záznam nese `source`, takže
seznam zdrojů, které něco přinesly, je z dat čitelný přesně. Chybělo jediné:
porovnání s minule publikovaným stavem.

**Hotovo:** `scripts/source_health.py` + brána `vyschlý zdroj` ve
`validate_release.py`. Porovnává živý katalog proti minule publikovanému
exportu po jednotlivých zdrojích:

```
zdrojů v katalogu: 136   (minule 136)
záznamů:           3441  (minule 3441)
OK — žádný zdroj nevyschl ani nepropadl
```

⚠ **Brána na celkový počet tohle chytit NEMOHLA.** Práh je 80 % a největší
zdroj má 341 z 3 441 záznamů, tedy 10 % — může tedy zmizet celý a projde.
Naměřeno: ze 136 zdrojů by jich **133 mohlo vyschnout po jednom**, aniž by
kterýkoli jednotlivý běh brána zastavila. Osm testů v `tests/test_publish.py`
hlídá obě strany (co zastavit musí i co pustit musí).

**Co zbývá:** propojení `routing.yaml` se `source` id je pořád nedodělek,
ale je to úkol pro pohodlí („čím se ten zdroj sbírá"), ne pro bezpečnost
(„co vyschlo"). Ta druhá otázka je zodpovězená.

---

## ✅ 148 záznamů odkazovalo na rozcestník, ne na výzvu (2026-09-02)

**4,3 % celého katalogu** — všechno `dotace.khk.cz` (DOTIS, Královéhradecký
kraj) — mělo `source_url` i `source_doc` nastavené na `https://dotace.khk.cz/`,
tedy na ÚVODNÍ STRÁNKU portálu.

Produkt u každé výzvy slibuje odkaz na originál. Tenhle odkaz ten slib formálně
plní a věcně ne: žadatel skončí na rozcestníku se stovkou programů a hledá
znovu. URL byla platná, stránka se otevřela, čtvrt roku si toho nikdo nevšiml —
a přesně proto to nemohla chytit žádná stávající brána.

**Hluboký odkaz existoval celou dobu.** DOTIS je React SPA; cesty jsou
v `static/js/main.*.js` a mezi nimi `path:"/grantProgram/:memo"`. Klíč `memo`
je kód programu (`26POVU1`), který už v titulku každého záznamu je. Ověřeno
v prohlížeči: `https://dotace.khk.cz/grantProgram/26POVU1` vykreslí číselné
označení, název i účel programu.

Opraveno na dvou místech — v harvesteru (`ingest_dotis.py:dotis_url`, aby to
tak přicházelo rovnou) i v úklidu (`fix_dataset.py` sekce A5, kvůli záznamům
z dřívějších běhů). Tři testy v `test_core.py` hlídají obojí i to, že se
odkaz NEVYROBÍ bez kódu: vymyšlený kód vykreslí prázdný detail, což je horší
než rozcestník.

⚠ **Změna `source_url` mění `content_hash`, ale ne to, co uvidí zákazník.**
Ingest v Grantiu zakládá `catalog_grant_change` jen při posunu termínu nebo
částky, takže 148 přepsaných odkazů neudělá 148 upozornění.

---

## ✅ Dvojí identita organizací — vyřešeno ze tří čtvrtin (2026-09-03)

Ze čtyř případů níže zbývá **jeden**, a to způsobem, před kterým ten odstavec
sám varoval: pravidlem, ne ručním smazáním čtyř řádků.

| případ | stav k 2026-09-03 |
|---|---|
| `nadacevia.cz` (1) | **pryč** — „Nabídka programů" je rozcestník, chytá ho `NOT_A_CALL` |
| `vdv.cz` (1) | **pryč** — nábor hodnotitelů, chytá ho `NOT_A_CALL` |
| `nadacecez.cz` (1) | **problém to nikdy nebyl** — je to řádná výzva s termíny (Zaměstnanecké granty 2026, 1. 3. – 31. 3.). Ověřeno v datech, ne odhadnuto |
| `nadace-agrofert.cz` (1) | **zbývá** — záznam je homepage nadace |

Obě odstraněné byly zároveň jediné záznamy svých doménových zdrojů, takže
počet zdrojů klesl 136 → 134 a dvojí identita u nich zanikla celá.

**Proč `nadace-agrofert.cz` zůstává:** není to rozcestník ani nábor, je to
homepage s titulkem konkrétního fondu („Nadace AGROFERT — Fond na Podporu
rodičů samoživitelů"). Chce to pravidlo na DUPLICITU ORGANIZACE, ne na druh
stránky — a to je jiná úloha. Ruční smazání by se při příštím sběru vrátilo.

**Zamítnuté pravidlo (ať se nezkouší znovu):** „titulek je jméno organizace"
(tvar `Nadace X`). Naměřeno na celém katalogu — trefí 4 záznamy a **všechny
čtyři jsou řádné programy**: „Nadace ČEZ – Program Stromy", „Nadace OKD
obcím", „Nadační fond Karlovarského kraje", „Nadační fond Hyundai (Nadace
OSF)". Nadace svoje programy běžně pojmenovávají po sobě. Zůstává jako
`PROPUSTIT` v `tests/test_notacall.py`.

<details>
<summary>Původní zápis z 2026-09-02 (pro kontext)</summary>

## ⚠ Čtyři organizace mají v datech dvojí identitu (2026-09-02, neopraveno)

| krátké id | doménové id | co je v tom doménovém |
|---|---|---|
| `nadacevia` (24) | `nadacevia.cz` (1) | rozcestník „Nabídka programů" |
| `nadacecez` (16) | `nadacecez.cz` (1) | vypadá jako řádná výzva |
| `nadace-agrofert` (7) | `nadace-agrofert.cz` (1) | homepage nadace |
| `vdv` (5) | `vdv.cz` (1) | výzva pro HODNOTITELE, ne pro žadatele |

Dvě z těch čtyř nejsou výzvy (rozcestník a homepage), jedna míří na jinou
cílovou skupinu. `fix_dataset.py` má sekci A2 přesně na tenhle vzor
(`VARIANT_DEDUP`), ale ta maže jen při SHODĚ TITULKŮ — a tady se tituly liší,
protože jde o jiné stránky téhož webu.

**Proč to nechávám otevřené:** správná oprava není smazat čtyři řádky, ale
poznat, že záznam je rozcestník. Pravidlo „URL je kořen webu" NEPLATÍ —
naměřeno, sedne na 153 záznamů a 148 z nich jsou řádné programy KHK (viz
oddíl výš). Rozhodovat to bez pravidla znamená ruční zásah, který se při
příštím sběru vrátí.

</details>

---

## ✅ Obnova 2026-09-03 — třída B objevena, 28 „extraktorů" odhaleno

**+77 záznamů** (3448 → 3525), z toho 75 z EU Funding & Tenders portálu.

### Co se ukázalo

`refresh_run.py` znal jednu cestu bez modelu (harvest → strukturní ingest, 14
zdrojů). Cesta číslo dvě — harvest → `build_extract_input` →
`data/_<slug>_extract.py` → `ingest_rich` — byla popsaná v `docs/REFRESH.md`,
ale v žádném registru. Ověřeno živě na `opd`: 12 výzev, nula účasti modelu.

Přibylo `EXTRACT_SOURCES` a `--tier extract`.

### A hned nato ta nepříjemnější půlka

Ze 42 souborů `data/_*_extract.py` jich **jen 15 vstup opravdu čte**. Zbytek má
výsledek napsaný natvrdo — přepis jedné extrakce z 2026‑06/07 do literálů.

Nebezpečné je, že se to nepozná: spustí se, vytiskne „wrote N grants", skončí
nulou. A protože `ingest_rich` páruje obsah se zdrojem podle **pořadí**
vstupních souborů, dostane po každé změně listingu záznam **cizí odkaz**:

| titulek (z června) | odkaz (z dnešního harvestu) |
|---|---|
| Výzva č. 31_22_019 – Nákup nízkoemisních vozidel | `/vyzva-c.-31_22_002-budovani-kapacit-detskych-skupin` |
| Dotace … Bílá stuha | `/dotace-na-podporu-rodiny-pro-nestatni-neziskove-organizace` |

Prvním během to stihlo zapsat 7 záznamů a orazítkovat 350 dalších jako ověřené
dnes. Vráceno, razítka odebrána, zdroje vedeny v `refresh_run.TRANSCRIBED`.
**Cesta ven je pro ně tatáž jako pro třídu C — model.**

### Uklizeno při tom

- **8 harvesterů mělo `--seeds` povinný a jeho soubor gitignorovaný** → po
  čerstvém klonu nespustitelné. `.gitignore` má teď třetí výjimku (vstup je
  kód, ne data); čtyři chybějící soubory zrekonstruovány z katalogu.
- **Brána „známé stáří" se ptala špatně.** Počítala razítka všech zdrojů, takže
  vyřazení nedůvěryhodného zdroje hlásila jako ztrátu. Ptá se teď jen na zdroje
  z registru.
- **`pages.yml` běžel na každý push** a publikoval web, který má GitHub Pages
  vypnuté (`/pages` i stránka vrací 404) — 49 s a `fetch-depth: 0` nad 2GB
  historií. Teď jen `workflow_dispatch`; zapnutí Pages je jedno kliknutí
  vlastníka repa.

### Zbývá u tří zdrojů

| zdroj | co je | čí to je |
|---|---|---|
| `sfpi` | `sfpi.cz/wp-json/wp/v2/pages` → **404**, WP REST API zrušeno | zdroj |
| `eeagrants` | harvest neskončil do 30 min | k prověření |
| `kr-jihomoravsky` | úřední deska za přihlášením (**401**) | zdroj |
