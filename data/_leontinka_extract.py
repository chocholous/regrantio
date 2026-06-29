#!/usr/bin/env python3
# Vrstva 2 extrakce pro Nadaci Leontinka (nadaceleontinka.cz, parser scripts/leontinka.py).
# grant_00 = vypsane-granty (Grantové řízení 2026) → 1 grant; grant_01 = o-nadaci → mission_00.
# Hlavní roční uzávěrka 19. 5. 2026 už prošla (dnes 27. 6. 2026), ALE „Urgentní žádosti
# posuzujeme také průběžně." → deadline="průběžně" → compute_status: open/high (rolling).
# Roční kolo dokumentováno v deadliny[].
import json, os, shutil

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
KONT = {"osoba": "Barbara Hucková", "email": "huckova@nadaceleontinka.cz", "telefon": "724 055 118"}
out_grant, out_mission = {}, {}

# --- grant_00: Grantové řízení 2026 (vypsane-granty) ---
out_grant["grant_00"] = {
 "title": "Grantové řízení Nadace Leontinka 2026",
 "oblast": ["sociální", "zdravotní postižení", "děti a mládež", "vzdělávání"],
 "focus_area": "Podpora aktivit zrakově postižených, především dětí a mladých lidí: raná péče, speciální školy a učební pomůcky, osobní asistence a integrace do běžných škol, kompenzační pomůcky a technologie, výcvikové/léčebné programy, sport, prevence zrakových onemocnění, asistenční psi, stipendia.",
 "open_from": "2026-02-17", "deadline": "průběžně",
 "deadliny": [
   {"datum": "2026-05-19", "kontext": "Uzávěrka velkého ročního grantového řízení 2026 (vyhlášení 17. 2. 2026, výsledky do 30. 6. 2026)."},
   {"datum": None, "kontext": "Urgentní žádosti posuzuje nadace také průběžně mimo roční kolo."}],
 "obdobi_realizace": "od 13. 4. 2026 do 30. 6. 2027",
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": "Občanská sdružení/spolky, obecně prospěšné společnosti, církevní právnické osoby, zapsané ústavy, fyzické osoby a další subjekty, jejichž hlavním předmětem činnosti je podpora aktivit zrakově postižených. Žádat mohou i osoby se zrakovým postižením ukrajinské národnosti se statusem uprchlíka v ČR.",
 "typ_zadatele": ["neziskovka", "fyzicka_osoba", "prispevkova_organizace"],
 "cilova_skupina": ["zrakově postižené děti a mladí lidé", "osoby se zrakovým postižením", "osoby se zdravotním postižením"],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["vlastni_zdroje"],
 "rezim_prijmu": "prubezna", "delka": "viceleta",
 "how_to_apply": "Žádost o nadační příspěvek (formulář pro fyzické/právnické osoby na webu) se podává elektronicky včetně všech příloh na e-mail info@nadaceleontinka.cz. O udělení a výši příspěvku rozhoduje správní rada (zasedá min. 4× ročně), rozhodnutí je konečné a není na příspěvek právní nárok.",
 "required_attachments": ["FO: oboustranná kopie OP a průkazu ZTP/P", "FO: doklad o přiznání invalidního důchodu (je-li)", "FO: čestné prohlášení o výši příjmů", "FO: kopie smlouvy či výpisu z bankovního účtu", "FO: kopie aktuální zprávy očního lékaře", "FO: čestné prohlášení o dalších příspěvcích na tentýž účel", "FO: potvrzení o studiu (stipendium) / vyjádření sociálního odboru (kompenzační pomůcka)", "PO: doklad o právní subjektivitě a předmětu činnosti", "PO: statut nebo stanovy", "PO: doklad o přidělení IČ", "PO: rozhodnutí o registraci sociálních služeb (poskytovatelé)", "PO: doklad o vedení bankovního účtu"],
 "cislo_vyzvy": None,
 "source_doc": "https://nadaceleontinka.cz/projekt/vypsane-granty",
 "kontakt": KONT,
 "evidence": {
   "title": "Nadace Leontinka vyhlašuje každoročně velké grantové řízení.",
   "eligible_applicants": "jejichž hlavním předmětem činnosti je podpora aktivit zrakově postižených.",
   "deadline": "Urgentní žádosti posuzujeme také průběžně.",
   "how_to_apply": "Grantové žádosti se podávají elektronicky, včetně všech příloh, na e-mailovou adresu: info@nadaceleontinka.cz."}}

# --- foundation_mission (o-nadaci → mission_00) ---
out_mission["mission_00"] = {
 "name": "Nadace Leontinka",
 "mission": "Od roku 2005 přináší světlo do života lidem se zrakovým postižením, především dětem a mladým lidem; pomáhá s integrací do běžného života v rámci vzdělání, společenských, sportovních i volnočasových aktivit a systematicky podporuje střediska rané péče po celé ČR.",
 "support_topics": ["raná péče pro zrakově a kombinovaně postižené děti", "speciální školy a učební pomůcky", "osobní asistence a integrace do běžných škol", "kompenzační pomůcky a technologie", "sport a prevence zrakových onemocnění", "osvěta"],
 "cilova_skupina": ["zrakově postižené děti a mladí lidé", "osoby se zrakovým postižením"],
 "regions": ["Česká republika"],
 "forma_podpory": ["dotace"],
 "jak_oslovit": "Nadace shromažďuje prostředky od individuálních dárců, partnerů a sponzorů a z benefičních akcí; finanční i nefinanční dary pak rozděluje v rámci grantového řízení mezi jednotlivé projekty zaměřené na pomoc konkrétním institucím a dětem.",
 "kontakt": {"osoba": None, "email": "info@nadaceleontinka.cz", "telefon": None},
 "source_doc": "https://nadaceleontinka.cz/projekt/o-nadaci",
 "evidence": {
   "mission": "Nadace Leontinka už od roku 2005 přináší světlo do života lidem se zrakovým postižením",
   "jak_oslovit": "Finanční prostředky a nefinanční dary poté nadace rozděluje v rámci grantového řízení mezi jednotlivé projekty"}}

os.makedirs("data/leontinka_out", exist_ok=True)
shutil.copyfile("data/leontinka_in/grant_01.json", "data/leontinka_in/mission_00.json")
for k, v in out_grant.items():
    json.dump(v, open(f"data/leontinka_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in out_mission.items():
    json.dump(v, open(f"data/leontinka_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out_grant), "grant +", len(out_mission), "mission to data/leontinka_out/")
