#!/usr/bin/env python3
# Vrstva 2 extrakce pro EHP a Norské fondy (eeagrants.cz; data data/eeagrants.jsonl → vyčištěno do
# data/eeagrants_documents.jsonl). 26 individuálních výzev programového období Finančního mechanismu
# EHP/Norsko 2014–2021 (NKM = Ministerstvo financí). Období skončilo (poslední výzvy 2024) → většinou
# closed; deadline parsován z těla, open_from z „vyhlašuje dne …". zdroj=ehp_norsko (kanon). Status kód.
import json, os, re

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW = ("Žádost o grant se podávala elektronicky dle podmínek výzvy; zprostředkovatelem programu je "
       "Ministerstvo financí ČR (Národní kontaktní místo pro EHP a Norské fondy).")
AREA_TYP = {"Výzkum": ["skola_vyzkumna_org"], "Vzdělávání": ["skola_vyzkumna_org", "neziskovka"]}
AREA_CIL = {
    "Lidská práva": ["ohrožené skupiny", "oběti domácího násilí", "Romové", "veřejnost"],
    "Kultura": ["veřejnost", "umělci", "kulturní instituce"],
    "Zdraví": ["pacienti", "veřejnost"], "Životní prostředí": ["veřejnost", "obce"],
    "Spravedlnost": ["osoby ve výkonu trestu", "veřejnost"],
    "Řádná správa": ["občané", "veřejnost"], "Výzkum": ["výzkumní pracovníci"],
    "Vzdělávání": ["studenti", "školy"], "Občanská společnost": ["neziskové organizace", "veřejnost"],
    "Sociální dialog": ["zaměstnanci", "sociální partneři"], "Vnitřní věci": ["veřejnost"],
}
MONTHS = None
DATE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")


def iso(s):
    m = DATE.search(s or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def title_clean(t):
    t = re.sub(r"^(VÝZVA UKONČENA:|AKTUALIZACE:?|UKONČENO:)\s*", "", t, flags=re.I).strip()
    t = re.split(r"\s*\(otevřena do", t)[0].strip(" -–|")
    return t[:140]


def focus_of(b, title):
    for pat in (r"(Cílem[^.]{20,260}\.)", r"(Jejím cílem[^.]{20,260}\.)",
                r"(Z výzvy[^.]{20,260}\.)", r"(Podporováno[^.]{20,260}\.)"):
        m = re.search(pat, b)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
    return title


def main():
    recs = [json.loads(l) for l in open("data/eeagrants_documents.jsonl", encoding="utf-8")]
    os.makedirs("data/eeagrants_out", exist_ok=True)
    for i, r in enumerate(recs):
        b = r.get("body_text", "")
        area = r.get("_area", "")
        title = title_clean(r.get("title", ""))
        of = re.search(r"vyhlašuje[^.]{0,50}?dne\s*(\d{1,2}\.\s*\d{1,2}\.\s*20\d\d)", b)
        open_from = iso(of.group(1)) if of else None
        deadline = iso(r.get("_deadline")) if r.get("_deadline") else None
        if not deadline:
            dl = re.search(r"(otevřena do|uzávěrk[^.]{0,30}?|žádostí do|do)\s*(\d{1,2}\.\s*\d{1,2}\.\s*20\d\d)", b, re.I)
            deadline = iso(dl.group(2)) if dl else None
        if not deadline:
            # výzva z ukončeného období 2014–2021; přesné datum není v textu, ale ROK je v URL →
            # konzervativní year-end (status closed je jistý, nehádám konkrétní den).
            ym = re.search(r"/(?:vyzvy|aktuality)/(20\d\d)/", r.get("url", ""))
            if ym:
                deadline = f"{ym.group(1)}-12-31"
        f = {
            "title": f"EHP/Norské fondy – {area}: {title}" if area else title,
            "oblast": [area, "mezinárodní spolupráce"] if area else ["mezinárodní spolupráce"],
            "focus_area": focus_of(b, title),
            "open_from": open_from, "deadline": deadline,
            "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
            "eligible_applicants": ("Oprávnění žadatelé dle podmínek konkrétní výzvy programu "
                                    f"{area} (zpravidla neziskové organizace, instituce, obce či kraje "
                                    "a další subjekty; viz text výzvy)."),
            "typ_zadatele": AREA_TYP.get(area, ["neziskovka", "prispevkova_organizace", "obec_verejny_subjekt"]),
            "cilova_skupina": AREA_CIL.get(area, ["veřejnost"]),
            "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["ehp_norsko"],
            "rezim_prijmu": "jednorazova_vyzva", "delka": "viceleta",
            "how_to_apply": HOW, "required_attachments": [], "source_doc": r.get("url"),
            "cislo_vyzvy": "EHP/Norsko 2014–2021",
            "evidence": {"title": title[:80],
                         **({"deadline": r.get("_deadline")} if r.get("_deadline") else {}),
                         **({"open_from": of.group(1)} if of else {})},
        }
        json.dump(f, open(f"data/eeagrants_out/grant_{i:02d}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"wrote {len(recs)} grants to data/eeagrants_out/")


if __name__ == "__main__":
    main()
