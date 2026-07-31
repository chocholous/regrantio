# platform_data/ — MĚŘENÉ VÝSLEDKY (historické, needituj)

Výstupy jednorázových detekčních a měřicích běhů z 06/2026. Pipeline je nečte; jsou tu jako
doklad, jak detekce a měření pokrytí probíhalo, a jako referenční seznamy pro prompty.
**Autoritativní mapa host→platforma je `platform_map.json` v KOŘENI repa.**

| soubor | co to je |
|---|---|
| `cms_clusters.json` | strukturální shluky otisků (`cms_similarity.py`) |
| `detect_platforms_result.json` | výsledek LLM re-detekce platforem |
| `type_coverage_result.json`, `field_coverage_result.json`, `divergent_cov_result.json` | měření pokrytí typů a polí |
| `diversity_candidates.json` | nejodlišnější nevzorkované zdroje (`diversity_finder.py`) |
| `phrasing_mined.json` | vytěžené formulace pro prompty |
