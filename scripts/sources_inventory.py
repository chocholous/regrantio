#!/usr/bin/env python3
"""sources_inventory.py — JEDEN INVENTÁŘ ZDROJŮ: `data/sources.json`.

Do 2026‑09‑14 odpovídaly na otázku „jaké zdroje máme" čtyři různé věci a každá
jinak: `source_names.json` (jméno), registr v `refresh_run.py` (čím a jak se
obnovuje, jen 28 + 21 zdrojů), `routing.yaml` (platforma → harvester, 81
položek klíčovaných doménou) a samotný katalog (135 hodnot `source`). Číslo
„kolik zdrojů funguje" se z toho nedalo přečíst bez ručního procházení.

Tenhle skript to SPOJÍ do jednoho souboru a drží v něm dvě vrstvy:

  • KURÁTOROVANÉ pole (píše člověk, regenerace je zachová):
      name           jméno poskytovatele, jak ho říká žadatel
      homepage       kde zdroj bydlí
      note           cokoli, co má příští člověk vědět (blok, dohoda, výjimka)
  • POČÍTANÉ pole (přepisují se při každém běhu):
      type           převažující `typ_poskytovatele` v datech
      refresh        A = strukturní ingest · B = vlastní parser · C = model ·
                     T = přepsaný extraktor (obnovu jen předstírá) · F = zmrazený
                     (zdroj za přihlášením / mrtvý) · ? = nikde v registru
      harvester      skript, kterým se sbírá (je-li v registru)
      records / live počty v katalogu (live = open, announced, unknown)
      last_fetched   nejnovější `provenance.fetched_at` u zdroje

Spuštění (z kořene repa):
    python scripts/sources_inventory.py            # přepočítá a zapíše
    python scripts/sources_inventory.py --check    # jen ověří, že inventář sedí na katalog (brána)
"""
import argparse
import collections
import datetime
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

CATALOG = os.path.join(ROOT, "data", "opportunities.jsonl")
NAMES = os.path.join(ROOT, "data", "source_names.json")
INVENTORY = os.path.join(ROOT, "data", "sources.json")

CURATED = ("name", "homepage", "note")

# Zdroje, o kterých víme, že se obnovit nedají, a proč. Kurátorované; sem se
# píše ručně, ne odvozením — „zmrazený" je rozhodnutí, ne měření.
FROZEN = {
    "kr-jihomoravsky.cz": "úřední deska za přihlášením (HTTP 401 od 2026-09-01)",
    "sfpi": "WP REST API zrušeno (404)",
}


# Rodiny CMS, které obnovuje jeden sdílený harvester (viz routing.yaml `families:`).
FAMILY_HARVESTER = {
    "dsw2_otevrenamesta": "dsw2.py",
    "vismo": "vismo.py",
    "kentico": "kentico_irop.py",
    "plone": "plone_ostrava.py",
}


def _registry():
    """Třída obnovy a harvester: `refresh_run.py` (výslovný registr) + rodiny z `platform_map.json`."""
    import refresh_run as rr  # noqa: WPS433
    out = {}
    try:
        final = json.load(open(os.path.join(ROOT, "platform_map.json"), encoding="utf-8")).get("final") or {}
        for host, info in final.items():
            h = FAMILY_HARVESTER.get((info or {}).get("plat"))
            if h:
                out[host] = ("A", h)
    except (OSError, ValueError):
        pass
    for slug, spec in rr.SOURCES.items():
        out[slug] = ("A", spec[0][0] if isinstance(spec, tuple) and spec and isinstance(spec[0], list) else None)
    for slug, spec in rr.EXTRACT_SOURCES.items():
        out[slug] = ("B", spec[0][0] if spec and isinstance(spec[0], list) else None)
    for slug in rr.TRANSCRIBED:
        out[slug] = ("T", None)
    # Přepsaný extraktor s harvesterem má od 2026‑09‑14 cestu přes model
    # (`refresh_run.py --tier model`): třída C, ne T.
    for slug, spec in getattr(rr, "MODEL_SOURCES", {}).items():
        out[slug] = ("C", spec[0])
    return out


# Slug v datech ≠ jméno skriptu. Tohle je to propojení, o kterém REMAINING.md
# psalo, že „nikde v repozitáři neexistuje" — teď existuje tady a jen tady.
HARVESTER_ALIASES = {
    "havirov-city.cz": "havirov_harvest.py",
    "granty.chomutov.cz": "chomutov_harvest.py",
    "mmkv.cz": "kv_mesto_harvest.py",
    "mestojablonec.cz": "jablonec_harvest.py",
    "mmdecin.cz": "decin_harvest.py",
    "olomouc.eu": "olomouc_mesto_harvest.py",
    "karvina.cz": "karvina_harvest.py",
    "pardubice.eu": "pardubice_mesto_harvest.py",
    "pardubickykraj.cz": "pardubicky_harvest.py",
    "dotace.plzen.eu": "plzen_mesto_harvest.py",
    "dotace.plzensky-kraj.cz": "plzen_mesto_harvest.py",
    "granty.liberec.cz": "liberec_mesto_harvest.py",
    "frydekmistek.cz": "fm_harvest.py",
    "opava-city.cz": "opava_harvest.py",
    "dotace.ostrava.cz": "ostrava_harvest.py",
    "mkcr": "mk_harvest.py",
    "mzcr": "mv_cms.py",
    "nadacecez": "harvest_site.py",
}


