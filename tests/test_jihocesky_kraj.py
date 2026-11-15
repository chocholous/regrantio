#!/usr/bin/env python3
"""Sběrač Jihočeského kraje: párování plánovaného programu s vyhlášenou výzvou (2026-11-15).

Řádek tabulky „dotační programy Jčk <rok>“ a pozdější výzva téhož programu musí
dostat týž `klic`, jinak upsert nechá v katalogu oba záznamy. Párování ale nesmí
spojit dva různé programy ani dva ročníky.

Spuštění:  python tests/test_jihocesky_kraj.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from jihocesky_harvest import norm, same_program, same_year, slug  # noqa: E402


def test_jmeno_bez_roku_kraje_a_diakritiky():
    assert norm("Program obnovy venkova Jihočeského kraje v roce 2027") == "program obnovy venkova"
    assert slug("Podpora jednotek SDH obcí Jihočeského kraje v oblasti investičních projektů") == \
        "podpora-jednotek-sdh-obci-v-oblasti-investicnich-projektu"


def test_tentyz_program_se_spari():
    assert same_program("Dotační program Podpora kultury v Jihočeském kraji 2027", "Podpora kultury 2027")
    assert same_program("Podpora jednotek SDH obcí Jihočeského kraje v oblasti investičních projektů 2027",
                        "Podpora jednotek SDH obcí Jihočeského kraje v oblasti investičních projektů")


def test_ruzne_programy_se_nesparuji():
    # Investiční a neinvestiční výzva SDH jsou dva programy.
    assert not same_program("Podpora jednotek SDH obcí v oblasti neinvestičních projektů",
                            "Podpora jednotek SDH obcí v oblasti investičních projektů")
    # Krátké jméno nestačí: „Podpora“ je v názvu skoro každého programu.
    assert not same_program("Podpora", "Podpora kultury 2027")


def test_rocnik_musi_sedet():
    call = {"nazev": "Podpora jednotek SDH obcí", "open_from": "2026-03-09", "deadline": "2026-06-30"}
    assert not same_year(call, 2027)
    assert same_year({**call, "open_from": "2027-01-15", "deadline": "2027-02-28"}, 2027)


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
