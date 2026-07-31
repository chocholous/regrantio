#!/usr/bin/env python3
"""Ingest DOTIS harvest (dotis_harvest.py) → opportunities.jsonl.

Strom programů→podprogramů (dotačních titulů) s dateBeg/dateEnd → 1 titul = 1 oportunita.
oblast odvozena z PROGRAMU (memo→oblast, deterministicky); status DOPOČÍTÁ kód z dat (ne `state`).
region = kraj (--kraj). typ_zadatele/eligible/částka nejsou v API listingu (partial opportunity).

Lossless: harvest drží VŠECHNY tituly (i 2011). Do opportunities jdou jen relevantní (dateEnd >= --since,
default 2025-01-01) — to NENÍ harvest-cap, ale opportunity-relevance (starý uzavřený titul ≠ oportunita);
počet zahozených se NAHLAS loguje (lossless raw je zachován v h_dotis_*.json).

UPSERT (2026-07-31): zápis jde do katalogu přes sdílený scripts/upsert.py — re-harvest
aktualizuje existující tituly (dřív append-only skip → refresh se nepropsal).

Usage: python3 scripts/ingest_dotis.py data/h_dotis_khk.json --kraj "Královéhradecký kraj" [--out data/opportunities.jsonl] [--since 2025-01-01] [--today 2026-07-31]
"""
import argparse, json, os, re, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opportunities import compute_status, canon_key, _pd
from upsert import upsert

# oblast NEklasifikujeme keyword/memo-heuristikou → LLM vrstva 2 (viz ingest_kraj.py).
# Kód programu (memo) i program_name se ukládají do extra/focus_area, ať z nich LLM může čerpat.


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("--kraj", required=True, help="název kraje pro region (Královéhradecký kraj)")
    ap.add_argument("--out", default="data/opportunities.jsonl")
    ap.add_argument("--since", default="2025-01-01", help="ingest jen tituly s dateEnd >= datum (opportunity-relevance)")
    ap.add_argument("--today", default=date.today().isoformat())
    a = ap.parse_args()
    today = _pd(a.today) or date.today()
    H = json.load(open(a.inp, encoding="utf-8"))
    source = H["source"]

    recs, old_skip = [], 0
    for prog in H["programs"]:
        prog_name = prog.get("name") or ""
        for s in prog.get("subprojects") or []:
            memo = s.get("memo") or ""
            name = s.get("name") or prog_name
            of = (s.get("dateBeg") or "")[:10] or None
            dl = (s.get("dateEnd") or "")[:10] or None
            if dl and dl < a.since:
                old_skip += 1
                continue
            st, conf = compute_status(of, dl, today)
            title = f"{name} ({memo})" if memo else name
            gid = canon_key("grant", title, source + "/" + memo)
            rec = {
                "kind": "grant", "source": source, "source_url": f"https://{source}/",
                "title": title, "focus_area": prog_name, "open_from": of, "deadline": dl,
                "status": st, "status_confidence": conf, "amount": None,
                "eligible_applicants": None, "required_attachments": [],
                "how_to_apply": f"Žádost přes dotační portál {source}", "source_doc": f"https://{source}/", "id": gid,
                "facets": {
                    "oblast": [], "typ_zadatele": [], "sektor_zadatele": [],     # ← LLM vrstva 2
                    "typ_poskytovatele": "samosprava_kraj", "forma_podpory": ["dotace"],
                    "zdroj_financovani": ["krajsky"], "rezim_prijmu": None, "delka": None,
                    "zpusob_podani": ["elektronicky_portal"], "cilova_skupina": [], "mira_podpory_pct": None,
                    "spoluucast": None, "vyse_alokace_czk": None, "vyse_max_zadatel_czk": None,
                    "region": {"nazev": a.kraj, "obec": None, "okres": None, "kraj": a.kraj,
                               "celostatni": False, "_conf": "high"},
                },
                "provenance": {"layer": 1, "harvester": "dotis_harvest.py", "platform": "dotis",
                               "harvest_url": f"https://{source}/", "harvest_file": a.inp,
                               "api_base": H.get("api_base"), "documents": []},
                "extra": {"memo": memo, "program": prog_name, "id_Def_Subproject": s.get("id_Def_Subproject"),
                          "state": s.get("state")},
                "citations": [],
            }
            recs.append(rec)

    st = upsert(a.out, recs)
    from collections import Counter
    print(json.dumps({"MARKER": "INGEST_DOTIS", "source": source, **st,
                      "skipped_old_lossless_kept": old_skip,
                      "by_status": dict(Counter(r["status"] for r in recs))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
