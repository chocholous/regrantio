#!/usr/bin/env python3
"""Vrstva 2 pro OP TAK — Operační program Technologie a aplikace pro konkurenceschopnost.

Zdroj: optak.gov.cz (harvester `scripts/harvest_site.py --base https://optak.gov.cz`).
Řídicí orgán MPO, EFRR. Podpora malých a středních podniků: marketing, inovační
vouchery, poradenství, znalostní transfer, technologie, úspory energie.

⚠ DOMÉNA SE ZMĚNILA A REPOZITÁŘ O TOM NEVĚDĚL. `REMAINING.md` vedl OP TAK jako
blokovaný: „web API (agentura-api.org) je prázdný SPA shell". Ta doména je
mrtvá; program se přestěhoval na `optak.gov.cz` a je to server-rendered web.
Naměřeno 2026-09-04.

DETERMINISTICKY, bez modelu. Stránky mají pravidelnou hlavičku:

    Alokace 400 mil. Kč (204 mil. Kč méně rozvinuté regiony / …)
    Vyhlášení výzvy 15. 5. 2026
    Zahájení příjmu žádostí 18. 6. 2026
    Ukončení příjmu žádostí 19. 10. 2026

⚠ ROZHODUJE DATUM UKONČENÍ PŘÍJMU, NE SLOVO „VÝZVA" V TITULKU. BFS přinese
27 stránek, z toho 19 má v titulku „výzva" — jenže část z nich jsou AKTUALITY
o výzvách („Poradenství – výzva III. vyhlášena dne…") a pozvánky na semináře
(„Online seminář Marketing – výzva I."). Ty do katalogu výzev nepatří: uživatel
by na ně klikl s tím, že podá žádost.

Stránka, na kterou lze podat žádost, uvádí, dokdy se podává. To je ten rozdíl.

STATUS SE NEPOČÍTÁ — dopočítá ho `compute_status` z termínů (pravidlo repa).

Spuštění (po `build_extract_input --no-prefilter`):
    python data/_optak_extract.py
"""
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr:
        sys.stderr.reconfigure(encoding="utf-8")

IN = "data/optak_in"
OUT = "data/optak_out"

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]

HOW = ("Žádost se podává elektronicky v IS KP21+ (MS2021+). Podmínky, oprávnění žadatelé "
       "a povinné přílohy jsou v textu výzvy a v Pravidlech pro žadatele a příjemce OP TAK.")

DATUM = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")
POLE = {
    "alokace": re.compile(r"Alokace\s+([^\n]{3,160})"),
    "vyhlaseni": re.compile(r"Vyhlášení\s+výzvy\s+(\d{1,2}\.\s*\d{1,2}\.\s*20\d\d)"),
    "open_from": re.compile(r"Zahájení\s+příjmu\s+žádostí\s+(\d{1,2}\.\s*\d{1,2}\.\s*20\d\d)"),
    "deadline": re.compile(r"Ukončení\s+příjmu\s+žádostí\s+(\d{1,2}\.\s*\d{1,2}\.\s*20\d\d)"),
}

# téma z názvu výzvy → kanonická oblast (`consolidate.py` je nechá být)
TEMA = [
    (r"marketing|veletr|výstav", ["podnikani", "marketing"]),
    (r"inovačn[íi] vouch|znalostn[íi] transfer|výzkum|vývoj", ["podnikani", "veda_vyzkum"]),
    (r"poradenstv", ["podnikani"]),
    (r"úspor|energi|fotovolt|obnoviteln", ["podnikani", "zivotni_prostredi"]),
    (r"digitaliz|kyberbezpe|ict", ["podnikani", "it_digitalizace"]),
    (r"technologi", ["podnikani", "konkurenceschopnost"]),
    (r"oběhov|cirkul|odpad", ["podnikani", "odpady"]),
    (r"vod[ao]hospod|voda", ["podnikani", "zivotni_prostredi"]),
]


