# REMAINING.md — co zbývá

Stav k **2026‑11‑12**. Čísla se sem neopisují, měří je brána a
[`docs/QUALITY.md`](docs/QUALITY.md); tady je jen, co zbývá, proč a kdo má
další krok. Starší stavové zápisy (červen až září 2026) jsou v
[`docs/archiv/REMAINING-do-2026-09.md`](docs/archiv/REMAINING-do-2026-09.md).
Úplný seznam před spuštěním produktu vede aplikace
(`the-machine-app/docs/PRUVODCE.md` §19); položky tady jsou jeho datová část.

## Kde to je

| | |
|---|---|
| katalog | 4 242 záznamů ze 136 zdrojů, 1 821 živých (otevřené, vyhlášené, bez známé lhůty) |
| kontrakt exportu | 1.3 |
| brána | 13 kontrol, 201 testů v 10 souborech, zelená |
| poslední zápis do databáze produktu | běhy #65 a #66, 12. 11. |
| zdroje ověřené do 21 dnů | 122 ze 136; 8 má cestu a nikdy se neověřilo, 3 jsou bez cesty, 2 zmrazené, 1 stárne |
| živé záznamy ověřené u zdroje do 7 dnů | 1 341 z 1 821; 426 je bez razítka |

## Co zbývá

| # | co | proč | priorita | další krok má |
|---|---|---|---|---|
| 1 | **Repozitář je veřejný a nese celý katalog i export** | produkt prodává přístup ke katalogu (rozhodnutí z 11. 9. a 30. 9. v aplikaci); kdokoli si ho dnes stáhne z GitHubu | P0 | vlastník: přepnout repozitář na soukromý (CI poběží dál), nebo rozhodnout, že veřejný zůstává |
| 2 | **Automatická obnova na serveru** (návrh R1 v průvodci aplikace) | obnova je ruční a stojí na stroji a účtu jednoho člověka; čerstvost je to, za co se platí | P0 | vlastník: klíč k modelu a rozhodnutí; pak vývoj |
| 3 | **Klíč k modelu v `.env`** (`ANTHROPIC_API_KEY`) | třídy C a P (38 zdrojů) bez něj čtou agenti v sezení Claude Code; na pravidelný provoz to nestačí | P0 | vlastník |
| 4 | **Pokrytí: MAS, SZIF, nadace, města** | hlavní cílovka (malé obce, spolky) má tam většinu peněz; mapa a cesta ke každé mezeře je v [`docs/coverage.md`](docs/coverage.md), poslední oddíl | P0 až P1 | vlastník vybere pořadí, pak vývoj |
| 5 | **Lhůta bez roku u zdrojů čtených modelem** | u Hodonína dalo čtení starým ročníkům letošní rok (opraveno 11. 11., `8328fd9`); kde výpis nenese datum vyvěšení, chybí opora a stejná vada může být jinde | P1 | vývoj: projít zdroje tříd C a P, kde lhůta přišla bez roku |
| 6 | **Dva programy s více otevřenými ročníky** (Dobříš 2026, Individuální dotace Pardubického kraje) | brána je hlásí jako varování (práh je 5); buď jsou to dva skutečné tituly, nebo zdvojený záznam | P2 | vývoj: ověřit u zdroje |
| 7 | **8 zdrojů s cestou, které se nikdy neověřily, a 3 bez cesty** (Konto Bariéry, Nadace táta a máma, Nadace Jakuba Voráčka) | jejich záznamy nemají razítko čerstvosti | P1 | vývoj: pustit třídu P, zbylým zapsat cestu nebo je vyřadit |
| 8 | **Doložitelnost citací** | ve zdroji se dohledá 50,9 % citací; u lhůty 62 %, u částky 58 %, u ostatních polí do 17 % | P1 | vývoj: s klíčem přečíst znovu, co citaci ztratilo |
| 9 | **Korpus stažených dokumentů bez zálohy** (asi 6,7 GB mimo `data_bundle/`, jediná kopie na jednom disku) | ztráta disku znamená nový sběr | P1 | vlastník: kam zálohovat; pak vývoj |
| 10 | **`data_bundle/` v gitu** (1,8 GB ve stromu, 2 GB v historii) | klon je pomalý; historie se nepřepisuje, jen se přestane přidávat | P2 | vlastník: publikovat balík mimo git |
| 11 | **GitHub Pages a `docs/grants_app.html`** (soubor z 31. 7., 16 MB) | Pages nejsou zapnuté, workflow je jen ruční, prohlížeč nikdo nepoužívá; publikace by zveřejnila katalog | P2 | vlastník: smazat workflow a soubor, nebo je oživit |

## Co se nedělá (vědomě)

- Zdroje, které robotům vracejí 403 (tři stránky MŽP), se neobcházejí; jen
  dohodou nebo jiným zdrojem.
- Výzvy Evropské komise se z katalogu nevyřazují, produkt je počítá zvlášť.
- Zápis do databáze produktu se neautomatizuje, dokud o tom vlastník
  nerozhodne (bod 2).
