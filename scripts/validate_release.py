#!/usr/bin/env python3
"""validate_release.py — release/CI gate nad GIT-TRACKED soubory (běží i bez gitignored data/).

Chytá třídu chyb, co prošla do produkce (rozbitý routing.yaml = ASCII `"` v českém stringu) a hlídá
publikovaný export (docs/opportunities.json). Spouštěj lokálně před pushem i v GitHub Actions.

Kontroly:
  1. py_compile všech scripts/*.py + data/_*_extract.py (syntax)
  1b. unit testy tests/test_core.py — compute_status, upsert merge, derive_deadlines
  2. routing.yaml se parsuje (yaml.safe_load) + má `families`/`sources`/`default`
  3. platform_map.json + limits.json jsou validní JSON
  4. docs/opportunities.json = publikovaný export: meta(schema_version/count/generated_at), count==len,
     každý grant má neprázdné `id` + `content_hash`, `id` unikátní, a content_hash je REPRODUKOVATELNÝ
     (přepočet dle export_api.content_hash sedí → export logika je konzistentní).

Exit 0 = OK, 1 = našla chyby (vypsané). Bez argumentů; pouští se z kořene repa.
"""
import glob, json, os, sys, py_compile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
errors = []
EXPORT = "docs/opportunities.json"   # veřejný kontrakt (generuje scripts/export_api.py)


class Skip(Exception):
    """Kontrolu nelze provést v tomhle prostředí (např. CI bez gitignored dat)."""


def check(name, fn):
    try:
        fn()
        print(f"  ✓ {name}")
    except Skip as e:
        print(f"  — {name}: SKIP ({e})")
    except Exception as e:
        errors.append(f"{name}: {e}")
        print(f"  ✗ {name}: {e}")


def compile_all():
    bad = []
    files = glob.glob("scripts/*.py") + glob.glob("data/_*_extract.py")
    for f in files:
        try:
            py_compile.compile(f, doraise=True)
        except py_compile.PyCompileError as e:
            bad.append(f"{f}: {str(e).splitlines()[0][:80]}")
    if bad:
        raise RuntimeError(f"{len(bad)} syntax errors → " + " | ".join(bad[:5]))
    print(f"    ({len(files)} .py souborů zkompilováno)")


def check_routing():
    import yaml
    d = yaml.safe_load(open("routing.yaml", encoding="utf-8"))
    for k in ("families", "sources", "default"):
        if k not in d:
            raise RuntimeError(f"chybí klíč `{k}`")
    print(f"    ({len(d['sources'])} sources, {len(d['families'])} families)")


def check_json_configs():
    for f in ("platform_map.json", "limits.json"):
        json.load(open(f, encoding="utf-8"))


def check_product_contract():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import export_api
    d = json.load(open("docs/opportunities.json", encoding="utf-8"))
    meta, grants = d.get("meta", {}), d.get("grants", [])
    for k in ("schema_version", "count", "generated_at"):
        if k not in meta:
            raise RuntimeError(f"meta chybí `{k}`")
    if meta["count"] != len(grants):
        raise RuntimeError(f"meta.count={meta['count']} != len(grants)={len(grants)}")
    if not grants:
        raise RuntimeError("grants je prázdné")
    ids, no_hash, hash_mismatch = set(), 0, 0
    for g in grants:
        gid = g.get("id")
        if not gid:
            raise RuntimeError("grant bez `id`")
        ids.add(gid)
        if not g.get("content_hash"):
            no_hash += 1
            continue
        recomputed = export_api.content_hash({k: v for k, v in g.items() if k != "content_hash"})
        if recomputed != g["content_hash"]:
            hash_mismatch += 1
    if len(ids) != len(grants):
        raise RuntimeError(f"duplicitní id: {len(grants) - len(ids)}")
    if no_hash:
        raise RuntimeError(f"{no_hash} grantů bez content_hash")
    if hash_mismatch:
        raise RuntimeError(f"{hash_mismatch} content_hash nereprodukovatelných (export logika nesedí)")
    print(f"    (schema {meta['schema_version']}, {len(grants)} grantů, id unikátní, hash konzistentní)")


