#!/usr/bin/env python3
"""Vrstva 2 (model) přes Claude API — spustitelná ze skriptu, ne jen z Claude Code.

⚠ PROČ TENHLE SKRIPT EXISTUJE (2026‑09‑11). Extrakce polí z plného textu
výzvy (`workflows/extract_wf.js`) běžela JEN jako workflow uvnitř Claude Code:
agent s nástroji Read/Write, spouštěný ručně v sezení. Důsledek pro produkt:
bez modelu se obnovuje 28 zdrojů ze 135 (`refresh_run.py`), zbylých ~100 má
razítko z června 2026 nebo žádné a jejich stárnutí zakrývá jen to, že status
počítá kód. Katalog, jehož dvě třetiny se nedají obnovit bez lidského sezení,
není produkční zdroj dat.

Tohle je TÁŽ extrakce jako ve workflow — týž prompt, týž seznam klíčů, týž
tvar vnořených objektů, týž výstup (`<out-dir>/<basename>.json` pro
`ingest_rich.py`) — jen volaná přes Messages API, takže ji může pustit
`refresh_run.py` v GitHub Actions.

⚠ PROMPT SE ČTE Z `workflows/extract_wf.js`, NE Z KOPIE. `prompts/extract_grant.md`
už jednou zaostal o celou revizi za inline promptem workflow, přesně jak tam
stojí. Dvě místa pravdy o tom, jak se čte výzva, by se rozešla znovu; proto
se `COMMON`, `SYS` a `SCHEMAS` parsují z JS zdroje. Když se v JS změní tvar
těch bloků, tenhle skript to ohlásí hned na startu, ne tichou odchylkou.

Bez `ANTHROPIC_API_KEY` skript skončí kódem 2 a řekne to; nic nepředstírá.

    python scripts/extract_api.py --in-dir data/esfcr_in --out-dir data/esfcr_out --dry-run
    python scripts/extract_api.py --in-dir data/esfcr_in --out-dir data/esfcr_out --limit 3   # sonda
    python scripts/extract_api.py --in-dir data/esfcr_in --out-dir data/esfcr_out            # celý zdroj

Pak jako dřív:  python scripts/ingest_rich.py --out-dir data/esfcr_out --src data/esfcr_in
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse
import concurrent.futures
import glob
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(ROOT, "workflows", "extract_wf.js")

# Výchozí model: Sonnet 5. Workflow měl `sonnet` (Haiku na bohatém schématu
# malformoval), Opus 5 je přesnější, ale výzva má i 150 000 znaků příloh
# a zdroj jich má stovky — volba je v ceně; přepíná `--model`.
DEFAULT_MODEL = "claude-sonnet-5"
MAX_OUTPUT_TOKENS = 16000


class WorkflowDrift(RuntimeError):
    """Tvar `extract_wf.js` se změnil a prompt se z něj nedá přečíst."""


def load_prompts():
    """COMMON + SYS + klíče + tvar vnořených objektů — z JS, ne z kopie."""
    js = open(WORKFLOW, encoding="utf-8").read()
    m = re.search(r"const COMMON = `(.*?)`\n", js, re.S)
    if not m:
        raise WorkflowDrift("COMMON")
    common = m.group(1)
    m = re.search(r"const SYS = \{\n  grant: `(.*?)`,\n\n  foundation_mission: `(.*?)`,\n\}", js, re.S)
    if not m:
        raise WorkflowDrift("SYS")
    system = {
        "grant": m.group(1).replace("${COMMON}", common),
        "foundation_mission": m.group(2).replace("${COMMON}", common),
    }

    def block(name, nxt):
        mm = re.search(r"  " + name + r": \{\n    type: 'object'.*?\n    properties: \{\n(.*?)\n    \},\n  \},\n" + nxt, js, re.S)
        if not mm:
            raise WorkflowDrift(f"SCHEMAS.{name}")
        return mm.group(1)

    blocks = {"grant": block("grant", "  foundation_mission"), "foundation_mission": block("foundation_mission", r"\}")}
    keys, shape = {}, {}
    for t, b in blocks.items():
        keys[t] = re.findall(r"^\s{6}(\w+): \{", b, re.M)
        parts = []
        for pm in re.finditer(r"^\s{6}(\w+): \{(.*?)(?=^\s{6}\w+: \{|\Z)", b, re.S | re.M):
            k, body = pm.group(1), pm.group(2)
            nested = re.search(r"properties: \{(.*)", body, re.S)
            if nested and k != "evidence":
                sub = re.findall(r"(\w+): \{ type", nested.group(1))
                arr = "[]" if "type: 'array'" in body.split("properties")[0] else ""
                parts.append(f"{k}{arr}={{{','.join(sub)}}}")
        shape[t] = "; ".join(parts)
    if "title" not in keys["grant"] or "evidence" not in keys["grant"]:
        raise WorkflowDrift("KEYS.grant")
    return system, keys, shape


def type_of(path: str) -> str:
    return "foundation_mission" if os.path.basename(path).startswith("mission_") else "grant"


def user_message(doc: dict, t: str, keys: list, shape: str) -> str:
    """Totéž zadání jako ve workflow, jen dokument je v textu místo v souboru pro Read."""
    parts = [f"# title\n{doc.get('title') or ''}", f"# body\n{doc.get('body') or ''}"]
    if doc.get("attachments_md"):
        parts.append(f"# attachments_md\n{doc['attachments_md']}")
    if doc.get("related_context"):
        parts.append(f"# related_context\n{doc['related_context']}")
    parts.append(
        f"Sestav JEDEN JSON objekt se VŠEMI klíči (chybějící hodnota = null nebo []): {', '.join(keys)}.\n"
        f"Tvar vnořených objektů (PŘESNĚ tyto klíče, nic nepřejmenovávej): {shape}. evidence={{nazev_pole: doslovná citace}}.\n"
        "Odpověz POUZE tím JSON objektem — žádný ```json fence, žádný komentář, jen syrový JSON, UTF-8 s diakritikou."
    )
    return "\n\n".join(parts)


def parse_json(text: str):
    """Model má vrátit syrový JSON; fence nebo věta okolo se odřízne, zbytek je chyba."""
    s = text.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    a, b = s.find("{"), s.rfind("}")
    if a == -1 or b == -1:
        raise ValueError("bez JSON objektu")
    return json.loads(s[a : b + 1])


def extract_one(client, model: str, path: str, out_dir: str, system: dict, keys: dict, shape: dict) -> dict:
    t = type_of(path)
    doc = json.load(open(path, encoding="utf-8"))
    out_path = os.path.join(out_dir, os.path.basename(path))
    started = time.time()
    with client.messages.stream(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        thinking={"type": "adaptive"},
        system=system[t],
        messages=[{"role": "user", "content": user_message(doc, t, keys[t], shape[t])}],
    ) as stream:
        final = stream.get_final_message()
    text = "".join(b.text for b in final.content if getattr(b, "type", "") == "text")
    usage = getattr(final, "usage", None)
    try:
        data = parse_json(text)
    except (ValueError, json.JSONDecodeError) as e:
        # Syrová odpověď zůstane vedle (`.raw.txt`) k ručnímu rozboru; do výstupu se
        # nepíše nic, co není JSON, aby `ingest_rich` nedostal půlku záznamu.
        # (Dávková oprava `repair_out.py` odešla s úklidem `b17cdfa`.)
        open(out_path + ".raw.txt", "w", encoding="utf-8").write(text)
        return {"path": path, "ok": False, "error": f"neplatný JSON: {e}", "seconds": round(time.time() - started, 1)}
    missing = [k for k in keys[t] if k not in data]
    for k in missing:
        data[k] = None
    data["_source_id"] = doc.get("id")
    json.dump(data, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return {
        "path": path,
        "ok": True,
        "missing_keys": missing,
        "seconds": round(time.time() - started, 1),
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }


def is_done(in_path: str, out_dir: str) -> bool:
    """Výstup existuje A patří k témuž dokumentu (`_source_id` = id vstupu).

    Vstupy se při obnově číslují znovu podle pořadí, takže samotná existence
    souboru `grant_07.json` neříká nic o tom, ke které výzvě patří (2026-11-08)."""
    out = os.path.join(out_dir, os.path.basename(in_path))
    if not os.path.exists(out):
        return False
    try:
        data = json.load(open(out, encoding="utf-8"))
        doc = json.load(open(in_path, encoding="utf-8"))
    except (ValueError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict) or not data.get("_source_id") or data["_source_id"] != doc.get("id"):
        return False
    return still_valid(data, doc)


# Pole, na kterých stojí rozhodnutí uživatele: kdy žádat a kolik.
KEY_FIELDS = ("deadline", "open_from", "vyse_hlavni_czk")


def _squash(s: str) -> str:
    return "".join((s or "").lower().split())


def still_valid(data: dict, doc: dict) -> bool:
    """Výstup platí, dokud citace jeho klíčových polí stojí v DNEŠNÍM dokumentu.

    ⚠ NAMĚŘENO 2026-11-09: 12 ze 110 výstupů ze září neslo lhůtu nebo částku,
    kterou dnešní stránka už neuváděla — SFŽP prodloužil brownfieldy do
    29. 1. 2027, RES+ naopak zkrátil na 30. 11. 2026, KOMUNERG o rok. Výstup
    byl správně spárovaný, jen ze starší verze stránky. Kde citace zmizela,
    dokument se čte znovu; obnova tak stojí úměrně změnám, ne velikosti zdroje.
    Rozcestník (`_skip`) citace nemá a platí."""
    if data.get("_skip"):
        return True
    text = _squash("\n".join(x for x in (doc.get("title"), doc.get("body"), doc.get("attachments_md")) if x))
    ev = data.get("evidence") or {}
    for k in KEY_FIELDS:
        q = ev.get(k) if isinstance(ev, dict) else None
        if data.get(k) in (None, "", []) or not isinstance(q, str):
            continue
        nq = _squash(q)
        if len(nq) < 8 or nq in text:
            continue
        if len(nq) >= 30 and nq[len(nq) // 2 - 14: len(nq) // 2 + 14] in text:
            continue
        return False
    return True


def realign(in_dir: str, out_dir: str) -> dict:
    """Výstupy pod čísla jejich vstupů podle `_source_id` (2026-11-09).

    `build_extract_input` při každé sklizni čísluje vstupy znovu; výstup výzvy,
    která se posunula z `grant_11` na `grant_00`, by jinak ležel pod starým
    číslem, četl by se znovu a přepsal cizí výstup. Výstup, jehož adresu žádný
    vstup nemá (výzva zmizela z webu), jde do `<out>_stale/`; nic se nemaže."""
    import shutil
    by_id = {}
    for p in glob.glob(os.path.join(in_dir, "*.json")):
        if os.path.basename(p) == "paths.json":
            continue
        try:
            by_id.setdefault(json.load(open(p, encoding="utf-8")).get("id"), []).append(os.path.basename(p))
        except (ValueError, json.JSONDecodeError):
            pass
    staged, stale = {}, []
    for p in glob.glob(os.path.join(out_dir, "*.json")):
        base = os.path.basename(p)
        try:
            sid = json.load(open(p, encoding="utf-8")).get("_source_id")
        except (ValueError, json.JSONDecodeError, AttributeError):
            continue
        if not sid:
            continue  # starý tvar bez adresy: nechat, kde je (is_done ho stejně nepočítá)
        kind = base.split("_", 1)[0]
        targets = [b for b in by_id.get(sid, []) if b.split("_", 1)[0] == kind]
        if targets:
            staged[p] = targets[0]
        else:
            stale.append(p)
    stale_dir = out_dir.rstrip("/\\") + "_stale"

    def park(path):
        """Odložit stranou; existující soubor ve `_stale` se nepřepíše."""
        os.makedirs(stale_dir, exist_ok=True)
        stem, ext = os.path.splitext(os.path.basename(path))
        dest, n = os.path.join(stale_dir, stem + ext), 1
        while os.path.exists(dest):
            dest, n = os.path.join(stale_dir, f"{stem}.{n}{ext}"), n + 1
        shutil.move(path, dest)

    for p in stale:  # nejdřív stranou, ať neblokují místa a nepletou se s přesunutými
        park(p)
    tmp = {}
    for p, target in staged.items():
        if os.path.basename(p) != target:
            t = p + ".realign"
            os.replace(p, t)
            tmp[t] = os.path.join(out_dir, target)
    for t, dest in tmp.items():
        if os.path.exists(dest):  # na cílovém místě starý výstup bez adresy → stranou
            park(dest)
        os.replace(t, dest)
    return {"moved": len(tmp), "stale": len(stale)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--in-dir", required=True, help="výstup build_extract_input.py (grant_NNNN.json, mission_NNNN.json)")
    ap.add_argument("--out-dir", required=True, help="kam psát <basename>.json pro ingest_rich.py")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--limit", type=int, default=0, help="SONDA: jen prvních N dokumentů (0 = všechny)")
    ap.add_argument("--workers", type=int, default=4, help="souběžné požadavky")
    ap.add_argument("--redo", action="store_true", help="přepsat i už existující výstupy")
    ap.add_argument("--dry-run", action="store_true", help="spočítat, co by se poslalo; API se nevolá")
    a = ap.parse_args()

    try:
        system, keys, shape = load_prompts()
    except WorkflowDrift as e:
        print(f"✗ workflows/extract_wf.js má jiný tvar, prompt se nedá přečíst: {e}", file=sys.stderr)
        return 1

    if os.path.isdir(a.out_dir) and not a.dry_run:
        r = realign(a.in_dir, a.out_dir)
        if r["moved"] or r["stale"]:
            print(f"· výstupy srovnány podle adresy: přesunuto {r['moved']}, odloženo {r['stale']}")
    paths = sorted(p for p in glob.glob(os.path.join(a.in_dir, "*.json")) if os.path.basename(p) != "paths.json")
    if not a.redo:
        paths = [p for p in paths if not is_done(p, a.out_dir)]
    if a.limit:
        paths = paths[: a.limit]
    chars = 0
    for p in paths:
        d = json.load(open(p, encoding="utf-8"))
        chars += len(d.get("body") or "") + len(d.get("attachments_md") or "") + len(d.get("related_context") or "")
    print(f"· {len(paths)} dokumentů k extrakci, ~{chars / 1e6:.1f} M znaků vstupu, model {a.model}")
    if a.dry_run:
        print("· nasucho: API se nevolá")
        return 0
    if not paths:
        return 0

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("✗ Chybí ANTHROPIC_API_KEY — vrstva 2 přes API není v tomhle prostředí zapnutá. "
              "Skript nic nepředstírá: bez klíče se neextrahuje.", file=sys.stderr)
        return 2
    try:
        import anthropic
    except ImportError:
        print("✗ Chybí balík `anthropic`: pip install -r requirements-model.txt", file=sys.stderr)
        return 2

    os.makedirs(a.out_dir, exist_ok=True)
    client = anthropic.Anthropic(max_retries=3)
    ok = fail = 0
    tin = tout = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        futures = {ex.submit(extract_one, client, a.model, p, a.out_dir, system, keys, shape): p for p in paths}
        for fut in concurrent.futures.as_completed(futures):
            p = futures[fut]
            try:
                r = fut.result()
            except Exception as e:  # síť, limit, model — jeden dokument nesmí shodit dávku
                r = {"path": p, "ok": False, "error": str(e)[:200]}
            if r["ok"]:
                ok += 1
                tin += r.get("input_tokens") or 0
                tout += r.get("output_tokens") or 0
                note = f" (chybělo {len(r['missing_keys'])} klíčů)" if r.get("missing_keys") else ""
                print(f"  ✓ {os.path.basename(p)} {r['seconds']}s{note}")
            else:
                fail += 1
                print(f"  ✗ {os.path.basename(p)}: {r.get('error')}")
    print(f"\nhotovo {ok}/{len(paths)}, selhalo {fail}; tokeny vstup {tin:,} · výstup {tout:,}")
    return 1 if fail and not ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
