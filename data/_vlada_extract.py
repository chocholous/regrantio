#!/usr/bin/env python3
# Vrstva 2 pro Úřad vlády ČR – dotace NNO (vlada.gov.cz; parser scripts/vlada.py). 7 národních programů
# (lidská práva/paměť, rovnost žen, menšinové jazyky, romská integrace ×2, zdravotně postižení, drogy).
# Harvest má title/oblast/deadline → passthrough. amount=null (jen v PDF výzvy — nehalucinujeme).
# typ=ministerstvo (Úřad vlády = ústřední správní úřad), zdroj=narodni_rozpocet. Status v kódu.
import json, os, glob, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW = ("Žádost se podává elektronicky (datová schránka / e-mail s kvalifikovaným podpisem / příslušná "
       "webová aplikace) v termínu dotačního řízení; podmínky a alokace viz text výzvy na vlada.gov.cz.")


def main():
    recs = [json.loads(l) for l in open("data/vlada_documents.jsonl", encoding="utf-8")]
    for d in ("data/vlada_in", "data/vlada_out"):
        os.makedirs(d, exist_ok=True)
        for p in glob.glob(d + "/grant_*.json"):
            os.remove(p)
    for i, r in enumerate(recs):
        title = r.get("title")
        prog = r.get("programme") or title
        json.dump({"id": r["url"], "web": "vlada", "force_type": "grant", "title": title,
                   "body": r.get("body_text") or "", "attachments_md": ""},
                  open(f"data/vlada_in/grant_{i:02d}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        ev = {"title": title[:80]}
        if r.get("deadline_cue"):
            ev["deadline"] = r["deadline_cue"][:50]
        rec = {
            "title": title,
            "oblast": (r.get("oblast") or []) + ["NNO", "veřejně prospěšné aktivity"],
            "focus_area": (f"Národní dotační program Úřadu vlády ČR ({prog}) na rok 2026 na podporu "
                           f"veřejně prospěšných aktivit nestátních neziskových organizací."),
            "open_from": None, "deadline": r.get("deadline"),
            "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
            "eligible_applicants": ("Nestátní neziskové organizace (spolky, ústavy, obecně prospěšné "
                                    "společnosti, účelová zařízení církví, nadace/nadační fondy) působící "
                                    "v dané oblasti; u některých programů i obce. Viz text výzvy."),
            "typ_zadatele": ["nestatni_neziskova_organizace", "spolek"], "cilova_skupina": [], "region": CR,
            "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
            "rezim_prijmu": "jednorazova_vyzva", "delka": "jednoleta",
            "how_to_apply": HOW, "required_attachments": [], "source_doc": r["url"],
            "cislo_vyzvy": None, "evidence": ev,
        }
        json.dump(rec, open(f"data/vlada_out/grant_{i:02d}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"wrote {len(recs)} grants → data/vlada_out/ (+_in)")


if __name__ == "__main__":
    main()
