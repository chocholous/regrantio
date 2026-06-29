#!/usr/bin/env python3
# Vrstva 2 extrakce pro Státní fond podpory investic / SFRB (sfpi.cz; parser scripts/sfpi.py).
# 6 programů s extrahovatelným obsahem (bydlení: úvěry + dotace). VYNECHÁNO: 02/03 (duplicitní
# Živel-3 stránky), 07 (Ubytování uprchlíků = podmínky pronájmu, ne grantová výzva), 09–13
# (Zateplování/Vlastní bydlení/Nájemní byty/Program 150/600 = page-builder, tělo přes REST prázdné).
# amount=null (konkrétní stropy jsou v NV/PDF, ne v hubu → nehalucinuji). Status NEvyplňuji (počítá kód).
import json, os

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW = "Žádost se podává elektronicky prostřednictvím Klientského portálu SFPI (portal.sfpi.cz)."
out = {}
def g(idx, **f):
    out[f"grant_{idx:02d}"] = f

g(0, title="Úsporné bytové domy (úvěr na renovace bytových domů)",
  oblast=["bydlení", "energetické úspory"],
  focus_area="Zvýhodněný úvěr na úsporné renovace bytových domů – finanční nástroj IROP (2. investiční cyklus, prostředky IROP 2014–2020 + SFPI).",
  open_from="2026-07-07", deadline="průběžně",
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Vlastníci bytových domů – právnické i fyzické osoby a společenství vlastníků jednotek (SVJ).",
  typ_zadatele=["firma", "fyzicka_osoba", "neziskovka", "obec_verejny_subjekt"],
  cilova_skupina=["vlastníci bytových domů"], region=CR,
  forma_podpory=["zapujcka_uver"], zdroj_financovani=["eu_fondy"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="Úsporné bytové domy (UBD)",
  evidence={"title": "Úvěrový program Úsporné bytové domy", "open_from": "Příjem žádosti bude zahájen 7. 7. 2026"})

g(1, title="Živel 3 – obnova bydlení po povodních (září 2024)",
  oblast=["bydlení", "obnova po katastrofě"],
  focus_area="Podpora obnovy obydlí postiženého povodní 13.–18. 9. 2024 (oprava, nová výstavba, nákup nemovitosti, obnova rozestavěného obydlí).",
  open_from=None, deadline="průběžně",
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Vlastník nebo spoluvlastník obydlí nebo společenství vlastníků jednotek v domě, který v době povodně obydlí užíval k bydlení nebo je pronajímal.",
  typ_zadatele=["fyzicka_osoba", "neziskovka"], cilova_skupina=["osoby postižené povodní"], region=CR,
  forma_podpory=["zapujcka_uver"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="Živel 3",
  evidence={"title": "Živel 3", "eligible_applicants": "Vlastník nebo spoluvlastník obydlí nebo společenství vlastníků jednotek v domě"})

g(4, title="Bytové domy bez bariér (dotace na odstranění bariér)",
  oblast=["bydlení", "bezbariérovost"],
  focus_area="Dotace na odstranění bariér v bytovém domě (bezbariérový přístup, výtahy, úpravy pro osoby se zrakovým postižením) z programu Ministerstva pro místní rozvoj.",
  open_from="2025-01-16", deadline="2025-03-19",
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Vlastníci bytových domů (společenství vlastníků jednotek, bytová družstva, obce a další vlastníci bytových domů).",
  typ_zadatele=["firma", "neziskovka", "obec_verejny_subjekt"],
  cilova_skupina=["osoby se zdravotním postižením", "senioři"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="1/BDBB/2024",
  evidence={"title": "program Bytové domy bez bariér", "open_from": "Příjem žádostí prostřednictvím Klientského portálu SFPI bude zahájen 16. 1. 2025", "deadline": "dne 19. 3. 2025 bude ukončen příjem žádosti do programu Bytové domy bez bariér z důvodu vyčerpání alokace"})

g(5, title="Dostupné nájemní bydlení (úvěr a dotace pro obce z NPO)",
  oblast=["bydlení", "dostupné bydlení"],
  focus_area="Úvěr a dotace městům a obcím na výstavbu dostupného nájemního bydlení (Národní plán obnovy).",
  open_from=None, deadline="2025-06-30",
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Města a obce (a jimi založené či ovládané subjekty) realizující projekty dostupného nájemního bydlení.",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["nájemníci", "domácnosti"], region=CR,
  forma_podpory=["zapujcka_uver", "dotace"], zdroj_financovani=["npo"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="1/DB/2024",
  evidence={"title": "program Dostupné nájemní bydlení", "deadline": "Poslední termín podání žádosti je tedy 30. 6. 2025 ve 23.59 hod."})

g(6, title="Nájemní bydlení (dotace a úvěr na výstavbu nájemních bytů)",
  oblast=["bydlení"],
  focus_area="Dotace a úvěr právnickým osobám na výstavbu nájemních bytů (nařízení vlády č. 107/2023 Sb.).",
  open_from="2023-05-15", deadline="2023-08-31",
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Právnické osoby, které chtějí stavět nájemní byty.",
  typ_zadatele=["firma"], cilova_skupina=["nájemníci"], region=CR,
  forma_podpory=["dotace", "zapujcka_uver"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="1/NB/2023",
  evidence={"title": "program Nájemní bydlení", "open_from": "zahájení příjmu žádostí 15. 5. 2023 v 10.00", "deadline": "dne 31. srpna 2023 byl ukončen příjem žádosti do programu Nájemní bydlení z důvodu vyčerpání alokace"})

g(8, title="Regenerace veřejných prostranství na sídlištích (dotace a úvěr)",
  oblast=["bydlení", "veřejná prostranství", "regionální rozvoj"],
  focus_area="Dotace nebo dotace a úvěr na přeměnu městských sídlišť na víceúčelové celky a zlepšení obytného prostředí (NV č. 390/2017 Sb.). Program byl ukončen – výzvy se nadále nevyhlašují.",
  open_from="2021-10-15", deadline=None,
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Obce a města (vlastníci/správci veřejných prostranství na sídlištích) dle NV č. 390/2017 Sb.",
  typ_zadatele=["obec_verejny_subjekt"], cilova_skupina=["obyvatelé sídlišť"], region=CR,
  forma_podpory=["dotace", "zapujcka_uver"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW, cislo_vyzvy="5/2022 (poslední výzva)",
  dalsi_datumy=[{"datum": None, "popis": "Program ukončen – SFPI nebude vyhlašovat výzvu pro další období (zveřejněno 17. 10. 2022)"}],
  evidence={"title": "program Regenerace sídlišť", "open_from": "Státní fond podpory investic vyhlašuje dne 15. října 2021 výzvu"})

os.makedirs("data/sfpi_out", exist_ok=True)
for k, v in out.items():
    json.dump(v, open(f"data/sfpi_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} grants to data/sfpi_out/ (skipped duplicates/conditions/page-builder hubs)")
