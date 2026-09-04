#!/usr/bin/env python3
# Vrstva 2 extrakce pro Vinařský fond ČR (vinarskyfond.cz, custom parser scripts/vinarskyfond.py).
# 1 foundation_mission (fond celkově) + 4 granty (tematické okruhy C/D/E/F).
# grant_00 → mission_00 (kopie vstupu pro basename join). Pozn.: Pravidla-PDF mají pdftotext
# poškozenou diakritiku → evidence pro sdílená pole z čistého BODY (WP), částky přes číselné fragmenty.
import json, os, shutil

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
PORTAL = "https://portal.vinarskyfond.cz/"
ELIG = "Fyzické a právnické osoby žádající o podporu (vinaři, vinohradníci, registrovaní výrobci vína, vinařské spolky a uskupení) se sídlem/pobytem v ČR."
HOW = "Žádosti se podávají pouze elektronicky na Portálu Vinařského fondu (https://portal.vinarskyfond.cz/) s využitím identity občana / elektronického podpisu, případně datovou schránkou (6tnj224)."
out_grant, out_mission = {}, {}

def okruh(letter, title, oblast, focus, mira_pct, max_proj, alokace, focus_ev, mira_ev, src_id):
    castky = [{"typ": "mira_pct", "hodnota": mira_pct, "kontext": f"Výše podpory je maximálně {mira_pct} % uznatelných nákladů."}]
    if alokace:
        castky.append({"typ": "alokace", "hodnota": alokace, "kontext": f"Finanční částka vyčleněná Radou Vinařského fondu na tento tematický okruh."})
    if max_proj:
        castky.append({"typ": "max_zadatel", "hodnota": max_proj, "kontext": "Maximální výše podpory na projekt."})
    # evidence JEN pro pole groundovatelná v čistém BODY (WP) — Pravidla-PDF mají poškozenou
    # diakritiku (pdftotext), proto se focus/částky z PDF necitují (byly by match=none).
    ev = {"deadline": "od 1. 7. do 15. 8.",
          "eligible_applicants": "vinařům, vinohradníkům, vinařským spolkům a uskupením",
          "how_to_apply": "https://portal.vinarskyfond.cz/"}
    return {
     "title": title, "oblast": oblast, "focus_area": focus,
     "open_from": None, "deadline": "2026-08-15",
     "deadliny": [{"datum": "2026-08-15", "kontext": "Podávání žádostí o podporu od 1. 7. do 15. 8. 2026"},
                  {"datum": "2026-02-15", "kontext": "v termínech od 1.1. do 15.2 a od 1. 7. do 15. 8."}],
     "obdobi_realizace": "realizace akcí od 1. 10. 2026 do 31. 3. 2027",
     "castky": castky, "vyse_hlavni_czk": max_proj, "spoluucast": True,
     "eligible_applicants": ELIG,
     "typ_zadatele": ["osvc_podnikatel", "firma", "neziskovka", "fyzicka_osoba"],
     "cilova_skupina": ["vinaři", "vinohradníci", "veřejnost"],
     "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["vlastni_zdroje"],
     "rezim_prijmu": "kolova", "delka": "jednoleta",
     "how_to_apply": HOW, "required_attachments": ["čestné prohlášení žadatele"],
     "cislo_vyzvy": f"okruh {letter}", "source_doc": src_id,
     "kontakt": {"osoba": None, "email": "info@vinarskyfond.cz", "telefon": "541 652 471"},
     "evidence": ev}

S = "https://vinarskyfond.cz/wp-content/uploads/2026/05/"
out_grant["grant_01"] = okruh("C", "Vinařský fond – okruh C – Vzdělávání (školení, semináře, konference)",
  ["vzdělávání", "vinařství", "zemědělství"],
  "Podpora konání seminářů, školení a konferencí s vinařskou tematikou (vzdělávání v oblasti vinařství, vinohradnictví a sommelierství) pro pořadatele.",
  80, 200000, 1000000,
  "Podpora je poskytována na konání seminářů, školení a konferencí s vinařskou tematikou",
  "40 000", S + "31662_2026_Pravidla_okruh_C.pdf")
