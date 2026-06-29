#!/usr/bin/env python3
# Vrstva 2 extrakce pro Nadaci Partnerství (nadacepartnerstvi.cz, parser scripts/partnerstvi.py).
# grant_00 = Sázíme budoucnost 2026 (do 100 tis.) → 1 open grant; grant_01 = o-nas → mission_00.
# Žádosti přes systém Grantys (www.nap.grantys.cz). Uzávěrka 31.7.2026 → status open.
import json, os, shutil

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
out_grant, out_mission = {}, {}

# --- grant_00: Sázíme budoucnost 2026: granty do 100 tisíc ---
out_grant["grant_00"] = {
 "title": "Sázíme budoucnost 2026: granty do 100 tisíc",
 "oblast": ["životní prostředí", "krajina", "adaptace na změnu klimatu"],
 "focus_area": "Výsadby stromů a keřů a další adaptační opatření ve volné (nelesní, nezastavěné) krajině: obnova polních cest, tvorba travních pásů a mezí, úprava drobných vodních toků/studánek/pramenů, opatření pro zasakování vody, následná péče po dobu 3 let. Cílem je zmírnění teplotních extrémů, zadržování vody, zvýšení biodiverzity.",
 "open_from": "2026-05-18", "deadline": "2026-07-31",
 "deadliny": [{"datum": "2026-07-31", "kontext": "Uzávěrka příjmu žádostí 31. 7. 2026 23:59 (vyhlášení 18. 5. 2026, výsledky 17. 9. 2026)."}],
 "obdobi_realizace": "1. 9. – 31. 12. 2026",
 "castky": [{"typ": "max_zadatel", "hodnota": 100000, "kontext": "Až 50 tis. Kč na výsadby stromů a keřů (priorita A) + až 50 tis. Kč na další adaptační opatření (priorita B); max. 100 000 Kč na projekt (neinvestiční výdaje)."}],
 "vyse_hlavni_czk": 100000, "spoluucast": None,
 "eligible_applicants": "Pouze právnické osoby: spolky, ústavy, obecně prospěšné společnosti, církevní právnické osoby, příspěvkové organizace, společenství vlastníků jednotek, družstva, nadace a nadační fondy, školské právnické osoby, obce a svazky obcí, veřejné výzkumné instituce.",
 "typ_zadatele": ["neziskovka", "obec_verejny_subjekt", "prispevkova_organizace", "skola_vyzkumna_org"],
 "cilova_skupina": ["právnické osoby pečující o krajinu", "obce", "spolky a komunity"],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["vlastni_zdroje"],
 "rezim_prijmu": "jednorazova_vyzva", "delka": "jednoleta",
 "how_to_apply": "Žádost se podává výhradně elektronicky v online systému Grantys na www.nap.grantys.cz: žadatel vybere grantovou výzvu „Sázíme budoucnost: granty do 100 000 Kč“, vyplní formulář žádosti a rozpočet a vloží povinné přílohy (bez nich nebude žádost přijata).",
 "required_attachments": ["vyplněný formulář žádosti v systému Grantys", "rozpočet projektu", "povinné přílohy žádosti dle výzvy (v elektronické podobě)"],
 "cislo_vyzvy": None,
 "source_doc": "https://www.nadacepartnerstvi.cz/sazime-budoucnost-granty-do-100-tisic-2026",
 "kontakt": {"osoba": None, "email": None, "telefon": None},
 "evidence": {
   "title": "Sázíme budoucnost 2026: granty do 100 tisíc",
   "castky": "Získejte až 50 tisíc korun na výsadby stromů a keřů a dalších až 50 tisíc korun na další adaptační opatření ve volné krajině",
   "eligible_applicants": "Oprávněnými žadateli jsou pouze právnické osoby",
   "deadline": "uzávěrka příjmu žádostí: 31. 7. 2026 23:59",
   "how_to_apply": "Žádost se podává výhradně elektronicky a vyplňuje v online systému Grantys na www.nap.grantys.cz"}}

# --- foundation_mission (o-nas → mission_00) ---
out_mission["mission_00"] = {
 "name": "Nadace Partnerství",
 "mission": "Největší česká environmentální nadace. Podstatou práce je spojovat a vytvářet partnerství mezi všemi, kterým záleží na zdravé budoucnosti Česka a Evropy; finančně podporuje, vzdělává a pomáhá lidem a komunitám, aby převzali zodpovědnost za péči o životní prostředí, místní rozvoj a kvalitu života.",
 "support_topics": ["výsadby stromů a péče o krajinu", "adaptace na změnu klimatu", "zadržování vody v krajině", "místní rozvoj a komunity", "udržitelná turistika", "environmentální vzdělávání"],
 "cilova_skupina": ["obce a města", "spolky a neziskové organizace", "komunity a místní lídři", "právnické osoby pečující o přírodu"],
 "regions": ["Česká republika"],
 "forma_podpory": ["dotace"],
 "jak_oslovit": "Finančně podporuje projekty prostřednictvím grantových výzev (žádosti v online systému Grantys), vedle toho vzdělává a propojuje místní lídry. Součást mezinárodního konsorcia Environmental Partnership Association (EPA).",
 "kontakt": {"osoba": None, "email": None, "telefon": None},
 "source_doc": "https://www.nadacepartnerstvi.cz/o-nas",
 "evidence": {
   "mission": "Tvoříme partnerství pro přírodu. Finančně podporujeme, vzděláváme a pomáháme lidem a komunitám",
   "support_topics": "Podstatou naší práce je spojovat."}}

os.makedirs("data/partnerstvi_out", exist_ok=True)
shutil.copyfile("data/partnerstvi_in/grant_01.json", "data/partnerstvi_in/mission_00.json")
for k, v in out_grant.items():
    json.dump(v, open(f"data/partnerstvi_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in out_mission.items():
    json.dump(v, open(f"data/partnerstvi_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out_grant), "grant +", len(out_mission), "mission to data/partnerstvi_out/")
