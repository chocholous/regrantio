#!/usr/bin/env python3
# Vrstva 2 pro EU Funding & Tenders Portal (ec.europa.eu; parser scripts/eu_ft.py). 979 otevřených
# centrálně řízených výzev EU (Horizon/Erasmus+/Creative Europe/Digital/CEF/LIFE/CERV/SMP/EU4Health…).
# Harvest UŽ má strukturu (open_from/deadline/programme/oblast) → konverze. amount=null (rozpočet je
# v topic detailu/pracovním programu — nehalucinujeme). typ=evropska_komise, zdroj=eu_primy. Status v kódu.
import json, os, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REG = [{"nazev": "Evropská unie / Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW = ("Žádost se podává elektronicky přes EU Funding & Tenders Portal (ec.europa.eu), přihlášení přes "
       "EU Login, v termínu výzvy. Podmínky a rozpočet viz topic page a pracovní program programu.")
ELIG = ("Právnické osoby z členských států EU a asociovaných zemí (výzkumné organizace, podniky vč. MSP, "
        "univerzity, NNO, veřejné instituce, města) – obvykle v mezinárodním konsorciu dle podmínek "
        "konkrétní výzvy a pracovního programu.")


def focus_area(prog, types_of_action, ident):
    """Podnadpis výzvy — skládá se JEN z toho, co opravdu víme.

    ⚠ NAMĚŘENO 2026-09-01 v Grantiu, na detailu výzvy. Stálo tu
    `f"Typ akce: {r.get('typesOfAction') or '-'}."` a u výzev, kde EC to pole
    nevyplňuje, se to zákazníkovi vysázelo doslova:

        Výzva programu Horizon Europe (...). Typ akce: -. Identifikátor HORIZON-CL4-...

    Bylo to u 40 ze 3 187 podnadpisů. Zástupný znak za chybějící hodnotu je
    v pracovním výpisu v pořádku, ve větě určené člověku ne — a hlavně nejde
    o „neznámý typ akce", ale o to, že o typu akce nemáme co říct. Věta, která
    chybějící údaj přeskočí, je pravdivější než věta, která ho pojmenuje
    pomlčkou.
    """
    parts = [f"Výzva programu {prog} (centrálně řízený program Evropské komise)."]
    if types_of_action:
        parts.append(f"Typ akce: {types_of_action}.")
    if ident:
        parts.append(f"Identifikátor {ident}.")
    return " ".join(parts)


def main():
    recs = [json.loads(l) for l in open("data/eu_ft_documents.jsonl", encoding="utf-8")]
    for d in ("data/eu_ft_in", "data/eu_ft_out"):
        os.makedirs(d, exist_ok=True)
        import glob
        for p in glob.glob(d + "/grant_*.json"):
            os.remove(p)
    for i, r in enumerate(recs):
        ident = r.get("identifier") or ""
        title = r.get("title") or ident
        prog = r.get("programme") or "EU"
        body = r.get("body_text") or ""
        json.dump({"id": r.get("url"), "web": "eu_ft", "force_type": "grant", "title": title, "body": body, "attachments_md": ""},
                  open(f"data/eu_ft_in/grant_{i:04d}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        ev = {"title": title[:80]}
        if r.get("deadline"):
            ev["deadline"] = r["deadline"]
        rec = {
            "title": title,
            "oblast": (r.get("oblast") or []) + ["EU dotace"],
            "focus_area": focus_area(prog, r.get("typesOfAction"), ident),
            "open_from": r.get("open_from"), "deadline": r.get("deadline"),
            "castky": [], "vyse_hlavni_czk": None, "spoluucast": True,
            "eligible_applicants": ELIG, "typ_zadatele": [], "cilova_skupina": [], "region": REG,
            "forma_podpory": ["dotace"], "zdroj_financovani": ["eu_primy"],
            "rezim_prijmu": "jednorazova_vyzva", "delka": "viceleta",
            "how_to_apply": HOW, "required_attachments": [], "source_doc": r.get("url"),
            "cislo_vyzvy": ident, "evidence": ev,
        }
        json.dump(rec, open(f"data/eu_ft_out/grant_{i:04d}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"wrote {len(recs)} grants → data/eu_ft_out/ (+_in)")


if __name__ == "__main__":
    main()
