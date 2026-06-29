#!/usr/bin/env python3
# Vrstva 2 extrakce pro MMR – národní dotace (mmr.gov.cz; parser scripts/mmr.py). 9 programů.
# VYNECHÁNO: SFPI-overlap (ŽIVEL SFPI, Revitalizace brownfieldů = příjemce SFPI), administrativní
# (Závazky reg. rad, COVID administrace), destinačně-specifické/historické (Jeseníky, České Švýcarsko,
# Státní program CR 2000s), duplicitní ročníky (euroregiony/PORR/NNO 2025). IROP/EU = P3 (mimo).
# amount=null (výše v Výzva PDF). Status NEvyplňuji (počítá kód). Lhůty bez data = aktivní program
# „mezi koly" / DT zveřejňované postupně → unknown (čestné).
import json, os

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW = "Žádost se podává elektronicky (formulář www3.mmr.cz/zad); konzultační servis na ks.crr.gov.cz."
out = {}
def g(idx, **f):
    out[f"grant_{idx:02d}"] = f

g(0, title="Podpora obnovy a rozvoje regionů 2026 (PORR)",
  oblast=["regionální rozvoj", "venkov"],
  focus_area="Zastřešující národní program MMR pro obce – dotační tituly: Podpora obnovy a rozvoje venkova, Vesnice roku, Podpora rozvoje hospodářsky a sociálně ohrožených území, Podpora chytrých měst a obcí a podpora obcí do 3 000, resp. 3 001–10 000 obyvatel.",
  open_from=None, deadline=None,
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Obce (zejména do 3 000 obyvatel, u vybraných dotačních titulů do 10 000), svazky obcí a další subjekty dle jednotlivých dotačních titulů.",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["obyvatelé obcí", "obyvatelé venkova"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="jednoleta", how_to_apply=HOW, cislo_vyzvy="PORR 2026",
  evidence={"title": "Podpora obnovy a rozvoje regionů 2026"})

