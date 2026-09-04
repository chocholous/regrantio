#!/usr/bin/env python3
"""Testy KRITICKÉ logiky pipeline — to, co při tichém rozbití zkazí data v produktu.

Proč zrovna tyhle tři oblasti:
  • compute_status  — jediné místo, kde vzniká open/closed. Chyba tady = špatné statusy
                      u 3400 grantů a nikdo si toho nemusí všimnout (data „vypadají OK").
  • upsert       — rozhoduje, co se při refreshi přepíše. Chyba = ztráta obohacení
                      z vrstvy 2 nebo naopak neaktualizovaná data.
  • derive_deadlines— odvozuje termín z textu. Chyba = FABRIKOVANÉ datum v produktu.

Spuštění:  python -m pytest tests/ -q      (nebo: python tests/test_core.py)
Bez pytestu funguje i přímé spuštění — má vlastní mini-runner.
"""
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from opportunities import compute_status          # noqa: E402
from upsert import merge, _enriched, upsert, stamp, _without_stamp  # noqa: E402
import derive_deadlines as dd                     # noqa: E402
import czech                                     # noqa: E402

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


# ---------------------------------------------------------------- upsert
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


def test_razitko_neudela_ze_vsech_zaznamu_zmenene(tmpdir=None):
    """⚠ TOHLE JE CELÝ DŮVOD, PROČ `_without_stamp` EXISTUJE.

    `fetched_at` se zapisuje i záznamu, který se nezměnil. Kdyby vstupovalo do
    porovnání, hlásil by druhý běh nad TÝMIŽ daty „updated" u všech záznamů —
    a statistika, která je vždycky stejná, se přestane číst. Test tedy pouští
    upsert dvakrát nad identickým vstupem a trvá na tom, že podruhé je
    všechno `unchanged`.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "k.jsonl")
        recs = [_raw(id="a"), _raw(id="b")]
        first = upsert(p, [dict(r) for r in recs], when="2026-09-01")
        assert (first["new"], first["updated"], first["unchanged"]) == (2, 0, 0)

        # druhý běh, JINÝ den, ale stejná data
        second = upsert(p, [dict(r) for r in recs], when="2026-09-03")
        assert (second["new"], second["updated"]) == (0, 0), second
        assert second["unchanged"] == 2, second

        # razítko se ale přesto posunulo — „viděli jsme to dnes"
        import json as _j
        got = {r["id"]: r["provenance"]["fetched_at"]
               for r in map(_j.loads, open(p, encoding="utf-8"))}
        assert got == {"a": "2026-09-03", "b": "2026-09-03"}, got


def test_razitko_nezastini_skutecnou_zmenu():
    """Opačný směr: když se fakt změní, `updated` to pořád musí poznat."""
    import json as _j, tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "k.jsonl")
        upsert(p, [_raw(id="a", deadline="2026-01-01")], when="2026-09-01")
        out = upsert(p, [_raw(id="a", deadline="2026-12-31")], when="2026-09-03")
        assert out["updated"] == 1 and out["unchanged"] == 0, out
        rec = _j.loads(open(p, encoding="utf-8").read().strip())
        assert rec["deadline"] == "2026-12-31"


def test_razitko_nesahne_na_ostatni_provenance():
    """Razítko přidává klíč, nepřepisuje původ (harvester, dokumenty, vrstva)."""
    r = stamp({"provenance": {"layer": 2, "harvester": "extract_wf"}}, "2026-09-03")
    assert r["provenance"] == {"layer": 2, "harvester": "extract_wf",
                               "fetched_at": "2026-09-03"}
    assert _without_stamp(r)["provenance"] == {"layer": 2, "harvester": "extract_wf"}


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


# ---------------------------------------------------------------- czech.py (sdílené parsování)
def test_czech_datum_ciselne():
    assert czech.cz_date_to_iso("Termín: 15. 11. 2026 do 12:00") == "2026-11-15"
    assert czech.cz_date_to_iso("15.11.2026") == "2026-11-15"


def test_czech_datum_slovni():
    assert czech.cz_date_to_iso("do 31. ledna 2027") == "2027-01-31"
    assert czech.cz_date_to_iso("do 31. unora 2027") is None      # 31. 2. neexistuje


def test_czech_neexistujici_datum_je_none():
    """Klíčové: 24 starých parserů tohle NEVALIDOVALO a umělo vyrobit 2026-13-45."""
    for bad in ("31. 2. 2026", "45. 1. 2026", "1. 13. 2026", "30. 2. 2026"):
        assert czech.cz_date_to_iso(bad) is None, f"{bad} nesmí projít"


def test_czech_bez_data_vraci_none():
    for s in ("bude upřesněno", "", None, "duben 2026"):
        assert czech.cz_date_to_iso(s) is None


def test_czech_vsechna_data_serazena():
    ds = czech.cz_dates_all("od 1. 3. 2026 do 30. 6. 2026, náhradní 31. ledna 2027")
    assert ds == ["2026-03-01", "2026-06-30", "2027-01-31"]


def test_czech_strip_tags():
    assert czech.strip_tags("<p>první</p><p>druhá</p>").splitlines() == ["první", "druhá"]
    assert "alert" not in czech.strip_tags("<script>alert(1)</script>text")
    assert czech.strip_tags("a&nbsp;&amp;&nbsp;b") == "a & b"


def test_czech_sentence_at():
    t = "Úvodní věta. Lhůta pro podání žádosti je do 31. 12. 2026 včetně."
    s = czech.sentence_at(t, t.find("31. 12."))
    assert "Lhůta pro podání" in s and "Úvodní věta" not in s


# ---------------------------------------------------- odkaz vede na výzvu, ne na rozcestník
#
# ⚠ 148 ZÁZNAMŮ (4,3 % KATALOGU) MÍŘILO NA ÚVODNÍ STRÁNKU PORTÁLU.
# Produkt u každé výzvy slibuje „odkaz na originál". Odkaz na
# `https://dotace.khk.cz/` ten slib formálně plní a věcně ne: žadatel skončí
# na rozcestníku se stovkou programů a hledá znovu. Platná URL, otevře se,
# čtvrt roku si toho nikdo nevšiml.
#
# Hluboký odkaz `/grantProgram/:memo` je v SPA bundlu a `memo` je kód, který
# už v titulku každého záznamu je. Testuje se OBOJÍ směr: že se kód použije,
# když je, a že se odkaz nevyrobí, když není — vymyšlený kód vykreslí prázdný
# detail, což je horší než rozcestník.


def test_dotis_odkaz_miri_na_program():
    import ingest_dotis
    assert ingest_dotis.dotis_url("dotace.khk.cz", "26POVU1") == "https://dotace.khk.cz/grantProgram/26POVU1"


def test_dotis_bez_kodu_zustane_na_rozcestniku():
    import ingest_dotis
    assert ingest_dotis.dotis_url("dotace.khk.cz", "") == "https://dotace.khk.cz/"
    assert ingest_dotis.dotis_url("dotace.khk.cz", None) == "https://dotace.khk.cz/"


def test_katalog_nema_dotis_zaznam_na_rozcestniku():
    """Vlastnost výsledku, ne skriptu: kdyby data přišla jinou cestou, chytne je to stejně."""
    import json as _json
    path = os.path.join(ROOT, "data", "opportunities.jsonl")
    if not os.path.exists(path):
        return
    bad = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = _json.loads(line)
            if (r.get("provenance") or {}).get("platform") != "dotis":
                continue
            src = r.get("source") or ""
            if (r.get("source_url") or "").rstrip("/") == f"https://{src}":
                bad.append(r.get("title"))
    assert not bad, f"{len(bad)} DOTIS záznamů míří na rozcestník (např. {bad[0]!r})"


# ---------------------------------------------------------------- mini-runner (bez pytestu)

# ---------------------------------------------------------------- registr obnovy
def test_registr_neobsahuje_extraktor_s_daty_natvrdo():
    """⚠ NEJHORŠÍ MOŽNÝ ZDROJ NENÍ TEN, KTERÝ SPADNE. Je to ten, který doběhne,
    nic nezmění a tváří se, že obnovil.

    Souborů `data/_<slug>_extract.py` je 42, ale jen 15 z nich vstup opravdu
    ČTE. Zbytek jsou přepisy jedné extrakce z 2026-06/07 do pythonních
    literálů — spustí se, vytisknou „wrote N grants" a skončí nulou.

    Zaregistrovat takový soubor do obnovy znamená vyrobit běh, který:
      1. opravdu stáhne stránku,
      2. přepíše přes ni červnová data,
      3. ohlásí ✓ a orazítkuje záznamy jako ověřené dnes.

    Naměřeno 2026-09-03: přesně tohle se stalo 350 záznamům, než se to zachytilo.
    Test hlídá, že se to nevrátí — a je to strukturální kontrola, ne seznam:
    ptá se KAŽDÉHO registrovaného extraktoru, jestli čte vstup.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "scripts"))
    import refresh_run

    # ⚠ POUŽÍVÁ SE DETEKTOR Z `refresh_run`, NE VLASTNÍ KOPIE VZORU.
    # První verze tohohle testu si nesla vlastní regulární výraz — a ten byl
    # navíc ŠPATNĚ: hledal jen čtení ze složky `_in/`, takže šest extraktorů,
    # které čtou rovnou harvest, označil za přepisy. Dvě kopie pravidla znamenají,
    # že se jedna z nich mýlí a nikdo to nepozná.
    hriche = [s for s in refresh_run.EXTRACT_SOURCES if not refresh_run.cte_vstup(s)]
    assert not hriche, (
        "v registru obnovy jsou extraktory s daty natvrdo (nečtou vstup): "
        + ", ".join(hriche)
    )

    # Opačný směr: přepisem se nesmí zbytečně říkat parseru.
    zbytecne = [s for s in refresh_run.TRANSCRIBED if refresh_run.cte_vstup(s)]
    assert not zbytecne, (
        "vedeno jako přepis, ale vstup čte (patří do registru): " + ", ".join(zbytecne)
    )


