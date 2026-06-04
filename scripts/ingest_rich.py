#!/usr/bin/env python3
"""Bohatý ingest vrstvy 2 → opportunities.jsonl (nové schéma z /tmp/out).

Spojuje: /tmp/out/<base>.json (bohatá extrakce) ↔ /tmp/mg2|/tmp/mm2/<base>.json (id, web, body)
↔ stávající opportunities.jsonl (provenance.documents + source_url, dle id). Pro 620 extrahovaných
ID nahradí záznam BOHATOU verzí; 158 ostatních (prázdné/dsw2 programy) projde beze změny.

Princip:
- multi→hlavní+sběrače: deadline (hlavní) + deadliny[] (sběrač) · vyse_hlavni_czk + castky[] · dalsi_*
- region[]→geo: region[0] do facets.region {nazev,obec,okres,kraj,celostatni,_conf}; plné pole do extra
- doc-role: dokumenty[]{popis,role} → extra (build_app fasetuje typ dokumentu)
- STATUS v kódu (compute_status), NE z LLM · evidence→citations (resolve_citations)
- facety = RAW hodnoty (konsolidace je SAMOSTATNÝ pass scripts/consolidate.py)

Usage:
  python3 scripts/ingest_rich.py [--out-dir /tmp/out] [--src /tmp/mg2 /tmp/mm2]
      [--existing data/opportunities.jsonl] [--out data/opportunities_v2.jsonl] [--today 2026-06-01]
"""
import argparse, glob, json, os, re, sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opportunities import compute_status, resolve_citations, _pd, _host  # reuse

# rich pole, která se NEvkládají do extra (jsou už v core/facets/citations) — zbytek = lossless extra
CORE_GRANT = {"title", "focus_area", "open_from", "deadline", "oblast", "typ_zadatele", "cilova_skupina",
              "forma_podpory", "zdroj_financovani", "rezim_prijmu", "delka", "spoluucast",
              "eligible_applicants", "required_attachments", "how_to_apply", "source_doc", "evidence",
              "vyse_hlavni_czk", "castky", "region"}
CORE_MISSION = {"name", "mission", "support_topics", "cilova_skupina", "regions", "forma_podpory",
                "jak_oslovit", "kontakt", "source_doc", "evidence"}


def _num(x):
    """číslo z int/float nebo z numerického stringu ('4 700 000', '70 %') → int; jinak None."""
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return int(x)
    if isinstance(x, str):
        s = re.sub(r"[^\d]", "", x)
        return int(s) if s else None
    return None


def _provider_types(path):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


def _castka_pick(castky, pred):
    for c in castky:
        if isinstance(c, dict) and pred((c.get("typ") or "").lower()):
            n = _num(c.get("hodnota"))
            if n:
                return n
    return None


def _facets_grant(f, host, ptypes):
    castky = f.get("castky") or []
    alok = _castka_pick(castky, lambda t: "alokace" in t)
    maxz = _num(f.get("vyse_hlavni_czk")) or _castka_pick(
        castky, lambda t: ("strop" in t or "max" in t or "maxim" in t) and ("zadatel" in t or "projekt" in t or "zad" in t))
    mira = None
    for c in castky:
        t = (c.get("typ") or "").lower()
        if any(k in t for k in ("procento", "pct", "podil", "mira", "míra")):
            n = _num(c.get("hodnota"))
            if n and n <= 100:
                mira = n
                break
    region = [r for r in (f.get("region") or []) if isinstance(r, dict)]
    r0 = region[0] if region else {}
    reg = {"nazev": r0.get("nazev"), "obec": r0.get("obec"), "okres": r0.get("okres"),
           "kraj": r0.get("kraj"), "celostatni": bool(r0.get("celostatni")),
           "_conf": "high" if region else "low"}
    return {
        "oblast": f.get("oblast") or [],
        "typ_zadatele": f.get("typ_zadatele") or [],
        "sektor_zadatele": [],                       # doplní consolidate.py (rollup z typ_zadatele)
        "typ_poskytovatele": ptypes.get(host),
        "forma_podpory": f.get("forma_podpory") or [],
        "zdroj_financovani": f.get("zdroj_financovani") or [],
        "rezim_prijmu": f.get("rezim_prijmu"),
        "delka": f.get("delka"),
        "zpusob_podani": [],                          # how_to_apply je próza; odvodí build/consolidate
        "cilova_skupina": f.get("cilova_skupina") or [],
        "mira_podpory_pct": mira,
        "spoluucast": f.get("spoluucast"),
        "vyse_alokace_czk": alok,
        "vyse_max_zadatel_czk": maxz,
        "region": reg,
        "multi_region": len(region) > 1,
    }


