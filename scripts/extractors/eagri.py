#!/usr/bin/env python3
# Vrstva 2 extrakce pro eAGRI / Ministerstvo zemědělství (mze.gov.cz, custom parser scripts/eagri.py).
# 10 národních dotačních programů. Indexy grant_NN = data/eagri_in/grant_NN.json (join přes basename).
import json, os

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
out = {}

out["grant_00"] = {
 "title": "Údržba a obnova kulturních a venkovských prvků pro rok 2026 (program 129 670)",
 "oblast": ["příroda a krajina", "kultura", "venkov"],
 "focus_area": "Údržba a obnova stávajících kulturních a venkovských prvků venkovské krajiny (podprogram 129 672 – drobné sakrální a historické prvky).",
 "open_from": None, "deadline": "2026-02-15",
 "deadliny": [{"datum": "2026-02-15", "kontext": "do 15. února 2026"}],
 "obdobi_realizace": "rok 2026",
 "castky": [{"typ": "min_zadatel", "hodnota": 15000, "kontext": "Minimální hodnota požadované dotace činí 15 000 Kč."},
            {"typ": "max_zadatel", "hodnota": 400000, "kontext": "Maximální hodnota poskytnuté dotace činí 400 000 Kč."},
            {"typ": "mira_pct", "hodnota": 70, "kontext": "Druhá úroveň dotace je max. 70 % ze způsobilých výdajů, pokud se předmět dotace nachází v obci do 2000 obyvatel."}],
 "vyse_hlavni_czk": 400000, "spoluucast": True,
 "eligible_applicants": "Vlastník kulturního či venkovského prvku venkovské krajiny – obec (město, městys) i další fyzické a právnické osoby.",
 "typ_zadatele": ["obec_verejny_subjekt", "fyzicka_osoba", "neziskovka"], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "jednoleta",
 "how_to_apply": "Žádost se podává na Ministerstvo zemědělství (podatelna MZe / datová schránka); podrobnosti v Zásadách programu 129 670 a v Informaci pro žadatele k výzvě 129 672-26.",
 "required_attachments": [], "cislo_vyzvy": "129 672-26",
 "source_doc": "https://mze.gov.cz/public/portal/mze/dotace/narodni-dotace/dotace-na-udrzbu-a-obnovu-kulturnich-a-1/dotace-na-udrzbu-a-obnovu-kulturnich-a-venkovskych-prvku-pro-rok-2026",
 "evidence": {
   "title": "Dotace na údržbu a obnovu kulturních a venkovských prvků pro rok 2026",
   "deadline": "do 15. února 2026",
   "castky": "Minimální hodnota požadované dotace činí 15 000 Kč.",
   "vyse_hlavni_czk": "Maximální hodnota poskytnuté dotace činí 400 000 Kč."}}

out["grant_01"] = {
 "title": "Údržba a obnova kulturních a venkovských prvků pro rok 2025 (program 129 670)",
 "oblast": ["příroda a krajina", "kultura", "venkov"],
 "focus_area": "Údržba a obnova stávajících kulturních a venkovských prvků venkovské krajiny (podprogram 129 672) – ročník 2025.",
 "open_from": None, "deadline": "2025-02-18",
 "deadliny": [{"datum": "2025-02-18", "kontext": "Zásobník žádostí ke dni 18. 2. 2025"}],
 "obdobi_realizace": "rok 2025",
 "castky": [{"typ": "max_zadatel", "hodnota": 300000, "kontext": "Maximální výše podpory na jednotlivou žádost byla oproti roku 2025 zvýšena z 300 tis. Kč na 400 tis. (tj. v roce 2025 činila 300 tis. Kč)."}],
 "vyse_hlavni_czk": 300000, "spoluucast": True,
 "eligible_applicants": "Vlastník kulturního či venkovského prvku venkovské krajiny – obec (město, městys) i další fyzické a právnické osoby.",
 "typ_zadatele": ["obec_verejny_subjekt", "fyzicka_osoba", "neziskovka"], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "jednoleta",
 "how_to_apply": "Žádost se podává na Ministerstvo zemědělství dle Zásad programu 129 670 a Informace pro žadatele k výzvě 129 672-25.",
 "required_attachments": [], "cislo_vyzvy": "129 672-25",
 "source_doc": "https://mze.gov.cz/public/portal/mze/dotace/narodni-dotace/dotace-na-udrzbu-a-obnovu-kulturnich-a-1/dotace-na-udrzbu-a-obnovu-kulturnich-a-venkovskych-prvku-pro-rok-2025",
 "dalsi_datumy": [{"datum": "2026-01-22", "popis": "Ukončený zásobník žádostí ke dni 22. 1. 2026."}],
 "evidence": {
   "title": "Dotace na údržbu a obnovu kulturních a venkovských prvků pro rok 2025",
   "deadline": "Zásobník žádostí ke dni 18. 2. 2025"}}

