#!/usr/bin/env python3
"""publish_db.py — PUBLIKACE KATALOGU PŘÍMO DO DATABÁZE PRODUKTU.

    python scripts/publish_db.py --dry-run     # spočítej, nic nezapisuj
    python scripts/publish_db.py               # zapiš
    python scripts/publish_db.py --force       # obejdi pojistky (vědomě!)

PROČ TENHLE SKRIPT EXISTUJE
───────────────────────────
Do 2026-09-04 vedla cesta dat do produktu přes DRUHÝ repozitář: regrantio
vyrobilo `docs/opportunities.json`, pushlo ho na GitHub, a v `the-machine-app`
se pustil `node scripts/ingest-catalog.mjs`, který si ho stáhl zpátky po HTTP
a zapsal do databáze. Dva příkazy ve dvou repozitářích, dvě prostředí a jedna
okружní cesta přes internet pro soubor, který leží na disku vedle.

Tenhle skript je táž práce v jednom kroku. `ingest-catalog.mjs` se tím ruší;
implementace je JEDNA a je tady.

⚠ PUBLIKUJE SE EXPORT, NE KATALOG. Vstupem je `docs/opportunities.json`, ne
`data/opportunities.jsonl`. Dva důvody, oba podstatné:
  1. Export vzniká AŽ ZA BRÁNOU KVALITY (`validate_release.py` v `refresh_run`
     stojí před `export_api.py`). Publikovat katalog by tu bránu obešlo.
  2. Export je kurátorovaný — nese 11 polí z 12, bez `provenance` a `extra`.
     Přesně to je „zdrojová reprezentace“, kterou produkt drží v `raw`.

⚠ TŘI POJISTKY, A KAŽDÁ SE PTÁ NA NĚCO JINÉHO. Zdědily se z `ingest-catalog.mjs`
i s odůvodněním, protože každá vznikla z konkrétní naměřené situace:
  • ČAS   — nový export nesmí být starší než data v katalogu. Jediná pojistka,
            která chytí „nahráli jsme loňský soubor“; ty dvě níž měří velikost
            a starší export je skoro stejně velký jako nový.
  • POČET — nový sběr musí mít aspoň 80 % dosavadních záznamů.
  • ÚBYTEK— najednou nesmí zmizet víc než pětina.

⚠ NIC SE NEMAŽE. Záznam, který z feedu zmizel, dostane `withdrawn_at`. Někdo si
ho může mít uložený a smazaný řádek by z jeho seznamu udělal prázdné místo.

Prostředí (`.env` v kořeni regrantia, nikdy v gitu):
    PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
    SUPABASE_SERVICE_ROLE_KEY=<service role>

⚠ ZAPISUJE SE POD SERVICE ROLE. `catalog_grant` má zapnutou RLS a žádná role
z prohlížeče do ní psát nesmí.
"""
import argparse
import datetime
import json
import os
import ssl
import sys
import unicodedata
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr:
        sys.stderr.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT = os.path.join(ROOT, "docs", "opportunities.json")

# MAJOR verze kontraktu, které rozumíme. MINOR přírůstek je zpětně kompatibilní
# (`docs/EXPORT.md` §4); MAJOR znamená přejmenované nebo odebrané pole — na to
# musí reagovat člověk, ne tichý import.
EXPECTED_MAJOR = "1"

MIN_RATIO = 0.8            # nový sběr nesmí mít míň než 80 % dosavadních záznamů
MAX_WITHDRAWN_RATIO = 0.2  # najednou nesmí zmizet víc než pětina
CHUNK = 500                # řádků na jeden požadavek (strop na velikost těla)

# Slovní termíny, které znamenají „bere se pořád“.
ROLLING = {"průběžně", "rolling", "průběžný", "prubezne"}


# ---------------------------------------------------------------- mapování
def _str(v):
    """Neprázdný řetězec, nebo None. Prázdný řetězec je chybějící hodnota."""
    if not isinstance(v, str):
        return None
    t = v.strip()
    return t or None


def _list(v):
    """Pole neprázdných řetězců, bez duplicit, v původním pořadí."""
    if not isinstance(v, list):
        return []
    out = []
    for item in v:
        s = _str(item)
        if s and s not in out:
            out.append(s)
    return out


def _money(v):
    """Konečné nezáporné číslo, jinak None.

    ⚠ `bool` je v Pythonu podtyp `int`, takže `True` by prošlo jako částka 1.
    """
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if v != v or v in (float("inf"), float("-inf")) or v < 0:  # NaN / ±inf / záporné
        return None
    return v


