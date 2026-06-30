# PRODUCT_API.md — datový kontrakt pro produkt (webová aplikace)

Tenhle dokument je **závazný kontrakt** mezi pipeline (regrantio) a produktem (zákaznická webová
aplikace, kde uživatelé prohledávají grantovou databázi). Pipeline produkuje jeden veřejný export;
produkt si ho stahuje a synchronizuje do své databáze. Vše ostatní v repu (`data/`, `scripts/`,
vrstva 2…) je interní a produkt se na to **nesmí spoléhat** — jediný stabilní povrch je tenhle export.

Generuje ho `scripts/export_api.py` z interního zdroje pravdy `data/opportunities_v2.jsonl`.

---

## 1. Kde to leží (endpoint)

Statický JSON soubor publikovaný přes GitHub Pages (žádný runtime server, žádná autentizace):

```
https://chocholous.github.io/regrantio/branches/<branch>/opportunities.json
```

- **Produkční větev:** dohodněte JEDNU stabilní větev jako produkční zdroj (dnes data vznikají na
  `coverage-expansion-next`; než se mergne do `main`, ber `branches/main/opportunities.json` jako
  produkční a `branches/<dev>/…` jako náhled). Produkt by měl číst z JEDNÉ konfigurovatelné URL.
- Soubor je ~10 MB (jeden GET, gzip přes Pages). Klidně cachuj; `meta.generated_at` je freshness signál.
- V repu je tatáž data i jako `docs/opportunities.json` (to, co se publikuje).

---

## 2. Tvar souboru

```jsonc
{
  "meta": {
    "schema_version": "1.1",            // při breaking změně schématu stoupne MAJOR
    "generated_at": "2026-06-30T14:53:37+00:00",  // UTC ISO-8601
    "generated_date": "2026-06-30",     // jen datum (pro snadné porovnání „je dnešní?")
    "count": 2749,                       // počet záznamů v grants[]
    "source": "regrantio pipeline",
    "content_hash_fields": [ ... ],      // která pole vstupují do content_hash (audit/transparentnost)
    "status_rule": "open if today<=deadline; announced if today<open_from; closed if today>deadline …"
  },
  "grants": [ { /* záznam, viz §4 */ }, ... ]
}
```