out["grant_02"] = {
 "title": "Dotační program 129 720 Centra odborné přípravy 2024–2028 (výzva pro rok 2026)",
 "oblast": ["vzdělávání", "zemědělství"],
 "focus_area": "Podpora pořízení moderních učebních pomůcek vybraných center odborné přípravy (zemědělských a lesnických škol).",
 "open_from": "2026-01-12", "deadline": "2026-03-11",
 "deadliny": [{"datum": "2026-03-11", "kontext": "Žádosti o dotaci budou přijímány v termínu od 12. ledna 2026 a po změně Výzvy až do 11. března 2026."}],
 "obdobi_realizace": "2024–2028",
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
 "eligible_applicants": "Vybraná centra odborné přípravy (zemědělské a lesnické školy) – okruh oprávněných žadatelů je dán přílohou „Centra odborné přípravy 2024-2028, jmenný seznam“.",
 "typ_zadatele": ["skola_vyzkumna_org"], "cilova_skupina": ["žáci"],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "viceleta",
 "how_to_apply": "Žádost o dotaci dle Výzvy programu 129 720 (č. j. MZE-90968/2025-13133); Zpráva o pořízení učebních pomůcek se předkládá datovou schránkou MZe.",
 "required_attachments": [], "cislo_vyzvy": "MZE-90968/2025-13133",
 "source_doc": "https://mze.gov.cz/public/portal/mze/dotace/narodni-dotace/dotace-centra-odborne-pripravy/dotacni-program-129-720-centra-odborne-pripravy-2024-2028",
 "evidence": {
   "title": "Dotační program 129 720 Centra odborné přípravy 2024-2028",
   "deadline": "Žádosti o dotaci budou přijímány v termínu od 12. ledna 2026 a po změně Výzvy až do 11. března 2026.",
   "eligible_applicants": "Okruh oprávněných žadatelů o dotaci je uveden v příloze Centra odborné přípravy 2024-2028, jmenný seznam."}}

out["grant_03"] = {
 "title": "Národní dotace podle § 2 a § 2d zákona o zemědělství (Zásady pro rok 2026)",
 "oblast": ["zemědělství", "potravinářství", "venkov"],
 "focus_area": "Dotační programy MZe na udržování výrobního potenciálu zemědělství, podporu chovu a pěstování, kvalitu a bezpečnost potravin, poradenství a vzdělávání – stanovené Zásadami na příslušný kalendářní rok.",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": "rok 2026",
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": "Zejména zemědělští podnikatelé, chovatelé, pěstitelé a další subjekty vymezené jednotlivými dotačními programy v Zásadách (žádosti se podávají přes Portál farmáře SZIF).",
 "typ_zadatele": ["osvc_podnikatel", "firma", "neziskovka"], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "jednoleta",
 "how_to_apply": "Žádosti o jednotlivé dotační tituly se podávají dle Zásad pro daný rok, zpravidla prostřednictvím Portálu farmáře SZIF.",
 "required_attachments": [], "cislo_vyzvy": None,
 "source_doc": "https://mze.gov.cz/public/portal/mze/dotace/narodni-dotace/zasady-zemedelstvi-potravinarstvi",
 "evidence": {
   "title": "Zásady, kterými se stanovují podmínky pro poskytování dotací na základě § 2 a § 2d zákona č. 252/1997 Sb., o zemědělství",
   "focus_area": "jsou vydávány Ministerstvem zemědělství na příslušný kalendářní rok v návaznosti na schválený rozpočet"}}

