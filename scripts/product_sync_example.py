#!/usr/bin/env python3
"""product_sync_example.py — REFERENČNÍ implementace sync algoritmu pro produkt (web app).

Není součástí pipeline; je to vzor pro produktový tým + self-test, který DOKAZUJE, že kontrakt
z `docs/PRODUCT_API.md §3` funguje (inkrementální sync přes `id` + `content_hash` + delete chybějících).
Funkci `sync()` zkopíruj/přepiš do produktu (jazyk dle libosti); je úmyslně bez závislostí.

  python scripts/product_sync_example.py            # demo nad docs/opportunities.json (vše insert)
  python scripts/product_sync_example.py --selftest # dokáž insert/update/delete/no-op na 2 verzích exportu
"""
import argparse, copy, json, os, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sync(db, incoming_grants):
    """Idempotentní upsert + delete. `db` = {id: content_hash} (produktová DB; zde jen otisk pro demo).
    Vrací akce. V reálu místo content_hash drž celý záznam a při update/insert ho zapiš/re-indexuj."""
    inserted, updated, unchanged, deleted = [], [], [], []
    incoming_ids = set()
    for g in incoming_grants:
        gid, h = g["id"], g["content_hash"]
        incoming_ids.add(gid)
        if gid not in db:
            inserted.append(gid)            # nový grant → INSERT + index
        elif db[gid] != h:
            updated.append(gid)             # změněný obsah → UPDATE + re-index
        else:
            unchanged.append(gid)           # beze změny → přeskoč (žádná práce)
        db[gid] = h
    for gid in list(db.keys()):
        if gid not in incoming_ids:
            deleted.append(gid)             # zmizel ze zdroje → soft-delete (viz PRODUCT_API §6)
            del db[gid]
    return {"inserted": inserted, "updated": updated, "unchanged": unchanged, "deleted": deleted}


def load_export(path):
    d = json.load(open(path, encoding="utf-8"))
    return d["meta"], d["grants"]


def demo(path):
    meta, grants = load_export(path)
    db = {}
    r = sync(db, grants)
    print(f"# DEMO sync nad {path} (prázdná DB → vše insert)")
    print(f"  export: schema {meta['schema_version']}, generated {meta.get('generated_date', '?')}, count {meta['count']}")
    print(f"  inserted={len(r['inserted'])} updated={len(r['updated'])} "
          f"unchanged={len(r['unchanged'])} deleted={len(r['deleted'])}")
    print(f"  DB nyní obsahuje {len(db)} záznamů")
    # druhý běh téhož exportu = vše unchanged (idempotence)
    r2 = sync(db, grants)
    assert not (r2["inserted"] or r2["updated"] or r2["deleted"]), "2. běh téhož exportu nemá nic měnit!"
    print(f"  re-sync téhož exportu: unchanged={len(r2['unchanged'])} (idempotentní ✓)")


def selftest(path):
    """Dokáž 4 přechody: insert / update / delete / no-op mezi export v1 → v2."""
    import hashlib
    _, grants = load_export(path)
    assert len(grants) >= 5, "potřebuju aspoň 5 záznamů"
    v1 = grants[:200]                                   # menší vzorek pro rychlost
    db = {}
    sync(db, v1)
    base = len(db)

    # Sestav v2: změň 1 (jiný content_hash), odeber 1, přidej 1, zbytek beze změny.
    v2 = copy.deepcopy(v1)
    changed_id = v2[0]["id"]
    v2[0]["content_hash"] = hashlib.sha1(b"NOVY_OBSAH").hexdigest()[:16]   # simuluj změnu obsahu
    removed_id = v2[1]["id"]
    del v2[1]                                                              # odeber 2. záznam
    new_grant = {"id": "https://example.test/novy-grant", "content_hash": "ffffffffffffffff"}
    v2.append(new_grant)                                                   # přidej nový

    r = sync(db, v2)
    ok = (r["updated"] == [changed_id]
          and r["deleted"] == [removed_id]
          and r["inserted"] == [new_grant["id"]]
          and len(r["unchanged"]) == base - 2          # všechny kromě změněného a odebraného
          and len(db) == base)                          # +1 nový, -1 odebraný = stejný počet
    print("# SELFTEST sync v1 → v2")
    print(f"  base={base}  updated={r['updated']}  deleted={r['deleted']}  inserted={r['inserted']}  "
          f"unchanged={len(r['unchanged'])}  db={len(db)}")
    if ok:
        print("  ✓ PASS — insert/update/delete/no-op přesně dle kontraktu")
        return 0
    print("  ✗ FAIL — sync se nechová dle PRODUCT_API §3")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=os.path.join(ROOT, "docs", "opportunities.json"))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest(a.inp))
    demo(a.inp)


if __name__ == "__main__":
    main()
