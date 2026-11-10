#!/usr/bin/env python3
"""Vrstva 2 pro dotaceeu.cz (výzvy z MS2021+), 2026‑11‑10.

Zdroj: `scripts/dotaceeu.py` (OP Rybářství, OP AMIF, OP FVB, OP NSHV,
finanční nástroje). DETERMINISTICKY: detail má štítky na vlastních řádcích
a hodnotu na dalším („Číslo výzvy:“, „Druh výzvy:“, „Oprávnění žadatelé:“,
„Zahájení příjmu žádostí:“, „Ukončení příjmu žádostí:“).

⚠ Výzva, o kterou smí žádat jen jmenovaný státní úřad („Ministerstvo vnitra
- Policie ČR“, „Kancelář veřejného ochránce práv“), se nezapíše: nikdo
z uživatelů o ni žádat nemůže a v katalogu by byla šum. Pozná se tak, že
oprávnění žadatelé nejmenují žádnou skupinu (organizace, podniky, obce…).
"""
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

IN = "data/dotaceeu.cz_in"
OUT = "data/dotaceeu.cz_out"
CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
DATUM = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")
STITKY = ("Číslo výzvy", "Druh výzvy", "Programové období", "Operační program", "Prioritní osa",
          "Oprávnění žadatelé", "Zpřístupnění žádosti o podporu", "Zahájení příjmu žádostí",
          "Ukončení příjmu žádostí", "Více informací na", "Stav výzvy", "Informace o výzvě")
SKUPINA = re.compile(r"organizac|podnik|obc[eíi]|\bobec|spolk|nezisk|nestátn|právnick|fyzick|osob|sdružen|škol|kraj|"
                     r"zpracovatel|producent|rybář|akvakultur|MSP|malé a střední", re.I)
# Zkratky MS2021+: NNO (nestátní neziskové), OSS (organizační složky státu), VÚSC (kraje).
TYP = [
    (r"nestátn\w+ nezisk|nezisk\w+ organizac|\bNNO\b|spolk|obecně prospěšn|nadac", "neziskovka"),
    (r"podnik|MSP|malé a střední|zpracovatel|producent|akvakultur|rybář", "firma"),
    (r"podnikaj\w+ fyzick", "osvc_podnikatel"),
    (r"\bobc[eíi]\b|\bobec\b|kraj[eůi]?\b|územní\w* samospráv|\bVÚSC\b", "obec_verejny_subjekt"),
    (r"příspěvkov\w+ organizac", "prispevkova_organizace"),
    (r"škol|vysok\w+ učen|výzkumn\w+ (?:organizac|instituc)", "skola_vyzkumna_org"),
]
OBLAST_PROGRAM = [
    (r"Rybářství", ["rybolov", "podnikani"]),
    (r"Azylového|AMIF", ["migrace"]),
    (r"vnitřní bezpečnost|FVB", ["bezpecnost"]),
    (r"správy hranic|NSHV", ["bezpecnost"]),
]


def pole(text, stitek):
    """Hodnota pod štítkem: řádky do dalšího štítku."""
    m = re.search(rf"^{re.escape(stitek)}:\s*$", text, re.M)
    if not m:
        return ""
    radky = []
    for ln in text[m.end():].split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        if any(ln.startswith(s + ":") or ln == s for s in STITKY):
            break
        radky.append(ln)
    return " ".join(radky).strip()


def iso(s):
    m = DATUM.search(s or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def main():
    if not os.path.isdir(IN):
        print(f"✖ Chybí {IN}. Spusť nejdřív harvest a build_extract_input (refresh_run --only dotaceeu.cz).")
        return 1
    soubory = sorted(f for f in os.listdir(IN) if re.match(r"grant_\d+\.json$", f))
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if re.match(r"grant_\d+\.json$", f):
            os.remove(os.path.join(OUT, f))

    napsano = statni = 0
    for jmeno in soubory:
        r = json.load(io.open(os.path.join(IN, jmeno), encoding="utf-8"))
        url = r.get("id") or ""
        text = r.get("body") or ""
        title = re.sub(r"\s+", " ", r.get("title") or "").strip()
        kdo = pole(text, "Oprávnění žadatelé")
        if kdo and not SKUPINA.search(kdo):
            statni += 1
            continue
        program = pole(text, "Operační program")
        cislo = pole(text, "Číslo výzvy") or None
        druh = pole(text, "Druh výzvy").lower()
        zacatek = pole(text, "Zahájení příjmu žádostí")
        konec = pole(text, "Ukončení příjmu žádostí")
        fn = "/Financni-nastroje/" in url

        info = text.split("Informace o výzvě", 1)[1] if "Informace o výzvě" in text else ""
        popis = re.sub(r"\s+", " ", re.split(r"\nAktuality\n|Odkaz na výzvu u poskytovatele", info)[0]).strip()
        if popis.startswith(title):
            popis = popis[len(title):].strip()

        typy = []
        for vzor, kanon in TYP:
            if re.search(vzor, kdo, re.I) and kanon not in typy:
                typy.append(kanon)
        oblast = []
        for vzor, kanon in OBLAST_PROGRAM:
            if re.search(vzor, f"{program} {title}", re.I):
                oblast += [k for k in kanon if k not in oblast]
        if fn and "podnikani" not in oblast:
            oblast.append("podnikani")

        ev = {"title": title[:80]}
        if konec:
            ev["deadline"] = konec[:40]
        f = {
            "_source_id": url,
            "title": title,
            "focus_area": (popis or f"Výzva programu {program}.")[:900],
            "oblast": oblast,
            "open_from": iso(zacatek),
            "deadline": iso(konec),
            "castky": [],
            "vyse_hlavni_czk": None,
            "spoluucast": None,
            "eligible_applicants": kdo[:1200] or None,
            "typ_zadatele": typy,
            "cilova_skupina": ["cizinci_migranti"] if "migrace" in oblast else [],
            "region": CR,
            "forma_podpory": ["zapujcka_uver"] if fn else ["dotace"],
            "zdroj_financovani": ["eu_fondy"],
            "rezim_prijmu": "prubezna" if "průběž" in druh else "kolova" if "kolov" in druh else "jednorazova_vyzva",
            "delka": None,
            "dalsi_datumy": [],
            "how_to_apply": ("Finanční nástroj se sjednává u banky nebo Národní rozvojové banky; podrobnosti u poskytovatele."
                             if fn else "Žádost se podává v systému IS KP21+ (iskp21.mssf.cz)."),
            "required_attachments": [],
            "source_doc": url,
            "cislo_vyzvy": cislo,
            "evidence": ev,
        }
        json.dump(f, io.open(os.path.join(OUT, jmeno), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        napsano += 1
    print(f"wrote {napsano} grants → {OUT}/ (jen pro státní úřad, vynecháno {statni})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
