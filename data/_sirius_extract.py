#!/usr/bin/env python3
# Vrstva 2 extrakce pro Nadaci Sirius (nadacesirius.cz, parser scripts/sirius.py).
# Sirius vyhlašuje grantové řízení zpravidla 1× ročně; v době sběru NENÍ otevřená
# žádná grantová výzva ("V současné době není otevřena žádná grantová výzva.").
# Historická grantová řízení = výsledkové souhrny (results ≠ opportunity).
# → ingestuje se pouze foundation_mission (about → mission_00). grant_01 (pravidla) se nepíše.
import json, os, shutil

out_mission = {}

# --- foundation_mission (o-nas/nadace-sirius → mission_00) ---
out_mission["mission_00"] = {
 "name": "Nadace Sirius",
 "mission": "Soukromá nadace založená v roce 2008, zaměřená na pomoc znevýhodněným a ohroženým dětem. Posláním je všestranně přispívat ke zlepšování kvality života dětí; cílem aktivit je funkční rodina (biologická nebo náhradní).",
 "support_topics": ["prevence ohrožení dítěte a rodiny", "náhradní rodinná a ústavní péče", "podpora zdravotně znevýhodněných dětí", "sanace ohrožené rodiny"],
 "cilova_skupina": ["ohrožené děti", "rodiny s dětmi", "děti v náhradní péči", "děti se zdravotním postižením"],
 "regions": ["Česká republika"],
 "forma_podpory": ["dotace"],
 "jak_oslovit": "Prostřednictvím pravidelně vypisovaných grantových řízení (zpravidla jednou ročně) podporuje aktivity neziskových organizací; témata jsou vybírána na základě odborné analýzy. Mimo otevřené grantové kolo nelze žádat — sledovat sekci Aktuální grantová výzva na webu nadace.",
 "kontakt": {"osoba": None, "email": None, "telefon": "+420 702 026 600"},
 "source_doc": "https://www.nadacesirius.cz/o-nas/nadace-sirius",
 "evidence": {
   "mission": "Posláním Nadace Sirius je všestranně přispívat ke zlepšování kvality života dětí.",
   "jak_oslovit": "Prostřednictvím pravidelně vypisovaných grantových řízení rovněž podporuje aktivity jiných neziskových organizací"}}

os.makedirs("data/sirius_out", exist_ok=True)
# basename-join workaround: mission čte _in/mission_00.json (= about grant_00), do _out píšeme jen mission_00
shutil.copyfile("data/sirius_in/grant_00.json", "data/sirius_in/mission_00.json")
for k, v in out_mission.items():
    json.dump(v, open(f"data/sirius_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote", len(out_mission), "mission to data/sirius_out/ (no open grants)")
