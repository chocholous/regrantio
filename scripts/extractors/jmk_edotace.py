#!/usr/bin/env python3
"""Vrstva 2 pro Jihomoravský kraj, dotační portál e‑dotace.jmk.cz (2026‑11‑10).

Zdroj: `scripts/jmk_edotace.py`. DETERMINISTICKY, bez modelu: portál má
u programu řádky „štítek: hodnota“ a pod nimi dotační tituly, každý
s vlastním příjemcem, rozpětím podpory a spoluúčastí:

  Objem finančních prostředků vyčleněných na program: 25000000 Kč
  Cíl/účel programu: …
  Příjem žádostí: 02.11.2026 00:01 - 27.11.2026 23:00
  Dotační titul: DT 1 - …
  Příjemce podpory: …
  Minimální výše podpory na jeden projekt/akci/činnost: 50000 Kč
  Maximální výše podpory na jeden projekt/akci/činnost: 300000 Kč
  Minimální podíl spoluúčasti žadatele: 50 %

Jeden záznam na program. Lhůta je nejpozdější konec příjmu, začátek ten
nejdřívější; strop na žadatele nejvyšší maximum z titulů. Typ žadatele se čte
z řádků „Příjemce podpory“ podle slov, která ho jmenují; co neříkají, zůstane
prázdné („nehalucinovat“, CLAUDE.md).
"""
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

IN = "data/jmk_edotace_in"
OUT = "data/jmk_edotace_out"
JMK = [{"nazev": "Jihomoravský kraj", "obec": None, "okres": None, "kraj": "Jihomoravský kraj", "celostatni": False}]
DT = re.compile(r"(\d{1,2})\.(\d{1,2})\.(20\d\d)")

TYP = [
    (r"\bobc[eíi]\b|\bobec\b|svazk\w* obc|městsk\w+ část|\bměst[ao]\b", "obec_verejny_subjekt"),
    (r"spolk|spolkov\w+ rejstřík|obecně prospěšn|zapsan\w+ ústav|nadac|nadačn|nestátn\w* nezisk|nezisk\w+ organizac|církevn\w+ právnick", "neziskovka"),
    (r"podnikaj\w+ právnick|obchodn\w+ společnost|podnikatel|provozuj\w+ prodejn", "firma"),
    (r"podnikaj\w+ (?:\w+ (?:nebo|či|a) )?fyzick|fyzick\w+ osob\w+ podnikaj|OSVČ", "osvc_podnikatel"),
    (r"příspěvkov\w+ organizac", "prispevkova_organizace"),
    (r"škol|vysok\w+ učen", "skola_vyzkumna_org"),
    (r"sportovn\w+ klub|tělocvičn\w+ jednot|tělovýchovn", "sportovni_klub"),
    (r"církev|nábožensk\w+ společnost", "cirkev"),
    (r"fyzick\w+ (nebo|či|a) právnick|fyzick\w+ osob(?!\w* podnikaj)", "fyzicka_osoba"),
]
# Fyzická i právnická osoba bez omezení = kdokoli (kromě veřejné správy jmenovitě).
KDOKOLI = re.compile(r"fyzick\w+ nebo právnick\w+ osob", re.I)
OBLAST = [
    (r"kultur|památ|umělec|lidov\w+ oděv|folklor|audiovizu", "kultura_umeni"),
    (r"památ", "pamatkova_pece"),
    (r"sport|tělovýchov|cyklisti", "sport_volny_cas"),
    (r"venkov|obchůdek|prodejn|vinař|ovocnář|regionální produkc|zeměděl", "komunitni_rozvoj"),
    (r"cyklisti|doprav", "doprava_mobilita"),
    (r"turisti|cestovní ruch", "cestovni_ruch"),
    (r"sociáln|senior|rodin|pečuj|protidrog|potravinov", "socialni_sluzby"),
    (r"zdravot", "zdravi"),
    (r"mládež|děti|škol|vzdělá", "vzdelavani_mladez"),
    (r"životní prostředí|EVVO|ekolog|vod[ay]", "zivotni_prostredi"),
    (r"hasič|JSDH|bezpečnost", "bezpecnost"),
    (r"územní\w* plán|infrastruktur", "bydleni_infrastruktura"),
]


def iso(d):
    return f"{d[2]}-{int(d[1]):02d}-{int(d[0]):02d}"


def radky(text, stitek):
    return [m.group(1).strip() for m in re.finditer(rf"^{re.escape(stitek)}:\s*(.+)$", text, re.M)]


def kc(s):
    m = re.search(r"([\d\s ]+)\s*Kč", s or "")
    if not m:
        return None
    try:
        return int(re.sub(r"\D", "", m.group(1)))
    except ValueError:
        return None


