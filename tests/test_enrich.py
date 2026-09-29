#!/usr/bin/env python3
"""Testy ODVOZENÝCH POLÍ kontraktu 1.2 (`scripts/enrich.py`, `scripts/dedup.py`).

Co hlídají a proč:
  • scope        — Horizon je `eu_central`, obecní program `local`. Podle toho
                   produkt řadí; kdyby obec vyšla jako `national`, spolek by
                   dostal Horizon nad program svého města.
  • deadline_kind— `recurring` jen s dokladem (kolový režim, „každoročně",
                   rodina ročníků). Bez dokladu `unknown`. Hádání by z každého
                   obecního programu udělalo „vyhlašuje se každý rok".
  • program_key  — ročník a číslo kola do klíče nepatří, zdroj ano.
  • variant_of   — jen uzavřené ročníky; dva živé záznamy se neslučují nikdy.
  • provenance   — necitované pole není doložené; pole, které chybí, původ nemá.
  • otisk        — odvozeniny do `content_hash` nevstupují.

Spuštění:  python tests/test_enrich.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import dedup      # noqa: E402
import enrich     # noqa: E402
import export_api  # noqa: E402


def _grant(**over):
    base = {"id": "g1", "kind": "grant", "source": "mesto.cz", "source_url": "https://mesto.cz/1",
            "title": "Program podpory sportu 2026", "deadline": "2026-10-31", "open_from": "2026-09-01",
            "facets": {"typ_poskytovatele": "samosprava_obec",
                       "region": {"kraj": "Jihomoravský kraj", "obec": "Brno", "celostatni": False}},
            "provenance": {"layer": 2}, "extra": {}, "citations": []}
    base.update(over)
    return base


# ---------------------------------------------------------------- scope
def test_scope_obec_je_local():
    assert enrich.scope(_grant()) == "local"


def test_scope_evropska_komise_je_eu_central():
    assert enrich.scope(_grant(facets={"typ_poskytovatele": "evropska_komise", "region": {"celostatni": True}})) == "eu_central"


def test_scope_ministerstvo_celostatni_je_national():
    assert enrich.scope(_grant(facets={"typ_poskytovatele": "ministerstvo", "region": {"celostatni": True}})) == "national"


def test_scope_nadace_omezena_na_kraj_je_regional():
    assert enrich.scope(_grant(facets={"typ_poskytovatele": "nadace",
                                       "region": {"kraj": "Kraj Vysočina", "celostatni": False}})) == "regional"


def test_scope_bez_faset_je_national():
    assert enrich.scope({"facets": {}}) == "national"


# ---------------------------------------------------------------- deadline_kind
def test_iso_lhuta_je_fixed():
    assert enrich.deadline_kind(_grant()) == "fixed"


def test_prubezne_je_rolling():
    assert enrich.deadline_kind(_grant(deadline="průběžně")) == "rolling"


def test_bez_lhuty_bez_dokladu_je_unknown():
    assert enrich.deadline_kind(_grant(deadline=None)) == "unknown"


def test_kolovy_rezim_bez_lhuty_je_recurring():
    g = _grant(deadline=None)
    g["facets"]["rezim_prijmu"] = "kolova"
    assert enrich.deadline_kind(g) == "recurring"


def test_kazdorocne_v_kontextu_je_recurring():
    g = _grant(deadline=None, extra={"deadliny": [{"datum": "15. 11.", "kontext": "každoročně do 15. 11."}]})
    assert enrich.deadline_kind(g) == "recurring"
    assert enrich.deadline_note(g) == "každoročně do 15. 11."


def test_odvozena_lhuta_je_recurring():
    g = _grant(extra={"deadline_derived_rule": "nearest-future"})
    assert enrich.deadline_kind(g) == "recurring"


def test_poznamka_k_lhute_jen_bez_iso():
    assert enrich.deadline_note(_grant(extra={"deadliny": [{"datum": None, "kontext": "něco"}]})) is None


# ---------------------------------------------------------------- program_key
def test_rocnik_do_klice_nepatri():
    a = enrich.program_key(_grant(title="Program podpory sportu 2025"))
    b = enrich.program_key(_grant(title="Program podpory sportu 2026"))
    assert a == b


def test_cislo_kola_do_klice_nepatri():
    a = enrich.program_key(_grant(title="63. výzva – Energetické úspory"))
    b = enrich.program_key(_grant(title="64. výzva – Energetické úspory"))
    assert a == b


def test_zdroj_do_klice_patri():
    a = enrich.program_key(_grant(source="brno.cz", title="Individuální dotace"))
    b = enrich.program_key(_grant(source="olomouc.cz", title="Individuální dotace"))
    assert a != b


def test_prazdny_titul_nema_klic():
    assert enrich.program_key(_grant(title="")) is None


# ---------------------------------------------------------------- rodiny
def test_starsi_rocnik_je_varianta_noveho():
    old = _grant(id="a", title="Program podpory sportu 2025", deadline="2025-10-31")
    new = _grant(id="b", title="Program podpory sportu 2026", deadline="2026-10-31")
    fam = dedup.assign_families([old, new], today="2026-09-14")
    assert fam["a"]["variant_of"] == "b"
    assert fam["b"]["variant_of"] is None
    assert fam["b"]["family"]["years"] == [2025, 2026]
    assert fam["b"]["family"]["typical_deadline"] == "31. 10."
    assert fam["b"]["family"]["earlier"][0]["id"] == "a"


def test_dva_zive_zaznamy_se_neslucuji():
    a = _grant(id="a", title="63. výzva – Energetické úspory", deadline="2026-11-20")
    b = _grant(id="b", title="64. výzva – Energetické úspory", deadline="2026-11-20")
    fam = dedup.assign_families([a, b], today="2026-09-14")
    assert fam["a"]["variant_of"] is None and fam["b"]["variant_of"] is None
    assert fam["a"]["family"] or fam["b"]["family"]


def test_program_bez_lhuty_je_kanonicky_pred_uzavrenymi():
    cur = _grant(id="c", title="Podpora talentů", deadline=None)
    old = _grant(id="o", title="Podpora talentů 2021", deadline="2021-10-31")
    fam = dedup.assign_families([old, cur], today="2026-09-14")
    assert fam["o"]["variant_of"] == "c"


def test_zaznam_bez_rodiny_neni_ve_vysledku():
    assert dedup.assign_families([_grant()], today="2026-09-14") == {}


# ---------------------------------------------------------------- provenance
def test_puvod_z_vrstvy_a_citace():
    g = _grant(citations=[{"field": "deadline", "match": "exact"}, {"field": "amount", "match": "none"}],
               amount=100000)
    p = enrich.field_provenance(g)
    assert p["deadline"] == {"method": "model", "cited": True}
    assert p["amount"] == {"method": "model", "cited": False}


def test_chybejici_pole_nema_puvod():
    assert "amount" not in enrich.field_provenance(_grant(amount=None))


def test_parser_je_parsed():
    g = _grant(provenance={"layer": 1})
    assert enrich.field_provenance(g)["deadline"]["method"] == "parsed"


def test_odvozena_lhuta_je_derived():
    g = _grant(extra={"deadline_derived_rule": "x"})
    assert enrich.field_provenance(g)["deadline"]["method"] == "derived"


# ---------------------------------------------------------------- obsah z extra
def test_kontakt_bere_prvni_pouzitelny():
    g = _grant(extra={"kontakt": [{"osoba": None, "email": None, "telefon": None},
                                  {"osoba": "Jana N.", "email": " j@x.cz ", "telefon": None}]})
    assert enrich.contact(g) == {"osoba": "Jana N.", "email": "j@x.cz", "telefon": None}


def test_kontakt_bez_udaju_je_null():
    assert enrich.contact(_grant(extra={"kontakt": {"osoba": None, "email": None, "telefon": None}})) is None


def test_dokumenty_bez_popisu_se_vynechaji():
    g = _grant(extra={"dokumenty": [{"popis": "Pravidla", "role": "pravidla_podminky"}, {"popis": "", "role": "x"},
                                    {"popis": "Vzor", "role": "neznama"}]})
    docs = enrich.documents(g)
    assert [d["popis"] for d in docs] == ["Pravidla", "Vzor"]
    assert docs[1]["role"] == "ostatni"


# ---------------------------------------------------------------- early_close
def _step(veta, deadline="2026-09-30"):
    return _grant(deadline=deadline, open_from="2026-06-01", extra={"dalsi_datumy": [{"datum": None, "popis": veta}]})


def test_predcasny_konec_s_datem_je_closed_a_posune_uzaverku():
    g = _step("Příjem žádostí byl předčasně ukončen dne 11. 8. 2026 z důvodu převisu 300 % alokace.")
    ec = enrich.early_close(g)
    assert ec["state"] == "closed" and ec["on"] == "2026-08-11" and ec["planned"] == "2026-09-30"
    out = {**g, "early_close": ec, "status": "open", "field_provenance": {}}
    export_api.apply_early_close(out)
    assert out["deadline"] == "2026-08-11"
    assert out["status"] == "closed"
    assert out["field_provenance"]["deadline"] == {"method": "derived", "cited": True}


def test_slovosled_step():
    veta = "Z důvodu naplnění finančního objemu podaných žádostí ve výši 300 % alokace výzvy byl dne 11.8.2026 v 0:01 ukončen příjem žádostí o podporu."
    ec = enrich.early_close(_step(veta))
    assert ec["state"] == "closed" and ec["on"] == "2026-08-11"


def test_pozastaveni_kvuli_alokaci_je_konec():
    veta = "Příjem žádostí byl k 15.9. 2025 z důvodu zarezervování celé programové alokace pozastaven."
    g = _step(veta, deadline=None)
    g["open_from"] = None
    ec = enrich.early_close(g)
    assert ec["state"] == "closed" and ec["on"] == "2025-09-15"


def test_konec_pro_cast_regionu_neni_konec_vyzvy():
    veta = ("Méně rozvinuté regiony: Z důvodu naplnění finančního objemu podaných žádostí ve výši 300 % "
            "alokace výzvy byl dne 1.8.2026 v 0:01 ukončen příjem žádostí o podporu.")
    ec = enrich.early_close(_step(veta, deadline="2026-10-15"))
    assert ec["state"] == "may" and ec["on"] is None


def test_datum_slovem():
    ec = enrich.early_close(_step("Příjem žádostí byl ukončen dne 11. srpna 2026 z důvodu vyčerpání alokace."))
    assert ec["on"] == "2026-08-11"


def test_budouci_konec_je_obycejna_uzaverka():
    assert enrich.early_close(_step("Příjem žádostí bude ukončen 30. 9. 2026 ve 14:00.")) is None


def test_konec_v_den_uzaverky_neni_predcasny():
    assert enrich.early_close(_step("Příjem žádostí byl ukončen 30. 9. 2026.")) is None


def test_docasne_pozastaveny_online_prijem_neni_konec():
    assert enrich.early_close(_step("Žádost lze podat poštou (příjem žádostí je dočasně pozastaven pro online podání).")) is None


def test_konec_u_davno_prosle_vyzvy_je_historie():
    g = _step("Příjem žádostí ukončen dne 30. 4. 2017", deadline="2020-02-04")
    g["provenance"] = {"fetched_at": "2026-09-23T04:00:00+00:00"}
    assert enrich.early_close(g) is None


def test_konec_pred_zacatkem_prijmu_je_jine_kolo():
    g = _step("Příjem žádostí byl ukončen dne 30. 4. 2025.", deadline="2026-12-31")
    g["open_from"] = "2026-01-01"
    assert enrich.early_close(g) is None


def test_veta_bez_data_uzaverku_nehybe_ani_s_razitkem():
    g = _step("Z důvodu vyčerpání alokace byl příjem žádostí ukončen.")
    g["provenance"] = {"fetched_at": "2026-09-01T04:00:00+00:00"}
    ec = enrich.early_close(g)
    assert ec == {"state": "closed", "on": None, "note": ec["note"], "planned": None}
    out = {**g, "early_close": ec}
    export_api.apply_early_close(out)
    assert out["deadline"] == "2026-09-30"


def test_bez_data_a_bez_razitka_se_uzaverka_nehybe():
    ec = enrich.early_close(_step("Příjem žádostí ukončen z důvodu vyčerpání alokace.", deadline=None))
    assert ec["state"] == "closed" and ec["on"] is None
    out = {**_step("x", deadline=None), "early_close": ec}
    export_api.apply_early_close(out)
    assert out["deadline"] is None


def test_do_vycerpani_alokace_je_may():
    ec = enrich.early_close(_step("Příjem od 1. 6. 2026 do 31. 10. 2026 nebo do vyčerpání alokace."))
    assert ec["state"] == "may" and ec["on"] is None and "vyčerpání alokace" in ec["note"]


def test_bez_zminky_nic():
    assert enrich.early_close(_grant()) is None


# ---------------------------------------------------------------- otisk
def test_odvozeniny_nejsou_v_otisku():
    for f in ("scope", "deadline_kind", "program_key", "variant_of", "family", "field_provenance", "deadline_note",
              "early_close"):
        assert f not in export_api.HASH_FIELDS, f


def test_obsah_ze_zdroje_v_otisku_je():
    for f in ("call_number", "contact", "documents"):
        assert f in export_api.HASH_FIELDS, f


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ✓ {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ✗ {fn.__name__}: {e!r}")
    print(f"{len(fns) - failed}/{len(fns)} testů prošlo")
    sys.exit(1 if failed else 0)
