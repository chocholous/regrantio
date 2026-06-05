#!/usr/bin/env python3
"""Krok 2a vrstvy 2: sestav agent-friendly extrakční vstupy pro samosprávné/strukturní zdroje.

Join: záznam v opportunities.jsonl (id=canon_key) ↔ harvest program (plný _text + URL příloh)
↔ doc-store manifest (stažený text příloh). Per dotčený záznam vyprodukuje
{id, web, title, body, attachments_md} = PLNÝ text programu + PLNÝ text příloh (bez ořezu,
acquisition.input_truncation=null). `id` = stabilní opportunity id pro merge zpět.

Dotčené = stejný filtr jako vyříznuté keyword ingesty (platform∈{dotis,fondvysociny,kentico}
nebo harvester==platform). Záznam bez harvest-textu i bez příloh dostane body=focus/title
(LLM zvládne aspoň klasifikaci oblasti).

Usage: python3 scripts/build_samosprava_extract_input.py --out-dir /tmp/ei_sam
"""
import argparse, glob, json, os, re, sys
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docstore

ATT_KEYS = ("_attachments", "_documents", "attachments", "_files", "documents")


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]", " ", (s or "").lower())).strip()


def affected(r):
    p = r.get("provenance") or {}
    pl, hv = p.get("platform"), p.get("harvester")
    return pl in ("dotis", "fondvysociny", "kentico") or (pl is not None and pl == hv)


def doc_urls(prog):
    base = prog.get("url") or ""
    out = []
    for k in ATT_KEYS:
        v = prog.get(k)
        if isinstance(v, list):
            for it in v:
                u = it if isinstance(it, str) else (it.get("url") if isinstance(it, dict) else None)
                if u:
                    out.append(urljoin(base, u))
    return out


def att_md(urls, manifest):
    parts = []
    for u in urls:
        e = manifest.get(u)
        if not e or not e.get("ok"):
            continue
        path = e.get("md_path") or e.get("txt_path")
        if path and os.path.exists(path):
            try:
                parts.append(open(path, encoding="utf-8", errors="replace").read())
            except Exception:
                pass
    return "\n\n".join(parts)


def harvest_programs():
    """Yield (source, title, body, doc_urls) ze všech strukturních harvestů."""
    # dict/programs: města + kraje + fondvysociny
    for f in glob.glob("data/h_mesto_*.json") + glob.glob("data/h_kraj_*.json") + ["data/h_fondvysociny.json"]:
        if not os.path.exists(f):
            continue
        try:
            H = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        src = H.get("source")
        for p in H.get("programs", []):
            yield src, p.get("nazev") or "", (p.get("_text") or p.get("popis") or ""), doc_urls(p)
    # dotis (nested programs→subprojects); title = "name (memo)"
    if os.path.exists("data/h_dotis_khk.json"):
        H = json.load(open("data/h_dotis_khk.json", encoding="utf-8"))
        src = H.get("source")
        for prog in H.get("programs", []):
            for s in prog.get("subprojects") or []:
                memo = s.get("memo") or ""
                name = s.get("name") or prog.get("name") or ""
                title = f"{name} ({memo})" if memo else name
                yield src, title, prog.get("name") or "", []
    # kentico (jsonl): {url,title,eligible,attachments}
    for f, src in (("data/h_kentico_irop.jsonl", "irop.gov.cz"), ("data/h_kentico_dotaceeu.jsonl", "dotaceeu.cz")):
        if not os.path.exists(f):
            continue
        for l in open(f, encoding="utf-8"):
            try:
                r = json.loads(l)
            except Exception:
                continue
            atts = [a.get("url") for a in (r.get("attachments") or []) if isinstance(a, dict) and a.get("url")]
            body = " ".join(x for x in (r.get("eligible"), r.get("text")) if x)
            yield src, r.get("title") or "", body, atts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opps", default="data/opportunities.jsonl")
    ap.add_argument("--out-dir", default="/tmp/ei_sam")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    for f in glob.glob(a.out_dir + "/grant_*.json"):
        os.remove(f)

    # index dotčených opportunities: (source, normtitle) -> opp record
    opp = {}
    for l in open(a.opps, encoding="utf-8"):
        r = json.loads(l)
        if affected(r):
            opp[(r.get("source"), norm(r.get("title")))] = r
    print(f"dotčených opportunities: {len(opp)}", file=sys.stderr)

    manifest = docstore.load_manifest()
    built = {}   # opp_id -> {body, att}
    matched = 0
    for src, title, body, urls in harvest_programs():
        key = (src, norm(title))
        r = opp.get(key)
        if not r:
            continue
        oid = r["id"]
        amd = att_md(urls, manifest) if urls else ""
        # nejbohatší varianta vyhrává (víc harvest řádků může mapovat na týž id)
        prev = built.get(oid)
        score = len(body or "") + len(amd)
        if not prev or score > prev["score"]:
            built[oid] = {"body": body or "", "att": amd, "title": r.get("title"),
                          "web": src, "score": score,
                          "elig": r.get("eligible_applicants"), "focus": r.get("focus_area")}
        matched += 1

    # doplň dotčené BEZ harvest-matche (body z opportunities: focus/eligible/title)
    for (src, _), r in opp.items():
        oid = r["id"]
        if oid not in built:
            body = " ".join(x for x in (r.get("focus_area"), r.get("eligible_applicants")) if x)
            built[oid] = {"body": body, "att": "", "title": r.get("title"), "web": src,
                          "score": len(body), "elig": r.get("eligible_applicants"), "focus": r.get("focus_area")}

    paths = {}
    n = 0
    rich = withatt = 0
    for oid, d in built.items():
        body = d["body"]
        if d.get("elig") and d["elig"] not in body:
            body = (body + "\nOprávnění žadatelé: " + d["elig"]).strip()
        base = f"grant_{n:04d}.json"
        json.dump({"id": oid, "web": d["web"], "title": d["title"], "body": body,
                   "attachments_md": d["att"]},
                  open(os.path.join(a.out_dir, base), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        paths[base] = oid
        if len(body) > 500:
            rich += 1
        if d["att"]:
            withatt += 1
        n += 1
    json.dump(paths, open(os.path.join(a.out_dir, "paths.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "EI_SAMOSPRAVA", "vstupů": n, "harvest_match": matched,
                      "bohatý_body": rich, "s_přílohami": withatt, "out_dir": a.out_dir}, ensure_ascii=False))


if __name__ == "__main__":
    main()