g(1, title="Obnova německých hrobů 2026",
  oblast=["kulturní dědictví", "regionální rozvoj"],
  focus_area="Dotace na obnovu hrobů německých občanů nebo českých občanů hlásících se k německé menšině a na podporu zachování historické paměti, regionální identity a kulturního dědictví.",
  open_from="2026-01-05", deadline="2026-04-30",
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Vlastníci či správci dotčených hrobů a integrovaných památníků (obce, spolky a další subjekty dle podmínek výzvy); neinvestiční i smíšená dotace.",
  typ_zadatele=["obec_verejny_subjekt", "neziskovka"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="jednoleta", how_to_apply=HOW, cislo_vyzvy="1/2026/117D75",
  evidence={"title": "z programu Obnova německých hrobů", "open_from": "Zahájení příjmu žádostí: 5. ledna 2026", "deadline": "Ukončení příjmu žádostí: 30 . dubna 2026"})

g(2, title="Podpora euroregionů 2026 (odstraňování překážek přeshraniční spolupráce)",
  oblast=["regionální rozvoj", "přeshraniční spolupráce"],
  focus_area="Podpora provozu a aktivit euroregionů v oblasti identifikace a odstraňování překážek přeshraniční spolupráce a zlepšení životních podmínek v příhraničních oblastech.",
  open_from="2025-11-13", deadline="2026-01-29",
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Euroregiony (zájmová sdružení / spolky působící v příhraničních oblastech).",
  typ_zadatele=["neziskovka", "obec_verejny_subjekt"], cilova_skupina=["obyvatelé příhraničí"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="jednoleta", how_to_apply=HOW, cislo_vyzvy="1/2026/Z1720",
  evidence={"title": "programu Podpora euroregionů v oblasti odstraňování překážek přeshraniční spolupráce", "open_from": "Zahájení příjmu žádostí: 13 . listopadu 2025", "deadline": "Ukončení příjmu žádostí: 29 . ledna 2026"})

g(5, title="Podpora pro odstraňování bariér v budovách (bezbariérové obce)",
  oblast=["bezbariérovost", "regionální rozvoj"],
  focus_area="Podpora budování ucelených bezbariérových tras měst a obcí (Národní rozvojový program mobility pro všechny): odstraňování bariér v budovách domů s pečovatelskou službou a v budovách městských a obecních úřadů; součástí je i EUROKLÍČ.",
  open_from=None, deadline=None,
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Obce a města realizující bezbariérové úpravy budov a tras.",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["osoby se zdravotním postižením", "senioři"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="jednoleta", how_to_apply=HOW, cislo_vyzvy="Bezbariérové obce / NRPM",
  evidence={"title": "Podpora pro odstraňování bariér v budovách", "focus_area": "finančně podílí na budování ucelených bezbariérových tras měst a obcí"})

g(6, title="Pevnostní města Terezín a Josefov",
  oblast=["kulturní dědictví", "regionální rozvoj"],
  focus_area="Dotace na obnovu a rozvoj pevnostních měst Terezín a Josefov (regenerace a využití pevnostního dědictví).",
  open_from=None, deadline=None,
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Města Terezín a Josefov (Jaroměř), případně jimi zřizované organizace.",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="jednoleta", how_to_apply=HOW, cislo_vyzvy="Pevnostní města Terezín a Josefov",
  evidence={"title": "Pevnostní města Terezín a Josefov"})

g(11, title="Podpora výkonů rozhodnutí stavebních úřadů",
  oblast=["stavební právo", "regionální rozvoj"],
  focus_area="Dočasná finanční podpora obcím (jejichž úřady jsou obecnými stavebními úřady) na zajištění výkonu rozhodnutí ve veřejném zájmu (náhradní výkon při odstranění stavby, zabezpečovací práce); poskytováno prostřednictvím krajů.",
  open_from=None, deadline=None,
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Obce s obecným stavebním úřadem (prostřednictvím krajů ČR).",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="prubezna", delka="jednoleta", how_to_apply=HOW, cislo_vyzvy="Podpora výkonů rozhodnutí stavebních úřadů",
  evidence={"title": "Program Podpora výkonů rozhodnutí stavebních úřadů"})

g(13, title="Oživení cestovního ruchu podporou infrastruktury cestovního ruchu",
  oblast=["cestovní ruch", "infrastruktura"],
  focus_area="Podpora rozvoje veřejné a doprovodné infrastruktury cestovního ruchu (DT 1 – národní a nadregionální úroveň; DT 2 – v regionech, krajské grantové schéma).",
  open_from=None, deadline=None,
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Subjekty rozvíjející veřejnou infrastrukturu cestovního ruchu; u dotačního titulu DT 2 (krajské grantové schéma) jsou oprávněnými žadateli pouze kraje.",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["turisté", "veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="jednoleta", how_to_apply=HOW, cislo_vyzvy="Oživení CR – infrastruktura",
  evidence={"title": "Oživení cestovního ruchu podporou infrastruktury", "eligible_applicants": "DT 2 - Podpora veřejné infrastruktury CR v regionech (krajské grantové schéma) - opravněnými žadateli jsou pouze kraje"})

g(14, title="Podpora organizací destinačního managementu (DMO) 2025+",
  oblast=["cestovní ruch"],
  focus_area="Systémová podpora řízení cestovního ruchu v ČR – podpora certifikovaných organizací destinačního managementu (DMO) a jejich činnosti.",
  open_from=None, deadline=None,
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Certifikované organizace destinačního managementu (DMO).",
  typ_zadatele=["neziskovka", "obec_verejny_subjekt"], cilova_skupina=["turisté", "veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="jednoleta", how_to_apply=HOW, cislo_vyzvy="DMO 2025+",
  evidence={"title": "Podpora organizací destinačního managementu", "focus_area": "podpora certifikovaných organizací destinačního managementu (DMO) a jejich činnosti"})

g(17, title="Dotace pro nestátní neziskové organizace 2026 (MMR)",
  oblast=["regionální rozvoj", "bydlení", "cestovní ruch"],
  focus_area="Dotace nestátním neziskovým organizacím na veřejně prospěšné činnosti v oblastech MMR: přístupnost staveb, metodická a koncepční podpora v bydlení, udržitelný rozvoj regionů/měst/obcí a udržitelný rozvoj cestovního ruchu.",
  open_from="2026-03-26", deadline="2026-04-27",
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Nestátní neziskové organizace (spolky, obecně prospěšné společnosti, ústavy, nadace a nadační fondy) působící ve veřejně prospěšných činnostech.",
  typ_zadatele=["neziskovka"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="kolova", delka="jednoleta", how_to_apply=HOW, cislo_vyzvy="NNO 2026 (1. a 2. výzva)",
  dalsi_datumy=[{"datum": "2025-11-19", "popis": "1. výzva č. 1/2026/NNO (vyhlášena 19. 11. 2025) – více oblastí podpory"},
                {"datum": "2026-04-27", "popis": "2. výzva č. 2/2026/NNO (26. 3. – 27. 4. 2026) – Udržitelný rozvoj regionů, měst a obcí"}],
  evidence={"title": "vyhlašuje Ministerstvo pro místní rozvoj dne 26. 3. 2026 výzvu č. 2 /2026/NNO", "open_from": "Zahájení příjmu žádostí: 26. března 2026, od 12 hodin", "deadline": "Ukončení příjmu žádostí: 27. dubna 2026"})

os.makedirs("data/mmr_out", exist_ok=True)
for k, v in out.items():
    json.dump(v, open(f"data/mmr_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} grants to data/mmr_out/ (národní dotace; SFPI/EU/administrativní/duplicity vynechány)")
