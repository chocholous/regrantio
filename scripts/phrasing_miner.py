#!/usr/bin/env python3
"""Vytěží z korpusu (wp_full + vismo dokumenty) REÁLNÉ FORMULACE, jak se mluví
o grantových polích (deadline / amount / eligible / how_to_apply). Výstup =
ranked trigger-fráze → materiál pro lepší Haiku prompt (synonyma + few-shot).
"""
import json, re, glob, os
from collections import Counter

# kontextová slova = pole se o nich bavi
DATE = r"\d{1,2}\.\s*\d{1,2}\.\s*20\d{2}"
SAMP = 4000  # kolik záznamů na soubor max (rychlost)

deadline_trig = Counter()   # fráze před datem v žádostním kontextu
amount_trig = Counter()
eligible_trig = Counter()
howto_trig = Counter()

# normalizace: zkrať na label-jádro
def norm(p):
    p = re.sub(r"\s+", " ", p).strip().lower()
    p = re.sub(r"^[\W\d]+", "", p)
    return p[-45:]

DEADLINE_CTX = re.compile(
    r"([\wáčďéěíňóřšťúůýž ]{6,40}?)\s*(?::|\bdo\b)\s*" + DATE, re.I)
AMOUNT_LAB = re.compile(
    r"([\wáčďéěíňóřšťúůýž ]{4,35}?)\s*:?\s*(?:\d[\d  .]{2,}|[Aa]lokac|[Mm]íra)\s*(?:Kč|mil|%|korun)", re.I)
ELIG_LAB = re.compile(
    r"\b(opráv\w+ žadatel\w*|žadatel\w*\s+(?:o (?:dotaci|podporu)\s+)?je|žadatelem\s+(?:o\s+\w+\s+)?(?:může být|je)|příjemc\w+\s+(?:podpory|dotace)\s+(?:je|jsou|může)|o (?:dotaci|podporu|grant)\s+mohou žádat|způsobil\w+ žadatel\w*)", re.I)
HOWTO_LAB = re.compile(
    r"\b(žádost\w*\s+(?:se\s+)?(?:podáv\w+|lze podat|musí být)|podání žádost\w+|žádost\w*\s+je\s+(?:možné|nutno)|způsob podání)", re.I)
DLWORD = re.compile(r"žádost|podán|příjm|příjem|lhůt|termín|uzávěr", re.I)


def harvest(text):
    for m in DEADLINE_CTX.finditer(text):
        lab = m.group(1)
        if DLWORD.search(lab):
            deadline_trig[norm(lab)] += 1
    for m in AMOUNT_LAB.finditer(text):
        amount_trig[norm(m.group(1))] += 1
    for m in ELIG_LAB.finditer(text):
        eligible_trig[norm(m.group(1))] += 1
    for m in HOWTO_LAB.finditer(text):
        howto_trig[norm(m.group(1))] += 1


n = 0
# wp_full grant-bearing zdroje
for f in glob.glob("data/wp_full/*.jsonl"):
    web = os.path.basename(f).split("__")[0]
    if not re.search(r"dotacni|opjak|opzp|opst|sfzp|tacr|gacr|nsa|mzd|nadace|narodniprogramzp|pgrlf|crr", web):
        continue
    if os.path.getsize(f) == 0:
        continue
    for i, line in enumerate(open(f, encoding="utf-8")):
        if i >= SAMP:
            break
        try:
            r = json.loads(line)
        except Exception:
            continue
        _t = r.get("title"); _t = _t if isinstance(_t, str) else r.get("title_text")  # nové kanonické vs legacy wp_full snapshot (title=raw objekt)
        harvest((_t or "") + " " + (r.get("text") or r.get("content_text") or ""))
        n += 1
# vismo dokumenty + jejich přílohy text
if os.path.exists("data/vismo_documents.jsonl"):
    for line in open("data/vismo_documents.jsonl", encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        harvest(r.get("body_text", ""))
        for a in r.get("attachments", []):
            if a.get("text_excerpt"):
                harvest(a["text_excerpt"])
        n += 1

out = {
    "n_records": n,
    "deadline_phrasings": deadline_trig.most_common(25),
    "amount_phrasings": amount_trig.most_common(20),
    "eligible_phrasings": eligible_trig.most_common(20),
    "howto_phrasings": howto_trig.most_common(15),
}
json.dump(out, open("phrasing_mined.json", "w"), ensure_ascii=False, indent=1)
print(f"vytěženo z {n} záznamů\n")
for k in ("deadline_phrasings", "eligible_phrasings", "amount_phrasings", "howto_phrasings"):
    print(f"=== {k} ===")
    for p, c in out[k][:14]:
        if c >= 2 and len(p) > 3:
            print(f"  {c:5d}  {p}")
    print()
print("PHRASING_DONE")
