#!/usr/bin/env python3
"""Krok 2c: merge LLM extrakce (extract_wf → /tmp/eo_sam) zpět do opportunities.jsonl.

Join přes paths.json (basename → opp_id). Aktualizuje JEN dotčené záznamy:
- oblast / typ_zadatele / cilova_skupina ← EXTRAKCE (vocab-validováno; nahrazuje smazaný keyword)
- alokace / max / míra / spoluúčast / forma / zdroj / režim / délka ← doplní, kde je prázdno
- eligible / focus_area / how_to_apply ← doplní, kde je prázdno
- deadline / open_from ← PONECHÁ z harvestu (strukturně autoritativní); z extrakce jen když harvest null + ISO
- status ← přepočítá kód z finálních dat
- extra ← lossless (deadliny/castky/dokumenty/dalsi_*/cislo_vyzvy/kontakt); provenance.layer=2
Vocab-validace zahodí Haiku slipy mimo slovník (consolidation_maps).

Usage: python3 scripts/merge_extraction.py --eo /tmp/eo_sam --paths /tmp/ei_sam/paths.json [--today 2026-06-05] [--apply]
"""
import argparse, glob, json, os, re, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opportunities import compute_status, resolve_citations, _pd
from ingest_rich import _facets_grant
import repair_out

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opps", default="data/opportunities.jsonl")
    ap.add_argument("--eo", default="/tmp/eo_sam")
    ap.add_argument("--paths", default="/tmp/ei_sam/paths.json")
    ap.add_argument("--maps", default="data/consolidation_maps.json")
    ap.add_argument("--today", default="2026-06-05")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    today = _pd(a.today) or date.today()

    maps = json.load(open(a.maps, encoding="utf-8"))
    VOC = {k: set(maps[k].values()) for k in ("oblast", "typ_zadatele", "cilova_skupina")}
    paths = json.load(open(a.paths, encoding="utf-8"))

    # načti + repair extrakční výstupy → opp_id -> obj
    ext, parsed, failed = {}, 0, 0
    for f in glob.glob(a.eo + "/grant_*.json"):
        oid = paths.get(os.path.basename(f))
        if not oid:
            continue
        obj, _rep = repair_out.load_repaired(open(f, encoding="utf-8").read())
        if isinstance(obj, dict):
            ext[oid] = obj; parsed += 1
        else:
            failed += 1

    rows = [json.loads(l) for l in open(a.opps, encoding="utf-8")]
    upd = Counter = 0
    stats = {"oblast": 0, "alokace": 0, "eligible": 0, "max": 0, "mira": 0}
    for r in rows:
        obj = ext.get(r.get("id"))
        if not obj:
            continue
        nf = _facets_grant(obj, r.get("source"), {})
        f = r.setdefault("facets", {})
        # 1) klasifikační fazety ← extrakce PASS-THROUGH (free-text); kanonizaci dělá consolidate.py
        #    přes consolidation_maps (variant→kanon). NEvalidovat/nezahazovat tady — extract_wf
        #    záměrně produkuje přirozené hodnoty, mapování je úkol consolidate (jako u korpusu 620).
        for key in ("oblast", "typ_zadatele", "cilova_skupina"):
            vals = nf.get(key) or []
            if vals:
                f[key] = vals
                if key == "oblast":
                    stats["oblast"] += 1
        # 2) bohatá pole — doplnit kde prázdno
        if not f.get("vyse_alokace_czk") and nf.get("vyse_alokace_czk"):
            f["vyse_alokace_czk"] = nf["vyse_alokace_czk"]; stats["alokace"] += 1
        if not f.get("vyse_max_zadatel_czk") and nf.get("vyse_max_zadatel_czk"):
            f["vyse_max_zadatel_czk"] = nf["vyse_max_zadatel_czk"]; stats["max"] += 1
        if not f.get("mira_podpory_pct") and nf.get("mira_podpory_pct"):
            f["mira_podpory_pct"] = nf["mira_podpory_pct"]; stats["mira"] += 1
        if f.get("spoluucast") is None and nf.get("spoluucast") is not None:
            f["spoluucast"] = nf["spoluucast"]
        for key in ("forma_podpory", "zdroj_financovani"):
            if not f.get(key) and nf.get(key):
                f[key] = nf[key]
        for key in ("rezim_prijmu", "delka"):     # schéma=scalar; Haiku občas vrátí list → vezmi první
            v = nf.get(key)
            if isinstance(v, list):
                v = v[0] if v else None
            if not f.get(key) and isinstance(v, str) and v:
                f[key] = v
        # 3) prózová pole — doplnit kde prázdno
        if not r.get("eligible_applicants") and obj.get("eligible_applicants"):
            r["eligible_applicants"] = obj["eligible_applicants"]; stats["eligible"] += 1
        if not r.get("focus_area") and obj.get("focus_area"):
            r["focus_area"] = obj["focus_area"]
        if not r.get("how_to_apply") and obj.get("how_to_apply"):
            r["how_to_apply"] = obj["how_to_apply"]
        if not r.get("amount") and nf.get("vyse_max_zadatel_czk"):
            r["amount"] = nf["vyse_max_zadatel_czk"]
        # 4) datumy: harvest autoritativní; z extrakce jen když harvest prázdný + ISO
        for key in ("deadline", "open_from"):
            if not r.get(key) and ISO.match(obj.get(key) or ""):
                r[key] = obj[key]
        st, conf = compute_status(r.get("open_from"), r.get("deadline"), today)
        r["status"], r["status_confidence"] = st, conf
        # 5) lossless extra + provenance + grounding
        extra = r.setdefault("extra", {})
        for k in ("deadliny", "castky", "dokumenty", "dalsi_datumy", "dalsi_castky", "cislo_vyzvy",
                  "kontakt", "hodnotici_kriteria", "obdobi_realizace"):
            if obj.get(k):
                extra[k] = obj[k]
        prov = r.setdefault("provenance", {})
        prov["layer"] = 2
        if "extract_wf" not in (prov.get("harvester") or ""):
            prov["harvester"] = (prov.get("harvester") or "") + "+extract_wf(haiku)"
        if obj.get("evidence"):
            r["_evidence"] = obj["evidence"]; r.setdefault("_page_text", "")
            try: resolve_citations(r)
            except Exception: pass
        upd += 1

    print(json.dumps({"MARKER": "MERGE_EXTRACTION", "extrakcí_načteno": parsed, "parse_fail": failed,
                      "aktualizováno": upd, "fill": stats, "applied": a.apply}, ensure_ascii=False))
    if a.apply:
        with open(a.opps, "w", encoding="utf-8") as o:
            for r in rows:
                o.write(json.dumps(r, ensure_ascii=False) + "\n")
        print("zapsáno do", a.opps)
    else:
        print("(dry-run — spusť s --apply)")


if __name__ == "__main__":
    main()
