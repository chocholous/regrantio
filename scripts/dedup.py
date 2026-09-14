#!/usr/bin/env python3
"""dedup.py — RODINY ROČNÍKŮ: který záznam je hlavní a které jsou starší kola téhož programu.

Naměřeno 2026‑09‑14: 313 rodin, 914 záznamů. Typický tvar je „INFRASTRUKTURA
CESTOVNÍHO RUCHU 2020 … 2025" (Fond Vysočiny, šest záznamů) nebo „Sport pro
Medlánky 2024 / 2025 / 2026". Pro žadatele je to JEDEN program, který se
vyhlašuje každý rok — a seznam, ve kterém stojí šestkrát pod sebou, je
seznam, který se nedá číst.

Co se dělá a co ne:

  • KANONICKÝ záznam rodiny = ten, o který si dnes lze říct: nejdřív podle
    stavu (open > announced > unknown > closed), pak podle nejpozdější lhůty.
  • `variant_of` dostanou JEN uzavřené ročníky (lhůta v minulosti). Dva ŽIVÉ
    záznamy téže rodiny se nikdy neslučují: „63. výzva" a „64. výzva" OPŽP mají
    stejné jméno, lhůtu i alokaci a jsou to dvě různé výzvy (pro dva typy
    regionů). Sloučit je by uživateli jednu schovalo, a to je horší než
    duplicita.
  • Rodina se ZAPÍŠE na kanonický záznam (`family`): kolik ročníků zdroj
    listuje, které roky a jestli mají společný den uzávěrky. To je doklad
    o opakování, který jinak nikde není — „vyhlašováno 2019 až 2025, uzávěrka
    obvykle 31. 10." řekne žadateli víc než „lhůta neuvedena".

⚠ Nic se nemaže a `id` se nemění. Je to anotace, ne slučování; produkt sám
rozhodne, že starší ročníky v seznamu schová a na detailu je ukáže.
"""
import collections
import datetime
import re

import enrich

_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_STATUS_RANK = {"open": 0, "announced": 1, "unknown": 2, "closed": 3}


def _status(rec, today):
    d = rec.get("deadline")
    o = rec.get("open_from")
    if isinstance(d, str) and d.strip().lower() in enrich.ROLLING_WORDS:
        return "open"
    if not (isinstance(d, str) and _ISO.match(d)):
        return "unknown"
    if today > d:
        return "closed"
    if isinstance(o, str) and _ISO.match(o) and today < o:
        return "announced"
    return "open"


def _year(rec):
    """Rok ročníku: z lhůty, jinak z titulku (poslední čtyřčíslí 20xx)."""
    d = rec.get("deadline")
    if isinstance(d, str) and _ISO.match(d):
        return int(d[:4])
    m = re.findall(r"\b(20\d{2})\b", rec.get("title") or "")
    return int(m[-1]) if m else None


def _sort_key(rec, today):
    d = rec.get("deadline") if isinstance(rec.get("deadline"), str) and _ISO.match(rec.get("deadline") or "") else ""
    return (_STATUS_RANK[_status(rec, today)], "" if d else "~", d and "".join(chr(255 - ord(c)) for c in d), rec.get("id") or "")


def assign_families(records, today=None):
    """Vrátí `{id: {"variant_of": id|None, "family": {...}|None}}` pro každý grant."""
    today = today or datetime.date.today().isoformat()
    groups = collections.defaultdict(list)
    for r in records:
        if r.get("kind") != "grant":
            continue
        key = enrich.program_key(r)
        if key:
            groups[key].append(r)

    out = {}
    for key, members in groups.items():
        if len(members) < 2:
            continue
        # Nejlepší kandidát první; lhůta se řadí sestupně přes „inverzní" řetězec,
        # aby se nemíchal formát dat s pořadím stavů.
        members = sorted(members, key=lambda r: _sort_key(r, today))
        canonical = members[0]
        years = sorted({y for y in (_year(m) for m in members) if y})
        # Společný den uzávěrky: všechny ročníky s ISO lhůtou mají týž DD-MM.
        days = {m["deadline"][5:] for m in members if isinstance(m.get("deadline"), str) and _ISO.match(m["deadline"])}
        typical = None
        if len(days) == 1 and sum(1 for m in members if isinstance(m.get("deadline"), str) and _ISO.match(m["deadline"])) >= 2:
            mm, dd = next(iter(days)).split("-")
            typical = f"{int(dd)}. {int(mm)}."
        variants = []
        for m in members[1:]:
            if _status(m, today) == "closed":
                variants.append(m)
                out[m["id"]] = {"variant_of": canonical["id"], "family": None}
            else:
                # Živý souběžný záznam (paralelní výzva): zůstává sám sebou.
                out[m["id"]] = {"variant_of": None, "family": None}
        out[canonical["id"]] = {
            "variant_of": None,
            "family": {
                "key": key,
                "rounds": len(members),
                "years": years,
                "typical_deadline": typical,
                "earlier": [{"id": v["id"], "year": _year(v), "deadline": v.get("deadline")} for v in variants][:12],
            },
        }
    return out


def report(records, today=None):
    fam = assign_families(records, today)
    variants = sum(1 for v in fam.values() if v["variant_of"])
    families = sum(1 for v in fam.values() if v["family"])
    return {"families": families, "variants": variants,
            "recurring_families": sum(1 for v in fam.values() if v["family"] and len(v["family"]["years"]) >= 2)}


if __name__ == "__main__":
    import json
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    recs = [json.loads(l) for l in open("data/opportunities.jsonl", encoding="utf-8") if l.strip()]
    print(json.dumps(report(recs), ensure_ascii=False))
