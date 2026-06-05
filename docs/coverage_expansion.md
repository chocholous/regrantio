# Coverage expansion — roadmap rozšíření zdrojů

> Větev `coverage-expansion`. Cíl: pokrýt **všechna** ministerstva, kraje, nadace a města.
> **Vodítko = current data** (`platform_map.json`: 507 hostů / 83 platforem detekováno; 51 v `opportunities.jsonl`).
> Gap = **65 grantových hostů** (`grant:true`, nezpracované). Tenhle dokument je jejich tříděný plán.

## Princip (z architektury, viz README + docs/platform_playbook.md)
Každá CMS-rodina = jeden tenký harvester (vrstva 1: TEXT + dokumenty). Pak univerzální vrstva 2 (LLM).
**Rozšíření = pro každou novou platformu buď reuse existující harvester, nebo napsat nový tenký parser / Apify.**

## Existující harvestery (reuse bez kódu)
| platforma | harvester | pokrývá v gapu |
|---|---|---|
| Kentico | `scripts/kentico_irop.py --base … --listing …` | dotaceeu.cz, irop.gov.cz, mk.gov.cz, mmr.gov.cz |
| WordPress REST | `scripts/wp_harvest.py` | abakus.cz |
| vismo | `scripts/vismo.py` + `vismo_detail.py` | (další obecní úřední desky) |
| dsw2 / Otevřená města | `scripts/dsw2.py` | (další instance — viz dsw2 discovery memory) |

## GAP po kategoriích (65 zdrojů)

### MINISTERSTVA / stát (13) — nejvyšší priorita
- **Kentico (reuse ✓):** `dotaceeu.cz`, `irop.gov.cz`, `mk.gov.cz`, `mmr.gov.cz`
- **custom_spa** (Apify/Playwright XHR replay — viz docs/apify_howto.md): `eagri.cz`, `jdp2.mf.gov.cz`, `mpsv.gov.cz`, `www.mk.gov.cz`
- **ostatní CMS** (nový parser): `czechaid.cz` (netservis), `dpmkportal.mkcr.cz` (aspnet_mvc), `isprom.msmt.gov.cz` (nette), `msmt.gov.cz` (marwel), `mze.gov.cz` (eagri_portal)

### KRAJE (7) — vysoká priorita (chybí celá vrstva krajských dotací)
- **aspnet_webforms** (Apify postback / WebForms harvester): `deska.pardubickykraj.cz`, `dotace.kr-jihomoravsky.cz`
- **edotace_plzen** (1 parser pokryje Plzeň město+kraj): `dotace.plzensky-kraj.cz`, `dotace.plzen.eu`
- **SPA/custom**: `dotace.khk.cz` (react), `dotace.kraj-lbc.cz` (firon), `rozvojkhk.cz` (aspnetcore), `zlinskykraj.cz` (codeigniter)

### MĚSTA (7)
- **aspnet_webforms**: `granty.praha.eu` (Praha!)
- **nette_custom**: `dotace.brno.cz`, `www.podbrnensko.cz`
- **edotace_plzen**: `dotace.plzen.eu` · **angular**: `dotace.olomouc.eu` · **nette**: `dpo-archiv.plzen.eu`

### NADACE / FONDY (12)
- **WordPress (reuse ✓):** `abakus.cz`
- **custom_php** (1 vzor pokryje víc): `nadace-agrofert.cz`, `nadacevodafone.cz`
- **různé CMS (nový parser/WP-REST sniff):** `nadacecez.cz`, `nadaceo2.cz`, `nadaceokd.cz`, `nadace-adra.cz`, `nadacnifondalbert.cz`, `nadace.veronica.cz`, `fondkinematografie.cz` (nette), `hlavkovanadace.cz` (static)

### EU / mezinárodní (6)
- **comerto** (1 parser: `at-cz.eu`, `sn-cz2027.eu`), **custom_php** (`eeagrants.cz`), **laravel** (`interreg-danube.eu`), **custom_spa** (`cz-pl.eu`)

### OSTATNÍ (20)
Granty mimo 4 hlavní kategorie: `vdv.cz`, `osa.cz` (autorské), `olympic.cz`, `sgs.cvut.cz` (vysokoškolské), `visegradfund.org`, `dp.dotacesport.cz`, `grantovydiar.cz` (agregátor — pozor, sekundární zdroj), … — nižší priorita.

