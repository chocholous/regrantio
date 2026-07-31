# scripts/legacy — karanténa (v1 éra / jednorázové opravy)

Skripty, které NEJSOU součástí živé v2 pipeline (harvest → build_extract_input →
`data/_<src>_extract.py` → ingest_rich → consolidate → fix_dataset → build_app → export_api).
Ponechány pro referenci/archeologii; nic v živé pipeline je neimportuje.

| skript | proč je tady |
|---|---|
| `build_report_html.py` | v1 prohlížeč `opportunities.jsonl` — nahrazen `build_app.py` (v2) |
| `canon_facets.py` | starý facet-enforce — nahrazen `consolidate.py` + `consolidation_maps.json` |
| `cleanup_granularity.py` | jednorázový úklid v1 program×výzva |
| `extend_maps_extract.py` | jednorázové rozšíření consolidation_maps (LLM varianty) |
| `fix_region.py` | jednorázová oprava regionů — nahrazeno `fix_dataset.py` sekcí D |
| `merge_extraction.py` | v1 merge LLM extrakce — nahrazen `ingest_rich.py` |
| `rebuild_inputs.py`, `repair_out.py`, `fix_docs.py` | jednorázové opravy /tmp artefaktů a doc-store |
| `phrasing_miner.py`, `probe_quality.py` | jednorázové analytické sondy |
| `save_classifications.py` | v1 classify ledger (`data/classifications.jsonl`) |
| `save_unknown_evidence.py` | jednorázový sběr důkazů při re-fingerprintu platforem |
| `build_apify_input.py`, `ingest_apify.py` | Apify most — použije se AŽ při placené P3 session (WebForms/dotaceeu); do té doby mimo živou pipeline |
| `azv_life_build_input.py` | builder AZV/LIFE z `wp_full` — zdroj nikdy nebyl ingestován (0 záznamů v datasetu); kandidát na dokončení, ne živý kód |

Pozn.: `pipeline.py` v kořeni je také legacy stub (viz REMAINING ⚑4), ale zůstává na místě,
protože ho popisuje README/CLAUDE.md jako historický vstupní bod.