def _bool(v):
    return v if isinstance(v, bool) else None


def iso_date(value):
    """Prvních deset znaků, jsou-li to `YYYY-MM-DD`. Jinak None.

    Zrcadlí `isoDate` z `src/lib/catalog/status.ts`: feed umí i slovní termín
    („průběžně“), který se do sloupce `date` nevejde.
    """
    s = value or ""
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        d = s[:10]
        if d[:4].isdigit() and d[5:7].isdigit() and d[8:10].isdigit():
            return d
    return None


def normalize_text(s):
    """Malá písmena bez diakritiky.

    ⚠ MUSÍ DÁVAT TOTÉŽ CO `normalizeText` v `src/lib/catalog/search.ts`.
    Aplikace tou funkcí normalizuje DOTAZ a databáze drží normalizovaný TEXT;
    kdyby se rozešly, projeví se to jako „na vývoji to najde, v produkci ne“.
    Rozklad NFD oddělí háčky a čárky do samostatných znaků U+0300–U+036F,
    které se zahodí — takže „skoly“ najde „školy“.
    """
    d = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in d if not (0x0300 <= ord(c) <= 0x036F))


def _as_js_string(v):
    """Převod na text tak, jak by ho udělal JavaScript.

    ⚠ NENÍ TO KOSMETIKA. `eligible_applicants` je u 173 z 3 525 záznamů POLE,
    ne řetězec — vrstva 2 ho tak u některých zdrojů vrací. Původní implementace
    v `join(' ')` spoléhala na to, že JS pole tiše převede: `String(["a","b"])`
    je `"a,b"`, tedy čárkou, ne mezerou. Python by na tomtéž spadl.

    Naměřeno při přenosu mapování do regrantia (2026-09-04): bez tohohle se
    173 záznamům rozešel `search_text` a v produktu by se přestaly hledat podle
    okruhu žadatelů. Pravidlo se proto zrcadlí doslova, ne „rozumněji“ —
    normalizace textu musí dopadnout stejně na obou stranách.
    """
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return ",".join(_as_js_string(x) for x in v)
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def search_haystack(g):
    """Text, ve kterém se u výzvy hledá — čtyři pole, ne celý záznam.

    Název, zaměření, okruh žadatelů a jméno zdroje. Kdyby se přidal postup
    podání, začal by dotaz „elektronicky“ vracet půlku katalogu.
    """
    parts = [g.get("title"), g.get("focus_area"), g.get("eligible_applicants"), g.get("source")]
    # `filter(Boolean)` v JS zahodí null, undefined i PRÁZDNÝ ŘETĚZEC a prázdné
    # pole `[]` naopak nechá (je pravdivé) → přispěje prázdným řetězcem.
    kept = [_as_js_string(p) for p in parts if not (p is None or p == "" or p is False)]
    return normalize_text(" ".join(kept))


def to_row(g):
    """Záznam z exportu → řádek `catalog_grant`. Vrací (row, None) nebo (None, důvod).

    PŘÍSNOST: záznam se zahazuje JEN tehdy, když nemá identitu (`id`, `kind`,
    `source`, `source_url`). Vadná jednotlivá hodnota se zahodí sama a záznam
    projde — vyhodit celou výzvu kvůli jedné částce by znamenalo schovat
    uživateli podporu, o kterou si může říct.
    """
    if not isinstance(g, dict):
        return None, "záznam není objekt"
    gid = _str(g.get("id"))
    if not gid:
        return None, "chybí id"
    kind = g.get("kind")
    if kind not in ("grant", "foundation_mission"):
        return None, f"neznámý kind: {kind}"
    source = _str(g.get("source"))
    if not source:
        return None, "chybí source"
    source_url = _str(g.get("source_url"))
    if not source_url:
        return None, "chybí source_url"

    f = g.get("facets") or {}
    region = f.get("region") or {}
    deadline_raw = _str(g.get("deadline"))
    open_from_raw = _str(g.get("open_from"))

    return {
        "id": gid,
        "kind": kind,
        "source": source,
        "source_url": source_url,
        "title": _str(g.get("title")),
        "focus_area": _str(g.get("focus_area")),
        "eligible_applicants": _str(g.get("eligible_applicants")),
        "how_to_apply": _str(g.get("how_to_apply")),
        "source_doc": _str(g.get("source_doc")),
        # Datum se ukládá DVAKRÁT: jednou jako `date` pro řazení a filtry,
        # jednou syrově, protože feed umí i slovní termín a uživatel ho má vidět.
        "open_from": iso_date(open_from_raw),
        "deadline": iso_date(deadline_raw),
        "open_from_raw": open_from_raw,
        "deadline_raw": deadline_raw,
        "deadline_rolling": deadline_raw is not None and deadline_raw.lower() in ROLLING,
        "amount": _money(g.get("amount")),
        "oblast": _list(f.get("oblast")),
        "typ_zadatele": _list(f.get("typ_zadatele")),
        "sektor_zadatele": _list(f.get("sektor_zadatele")),
        "forma_podpory": _list(f.get("forma_podpory")),
        "zdroj_financovani": _list(f.get("zdroj_financovani")),
        "cilova_skupina": _list(f.get("cilova_skupina")),
        "zpusob_podani": _list(f.get("zpusob_podani")),
        "typ_poskytovatele": _str(f.get("typ_poskytovatele")),
        "rezim_prijmu": _str(f.get("rezim_prijmu")),
        "kraj": _str(region.get("kraj")),
        "obec": _str(region.get("obec")),
        "celostatni": _bool(region.get("celostatni")),
        "search_text": search_haystack(g),
        "raw": g,
        "content_hash": _str(g.get("content_hash")),
    }, None


