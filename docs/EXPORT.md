# EXPORT.md — publikovaná podoba katalogu

Pipeline drží **jeden katalog**: `data/opportunities.jsonl` (řádek = jeden záznam, interní zdroj
pravdy, gitignored). `scripts/export_api.py` z něj dělá jeho **publikovanou podobu**:
`docs/opportunities.json` — jeden soubor, jen kurátorovaná pole, bez interních stop po sběru.
Publikuje se přes GitHub Pages vedle prohlížecí appky.

Nic jiného v repu (`data/`, `scripts/`, mezistupně vrstvy 2) není stabilní povrch — konzument
čte tenhle jeden soubor.

---

## 1. Tvar

```jsonc
{
  "meta": {
    "schema_version": "1.1",                      // MAJOR.MINOR
    "generated_at": "2026-07-31T18:07:00+00:00",  // UTC ISO-8601
    "generated_date": "2026-07-31",
    "count": 3397,
    "source": "regrantio pipeline",
    "content_hash_fields": [ ... ],               // která pole vstupují do otisku
    "status_rule": "..."                          // slovní zápis pravidla ze §3
  },
  "grants": [ { /* záznam */ }, ... ]
}
```

Export je **úplný snímek**, ne diff — vždy všechny aktuální záznamy. Klíč je `id` (kanonická URL
zdroje, stabilní). Každý záznam nese `content_hash` (16 hex) = otisk věcného obsahu; hash schválně
NEzahrnuje `status`/`status_confidence` (mění se sám, jak míjejí termíny) ani `id`, takže se změní
jen při reálné změně obsahu.

`grants[]` má dva druhy záznamů rozlišené polem `kind`:
- `"grant"` — konkrétní výzva (drtivá většina),
- `"foundation_mission"` — nadace bez otevřené výzvy (mise + témata); nepatří mezi otevřené výzvy.

---

## 2. Pole

**Společná:** `id` (URL, primární klíč) · `kind` · `source` (slug/host) · `source_url` ·
`facets` (kanonizované filtrovací osy) · `citations` (grounding: pole → doslovná citace ze zdroje) ·
`content_hash`.

**`kind = "grant"`:**

| pole | typ | význam |
|---|---|---|
| `title` | string | název výzvy (neprázdný) |
| `focus_area` | string \| null | krátký popis zaměření |
| `open_from` | string \| null | začátek příjmu — ISO `YYYY-MM-DD`, `"průběžně"`, nebo null |
| `deadline` | string \| null | konec příjmu — ISO, `"průběžně"`, nebo null |
| `status` | enum | `open`/`announced`/`closed`/`unknown` — **snapshot z buildu, viz §3** |
| `status_confidence` | string | `parsed` / `derived` (odvozeno z opakující se lhůty) |
| `amount` | number \| null | hlavní částka v CZK; **null = neuvedeno, ne 0** |
| `eligible_applicants` | string \| null | kdo může žádat (próza) |
| `required_attachments` | array | povinné přílohy (může být prázdné) |
| `how_to_apply` | string \| null | jak podat |
| `source_doc` | string \| null | odkaz na zdrojový dokument (PDF výzvy…) |

**`kind = "foundation_mission"`:** `name` · `mission` · `support_topics[]` · `regions[]`.

**`facets`** (kanonizované hodnoty, detail v `schema/opportunity_schema.md`):
- `typ_poskytovatele` (string): `ministerstvo`, `samosprava_kraj`, `samosprava_obec`, `statni_fond`,
  `statni_agentura`, `nadace`, `firemni_nadace`, `nadacni_fond`, `zahranicni_fond`, `evropska_komise`
- `zdroj_financovani` (array): `narodni_rozpocet`, `eu_fondy`, `eu_primy`, `npo`, `ehp_norsko`, …
- `oblast`, `typ_zadatele`, `cilova_skupina` (arrays)
- `region` (object): `{kraj: string|null, celostatni: bool}`

Facety jsou pole tam, kde výzva spadá pod víc hodnot; `typ_poskytovatele` a `region` jsou jednoznačné.

---

## 3. Status je odvozený, ne uložený

Otevřená a uzavřená výzva jsou textově identické — liší se jen termínem vůči dnešku. `status`
v exportu je snapshot z času buildu a **zastará**. Kdo export čte, má si ho přepočítat z
`open_from`/`deadline` k reálnému dnešku. Kanonické pravidlo je
`scripts/opportunities.py:compute_status` (zrcadlí ho i appka v `build_app.py`):

```
deadline == "průběžně"                 → open
deadline == null                       → unknown   (katalogový program bez jedné lhůty)
today > deadline                       → closed
today < open_from                      → announced (vyhlášeno, příjem nezačal)
jinak                                  → open
```

`unknown` je ≈ čtvrtina záznamů a **není to chyba** — jsou to opakující se / katalogové programy obcí
a krajů („každoročně 15. 11.", „průběžně během roku"). Neprezentovat je jako `closed`.

`closed` výzvy v exportu zůstávají, dokud je zdroj listuje. Zmizení záznamu z exportu ≠ closed;
znamená to, že zdroj výzvu už vůbec nenabízí.

---

## 4. Záruky

`fix_dataset.py` běží před každým exportem, takže platí:
`id` unikátní a neprázdné · `title` u grantů neprázdné · `amount` je číslo nebo null (nikdy string
ani 0 místo „neuvedeno") · datumy jsou ISO `YYYY-MM-DD`, `"průběžně"`, nebo null · `deadline` není
dřív než `open_from` · čisté UTF-8 · `content_hash` deterministický.

**Co garantované není a je to záměr:** `amount = null` a `status = unknown` jsou časté a správné —
částka bývá jen v zadávací dokumentaci a katalogové programy nemají jednu lhůtu. Poctivý `null` má
přednost před vymyšleným číslem.

**Verzování:** `meta.schema_version` `MAJOR.MINOR`. MINOR = zpětně kompatibilní přírůstek (nové pole).
MAJOR = breaking změna (přejmenované/odebrané pole, změna typu) — na tu je potřeba reagovat.

**Pojistka:** `export_api.py --min-ratio` (default 0.9) běh zastaví (exit 2) a export NEpřepíše,
pokud by měl nový snímek méně než 90 % záznamů předchozího. Rozbitý sběr tím nemůže zdecimovat
publikovaná data. Vědomé velké smazání se povolí `--force`.
