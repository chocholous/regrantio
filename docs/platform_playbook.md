# Platform playbook — definice rodin, detekce, harvester, metoda

> **Strojová routing tabulka platforma→harvester je `routing.yaml`** (`scripts/routing.py --host <host>` / `--all`). Tenhle dokument je LIDSKÝ popis rodin (podpis, obtížnost, lekce). Cesty harvesterů níž = `scripts/`.

507 hostů, ~83 platforem po re-detekci. **1 CMS rodina = 1 tenký harvester.** Metoda získání grantu
se sbalí do 5 archetypů: (1) strukturovaný/API, (2) listing→dokumenty→LLM, (3) SPA/postback (Apify),
(4) WordPress REST, (5) **SPA/grid se skrytým JSON-XHR → odposlech Playwrightem jednou → čistý HTTP replay**
(bez Apify; viz `scripts/lewis_discover.py` + `lewis_dynamo.py`). Status vždy v kódu.

## Jak číst: jdou detaily snadno?
- ✅ **deterministicky** (bez LLM) — jen dotacni.info (šablona h2), IROP/dotaceEU (Kentico inline pole), arcgis (JSON)
- ◐ **harvest snadný, detaily Haiku na PDF/prózu** — většina (vismo, plone, mv/hzs, mmr, drupal, nadace…)
- ❌ **headless/Apify** — SPA + WebForms postback

---

## HOTOVÉ (extrakce postavena)

| Rodina | # | Detekce (podpis) | Přístup | Harvester | Detaily | Status |
|---|---|---|---|---|---|---|
| **wordpress** | 88 | `/wp-json`, `/wp-content`, generator Elementor/WP | REST API | `scripts/wp_harvest.py` (lossless) | dotacni.info ✅ / jinde Haiku | ✅ data/wp_full |
| **vismo** | 40 | `webhouse`, `/aspinclude/vismoweb5/`, `.dok`, `/ds-`/`/ms-`/`/d-`, File.ashx | HTML listing + File.ashx přílohy | `scripts/vismo.py` + `vismo_detail.py` | status z „Úřední deska od-do" (67%), jinak Haiku | ✅ data/vismo_documents + files |
| **dsw2_otevrenamesta** | 28 | `var fonds=`, `/explore/fonds`+`/explore/appeals`, `bootstrap-treeview` | inline JS vars | `scripts/dsw2.py` + `dsw2_fetch.py` | programy/výzvy discovery; alokace v dok | ✅ data/dsw2_* |

## PROZKOUMANÉ (struktura známá, PoC/část)

| Rodina | # | Detekce | Přístup | Metoda | Detaily |
|---|---|---|---|---|---|
| **kentico** | 11 | `CMSPages`, `/getmedia/`, `CMSScript` | 3 šablony! | (A) IROP+dotaceEU=statické inline pole `scripts/kentico_irop.py`; (B) MMR/MK/MDČR=hub→próza→getmedia; (C) nadace bespoke | A ✅ deterministicky / B Haiku |
| **plone** | 22 | generator Plone, `/resolveuid/`, `++theme++ova-theme` | folder→roční detail→.pdf | 1 parser na ostravské obvody | ❌ zásady=33k PDF → Haiku |
| **aspnet_mv_hzs** | 6 | `/clanek/{slug}.aspx` + `/soubor/` | HZS ploché=lehké / MV WebForms postback=Apify | `scripts/mv_cms.py` | PDF/Haiku |
| **grantys** | 5 (~3 reálné) | `ng-app="grantys.client"`, 1808B shell | **SPA gated API** → Apify | /api/project/supported (403 bez session) | data v JSON za bránou |
| **custom_php (eeagrants)** | (1 ověřen) | `/cs/programy/<oblast>`, `/cs/vyzvy`, server-rendered | statické HTTP, BFS | `scripts/eeagrants.py` (50 str / 480 dok) | ✅ vrstva 2 ověřena (3 výzvy: částka, 7–11 příloh, jak žádat) |
| **Lewis/Dynamo GrantyPortal** | granty.praha + další města | `/GrantyPortal/`, `SeznamJS`+`ODataSimpleFromSql`, Knockout grid | **JSON-XHR, HTTP replay po Playwright objevu** (NE Apify) | `lewis_discover.py` → `lewis_dynamo.py` | strukturovaně ✅ (112k záznamů); ⚠ jen **rozhodnuté žádosti = `project`**, ne otevřené výzvy |

## ZMAPOVANÉ POVRCHOVĚ (typ znám, extrakce TODO)

