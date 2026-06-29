#!/usr/bin/env python3
# Vrstva 2 extrakce pro OPŽP 2021–2027 (opzp.cz; parser scripts/opzp.py). 107 EU výzev (CPT call).
# Deterministicky z labelovaného front-end bloku: Druh výzvy / Podání žádosti od-do / Alokace / Popis
# (Specifický cíl + Opatření). Status NEvyplňuji (kód z deadline). zdroj=eu_fondy, typ_pos=ministerstvo.
import json, os, re

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW = ("Žádost se podává elektronicky přes IS KP21+ (MS2021+). Oprávnění žadatelé a podmínky se řídí "
       "Pravidly pro žadatele a příjemce a textem konkrétní výzvy.")
D = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")
# Specifický cíl 1.x → tematická oblast
SC_OBLAST = {
    "1.1": ["energetické úspory"], "1.2": ["obnovitelné zdroje energie"],
    "1.3": ["adaptace na změnu klimatu", "prevence rizik"],
    "1.4": ["vodní hospodářství", "vodovody a kanalizace"],
    "1.5": ["odpady", "oběhové hospodářství"],
    "1.6": ["příroda a biodiverzita", "ochrana ovzduší"],
}
KW = [(r"protipovod|povodn|sucho|adaptac|krajin|retenc|sesuv|svah", ["adaptace na změnu klimatu"]),
      (r"energetick[ýé] [úu]spor|zateplen|sn[íi]žen[íi] energetick", ["energetické úspory"]),
      (r"obnoviteln|fotovolt|tepeln[ée] [čc]erpadl|biometan", ["obnovitelné zdroje energie"]),
      (r"vodovod|kanalizac|[čc]ist[íi]rn|vodn[íi] zdroj|p[ií]tn[áa] voda", ["vodní hospodářství"]),
      (r"odpad|recyklac|ob[ěe]hov[ée]|skl[áa]dk", ["odpady", "oběhové hospodářství"]),
      (r"biodiverzit|[úu]zem[íi] soustavy natura|chr[áa]n[ěe]n[ée] [úu]zem|p[ée][čc]e o p[řr][íi]rod|druhov[ée] ochran", ["příroda a biodiverzita"]),
      (r"ovzduš|emis|zne[čc]i[šs]t[ěe]n", ["ochrana ovzduší"])]


def iso(s):
    m = D.search(s or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def field(body, label):
    """Hodnota = první neprázdný řádek za labelem."""
    lines = body.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == label or ln.strip().startswith(label):
            for nx in lines[i + 1:i + 3]:
                if nx.strip():
                    return nx.strip()
    return ""


def main():
    recs = [json.loads(l) for l in open("data/opzp_documents.jsonl", encoding="utf-8")]
    os.makedirs("data/opzp_out", exist_ok=True)
    n = 0
    for i, r in enumerate(recs):
        b = r.get("body_text", "")
        title = r.get("title", "").strip()
        # perex = text mezi názvem a „Stav výzvy"
        perex = ""
        m = re.search(re.escape(title) + r"\s*\n(.+?)\nStav v[ýy]zvy", b, re.S)
        if m:
            perex = re.sub(r"\s+", " ", m.group(1)).strip()
        # Podání žádosti: „D. M. YYYY - D. M. YYYY"
        pod = field(b, "Podání žádosti") or field(b, "Podan")
        dates = D.findall(pod)
        open_from = f"{dates[0][2]}-{int(dates[0][1]):02d}-{int(dates[0][0]):02d}" if len(dates) >= 1 else None
        deadline = f"{dates[1][2]}-{int(dates[1][1]):02d}-{int(dates[1][0]):02d}" if len(dates) >= 2 else None
        druh = field(b, "Druh výzvy").lower()
        rezim = "kolova" if "kolov" in druh else ("prubezna" if "průb" in druh or "prub" in druh else "jednorazova_vyzva")
        # Alokace
        am = None
        ma = re.search(r"Alokace\s*\n\s*([\d   ]+)\s*K[čc]", b)
        if ma:
            s = re.sub(r"\D", "", ma.group(1))
            am = int(s) if s else None
        # oblast: ze Specifického cíle + keywords
        oblast = ["životní prostředí"]
        sc = re.search(r"Specifick[ýé] c[íi]l\s*(\d\.\d)", b)
        if sc and sc.group(1) in SC_OBLAST:
            oblast += SC_OBLAST[sc.group(1)]
        ctx = (perex + " " + b).lower()
        for pat, obs in KW:
            if re.search(pat, ctx):
                for o in obs:
                    if o not in oblast:
                        oblast.append(o)
        opatr = re.search(r"(Opat[řr]en[íi][^\n]{0,160})", b)
        focus = perex or (re.sub(r"\s+", " ", opatr.group(1)).strip() if opatr else f"Výzva {title} Operačního programu Životní prostředí 2021–2027.")
        cv = re.match(r"(\d+)\.\s*v[ýy]zva", title)
        ev = {"title": title[:80]}
        if deadline and pod:
            ev["deadline"] = re.sub(r"\s+", " ", pod)[:50]
        if am and ma:
            ev["vyse_hlavni_czk"] = re.sub(r"\s+", " ", ma.group(0))[:40]
        f = {
            "title": title,
            "oblast": oblast,
            "focus_area": focus[:600],
            "open_from": open_from, "deadline": deadline,
            "castky": [{"typ": "alokace", "hodnota": am}] if am else [],
            "vyse_hlavni_czk": am, "spoluucast": True,
            "eligible_applicants": ("Oprávnění žadatelé dle Pravidel pro žadatele a příjemce a textu konkrétní "
                                    "výzvy OPŽP (typicky obce, kraje, organizace zřizované veřejnou správou, "
                                    "podnikatelské i neziskové subjekty dle zaměření specifického cíle)."),
            "typ_zadatele": [],
            "cilova_skupina": [], "region": CR,
            "forma_podpory": ["dotace"], "zdroj_financovani": ["eu_fondy"],
            "rezim_prijmu": rezim, "delka": None,
            "how_to_apply": HOW, "required_attachments": [], "source_doc": r.get("url"),
            "cislo_vyzvy": (f"{cv.group(1)}. výzva OPŽP" if cv else None),
            "evidence": ev,
        }
        json.dump(f, open(f"data/opzp_out/grant_{i:02d}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
    print(f"wrote {n}/{len(recs)} grants to data/opzp_out/")


if __name__ == "__main__":
    main()
