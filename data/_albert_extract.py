#!/usr/bin/env python3
# Vrstva 2 extrakce pro Nadační fond Albert (nadacnifondalbert.cz, parser scripts/albert.py).
# 2 granty (Bertík pomáhá 2027, Stipendijní grant 2026/2027) + 1 foundation_mission.
# Vstup: grant_00=stipendijni, grant_01=bertik, grant_02=about → mission_00.
import json, os, shutil

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
B = "https://www.nadacnifondalbert.cz"
KONT = {"osoba": "Barbora Veselá", "email": "barbora.vesela1@albert.cz", "telefon": "+420 601 199 975"}
out_grant, out_mission = {}, {}

# --- grant_00: Stipendijní grant 2026/2027 (informace/stipendijni-grant) ---
out_grant["grant_00"] = {
 "title": "Stipendijní grant 2026/2027 (Nadační fond Albert)",
 "oblast": ["vzdělávání", "sociální", "stipendia"],
 "focus_area": "Stipendium pro studenty VŠ a VOŠ z dětských domovů a neziskových organizací; podpora vzdělávání, osobního rozvoje a přechodu do samostatného života. Granty kryjí školné, ubytování, stravu, učebnice, IT pomůcky, cestovné, kurzy aj.",
 "open_from": "2026-05-18", "deadline": "2026-07-12",
 "deadliny": [{"datum": "2026-07-12", "kontext": "Konec příjmu žádostí (od 18. 5. 2026); výsledky do 10. 8. 2026."}],
 "obdobi_realizace": "akademický rok 2026/2027",
 "castky": [{"typ": "max_zadatel", "hodnota": 50000, "kontext": "Maximální výše grantu činí 50 000 Kč na žadatele/studenta."}],
 "vyse_hlavni_czk": 50000, "spoluucast": None,
 "eligible_applicants": "Studenti ve věku 18–26 let, kteří žijí v dětském domově nebo jsou klienty organizace pracující se sociálně ohroženými dětmi a rodinami a studují (či se hlásí na) VŠ nebo VOŠ.",
 "typ_zadatele": ["fyzicka_osoba"],
 "cilova_skupina": ["studenti", "mladí lidé z dětských domovů", "sociálně znevýhodnění"],
 "region": CR, "forma_podpory": ["stipendium", "dotace"], "zdroj_financovani": ["soukrome_zdroje"],
 "rezim_prijmu": "jednorazova_vyzva", "delka": "jednoleta",
 "how_to_apply": "Žádost podává student samostatně přes online systém na www.nadacnifondalbert.cz; do systému se přihlašuje pod zaregistrovaným dětským domovem nebo neziskovou organizací. Nutné doložit doklad o studiu, motivační dopis, doporučení a rozpočet.",
 "required_attachments": ["doklad o studiu (potvrzení/přihláška, výpis známek)", "motivační dopis", "doporučení z dětského domova nebo neziskové organizace", "rozpočet plánovaného využití stipendia"],
 "cislo_vyzvy": None,
 "source_doc": B + "/informace/stipendijni-grant",
 "kontakt": KONT,
 "evidence": {
   "title": "Tento grantový program je určen studentům a studentkám z dětských domovů a neziskových organizací, kteří studují vysokou školu nebo vyšší odbornou školu",
   "eligible_applicants": "Student*, který žije v dětském domově nebo je klientem organizace pracující se sociálně ohroženými dětmi a rodinami",
   "castky": "Maximální výše grantu činí 50 000 K",
   "deadline": "Žádost o nadační příspěvek se podává od 18. 5. 2026 do 12. 7. 2026"}}

