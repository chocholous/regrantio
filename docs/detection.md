# Detekce platforem — jak poznat, čím web běží (a komu se podobá)

**NEVĚŘ platform labelu z merged_dataset** — detekce slévá CMS podle sdíleného podpisu
(„mv_legacy_cms" = 3 CMS, „gordic_ginis" = backend+kraje). Vždy ověř generátor / otisk.

## Třívrstvá detekce (hybrid — deterministika levná, LLM na zbytek)

### 1. Deterministický fingerprint (zdarma, ~53 % hostů) — `scripts/platform_refingerprint.py`
Stáhne homepage, hledá podpisy:
- **generator meta** (`Plone`, `WordPress`, `Drupal`, `Joomla`, `TYPO3`, `Public4u`…)
- **charakteristické cesty** (`/wp-content`, `/wp-json`, `resolveuid`, `/aspinclude/vismoweb`, `++resource++`, `/sites/default`, `/typo3conf`, `/o/` liferay, `/clanek`+`/soubor`, `/getmedia/`, `CMSPages`, `var fonds=`, `/explore/`)
- **hlavičky** (`Server`, `X-Powered-By`, `X-Drupal-Cache`, `X-AspNet-Version`)
- **JS markery** (`__NEXT_DATA__`, `__NUXT__`, `ng-app`)
Výstup: detected platform + evidence. Jasný podpis → label (LLM netřeba, tam je deterministika LEPŠÍ).

### 2. Strukturální podobnost / shlukování (label-free) — `scripts/cms_similarity.py`  ⭐ nejrobustnější
Otisk webu = množina tokenů: **normalizované asset-cesty** (script/css bez hashů — nejsilnější
signál, stejný vendor=stejné bundly) + URL vzory + cookie + Server/X-Powered-By + generator.
Union-find na **Jaccard ≥ 0.30** → **CMS RODINY**. Detekuje příbuznost bez ohledu na label:
- potvrdí známé (vismo, dsw2, Plone-ova-theme, WP-themes)
- 🆕 najde vendory mimo ruční tabulku (Wedar `/js/global/wedar/`, Zlín `/assets/custom/frontend/`, highslide)
- seskupí stejného dodavatele (Zlín kraj+město, SFZP themes, Brno Liferay `/o/brno-theme/`)
- chytí nové instance známých (dotace.chyne/medlanky = dsw2)
- ⚠ pozor na tranzitivní šum (řetěz přes generické jquery/bootstrap) → vyžaduj ≥1 diskriminační token.

### 3. Sonnet nad důkazy (UNKNOWN tail) — `scripts/detect_platforms_wf.js`
Pro weby bez čistého podpisu (`save_unknown_evidence.py` uloží trimovaný HTML důkaz do
`platform_evidence/<host>.txt`): Sonnet agenti čtou důkazy, rozpoznají platformu i **pojmenují
NOVÉ** (footer „provozuje/redakční systém", vendor, cookie, bundle). **Sdílený registr podpisů**
(round1 emituje markery → orchestrátor sloučí → round2 sjednotí názvy). Výsledek (2026-05-31):
**171 UNKNOWN → 163 rozpoznáno, 75 podpisů, jen 8 zůstalo.** Odhalil ~65 grantových zdrojů
schovaných v UNKNOWN (IROP/dotaceEU Kentico, granty.praha, krajské dotační portály, velké nadace).

## Doporučení: použij #2 jako primární
Strukturální otisk (#2) je robustnější než ruční generator-tabulka (#1 má slepá místa —
abakus.cz=WP-Elementor v UNKNOWN). Workflow: otisk #2 → rodiny → #1 pro generator-potvrzení →
#3 (Sonnet) jen na zbylé UNKNOWN. Grant-flag z detekce má FP (kb.cz=banka) i FN (nadace) →
u poskytovatelů ověř ručně.

## Jak přidat NOVOU platformu (když narazíš)
1. Spusť `cms_similarity.py` — patří k existující rodině? (1 parser pokryje celou)
2. Když ne: zjisti přístup (REST? inline-JS? HTML-listing? SPA? postback?) probe homepage + dotační sekce.
3. Najdi přílohový handler → ověř `dsw2_fetch.sniff_ext` (univerzální).
4. Zapiš do `platform_playbook.md`: podpis + harvester + metoda + jdou-detaily-snadno.

## Artefakty
- `platform_refingerprint_out.json` — deterministická detekce 507 hostů
- `cms_clusters.json` — strukturální CMS rodiny
- `detect_platforms_result.json` — Sonnet re-detekce UNKNOWN (75 podpisů)
- `platform_map.json` — finální mapa host→platforma (det + Sonnet sloučeno)
- `diversity_candidates.json` — nejodlišnější zdroje (active learning)
