# REFRESH.md — jak udržet dataset aktuální (update strategie)

Databáze NESMÍ být jednorázový snapshot. Tenhle dokument říká, **co re-harvestovat, jak často a jak
to bezpečně dotáhnout do produktu**. Kvalita > počet: refresh nesmí zhoršit data ani smazat granty
z produktu kvůli rozbitému běhu.

Doprovodný nástroj: **`python scripts/refresh.py`** = živý checklist (zdroj → harvester → tier →
počet záznamů → příkaz) + gap-check. Spusť ho na začátku každého refresh kola.

---

## 1. Dvě věci, které „stárnou" jinak

1. **Status (open/closed)** — stárne KAŽDÝ DEN, ale NEvyžaduje re-harvest. Status se počítá z
   `open_from`/`deadline` klientsky k dnešku (appka i produkt, viz `docs/PRODUCT_API.md §5`).
   → „dnes zavřené" výzvy zmizí z otevřených i bez nového exportu. **Žádná akce.**
2. **Obsah (nové/změněné/zaniklé výzvy)** — stárne v řádu týdnů a VYŽADUJE re-harvest zdroje.
   → tohle je vlastní náplň refreshe (§3).

---

## 2. Kadence (realistická, bez placených nástrojů)

Otevřené výzvy se nemění po hodinách. Doporučená kadence:

| Co | Jak často | Proč |
|---|---|---|
| **structured** zdroje (WP REST / JSON API / inline-JS) | **týdně** | levné (vteřiny–minuty), čistá re-harvestovatelnost; nové výzvy přibývají průběžně |
| **html** zdroje (front-end listing/detail parsery) | **2 týdny** | levné, ale parser citlivý na redesign → ověř, že počet nespadl |
| **seed** zdroje (mpo/eagri/mmr/vlada/marwel/sfk) | **měsíčně + při novém ročníku** | nový dotační ročník = doplnit seed URL ručně (viz harvester `--seeds`) |
| **browser** zdroje (eu_ft, lewis SPA) | **měsíčně** | potřebuje Playwright/odposlech; EU F&T má vlastní deadline filtr |
| **export + deploy** (tail) | **po každém refresh kole** | `build_app` → `export_api` → commit → Pages |

Tieru zdroje se ptej `scripts/refresh.py` (sloupec `tier`). Nemusíš dělat všechno najednou —
refreshuj po tierech / skupinách a commituj průběžně.

---

## 3. Refresh jednoho zdroje (smyčka)

Re-harvest je TÝŽ recept jako přidání zdroje (viz `docs/SESSION_PLAYBOOK.md §1`), jen běží nad
existujícím parserem. Pro zdroj `<src>` s harvesterem `scripts/<h>.py`:

```
1. HARVEST   python scripts/<h>.py                  # → data/<src>_documents.jsonl (přepíše)
             u WP/listingových zdrojů s ročníky použij --since/--year ať nebereš staré ročníky
2. INPUT     python scripts/build_extract_input.py data/<src>_documents.jsonl --source <src> --out-dir data/<src>_in --force-type grant
3. VRSTVA 2  python data/_<src>_extract.py           # deterministický extraktor (TRACKOVANÝ v gitu)
4. INGEST    python scripts/ingest_rich.py --out-dir data/<src>_out --src data/<src>_in \
                --existing data/opportunities_v2.jsonl --out data/opportunities_v2.jsonl \
                --harvest-file data/<src>_documents.jsonl --today <YYYY-MM-DD>
5. TAIL      python scripts/consolidate.py
             python scripts/fix_dataset.py --today <YYYY-MM-DD>
             python scripts/build_app.py && cp data/grants_app.html docs/grants_app.html
             python scripts/export_api.py             # → docs/opportunities.json (+ content_hash, pojistka)
6. COMMIT    git add -A && git commit && git push
```

**ingest_rich je idempotentní upsert podle `id`** (= URL): re-harvest stejné výzvy ji aktualizuje
(ne duplikuje); nová výzva přibude; výzva, kterou zdroj stáhl, v novém harvestu chybí → zůstane v
datasetu jako poslední známý stav (consolidate/fix neodstraní). Tvrdé odebrání zaniklých výzev řeš
vědomě (viz §5).

