# Recon ministerstva — kde žijí výzvy a jak je harvestovat (2026-06-10)

> POUZE recon (max ~10–15 requestů per web + 1× `xhr_discover`). MŠMT vynecháno (harvest běží jinde).
> Doktrína STRUKTURA PŘED PRÓZOU dodržena — u každého zdroje hledán strukturovaný endpoint dřív než próza.

## Souhrnná tabulka

| Ministerstvo / zdroj | Kde žijí výzvy (URL) | Přístup | Strukturovaná data | Pracnost | Pořadí |
|---|---|---|---|---|---|
| **MK** mk.gov.cz | `https://mk.gov.cz/zadosti-o-dotace-cs-2023` — 8 HTML tabulek (per oblast) | HTML listing (tabulky) | ✅ **ANO** — název + příjem žádostí OD/DO přímo v tabulce | **snadné** | **1** |
| **ESF (MPSV)** esfcr.cz | `https://www.esfcr.cz/prehled-vyzev-opz-plus` (a `/prehled-vyzev-opz`) | HTML listing (Liferay AssetPublisher) + **RSS** | ✅ semi — `div.article`: číslo výzvy, „Platnost do" (deadline), datum uveřejnění | **snadné** | **2** |
| **CzechAid (MZV/ČRA)** czechaid.gov.cz | `https://czechaid.gov.cz/dotace` — chronologický listing | HTML listing | ◐ listing ano, deadline v próze detailu („Lhůta pro podání žádosti… do …") | **snadné** | **3** |
| **MMR** mmr.gov.cz | `/cs/narodni-dotace/<program>/<program-ROK>/<podprogram>` (3 úrovně, Kentico B) | HTML hub→próza→`/getmedia/` | ❌ deadline jen v próze/PDF; RSS `?rss=Avizo/Novinky` jako change-feed | **střední** | 4 |
| **MPSV** mpsv.gov.cz | `/dotace-a-verejne-zakazky` → `/dotacni-rizeni`, NPO výzvy `31_xx` | Nuxt **SSR** — obsah v HTML/`__NUXT__` payloadu (žádný datový XHR) | ◐ celý strom v SSR payloadu; pole v próze | **střední** | 5 |
| **MZe/eAGRI** mze.gov.cz | `/public/portal/mze/dotace` (kompletní strom v mega-menu), harmonogramy výzev per OP | HTML listing (custom eAGRI portál, server-rendered) + RSS | ◐ `ea-listing__item` bloky (titul, datum, Stáhnout); deadline v próze/Zásadách | **střední** (⚠ WAF) | 6 |
| isprom.msmt.gov.cz | — (žádostní portál Nette; výzvy odkazuje na msmt.gov.cz) | — | ❌ | skip | — |
| dpmkportal.mk.gov.cz | — (žádostní portál, ASP.NET WebForms, ASD Software, za loginem) | — | ❌ | skip | — |

Apify není potřeba **nikde** — všech 6 reálných zdrojů je server-rendered, čisté HTTP stačí.

---

## Poznámky per zdroj (pro navazující parser, bez opakování průzkumu)

### 1. MK — mk.gov.cz ⭐ nejstrukturovanější
- **Centrální listing:** `https://mk.gov.cz/zadosti-o-dotace-cs-2023` (167 kB, server-rendered).
  **8 `<table>`** seskupených podle oblastí (Profesionální umění, …). Řádek = `NÁZEV DOTAČNÍ VÝZVY | PŘÍJEM ŽÁDOSTÍ (OD) | PŘÍJEM ŽÁDOSTÍ (DO) | ZPŮSOB PODÁNÍ`.
  V 1. buňce `<a href="/oborova-dotacni-rizeni-na-rok-2026-vyhlasovaci-podminky">` → detail s vyhlašovacími podmínkami (próza → Haiku na amount/eligible), ve 4. buňce link na dotační portál.
  Formáty dat kolísají: `23. 3. 2026` i `01.09.2025 (od 15.00)` — parser musí tolerovat čas v závorce.
- Rozcestník okruhů: `/dotacni-okruhy-cs-1137`. CMS bespoke (slug-id `…-cs-NNNN`), žádné `getmedia`/Kentico markery na novém webu.
- **dpmkportal.mk.gov.cz** (redirect z dpmkportal.mkcr.cz): ASP.NET WebForms (`__doPostBack`, `WebResource.axd`), vendor ASD Software, vše za registrací/loginem. Žádný veřejný katalog výzev — **jen žádostní portál**, katalog NE.

### 2. ESFCR — esfcr.cz (ESF/OPZ+ výzvy MPSV)
- **Liferay** (AUI, portlet `esfportalportletapplication`), plně server-rendered.
- Listing `https://www.esfcr.cz/prehled-vyzev-opz-plus`: opakovaný blok
  ```html
  <div class="article">
    <h3 class="article-heading"><a href="/vyzva-062-opz-plus">…</a></h3>
    <p>Číslo výzvy: 062</p>
    <p>Platnost do: 30. 09. 2026 14:00</p>
    <div class="meta"><span class="publish-date">28. 5. 2026</span> … Určeno pro: <strong>Žadatel</strong></div>
  </div>
  ```
  → **deadline („Platnost do") přímo v listingu**, deterministicky.
- **RSS:** `https://www.esfcr.cz/prehled-vyzev-opz-plus/-/asset_publisher/SfUza2tXdZGm/rss?p_p_cacheability=cacheLevelFull` — change-feed zdarma.
- Detail výzvy = `/vyzva-NNN-opz-plus` (server-rendered, přílohy). Stránkování AssetPublisheru přes `_101_INSTANCE_*_delta`/`cur` parametry (ověřit při harvestu). Starší výzvy: `/prehled-vyzev-opz`, tematické: `/zamestnavani-a-vzdelavani-aktualni-vyzvy`, `/detske-skupiny-aktualni-vyzvy`, `/rovnost-zen-a-muzu-aktualni-vyzvy`.

### 3. CzechAid — czechaid.gov.cz (pozor: czechaid.cz → .gov.cz)
- **NETservis CMS** (`<meta name="author" content="NETservis s.r.o."/>`), server-rendered, jQuery.
- Listing `https://czechaid.gov.cz/dotace` (63 kB): chronologie výzev, odkazy `/dotace/<slug>` (slug nese stav: `zruseno-…`, `uzavrena-…`, `dotacni-vyzva-…`).
- Detail (`/dotace/dotacni-vyzva-…`): próza s „**Lhůta pro podání žádosti** o poskytnutí dotace … do 25. …" + přílohy `/cs/file/<md5>/<id>/<název>.pdf|zip` (vyzva+přílohy, QA). → tenký parser listingu + Haiku na detail.
- Výsledky řízení (award) tamtéž jako PDF `Vysledek dotacniho rizeni_*.pdf` → entity `project`, ne výzva.

### 4. MMR — mmr.gov.cz (Kentico šablona B, potvrzeno)
- **3 úrovně:** hub `/cs/narodni-dotace` → program-rok (`/cs/narodni-dotace/podpora-a-rozvoj-regionu/podpora-obnovy-a-rozvoje-regionu-2026` — téměř prázdný rozcestník!) → **podprogram = skutečný detail výzvy** (`…/porr-vesnice-roku`: próza + **19× `/getmedia/`** dokumentů). Interní odkazy mají legacy tvar `/Narodni-dotace/...` (case-insensitive, místy mezery/závorky v URL — escapovat).
- Žádný centrální listing „Vyhlášené výzvy s daty" nenalezen; deadline jen v próze/PDF podprogramu → tenký HTML crawler (BFS od `/cs/narodni-dotace`, hloubka 3) + Haiku. Neredukovatelná próza potvrzena.
- **RSS hub:** `/cs/ostatni/web/rss` — kanály `?rss=Avizo|Novinky|EUDotace|IROP|AllPageFefed…` (Avizo = tiskové avízo, ne čisté výzvy; použitelné jako change-detektor).
- EU výzvy MMR žijí na dotaceeu.cz/IROP (už pokryto `kentico_irop.py`).

### 5. MPSV — mpsv.gov.cz (Nuxt SSR — NENÍ to klasická SPA!)
- mpsv.cz → mpsv.gov.cz. **Nuxt 3, plný SSR**: obsah je v HTML + `window.__NUXT__` payloadu (~1,3 MB/stránka). `xhr_discover` zachytil **jediný XHR = chatbot** `da.mpsv.cz/api/v1/*` — žádné datové API pro obsah. `/cms/api` existuje (404 JSON na root), ale frontend ho nevolá → ignorovat.
- → **statické HTTP stačí**; parsovat rendrovaný HTML (nebo `__NUXT__` JSON, obsahuje i navigační strom celé sekce).
- Vstupy: `/dotace-a-verejne-zakazky` (hub, v payloadu kompletní podstrom včetně historie), `/dotacni-rizeni` (oblasti: sociální služby, rodina, seniorské organizace…), NPO výzvy `Výzva č. 31_22_002 …` (zachyceno v payloadu). Detail = próza + přílohy → Haiku.
- ESF/OPZ+ výzvy MPSV **nejsou tady** — žijí na esfcr.cz (viz #2).

### 6. MZe/eAGRI — mze.gov.cz (custom eAGRI portál)
- eagri.cz → `https://mze.gov.cz/public/portal/mze/` (portál migrován). `dotace.mze.cz` **neexistuje** (DNS).
- **⚠ WAF**: plain UA `Mozilla/5.0` / rychlé sekvence → blok „Váš přístup byl … zablokován" (HTML s helpdesk@mze.cz). S plnými browser-hlavičkami (UA Chrome, Accept, Accept-Language) a throttlingem (~1 req/5–10 s) prochází.
- Server-rendered; **mega-menu obsahuje kompletní strom** sekce Dotace (1 fetch `/public/portal/mze/dotace` = 195 kB ≈ sitemap, ~900 odkazů `dotac*`).
- Struktura: `/public/portal/mze/dotace/narodni-dotace/<program>/<program-pro-rok-2026>` = stránka výzvy. Obsah = bloky `div.ea-listing__item` → `ea-flow__row` (titul, datum, anotace) + download `a.ea-link--standalone href="/public/portal/mze/-aNNNNN---<hash>/<slug>?_linka=aNNNNN"` (pdf/doc — Zásady, vyhlášení, zásobníky žádostí). Deadline v próze/Zásadách → Haiku.
- Harmonogramy výzev OP: `/public/portal/mze/dotace/szp-pro-obdobi-2021-2027/harmonogram-vyzev`, `/public/portal/mze/dotace/operacni-program-rybarstvi-na-obdobi-2021-2027/harmonogram-vyzev`.
- **RSS:** `/public/portal/mze/rss` (novinky obsahují vyhlášení výzev, např. „VI. Výzva … podprogram 129 403"). Aplikační registry (`/public/app/eagriapp/*`) = registry příjemců/akcí, ne výzvy.
- Pozn.: žádosti zemědělských dotací administruje SZIF (szif.cz) — mimo scope tohoto reconu.

### isprom.msmt.gov.cz — skip
- Nette **žádostní portál** (login/registrace, metodika, nápověda). Homepage „aktuality" odkazují výzvy na `msmt.gov.cz/mladez/vyzva-…` → výzvy žijí na MŠMT (harvest běží jinde). Žádný veřejný JSON katalog výzev.

---

## Ověřené příkazy / vzory (reprodukce)

```bash
# ESFCR listing — deterministický parse div.article (+ RSS change-feed)
curl -s -A "$UA" https://www.esfcr.cz/prehled-vyzev-opz-plus

# MK tabulky výzev (8× <table>, od/do data)
curl -s -A "$UA" https://mk.gov.cz/zadosti-o-dotace-cs-2023

# MZe — POMALU, plné hlavičky, jinak WAF blok
curl -s -A "$UA_CHROME" -H "Accept-Language: cs-CZ" https://mze.gov.cz/public/portal/mze/dotace

# MPSV — SSR, žádný XHR (ověřeno scripts/xhr_discover.py --url ".../dotace-a-verejne-zakazky" → jen chatbot da.mpsv.cz)
curl -s -A "$UA" https://mpsv.gov.cz/dotacni-rizeni   # obsah v HTML/__NUXT__
```