`grants[]` obsahuje DVA druhy záznamů rozlišené polem `kind`:
- `"grant"` — konkrétní dotační příležitost / výzva (drtivá většina).
- `"foundation_mission"` — nadace/fond, který zrovna NEMÁ otevřenou výzvu, ale je relevantní (mise +
  témata, kam se dá obrátit). Má jiná pole (viz §4). Produkt je může zobrazit jinak (např. „grantmaker"
  místo „výzva") nebo skrýt — ale **neměl by je řadit mezi otevřené výzvy**.

---

## 3. Jak produkt synchronizuje (povinné chování)

Export je **úplný snapshot** (vždy všechny aktuální záznamy), ne diff. Inkrementální sync:

1. **Klíč = `id`.** `id` je stabilní (= kanonická URL zdroje). UPSERT podle `id`.
2. **Změna = `content_hash`.** Každý grant nese `content_hash` (16 hex znaků) = otisk věcného obsahu.
   Pokud se `id` už v DB má a `content_hash` se NEzměnil → přeskoč (žádná práce, žádné re-indexování).
   Pokud se `content_hash` změnil → záznam se aktualizoval, přepiš ho / re-indexuj.
3. **Odebrání = chybějící `id`.** Záznam, který je v produktové DB, ale v novém exportu už NENÍ,
   byl odebrán (zdroj ho stáhl / výzva zanikla). Produkt ho má **smazat nebo archivovat**
   (soft-delete doporučeno — viz §6).
4. **Status NEpřebírej z exportu jako pravdu** — počítej ho klientsky z `open_from`/`deadline`
   k reálnému dnešku (viz §5). Pole `status`/`status_confidence` v exportu jsou jen build-time snapshot.

> `content_hash` schválně NEzahrnuje `status`/`status_confidence` (mění se sám jak míjejí deadliny) ani
> `id`. Takže hash se změní jen když se změní VĚCNÝ obsah výzvy — ne každý den. Status řeš zvlášť (§5).

Pseudokód:
```python
incoming = fetch(URL)["grants"]
incoming_ids = {g["id"] for g in incoming}
for g in incoming:
    cur = db.get(g["id"])
    if cur is None:                 db.insert(g)
    elif cur.content_hash != g["content_hash"]:  db.update(g)
    # jinak beze změny
for id in db.all_ids() - incoming_ids:
    db.soft_delete(id)             # výzva zmizela ze zdroje
```

> **Referenční implementace + důkaz:** `scripts/product_sync_example.py` obsahuje hotovou funkci
> `sync()` (zkopíruj do produktu) a `--selftest`, který na reálném exportu dokazuje insert/update/
> delete/no-op + idempotenci. Tentýž selftest běží v CI (`validate_release.py`) → kontrakt se nehne
> bez upozornění.

---

## 4. Schéma záznamu (pole)

### 4.1 Společná pole (`kind` = grant i foundation_mission)
| pole | typ | význam |
|---|---|---|
| `id` | string (URL) | **primární klíč, stabilní.** Kanonická URL zdroje. |
| `kind` | `"grant"` \| `"foundation_mission"` | druh záznamu |
| `source` | string | identifikátor zdroje (host nebo slug, např. `nsa`, `dotace.brno.cz`) |
| `source_url` | string (URL) | odkaz na originální stránku (typicky == `id`) |
| `facets` | object | kanonizované filtrovací facety (viz §4.4) |
| `citations` | object | grounding: pole → doslovná citace ze zdroje (důvěryhodnost) |
| `content_hash` | string (16 hex) | otisk věcného obsahu pro sync (viz §3) |

### 4.2 Pole `kind` = `"grant"`
| pole | typ | nullable | význam |
|---|---|---|---|
| `title` | string | ne | název výzvy |
| `focus_area` | string | ano | krátký popis zaměření |
| `open_from` | string \| null | ano | datum začátku příjmu (ISO `YYYY-MM-DD`, nebo `"průběžně"`, nebo null) |
| `deadline` | string \| null | ano | datum konce příjmu (ISO, nebo `"průběžně"`, nebo null) |
| `status` | enum | — | build-time snapshot: `open`/`announced`/`closed`/`unknown` — **přepočítej, §5** |
| `status_confidence` | string | — | jak jistý je status (info) |
| `amount` | number \| null | ano | hlavní částka v CZK (alokace / max na žadatele); **null = neuvedeno, ne 0** |
| `eligible_applicants` | string \| null | ano | kdo může žádat (próza) |
| `required_attachments` | array | — | povinné přílohy (může být prázdné) |
| `how_to_apply` | string \| null | ano | jak podat |
| `source_doc` | string \| null | ano | odkaz na zdrojový dokument (PDF výzvy…) |

### 4.3 Pole `kind` = `"foundation_mission"`
| pole | typ | význam |
|---|---|---|
| `name` | string | jméno nadace/fondu |
| `mission` | string | mise / čemu se věnuje |
| `support_topics` | array | témata, která podporuje |
| `regions` | array | působnost |

### 4.4 `facets` (filtrovací osy — kanonizované hodnoty)
Slouží k filtrování v produktu. Klíčové facety (víc viz `schema/opportunity_schema.md`):
- `typ_poskytovatele` (string): `ministerstvo`, `samosprava_kraj`, `samosprava_obec`, `statni_fond`,
  `statni_agentura`, `nadace`, `firemni_nadace`, `nadacni_fond`, `zahranicni_fond`, `evropska_komise`.
- `zdroj_financovani` (**array** stringů): `narodni_rozpocet`, `eu_fondy`, `eu_primy`, `npo`,
  `ehp_norsko`, `krajsky`, `vlastni_zdroje`, … (může být víc zdrojů zároveň).
- `oblast` (array): tematické oblasti podpory.
- `typ_zadatele` (array), `cilova_skupina` (array): kdo žádá / pro koho.
- `region` (object): `{kraj: <string|null>, celostatni: <bool>}` — pro filtr „dle kraje".
  Národní/EU poskytovatelé mají `celostatni: true`; samospráva má `kraj` doplněný.

> **Pozn.:** facety jsou `array` tam, kde výzva spadá pod víc hodnot. Produkt s nimi musí umět zacházet
> jako s mnoha-hodnotovými (kromě `typ_poskytovatele` a `region`, které jsou jednoznačné).

---

## 5. Status — počítej klientsky (NEspoléhej na snapshot)

Otevřená a uzavřená výzva jsou textově identické; liší se jen **deadlinem vs. dnešek**. Uložený `status`
je snapshot z času buildu a **zastará**. Produkt musí status přepočítat z `open_from`/`deadline` k
reálnému dnešku. Kanonické pravidlo (`scripts/opportunities.py:compute_status`, zrcadlí ho i appka):

```
deadline == "průběžně"      → open    (průběžná výzva, bez pevného konce)
deadline == null/neznámé    → unknown (neumíme určit — typicky katalogový program bez jedné lhůty)
today  >  deadline          → closed
today  <  open_from         → announced (vyhlášeno, příjem ještě nezačal)
jinak (open_from <= today <= deadline) → open
```

Doporučení: produkt si status drží jako **odvozenou hodnotu** (přepočítává při zobrazení / nočním jobu),
ne jako uloženou pravdu. Tím „open" počet přirozeně klesá, jak deadliny míjejí, bez nového exportu.

---

## 6. Odebrání, archivace, trvalé odkazy

- Záznamy mizí legitimně: výzva se uzavře a zdroj ji stáhne, nadace přestane být relevantní, zdroj
  změní URL. Pro uživatele i SEO je lepší **soft-delete** (označit `removed_at`, skrýt z vyhledávání,
  ale ponechat detail dostupný) než tvrdé smazání.
- `closed` výzvy v exportu ZŮSTÁVAJÍ, dokud je zdroj listuje (mají hodnotu jako reference / „příští rok
  zas"). Zmizení z exportu ≠ closed; je to „zdroj už to nenabízí".
- `id` (= URL) je trvalý odkaz. Pokud zdroj změní URL, vznikne nový `id` (nový záznam) a starý zmizí —
  produkt to uvidí jako delete+insert. To je přijatelné; URL grantových výzev jsou většinou stabilní.

---

## 7. Update cadence (jak často fetchovat)

- Pipeline se re-harvestuje a re-exportuje dávkově (viz `docs/REFRESH.md`). Typická kadence je
  **týdně** (otevřené výzvy se nemění po hodinách).
- Produkt: stáhni export **1× denně** (cron). Levné: porovnej `meta.generated_at` / `meta.count`;
  když se nezměnily od posledně, není co dělat. I bez nového exportu produkt **denně přepočítává status**
  (§5), takže „dnes zavřené" výzvy zmizí z „otevřených" i mezi exporty.
- Doporučený job v produktu: noční (a) fetch exportu + sync (§3), (b) přepočet statusů.

---

## 8. Verzování schématu

- `meta.schema_version` = `MAJOR.MINOR`.
- **MINOR** stoupne při zpětně kompatibilní změně (přidané pole — produkt může ignorovat). Aktuálně
  `1.1` přidalo `content_hash` + `meta.generated_date`.
- **MAJOR** stoupne při breaking změně (přejmenované/odebrané pole, změna typu). Produkt by měl při
  neočekávaném MAJORu **zastavit sync a upozornit**, ne tiše rozbít data.

---

## 9. Záruky kvality (na co se dá spolehnout)

Export je auditovaný (`scripts/fix_dataset.py` před každým buildem). Garantováno:
- `id` je unikátní a neprázdné; `title` (u grantů) neprázdné; `source_url` přítomné.
- `amount` je číslo nebo null (nikdy string/0-jako-neuvedeno); datumy jsou ISO `YYYY-MM-DD`,
  `"průběžně"`, nebo null; `deadline` není dřív než `open_from`.
- Žádné mojibake (čisté UTF-8). Žádné build-time exact duplicity (`id`).
- `content_hash` je deterministický: stejný věcný obsah → stejný hash napříč běhy.

**Co NENÍ garantováno (a je to záměr, ne chyba):** `amount=null` a `status=unknown` jsou časté a
**správné** — částka bývá jen v PDF zadávací dokumentaci a katalogové programy nemají jednu lhůtu.
Pipeline raději pošle poctivý `null` než vymyšlené číslo. Produkt to má prezentovat jako „neuvedeno",
ne 0 / „zdarma".

---

## 10. Bezpečnostní pojistka při generování

`export_api.py` má `--min-ratio` (default 0.9): pokud by nový export měl < 90 % záznamů předchozího
(příznak rozbitého harvestu), **běh se zastaví** (exit 2) a export se NEpřepíše — aby rozbitý běh
nesmazal granty z produktu. Vědomé velké smazání se povolí `--force`. Produkt tím dostává navíc
ochranu, že do něj nepřiteče náhle zdecimovaný dataset.
