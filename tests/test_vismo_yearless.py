#!/usr/bin/env python3
"""Lhůta psaná bez roku: rok určuje datum vyvěšení, ne rok čtení.

NAMĚŘENO 2026-11-11 (Hodonín): programy píšou „od 1. 11. do 10. 12.“ bez roku.
Letošní ročníky proto v katalogu chyběly a staré, kterým rok doplnil model,
stály mezi otevřenými. Tyhle testy drží pravidlo `vismo_refresh.yearless_window`.

    python tests/test_vismo_yearless.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from vismo_refresh import listing_date, submission_window, yearless_window  # noqa: E402

D = datetime.date
TODAY = D(2026, 11, 11)
PROGRAM = ("Čl. 5 Lhůta pro podání žádosti Žádosti o dotace na běžný rok je možné odevzdávat "
           "od 01.11. do 10.12. aktuálního roku. Při doručení poštou s razítkem pošty s datem 10.12. Čl. 6 Kritéria")


def test_letosni_program_dostane_rok_vyveseni():
    of, dl, quote = yearless_window(PROGRAM, D(2026, 9, 16), TODAY)
    assert (of, dl) == ("2026-11-01", "2026-12-10")
    assert "od 01.11. do 10.12." in quote


def test_stary_program_zustane_ve_svem_roce():
    assert yearless_window(PROGRAM, D(2017, 9, 15), TODAY)[:2] == ("2017-11-01", "2017-12-10")


def test_lhuta_pres_novy_rok():
    text = "Lhůta pro podání žádosti: odevzdávat od 16.12. aktuálního roku do 06.01. běžného roku. Čl. 7"
    assert yearless_window(text, D(2026, 9, 21), TODAY)[:2] == ("2026-12-16", "2027-01-06")


def test_vic_kol_plati_nejblizsi_ktere_neminulo():
    text = ("Lhůta pro podání žádosti: žádosti je možné odevzdávat od 2.1. do 31.1. běžného roku, "
            "od 1.4. do 30.4. běžného roku a od 1.9. do 30.9. běžného roku. Čl. 4")
    assert yearless_window(text, D(2026, 9, 21), TODAY)[:2] == ("2027-01-02", "2027-01-31")


def test_odkaz_na_clanek_uprostred_vety_neni_konec_oddilu():
    text = ("Lhůta pro podání žádosti Žádosti budou podávány ve dvou kolech. 1. kolo je určeno na podporu "
            "projektů v souladu s čl. 1. Žádosti v 1. kole je možné podávat od 01.11. do 10.12. aktuálního roku. Čl. 6")
    assert yearless_window(text, D(2026, 9, 16), TODAY)[:2] == ("2026-11-01", "2026-12-10")


def test_lhuta_s_rokem_sem_nepatri():
    text = "Lhůta pro podání žádosti je od 1. 11. 2026 do 10. 12. 2026. Čl. 6"
    assert yearless_window(text, D(2026, 9, 16), TODAY) == (None, None, None)
    assert submission_window(text, TODAY)[:2] == ("2026-11-01", "2026-12-10")


def test_bez_oddilu_lhuty_nic():
    assert yearless_window("Konzultace od 1.10. do 31.10. s pracovníkem odboru.", D(2026, 9, 16), TODAY) == (None, None, None)


def test_datum_vyveseni_z_vypisu():
    assert listing_date({"date": "15.9.2017"}) == D(2017, 9, 15)
    assert listing_date({"date": ""}) is None
    assert listing_date({}) is None


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
            print(f"  FAIL {name}  {e}")
    print(f"\n{len(tests) - len(fails)}/{len(tests)} prošlo")
    sys.exit(1 if fails else 0)
