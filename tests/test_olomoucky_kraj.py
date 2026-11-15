#!/usr/bin/env python3
"""Sběrač Olomouckého kraje (`olomoucky_harvest`, přepsaný 2026-11-15).

Vzorek detailu je zkrácená skutečná stránka titulu 06_02_01. Když web změní
štítky nebo zápis termínů v adrese, test to řekne dřív, než katalog tiše
přijde o termíny, dokumenty nebo žadatele.

Spuštění:  python tests/test_olomoucky_kraj.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from olomoucky_harvest import (  # noqa: E402
    applicant_kinds, dates_from_slug, dates_from_text, parse_detail, tidy_name,
)

PAGE = """
<div class="grant-detail"> <table> <tbody>
<tr > <td><strong>Název</strong></td> <td> <h3 style="color: black"> 06_02_01_Podpora sportovních akcí </h3> </td> </tr>
<tr > <td><strong>Anotace</strong></td> <td> Z dotačního titulu je možné žádat o podporu sportovních akcí. </td> </tr>
<tr > <td><strong>Termín příjmu žádostí</strong></td> <td> 7.4. - 17.4.2026 do 12:00 </td> </tr>
<tr > <td><strong>Oprávnění žadatelé</strong></td> <td> <br /><a
   href="/uploads/grant/324/doc/okruh-opravnenych-zadatelu.pdf"
   target="_BLANK" >Okruh oprávněných žadatelů v dotačním titulu.pdf</a> </td> </tr>
<tr> <td><strong>Pravidla</strong></td> <td> <a
   href="/uploads/grant/324/doc/pravidla-dotacniho-titulu-1.pdf" target="_BLANK" >Pravidla dotačního titulu 1.pdf</a> </td> </tr>
<tr> <td><strong>Žádost vzor</strong></td> <td> <a href="/uploads/grant/324/doc/vzor-zadosti.pdf" target="_BLANK" >Vzor žádosti.pdf</a> </td> </tr>
</tbody> </table>
<h3>Ukončený dotační program/titul</h3>
<table><tbody><tr> <td> <strong>Vyhodnocení</strong> </td> <td> <a href="/uploads/grant/324/doc/vyhodnoceni.pdf">vyhodnocení.pdf</a> </td> </tr></tbody></table>
</div>
"""


def test_detail_stitky_a_dokumenty():
    d = parse_detail(PAGE)
    assert (d["kod"], d["nazev"]) == ("06_02_01", "Podpora sportovních akcí")
    assert d["popis"].startswith("Z dotačního titulu")
    assert dates_from_text(d["termin"]) == ("2026-04-07", "2026-04-17")
    assert d["eligible_pdf"] == "https://www.olkraj.cz/uploads/grant/324/doc/okruh-opravnenych-zadatelu.pdf"
    # Vyhodnocení ukončeného titulu je výsledek, ne podklad k žádosti.
    assert [x["role"] for x in d["dokumenty"]] == ["pravidla_podminky", "formular", "pravidla_podminky"]


def test_terminy_z_adresy():
    p = "https://www.olkraj.cz/dotace-granty-prispevky-krajske-dotacni-programy-2026/"
    assert dates_from_slug(p + "06-02-01-podpora-sportovnich-akci-prijem-zadosti-07-04-17-04-2026") == ("2026-04-07", "2026-04-17")
    assert dates_from_slug(p + "13-01-02-dotace-prijem-zadosti-12-01-2026-19-01-2026") == ("2026-01-12", "2026-01-19")
    assert dates_from_slug(p + "13-02-01-dotace-prijem-zadosti-od-12-01-2026-do-09-02-2026") == ("2026-01-12", "2026-02-09")
    assert dates_from_slug(p + "12-01-01-akce-cestovniho-ruchu-prijem-zadosti-12-26-1-2026") == ("2026-01-12", "2026-01-26")
    assert dates_from_slug(p + "07-01-01-obnova-kulturnich-pamatek-prijem-dotaci-19-01-30-01-2026") == ("2026-01-19", "2026-01-30")
    assert dates_from_slug(p + "10-03-program-na-podporu-primarni-pece") == (None, None)


def test_nazev_bez_terminu_verzalek_a_pomlcky():
    assert tidy_name("06_01_01_Podpora celoroční sportovní činnosti (příjem žádostí od 4.9. - 18.9.2026)") == \
        ("06_01_01", "Podpora celoroční sportovní činnosti")
    assert tidy_name("08_01_01_PODPORA PREVENCE KRIMINALITY (výsledky budou schvalovány na ZOK)") == \
        ("08_01_01", "Podpora prevence kriminality")
    assert tidy_name("03_01_03 – Obnova enviromentálních funkcí území") == ("03_01_03", "Obnova enviromentálních funkcí území")
    assert tidy_name("Dotační program 10_02_Program pro vzdělávání ve zdravotnictví") == \
        ("10_02", "Program pro vzdělávání ve zdravotnictví")
    assert tidy_name("08_01_04_PODPORA SLUŽEB NA ÚZEMÍ OLOMOUCKÉHO KRAJE")[1] == "Podpora služeb na území Olomouckého kraje"


def test_vyluka_neni_opravneny_zadatel():
    text = ("Žadatelem může být pouze: I. obec v územním obvodu Olomouckého kraje, II. dobrovolný svazek obcí. "
            "Žadatelem v dotačním titulu nemůže být: fyzická osoba, příspěvková organizace zřízená krajem.")
    assert applicant_kinds(text) == ["obec_verejny_subjekt"]


def test_obecna_pravnicka_osoba_a_spolek():
    assert applicant_kinds("Žadatelem může být pouze: právnická osoba: I. jejímž předmětem činnosti je sport") == \
        ["firma", "neziskovka"]
    assert applicant_kinds("Žadatelem může být pouze právnická osoba, kterou je spolek hasičů") == ["neziskovka"]
    assert applicant_kinds(None) == []


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
