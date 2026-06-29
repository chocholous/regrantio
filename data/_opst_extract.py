#!/usr/bin/env python3
# Vrstva 2 extrakce pro OP Spravedlivá transformace 2021–2027 (opst.cz; parser scripts/opst.py).
# Stejný front-end blok jako OPŽP (Druh výzvy / Podání žádosti od-do / Alokace / Popis) → stejné
# deterministické parsování. Liší se OBLAST (transformace, ne SC 1.x) a REGION (cílené na 3 uhelné
# kraje → kraj facet z názvu). Status NEvyplňuji (kód z deadline). zdroj=eu_fondy, typ=ministerstvo.
import json, os, re

HOW = ("Žádost se podává elektronicky přes IS KP21+ (MS2021+). Oprávnění žadatelé a podmínky se řídí "
       "Pravidly pro žadatele a příjemce a textem konkrétní výzvy OP Spravedlivá transformace.")
D = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")
# uhelné kraje OP ST → kraj facet (název v titulku/perexu výzvy)
KRAJE = [("moravskoslezsk", "Moravskoslezský kraj"), ("ústeck", "Ústecký kraj"), ("usteck", "Ústecký kraj"),
         ("karlovarsk", "Karlovarský kraj")]
KW = [(r"rekvalifik|vzděl[áa]v|dovednost|zam[ěe]stnan", ["vzdělávání", "zaměstnanost"]),
      (r"podnik|MSP|startup|start-up|inovac|výzkum|vývoj", ["podnikání a inovace", "věda a výzkum"]),
      (r"brownfield|revitaliz|sanac|rekultivac", ["brownfieldy", "regenerace území"]),
      (r"energetik|obnoviteln|fotovolt|teplárenstv|vod[íi]k", ["čistá energetika"]),
      (r"ob[ěe]hov|odpad|recyklac", ["oběhové hospodářství"]),
      (r"univerzit|vouchery", ["věda a výzkum"])]


def field(body, label):
    lines = body.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == label or ln.strip().startswith(label):
            for nx in lines[i + 1:i + 3]:
                if nx.strip():
                    return nx.strip()
    return ""


def regions(title, perex):
    t = (title + " " + perex).lower()
    found = []
    for key, name in KRAJE:
        if key in t and name not in found:
            found.append(name)
    if not found:
        return [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
    multi = len(found) > 1
    return [{"nazev": n, "obec": None, "okres": None, "kraj": n, "celostatni": False} for n in found] or \
           [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]


def main():
    recs = [json.loads(l) for l in open("data/opst_documents.jsonl", encoding="utf-8")]
    os.makedirs("data/opst_out", exist_ok=True)
    for i, r in enumerate(recs):
        b = r.get("body_text", "")
        title = r.get("title", "").strip()
        m = re.search(re.escape(title) + r"\s*\n(.+?)\nStav v[ýy]zvy", b, re.S)
        perex = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        pod = field(b, "Podání žádosti") or field(b, "Podan")
        dts = D.findall(pod)
        open_from = f"{dts[0][2]}-{int(dts[0][1]):02d}-{int(dts[0][0]):02d}" if len(dts) >= 1 else None
        deadline = f"{dts[1][2]}-{int(dts[1][1]):02d}-{int(dts[1][0]):02d}" if len(dts) >= 2 else None
        druh = field(b, "Druh výzvy").lower()
        rezim = "kolova" if "kolov" in druh else ("prubezna" if "průb" in druh or "prub" in druh else "jednorazova_vyzva")
        am = None
        ma = re.search(r"Alokace\s*\n\s*([\d   ]+)\s*K[čc]", b)
        if ma:
            s = re.sub(r"\D", "", ma.group(1))
            am = int(s) if s else None
        oblast = ["spravedlivá transformace", "regionální rozvoj"]
        ctx = (perex + " " + title + " " + b).lower()
        for pat, obs in KW:
            if re.search(pat, ctx):
                for o in obs:
                    if o not in oblast:
                        oblast.append(o)
        reg = regions(title, perex)
        opatr = re.search(r"(Opat[řr]en[íi][^\n]{0,160}|Specifick[ýé] c[íi]l[^\n]{0,160})", b)
        focus = perex or (re.sub(r"\s+", " ", opatr.group(1)).strip() if opatr else
                          f"Výzva {title} – OP Spravedlivá transformace (Fond pro spravedlivou transformaci).")
        cv = re.match(r"(\d+)\.\s*v[ýy]zva", title)
        ev = {"title": title[:80]}
        if deadline and pod:
            ev["deadline"] = re.sub(r"\s+", " ", pod)[:50]
        if am and ma:
            ev["vyse_hlavni_czk"] = re.sub(r"\s+", " ", ma.group(0))[:40]
        f = {
            "title": title, "oblast": oblast, "focus_area": focus[:600],
            "open_from": open_from, "deadline": deadline,
            "castky": [{"typ": "alokace", "hodnota": am}] if am else [],
            "vyse_hlavni_czk": am, "spoluucast": True,
            "eligible_applicants": ("Oprávnění žadatelé dle Pravidel pro žadatele a příjemce a textu konkrétní "
                                    "výzvy OP ST (typicky obce, kraje, podnikatelé, výzkumné a vzdělávací "
                                    "instituce a neziskové subjekty v uhelných regionech dle zaměření výzvy)."),
            "typ_zadatele": [], "cilova_skupina": [], "region": reg,
            "forma_podpory": ["dotace"], "zdroj_financovani": ["eu_fondy"],
            "rezim_prijmu": rezim, "delka": None,
            "how_to_apply": HOW, "required_attachments": [], "source_doc": r.get("url"),
            "cislo_vyzvy": (f"{cv.group(1)}. výzva OP ST" if cv else None),
            "evidence": ev,
        }
        json.dump(f, open(f"data/opst_out/grant_{i:02d}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"wrote {len(recs)} grants to data/opst_out/")


if __name__ == "__main__":
    main()