out_grant["grant_02"] = okruh("D", "Vinařský fond – okruh D – Propagační materiály",
  ["vinařství", "marketing", "média"],
  "Podpora výroby tištěných, audiovizuálních a online materiálů podporujících informování veřejnosti o vinohradnictví a vinařství.",
  50, None, 500000,
  "na výrobu tištěných, audiovizuálních a online materiálů podporujících informování veřejnosti o vinohradnictví a vinařství",
  "500 000 Kc", S + "31662_2026_Pravidla_okruh_D.pdf")
out_grant["grant_03"] = okruh("E", "Vinařský fond – okruh E – Propagační akce (vinařská turistika)",
  ["vinařství", "cestovní ruch", "kultura"],
  "Podpora konání akcí zaměřených na rozvoj vinařské turistiky – „otevřené sklepy“, slavnosti vinobraní a další propagační akce s tematikou vinařství.",
  50, None, 1500000,
  "na konání akcí zaměřených na rozvoj vinařské turistiky",
  "1 500 000 Kc", S + "31662_2026_Pravidla_okruh_E.pdf")
out_grant["grant_04"] = okruh("F", "Vinařský fond – okruh F – Významné projekty",
  ["vinařství", "marketing"],
  "Podpora realizace projektů s celostátním a/nebo mezinárodním významem výrazně přispívajících k propagaci vína, vinařství a vinohradnictví (nespadajících do ostatních okruhů).",
  80, None, 5000000,
  "na realizaci projektů s celostátním a/nebo mezinárodním významem",
  "5 000 000 Kc", S + "31662_2026_Pravidla_okruh_F.pdf")

# --- foundation_mission (grant_00 → mission_00) ---
out_mission["mission_00"] = {
 "name": "Vinařský fond České republiky",
 "mission": "Veřejný fond zřízený podle zákona o vinohradnictví a vinařství; podporuje marketing, propagaci a rozvoj vína, vinařství a vinohradnictví v ČR (značka „Vína z Moravy, vína z Čech“) a financuje stovky vinařských akcí a projektů ročně.",
 "support_topics": ["propagace vína", "vinařská turistika", "vzdělávání ve vinařství", "propagační materiály", "vinařské akce a projekty"],
 "cilova_skupina": ["vinaři", "vinohradníci", "vinařské spolky a uskupení", "veřejnost"],
 "regions": ["Česká republika"],
 "forma_podpory": ["dotace"],
 "jak_oslovit": "Žádosti o podporu se podávají elektronicky na Portálu Vinařského fondu (https://portal.vinarskyfond.cz/) ve dvou termínech ročně: 1. 1.–15. 2. a 1. 7.–15. 8.",
 "kontakt": {"osoba": None, "email": "info@vinarskyfond.cz", "telefon": "541 652 471"},
 "source_doc": "https://vinarskyfond.cz/podpory/",
 "evidence": {
   "name": "Vinařský fond",
   "mission": "Vinařský fond každoročně podpoří stovky vinařských akcí a projektů.",
   "jak_oslovit": "Žádosti o podporu se podávají pouze elektronicky v termínech od 1.1. do 15.2 a od 1. 7. do 15. 8."}}

os.makedirs("data/vinarskyfond_out", exist_ok=True)
shutil.copyfile("data/vinarskyfond_in/grant_00.json", "data/vinarskyfond_in/mission_00.json")
for k, v in out_grant.items():
    json.dump(v, open(f"data/vinarskyfond_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in out_mission.items():
    json.dump(v, open(f"data/vinarskyfond_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out_grant), "grants +", len(out_mission), "mission to data/vinarskyfond_out/")