| Rodina | # | Detekce | Pozn. |
|---|---|---|---|
| **drupal** | 22 | `Drupal.settings`, `/sites/default` | nadace/zahraniční; občas JSON:API |
| **custom_php / nette** | 29+9 | bespoke; Nette markery | ⭐ **NADACE + krajské dotační portály** (darujme.cz, nadace ČEZ/O2/Agrofert, dotace.brno.cz, fondkinematografie). Každý JINÝ → per-site, vysoká hodnota. ✅ eeagrants HOTOVO (`scripts/eeagrants.py`). Sonda: hledej grant-slova v server-rendered HTML — kde jsou (eeagrants 16, nadaceokd 8), stačí statické HTTP |
| **custom_spa** | 18 | žádný HTML obsah, JS bundle (OLC Webdesign) | czso/eagri/mpsv → **Apify headless** |
| **joomla** | 14 | generator Joomla, `/media/jui` | bespoke + občas API |
| **liferay** | 11 | `Liferay`, `/o/brno-theme/` | brno.cz MČ portál |
| **bm_cms** (Beneš&Michl) | 9 | vendor podpis, `bxslider` | Plzeň obvody `umoX.plzen.eu` |
| **public4u** | 7 | `gen:public4u`, `gallery4u.js` | mulouny/přerov/prostějov/šumperk/trutnov |
| **aspnet_webforms** (CZI) | 5 | CZI webdesign | ⭐ **granty.praha.eu, zadosti.sfzp.cz, dotace.JMK** — grid přes JSON-XHR. **NE nutně Apify**: granty.praha = Lewis/Dynamo → HTTP replay po Playwright objevu (`lewis_dynamo.py`). U dalších ověř, zda taky `ODataSimple*` (pak HTTP) |
| **gordic_ginis** | 6 | `gordic`/`ginis` v patičce | ⚠ ZAVÁDĚJÍCÍ — GINIS=registr/úřední deska backend, ne dotace; krajské dotace na hlavním webu kraje (bespoke) |
| **marwel** | 4 | Marwel vendor | MŠMT, Karviná |
| **galileo** | 4 | Galileo vendor | municipal |
| **arcgis_hub** | 3 | Esri ArcGIS, `/opendata-ui/` | ⭐ **Open Data API (JSON)** — triviální |
| **Wedar / highslide / origine / Zlín-vendor / firon / webtodate=Macron / edee=FG Forrest / visu=Visualio / edotace=PilsCom / comerto / typo3 / sharepoint** | po 1-4 | vendor podpisy (`/js/global/wedar/`, `/assets/custom/frontend/` …) | 1 parser/vendor; municipal/nadace |

## FALSE POSITIVES / vyloučit
- **www.kb.cz** = Komerční BANKA (Kentico, ale „Podpora"=zákaznická, ne dotace)
- **ERR_fetch (67)** — DNS/timeout/WAF; část retry, část WAF-blok
- **UNKNOWN (8)** — acf.cz/csob.cz/asociacedso.cz nerozpoznané i Sonnetem
- **~42 singletonů** — bespoke vendor po 1 webu, nízká priorita

## KLÍČOVÉ LEKCE
- **„mv_legacy_cms" NEEXISTUJE** — slil Plone(17)+ASPNET-MV/HZS(3)+Public4u(3). Vždy ověř generátor.
- **„gordic_ginis" konfláduje** GINIS backend s krajskými weby (vložené widgety v patičce).
- **engine sdílený, výzvy-šablona per-web** (Kentico 3 šablony, vismo varianty, mv 3 případy).
- **přílohová pipeline univerzální** — `dsw2_fetch.sniff_ext` funguje na File.ashx / /soubor / /getmedia / .pdf (ověřeno 4× reuse).
- **ⓘ ZÁCHRANA grantů z obalů** — Haiku classify (`scripts/classify_wf.js`) správně vytáhne grant schovaný v „úřední desce / news / administrativě" (vyhlášení veřejné soutěže, „Vyhlášena výzva č. X"). Nespoléhej na regex/klíčová slova pro určení typu — `výběrové řízení`/`veřejná soutěž` jsou reálné granty. Klasifikuj OBSAHEM (LLM), ne obalem.
- **ⓘ ořez vstupu ZABÍJÍ vrstvu 2** — `amount` 27 % → 90 % po odstranění stropů (měřeno na 30 grantech). Vrstva 2 = `scripts/extract_wf.js`: plný text + plný text VŠECH příloh, 1 oportunita = 1 agent, žádné limity počtu/délky.
- **ⓘ vismo File.ashx není 100% v datech** — krnov.cz měl 0 příloh v `vismo_documents.jsonl`, ale živá stránka 5 dok (vyhlášení.pdf, podmínky, žádost.xls). Selektor příloh `vismo_detail.py` je host-specific křehký → u prázdných příloh ověř živě / re-harvest, jinak vrstva 2 hladoví (chybí deadline/amount).
- **ⓘ project ≠ WP-próza** — award-pole (grantee/amount/year) jdou jen ze strukturovaných zdrojů (dsw2 100 %, Lewis/Dynamo); WP `entity=project` jsou popisy iniciativ (grantee 6 %). granty.praha portál = rozhodnuté žádosti (Schválená/Nepřidělená dotace) → `project`, ne výzvy; otevřené výzvy Prahy na `praha.eu` CMS stránkách (samostatný harvest).
