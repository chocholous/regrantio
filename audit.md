# Engineering Audit — regrantio / opportunity_pipeline

Audit větve `main`. Harvestery na větvi `coverage-expansion` jsou mimo rozsah.

Severity: **Critical** rozbije výstup / tichá ztráta dat · **High** vážná degradace nebo blokuje běh · **Medium** lokální chyba / past · **Low** nekonzistence / dead code.

> **Rozsah:** statická analýza všech zdrojových souborů repa (každý `.py`/`.js`, prompty, schéma, docs, configy). Tam, kde to dataset v `data/` dovolil, je defekt doložen i z přiložených dat (uvedeno u konkrétního bodu jako „Evidence z dat").

| # | Sev | Problém |
|---|-----|---------|
| 2 | Medium | `vismo_detail.py:94` ořezává `body_text` na 8000 znaků mimo `limits.json` (vstup LLM i groundingu) |
| 4 | Medium | Sedm různých referenčních „dnešních" dat pro výpočet statusu |
| 5 | Medium | `pipeline.py` produkuje prázdná pole (stub vydávaný za driver) |
| 6 | Medium | `os.system("rm -f")` neportovatelné na Windows + neescapované |
| 8 | Medium | App odkazy `raw_rel/md_rel/txt_rel` se nikdy nevyplní |
| 9 | Medium | Nekonzistentní padding indexů (2 vs 4) mezi builder/workflow/repair |
| 10 | Low | Konverze doc/odt/rtf/pptx jen pro macOS (textutil) — docx už cross-platform (python-docx) |
| 12 | Medium | Hardcoded `data/h19_<web>.jsonl` join — sedí jen na část zdrojů |
| 13 | Medium | `kentico_irop.py` stahuje max 8 příloh (hardcoded cap) |
| 14 | Medium | Natvrdo psané `/tmp` a `/opt/homebrew` cesty ve vrstvě 2 |
| 15 | Low | Konverzní binárky volány bez preflight kontroly dostupnosti |
| 16 | Medium | `vismo.py` hardcoded BFS strop 40/hloubka 2 mimo `limits.json` |
| 18 | Low | `store_url` nevrací `md_path`, builder ho preferuje → vždy `.txt` |
| 19 | Low | `wp_harvest.py` strop 100 stran natvrdo |
| 20 | Low | `eeagrants.py` komentář ≠ kód; úzký doc regex (bez `ods`/`pptx`) ve 3 harvesterech |
| 21 | Low | Mrtvá závislost `pymupdf4llm` + natvrdo psané limity mimo `limits.json` |
| 22 | Low | Cross-source dedup chybí → duplicitní výzvy napříč zdroji |
| 23 | Low | `schema/opportunity_schema.md` nesouhlasí s implementací |
| 24 | Low | Trojí redundance ingest/facety/náhled; `facet_wf.js` nezapojen |
| 25 | Low | Drift modelu: docs Haiku, kód defaultuje Sonnet |
| 26 | Medium | Hardcoded absolutní cesta autora `/Users/chocholous/…` ve 3 workflow |
| 27 | Low | Detekční/mining skripty zapisují výstup do rootu, ne `platform_data/` |
| 28 | Low | „Safety cap 150k" deklarovaný v docs, ale nikde neimplementovaný |
| 29 | Low | `classify_type.md` i `verify_classify_wf.js` zaostávají za živým classify promptem (chybí `attachments_md`) |
| 30 | Medium | Doc-store (`store_url`) konvertuje bez OCR a bez markdownu — skeny tiše prázdné, rozchází se s `to_markdown.py` |
| 31 | Low | Rozbité odkazy v dokumentaci: `pitfalls.md` na neexistující `*_cov_result.json`; `README.md` na zaniklé `extract/*.py` cesty |
| 33 | Low | `dsw2.py:54` `.lstrip("www.")` maže ZNAKY ne prefix → komolí `foundation_id` u hostů začínajících na `w` |

---

### 2. `vismo_detail.py` ořezává `body_text` na 8000 znaků — Medium
**Kde:** `scripts/vismo_detail.py:94` (`"body_text": body[:8000]`).
**Problém:** Natvrdo zakódovaný ořez **těla výzvy** mimo `limits.json` (kde `acquisition.input_truncation = null` s komentářem „ořez sráží amount 27 %→90 %"). `body_text` jde do vrstvy 2 (`build_extract_input._shape` → `body`) i do groundingu (`_page_text` v `ingest_vismo`/`ingest_enriched`) → porušuje doktrínu „data vždy celá".
**Dopad:** Tělo výzvy delší než 8000 znaků se do LLM i `resolve_citations` dostane useknuté.
**Fix:** Odstranit `[:8000]`; případný strop jen jako `safety` v `limits.json` s `⚠` logem.
**Rozsah (ať nevznikne false positive):** ořez se týká JEN `vismo_detail.py:94`. `vismo_detail.py:117` (`[:1500]`) a `mv_cms.py:72` (`[:1200]`) jsou `text_excerpt` (náhled přílohy v manifestu), ne vstup LLM — plný text přílohy jde přes `txt_path`/doc-store. `mv_cms.py:57` má `body_text` bez ořezu.

### 4. Sedm různých referenčních dat pro status — Medium
**Kde:** `pipeline.py:21` (2026-06-01), `scripts/kentico_irop.py:11` (2026-06-01), `scripts/vismo_detail.py:16` (2026-05-30), `scripts/ingest_rich.py:153` (2026-06-01), `scripts/opportunities.py:375` (`date.today()`), `scripts/dsw2.py:347` (`date.today()` → `derive_status` appeals), `scripts/build_app.py:423` (natvrdo `"2026-06-05"`).
**Problém:** Status se počítá v kódu, ale „dnešek" je v každém modulu jiný; vismo i dsw2 navíc počítají status z harvest-time (dsw2 status se sice při ingestu přepočítá `compute_status`, ale harvest-time `status` zůstává v `extra`).
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

### 10. Konverze doc/odt/rtf/pptx jen pro macOS — Low (docx VYŘEŠENO cross-platform)
**Kde:** `scripts/dsw2_fetch.py` (`textutil` pro doc/odt/rtf/ppt/pptx), `scripts/to_markdown.py:88` (`OcrMacOptions`/Apple Vision), `scripts/fix_docs.py:60` (`/opt/homebrew/bin/soffice`).
**Problém:** `textutil`, OCR přes Apple Vision a `soffice` (absolutní homebrew cesta) jsou macOS-only.
**Vyřešená část (docx):** `dsw2_fetch.convert` má pro `docx` cross-platform větev přes **python-docx** (fallback na textutil); na Windows recovered 19 docx příloh MŠMT. PDF (`pdftotext`) a Excel (`openpyxl`/`xlrd`) byly platformově nezávislé už dřív.
**Zbývá:** `doc` (starý binární), `odt`, `rtf`, `ppt`, `pptx` stále jen textutil → mimo macOS bez textu.
**Fix:** `odt`/`rtf`/`pptx` přes `pandoc`/`libreoffice` (detekce `shutil.which`), `.doc` přes `antiword`/`libreoffice`; chybějící konvertor logovat hlasitě.

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

### 20. `eeagrants.py` — komentář ≠ kód; úzký doc regex ve 3 harvesterech — Low
**Kde:** `scripts/eeagrants.py:6,65` (komentář vs kód) a `:34` (regex); **stejný úzký regex** `\.(pdf|docx?|xlsx?|odt)` i v `scripts/harvest_site.py:26` a `scripts/praha_grants.py:30`.
**Problém:** Komentář „BFS 1 úroveň", ale kód re-enqueue z každé stránky (BFS libovolné hloubky). Doc regex ve všech třech server-rendered harvesterech postrádá `ods`, `pptx` (a `rtf`, `zip`) — na rozdíl od `dsw2_fetch.DOC_EXT_RE`/`wp_harvest.DOC_RE`, které je mají.
**Dopad:** Zavádějící komentář; `.ods/.pptx` přílohy se z těchto zdrojů neodkazují → vypadnou z doc-store → chybí v LLM vstupu.
**Fix:** Opravit komentář; sjednotit doc regex napříč harvestery na `dsw2_fetch.DOC_EXT_RE` (jeden sdílený zdroj).

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

### 29. `classify_type.md` i `verify_classify_wf.js` zaostávají za živým classify promptem — Low
**Kde:** `scripts/classify_wf.js:20` (LIVE: „title, body, web, **attachments_md = PLNÝ text příloh**") vs `prompts/classify_type.md:9` a `scripts/verify_classify_wf.js:19` (obě jen „title, body, web", bez příloh).
**Problém:** Živý workflow klasifikuje z těla **i příloh** (tenká stránka s „Výzva.pdf" = grant). Dvě kopie zaostaly:
- `classify_type.md` čte jen tělo; navíc nemá banner „tady prompt NEŽIJE" (který má `extract_grant.md`) → vypadá autoritativně.
- `verify_classify_wf.js:18` se sám deklaruje jako „**IDENTICKÝ prompt jako classify_wf.js** (fair cross-model check)", ale jeho `SYS` `attachments_md` **postrádá**. Cross-model audit (Opus+Sonnet) tedy měří proti **slabšímu** promptu než produkce → reportovaná accuracy nemusí odpovídat živé klasifikaci.
**Dopad:** Kdo se řídí `.md`, reprodukuje horší klasifikaci; verifikační běh není férový vůči produkci (falešná kalibrace).
**Fix:** Sjednotit obě kopie s `classify_wf.js` (doplnit `attachments_md`); do `classify_type.md` přidat disclaimer „autoritativní je `classify_wf.js`", nebo `.md` označit jako historický (jako `extract_grant.md`).

### 30. Doc-store konvertuje bez OCR a bez markdownu (rozpor s `to_markdown.py`) — Medium
**Kde:** `scripts/docstore.py:61` (`df.convert(raw, ext, txt, 60)`) → `scripts/dsw2_fetch.py:133-153` (pdf = `pdftotext`, **žádné OCR**, výstup jen `.txt`) vs `scripts/to_markdown.py`/`scripts/fix_docs.py` (pdf-sken → docling+OCR / tesseract, výstup `.md`).
**Problém:** Existují **dvě nezávislé konverzní cesty**: (a) `docstore.store_url` → `dsw2_fetch.convert` (volá ji `build_extract_input` při materializaci nových příloh) dělá jen `pdftotext`/`textutil`/`xls` → `.txt`, **bez OCR a bez markdownu**; (b) `to_markdown.py`/`fix_docs.py` jsou **samostatné** passy s OCR (`.md`). Skenované PDF přes cestu (a) nemají textovou vrstvu → `pdftotext` vrátí prázdno a OCR se nespustí. Navíc `docstore.store_url:62-63` označí `ok=True` pokaždé, když `.txt` soubor existuje, a `chars` plní z `os.path.getsize(txt)` — tj. prázdný/form-feed výstup může projít jako úspěch. `store_url` taky nikdy nezapíše `md_path` (→ #18), takže nově stažené dokumenty jdou do LLM jako horší `.txt`, dokud nedoběhne `to_markdown`.
**Evidence z dat:** v `data/files/manifest.jsonl` chybí klíč `md_path` u všech záznamů (potvrzuje #18). V `data/vismo_files/` je **134 z 680** `.txt` (≈20 %) fakticky prázdných (<20 znaků) — skeny prohnané `pdftotext` bez OCR.
**Dopad:** ~20 % skenovaných příloh skončí bez textu (grounding `match:none`, prázdné `attachments_md`); kvalita závisí na tom, zda doběhl OCR pass (`to_markdown`/`fix_docs`). Souvisí s #10 (OCR jen macOS), #15 (prázdný převod nehlídán) a #18 (`md_path`).
**Fix:** Sjednotit konverzi na jednu cestu (OCR i pro `store_url`); ve `store_url` měřit reálné znaky (ne pouhý `getsize`) a prázdný převod logovat `⚠`/`ok=False`.

### 31. Rozbité odkazy v dokumentaci — Low
**Kde:** `prompts/pitfalls.md:5` (`platform_data/{field,type,divergent}_cov_result.json`) vs reálné soubory `platform_data/field_coverage_result.json` + `type_coverage_result.json` (`divergent_cov_result.json` sedí). `README.md:57` odkazuje `extract/wp_harvest.py` / `extract/vismo.py` / `extract/kentico_irop.py` / `extract/mv_cms.py` — `extract/` je zaniklá cesta rodičovského repa (po osamostatnění vše v `scripts/`, viz `pipeline.py:20` „dřív ../extract").
**Problém:** Dokumentace ukazuje na neexistující soubory: `field_cov_result.json`/`type_cov_result.json` (chybí „overage") a celý adresář `extract/`. Souvisí s #25/#27/#28 (docs zaostávají za kódem — Haiku vs Sonnet, root vs `platform_data/`, 150k cap).
**Dopad:** Čtenář dohledává neexistující artefakty/skripty; klesá důvěryhodnost docs jako návodu.
**Fix:** Opravit názvy na `field_coverage_result.json`/`type_coverage_result.json`; přepsat `extract/` → `scripts/` v `README.md`.

### 33. `lstrip("www.")` maže znaky, ne prefix → komolí `foundation_id` — Low
**Kde:** `scripts/dsw2.py:54` (`slug_of`): `host = re.sub(r"^https?://", "", base_of(u)).lstrip("www.")`.
**Problém:** `str.lstrip("www.")` neodstraní prefix `"www."`, ale **libovolné vedoucí znaky z množiny `{w, ., }`**. Host začínající na `w` o ně přijde: `wroclaw.cz` → `roclaw.cz`, `web.kraj.cz` → `eb.kraj.cz`. Pro `www.foo` to funguje jen náhodou. `slug_of` plní `foundation_id` u VŠECH dsw2 entit (`extract_site:273` → programs/appeals/projects/links). (Pozn.: `wp_harvest.slug_of` to dělá správně přes `re.sub(r"^www\.", …)`.)
**Dopad:** Zkomolený `foundation_id` (identita/label zdroje) u dsw2 hostů na `w` — riziko nekonzistence v provenienci a případného mismatchu při joinu/labelování.
**Fix:** `re.sub(r"^www\.", "", host)` místo `lstrip("www.")` (sjednotit s `wp_harvest.slug_of`).

---

## Vyřešeno během práce (objeveno mimo původní číslování)

- **#1 (build_app/ingest_rich názvy souborů) — VYŘEŠENO** (odebráno výše): `build_app.py` default `--in` přepnut na `data/opportunities_v2.jsonl` (rich, s `facets`, výstup `ingest_rich`); docstring/usage sjednoceny. Plochý `opportunities.py` → `opportunities.jsonl` už nekoliduje se vstupem appky.
- **prefilter.py četl jen klíč `text` — VYŘEŠENO**: zdroje s `body_text`/`attachments` (mv_cms, kentico, vismo) se mylně dropovaly jako „empty" (mv.gov.cz: −7/7 → 0). Opraveno: `clean()` tolerantní k `text`/`body_text`/`content_text` + `documents`/`attachments` (shodně s `build_extract_input._shape`). Tatáž rodina jako #17.
