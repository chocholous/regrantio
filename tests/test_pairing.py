#!/usr/bin/env python3
"""Výstup modelu patří k výzvě podle adresy, ne podle pořadí.

⚠ NAMĚŘENO 2026-11-08. Vstupy vrstvy 2 (`data/<zdroj>_in/grant_NN.json`) se
při každé obnově číslují znovu podle pořadí na webu. Výstupy modelu zůstávaly
pod starým číslem a `ingest_rich` je spojil s tím vstupem, který dnes nese
totéž číslo. Když zdroj přidal výzvu na začátek seznamu, každá další výzva
dostala název, lhůtu a podmínky své sousedky: u SFŽP 12 záznamů, u MPSV 10,
u SFAV 3. Žádná kontrola to nechytila, data byla formálně platná.

Testy hlídají tři místa:
  · `ingest_rich` cizí výstup (jiné `_source_id`) do katalogu nepustí;
  · rozcestník (`_skip`) záznam se svou adresou z katalogu vyřadí;
  · `is_done` nepovažuje cizí výstup za hotový, takže se vstup přečte znovu.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from extract_api import is_done  # noqa: E402
from pair_model_outputs import code  # noqa: E402


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def _grant(title, sid=None, **kw):
    g = {"title": title, "deadline": "2027-01-31", "open_from": None, "castky": [], "region": []}
    g.update(kw)
    if sid:
        g["_source_id"] = sid
    return g


def _ingest(tmp, existing):
    ex = os.path.join(tmp, "existing.jsonl")
    with open(ex, "w", encoding="utf-8") as f:
        for r in existing:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    out = os.path.join(tmp, "out.jsonl")
    p = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "ingest_rich.py"),
         "--out-dir", os.path.join(tmp, "out"), "--src", os.path.join(tmp, "in"),
         "--existing", ex, "--out", out, "--today", "2026-11-08",
         "--manifest", os.path.join(tmp, "none.jsonl"), "--provider-types", os.path.join(tmp, "none.json")],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr[-600:]
    marker = json.loads([l for l in p.stdout.splitlines() if "INGEST_RICH" in l][-1])
    recs = {r["id"]: r for r in map(json.loads, open(out, encoding="utf-8"))}
    return marker, recs


def test_cizi_vystup_se_nespoji():
    """Výstup výzvy B leží pod číslem, které dnes nese výzva A → A ho nedostane."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(f"{tmp}/in/grant_00.json", {"id": "https://x.cz/a", "web": "x.cz", "title": "A", "body": ""})
        _write(f"{tmp}/out/grant_00.json", _grant("Výzva B", sid="https://x.cz/b"))
        marker, recs = _ingest(tmp, [{"id": "https://x.cz/a", "title": "Výzva A", "kind": "grant"}])
        assert marker["foreign"] == 1
        assert recs["https://x.cz/a"]["title"] == "Výzva A"


def test_vlastni_vystup_se_spoji():
    with tempfile.TemporaryDirectory() as tmp:
        _write(f"{tmp}/in/grant_00.json", {"id": "https://x.cz/a", "web": "x.cz", "title": "A", "body": ""})
        _write(f"{tmp}/out/grant_00.json", _grant("Výzva A 2027", sid="https://x.cz/a"))
        marker, recs = _ingest(tmp, [])
        assert marker["foreign"] == 0 and marker["rich"] == 1
        assert recs["https://x.cz/a"]["title"] == "Výzva A 2027"
        assert "_source_id" not in recs["https://x.cz/a"].get("extra", {})


