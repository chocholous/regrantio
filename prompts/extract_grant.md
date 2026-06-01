# Prompt — VRSTVA 2: extrakce polí grantu (Haiku, masivně paralelní)

Pro dokument klasifikovaný jako `grant`. Vstup = PLNÝ markdown obsahu + markdown příloh
(NEOŘEZÁVAT — kontext ~200k). Extrahuje DATA; status dopočítá kód.

## System / instrukce
```
Jsi extraktor české dotační VÝZVY do jednotného schématu. Dostaneš plný text výzvy + text příloh (pravidla/žádost v markdownu).
Extrahuj POUZE to, co je v textu (nehalucinuj). Pole, co nejdou určit = null.

POLE:
- title               název výzvy
- focus_area          tematická oblast / na co
- open_from           datum ZAHÁJENÍ příjmu žádostí (YYYY-MM-DD)
- deadline            datum UKONČENÍ příjmu žádostí (YYYY-MM-DD)  [u rolling: "průběžně"]
- amount              výše/alokace/míra podpory výzvy (text — opiš relevantní větu)
- eligible_applicants kdo MŮŽE žádat (oprávnění/způsobilí žadatelé)
- required_attachments povinné přílohy ŽÁDOSTI (co musí žadatel doložit)
- how_to_apply        jak/kde podat žádost

⚠ NEPLEŤ SI (kritické — z reálných dat):
- deadline ≠ "termín realizace/dokončení", "platnost: DATUM" (verze přílohy), "vyhlášení výsledků",
  "ZoR/ŽoP" (reporting), "počátek řešení", "lhůta pro rozhodnutí" (úřad), "konalo se", open_from.
  Při prodloužení vezmi POZDĚJŠÍ datum.
- amount ≠ "výše odvodu" (sankce), "výše půjčky/jistina/úroky/pojistné" (úvěr≠dotace),
  "požadovaná výše" (pole žadatele), "podpořen částkou" (to je projekt), "celkem X mld." (všechny výzvy).
  "Minimální/max. výše NENÍ stanovena" → zaznamenej "nestanoveno", ne 0/null.
- eligible ≠ "cílová skupina" (příjemci služby), "typy aktivit" (obsah), "podpořené návrhy" (výsledky),
  "prostřednictvím krajů" (administrace).
- required_attachments ≠ soubory výzvy KE STAŽENÍ (pravidla/manuály) — jen co dokládá ŽADATEL.

Vrať JSON. Status NEvyplňuj — dopočítá se z dat.
```

## Schema výstupu
```json
{
  "title": "...", "focus_area": "...",
  "open_from": "YYYY-MM-DD|null", "deadline": "YYYY-MM-DD|průběžně|null",
  "amount": "... text ...|nestanoveno|null",
  "eligible_applicants": "...|null",
  "required_attachments": ["..."],
  "how_to_apply": "...|null",
  "source_doc": "z které přílohy/stránky pole pochází (pro grounding)"
}
```

## Varianty per typ
- **project:** title, grantee, amount (vyúčtovaná), year, focus_area
- **foundation_mission:** name, mission, support_topics[], regions[]
- Status doplní `scripts/opportunities.py:compute_status` (open/closed/announced z dat vs dnešek), NE LLM.

## Zapojení v receptu (kde tenhle prompt žije — viz `README.md`)
- **Spouští ho `scripts/extract_wf.js`** = mnou řízené Claude-workflow, **1 oportunita = 1 Haiku agent**.
- **Vstup = PLNÝ text + plné přílohy z doc-store** (`scripts/docstore.py` → `data/files/<source>/<sha>.txt`, vazba přes `documents[]` URL z vrstvy 1). **NEOŘEZÁVAT** — měřeno: ořez sráží `amount` 27 %→90 %. Limity jen v `limits.json`.
- **Výstup → `scripts/opportunities.py`** = kanonické úložiště (jednotné schéma + status + `extra` lossless + `provenance` + `citations`).
- **EVIDENCE per pole (povinné):** pro KAŽDÉ vyplněné pole vrať do `evidence{pole: citace}` PŘESNOU DOSLOVNOU citaci ze zdroje (verbatim, ať ji lze najít fulltextem). `resolve_citations` ji pak lokalizuje v souboru (`char_start/end`); necituj, co v textu doslova není (jinak `match=none` = drift → kontrola člověkem).

## Validace (POVINNÁ před hromadným během)
- Otestuj prompt na malém vzorku PROTI ŽIVÉMU ZDROJI (groundedness: je pole reálně v textu? — ověřitelné přes `provenance.documents[].txt_path`).
- Ground-truth = dotacni.info (šablona) + IROP (inline) — měř precision/recall per pole. (Praha aktuální: pokrytí 94–100 %, groundedness 100 %.)
- Coverage loop (`docs/coverage.md`) doplňuje nové záludnosti do `pitfalls.md`.
