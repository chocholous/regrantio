#!/usr/bin/env python3
# Vrstva 2 extrakce pro MPSV (mpsv.gov.cz; parser scripts/mpsv.py). 11 reálných výzev z 19 vstupů:
#   národní dotační tituly (00 Rodina 2026, 05 sociální služby nadregionální, 17 Bílá stuha) — čistý body
#   OPZ+ investiční výzvy 31_xx (06–13) — tělo tenké, detail v PDF (pdftotext porušil diakritiku → evidence
#   jen z čistého body = title; alokace/lhůty z PDF do polí, ne do citací).
# VYNECHÁNO (nezapisuje se → ingest passne): 01 Výzvy (hub), 02 Národní dotační tituly (hub),
#   03 Rodina a ochrana práv dětí (policy overview), 04 Sociální práce (oblast hub),
#   14 samospráva stárnutí (zrušeno 2020), 15 Rodina-NNO (rok-index hub = 00), 16 Ukrajina (hub výzev),
#   18 restituce církevního majetku (Zásady, administrativní metodika). Status NEvyplňuji (počítá kód).
import json, os

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW_OK_R = "Žádost se podává elektronicky prostřednictvím aplikace OK služby rodina."
HOW_OK_P = "Žádost se zpracuje a podá elektronicky prostřednictvím aplikace OK služby poskytovatel."
HOW_ISKP = "Žádost se podává elektronicky v aplikaci IS KP14+/IS KP21+ (portál MS2014+/MS2021+)."
SOC_PROV = ["neziskovka", "obec_verejny_subjekt", "prispevkova_organizace"]
SOC_CIL = ["osoby se zdravotním postižením", "senioři", "osoby v nepříznivé sociální situaci"]

out = {}
def g(idx, **f):
    out[f"grant_{idx:02d}"] = f