def iso(s):
    m = DATUM.search(s or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def castka(text):
    """„400 mil. Kč (204 mil. Kč …)" → 400000000.

    Bere PRVNÍ číslo — to je celková alokace; čísla v závorce jsou její rozpad
    podle typu regionu a sečíst je by dalo dvojnásobek.
    """
    m = re.match(r"\s*([\d\s .,]+)\s*(mil|mld|tis)?\.?\s*Kč", text or "")
    if not m:
        return None
    cislo = m.group(1).replace(" ", "").replace(" ", "").replace(",", ".").rstrip(".")
    try:
        hodnota = float(cislo)
    except ValueError:
        return None
    nasobek = {"mil": 1_000_000, "mld": 1_000_000_000, "tis": 1_000}.get(m.group(2) or "", 1)
    return int(hodnota * nasobek)


def main():
    if not os.path.isdir(IN):
        print(f"✖ Chybí {IN}. Spusť nejdřív:")
        print("   python scripts/harvest_site.py --base https://optak.gov.cz "
              "--source optak --out data/optak_documents.jsonl")
        print("   python scripts/build_extract_input.py data/optak_documents.jsonl "
              "--source optak --out-dir data/optak_in --force-type grant")
        return 1

    # ⚠ ČTE SE SLOŽKA `_in`, NE HARVEST. A není to detail.
    #
    # `ingest_rich` páruje obsah se zdrojem podle JMÉNA SOUBORU: `_in/grant_07`
    # dá adresu, `_out/grant_07` obsah. Kdo číslu ve výstupu dá pořadí
    # z harvestu, spáruje záznamy se špatnými adresami všude tam, kde
    # `build_extract_input` něco odfiltroval.
    #
    # Naměřeno při psaní tohohle souboru: harvest měl 25 stránek, `_in` jich má
    # 23, a výstup začínal na `grant_04` — `ingest_rich` hlásil `miss_src: 3`.
    # Je to TÁŽ vada, kvůli které je 21 souborů v `refresh_run.TRANSCRIBED`;
    # tam se jen neprojeví hláškou, protože obsah je natvrdo a čísla sedí
    # náhodou, dokud se listing na webu nepřeskládá.
    #
    # Autorita na číslování je `_in`. Tečka.
    soubory = sorted(f for f in os.listdir(IN) if re.match(r"grant_\d+\.json$", f))
    os.makedirs(OUT, exist_ok=True)
    napsano, preskoceno = 0, 0

    for jmeno in soubory:
        r = json.load(io.open(os.path.join(IN, jmeno), encoding="utf-8"))
        title = re.sub(r"\s+", " ", r.get("title") or "").strip()
        text = r.get("body") or ""

        deadline = None
        m = POLE["deadline"].search(text)
        if m:
            deadline = iso(m.group(1))

        # ⚠ MUSÍ PLATIT OBOJÍ: titulek výzvy A termín podání.
        #
        # Jen termín nestačí — HOMEPAGE („Pro vaše chytré podnikání") vypisuje
        # termín výzvy, kterou zrovna propaguje, takže by prošla jako výzva.
        # Jen titulek nestačí taky — aktuality a semináře mají „výzva" v názvu
        # a žádat se na ně nedá.
        if not deadline or not re.search(r"v[ýy]zva", title, re.I):
            preskoceno += 1
            continue

        open_from = None
        m = POLE["open_from"].search(text)
        if m:
            open_from = iso(m.group(1))

        alok = None
        m = POLE["alokace"].search(text)
        if m:
            alok = castka(m.group(1))

        oblast = ["podnikani"]
        nizky = title.lower()
        for pat, obs in TEMA:
            if re.search(pat, nizky):
                oblast = [o for o in obs]
                break

        # první věta za hlavičkou = podtitulek s věcným zaměřením
        perex = ""
        po_titulku = text[len(title):].lstrip() if text.startswith(title) else text
        m = re.match(r"([^\n]{40,400}?)(?:\s+Alokace|\s+Vyhlášení|$)", po_titulku)
        if m:
            perex = re.sub(r"\s+", " ", m.group(1)).strip()

        evidence = {"title": title[:80]}
        if deadline:
            evidence["deadline"] = re.sub(r"\s+", " ", POLE["deadline"].search(text).group(0))[:60]
        if alok:
            evidence["vyse_hlavni_czk"] = re.sub(r"\s+", " ", POLE["alokace"].search(text).group(0))[:60]

        f = {
            "title": title,
            "focus_area": (perex or f"Výzva {title} Operačního programu Technologie a aplikace "
                                   f"pro konkurenceschopnost (OP TAK).")[:600],
            "oblast": oblast,
            "open_from": open_from,
            "deadline": deadline,
            "castky": [{"typ": "alokace", "hodnota": alok}] if alok else [],
            "vyse_hlavni_czk": None,   # alokace programu ≠ strop na žadatele — NEFABRIKUJEME
            "spoluucast": True,
            "eligible_applicants": ("Malé a střední podniky (u některých aktivit i velké podniky) "
                                    "dle textu výzvy a Pravidel pro žadatele a příjemce OP TAK."),
            "typ_zadatele": ["firma", "osvc_podnikatel"],
            "cilova_skupina": ["podniky"],
            "region": CR,
            "forma_podpory": ["dotace"],
            "zdroj_financovani": ["eu_fondy"],
            "rezim_prijmu": "kolova",
            "delka": None,
            "how_to_apply": HOW,
            "required_attachments": [],
            "source_doc": r.get("id"),
            "evidence": evidence,
        }
        # Jméno souboru se PŘEBÍRÁ ze vstupu, nedopočítává — viz poznámka výš.
        json.dump(f, io.open(os.path.join(OUT, jmeno), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        napsano += 1

    print(f"wrote {napsano} grants → {OUT}/ (přeskočeno {preskoceno} bez termínu podání)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
