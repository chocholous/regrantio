#!/usr/bin/env python3
# Vrstva 2 extrakce pro Hlávkovu nadaci (hlavkovanadace.cz, custom parser scripts/hlavka.py).
# 1 foundation_mission (program_2026) + 3 granty (nujh / cena / pokyny-příspěvky).
# grant_01 (program_2026) → mission_01 (kopie vstupu, aby ingest_rich napároval basename).
import json, os, shutil

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
B = "https://www.hlavkovanadace.cz/"
out_grant, out_mission = {}, {}

# --- foundation_mission (program_2026 → mission_01) ---
out_mission["mission_01"] = {
 "name": "Nadání Josefa, Marie a Zdeňky Hlávkových (Hlávkova nadace)",
 "mission": "Podporovat vědecké, literární a umělecké snahy českého národa, přispívat k uspokojování jeho kulturních potřeb a podporovat potřebné a nadané studující na českých veřejných vysokých školách v souladu s poslední vůlí Josefa Hlávky.",
 "support_topics": ["věda a výzkum", "literatura", "umění", "vzdělávání", "podpora studentů", "český jazyk a kulturní tradice", "národní hospodářství"],
 "cilova_skupina": ["studenti veřejných vysokých škol", "mladí vědečtí pracovníci", "umělci", "badatelé"],
 "regions": ["Česká republika"],
 "forma_podpory": ["stipendium", "dotace", "cena_soutez"],
 "jak_oslovit": "Žádost o nadační příspěvek se podává osobně, poštou nebo e-mailem do administrace Nadání (Vodičkova 17, Praha 1); o přiznání rozhoduje správní rada na pravidelných schůzích.",
 "kontakt": {"osoba": "PhDr. Dagmar Rýdlová", "email": "josefhlavka@volny.cz", "telefon": "224 947 686"},
 "source_doc": B + "program_2026.php",
 "evidence": {
   "name": "Nadání Josefa, Marie a Zdeňky Hlávkových",
   "mission": "posláním Nadání je podporovat vědecké, literární a umělecké snahy českého národa, přispívat k uspokojování jeho kulturních potřeb a podporovat potřebné a nadané studující na českých veřejných vysokých školách v souladu s vůlí zakladatele Nadání"}}

# --- grant: Veřejná soutěž NÚJH 2026 (nujh_2026 → grant_00) ---
out_grant["grant_00"] = {
 "title": "Veřejná soutěž o nadační příspěvky (stipendia) Národohospodářského ústavu Josefa Hlávky 2026",
 "oblast": ["věda a výzkum", "národní hospodářství", "společenské vědy"],
 "focus_area": "Individuální nadační příspěvky (stipendia) na vytvoření nebo dokončení původních badatelských prací o českém národním hospodářství a jeho historických i společenských souvislostech; hlavní téma 2026 „Současné proměny a kontexty vývoje české společnosti a české národní zájmy ve 21. století“.",
 "open_from": None, "deadline": "2026-05-15",
 "deadliny": [{"datum": "2026-05-15", "kontext": "Termín zaslání přihlášek je do 15.5.2026"}],
 "obdobi_realizace": "rok 2026",
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": "Všichni badatelé (s případnými spolupracovníky), kteří prokáží svou erudici a schopnost v dané oblasti vědecky pracovat; příležitost mohou dostat i mladí uchazeči s menším počtem publikovaných prací.",
 "typ_zadatele": ["fyzicka_osoba", "skola_vyzkumna_org"], "cilova_skupina": ["badatelé", "vědci"],
 "region": CR, "forma_podpory": ["stipendium"], "zdroj_financovani": ["vlastni_zdroje"],
 "rezim_prijmu": "jednorazova_vyzva", "delka": "jednoleta",
 "how_to_apply": "Přihlášku (návrh tématu, popis přístupu, struktura a rozsah studie, životopis, seznam prací, požadovaná výše příspěvku) zaslat poštou nebo doručit osobně na adresu Nadace, Národohospodářský ústav, Vodičkova 17, 110 00 Praha 1, do 15. 5. 2026.",
 "required_attachments": ["návrh zvoleného tématu", "popis přístupu k řešení", "struktura a rozsah studie", "seznam publikovaných prací", "kopie poslední úspěšné studie", "požadovaná výše příspěvku"],
 "cislo_vyzvy": None, "source_doc": B + "nujh_2026.php",
 "kontakt": {"osoba": "PhDr. Dagmar Rýdlová", "email": "josefhlavka@volny.cz", "telefon": "224 947 686"},
 "evidence": {
   "title": "Veřejná soutěž o získání nadačních příspěvků (stipendií) Národohospodářského ústavu Josefa Hlávky v roce 2026",
   "deadline": "Termín zaslání přihlášek je do 15.5.2026",
   "eligible_applicants": "Podpora je určena všem badatelům (s případnými spolupracovníky), kteří prokáží svou erudici a schopnost v dané oblasti vědecky pracovat.",
   "focus_area": "k vytvoření nebo dokončení původních badatelských prací, které překračují rámec již dosažených poznatků o českém národním hospodářství"}}