# ---- národní dotační tituly (čistý body) ---------------------------------------------
g(0, title="Dotační řízení Rodina pro rok 2026 (podpora rodiny pro nestátní neziskové organizace)",
  oblast=["sociální", "rodina"],
  focus_area="Neinvestiční dotace nestátním neziskovým organizacím na podporu rodiny v Národním dotačním titulu Rodina pro rok 2026.",
  open_from="2025-10-14", deadline="2025-11-10",
  castky=[{"typ": "max_zadatel", "hodnota": 3000000}], vyse_hlavni_czk=3000000, spoluucast=True,
  eligible_applicants="Nestátní neziskové organizace (spolky a pobočné spolky, obecně prospěšné společnosti, ústavy, církve a církevní právnické osoby, nadace a nadační fondy).",
  typ_zadatele=["neziskovka"], cilova_skupina=["rodiny", "děti"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="jednoleta", how_to_apply=HOW_OK_R, cislo_vyzvy="NDT Rodina 2026",
  evidence={"title": "dotačního titulu na podporu rodiny", "deadline": "Termín pro podávání žádostí je stanoven od 14.10.2025 – do 10.11.2025", "vyse_hlavni_czk": "na jeden projekt lze nárokovat pouze 3 000 000 Kc"})

g(5, title="Dotační řízení MPSV pro rok 2026 v oblasti poskytování sociálních služeb s nadregionální či celostátní působností",
  oblast=["sociální"],
  focus_area="Dotace ze státního rozpočtu poskytovatelům sociálních služeb s nadregionálním či celostátním charakterem (zařazení do Sítě B pro rok 2027) podle zákona o sociálních službách.",
  open_from=None, deadline="2026-06-30",
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Právnické a fyzické osoby, které poskytují sociální služby s nadregionální či celostátní působností (poskytovatelé sociálních služeb).",
  typ_zadatele=["neziskovka", "prispevkova_organizace", "firma", "fyzicka_osoba"],
  cilova_skupina=["osoby závislé na pomoci", "senioři", "osoby se zdravotním postižením"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="jednoleta", how_to_apply=HOW_OK_P, cislo_vyzvy="sociální služby nadregionální 2026",
  dalsi_datumy=[{"datum": "2026-01-30", "popis": "termín pro podání žádosti přes OK služby poskytovatel"}, {"datum": "2026-08-31", "popis": "hodnocení žádostí"}],
  evidence={"title": "dotační řízení v oblasti poskytování sociálních služeb s nadregionální či celostátní působností", "deadline": "Termín pro podání žádostí je stanoven do 30. června 2026", "eligible_applicants": "pro právnické a fyzické osoby, které poskytují sociální služby"})

g(17, title="Dotace na podporu obcím oceněným titulem Bílá stuha v soutěži Vesnice roku 2025",
  oblast=["rodina", "sociální", "regionální rozvoj"],
  focus_area="Neinvestiční dotace obcím oceněným titulem Bílá stuha (Vesnice roku 2025) na opatření v oblasti rodinné a proseniorské politiky a primární prevence.",
  open_from="2025-09-08", deadline="2025-11-07",
  castky=[{"typ": "max_zadatel", "hodnota": 800000}], vyse_hlavni_czk=800000, spoluucast=True,
  eligible_applicants="Pouze obce oceněné titulem Bílá stuha v krajském kole soutěže Vesnice roku 2025 (jedna žádost na žadatele).",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["rodiny s dětmi", "senioři", "děti a mládež"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="jednoleta", how_to_apply="Žádost se podává v dotačním řízení odboru rodinné politiky, ochrany dětí a sociálního začleňování MPSV.",
  cislo_vyzvy="Bílá stuha 2025",
  evidence={"title": "Podpora obcím oceněným titulem Bílá stuha v soutěži Vesnice roku 2025", "deadline": "Možnost podávat žádosti o neinvestiční dotace bude otevřena od 8. září do 7. listopadu 2025", "vyse_hlavni_czk": "ve výši max. 800 tis. Kč"})

# ---- OPZ+ investiční výzvy 31_xx (ESF+; lhůty/alokace z PDF) ---------------------------
def opz(idx, num, title, oblast, focus, deadline, alokace, vmax, vmin, realiz, typ=None, cil=None):
    g(idx, title=title, oblast=oblast, focus_area=focus,
      open_from=None, deadline=deadline,
      castky=[c for c in [{"typ": "alokace", "hodnota": alokace} if alokace else None,
                          {"typ": "max_zadatel", "hodnota": vmax} if vmax else None,
                          {"typ": "min_zadatel", "hodnota": vmin} if vmin else None] if c],
      vyse_hlavni_czk=vmax or alokace, spoluucast=True,
      eligible_applicants="Poskytovatelé sociálních služeb dle zákona č. 108/2006 Sb. (nestátní neziskové organizace i subjekty veřejného sektoru – obce, kraje, jimi zřizované organizace).",
      typ_zadatele=typ or SOC_PROV, cilova_skupina=cil or SOC_CIL, region=CR,
      forma_podpory=["dotace"], zdroj_financovani=["eu_fondy"],
      rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW_ISKP, cislo_vyzvy=num,
      dalsi_datumy=[{"datum": realiz, "popis": "nejzazší datum ukončení realizace projektu"}] if realiz else [],
      evidence={"title": title})

opz(6, "31_22_019", "Výzva č. 31_22_019 – Nákup nízkoemisních vozidel pro sociální služby",
    ["sociální", "doprava"], "Nákup nízkoemisních vozidel (elektromobily, plug-in hybridy) pro poskytovatele ambulantních a terénních sociálních služeb (OPZ+).",
    None, 228000000, 5360000, 250000, "2024-04-30")
opz(7, "31_23_066", "Výzva č. 31_23_066 – Nákup nízkoemisních vozidel pro sociální služby II",
    ["sociální", "doprava"], "Nákup nízkoemisních vozidel pro ambulantní a terénní sociální služby – II. výzva (OPZ+), max. 5 vozidel na projekt.",
    None, None, 5360000, 250000, "2024-11-15")
opz(8, "31_22_003", "Výzva č. 31_22_003 – Rozvoj a modernizace materiálně technické základny sociálních služeb",
    ["sociální", "infrastruktura"], "Rozvoj a modernizace materiálně technické základny sociálních služeb (OPZ+); dotace 10–80 mil. Kč na projekt.",
    "2025-06-30", None, 80000000, 10000000, "2025-08-31")
opz(9, "31_22_043", "Výzva č. 31_22_043 – Zvyšování kapacit nepobytových komunitních sociálních služeb",
    ["sociální", "infrastruktura"], "Zvyšování kapacit nepobytových komunitních sociálních služeb (OPZ+); pro veřejný sektor 1–30 mil. Kč.",
    "2024-07-31", 1000000000, 30000000, 1000000, "2025-10-31")
opz(10, "31_22_044", "Výzva č. 31_22_044 – Modernizace a rozvoj pobytových služeb sociální péče",
    ["sociální", "infrastruktura"], "Modernizace a rozvoj pobytových služeb sociální péče (OPZ+); pro veřejný sektor 5–80 mil. Kč.",
    None, 4824000000, 80000000, 5000000, "2025-12-31")
opz(11, "31_24_108", "Výzva č. 31_24_108 – Zvyšování kapacit služeb sociálního poradenství a služeb sociální prevence",
    ["sociální"], "Zvyšování kapacit služeb sociálního poradenství a sociální prevence (OPZ+); 1–30 mil. Kč na projekt.",
    "2024-09-02", 750000000, 30000000, 1000000, "2026-04-30")
opz(12, "31_24_138", "Výzva č. 31_24_138 – Modernizace a rozvoj pobytových služeb sociální péče II",
    ["sociální", "infrastruktura"], "Modernizace a rozvoj pobytových služeb sociální péče – II. výzva (OPZ+).",
    "2025-06-30", 750000000, None, None, "2026-04-30")
opz(13, "31_24_140", "Výzva č. 31_24_140 – Zvyšování kapacit sociálního poradenství, sociální prevence a nepobytových služeb péče",
    ["sociální"], "Zvyšování kapacit sociálního poradenství, sociální prevence a nepobytových služeb péče (OPZ+).",
    "2026-06-30", 1000000000, None, None, "2026-06-30")

os.makedirs("data/mpsv_out", exist_ok=True)
for k, v in out.items():
    json.dump(v, open(f"data/mpsv_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} grants to data/mpsv_out/ (skipped 8 hubs/overviews/cancelled pages)")
