#!/usr/bin/env python3
# Vrstva 2 extrakce pro Nadaci Veronica (nadace.veronica.cz, parser scripts/veronica.py).
# 1 foundation_mission + 1 grant (Společně pro přírodu) — oba ze stránky ziskej-grant.php.
# grant_00 → mission_00 (kopie vstupu pro basename join).
import json, os, shutil

MS = [{"nazev": "Morava a Slezsko", "obec": None, "okres": None, "kraj": None, "celostatni": False}]
B = "https://nadace.veronica.cz"
out_grant, out_mission = {}, {}

out_grant["grant_00"] = {
 "title": "Společně pro přírodu (grantový program Nadace Veronica)",
 "oblast": ["prostředí", "příroda a krajina", "komunitní rozvoj"],
 "focus_area": "Granty pro ekologické projekty zvyšující sounáležitost lidí s místy, kde žijí, zájem o ochranu přírody a klimatu, posilování komunitních vztahů zapojováním veřejnosti a zvyšování kvality životního prostředí.",
 "open_from": None, "deadline": "průběžně",
 "deadliny": [{"datum": "2026-03-13", "kontext": "Nejbližší uzávěrka pro příjem žádostí; příspěvky se udělují dvakrát ročně (březen/duben, září/říjen)."}],
 "obdobi_realizace": None,
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": "Jednotlivci, týmy i organizace z Moravy a ze Slezska.",
 "typ_zadatele": ["fyzicka_osoba", "neziskovka", "obec_verejny_subjekt"],
 "cilova_skupina": ["veřejnost", "místní komunity"],
 "region": MS, "forma_podpory": ["dotace", "zapujcka_uver"], "zdroj_financovani": ["vlastni_zdroje"],
 "rezim_prijmu": "prubezna", "delka": "jednoleta",
 "how_to_apply": "Žádosti se přijímají během celého roku a zasílají elektronicky; o udělení příspěvku rozhoduje správní rada nadace dvakrát ročně (březen/duben, září/říjen).",
 "required_attachments": [], "cislo_vyzvy": None,
 "source_doc": B + "/page/ziskej-grant.php",
 "evidence": {
   "title": "program Společně pro přírodu",
   "focus_area": "Cílem programu je zvyšování sounáležitosti lidí s místy, kde žijí, povzbuzení k jejich vlastní aktivitě a zájmu o ochranu přírody a klimatu, posilování komunitních vztahů zapojováním veřejnosti a zvyšování kvality životního prostředí.",
   "eligible_applicants": "O příspěvek mohou žádat jednotlivci, týmy i organizace z Moravy a ze Slezska."}}

out_mission["mission_00"] = {
 "name": "Nadace Veronica",
 "mission": "Největší moravská nadace zaměřená na ochranu přírody, krajiny a životního prostředí; od roku 2008 pravidelně uděluje granty pro ekologické projekty v rámci programu Společně pro přírodu (dříve Společně pro Brno).",
 "support_topics": ["ochrana přírody", "ochrana krajiny", "životní prostředí", "ochrana klimatu", "ekologické projekty", "komunitní aktivity"],
 "cilova_skupina": ["jednotlivci", "týmy", "organizace", "místní komunity", "veřejnost"],
 "regions": ["Morava a Slezsko"],
 "forma_podpory": ["dotace", "zapujcka_uver"],
 "jak_oslovit": "O grant z programu Společně pro přírodu mohou žádat jednotlivci, týmy i organizace z Moravy a Slezska; nadace rozděluje i další nadační příspěvky a půjčky pro jednorázové projekty na základě rozhodnutí správní rady.",
 "kontakt": {"osoba": None, "email": None, "telefon": None},
 "source_doc": B + "/page/ziskej-grant.php",
 "evidence": {
   "mission": "je největší moravská nadace zaměřená na ochranu přírody, krajiny a životního prostředí",
   "jak_oslovit": "Od roku 2008 pravidelně udělujeme granty pro ekologické projekty v rámci programu Společně pro přírodu"}}

os.makedirs("data/veronica_out", exist_ok=True)
shutil.copyfile("data/veronica_in/grant_00.json", "data/veronica_in/mission_00.json")
for k, v in out_grant.items():
    json.dump(v, open(f"data/veronica_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in out_mission.items():
    json.dump(v, open(f"data/veronica_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out_grant), "grant +", len(out_mission), "mission to data/veronica_out/")
