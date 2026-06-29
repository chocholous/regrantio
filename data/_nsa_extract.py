#!/usr/bin/env python3
# Vrstva 2 extrakce pro Národní sportovní agenturu (nsa.gov.cz; parser scripts/nsa.py).
# Výzvy aktuálního cyklu (sport): neinvestiční (Můj klub, sportovní organizace olympijského/
# paralympijského hnutí, významné akce, reprezentace, parasport…) i investiční (Regiony,
# Standardizovaná/Movité infrastruktura, obnova po povodních). Deterministicky parsuje z labelovaného
# Elementor bloku (DATUM VYHLÁŠENÍ / ZAHÁJENÍ + UKONČENÍ PŘÍJMU ŽÁDOSTÍ / ALOKACE / próza).
# typ_poskytovatele=statni_agentura, zdroj=narodni_rozpocet. Status NEvyplňuji (kód z deadline).
import json, os, re

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW = ("Žádost se podává elektronicky přes Dotační portál NSA / Jednotný dotační portál (JDP); "
       "žadatel musí mít aktuální údaje v Rejstříku sportu. Podrobnosti viz znění výzvy.")
D = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")


def iso(line):
    m = D.search(line or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def after(body, label):
    """První neprázdný řádek za daným labelem (label/value jsou na samostatných řádcích)."""
    lines = body.split("\n")
    for i, ln in enumerate(lines):
        if label in ln:
            for nx in lines[i + 1:i + 4]:
                if nx.strip():
                    return nx.strip()
    return ""


def amount(body):
    m = re.search(r"ALOKACE\s*\n\s*([\d\s ]{4,})\s*K", body)
    if not m:
        return None
    s = re.sub(r"\D", "", m.group(1))
    return int(s) if s else None


# kategorie výzvy → (oblast navíc, typ_zadatele, popis žadatele) — vodítka z názvu, žádná halucinace
def classify(title, body):
    t = (title + " " + body).lower()
    inv = bool(re.search(r"investi[čc]n[íi] program|infrastruktur|výstavb|vystavb|"
                         r"technick[ée] zhodnocen|movit|standardizovan|obnova sportovn", t))
    if re.search(r"m[ůu]j klub|tj/sk|tj a sk|tj\b|\bsk\b|zps", t):
        who = ("Sportovní kluby a tělovýchovné jednoty, které dlouhodobě a pravidelně organizují "
               "sportovní činnost dětí a mládeže.")
        typz = ["spolek", "nestatni_neziskova_organizace"]
    elif re.search(r"infrastruktur|regiony|investice|standardizovan|movit|obnova|kabina|za[řr][íi]zen", t):
        who = ("Vlastníci a provozovatelé sportovních zařízení – obce a jejich organizace, spolky a "
               "další sportovní organizace, dle podmínek výzvy.")
        typz = ["obec", "spolek", "nestatni_neziskova_organizace"]
    elif re.search(r"reprezentac", t):
        who = "Sportovní svazy a organizace zajišťující státní sportovní reprezentaci."
        typz = ["nestatni_neziskova_organizace", "spolek"]
    elif re.search(r"akce", t):
        who = "Pořadatelé významných sportovních akcí konaných na území ČR."
        typz = ["nestatni_neziskova_organizace", "spolek"]
    else:  # zastřešující / svazového charakteru / olympijského / paralympijského hnutí / parasport
        who = ("Zastřešující, svazové a celostátní sportovní organizace (sportovní svazy, "
               "olympijské/paralympijské a obdobné organizace).")
        typz = ["nestatni_neziskova_organizace", "spolek"]
    oblast = ["sport", "tělovýchova"]
    if inv:
        oblast.append("sportovní infrastruktura")
    if re.search(r"parasport|handicap|downov|zdravotn[ěe] postižen|paralympij", t):
        oblast.append("zdravotně postižení")
    return oblast, typz, who, inv


def focus(body):
    """Próza pod strukturním blokem: věta 'zveřejňuje …' + 'zaměřena na …' (bez ořezu kontextu)."""
    parts = []
    z = re.search(r"(Národní sportovní agentura (?:zveřejňuje|vyhlašuje)[^\n]+)", body)
    if z:
        parts.append(re.sub(r"\s+", " ", z.group(1)).strip())
    f = re.search(r"((?:Výzva je[^\n]*?zaměřena|Cílem (?:Výzvy|výzvy)|Účelem)[^\n]+)", body)
    if f:
        parts.append(re.sub(r"\s+", " ", f.group(1)).strip())
    return " ".join(parts) if parts else None


def main():
    recs = [json.loads(l) for l in open("data/nsa_documents.jsonl", encoding="utf-8")]
    os.makedirs("data/nsa_out", exist_ok=True)
    n = 0
    for i, r in enumerate(recs):
        b = r.get("body_text", "")
        title = r.get("title", "").strip()
        if re.search(r"\bzru[šs]en", b.lower()):  # zrušená výzva = není reálná příležitost
            print(f"  skip (zrušená): {title[:50]}")
            continue
        open_from = iso(after(b, "ZAHÁJENÍ PŘÍJMU ŽÁDOSTÍ"))
        deadline = iso(after(b, "UKONČENÍ PŘÍJMU ŽÁDOSTÍ"))
        am = amount(b)
        oblast, typz, who, inv = classify(title, b)
        rezim = "kolova" if re.search(r"kolov[ouái]\s+(?:soutěžní|nesoutěžní)?\s*[Vv]ýzv", b) else \
                ("prubezna" if re.search(r"pr[ůu]b[ěe][žz]n", b) else "jednorazova_vyzva")
        foc = focus(b) or (f"Dotační výzva Národní sportovní agentury v oblasti sportu: {title}.")
        ev = {"title": title[:80]}
        dl_line = after(b, "UKONČENÍ PŘÍJMU ŽÁDOSTÍ")
        if deadline and dl_line:
            ev["deadline"] = dl_line[:40]
        if am:
            al = re.search(r"ALOKACE\s*\n\s*([\d\s ]+K[čc])", b)
            if al:
                ev["vyse_hlavni_czk"] = re.sub(r"\s+", " ", al.group(1)).strip()[:40]
        f = {
            "title": title,
            "oblast": oblast,
            "focus_area": foc,
            "open_from": open_from, "deadline": deadline,
            "castky": [{"typ": "alokace", "hodnota": am}] if am else [],
            "vyse_hlavni_czk": am, "spoluucast": True,
            "eligible_applicants": who,
            "typ_zadatele": typz,
            "cilova_skupina": ["sportovci", "děti a mládež"] if re.search(r"klub|mládež|děti|tj|sk", title.lower()) else ["sportovci"],
            "region": CR,
            "forma_podpory": ["dotace"],
            "zdroj_financovani": ["narodni_rozpocet"],
            "rezim_prijmu": rezim, "delka": "jednoleta",
            "how_to_apply": HOW, "required_attachments": [], "source_doc": r.get("url"),
            "cislo_vyzvy": (re.search(r"\b(\d+/20\d\d)\b", title).group(1) if re.search(r"\b\d+/20\d\d\b", title) else None),
            "evidence": ev,
        }
        json.dump(f, open(f"data/nsa_out/grant_{i:02d}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        n += 1
    print(f"wrote {n}/{len(recs)} grants to data/nsa_out/")


if __name__ == "__main__":
    main()