out["grant_04"] = {
 "title": "Podpora projektů nestátních neziskových organizací z kapitoly Ministerstva zemědělství (výzva pro rok 2026)",
 "oblast": ["zemědělství", "venkov", "vzdělávání"],
 "focus_area": "Dotace na projekty nestátních neziskových organizací v působnosti Ministerstva zemědělství (zemědělství, lesnictví, vodní hospodářství, venkov).",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": "rok 2026",
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
 "eligible_applicants": "Nestátní neziskové organizace (dle Zásad vlády pro poskytování dotací NNO a Zásad MZe).",
 "typ_zadatele": ["neziskovka"], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "jednorazova_vyzva", "delka": "jednoleta",
 "how_to_apply": "Na základě výzvy k podání žádostí vyhlášené 29. srpna 2025; vychází ze zákona č. 218/2000 Sb. a Zásad vlády pro poskytování dotací NNO.",
 "required_attachments": [], "cislo_vyzvy": None,
 "source_doc": "https://mze.gov.cz/public/portal/mze/dotace/narodni-dotace/dotace-nestatnim-neziskovym-organizacim",
 "dalsi_datumy": [{"datum": "2025-08-29", "popis": "Výzva k podání žádostí na podporu projektů NNO pro rok 2026 vyhlášena 29. srpna 2025."}],
 "evidence": {
   "title": "Ministerstvo zemědělství vyhlašuje VÝZVU K PODÁNÍ ŽÁDOSTÍ NA PODPORU PROJEKTŮ NESTÁTNÍCH NEZISKOVÝCH ORGANIZACÍ PRO ROK 2026",
   "eligible_applicants": "z usnesení vlády ze dne 1. června 2020 č. 591, o Zásadách vlády pro poskytování dotací ze státního rozpočtu České republiky nestátním neziskovým organizacím"}}

out["grant_05"] = {
 "title": "Podpora retence vody v krajině – rybníky a vodní nádrže – 2. etapa (program 129 380)",
 "oblast": ["voda", "příroda a krajina", "zemědělství"],
 "focus_area": "Zadržení vody v krajině, posílení protipovodňových funkcí rybníků a zvýšení jejich bezpečnosti – výstavba, obnova a rekonstrukce rybníků nad 2 ha a odbahnění rybníků 2–30 ha.",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": "2024–2028",
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
 "eligible_applicants": "Právnická či fyzická osoba zapsaná v evidenci zemědělského podnikatele, vybrané univerzity a školní zařízení, organizační jednotky ČRS nebo MRS, rybářská sdružení či spolky (podmínka hospodaření na 15 ha vodních ploch u rekonstrukcí).",
 "typ_zadatele": ["osvc_podnikatel", "firma", "skola_vyzkumna_org", "neziskovka"], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "viceleta",
 "how_to_apply": "Dle Pravidel MZe (č. j. MZE-51981/2025-15152); formuláře EDS se vytvářejí na https://isprofin.mfcr.cz. Kontakt: Oddělení vody v krajině a rozpočtu.",
 "required_attachments": [], "cislo_vyzvy": "129 380",
 "kontakt": {"osoba": "Ing. Karel Pelikán", "email": "karel.pelikan@mze.gov.cz", "telefon": "221 813 048"},
 "source_doc": "https://mze.gov.cz/public/portal/mze/dotace/narodni-dotace/dotace-ve-vodnim-hospodarstvi/rybniky",
 "evidence": {
   "title": "Podpora retence vody v krajině – rybníky a vodní nádrže – 2. etapa",
   "focus_area": "je zadržení vody v krajině, posílení protipovodňových funkcí rybníků a zvýšení jejich bezpečnosti.",
   "eligible_applicants": "může být žadatelem o podporu z programu 129 380 pouze právnická či fyzická osoba, zapsaná v evidenci zemědělského podnikatele, dále vybrané univerzity a školní zařízení, organizační jednotky ČRS nebo MRS nebo rybářská sdružení či spolky",
   "obdobi_realizace": "Doba trvání programu 129 380 podle schválené dokumentace je v rozmezí let 2024–2028."}}

