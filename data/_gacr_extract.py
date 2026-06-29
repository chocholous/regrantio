#!/usr/bin/env python3
# Vrstva 2 extrakce pro Grantovou agenturu ČR (gacr.cz; parser scripts/gacr.py). 14 výzev aktuálního
# cyklu: 7 hlavních veřejných soutěží 2027 (EXPRO, JUNIOR STAR, Mezinárodní-bilaterální, Návratové granty,
# POSTDOC IF IN/OUT, Standardní) + 7 LA/bilaterálních výzev (Weave). amount=null (konkrétní strop je v
# Zadávací dokumentaci, ne v oznámení → NEhalucinuji). Status NEvyplňuji (počítá kód z deadline).
import json, os

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
VO = ["skola_vyzkumna_org"]          # uchazeč GA ČR = výzkumná organizace (VŠ, ústavy AV, výzkumné instituce)
VEDCI = ["vědci a výzkumní pracovníci"]
def HOW(is_):
    return f"Návrh projektu se podává elektronicky v informačním systému {is_}; způsobilost se dokládá čestným prohlášením do datové schránky GA ČR."

out = {}
def g(idx, **f):
    out[f"grant_{idx:02d}"] = f

# ---- 7 hlavních veřejných soutěží 2027 ------------------------------------------------
g(0, title="Vyhlášení veřejné soutěže EXPRO 2027",
  oblast=["věda a výzkum", "základní výzkum"],
  focus_area="Grantové projekty excelence v základním výzkumu EXPRO – budování špičkových výzkumných týmů a etablování excelentních vědců.",
  open_from="2026-03-05", deadline="2026-04-20",
  castky=[], vyse_hlavni_czk=None, spoluucast=False,
  eligible_applicants="Výzkumné organizace (vysoké školy, ústavy AV ČR a další výzkumné instituce) jako uchazeč za řešitele projektu.",
  typ_zadatele=VO, cilova_skupina=VEDCI, region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW("GRITA"), cislo_vyzvy="EXPRO 2027",
  evidence={"title": "Vyhlášení veřejné soutěže EXPRO 2027", "open_from": "Soutěžní lhůta začíná 5. 3. 2026", "deadline": "Návrhy projektů je možné podávat do 20. 4. 2026"})