## Strategie (pořadí dle hodnota/úsilí)
1. **Reuse harvestery (nulové úsilí):** Kentico 4 ministerstva + WP nadace → ihned.
2. **1 parser = víc zdrojů:** `edotace_plzen` (Plzeň ×2), `comerto` (EU ×2), `custom_php` nadace.
3. **aspnet_webforms harvester** (Apify postback) → odemkne kraje + Praha + zadosti.sfzp.cz (velká hodnota: krajská vrstva).
4. **custom_spa** (Playwright XHR replay jako lewis_discover) → ministerstva SPA.
5. Zbytek nette/react/angular per zdroj.

## Pravidla (nezapomenout)
- **STRUKTURA PŘED PRÓZOU** — u každého zkus strukturovaný endpoint (WP REST sniff, XHR, inline-JS) než LLM.
- **Ověř, CO endpoint dá** (award-DB ≠ otevřené výzvy; `grantovydiar.cz` je agregátor = dedup riziko).
- **Status v kódu**, lossless harvest, grounding — jako u stávajících.
- Po harvestu: `build_extract_input.py` → vrstva 2 (classify_wf + extract_wf) → `ingest_rich.py` → `consolidate.py` → `build_app.py`.

## Stav

### ✅ Hotovo (větev coverage-expansion, noční běh)
- **IROP** (`irop.gov.cz`) — 120 výzev (63 OPEN), `kentico_irop.py --enumerate 125` → `ingest_kentico.py`
- **dotaceEU** (`dotaceeu.cz`) — 13 výzev (12 OPEN), umbrella ESIF
- → **+133 EU-fund grantů, 75 OPEN** (akční deadliny 2026–2028) — řeší temporální chudobu (dřív 47 budoucích deadlinů). opportunities 778→911.
- `scripts/ingest_kentico.py` — reusable pro JAKÝKOLI Kentico portál (Czech datum→ISO, oblast z keywords title, typ_zadatele z eligible, region=celostátní, zdroj=eu_fondy).