def test_prepsane_zdroje_nejsou_v_registru():
    """Druhá strana téhož: seznam přepsaných a registr se nesmí protnout."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "scripts"))
    import refresh_run

    prekryv = set(refresh_run.EXTRACT_SOURCES) & set(refresh_run.TRANSCRIBED)
    assert not prekryv, f"zdroj je zároveň registrovaný i vedený jako přepsaný: {prekryv}"

    prekryv2 = set(refresh_run.SOURCES) & set(refresh_run.EXTRACT_SOURCES)
    assert not prekryv2, f"zdroj je ve dvou registrech naráz: {prekryv2}"


def test_registrovany_harvest_ma_svuj_skript():
    """Registr smí jmenovat jen skripty, které existují — jinak `--list` lže."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(root, "scripts"))
    import refresh_run

    chybi = []
    for slug, (harvest, _tier) in refresh_run.EXTRACT_SOURCES.items():
        if not os.path.exists(os.path.join(root, "scripts", harvest[0])):
            chybi.append(f"{slug} → {harvest[0]}")
        # `--seeds` ukazuje na soubor, který musí být V REPOZITÁŘI (.gitignore výjimka 3)
        if "--seeds" in harvest:
            seed = harvest[harvest.index("--seeds") + 1]
            if not os.path.exists(os.path.join(root, seed)):
                chybi.append(f"{slug} → chybí {seed}")
    assert not chybi, "registr jmenuje neexistující soubory: " + ", ".join(chybi)


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
