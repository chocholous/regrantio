# Engineering Audit — regrantio / opportunity_pipeline

Audit větve `main`. Harvestery na větvi `coverage-expansion` jsou mimo rozsah.

Severity: **Critical** rozbije výstup / tichá ztráta dat · **High** vážná degradace nebo blokuje běh · **Medium** lokální chyba / past · **Low** nekonzistence / dead code.

| # | Sev | Problém |
|---|-----|---------|
| 1 | Medium | Re-běh `opportunities.py` přepíše rich `opportunities.jsonl` plochým bez `facets` |
| 2 | Medium | `vismo_detail.py` ořezává tělo na 8000 znaků mimo `limits.json` |
| 3 | High | `json_repair` chybí v `requirements.txt` (povinný krok vrstvy 2 spadne) |
| 4 | Medium | Šest různých referenčních „dnešních" dat pro výpočet statusu |
| 5 | Medium | `pipeline.py` produkuje prázdná pole (stub vydávaný za driver) |
| 6 | Medium | `os.system("rm -f")` neportovatelné na Windows + neescapované |
| 7 | Medium | TLS verifikace vypnutá (`CERT_NONE`) v 11 scraperech |
| 8 | Medium | App odkazy `raw_rel/md_rel/txt_rel` se nikdy nevyplní |
| 9 | Medium | Nekonzistentní padding indexů (2 vs 4) mezi builder/workflow/repair |
| 10 | Medium | Konverze dokumentů jen pro macOS — doc/docx/odt/pptx mimo macOS bez textu |
| 11 | Low | Grounding citací závisí na `--link-docs`; `ingest_rich` ten krok nemá |
| 12 | Medium | Hardcoded `data/h19_<web>.jsonl` join — sedí jen na část zdrojů |
| 13 | Medium | `kentico_irop.py` stahuje max 8 příloh (hardcoded cap) |
| 14 | Medium | Natvrdo psané `/tmp` a `/opt/homebrew` cesty ve vrstvě 2 |
| 15 | Low | Konverzní binárky volány bez preflight kontroly dostupnosti |
| 16 | Medium | `vismo.py` hardcoded BFS strop 40/hloubka 2 mimo `limits.json` |
| 17 | Medium | Tři nekompatibilní výstupní schémata vrstvy 1 vs jeden konzument |
| 18 | Low | `store_url` nevrací `md_path`, builder ho preferuje → vždy `.txt` |
| 19 | Low | `wp_harvest.py` strop 100 stran natvrdo |
| 20 | Low | `eeagrants.py` komentář ≠ kód; doc regex bez `ods`/`pptx` |
| 21 | Low | Mrtvá závislost `pymupdf4llm` + natvrdo psané limity mimo `limits.json` |
| 22 | Low | Cross-source dedup chybí → duplicitní výzvy napříč zdroji |
| 23 | Low | `schema/opportunity_schema.md` nesouhlasí s implementací |
| 24 | Low | Trojí redundance ingest/facety/náhled; `facet_wf.js` nezapojen |
| 25 | Low | Drift modelu: docs Haiku, kód defaultuje Sonnet |
| 26 | Medium | Hardcoded absolutní cesta autora `/Users/chocholous/…` ve 3 workflow |
| 27 | Low | Detekční/mining skripty zapisují výstup do rootu, ne `platform_data/` |
| 28 | Low | „Safety cap 150k" deklarovaný v docs, ale nikde neimplementovaný |
| 29 | Low | `prompts/classify_type.md` zaostává za živým promptem |

---

### 1. Re-běh `opportunities.py` přepíše rich `opportunities.jsonl` plochým — Medium
**Kde:** `scripts/opportunities.py:369` (OUT default `data/opportunities.jsonl`, ploché schéma bez `facets`) vs `scripts/ingest_rich.py:152` (`opportunities_v2.jsonl`, s `facets`) vs `scripts/build_app.py:455` (čte `data/opportunities.jsonl`, UI potřebuje `facets`).
**Problém:** `build_app` čte `data/opportunities.jsonl`, který musí být rich (s `facets`). Plochý ingest `opportunities.py` ale zapisuje do TÉHOŽ názvu — jeho re-běh přepíše rich soubor záznamy BEZ `facets`.
**Dopad:** Latentní past — kdo spustí `opportunities.py --reset`, tiše degraduje vstup appky (prázdné fasety). Kolize jmen mezi dvěma ingest cestami.
**Fix:** Oddělit výstupní jména (plochý vs rich) nebo sjednotit na jeden ingest; `build_app` ať čte explicitně rich soubor.

