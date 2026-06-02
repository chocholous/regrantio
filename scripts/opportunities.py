#!/usr/bin/env python3
"""Kanonické úložiště VRSTVY 2 — sjednocuje výstupy ze VŠECH zdrojů do jednoho schématu.

Vstup je heterogenní (per-zdroj formát vrstvy 1 → extrakce):
  - LLM extrakce (extract_wf.js workflow výstup): {path, type, fields{...}}
  - strukturované zdroje bez LLM (dsw2 appeals, granty.praha rows) — mapují se přímo
Výstup = data/opportunities.jsonl: 1 oportunita/řádek, PLOCHÁ pole dle druhu (viz
schema/opportunity_schema.md), STATUS dopočítaný v kódu, + provenience (source/source_url/_layer).

Status NEpochází z LLM — počítá se zde z dat vs dnešek (--today, default date.today()).

Použití:
  python3 scripts/opportunities.py --from-extraction /tmp/pg2_out.json --source praha [--src-dir /tmp/pg2]
  python3 scripts/opportunities.py --from-dsw2 data/dsw2_appeals.jsonl
  (zapisuje/přidává do data/opportunities.jsonl; --reset přepíše)
"""
import argparse, json, os, re, sys
from datetime import date

OUT_DEFAULT = "data/opportunities.jsonl"

