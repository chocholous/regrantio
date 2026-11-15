#!/usr/bin/env python3
"""Parser detailu titulu Plzeňského kraje (`plzen_kraj_harvest.parse_detail`, 2026-11-14).

Vzorek je zkrácená skutečná stránka /verejnost/dotacnititul/1606/. Když
portál změní štítky, test to řekne dřív, než katalog tiše přijde o žadatele
nebo částky.

Spuštění:  python tests/test_plzen_kraj.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from plzen_kraj_harvest import kinds, parse_detail  # noqa: E402

PAGE = """
<h3>Účel podpory</h3><p>Plzeňský kraj bude podporovat obce do 30 000 obyvatel, které provozují zvýhodněnou dopravu pro seniory.</p>
<h3>Důvod podpory</h3><p>Zachování a dostupnost služby.</p>
<h3>Potenciální žadatelé</h3><p>Obce do 30 000 obyvatel.</p>
<h3>Termíny</h3><table><tr><td>Zveřejnění</td><td>26.8.2026</td></tr></table>
<h3>Financování</h3>
<table><tr><td>Předpokládaný celkový objem finančních prostředků</td><td>1 000 000 Kč</td></tr>
<tr><td>Maximální požadovaná částka žadosti o dotaci</td><td>500 000 Kč</td></tr></table>
<h3>Administrátoři</h3><p>Karolína B.</p>
<h3>Přílohy</h3>
<table><tbody>
<tr><td><a href="/verejnost/dotacnititul/1606/soubor/aaa/">Stáhnout</a></td>
<td>priloha-c-2 <span>Pravidla dotačního titulu</span></td><td>Příloha č. 2 - Pravidla pro žadatele a příjemce dotace</td></tr>
<tr><td><a href="/verejnost/dotacnititul/1606/soubor/bbb/">Stáhnout</a></td>
<td>priloha-c-3 <span>Ostatní přiloha</span></td><td>Příloha č. 3 - Vzor žádosti</td></tr>
</tbody></table>
"""


def test_stitky_detailu():
    d = parse_detail(PAGE, "1606")
    assert d["eligible"] == "Obce do 30 000 obyvatel."
    assert d["popis"].startswith("Plzeňský kraj bude podporovat obce")
    assert "Zachování a dostupnost" in d["popis"]
    assert d["alokace_czk"] == 1_000_000
    assert d["max_czk"] == 500_000
    assert d["zverejneno"] == "2026-08-26"


def test_prilohy_s_adresou_a_druhem():
    docs = parse_detail(PAGE, "1606")["dokumenty"]
    assert [x["role"] for x in docs] == ["pravidla_podminky", "formular"]
    assert docs[0]["url"] == "https://dotace.plzensky-kraj.cz/verejnost/dotacnititul/1606/soubor/aaa/"


def test_typ_zadatele_ze_slov():
    assert kinds("Obce do 30 000 obyvatel.") == ["obec_verejny_subjekt"]
    assert kinds(None) == []


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