### 2. `vismo_detail.py` ořezává tělo na 8000 znaků — Medium
**Kde:** `scripts/vismo_detail.py:94` (`body[:8000]`), `:117` (`[:1500]`); `scripts/mv_cms.py:72` (`[:1200]`).
**Problém:** Natvrdo zakódovaný ořez těla mimo `limits.json` (kde `input_truncation = null` s komentářem „ořez sráží amount 27 %→90 %"). Porušuje vlastní doktrínu „data vždy celá".
**Dopad:** Tělo delší než limit se do LLM i groundingu dostane useknuté; roste s délkou stránek.
**Fix:** Odstranit `[:8000]`/`[:1500]`/`[:1200]`; případný strop jen jako `safety` v `limits.json` s logem.

### 3. `json_repair` chybí v `requirements.txt` — High
**Kde:** `scripts/repair_out.py:16` (`import json_repair`); `requirements.txt` (neobsahuje).
**Problém:** `repair_out.py` je povinný post-krok vrstvy 2 (`extract_wf.js` záměrně zapisuje syrový JSON). Závislost není deklarovaná.
**Dopad:** Na čistém prostředí `repair_out.py` → `ModuleNotFoundError`, výstupy vrstvy 2 zůstanou nekanonizované.
**Fix:** Přidat `json-repair` do `requirements.txt`.

### 4. Šest různých referenčních dat pro status — Medium
**Kde:** `pipeline.py:21` (2026-06-01), `scripts/kentico_irop.py:11` (2026-06-01), `scripts/vismo_detail.py:16` (2026-05-30), `scripts/ingest_rich.py:153` (2026-06-01), `scripts/opportunities.py:375` (`date.today()`), `scripts/build_app.py:423` (natvrdo `"2026-06-05"`).
**Problém:** Status se počítá v kódu, ale „dnešek" je v každém modulu jiný; vismo navíc přebírá status z harvest-time.
**Dopad:** Tatáž výzva (deadline 1.–4. 6. 2026) vyjde v různých zdrojích open vs closed; coverage statistika nesedí s kartami.
**Fix:** Jeden zdroj `TODAY` (env nebo `limits.json`) čtený všemi moduly; status přepočítat při ingestu.

### 5. `pipeline.py` produkuje prázdná pole — Medium
**Kde:** `pipeline.py:74-88,114-134`.
**Problém:** `extract_fields()` vrací stub `{deadline:None, amount:None, _todo:…}`, `classify_type()` vrací jen hint; `run()` to zapíše. Soubor je v README prezentován jako spustitelný driver.
**Dopad:** `pipeline.py --reuse-all` vyrobí validně vypadající `opportunities.jsonl`, kde má každý záznam null pole.
**Fix:** Smazat / přesunout do `legacy/` a odstranit z příkazů v README, nebo nechat `main()` skončit chybou s odkazem na workflow cestu.

### 6. `os.system("rm -f …")` — neportovatelné a neescapované — Medium
**Kde:** `scripts/build_extract_input.py:56`.
**Problém:** Spoléhá na POSIX `rm` + shell glob; `args.out_dir` se vkládá do shellu bez escapování.
**Dopad:** Na Windows se staré `grant_*.json` **tiše** nesmažou (`cmd.exe` glob nerozvine, `-f` potlačí chybu) a smíchají se s novým během.
**Fix:** `for p in glob.glob(os.path.join(args.out_dir, "grant_*.json")): os.remove(p)`.

### 7. TLS verifikace globálně vypnutá — Medium
**Kde:** `CERT_NONE` v `harvest_site.py`, `eeagrants.py`, `vismo.py`, `vismo_detail.py`, `mv_cms.py`, `praha_grants.py`, `kentico_irop.py`, `cms_similarity.py`, `platform_refingerprint.py`, `lewis_dynamo.py`, `save_unknown_evidence.py`.
**Problém:** Všechny scrapery vypínají `check_hostname` + `verify_mode`. Stažené dokumenty se konvertují a posílají do LLM.
**Dopad:** Žádná ochrana proti MITM/podvržení; relevantní zejména u downloadu příloh.
**Fix:** Ponechat default kontext; vadné certifikáty řešit per-host (`certifi`), ne plošně.

### 8. App odkazy na dokumenty se nikdy nevykreslí — Medium
**Kde:** `scripts/build_app.py:191-193` (`doc.raw_rel/md_rel/txt_rel`) vs `scripts/opportunities.py:155-162`, `scripts/ingest_rich.py:189` (produkují jen `{url, txt_path, ext}`).
**Problém:** Žádný modul `*_rel` klíče nezapisuje; šablona je čte.
**Dopad:** V detailu se zobrazí jen „originál ↗"; odkazy „stažený/md/text" jsou trvale mrtvé.
**Fix:** Doplnit do ingestu `*_rel` (relativně k HTML) z `txt_path`/`raw_path`/`md_path`, nebo odkazy z šablony odstranit.

### 9. Nekonzistentní padding indexů (2 vs 4) — Medium
**Kde:** `scripts/build_extract_input.py:80` (`grant_{i:02d}.json`) vs `scripts/extract_wf.js:11-13` (`padStart(4,'0')`) vs `scripts/repair_out.py:73` (`{prefix}_{i:04d}.json`).
**Problém:** Builder píše 2místné indexy, workflow `{dir,count}` a `repair --count` čekají 4místné. Funguje jen přes `paths.json`.
**Dopad:** Při použití `{dir,count}`/`--count` režimu se jména rozejdou → 0 nalezených souborů.
**Fix:** Sjednotit padding (4 místa) v jedné sdílené funkci.

### 10. Konverze dokumentů jen pro macOS — Medium
**Kde:** `scripts/dsw2_fetch.py:137-148` (`textutil`), `scripts/to_markdown.py:88` (`OcrMacOptions`/Apple Vision), `scripts/fix_docs.py:60` (`/opt/homebrew/bin/soffice`).
**Problém:** `textutil` (doc/docx/odt/rtf/pptx), OCR přes Apple Vision a `soffice` (absolutní homebrew cesta) jsou macOS-only. Na ne-macOS `convert()` pro Office/ODF vrátí chybu; PDF (`pdftotext`) a Excel (`openpyxl`/`xlrd`) mají platformově nezávislou cestu.
**Dopad:** Na Windows/Linux čerstvá konverze `doc`/`docx`/`odt`/`pptx` příloh selže → `attachments_md` prázdné → LLM extrahuje míň. V datasetu je ~1024 takových originálů (524 doc + 450 docx + 48 odt + 2 pptx); PDF/Excel nedotčeny.
**Fix:** Detekovat nástroje (`shutil.which`); na ne-macOS použít `pandoc`/`libreoffice`/`tesseract`; chybějící konvertor logovat jako tvrdou chybu.

### 11. Grounding citací závisí na `--link-docs` — Low
**Kde:** `scripts/opportunities.py:220,404-405`, `scripts/ingest_rich.py:189-194`.
**Problém:** Lokalizace citací polí v dokumentech potřebuje `documents[].txt_path`. Ten plní jen krok `--link-docs` v `opportunities.py`; `ingest_rich` ho nemá.
**Dopad:** Bez `--link-docs` (nebo přes `ingest_rich`) zůstane `txt_path` None a citace polí z PDF padají na `match:none`.
**Fix:** Před `resolve_citations` vždy naplnit `documents[].txt_path` z manifestu i v `ingest_rich`, fallback na `md_path`.

### 12. Hardcoded `data/h19_<web>.jsonl` join — Medium
**Kde:** `scripts/opportunities.py:217`.
**Problém:** Join předpokládá jmennou konvenci `data/h19_<web>.jsonl`; pro jinak pojmenované soubory `_hidx()` vrátí `{}` → tiše se ztratí `documents` + `extra`. Konvenci splňuje jen část zdrojů (zbytek = vismo/dsw2/… jde jinou ingest cestou).
**Dopad:** Křehké — funguje jen dokud se harvest soubory jmenují `h19_*`; mimo tuto konvenci tichá ztráta provenance.
**Fix:** Předávat mapu web→harvest_file explicitně, neodvozovat z prefixu.

### 13. `kentico_irop.py` stahuje max 8 příloh — Medium
**Kde:** `scripts/kentico_irop.py:91` (`if do_att and len(atts) < 8`).
**Problém:** Hardcoded acquisition cap, není v `limits.json` (`attachments_per_opportunity = null`). Přílohy 9+ se zalistují, ale nepřevedou.
**Dopad:** U výzev IROP s >8 přílohami zůstane text dalších dokumentů nezmaterializovaný → chybí v LLM vstupu.
**Fix:** Odstranit cap; materializaci dělat přes `docstore.py` (bez capu).

### 14. Natvrdo psané `/tmp` a `/opt/homebrew` cesty — Medium
**Kde:** `scripts/ingest_rich.py:148-149`, `scripts/repair_out.py:54`, `scripts/rebuild_inputs.py:24`, `scripts/probe_quality.py:15`, `scripts/fix_docs.py:60`.
**Problém:** Defaulty vrstvy 2 míří na `/tmp/*`; `fix_docs` volá soffice absolutní cestou pro Apple Silicon.
**Dopad:** Na Windows `/tmp` neexistuje → defaulty selžou; `fix_docs` spadne i na Intel macu/Linux.
**Fix:** `tempfile.gettempdir()` / konfigurovatelný workdir; soffice přes `shutil.which`.

### 15. Konverzní binárky volány bez preflight kontroly dostupnosti — Low
**Kde:** `scripts/dsw2_fetch.py:137`, `scripts/to_markdown.py:99,112,151,171`, `scripts/fix_docs.py:61,69,75`.
**Problém:** Konvertory se volají `subprocess.run(..., check=False)` bez předběžné kontroly (`shutil.which`). Chybějící nástroj vyhodí `FileNotFoundError`, který se zachytí a zapíše `status=fail` (selhání je viditelné). Mezera: nástroj, který existuje, ale vrátí prázdný výstup, projde dál v cestách, kde se délka výstupu nehlídá (typicky OCR).
**Dopad:** Robustnost — chybí jednotná preflight kontrola; riziko prázdného převodu hlavně u OCR.
**Fix:** Ověřit nástroje na startu (`shutil.which`), chybějící hlásit jako tvrdou chybu; v cestách bez kontroly hlídat 0 znaků.

### 16. `vismo.py` hardcoded BFS strop 40/hloubka 2 — Medium
**Kde:** `scripts/vismo.py:72` (`max_pages=40, max_depth=2`).
**Problém:** Acquisition cap natvrdo, ne přes `limits.json`. Sourozenci (`praha_grants.py`, `eeagrants.py`) berou `safety.runaway_page_ceiling`.
**Dopad:** Vismo obec s rozsáhlou dotační sekcí přijde o dokumenty tiše (strop 40).
**Fix:** Napojit na `limits.json` (`safety.runaway_page_ceiling`); hloubku zrušit nebo jako safety s `⚠`.

### 17. Tři nekompatibilní výstupní schémata vrstvy 1 — Medium
**Kde:** `scripts/wp_harvest.py:90-94` (`content_text`/`documents`), `scripts/mv_cms.py:57`, `scripts/kentico_irop.py:65` (`body_text`/`attachments`), `scripts/harvest_site.py`/`eeagrants.py` (`text`/`documents`) vs konzument `scripts/build_extract_input.py:30-44`.
**Problém:** `build_extract_input._shape` rozumí jen tvarům `harvest` (`text`+`documents`), `vismo` (`body_text`+`attachments`), `dsw2-appeals`. WP emituje tělo v `content_text`; `mv_cms`/`kentico` nemají vlastní `source-type`.
**Dopad:** Výstup `wp_harvest.py` (`content_text`/`title_text`) přes `--source-type harvest` → `r.get("text")`/`r.get("title")` jsou None → do LLM jde prázdné tělo **i titulek**. Latentní: živý dataset jede přes `h19_*` s `text`/`title`.
**Fix:** Normalizovat layer-1 výstupy na kanonické `{url,title,text,documents[]}`, nebo přidat source-type per harvester.

### 18. `store_url` nevrací `md_path`, builder ho preferuje — Low
**Kde:** `scripts/build_extract_input.py:74` (`e.get("md_path") or e.get("txt_path")`) vs `scripts/docstore.py:55-70`.
**Problém:** `store_url` zapisuje jen `txt_path`; `md_path` doplňuje až `to_markdown.py` do manifestu na disku, manifest se ale načítá jen jednou na startu.
**Dopad:** Nově stažené dokumenty jdou do LLM vždy jako `.txt` (horší než markdown).
**Fix:** Po `to_markdown` znovu načíst manifest, nebo v `store_url` generovat markdown.

### 19. `wp_harvest.py` strop 100 stran natvrdo — Low
**Kde:** `scripts/wp_harvest.py:63` (`while page <= 100`).
**Problém:** Acquisition cap (10 000 položek) v kódu, ne v `limits.json`.
**Dopad:** WP zdroj s >10 000 položkami v CPT se utne tiše.
**Fix:** Nahradit `safety.runaway_page_ceiling`, při dosažení logovat `⚠`.

### 20. `eeagrants.py` — komentář ≠ kód, úzký doc regex — Low
**Kde:** `scripts/eeagrants.py:6,35,65`.
**Problém:** Komentář „BFS 1 úroveň", ale kód re-enqueue z každé stránky (BFS libovolné hloubky). Doc regex (`:34`) postrádá `ods`, `pptx`.
**Dopad:** Zavádějící komentář; `.ods/.pptx` přílohy se neodkazují.
**Fix:** Opravit komentář; sjednotit doc regex s `dsw2_fetch.DOC_EXT_RE`.

### 21. Mrtvá závislost + natvrdo psané limity — Low
**Kde:** `requirements.txt:16` (`pymupdf4llm`, neimportováno), `scripts/docstore.py:53` (`sniff_ext(url, 15)`), `scripts/vismo_detail.py:134` (`--max-mb 40`), `limits.json` klíč `probe.sniff_ext_bytes` (`unit:"s"` ale název „bytes").
**Problém:** Nepoužitá závislost; natvrdo psané limity mimo `limits.json`; matoucí název/jednotka konfigurace.
**Fix:** Odstranit `pymupdf4llm`; `15`/`40` přes `L(...)`; přejmenovat klíč na `probe.sniff_ext_timeout_s`.

### 22. Cross-source dedup chybí — Low
**Kde:** `scripts/opportunities.py:108-120` (`canon_key` zahrnuje `host`).
**Problém:** Dedup jen v rámci jednoho zdroje.
**Dopad:** Stejná výzva z primárního webu + agregátoru + úřední desky se objeví víckrát → nadhodnocený počet.
**Fix:** Druhá vrstva dedupu napříč hosty dle čísla výzvy / IČO / normalizovaného titulku, s `also_seen` proveniencí.

### 23. `schema/opportunity_schema.md` nesouhlasí s implementací — Low
**Kde:** `schema/opportunity_schema.md` vs `scripts/extract_wf.js`, `scripts/ingest_rich.py`, `scripts/opportunities.py:122`.
**Problém:** Schéma popisuje `foundation/news/event` + ploché `amount`; kód používá `kind ∈ {grant,project,foundation_mission}`, neukládá news/event, a má bohaté `facets`/`castky[]`.
**Dopad:** Zavádějící datový model pro návrh navazující aplikace.
**Fix:** Aktualizovat schéma na skutečný model, nebo označit jako neaktuální náčrt.

### 24. Trojí redundance ingest/facety/náhled — Low
**Kde:** `opportunities.py` vs `ingest_rich.py`; `build_report_html.py` vs `build_app.py`; `facet_wf.js` vs `ingest_rich.py:_facets_grant`.
**Problém:** Tři dimenze dělají totéž paralelně. `facet_wf.js` není nikde zapojen (`ingest_rich` si facety odvozuje sám, jiným tvarem) → mrtvá/odložená větev.
**Dopad:** Nejasné, který modul je „pravda"; riziko opravy jen jednoho.
**Fix:** Vybrat jednu cestu pro facety (deterministická = levnější), `facet_wf.js` smazat nebo označit jako experiment.

### 25. Drift modelu Haiku vs Sonnet — Low
**Kde:** `README.md`/`CLAUDE.md` („Haiku extrahuje") vs `scripts/extract_wf.js:15`, `scripts/classify_wf.js:9`, `scripts/facet_wf.js:12` (default `'sonnet'`).
**Problém:** Dokumentace tvrdí Haiku, kód defaultuje Sonnet.
**Dopad:** Podhodnocené náklady/latence běhu — podstatné pro rozpočet agregátoru.
**Fix:** Sjednotit docs s realitou (vrstva 2 = Sonnet).

### 26. Hardcoded absolutní cesta autora ve workflow — Medium
**Kde:** `scripts/detect_platforms_wf.js:11` (`/Users/chocholous/Projects/re-grantio/unknown_manifest.json`), `scripts/coverage_wf.js:8-13`, `scripts/type_coverage_wf.js:8-13` (`/Users/chocholous/Projects/re-grantio/{coverage,type}_sample/batch_N.json`).
**Problém:** Vstupní cesty jsou natvrdo absolutní a navíc míří na **starý rodičovský repo** `re-grantio` (ne tento standalone). `detect_platforms_wf` čte `unknown_manifest.json` z cizí cesty, ač `save_unknown_evidence.py` ho píše do rootu tohoto repa.
**Dopad:** Tyto tři workflow nepoběží jinde ani na CI — okamžité „file not found".
**Fix:** Přijímat cesty přes `args` (jako `classify_improve_wf.js`/`extract_wf.js`), relativně k repu. Vedlejší: `detect_platforms_wf` počítá `canonical_renames`, ale neaplikuje je na finální `distribution`/`per_host` (jen `reassigned`) — buď aplikovat, nebo nevracet.

### 27. Detekční/mining skripty zapisují do rootu, ne `platform_data/` — Low
**Kde:** `scripts/cms_similarity.py:103` (`cms_clusters.json`), `scripts/platform_refingerprint.py:96` (`platform_refingerprint_out.json`), `scripts/diversity_finder.py:86` (`diversity_candidates.json`), `scripts/phrasing_miner.py:85` (`phrasing_mined.json`), `scripts/save_unknown_evidence.py:64` (`unknown_manifest.json` + `platform_evidence/`).
**Problém:** Skripty píší výstupy do CWD/rootu, ale kanonické kopie žijí v `platform_data/`. Řetězec detekce navíc čte z rootu.
**Dopad:** Běh zaneřádí kořen repa; nutný manuální přesun; riziko rozjetí root vs `platform_data/` verze.
**Fix:** Psát rovnou do `platform_data/` (konstantní cesta), nebo přidat `--out` s tímto defaultem.

### 28. „Safety cap 150k" deklarovaný, ale neimplementovaný — Low
**Kde:** `prompts/extract_grant.md:9` a `scripts/build_app.py:302` (arch text) tvrdí „bez ořezu (jen safety cap 150k, logováno)"; `limits.json` ani `scripts/extract_wf.js` žádný 150k cap nemají.
**Problém:** Dokumentovaná bezpečnostní pojistka neexistuje (ani v `limits.json`, ani v kódu).
**Dopad:** Buď chybí runaway-pojistka proti patologicky velkému vstupu do LLM, nebo je dokumentace klamná — falešný pocit ochrany.
**Fix:** Buď cap zavést do `limits.json` jako `safety.*` s `⚠` logem, nebo tvrzení z docs odstranit.

### 29. `prompts/classify_type.md` zaostává za živým promptem — Low
**Kde:** `prompts/classify_type.md:9` („Read JSON: title, body, web") vs `scripts/classify_wf.js:20` (live: „title, body, web, attachments_md = PLNÝ text příloh").
**Problém:** `.md` prompt klasifikuje jen z těla, živý workflow čte i přílohy — věcný rozdíl (tenká stránka s „Výzva.pdf"). `extract_grant.md` má banner „tady prompt NEŽIJE", `classify_type.md` ho nemá → vypadá autoritativně.
**Dopad:** Kdo se řídí `.md`, reprodukuje horší klasifikaci než produkce.
**Fix:** Buď doplnit do `classify_type.md` `attachments_md` + disclaimer „autoritativní je classify_wf.js", nebo `.md` označit jako historický.