def check_unit_tests():
    """Testy kritické logiky a publikační cesty.

    ⚠ OBA SOUBORY, ne jen `test_core`. `test_publish` hlídá manifest, otisk,
    pořadí nahrávání a brány — tedy věci, které se projeví AŽ U ZÁKAZNÍKA
    (rozbitá synchronizace, stažený kus souboru) a u nás vypadají jako úspěch.
    """
    import subprocess
    results = []
    for name in ("test_core.py", "test_identity.py", "test_publish.py"):
        t = os.path.join(ROOT, "tests", name)
        if not os.path.exists(t):
            continue
        r = subprocess.run([sys.executable, t], capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            tail = (r.stdout or "").strip().splitlines()[-3:]
            raise RuntimeError(f"{name} FAIL: " + " | ".join(tail))
        results.append(f"{name}: " + (r.stdout or "").strip().splitlines()[-1])
    if not results:
        raise Skip("tests/ chybí")
    print("    (" + "; ".join(results) + ")")


def check_data_quality():
    """Kvalita DAT v exportu — chytá to, co projde schématem, ale je věcně špatně.

    Proč: 24 z 38 harvesterů si nese vlastní parser českého data BEZ validace rozsahu
    (audit 2026-07-31) → umí vyrobit 2026-13-45. Dnes to zachytí sanitizace ve fix_dataset,
    ale to je záchranná síť bez pojistky. Tahle kontrola je ta pojistka."""
    import datetime as _dt
    if not os.path.exists(EXPORT):
        raise Skip(f"{EXPORT} není v pracovní kopii")
    grants = json.load(open(EXPORT, encoding="utf-8"))["grants"]
    bad_date, bad_range, inverted, empty_title = [], [], [], 0
    for g in grants:
        for f in ("open_from", "deadline"):
            v = g.get(f)
            if v in (None, "", "průběžně"):
                continue
            try:
                d = _dt.date.fromisoformat(str(v))
            except ValueError:
                bad_date.append(f"{g.get('id','?')[:50]}:{f}={v}")
                continue
            if not (2000 <= d.year <= 2035):
                bad_range.append(f"{g.get('id','?')[:50]}:{f}={v}")
        of, dl = g.get("open_from"), g.get("deadline")
        try:
            if of and dl and _dt.date.fromisoformat(str(of)) > _dt.date.fromisoformat(str(dl)):
                inverted.append(g.get("id", "?")[:50])
        except ValueError:
            pass
        if g.get("kind") == "grant" and not (g.get("title") or "").strip():
            empty_title += 1
    problems = []
    if bad_date:
        problems.append(f"{len(bad_date)} neplatných dat ({bad_date[0]})")
    if bad_range:
        problems.append(f"{len(bad_range)} dat mimo 2000–2035 ({bad_range[0]})")
    if inverted:
        problems.append(f"{len(inverted)} × deadline < open_from ({inverted[0]})")
    if empty_title:
        problems.append(f"{empty_title} grantů bez title")
    if problems:
        raise RuntimeError("; ".join(problems))
    print(f"    ({len(grants)} záznamů: data platná, žádné inverzní termíny, tituly neprázdné)")


CATALOG = "data/opportunities.jsonl"   # živý katalog (gitignored kromě tohohle souboru)

# Kolik smí nový sběr ztratit proti minule publikovanému exportu, než se to
# začne považovat za poruchu, a ne za úklid.
MIN_RATIO = 0.8


def check_no_collapse():
    """PROPAD POČTU ZÁZNAMŮ — pojistka proti publikaci zmrzačeného datasetu.

    ⚠ TOHLE JE JEDINÁ KONTROLA, KTERÁ SE PTÁ „KOLIK", A CHYBĚLA.

    Ostatní brány se dívají na jednotlivý záznam: platné datum, neprázdný titul,
    unikátní id. Dataset, ze kterého vypadlo pět zdrojů, tím projde bez jediné
    námitky — každý ze zbylých záznamů je totiž v pořádku. Nejhorší možný běh
    není ten, který spadne; je to ten, který v tichosti publikuje dvacetinu dat.

    ⚠ POROVNÁVÁ SE PROTI MINULE PUBLIKOVANÉMU EXPORTU, A TO JDE JEN TADY.
    Brána běží PŘED `export_api.py`, takže `docs/opportunities.json` je v tuhle
    chvíli ještě ta STARÁ verze a `data/opportunities.jsonl` už ta nová. O krok
    později by se porovnával export sám se sebou.

    ⚠ RŮST SE NEHLÍDÁ. Nový zdroj přinese skokem stovky záznamů a je to přesně
    to, co má pipeline dělat. Horní práh by znamenal bránu, která zastaví
    úspěch.

    Grantio má vlastní pojistku na svém vstupu (`ingest-catalog.mjs`) a ta
    zůstává: mezi námi a produktem je přenos souboru, což je jiná třída chyb.
    Tahle hlídá NÁŠ výstup.
    """
    if not os.path.exists(CATALOG):
        raise Skip(f"{CATALOG} není v pracovní kopii")
    if not os.path.exists(EXPORT):
        raise Skip(f"{EXPORT} není v pracovní kopii — první publikace nemá s čím porovnávat")

    with open(CATALOG, encoding="utf-8") as fh:
        now = sum(1 for line in fh if line.strip())

    previous = len(json.load(open(EXPORT, encoding="utf-8")).get("grants") or [])
    if previous == 0:
        raise Skip("minulý export je prázdný")

    ratio = now / previous
    if ratio < MIN_RATIO:
        raise RuntimeError(
            f"katalog má {now} záznamů proti {previous} v minulém exportu "
            f"({ratio * 100:.1f} %, práh {MIN_RATIO * 100:.0f} %). "
            f"Nejspíš vypadl zdroj — zkontroluj shrnutí refreshe, než tohle publikuješ."
        )

    print(f"    ({now} záznamů, minule {previous}, {now - previous:+d})")


def check_catalog_identity():
    """Identita záznamů v katalogu: bez id se nedá nic sledovat, duplicita mate.

    ⚠ HLÍDÁ SE TU KATALOG, NE EXPORT. `check_data_quality` kontroluje unikátnost
    až v exportu — jenže tam se duplicita projeví jako tichý přepis: dva záznamy
    se stejným id se v produktu slijí v jeden a ten druhý prostě zmizí. V tuhle
    chvíli ještě jde poznat, který zdroj ho vyrobil.
    """
    if not os.path.exists(CATALOG):
        raise Skip(f"{CATALOG} není v pracovní kopii")

    seen, dupes, missing = set(), [], 0
    with open(CATALOG, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            rid = rec.get("id")
            if not rid:
                missing += 1
                continue
            if rid in seen:
                dupes.append(f"{rec.get('source', '?')}:{str(rid)[:60]}")
            seen.add(rid)

    problems = []
    if missing:
        problems.append(f"{missing} záznamů bez id")
    if dupes:
        problems.append(f"{len(dupes)} duplicitních id (např. {dupes[0]})")
    if problems:
        raise RuntimeError("; ".join(problems))
    print(f"    ({len(seen)} unikátních id, žádné chybějící)")


def main():
    print("# VALIDATE RELEASE\n")
    check("compile all .py", compile_all)
    check("unit testy (kritická logika)", check_unit_tests)
    check("routing.yaml parses", check_routing)
    check("json configs valid", check_json_configs)
    check("kvalita dat (termíny, tituly)", check_data_quality)
    check("identita záznamů v katalogu", check_catalog_identity)
    check("propad počtu záznamů (brána)", check_no_collapse)
    print()
    if errors:
        print(f"FAIL — {len(errors)} chyb")
        sys.exit(1)
    print("OK — všechny kontroly prošly")


if __name__ == "__main__":
    main()
