#!/usr/bin/env python3
"""Doplní region tam, kde chybí (bylo „?" ve filtru kraj). Idempotentní.

Pravidla pro záznamy s prázdným regionem (bez kraj/celostatni/obec):
1. známý městský dsw2/portál host → obec + kraj (CITY mapa),
2. ministerstvo / státní fond / nadace (dle typ_poskytovatele nebo hosta) → celostátní,
3. fallback: neklasifikovatelný grant/program → celostátní (_conf=low).

Usage: python3 scripts/fix_region.py [--in data/opportunities.jsonl]
"""
import argparse, json

CITY = {
    "dotace.usti.cz": ("Ústí nad Labem", "Ústecký kraj"),
    "dotace.usti-nad-labem.cz": ("Ústí nad Labem", "Ústecký kraj"),
    "dotace.nmnm.cz": ("Nové Město na Moravě", "Kraj Vysočina"),
    "dotace.praha11.cz": ("Praha 11", "Hlavní město Praha"),
}
NAT_POSK = {"ministerstvo", "statni_fond", "nadace", "firemni_nadace", "nadacni_fond"}
NAT_HOST = ("mzcr", "mkcr", "mmr", "msmt", "mze", "nadac", "fond", "dotaceeu", "kontobariery", "voracek")


def empty(reg):
    return not (reg.get("kraj") or reg.get("celostatni") or reg.get("obec"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/opportunities.jsonl")
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.inp, encoding="utf-8")]
    obec = nat = fb = 0
    for r in rows:
        reg = r.setdefault("facets", {}).setdefault("region", {})
        if not empty(reg):
            continue
        host = r.get("source") or ""
        posk = r.get("facets", {}).get("typ_poskytovatele")
        if host in CITY:
            o, k = CITY[host]
            reg.update({"nazev": o, "obec": o, "kraj": k, "celostatni": False, "_conf": "high"}); obec += 1
        elif posk in NAT_POSK or host.endswith(".gov.cz") or any(x in host for x in NAT_HOST):
            reg.update({"celostatni": True, "_conf": "high"}); nat += 1
        else:
            reg.update({"celostatni": True, "_conf": "low"}); fb += 1
    with open(a.inp, "w", encoding="utf-8") as o:
        for r in rows:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"MARKER": "FIX_REGION", "obec_kraj": obec, "celostatni": nat, "fallback": fb}, ensure_ascii=False))


if __name__ == "__main__":
    main()