def _rec_grant(f, base_id, host, surl, prov, today, page):
    st, conf = compute_status(f.get("open_from"), f.get("deadline"), today)
    rec = {
        "kind": "grant", "source": host, "source_url": surl,
        "title": f.get("title"), "focus_area": f.get("focus_area"),
        "open_from": f.get("open_from"), "deadline": f.get("deadline"),
        "status": st, "status_confidence": conf,
        "amount": _num(f.get("vyse_hlavni_czk")),
        "eligible_applicants": f.get("eligible_applicants"),
        "required_attachments": f.get("required_attachments") or [],
        "how_to_apply": f.get("how_to_apply"), "source_doc": f.get("source_doc"),
        "id": base_id,
        "facets": _facets_grant(f, host, _rec_grant.ptypes),
        "provenance": prov,
    }
    # sběrače + role + multi-region + lossless zbytek → extra
    extra = {k: v for k, v in f.items() if k not in CORE_GRANT and v not in (None, "", [], {})}
    extra.update({k: f[k] for k in ("castky", "deadliny", "dokumenty", "prijemci",
                                    "dalsi_datumy", "dalsi_castky", "vyse_hlavni_czk")
                  if f.get(k) not in (None, "", [], {})})
    if len([r for r in (f.get("region") or []) if isinstance(r, dict)]) > 1:
        extra["region_all"] = f.get("region")
    rec["extra"] = extra
    rec["_evidence"] = f.get("evidence") or {}
    rec["_page_text"] = page
    return rec


def _rec_mission(f, base_id, host, surl, prov, page):
    rec = {
        "kind": "foundation_mission", "source": host, "source_url": surl,
        "name": f.get("name"), "mission": f.get("mission"),
        "support_topics": f.get("support_topics") or [], "regions": f.get("regions") or [],
        "id": base_id,
        # mise NEpatří do grantové oblast/cílová-facety (free support_topics by je tříštily) —
        # jejich témata zůstávají top-level + v extra; facety jen poskytovatel + forma
        "facets": {"typ_poskytovatele": _rec_grant.ptypes.get(host), "forma_podpory": f.get("forma_podpory") or []},
        "provenance": prov,
    }
    extra = {k: v for k, v in f.items() if k not in CORE_MISSION and v not in (None, "", [], {})}
    for k in ("jak_oslovit", "kontakt", "cilova_skupina"):
        if f.get(k) not in (None, "", [], {}):
            extra[k] = f[k]
    rec["extra"] = extra
    rec["_evidence"] = f.get("evidence") or {}
    rec["_page_text"] = page
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="/tmp/out")
    ap.add_argument("--src", nargs="+", default=["/tmp/mg2", "/tmp/mm2"])
    ap.add_argument("--existing", default="data/opportunities.jsonl")
    ap.add_argument("--provider-types", default="data/provider_types.json")
    ap.add_argument("--out", default="data/opportunities_v2.jsonl")
    ap.add_argument("--today", default="2026-06-01")
    a = ap.parse_args()
    today = _pd(a.today) or date.today()
    _rec_grant.ptypes = _provider_types(a.provider_types)

    # index vstupů: basename → (id, web, body)
    src_idx = {}
    for d in a.src:
        for fp in glob.glob(d + "/*.json"):
            try:
                r = json.load(open(fp, encoding="utf-8"))
                src_idx[os.path.basename(fp)] = (r.get("id"), r.get("web"), r.get("body") or "")
            except Exception:
                pass

    # existující záznamy: id → celý záznam (pro provenance + passthrough 158)
    existing = {}
    for l in open(a.existing, encoding="utf-8"):
        try:
            r = json.loads(l)
            existing[r.get("id")] = r
        except Exception:
            pass

    rich_ids, out_recs, miss_src, miss_id = set(), [], 0, 0
    for fp in sorted(glob.glob(a.out_dir + "/grant_*.json")) + sorted(glob.glob(a.out_dir + "/mission_*.json")):
        base = os.path.basename(fp)
        if base not in src_idx:
            miss_src += 1; continue
        gid, web, body = src_idx[base]
        host = web or _host(gid or "")
        try:
            f = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        old = existing.get(gid, {})
        prov = old.get("provenance") or {"layer": 2, "harvester": "extract_wf", "documents": []}
        surl = old.get("source_url") or gid
        is_mission = base.startswith("mission_")
        rec = (_rec_mission(f, gid, host, surl, prov, body) if is_mission
               else _rec_grant(f, gid, host, surl, prov, today, body))
        resolve_citations(rec)
        out_recs.append(rec)
        rich_ids.add(gid)

    # passthrough: vše z existing, co jsme NEnahradili
    passth = [r for rid, r in existing.items() if rid not in rich_ids]

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as o:
        for r in out_recs + passth:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")

    from collections import Counter
    print(json.dumps({"MARKER": "INGEST_RICH", "rich": len(out_recs), "passthrough": len(passth),
                      "total": len(out_recs) + len(passth), "miss_src": miss_src,
                      "by_status": dict(Counter(r.get("status") for r in out_recs if "status" in r)),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
