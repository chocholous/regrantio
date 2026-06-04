# Prompt — VRSTVA 2: extrakce polí oportunity

> **Tady prompt NEŽIJE.** Živý extrakční prompt je **inline v `scripts/extract_wf.js`**:
> `COMMON` (společná hlavička) + `SYS.grant` (výzva) + `SYS.foundation_mission` (mise) + `SHAPE` (kontrakt tvaru vnořených objektů, odvozený ze `SCHEMAS`).
>
> **Proč inline a ne v tomhle souboru:** workflow běží v JS sandboxu **bez přístupu k filesystému za běhu** (viz nástroj Workflow) — `agent()` dostává prompt jako JS string, takže ho NELZE načíst ze souboru. Inline je proto **jediný zdroj pravdy**; tenhle .md je historický ukazatel, aby nevznikla druhá divergující kopie (což se stalo: tahle verze zaostala o celou bohatou revizi — 8 plochých polí vs. živých ~27 polí s multi/region/částky/příjemci/sběrače/evidence).

## Co živý prompt dělá (orientačně — autoritativní je `extract_wf.js`)
- **Vstup:** PLNÉ tělo + PLNÝ text všech příloh (`attachments_md`), bez ořezu (jen safety cap 150k, logováno). Měřeno: ořez sráží `amount` z ~90 % na 27 %.
- **2 typy:** `grant` (výzva; výsledkový tvar přes `prijemci[]`) a `foundation_mission`. Typ se volí dle názvu souboru (`mission_` → mise).
- **Bohaté schéma** (multi cílová skupina / `region[]` geo / `castky[]` + `vyse_hlavni_czk` / `deadliny[]` + `deadline` / `dokumenty[]` s rolí / `kontakt` / `prijemci[]` pro výsledkové listiny / sběrače `dalsi_datumy[]`/`dalsi_castky[]`).
- **Prompt = NÁVOD** (jak to pozná člověk), ne slovník hodnot. Číselníkové pojmy jsou seed, ne uzávěr.
- **Status NEŘEŠÍ LLM** — dopočítá kód (`opportunities.py:compute_status`) z dat vs. dnešek.
- **EVIDENCE per pole (povinné):** ke každému vyplněnému poli doslovná verbatim citace do `evidence{pole: citace}`; `resolve_citations` ji lokalizuje v souboru (`char_start/end`, `match=exact/fragment/none`).

## Serializace (proč ne StructuredOutput)
Na bohatém vnořeném schématu se harness `StructuredOutput` (XML tool-arg) láme → prázdné `{}` → re-prompt smyčka. **Směr B:** agent JSON **zapíše Write toolem do souboru** (`/tmp/out/<id>.json`), návrat nese jen `hotovo`; po doběhu **batch `json_repair`** + měření velikosti/vyplněnosti přes `scripts/repair_out.py`.

## Negativní pravidla (pitfaly)
Granulární „NEPLEŤ SI" pravidla žijí v **`prompts/pitfalls.md`** (kurátorský log, plněný coverage-loopem) — ta nejdůležitější jsou vtělená do inline `SYS`. Když přidáš nový pitfall, patří do `pitfalls.md` a (je-li zásadní) do `SYS` v `extract_wf.js`.

## Varianty per typ (kanonické úložiště)
- **project:** title, grantee, amount (vyúčtovaná), year, focus_area — mapuje `opportunities.py`.
- **foundation_mission:** name, mission, support_topics[], cilova_skupina[], regions[], forma_podpory[], jak_oslovit, kontakt.
- Výstup → `scripts/opportunities.py` (jednotné schéma + status + `extra` lossless + `provenance` + `citations`).
