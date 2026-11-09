#!/usr/bin/env python3
"""Vrstva 2 (model) bez API klíče: zadání pro agenty v Claude Code.

⚠ PROČ (2026-11-08). Třída C (`refresh_run.py --tier model`) volá model přes
Messages API (`extract_api.py`) a bez `ANTHROPIC_API_KEY` se přeskočí. Totéž
čtení výzvy umí udělat agent v sezení Claude Code: týž prompt, týž seznam
klíčů, týž výstup. Tenhle skript dělá z extrakce opakovatelný postup místo
ručního odklikávání `workflows/extract_wf.js`:

  1. `--tasks`   ke každému dokumentu bez výstupu napíše úplné zadání
                 (`<tasks-dir>/<basename>.md`: systémový prompt, dokument,
                 seznam klíčů a tvar) — agent přečte jeden soubor a zapíše
                 jeden JSON do `<out-dir>/<basename>.json`;
  2. `--check`   ověří výstupy: platný JSON, všechny klíče (chybějící doplní
                 null), nic navíc mimo schéma; vadné vypíše a nesmaže.

⚠ ROZCESTNÍK NENÍ VÝZVA. Část vstupů jsou stránky „Výzvy“, „Naše poslání“,
„Národní dotační tituly“: odkazy na programy, ne program. API cesta z nich
dřív udělala záznam. Agent místo toho zapíše `{"_source_id": …, "_skip":
"<proč>"}` a `ingest_rich` záznam s touto adresou z katalogu vyřadí
(v databázi dostane `withdrawn_at`, nic se nemaže).

Prompt se čte z `workflows/extract_wf.js` přes `extract_api.load_prompts()`,
takže API cesta a ruční cesta nemůžou číst výzvu jinak. Pak jako vždy:
`ingest_rich.py --out-dir <out> --src <in> ...` (viz `refresh_run.model_chain`).

    python scripts/extract_manual.py --in-dir data/sfzp_in --out-dir data/sfzp_out --tasks data/sfzp_tasks
    python scripts/extract_manual.py --in-dir data/sfzp_in --out-dir data/sfzp_out --check
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract_api import is_done, load_prompts, realign, type_of, user_message  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def pending(in_dir, out_dir, redo=False):
    paths = sorted(p for p in glob.glob(os.path.join(in_dir, "*.json")) if os.path.basename(p) != "paths.json")
    if redo:
        return paths
    return [p for p in paths if not is_done(p, out_dir)]


def write_tasks(paths, tasks_dir, out_dir, system, keys, shape):
    os.makedirs(tasks_dir, exist_ok=True)
    for p in paths:
        t = type_of(p)
        doc = json.load(open(p, encoding="utf-8"))
        base = os.path.basename(p)
        out = os.path.join(out_dir, base).replace("\\", "/")
        body = (
            f"# ZADÁNÍ: vrstva 2 regrantia\n\n"
            f"Výstup zapiš do `{out}` jako JEDEN syrový JSON objekt (UTF-8, bez ```).\n"
            f"Do objektu přidej klíč `_source_id` s hodnotou {json.dumps(doc.get('id'), ensure_ascii=False)} "
            f"(podle něj se výstup spojí s výzvou).\n\n"
            f"Pokud dokument NENÍ jedna konkrétní výzva nebo program s podmínkami "
            f"(je to rozcestník, seznam odkazů, stránka „o nás“, archiv), zapiš místo toho jen "
            f"`{{\"_source_id\": {json.dumps(doc.get('id'), ensure_ascii=False)}, \"_skip\": \"<krátce proč>\"}}`.\n"
            f"Dlouhé přílohy nečti celé: hledej v tomto souboru (Grep) lhůty, částky, žadatele a podmínky.\n\n"
            f"## Systémový prompt\n\n{system[t]}\n\n"
            f"## Dokument a pokyny\n\n{user_message(doc, t, keys[t], shape[t])}\n"
        )
        open(os.path.join(tasks_dir, base.replace(".json", ".md")), "w", encoding="utf-8").write(body)
    return len(paths)


def check(in_dir, out_dir, keys):
    ok, bad = 0, []
    for p in sorted(glob.glob(os.path.join(in_dir, "*.json"))):
        base = os.path.basename(p)
        if base == "paths.json":
            continue
        o = os.path.join(out_dir, base)
        if not os.path.exists(o):
            continue
        t = type_of(p)
        try:
            data = json.load(open(o, encoding="utf-8"))
        except (ValueError, json.JSONDecodeError) as e:
            bad.append((base, f"neplatný JSON: {e}"))
            continue
        if not isinstance(data, dict):
            bad.append((base, "není objekt"))
            continue
        if data.get("_source_id") != json.load(open(p, encoding="utf-8")).get("id"):
            bad.append((base, "výstup patří k jiné výzvě (_source_id)"))
            continue
        if data.get("_skip"):
            if set(data) - {"_source_id", "_skip"}:
                bad.append((base, "rozcestník (_skip) nesmí nést údaje výzvy"))
                continue
            ok += 1
            continue
        missing = [k for k in keys[t] if k not in data]
        extra = [k for k in data if k not in keys[t] and k != "_source_id"]
        if extra:
            bad.append((base, f"klíče mimo schéma: {', '.join(extra)}"))
            continue
        if missing:
            for k in missing:
                data[k] = None
            json.dump(data, open(o, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        ok += 1
    return ok, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--tasks", help="složka pro zadání agentům (jen dokumenty bez výstupu)")
    ap.add_argument("--check", action="store_true", help="ověřit hotové výstupy")
    ap.add_argument("--redo", action="store_true", help="zadání i pro dokumenty, které výstup už mají")
    a = ap.parse_args()

    system, keys, shape = load_prompts()
    if os.path.isdir(a.out_dir):
        r = realign(a.in_dir, a.out_dir)
        if r["moved"] or r["stale"]:
            print(f"· výstupy srovnány podle adresy: přesunuto {r['moved']}, odloženo {r['stale']}")
    if a.tasks:
        paths = pending(a.in_dir, a.out_dir, a.redo)
        os.makedirs(a.out_dir, exist_ok=True)
        n = write_tasks(paths, a.tasks, a.out_dir, system, keys, shape)
        print(f"· {n} zadání v {a.tasks} (výstupy do {a.out_dir})")
    if a.check:
        ok, bad = check(a.in_dir, a.out_dir, keys)
        print(f"· výstupů v pořádku: {ok}, vadných: {len(bad)}")
        for b, why in bad:
            print(f"  ✗ {b}: {why}")
        return 1 if bad else 0
    if not a.tasks:
        print(f"· bez výstupu: {len(pending(a.in_dir, a.out_dir))} dokumentů")
    return 0


if __name__ == "__main__":
    sys.exit(main())
