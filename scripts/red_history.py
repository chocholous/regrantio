#!/usr/bin/env python3
"""red_history.py — KDO UŽ JAKÉ PENÍZE DOSTAL (registr dotací MF, IS ReD).

Otevřená data Registru dotací (`red.financnisprava.cz/opendata`, čtvrtletně,
CSV) nesou u každé dotace ze státního rozpočtu, státních fondů a EU příjemce
s IČO, poskytovatele, rok a rozhodnutou částku. Tenhle skript z nich skládá
malou tabulku historie po IČO:

    ico · poskytovatel · rok → počet dotací, rozhodnutá částka

Grantio ji čte ze dvou míst (`the-machine-app` `docs/KONCEPCE.md` D6):
  • profil a onboarding: „podle registru dotací jste od roku 2019 získali
    23 dotací od 5 poskytovatelů“ — fakt s původem, žádný odhad;
  • shoda: „tento poskytovatel vás už podpořil (2023, 2024)“ jako doložený
    důvod u výzvy téhož poskytovatele.

⚠ KRAJE A OBCE TU NEJSOU. ReD eviduje státní peníze; územní rozpočty má
MONITOR jen ve webovém rozhraní. Historie proto říká „od státu a z EU“,
nikdy „všechny dotace“.

⚠ JEN PRÁVNICKÉ OSOBY S IČO. Fyzické osoby (jméno, příjmení, rok narození)
se ani nenačítají: pro shodu je nepotřebujeme a v tabulce by byly osobní údaje.

Paměť: klíče dotací a příjemců jsou 40znakové hashe v IRI; drží se jen jejich
prvních 16 hex znaků jako celé číslo (kolize u milionů záznamů zanedbatelná).

Spuštění z kořene repa:
    python scripts/red_history.py --download           # stáhne CSV do data/red/
    python scripts/red_history.py                      # agreguje → data/red_history.jsonl
    python scripts/red_history.py --publish            # zapíše do Grantia (tabulka recipient_history)
"""
import argparse
import csv
import gzip
import io
import json
import os
import sys
import urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RED = os.path.join(ROOT, "data", "red")
OUT = os.path.join(ROOT, "data", "red_history.jsonl")
API = "https://red.financnisprava.cz/opendata/api/3/action/package_show?id="
DATASETS = {"prijemce-pomoci": "prijemce.csv.gz", "poskytovatel-dotace": None,
            "dotace": "dotace.csv.gz", "rozhodnuti": "rozhodnuti.csv.gz"}
FROM_YEAR = 2016

csv.field_size_limit(10_000_000)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def key(iri):
    """Poslední segment IRI je 40znakový hash; prvních 16 znaků jako int."""
    h = iri.rsplit("/", 1)[-1] if iri else ""
    return int(h[:16], 16) if len(h) >= 16 else None


def rows(name):
    path = os.path.join(RED, name)
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


def download():
    os.makedirs(RED, exist_ok=True)
    for ds in DATASETS:
        meta = json.load(urllib.request.urlopen(API + ds, timeout=60))
        res = [r for r in meta["result"]["resources"] if r["url"].endswith(".csv.gz")][0]
        dest = os.path.join(RED, os.path.basename(res["url"]))
        print(f"· {ds} → {dest} ({res.get('last_modified', '')[:10]})")
        urllib.request.urlretrieve(res["url"], dest)


def aggregate():
    provider_file = next(f for f in os.listdir(RED) if f.startswith("ciselnikdotaceposkytovatel"))
    providers = {key(r["iriDotacePoskytovatel"]): r["dotacePoskytovatelNazev"].strip() for r in rows(provider_file)}
    print(f"· poskytovatelů {len(providers)}")

    recipients = {}
    for r in rows("prijemce.csv.gz"):
        ico = (r.get("ico") or "").strip()
        if len(ico) == 8 and ico.isdigit() and not r.get("jmeno"):
            recipients[key(r["iriPrijemce"])] = int(ico)
    print(f"· příjemců s IČO {len(recipients)}")

    grants = {}
    for r in rows("dotace.csv.gz"):
        ico = recipients.get(key(r["iriPrijemce"]))
        if ico:
            grants[key(r["iriDotace"])] = ico
    print(f"· dotací právnických osob {len(grants)}")
    del recipients

    agg = defaultdict(lambda: [set(), 0.0])
    skipped = 0
    for r in rows("rozhodnuti.csv.gz"):
        try:
            year = int(r["rokRozhodnuti"] or 0)
        except ValueError:
            continue
        if year < FROM_YEAR:
            continue
        g = key(r["iriDotace"])
        ico = grants.get(g)
        provider = providers.get(key(r["iriDotacePoskytovatel"]))
        if not ico or not provider:
            skipped += 1
            continue
        try:
            amount = float(r["castkaRozhodnuta"] or 0)
        except ValueError:
            amount = 0.0
        a = agg[(ico, provider, year)]
        a[0].add(g)
        a[1] += amount
    print(f"· řádků historie {len(agg)} (bez příjemce nebo poskytovatele {skipped})")

    with open(OUT, "w", encoding="utf-8") as o:
        for (ico, provider, year), (ids, amount) in agg.items():
            o.write(json.dumps({"ico": f"{ico:08d}", "provider": provider, "year": year,
                                "awards": len(ids), "amount": round(amount)}, ensure_ascii=False) + "\n")
    print(f"✓ {OUT}")


def publish():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import publish_db as P  # noqa: E402  Db, load_env
    P.load_env()
    db = P.Db(os.environ.get("PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL"), os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    data = [json.loads(l) for l in open(OUT, encoding="utf-8")]
    print(f"· zapisuji {len(data)} řádků do recipient_history")
    for i in range(0, len(data), 1000):
        db.upsert("recipient_history", data[i:i + 1000])
        print(f"  {min(i + 1000, len(data))} / {len(data)}", end="\r")
    print("\n✓ hotovo")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--download", action="store_true")
    ap.add_argument("--publish", action="store_true")
    a = ap.parse_args()
    if a.download:
        download()
        return
    if a.publish:
        publish()
        return
    aggregate()


if __name__ == "__main__":
    main()