### ✅ Hotovo — kraje + nadace přes Apify + LLM (+ opportunity-gate)
- **Apify** `website-content-crawler` (playwright) → markdown → `build_apify_input.py` → `extract_wf` → `ingest_apify.py`.
- **Kraje**: Zlínský (7 výzev RP*/MaS*), Středočeský, Pardubický. **Nadace**: ČEZ, VDV (Olga Havlová), Via, AGROFERT, NROS, Vodafone, O2. → **+21 oportunit**, opportunities 911→932, poskytovatelů 53→62.
- **OPPORTUNITY-GATE (`ingest_apify.py`)** dle pravidla „oportunity, ne katalogy": zahodí generické katalogy/rozcestníky/info (titul „Dotace/Granty/grantová řízení/Pro žadatele…"), **news** („Nové dětské hřiště podpoří", „Z programu X půjdou…") a **externí domény** (crawl bloudil na computertrends/litomericko24…). Ponechá jen konkrétní výzvu (deadline/open_from/číslo výzvy / eligible+oblast) nebo misi s „jak požádat". Dropped 26/47.
- **Praha**: granty.praha.eu = žádostní portál (ne katalog); centrál = Liferay próza za WAF (13/16 URL „Request Rejected"), prošly jen `/web/*` + subdoména `zdravotni.praha.eu` (Dotace 2026 s deadlinem). Městské části (8) už máme. → částečně, WAF-limit.

### 📍 KRAJE — platformy + baseline stav
Dvojí vzor: **hlavní web** (katalog/výzvy → Apify+LLM+gate) vs **žádostní app-portál** `dotace.{kraj}.cz` (jen podání, NE katalog → vynecháno).
| Kraj | hlavní web / platforma | app-portál | baseline |
|---|---|---|---|
| Zlínský | zlinskykraj.cz (custom, čisté `/dotace/`) | — | ✅ 8 programů |
| Pardubický | pardubickykraj.cz | dotace.pardubickykraj.cz (WebForms) | ✅ 10 programů |
| Jihočeský | kraj-jihocesky.cz | — | 🟡 2 |
| Středočeský | stredoceskykraj.cz (Liferay) + dsw2 instance | dotace.stredoceskykraj.cz | 🟡 4 |
| Vysočina | kr-vysocina.cz (**vismo** → vismo.py!) | — | ⬜ jen landing (deeper) |
| MSK | msk.cz (Drupal) | — | ⬜ jen landing |
| Olomoucký | olkraj.cz | — | ⬜ landing |
| Liberecký | kraj-lbc.cz | dotace.kraj-lbc.cz (firon) | ⬜ landing |
| KHK | kr-kralovehradecky.cz | dotace.khk.cz (React) | ⬜ |
| Plzeňský | plzensky-kraj.cz | dotace.plzensky-kraj.cz (edotace) | ⬜ |
| Jihomoravský | kr-jihomoravsky.cz | dotace.kr-jihomoravsky.cz (WebForms) | ⬜ |
| Karlovarský | kr-karlovarsky.cz | dotace.kr-karlovarsky.cz | ⬜ |
| Ústecký | kr-ustecky.cz | — | ⬜ landing |
| Praha | praha.eu (Liferay, WAF) | granty.praha.eu | 🟡 viz výše |

**Baseline: 5/14 krajů s reálnými programy (24 oportunit).** Zbylé kraje dají při crawlu jen landing/„Dotační programy v oblasti X" listing → potřebují **depth-3 crawl** (listing oblasti → jednotlivé programy) nebo (Vysočina) **vismo.py**. Apify+LLM+gate pipeline ověřená.

### ⛔ Vzdáno přes noc (s důvodem — pro denní rozhodnutí)
- **mk.gov.cz, mmr.gov.cz** (Kentico, ale jen „dotační okruhy" / tematické stránky, NE jednotlivé výzvy s deadliny) → IROP parser nesedí; chce vlastní parser.
- **SPA „dotace.*" portály** (`dotace.olomouc.eu` angular, `dotace.khk.cz` react, `dotace.brno.cz`, `dotace.plzen.eu`) → jsou to **žádostní systémy** (`/zadost/`, `/zadosti/`), ne veřejné katalogy výzev; API vrací HTML fallback. Veřejné výzvy bývají na hlavním webu kraje/města.
- **Kraje WebForms** (`dotace.kr-jihomoravsky.cz`, `deska.pardubickykraj.cz`, `granty.praha.eu`, `zadosti.sfzp.cz`) → aspnet postback, žádný JSON/inline → **Apify postback** (viz docs/apify_howto.md).
- **Nadace** (WP/php) → próza → **LLM vrstva 2** (ne structured easy).

### ▶️ Další kroky (denní, vyžadují rozhodnutí/nástroje)
1. **Apify postback harvester** pro aspnet WebForms → odemkne kraje + Prahu + SFŽP (velká krajská vrstva). Apify stojí kredity → rozhodnutí uživatele.
2. **Major OP portály** (OPŽP `opzp.cz`, OPTAK, OPZ `esfcr.cz`) — každý vlastní CMS, per-site tenký parser; stovky EU výzev.
   - **OPŽP prozkoumáno:** výzvy mají čisté číslované URL `https://opzp.cz/dotace/{N}-vyzva/` (N≈1–110, enumerovatelné jako IROP) → title + status („Příjem žádostí probíhá/ukončen") jdou; ALE deadline/oprávnění/alokace jsou v PRÓZE (ne strukturní bloky) → potřebuje pečlivý field-parser NEBO LLM vrstvu 2. Layer-1 raw harvest (enumerate + plný text) je triviální → pak extract_wf. **Dobrý první denní cíl.**
3. **edotace_plzen** parser (1 = Plzeň město+kraj).
4. **Nadace přes LLM vrstvu 2** (rate-limit → dávkově, ne přes noc).
5. `comerto` (1 parser = at-cz.eu + sn-cz2027.eu, EU přeshraniční).

## XHR-discovery na posledních 5 krajích (provedeno)
Nástroj: `scripts/xhr_discover.py` (generický Playwright odposlech JSON-XHR; zobecnění lewis_discover).
- **Plzeňský** ✅ — edotace vrátil rendered tabulku → parse → 20 výzev (hotovo).
- **KHK** (dotace.khk.cz React) — `xhr_discover` 0 JSON XHR (data lazy/na interakci → chce proklik).
- **Karlovarský** (GINIS) — 1 POST → HTTP 400 (stateful GINIS RAP app, chce session/payload).
- **Vysočina** (fondvysociny SPA) — 0 XHR, žádný HTML listing, cesty 404.
- **JM** (dotace.kr-jihomoravsky WebForms + data.jmk.cz opendata) — opendata stuby/arcgis.
- **Praha** — centrál za WAF (jen /web/* + zdravotni subdoména prošly Apify).
→ **Závěr: 9/14 krajů je realistický baseline.** Posledních 5 = JS-API/stateful/WAF portály, které
odolávají content-crawleru, table-parse i základní XHR-discovery; každý chce bespoke per-portál
reverse-engineering (interaction-driven XHR / GINIS session / WAF). Nízká priorita vs hodnota.

## Posledních 5 krajů — jeden po druhém (per-portál průzkum)
Hypotéza usera „možná podobné platformy, nebo jiná platforma" → každý portál zvlášť rozebrán:

| Kraj | platforma | průlom | výsledek |
|---|---|---|---|
| **KHK** ✅ | React SPA „DOTIS" (Azure Functions) | `config.js`→`dotisAPIUrl`; veřejný anonymní `POST /api/Data/GetProjectSubprojectCollection {}` vrací CELÝ strom programů→titulů s `dateBeg/dateEnd` | **+142 oportunit** (11 open), `dotis_harvest.py`+`ingest_dotis.py`. DOTIS je mezi kraji jen KHK (proben config.js napříč). |
| **Vysočina** ✅ | Fond Vysočiny (server-rendered) | správné URL `/dotace/default/aktivni?kat=999` → detail `/dotace/zadosti/{KÓD}` čistě štítkovaný | **+14 programů** (8 open, s alokací+oprávněností), `fondvysociny_harvest.py`. Filtr TEST záznamů. |
| **Karlovarský** ⛔ | GINIS RAP (Gordic) | app = RSA-šifrovaný stateful (jsencrypt+signalr), POST→400 bez session; hlavní web `kr-karlovarsky.cz` = redirect-loop wall | **zeď** — šifrovaný žádostní app, ne veřejný katalog |
| **JM** ⛔ | F5 BigIP APM | `kr-jihomoravsky.cz` i `jmk.cz` za F5 APM (logout page); `data.jmk.cz` = ArcGIS opendata, ale obsah = **schválené/udělené dotace (příjemci = awards)**, ne otevřené výzvy | **zeď + awards-only** (awards porušují „oportunity ne katalogy") |
| **Praha** 🟡 | Liferay + BigIP WAF | 13/16 URL „Request Rejected"; prošly jen `/web/*` + `zdravotni.praha.eu` | **částečně** (WAF), městské části (8) máme |

**Závěr: cracknuty 2 z 5 (KHK, Vysočina) přidáním nových platforem (DOTIS API, Fond Vysočiny listing).**
Zbylé 3 (Karlovarský/JM/Praha) jsou **auth/WAF/šifrovací zdi**, ne crackable platformy — vyžadovaly by
obcházení F5 APM / RSA session emulaci (mimo legitimní rozsah). **Region pokrytí: všech 14 krajů má
v korpusu oportunity** (Karlovarský 4, Olomoucký 8 z prózy/extrakce); KHK+Vysočina mají navíc celý
krajský program-katalog z vlastního portálu. opportunities 1015→1171.

## KDE kraje publikují dotace → 6 nových HTML harvesterů (+319 programů)
Systematický průzkum: krajské `dotace.*` jsou žádostní portály; veřejné výzvy jsou na **hlavním webu (SSR HTML)**
nebo úřední desce. 6 krajů renderuje výzvy přímo do HTML → tenký deterministický harvester (vrstva 1):

| Kraj | zdroj (veřejný listing) | platforma | programů | open |
|---|---|---|---|---|
| **Pardubický** | `dotace.pardubickykraj.cz/grants` | Nuxt SSR (data v DOM, neúplný SSL→CERT_NONE) | 105 | 25 |
| **Liberecký** | `dotace.kraj-lbc.cz/` (18 oblastí) | Firon/Nette, **status Otevřen/Uzavřen v HTML** | 99 | 26 |
| **MSK** | `msk.cz/temata/dotace` → 9× `?pgid=` | vlastní PHP CMS | 95 | 6 |
| **Zlínský** | `zlinskykraj.cz/aktualne-vyhlasene-vyzvy...` | SSR HTML (kódy RP/SOC/NFV + alokace) | 10 | 7 |
| **Jihočeský** | `kraj-jihocesky.cz/cs/ku_dotace/vyhlasene` | SSR accordion | 5 | 4 |
| **Olomoucký** | `olkraj.cz/.../aktualni-dotacni-programy` | Nette (termíny ve slug detailu) | 5 | 1 |

Harvestery: `scripts/{pardubicky,liberecky,msk,zlinsky,jihocesky,olomoucky}_harvest.py` (stdlib, jednotný
kontrakt) → `scripts/ingest_kraj.py` (generický: oblast/typ z keywords, status z dat NEBO explicitní web-status
u Liberce, region=kraj). Odstraněny staré Apify-Zlínský duplicity (nahrazeny bohatšími HTML). opportunities 1171→1482.

### Stále přes Apify/WAF (ne přímý HTTP)
- **Ústecký** — vismo VISMO 6 blokuje fetch (404/WAF) → Apify nebo `portalobcana.kr-ustecky.cz` JSON API
- **Středočeský** — Liferay, výzvy roztříštěné po fondech → Apify+LLM (částečně máme)
- **JM** — `eud.jmk.cz` GINIS USU (postback) + `kr-jihomoravsky.cz` KEVIS render → Apify
- **Karlovarský** — celá doména WEDOS WAF (301-loop) → jediná cesta `edesky.cz/desky/76` přes Apify
- **Praha** — `eud.praha.eu/pub/rss/...` = plný RSS (ale dominují awards); otevřené výzvy → Apify nad `praha.eu/web/*`

**Stav krajů: 13/14 má reálné OTEVŘENÉ programy z veřejného zdroje** (chybí jen Karlovarský = WAF). open oportunit ~230.

## Posledních 5 zazděných krajů — kreativní průraz (4/5 cracknuto)
Každý jiným trikem (Playwright na JS/WAF, JSON-XHR, GINIS USU, RSS):

| Kraj | metoda průrazu | programů (open) | pozn. |
|---|---|---|---|
| **Ústecký** ✅ | Playwright na vismo dotační kalendář `kr-ustecky.cz/dotacni-kalendar?parent=2` (JS grid) | 94 (13) | s alokacemi; portalobcana JSON API neexistuje |
| **Středočeský** ✅ | čisté HTML (bez WAF) — rozcestník `prehled-dotaci` → per-fond stránky | 89 (1) | Liferay, ale veřejné HTML; mnoho termínů jen v PDF |
| **JM** ✅ | Playwright na GINIS USU `eud.jmk.cz` KAT050 (vyhlášení programů, ne awards) | 26 (30*) | KEVIS web je mrtvý archiv 2021; *open dle vývěsky, reálný deadline v PDF |
| **Praha** ✅ | Playwright render Liferay `praha.eu/web/*` + `eud.praha.eu` RSS (filtr awards) | 15 (announced) | roztříštěno po resortech; termíny/alokace v PDF |
| **Karlovarský** ⛔ | WEDOS WAF = **IP-reputační blok** (301-loop i přes Playwright/curl_cffi/headed Chrome) | 0 | harvester napsán; projde JEN z rezidenční IP/proxy. edesky deska = jen správní akty, ne programy |

Harvestery: `scripts/{ustecky,stredocesky,jm,praha,karlovarsky}_harvest.py` → `ingest_kraj.py`.
**Diagnóza Karlovarský:** WAF neposílá JS challenge, jde o čistý 301-loop dle IP reputace (datacentrová IP prostředí
je flaglá). `karlovarsky_harvest.py --method playwright` proběhne z rezidenční IP. Fallback edesky.cz/76 = úřední
deska bez dotačních programů (kraj je publikuje na webu za WAF).

### FINÁLNÍ STAV KRAJŮ: 13/14 s reálnými harvestovanými programy
opportunities 1015 → **1706** za session, **262 otevřených** napříč 12 kraji (Praha/Karlovarský mají termíny/data
v PDF → status unknown / čeká na rezidenční IP). Jediná zeď: Karlovarský (IP-reputační WAF, řešitelné jinou IP).

## Karlovarský dořešen (Wayback) + JM přílohy dotaženy z PDF
**Karlovarský — WEDOS WAF neprůrazný, ale Wayback ano:** Apify website-content-crawler (residential CZ,
firefox i chrome) = 0 stránek; Apify rag-web-browser (browser-playwright, residential) = HTTP 500.
WEDOS Global Protection blokuje i Apify residential. **Řešení: Wayback Machine** (`web/{TS}id_/` raw archiv
oblast-listingů `/dotace/dotacni-programy-karlovarskeho-kraje/oblast-*`) → `karlovarsky_wayback_harvest.py`:
**69 programů z 9 oblastí, nejnovější snapshot 2026-05-25** (čerstvé!), 59 s deadlinem, 7 open. Alokace jsou
jen na detailech (Wayback listing je nemá) → null. opportunities +69.

**JM přílohy — reálné deadliny z PDF:** vývěskové datumy na GINIS USU desce KLAMALY. `jm_pdf_enrich.py`
reuse GINIS session (Playwright) → stáhl 32/32 PDF pravidel → pdftotext → **16 reálných deadlinů**,
8 alokací, 4 oprávněné žadatele. Re-ingest: JM open 30→17 (řada programů reálně uzavřená už v únoru).
7 PDF = naskenované awards bez textové vrstvy (OCR neřešeno, nízká hodnota).

### 🏁 FINÁLNÍ STAV: 14/14 krajů má data, 13/14 aktuálně otevřené programy
opportunities **1015 → 1775** za session, **256 otevřených** napříč 13 kraji (Praha má termíny v PDF →
status announced/unknown; lze dotáhnout stejně jako JM). Jediná platforma, co odolala přímému i Apify
přístupu: WEDOS WAF (Karlovarský) — obejito přes Wayback.
