#!/usr/bin/env python3
"""Vrstva 2 pro Národní program Životní prostředí (narodniprogramzp.cz).

Zdroj: detaily výzev z `scripts/npzp.py` (výpis aktuální nabídky). Přidáno
2026-10-03: konkurence z něj má výzvy, katalog neměl žádnou.

DETERMINISTICKY, bez modelu. Detail výzvy má štítky na vlastních řádcích:

  Příjem žádostí:            10.10.2025 - 30.6.2027
  Alokace: 80 000 000 Kč
  <perex>
  Na co můžete dotaci získat · Kdo může žádat · Výše příspěvku
  Podmínky výzvy             „Výzva je vyhlášena jako jednokolová nesoutěžní“
  Termíny                    „Ukončení příjmu žádostí: 30. 6. 2027 …, nebo do vyčerpání alokace.“
  Jak podat žádost

Typ žadatele se čte z oddílu „Kdo může žádat“ podle slov, která ho jmenují
(obce, spolky, podnikatelé…), a jen z něj: navigace a patička webu zmiňují
kdeco. Co oddíl neříká, zůstane prázdné; „nehalucinovat“ (CLAUDE.md).
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

IN = "data/npzp_in"
OUT = "data/npzp_out"
CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
DATUM = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")
ODDILY = ["Na co můžete dotaci získat", "Kdo může žádat", "Výše příspěvku", "Podmínky výzvy",
          "Termíny", "Jak podat žádost", "Povinná publicita", "Kontaktní osoby", "Dokumenty ke stažení"]

# Kdo může žádat → kanonický typ žadatele (`data/consolidation_maps.json`).
TYP = [
    (r"\bobc[eíi]|\bobec\b|kraj[eůi]?\b|svazk\w* obc|dobrovoln\w+ svazk|městsk\w+ část|\bměst[ao]\b", "obec_verejny_subjekt"),
    # „ústav“ jen jako zapsaný ústav: Český hydrometeorologický ústav je státní organizace.
    (r"spolk|obecně prospěšn|zapsan\w+ ústav|nadac|nadačn|nestátn\w* (?:nezisk|subjekt)|zapsan\w+ spol", "neziskovka"),
    # Poradci (renovační pas) jsou podnikatelé: firma i živnostník.
    (r"podnikatel|podnik[ůy]?\b|obchodn\w+ společnost|provozovatel\w* zařízení|právnick\w+ osob\w+ podnikaj|poskytuj\w+ poradensk", "firma"),
    (r"fyzick\w+ osob\w+ podnikaj|OSVČ|poskytuj\w+ poradensk", "osvc_podnikatel"),
    (r"příspěvkov\w+ organizac|resortn\w+ organizac|organizačn\w+ slož\w+ státu|správ\w+ národní\w* park|Správa jeskyní|Agentura ochrany přírody|hydrometeorologick\w+ ústav", "prispevkova_organizace"),
    (r"škol|výzkumn\w+ organizac|vysok\w+ učen", "skola_vyzkumna_org"),
    (r"církev|náboženské? společnost", "cirkev"),
    (r"vlastní\w* (?:rodinn|bytov)|fyzick\w+ osob(?!\w* podnikaj)", "fyzicka_osoba"),
]
# Téma výzvy → kanonická oblast; životní prostředí mají všechny.
OBLAST = [
    (r"renovac|obytn\w+ budov|rodinn\w+ d[ůo]m|bytov\w+ d[ůo]m|bydlen", "bydleni_infrastruktura"),
    (r"návštěvnick|informačn\w+ střed|turist", "cestovni_ruch"),
    (r"vzdělávac|osvět|ekologick\w+ výchov", "vzdelavani_mladez"),
]


def iso(s):
    m = DATUM.search(s or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def oddil(text, nazev):
    """Text oddílu od jeho nadpisu po nadpis dalšího oddílu."""
    i = text.find(nazev)
    if i < 0:
        return ""
    zbytek = text[i + len(nazev):]
    konec = min([zbytek.find(o) for o in ODDILY if o != nazev and zbytek.find(o) > 0] or [len(zbytek)])
    s = zbytek[:konec]
    s = s.split("Kompletní podmínky naleznete")[0].split("Maximální výše podpory")[0]
    return re.sub(r"\s*\n\s*", " ", s).strip(" .\n")


def castka(radek):
    """„600 tis. Kč“ / „2 mil. Kč“ / „80 000 000 Kč“ → Kč."""
    m = re.search(r"([\d\s ]+(?:,\d+)?)\s*(mil|mld|tis)?\.?\s*Kč", radek or "")
    if not m:
        return None
    cislo = m.group(1).replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        hodnota = float(cislo)
    except ValueError:
        return None
    return int(hodnota * {"mil": 1_000_000, "mld": 1_000_000_000, "tis": 1_000}.get(m.group(2) or "", 1))


def main():
    if not os.path.isdir(IN):
        print(f"✖ Chybí {IN}. Spusť nejdřív harvest a build_extract_input (refresh_run --only npzp).")
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
        title = re.sub(r"\s+", " ", r.get("title") or "").strip()
        if "detail-vyzvy" not in url or not title:
            preskoceno += 1
            continue

        prijem = re.search(r"Příjem žádostí:\s*\n?\s*([^\n]+)", text)
        data = DATUM.findall(prijem.group(1)) if prijem else []
        open_from = f"{data[0][2]}-{int(data[0][1]):02d}-{int(data[0][0]):02d}" if data else None
        deadline = f"{data[1][2]}-{int(data[1][1]):02d}-{int(data[1][0]):02d}" if len(data) > 1 else None
        terminy = oddil(text, "Termíny")
        konec_radek = re.search(r"Ukončení příjmu žádostí:\s*([^\n]+(?:\n[^\n]*vyčerpání[^\n]*)?)", text)
        if konec_radek and iso(konec_radek.group(1)):
            deadline = iso(konec_radek.group(1))

        alokace_m = re.search(r"Alokace:\s*([^\n]+)", text)
        alokace = castka(alokace_m.group(1)) if alokace_m else None

        perex = ""
        if alokace_m:
            po = text[alokace_m.end():]
            perex = re.sub(r"\s+", " ", po.split("Podat žádost")[0]).strip()[:600]

        na_co = oddil(text, "Na co můžete dotaci získat")
        kdo = oddil(text, "Kdo může žádat")
        vyse = oddil(text, "Výše příspěvku")
        podminky = oddil(text, "Podmínky výzvy")
        jak = oddil(text, "Jak podat žádost")

        typy = []
        for vzor, kanon in TYP:
            if re.search(vzor, kdo, re.I) and kanon not in typy:
                typy.append(kanon)
        if re.search(r"všechny právnické osoby", kdo, re.I):
            for kanon in ("obec_verejny_subjekt", "neziskovka", "firma", "prispevkova_organizace", "skola_vyzkumna_org", "cirkev"):
                if kanon not in typy:
                    typy.append(kanon)

        oblast = ["zivotni_prostredi"]
        # Jen název a perex: podrobnosti zmiňují budovy i střediska mimochodem.
        tema = f"{title} {perex}"
        for vzor, kanon in OBLAST:
            if re.search(vzor, tema, re.I) and kanon not in oblast:
                oblast.append(kanon)

        # „Maximální výše podpory na jeden projekt činí 50 mil. Kč“, někdy víc
        # řádků podle druhu žadatele: strop je nejvyšší z nich.
        stropy = [(castka(m.group(1)), m) for m in re.finditer(r"Maximální výše podpory[^\n]*?(?:činí|:)\s*([^\n]+)", text)]
        stropy = [(c, m) for c, m in stropy if c]
        strop, strop_m = max(stropy, key=lambda x: x[0]) if stropy else (None, None)
        procento = re.search(r"(\d{1,3})\s*%\s*z celkových způsobilých výdajů", vyse)
        spoluucast = bool(procento and int(procento.group(1)) < 100)

        druh = podminky.lower()
        rezim = ("prubezna" if "nesoutěžní" in druh or "vyčerpání alokace" in terminy
                 else "kolova" if "kolov" in druh and "jednokolov" not in druh
                 else "jednorazova_vyzva")

        castky = []
        if strop:
            castky.append({"typ": "max_zadatel", "hodnota": strop})
        if alokace:
            castky.append({"typ": "alokace", "hodnota": alokace})

        konec = []
        for vzor in (enrich._CLOSED, enrich._MAY):
            for k in vzor.finditer(terminy):
                veta = enrich._sentence(terminy, k.start(), k.end())
                if veta not in konec:
                    konec.append(veta)

        npo = "NPO" in title
        cislo = re.search(r"č\.\s*(\d+/\d{4})", title)
        ev = {"title": title[:80]}
        if prijem:
            ev["deadline"] = prijem.group(1).strip()[:50]
        if strop_m:
            ev["vyse_max_zadatel_czk"] = strop_m.group(1).strip()[:40]

        f = {
            "title": title,
            "focus_area": perex or na_co[:600] or f"Výzva Národního programu Životní prostředí: {title}.",
            "oblast": oblast,
            "open_from": open_from,
            "deadline": deadline,
            "castky": castky,
            "vyse_hlavni_czk": strop,
            "spoluucast": spoluucast,
            "eligible_applicants": kdo[:1200] or None,
            "typ_zadatele": typy,
            "cilova_skupina": [],
            "region": CR,
            "forma_podpory": ["dotace"],
            "zdroj_financovani": ["npo"] if npo else ["narodni_rozpocet"],
            "rezim_prijmu": rezim,
            "delka": None,
            "dalsi_datumy": [{"datum": None, "popis": v} for v in konec[:3]],
            "how_to_apply": jak[:600] or "Žádost se podává elektronicky v Agendovém informačním systému SFŽP ČR (zadosti.sfzp.cz).",
            "required_attachments": [],
            "source_doc": url,
            "cislo_vyzvy": (f"{'NPO ' if npo else ''}{cislo.group(1)} NPŽP" if cislo else None),
            "evidence": ev,
        }
        json.dump(f, io.open(os.path.join(OUT, jmeno), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        napsano += 1
    print(f"wrote {napsano} grants → {OUT}/ (přeskočeno {preskoceno})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
