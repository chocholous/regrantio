#!/usr/bin/env python3
# Vrstva 2 extrakce pro Státní fond životního prostředí (sfzp.gov.cz; parser scripts/sfzp.py).
# 19 unikátních výzev (13 WP FN/PU stránek + 8 Modernizační fond detailů). grant_02 (2/2024 FN) a
# grant_03 (1/2024 FN) jsou TENČÍ DUPLIKÁTY bohatších grant_04 (2/2024 FN Půjčka) resp. grant_13
# (HOUSEnerg 1/2024 FN) → NEzapisují se (join by basename → ingest je passne). Status NEvyplňuji
# (počítá kód z deadline). Evidence = verbatim řádky z čistého body (resolve_citations je whitespace-insensitive).
import json, os

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
def kraj(*names):
    return [{"nazev": n, "obec": None, "okres": None, "kraj": n, "celostatni": False} for n in names]
HOW_PU = "Žádost o půjčku se podává elektronicky prostřednictvím elektronického formuláře IFN Bene-Fill, následně písemně nebo datovou schránkou s přílohami."
HOW_MF = "Elektronicky prostřednictvím Agendového informačního systému SFŽP ČR (AIS SFŽP ČR) na zadosti.sfzp.gov.cz."

out = {}
def g(idx, **f):
    out[f"grant_{idx:02d}"] = f

