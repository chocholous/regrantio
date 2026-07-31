# platform_data/ — HISTORICKÝ SNAPSHOT (needituj, nečti jako pravdu)

Výstupy jednorázových detekčních běhů z 06/2026. **Autoritativní mapa host→platforma je
`platform_map.json` v KOŘENI repa** (513 hostů); zdejší kopie je starší (507) a pipeline
ji nečte — zůstává jen jako doklad, jak detekce probíhala.

| soubor | co to je |
|---|---|
| `platform_map.json` | starší snapshot kořenové mapy |
| `cms_clusters.json` | strukturální shluky otisků (cms_similarity.py) |
| `detect_platforms_result.json` | výsledek LLM re-detekce platforem |
| `type_coverage_result.json`, `field_coverage_result.json`, `divergent_cov_result.json` | měření pokrytí typů a polí |
| `diversity_candidates.json` | nejodlišnější nevzorkované zdroje (diversity_finder.py) |
| `phrasing_mined.json` | vytěžené formulace pro prompty (legacy/phrasing_miner.py) |