# --- grant (cena): Cena Josefa Hlávky za vědeckou literaturu 2025/2026 (cena_2026 → grant_02) ---
out_grant["grant_02"] = {
 "title": "Cena Josefa Hlávky za vědeckou literaturu za rok 2025 (udělovaná v roce 2026)",
 "oblast": ["věda a výzkum", "literatura"],
 "focus_area": "Cena za původní knižní práci z oblasti vědecké a odborné literatury publikovanou v ČR v hodnoceném roce, ve čtyřech vědních oblastech: společenské vědy, vědy o neživé přírodě, vědy o živé přírodě a lékařské vědy.",
 "open_from": None, "deadline": "2026-02-06",
 "deadliny": [{"datum": "2026-02-06", "kontext": "Návrhy na ocenění (včetně 1 výtisku publikace) může zaslat každá právnická i fyzická osoba do 6. února 2026"}],
 "obdobi_realizace": "slavnostní předání v červnu 2026 na zámku v Lužanech",
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": "Návrh na ocenění může podat každá právnická i fyzická osoba (oceňováni jsou autoři původní vědecké knižní práce vydané v ČR).",
 "typ_zadatele": ["fyzicka_osoba", "neziskovka", "skola_vyzkumna_org"], "cilova_skupina": ["autoři vědecké literatury"],
 "region": CR, "forma_podpory": ["cena_soutez"], "zdroj_financovani": ["vlastni_zdroje"],
 "rezim_prijmu": "jednorazova_vyzva", "delka": "jednoleta",
 "how_to_apply": "Návrhy (včetně 1 výtisku publikace) zaslat do 6. 2. 2026 Nadaci Český literární fond (přes Zásilkovnu nebo osobně na NČLF, Pod Nuselskými schody 3, Praha 2); cena se uděluje společně s Nadáním J., M. a Z. Hlávkových.",
 "required_attachments": ["1 výtisk publikace"],
 "cislo_vyzvy": None, "source_doc": B + "cena_2026.php",
 "evidence": {
   "title": "Ceny Josefa Hlávky za vědeckou literaturu za rok 2025 udělované v roce 2026",
   "deadline": "může zaslat každá právnická i fyzická osoba do 6. února 2026",
   "focus_area": "Cena je udělována za původní knižní práci z oblasti vědecké a odborné literatury publikovanou v České republice v hodnoceném kalendářním roce, a to ve čtyřech vědních oblastech",
   "eligible_applicants": "Návrhy na ocenění (včetně 1 výtisku publikace) může zaslat každá právnická i fyzická osoba"}}

# --- grant: Nadační příspěvky / stipendia (pokyny_2026 → grant_03; rolling, rozhoduje správní rada) ---
out_grant["grant_03"] = {
 "title": "Nadační příspěvky a stipendia Nadání Josefa, Marie a Zdeňky Hlávkových (2026)",
 "oblast": ["věda a výzkum", "umění", "vzdělávání"],
 "focus_area": "Nadační příspěvky ve formě vědeckého, uměleckého, cestovního, doktorského a sociálního studijního stipendia pro výjimečné jednotlivce – studenty a mladé vědecké pracovníky a umělce (zpravidla do 5 let po absolvování VŠ, max. do 33 let).",
 "open_from": None, "deadline": "průběžně",
 "deadliny": [{"datum": "2026-09-07", "kontext": "Schůze správní rady 2026: 23. února, 27. dubna, 15. června, 7. září, 19. října, 14. prosince; přijímání žádostí končí deset dní před datem konání správní rady."}],
 "obdobi_realizace": "rok 2026",
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": "Vynikající jednotlivci z veřejných a státních vysokých škol a dalších institucí v působnosti MŠMT ČR a z Akademie věd ČR (nikoli instituce nebo kolektivy); u stipendií zpravidla do 5 let po absolvování VŠ, maximálně do věku 33 let.",
 "typ_zadatele": ["fyzicka_osoba"], "cilova_skupina": ["studenti vysokých škol", "mladí vědečtí pracovníci", "umělci"],
 "region": CR, "forma_podpory": ["stipendium", "dotace"], "zdroj_financovani": ["vlastni_zdroje"],
 "rezim_prijmu": "prubezna", "delka": "jednoleta",
 "how_to_apply": "Žádost o přiznání nadačního příspěvku přinést osobně do administrace Nadání (Vodičkova 17, Praha 1, schodiště č. 3, 2. patro), zaslat poštou nebo e-mailem; přijímání žádostí končí deset dní před datem konání správní rady.",
 "required_attachments": [],
 "cislo_vyzvy": None, "source_doc": B + "pokyny_2026.php",
 "kontakt": {"osoba": "dr. Rýdlová", "email": None, "telefon": "224 947 691"},
 "evidence": {
   "title": "Pokyny pro žadatele o nadační příspěvek",
   "deadline": "Přijímání žádostí končí deset dní před datem konání správní rady.",
   "how_to_apply": "Žádost o přiznání nadačního příspěvku může žadatel přinést osobně do administrace Nadání (Vodičkova 17, Praha 1, schodiště č. 3, 2. patro) nebo zaslat poštou, případně e-mailem."}}

os.makedirs("data/hlavka_out", exist_ok=True)
# mission: zkopíruj vstup grant_01 → mission_01 (aby ingest_rich.src_idx našel basename)
shutil.copyfile("data/hlavka_in/grant_01.json", "data/hlavka_in/mission_01.json")
for k, v in out_grant.items():
    json.dump(v, open(f"data/hlavka_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in out_mission.items():
    json.dump(v, open(f"data/hlavka_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out_grant), "grants +", len(out_mission), "mission to data/hlavka_out/")
