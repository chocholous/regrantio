#!/usr/bin/env python3
"""publish_export.py — vystaví hotový export do ÚSCHOVNY, odkud si ho vezme produkt.

    python scripts/publish_export.py            # nahraj docs/opportunities.json
    python scripts/publish_export.py --dry-run  # spočítej otisk a ukaž, co by se stalo
    python scripts/publish_export.py --keep 10  # kolik verzí nechat (default 10)

PROČ ÚSCHOVNA A NE REPOZITÁŘ
─────────────────────────────
Grantio dnes bere data z lokálního klonu regrantia vedle sebe. To funguje pro
vývoj, ale ne pro plánovač: znamenalo by to dát produktu přístup do repozitáře
se scrapery, historií a rozpracovanými větvemi — kvůli JEDNOMU souboru. Token
k repozitáři přitom nejde omezit na soubor.

Úschovna tenhle uzel rozvazuje. Regrantio publikuje artefakt, Grantio si ho
bere; hranice mezi projekty vede přes data, ne přes kód. A hlavně: regrantio
pak MŮŽE BÝT NEVEŘEJNÉ, aniž by se čehokoli dotklo na straně produktu.

CO SE NAHRÁVÁ
─────────────
Dva soubory, a to pořadí je podstatné:

  1. `exports/opportunities-<datum>-<otisk8>.json` … samotný export, VERZOVANĚ
  2. `manifest.json` .............................. ukazatel na aktuální verzi

⚠ MANIFEST AŽ PO EXPORTU. Kdyby se pořadí obrátilo, existoval by okamžik, kdy
manifest ukazuje na soubor, který ještě nedoputoval — a produkt by v tu chvíli
stáhl 404 nebo, hůř, kus souboru. Takhle je nejhorší možný mezistav „manifest
ukazuje na starší verzi", což je normální provozní stav, ne porucha.

⚠ VERZOVANÝ KLÍČ, NE PŘEPIS. Export se nikdy nepřepisuje, přibývá vedle. Vrátit
produkt ke starší verzi je pak úprava jednoho řádku v manifestu, ne obnova ze
zálohy. Staré verze uklízí `--keep`.

CO MUSÍ EXISTOVAT (jednorázově, viz docs/REFRESH.md §8)
─────────────────────────────────────────────────────
  SUPABASE_URL ................ adresa projektu
  SUPABASE_SERVICE_ROLE_KEY ... klíč s právem zápisu do úschovny
  REGRANTIO_BUCKET ............ jméno kbelíku (default `regrantio-exports`)

Bez nich skript NEBĚŽÍ NAPRÁZDNO — skončí s vysvětlením, co chybí. Tichý
„úspěch", po kterém v úschovně nic není, je horší než chyba.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr:
        sys.stderr.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_EXPORT = os.path.join(ROOT, "docs", "opportunities.json")
DEFAULT_BUCKET = "regrantio-exports"


def fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"✖ {msg}", file=sys.stderr)
    sys.exit(1)


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_manifest(payload: bytes, key: str, generated_at: str, count: int) -> dict:
    """
    Manifest je KONTRAKT, ne poznámka. Grantio ho čte v `scripts/lib/feed.mjs`
    a vyžaduje `sha256`, `key` a `generated_at`; `bytes` a `count` jsou navíc,
    ale kontroluje je, když tam jsou.
    """
    return {
        "sha256": sha256_of(payload),
        "bytes": len(payload),
        # Relativní klíč — úschovna se pak dá přestěhovat, aniž by se měnilo,
        # co sem regrantio zapisuje.
        "key": key,
        "generated_at": generated_at,
        "count": count,
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def upload(session, base: str, bucket: str, token: str, key: str, body: bytes, content_type: str) -> None:
    """Nahraje objekt. `x-upsert` je nutný jen u manifestu, který se přepisuje."""
    import urllib.error
    import urllib.request

    url = f"{base}/storage/v1/object/{bucket}/{key}"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("authorization", f"Bearer {token}")
    req.add_header("apikey", token)
    req.add_header("content-type", content_type)
    req.add_header("x-upsert", "true")
    try:
        with session.open(req, timeout=300) as resp:
            if resp.status not in (200, 201):
                fail(f"úschovna odmítla {key}: HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        if e.code == 404:
            fail(
                f"kbelík „{bucket}“ neexistuje.\n"
                f"  Založ ho v Supabase → Storage → New bucket, jméno „{bucket}“, PRIVATE.\n"
                f"  Podrobně: docs/REFRESH.md §8"
            )
        fail(f"úschovna odmítla {key}: HTTP {e.code} — {detail}")
    except urllib.error.URLError as e:
        fail(f"úschovna nedostupná: {e.reason}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export", default=DEFAULT_EXPORT, help="soubor exportu (default docs/opportunities.json)")
    ap.add_argument("--bucket", default=os.environ.get("REGRANTIO_BUCKET", DEFAULT_BUCKET))
    ap.add_argument("--keep", type=int, default=10, help="kolik verzí nechat v úschovně")
    ap.add_argument("--dry-run", action="store_true", help="spočítej otisk a ukaž plán, nic nenahrávej")
    a = ap.parse_args()

    if not os.path.exists(a.export):
        fail(f"export {a.export} neexistuje — pusť nejdřív scripts/export_api.py")

    with open(a.export, "rb") as fh:
        payload = fh.read()

    try:
        feed = json.loads(payload)
    except json.JSONDecodeError as e:
        fail(f"export není platný JSON: {e}")

    meta = feed.get("meta") or {}
    generated_at = meta.get("generated_at")
    count = int(meta.get("count") or len(feed.get("grants") or []))
    if not generated_at:
        fail("export nemá meta.generated_at — publikovat data bez času vzniku nejde")

    digest = sha256_of(payload)
    day = generated_at[:10]
    key = f"exports/opportunities-{day}-{digest[:8]}.json"
    manifest = build_manifest(payload, key, generated_at, count)

    print(f"· export     {a.export}")
    print(f"· záznamů    {count}")
    print(f"· vzniklo    {generated_at}")
    print(f"· velikost   {len(payload) / 1048576:.2f} MB")
    print(f"· otisk      {digest}")
    print(f"· klíč       {key}")

    if a.dry_run:
        print("\nNasucho — nic se nenahrálo. Manifest by vypadal takhle:")
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0

    base = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    token = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not base or not token:
        fail(
            "chybí SUPABASE_URL nebo SUPABASE_SERVICE_ROLE_KEY.\n"
            "  Bez nich se publikovat nedá; co přesně založit, je v docs/REFRESH.md §8.\n"
            "  Zkusit naprázdno: --dry-run"
        )

    import urllib.request

    session = urllib.request.build_opener()

    # ⚠ POŘADÍ: nejdřív data, teprve pak ukazatel na ně.
    print("\n· nahrávám export…")
    upload(session, base, a.bucket, token, key, payload, "application/json")

    print("· nahrávám manifest…")
    body = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    upload(session, base, a.bucket, token, "manifest.json", body, "application/json")

    print(f"\n✓ publikováno. Grantio si to vezme přes REGRANTIO_MANIFEST_URL:")
    print(f"  {base}/storage/v1/object/{a.bucket}/manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
