#!/usr/bin/env python3
"""Testy IDENTITY VÝZVY — klíče, na kterém stojí všechno, co produkt o výzvě ví.

`id` z `canon_key` není jen primární klíč. Je to vazba na uložené výzvy
zákazníka, na jeho pipeline, na poznámky a na historii změn. Když se identita
rozejde, projeví se to dvěma způsoby a ANI JEDEN NEVYPADÁ JAKO CHYBA:

  ROZPAD   Drobná změna názvu na webu poskytovatele vyrobí NOVÝ záznam. Původní
           přestane přicházet ve feedu, takže se v katalogu označí za stažený —
           a zákazníkovi zmizí ze seznamu výzva, o kterou se pořád může ucházet.

  SLITÍ    Dvě různé výzvy dostanou týž klíč. Druhá tiše přepíše první: v datech
           zbude jeden záznam, ve kterém je půlka údajů z jedné výzvy a půlka
           z druhé. Nic nespadne, jen to není pravda.

Pořadí, ve kterém `canon_key` identitu určuje, je proto seřazené od
NEJSPOLEHLIVĚJŠÍHO zdroje k nejméně spolehlivému:

  1. `uid`   — autoritativní identifikátor zdroje (dsw2 program_id apod.)
  2. doc id  — číslo dokumentu v adrese (vismo/otevřená města `/d-NNNNNN`)
  3. titulek — až když není nic lepšího

Spuštění:  python tests/test_identity.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from opportunities import canon_key  # noqa: E402


# ------------------------------------------------- 1. autoritativní id vyhrává
def test_uid_prebije_titulek():
    """⚠ TOHLE JE OBRANA PROTI ROZPADU. Zdroj si opraví překlep v názvu a výzva
    musí zůstat toutéž výzvou — jinak zákazníkovi zmizí z uložených."""
    a = canon_key("grant", "Podpora sportu 2026", "https://kraj.cz/a", uid="PS-01")
    b = canon_key("grant", "Podpora sportu v roce 2026", "https://kraj.cz/a", uid="PS-01")
    assert a == b


def test_uid_prebije_i_zmenenou_adresu():
    """Web se přestěhuje, program zůstává. Autoritativní id to přežije."""
    a = canon_key("grant", "Podpora sportu", "https://kraj.cz/stary", uid="PS-01")
    b = canon_key("grant", "Podpora sportu", "https://kraj.cz/novy", uid="PS-01")
    assert a == b


def test_ruzne_uid_se_neslijou():
    """⚠ A TOHLE JE OBRANA PROTI SLITÍ. Dva programy téhož názvu (jiný ročník,
    jiná oblast) musí zůstat dva."""
    a = canon_key("grant", "Podpora sportu", "https://kraj.cz/a", uid="PS-01")
    b = canon_key("grant", "Podpora sportu", "https://kraj.cz/a", uid="PS-02")
    assert a != b


# ------------------------------------------------------ 2. id dokumentu v URL
def test_doc_id_prebije_titulek():
    """Vismo a otevřená města nesou v adrese `/d-NNNNNN` — stabilní číslo
    dokumentu. Přejmenování programu na něj nesahá."""
    a = canon_key("grant", "Podpora sportu 2026", "https://kraj.cz/dotace/d-123456")
    b = canon_key("grant", "Podpora sportu 2027", "https://kraj.cz/dotace/d-123456")
    assert a == b


def test_ruzne_dokumenty_se_neslijou():
    a = canon_key("grant", "Podpora sportu", "https://kraj.cz/dotace/d-123456")
    b = canon_key("grant", "Podpora sportu", "https://kraj.cz/dotace/d-999999")
    assert a != b


# --------------------------------------------------------- 3. fallback titulek
def test_titulek_snese_interpunkci_a_mezery():
    """Bez autoritativního id rozhoduje titulek — ale NORMALIZOVANÝ. Čárka
    navíc, dvojitá mezera nebo vykřičník jsou úpravy sazby, ne jiná výzva."""
    a = canon_key("grant", "Podpora sportu, 2026", "https://kraj.cz/a")
    b = canon_key("grant", "Podpora  sportu 2026!", "https://kraj.cz/a")
    assert a == b


def test_titulek_snese_velikost_pismen():
    a = canon_key("grant", "PODPORA SPORTU", "https://kraj.cz/a")
    b = canon_key("grant", "Podpora sportu", "https://kraj.cz/a")
    assert a == b


def test_cislo_vyzvy_zustava_soucasti_identity():
    """⚠ „1. výzva" a „2. výzva" jsou DVĚ RŮZNÁ KOLA téhož programu.

    Normalizace zahazuje interpunkci, takže by se po ní lišily jen číslicí
    uvnitř slova — a kdyby ji některá budoucí úprava taky zahodila, slily by se
    obě kola v jedno. Číslo se proto vytahuje dopředu a je součástí klíče
    výslovně.
    """
    a = canon_key("grant", "1. výzva OPŽP", "https://kraj.cz/a")
    b = canon_key("grant", "2. výzva OPŽP", "https://kraj.cz/a")
    assert a != b
    assert a.endswith("1výzvaopžp") and "1|" in a


def test_titulek_se_neoreze():
    """⚠ ŽÁDNÝ STROP DÉLKY. Ořezaný titulek slévá výzvy, které se liší až
    v páté desítce znaků — a přesně tak vypadají názvy dotačních programů."""
    base = "Program na podporu rozvoje a obnovy sportovní infrastruktury v obcích do 3000 obyvatel"
    a = canon_key("grant", base + ", oblast A", "https://kraj.cz/a")
    b = canon_key("grant", base + ", oblast B", "https://kraj.cz/a")
    assert a != b


# ------------------------------------------------------------ 4. dedup po zdroji
def test_stejny_nazev_u_dvou_zdroju_se_neslije():
    """⚠ DEDUP JE V RÁMCI ZDROJE, NE NAPŘÍČ. „Podpora sportu" vyhlašuje kdekdo;
    kdyby klíč host neobsahoval, slily by se programy dvou různých krajů
    v jeden — a zákazník by u své výzvy viděl podmínky cizího kraje.
    """
    a = canon_key("grant", "Podpora sportu", "https://kraj-a.cz/x")
    b = canon_key("grant", "Podpora sportu", "https://kraj-b.cz/x")
    assert a != b


def test_druh_zaznamu_je_soucasti_klice():
    """Grant a profil nadace se stejným jménem nejsou totéž."""
    a = canon_key("grant", "Nadace ABC", "https://nadace.cz/x")
    b = canon_key("foundation_mission", "Nadace ABC", "https://nadace.cz/x")
    assert a != b


# ------------------------------------------------------------- 5. determinismus
def test_klic_je_deterministicky():
    """Dvě volání nad týmž vstupem musí dát totéž. Zní samozřejmě — ale kdyby se
    do klíče kdykoli dostal čas, náhoda nebo pořadí zpracování, rozpadl by se
    celý katalog při každém běhu a projevilo by se to jako 3400 nových výzev.
    """
    args = ("grant", "Podpora sportu 2026", "https://kraj.cz/dotace/d-123456")
    assert canon_key(*args) == canon_key(*args)


# ---------------------------------------------------------------- mini-runner
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
