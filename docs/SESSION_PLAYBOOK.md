# SESSION_PLAYBOOK.md — jak pracovat na regrantio (handoff pro příští session)

Operační příručka „JAK" (na rozdíl od `REMAINING.md` = „CO"). Přečti TENHLE soubor + `REMAINING.md`
+ `CLAUDE.md` na začátku každé session, ať neztratíš kontext a postup.

---

## 0. Cíl & zlatá pravidla

**Cíl:** kompletní, konkurenceschopná česká grantová databáze (7 vrstev pokrytí — viz vize-tabulka
v `REMAINING.md`). Aktuálně **2749 záznamů / 127 poskytovatelů** na větvi `coverage-expansion-next`.

**ZLATÁ PRAVIDLA (neporušuj):**
1. **NIKDY nemerguj do `main`** bez explicitního pokynu uživatele. Je to JEHO větev. Pracuj na
   `coverage-expansion-next`.
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
4. VRSTVA 2  data/_<src>_extract.py  → data/<src>_out/grant_NN.json   (JOIN je podle BASENAME = stejný index jako _in!)
             skip nějaký záznam = NEzapisuj jeho out soubor.
5. INGEST    python scripts/ingest_rich.py --out-dir data/<src>_out --src data/<src>_in --existing data/opportunities_v2.jsonl --out data/opportunities_v2.jsonl --harvest-file data/<src>_documents.jsonl --today <YYYY-MM-DD>
6. TAIL      consolidate.py → fix_dataset.py --today <dnes> → build_app.py
             → cp data/grants_app.html docs/grants_app.html → export_api.py (→ docs/opportunities.json)
7. KONFIG    fix_dataset PROVIDER_TYPE (slug→typ) · routing.yaml sources (host→harvester) ·
             platform_map.json final[host].grant=true · CLAUDE.md harvester řádek · REMAINING.md
8. VERIFY+   ověř (status / provider type / citace / kraj) → git add (KÓD/KONFIG/docs) → commit → push.
```

**Vzory harvesterů/extraktorů (kopíruj podle podobnosti):**
- WP REST strukturované: `gacr.py`, `sfzp.py`, `tacr.py` (+ jejich `data/_*_extract.py`).
- Front-end HTML (REST chudý/401): `sfdi.py` (blok „Základní údaje"), `tacr.py` (front-end info).
- Seed-driven landing pages (velký web): `mpo.py`, `eagri.py`, `marwel.py`.
- Kentico kategorie + filtr ročníku: `mmr.py`.
- Vyčištění existujícího harvestu: `data/_eeagrants_extract.py` (strip JS/nav).

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
- **ingest JOIN = basename** `grant_NN.json`; out musí mít stejné indexy jako in; přeskočení = nezapsat soubor.
- **Velké downloady** (build_extract_input s desítkami příloh) pusť na pozadí (`run_in_background`);
  **foreground `sleep` je blokovaný** — nečekej sleepem, čekej na notifikaci.
- **Gitignored:** `data/` celé (`*_documents.jsonl`, `opportunities_v2.jsonl`, `<src>_out/`, doc-store…)
  — VÝJIMKA: `data/_<src>_extract.py` se TRACKUJÍ (`.gitignore`: `/data/*` + `!/data/_*_extract.py`), jsou to
  vrstva-2 extraktory = kód. **Trackuj:** `scripts/*.py`, `data/_<src>_extract.py`, `routing.yaml`,
  `platform_map.json`, `CLAUDE.md`, `REMAINING.md`, `docs/grants_app.html`, `docs/opportunities.json`.

---

## 4. Deploy & produkt (po každém běhu)

- `docs/grants_app.html` = appka (deploy `pages.yml` → větev `gh-pages`, per-branch). Data inline v HTML;
  status se přepočítává KLIENTSKY. **Musíš cp z `data/grants_app.html` po build_app**, jinak je live stale.
- `docs/opportunities.json` = veřejný kurátorovaný export pro produkt (`scripts/export_api.py`):
  `{meta{schema_version,generated_at,count,status_rule}, grants[…]}`. Jen veřejná pole (BEZ `_*`,
  `provenance`, `extra`, `foundation_id`), RAW `open_from`/`deadline`. Stabilní Pages URL:
  `https://chocholous.github.io/regrantio/branches/<branch>/opportunities.json`.
- `gen_pages_index.py` kopíruje `docs/opportunities.json` do site per branch.

---

## 5. Kde hledat / co dál

- **`REMAINING.md`** = priority a mezery (P1 fondy ✓ · P2 ministerstva · **P2b agentury: NSA ✓ → SZIF/Úřad vlády další** ·
  P3 EU OP · P4 nadace 17→40+ · P5 chybějící města · P6 Brusel · P7 mezinárodní). Vize-tabulka = stav vs cíl.
- **`CLAUDE.md`** = architektura, příkazy, doc rozcestník.
- **`docs/`** = platform_playbook, detection, coverage, data_reuse, apify_howto.
- **Další na řadě (k 2026-06-29): SZIF — Státní zemědělský intervenční fond** (`szif.cz`; PRV/SZP, národní
  dotace v zemědělství) nebo **Úřad vlády** (Rada vlády pro NNO), pak nadace (P4) / EU OP (P3). EU/Brusel (P6) =
  velký zdroj přes EU Funding & Tenders Portal (strukturované API). (NSA HOTOVO 2026-06-29: 21 výzev sportu, statni_agentura.)
