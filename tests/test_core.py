#!/usr/bin/env python3
"""Testy KRITICKÉ logiky pipeline — to, co při tichém rozbití zkazí data v produktu.

Proč zrovna tyhle tři oblasti:
  • compute_status  — jediné místo, kde vzniká open/closed. Chyba tady = špatné statusy
                      u 3400 grantů a nikdo si toho nemusí všimnout (data „vypadají OK").
  • upsert_v2       — rozhoduje, co se při refreshi přepíše. Chyba = ztráta obohacení
                      z vrstvy 2 nebo naopak neaktualizovaná data.
  • derive_deadlines— odvozuje termín z textu. Chyba = FABRIKOVANÉ datum v produktu.

Spuštění:  python -m pytest tests/ -q      (nebo: python tests/test_core.py)
Bez pytestu funguje i přímé spuštění — má vlastní mini-runner.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from opportunities import compute_status          # noqa: E402
from upsert_v2 import merge, _enriched            # noqa: E402
import derive_deadlines as dd                     # noqa: E402

TODAY = datetime.date(2026, 7, 31)


# ---------------------------------------------------------------- compute_status
def test_status_prubezne_je_open():
    st, _ = compute_status(None, "průběžně", TODAY)
    assert st == "open"


def test_status_bez_deadlinu_je_unknown():
    st, _ = compute_status(None, None, TODAY)
    assert st == "unknown"


def test_status_minuly_deadline_je_closed():
    st, _ = compute_status("2026-01-01", "2026-07-30", TODAY)
    assert st == "closed"


def test_status_pred_zacatkem_je_announced():
    st, _ = compute_status("2026-09-01", "2026-12-31", TODAY)
    assert st == "announced"


def test_status_v_prubehu_je_open():
    st, _ = compute_status("2026-07-01", "2026-09-30", TODAY)
    assert st == "open"


def test_status_deadline_dnes_je_jeste_open():
    """Hraniční den: dnešek JE poslední den příjmu → výzva se nesmí tvářit jako zavřená."""
    st, _ = compute_status("2026-07-01", "2026-07-31", TODAY)
    assert st == "open"


# ---------------------------------------------------------------- upsert_v2
def _raw(**kw):
    base = {"id": "x", "title": "T", "deadline": "2026-01-01", "provenance": {"layer": 1},
            "facets": {"oblast": []}}
    base.update(kw)
    return base


def _rich(**kw):
    base = {"id": "x", "title": "Bohatý titul", "deadline": "2026-01-01",
            "focus_area": "popis z vrstvy 2", "citations": [{"field": "deadline"}],
            "provenance": {"layer": 2}, "facets": {"oblast": ["kultura_umeni"]}}
    base.update(kw)
    return base


def test_merge_syrovy_zaznam_se_prepise_cely():
    old, new = _raw(title="staré"), _raw(title="nové", deadline="2026-09-09")
    out = merge(old, new)
    assert out["title"] == "nové" and out["deadline"] == "2026-09-09"


def test_merge_obohaceny_zaznam_si_nechá_facety_a_popis():
    """Refresh NESMÍ zahodit práci vrstvy 2 — přepisuje jen fakta z listingu."""
    old = _rich()
    new = _raw(deadline="2026-09-09", title="chudý titul z listingu")
    out = merge(old, new)
    assert out["deadline"] == "2026-09-09"                    # fakt se aktualizoval
    assert out["focus_area"] == "popis z vrstvy 2"            # obohacení zůstalo
    assert out["facets"]["oblast"] == ["kultura_umeni"]
    assert out["title"] == "Bohatý titul"


def test_merge_neprepise_fakt_hodnotou_null():
    old = _rich(deadline="2026-05-05")
    out = merge(old, _raw(deadline=None))
    assert out["deadline"] == "2026-05-05"


def test_enriched_detekce():
    assert _enriched({"provenance": {"layer": 2}})
    assert _enriched({"citations": [{"x": 1}]})
    assert not _enriched({"provenance": {"layer": 1}})


# ---------------------------------------------------------------- derive_deadlines
def test_derive_opakujici_cislo_da_nejblizsi_budouci():
    iso, why = dd.derive({"datum": "každoročně 15.11.", "kontext": ""}, TODAY)
    assert iso == "2026-11-15" and why == "opakujici_cislo"


def test_derive_opakujici_slovne_prekloni_do_dalsiho_roku():
    """31. ledna už letos byl → nejbližší budoucí je až příští rok."""
    iso, _ = dd.derive({"datum": "31. ledna každého roku", "kontext": ""}, TODAY)
    assert iso == "2027-01-31"


def test_derive_iso_v_kontextu():
    iso, why = dd.derive({"datum": "2026-09-30", "kontext": "uzávěrka"}, TODAY)
    assert iso == "2026-09-30" and why == "iso_v_deadliny"


def test_derive_vagni_formulaci_nehada():
    """Klíčové proti fabrikaci: bez data se NESMÍ nic vymyslet."""
    for vague in ("bude upřesněno", "průběžně během roku", "", "duben"):
        iso, _ = dd.derive({"datum": vague, "kontext": vague}, TODAY)
        assert iso is None, f"z '{vague}' nesmí vzniknout datum, vzniklo {iso}"


def test_derive_neexistujici_datum_neprojde():
    iso, _ = dd.derive({"datum": "každoročně 31.2.", "kontext": ""}, TODAY)
    assert iso is None


def test_next_occurrence_dnesek_je_platny():
    assert dd.next_occurrence(31, 7, TODAY) == "2026-07-31"


# ---------------------------------------------------------------- mini-runner (bez pytestu)
if __name__ == "__main__":
    fails = []
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
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
