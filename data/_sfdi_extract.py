#!/usr/bin/env python3
# Vrstva 2 extrakce pro Státní fond dopravní infrastruktury (sfdi.gov.cz; parser scripts/sfdi.py).
# 8 příspěvkových programů (doprava: dotace na infrastrukturu obcí/krajů). VYNECHÁNO grant_08
# Povodňové škody (program neaktivní – příspěvek jen 2020, prázdná pole). Status NEvyplňuji (počítá kód
# z „Termín pro žádosti"). Příspěvky bez pevného deadline („-" / mezi ročníky) → deadline null = unknown.
import json, os

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW = "Žádost o příspěvek se podává dle Pravidel pro poskytování příspěvků z rozpočtu SFDI (elektronicky / datovou schránkou) ve stanovené lhůtě."
out = {}
def g(idx, **f):
    out[f"grant_{idx:02d}"] = f

g(0, title="Příspěvek SFDI na bezbariérové chodníky a zvyšování bezpečnosti chodců",
  oblast=["doprava", "bezpečnost", "bezbariérovost"],
  focus_area="Příspěvek na výstavbu a úpravy chodníků, přechodů a nástupišť MHD se zaměřením na bezbariérovost a bezpečnost chodců.",
  open_from=None, deadline=None,
  castky=[{"typ": "max_zadatel", "hodnota": 20000000}, {"typ": "mira_pct", "hodnota": 75}],
  vyse_hlavni_czk=20000000, spoluucast=True,
  eligible_applicants="Obec nebo organizační složka obce (městský obvod, městská či místní část).",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["chodci", "osoby se zdravotním postižením", "senioři"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="Bezbariérové chodníky",
  evidence={"title": "Bezbariérové chodníky", "vyse_hlavni_czk": "maximálně 20 mil. Kč na žadatele"})

g(1, title="Příspěvek SFDI na výstavbu a opravy cyklistických stezek",
  oblast=["doprava", "cyklodoprava"],
  focus_area="Příspěvek na výstavbu, opravu a značení cyklistických stezek a jízdních pruhů pro cyklisty.",
  open_from=None, deadline=None,
  castky=[{"typ": "mira_pct", "hodnota": 80}, {"typ": "min_zadatel", "hodnota": 1000000}],
  vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Obec, příspěvková organizace zřízená obcí nebo společenství/svazek obcí, kraj, příspěvková organizace nebo obchodní společnost správy a údržby silnic, organizační složka obce.",
  typ_zadatele=["obec_verejny_subjekt", "prispevkova_organizace"], cilova_skupina=["cyklisté", "veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="Cyklostezky",
  evidence={"title": "Cyklostezky", "vyse_hlavni_czk": "minimálně 1 mil. Kč, max. výše neomezená"})

g(2, title="Příspěvek SFDI na úpravy křížení komunikací (mimoúrovňová křížení)",
  oblast=["doprava", "infrastruktura", "bezpečnost"],
  focus_area="Příspěvek na stavební úpravy objektů mimoúrovňového křížení místních/účelových komunikací s nadřazenou infrastrukturou (lávky, mosty, podchody, nadjezdy).",
  open_from=None, deadline="2026-07-15",
  castky=[{"typ": "max_zadatel", "hodnota": 150000000}, {"typ": "mira_pct", "hodnota": 100}],
  vyse_hlavni_czk=150000000, spoluucast=True,
  eligible_applicants="Obce, jimi zřízené příspěvkové organizace či založené obchodní společnosti pro dopravní stavby; svazky obcí; kraje a jejich organizace; ŘSD; Správa železnic; státní podniky povodí.",
  typ_zadatele=["obec_verejny_subjekt", "prispevkova_organizace"], cilova_skupina=["účastníci silničního provozu", "veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="Křížení komunikací 2026",
  evidence={"title": "Křížení komunikací", "deadline": "Termín pro žádosti: 15.7.2026", "vyse_hlavni_czk": "maximálně 150 mil. Kč na žadatele"})

g(3, title="Příspěvek SFDI na zvyšování bezpečnosti silnic II. a III. třídy",
  oblast=["doprava", "bezpečnost"],
  focus_area="Příspěvek krajům na odstranění nehodových lokalit a obnovu dopravního značení u železničních přejezdů na silnicích II. a III. třídy.",
  open_from=None, deadline="2026-07-15",
  castky=[{"typ": "max_zadatel", "hodnota": 15000000}, {"typ": "mira_pct", "hodnota": 85}],
  vyse_hlavni_czk=15000000, spoluucast=True,
  eligible_applicants="Kraj, příspěvkové organizace zřízené krajem, nebo obchodní společnosti založené krajem za účelem hospodaření s majetkem v oblasti dopravy.",
  typ_zadatele=["obec_verejny_subjekt", "prispevkova_organizace"], cilova_skupina=["účastníci silničního provozu", "veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="Bezpečnost silnic II/III 2026",
  evidence={"title": "Bezpečnost silnic II. a III. třídy", "deadline": "Termín pro žádosti: 15.7.2026", "vyse_hlavni_czk": "maximálně 15. mil. Kč na kraj"})

g(4, title="Příspěvek SFDI na zabezpečení letišť",
  oblast=["doprava", "letecká doprava", "bezpečnost"],
  focus_area="Příspěvek provozovatelům civilních letišť na technické prostředky k ochraně civilního letectví před protiprávními činy.",
  open_from=None, deadline="2026-08-03",
  castky=[{"typ": "max_zadatel", "hodnota": 20000000}, {"typ": "mira_pct", "hodnota": 85}],
  vyse_hlavni_czk=20000000, spoluucast=True,
  eligible_applicants="Právnická nebo fyzická osoba se sídlem nebo organizační složkou v ČR, která je provozovatelem civilního letiště.",
  typ_zadatele=["firma", "fyzicka_osoba"], cilova_skupina=["cestující letecké dopravy"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="Zabezpečení letišť 2026",
  evidence={"title": "Zabezpečení letišť", "deadline": "Termín pro žádosti: 3.8.2026", "vyse_hlavni_czk": "max. 20 mil Kč"})

g(5, title="Příspěvek SFDI na multimodální překladiště",
  oblast=["doprava", "vodní doprava", "logistika"],
  focus_area="Příspěvek na infrastrukturu multimodálních překladišť (přístavní infrastruktura). Pro rok 2024 a další se s výzvou nepočítá.",
  open_from=None, deadline="2023-05-31",
  castky=[{"typ": "mira_pct", "hodnota": 80}], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Právnická osoba se sídlem/pobočkou v ČR, vlastník a provozovatel přístavní infrastruktury (nebo s adekvátním právem stavby/služebností).",
  typ_zadatele=["firma"], cilova_skupina=["logistika", "veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="Multimodální překladiště",
  dalsi_castky=[{"castka": "2 mil. EUR", "popis": "max. výše podpory na akci (ekvivalent dle kurzu ECB)"}],
  evidence={"title": "Multimodální překladiště", "deadline": "do 31. 05. 2023, pro rok 2024 a další není počítáno s další výzvou"})

g(6, title="Příspěvek SFDI na vybavení drážních vozidel jednotkami ETCS",
  oblast=["doprava", "železniční doprava"],
  focus_area="Příspěvek na zástavbu palubních jednotek ETCS do drážních vozidel (návaznost na grantovou dohodu CEF2) pro období 2024–2028.",
  open_from=None, deadline="2027-03-31",
  castky=[{"typ": "max_zadatel", "hodnota": 8500000}, {"typ": "mira_pct", "hodnota": 85}],
  vyse_hlavni_czk=8500000, spoluucast=True,
  eligible_applicants="Právnická či fyzická osoba se sídlem/složkou v ČR, vlastník nebo provozovatel drážního vozidla, který má schválenou grantovou dohodu z nástroje CEF2.",
  typ_zadatele=["firma"], cilova_skupina=["cestující železniční dopravy"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["eu_fondy", "narodni_rozpocet"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="Jednotky ETCS 2024–2028",
  dalsi_datumy=[{"datum": "2028-03-31", "popis": "poslední z navazujících termínů (31.3.2025/2026/2027/2028)"}],
  evidence={"title": "Jednotky ETCS", "deadline": "do 15. 07. 2024 (dále pak do 31. 03. 2025, 31. 03. 2026, 31. 03. 2027 a 31. 03. 2028)", "vyse_hlavni_czk": "8 500 tis. Kč na jedno drážní vozidlo"})

g(7, title="Příspěvek SFDI na nové technologie (průzkumné a projektové práce v dopravní infrastruktuře)",
  oblast=["doprava", "věda a výzkum", "infrastruktura"],
  focus_area="Příspěvek na průzkumné/projektové práce a studijní a expertní činnosti – nové diagnostické metody a aplikace v dopravní infrastruktuře.",
  open_from=None, deadline=None,
  castky=[{"typ": "mira_pct", "hodnota": 75}], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Organizační složky státu, státní příspěvkové/organizace hospodařící s majetkem dopravní infrastruktury, kraje a další osoby provádějící výstavbu/opravy dopravní infrastruktury.",
  typ_zadatele=["obec_verejny_subjekt", "prispevkova_organizace"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="Nové technologie",
  evidence={"title": "Nové technologie", "eligible_applicants": "organizační složky státu"})

os.makedirs("data/sfdi_out", exist_ok=True)
for k, v in out.items():
    json.dump(v, open(f"data/sfdi_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} grants to data/sfdi_out/ (skipped grant_08 Povodňové škody = neaktivní)")
