# Integrace regrantio feedu → produkt grantio.cz (the-machine-app)

Tenhle dokument je **konkrétní návod, jak náš grantový feed napojit na produkt grantio.cz** (repo
`chocholous/the-machine-app`, SvelteKit + Supabase). Doplňuje obecný kontrakt `docs/PRODUCT_API.md`
(co feed je) o **mapování na skutečné schéma produktu** (`public.grants`) + sync postup ve vašem stacku.

> Pro produktový tým (Pavel, Adam): tohle je vše, co potřebujete k zadrátování. Datová vrstva je
> naspecifikovaná turnkey; implementaci napíše Claude Code přímo ve vašem repu podle téhle spec.
> UI nad daty (filtry / AI chat / detail) je vaše product rozhodnutí, ne blocker integrace.

---

## 0. Jak to zapadá

`regrantio` (naše pipeline) sbírá a kurátoruje českou grantovou databázi (2749 grantů / 127
poskytovatelů) a publikuje **jeden veřejný JSON feed**. grantio.cz ten feed 1× denně stáhne a
upsertne do `public.grants`. Odtud už jede vaše stávající UI (vyhledávání, match scoring, wizard, …).

Náš feed je **už kurátorovaný** (je to výstup hotové extrakční pipeline) → je ekvivalentem vašeho
post-extraction výstupu, **ne** raw scrapu. Proto ho posílejte rovnou do `public.grants`, ne přes
`admin.grants`/Apify/runs mašinérii (ta je pro raw scraping).

---

## 1. Feed

| | |
|---|---|
| **URL** | `https://chocholous.github.io/regrantio/branches/<branch>/opportunities.json` |
| **Produkční větev (zatím)** | `coverage-expansion-next` → `.../branches/coverage-expansion-next/opportunities.json` |
| **Formát** | statický JSON, ~10 MB, bez autentizace (prostý GET) |
| **Kadence** | feed se obnovuje řádově týdně; **stahujte 1× denně** (noční cron) |
| **Freshness** | `meta.generated_at` / `meta.count` — když se nezměnily, sync přeskočte |

Dejte URL do env proměnné `REGRANTIO_FEED_URL` — až padne rozhodnutí o produkční větvi (merge do
`main` vs. zůstat na `coverage-expansion-next`), je to změna jednoho řádku.

Tvar feedu:
```jsonc
{
  "meta": { "schema_version": "1.1", "generated_at": "...", "generated_date": "2026-06-30",
            "count": 2749, "status_rule": "..." },
  "grants": [ { "id": "...", "kind": "grant", "title": "...", "content_hash": "...", ... } ]
}
```

---

## 2. Sync logika (idempotentní upsert + soft-delete)

Feed je úplný snapshot (vždy všechny záznamy), ne diff.

- **Klíč:** náš `id` (= stabilní URL grantu). Ulož do `grant_id_ext` a `dedupe_key = 'regrantio:' || id`.
  Upsert podle `dedupe_key` (`onConflict: 'dedupe_key'`).
- **Detekce změn:** každý grant nese `content_hash` (16 hex, otisk věcného obsahu). Aktualizuj/re-indexuj
  jen když se hash změní. (Volitelně ulož do nového sloupce — §5; bez něj prostě upsertuj vše, 2749 řádků
  denně je pro Postgres triviální.)
- **Odebrání:** regrantio řádek (`source_name='regrantio'`), jehož `id` v novém feedu chybí → výzva
  zanikla ve zdroji → **soft-delete** (nastav `status='closed'` / skryj z vyhledávání; ne hard delete,
  kvůli SEO/odkazům).

Referenční algoritmus (insert/update/delete/no-op + idempotence) i s běžícím self-testem je v našem
repu: `scripts/product_sync_example.py`. Překlop funkci `sync()` do TS + supabase-js.

---

## 3. Mapování polí: `opportunities.json` → `public.grants`

Vaše `public.grants` má sloupce pro skoro každé naše pole (schéma bylo postavené přesně na sync
grantového modelu). Granty (`kind = "grant"`):

| regrantio feed | `public.grants` sloupec | pozn. |
|---|---|---|
| `id` (URL) | `grant_id_ext` + `url` | klíč; `dedupe_key = 'regrantio:' + id` |
| `title` | `title` | |
| `focus_area` | `focus_area` + `short_description` | krátký popis zaměření |
| `eligible_applicants` | `ideal_grantee` | kdo může žádat (próza) |
| `how_to_apply` | `how_to_apply` | |
| `open_from` (ISO/`"průběžně"`/null) | `deadline_start` (timestamptz) | jen když ISO; jinak null |
| `deadline` (ISO/`"průběžně"`/null) | `deadline` (tstz) + `deadline_text` | ISO→`deadline`; `"průběžně"`→`deadline=null`,`deadline_text='průběžně'` |
| `status` | `status` | **počítej z dat**, neber snapshot — §4 |
| `amount` (number/null) | `max_amount` (numeric) + `amount_preview` | null = „neuvedeno", NE 0; `currency='CZK'` |
| `required_attachments[]` | `key_requirements[]` | povinné přílohy |
| `source_doc` | `documents` (jsonb `[{url,title}]`) | |
| `source` | `source_name` | (sjednoceně `'regrantio'`, původní zdroj zůstává v `id`/`url`) |
| `content_hash` | (volitelně) vlastní sloupec `source_content_hash` | §5 |
| `facets.region` `{kraj,celostatni}` | `regions[]` | `celostatni`→`['celostátní']`, jinak `[kraj]` |
| `facets.typ_zadatele[]` + `facets.cilova_skupina[]` | `target_groups[]` | sjednoť |
| `facets.oblast[]` | `tags[]` (+ `category` = první oblast) | tematické oblasti |
| `facets.typ_poskytovatele` | `provider` / `provider_display` | ministerstvo/kraj/nadace… |
| `facets.zdroj_financovani[]` | `funding_type` | první/join (narodni_rozpocet/eu_fondy/eu_primy…) |
| `facets.forma_podpory[]` | `call_type` | dotace/úvěr/příspěvek… |
| `citations` (grounding) | `data_flags` (jsonb) nebo nech | volitelné — doslovné citace pro „důvěryhodnost" UI |