out["grant_06"] = {
 "title": "Podpora opatření na malých vodních nádržích a drobných vodních tocích – 3. etapa (program 129 490)",
 "oblast": ["voda", "příroda a krajina"],
 "focus_area": "Zlepšení technického stavu malých vodních nádrží a drobných vodních toků, posílení retence vody v krajině a bezpečnosti při zvýšených průtocích.",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": "2024–2028",
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
 "eligible_applicants": "Dle podprogramu (např. 129 493 obce); žádosti se podávají na základě Výzvy správce programu prostřednictvím Jednotného dotačního portálu.",
 "typ_zadatele": ["obec_verejny_subjekt"], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "viceleta",
 "how_to_apply": "Žádosti se podávají na základě Výzvy správce programu prostřednictvím Jednotného dotačního portálu. Kontakt: Oddělení odstraňování povodňových škod a ostatních opatření ve vodním hospodářství.",
 "required_attachments": [], "cislo_vyzvy": "129 490",
 "source_doc": "https://mze.gov.cz/public/portal/mze/dotace/narodni-dotace/dotace-ve-vodnim-hospodarstvi/drobne-vodni-toky-a-male-vodni-nadrze",
 "dalsi_datumy": [{"datum": "2025", "popis": "Alokace pro I. Výzvu byla vyčerpána; aktuálně neprobíhá příjem nových žádostí."}],
 "evidence": {
   "title": "Podpora opatření na malých vodních nádržích a drobných vodních tocích",
   "focus_area": "je výrazné zlepšení technického stavu malých vodních nádrží a drobných vodních toků, které podpoří vodní režim krajiny, posílí retenci vody v krajině",
   "obdobi_realizace": "je realizován v letech 2024 –2028."}}

out["grant_07"] = {
 "title": "Podpora výstavby a obnovy infrastruktury vodovodů a kanalizací (programy 129 400 / 129 410 / 129 320)",
 "oblast": ["voda", "infrastruktura", "venkov"],
 "focus_area": "Investiční dotace na výstavbu, modernizaci, rekonstrukci a obnovu vodovodů a kanalizací – zabezpečení dostupnosti pitné vody a odvádění odpadních vod, s důrazem na obce do 2000 obyvatel a oblasti ohrožené suchem; podpora odstraňování povodňových škod 2024.",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": "realizace akcí do 31. 12. 2027 / 2028 / 2032 dle programu",
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
 "eligible_applicants": "Obce a vlastníci infrastruktury vodovodů a kanalizací (s důrazem na obce do 2000 obyvatel).",
 "typ_zadatele": ["obec_verejny_subjekt"], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "viceleta",
 "how_to_apply": "Pravidla, podmínky a výzvy jsou uvedeny pod záložkou příslušného programu/podprogramu.",
 "required_attachments": [], "cislo_vyzvy": "129 410 / 129 403 / 129 322",
 "source_doc": "https://mze.gov.cz/public/portal/mze/dotace/narodni-dotace/dotace-ve-vodnim-hospodarstvi/vodovody-a-kanalizace",
 "evidence": {
   "title": "Podpora výstavby a technického zhodnocení infrastruktury vodovodů a kanalizací",
   "focus_area": "Program 129 410 ... je primárně určen pro zvýšení dostupnosti pitné vody z vodovodů pro veřejnou potřebu a zajištění odvádění odpadních vod v obcích s důrazem na nejvíce zanedbané regiony a okresy se zaměřením na obce do 2000 obyvatel.",
   "obdobi_realizace": "Realizace akcí v rámci tohoto Programu musí být ukončena nejdéle do 31.12.2028."}}