def has_changed(row, stored_hash):
    """Rozhoduje `content_hash` z regrantia — je to jeho vlastní otisk obsahu.

    Když otisk chybí, bereme záznam jako změněný: přepsat shodná data je levné,
    minout skutečnou změnu ne.
    """
    if not row.get("content_hash") or not stored_hash:
        return True
    return row["content_hash"] != stored_hash


def change_worth_recording(before, after):
    """Ne každý přepis je událost — řádek vzniká jen u posunu LHŮTY nebo ČÁSTKY.

    ⚠ POROVNÁNÍ ČÍSEL PŘES `float(x or nan)` JE PAST a v Node verzi stálo 155
    prázdných řádků v ostré databázi: `NaN != NaN`, takže se každá výzva BEZ
    ČÁSTKY tvářila, že se jí částka právě změnila — a částku má 22 % katalogu.
    Proto se porovnává None s None, ne NaN s NaN.
    """
    if not before:
        return True  # nový záznam je vždycky událost

    def num(v):
        if v is None or v == "":
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    deadline_moved = str(before.get("deadline") or "") != str(after.get("deadline") or "")
    amount_moved = num(before.get("amount")) != num(after.get("amount"))
    return deadline_moved or amount_moved


# ---------------------------------------------------------------- PostgREST
class Db:
    """Tenký klient nad PostgREST. Bez závislosti — `urllib` stačí."""

    def __init__(self, url, key):
        self.base = url.rstrip("/") + "/rest/v1/"
        self.key = key
        self.ctx = ssl.create_default_context()
        try:
            import truststore
            self.ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        except Exception:  # noqa: BLE001
            pass

    def _req(self, method, path, body=None, prefer=None):
        h = {
            "apikey": self.key,
            "Authorization": "Bearer " + self.key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if prefer:
            h["Prefer"] = prefer
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, headers=h, method=method)
        try:
            with urllib.request.urlopen(req, timeout=180, context=self.ctx) as r:
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            raise RuntimeError(f"{method} {path} → HTTP {e.code}: {detail}") from None

    def select(self, path):
        return self._req("GET", path)

    def select_all(self, table, cols):
        """Čte PO STRÁNKÁCH.

        ⚠ PostgREST vrací nejvýš tisíc řádků na dotaz a tichý ořez by vypadal
        jako „všechno je nové“ — tedy jako přepis celého katalogu.
        """
        out, page = [], 0
        while True:
            got = self._req("GET", f"{table}?select={cols}&limit=1000&offset={page * 1000}")
            if not got:
                break
            out.extend(got)
            if len(got) < 1000:
                break
            page += 1
        return out

    def insert(self, table, rows, upsert=False):
        prefer = "return=representation" if upsert is False else "resolution=merge-duplicates,return=minimal"
        return self._req("POST", table, rows, prefer=prefer)

    def upsert(self, table, rows):
        return self._req("POST", table, rows, prefer="resolution=merge-duplicates,return=minimal")

    def patch(self, table, filt, body):
        return self._req("PATCH", f"{table}?{filt}", body, prefer="return=minimal")


