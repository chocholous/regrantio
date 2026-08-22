#!/usr/bin/env python3
"""Testy PUBLIKAČNÍ CESTY — toho, co stojí mezi hotovým datasetem a produktem.

`test_core.py` hlídá, aby data byla správná. Tenhle soubor hlídá, aby se
správná data správně DOSTALA VEN — a hlavně aby se špatná data ven nedostala.

Proč zrovna tohle:
  • manifest      — je to KONTRAKT. Grantio ho čte v `scripts/lib/feed.mjs`
                    a odmítne export, jehož otisk nesedí. Chybějící pole
                    v manifestu znamená rozbitou synchronizaci u zákazníka,
                    ne u nás — a projeví se to až tam.
  • otisk         — jediná obrana proti ZKRÁCENÉMU PŘENOSU. Useknutý soubor
                    bývá pořád platný JSON s méně záznamy, tedy nejhorší možný
                    vstup: projde kontrolou tvaru a vypadá jako „regrantio
                    přišlo o polovinu zdrojů".
  • pořadí        — manifest se nahrává POSLEDNÍ. Obráceně existuje okamžik,
                    kdy ukazuje na soubor, který ještě nedoputoval.
  • brána         — propad počtu záznamů. Dataset, ze kterého vypadlo pět
                    zdrojů, projde všemi kontrolami jednotlivého záznamu.

Spuštění:  python tests/test_publish.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import publish_export as pub  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _payload(count=3, generated_at="2026-08-22T17:26:17+00:00"):
    feed = {
        "meta": {"schema_version": "1.1", "generated_at": generated_at, "count": count},
        "grants": [{"id": f"g{i}", "content_hash": f"h{i}"} for i in range(count)],
    }
    return json.dumps(feed, ensure_ascii=False).encode("utf-8")


# ------------------------------------------------------------------- otisk
def test_otisk_je_stabilni():
    data = _payload()
    assert pub.sha256_of(data) == pub.sha256_of(data)


def test_zmena_jedineho_bajtu_zmeni_otisk():
    a = _payload()
    b = bytearray(a)
    b[-1] = b[-1] ^ 0x01
    assert pub.sha256_of(a) != pub.sha256_of(bytes(b))


def test_useknuty_soubor_ma_jiny_otisk():
    """⚠ TOHLE JE TEN PŘÍPAD, KVŮLI KTERÉMU MANIFEST NESE OTISK.

    Zkrácený přenos dá často pořád platný JSON s méně záznamy. Kontrola tvaru
    ho pustí; jediné, co ho odliší okamžitě a jednoznačně, je otisk.
    """
    full = _payload(count=100)
    truncated = full[: len(full) // 2]
    assert pub.sha256_of(full) != pub.sha256_of(truncated)


# ---------------------------------------------------------------- manifest
def test_manifest_ma_vsechna_pole_kontraktu():
    """Grantio vyžaduje `sha256`, `key` a `generated_at`; `bytes` kontroluje, když je."""
    data = _payload()
    m = pub.build_manifest(data, "exports/x.json", "2026-08-22T17:26:17+00:00", 3)
    for field in ("sha256", "key", "generated_at", "bytes", "count", "published_at"):
        assert field in m, f"manifest nemá {field}"


def test_manifest_nese_otisk_toho_souboru():
    data = _payload()
    m = pub.build_manifest(data, "exports/x.json", "2026-08-22T17:26:17+00:00", 3)
    assert m["sha256"] == pub.sha256_of(data)
    assert m["bytes"] == len(data)


def test_manifest_klic_je_relativni():
    """⚠ Relativní klíč = úschovna se dá přestěhovat beze změny publikace.

    Kdyby manifest nesl absolutní adresu, znamenala by změna úschovny zásah
    do regrantia — tedy dva projekty svázané kvůli jednomu řetězci.
    """
    m = pub.build_manifest(_payload(), "exports/x.json", "2026-08-22T17:26:17+00:00", 3)
    assert not m["key"].startswith("http")


def test_manifest_je_platny_json():
    m = pub.build_manifest(_payload(), "exports/x.json", "2026-08-22T17:26:17+00:00", 3)
    assert json.loads(json.dumps(m, ensure_ascii=False)) == m


# ------------------------------------------------------- pořadí a verzování
def test_klic_obsahuje_datum_i_otisk():
    """Verzovaný klíč: export se nikdy nepřepisuje, přibývá vedle.

    Vrátit produkt ke starší verzi je pak úprava jednoho řádku v manifestu,
    ne obnova ze zálohy.
    """
    data = _payload()
    digest = pub.sha256_of(data)
    key = f"exports/opportunities-2026-08-22-{digest[:8]}.json"
    assert "2026-08-22" in key and digest[:8] in key


def test_dva_ruzne_exporty_maji_ruzny_klic():
    a, b = _payload(count=3), _payload(count=4)
    assert pub.sha256_of(a)[:8] != pub.sha256_of(b)[:8]


def test_manifest_se_nahrava_posledni():
    """⚠ POŘADÍ JE SOUČÁST NÁVRHU, ne pořadí psaní.

    Kontroluje se nad ZDROJOVÝM KÓDEM, protože samotné nahrání potřebuje
    úschovnu. Je to hrubý test, ale chytá přesně tu záměnu, která by se jinak
    projevila až u zákazníka jako stažený kus souboru.
    """
    src = open(os.path.join(ROOT, "scripts", "publish_export.py"), encoding="utf-8").read()
    body = src[src.index("def main("):]
    assert body.index("nahrávám export") < body.index("nahrávám manifest")


# ------------------------------------------------------------------- brána
def _gate(catalog_lines, export_count):
    """Pustí bránu propadu nad dočasnými soubory a vrátí (prošlo, hláška)."""
    import validate_release as vr

    with tempfile.TemporaryDirectory() as tmp:
        catalog = os.path.join(tmp, "catalog.jsonl")
        export = os.path.join(tmp, "export.json")
        with open(catalog, "w", encoding="utf-8") as fh:
            for i in range(catalog_lines):
                fh.write(json.dumps({"id": f"g{i}"}) + "\n")
        with open(export, "w", encoding="utf-8") as fh:
            json.dump({"grants": [{"id": f"g{i}"} for i in range(export_count)]}, fh)

        old_catalog, old_export = vr.CATALOG, vr.EXPORT
        vr.CATALOG, vr.EXPORT = catalog, export
        try:
            vr.check_no_collapse()
            return True, ""
        except RuntimeError as e:
            return False, str(e)
        finally:
            vr.CATALOG, vr.EXPORT = old_catalog, old_export


def test_brana_pusti_beze_zmeny():
    passed, _ = _gate(3452, 3452)
    assert passed


def test_brana_pusti_rust():
    """⚠ RŮST SE NEHLÍDÁ. Nový zdroj přinese skokem stovky záznamů a je to
    přesně to, co má pipeline dělat."""
    passed, _ = _gate(4000, 3452)
    assert passed


def test_brana_pusti_maly_ubytek():
    """Uzavřené programy z katalogu mizí; pár procent je normální úklid."""
    passed, _ = _gate(3300, 3452)
    assert passed


def test_brana_zastavi_propad():
    """Vypadlý zdroj = tichá ztráta pětiny dat. Tohle je ta chyba, kterou
    žádná kontrola jednotlivého záznamu nezachytí."""
    passed, msg = _gate(1000, 3452)
    assert not passed
    assert "1000" in msg and "3452" in msg


def test_brana_zastavi_prazdny_katalog():
    passed, _ = _gate(0, 3452)
    assert not passed


# ------------------------------------------------------------------ identita
def _identity(records):
    import validate_release as vr

    with tempfile.TemporaryDirectory() as tmp:
        catalog = os.path.join(tmp, "catalog.jsonl")
        with open(catalog, "w", encoding="utf-8") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

        old = vr.CATALOG
        vr.CATALOG = catalog
        try:
            vr.check_catalog_identity()
            return True, ""
        except RuntimeError as e:
            return False, str(e)
        finally:
            vr.CATALOG = old


def test_identita_pusti_unikatni():
    passed, _ = _identity([{"id": "a"}, {"id": "b"}])
    assert passed


def test_identita_zastavi_duplicitu():
    """⚠ Duplicitní id se v produktu projeví TICHÝM PŘEPISEM: dva záznamy se
    slijí v jeden a ten druhý zmizí. Tady jde ještě poznat, který zdroj ho
    vyrobil."""
    passed, msg = _identity([{"id": "a", "source": "kraj.cz"}, {"id": "a", "source": "kraj.cz"}])
    assert not passed
    assert "kraj.cz" in msg


def test_identita_zastavi_chybejici_id():
    passed, msg = _identity([{"id": "a"}, {"source": "kraj.cz"}])
    assert not passed
    assert "bez id" in msg


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
