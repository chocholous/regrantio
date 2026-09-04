#!/usr/bin/env python3
"""Mapování katalogu na řádek databáze produktu.

⚠ TENHLE KÓD SE PŘESTĚHOVAL Z JINÉHO REPOZITÁŘE A JAZYKA. Do 2026-09-04 žil
v `the-machine-app/src/lib/catalog/row.ts` (TypeScript) a pouštěl ho
`scripts/ingest-catalog.mjs`. Přenos byl ověřen tak, že obě implementace
zpracovaly TÝŽ export (3 525 záznamů) a výsledné řádky se porovnaly pole po
poli: **3 525 z 3 525 shodných**.

Ta shoda ale byla jednorázová. Tenhle soubor ji drží — hlídá právě ta místa,
kde se Python a JavaScript rozcházejí a kde se to při přenosu opravdu stalo.

Spuštění:  python tests/test_publish_db.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import publish_db as P  # noqa: E402


def _g(**kw):
    base = {"id": "x", "kind": "grant", "source": "test.cz",
            "source_url": "https://test.cz/vyzva"}
    base.update(kw)
    return base


# ---------------------------------------------------------------- identita
def test_bez_identity_zaznam_neprojde():
    """Zahazuje se JEN chybějící identita — nic jiného."""
    for chybi in ("id", "source", "source_url"):
        g = _g()
        del g[chybi]
        row, why = P.to_row(g)
        assert row is None, f"bez `{chybi}` měl záznam vypadnout"
        assert chybi in why


def test_neznamy_kind_neprojde():
    row, why = P.to_row(_g(kind="news"))
    assert row is None and "news" in why


def test_vadna_hodnota_zaznam_NEZAHODI():
    """⚠ Vyhodit celou výzvu kvůli jedné částce by znamenalo schovat uživateli
    podporu, o kterou si může říct. Vadná hodnota se zahodí sama."""
    row, _ = P.to_row(_g(amount=-5, deadline="nesmysl", title="   "))
    assert row is not None
    assert row["amount"] is None          # záporná částka pryč
    assert row["deadline"] is None        # nedatum pryč ze sloupce `date`…
    assert row["deadline_raw"] == "nesmysl"   # …ale syrově zůstane
    assert row["title"] is None           # samé mezery = chybí


# ---------------------------------------------------------------- částka
def test_bool_neni_castka():
    """⚠ `bool` je v Pythonu podtyp `int`. Bez explicitní kontroly by `True`
    prošlo jako částka 1 — v JS by neprošlo, protože `typeof true !== 'number'`."""
    assert P._money(True) is None
    assert P._money(False) is None
    assert P._money(0) == 0
    assert P._money(1_000_000) == 1_000_000


def test_nekonecno_a_zaporne_pryc():
    for v in (float("inf"), float("-inf"), float("nan"), -1, "1000"):
        assert P._money(v) is None, v


# ---------------------------------------------------------------- text hledání
def test_normalizace_sundá_diakritiku():
    """Aplikace normalizuje DOTAZ toutéž funkcí; kdyby se rozešly, projeví se to
    jako „na vývoji to najde, v produkci ne"."""
    assert P.normalize_text("Školy A Obce") == "skoly a obce"
    assert P.normalize_text("PŘÍSPĚVEK") == "prispevek"
    assert P.normalize_text("Žížala Ďábel Ňuňu") == "zizala dabel nunu"


def test_pole_se_spoji_carkou_jako_v_javascriptu():
    """⚠ TOHLE SE PŘI PŘENOSU OPRAVDU ROZBILO.

    `eligible_applicants` je u 173 z 3 525 záznamů POLE. Původní kód se opíral
    o to, že JS pole tiše převede na text — a dělá to ČÁRKOU (`String(["a","b"])`
    je `"a,b"`), ne mezerou. Python na tomtéž spadl `TypeError`em.
    """
    assert P._as_js_string(["a", "b"]) == "a,b"
    assert P._as_js_string([]) == ""
    assert P._as_js_string(None) == ""
    assert P._as_js_string("text") == "text"
    hay = P.search_haystack(_g(title="Výzva", eligible_applicants=["Obce", "Spolky"]))
    assert hay == "vyzva obce,spolky test.cz"


