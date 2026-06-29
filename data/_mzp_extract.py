#!/usr/bin/env python3
# Vrstva 2 extrakce pro MŽP (mzp.gov.cz, harvest_site/drupal) — replikace extract_wf.js SYS.grant.
# 16 oportunit z 20 harvestovaných stránek (vynechán hub-index /, interreg-list a 2 administrativní
# NNO podstránky pro-3/pro-4). Indexy grant_NN odpovídají data/mzp_in/grant_NN.json (join přes basename).
import json, os

B = "https://www.mzp.gov.cz/cz/agenda/prehled-dotaci"
CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
out = {}

# ---- programové huby (dotační programy MŽP) ----
out["grant_01"] = {
 "title": "Národní plán obnovy – aktivity v gesci Ministerstva životního prostředí",
 "oblast": ["prostředí", "energetika", "klima"],
 "focus_area": "Realizace reforem a investic Národního plánu obnovy, u nichž je MŽP vlastníkem komponent (úspory energie ve veřejném sektoru, biodiverzita, adaptace na sucho).",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": None,
 "castky": [{"typ": "alokace", "hodnota": 33500000000, "kontext": "Celková alokace z prostředků NPO na aktivity, u kterých plní Ministerstvo životního prostředí funkci vlastníka, činí 33,5 mld. Kč (bez DPH)."}],
 "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": None, "typ_zadatele": [], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["npo", "eu_fondy", "narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "viceleta",
 "how_to_apply": "Harmonogram výzev je k dispozici na https://www.planobnovycr.cz/vyhlasene-vyzvy.",
 "required_attachments": [], "cislo_vyzvy": None, "source_doc": B + "/narodni-plan-obnovy",
 "evidence": {
   "title": "Národní plán obnovy",
   "castky": "Celková alokace z prostředků NPO na aktivity, u kterých plní Ministerstvo životního prostředí funkci vlastníka, činí 33,5 mld. Kč",
   "how_to_apply": "Harmonogram výzev je k dispozici na https://www.planobnovycr.cz/vyhlasene-vyzvy"}}

out["grant_02"] = {
 "title": "Národní program Životní prostředí (NPŽP)",
 "oblast": ["prostředí", "klima", "vzdělávání"],
 "focus_area": "Doplňkový národní program SFŽP ČR na efektivní využívání přírodních zdrojů, adaptaci na změnu klimatu a EVVO; dělí se na 10 prioritních os.",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": "tříleté období dle Rámce NPŽP (2024–2026)",
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": None, "typ_zadatele": [], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "viceleta",
 "how_to_apply": "Žádosti o podporu se podávají v rámci jednotlivých vyhlašovaných výzev, které administruje SFŽP ČR.",
 "required_attachments": [], "cislo_vyzvy": None, "source_doc": B + "/narodni-program-zivotni-prostredi",
 "evidence": {
   "title": "Národní program Životní prostředí",
   "focus_area": "NPŽP slouží jako doplňující program pro projekty, které nejsou podporovány v Operačním programu Životní prostředí",
   "how_to_apply": "Žádosti o podporu se podávají v rámci jednotlivých vyhlašovaných výzev, které administruje SFŽP ČR"}}

out["grant_03"] = {
 "title": "Program péče o krajinu (PPK)",
 "oblast": ["prostředí", "příroda a krajina"],
 "focus_area": "Dotační program na drobná opatření péče o krajinu ve čtyřech podprogramech (A–D): péče o ZCHÚ a Natura 2000, opatření ve volné krajině, péče o handicapované živočichy, osvětové a podkladové materiály.",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": None,
 "castky": [{"typ": "mira_pct", "hodnota": 100, "kontext": "Program poskytuje neinvestiční prostředky do výše 100 % vynaložených nákladů v roce podání žádosti."}],
 "vyse_hlavni_czk": None, "spoluucast": False,
 "eligible_applicants": "Dle podprogramu: správy národních parků, Agentura ochrany přírody a krajiny nebo Správa jeskyní ČR (A, D); fyzická i právnická osoba nebo organizační složka státu (B); subjekt zajišťující naplnění prostřednictvím akreditovaných záchranných stanic (C).",
 "typ_zadatele": ["obec_verejny_subjekt", "neziskovka", "fyzicka_osoba", "firma"],
 "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "jednoleta",
 "how_to_apply": "Žádosti jsou přijímány na základě vyhlášené výzvy; další informace na webu Agentury ochrany přírody a krajiny ČR.",
 "required_attachments": [], "cislo_vyzvy": None, "source_doc": B + "/program-pece-o-krajinu",
 "evidence": {
   "title": "Program péče o krajinu",
   "focus_area": "Program péče o krajinu je dotační program na podporu zejména drobných opatření. Dělí se na čtyři podprogramy",
   "castky": "Program poskytuje neinvestiční prostředky do výše 100 % vynaložených nákladů v roce podání žádosti"}}

out["grant_04"] = {
 "title": "Podpora obnovy přirozených funkcí krajiny 2019–2023 (POPFK)",
 "oblast": ["prostředí", "příroda a krajina", "klima"],
 "focus_area": "Realizace opatření z plánovacích a koncepčních dokumentů (plány péče o ZCHÚ, záchranné programy) a opatření přispívajících k adaptaci krajiny na změnu klimatu. Program byl ukončen, nahrazen NPO – Podpora obnovy přirozených funkcí krajiny.",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": "2019–2023",
 "castky": [{"typ": "mira_pct", "hodnota": 100, "kontext": "Program umožňoval podporu až do výše 100 % vynaložených nákladů."}],
 "vyse_hlavni_czk": None, "spoluucast": False,
 "eligible_applicants": "Okruh oprávněných žadatelů stanovovaly jednotlivé vyhlášené výzvy.",
 "typ_zadatele": [], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "jednoleta",
 "how_to_apply": "Žádosti o podporu opatření byly přijímány na základě vyhlášených výzev.",
 "required_attachments": [], "cislo_vyzvy": None,
 "source_doc": B + "/podpora-obnovy-prirozenych-funkci-krajiny-2019-2023",
 "dalsi_datumy": [{"datum": "2023", "popis": "Program byl ukončen, aktuálně probíhá jeho vyhodnocení."}],
 "evidence": {
   "title": "Podpora obnovy přirozených funkcí krajiny",
   "obdobi_realizace": "Program byl ukončen",
   "castky": "Program umožňoval podporu až do výše 100 % vynaložených nákladů",
   "eligible_applicants": "Příslušné výzvy rovněž stanovovaly okruh oprávněných žadatelů"}}

out["grant_05"] = {
 "title": "Národní plán obnovy – Podpora obnovy přirozených funkcí krajiny",
 "oblast": ["prostředí", "příroda a krajina", "voda", "klima"],
 "focus_area": "Adaptační opatření péče o přírodu a krajinu a podpora biodiverzity ve čtyřech podprogramech (164 péče o ZCHÚ/Natura 2000 a ZCHD, 165 adaptace ekosystémů na klima, 166 komplexní vodohospodářské studie, 167 opatření k jejich naplňování).",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": "2022–2025",
 "castky": [{"typ": "max_zadatel", "hodnota": 250000, "kontext": "Maximální výše dotace je 250 tis. Kč, pokud ve výzvě není uvedeno jinak."},
            {"typ": "mira_pct", "hodnota": 100, "kontext": "Uznatelné náklady jsou hrazeny až do výše 100 %."}],
 "vyse_hlavni_czk": 250000, "spoluucast": False,
 "eligible_applicants": "Dle podprogramu: rezortní organizace MŽP a kraje (164); široká škála žadatelů realizujících projekty na celém území ČR (165); správci vodních toků, kraje, obce, Státní pozemkový úřad, AOPK ČR a správy národních parků (166).",
 "typ_zadatele": ["obec_verejny_subjekt", "prispevkova_organizace", "neziskovka", "firma"],
 "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["npo", "narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "viceleta",
 "how_to_apply": "Žádosti zpracovává AOPK ČR a SFŽP ČR (mimorezortní žadatelé), resp. Odbor adaptace na změnu klimatu MŽP (rezortní organizace).",
 "required_attachments": [], "cislo_vyzvy": None,
 "source_doc": B + "/npo-podpora-obnovy-prirozenych-funkci-krajiny",
 "evidence": {
   "title": "Národní plán obnovy – podpora obnovy přirozených funkcí krajiny",
   "castky": "Maximální výše dotace je 250 tis. Kč, pokud ve výzvě není uvedeno jinak",
   "obdobi_realizace": "v letech 2022 – 2025"}}

out["grant_06"] = {
 "title": "Program švýcarsko-české spolupráce II – Udržitelný turismus a posílení biodiverzity",
 "oblast": ["prostředí", "příroda a krajina", "cestovní ruch"],
 "focus_area": "Řešení dvou hlavních příčin poklesu biodiverzity – zásahů člověka do ekosystémů (fragmentace krajiny) a nadměrného turismu – formou velkých projektů (nad 70 mil. Kč) a malého grantového schématu (0,5–5 mil. Kč).",
 "open_from": None, "deadline": None,
 "deadliny": [{"datum": "2025-03-28", "kontext": "Dne 28. března 2025 byla vyhlášena výzva č. 2 na podporu projektů malého grantového schématu."}],
 "obdobi_realizace": "realizace projektů do 31. 12. 2028 (resp. do 31. 10. 2028 pro malé grantové schéma)",
 "castky": [{"typ": "alokace", "hodnota": 1084000000, "kontext": "bylo alokováno 38,4 mil. CHF s národním kofinancováním 6,78 mil. CHF (celkem 45,18 mil. CHF, tedy cca 1 084 mil. Kč)"},
            {"typ": "mira_pct", "hodnota": 90, "kontext": "Výše grantu může činit až 90 % (v závislosti na míře veřejné podpory)."},
            {"typ": "max_zadatel", "hodnota": 5000000, "kontext": "Projekty v tzv. Malém grantovém schématu (dále MGS) v hodnotě 500 tisíc Kč až 5 mil. Kč"}],
 "vyse_hlavni_czk": None, "spoluucast": True,
 "eligible_applicants": "Každá právnická osoba se sídlem na území České republiky, s právní subjektivitou a identifikačním číslem organizace.",
 "typ_zadatele": ["neziskovka", "obec_verejny_subjekt", "firma", "prispevkova_organizace"],
 "cilova_skupina": ["veřejnost"],
 "region": [{"nazev": "Česká republika (mimo hl. m. Prahu)", "obec": None, "okres": None, "kraj": None, "celostatni": True}],
 "forma_podpory": ["dotace"], "zdroj_financovani": ["svycarske_fondy", "narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "viceleta",
 "how_to_apply": "Dotazy a konzultace e-mailem na swiss@mzp.gov.cz; podání datovou schránkou MŽP (ID 9gsaax4).",
 "required_attachments": [], "cislo_vyzvy": "č. 1 a č. 2",
 "kontakt": {"osoba": "Ing. Monika Vaněčková", "email": "swiss@mzp.gov.cz", "telefon": "267 122 795"},
 "source_doc": B + "/program-svycarsko-ceske-spoluprace-ii",
 "dokumenty": [{"popis": "Výzva č. 2 programu Udržitelný turismus a posílení biodiverzity", "role": "vyhlaseni"},
               {"popis": "Pokyny pro příjemce dotace", "role": "pravidla_podminky"},
               {"popis": "Oznámení výsledků 1. a 2. výzvy", "role": "vysledky"}],
 "evidence": {
   "title": "Udržitelný turismus a posílení biodiverzity",
   "castky": "bylo alokováno 38,4 mil. CHF s národním kofinancováním 6,78 mil. CHF (celkem 45,18 mil. CHF, tedy cca 1 084 mil. Kč)",
   "eligible_applicants": "Oprávněným žadatelem je každá právnická osoba se sídlem na území České republiky, s právní subjektivitou a identifikačním číslem organizace",
   "region": "Územně způsobilá pro realizaci projektů je celá ČR s výjimkou hl. m. Prahy",
   "how_to_apply": "swiss [at] mzp.gov.cz"}}

out["grant_08"] = {
 "title": "Sociální klimatický fond (SKF)",
 "oblast": ["sociální", "bydlení", "doprava", "klima", "energetika"],
 "focus_area": "Ochrana zranitelných domácností a jednotlivců před zdražováním z nového systému emisních povolenek pro budovy a dopravu (ETS2): úsporné bydlení, bezemisní veřejná doprava, poradenství.",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": "2026–2032",
 "castky": [{"typ": "alokace", "hodnota": 50000000000, "kontext": "V letech 2026–2032 může Česko získat až 50 miliard korun z nového Sociálního klimatického fondu (SKF)."}],
 "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": None,
 "typ_zadatele": [], "cilova_skupina": ["zranitelné domácnosti", "nízkopříjmové domácnosti", "veřejnost"],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["eu_fondy"],
 "rezim_prijmu": None, "delka": "viceleta",
 "how_to_apply": "Plán (Sociální klimatický plán) je v přípravě; připomínky lze zaslat na e-mail skf@mzp.gov.cz.",
 "required_attachments": [], "cislo_vyzvy": None, "source_doc": B + "/socialni-klimaticky-fond",
 "kontakt": {"osoba": "Karel Voldřich", "email": "karel.voldrich@mzp.gov.cz", "telefon": "267 122 274"},
 "evidence": {
   "title": "Sociální klimatický fond",
   "castky": "může Česko získat až 50 miliard korun z nového Sociálního klimatického fondu",
   "obdobi_realizace": "V letech 2026–2032"}}

out["grant_09"] = {
 "title": "Modernizační fond",
 "oblast": ["energetika", "klima", "doprava", "prostředí"],
 "focus_area": "Podpora investic do modernizace energetických soustav a zlepšení energetické účinnosti v programech TRANSCom, TRANSGov, GREENGAS, SMARTNET/PUBGRID, ELEGRID, KOMUNERG a I+.",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": "2021–2030",
 "castky": [{"typ": "alokace", "hodnota": 380000000000, "kontext": "Pro Českou republiku bude dostupných odhadem až 380-500 miliard Kč za celé období 2021 - 2030."}],
 "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": None,
 "typ_zadatele": ["firma", "obec_verejny_subjekt", "prispevkova_organizace"], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["eu_fondy"],
 "rezim_prijmu": "kolova", "delka": "viceleta",
 "how_to_apply": None,
 "required_attachments": [], "cislo_vyzvy": None, "source_doc": B + "/modernizacni-fond",
 "kontakt": {"osoba": "Jiří Jeřábek", "email": "jiri.jerabek@mzp.gov.cz", "telefon": "267 122 584"},
 "evidence": {
   "title": "Modernizační fond",
   "castky": "Pro Českou republiku bude dostupných odhadem až 380-500 miliard Kč za celé období 2021 - 2030",
   "focus_area": "TRANSGov Modernizace veřejné dopravy"}}

out["grant_10"] = {
 "title": "Finanční nástroje OPŽP / OPST – záruky a úvěry",
 "oblast": ["prostředí", "oběhové hospodářství", "infrastruktura"],
 "focus_area": "Nedotační podpora (úvěry, záruky, kombinace s dotací) pro ekonomicky životaschopné environmentální projekty; finanční nástroj v podobě finanční záruky pro oblast oběhového hospodářství v OPŽP 2021–2027.",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": None,
 "castky": [{"typ": "max_zadatel", "hodnota": 500000000, "kontext": "Výše zaručovaného úvěru se může pohybovat v rozmezí od 8 milionů do 500 milionů korun."},
            {"typ": "min_zadatel", "hodnota": 8000000, "kontext": "Výše zaručovaného úvěru se může pohybovat v rozmezí od 8 milionů do 500 milionů korun."},
            {"typ": "mira_pct", "hodnota": 50, "kontext": "Podpora formou záruky je u všech projektů stejná – 50 % poskytnutého komerčního úvěru."}],
 "vyse_hlavni_czk": 500000000, "spoluucast": True,
 "eligible_applicants": "Žadatelé s ekonomicky životaschopnými environmentálními projekty (model one-stop-shop: žádost o záruku i dotaci současně).",
 "typ_zadatele": ["firma", "obec_verejny_subjekt"], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["zapujcka_uver", "dotace"], "zdroj_financovani": ["eu_fondy"],
 "rezim_prijmu": "kolova", "delka": "viceleta",
 "how_to_apply": "Vyhlášeno MŽP ve spolupráci se SFŽP ČR (zprostředkovatel a administrátor); záruku i dotaci lze vyřídit jednou žádostí.",
 "required_attachments": [], "cislo_vyzvy": "č. 1/2025 FN", "source_doc": B + "/financni-nastroje",
 "evidence": {
   "title": "Finanční nástroj pro oběhové hospodářství",
   "castky": "Výše zaručovaného úvěru se může pohybovat v rozmezí od 8 milionů do 500 milionů korun",
   "focus_area": "jde o podporu formou úvěrů, záruk, kapitálových investic"}}

out["grant_11"] = {
 "title": "Zvýhodněné půjčky ze Státního fondu životního prostředí ČR",
 "oblast": ["prostředí", "voda", "bydlení"],
 "focus_area": "Zvýhodněné půjčky na kofinancování vodohospodářských projektů obcí do 2 tis. obyvatel (k výzvám 6/2024 a 7/2024 NPŽP) a na regeneraci brownfieldů (OPST, výzva 1/2026 FN).",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": None,
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": "Obce do 2 tis. obyvatel (zajištění vlastních zdrojů na kofinancování projektů podpořených z OPŽP 2021–2027).",
 "typ_zadatele": ["obec_verejny_subjekt"], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["zapujcka_uver"], "zdroj_financovani": ["narodni_rozpocet", "eu_fondy"],
 "rezim_prijmu": "prubezna", "delka": "viceleta",
 "how_to_apply": "Žádost se vyřizuje společně se žádostí o dotaci z OPŽP (jedno kontaktní místo); poskytování se řídí směrnicí MŽP č. 8/2017.",
 "required_attachments": [], "cislo_vyzvy": None, "source_doc": B + "/pujcky",
 "evidence": {
   "title": "Ministerstvo životního prostředí poskytuje prostřednictvím Státního fondu životního prostředí ČR zvýhodněné půjčky",
   "eligible_applicants": "jsou určeny pro zajištění vlastních zdrojů obcí do 2 tis. obyv., pouze na kofinancování projektů",
   "focus_area": "Půjčky jsou poskytovány na realizaci vodohospodářských projektů podpořených z dotačních výzev č. 6/2024 a č. 7/2024 z Národního programu životní prostředí"}}

out["grant_12"] = {
 "title": "Program na podporu projektů nestátních neziskových organizací (MŽP)",
 "oblast": ["prostředí", "vzdělávání"],
 "focus_area": "Dlouhodobá podpora aktivit nestátních neziskových organizací v oblasti ochrany životního prostředí a udržitelného rozvoje; dotace ze státního rozpočtu ve třech podprogramech (A, B, C) na příslušný kalendářní rok.",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": None,
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
 "eligible_applicants": "Nestátní neziskové organizace (spolky, obecně prospěšné společnosti) působící v oblasti ochrany životního prostředí.",
 "typ_zadatele": ["neziskovka"], "cilova_skupina": ["veřejnost"],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "jednoleta",
 "how_to_apply": "Veřejné výběrové řízení je obvykle vyhlašováno v roce předcházejícím roku realizace; žádosti přes elektronický systém Grantys MŽP.",
 "required_attachments": [], "cislo_vyzvy": None, "source_doc": B + "/program-na-podporu-projektu-nno",
 "kontakt": {"osoba": "Petra Nováková Sádková", "email": "petra.novakova@mzp.gov.cz", "telefon": "267 122 141"},
 "evidence": {
   "title": "Program na podporu projektů NNO",
   "focus_area": "Ministerstvo životního prostředí dlouhodobě podporuje aktivity nestátních neziskových organizací (NNO) v oblasti ochrany životního prostředí a udržitelného rozvoje",
   "eligible_applicants": "Dotace na projekty nestátních neziskových organizací jsou ze státního rozpočtu poskytovány ve třech podprogramech"}}

# ---- konkrétní NNO výzvy ----
def nno(title, suf, deadline, dl_ctx, castky, vyse, focus, oblast, extra_ev=None, obdobi="rok 2026"):
    ev = {"title": title.split(" – ")[0] if " – " in title else title,
          "deadline": dl_ctx, "how_to_apply": "Grantys MŽP"}
    if extra_ev:
        ev.update(extra_ev)
    return {
     "title": title, "oblast": oblast, "focus_area": focus,
     "open_from": None, "deadline": deadline,
     "deadliny": [{"datum": deadline, "kontext": dl_ctx}],
     "obdobi_realizace": obdobi,
     "castky": castky, "vyse_hlavni_czk": vyse, "spoluucast": True,
     "eligible_applicants": "Nestátní neziskové organizace (spolky, obecně prospěšné společnosti) působící v oblasti ochrany životního prostředí a udržitelného rozvoje.",
     "typ_zadatele": ["neziskovka"], "cilova_skupina": ["veřejnost"],
     "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
     "rezim_prijmu": "kolova", "delka": "jednoleta",
     "how_to_apply": "Projekty se podávají prostřednictvím elektronického systému Grantys MŽP a opis žádosti se doručuje datovou schránkou na MŽP.",
     "required_attachments": ["Formulář identifikace osob", "Přehled pozemků dotčených projektem"],
     "cislo_vyzvy": None, "source_doc": B + "/program-na-podporu-projektu-nno/" + suf,
     "kontakt": {"osoba": "Mgr. Petra Nováková Sádková", "email": "petra.novakova@mzp.gov.cz", "telefon": None},
     "dokumenty": [{"popis": "Text výzvy", "role": "vyhlaseni"},
                   {"popis": "Příručka pro žadatele a příjemce", "role": "pravidla_podminky"},
                   {"popis": "Manuál systému Grantys MŽP", "role": "metodika"}],
     "evidence": ev}

out["grant_15"] = nno(
 "Výzva Programu na podporu projektů NNO pro rok 2026 – Podprogram A", "vyzva-programu-na-podporu-projektu-nno-pro-1",
 "2025-09-30", "Příjem žádostí končí 30. září 2025 ve 23:59:59.",
 [{"typ": "min_zadatel", "hodnota": 50000, "kontext": "Minimální výše dotace na jeden projekt je 50 tis. Kč"},
  {"typ": "max_zadatel", "hodnota": 300000, "kontext": "maximální výše dotace na jeden projekt činí 300 tis. Kč"},
  {"typ": "mira_pct", "hodnota": 70, "kontext": "Dotace může tvořit maximálně 70 % celkových nákladů na realizaci projektu."}],
 300000,
 "Neinvestiční projekty NNO ve 12 tématech: ochrana přírody a biodiverzity, vliv životního prostředí na lidské zdraví, adaptace na klimatickou změnu, environmentální vzdělávání, výchova a osvěta a zapojování dobrovolníků.",
 ["prostředí", "vzdělávání", "zdraví"],
 extra_ev={"vyse_hlavni_czk": "maximální výše dotace na jeden projekt činí 300 tis. Kč",
           "castky": "Minimální výše dotace na jeden projekt je 50 tis. Kč, maximální výše dotace na jeden projekt činí 300 tis. Kč"})

out["grant_16"] = nno(
 "Výzva Programu na podporu projektů NNO pro rok 2026 – Podprogram C (participace)", "vyzva-programu-na-podporu-projektu-nno-pro-2",
 "2025-09-30", "Příjem žádostí končí 30. září 2025 ve 23:59:59.",
 [{"typ": "min_zadatel", "hodnota": 100000, "kontext": "Minimální výše dotace na jeden projekt je 100 tis. Kč"},
  {"typ": "max_zadatel", "hodnota": 500000, "kontext": "maximální výše dotace na jeden projekt činí 500 tis. Kč"},
  {"typ": "mira_pct", "hodnota": 70, "kontext": "Dotace může tvořit maximálně 70 % celkových nákladů na realizaci projektu."}],
 500000,
 "Dlouhodobé systémové projekty veřejně prospěšného charakteru zaměřené na metodické, koordinační, analytické a expertní činnosti environmentálních nástrojů strategického řízení (Státní politika životního prostředí ČR 2030).",
 ["prostředí", "vzdělávání"],
 extra_ev={"vyse_hlavni_czk": "maximální výše dotace na jeden projekt činí 500 tis. Kč",
           "castky": "Minimální výše dotace na jeden projekt je 100 tis. Kč, maximální výše dotace na jeden projekt činí 500 tis. Kč"})

out["grant_17"] = nno(
 "Výzva Programu na podporu projektů NNO pro rok 2025 – Podprogram A", "vyzva-programu-na-podporu-projektu-nno-pro-0",
 "2024-10-14", "Příjem žádostí končí 14. října 2024 ve 23:59:59.",
 [{"typ": "min_zadatel", "hodnota": 50000, "kontext": "Minimální výše dotace na jeden projekt je 50 tis. Kč"},
  {"typ": "max_zadatel", "hodnota": 300000, "kontext": "maximální výše dotace na jeden projekt činí 300 tis. Kč"},
  {"typ": "mira_pct", "hodnota": 70, "kontext": "Dotace může tvořit maximálně 70 % celkových nákladů na realizaci projektu."}],
 300000,
 "Neinvestiční projekty NNO ve 12 tématech: ochrana přírody a biodiverzity, vliv životního prostředí na lidské zdraví, adaptace na klimatickou změnu, environmentální vzdělávání, výchova a osvěta a zapojování dobrovolníků.",
 ["prostředí", "vzdělávání", "zdraví"], obdobi="rok 2025",
 extra_ev={"vyse_hlavni_czk": "maximální výše dotace na jeden projekt činí 300 tis. Kč",
           "castky": "Minimální výše dotace na jeden projekt je 50 tis. Kč, maximální výše dotace na jeden projekt činí 300 tis. Kč"})

out["grant_18"] = nno(
 "Výzva programu na podporu koordinačních projektů NNO pro rok 2025 – Podprogram B", "vyzva-programu-na-podporu-koordinacnich",
 "2024-10-14", "Příjem žádostí končí 14. října 2024 ve 23:59:59.",
 [{"typ": "max_zadatel", "hodnota": 3000000, "kontext": "Téma I. Koordinace podpory biodiverzity – maximální výše dotace 3 000 tis. Kč."},
  {"typ": "max_zadatel", "hodnota": 2000000, "kontext": "Téma II. Koordinace podpory pozemkových spolků – maximální výše dotace 2 000 tis. Kč."}],
 3000000,
 "Finanční podpora spolků a obecně prospěšných společností zajišťujících koordinační činnost lokálně významných projektů NNO (Téma I: koordinace podpory biodiverzity, Téma II: koordinace podpory pozemkových spolků).",
 ["prostředí"], obdobi="rok 2025",
 extra_ev={"vyse_hlavni_czk": "Téma I. Koordinace podpory biodiverzity – maximální výše dotace 3 000 tis. Kč",
           "castky": "Téma I. Koordinace podpory biodiverzity – maximální výše dotace 3 000 tis. Kč. Téma II. Koordinace podpory pozemkových spolků – maximální výše dotace 2 000 tis. Kč",
           "eligible_applicants": "finanční podpora spolků a obecně prospěšných společností"})
# Podprogram B = koordinační projekty spolků a o.p.s. (ne všechny NNO)
out["grant_18"]["eligible_applicants"] = "Spolky a obecně prospěšné společnosti, které mohou zajistit koordinační činnost lokálně významných projektů realizovaných nestátními neziskovými organizacemi."

out["grant_19"] = nno(
 "Výzva Programu na podporu projektů NNO pro rok 2025 – Podprogram C", "vyzva-programu-na-podporu-projektu-nno-pro",
 "2024-10-14", "Příjem žádostí končí 14. října 2024 ve 23:59:59.",
 [], None,
 "Dlouhodobé systémové projekty veřejně prospěšného charakteru zaměřené na metodické, koordinační, analytické a expertní činnosti v oblasti environmentálního vzdělávání, výchovy a osvěty (EVVO) a environmentálního poradenství (EP), s vazbou na Státní program EVVO.",
 ["prostředí", "vzdělávání"], obdobi="rok 2025")

os.makedirs("data/mzp_out", exist_ok=True)
for k, v in out.items():
    json.dump(v, open(f"data/mzp_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out), "extraction files to data/mzp_out/ :", ",".join(sorted(out)))
