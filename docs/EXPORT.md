# EXPORT.md — publikovaná podoba katalogu

Pipeline drží **jeden katalog**: `data/opportunities.jsonl` (řádek = jeden záznam, interní zdroj
pravdy, VERZOVANÝ v gitu). `scripts/export_api.py` z něj dělá jeho **publikovanou podobu**:
`docs/opportunities.json` — jeden soubor, jen kurátorovaná pole, bez interních stop po sběru.
Publikuje se přes GitHub Pages vedle prohlížecí appky.

Nic jiného v repu (`data/`, `scripts/`, mezistupně vrstvy 2) není stabilní povrch — konzument
čte tenhle jeden soubor.

---

## 1. Tvar

```jsonc
{
  "meta": {
    "schema_version": "1.2",                      // MAJOR.MINOR
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

**Společná:** `id` (URL, primární klíč) · `kind` · `source` (slug/host) ·
`provider` (jméno poskytovatele podle slugu — `data/source_names.json`; od 2026‑09‑11,
**mimo `content_hash`**, protože jméno zdroje není obsah výzvy) · `source_url` ·
`facets` (kanonizované filtrovací osy) · `citations` (grounding: pole → doslovná citace ze zdroje) ·
`content_hash`.

⚠ `source` je INTERNÍ identifikátor sběru („optak", „esfcr", „eu_ft") a nikdy se
nemá ukazovat člověku — do 2026‑09‑11 ho produkt vypisoval jako poskytovatele.

**`kind = "grant"`:**

| pole | typ | význam |
|---|---|---|
| `title` | string | název výzvy (neprázdný) |
| `focus_area` | string \| null | krátký popis zaměření |
| `open_from` | string \| null | začátek příjmu — ISO `YYYY-MM-DD`, `"průběžně"`, nebo null |
| `deadline` | string \| null | konec příjmu — ISO, `"průběžně"`, nebo null |
| `status` | enum | `open`/`announced`/`closed`/`unknown` — **snapshot z buildu, viz §3** |
| `status_confidence` | string | `parsed` / `derived` (odvozeno z opakující se lhůty) |
| `amount` | number \| null | nejvyšší podpora na **jednoho žadatele / projekt** v CZK; **null = neuvedeno, ne 0**. Celková alokace výzvy je ve `facets.vyse_alokace_czk`; částka, která se jí rovná nebo ji převyšuje, se nepublikuje (do 2026‑09‑26 tu byla „hlavní částka" a u 549 evropských výzev to byla alokace, až 97 mld. Kč; `fix_dataset.amount_per_applicant`) |
| `eligible_applicants` | string \| null | kdo může žádat (próza). **Vždy řetězec**, nikdy pole — hlídá `validate_release.py` (do 2026‑09‑11 173 záznamů neslo seznam) |
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

### 2b. Kontrakt 1.2 — obsah, který zůstával v `extra`, a odvozeniny (2026‑09‑14)

Produkt do té doby dostával jen pole vrstvy 2 a fasety; na čtyři otázky
žadatele („je to pro subjekt naší velikosti?", „má to lhůtu, nebo se to
vyhlašuje každý rok?", „není to jen další ročník toho, co vidím výš?",
„odkud ten údaj je?") odpovídal sám a každý na jiném místě. Od 1.2 odpovídá
katalog. Všechno počítá `scripts/enrich.py` a `scripts/dedup.py`
deterministicky z polí, která záznam už nese; nic z toho není nový sběr.

**Obsah ze zdroje** (vstupuje do `content_hash`):

| pole | typ | význam |
|---|---|---|
| `call_number` | string \| null | číslo výzvy, jak ho uvádí poskytovatel („01 (OP Doprava)") |
| `contact` | `{osoba, email, telefon}` \| null | kontakt uvedený u výzvy; první použitelný |
| `documents` | `[{popis, role, url?}]` | dokumenty, které zdroj u výzvy jmenuje; `role` ∈ pravidla_podminky · vyzva · formular · vzor_smlouvy · priloha · metodika · ostatni. Prázdné pole = zdroj žádné nejmenuje |
| `realization_period` | string \| null | období realizace, jak je napsané ve zdroji |

**Odvozeniny** (MIMO `content_hash` — změna pravidla není změna výzvy):

| pole | hodnoty | jak vzniká |
|---|---|---|
| `scope` | `local` · `regional` · `national` · `international` · `eu_central` | z `typ_poskytovatele` a `region`: obec → local, kraj → regional, Evropská komise → eu_central, zahraniční fond → international, jinak national (pokud se zdroj sám neomezí na kraj nebo obec) |
| `deadline_kind` | `fixed` · `rolling` · `recurring` · `unknown` | ISO lhůta → fixed; „průběžně" nebo režim `prubezna` → rolling; kolový režim, „každoročně" v kontextu lhůty, odvozený termín NEBO rodina se dvěma a víc ročníky → recurring; jinak unknown. **Nehádá se:** obecní program bez dokladu je `unknown` |
| `deadline_note` | string \| null | věta ze zdroje o lhůtě tam, kde ISO datum chybí („každoročně do 15. 11.") |
| `program_key` | 12 hex | rodina záznamů téhož programu u téhož zdroje: titul bez ročníku, čísla kola a pořadového čísla + `source` |
| `variant_of` | id \| null | tenhle záznam je UZAVŘENÝ starší ročník kanonického záznamu rodiny. Dva živé záznamy téže rodiny se nikdy neslučují („63. výzva" a „64. výzva" jsou dvě výzvy) |
| `family` | `{key, rounds, years[], typical_deadline, earlier[]}` \| null | jen na kanonickém záznamu rodiny: kolik ročníků zdroj listuje, které roky, společný den uzávěrky („31. 10."), starší ročníky |
| `field_provenance` | `{pole: {method, cited}}` | pro deadline · open_from · amount · eligible_applicants · focus_area · typ_zadatele · oblast · region: `method` ∈ parsed (vrstva 1) · model (vrstva 2) · derived (dopočet); `cited` = existuje doslovná citace, která se ve zdroji NAŠLA. Pole bez hodnoty tu není |

Konzument, který kontrakt 1.2 nezná, nová pole ignoruje; nic se nepřejmenovalo
ani neodebralo (MINOR). Grantio je mapuje v `publish_db.py:to_row` na sloupce
`scope`, `deadline_kind`, `program_key`, `variant_of`, `call_number`; zbytek
čte z `raw`. Odvozené sloupce porovnává `derived_changed()` zvlášť, protože
v otisku nejsou — `variant_of` se změní ve chvíli, kdy přibude NOVÝ ročník,
aniž by se starý změnil o písmeno.

Kvalita dat, ze kterých se tohle počítá, je změřená v `docs/QUALITY.md`
(`scripts/quality_report.py`, běží v tailu obnovy).

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