def test_prazdna_pole_se_do_hledani_nepocitaji():
    """`filter(Boolean)` v JS zahodí null i prázdný řetězec."""
    assert P.search_haystack(_g(title=None, focus_area="")) == "test.cz"


# ---------------------------------------------------------------- datum
def test_iso_date_bere_jen_platny_tvar():
    assert P.iso_date("2026-09-04") == "2026-09-04"
    assert P.iso_date("2026-09-04T10:00:00Z") == "2026-09-04"
    assert P.iso_date("průběžně") is None
    assert P.iso_date(None) is None
    assert P.iso_date("04.09.2026") is None


def test_prubezne_je_rolling():
    row, _ = P.to_row(_g(deadline="Průběžně"))
    assert row["deadline_rolling"] is True and row["deadline"] is None
    row, _ = P.to_row(_g(deadline="2026-09-04"))
    assert row["deadline_rolling"] is False


# ---------------------------------------------------------------- změny
def test_bez_castky_NENI_zmena_castky():
    """⚠ TATO PAST STÁLA 155 PRÁZDNÝCH ŘÁDKŮ V OSTRÉ DATABÁZI.

    V JS verzi se čísla porovnávala přes `Number(x ?? NaN)`, a `NaN !== NaN`,
    takže se každá výzva BEZ ČÁSTKY tvářila, že se jí částka právě změnila —
    a částku má jen 22 % katalogu. Python má tutéž past ve `float('nan')`.
    """
    before = {"deadline": "2026-01-01", "amount": None}
    after = {"deadline": "2026-01-01", "amount": None}
    assert P.change_worth_recording(before, after) is False


def test_posun_terminu_i_castky_je_zmena():
    b = {"deadline": "2026-01-01", "amount": 100}
    assert P.change_worth_recording(b, {"deadline": "2026-02-01", "amount": 100})
    assert P.change_worth_recording(b, {"deadline": "2026-01-01", "amount": 200})
    assert not P.change_worth_recording(b, {"deadline": "2026-01-01", "amount": 100})


def test_novy_zaznam_je_vzdycky_udalost():
    assert P.change_worth_recording(None, {"deadline": None, "amount": None})


def test_castka_jako_text_z_databaze_se_porovna_cislem():
    """PostgREST vrací `numeric` jako řetězec — „100" a 100 je totéž číslo."""
    assert not P.change_worth_recording({"deadline": None, "amount": "100"},
                                        {"deadline": None, "amount": 100})


# ---------------------------------------------------------------- otisk
def test_chybejici_otisk_znamena_zmeneno():
    """Přepsat shodná data je levné, minout skutečnou změnu ne."""
    assert P.has_changed({"content_hash": None}, "abc")
    assert P.has_changed({"content_hash": "abc"}, None)
    assert P.has_changed({"content_hash": "abc"}, "xyz")
    assert not P.has_changed({"content_hash": "abc"}, "abc")


# ---------------------------------------------------------------- fasety
def test_fasety_bez_duplicit_a_prazdnych():
    row, _ = P.to_row(_g(facets={"oblast": ["kultura", "kultura", "", None, "sport"]}))
    assert row["oblast"] == ["kultura", "sport"]


def test_region_se_rozpadne_do_sloupcu():
    row, _ = P.to_row(_g(facets={"region": {"kraj": "Jihomoravský", "obec": None,
                                            "celostatni": False}}))
    assert row["kraj"] == "Jihomoravský"
    assert row["obec"] is None
    assert row["celostatni"] is False


def test_chybejici_fasety_nejsou_chyba():
    row, _ = P.to_row(_g())
    assert row["oblast"] == [] and row["kraj"] is None and row["celostatni"] is None


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    fails = []
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    for name, fn in tests:
        try:
            fn()
            print(f"  ok   {name}")
        except AssertionError as e:
            fails.append(name); print(f"  FAIL {name}: {e}")
        except Exception as e:  # noqa: BLE001
            fails.append(name); print(f"  ERR  {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - len(fails)}/{len(tests)} prošlo")
    sys.exit(1 if fails else 0)
