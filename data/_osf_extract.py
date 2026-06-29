#!/usr/bin/env python3
# Vrstva 2 extrakce pro Nadaci OSF (Open Society Fund Praha; osf.cz; parser scripts/osf.py).
# K 2026-06 nemá otevřenou žadatelskou výzvu (Stronger Roots 2026–2027 rozdělen 11/2025) → 1 mission
# (jako NROS/VDV/O2). Mission je grounded z „Co děláme" (data/osf_in/grant_00.json). Grantové _in
# soubory (kdyby OSF vypsalo otevřenou výzvu) se zpracují deterministicky níž. typ_poskytovatele=nadace.
import json, os, glob, shutil

REG = ["Česká republika"]
KONT = {"osoba": None, "email": None, "telefon": None}


def mission(body):
    # evidence = doslovná věta z „Co děláme" (musí být v body_text)
    ev = {}
    for q in ("V programech Nadace OSF rozdělujeme finanční prostředky organizacím občanské společnosti,",
              "rozdělujeme finanční prostředky organizacím občanské společnosti"):
        if q[:40] in body:
            i = body.find(q[:40])
            ev["mission"] = body[i:i + 180].split("\n")[0].strip()
            break
    return {
        "name": "Nadace OSF (Open Society Fund Praha)",
        "mission": ("Nezávislá nadace, která v rámci svých programů rozděluje finanční prostředky organizacím "
                    "občanské společnosti prosazujícím systémové změny na celostátní, regionální i lokální "
                    "úrovni; otevírá opomíjená a složitá témata a pilotuje inovativní projekty (demokracie a "
                    "otevřená společnost, lidská práva, inkluzivní vzdělávání, nezávislá média, moderní stát)."),
        "support_topics": ["občanská společnost a aktivní občanství", "demokracie a otevřená společnost",
                           "lidská práva", "inkluzivní vzdělávání", "nezávislá média a žurnalistika",
                           "moderní a transparentní stát"],
        "cilova_skupina": ["nestátní neziskové organizace", "sítě organizací občanské společnosti",
                           "novináři"],
        "regions": REG, "forma_podpory": ["dotace"],
        "jak_oslovit": ("Podpora se rozděluje přes vlastní programy (Stronger Roots, Advokační forum, "
                        "Novinářská cena, Vzdělávání a rozvoj) a donorské fondy (Fond pro moderní stát, "
                        "Fond Generace OSF, Nadační fond Hyundai, Fond Daniela Anýže, Active Citizens Fund). "
                        "Otevřené grantové výzvy se vyhlašují na osf.cz/granty; mimo výzvy lze oslovit "
                        "programové manažery. Spravuje i dárcovské fondy na míru."),
        "kontakt": KONT, "source_doc": "https://osf.cz/co-delame/",
        "evidence": ev or {"mission": "Nadace OSF"}}


def main():
    os.makedirs("data/osf_out", exist_ok=True)
    about = None
    for path in sorted(glob.glob("data/osf_in/grant_*.json")):
        d = json.load(open(path, encoding="utf-8"))
        base = os.path.basename(path)
        kind_about = "co-delame" in (d.get("id") or "") or d.get("title", "").startswith("Nadace OSF")
        if kind_about and about is None:
            about = (base, d)
            continue
        # (future) otevřená výzva → grant; zatím žádná takovou nemáme
    if about:
        base, d = about
        shutil.copyfile(f"data/osf_in/{base}", "data/osf_in/mission_00.json")
        json.dump(mission(d.get("body") or ""), open("data/osf_out/mission_00.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("wrote 1 mission -> data/osf_out/mission_00.json")
    else:
        print("⚠ žádný about doc nenalezen")


if __name__ == "__main__":
    main()