out["grant_08"] = {
 "title": "Prevence před povodněmi (dotační program MZe)",
 "oblast": ["voda", "infrastruktura", "bezpečnost"],
 "focus_area": "Realizace opatření zajišťujících systémovou ochranu před povodněmi měst a obcí – zejména výstavba suchých nádrží (poldrů), úpravy na vodních dílech a opatření podél vodních toků v intravilánech.",
 "open_from": None, "deadline": None, "deadliny": [],
 "obdobi_realizace": None,
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
 "eligible_applicants": "Města a obce (resp. správci vodních toků) realizující protipovodňová opatření.",
 "typ_zadatele": ["obec_verejny_subjekt"], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
 "rezim_prijmu": "kolova", "delka": "viceleta",
 "how_to_apply": "Dle pravidel programu „Prevence před povodněmi“ (financováno ze státního rozpočtu ČR).",
 "required_attachments": [], "cislo_vyzvy": None,
 "source_doc": "https://mze.gov.cz/public/portal/mze/dotace/narodni-dotace/dotace-ve-vodnim-hospodarstvi/prevence-pred-povodnemi",
 "evidence": {
   "title": "Dotační program „Prevence před povodněmi“",
   "focus_area": "je zaměřen na realizaci opatření zajišťujících systémovou ochranu před povodněmi městům a obcím z finančních prostředků státního rozpočtu České republiky."}}

out["grant_09"] = {
 "title": "Národní plán obnovy – komponenta 2.6 Ochrana přírody a adaptace na změnu klimatu (Ministerstvo zemědělství)",
 "oblast": ["příroda a krajina", "voda", "klima", "lesnictví"],
 "focus_area": "Udržitelnost zemědělské a lesnické krajiny v kontextu klimatické změny: protipovodňová ochrana, drobné vodní toky a malé vodní nádrže, pozemkové úpravy, budování lesů odolných vůči klimatu a zadržování vody v lese.",
 "open_from": None, "deadline": "2026-08-31",
 "deadliny": [{"datum": "2026-08-31", "kontext": "Žádosti o dotaci bude možné podávat do srpna 2026."}],
 "obdobi_realizace": "způsobilé výdaje uznatelné od 1. února 2020 (RRF, období 2021–2027)",
 "castky": [{"typ": "alokace", "hodnota": 12984000000, "kontext": "Odhadované náklady: 12 984 mil. Kč."}],
 "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": "Dle jednotlivé investice (obce, vlastníci a správci pozemků a lesů, Státní pozemkový úřad a další subjekty realizující opatření komponenty 2.6).",
 "typ_zadatele": ["obec_verejny_subjekt", "osvc_podnikatel", "firma", "neziskovka"], "cilova_skupina": [],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["npo", "eu_fondy"],
 "rezim_prijmu": "kolova", "delka": "viceleta",
 "how_to_apply": "Žádosti o dotaci v rámci jednotlivých investic komponenty 2.6 (do srpna 2026); podpora z Nástroje pro oživení a odolnost (RRF).",
 "required_attachments": [], "cislo_vyzvy": "komponenta 2.6",
 "source_doc": "https://mze.gov.cz/public/portal/mze/dotace/narodni-plan-obnovy",
 "evidence": {
   "title": "Ministerstvo zemědělství je v rámci pilíře „Fyzická infrastruktura a zelená tranzice“ vlastníkem komponenty 2.6 Ochrana přírody a adaptace na změnu klimatu.",
   "deadline": "Žádosti o dotaci bude možné podávat do srpna 2026",
   "castky": "Odhadované náklady: 12 984 mil. Kč."}}

os.makedirs("data/eagri_out", exist_ok=True)
for k, v in out.items():
    json.dump(v, open(f"data/eagri_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out), "extraction files to data/eagri_out/ :", ",".join(sorted(out)))