# --- grant_01: Bertík pomáhá 2027 (informace/informace-pro-zadatele-bertik-pomaha) ---
out_grant["grant_01"] = {
 "title": "Bertík pomáhá 2027 (grantový program Nadačního fondu Albert)",
 "oblast": ["sociální", "vzdělávání", "děti a mládež"],
 "focus_area": "Podpora rozvoje, vzdělávání a péče o psychické zdraví dětí a mládeže ze sociálně ohroženého prostředí (ústavní/ochranná výchova, rizikové chování). Pět oblastí: individuální vzdělávací podpora do 26 let, programy přechodu do samostatného života, preventivní aktivity, psychoterapeutická pomoc, vzdělávání pracovníků.",
 "open_from": "2026-06-08", "deadline": "2026-07-22",
 "deadliny": [{"datum": "2026-07-22", "kontext": "Konec příjmu žádostí (od 8. 6. 2026, do půlnoci 22. 7. 2026)."}],
 "obdobi_realizace": "max. 12 měsíců, zahájení nejdříve 1. 1. 2027",
 "castky": [
   {"typ": "max_zadatel", "hodnota": 60000, "kontext": "Žadatel může podat žádost v maximální výši 60 000 Kč (max. dvě žádosti při více krajích/pobočkách)."},
   {"typ": "alokace", "hodnota": 5000000, "kontext": "Celková alokovaná výše grantového programu BERTÍK POMÁHÁ 2027 je 5 000 000 Kč."}],
 "vyse_hlavni_czk": 60000, "spoluucast": None,
 "eligible_applicants": "Neziskové a veřejně prospěšné organizace a také rozpočtové a příspěvkové organizace se sídlem v ČR, jejichž činnost je v souladu s posláním Nadačního fondu Albert.",
 "typ_zadatele": ["neziskovka", "obec_verejny_subjekt", "prispevkova_organizace"],
 "cilova_skupina": ["děti a mládež v ústavní a ochranné výchově", "děti a mládež s rizikovým chováním", "sociálně znevýhodněné děti"],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["soukrome_zdroje"],
 "rezim_prijmu": "jednorazova_vyzva", "delka": "jednoleta",
 "how_to_apply": "Žádost se vkládá výhradně elektronicky přes online systém na www.nadacnifondalbert.cz (registrace, přihlašovací jméno = IČ organizace). O výši podpory rozhodují zákazníci hlasováním v regionálně přiřazených prodejnách Albert (kampaň 14.–27. 10. 2026).",
 "required_attachments": ["žádost", "rozpočet"], "cislo_vyzvy": None,
 "source_doc": B + "/informace/informace-pro-zadatele-bertik-pomaha",
 "kontakt": KONT,
 "evidence": {
   "focus_area": "směřují k podpoře rozvoje, vzdělávání a péče o psychické zdraví dětí a mládeže ze sociálně ohroženého prostředí",
   "eligible_applicants": "Žádat mohou neziskové a veřejně prospěšné organizace a také rozpočtové a příspěvkové organizace",
   "castky": "může podat žádost v maximální výši 60 000 Kč",
   "deadline": "Žadatelé mohou podávat žádosti o nadační příspěvek od 8. 6. 2026 do 22. 7. 2026"}}

# --- foundation_mission (o-nadacnim-fondu-albert → mission_00) ---
out_mission["mission_00"] = {
 "name": "Nadační fond Albert",
 "mission": "Vznikl v roce 2009, aby zastřešil dlouhodobé charitativní aktivity obchodů Albert. Posláním je podpora zdravého životního stylu dětí i jejich rodičů a podpora vzdělávání, integrace a rozvoje dětí ze sociálně znevýhodněného prostředí.",
 "support_topics": ["vzdělávání a rozvoj sociálně znevýhodněných dětí", "psychické zdraví dětí a mládeže", "zdravý životní styl", "stipendia", "integrace dětí ze znevýhodněného prostředí"],
 "cilova_skupina": ["děti a mládež ze sociálně znevýhodněného prostředí", "děti v ústavní výchově", "studenti", "rodiny"],
 "regions": ["Česká republika"],
 "forma_podpory": ["dotace", "stipendium"],
 "jak_oslovit": "Získané finanční prostředky rozděluje prostřednictvím grantových výzev (Bertík pomáhá, Stipendijní grant) a realizuje vlastní projekty (Obchůdky s Albertem, Zdravá 5, materiální a potravinová pomoc).",
 "kontakt": {"osoba": "Barbora Veselá", "email": "barbora.vesela1@albert.cz", "telefon": "+420 601 199 975"},
 "source_doc": B + "/o-nadacnim-fondu-albert",
 "evidence": {
   "mission": "Jeho posláním je od samého počátku podpora zdravého životního stylu",
   "jak_oslovit": "Získané finanční prostředky rozděluje prostřednictvím grantových výzev"}}

os.makedirs("data/albert_out", exist_ok=True)
shutil.copyfile("data/albert_in/grant_02.json", "data/albert_in/mission_00.json")
for k, v in out_grant.items():
    json.dump(v, open(f"data/albert_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in out_mission.items():
    json.dump(v, open(f"data/albert_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out_grant), "grants +", len(out_mission), "mission to data/albert_out/")