g(1, title="Vyhlášení veřejné soutěže JUNIOR STAR 2027",
  oblast=["věda a výzkum", "základní výzkum"],
  focus_area="Projekty JUNIOR STAR pro začínající vědce (do 8 let od získání Ph.D.) na vybudování vlastní výzkumné skupiny a samostatného směru bádání.",
  open_from="2026-03-05", deadline="2026-04-20",
  castky=[], vyse_hlavni_czk=None, spoluucast=False,
  eligible_applicants="Výzkumné organizace; řešitel je začínající vědec do 8 let od získání titulu Ph.D.",
  typ_zadatele=VO, cilova_skupina=["začínající vědci", "mladí výzkumní pracovníci"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW("GRITA"), cislo_vyzvy="JUNIOR STAR 2027",
  evidence={"title": "Vyhlášení veřejné soutěže JUNIOR STAR 2027", "open_from": "Soutěžní lhůta začíná 5. 3. 2026", "deadline": "Návrhy projektů je možné podávat do 20. 4. 2026"})

g(2, title="Vyhlášení veřejné soutěže Mezinárodní-bilaterální projekty 2027",
  oblast=["věda a výzkum", "základní výzkum"],
  focus_area="Mezinárodní bilaterální projekty základního výzkumu se zahraničními agenturami (Tchaj-wan – NSTC, Jižní Korea – NRF).",
  open_from="2026-02-10", deadline="2026-03-31",
  castky=[], vyse_hlavni_czk=None, spoluucast=False,
  eligible_applicants="Výzkumné organizace ve spolupráci se zahraničním partnerem dle příslušné bilaterální dohody.",
  typ_zadatele=VO, cilova_skupina=VEDCI, region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW("GRIS"), cislo_vyzvy="Mezinárodní-bilaterální 2027",
  evidence={"title": "Vyhlášení veřejné soutěže Mezinárodní-bilaterální projekty 2027", "open_from": "Soutěžní lhůta začíná 10. 2. 2026", "deadline": "Návrhy projektů je možné podávat do 31. 3. 2026"})

g(3, title="Vyhlášení veřejné soutěže Návratové granty 2027",
  oblast=["věda a výzkum", "základní výzkum"],
  focus_area="Návratové granty – podpora vědců vracejících se k vědecké kariéře v ČR (po rodičovství či jiné delší přestávce).",
  open_from="2026-02-10", deadline="2026-03-31",
  castky=[], vyse_hlavni_czk=None, spoluucast=False,
  eligible_applicants="Výzkumné organizace; řešitel je vědec navracející se k aktivní vědecké práci.",
  typ_zadatele=VO, cilova_skupina=["vědci navracející se do vědy"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW("GRIS"), cislo_vyzvy="Návratové granty 2027",
  evidence={"title": "Vyhlášení veřejné soutěže Návratové granty 2027", "open_from": "Soutěžní lhůta začíná 10. 2. 2026", "deadline": "Návrhy projektů je možné podávat do 31. 3. 2026"})

g(4, title="Vyhlášení veřejné soutěže POSTDOC INDIVIDUAL FELLOWSHIP OUTGOING 2027",
  oblast=["věda a výzkum", "základní výzkum"],
  focus_area="POSTDOC INDIVIDUAL FELLOWSHIP – OUTGOING: zahraniční stáže českých postdoktorandů s návratovou fází v ČR.",
  open_from="2026-02-10", deadline="2026-03-31",
  castky=[], vyse_hlavni_czk=None, spoluucast=False,
  eligible_applicants="Výzkumné organizace; řešitel je postdoktorand (do několika let od Ph.D.) vyjíždějící na zahraniční stáž.",
  typ_zadatele=VO, cilova_skupina=["postdoktorandi"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW("GRIS"), cislo_vyzvy="POSTDOC IF OUTGOING 2027",
  evidence={"title": "Vyhlášení veřejné soutěže POSTDOC INDIVIDUAL FELLOWSHIP – OUTGOING", "open_from": "Soutěžní lhůta začíná 10. 2. 2026", "deadline": "Návrhy projektů je možné podávat do 31. 3. 2026"})

g(5, title="Vyhlášení veřejné soutěže POSTDOC INDIVIDUAL FELLOWSHIP INCOMING 2027",
  oblast=["věda a výzkum", "základní výzkum"],
  focus_area="POSTDOC INDIVIDUAL FELLOWSHIP – INCOMING: příchod zahraničních postdoktorandů na výzkumné stáže do českých institucí.",
  open_from="2026-02-10", deadline="2026-03-31",
  castky=[], vyse_hlavni_czk=None, spoluucast=False,
  eligible_applicants="Výzkumné organizace přijímající zahraničního postdoktoranda jako řešitele.",
  typ_zadatele=VO, cilova_skupina=["postdoktorandi"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW("GRIS"), cislo_vyzvy="POSTDOC IF INCOMING 2027",
  evidence={"title": "Vyhlášení veřejné soutěže POSTDOC INDIVIDUAL FELLOWSHIP – INCOMING", "open_from": "Soutěžní lhůta začíná 10. 2. 2026", "deadline": "Návrhy projektů je možné podávat do 31. 3. 2026"})

g(6, title="Vyhlášení veřejné soutěže Standardní projekty 2027",
  oblast=["věda a výzkum", "základní výzkum"],
  focus_area="Standardní grantové projekty základního výzkumu napříč všemi vědními obory.",
  open_from="2026-02-10", deadline="2026-03-31",
  castky=[], vyse_hlavni_czk=None, spoluucast=False,
  eligible_applicants="Výzkumné organizace (vysoké školy, ústavy AV ČR a další výzkumné instituce) za řešitele projektu.",
  typ_zadatele=VO, cilova_skupina=VEDCI, region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW("GRIS"), cislo_vyzvy="Standardní projekty 2027",
  evidence={"title": "Vyhlášení veřejné soutěže Standardní projekty 2027", "open_from": "Soutěžní lhůta začíná 10. 2. 2026", "deadline": "Návrhy projektů je možné podávat do 31. 3. 2026"})

# ---- LA / bilaterální výzvy (Weave) ---------------------------------------------------
def la(idx, title, focus, open_from, deadline, num, rezim="jednorazova_vyzva", dl_quote=None, of_quote=None):
    g(idx, title=title, oblast=["věda a výzkum", "základní výzkum", "mezinárodní spolupráce"],
      focus_area=focus, open_from=open_from, deadline=deadline,
      castky=[], vyse_hlavni_czk=None, spoluucast=False,
      eligible_applicants="Výzkumné organizace; mezinárodní projekt hodnocený na principu Lead Agency (iniciativa Weave) ve spolupráci s partnerskou agenturou.",
      typ_zadatele=VO, cilova_skupina=VEDCI, region=CR,
      forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
      rezim_prijmu=rezim, delka="viceleta", how_to_apply=HOW("GRIS"), cislo_vyzvy=num,
      evidence={"title": title, **({"deadline": dl_quote} if dl_quote else {}), **({"open_from": of_quote} if of_quote else {})})

la(7, "Výzva pro podávání chorvatsko-českých projektů (Lead Agency 2027)",
   "Mezinárodní projekty s chorvatskou agenturou HRZZ na principu Lead Agency (GA ČR partnerská organizace), iniciativa Weave.",
   "2026-03-26", "2026-05-04", "LA Weave – HRZZ 2027",
   dl_quote="Českou část návrhu projektu je možné podávat nejpozději do 4. 5. 2026", of_quote="Lhůta pro podávání návrhů projektů začíná 26. 3. 2026")
la(8, "Výzva pro podávání slovinsko-českých projektů (Lead Agency 2027)",
   "Mezinárodní projekty se slovinskou agenturou ARIS na principu Lead Agency (GA ČR partnerská organizace), iniciativa Weave.",
   "2026-02-16", "2026-04-07", "LA Weave – ARIS 2027",
   dl_quote="Českou část návrhu projektu je možné podávat nejpozději do 7. 4. 2026", of_quote="Lhůta pro podávání návrhů projektů začíná 16. 2. 2026")
la(9, "Výzva pro podávání projektů na principu Lead Agency 2027 (GA ČR jako Lead Agency)",
   "Mezinárodní projekty, kde GA ČR vystupuje v roli Lead Agency (partneři FWF, DFG, NCN, ARIS, SNSF, FNR, HRZZ), iniciativa Weave.",
   "2026-02-10", "2026-03-31", "LA Weave – GA ČR Lead 2027",
   dl_quote="Návrhy projektů je možné podávat do 31. 3. 2026", of_quote="Lhůta pro podávání návrhů projektů začíná 10. 2. 2026")
la(10, "Výzva pro podávání švýcarsko-českých projektů (Lead Agency 2027)",
   "Mezinárodní projekty se švýcarskou agenturou SNSF na principu Lead Agency (GA ČR partnerská organizace); švýcarské termíny 1. 4. a 1. 10. 2026, česká část do 7 dnů poté.",
   None, "2026-10-08", "LA Weave – SNSF 2027",
   dl_quote="tedy do 8. 4. , případně 8. 10. 2026")
la(11, "Výzva pro podávání projektů Lead Agency – GA ČR partnerskou organizací – kontinuální (DFG, FWF)",
   "Kontinuální výzva pro mezinárodní projekty s DFG (Německo) a FWF (Rakousko), GA ČR partnerská organizace, iniciativa Weave; česká část do 7 dnů od podání k DFG/FWF.",
   "2026-02-10", "průběžně", "LA Weave – DFG/FWF kontinuální", rezim="prubezna",
   of_quote="Lhůta pro podávání návrhů projektů začíná 10. 2. 2026")
la(12, "Výzva pro podávání lucembursko-českých projektů (Lead Agency 2027)",
   "Mezinárodní projekty s lucemburskou agenturou FNR na principu Lead Agency (GA ČR partnerská organizace), iniciativa Weave.",
   "2025-12-18", "2026-04-28", "LA Weave – FNR 2027",
   dl_quote="Českou část návrhu projektu je možné podávat nejpozději do 28. 4. 2026", of_quote="Lhůta pro podávání návrhů projektů začíná 18. 12. 2025")
la(13, "Výzva pro podávání polsko-českých projektů (Lead Agency 2027)",
   "Mezinárodní projekty s polskou agenturou NCN na principu Lead Agency (GA ČR partnerská organizace), iniciativa Weave.",
   "2025-09-15", "2025-12-22", "LA Weave – NCN 2027",
   dl_quote="Českou část návrhu projektu je možné podávat nejpozději do 22. 12. 2025", of_quote="Lhůta pro podávání návrhů projektů začíná 15. 9. 2025")

os.makedirs("data/gacr_out", exist_ok=True)
for k, v in out.items():
    json.dump(v, open(f"data/gacr_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} grants to data/gacr_out/")
