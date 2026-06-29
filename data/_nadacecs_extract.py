#!/usr/bin/env python3
# Vrstva 2 extrakce pro Nadaci České spořitelny — PRŮBĚŽNÝ grant.
# grant_00 = jak-ziskat-nasi-podporu: nadace přijímá koncepty projektů průběžně
# (e-mailem, odpověď do 30 dnů) → deadline="průběžně" → compute_status open.
# Doplňuje existující foundation_mission (nadacecs byl dosud mission-only, 0 grantů).
import json, os

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
out_grant = {}

out_grant["grant_00"] = {
 "title": "Podpora projektů Nadace České spořitelny (průběžný příjem konceptů)",
 "oblast": ["vzdělávání", "sociální", "děti a mládež"],
 "focus_area": "Podpora projektů v souladu s hodnotami nadace (inovativnost, udržitelnost, prohlubování spolupráce s ostatními aktéry) a s co největším dopadem na cílovou skupinu dětí a teenagerů. Nadace se zaměřuje na vzdělávání („#silnější díky vzdělávání“).",
 "open_from": None, "deadline": "průběžně",
 "deadliny": [{"datum": None, "kontext": "Příjem konceptů projektů průběžně e-mailem; nadace odpoví do 30 dnů (žádná pevná uzávěrka)."}],
 "obdobi_realizace": None,
 "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
 "eligible_applicants": "Primárně neziskové organizace — zapsané spolky, zapsané ústavy nebo obecně prospěšné společnosti.",
 "typ_zadatele": ["neziskovka"],
 "cilova_skupina": ["děti", "teenageři", "mládež"],
 "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["vlastni_zdroje"],
 "rezim_prijmu": "prubezna", "delka": "jednoleta",
 "how_to_apply": "Koncept projektu (s náležitostmi níže) zašlete e-mailem na info@nadacecs.cz; nadace odpoví do 30 dnů. Projekt musí být v souladu s hodnotami nadace a mít dopad na cílovou skupinu dětí a teenagerů.",
 "required_attachments": ["informace o žadateli", "popis projektu (východiska, cíle a dopad na cílovou skupinu)", "definice primární cílové skupiny", "časový harmonogram projektu", "celkový rozpočet a struktura financování", "udržitelnost projektu"],
 "cislo_vyzvy": None,
 "source_doc": "https://www.nadacecs.cz/cs/jak-ziskat-nasi-podporu",
 "kontakt": {"osoba": None, "email": "info@nadacecs.cz", "telefon": None},
 "evidence": {
   "focus_area": "Musí být v souladu s našimi hodnotami, jakou jsou inovativnost, udržitelnost, prohlubování spolupráce s ostatními aktéry a co největší dopad na cílovou skupinu dětí a teenagerů.",
   "eligible_applicants": "Primárně neziskové organizace jako jsou zapsané spolky, zapsané ústavy nebo obecně prospěšné společnosti.",
   "how_to_apply": "Koncept projektu nám pošlete na",
   "deadline": "Odpovíme vám do 30 dnů."}}

os.makedirs("data/nadacecs_out", exist_ok=True)
for k, v in out_grant.items():
    json.dump(v, open(f"data/nadacecs_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out_grant), "grant to data/nadacecs_out/")