def _own_harvester(slug):
    """`scripts/<jméno>_harvest.py` nebo `scripts/<jméno>.py` podle prvního tokenu slugu."""
    if slug in HARVESTER_ALIASES:
        return HARVESTER_ALIASES[slug]
    stem = slug.split(".")[0].replace("-", "_")
    for cand in (f"{stem}_harvest.py", f"{stem}.py"):
        if os.path.exists(os.path.join(ROOT, "scripts", cand)) and cand not in ("routing.py", "limits.py"):
            return cand
    return None


def _status(rec, today):
    d = rec.get("deadline")
    if isinstance(d, str) and d.strip().lower() in ("průběžně", "prubezne", "průběžný", "rolling"):
        return "open"
    if not d:
        return "unknown"
    if today > d:
        return "closed"
    o = rec.get("open_from")
    if o and today < o:
        return "announced"
    return "open"


def build(today=None):
    today = today or datetime.date.today().isoformat()
    names = {k: v for k, v in json.load(open(NAMES, encoding="utf-8")).items() if not k.startswith("_")}
    old = {}
    if os.path.exists(INVENTORY):
        old = {k: v for k, v in json.load(open(INVENTORY, encoding="utf-8")).items() if not k.startswith("_")}
    registry = _registry()

    recs = [json.loads(l) for l in open(CATALOG, encoding="utf-8") if l.strip()]
    per = collections.defaultdict(list)
    for r in recs:
        per[r.get("source")].append(r)

    inv = {}
    for slug, rs in sorted(per.items()):
        types = collections.Counter((r.get("facets") or {}).get("typ_poskytovatele") for r in rs if r.get("kind") == "grant")
        types.pop(None, None)
        fetched = [((r.get("provenance") or {}).get("fetched_at") or "") for r in rs]
        last = max(fetched) if any(fetched) else None
        hosts = collections.Counter()
        for r in rs:
            u = r.get("source_url") or ""
            host = u.split("/")[2] if u.startswith("http") and u.count("/") >= 2 else None
            if host:
                hosts[host] += 1
        cls, harvester = registry.get(slug, ("?", None))
        if slug in FROZEN:
            cls = "F"
        elif cls == "?":
            # Zdroj s vlastním harvesterem, ale bez deterministického extraktoru:
            # obnova vede přes model (třída C). Bez harvesteru zůstává „?" —
            # jednorázový sběr, u kterého cesta k obnově NENÍ zapsaná.
            own = _own_harvester(slug)
            if own:
                cls, harvester = "C", own
            elif any(fetched):
                cls = "C"
        entry = {
            "name": (old.get(slug) or {}).get("name") or names.get(slug),
            "homepage": (old.get(slug) or {}).get("homepage") or (("https://" + hosts.most_common(1)[0][0]) if hosts else None),
            "note": (old.get(slug) or {}).get("note") or FROZEN.get(slug),
            "type": types.most_common(1)[0][0] if types else None,
            "refresh": cls,
            "harvester": harvester,
            "records": len(rs),
            "live": sum(1 for r in rs if r.get("kind") == "grant" and _status(r, today) != "closed"),
            "last_fetched": last,
        }
        inv[slug] = entry
    return inv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="jen ověř, nezapisuj")
    a = ap.parse_args()
    inv = build()
    if a.check:
        if not os.path.exists(INVENTORY):
            print("✖ data/sources.json neexistuje — pusť scripts/sources_inventory.py")
            return 1
        cur = {k: v for k, v in json.load(open(INVENTORY, encoding="utf-8")).items() if not k.startswith("_")}
        missing = sorted(set(inv) - set(cur))
        unnamed = sorted(k for k, v in inv.items() if not v["name"])
        if missing or unnamed:
            for m in missing:
                print(f"✖ zdroj {m} není v inventáři")
            for u in unnamed:
                print(f"✖ zdroj {u} nemá jméno")
            return 1
        print(f"✓ inventář: {len(cur)} zdrojů, všechny pojmenované")
        return 0
    out = {"_README": "Inventář zdrojů. Kurátorovaná pole: name, homepage, note. Ostatní přepisuje "
                      "scripts/sources_inventory.py z katalogu a registru obnovy — neupravovat ručně.",
           **inv}
    with open(INVENTORY, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, ensure_ascii=False, indent="\t")
        fh.write("\n")
    by = collections.Counter(v["refresh"] for v in inv.values())
    print(f"✓ {len(inv)} zdrojů → data/sources.json   " + "  ".join(f"{k}={n}" for k, n in sorted(by.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