# ---- A) WP FN/PU výzvy (financní nástroje / půjčky) -----------------------------------
g(0, title="Finanční nástroj pro regeneraci brownfieldů – č. 1/2026 FN",
  oblast=["prostředí", "regionální rozvoj", "infrastruktura"],
  focus_area="Obnova brownfieldů v Ústeckém a Karlovarském kraji (občanská vybavenost, školy, kulturní a komunitní centra) kombinací bezúročného úvěru a dotace z OP Spravedlivá transformace.",
  open_from="2026-03-12", deadline="2026-10-30",
  castky=[{"typ": "alokace", "hodnota": 1550000000}, {"typ": "max_zadatel", "hodnota": 300000000}, {"typ": "mira_pct", "hodnota": 100}],
  vyse_hlavni_czk=300000000, spoluucast=False,
  eligible_applicants="Široký okruh veřejných subjektů; pro aktivity b) a c) také obchodní společnosti, družstva a podnikající fyzické osoby (definice v kapitole 3 Výzvy).",
  typ_zadatele=["obec_verejny_subjekt", "firma", "osvc_podnikatel"],
  cilova_skupina=["veřejnost"], region=kraj("Ústecký kraj", "Karlovarský kraj"),
  forma_podpory=["dotace", "zapujcka_uver"], zdroj_financovani=["eu_fondy"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW_MF, cislo_vyzvy="1/2026 FN",
  evidence={"title": "Finanční nástroj pro regeneraci brownfieldů", "deadline": "Příjem žádostí probíhá od 12. března 2026 do 30. října 2026", "vyse_hlavni_czk": "Maximální výše CZV činí v případě Ústeckého kraje 300 mil. Kč"})

g(1, title="Finanční nástroj pro oběhové hospodářství – č. 1/2025 FN",
  oblast=["prostředí", "oběhové hospodářství", "odpady"],
  focus_area="Podpora projektů na zvýšení kapacity pro zpracování vybraných druhů odpadů formou finanční záruky za 50 % jistiny komerčního úvěru v kombinaci s dotací (OPŽP 2021–2027).",
  open_from="2025-08-01", deadline="2027-01-06",
  castky=[{"typ": "alokace", "hodnota": 930000000}, {"typ": "max_zadatel", "hodnota": 500000000}, {"typ": "mira_pct", "hodnota": 20}],
  vyse_hlavni_czk=930000000, spoluucast=True,
  eligible_applicants="Obchodní subjekty a podniky zapojené do oběhového hospodářství; obce, kraje, svazky obcí a další subjekty definované v kapitole 3 Výzvy.",
  typ_zadatele=["firma", "obec_verejny_subjekt"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["zapujcka_uver", "dotace"], zdroj_financovani=["eu_fondy"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW_MF, cislo_vyzvy="1/2025 FN",
  evidence={"title": "Finanční nástroj pro oběhové hospodářství", "deadline": "1. 8. 2025 – 6. 1. 2027", "vyse_hlavni_czk": "930 milionů Kč"})

g(4, title="Výzva č. 2/2024 FN: Půjčka na předfinancování výdajů projektů z 28., 46. a 47. dotační výzvy OPŽP 2021+ a posílení vlastních zdrojů v 160. výzvě OPŽP 2014+",
  oblast=["prostředí"],
  focus_area="Půjčka neziskovým subjektům na předfinancování výdajů projektů OPŽP 2021+ a posílení vlastních zdrojů projektů ze 160. výzvy OPŽP 2014+.",
  open_from="2024-09-25", deadline="2024-12-31",
  castky=[{"typ": "alokace", "hodnota": 103000000}], vyse_hlavni_czk=103000000, spoluucast=False,
  eligible_applicants="Zapsané spolky, pobočné spolky a obecně prospěšné společnosti se schváleným projektem v předmětných výzvách OPŽP.",
  typ_zadatele=["neziskovka"], cilova_skupina=["neziskové organizace"], region=CR,
  forma_podpory=["zapujcka_uver"], zdroj_financovani=["eu_fondy"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW_PU, cislo_vyzvy="2/2024 FN",
  evidence={"title": "Půjčka na předfinancování výdajů projektů", "deadline": "Od 25. 9. 2024 (10 hodin) do 31. 12. 2024 (14 hodin)", "vyse_hlavni_czk": "Cíl 1: 100 mil. Kč"})

g(5, title="Výzva č. 1/2024 PU: Půjčka pro úspěšné projekty ve výzvě NPŽP 6/2024 a 7/2024 a programu podpory Ministerstva zemědělství",
  oblast=["prostředí", "vodní hospodářství"],
  focus_area="Půjčka na posílení vlastních zdrojů obcí do 2 tis. obyvatel na vodohospodářské projekty z výzev NPŽP 6/2024 a 7/2024 a programu MZe 129 410.",
  open_from="2024-06-15", deadline="2024-09-16",
  castky=[{"typ": "alokace", "hodnota": 2000000000}], vyse_hlavni_czk=2000000000, spoluucast=True,
  eligible_applicants="Obce do 2 tis. obyvatel se schválenou dotací ve výzvě 6/2024 nebo 7/2024 NPŽP, popř. v programu MZe.",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["obyvatelé obcí"], region=CR,
  forma_podpory=["zapujcka_uver"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW_PU, cislo_vyzvy="1/2024 PU",
  evidence={"title": "Půjčka pro úspěšné projekty ve výzvě NPŽP", "deadline": "Od 15. 6. 2024 (10 hodin) do 16. 9. 2024 (14 hodin)", "vyse_hlavni_czk": "2 miliardy Kč"})

g(6, title="Výzva 1/2022 PU: Půjčka na projekty podpořené dotací z OPŽP 2021–2027",
  oblast=["prostředí", "vodní hospodářství", "vzdělávání"],
  focus_area="Zvýhodněná půjčka na posílení vlastních zdrojů u vodohospodářských projektů a modernizace vzdělávacích environmentálních center podpořených z OPŽP 2021–2027.",
  open_from="2022-09-01", deadline="2023-05-31",
  castky=[{"typ": "alokace", "hodnota": 844500000}, {"typ": "jine", "hodnota": 50000000}], vyse_hlavni_czk=50000000, spoluucast=True,
  eligible_applicants="Obce do 2 000 obyvatel a další oprávnění příjemci se schválenou dotací v OPŽP 2021–2027 (specifický cíl 1.4, opatření 1.3.9).",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["obyvatelé obcí"], region=CR,
  forma_podpory=["zapujcka_uver", "dotace"], zdroj_financovani=["eu_fondy"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW_PU, cislo_vyzvy="1/2022 PU",
  evidence={"title": "Půjčka na projekty podpořené dotací z OPŽP", "deadline": "Od 1. 9. 2022 od 9:00 hodin do 31. 5. 2023", "vyse_hlavni_czk": "50 mil. Kč pro půjčku určenou na modernizaci environmentálních center"})

g(7, title="Výzva č. OPST PP-1/2021",
  oblast=["regionální rozvoj", "prostředí"],
  focus_area="Podpora předprojektové a projektové přípravy strategických projektů v Karlovarském, Moravskoslezském a Ústeckém kraji v rámci Mechanismu pro spravedlivou transformaci.",
  open_from="2021-11-16", deadline="2022-01-17",
  castky=[{"typ": "alokace", "hodnota": 170000000}], vyse_hlavni_czk=170000000, spoluucast=True,
  eligible_applicants="Nositelé strategických projektů usilujících o podporu z pilířů Mechanismu pro spravedlivou transformaci ve strukturálně postižených krajích.",
  typ_zadatele=["obec_verejny_subjekt", "firma"], cilova_skupina=["veřejnost"],
  region=kraj("Karlovarský kraj", "Moravskoslezský kraj", "Ústecký kraj"),
  forma_podpory=["dotace"], zdroj_financovani=["eu_fondy"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW_MF, cislo_vyzvy="OPST PP-1/2021",
  evidence={"title": "Výzva č. OPST PP-1/2021", "deadline": "Příjem žádostí : 16. 11. 2021 (12:00 h) – 17. 1. 2022 (12:00 h)", "vyse_hlavni_czk": "Alokace : 170 000 000 Kč"})

g(8, title="Výzva 1/2019 PU: Zvýhodněná půjčka na vodohospodářské projekty podpořené dotací z OPŽP",
  oblast=["prostředí", "vodní hospodářství"],
  focus_area="Zvýhodněná bezúročná půjčka na vodohospodářské projekty (čištění odpadních vod, dodávka pitné vody) podpořené dotací z OPŽP.",
  open_from="2020-01-02", deadline="2020-06-30",
  castky=[{"typ": "alokace", "hodnota": 500000000}], vyse_hlavni_czk=500000000, spoluucast=True,
  eligible_applicants="Obce, města, kraje, dobrovolné svazky obcí, městské části hl. m. Prahy, jimi zřizované příspěvkové organizace a obchodní společnosti vlastněné z více než 50 % obcemi.",
  typ_zadatele=["obec_verejny_subjekt", "prispevkova_organizace", "firma"], cilova_skupina=["obyvatelé obcí"], region=CR,
  forma_podpory=["zapujcka_uver", "dotace"], zdroj_financovani=["eu_fondy"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW_PU, cislo_vyzvy="1/2019 PU",
  evidence={"title": "Zvýhodněná půjčka na vodohospodářské projekty", "deadline": "Příjem žádostí bude probíhat od 2. ledna do 30. června 2020", "vyse_hlavni_czk": "500 milionů Kč"})

g(9, title="Výzva 3/2016 PU",
  oblast=["prostředí", "energetické úspory"],
  focus_area="Zvýhodněná půjčka na projekty snížení energetické náročnosti veřejných budov podpořené dotací z OPŽP (specifický cíl 5.1).",
  open_from="2016-10-07", deadline="2019-12-31",
  castky=[{"typ": "alokace", "hodnota": 500000000}], vyse_hlavni_czk=500000000, spoluucast=True,
  eligible_applicants="Kraje, obce, města, dobrovolné svazky obcí, státní organizace, veřejné výzkumné instituce, příspěvkové organizace, školy, neziskové organizace a církve.",
  typ_zadatele=["obec_verejny_subjekt", "prispevkova_organizace", "skola_vyzkumna_org", "neziskovka"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["zapujcka_uver", "dotace"], zdroj_financovani=["eu_fondy"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW_PU, cislo_vyzvy="3/2016 PU",
  evidence={"title": "Výzva 3/2016 PU", "deadline": "7. října 2016 – 31. prosince 2019", "vyse_hlavni_czk": "500 milionů korun"})

g(10, title="Výzva 2/2016 PU",
  oblast=["prostředí", "vodní hospodářství"],
  focus_area="Zvýhodněná půjčka na vodohospodářské projekty podpořené dotací z OPŽP (snížení znečištění vod, dodávka pitné vody). Příjem žádostí ukončen z důvodu vyčerpání alokace.",
  open_from=None, deadline=None,
  castky=[{"typ": "alokace", "hodnota": 690000000}], vyse_hlavni_czk=690000000, spoluucast=True,
  eligible_applicants="Obce, města, kraje, dobrovolné svazky obcí, městské části hl. m. Prahy, jimi zřizované příspěvkové organizace a obchodní společnosti vlastněné z více než 50 % obcemi.",
  typ_zadatele=["obec_verejny_subjekt", "prispevkova_organizace", "firma"], cilova_skupina=["obyvatelé obcí"], region=CR,
  forma_podpory=["zapujcka_uver", "dotace"], zdroj_financovani=["eu_fondy"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW_PU, cislo_vyzvy="2/2016 PU",
  dalsi_datumy=[{"datum": None, "popis": "Příjem žádostí ukončen z důvodu vyčerpání alokace (přesné datum neuvedeno)"}],
  evidence={"title": "Výzva 2/2016 PU", "vyse_hlavni_czk": "690 milionů Kč"})

g(11, title="Výzva 1/2016 PU",
  oblast=["prostředí", "odpady", "oběhové hospodářství"],
  focus_area="Zvýhodněná půjčka na projekty v oblasti odpadového hospodářství (sběr, třídění, materiálové využití odpadů) podpořené dotací z OPŽP (aktivity 3.2.1 a 3.2.2).",
  open_from="2016-09-01", deadline="2018-12-31",
  castky=[{"typ": "alokace", "hodnota": 60000000}], vyse_hlavni_czk=60000000, spoluucast=True,
  eligible_applicants="Města, obce, kraje, svazky měst a obcí a další subjekty žádající o dotaci v OPŽP na aktivity 3.2.1 a 3.2.2 (mimo státní příspěvkové organizace a organizační složky státu).",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["zapujcka_uver", "dotace"], zdroj_financovani=["eu_fondy"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW_PU, cislo_vyzvy="1/2016 PU",
  evidence={"title": "Výzva 1/2016 PU", "deadline": "1. září 2016 – 31. prosince 2018", "vyse_hlavni_czk": "60 milionů Kč"})

g(12, title="Výzva 1/2017 IFN",
  oblast=["prostředí", "průmysl"],
  focus_area="Zvýhodněná IFN půjčka dotovaná z EU fondů na snížení průmyslového znečištění a rekonstrukci ekologicky rizikových provozů (OPŽP 2014–2020, SC 3.5).",
  open_from="2017-10-16", deadline="2021-02-28",
  castky=[{"typ": "alokace", "hodnota": 280000000}, {"typ": "jine", "hodnota": 93000000}], vyse_hlavni_czk=280000000, spoluucast=True,
  eligible_applicants="Subjekty realizující projekty z OPŽP 2014–2020 v prioritní ose 3, specifický cíl 3.5 (snížení environmentálních rizik).",
  typ_zadatele=["firma", "obec_verejny_subjekt"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["zapujcka_uver", "dotace"], zdroj_financovani=["eu_fondy"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW_PU, cislo_vyzvy="1/2017 IFN",
  evidence={"title": "Výzva 1/2017 IFN", "deadline": "Od 16. října 2017 do 28. února 2021", "vyse_hlavni_czk": "Na zvýhodněné půjčky je v pilotní výzvě vyhrazeno 280 milionů korun"})

# ---- B) Modernizační fond výzvy -------------------------------------------------------
g(13, title="Výzva HOUSEnerg č. 1/2024 FN – Půjčky ze SFŽP ČR na spolufinancování projektů financovaných z programu Nová zelená úsporám",
  oblast=["prostředí", "energetické úspory", "bydlení"],
  focus_area="Bezúročné půjčky bankám a stavebním spořitelnám na poskytování zvýhodněných úvěrů fyzickým osobám na komplexní renovace rodinných domů (NZÚ – Oprav dům po babičce).",
  open_from="2024-03-15", deadline="2026-12-31",
  castky=[{"typ": "alokace", "hodnota": 6000000000}, {"typ": "mira_pct", "hodnota": 50}], vyse_hlavni_czk=6000000000, spoluucast=False,
  eligible_applicants="Podnikatelské subjekty s bankovní licencí od ČNB včetně stavebních spořitelen (banky podle § 1 zákona č. 21/1992 Sb., o bankách).",
  typ_zadatele=["firma"], cilova_skupina=["domácnosti", "fyzické osoby"], region=CR,
  forma_podpory=["zapujcka_uver"], zdroj_financovani=["modernizacni_fond"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW_MF, cislo_vyzvy="HOUSEnerg 1/2024 FN",
  evidence={"title": "Výzva HOUSEnerg č. 1/2024 FN", "deadline": "Ukončení příjmu žádostí: 31. 12. 2026 do 15:00 hod.", "vyse_hlavni_czk": "Alokace: 6 000 000 000 Kč"})

g(14, title="Výzva ELEGRID č. 1/2025 – Modernizace a rozvoj elektrizační soustavy",
  oblast=["prostředí", "energetika", "infrastruktura"],
  focus_area="Posilování elektrizační soustavy pro zvýšení připojitelnosti obnovitelných zdrojů (nová vedení, elektrické stanice, transformátory, systémy řízení).",
  open_from="2025-09-29", deadline="2027-01-29",
  castky=[{"typ": "alokace", "hodnota": 10000000000}], vyse_hlavni_czk=10000000000, spoluucast=True,
  eligible_applicants="Provozovatelé distribučních soustav s více než 90 000 odběrnými místy připojení k přenosové soustavě a provozovatel přenosové soustavy.",
  typ_zadatele=["firma"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["modernizacni_fond"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW_MF, cislo_vyzvy="ELEGRID 1/2025",
  evidence={"title": "Výzva ELEGRID č. 1/2025", "deadline": "Ukončení příjmu žádostí: 29. 1. 2027 do 12:00 hod.", "vyse_hlavni_czk": "Alokace: 10 000 000 000 Kč"})

g(15, title="Výzva KOMUNERG č. 1/2025 – Rozvoj energetických společenství",
  oblast=["prostředí", "energetika", "komunitní energetika"],
  focus_area="Pořízení nových komunitních zdrojů obnovitelné energie (FVE, větrné, bioplyn, bateriová úložiště) a souvisejících řídicích systémů pro energetická společenství.",
  open_from="2026-01-15", deadline="2027-12-31",
  castky=[{"typ": "alokace", "hodnota": 1000000000}], vyse_hlavni_czk=1000000000, spoluucast=True,
  eligible_applicants="Energetická společenství.",
  typ_zadatele=["energetické společenství", "obec_verejny_subjekt"], cilova_skupina=["domácnosti", "obce"], region=CR,
  forma_podpory=["dotace", "zapujcka_uver"], zdroj_financovani=["modernizacni_fond"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW_MF, cislo_vyzvy="KOMUNERG 1/2025",
  evidence={"title": "Výzva KOMUNERG č. 1/2025", "deadline": "Ukončení příjmu žádostí: 31. 12. 2027 , 12:00 hod.", "vyse_hlavni_czk": "Alokace: 1 000 000 000 Kč"})

g(16, title="Výzva TRANSGov č. 1/2024 – Modernizace dopravy (II. kolo)",
  oblast=["prostředí", "doprava"],
  focus_area="Pořízení nových bezemisních železničních vozidel (EMU, BEMU, vodíkové) pro regionální osobní dopravu jako náhrada za dieselová a zastaralá vozidla (II. kolo).",
  open_from="2025-12-01", deadline="2026-12-31",
  castky=[{"typ": "alokace", "hodnota": 15000000000}, {"typ": "mira_pct", "hodnota": 70}], vyse_hlavni_czk=15000000000, spoluucast=True,
  eligible_applicants="Provozovatelé regionální železniční osobní dopravy a kraje, jejichž projektové záměry uspěly v 1. kole výzvy.",
  typ_zadatele=["firma", "obec_verejny_subjekt"], cilova_skupina=["cestující"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["modernizacni_fond"],
  rezim_prijmu="kolova", delka="viceleta", how_to_apply=HOW_MF, cislo_vyzvy="TRANSGov 1/2024",
  evidence={"title": "Výzva TRANSGov č. 1/2024", "deadline": "Ukončení příjmu žádostí: 31. prosince 2026 , 12:00 hod.", "vyse_hlavni_czk": "Alokace: 15 000 000 000 Kč"})

g(17, title="Výzva TRANSGov č. 2/2025 – Elektrizace železničních tratí",
  oblast=["prostředí", "doprava", "infrastruktura"],
  focus_area="Vybudování infrastruktury pro bezemisní mobilitu kolejových vozidel (trakční vedení, napájecí a spínací stanice) – přechod od spalovacích motorů.",
  open_from="2025-12-10", deadline="2027-03-31",
  castky=[{"typ": "alokace", "hodnota": 7175000000}, {"typ": "jine", "hodnota": 35000000}], vyse_hlavni_czk=7175000000, spoluucast=True,
  eligible_applicants="Správa železnic, státní organizace.",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["cestující"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["modernizacni_fond"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW_MF, cislo_vyzvy="TRANSGov 2/2025",
  evidence={"title": "Výzva TRANSGov č. 2/2025", "deadline": "Ukončení příjmu žádostí: 31. března 2027 , 12:00 hod.", "vyse_hlavni_czk": "Alokace: 7 175 000 000 Kč"})

g(18, title="Výzva TRANSCOM č. 1/2025 – Pořízení elektrických lokomotiv pro nákladní dopravu",
  oblast=["prostředí", "doprava"],
  focus_area="Nákup nových elektrických lokomotiv jako náhrada stávajících s nižší energetickou účinností pro nákladní železniční dopravu.",
  open_from="2025-12-15", deadline="2026-10-30",
  castky=[{"typ": "alokace", "hodnota": 3500000000}, {"typ": "mira_pct", "hodnota": 30}], vyse_hlavni_czk=3500000000, spoluucast=True,
  eligible_applicants="Podnikatelské subjekty registrované v ČR poskytující služby v oblasti nákladní železniční dopravy.",
  typ_zadatele=["firma"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["modernizacni_fond"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW_MF, cislo_vyzvy="TRANSCom 1/2025",
  evidence={"title": "Výzva TRANSCOM č. 1/2025", "deadline": "Ukončení příjmu žádostí: 30. října 2026 , 12:00 hod.", "vyse_hlavni_czk": "Alokace: 3 500 000 000 Kč"})

g(19, title="Výzva RES+ č. 6/2025 – Agrofotovoltaické elektrárny",
  oblast=["prostředí", "energetika", "zemědělství"],
  focus_area="Instalace nových agrofotovoltaických elektráren (10 kWp–1 MWp) na zemědělsky obhospodařovaných pozemcích v registru LPIS.",
  open_from="2026-01-15", deadline="2027-06-30",
  castky=[{"typ": "alokace", "hodnota": 300000000}, {"typ": "mira_pct", "hodnota": 30}], vyse_hlavni_czk=300000000, spoluucast=True,
  eligible_applicants="Zemědělští podnikatelé registrovaní v Evidenci zemědělského podnikatele, kteří obhospodařují pozemky v LPIS a jsou (budoucími) držiteli licence pro podnikání v energetice.",
  typ_zadatele=["zemědělský podnikatel", "firma", "osvc_podnikatel"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["modernizacni_fond"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW_MF, cislo_vyzvy="RES+ 6/2025",
  evidence={"title": "Výzva RES+ č. 6/2025", "deadline": "Ukončení příjmu žádostí: 30. června 2027 , 12:00 hod.", "vyse_hlavni_czk": "Alokace: 300 000 000 Kč"})

g(20, title="Výzva TRANSCom č. 2/2025 – Bezemisní silniční nákladní doprava",
  oblast=["prostředí", "doprava"],
  focus_area="Náhrada neekologických nákladních vozidel se vznětovými motory nákupem vozů s nulovými emisemi (kategorie N2/N3) včetně dobíjecích stanic.",
  open_from="2026-02-02", deadline="2026-11-30",
  castky=[{"typ": "alokace", "hodnota": 960000000}, {"typ": "mira_pct", "hodnota": 50}], vyse_hlavni_czk=960000000, spoluucast=True,
  eligible_applicants="Podnikatelské subjekty registrované v ČR provozující silniční nákladní dopravu.",
  typ_zadatele=["firma"], cilova_skupina=["veřejnost"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["modernizacni_fond"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW_MF, cislo_vyzvy="TRANSCom 2/2025",
  evidence={"title": "Výzva TRANSCom č. 2/2025", "deadline": "Ukončení příjmu žádostí: 30. listopadu 2026 , 12:00 hod.", "vyse_hlavni_czk": "Alokace: 960 000 000 Kč"})

os.makedirs("data/sfzp_out", exist_ok=True)
for k, v in out.items():
    json.dump(v, open(f"data/sfzp_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} grants to data/sfzp_out/ (skipped grant_02, grant_03 = duplikáty 04/13)")