def main():
    if not os.path.isdir(IN):
        print(f"✖ Chybí {IN}. Spusť nejdřív harvest a build_extract_input (refresh_run --only jmk_edotace).")
        return 1
    soubory = sorted(f for f in os.listdir(IN) if re.match(r"grant_\d+\.json$", f))
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if re.match(r"grant_\d+\.json$", f):
            os.remove(os.path.join(OUT, f))

    napsano = preskoceno = 0
    for jmeno in soubory:
        r = json.load(io.open(os.path.join(IN, jmeno), encoding="utf-8"))
        url = r.get("id") or ""
        text = r.get("body") or ""
        title = re.sub(r"\s+", " ", r.get("title") or "").strip()
        if "programDetail" not in url or not title:
            preskoceno += 1
            continue

        prijem = radky(text, "Příjem žádostí")
        data = [DT.findall(p) for p in prijem]
        zacatky = [iso(d[0]) for d in data if d]
        konce = [iso(d[1]) for d in data if len(d) > 1]
        open_from = min(zacatky) if zacatky else None
        deadline = max(konce) if konce else None

        objem = kc((radky(text, "Objem finančních prostředků vyčleněných na program") or [""])[0])
        maxima = [kc(x) for x in radky(text, "Maximální výše podpory na jeden projekt/akci/činnost")]
        maxima = [x for x in maxima if x]
        strop = max(maxima) if maxima else None
        podily = [int(m.group(1)) for x in radky(text, "Minimální podíl spoluúčasti žadatele")
                  for m in [re.search(r"(\d{1,3})\s*%", x)] if m]
        prijemci = radky(text, "Příjemce podpory")
        kdo = " · ".join(dict.fromkeys(prijemci))
        tituly = radky(text, "Dotační titul")
        cil = (radky(text, "Cíl/účel programu") or [""])[0]
        cislo = (radky(text, "Číslo usnesení") or [None])[0]

        # „Podnikající právnická nebo fyzická osoba“ je OSVČ, ne občan.
        bez_podnik = re.sub(r"podnikaj\w+ (?:\w+ (?:nebo|či|a) )?fyzick\w+ osob\w*", "", kdo, flags=re.I)
        typy = []
        for vzor, kanon in TYP:
            hledat = bez_podnik if kanon == "fyzicka_osoba" else kdo
            if re.search(vzor, hledat, re.I) and kanon not in typy:
                typy.append(kanon)
        if KDOKOLI.search(kdo):
            for kanon in ("neziskovka", "obec_verejny_subjekt", "firma", "osvc_podnikatel", "fyzicka_osoba"):
                if kanon not in typy:
                    typy.append(kanon)

        tema = f"{title} {cil} {' '.join(tituly)}"
        oblast = []
        for vzor, kanon in OBLAST:
            if re.search(vzor, tema, re.I) and kanon not in oblast:
                oblast.append(kanon)

        castky = []
        if strop:
            castky.append({"typ": "max_zadatel", "hodnota": strop})
        if objem:
            castky.append({"typ": "alokace", "hodnota": objem})

        ev = {"title": title[:80]}
        if prijem:
            ev["deadline"] = prijem[0][:50]
        if strop:
            ev["vyse_max_zadatel_czk"] = next(x for x in radky(text, "Maximální výše podpory na jeden projekt/akci/činnost") if kc(x) == strop)[:40]

        popis_titulu = "; ".join(tituly[:8])
        f = {
            "_source_id": url,
            "title": title,
            "focus_area": (cil + (f" Dotační tituly: {popis_titulu}." if popis_titulu else ""))[:900] or title,
            "oblast": oblast,
            "open_from": open_from,
            "deadline": deadline,
            "castky": castky,
            "vyse_hlavni_czk": strop,
            "spoluucast": bool(podily and max(podily) > 0),
            "eligible_applicants": kdo[:1200] or None,
            "typ_zadatele": typy,
            "cilova_skupina": [],
            "region": JMK,
            "forma_podpory": ["dotace"],
            "zdroj_financovani": ["krajsky"],
            "rezim_prijmu": "jednorazova_vyzva",
            "delka": None,
            "dalsi_datumy": [],
            "how_to_apply": "Žádost se podává elektronicky na dotačním portálu Jihomoravského kraje (e-dotace.jmk.cz); postup popisuje Příručka pro žadatele eDotace.",
            "required_attachments": [],
            "source_doc": url,
            "cislo_vyzvy": f"usnesení {cislo}" if cislo else None,
            "evidence": ev,
        }
        json.dump(f, io.open(os.path.join(OUT, jmeno), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        napsano += 1
    print(f"wrote {napsano} grants → {OUT}/ (přeskočeno {preskoceno})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
