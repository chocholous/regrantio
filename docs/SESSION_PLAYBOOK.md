# SESSION_PLAYBOOK.md — jak pracovat na regrantio (handoff pro příští session)

Operační příručka „JAK" (na rozdíl od `REMAINING.md` = „CO"). Přečti TENHLE soubor + `REMAINING.md`
+ `CLAUDE.md` na začátku každé session, ať neztratíš kontext a postup.

> Srovnáno se skutečností 2026‑11‑12: oddíly 0, 4 a 5 a spojování výstupu se vstupem. Recept (§1),
> pravidla kvality (§2) a pasti (§3) jsou z léta 2026 a platí.

---

## 0. Cíl & zlatá pravidla

**Cíl:** úplný a věrohodný katalog českých dotačních výzev pro produkt Grantio. Aktuální počty neopisuj
sem: měří je `docs/QUALITY.md` (12. 11. 2026: 4 242 záznamů, 136 zdrojů).

**ZLATÁ PRAVIDLA (neporušuj):**
1. **Jediná větev je `main`** a commituje se do ní jen po zelené bráně (`validate_release.py`).
   **Zápis do databáze produktu (`publish_db.py`) je zásah do běžícího produktu:** nejdřív
   `--dry-run` a porovnání po zdrojích, zapisuje vlastník nebo s jeho souhlasem
   (`the-machine-app/docs/tech/PROVOZ.md` §3).
2. **NEHALUCINUJ.** Co není v textu zdroje, nevyplňuj. `amount=null`, když částka není uvedená
   (bývá jen v PDF/zadávací dokumentaci). Nevymýšlej deadline. Nezakládej fiktivní záznamy
   (když zdroj nemá přímé dotace = MD → zdokumentuj a jdi dál, žádné fake záznamy).
3. **Status počítá KÓD, ne LLM** (`scripts/opportunities.py:compute_status`). Ukládej RAW
   `open_from`/`deadline`; appka i export status přepočítají klientsky k dnešku.
