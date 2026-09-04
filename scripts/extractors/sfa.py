#!/usr/bin/env python3
# Vrstva 2 extrakce pro Státní fond audiovize (sfa.gov.cz, dříve Fond kinematografie; parser scripts/sfa.py).
# 1 foundation_mission + 7 otevřených/nedávno uzavřených výzev (okruh B Televizní díla, D Infrastruktura).
# grant_00 → mission_00. Pozn.: Vyzva-PDF mají pdftotext poškozenou diakritiku → evidence (title/deadline)
# z čistého HTML body parseru; focus/eligible vyplněny, ale z PDF se necitují (byly by none).
import json, os, shutil

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
ELIG = "Výrobci, koproducenti, případně distributoři českých audiovizuálních děl s místem podnikání, trvalého pobytu nebo sídlem na území ČR."
HOW = "Žádost se podává na předepsaném formuláři Státního fondu audiovize a prostřednictvím webového formuláře v dané lhůtě; podpora je selektivní (rozhoduje příslušná rada)."
B = "https://sfa.gov.cz/vyzvy/"
out_grant, out_mission = {}, {}

def vyzva(idx, code, area_n, name, oblast, focus, deadline, dl_quote, cil):
    out_grant[f"grant_{idx:02d}"] = {
     "title": f"{code} {name}",
     "oblast": oblast, "focus_area": focus,
     "open_from": None, "deadline": deadline,
     "deadliny": [{"datum": deadline, "kontext": dl_quote}],
     "obdobi_realizace": "rok 2026",
     "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
     "eligible_applicants": ELIG,
     "typ_zadatele": ["firma", "osvc_podnikatel", "neziskovka", "fyzicka_osoba"],
     "cilova_skupina": cil,
     "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
     "rezim_prijmu": "jednorazova_vyzva", "delka": "jednoleta",
     "how_to_apply": HOW, "required_attachments": [],
     "cislo_vyzvy": code, "source_doc": f"{B}{area_n}#{code}",
     "kontakt": {"osoba": None, "email": "info@sfa.gov.cz", "telefon": None},
     "evidence": {"title": f"{code} {name}", "deadline": dl_quote}}

FILM = ["film a audiovize", "kultura"]
PROD = ["filmoví tvůrci", "producenti", "veřejnost"]
DIST = ["distributoři", "filmoví tvůrci", "diváci"]
vyzva(1, "2026-B-2-3-39", 2, "Výroba dokumentárního díla", FILM,
      "Podpora výroby českých dokumentárních televizních děl (krátkometrážních i celovečerních, dokumentárních minisérií 2–4 díly nebo seriálů 5–13 dílů).",
      "2026-07-15", "do 15. 7. 2026", PROD)
vyzva(2, "2026-B-2-4-40", 2, "Výroba hraného seriálu nebo minisérie", FILM,
      "Podpora výroby českých hraných televizních seriálů nebo minisérií.",
      "2026-07-15", "do 15. 7. 2026", PROD)
vyzva(3, "2026-B-1-3-34", 2, "Kompletní vývoj dokumentárního díla", FILM,
      "Podpora kompletního vývoje českých dokumentárních audiovizuálních děl (příprava před výrobou).",
      "2026-06-05", "do 5. 6. 2026", PROD)
vyzva(4, "2026-D-3-5-41", 4, "Distribuční projekty – práce s publikem", FILM,
      "Podpora distribučních projektů zaměřených na práci s publikem a rozvoj filmového diváctví.",
      "2026-07-27", "do 27. 7. 2026", DIST)
vyzva(5, "2026-D-5-5-47", 4, "Účast českých audiovizuálních děl na mezinárodních festivalech nebo při nominaci na ceny", FILM,
      "Podpora účasti českých audiovizuálních děl na mezinárodních festivalech nebo při nominaci na mezinárodní ceny.",
      "2026-09-30", "do 30. 9. 2026", DIST)
vyzva(6, "2026-D-3-6-46", 4, "Distribuce filmu", FILM,
      "Podpora distribuce filmů (průběžná výzva pro distribuci českých audiovizuálních děl).",
      "2026-09-30", "do 30. 9. 2026", DIST)
vyzva(7, "2026-D-5-1-1", 4, "Účast českých audiovizuálních děl na mezinárodních festivalech", FILM,
      "Podpora účasti českých audiovizuálních děl na mezinárodních festivalech (předchozí výzva).",
      "2026-03-31", "do 31. 3. 2026", DIST)

out_mission["mission_00"] = {
 "name": "Státní fond audiovize",
 "mission": "Veřejný fond podle zákona č. 496/2012 Sb., o audiovizi; podporuje českou audiovizi v celé šíři – od vývoje a výroby audiovizuálních děl po jejich distribuci, dále filmové festivaly, technický rozvoj kin, propagaci, vzdělávání a filmové publikace. Podpora je selektivní, rozhodují čtyři odborné rady.",
 "support_topics": ["vývoj a výroba filmů", "televizní díla", "animace a videohry", "distribuce", "filmové festivaly", "kina a infrastruktura", "filmové pobídky", "vzdělávání a publikace"],
 "cilova_skupina": ["filmoví tvůrci", "producenti", "distributoři", "kina", "veřejnost"],
 "regions": ["Česká republika"],
 "forma_podpory": ["dotace", "filmové pobídky"],
 "jak_oslovit": "O podporu se žádá v rámci vyhlašovaných výzev ve čtyřech okruzích (A Kinematografie, B Televizní díla, C Animace & Videohry, D Infrastruktura); o podpoře rozhodují čtyři rady.",
 "kontakt": {"osoba": None, "email": "info@sfa.gov.cz", "telefon": None},
 "source_doc": "https://sfa.gov.cz/podpora-audiovize",
 "evidence": {
   "name": "Státní fond audiovize",
   "mission": "Český stát si uvědomuje potřebu podporovat českou audiovizi, a to v její plné šíři od vývoje a výroby audiovizuálních děl po jejich distribuci.",
   "jak_oslovit": "O podpoře rozhodují čtyři rady, rada pro podporu kinematografie, rada pro podporu televizních děl, rada pro podporu animovaných děl a videoher a rada pro podporu infrastruktury."}}

os.makedirs("data/sfa_out", exist_ok=True)
shutil.copyfile("data/sfa_in/grant_00.json", "data/sfa_in/mission_00.json")
for k, v in out_grant.items():
    json.dump(v, open(f"data/sfa_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in out_mission.items():
    json.dump(v, open(f"data/sfa_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out_grant), "grants +", len(out_mission), "mission to data/sfa_out/")
