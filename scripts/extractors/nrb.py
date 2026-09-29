#!/usr/bin/env python3
"""Vrstva 2 pro Národní rozvojovou banku (nrb.cz) — úvěry s dotační složkou.

Zdroj: produktové stránky `https://www.nrb.cz/produkt/<slug>/` (harvester
`harvest_site.py --base https://www.nrb.cz --follow ^/produkt/`). Přidáno
2026-09-29: tržní přehled zadavatele ukázal, že financování už není jen
„dotace, nebo nic“ (Nové úspory energie: bezúročný úvěr až 90 % výdajů
a k němu příspěvek až 20 %), a NRB v katalogu nebyla vůbec.

DETERMINISTICKY, bez modelu. Stránka produktu má drobečkovou navigaci
(„Domů / Úvěry / Nové úspory energie“ nebo „Domů / Veřejný sektor / …“),
perex, řádek s kraji („Celá ČR“ nebo výčet krajů) a parametry
(„Výše úvěru 0,5 až 60 mil. Kč“, „Výše dotace až 25 %“, „Finanční příspěvek
až 20 %“, „Aktivní příjem žádostí od 5. 8. 2026“).

Co se BERE: úvěry pro podnikatele (sekce Úvěry) a financování veřejného
sektoru. Co NE: záruky (žadatel nežádá o peníze, ale banka ručí jeho bance)
a poradenství (ELENA); obojí by v katalogu výzev mátlo.

Forma podpory: úvěr = `zapujcka_uver`; s dotační složkou navíc `dotace`
(Grantio pak v řádku neříká „jen půjčka“). Lhůta: produkty běží průběžně do
vyčerpání alokace, takže `deadline` je „průběžně“ a věta o konci příjmu jde
do `dalsi_datumy`, odkud ji čte `enrich.early_close`.
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import enrich  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

IN = "data/nrb_in"
OUT = "data/nrb_out"
KRAJE = ["Hlavní město Praha", "Středočeský kraj", "Jihočeský kraj", "Plzeňský kraj", "Karlovarský kraj",
         "Ústecký kraj", "Liberecký kraj", "Královéhradecký kraj", "Pardubický kraj", "Vysočina",
         "Jihomoravský kraj", "Olomoucký kraj", "Zlínský kraj", "Moravskoslezský kraj"]
DATUM = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")


def iso(s):
    m = DATUM.search(s or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def castka(text):
    """„0,5 až 60 mil. Kč“ → 60 000 000 (horní mez = strop na žadatele)."""
    m = re.search(r"([\d\s ,.]+)\s*(mil|mld|tis)?\.?\s*Kč", text or "")
    if not m:
        return None
    cislo = re.split(r"\s*(?:až|-|–)\s*", m.group(1).strip())[-1].replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        hodnota = float(cislo)
    except ValueError:
        return None
    return int(hodnota * {"mil": 1_000_000, "mld": 1_000_000_000, "tis": 1_000}.get(m.group(2) or "", 1))


def main():
    if not os.path.isdir(IN):
        print(f"✖ Chybí {IN}. Spusť nejdřív harvest a build_extract_input (refresh_run --only nrb).")
        return 1
    soubory = sorted(f for f in os.listdir(IN) if re.match(r"grant_\d+\.json$", f))
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):  # staré výstupy pryč, jméno páruje obsah s adresou
        if re.match(r"grant_\d+\.json$", f):
            os.remove(os.path.join(OUT, f))

    napsano = preskoceno = 0
    for jmeno in soubory:
        r = json.load(io.open(os.path.join(IN, jmeno), encoding="utf-8"))
        url = r.get("id") or ""
        text = r.get("body") or ""
        if not re.search(r"/produkt/[a-z0-9-]+/?$", url):
            preskoceno += 1
            continue
        # Navigace je na každé stránce stejná a zmiňuje „Veřejný sektor“ i „Podnikatelé“;
        # obsah produktu začíná až za ní („Povinně uveřejňované informace“ je její konec).
        konec_menu = text.find("Povinně uveřejňované informace")
        obsah = text[konec_menu + len("Povinně uveřejňované informace"):] if konec_menu >= 0 else text
        verejny = bool(re.search(r"Veřejný sektor|veřejného sektoru", obsah[:1500]))
        uver = re.search(r"Výše úvěru\s+([^\n|]{3,60})", text)
        if not uver:
            preskoceno += 1
            continue
        title = re.sub(r"\s*[-–|]\s*NRB\s*$", "", re.sub(r"\s+", " ", r.get("title") or "")).strip()
        strop = castka(uver.group(1))

        # perex: první delší věta po nadpisu
        po = text[text.find(title, text.find("Domů")) + len(title):] if title and title in text else text
        perex = next((s.strip() for s in re.split(r"\s*\|\s*|\n", po) if len(s.strip()) > 80), "")[:600]

        region = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
        kraje = [k for k in KRAJE if re.search(r"\b" + re.escape(k) + r"\b", obsah[:3000])]
        # „…postižených krajů (Ústecký, Karlovarský a Moravskoslezský)“: přídavná jména
        # v závorce hned za slovem kraj.
        zavorka = re.search(r"kraj\w*\s*\(([^)]{5,120})\)", obsah[:3000])
        if zavorka and not kraje:
            kraje = [k for k in KRAJE if k.split()[0][:-1] in zavorka.group(1)]
        if "Celá ČR" not in obsah[:3000] and kraje:
            region = [{"nazev": k, "obec": None, "okres": None, "kraj": k, "celostatni": False} for k in kraje]

        # Dotační složka: parametr („Výše dotace až 25 %“), nebo věta v perexu
        # („získat k našemu úvěru 25% dotaci Evropské komise“), když karty parametrů
        # ve vstupu chybí (Úvěr s dotací EK, 2026-09-29).
        dotacni = re.search(r"(Výše dotace|Finanční příspěvek)\s+až\s+\d+\s*%|\d+\s*%\s*dotac", obsah)
        m = re.search(r"Aktivní příjem žádostí od\s+(\d{1,2}\.\s*\d{1,2}\.\s*20\d\d)", text)
        open_from = iso(m.group(1)) if m else None

        konec = []
        for vzor in (enrich._CLOSED, enrich._MAY):
            for k in vzor.finditer(text):
                veta = enrich._sentence(text, k.start(), k.end())
                if veta not in konec:
                    konec.append(veta)

        f = {
            "title": title,
            "focus_area": perex or f"Produkt Národní rozvojové banky: {title}.",
            "oblast": ["podnikani"] if not verejny else ["rozvoj_obci"],
            "open_from": open_from,
            "deadline": "průběžně",
            "castky": [{"typ": "max_zadatel", "hodnota": strop}] if strop else [],
            "vyse_hlavni_czk": None,
            "eligible_applicants": ("Subjekty veřejného sektoru podle podmínek produktu." if verejny
                                    else "Podnikatelé podle podmínek produktu (velikost a místo realizace uvádí výzva)."),
            "typ_zadatele": ["obec_verejny_subjekt"] if verejny else ["firma", "osvc_podnikatel"],
            "cilova_skupina": ["verejna_sprava"] if verejny else ["podniky"],
            "region": region,
            "forma_podpory": ["zapujcka_uver", "dotace"] if dotacni else ["zapujcka_uver"],
            "zdroj_financovani": ["narodni_rozpocet"],
            "rezim_prijmu": "prubezna",
            "dalsi_datumy": [{"datum": None, "popis": v} for v in konec[:3]],
            "how_to_apply": "Žádost se podává u Národní rozvojové banky (online sjednání nebo přes partnerskou banku) podle podmínek produktu.",
            "required_attachments": [],
            "source_doc": url,
            "evidence": {"title": title[:80], "vyse_max_zadatel_czk": re.sub(r"\s+", " ", uver.group(0))[:60]},
        }
        json.dump(f, io.open(os.path.join(OUT, jmeno), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        napsano += 1
    print(f"wrote {napsano} grants → {OUT}/ (přeskočeno {preskoceno})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
