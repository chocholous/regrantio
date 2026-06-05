#!/usr/bin/env python3
"""Generický ingest krajských HTML-listing harvestů → opportunities.jsonl.

KONTRAKT (co musí harvester per kraj vyprodukovat — JSON):
{
  "source": "zlinskykraj.cz",          # host
  "kraj": "Zlínský kraj",              # název kraje (region)
  "platform": "zlinsky_html",          # libovolný štítek platformy
  "programs": [
    {
      "nazev": "RP30-25 Rozvoj obcí ...",   # POVINNÉ
      "open_from": "2026-01-02"|null,        # ISO nebo null
      "deadline": "2026-06-30"|null,         # ISO nebo null
      "status": "open"|"closed"|null,        # JEN když web uvádí explicitně (Liberec); jinak null → dopočítá kód
      "alokace_czk": 70000000|null,          # int nebo null
      "max_czk": null,                       # vyše na žadatele, pokud uvedeno
      "popis": "...",                        # krátký popis (focus_area), může být null
      "eligible": "obce 2000-5000 obyvatel", # text oprávněnosti, může být null
      "kod": "RP30-25"|null,
      "url": "https://..."                   # odkaz na program
    }, ...
  ]
}

Ingest dopočítá status z dat (pokud není explicitní), oblast z názvu+popisu (univerzální keyword tabulka),
typ_zadatele z eligible, region=kraj. poskytovatel=samosprava_kraj, zdroj=krajsky.

Usage: python3 scripts/ingest_kraj.py data/h_kraj_zlinsky.json [data/h_kraj_*.json ...] --out data/opportunities.jsonl [--today 2026-06-05]
"""
import argparse, json, os, re, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opportunities import compute_status, canon_key, _pd

# POZN.: oblast / typ_zadatele / cilova_skupina ZÁMĚRNĚ neklasifikujeme keyword-heuristikou.
# Dle architektury (CLAUDE.md) je klasifikace fazet práce LLM vrstvy 2 (classify nad textem),
# kód jen počítá status z dat. Strukturní ingest plní jen to, co reálně vytěží (datumy/částka/
# region/eligible-text) + lossless text; fazety nechává prázdné → doplní LLM vrstva 2.


def _num(x):
    if x is None: return None
    if isinstance(x, (int, float)): return int(x)
    d = re.sub(r"[^\d]", "", str(x))
    return int(d) if d else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", default="data/opportunities.jsonl")
    ap.add_argument("--today", default="2026-06-05")
    a = ap.parse_args()
    today = _pd(a.today) or date.today()

    seen = set()
    if os.path.exists(a.out):
        for l in open(a.out, encoding="utf-8"):
            try: seen.add(json.loads(l).get("id"))
            except Exception: pass

    from collections import Counter
    grand = Counter()
    total_written = 0
    for inp in a.inputs:
        H = json.load(open(inp, encoding="utf-8"))
        source, kraj = H["source"], H["kraj"]
        platform = H.get("platform", "kraj_html")
        uroven = H.get("uroven", "kraj")           # "kraj" | "obec" (statutární/krajská města)
        obec = H.get("obec")                        # název města (jen pro uroven=obec)
        if uroven == "obec":
            poskyt, zdroj = "samosprava_obec", "obecni"
            region = {"nazev": obec or kraj, "obec": obec, "okres": None, "kraj": kraj,
                      "celostatni": False, "_conf": "high"}
        else:
            poskyt, zdroj = "samosprava_kraj", "krajsky"
            region = {"nazev": kraj, "obec": None, "okres": None, "kraj": kraj,
                      "celostatni": False, "_conf": "high"}
        recs = []
        for p in H["programs"]:
            nazev = (p.get("nazev") or "").strip()
            if not nazev:
                continue
            popis = p.get("popis") or ""
            of, dl = p.get("open_from"), p.get("deadline")
            if p.get("status") in ("open", "closed", "announced"):
                st, conf = p["status"], "high"          # web uvádí explicitně (Liberec)
            else:
                st, conf = compute_status(of, dl, today)
            eligible = p.get("eligible")
            gid = canon_key("grant", nazev, p.get("url") or source + "/" + (p.get("kod") or nazev[:30]))
            rec = {
                "kind": "grant", "source": source, "source_url": p.get("url"),
                "title": nazev, "focus_area": popis or None, "open_from": of, "deadline": dl,
                "status": st, "status_confidence": conf, "amount": _num(p.get("max_czk")),
                "eligible_applicants": eligible, "required_attachments": [],
                "how_to_apply": f"Žádost přes dotační portál {source}", "source_doc": p.get("url"), "id": gid,
                "facets": {
                    "oblast": [], "typ_zadatele": [],     # ← LLM vrstva 2 (ne keyword)
                    "sektor_zadatele": [], "typ_poskytovatele": poskyt,
                    "forma_podpory": ["dotace"], "zdroj_financovani": [zdroj],
                    "rezim_prijmu": None, "delka": None, "zpusob_podani": ["elektronicky_portal"],
                    "cilova_skupina": [], "mira_podpory_pct": None, "spoluucast": None,
                    "vyse_alokace_czk": _num(p.get("alokace_czk")), "vyse_max_zadatel_czk": _num(p.get("max_czk")),
                    "region": dict(region),
                },
                "provenance": {"layer": 1, "harvester": platform, "platform": platform,
                               "harvest_url": p.get("url"), "harvest_file": inp, "documents": []},
                "extra": {k: v for k in ("kod",) if (v := p.get(k))},
                "citations": [],
            }
            recs.append(rec)
        written, dup = 0, 0
        with open(a.out, "a", encoding="utf-8") as o:
            for r in recs:
                if r["id"] in seen:
                    dup += 1; continue
                seen.add(r["id"]); o.write(json.dumps(r, ensure_ascii=False) + "\n"); written += 1
        total_written += written
        st_c = Counter(r["status"] for r in recs)
        print(json.dumps({"MARKER": "INGEST_KRAJ", "source": source, "kraj": kraj,
                          "written": written, "dedup": dup, "by_status": dict(st_c)}, ensure_ascii=False))
        grand[source] = written
    print(json.dumps({"MARKER": "INGEST_KRAJ_TOTAL", "written": total_written, "by_source": dict(grand)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
