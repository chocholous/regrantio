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
