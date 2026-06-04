#!/usr/bin/env python3
"""Ingest Kentico (IROP/dotaceEU/ministerstva) → opportunities.jsonl.

Kentico harvester (kentico_irop.py) dává STRUKTUROVANÁ pole (title, open_from, deadline, eligible,
status). Sem se mapují do opportunity schématu. Akční pole (deadline/status/eligible) jsou strukturní;
tematické facety (oblast/typ_zadatele) odvozeny DETERMINISTICKY z title/eligible (bez LLM) — hrubé, ale
dává faseta smysl; jemnější LLM enrichment může přijít později. allocation/support_rate harvester
mis-parsuje → NEpoužívají se.

Usage: python3 scripts/ingest_kentico.py data/h_kentico_irop.jsonl --source irop.gov.cz --out data/opportunities.jsonl [--today 2026-06-05]
"""
import argparse, json, os, re, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opportunities import compute_status, canon_key, _host, _pd

# oblast z klíčových slov v title (IROP/infrastrukturní programy)
OBLAST_KW = [
    (r"zdrav|urgent|nemocnic|záchrann.*zdrav|ambulanc", "zdravi"),
    (r"záchrann|IZS|hasič|bezpečn|kyber", "bezpecnost"),
    (r"eGovernment|egov|digital|informačn.*systém|kybernet", "it_digitalizace"),
    (r"doprav|silnic|cykl|mobilita|tramvaj|drážn|železni|terminál", "doprava_mobilita"),
    (r"sociál.*byd|sociální byd", "bydleni_infrastruktura"),
    (r"sociál|deinstitucionaliz|pečovat|komunitní péč", "socialni_sluzby"),
    (r"vzděl|škol|učeben|gramotnost", "vzdelavani_mladez"),
    (r"kultur|divadl|knihovn", "kultura_umeni"),
    (r"památk|kulturní dědictví", "pamatkova_pece"),
    (r"zeleň|životní prostř|energetick|nízkouhlík|adaptac.*změn|biodiverz|krajin|fotovolta|oběhov.*hospod|recykl|odpad|úspor.*energ|obnoviteln|transformac|emis|voda|protipovod|znečiš", "zivotni_prostredi"),
    (r"výzkum|inovac|věd|technolog|startup|podnikán|MSP|konkurenceschop", "veda_vyzkum"),
    (r"bydlen|revitaliz|regenerac|veřejn.*prostranstv|brownfield|infrastruktur", "bydleni_infrastruktura"),
    (r"cestovn.*ruch|turis", "cestovni_ruch"),
]
# typ_zadatele z eligible textu
TYP_KW = [
    (r"\bobc[ei]\b|\bobec\b|měst[ao]|samospráv", "obec_verejny_subjekt"),
    (r"\bkraj", "obec_verejny_subjekt"),
    (r"církv|nábožensk", "cirkev"),
    (r"organizace zřizovan|příspěvkov|PO OSS|OSS|zakládan", "prispevkova_organizace"),
    (r"nestátní neziskov|NNO|spolek|o\.p\.s|nadac|ústav", "neziskovka"),
    (r"\bškol|univerzit|vysok.*škol|výzkumn", "skola_vyzkumna_org"),
    (r"podnikatel|firm|s\.r\.o|a\.s\.|MSP|právnick.*osob", "firma"),
]


def cz_iso(s):
    m = re.match(r"\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s or "")
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def kw(text, table, multi=False):
    t = (text or "").lower()
    out = []
    for pat, val in table:
        if re.search(pat, t, re.I):
            out.append(val)
            if not multi:
                return [val]
    return list(dict.fromkeys(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("--source", required=True, help="host (irop.gov.cz)")
    ap.add_argument("--platform", default="kentico")
    ap.add_argument("--poskytovatel", default="ministerstvo")
    ap.add_argument("--zdroj", default="eu_fondy")
    ap.add_argument("--out", default="data/opportunities.jsonl")
    ap.add_argument("--today", default="2026-06-05")
    a = ap.parse_args()
    today = _pd(a.today) or date.today()

    seen = set()
    if os.path.exists(a.out):
        for l in open(a.out, encoding="utf-8"):
            try: seen.add(json.loads(l).get("id"))
            except Exception: pass

    recs, dup = [], 0
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
        oblast = kw(title, OBLAST_KW, multi=True) or ["bydleni_infrastruktura"]  # IROP default = infrastruktura
        typz = kw(r.get("eligible"), TYP_KW, multi=True)
        rec = {
            "kind": "grant", "source": a.source, "source_url": url,
            "title": title, "focus_area": None, "open_from": of, "deadline": dl,
            "status": st, "status_confidence": conf, "amount": None,
            "eligible_applicants": r.get("eligible"), "required_attachments": [],
            "how_to_apply": None, "source_doc": url, "id": gid,
            "facets": {
                "oblast": oblast, "typ_zadatele": typz, "sektor_zadatele": [],
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

    written = 0
    with open(a.out, "a", encoding="utf-8") as o:
        for r in recs:
            if r["id"] in seen:
                dup += 1; continue
            seen.add(r["id"]); o.write(json.dumps(r, ensure_ascii=False) + "\n"); written += 1
    from collections import Counter
    print(json.dumps({"MARKER": "INGEST_KENTICO", "source": a.source, "written": written,
                      "dedup": dup, "by_status": dict(Counter(r["status"] for r in recs)),
                      "by_oblast": dict(Counter(o for r in recs for o in r["facets"]["oblast"]))},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
