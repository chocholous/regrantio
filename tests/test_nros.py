#!/usr/bin/env python3
"""Grantový kalendář NROS (`nros.py`, 2026-11-15).

Vzorek je zkrácený skutečný kalendář: blok se značenou hlavičkou (program,
výzva, částka) a štítky v textu. Data jsou rozdělená značkami („18</b>. 5.“),
stav „Před otevřením“ nese loňské datum vyhlášení a věta o školské právnické
osobě „zřízené fyzickou osobou“ fyzickou osobu žadatelem nedělá.

Spuštění:  python tests/test_nros.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from nros import parse  # noqa: E402

PAGE = """
<h2>Aktuální grantové výzvy:</h2>
<div class="et_pb_pricing_heading"> <h2 class="et_pb_pricing_title">Program: Správný start</h2>
<span class="et_pb_best_value">4. kolo</span> </div>
<div class="et_pb_pricing_content_top"><span class="et_pb_et_price"><span class="et_pb_sum">45 000 Kč </span></span></div>
<ul><li><b>Oblast podpory: </b>Projekty pro děti a mládež v okolí prodejen Tesco.</li>
<li><b>Datum vyhlášení:</b> <b>18</b>. 5. 2026</li>
<li><b>Oprávnění žadatelé: </b>Spolek, pobočný spolek, ústav, příspěvková organizace</li>
<li><b>Stav programu:</b> Příjem žádostí 18. 5. – 14. 6. 2026 na https://corporate.itesco.cz/spravny-start</li></ul>
<div class="et_pb_pricing_heading"> <h2 class="et_pb_pricing_title">Program: Pomozte dětem</h2>
<span class="et_pb_best_value">Roční projekty</span> </div>
<div class="et_pb_pricing_content_top"><span class="et_pb_et_price"><span class="et_pb_sum">500 000 - 650 000 Kč</span></span></div>
<ul><li><b>Oblast podpory</b>: Přímá pomoc ohroženým dětem.</li>
<li><b>Datum vyhlášení:</b> 18. 2. 2025</li>
<li><b>Oprávnění žadatelé:</b> <b>S</b>polek, nadace, školská právnická osoba zřízená právnickou nebo fyzickou osobou.</li>
<li><b>Stav výzvy:</b> Před otevřením</li></ul>
<h3>Kontaktujte nás</h3>
"""


def test_kolo_s_oknem_prijmu():
    start = parse(PAGE)[0]
    assert start["nazev"] == "Správný start: 4. kolo (2026)"
    assert (start["open_from"], start["deadline"], start["max_czk"]) == ("2026-05-18", "2026-06-14", 45000)
    assert start["klic"] == "nros-spravny-start-4-kolo-2026"
    assert "neziskovka" in start["typ_zadatele"]


def test_pred_otevrenim_je_ohlasena_bez_terminu():
    roc = parse(PAGE)[1]
    assert roc["status"] == "announced"
    assert (roc["open_from"], roc["deadline"], roc["max_czk"]) == (None, None, 650000)
    assert roc["nazev"] == "Pomozte dětem: Roční projekty"
    assert roc["eligible"].startswith("Spolek")
    assert "fyzicka_osoba" not in roc["typ_zadatele"]


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
