#!/usr/bin/env python3
"""Opportunity pipeline — DRIVER spojující fáze nad UŽ STAŽENÝMI daty.

Recept (viz README.md): detekce → harvest(reuse) → doc→md → klasifikace typu(Sonnet/Haiku)
→ extrakce polí(Haiku) → výpočet statusu(kód) → dedup/grounding.

Toto je SKELETON: deterministické fáze (reuse dat, doc-konverze, status, dedup) jsou plně
implementovatelné; LLM fáze (klasifikace/extrakce) volají prompt + model (Haiku/Sonnet) —
zde jako stub `llm_call()` k zapojení (Apify/Anthropic SDK dle prostředí).

Spuštění:
  python3 pipeline.py --source <host_or_jsonl>           # 1 zdroj
  python3 pipeline.py --reuse-all --out data/opportunities.jsonl
"""
import argparse, json, os, re, sys, glob
from datetime import date

# REPO = kořen TOHOTO repa (opportunity_pipeline je teď soběstačný; data v ./data, mapa v ./platform_map.json)
REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts"))  # lokální dsw2_fetch (dřív ../extract)
TODAY = date(2026, 6, 1)


# ---------- FÁZE 0: detekce rodiny (→ docs/detection.md, scripts/cms_similarity.py) ----------
def detect_family(host):
    """Vrať CMS rodinu z platform_map.json (předpočítáno) nebo spusť cms_similarity."""
    pm = json.load(open(os.path.join(REPO, "platform_map.json")))
    return pm.get("final", {}).get(host, {}).get("plat", "UNKNOWN")


# ---------- FÁZE 1: harvest s REUSE (→ docs/data_reuse.md) ----------
def harvest_reuse(host):
    """Vrať záznamy z UŽ STAŽENÝCH dat, kde existují. Jinak () → nutný scrape/Apify."""
    recs = []
    # WordPress
    for f in glob.glob(os.path.join(REPO, "data/wp_full", f"{host.replace('.','-')}*__*.jsonl")):
        for l in open(f, encoding="utf-8"):
            try:
                r = json.loads(l)
            except Exception:
                continue
            _t = r.get("title")  # nové kanonické vs legacy wp_full snapshot (title=raw objekt)
            recs.append({"url": r.get("url"), "title": _t if isinstance(_t, str) else r.get("title_text"),
                         "date": r.get("date"), "text": r.get("text") or r.get("content_text"),
                         "html": r.get("content_html"), "documents": r.get("documents", []),
                         "entity_hint": r.get("entity")})
    # vismo
    if not recs:
        vf = os.path.join(REPO, "data/vismo_documents.jsonl")
        if os.path.exists(vf):
            for l in open(vf, encoding="utf-8"):
                r = json.loads(l)
                if host in (r.get("web") or ""):
                    recs.append({"url": r.get("url"), "title": r.get("title"),
                                 "text": r.get("body_text"),
                                 "documents": [a["url"] for a in r.get("attachments", [])],
                                 "attachment_texts": [a.get("text_excerpt") for a in r.get("attachments", [])],
                                 "uredni_od": r.get("uredni_od"), "uredni_do": r.get("uredni_do")})
    return recs  # () → README fáze 1: spusť harvester/Apify dle platform_playbook


# ---------- FÁZE 2: dokumenty → markdown (reuse data/*_files, jinak dsw2_fetch) ----------
def docs_to_markdown(doc_urls):
    import dsw2_fetch as df
    out = []
    for u in doc_urls or []:
        # reuse: hledej už převedený .txt podle sha
        # (zde zjednodušeno; produkčně mapuj host/sha → data/vismo_files|dsw2_files)
        ext = df.sniff_ext(u, 15) or df.ext_of(u)
        out.append({"url": u, "ext": ext})  # download+convert by se volal tady
    return out


# ---------- FÁZE 3-4: LLM (klasifikace typu + extrakce polí) ----------
def llm_call(prompt_file, text, model="haiku"):
    """STUB — zapoj Haiku/Sonnet (Anthropic SDK / Apify). Prompt v prompts/."""
    raise NotImplementedError("Zapoj model: prompts/%s + %s na text" % (prompt_file, model))


def classify_type(rec):
    # return llm_call("classify_type.md", rec["text"], model="haiku")["base_type"]
    return rec.get("entity_hint") or "grant"  # fallback na harvest hint


def extract_fields(rec, base_type):
    # full text + markdown příloh, BEZ ořezu; prompts/extract_grant.md + pitfalls.md
    # return llm_call("extract_grant.md", rec["text"] + "\n\n" + attachments_md, model="haiku")
    return {"title": rec.get("title"), "deadline": None, "amount": None,
            "eligible_applicants": None, "_todo": "zapoj Haiku"}


# ---------- FÁZE 5: status z dat (KÓD, ne LLM) ----------
def compute_status(fields, rec):
    def pd(s):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s or "")
        return date(int(m[1]), int(m[2]), int(m[3])) if m else None
    do = pd(rec.get("uredni_do")) or pd(fields.get("deadline"))
    of = pd(rec.get("uredni_od")) or pd(fields.get("open_from"))
    if not do:
        return ("unknown", "low")
    if TODAY > do:
        return ("closed", "high")
    if of and TODAY < of:
        return ("announced", "high")
    return ("open", "high")


# ---------- FÁZE 6: dedup & grounding ----------
def canon_key(opp):
    t = (opp.get("title") or "").lower()
    m = re.search(r"(\d+)\.\s*výzv", t)
    return m.group(1) + "|" + re.sub(r"[^a-záčďéěíňóřšťúůýž0-9]+", "", t)[:40] if m else re.sub(r"[^a-z0-9]+", "", t)[:50]


def run(hosts, out_path):
    seen = {}
    with open(out_path, "w", encoding="utf-8") as o:
        for host in hosts:
            fam = detect_family(host)
            recs = harvest_reuse(host)
            for r in recs:
                bt = classify_type(r)
                if bt not in ("grant", "project"):
                    continue
                f = extract_fields(r, bt)
                st, conf = compute_status(f, r)
                opp = {"source": host, "family": fam, "base_type": bt,
                       "status": st, "status_conf": conf, "url": r.get("url"), **f}
                k = canon_key(opp)
                if k in seen:  # dedup + grounding
                    seen[k].setdefault("also_seen", []).append(host)
                    continue
                seen[k] = opp
                o.write(json.dumps(opp, ensure_ascii=False) + "\n")
    print(f"opportunit: {len(seen)} → {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    ap.add_argument("--reuse-all", action="store_true")
    ap.add_argument("--out", default="data/opportunities.jsonl")
    args = ap.parse_args()
    if args.reuse_all:
        pm = json.load(open(os.path.join(REPO, "platform_map.json")))
        hosts = list(pm.get("final", {}).keys())
    else:
        hosts = [args.source]
    run(hosts, args.out)


if __name__ == "__main__":
    main()
