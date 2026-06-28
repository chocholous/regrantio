#!/usr/bin/env python3
"""Routing — platforma → harvester (Fáze 0). Jediný zdroj pravdy "čím harvestovat".

route(platforma)        → {harvester[], method, layer2, note}  (nebo default)
route_host(host)        → (platforma z platform_map, routing entry)
CLI:
  python3 scripts/routing.py --host nadacecez.cz
  python3 scripts/routing.py --platform vismo
  python3 scripts/routing.py --all          # celá tabulka

POZOR: routing je VODÍTKO — platforma i metoda se při sběru VŽDY ověří živě (Fáze 0).
"""
import argparse, json, os, sys
import yaml

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí → v diagnostice → vynuť UTF-8 (no-op jinde)
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "routing.yaml"), encoding="utf-8") as f:
    _R = yaml.safe_load(f)

def route(platform):
    return _R["families"].get(platform, _R["default"])

def route_host(host):
    pm = json.load(open(os.path.join(ROOT, "platform_map.json"), encoding="utf-8"))["final"]
    plat = (pm.get(host) or {}).get("plat", "UNKNOWN")
    src = (_R.get("sources") or {}).get(host)        # host-specific dedikovaný parser má přednost
    if src:
        return plat, {**route(plat), **src}          # harvester/note z override, method/layer2 z rodiny
    return plat, route(plat)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host"); ap.add_argument("--platform"); ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.all:
        for plat, e in {**_R["families"], "(default)": _R["default"]}.items():
            print(f"  {plat:22} {','.join(e.get('harvester') or ['—']):46} {e.get('method','')[:50]}")
        for host, e in (_R.get("sources") or {}).items():       # host-override dedikované parsery
            print(f"  source:{host:30} {','.join(e.get('harvester') or ['—']):40} {e.get('note','')[:40]}")
    elif a.host:
        plat, e = route_host(a.host)
        print(json.dumps({"host": a.host, "platform": plat, **e}, ensure_ascii=False, indent=1))
    elif a.platform:
        print(json.dumps({"platform": a.platform, **route(a.platform)}, ensure_ascii=False, indent=1))
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