---

## 4. Bezpečnost refreshe (aby rozbitý běh neublížil produktu)

1. **Pojistka v exportu:** `export_api.py --min-ratio 0.9` zastaví export, když by měl <90 % záznamů
   předchozího (rozbitý harvest). Rozbitý běh tak NEsmaže granty z produktu. Vědomé velké smazání: `--force`.
2. **Po každém harvestu zkontroluj počet:** `scripts/refresh.py` ukáže záznamy/zdroj — když u zdroje
   spadne na ~0, parser se nejspíš rozbil (redesign webu) → oprav parser, ne dataset.
3. **Integrita před exportem:** `fix_dataset.py` audituje (0 bad_amount/date/dup/status_mismatch).
   Nepřepisuj produkt, dokud audit nečistý.
4. **Nehalucinovat při refreshi:** stejné zlaté pravidlo — `amount=null`/`deadline=null` zůstává null.

---

## 5. Odebírání zaniklých výzev (volitelné, vědomé)

Default chování = výzvy se v datasetu drží i po zmizení ze zdroje (closed mají referenční hodnotu).
Produkt řeší „zmizení ze zdroje" sám: výzva, jejíž `id` v novém exportu chybí, se v produktu
soft-deletuje (viz `docs/PRODUCT_API.md §6`). Pokud chceš čistit i interní dataset, dělej to vědomě
per-zdroj (re-harvest celý zdroj → nahraď jeho podmnožinu), ne plošně.

---

## 6. Známé refresh-gapy (k dořešení, ne blokující)

`scripts/refresh.py` gap-check rozlišuje:
- **family-covered** (43 zdrojů) — host je v `platform_map.json`, kryje ho FAMILY harvester
  (vismo/dsw2/kentico). Re-harvestovatelné; jen nejsou per-host v `routing.yaml sources:`. Refresh:
  spusť family harvester (`vismo.py`/`dsw2.py`/`kentico_irop.py`) na daný host. **OK.**
- **ORPHAN** (cca 20 „zdrojů") — dvě skupiny:
  1. **slug↔host mismatch** (mv, msmt, mzcr, mzp, mkcr, nadacevia…): zdroj JE registrovaný, jen
     dataset `source` je slug a routing klíč je host (`mv.gov.cz`). Reálně refreshovatelné svým
     harvesterem (`mv_cms.py`, `marwel.py`, drupal/kentico). Kosmetika, ne gap.
  2. **⚠ jednorázový nadační batch `h19_*`** (fondbudoucnosti 36, socialninadacnifond 12,
     fondpaliativnipece 12, nadaceokd 8, kellner 5, vdv 5, nasedite 4, krasapomoci 2, nadacecs 2,
     kontobariery 1, nadacetm 1, voracek 1…): sklizeno starým hromadným během (`harvest19_*` /
     `h19_*.jsonl`), BEZ dedikovaného registrovaného harvesteru a bez `data/_<src>_extract.py`.
     **To je jediný skutečný reprodukční gap.** Tyto nadace se dnes nedají čistě re-harvestovat
     stejným receptem; většina jsou navíc ne-WP/blokující weby (viz REMAINING recon). Do produkce:
     buď je dotáhnout na per-web parser (až bude čas, P4), nebo je ponechat jako poslední známý stav.

---

## 7. Plně automatizovaný refresh (proč zatím ne)

Jeden „zmáčkni tlačítko" job pro VŠECHNY zdroje záměrně nestavíme: harvestery jsou různě drahé
(Playwright, WAF/proxy, seed-driven ruční ročníky) a vrstva 2 části jede přes LLM workflow uvnitř
Claude Code. Realistický provoz = **refresh po tierech** (`refresh.py` jako checklist), structured
týdně, zbytek řidčeji. Pokud bude potřeba scheduler, kandidát je GitHub Actions cron na samotné
**structured** harvestery (bez Playwrightu/LLM) → PR s diffem datasetu k revizi. Není to ale nutné
pro produkční provoz: export je idempotentní a produkt sync zvládá inkrementálně (content_hash).
