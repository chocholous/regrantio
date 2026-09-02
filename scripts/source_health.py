#!/usr/bin/env python3
"""ZDRAVÍ ZDROJŮ — který zdroj vyschl mezi dvěma publikacemi.

===============================================================================
⚠ NA OTÁZKU „KOLIK ZDROJŮ FUNGUJE" REPOZITÁŘ NEUMĚL ODPOVĚDĚT (2026-09-01).

`REMAINING.md` to má rozepsané: tři mechanické pokusy o spočítání funkčních
zdrojů daly 81 / 51 / 33 a `docs/PREHLED.md` v Grantiu tvrdilo 136. Čtyři čísla,
čtyři různé veličiny, žádná z nich nebyla ta hledaná.

Navrhovaná oprava zněla „přidat do `routing.yaml` pole `source:`". Když jsem se
na to podíval s daty v ruce, ukázalo se, že by to nestačilo, a proč:

    routing.yaml má        81 položek
    dataset má            136 hodnot `source`
    z toho routing pokrývá 74

⚠ **`routing.yaml` NENÍ INVENTÁŘ ZDROJŮ A NIKDY JÍM NEBYL.** Je to směrovník
„platforma → čím to harvestovat"; víc než šedesát skutečně sbíraných zdrojů
v něm nemá položku vůbec, protože jedou přes rodinu (`families:`) nebo přes
vlastní skript. Doplnit tam `source:` by tedy vyrobilo inventář, který o dvou
třetinách sběru mlčí — a to je horší než žádný, protože se podle něj rozhoduje.

⚠ INVENTÁŘ UŽ EXISTUJE A JE JÍM DATASET. Každý záznam nese `source`, takže
seznam zdrojů, které opravdu něco přinesly, je z dat čitelný přesně. Chybí
jediné: POROVNÁNÍ S MINULE PUBLIKOVANÝM STAVEM. Vyschlý zdroj se totiž nepozná
z jednoho běhu — všechny zbylé záznamy jsou v pořádku a celkový počet klesne
o jednotky procent.

===============================================================================
JAK TO FUNGUJE

Porovnává `data/opportunities.jsonl` (nový katalog) proti `docs/opportunities.json`
(minule publikovaný export) po jednotlivých zdrojích. Je to týž pár souborů
a týž okamžik, jaký používá brána na propad počtu v `validate_release.py` —
běží PŘED `export_api.py`, takže export je ještě ta stará verze.

    vyschlý     zdroj měl aspoň MIN_TRACKED záznamů a teď má nula
    propadlý    zdroj ztratil víc než COLLAPSE_RATIO svých záznamů
    nový        zdroj v minulém exportu nebyl (jen se vypíše, nebrání ničemu)

⚠ RŮST SE NEHLÍDÁ, stejně jako u brány na celkový počet: nový zdroj přinese
skokem stovky záznamů a je to přesně to, co má pipeline dělat.

⚠ MALÉ ZDROJE SE NEHLÍDAJÍ NA PROPAD. Zdroj se dvěma záznamy spadne na jeden
kdykoli poskytovatel zavře jednu výzvu — a to není porucha sběru, to je normální
život. Hlídá se u nich jen nula, a i to až od MIN_TRACKED záznamů.

Spuštění samostatně:  python scripts/source_health.py
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "data", "opportunities.jsonl")
EXPORT = os.path.join(ROOT, "docs", "opportunities.json")

# Od kolika záznamů se zdroj vůbec sleduje. Pod tím je zmizení nerozeznatelné
# od běžného uzavření poslední výzvy.
MIN_TRACKED = 3

# O kolik smí zdroj přijít, než je to porucha. 0,5 = polovina.
COLLAPSE_RATIO = 0.5

# Od kolika záznamů má smysl hlídat i částečný propad.
MIN_FOR_RATIO = 10


def counts_from_catalog(path=CATALOG):
    """Počty záznamů po zdrojích v živém katalogu (JSONL)."""
    out = collections.Counter()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out[json.loads(line).get("source")] += 1
    return out


def counts_from_export(path=EXPORT):
    """Počty záznamů po zdrojích v minule publikovaném exportu."""
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    return collections.Counter(g.get("source") for g in (payload.get("grants") or []))


def compare(now, before, min_tracked=MIN_TRACKED, collapse_ratio=COLLAPSE_RATIO,
            min_for_ratio=MIN_FOR_RATIO):
    """Rozdíl dvou snímků. Vrací (vyschlé, propadlé, nové).

    `vyschlé`  … [(zdroj, kolik měl)]        — teď nula
    `propadlé` … [(zdroj, kolik má, měl)]    — ztráta nad prahem
    `nové`     … [(zdroj, kolik má)]
    """
    dried, collapsed, fresh = [], [], []
    for src, had in before.items():
        has = now.get(src, 0)
        if had >= min_tracked and has == 0:
            dried.append((src, had))
        elif had >= min_for_ratio and has < had * (1 - collapse_ratio):
            collapsed.append((src, has, had))
    for src, has in now.items():
        if src not in before:
            fresh.append((src, has))
    dried.sort(key=lambda t: -t[1])
    collapsed.sort(key=lambda t: t[1] - t[2])
    fresh.sort(key=lambda t: -t[1])
    return dried, collapsed, fresh


def main():
    if not os.path.exists(CATALOG):
        print("data/opportunities.jsonl není v pracovní kopii")
        return 0
    if not os.path.exists(EXPORT):
        print("docs/opportunities.json není v pracovní kopii — není s čím porovnávat")
        return 0

    now, before = counts_from_catalog(), counts_from_export()
    dried, collapsed, fresh = compare(now, before)

    print(f"zdrojů v katalogu: {len(now)}   (minule {len(before)})")
    print(f"záznamů:           {sum(now.values())}   (minule {sum(before.values())})")

    if fresh:
        print("\nNOVÉ ZDROJE")
        for src, has in fresh:
            print(f"  +{has:5d}  {src}")
    if collapsed:
        print("\nPROPAD")
        for src, has, had in collapsed:
            print(f"  {has:5d}  {src}   (minule {had})")
    if dried:
        print("\nVYSCHLO")
        for src, had in dried:
            print(f"  {0:5d}  {src}   (minule {had})")

    if dried or collapsed:
        print(f"\nFAIL — {len(dried)} vyschlých, {len(collapsed)} propadlých")
        return 1
    print("\nOK — žádný zdroj nevyschl ani nepropadl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