def test_rozcestnik_vyradi_zaznam_s_cizimi_daty():
    """Na adrese rozcestníku ležel záznam s daty sousední výzvy → ven, ostatní zůstanou."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(f"{tmp}/in/grant_00.json", {"id": "https://x.cz/vyzvy", "web": "x.cz", "title": "Výzvy", "body": ""})
        _write(f"{tmp}/out/grant_00.json", {"_source_id": "https://x.cz/vyzvy", "_skip": "seznam odkazů"})
        marker, recs = _ingest(tmp, [
            {"id": "https://x.cz/vyzvy", "title": "Výzva Rodina 2026", "kind": "grant"},
            {"id": "https://x.cz/jina", "title": "Jiná výzva", "kind": "grant"},
        ])
        assert marker["skipped"] == 1 and marker["dropped"] == 1
        assert "https://x.cz/vyzvy" not in recs
        assert "https://x.cz/jina" in recs


def test_grant_vyhraje_nad_popisem_nadace_se_stejnou_adresou():
    """Leontinka: grantové řízení a popis nadace z téže stránky — popis grant nepřepíše."""
    with tempfile.TemporaryDirectory() as tmp:
        u = "https://n.cz/vypsane-granty"
        _write(f"{tmp}/in/grant_01.json", {"id": u, "web": "n.cz", "title": "Granty", "body": ""})
        _write(f"{tmp}/in/mission_00.json", {"id": u, "web": "n.cz", "title": "Nadace", "body": ""})
        _write(f"{tmp}/out/grant_01.json", _grant("Grantové řízení 2026", sid=u))
        _write(f"{tmp}/out/mission_00.json", {"name": "Nadace N", "mission": "pomáhá", "_source_id": u})
        marker, recs = _ingest(tmp, [])
        assert marker["mission_clash"] == 1
        assert recs[u]["kind"] == "grant" and recs[u]["title"] == "Grantové řízení 2026"


def test_existujici_popis_nadace_nezmeni_druh():
    """Partnerství: na adrese je v katalogu popis nadace → grant z téže stránky ho nepřepíše."""
    with tempfile.TemporaryDirectory() as tmp:
        u = "https://n.cz/o-nas"
        _write(f"{tmp}/in/grant_00.json", {"id": u, "web": "n.cz", "title": "O nás", "body": ""})
        _write(f"{tmp}/in/mission_00.json", {"id": u, "web": "n.cz", "title": "Nadace", "body": ""})
        _write(f"{tmp}/out/grant_00.json", _grant("Granty 2026", sid=u))
        _write(f"{tmp}/out/mission_00.json", {"name": "Nadace N", "mission": "pomáhá", "_source_id": u})
        marker, recs = _ingest(tmp, [{"id": u, "kind": "foundation_mission", "name": "Nadace N"}])
        assert marker["mission_clash"] == 1
        assert recs[u]["kind"] == "foundation_mission"
        assert marker["total"] == 1


def test_rozcestnik_nevyradi_popis_nadace():
    """Stránka „o nás“ není výzva, ale popis nadace na ní zůstává."""
    with tempfile.TemporaryDirectory() as tmp:
        u = "https://n.cz/o-nas"
        _write(f"{tmp}/in/grant_00.json", {"id": u, "web": "n.cz", "title": "O nás", "body": ""})
        _write(f"{tmp}/out/grant_00.json", {"_source_id": u, "_skip": "stránka o nás"})
        marker, recs = _ingest(tmp, [{"id": u, "kind": "foundation_mission", "name": "Nadace N"}])
        assert marker["dropped"] == 0
        assert recs[u]["kind"] == "foundation_mission"


def test_is_done_jen_pro_svuj_vystup():
    with tempfile.TemporaryDirectory() as tmp:
        inp = f"{tmp}/in/grant_03.json"
        _write(inp, {"id": "https://x.cz/a", "title": "A"})
        assert not is_done(inp, f"{tmp}/out")                       # žádný výstup
        _write(f"{tmp}/out/grant_03.json", _grant("A"))
        assert not is_done(inp, f"{tmp}/out")                       # starý výstup bez adresy
        _write(f"{tmp}/out/grant_03.json", _grant("B", sid="https://x.cz/b"))
        assert not is_done(inp, f"{tmp}/out")                       # cizí výstup
        _write(f"{tmp}/out/grant_03.json", _grant("A", sid="https://x.cz/a"))
        assert is_done(inp, f"{tmp}/out")
        _write(f"{tmp}/out/grant_03.json", {"_source_id": "https://x.cz/a", "_skip": "rozcestník"})
        assert is_done(inp, f"{tmp}/out")                           # rozcestník se znovu nečte


def test_realign_presune_vystup_za_svym_vstupem():
    """GA ČR po přestavbě webu: výzva LA z grant_11 je teď grant_00, EXPRO z webu zmizela."""
    from extract_api import realign
    with tempfile.TemporaryDirectory() as tmp:
        _write(f"{tmp}/in/grant_00.json", {"id": "https://g.cz/la/"})
        _write(f"{tmp}/in/grant_01.json", {"id": "https://g.cz/pl/"})
        _write(f"{tmp}/out/grant_00.json", _grant("EXPRO 2027", sid="https://g.cz/expro/"))
        _write(f"{tmp}/out/grant_11.json", _grant("LA kontinuální", sid="https://g.cz/la/"))
        _write(f"{tmp}/out_stale/grant_00.json", _grant("dřívější odložený", sid="https://g.cz/x/"))
        r = realign(f"{tmp}/in", f"{tmp}/out")
        assert r == {"moved": 1, "stale": 1}
        la = json.load(open(f"{tmp}/out/grant_00.json", encoding="utf-8"))
        assert la["_source_id"] == "https://g.cz/la/"
        assert not os.path.exists(f"{tmp}/out/grant_11.json")
        assert is_done(f"{tmp}/in/grant_00.json", f"{tmp}/out")
        assert not is_done(f"{tmp}/in/grant_01.json", f"{tmp}/out")
        parked = sorted(os.listdir(f"{tmp}/out_stale"))
        assert parked == ["grant_00.1.json", "grant_00.json"]       # nic se nepřepsalo


def test_overeni_stranky_podle_citace_lhuty():
    """refresh_pages: citace lhůty na stránce pořád stojí → beze změny, i složená z kusů."""
    from refresh_pages import norm, quote_on_page
    page = norm("Program 2026.  Žádosti lze podávat\xa0do 31. 3. 2027 na adrese fondu. Formulář ke stažení.")
    assert quote_on_page("Žádosti lze podávat do 31. 3. 2027", page)
    assert quote_on_page("Program 2026. / Žádosti lze podávat do 31. 3. 2027", page)
    assert not quote_on_page("Žádosti lze podávat do 30. 6. 2026", page)    # lhůta se změnila
    assert not quote_on_page("", page)


def test_catalog_id_zachova_zaznam_s_id_z_nazvu():
    """Obnova stránky záznamu `grant:<zdroj>:<název>` dá dokumentu TOTÉŽ id, ne adresu."""
    with tempfile.TemporaryDirectory() as tmp:
        docs = f"{tmp}/docs.jsonl"
        with open(docs, "w", encoding="utf-8") as f:
            f.write(json.dumps({"url": "https://n.cz/program", "catalog_id": "grant:n.cz:program2026",
                                "title": "Program", "text": "Podpora spolků " * 20, "documents": []},
                               ensure_ascii=False) + "\n")
        p = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_extract_input.py"), docs,
                            "--source", "n", "--out-dir", f"{tmp}/in", "--no-prefilter"],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        assert p.returncode == 0, p.stderr[-400:]
        assert json.load(open(f"{tmp}/in/grant_00.json", encoding="utf-8"))["id"] == "grant:n.cz:program2026"


def test_kod_vyzvy_v_nazvu():
    assert code("Výzva č. 31_22_019 – Nákup vozidel") == "31_22_019"
    assert code("2026-D-5-5-47 Účast českých děl") == "2026-D-5-5-47"
    assert code("Výzva č. 2/2024 FN: Půjčka") == "2/2024FN"
    assert code("Výzva 2/2024 FN") == "2/2024FN"
    assert code("Program TREND") is None


if __name__ == "__main__":
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
