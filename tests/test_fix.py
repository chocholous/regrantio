#!/usr/bin/env python3
"""Čištění textů a částka na žadatele (`fix_dataset.clean_text`, `amount_per_applicant`).

⚠ NAMĚŘENO 2026-09-26 na exportu 3 852 záznamů:

  - 20 záznamů neslo HTML entity doslova („fond &#8211; školství", „&hellip;"),
  - 549 ze 779 záznamů s částkou mělo jako `amount` celou alokaci výzvy
    (až 97 mld. Kč) a Grantio ji ukazovalo jako „Maximálně na žadatele".

Obě pravidla běží v tailu každé obnovy nad celým katalogem, takže se testují
z obou stran: co se změnit má, i co se změnit nesmí.

Spuštění:  python tests/test_fix.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from fix_dataset import amount_per_applicant, clean_text  # noqa: E402
from ingest_rich import _num  # noqa: E402


def test_entity_se_dekoduji():
    assert clean_text("Středočeský Infrastrukturní fond &#8211; školství") == "Středočeský Infrastrukturní fond – školství"
    assert clean_text("pro děti&hellip;") == "pro děti…"
    assert clean_text("&#8222;Obědy&#8220;") == "„Obědy“"


def test_zdvojene_mezery_a_okraje():
    assert clean_text("49. výzva –  Protipovodňová opatření ") == "49. výzva – Protipovodňová opatření"


def test_text_bez_vady_zustane_beze_zmeny():
    t = "Podpora sportu v obci Loket.\nDruhý odstavec."
    assert clean_text(t) == t
    assert clean_text(None) is None
    assert clean_text(42) == 42


def _rec(amount, alok=None, maxz=None):
    return {"amount": amount, "facets": {"vyse_alokace_czk": alok, "vyse_max_zadatel_czk": maxz}}


def test_castka_rovna_alokaci_neni_castka_na_zadatele():
    assert amount_per_applicant(_rec(97_021_880_911, alok=97_021_880_911, maxz=97_021_880_911)) == (None, None)


def test_strop_na_zadatele_se_zachova():
    assert amount_per_applicant(_rec(500_000, alok=21_000_000, maxz=500_000)) == (500_000, 500_000)


def test_castka_bez_alokace_se_nemeni():
    assert amount_per_applicant(_rec(30_000)) == (30_000, None)


def test_chybejici_castka_se_doplni_ze_stropu():
    assert amount_per_applicant(_rec(None, alok=21_000_000, maxz=400_000)) == (400_000, 400_000)


def test_strop_vyssi_nez_alokace_je_spatne_prectene_cislo():
    # „125 000 Kč / 5 000 EUR" slepené do 1 250 005 000 při alokaci 5 mil.
    assert amount_per_applicant(_rec(None, alok=5_000_000, maxz=1_250_005_000)) == (None, None)


def test_parser_bere_prvni_cislo():
    assert _num("125 000 Kč / 5 000 EUR") == 125_000
    assert _num("4 700 000") == 4_700_000
    assert _num("70 %") == 70
    assert _num("1,5 mil. Kč") == 1_500_000
    assert _num("2 mld. Kč") == 2_000_000_000
    assert _num("nestanoveno") is None
    assert _num(30000) == 30000


def test_null_zustava_null():
    assert amount_per_applicant(_rec(None, alok=21_000_000)) == (None, None)


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
            fails.append((name, e))
            print(f"  FAIL {name}: {e}")
        except Exception as e:  # noqa: BLE001
            fails.append((name, e))
            print(f"  ERR  {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - len(fails)}/{len(tests)} prošlo")
    sys.exit(1 if fails else 0)
