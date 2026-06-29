#!/usr/bin/env python3
# Vrstva 2 extrakce pro Nadaci ADRA (nadace-adra.cz, parser scripts/nadace_adra.py).
# 1 foundation_mission + 2 granty (nadační příspěvky jednotlivcům; grantové řízení 2022/2023).
# grant_00 → mission_00 (kopie vstupu pro basename join).
import json, os, shutil

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
B = "https://www.nadace-adra.cz"
out_grant, out_mission = {}, {}

# --- grant: Nadační příspěvky pro jednotlivce a rodiny (postup-a-pravidla → grant_01) ---
out_grant["grant_01"] = {
 "title": "Nadační příspěvky pro jednotlivce a rodiny – veřejná sbírka „Pomáhat může každý“",
 "oblast": ["sociální", "zdraví", "humanitární pomoc"],
 "focus_area": "Pomoc osobám, rodinám nebo skupinám v ČR, které se ocitly v tíživé životní situaci v důsledku mimořádných událostí či zdravotních a sociálních důvodů (povodeň, požár, násilí, autonehoda apod.).",
 "open_from": None, "deadline": "průběžně", "deadliny": [],
 "obdobi_realizace": None,
 "castky": [{"typ": "max_zadatel", "hodnota": 15000, "kontext": "příspěvek jednorázový menšího rozsahu (zpravidla do 15 000 Kč)"}],
 "vyse_hlavni_czk": 15000, "spoluucast": None,
 "eligible_applicants": "Osoby, rodiny nebo skupiny, které se v České republice ocitly v tíživé životní situaci, již nemohou zvládnout vlastními silami (zdravotní, sociální či jiné závažné důvody).",
 "typ_zadatele": ["fyzicka_osoba"],
 "cilova_skupina": ["jednotlivci", "rodiny", "senioři", "děti", "lidé v nouzi"],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["vlastni_zdroje"],
 "rezim_prijmu": "prubezna", "delka": "jednoleta",
 "how_to_apply": "Žádost se podává na formuláři Nadace ADRA dle Postupu a pravidel poskytování nadačních příspěvků; možná je pomoc jednorázová i dlouhodobá.",
 "required_attachments": [], "cislo_vyzvy": None,
 "source_doc": B + "/potrebuji-pomoci/postup-a-pravidla-poskytovani-prispevku/postup-a-pravidla-poskytovani-prispevku.html",
 "kontakt": {"osoba": None, "email": "nadace@adra.cz", "telefon": "732 355 962"},
 "evidence": {
   "title": "Postup a pravidla poskytování nadačních příspěvků z veřejné sbírky „Pomáhat může každý“",
   "eligible_applicants": "Nadace ADRA podporuje osoby, rodiny nebo skupiny, které se v České republice ocitly v tíživé životní situaci",
   "castky": "příspěvek jednorázový menšího rozsahu (zpravidla do 15 000 Kč)"}}

# --- grant: Grantové řízení 2022/2023 – paliativní péče (grantove-rizeni → grant_02) ---
out_grant["grant_02"] = {
 "title": "Grantové řízení 2022/2023 – podpora paliativní péče v hospici",
 "oblast": ["zdraví", "sociální", "paliativní péče"],
 "focus_area": "Veřejné grantové řízení na podporu paliativní péče v hospici (mobilní specializovaná paliativní péče, hospicová péče).",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": "2022/2023",
 "castky": [{"typ": "alokace", "hodnota": 962000, "kontext": "Správní rada schválila podporu projektů v celkové výši 962.000 Kč."}],
 "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": "Neziskové organizace poskytující paliativní a hospicovou péči (mobilní hospice, domácí hospice).",
 "typ_zadatele": ["neziskovka"],
 "cilova_skupina": ["pacienti", "nevyléčitelně nemocní", "rodiny pacientů"],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["vlastni_zdroje"],
 "rezim_prijmu": "jednorazova_vyzva", "delka": "jednoleta",
 "how_to_apply": "Projekty se podávaly v rámci veřejného grantového řízení vyhlášeného v dubnu 2022; o podpoře rozhodla správní rada na doporučení Grantové komise.",
 "required_attachments": [], "cislo_vyzvy": None,
 "source_doc": B + "/jak-pomahame/grantove-rizeni/grantove-rizeni-2021-2022.html",
 "dalsi_datumy": [{"datum": "2022-04", "popis": "Nadace ADRA vyhlásila veřejné grantové řízení 2022/2023 v dubnu 2022."}],
 "evidence": {
   "title": "Grantové řízení 2022/2023",
   "focus_area": "na podporu paliativní péče v hospici",
   "castky": "v celkové výši 962.000"}}

# --- foundation_mission (podpora-projektu → mission_00) ---
out_mission["mission_00"] = {
 "name": "Nadace ADRA",
 "mission": "Pomáhá potřebným v ČR komplexně – nestátním neziskovým organizacím působícím v sociálně-zdravotní oblasti i jednotlivcům a rodinám v tíživé životní situaci; jako člen mezinárodní sítě ADRA se zapojuje také do humanitární a rozvojové pomoci v zahraničí.",
 "support_topics": ["pomoc jednotlivcům a rodinám v nouzi", "sociálně-zdravotní oblast", "hospicová a paliativní péče", "humanitární a rozvojová pomoc", "veřejná sbírka"],
 "cilova_skupina": ["jednotlivci", "rodiny", "senioři", "děti", "neziskové organizace"],
 "regions": ["Česká republika", "zahraničí"],
 "forma_podpory": ["dotace"],
 "jak_oslovit": "O nadační příspěvek lze žádat na formuláři Nadace ADRA (pomoc jednotlivcům/rodinám); organizace se mohou hlásit do vyhlašovaných grantových řízení.",
 "kontakt": {"osoba": None, "email": "nadace@adra.cz", "telefon": "732 355 962"},
 "source_doc": B + "/jak-pomahame/podpora-projektu/podpora-projektu.html",
 "evidence": {
   "name": "Nadace ADRA",
   "mission": "abychom mohli potřebným v ČR pomáhat komplexně - nestátním neziskovým organizacím působícím v sociálně-zdravotní oblasti, event. jednotlivcům (rodinám)"}}

os.makedirs("data/nadace_adra_out", exist_ok=True)
shutil.copyfile("data/nadace_adra_in/grant_00.json", "data/nadace_adra_in/mission_00.json")
for k, v in out_grant.items():
    json.dump(v, open(f"data/nadace_adra_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in out_mission.items():
    json.dump(v, open(f"data/nadace_adra_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out_grant), "grants +", len(out_mission), "mission to data/nadace_adra_out/")
