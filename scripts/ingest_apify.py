#!/usr/bin/env python3
"""Ingest Apify-crawlnutých (kraje/nadace) extrakcí → opportunities.jsonl S OPPORTUNITY-GATE.

Apify crawl posbíral i KATALOGY/ROZCESTNÍKY (ne jen oportunity). Gate ponechá jen záznamy s
konkrétní oportunitou (deadline / oprávněnost / částka / číslo výzvy / mise s tím, jak požádat),
generické katalogy (titul „Dotace/Granty/Programové dotace…" bez signálu) ZAHODÍ. Reuse rich mapping
z ingest_rich. Facety dle kategorie: kraj→samosprava_kraj/krajsky, nadace→nadace/vlastni_zdroje.

Usage: python3 scripts/ingest_apify.py --out-dir /tmp/apify_out --meta data/apify_meta.json --out data/opportunities.jsonl [--dry-run]
"""
import argparse, glob, json, os, re, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opportunities import compute_status, resolve_citations, _pd, _host
from ingest_rich import _facets_grant, _num, CORE_GRANT, _rec_grant  # reuse

# povolené zdrojové domény (seed crawlů) — crawl bloudil na externí news, ty ZAHODIT
ALLOWED = {"zlinskykraj.cz", "stredoceskykraj.cz", "pardubickykraj.cz", "kr-ustecky.cz",
           "kr-kralovehradecky.cz", "kr-karlovarsky.cz", "jihocesky.cz",
           "nadacecez.cz", "nadaceokd.cz", "nros.cz", "nadacevia.cz", "vdv.cz",
           "nadacevodafone.cz", "nadaceo2.cz", "nadace-agrofert.cz"}
# katalog/info/rozcestník/news fráze (kdekoli v titulu) → ZAHODIT
CATALOG = re.compile(r"grantov[áé] (řízení|programy)|pro žadatele|pro média|pro media|aktuality|"
                     r"domovská stránka|přehled (výzev|dotací|grant)|webový portál|"
                     r"aktuálně vyhlášené|nadační příspěvky|seznam (výzev|dotací)|"
                     r"^\s*(městské |programové )?(granty|dotace)( a projekty)?\s*(—|\||$)", re.I)


def is_opportunity(f, title):
    """True = konkrétní oportunita; False = katalog/rozcestník/news (pozor: ne katalogy!)."""
    t = (title or "").strip()
    if not t or CATALOG.search(t):
        return False
    elig_ok = f.get("eligible_applicants") and len(str(f["eligible_applicants"])) > 40
    theme = f.get("focus_area") or f.get("oblast")
    # SILNÝ signál konkrétní výzvy/programu (ne news, ne katalog)
    vyzva = (f.get("deadline") or f.get("open_from") or f.get("cislo_vyzvy")
             or (f.get("deadliny") and len(f["deadliny"]) > 0)
             or (elig_ok and theme))
    # foundation_mission: jen pokud nese KONKRÉTNÍ jak požádat (ne homepage/about)
    mission_sig = f.get("mission") and f.get("jak_oslovit")
    return bool(vyzva or mission_sig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/tmp/apify_out")
    ap.add_argument("--meta", default="data/apify_meta.json")
    ap.add_argument("--out", default="data/opportunities.jsonl")
    ap.add_argument("--today", default="2026-06-05")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = _pd(a.today) or date.today()
    _rec_grant.ptypes = {}  # apify zdroje nejsou v provider_types
    meta = json.load(open(a.meta, encoding="utf-8"))
    POSK = {"kraj": "samosprava_kraj", "nadace": "nadace"}
    ZDROJ = {"kraj": "krajsky", "nadace": "vlastni_zdroje"}

    seen = set()
    if os.path.exists(a.out):
        for l in open(a.out, encoding="utf-8"):
            try: seen.add(json.loads(l).get("id"))
            except Exception: pass

    keep, drop, dropped_titles = [], [], []
    for fp in sorted(glob.glob(a.out_dir + "/grant_*.json")):
        base = os.path.basename(fp)
        m = meta.get(base)
        if not m:
            continue
        try:
            f = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        title = f.get("title") or m.get("url")
        host = m["web"]; cat = m["kategorie"]
        if host not in ALLOWED:                       # crawl odbloudil na externí web (news) → ven
            drop.append(base); dropped_titles.append(f"[ext:{host}] " + (title or "?")[:40]); continue
        if not is_opportunity(f, title):
            drop.append(base); dropped_titles.append((title or "?")[:50]); continue
        st, conf = compute_status(f.get("open_from"), f.get("deadline"), today)
        rec = {
            "kind": "grant", "source": host, "source_url": m["url"],
            "title": title, "focus_area": f.get("focus_area"),
            "open_from": f.get("open_from"), "deadline": f.get("deadline"),
            "status": st, "status_confidence": conf, "amount": _num(f.get("vyse_hlavni_czk")),
            "eligible_applicants": f.get("eligible_applicants"),
            "required_attachments": f.get("required_attachments") or [],
            "how_to_apply": f.get("how_to_apply"), "source_doc": m["url"], "id": m["id"],
            "facets": _facets_grant(f, host, {host: POSK.get(cat)}),
            "provenance": {"layer": 2, "harvester": "apify/website-content-crawler",
                           "platform": "apify", "harvest_url": m["url"], "documents": []},
        }
        rec["facets"]["typ_poskytovatele"] = POSK.get(cat)
        if not rec["facets"].get("zdroj_financovani"):
            rec["facets"]["zdroj_financovani"] = [ZDROJ.get(cat)]
        # kraj → kraj do regionu (z hosta hrubě); nadace → celostátní
        if cat == "nadace":
            rec["facets"]["region"] = {"nazev": None, "obec": None, "okres": None, "kraj": None,
                                       "celostatni": True, "_conf": "low"}
        extra = {k: v for k, v in f.items() if k not in CORE_GRANT and v not in (None, "", [], {})}
        for k in ("castky", "deadliny", "dokumenty", "prijemci", "dalsi_datumy", "dalsi_castky"):
            if f.get(k): extra[k] = f[k]
        rec["extra"] = extra
        rec["_evidence"] = f.get("evidence") or {}
        rec["_page_text"] = ""
        resolve_citations(rec)
        keep.append(rec)

    new = [r for r in keep if r["id"] not in seen]
    if not a.dry_run:
        with open(a.out, "a", encoding="utf-8") as o:
            for r in new:
                seen.add(r["id"]); o.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(json.dumps({"MARKER": "INGEST_APIFY", "kept": len(keep), "new_written": 0 if a.dry_run else len(new),
                      "dropped_catalogs": len(drop),
                      "by_source": dict(Counter(r["source"] for r in keep))}, ensure_ascii=False))
    if a.dry_run:
        print("DROPPED (katalogy):", "; ".join(dropped_titles[:30]))
        print("KEPT vzorek:", "; ".join((r["title"] or "?")[:45] for r in keep[:15]))


if __name__ == "__main__":
    main()