def _pd(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    return date(int(m[1]), int(m[2]), int(m[3])) if m else None

def compute_status(open_from, deadline, today):
    """status v KÓDU (ne LLM): announced/open/closed/unknown + confidence."""
    if (deadline or "") in ("průběžně", "rolling"):
        return "open", "high"   # rolling = otevřeno dokud běží
    do, of = _pd(deadline), _pd(open_from)
    if not do:
        return "unknown", "low"
    if of and today < of:
        return "announced", "high"
    if today > do:
        return "closed", "high"
    return "open", "high"

def _norm_map(s):
    """Vrať (text bez whitespace + lowercase, index-mapa na originál).
    Bez whitespace = odolné vůči PDF řádkování i mezerám v datech (24. 6. 2026 ≈ 24.6.2026)."""
    out, idx = [], []
    for i, ch in enumerate(s):
        if ch.isspace():
            continue
        out.append(ch.lower()); idx.append(i)
    return "".join(out), idx

def resolve_citations(opp):
    """Pro každé pole v _evidence LOKALIZUJ verbatim citaci ve zdrojích (body stránky +
    stažené dokumenty) → {field, value, quote, source, char_start, char_end, context, match}.
    Grounding NEhodnotí (verdikt na člověku) — jen najde místo + označí shodu (exact/fragment/none)."""
    ev = opp.pop("_evidence", {}) or {}
    # zdroje k prohledání: body stránky (layer-1) + stažené dokumenty (doc-store)
    sources = []
    page = opp.pop("_page_text", None)
    if page:
        sources.append({"kind": "page", "ref": opp.get("source_url"), "text": page})
    for d in opp.get("provenance", {}).get("documents", []):
        if d.get("txt_path") and os.path.exists(d["txt_path"]):
            try:
                sources.append({"kind": "doc", "ref": d["txt_path"], "url": d.get("url"),
                                "text": open(d["txt_path"], encoding="utf-8", errors="replace").read()})
            except Exception:
                pass
    for s in sources:
        s["nt"], s["imap"] = _norm_map(s["text"])

    def locate(nq):
        for s in sources:                                   # 1) přesná shoda (bez whitespace)
            pos = s["nt"].find(nq)
            if pos >= 0:
                return s, pos, len(nq), "exact"
        if len(nq) >= 30:                                   # 2) fragmentový fallback (drift LLM)
            frag = nq[len(nq) // 2 - 14: len(nq) // 2 + 14]
            for s in sources:
                pos = s["nt"].find(frag)
                if pos >= 0:
                    return s, pos, len(frag), "fragment"
        return None, None, None, "none"

    cites = []
    for field, quote in ev.items():
        if not quote or not isinstance(quote, str):
            continue
        nq = "".join(quote.lower().split())
        c = {"field": field, "value": opp.get(field), "quote": quote,
             "source": None, "ref": None, "char_start": None, "char_end": None, "match": "none"}
        if len(nq) >= 8:
            s, pos, ln, match = locate(nq)
            if s:
                start = s["imap"][pos]; end = s["imap"][min(pos + ln - 1, len(s["imap"]) - 1)] + 1
                c.update(source=s["kind"], ref=s.get("url") or s["ref"],
                         char_start=start, char_end=end, context=s["text"][start:end], match=match)
        cites.append(c)
    if cites:
        opp["citations"] = cites
    return opp

def canon_key(kind, title, source_url):
    t = re.sub(r"[^a-z0-9á-ž]+", "", (title or "").lower())[:48]
    m = re.search(r"(\d+)\.\s*výzv", (title or "").lower())
    num = (m.group(1) + "|") if m else ""
    return f"{kind}:{num}{t}" or f"{kind}:{(source_url or '')[-40:]}"

CANON_FIELDS = {  # co se mapuje do schématu (zbytek → extra, nic se nezahodí)
    "grant": {"title", "focus_area", "open_from", "deadline", "amount", "eligible_applicants",
              "required_attachments", "how_to_apply", "source_doc"},
    "project": {"title", "grantee", "grantee_ico", "amount", "year", "period", "focus_area"},
    "foundation_mission": {"name", "mission", "support_topics", "regions"},
}

# ---------- mapování polí vrstvy 2 → jednotný model ----------
def opp_from_fields(kind, f, prov, today, extra=None):
    base = {"kind": kind, "source": prov["source"], "foundation_id": prov.get("foundation_id"),
            "source_url": prov.get("source_url")}
    if kind == "grant":
        st, conf = compute_status(f.get("open_from"), f.get("deadline"), today)
        base.update(title=f.get("title"), focus_area=f.get("focus_area"),
                    open_from=f.get("open_from"), deadline=f.get("deadline"),
                    status=st, status_confidence=conf,
                    amount=f.get("amount"), eligible_applicants=f.get("eligible_applicants"),
                    required_attachments=f.get("required_attachments") or [],
                    how_to_apply=f.get("how_to_apply"), source_doc=f.get("source_doc"))
    elif kind == "project":
        # project status z roku/období (done když rok < letošek, jinak open)
        yr = str(f.get("year") or f.get("period") or "")
        ym = re.search(r"20\d\d", yr)
        st = "closed" if (ym and int(ym.group()) < today.year) else "open"
        base.update(title=f.get("title"), grantee=f.get("grantee"), grantee_ico=f.get("grantee_ico"),
                    amount=f.get("amount"), year=f.get("year"), focus_area=f.get("focus_area"),
                    status=st, status_confidence="low")
    elif kind == "foundation_mission":
        base.update(name=f.get("name"), mission=f.get("mission"),
                    support_topics=f.get("support_topics") or [], regions=f.get("regions") or [])
    base["id"] = canon_key(kind, base.get("title") or base.get("name"), base.get("source_url"))
    # Q2 — VAZBA na zdroj: layer-1 raw + stažené soubory
    base["provenance"] = {
        "layer": prov.get("_layer", 2), "harvester": prov.get("_harvester"),
        "harvest_file": prov.get("harvest_file"),     # který data/*.jsonl nese raw záznam
        "harvest_url": prov.get("source_url"),        # klíč do něj (= web stránka)
        "documents": prov.get("documents") or [],     # [{url, txt_path, ext}] stažené podklady
        "classification": prov.get("classification"), # {base_type, confidence, reasoning[]} = PROČ zařazeno (audit)
    }
    # Q1 — LOSSLESS: vše nemapované se uloží do extra (nic se nezahodí)
    structural = CANON_FIELDS.get(kind, set()) | {"evidence"}
    over = {k: v for k, v in (f or {}).items() if k not in structural and v not in (None, "", [], {})}
    if extra:
        over.update(extra)
    base["extra"] = over
    base["_evidence"] = (f or {}).get("evidence") or {}   # {pole: verbatim citace} → resolve_citations()
    return base

# ---------- vstup: extract_wf workflow výstup ----------
def _harvest_index(harvest_file):
    """url → layer-1 raw záznam (pro join dokumentů + lossless extra)."""
    idx = {}
    if harvest_file and os.path.exists(harvest_file):
        for l in open(harvest_file, encoding="utf-8"):
            try:
                r = json.loads(l); idx[r.get("url")] = r
            except Exception:
                pass
    return idx

def _load_classifications(path):
    """url → {base_type, confidence, reasoning[]} z data/classifications.jsonl (audit zařazení)."""
    idx = {}
    if path and os.path.exists(path):
        for l in open(path, encoding="utf-8"):
            try:
                e = json.loads(l)
                idx[e["url"]] = {"base_type": e.get("base_type"), "confidence": e.get("confidence"),
                                 "reasoning": e.get("reasoning") or []}
            except Exception:
                pass
    return idx


def ingest_extraction(result_path, source, src_dir, harvest_file, today, classifications=None):
    raw = json.load(open(result_path, encoding="utf-8"))
    items = raw["result"] if isinstance(raw, dict) and "result" in raw else raw
    hidx = _harvest_index(harvest_file)
    classifications = classifications or {}
    for it in items:
        f = it.get("fields")
        if not f:
            continue
        sp, surl, fid, page = it.get("path"), None, None, None
        if sp and src_dir and os.path.exists(sp):
            s = json.load(open(sp, encoding="utf-8"))
            surl = s.get("id"); fid = s.get("_oblast") or s.get("web"); page = s.get("body")
        surl = surl or f.get("source_doc")
        rawrec = hidx.get(surl, {})
        # dokumenty z layer-1 raw (URL; txt_path doplní doc-store až bude perzistentní)
        docs = [{"url": u, "txt_path": None} for u in (rawrec.get("documents") or [])]
        # lossless extra z raw (BEZ velkého textu — ten je dohledatelný přes harvest_file+url)
        extra = {k: v for k, v in rawrec.items()
                 if k not in ("url", "title", "text", "html", "documents", "content_html", "content_text")
                 and v not in (None, "", [], {})}
        prov = {"source": source, "source_url": surl, "foundation_id": fid,
                "_layer": 2, "_harvester": "extract_wf",
                "harvest_file": harvest_file, "documents": docs,
                "classification": classifications.get(surl)}   # PROČ zařazeno (base_type+confidence+reasoning)
        opp = opp_from_fields(it.get("type", "grant"), f, prov, today, extra=extra)
        opp["_page_text"] = page   # tělo stránky (layer-1) — prohledá resolve_citations
        yield opp

# ---------- vstup: dsw2 appeals (STRUKTUROVANÉ, bez LLM) ----------
def ingest_dsw2(path, today):
    consumed = {"title", "focus_area", "open_from", "deadline", "amount", "eligible_applicants",
                "url", "source_url", "foundation_id", "status"}
    for line in open(path, encoding="utf-8"):
        a = json.loads(line)
        f = {"title": a.get("title"), "focus_area": a.get("focus_area"),
             "open_from": a.get("open_from"), "deadline": a.get("deadline"),
             "amount": a.get("amount"), "eligible_applicants": a.get("eligible_applicants"),
             "required_attachments": [], "how_to_apply": None, "source_doc": a.get("source_url")}
        docs = [{"url": u, "txt_path": None} for u in (a.get("links") or [])]
        extra = {k: v for k, v in a.items() if k not in consumed and v not in (None, "", [], {})}
        prov = {"source": "dsw2", "source_url": a.get("url"), "foundation_id": a.get("foundation_id"),
                "_layer": 1, "_harvester": "dsw2.py", "harvest_file": path, "documents": docs}
        yield opp_from_fields("grant", f, prov, today, extra=extra)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-extraction", help="extract_wf workflow výstup (JSON)")
    ap.add_argument("--source", default="?", help="název zdroje (praha/eeagrants…)")
    ap.add_argument("--src-dir", help="adresář zdrojových per-doc JSON (pro source_url)")
    ap.add_argument("--harvest-file", help="layer-1 raw jsonl (join dokumentů + lossless extra)")
    ap.add_argument("--from-dsw2", help="data/dsw2_appeals.jsonl (strukturované)")
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--link-docs", action="store_true", help="vyplň provenance.documents[].txt_path z doc-store manifestu")
    ap.add_argument("--reset", action="store_true", help="přepiš místo append")
    ap.add_argument("--today", help="referenční datum YYYY-MM-DD (default dnes)")
    ap.add_argument("--classifications", help="data/classifications.jsonl → provenance.classification (PROČ zařazeno)")
    args = ap.parse_args()
    today = _pd(args.today) or date.today()
    cls = _load_classifications(args.classifications)

    recs = []
    if args.from_extraction:
        recs += list(ingest_extraction(args.from_extraction, args.source, args.src_dir, args.harvest_file, today, cls))
    if args.from_dsw2:
        recs += list(ingest_dsw2(args.from_dsw2, today))

    if args.link_docs:   # doplň txt_path z kanonického doc-store manifestu
        man = {}
        mf = "data/files/manifest.jsonl"
        if os.path.exists(mf):
            for l in open(mf, encoding="utf-8"):
                try: e = json.loads(l); man[e["url"]] = e.get("txt_path")
                except Exception: pass
        for r in recs:
            for d in r.get("provenance", {}).get("documents", []):
                if d.get("url") in man:
                    d["txt_path"] = man[d["url"]]

    for r in recs:   # evidence (verbatim citace z LLM) → citations (lokalizace v souboru + offset)
        resolve_citations(r)

    # dedup dle id v rámci tohoto běhu + proti existujícímu souboru (append)
    seen = set()
    if not args.reset and os.path.exists(args.out):
        for l in open(args.out, encoding="utf-8"):
            try: seen.add(json.loads(l).get("id"))
            except Exception: pass
    mode = "w" if args.reset else "a"
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    written, dup = 0, 0
    with open(args.out, mode, encoding="utf-8") as o:
        for r in recs:
            if r["id"] in seen:
                dup += 1; continue
            seen.add(r["id"]); o.write(json.dumps(r, ensure_ascii=False) + "\n"); written += 1
    from collections import Counter
    print(json.dumps({"MARKER": "OPPORTUNITIES", "written": written, "dedup_skipped": dup,
                      "by_status": dict(Counter(r["status"] for r in recs if "status" in r)),
                      "today": str(today), "out": args.out}, ensure_ascii=False))

if __name__ == "__main__":
    main()