4. **Fix everything you find.** Když narazíš na bug/nekonzistenci, oprav ji hned (ne „flag for later").
5. **Po každém přidaném zdroji** aktualizuj `REMAINING.md` (odškrtni + stats) a commit+push.

---

## 1. Recept na přidání zdroje (hlavní smyčka)

```
1. PRŮZKUM   platform_map check → probe (WP REST? Kentico? bespoke?) → najdi dotace/výzvy sekci.
             „STRUKTURA PŘED PRÓZOU": zkus strukturovaný endpoint (WP REST CPT, XHR) dřív než HTML.
2. HARVEST   scripts/<src>.py → data/<src>_documents.jsonl
             tvar: {url, host, title, body_text, attachments:[{url,label}], n_attachments}
3. INPUT     python scripts/build_extract_input.py data/<src>_documents.jsonl --source <src> --out-dir data/<src>_in --force-type grant
4. VRSTVA 2  scripts/extractors/<src>.py  → data/<src>_out/grant_NN.json
             Výstup patří k ADRESE, ne k číslu souboru (od 2026-11-08): každý výstup nese `_source_id`
             (= `id` vstupu) a `ingest_rich` cizí výstup odmítne. Rozcestník, který výzvou není,
             se označí `{"_source_id": …, "_skip": "…"}` (docs/REFRESH.md).
5. INGEST    python scripts/ingest_rich.py --out-dir data/<src>_out --src data/<src>_in --existing data/opportunities.jsonl --out data/opportunities.jsonl --harvest-file data/<src>_documents.jsonl --today <YYYY-MM-DD>
6. TAIL      python scripts/refresh_run.py --tail-only   (přepočet → brána → export → kvalita; bez sítě)
7. KONFIG    fix_dataset PROVIDER_TYPE (slug→typ) · routing.yaml sources (host→harvester) ·
             platform_map.json final[host].grant=true · CLAUDE.md harvester řádek · REMAINING.md
8. VERIFY+   ověř (status / provider type / citace / kraj) → `python scripts/validate_release.py`
             (syntax + routing.yaml + kontrakt opportunities.json) → git add (KÓD/KONFIG/docs) → commit → push.
             CI (`.github/workflows/validate.yml`) tutéž validaci pustí na push — ale chytni to lokálně dřív.
```

**Vzory harvesterů/extraktorů (kopíruj podle podobnosti):**
- WP REST strukturované: `gacr.py`, `sfzp.py`, `tacr.py` (+ jejich `scripts/extractors/*.py`).
- Front-end HTML (REST chudý/401): `sfdi.py` (blok „Základní údaje"), `tacr.py` (front-end info).
- Seed-driven landing pages (velký web): `mpo.py`, `eagri.py`, `marwel.py`.
- Kentico kategorie + filtr ročníku: `mmr.py`.
- Vyčištění existujícího harvestu: `scripts/extractors/eeagrants.py` (strip JS/nav).

---

## 2. Pevná pravidla extrakce / kvality dat

- **Filtruj na AKTUÁLNÍ CYKLUS** u zdrojů, co listují všechny ročníky (`--since`, vzor `gacr.py`/`tacr.py`).
  Bez toho dataset zaplaví 6× tentýž program.
- **Vynech NEgrantové:** hub/listing/info/„aktuality"/administrativní stránky; duplicitní ročníky;
  overlap s už harvestovaným (např. MMR „Podpora bydlení" = SFPI, NEbrat znovu).
- **Scope discipline:** EU operační programy (OP TAK/OPŽP/OPZ+/OP JAK…) = **P3, MIMO** národní harvest.
  Mezinárodní partnerství (Eurostars/CET/DUT/QuantERA) = **P6/P7**. Nemíchej do národního zdroje.
- **zdroj_financovani kanon:** `narodni_rozpocet`, `eu_fondy`, `npo`, `ehp_norsko`, `krajsky`, `vlastni_zdroje`.
  Pro nové (Modernizační fond) klidně nový string — `consolidate.py` mapuje.
- **typ_poskytovatele vocab:** `samosprava_kraj/obec`, `ministerstvo`, `statni_fond`, `statni_agentura`
  (GAČR/TAČR), `nadace`/`firemni_nadace`/`nadacni_fond`, `zahranicni_fond` (EHP/Norsko, Visegrád, Swiss).
- **region/kraj:** samosprávě se kraj DOPLNÍ z hostu (`fix_dataset.py` sekce D, naučí se majoritou);
  národní poskytovatelé → `celostatni=true`. Nový samosprávný all-null host přidej do `SOURCE_KRAJ_MANUAL`.
- **Citace (grounding):** `evidence={pole: doslovná citace ze zdroje}`; `resolve_citations` je
  whitespace/case-insensitive, takže stačí věrná česká věta. Extrahuj z ČISTÉHO UTF-8, ne z mojibake konzole.
- **Closed historické bez přesného data:** když ROK znám (z URL) a období skončilo → year-end fallback
  (`<rok>-12-31`) je OK (status closed je jistý), nehádej konkrétní den.

---

## 3. Technické pasti (Windows + tento repo) — TADY se nejvíc ztrácí čas

- **cp1250 konzole:** Windows konzole neumí `→ · ⚠ – Č ž …`. (a) každý skript co tiskne non-ASCII má
  `if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8")`. (b) Když Bash výstup
  zmizí („Binary file (standard input) matches") nebo spadne na UnicodeEncodeError → **zapiš do scratchpad
  souboru a přečti Read toolem** (čte UTF-8 čistě). Nepiš dlouhé české printy do konzole.
- **TLS:** používej `http_util.urlopen` (auto-fallback přes Avast/gov WAF, varuje jednou). NE přímý urllib.
- **ASP.NET WebForms (mk.gov.cz):** celý obsah je v jednom `<form>` → v `to_text` **NEstrip `<form>`**.
- **Kentico (mmr/mk/mdcr):** kategorie vrací jen sdílený sidebar nav → **odečti nav** (diff proti hubu)
  ať najdeš program-linky; obsah bývá ve front-endu, ne v REST.
- **WP page-builder (Kadence=tacr, Elementor=sfpi):** REST `content` prázdný/CSS-noise → **front-end HTML**
  + strip `<style>` BLOKŮ (ne jen tagů).
- **WP bulk content payload (sfzp):** druhá stránka `?per_page=100&_fields=…content` vrátí HTML WAF stránku
  → fetchuj content jednotlivých stránek po id.
- **České datum má tečky** → na věty s datem NEpoužívej `[^.]`; použij date-aware regex `\d{1,2}\.\s*\d{1,2}\.\s*20\d\d`.
- **ASCII `"` uvnitř českého string-literálu** v `_extract.py` → SyntaxError (předčasné ukončení stringu).
  Použij kulaté uvozovky `„ "` nebo `"` uvnitř vůbec nedávej. Vždy `ast.parse` před spuštěním.
  ⚠ **Stejná past kousla `routing.yaml`** (2026-06-30): `„open"` (české otevírací `„` + ASCII zavírací `"`)
  v note u ec.europa.eu předčasně ukončilo YAML double-quoted string → `routing.py` padal od eu_ft commitu.
  Po editaci YAML/JSON/PY s českým textem VŽDY parse-test (`python -c "import yaml; yaml.safe_load(open(...))"`)
  nebo `py_compile`/`ast.parse`. Smoke-test celého repa: `py_compile` všech `scripts/*.py` + `scripts/extractors/*.py`.
- **Výstup vrstvy 2 se páruje podle `_source_id`** (adresa vstupu), ne podle čísla souboru; do
  2026‑11‑08 to bylo podle čísla a po přidání výzvy na web dostala každá další data své sousedky.
- **Velké downloady** (build_extract_input s desítkami příloh) pusť na pozadí (`run_in_background`);
  **foreground `sleep` je blokovaný** — nečekej sleepem, čekej na notifikaci.
- **Gitignored:** `data/` celé (`*_documents.jsonl`, `opportunities.jsonl`, `<src>_out/`, doc-store…)
  — VÝJIMKA: `scripts/extractors/<src>.py` se TRACKUJÍ (`.gitignore`: `/data/*` + `!/scripts/extractors/*.py`), jsou to
  vrstva-2 extraktory = kód. **Trackuj:** `scripts/*.py`, `scripts/extractors/<src>.py`, `routing.yaml`,
  `platform_map.json`, `CLAUDE.md`, `REMAINING.md`, `docs/grants_app.html`, `docs/opportunities.json`.

---

## 4. Export a zápis (po každé obnově)

- **Jeden katalog:** `data/opportunities.jsonl` = interní zdroj pravdy (řádek = záznam, verzovaný v gitu).
  Všechno do něj upsertuje a všechno z něj čte. Žádné varianty.
- `docs/opportunities.json` = publikovaná podoba katalogu (`scripts/export_api.py`, kontrakt 1.3
  v `docs/EXPORT.md`): jen kurátorovaná pole, RAW `open_from` a `deadline`, stav se počítá k dnešku
  až u čtenáře. Vzniká v tailu obnovy až ZA branou.
- **Do produktu** jde export přes `scripts/publish_db.py` (nejdřív `--dry-run`), ručně; postup
  a porovnání po zdrojích je v `the-machine-app/docs/tech/PROVOZ.md` §3. Opakovaný `--dry-run`
  po zápisu musí hlásit 0 změn.
- Prohlížeč `docs/grants_app.html` (`build_app.py`) a GitHub Pages (`pages.yml`, jen ručně)
  jsou pozůstatek z léta: Pages nejsou zapnuté a soubor je z 31. 7. Nic na nich nestojí.

---

## 5. Kde hledat / co dál

- **`REMAINING.md`** = co zbývá dnes a kdo má další krok.
- **`docs/coverage.md`** (poslední oddíl) = co v katalogu chybí a cesta ke každé mezeře (MAS, SZIF, nadace…).
- **`docs/QUALITY.md`** = měřená kvalita a stav každého zdroje; **`docs/REFRESH.md`** = třídy obnovy a pojistky.
- **`CLAUDE.md`** = příkazy, pevná pravidla, rozcestník.
- Starší stavové zápisy (červen až září 2026) jsou v `docs/archiv/REMAINING-do-2026-09.md`.
