#!/usr/bin/env python3
"""refresh_run.py — JEDEN PŘÍKAZ, kterým se katalog skutečně obnoví.

`refresh.py` je checklist: řekne, CO by se dalo obnovit. Tenhle skript to UDĚLÁ —
pro zdroje, které to zvládnou bez jazykového modelu.

    python scripts/refresh_run.py --list          # co je v registru a čím se obnoví
    python scripts/refresh_run.py                 # obnov vše deterministické + tail
    python scripts/refresh_run.py --tier structured
    python scripts/refresh_run.py --only dotace.khk.cz,fondvysociny.cz
    python scripts/refresh_run.py --tail-only     # jen přepočet + export (bez sítě)
    python scripts/refresh_run.py --dry-run       # ukaž příkazy, nic nespouštěj

DVĚ TŘÍDY ZDROJŮ, a rozdíl je zásadní
─────────────────────────────────────
  deterministické  harvest → strukturní ingest. Celá cesta je kód, takže se dá
                   pustit kdykoli a opakovaně. TOHLE skript umí.
  modelové         harvest → build_extract_input → extract_wf.js (LLM) → ingest_rich.
                   Vyžaduje běh workflow uvnitř Claude Code, takže to není věc
                   cronu ani tohohle skriptu. Viz README a docs/REFRESH.md.

⚠ NOVÉ VÝZVY U MODELOVÝCH ZDROJŮ TENHLE SKRIPT NEPŘINESE. Přinese je u zdrojů
deterministických a u VŠECH srovná termíny a status k dnešku — což je ta část
zastarávání, která se děje sama od sebe každý den, i když nikdo nic nepublikoval.

⚠ JEDEN ZDROJ NESMÍ SHODIT CELÝ BĚH. Weby krajů padají, mění se a jsou pomalé.
Chyba se zaznamená, pokračuje se dál a shrnutí na konci ji přizná; návratový kód
je nenulový, aby si toho všiml i plánovač.

⚠ TAIL BĚŽÍ VŽDYCKY, i když všechny harvesty selžou. Přepočet statusu na síti
nezávisí a je to to nejlevnější, co se dá pro čerstvost udělat.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr:
        sys.stderr.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

# -----------------------------------------------------------------------------
# REGISTR DETERMINISTICKÝCH ZDROJŮ
# -----------------------------------------------------------------------------
# host → (harvest argumenty, výstupní soubor, ingest argumenty, tier)
#
# Tier je jen VÝBĚROVÉ KRITÉRIUM, ne jiný postup: `structured` = JSON/REST API
# (rychlé, odolné), `html` = parsování stránek (levné, ale citlivé na redesign).
#
# Výstupní soubor je ZÁMĚRNĚ tentýž, jaký má harvester jako default: kdo pustí
# harvester ručně, dostane totéž co tenhle skript a ingest se nespleje.
SOURCES = {
    "dotace.khk.cz": (
        ["dotis_harvest.py", "--web", "https://dotace.khk.cz", "--source", "dotace.khk.cz",
         "--out", "data/h_dotis_khk.json"],
        "data/h_dotis_khk.json",
        ["ingest_dotis.py", "data/h_dotis_khk.json", "--kraj", "Královéhradecký kraj"],
        "structured",
    ),
    "fondvysociny.cz": (
        ["fondvysociny_harvest.py"], "data/h_fondvysociny.json",
        ["ingest_fondvysociny.py", "data/h_fondvysociny.json"],
        "html",
    ),
    "dotace.kraj-lbc.cz": (
        ["liberecky_harvest.py"], "data/h_kraj_liberecky.json",
        ["ingest_kraj.py", "data/h_kraj_liberecky.json"],
        "html",
    ),
    "dotace.pardubickykraj.cz": (
        ["pardubicky_harvest.py"], "data/h_kraj_pardubicky.json",
        ["ingest_kraj.py", "data/h_kraj_pardubicky.json"],
        "html",
    ),
    "kr-ustecky.cz": (
        ["ustecky_harvest.py"], "data/h_kraj_ustecky.json",
        ["ingest_kraj.py", "data/h_kraj_ustecky.json"],
        "html",
    ),
    "msk.cz": (
        ["msk_harvest.py"], "data/h_kraj_msk.json",
        ["ingest_kraj.py", "data/h_kraj_msk.json"],
        "html",
    ),
    "stredoceskykraj.cz": (
        ["stredocesky_harvest.py"], "data/h_kraj_stredocesky.json",
        ["ingest_kraj.py", "data/h_kraj_stredocesky.json"],
        "html",
    ),
    "kr-karlovarsky.cz": (
        ["karlovarsky_harvest.py"], "data/h_kraj_karlovarsky.json",
        ["ingest_kraj.py", "data/h_kraj_karlovarsky.json"],
        "html",
    ),
    "kr-jihomoravsky.cz": (
        ["jm_harvest.py"], "data/h_kraj_jm.json",
        ["ingest_kraj.py", "data/h_kraj_jm.json"],
        "html",
    ),
    "kraj-jihocesky.cz": (
        ["jihocesky_harvest.py"], "data/h_kraj_jihocesky.json",
        ["ingest_kraj.py", "data/h_kraj_jihocesky.json"],
        "html",
    ),
    "olkraj.cz": (
        ["olomoucky_harvest.py"], "data/h_kraj_olomoucky.json",
        ["ingest_kraj.py", "data/h_kraj_olomoucky.json"],
        "html",
    ),
    "zlinskykraj.cz": (
        ["zlinsky_harvest.py"], "data/h_kraj_zlinsky.json",
        ["ingest_kraj.py", "data/h_kraj_zlinsky.json"],
        "html",
    ),
    "praha.eu": (
        ["praha_harvest.py"], "data/h_kraj_praha.json",
        ["ingest_kraj.py", "data/h_kraj_praha.json"],
        "html",
    ),
    # ⚠ Brno je „mesto", ne „kraj" — jméno souboru se od ostatních liší.
    "dotace.brno.cz": (
        ["brno_harvest.py"], "data/h_mesto_brno.json",
        ["ingest_kraj.py", "data/h_mesto_brno.json"],
        "html",
    ),
}

# Přepočet a export. Na síti nezávisí, takže běží i po neúspěšném harvestu.
TAIL = [
    (["derive_deadlines.py"], "doplnění termínů z opakujících se lhůt"),
    (["fix_dataset.py"], "dedup, reklasifikace, přepočet statusu k dnešku"),
    (["consolidate.py"], "sjednocení variant faset na kanonické hodnoty"),
    # ⚠ BRÁNA PŘED PUBLIKACÍ, ne po ní. Export je to, co si stáhne produkt;
    # zveřejnit dataset s inverzním termínem nebo prázdným titulem a teprve
    # potom to zjistit znamená, že si vadu odnesou uživatelé.
    (["validate_release.py"], "kontrola kvality dat (brána)"),
    (["export_api.py"], "veřejný export docs/opportunities.json"),
]


def run(args, label, dry):
    """Spustí krok. Vrací (ok, poslední řádek výstupu)."""
    cmd = [PY, os.path.join("scripts", args[0])] + args[1:]
    if dry:
        print(f"    $ {' '.join(cmd[1:])}")
        return True, ""
    t = time.time()
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=1800)
    except subprocess.TimeoutExpired:
        print(f"    ✖ {label}: překročen čas (30 min)")
        return False, ""
    tail = [l for l in (p.stdout or "").strip().splitlines() if l.strip()]
    last = tail[-1] if tail else ""
    if p.returncode != 0:
        print(f"    ✖ {label} (kód {p.returncode}) — {(p.stderr or last or '').strip()[:200]}")
        return False, last
    print(f"    ✓ {label}  {int(time.time() - t)}s  {last[:150]}")
    return True, last


def counts(path="data/opportunities.jsonl"):
    p = os.path.join(ROOT, path)
    if not os.path.exists(p):
        return 0
    with open(p, encoding="utf-8") as fh:
        return sum(1 for _ in fh)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="čárkou oddělené hosty z registru")
    ap.add_argument("--tier", choices=["structured", "html"], help="jen zdroje daného tieru")
    ap.add_argument("--list", action="store_true", help="vypiš registr a skonči")
    ap.add_argument("--tail-only", action="store_true", help="jen přepočet a export, bez sítě")
    ap.add_argument("--skip-tail", action="store_true", help="jen harvest a ingest")
    ap.add_argument("--dry-run", action="store_true", help="ukaž příkazy, nic nespouštěj")
    a = ap.parse_args()

    if a.list:
        print(f"DETERMINISTICKÉ ZDROJE ({len(SOURCES)}) — harvest + strukturní ingest, bez modelu\n")
        for host, (h, _out, i, tier) in sorted(SOURCES.items()):
            print(f"  {host:26} {tier:11} {h[0]:26} → {i[0]}")
        print("\nOstatní zdroje potřebují modelovou vrstvu (extract_wf.js) — viz docs/REFRESH.md.")
        return 0

    chosen = sorted(SOURCES)
    if a.tier:
        chosen = [h for h in chosen if SOURCES[h][3] == a.tier]
    if a.only:
        want = [s.strip() for s in a.only.split(",") if s.strip()]
        unknown = [w for w in want if w not in SOURCES]
        if unknown:
            print(f"✖ Neznámé zdroje: {', '.join(unknown)}")
            print(f"  Známé: {', '.join(sorted(SOURCES))}")
            return 2
        chosen = want

    before = counts()
    failed = []

    # ⚠ ZÁLOHA PŘED SÍTÍ, ne až ve `fix_dataset`. Ten dělá `.bak` až ze stavu PO
    # ingestu, takže rozbitý harvest, který katalog poškodí, se do ní stihne
    # propsat. Tahle kopie je poslední stav PŘED tím, než se čehokoli dotkla síť.
    src = os.path.join(ROOT, "data/opportunities.jsonl")
    if not a.tail_only and not a.dry_run and os.path.exists(src):
        shutil.copyfile(src, src + ".pre-refresh.bak")
        print(f"· záloha před během → data/opportunities.jsonl.pre-refresh.bak ({before} záznamů)\n")

    if not a.tail_only:
        print(f"═══ HARVEST + INGEST ({len(chosen)} zdrojů) ═══")
        for host in chosen:
            harvest, out, ingest, _tier = SOURCES[host]
            print(f"\n  {host}")
            ok, _ = run(harvest, "harvest", a.dry_run)
            if not ok:
                failed.append(f"{host} (harvest)")
                continue
            # Prázdný nebo chybějící výstup = ingest by tiše nic neudělal.
            if not a.dry_run and not os.path.exists(os.path.join(ROOT, out)):
                print(f"    ✖ harvest neuložil {out}")
                failed.append(f"{host} (bez výstupu)")
                continue
            ok, _ = run(ingest, "ingest", a.dry_run)
            if not ok:
                failed.append(f"{host} (ingest)")

    if not a.skip_tail:
        print(f"\n═══ PŘEPOČET A EXPORT ═══")
        for args, label in TAIL:
            ok, _ = run(args, label, a.dry_run)
            if not ok:
                failed.append(label)
                # Export bez přepočtu by vydal nesrovnaná data — dál nemá smysl.
                break

    after = counts()
    print(f"\n═══ SHRNUTÍ ═══")
    print(f"  záznamů v katalogu: {before} → {after}  ({after - before:+d})")
    if failed:
        print(f"  ✖ selhalo: {', '.join(failed)}")
        print("  Ostatní zdroje proběhly; oprav a pusť znovu jen ty selhané (--only).")
        return 1
    print("  ✓ bez chyb")
    return 0


if __name__ == "__main__":
    sys.exit(main())
