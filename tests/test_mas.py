#!/usr/bin/env python3
"""Sběrač výzev MAS (`mas.py`, 2026-11-15): kdy je stránka otevřenou výzvou.

Výzvu MAS sběrač pozná podle budoucího data u řeči o příjmu žádostí. Věty jsou
skutečné z webů MAS (15. 11.): tytéž stránky nesou i konec realizace, jednání
komise nebo pozvánky, a ty výzvu otevřenou nedělají.

Spuštění:  python tests/test_mas.py
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from mas import NOT_A_CALL, boilerplate, intake_dates  # noqa: E402
from mas_list import norm  # noqa: E402

TODAY = date(2026, 11, 15)


def test_lhuta_prijmu_je_otevrena_vyzva():
    assert intake_dates("Příjem záměrů na MAS: od 29. 9. 2026 od 12:00 hod. do 30. 11. 2026", TODAY) == [date(2026, 11, 30)]
    assert intake_dates("Datum ukončení sběru žádostí je 18. 12. 2026", TODAY) == [date(2026, 12, 18)]
    assert intake_dates("Termín příjmu záměrů mimo MS21+ (tj. na MAS): 12. 12. 2026", TODAY) == [date(2026, 12, 12)]


def test_realizace_komise_a_akce_nejsou_lhuta():
    assert intake_dates("Datum ukončení realizace projektu: 31. 8. 2028", TODAY) == []
    assert intake_dates("projekty hodnotí Výběrová komise MAS, jednání proběhne 23.11.2026", TODAY) == []
    assert intake_dates("Podání žádosti do 14. 9. 2026. Nejzazší termín realizace projektu: 31. 8. 2028", TODAY) == []
    # Uplynulá lhůta příjmu: výzva je ukončená.
    assert intake_dates("Příjem žádostí do 31. 3. 2026", TODAY) == []


def test_zprava_o_vyzve_neni_vyzva():
    assert NOT_A_CALL.search("Výzva č. 4 programu MAS-IROP uzavřena, podáno 14 Žádostí o dotaci")
    assert NOT_A_CALL.search("ZMĚNA č.2 ve Výzvě č.4 MAS-IROP – HASIČI")
    assert not NOT_A_CALL.search("17. VÝZVA MAS Havlíčkův kraj - IROP - HASIČI 2026")


def test_sablona_webu_ale_ne_popisky():
    side = "<p>Zveme vás na lampionový průvod do Nezdic, sraz v 17 hodin u obecního úřadu.</p>"
    label = "<td>Datum ukončení příjmu</td>"
    pages = [f"{side}{label}<p>Výzva {i}: text výzvy, který je na každé stránce jiný a dost dlouhý.</p>" for i in range(3)]
    boiler = boilerplate(pages)
    assert "Zveme vás na lampionový průvod do Nezdic, sraz v 17 hodin u obecního úřadu." in boiler
    assert "Datum ukončení příjmu" not in boiler
    long_label = "<td>Datum ukončení příjmu Projektových záměrů na MAS Telčsko přes e-mail viz níže</td>"
    assert not boilerplate([long_label] * 3)
    assert boilerplate(pages[:2]) == frozenset()


def test_uzemi_vyzvy_jsou_obce_mas():
    from fix_dataset import mas_scope
    seeds = [{"mas": "MAS Česká Kanada o.p.s.", "web": "http://www.masck.cz", "kraje": ["Jihočeský kraj"],
              "obce": [{"kod": 546712, "nazev": "Jindřichův Hradec"}]},
             {"mas": "MAS Dvou krajů", "web": "https://mas2.cz/", "kraje": ["Kraj Vysočina", "Jihočeský kraj"], "obce": []}]
    rec = {"kind": "grant", "source": "mas", "source_url": "https://masck.cz/cs/vyzvy-mas/7-vyzva/",
           "facets": {"region": {"kraj": None, "celostatni": True}}}
    other = {"kind": "grant", "source": "mas", "source_url": "https://mas2.cz/vyzva", "facets": {}}
    assert mas_scope([rec, other], seeds) == 2
    reg = rec["facets"]["region"]
    assert rec["provider"] == "MAS Česká Kanada o.p.s."
    assert (reg["kraj"], reg["celostatni"], reg["vymezene_uzemi"]) == ("Jihočeský kraj", False, True)
    assert reg["obce"] == [{"kod": 546712, "nazev": "Jindřichův Hradec"}]
    # MAS přes hranici kraje: kraj nevíme, rozhodují obce.
    assert other["facets"]["region"]["kraj"] is None


def test_mas_a_pobocka_na_jedne_domene():
    from fix_dataset import mas_scope
    seeds = [{"mas": "MAS Krajina srdce, z.s.", "web": "http://www.maskrajinasrdce.cz", "kraje": ["Jihočeský kraj"],
              "obce": [{"kod": 1, "nazev": "Sedlec-Prčice"}, {"kod": 2, "nazev": "Nadějkov"}]},
             {"mas": "MMAS Krajina srdce pobočný spolek", "web": "https://www.maskrajinasrdce.cz/mmas-krajina-srdce-pro-tabor/",
              "kraje": ["Jihočeský kraj"], "obce": [{"kod": 3, "nazev": "Tábor"}]}]
    call = {"kind": "grant", "source": "mas", "source_url": "https://www.maskrajinasrdce.cz/14-vyzva-irop-vzdelavani-v-zs/"}
    city = {"kind": "grant", "source": "mas", "source_url": "https://www.maskrajinasrdce.cz/mmas-krajina-srdce-pro-tabor/1-vyzva/"}
    mas_scope([call, city], seeds)
    assert call["provider"] == "MAS Krajina srdce, z.s."
    assert city["provider"] == "MMAS Krajina srdce pobočný spolek"


def test_jmeno_mas_k_parovani():
    assert norm("MAS Česká Kanada o.p.s.") == "ceska kanada"
    assert norm("Místní akční skupina Rožnovsko, z.s.") == "roznovsko"


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    fails = []
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ok   {name}")
        except AssertionError as e:
            fails.append(name)
            print(f"  FAIL {name}: {e}")
    print(f"\n{len(tests) - len(fails)}/{len(tests)} prošlo")
    sys.exit(1 if fails else 0)
