# Apify — kdy a jak (jen na to, co statický fetch nezvládne)

Apify NENÍ default. Statický fetch + skripty zvládnou ~80 % zdrojů. Apify jen pro:

## Kdy Apify
1. **SPA (JavaScriptem renderované)** — obsah není v HTML, načítá se z API přes JS:
   - `grantys` (`ng-app="grantys.client"`, gated API 403 bez session)
   - `custom_spa` (OLC Webdesign: czso/eagri/mpsv)
   - `react_nextjs`/`vue_nuxt`/`angular` nadace (donio, kellnerfoundation, dotace.olomouc angular)
2. **WebForms postback** — obsah za `__doPostBack` (ne GET):
   - `aspnet_webforms` CZI (granty.praha.eu, zadosti.sfzp.cz, dotace.kr-jihomoravsky)
   - MV `mv.gov.cz` vícekapitolové `?q=` (chnum base64) — kapitoly přes postback
3. **WAF-blokované** zdroje z ERR_fetch (kde retry nepomohl).

## Jak (mcpc / Apify REST — viz [[apify-mcpc-setup]])
- Actor: **`apify/website-content-crawler`** — `startUrls`, `maxCrawlDepth` (0 pro single, vyšší pro listing→detail), JS rendering ON → vrací **markdown** obsahu.
- Pro listingy: crawl s depth=1-2 na dotační sekci → markdown všech detailů.
- Výstup → stejný formát jako statický harvest (`{url, title, text, document_urls[]}`) → pokračuje fáze 2-6.
- Dokumenty (PDF/DOC) i z Apify markdownu → `dsw2_fetch.py` download+convert.

## Gotchas
- mcpc 0.3.0, token v env; `get-dataset-items` (ne get-actor-output); REST API pro stažení datasetu.
- Headless ≠ vždy nutný: vždy nejdřív ověř, jestli obsah NENÍ ve statickém HTML (dsw2 vypadal jako SPA, ale data byla inline) — ušetří kredity.
- Interaktivně-autentizované MCP servery můžou v headless/cron běhu chybět.

## Rozhodovací strom
```
homepage statický fetch → je obsah v HTML?
  ANO → skript (REST/HTML/inline-JS)             ← většina
  NE (1808B shell / ng-app / __NEXT) → Apify SPA render
  obsah za __doPostBack ?q= → Apify (klikání/render)
  403/WAF i s retry → Apify (jiná IP/browser)
```
