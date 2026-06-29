#!/usr/bin/env python3
# Vrstva 2 extrakce pro MŠMT (marwel) — replikace extract_wf.js SYS.grant schématu.
import json, os

S = "https://msmt.gov.cz/"
out = {}

out["grant_00"] = {
 "title":"Podpora nestátních neziskových organizací pro rok 2026 v oblasti PRÁCE S DĚTMI A MLÁDEŽÍ",
 "oblast":["mládež","volný čas","vzdělávání"],
 "focus_area":"Podpora celoroční činnosti NNO pracujících s dětmi a mládeží (osvědčené organizace, projekty s nadregionálním dopadem)",
 "open_from":None,"deadline":"2025-10-31",
 "deadliny":[{"datum":"2025-10-31","kontext":"Termín pro podání žádostí: do 31. 10. 2025"}],
 "obdobi_realizace":"od 1. 1. 2026 do 31. 12. 2026",
 "castky":[{"typ":"alokace","hodnota":146000000,"kontext":"Celková alokace Výzvy je 146 000 000 Kč"}],
 "vyse_hlavni_czk":146000000,"spoluucast":None,
 "eligible_applicants":"Nestátní neziskové organizace (spolky, ústavy, obecně prospěšné společnosti, nadace) pracující s dětmi a mládeží.",
 "typ_zadatele":["neziskovka"],"cilova_skupina":["děti_mladez"],
 "region":[{"nazev":"Česká republika","celostatni":True}],
 "forma_podpory":["dotace"],"zdroj_financovani":["narodni_rozpocet"],
 "rezim_prijmu":"kolova","delka":"jednoleta",
 "how_to_apply":"Žádosti se vkládají přes informační systém ISPROM (https://isprom.msmt.gov.cz), žádost doručit na MŠMT do termínu.",
 "required_attachments":[],
 "dalsi_datumy":[{"datum":"2026-06-30","popis":"u jedné z dílčích výzev uveden termín od 30.6.2026"}],
 "cislo_vyzvy":None,"source_doc":S+"mladez/podpora-nestatnich-neziskovych-organizaci-pro-rok-2026-v",
 "evidence":{
   "title":"PODPORA NESTÁTNÍCH NEZISKOVÝCH ORGANIZACÍ PRO ROK 2026 V OBLASTI PRÁCE S DĚTMI A MLÁDEŽÍ",
   "deadline":"Termín pro podání žádostí: do 31. 10. 2025",
   "vyse_hlavni_czk":"146 000 000",
   "castky":"146 000 000",
   "obdobi_realizace":"od 1. 1. 2026 do 31. 12. 2026",
   "how_to_apply":"ISPROM na adrese https://isprom.msmt.gov.cz"}}

out["grant_01"] = {
 "title":"Na učitelích záleží – rok 2026",
 "oblast":["vzdělávání"],
 "focus_area":"Neinvestiční dotace na podporu pedagogických pracovníků (Na učitelích záleží)",
 "open_from":None,"deadline":"2025-10-31",
 "deadliny":[{"datum":"2025-10-31","kontext":"Žádost musí být doručena na MŠMT nejpozději do 31. 10. 2025"}],
 "obdobi_realizace":"od 1. 1. 2026 do 31. 12. 2026",
 "castky":[{"typ":"alokace","hodnota":1500000,"kontext":"Celková alokace Výzvy je 1 500 000 Kč"}],
 "vyse_hlavni_czk":1500000,"spoluucast":None,
 "eligible_applicants":None,
 "typ_zadatele":[],"cilova_skupina":["pedagogičtí pracovníci","učitelé"],
 "region":[{"nazev":"Česká republika","celostatni":True}],
 "forma_podpory":["dotace"],"zdroj_financovani":["narodni_rozpocet"],
 "rezim_prijmu":"jednorazova_vyzva","delka":"jednoleta",
 "how_to_apply":"On-line formulář IS Integrace; žádost včetně příloh zaslat datovou schránkou (ID vidaawt) poskytovateli do 31. 10. 2025.",
 "required_attachments":[],
 "cislo_vyzvy":None,"source_doc":S+"vzdelavani/zakladni-vzdelavani/vyzva-na-ucitelich-zalezi-rok-2026",
 "evidence":{
   "title":"Výzvu pro podávání žádostí o poskytnutí neinvestiční dotace: Na učitelích záleží – rok 2026",
   "deadline":"doručena na MŠMT, nejpozději do 31. 10. 2025",
   "castky":"1 500 000",
   "how_to_apply":"prostřednictvím datové schránky (ID datov"}}

