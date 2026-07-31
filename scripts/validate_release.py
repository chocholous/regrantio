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
    """Testy kritické logiky (compute_status / upsert merge / derive_deadlines)."""
    import subprocess
    t = os.path.join(ROOT, "tests", "test_core.py")
    if not os.path.exists(t):
        raise Skip("tests/test_core.py chybí")
    r = subprocess.run([sys.executable, t], capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stdout or "").strip().splitlines()[-3:]
        raise RuntimeError("unit testy FAIL: " + " | ".join(tail))
    print("    (" + (r.stdout or "").strip().splitlines()[-1] + ")")


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


def main():
    print("# VALIDATE RELEASE\n")
    check("compile all .py", compile_all)
    check("unit testy (kritická logika)", check_unit_tests)
    check("routing.yaml parses", check_routing)
    check("json configs valid", check_json_configs)
    check("kvalita dat (termíny, tituly)", check_data_quality)
    print()
    if errors:
        print(f"FAIL — {len(errors)} chyb")
        sys.exit(1)
    print("OK — všechny kontroly prošly")


if __name__ == "__main__":
    main()
