#!/usr/bin/env python3
"""Vrstva 2 pro MK ČR (mk.gov.cz; harvester scripts/mk_harvest.py).

DETERMINISTICKÁ extrakce — MK publikuje výzvy v HTML tabulkách centrálního listingu
`zadosti-o-dotace-cs-2023` (8 tabulek per oblast), kde jsou PŘÍJEM ŽÁDOSTÍ OD / DO
strukturovaně v buňkách. Harvester je už rozparsoval (open_from/deadline/open_from_raw/…),
takže tady se NIC nehádá:

  • open_from/deadline = přímo z tabulky (raw buňky zůstávají v evidence)
  • status              = NEVYPLŇUJE SE (počítá kód: ingest_rich → compute_status)
  • oblast              = mapa MK oblasti (heading tabulky) → raw facet label pro consolidate.py
  • how_to_apply        = sloupec ZPŮSOB PODÁNÍ (+ standardní věta o Dotačním portálu MK)
  • amount              = null (alokace ani strop na žadatele nejsou v listingu; bývají až
                          v PDF vyhlašovacích podmínek → nehalucinujeme)
  • eligible_applicants = null (tamtéž) — vyplní se jen když to PDF říká jednou větou (níž)
  • evidence            = doslovná citace z těla detailu NEBO z textu přílohy (grounding)

Join: `data/mk_in/grant_NN.json` (build_extract_input) ↔ `data/mk_documents.jsonl` podle `id`
(= url záznamu, tj. detail URL + fragment programu). Basename se zachovává → ingest_rich spáruje.

Spuštění (z kořene repa, po build_extract_input):
  python scripts/build_extract_input.py data/mk_documents.jsonl --source mk --out-dir data/mk_in --force-type grant
  python data/_mk_extract.py
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import glob
import json
import os
import re

IN_DIR, OUT_DIR = "data/mk_in", "data/mk_out"
HARVEST = "data/mk_documents.jsonl"

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]

# MK heading oblasti (sloupec `area` z listingu) → RAW facet label; kanon dopočítá consolidate.py.
AREA_OBLAST = {
    "Profesionální umění": ["kultura"],
    "Literatura a knihovny": ["kultura", "literatura"],
    "Muzea a galerie": ["kultura", "kulturní dědictví"],
    "Kulturní dědictví": ["kulturní dědictví"],
    "Regionální a národnostní kultura": ["kultura", "komunitní rozvoj"],
    "Mezinárodní spolupráce": ["kultura", "mezinárodní spolupráce"],
    "Média a audiovize": ["média"],
    "Církve a náboženské společnosti": ["náboženství"],
}

HOW_BASE = ("Žádost se podává v dotačním řízení Ministerstva kultury ve lhůtě uvedené ve vyhlášení "
            "programu; podmínky a formuláře jsou ve vyhlašovacích podmínkách konkrétního programu.")

CZ_MONTHS = ["ledna", "února", "března", "dubna", "května", "června",
             "července", "srpna", "září", "října", "listopadu", "prosince"]


def date_variants(iso):
    """ISO datum → možné české zápisy v textu (kvůli hledání doslovné citace)."""
    if not iso or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", iso):
        return []
    y, m, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
    return [f"{d}. {m}. {y}", f"{d}.{m}.{y}", f"{d}. {m}.{y}", f"{d:02d}.{m:02d}.{y}",
            f"{d}. {CZ_MONTHS[m - 1]} {y}"]


def find_quote(texts, needles, width=220):
    """Najdi v textech větu obsahující některý z `needles` → doslovná citace pro evidence."""
    for text in texts:
        if not text:
            continue
        for n in needles:
            i = text.find(n)
            if i < 0:
                continue
            start = max(0, text.rfind("\n", 0, i), text.rfind(". ", max(0, i - width), i))
            seg = text[start:i + len(n) + 90]
            seg = re.sub(r"\s+", " ", seg).strip(" .;\n")
            if len(seg) >= 15:
                return seg[:280]
    return None


def load_harvest():
    by_id = {}
    for line in open(HARVEST, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            by_id[r.get("url")] = r
    return by_id


def att_texts(rec):
    out = []
    for a in rec.get("attachments") or []:
        p = a.get("txt_path")
        if p and os.path.exists(p):
            try:
                out.append(open(p, encoding="utf-8", errors="replace").read())
            except Exception:  # noqa: BLE001
                pass
    return out


def build(rec, src):
    """rec = záznam z mk_documents.jsonl, src = odpovídající data/mk_in/grant_NN.json."""
    title = (rec.get("title") or "").strip()
    area = rec.get("area")
    body = src.get("body") or rec.get("body_text") or ""
    docs = att_texts(rec)
    texts = [body] + docs

    ev = {}
    q = find_quote(texts, [title[:60]]) if title else None
    if q:
        ev["title"] = q
    for field, iso, raw in (("deadline", rec.get("deadline"), rec.get("deadline_raw")),
                            ("open_from", rec.get("open_from"), rec.get("open_from_raw"))):
        q = find_quote(texts, date_variants(iso)) if iso else None
        if q:
            ev[field] = q
        elif raw:                       # citace z tabulky listingu (raw buňka) — grounding v datech zdroje
            ev[field] = raw
    # výzva/vyhlašovací podmínky jako source_doc (první PDF přílohy detailu)
    src_doc = None
    for a in rec.get("attachments") or []:
        if (a.get("ext") or "").lower() == "pdf":
            src_doc = a.get("url")
            break

    how = HOW_BASE
    if rec.get("submission"):
        how = f"Způsob podání dle vyhlášení: {rec['submission']}. " + HOW_BASE

    return {
        "title": title,
        "focus_area": (f"Dotační (výběrové) řízení Ministerstva kultury ČR v oblasti "
                       f"„{area}“." if area else "Dotační řízení Ministerstva kultury ČR."),
        "oblast": AREA_OBLAST.get(area, ["kultura"]),
        "open_from": rec.get("open_from"),
        "deadline": rec.get("deadline"),
        "castky": [],
        "vyse_hlavni_czk": None,          # alokace/strop nejsou v listingu → null, nehádá se
        "spoluucast": None,
        "eligible_applicants": None,      # jen v PDF podmínek → vrstva 2 by hádala; null
        "typ_zadatele": [],
        "cilova_skupina": [],
        "region": CR,
        "forma_podpory": ["dotace"],
        "zdroj_financovani": ["narodni_rozpocet"],
        "rezim_prijmu": "kolova" if rec.get("deadline") else "neuvedeno",
        "delka": None,
        "how_to_apply": how,
        "required_attachments": [],
        "source_doc": src_doc or rec.get("detail_url"),
        "poskytovatel": "Ministerstvo kultury ČR",
        "mk_oblast": area,
        "evidence": ev,
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for p in glob.glob(os.path.join(OUT_DIR, "grant_*.json")):
        os.remove(p)
    by_id = load_harvest()
    n, skipped = 0, 0
    for path in sorted(glob.glob(os.path.join(IN_DIR, "grant_*.json"))):
        src = json.load(open(path, encoding="utf-8"))
        rec = by_id.get(src.get("id"))
        if not rec or rec.get("kind") != "vyzva":
            skipped += 1          # listing stránka / nespárováno → NEzapisuj out (ingest ji vynechá)
            continue
        f = build(rec, src)
        json.dump(f, open(os.path.join(OUT_DIR, os.path.basename(path)), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
    print(f"wrote {n} grants -> {OUT_DIR}/ (skipped {skipped}: listing/nespárováno)")


if __name__ == "__main__":
    main()
