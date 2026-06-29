#!/usr/bin/env python3
# Vrstva 2 extrakce pro Státní fond kultury ČR (na mk.gov.cz; parser scripts/sfk.py). 1 záznam =
# program projektových dotací SFK na rok 2026 (3 výzvy/uzávěrky ročně přes DP MK, výzva č. 4501).
# Tematické okruhy z titulu fondu (zákon č. 239/1992 Sb.) — na stránce nejsou, body nese jen termíny.
# Status NEvyplňuji (počítá kód z deadline). amount=null (výše dle projektu, není v oznámení).
import json, os

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
out = {
 "grant_00": {
  "title": "Dotace Státního fondu kultury ČR na rok 2026",
  "oblast": ["kultura"],
  "focus_area": "Projektové dotace Státního fondu kultury ČR na podporu kultury (zákon č. 239/1992 Sb.): "
                "vznik a realizace uměleckých děl, kulturní aktivity (festivaly, výstavy, koncerty, přehlídky), "
                "podpora knih a periodického tisku, ochrana a využití kulturních památek a propagace české kultury. "
                "Pro rok 2026 vyhlásila Rada SFK 3 výzvy podle období zahájení projektů.",
  "open_from": None, "deadline": "2026-04-24",
  "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
  "eligible_applicants": "Právnické i fyzické osoby působící v oblasti kultury (umělci, spolky, neziskové organizace, "
                         "nakladatelé, kulturní instituce, obce a další žadatelé realizující kulturní projekty).",
  "typ_zadatele": ["neziskovka", "firma", "fyzicka_osoba", "obec_verejny_subjekt"],
  "cilova_skupina": ["umělci", "veřejnost"], "region": CR,
  "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
  "rezim_prijmu": "kolova", "delka": "jednoleta",
  "how_to_apply": "Žádost se podává výhradně elektronicky prostřednictvím Dotačního portálu Ministerstva kultury "
                  "(dpmkportal.mk.gov.cz), výzva č. 4501 „Žádosti o dotace SFK na rok 2026“.",
  "required_attachments": [],
  "cislo_vyzvy": "SFK 2026 (DP MK č. 4501)",
  "dalsi_datumy": [
    {"datum": "2025-08-31", "popis": "1. výzva (příjem 25.–31. 8. 2025): projekty zahajované 1. 1. – 30. 4. 2026 + celoroční činnost"},
    {"datum": "2025-12-19", "popis": "2. výzva (příjem 11.–19. 12. 2025): projekty zahajované 1. 5. – 31. 8. 2026"},
    {"datum": "2026-04-24", "popis": "3. výzva (příjem 16.–24. 4. 2026): projekty zahajované 1. 9. – 31. 12. 2026"},
  ],
  "kontakt": {"osoba": None, "email": "hotline-dpmk@asd-software.cz", "telefon": "+420 841 135 135"},
  "evidence": {
    "title": "Žádosti o dotace SFK na rok 2026",
    "deadline": "od 16. do 24. dubna 2026 lze žádat o podporu projektů zahajovaných v termínu 1. 9. – 31. 12. 2026",
    "how_to_apply": "Žádosti o dotace SFK na rok 2026 budou nově přijímány výhradně prostřednictvím Dotačního portálu ministerstva kultury",
  },
 }
}
os.makedirs("data/sfk_out", exist_ok=True)
for k, v in out.items():
    json.dump(v, open(f"data/sfk_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} grant to data/sfk_out/")
