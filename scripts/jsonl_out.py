#!/usr/bin/env python3
"""Zápis sklizně na disk — s jedinou pojistkou, kterou harvestery potřebují.

⚠ PRÁZDNÁ SKLIZEŇ NESMÍ PŘEPSAT PŘEDCHOZÍ (2026‑09‑23).

Každý harvester zapisoval výsledek přes `open(out, "w")`. Ten soubor nejdřív
usekne na nulu a teprve pak do něj píše — takže když sklizeň nic nepřinesla
(spadlá síť, změněný web, HTTP 403 za příliš rychlé procházení), zbyl na disku
prázdný soubor a vstup pro extrakci zmizel. Navenek to přitom vypadá jako
úspěch: krok skončí nulou, souhrn ohlásí `pages: 0` a běh pokračuje dál.

Přesně tohle se stalo 23. 9. u `msmt`: web mě po rychlé sklizni odmítl s 403,
harvest zapsal nulu a hotových 103 dokumentů bylo pryč. Katalog to nepoškodí
(ingest je upsert, záznamy zůstanou z minula), ale ten zdroj z běhu vypadne
a nikomu to nedojde.

Pravidlo: **nic jsem nesklidil = na disku zůstává to z minula a krok skončí
chybou.** Chyba je tu ta správná odpověď — běh pokračuje k dalším zdrojům
(`refresh_run.py` sbírá selhání do souhrnu) a v logu je vidět, který zdroj se
neobnovil a proč.

Použití v harvesteru:

    from jsonl_out import write_jsonl

    n = write_jsonl(args.out, recs, marker="MSMT_HARVEST")
    if n == 0:
        return 1            # prázdná sklizeň → krok selhal, soubor se nedotkl
"""
import json
import os
import sys


def write_jsonl(path, records, marker=None, append=False, allow_empty=False):
    """Zapíše záznamy jako JSONL. → počet zapsaných (0 = nezapsáno, soubor beze změny).

    `append=True` (režim `--resume`) pojistku vypíná: navazující běh smí přidat
    nula řádků, protože předchozí obsah zůstává tak jako tak.
    `allow_empty=True` je pro zdroje, u kterých je prázdno legitimní výsledek
    (rozcestník bez výzev) — zdůvodni to u volání, ať to není tichá výjimka.
    """
    records = list(records)
    if not records and not append and not allow_empty:
        note = {"MARKER": marker or "HARVEST", "records": 0, "out": path,
                "note": "nic se nesklidilo — předchozí soubor zůstává beze změny"}
        print(json.dumps(note, ensure_ascii=False), file=sys.stderr)
        return 0

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a" if append else "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(records)


def write_json(path, payload, marker=None, allow_empty=False):
    """Totéž pro jeden JSON dokument (harvestery, které zapisují pole nebo objekt)."""
    empty = payload is None or (isinstance(payload, (list, dict, str)) and len(payload) == 0)
    if empty and not allow_empty:
        note = {"MARKER": marker or "HARVEST", "records": 0, "out": path,
                "note": "nic se nesklidilo — předchozí soubor zůstává beze změny"}
        print(json.dumps(note, ensure_ascii=False), file=sys.stderr)
        return 0

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return len(payload) if hasattr(payload, "__len__") else 1
