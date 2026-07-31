#!/usr/bin/env python3
"""Ingest Fond Vysočiny harvest → opportunities.jsonl.

Strukturovaná pole (popis/alokace/termín/typ žadatele) → opportunity. oblast z názvu+popisu,
typ_zadatele z textu oprávněnosti, status z termínů (kód). alokace → vyse_alokace_czk.

UPSERT (2026-07-31): zápis do katalogu přes sdílený scripts/upsert.py — re-harvest
aktualizuje existující programy (dřív append-only skip → refresh se nepropsal).

Usage: python3 scripts/ingest_fondvysociny.py data/h_fondvysociny.json [--out data/opportunities.jsonl] [--today 2026-07-31]
"""
import argparse, json, os, re, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opportunities import compute_status, canon_key, _pd
from upsert import upsert

# oblast / typ_zadatele NEklasifikujeme keyword-heuristikou → LLM vrstva 2 (viz ingest_kraj.py).


def _num(s):
    if not s: return None
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("--out", default="data/opportunities.jsonl")
    ap.add_argument("--today", default=date.today().isoformat())
    a = ap.parse_args()
    today = _pd(a.today) or date.today()
    H = json.load(open(a.inp, encoding="utf-8"))
    source, kraj = H["source"], H["kraj"]

    recs = []
    for p in H["programs"]:
        nazev, popis = p.get("nazev") or p["id"], p.get("popis") or ""
        of, dl = p.get("open_from"), p.get("deadline")
        st, conf = compute_status(of, dl, today)
        eligible = p.get("typ_zadatele")
        gid = canon_key("grant", nazev, p.get("url") or source + "/" + p["id"])
        rec = {
            "kind": "grant", "source": source, "source_url": p.get("url"),
            "title": nazev, "focus_area": popis or None, "open_from": of, "deadline": dl,
            "status": st, "status_confidence": conf, "amount": None,
            "eligible_applicants": eligible, "required_attachments": [],
            "how_to_apply": f"Žádost přes portál {source}", "source_doc": p.get("url"), "id": gid,
            "facets": {
                "oblast": [], "typ_zadatele": [],     # ← LLM vrstva 2 (ne keyword)
                "sektor_zadatele": [], "typ_poskytovatele": "samosprava_kraj",
                "forma_podpory": ["dotace"], "zdroj_financovani": ["krajsky"],
                "rezim_prijmu": None, "delka": None, "zpusob_podani": ["elektronicky_portal"],
                "cilova_skupina": [], "mira_podpory_pct": None, "spoluucast": None,
                "vyse_alokace_czk": _num(p.get("alokace")), "vyse_max_zadatel_czk": None,
                "region": {"nazev": kraj, "obec": None, "okres": None, "kraj": kraj,
                           "celostatni": False, "_conf": "high"},
            },
            "provenance": {"layer": 1, "harvester": "fondvysociny_harvest.py", "platform": "fondvysociny",
                           "harvest_url": p.get("url"), "harvest_file": a.inp, "documents": []},
            "extra": {"id_programu": p["id"], "alokace_text": p.get("alokace")},
            "citations": [],
        }
        recs.append(rec)

    st = upsert(a.out, recs)
    from collections import Counter
    print(json.dumps({"MARKER": "INGEST_FONDVYSOCINY", **st,
                      "by_status": dict(Counter(r["status"] for r in recs))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
