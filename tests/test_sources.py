#!/usr/bin/env python3
"""Nové zdroje z 10. 11. 2026: Jihomoravský kraj (e‑dotace), dotaceeu.cz, Vismo.

Parsery jsou deterministické, takže se testují na malých vzorcích ve tvaru,
jaký dává web: co se přečíst má, i co se přečíst nesmí (mobilní kopie
tabulky, výzva jen pro státní úřad, „příspěvkové organizace“ místo dotací).

Spuštění:  python tests/test_sources.py
"""
import importlib.util
import io
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_extractor(mod, recs):
    """Spustí extraktor nad dočasnými složkami; vrátí výstupy podle jména souboru."""
    with tempfile.TemporaryDirectory() as d:
        mod.IN, mod.OUT = os.path.join(d, "in"), os.path.join(d, "out")
        os.makedirs(mod.IN)
        for i, r in enumerate(recs):
            json.dump(r, io.open(os.path.join(mod.IN, f"grant_{i:02d}.json"), "w", encoding="utf-8"), ensure_ascii=False)
        assert mod.main() == 0
        return {f: json.load(io.open(os.path.join(mod.OUT, f), encoding="utf-8")) for f in sorted(os.listdir(mod.OUT))}


def row(label, value):
    return ["$", "div", None, {"className": "main-table-row merged", "children": [
        ["$", "div", None, {"className": "main-table-header", "children": [label, ":"]}],
        ["$", "div", None, {"children": value}]]}]


def test_jmk_rsc_na_radky_bez_mobilni_kopie():
    jmk = load("scripts/jmk_edotace.py", "jmk_edotace")
    rows = {"12": ["$", "div", None, {"className": "text-left", "children": [
        ["$", "h2", None, {"className": "section-title", "children": "Podpora kultury 2027"}],
        ["$", "div", None, {"className": "hidden md:block", "children": [row("Příjem žádostí", "02.11.2026 00:01 - 27.11.2026 23:00")]}],
        ["$", "div", None, {"className": "md:hidden", "children": [row("Příjem žádostí", "DUPLIKÁT")]}],
        ["$", "a", None, {"href": "/web/api/attachment/abc?name=Program.pdf", "children": "Program.pdf"}],
    ]}]}
    lines, links = jmk.text_of(rows)
    assert lines[0] == "Podpora kultury 2027"
    assert "Příjem žádostí: 02.11.2026 00:01 - 27.11.2026 23:00" in lines
    assert not any("DUPLIKÁT" in ln for ln in lines)
    assert links == ["/web/api/attachment/abc?name=Program.pdf"]


def test_jmk_program_lhuta_strop_a_zadatele():
    ex = load("scripts/extractors/jmk_edotace.py", "x_jmk")
    body = "\n".join([
        "OBCHŮDEK 2021+ v Jihomoravském kraji – V. výzva",
        "Objem finančních prostředků vyčleněných na program: 3800000 Kč",
        "Cíl/účel programu: Udržení venkovských prodejen.",
        "Příjem žádostí: 16.06.2026 00:01 - 30.06.2026 23:00",
        "Dotační titul: OBCHŮDEK 2021+",
        "Příjemce podpory: obec, podnikající právnická nebo fyzická osoba provozující prodejnu v obci",
        "Maximální výše podpory na jeden projekt/akci/činnost: 100000 Kč",
        "Minimální podíl spoluúčasti žadatele: 50 %",
    ])
    out = run_extractor(ex, [{"id": "https://e-dotace.jmk.cz/web/programDetail/1", "title": body.split("\n")[0], "body": body}])
    g = out["grant_00.json"]
    assert (g["open_from"], g["deadline"]) == ("2026-06-16", "2026-06-30")
    assert g["vyse_hlavni_czk"] == 100000 and g["spoluucast"] is True
    assert {"typ": "alokace", "hodnota": 3800000} in g["castky"]
    # Podnikající fyzická osoba je OSVČ, ne občan.
    assert "osvc_podnikatel" in g["typ_zadatele"] and "fyzicka_osoba" not in g["typ_zadatele"]
    assert g["region"][0]["kraj"] == "Jihomoravský kraj"


def test_dotaceeu_jen_statni_urad_se_nezapise():
    ex = load("scripts/extractors/dotaceeu.cz.py", "x_deu")
    statni = "\n".join(["19. výzva OP FVB", "Operační program:", "13 OP FVB", "Oprávnění žadatelé:",
                        "Ministerstvo vnitra - Policie ČR", "Ukončení příjmu žádostí:", "18. 11. 2026", "Stav výzvy:", "Plánovaná"])
    nno = "\n".join(["55. výzva OP AMIF", "Číslo výzvy:", "12_26_055", "Druh výzvy:", "Kolová", "Operační program:",
                     "12 Operační program Azylového, migračního a integračního fondu", "Oprávnění žadatelé:",
                     "právnická osoba - NNO, OSS a jejich příspěvkové organizace, VÚSC", "Zahájení příjmu žádostí:",
                     "31. 10. 2026", "Ukončení příjmu žádostí:", "18. 12. 2026", "Stav výzvy:", "Otevřená"])
    out = run_extractor(ex, [
        {"id": "https://www.dotaceeu.cz/Jak-ziskat-dotaci/Vyzvy/Obdobi-2021-2027/13-x/19", "title": "19. výzva OP FVB", "body": statni},
        {"id": "https://www.dotaceeu.cz/Jak-ziskat-dotaci/Vyzvy/Obdobi-2021-2027/12-x/55", "title": "55. výzva OP AMIF", "body": nno},
    ])
    assert list(out) == ["grant_01.json"]
    g = out["grant_01.json"]
    assert (g["open_from"], g["deadline"]) == ("2026-10-31", "2026-12-18")
    assert {"neziskovka", "obec_verejny_subjekt", "prispevkova_organizace"} <= set(g["typ_zadatele"])
    assert g["rezim_prijmu"] == "kolova" and "migrace" in g["oblast"]


def test_vyrazeny_zdroj_neni_vyschly_ale_jiny_ano():
    import source_health as sh
    dried, _, _ = sh.compare({"jmk_edotace": 3}, {"kr-jihomoravsky.cz": 34, "msk.cz": 40})
    assert [s for s, _ in dried] == ["msk.cz"]


def test_vismo_nehleda_prispevkove_organizace():
    vismo = load("scripts/vismo.py", "vismo_t")
    assert vismo.NOT_DOTACE_RE.search("Příspěvkové organizace města")
    assert vismo.NOT_DOTACE_RE.search("/prispevkove%2Dorganizace%2Dmesta/ms-29976")
    assert not vismo.NOT_DOTACE_RE.search("Granty a dotace")
    assert vismo.NARROW_RE.search("Grantový systém města") and not vismo.NARROW_RE.search("Příspěvky")


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
