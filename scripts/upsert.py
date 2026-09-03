#!/usr/bin/env python3
"""Sdílený UPSERT do data/opportunities.jsonl pro strukturní layer-1 ingesty.

Historicky ingest_kraj/ingest_dotis/ingest_kentico/ingest_fondvysociny APPENDOVALY do v1
`opportunities.jsonl` a duplicitní id přeskočily → re-harvest téhož programu se změněným
deadlinem se do datasetu NIKDY nepropsal (html-tier ~1300 záznamů fakticky nešel refreshovat).
Tenhle modul je JEDNO místo s korektní sémantikou refreshe:

  • UPSERT dle `id`: nový záznam se přidá, existující AKTUALIZUJE, pořadí souboru se drží.
  • Ochrana obohacení: záznam, který už prošel vrstvou 2 (provenance.layer==2 / má citations),
    se NEpřepisuje celý — přepíšou se jen FAKTA z listingu (datumy/status/částky/source_url);
    LLM facety, focus_area a citace zůstávají. Syrový layer-1 záznam se přepíše celý.
  • Nic se nemaže: záznam, který v novém harvestu chybí, zůstává (poslední známý stav;
    odebrání řeší vědomě fix_dataset/export — viz docs/REFRESH.md §5).

Použití (v ingest skriptu):
    from upsert import upsert
    stats = upsert(out_path, recs)      # → {"new": n, "updated": n, "unchanged": n, "total": n}
"""
import datetime
import json
import os

# Fakta z listingu, která smí refresh přepsat i u záznamu obohaceného vrstvou 2.
REFRESHABLE = ("open_from", "deadline", "status", "status_confidence", "amount", "source_url")
REFRESHABLE_FACETS = ("vyse_alokace_czk", "vyse_max_zadatel_czk")


def _today():
    return datetime.date.today().isoformat()


def stamp(rec, when=None):
    """Zapiš do záznamu DEN, KDY JSME HO NAPOSLED VIDĚLI U ZDROJE.

    ⚠ NENÍ to „datum změny". Záznam, který se po refreshi nezměnil, dostane
    dnešní razítko taky — a je to ten důležitější případ: znamená „ověřeno,
    že u zdroje pořád je". Bez toho se „výzva je stará" nedá odlišit od
    „výzvu jsme dlouho nekontrolovali", což jsou dvě různé věci a produkt
    na ně reaguje opačně.
    """
    prov = dict(rec.get("provenance") or {})
    prov["fetched_at"] = when or _today()
    rec["provenance"] = prov
    return rec


def _without_stamp(rec):
    """Kopie záznamu bez razítka — pro POROVNÁNÍ obsahu.

    ⚠ BEZ TOHOTO by razítko zničilo signál, kvůli kterému refresh existuje:
    kdyby se `fetched_at` porovnávalo taky, lišil by se po něm KAŽDÝ záznam
    a statistika by hlásila „updated" u všech 3450. Číslo, které je vždycky
    stejné, se přestane číst.
    """
    if "provenance" not in rec:
        return rec
    out = dict(rec)
    prov = dict(out.get("provenance") or {})
    prov.pop("fetched_at", None)
    out["provenance"] = prov
    return out


def _enriched(rec):
    """Prošel záznam vrstvou 2? (pak ho refresh přepisuje jen částečně)"""
    return (rec.get("provenance") or {}).get("layer") == 2 or bool(rec.get("citations"))


def merge(old, new):
    """Refresh existujícího záznamu: u syrového layer-1 přepiš celý, u obohaceného jen fakta."""
    if not _enriched(old):
        return new
    out = dict(old)
    for k in REFRESHABLE:
        if new.get(k) is not None:
            out[k] = new[k]
    of, nf = dict(out.get("facets") or {}), new.get("facets") or {}
    for k in REFRESHABLE_FACETS:
        if nf.get(k) is not None:
            of[k] = nf[k]
    out["facets"] = of
    return out


def load(out_path):
    """→ (order[list of id], byid{id: rec}); tolerantní k vadným řádkům."""
    order, byid = [], {}
    if os.path.exists(out_path):
        for line in open(out_path, encoding="utf-8"):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            rid = r.get("id")
            if rid in byid:              # tvrdá duplicita v souboru → poslední vyhrává
                byid[rid] = r
                continue
            order.append(rid)
            byid[rid] = r
    return order, byid


def write(out_path, order, byid):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as o:
        for rid in order:
            o.write(json.dumps(byid[rid], ensure_ascii=False) + "\n")


def upsert(out_path, recs, when=None):
    """Upsertni `recs` do jsonl `out_path` (viz modul docstring). Vrací statistiky.

    Každý záznam, který tudy projde, dostane `provenance.fetched_at` — i ten
    beze změny. Porovnává se ale obsah BEZ razítka, takže `updated` dál znamená
    „u zdroje se něco změnilo", ne „proběhl refresh".
    """
    when = when or _today()
    order, byid = load(out_path)
    new = upd = keep = 0
    for r in recs:
        rid = r.get("id")
        if not rid:
            continue
        if rid in byid:
            merged = merge(byid[rid], r)
            if _without_stamp(merged) == _without_stamp(byid[rid]):
                keep += 1
            else:
                upd += 1
            byid[rid] = stamp(merged, when)
        else:
            order.append(rid)
            byid[rid] = stamp(r, when)
            new += 1
    write(out_path, order, byid)
    return {"new": new, "updated": upd, "unchanged": keep, "total": len(order),
            "fetched_at": when}
