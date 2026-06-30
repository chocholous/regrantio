#!/usr/bin/env python3
"""validate_release.py — release/CI gate nad GIT-TRACKED soubory (běží i bez gitignored data/).

Chytá třídu chyb, co prošla do produkce (rozbitý routing.yaml = ASCII `"` v českém stringu) a hlídá
veřejný kontrakt produktu (docs/opportunities.json). Spouštěj lokálně před pushem i v GitHub Actions.

Kontroly:
  1. py_compile všech scripts/*.py + data/_*_extract.py + pipeline.py (syntax)
  2. routing.yaml se parsuje (yaml.safe_load) + má `families`/`sources`/`default`
  3. platform_map.json + limits.json jsou validní JSON
  4. docs/opportunities.json = veřejný kontrakt: meta(schema_version/count/generated_at), count==len,
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


def check(name, fn):
    try:
        fn()
        print(f"  ✓ {name}")
    except Exception as e:
        errors.append(f"{name}: {e}")
        print(f"  ✗ {name}: {e}")


def compile_all():
    bad = []
    files = glob.glob("scripts/*.py") + glob.glob("data/_*_extract.py")
    if os.path.exists("pipeline.py"):
        files.append("pipeline.py")
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


def main():
    print("# VALIDATE RELEASE\n")
    check("compile all .py", compile_all)
    check("routing.yaml parses", check_routing)
    check("json configs valid", check_json_configs)
    check("product contract (opportunities.json)", check_product_contract)
    print()
    if errors:
        print(f"FAIL — {len(errors)} chyb")
        sys.exit(1)
    print("OK — všechny kontroly prošly")


if __name__ == "__main__":
    main()
