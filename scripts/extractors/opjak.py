#!/usr/bin/env python3
# Vrstva 2 extrakce pro OP JAK 2021–2027 (opjak.cz; parser scripts/opjak.py). 8 aktuálních EU výzev MŠMT
# (vzdělávání + výzkum/vývoj). Deterministicky: název+kód · datumové rozpětí (ČESKÁ jména měsíců) ·
# Celková alokace · perex/cíl. Konec rozpětí = deadline příjmu (potvrzeno countdownem „Zbývá N dní").
# Status NEvyplňuji (kód z deadline). zdroj=eu_fondy, typ=ministerstvo.
import json, os, re

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW = ("Žádost se podává elektronicky přes IS KP21+ (MS2021+). Oprávnění žadatelé a podmínky se řídí "
       "Pravidly pro žadatele a příjemce a textem konkrétní výzvy OP JAK.")
MONTHS = {"ledna": 1, "února": 2, "unora": 2, "března": 3, "brezna": 3, "dubna": 4, "května": 5,
          "kvetna": 5, "června": 6, "cervna": 6, "července": 7, "cervence": 7, "srpna": 8,
          "září": 9, "zari": 9, "října": 10, "rijna": 10, "listopadu": 11, "prosince": 12}
MN = "|".join(MONTHS)
DRANGE = re.compile(r"(\d{1,2})\.\s*(" + MN + r")\s*(20\d\d)\s*-\s*(\d{1,2})\.\s*(" + MN + r")\s*(20\d\d)")
KW = [(r"MSCA|Fellowship|Teaming|Open Science|[šs]pi[čc]kov[ýé] v[ýy]zkum|excelen|v[ýy]zkum|v[ěe]da", ["věda a výzkum"]),
      (r"MAP|ak[čc]n[íi] pl[áa]nov|Smart Akceler|vzd[ěe]l[áa]v|[šs]kol|pedagog|u[čc]itel", ["vzdělávání"]),
      (r"\bAI\b|umě[ll][áé] inteligenc|digit", ["digitalizace"]),
      (r"Technick[áa] pomoc", ["technická pomoc"])]


def iso(d, mon, y):
    m = MONTHS.get(mon.lower())
    return f"{y}-{m:02d}-{int(d):02d}" if m else None


def main():
    recs = [json.loads(l) for l in open("data/opjak_documents.jsonl", encoding="utf-8")]
    os.makedirs("data/opjak_out", exist_ok=True)
    for i, r in enumerate(recs):
        b = r.get("body_text", "")
        title = re.sub(r"\s*-\s*OP JAK\s*$", "", r.get("title", "").strip())
        dr = DRANGE.search(b)
        open_from = iso(dr.group(1), dr.group(2), dr.group(3)) if dr else None
        deadline = iso(dr.group(4), dr.group(5), dr.group(6)) if dr else None
        am = None
        ma = re.search(r"Celkov[áa] alokace\s*\n\s*([\d   ]+)\s*mil\.\s*K[čc]", b)
        if ma:
            s = re.sub(r"\D", "", ma.group(1))
            am = int(s) * 1_000_000 if s else None
        # focus: perex po „Aktualizováno DATUM" nebo „Cíl výzvy"
        focus = None
        fm = re.search(r"C[íi]l v[ýy]zvy\s*\n([^\n]{40,400})", b)
        if not fm:
            fm = re.search(r"Aktualizov[áa]no[^\n]*\n([^\n]{40,400})", b)
        if fm:
            focus = re.sub(r"\s+", " ", fm.group(1)).strip()
        oblast = []
        ctx = (title + " " + b).lower()
        for pat, obs in KW:
            if re.search(pat, ctx, re.I):
                for o in obs:
                    if o not in oblast:
                        oblast.append(o)
        if not oblast:
            oblast = ["vzdělávání", "věda a výzkum"]
        code = re.search(r"\b(\d\d_\d\d_\d\d\d)\b", title)
        ev = {"title": title[:80]}
        if dr:
            ev["deadline"] = re.sub(r"\s+", " ", dr.group(0))
        if am and ma:
            ev["vyse_hlavni_czk"] = re.sub(r"\s+", " ", ma.group(0))[:40]
        f = {
            "title": title,
            "oblast": oblast,
            "focus_area": focus or f"Výzva {title} – OP Jan Amos Komenský 2021–2027 (MŠMT).",
            "open_from": open_from, "deadline": deadline,
            "castky": [{"typ": "alokace", "hodnota": am}] if am else [],
            "vyse_hlavni_czk": am, "spoluucast": True,
            "eligible_applicants": ("Oprávnění žadatelé dle Pravidel pro žadatele a příjemce a textu konkrétní "
                                    "výzvy OP JAK (dle zaměření: vysoké školy a výzkumné organizace, školy a "
                                    "jejich zřizovatelé, kraje/MAS, organizační složky státu)."),
            "typ_zadatele": [], "cilova_skupina": [], "region": CR,
            "forma_podpory": ["dotace"], "zdroj_financovani": ["eu_fondy"],
            "rezim_prijmu": "prubezna", "delka": None,
            "how_to_apply": HOW, "required_attachments": [], "source_doc": r.get("url"),
            "cislo_vyzvy": (f"{code.group(1)} (OP JAK)" if code else None),
            "evidence": ev,
        }
        json.dump(f, open(f"data/opjak_out/grant_{i:02d}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"wrote {len(recs)} grants to data/opjak_out/")


if __name__ == "__main__":
    main()