def load_env():
    """`.env` v kořeni regrantia. Bez závislosti na python-dotenv."""
    p = os.path.join(ROOT, ".env")
    if not os.path.exists(p):
        return
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="inp", default=EXPORT, help="publikovaný export")
    ap.add_argument("--dry-run", action="store_true", help="spočítej, nic nezapisuj")
    ap.add_argument("--force", action="store_true", help="obejdi pojistky (vědomě!)")
    a = ap.parse_args()

    load_env()

    # --- 1. NAČÍST A OVĚŘIT KONTRAKT -----------------------------------------
    if not os.path.exists(a.inp):
        print(f"✖ Export {a.inp} neexistuje. Pusť nejdřív scripts/export_api.py.")
        return 1
    feed = json.load(open(a.inp, encoding="utf-8"))
    meta, grants = feed.get("meta") or {}, feed.get("grants")
    if not meta.get("schema_version") or not isinstance(grants, list):
        print("✖ Export nemá očekávaný tvar { meta, grants[] } — změnil se kontrakt?")
        return 1
    major = str(meta["schema_version"]).split(".")[0]
    if major != EXPECTED_MAJOR:
        print(f"✖ Nekompatibilní schema_version: {meta['schema_version']} (čekáno {EXPECTED_MAJOR}.x)")
        print("  Zkontroluj docs/EXPORT.md a uprav mapování, než publikaci pustíš znovu.")
        return 1

    print(f"· Zdroj: {os.path.relpath(a.inp, ROOT)}")
    print(f"· Kontrakt {meta['schema_version']}, data z pipeline {meta.get('generated_at')}")

    # --- 2. PŘELOŽIT ----------------------------------------------------------
    rows, rejected = [], []
    for g in grants:
        row, why = to_row(g)
        (rows.append(row) if row else rejected.append((g.get("id") if isinstance(g, dict) else None, why)))
    if not rows:
        print("✖ Po překladu nezbyl ani jeden použitelný záznam.")
        return 1
    print(f"· Přeloženo {len(rows)} záznamů, zahozeno {len(rejected)}")
    for rid, why in rejected[:10]:
        print(f"  ⚠ {rid or '(bez id)'}: {why}")
    if len(rejected) > 10:
        print(f"  ⚠ … a dalších {len(rejected) - 10}")

    # Duplicitní id by v dávkovém zápisu tiše přepsalo samo sebe.
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        seen, dup = set(), []
        for i in ids:
            if i in seen:
                dup.append(i)
            seen.add(i)
        print(f"✖ Export obsahuje {len(dup)} duplicitních id, například {', '.join(dup[:3])}")
        return 1

    # --- 3. PŘIPOJIT ----------------------------------------------------------
    url = os.environ.get("PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    have_db = bool(url and key)
    dry = a.dry_run or not have_db
    if dry and not a.dry_run:
        print("\n· BEZ PŘÍSTUPU K DATABÁZI — projdu vše kromě zápisu.")
        print("  Chybí PUBLIC_SUPABASE_URL nebo SUPABASE_SERVICE_ROLE_KEY v .env.")

    existing, previous_generated = {}, None
    db = None
    # ⚠ NASUCHO SE DATABÁZE ČTE, JEN SE DO NÍ NEZAPISUJE.
    #
    # Zděděná verze (`ingest-catalog.mjs`) při `--dry-run` databázi vůbec
    # neotevřela, takže hlásila „nových 3525, změněných 0" — tedy že se přepíše
    # celý katalog. To není zkouška, to je jiná odpověď na jinou otázku.
    # Běh nasucho má říct, CO BY SE STALO; k tomu musí vidět dosavadní stav.
    if have_db:
        db = Db(url, key)
        last = db.select("catalog_import?select=generated_at&status=eq.ok"
                         "&order=finished_at.desc&limit=1")
        previous_generated = (last[0]["generated_at"] if last else None)
        for r in db.select_all("catalog_grant", "id,content_hash,deadline,amount,withdrawn_at"):
            existing[r["id"]] = r
        print(f"· V databázi je {len(existing)} záznamů")

    # --- 4. POROVNAT ----------------------------------------------------------
    incoming = {r["id"] for r in rows}
    to_insert, to_update, unchanged = [], [], 0
    for row in rows:
        prev = existing.get(row["id"])
        if not prev:
            to_insert.append(row)
        elif has_changed(row, prev.get("content_hash")) or prev.get("withdrawn_at"):
            to_update.append(row)
        else:
            unchanged += 1
    to_withdraw = [i for i, r in existing.items() if i not in incoming and not r.get("withdrawn_at")]

    print()
    print(f"  nových      {len(to_insert)}")
    print(f"  změněných   {len(to_update)}")
    print(f"  beze změny  {unchanged}")
    print(f"  ke stažení  {len(to_withdraw)}")

    # --- 5. POJISTKY ----------------------------------------------------------
    problems = []
    if previous_generated and meta.get("generated_at"):
        def ts(x):
            try:
                return datetime.datetime.fromisoformat(str(x).replace("Z", "+00:00"))
            except ValueError:
                return None
        new_t, old_t = ts(meta["generated_at"]), ts(previous_generated)
        if new_t and old_t and new_t < old_t:
            problems.append(f"export je STARŠÍ než data v katalogu: nabízí se "
                            f"{meta['generated_at']}, uvnitř už je {previous_generated}")
    if existing:
        ratio = len(rows) / len(existing)
        wratio = len(to_withdraw) / len(existing)
        if ratio < MIN_RATIO:
            problems.append(f"nový sběr má {ratio * 100:.1f} % dosavadních záznamů "
                            f"(práh {MIN_RATIO * 100:.0f} %)")
        if wratio > MAX_WITHDRAWN_RATIO:
            problems.append(f"najednou by zmizelo {wratio * 100:.1f} % záznamů "
                            f"(práh {MAX_WITHDRAWN_RATIO * 100:.0f} %)")
    if problems:
        print()
        for p in problems:
            print(f"✖ {p}", file=sys.stderr)
        if not a.force:
            print("✖ Pojistka zastavila publikaci. Zkontroluj běh; přepsat lze pomocí --force.")
            return 1
        print("⚠ --force: pokračuju navzdory pojistce.")

    if dry:
        print("\n✓ Nasucho hotovo. Data i mapování prošly, zapisovat se nebude.")
        return 0

    # --- 6. ZAPSAT ------------------------------------------------------------
    run = db.insert("catalog_import", [{
        "schema_version": meta["schema_version"],
        "generated_at": meta.get("generated_at"),
        "total": len(rows),
        "status": "running",
        "source_url": "regrantio:" + os.path.relpath(a.inp, ROOT).replace("\\", "/"),
    }])
    run_id = run[0]["id"]

    def finish(status, note=None):
        db.patch("catalog_import", f"id=eq.{run_id}", {
            "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "inserted": len(to_insert), "updated": len(to_update),
            "unchanged": unchanged, "withdrawn": len(to_withdraw),
            "rejected": len(rejected), "status": status, "note": note,
        })

    try:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        changes = []
        for row in to_insert + to_update:
            prev = existing.get(row["id"])
            kind = "created" if not prev else ("restored" if prev.get("withdrawn_at") else "updated")
            if kind != "updated" or change_worth_recording(prev, row):
                changes.append({
                    "grant_id": row["id"], "import_id": run_id, "kind": kind,
                    "deadline_before": (prev or {}).get("deadline"),
                    "deadline_after": row["deadline"],
                    "amount_before": (prev or {}).get("amount"),
                    "amount_after": row["amount"],
                })

        payload = []
        for row in to_insert + to_update:
            r = dict(row)
            r["last_seen_at"] = now
            r["updated_at"] = now
            r["withdrawn_at"] = None   # návrat záznamu zpět mezi živé
            payload.append(r)

        written = 0
        for i in range(0, len(payload), CHUNK):
            db.upsert("catalog_grant", payload[i:i + CHUNK])
            written += len(payload[i:i + CHUNK])
            print(f"  zapsáno {written} / {len(payload)}", end="\r")
        if payload:
            print(f"  zapsáno {written} / {len(payload)}")

        # ⚠ STAŽENÍ JE OZNAČENÍ, NE SMAZÁNÍ.
        if to_withdraw:
            for i in range(0, len(to_withdraw), CHUNK):
                part = to_withdraw[i:i + CHUNK]
                lst = ",".join('"' + x.replace('"', '\\"') + '"' for x in part)
                db.patch("catalog_grant", f"id=in.({lst})", {"withdrawn_at": now})
                changes.extend({"grant_id": x, "import_id": run_id, "kind": "withdrawn"} for x in part)
            print(f"  staženo {len(to_withdraw)}")

        for i in range(0, len(changes), CHUNK):
            db.upsert("catalog_grant_change", changes[i:i + CHUNK])

        finish("ok")
        print(f"\n✓ Hotovo. Běh #{run_id}: +{len(to_insert)} ~{len(to_update)} "
              f"−{len(to_withdraw)}, {len(changes)} změn k oznámení.")
        return 0
    except Exception as e:  # noqa: BLE001
        finish("failed", str(e)[:400])
        print(f"\n✖ Zápis selhal: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