out["grant_02"] = {
 "title":"Podpora nadaných žáků základních a středních škol v roce 2026",
 "oblast":["vzdělávání","mládež"],
 "focus_area":"Podpora neformálního a zájmového vzdělávání nadaných žáků ZŠ a SŠ",
 "open_from":None,"deadline":"2025-10-31",
 "deadliny":[{"datum":"2025-10-31","kontext":"Žádost je nutné podat v souladu s Výzvou do 31. října 2025"}],
 "obdobi_realizace":"od 1. 1. 2026 do 31. 12. 2026",
 "castky":[{"typ":"alokace","hodnota":13500000,"kontext":"Celková alokace Výzvy je 13 500 000 Kč"}],
 "vyse_hlavni_czk":13500000,"spoluucast":None,
 "eligible_applicants":"Právnické osoby vykonávající činnost školy / organizace v oblasti práce s nadanými žáky ZŠ a SŠ.",
 "typ_zadatele":["skola_vyzkumna_org","neziskovka"],"cilova_skupina":["nadaní žáci","děti_mladez"],
 "region":[{"nazev":"Česká republika","celostatni":True}],
 "forma_podpory":["dotace"],"zdroj_financovani":["narodni_rozpocet"],
 "rezim_prijmu":"jednorazova_vyzva","delka":"jednoleta",
 "how_to_apply":"Žádosti se vkládají přes informační systém ISPROM (https://isprom.msmt.gov.cz/), otevřen 1. října 2025.",
 "required_attachments":[],
 "cislo_vyzvy":None,"source_doc":S+"mladez/vyzva-podpora-nadanych-zaku-zakladnich-a-strednich-skol-v-1",
 "evidence":{
   "title":"Výzvu Podpora nadaných žáků základních a středních škol v roce 2026",
   "deadline":"podat v souladu s Výzvou do 31. října 2025",
   "castky":"13 500 000",
   "how_to_apply":"systému ISPROM na adrese https://isprom.msmt.gov.cz"}}

out["grant_03"] = {
 "title":"Podpora aktivit v oblasti primární prevence rizikového chování a podpory duševního zdraví ve školách a školských zařízeních pro rok 2026",
 "oblast":["prevence","duševní zdraví","vzdělávání"],
 "focus_area":"Primární prevence rizikového chování a podpora duševního zdraví ve školách (3 moduly: individuální, interaktivní, …)",
 "open_from":None,"deadline":None,
 "deadliny":[],"obdobi_realizace":"rok 2026",
 "castky":[],"vyse_hlavni_czk":None,"spoluucast":None,
 "eligible_applicants":"Školy a školská zařízení, NNO (dle modulu) v oblasti primární prevence.",
 "typ_zadatele":["skola_vyzkumna_org","neziskovka"],"cilova_skupina":["děti_mladez","žáci"],
 "region":[{"nazev":"Česká republika","celostatni":True}],
 "forma_podpory":["dotace"],"zdroj_financovani":["narodni_rozpocet"],
 "rezim_prijmu":"kolova","delka":"jednoleta",
 "how_to_apply":"Žádosti přes systém IS-PREVENCE (viz Výzva).",
 "required_attachments":[],
 "cislo_vyzvy":None,"source_doc":S+"vzdelavani/socialni-programy/vyzva-podpora-aktivit-v-oblasti-primarni-prevence-rizikoveho",
 "evidence":{
   "title":"Výzvu Podpora aktivit v oblasti primární prevence rizikového chování a podpory duševního zdraví ve školách a školských zařízeních pro rok 2026",
   "focus_area":"Výzva je rozdělena na 3 moduly",
   "oblast":"Národní strategie primární prevence rizikového chování"}}