Nadace (`kind = "foundation_mission"`, 25 záznamů — nadace bez otevřené výzvy):

| regrantio feed | `public.grants` sloupec |
|---|---|
| `name` | `title` |
| `mission` | `description` + `grant_summary` |
| `support_topics[]` | `tags[]` |
| `regions[]` | `regions[]` |
| (konstanta) | `content_classification = 'foundation_mission'` (aby šly skrýt z „otevřených výzev") |

**Default:** `currency='CZK'`, `is_canonical=true`, `source_name='regrantio'`.
**Nech null:** `description` u grantů (nemáme dlouhý popis — případně slož z `focus_area` +
`eligible_applicants`), `min_amount`, `contact_*` (ve feedu většinou nejsou).

---

## 4. Status — počítej z dat, neber snapshot

Uložený `status` ve feedu je build-time snapshot a zastará (otevřená/zavřená se liší jen datem vs.
dnešek). Počítej status z `open_from`/`deadline` k dnešku (denně / při zobrazení):

```
deadline == "průběžně"   → open
deadline prázdné/null     → 'unknown' (katalogový program bez jedné lhůty)
dnešek > deadline         → closed
dnešek < open_from        → 'announced' (vyhlášeno, příjem nezačal)
jinak                     → open   (+ 'closing' když deadline < ~14 dní → vaše stávající logika)
```

Ukládej RAW `open_from`/`deadline`, status drž jako odvozený. Constraint `open/closing/closed` byl u
vás stejně dropnutý, takže `unknown`/`announced` jdou uložit, nebo si je namapuj na svou taxonomy.

**Co znamená `unknown` (≈24 % grantů, čekej to):** grant nemá jednu parsovatelnou lhůtu — jsou to
převážně **opakující se / katalogové programy** obcí a krajů (deadline typu „každoročně 15. 11.",
„průběžně během roku", „31. ledna každého roku"). NENÍ to chyba ani chybějící data — je to realita
zdroje (nefabrikujeme lhůtu, kterou neznáme). **V UI je neprezentuj jako `closed`** — ukaž např.
„termín neuveden / průběžně — ověř u zdroje" + odkaz na `url`. Část z nich je `rezim_prijmu='prubezna'`
(průběžný příjem) → můžeš je volitelně zobrazit jako otevřené, ale my je držíme `unknown` (poctivěji,
nevíme, jestli program neskončil).

---

## 5. (Volitelná) mini-migrace pro efektivní detekci změn

```sql
-- supabase/migrations/<timestamp>_add_regrantio_content_hash.sql
ALTER TABLE public.grants ADD COLUMN IF NOT EXISTS source_content_hash text;
COMMENT ON COLUMN public.grants.source_content_hash IS
  'content_hash z externího feedu (regrantio) pro idempotentní change-detection.';
```
Sync pak: `if existing.source_content_hash == feed.content_hash → skip`. Bez sloupce upsertuj vše.

---

## 6. Co postavit (data layer — zadání pro Claude Code v the-machine-app)

1. **Sync job** (`scripts/sync-regrantio.ts` nebo admin endpoint `src/routes/admin/sync-regrantio/+server.ts`):
   fetch `REGRANTIO_FEED_URL` → mapuj (§3) → upsert do `public.grants` přes `dedupe_key` → status (§4)
   → soft-delete regrantio řádky chybějící ve feedu. Idempotentní (2. běh téhož feedu nic nemění).
2. **Spouštění:** noční cron (1×/den) — systémový cron / GitHub Action / Supabase scheduled function,
   jak spouštíte ostatní joby.
3. **Env:** `REGRANTIO_FEED_URL` do `.env.example` + prod/staging.
4. **Validace:** `pnpm check` + `pnpm lint` 0/0; přidej unit test syncu (vzor self-testu:
   regrantio `scripts/product_sync_example.py`).

UI nad daty (filtry / AI chat / detail) řeší stávající routes (`/grants`, `/api/chat`, `/wizard`).
**Datová vrstva je tímhle hotová**; UI je product rozhodnutí.

---

## 7. Záruky feedu

`id` unikátní/neprázdné · `amount` číslo nebo null (nikdy string/0) · datumy ISO `YYYY-MM-DD`/
`"průběžně"`/null · `deadline` ne dřív než `open_from` · žádné duplicity · čisté UTF-8 ·
`content_hash` deterministický · pojistka proti kolapsu (rozbitý běh nepřepíše feed zdecimovaným
datasetem). `amount=null`/`status=unknown` jsou časté a **správné** (zobraz „neuvedeno", ne 0).
Verzování `meta.schema_version` `MAJOR.MINOR`: MINOR = zpětně kompat. (nové pole, ignoruj); při
neočekávaném **MAJORu** sync zastav a ozvi se.

---

## 8. Než to půjde naživo (rozhodnutí)

1. **Která regrantio větev je produkční feed** (merge do `main` vs. zůstat `coverage-expansion-next`) —
   změna jedné env hodnoty u produktu.
2. Soft-delete vs. hard-delete na vaší straně (doporučeno soft-delete).
