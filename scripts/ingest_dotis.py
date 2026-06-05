#!/usr/bin/env python3
"""Ingest DOTIS harvest (dotis_harvest.py) → opportunities.jsonl.

Strom programů→podprogramů (dotačních titulů) s dateBeg/dateEnd → 1 titul = 1 oportunita.
oblast odvozena z PROGRAMU (memo→oblast, deterministicky); status DOPOČÍTÁ kód z dat (ne `state`).
region = kraj (--kraj). typ_zadatele/eligible/částka nejsou v API listingu (partial opportunity).

Lossless: harvest drží VŠECHNY tituly (i 2011). Do opportunities jdou jen relevantní (dateEnd >= --since,
default 2025-01-01) — to NENÍ harvest-cap, ale opportunity-relevance (starý uzavřený titul ≠ oportunita);
počet zahozených se NAHLAS loguje (lossless raw je zachován v h_dotis_*.json).

Usage: python3 scripts/ingest_dotis.py data/h_dotis_khk.json --kraj "Královéhradecký kraj" --out data/opportunities.jsonl [--since 2025-01-01] [--today 2026-06-05]
"""
import argparse, json, os, re, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opportunities import compute_status, canon_key, _pd

# program memo (prefix titulu) → oblast (cílový slovník z consolidation_maps)
MEMO_OBLAST = {
    "CRG": ["cestovni_ruch"], "DAR": ["ostatni"], "DSO": ["socialni_sluzby"],
    "INV": ["veda_vyzkum", "podnikani"], "KPG": ["kultura_umeni", "pamatkova_pece"],
    "MUP": ["ostatni"], "NDZ": ["ostatni"], "NUP": ["ostatni"], "OPK": ["zivotni_prostredi"],
    "POV": ["bydleni_infrastruktura", "komunitni_rozvoj"], "RGI": ["ostatni"],
    "RRD": ["bydleni_infrastruktura"], "SMP": ["socialni_sluzby"], "SMR": ["sport_volny_cas"],
    "SMV": ["vzdelavani_mladez"], "SPT": ["sport_volny_cas"], "SVD": ["socialni_sluzby"],
    "ZPD": ["zivotni_prostredi"],
}
# jemné doladění širokých programů (RRD/MUP/RGI) podle slov v názvu titulu
NAME_OBLAST = [
    (r"hasič|JPO|požárn|SDH|protipožár|akceschop", "bezpecnost"),
    (r"cykl|cyklost|cyklotr", "cestovni_ruch"),
    (r"sociáln|rodin|ohrožen", "socialni_sluzby"),
    (r"podnikán|prodejen|ekonomik|farmář", "podnikani"),
    (r"voda|krajin|zeleň|EVVO|ekolog|včela|myslivost|zemědělsk", "zivotni_prostredi"),
    (r"kultur|památk|varhan|muze", "kultura_umeni"),
    (r"sport|tělovýchov", "sport_volny_cas"),
    (r"vzdělá|škol|nadán", "vzdelavani_mladez"),
    (r"územní plán|infrastruktur|veřejn.*prostran|mobilit", "bydleni_infrastruktura"),
]


def memo_prefix(memo):
    """'26RRD12' → 'RRD' (vynech 2 číslice roku, vezmi písmena)."""
    m = re.match(r"\d{2}([A-Z]+)", memo or "")
    return (m.group(1)[:3] if m else (memo or "")[:3]).upper()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("--kraj", required=True, help="název kraje pro region (Královéhradecký kraj)")
    ap.add_argument("--out", default="data/opportunities.jsonl")
    ap.add_argument("--since", default="2025-01-01", help="ingest jen tituly s dateEnd >= datum (opportunity-relevance)")
    ap.add_argument("--today", default="2026-06-05")
    a = ap.parse_args()
    today = _pd(a.today) or date.today()
    H = json.load(open(a.inp, encoding="utf-8"))
    source = H["source"]

    seen = set()
    if os.path.exists(a.out):
        for l in open(a.out, encoding="utf-8"):
            try: seen.add(json.loads(l).get("id"))
            except Exception: pass

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
            pref = memo_prefix(memo)
            oblast = list(MEMO_OBLAST.get(pref, ["ostatni"]))
            if pref in ("RRD", "MUP", "RGI", "DAR"):       # široké programy → doladit dle názvu
                for pat, ob in NAME_OBLAST:
                    if re.search(pat, name, re.I):
                        oblast = [ob]; break
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
                    "oblast": oblast, "typ_zadatele": [], "sektor_zadatele": [],
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

    written, dup = 0, 0
    with open(a.out, "a", encoding="utf-8") as o:
        for r in recs:
            if r["id"] in seen:
                dup += 1; continue
            seen.add(r["id"]); o.write(json.dumps(r, ensure_ascii=False) + "\n"); written += 1
    from collections import Counter
    print(json.dumps({"MARKER": "INGEST_DOTIS", "source": source, "written": written, "dedup": dup,
                      "skipped_old_lossless_kept": old_skip,
                      "by_status": dict(Counter(r["status"] for r in recs)),
                      "by_oblast": dict(Counter(o for r in recs for o in r["facets"]["oblast"]))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
