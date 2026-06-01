# Znovupoužitelná data — co už je stažené (NESCRAPOVAT ZNOVU)

Pipeline má fázi 1 (harvest) PŘESKOČIT tam, kde data existují. Cesty relativní k repo kořeni `re-grantio/`.

## Harvestovaná data (HTML→text, lossless)
| Zdroj | Soubor | Obsah | Reuse pro |
|---|---|---|---|
| WordPress (88 webů) | `data/wp_full/*.jsonl` (127 souborů, 896 MB, ~73k zázn.) | PLNÝ content.rendered (text+html), links, **documents[]**, terms, meta — lossless | fáze 1 WP, fáze 3-4 přímo |
| vismo (13 webů) | `data/vismo_listing.jsonl` (344 dok) + `data/vismo_documents.jsonl` (185 výzev s detaily) | listing + detail + status + přílohy | fáze 1-2 vismo |
| dotacni.info (agregátor) | `data/dotacni_structured.json` (8127, strukturováno) | title/open_from/deadline/status/amount/eligible | ⭐ GROUND-TRUTH + přímý import |
| dsw2 (28 měst) | `data/dsw2_programs.jsonl` (274), `dsw2_appeals.jsonl` (67), `dsw2_projects.jsonl` (1325), `dsw2_conditions.jsonl` (15 karet) | programy/výzvy/projekty/rozhodovací karty | fáze 1 dsw2 |

## Převedené DOKUMENTY (PDF/DOC/XLS → text) — fáze 2 už hotová
| Adresář | # .txt | Zdroj | Obsah |
|---|---|---|---|
| `data/vismo_files/<host>/<sha>.{ext,txt}` | **680** (112 MB) | vismo File.ashx přílohy | zásady, výzva PDF, žádosti, formuláře |
| `data/dsw2_files/<host>/<sha>.{ext,txt}` | 16 | dsw2 dokumenty | rozhodovací podmínky |
| `data/dsw2_web_text.jsonl` | — | Apify web crawl 17 externích | markdown |

## Raw materiál k dalšímu vytěžení
- `data/wp_full/*.jsonl` má v každém zázn. `documents[]` (39773 dokumentů celkem) — URL příloh k stažení+konverzi (fáze 2) tam, kde ještě nejsou.
- `data/vismo_documents.jsonl` má `attachments[].text_excerpt` (1500 zn) + `txt_path` na plný text.

## Mapy & znalost (platform_data/)
- `platform_map.json` — host → platforma (det+Sonnet)
- `cms_clusters.json` — CMS rodiny (otisk)
- `detect_platforms_result.json` — Sonnet re-detekce (75 podpisů)
- `diversity_candidates.json` — nejodlišnější zdroje (active learning)
- `phrasing_mined.json`, `*_cov_result.json` — vytěžené formulace + záludnosti polí

## Pravidlo
**Fáze 1 (harvest) a fáze 2 (doc→md) první KONTROLUJÍ tyto soubory.** Scrape/Apify jen na to,
co tu NENÍ (nové zdroje, SPA/postback weby, nestažené přílohy). Šetří čas i Apify kredity.
