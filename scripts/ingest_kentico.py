#!/usr/bin/env python3
"""Ingest Kentico (IROP/dotaceEU/ministerstva) → opportunities.jsonl.

Kentico harvester (kentico_irop.py) dává STRUKTUROVANÁ pole (title, open_from, deadline, eligible,
status). Sem se mapují do opportunity schématu. Akční pole (deadline/status/eligible) jsou strukturní;
tematické facety (oblast/typ_zadatele) odvozeny DETERMINISTICKY z title/eligible (bez LLM) — hrubé, ale
dává faseta smysl; jemnější LLM enrichment může přijít později. allocation/support_rate harvester
mis-parsuje → NEpoužívají se.

UPSERT (2026-07-31): zápis do katalogu přes sdílený scripts/upsert.py — re-harvest
aktualizuje existující výzvy (dřív append-only skip → refresh se nepropsal).

Usage: python3 scripts/ingest_kentico.py data/h_kentico_irop.jsonl --source irop.gov.cz [--out data/opportunities.jsonl] [--today 2026-07-31]
"""
import argparse, json, os, re, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opportunities import compute_status, canon_key, _host, _pd
from upsert import upsert

# oblast / typ_zadatele NEklasifikujeme keyword-heuristikou → LLM vrstva 2 (viz ingest_kraj.py).


def cz_iso(s):
    m = re.match(r"\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s or "")
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("--source", required=True, help="host (irop.gov.cz)")
    ap.add_argument("--platform", default="kentico")
    ap.add_argument("--poskytovatel", default="ministerstvo")
    ap.add_argument("--zdroj", default="eu_fondy")
    ap.add_argument("--out", default="data/opportunities.jsonl")
    ap.add_argument("--today", default=date.today().isoformat())
    a = ap.parse_args()
    today = _pd(a.today) or date.today()

    recs = []
    for line in open(a.inp, encoding="utf-8"):
        r = json.loads(line)
        url = r.get("url"); title = r.get("title")
        if not title:
            continue
        of, dl = cz_iso(r.get("open_from")), cz_iso(r.get("deadline"))
        st, conf = compute_status(of, dl, today)
        if st == "unknown" and r.get("status") in ("open", "closed", "announced"):
            st, conf = r["status"], "high"
        gid = canon_key("grant", title, url)
        rec = {
            "kind": "grant", "source": a.source, "source_url": url,
            "title": title, "focus_area": None, "open_from": of, "deadline": dl,
            "status": st, "status_confidence": conf, "amount": None,
            "eligible_applicants": r.get("eligible"), "required_attachments": [],
            "how_to_apply": None, "source_doc": url, "id": gid,
            "facets": {
                "oblast": [], "typ_zadatele": [], "sektor_zadatele": [],     # ← LLM vrstva 2
                "typ_poskytovatele": a.poskytovatel, "forma_podpory": ["dotace"],
                "zdroj_financovani": [a.zdroj], "rezim_prijmu": None, "delka": None,
                "zpusob_podani": [], "cilova_skupina": [], "mira_podpory_pct": None,
                "spoluucast": None, "vyse_alokace_czk": None, "vyse_max_zadatel_czk": None,
                "region": {"nazev": None, "obec": None, "okres": None, "kraj": None,
                           "celostatni": True, "_conf": "high"},
            },
            "provenance": {"layer": 1, "harvester": "kentico_irop.py", "platform": a.platform,
                           "harvest_url": url, "harvest_file": a.inp,
                           "documents": [{"url": x.get("url"), "txt_path": None}
                                         for x in (r.get("attachments") or []) if isinstance(x, dict)]},
            "extra": {k: v for k, v in r.items()
                      if k not in ("url", "title", "open_from", "deadline", "eligible", "status",
                                   "status_conf", "attachments", "allocation", "support_rate")
                      and v not in (None, "", [], {})},
            "citations": [],
        }
        recs.append(rec)

    st = upsert(a.out, recs)
    from collections import Counter
    print(json.dumps({"MARKER": "INGEST_KENTICO", "source": a.source, **st,
                      "by_status": dict(Counter(r["status"] for r in recs))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