# --- 2016 archivní rozvojové programy (historické; na hubu, ale staré) ---
out["grant_04"] = {
 "title":"Rozvojový program – Bezplatná výuka českého jazyka přizpůsobená potřebám žáků-cizinců z třetích zemí (2016)",
 "oblast":["vzdělávání","integrace cizinců"],
 "focus_area":"Bezplatná výuka českého jazyka pro žáky-cizince z třetích zemí (rozvojový program 2016)",
 "open_from":None,"deadline":None,
 "deadliny":[],"obdobi_realizace":"rok 2016",
 "castky":[],"vyse_hlavni_czk":None,"spoluucast":None,
 "eligible_applicants":"Právnické osoby vykonávající činnost školy; žadatelem o dotaci je krajský úřad.",
 "typ_zadatele":["skola_vyzkumna_org","obec_verejny_subjekt"],"cilova_skupina":["žáci-cizinci","děti_mladez"],
 "region":[{"nazev":"Česká republika","celostatni":True}],
 "forma_podpory":["dotace"],"zdroj_financovani":["narodni_rozpocet"],
 "rezim_prijmu":"jednorazova_vyzva","delka":"jednoleta","how_to_apply":None,
 "required_attachments":[],
 "cislo_vyzvy":"MŠMT-4100/2016-2","source_doc":S+"vzdelavani/zakladni-vzdelavani/vyhlaseni-rozvojoveho-programu-bezplatna-vyuka-ceskeho",
 "evidence":{
   "title":"Bezplatná výuka českého jazyka přizpůsobená potřebám žáků-cizinců z třetích zemí",
   "obdobi_realizace":"vyhlašuje na rok 2016",
   "cislo_vyzvy":"4100/2016-2"}}

out["grant_05"] = {
 "title":"Rozvojový program – Zajištění podmínek základního vzdělávání nezletilých azylantů a žadatelů o mezinárodní ochranu (2016)",
 "oblast":["vzdělávání","integrace cizinců"],
 "focus_area":"Zajištění podmínek základního vzdělávání nezletilých azylantů, osob s doplňkovou ochranou a žadatelů o mezinárodní ochranu (2016)",
 "open_from":None,"deadline":None,
 "deadliny":[],"obdobi_realizace":"rok 2016",
 "castky":[],"vyse_hlavni_czk":None,"spoluucast":None,
 "eligible_applicants":"Právnické osoby vykonávající činnost školy; žadatelem o dotaci je krajský úřad.",
 "typ_zadatele":["skola_vyzkumna_org","obec_verejny_subjekt"],"cilova_skupina":["azylanti","žáci-cizinci","děti_mladez"],
 "region":[{"nazev":"Česká republika","celostatni":True}],
 "forma_podpory":["dotace"],"zdroj_financovani":["narodni_rozpocet"],
 "rezim_prijmu":"jednorazova_vyzva","delka":"jednoleta","how_to_apply":None,
 "required_attachments":[],
 "cislo_vyzvy":"MSMT-3229/2016","source_doc":S+"vzdelavani/zakladni-vzdelavani/vyhlaseni-rozvojoveho-programu-zajisteni-podminek-zakladniho-1",
 "evidence":{
   "title":"Zajištění podmínek základního vzdělávání nezletilých azylantů",
   "obdobi_realizace":"na rok 2016",
   "cislo_vyzvy":"3229/2016"}}

out["grant_06"] = {
 "title":"Rozvojový program – Zajištění bezplatné přípravy k začlenění do základního vzdělávání dětí občanů EU (2016)",
 "oblast":["vzdělávání","integrace cizinců"],
 "focus_area":"Bezplatná příprava k začlenění do základního vzdělávání dětí osob se státní příslušností jiného členského státu EU (2016)",
 "open_from":None,"deadline":None,
 "deadliny":[],"obdobi_realizace":"rok 2016",
 "castky":[],"vyse_hlavni_czk":None,"spoluucast":None,
 "eligible_applicants":"Právnické osoby vykonávající činnost školy; žadatelem o dotaci je krajský úřad.",
 "typ_zadatele":["skola_vyzkumna_org","obec_verejny_subjekt"],"cilova_skupina":["děti občanů EU","žáci-cizinci","děti_mladez"],
 "region":[{"nazev":"Česká republika","celostatni":True}],
 "forma_podpory":["dotace"],"zdroj_financovani":["narodni_rozpocet"],
 "rezim_prijmu":"jednorazova_vyzva","delka":"jednoleta","how_to_apply":None,
 "required_attachments":[],
 "cislo_vyzvy":"MSMT-3393/2016","source_doc":S+"vzdelavani/zakladni-vzdelavani/vyhlaseni-rozvojoveho-programu-zajisteni-bezplatne-pripravy-1",
 "evidence":{
   "title":"Zajištění bezplatné přípravy k začlenění do základního vzdělávání",
   "obdobi_realizace":"vyhlašuje na rok 2016",
   "cislo_vyzvy":"3393/2016"}}

os.makedirs("data/msmt_out", exist_ok=True)
for k, v in out.items():
    json.dump(v, open(f"data/msmt_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out), "extraction files to data/msmt_out/")
