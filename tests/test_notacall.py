#!/usr/bin/env python3
"""Oznámení výsledků není výzva.

⚠ NAMĚŘENO 2026-09-01 v produktu, na katalogu 3 440 záznamů. Jedenáct z nich se
tvářilo jako výzva, o kterou lze žádat, a byla to oznámení, JAK ta výzva dopadla.
Nejvýmluvnější z nich:

    Výsledky stipendijního programu MSPP 2025 (NEWS, NE výzva)

Extrakce sama napsala do titulku, že to výzva není, a záznam přesto vyšel jako
`kind=grant`. Anotace bez brány není rozhodnutí, je to poznámka.

Žádná ze stávajících kontrol to chytit nemohla: záznamy mají platná data,
neprázdný titulek, unikátní id i reprodukovatelný otisk. Jsou VĚCNĚ špatně, ne
formálně. Po zavedení pravidla jich v exportu bylo 24.

⚠ TESTUJÍ SE OBĚ STRANY PRAVIDLA. Pravidlo, které nic nepropustí, je stejně
špatné jako pravidlo, které nic nechytí — a tohle běží nad titulky výzev,
u kterých se o výsledcích minulých kol běžně mluví.

Spuštění:  python tests/test_notacall.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from fix_dataset import NOT_A_CALL  # noqa: E402


CHYTIT = [
    "Výsledky grantových řízení | Nadace AGROFERT",
    "Výsledky výběrových dotačních řízení na rok 2026 — 1. kolo hodnocení",
    "Vyhlášení výsledků VES 2008 – 2011 na základě rozhodnutí ministra zdravotnictví",
    "Vyhlášení výsledku jednostupňové veřejné soutěže o účelovou podporu",
    "Výsledky stipendijního programu MSPP 2025 (NEWS, NE výzva)",
    "  výsledky grantového řízení 2026",  # odsazení a malá písmena nesmí pravidlo obejít
    # Nábor do hodnotící komise — JE to výzva, ale pro někoho jiného než pro
    # organizaci, která shání peníze.
    "Výzva pro hodnotitelky a hodnotitele programu EEA Civil Society Fund",
    "Nábor hodnotitelů projektových žádostí",
    # Rozcestník — stránka, ze které se teprve na programy odbočuje.
    "Nabídka programů - Nadace Via",
    "Přehled dotačních programů",
    "Seznam výzev | Ministerstvo",
]

PROPUSTIT = [
    # ⚠ TOHLE JE TA DŮLEŽITĚJŠÍ POLOVINA. Řádná výzva o výsledcích běžně mluví;
    # kdyby se hledalo kdekoli v titulku, přišel by katalog o platné výzvy.
    "Program podpory kultury 2027 (výsledky loňského ročníku zveřejněny)",
    "Výzva č. 98 — Systémy pro posuzování znečištění ovzduší",
    "Podpora výzkumu a vývoje, včetně zveřejnění výsledků",
    "Grantové řízení Nadace OKD 2027",
    "Informace o podmínkách podání žádosti",
    "Výsledkem projektu má být studie proveditelnosti",
    # ⚠ HODNOTITEL V TITULKU JEŠTĚ NEDĚLÁ NÁBOR. Tohle je dotace, která
    # vzdělávání hodnotitelů FINANCUJE — rozdíl nese předložka, ne slovo.
    "Výzva č. 12 — podpora vzdělávání hodnotitelů kvality",
    "Program na rozvoj hodnotitelských kapacit v kultuře",
    # ⚠ ROZCESTNÍK MUSÍ TITULEK VYČERPAT. Za tímhle pokračuje předmět podpory,
    # takže je to konkrétní program, ne stránka s odkazy.
    "Nabídka dotací na výměnu kotlů 2027",
    "Přehled programů podpory bydlení pro obce",
    # Falešné poplachy zamítnutého pravidla „titulek je jméno organizace“ —
    # všechny čtyři jsou řádné programy (naměřeno na celém katalogu).
    "Nadace ČEZ – Program Stromy",
    "Nadace OKD obcím",
    "Nadační fond Karlovarského kraje",
    "Nadační fond Hyundai (Nadace OSF)",
]


def test_oznameni_vysledku_chytne():
    for title in CHYTIT:
        assert NOT_A_CALL.search(title), f"mělo se chytit: {title!r}"


def test_radna_vyzva_projde():
    for title in PROPUSTIT:
        assert not NOT_A_CALL.search(title), f"nemělo se chytit: {title!r}"


def test_prazdny_titulek_nepadne():
    """Titulek může chybět; o prázdné tituly se stará jiná kontrola."""
    assert not NOT_A_CALL.search("")


def test_brana_ma_stejne_pravidlo():
    """Výraz stojí ve DVOU souborech a musí být doslova stejný.

    ⚠ JE TO ZÁMĚRNÁ DUPLICITA, ne opomenutí. `validate_release.py` je brána,
    která běží i v CI bez gitignored `data/`, a nesmí spadnout jen proto, že se
    nepodařilo naimportovat skript, který právě kontroluje. Cenou za to je, že
    se ty dvě kopie můžou rozejít — a rozejdou se tiše: brána by propouštěla,
    čistička mazala, nebo naopak. Proto tenhle test.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gate = open(os.path.join(root, "scripts", "validate_release.py"), encoding="utf-8").read()
    for fragment in (
        r"^\s*výsledky\b",
        r"^\s*(vyhlášení|oznámení)\s+výsledk\w*",
        r"^\s*informace\s+o\s+(ne)?přijetí",
        r"\(\s*news\s*,\s*ne\s+výzva\s*\)",
        r"^\s*výzva\s+pro\s+[^\n]{0,30}hodnotitel",
        r"^\s*(nábor|hledáme)\s+[^\n]{0,20}hodnotitel",
        r"(programů|dotací|výzev)\s*($|[-–—|(])",
    ):
        assert fragment in gate, f"brána nezná část pravidla: {fragment!r}"
        assert NOT_A_CALL.pattern.find(fragment) >= 0, f"čistička nezná část pravidla: {fragment!r}"


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
