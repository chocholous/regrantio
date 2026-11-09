#!/usr/bin/env python3
"""Jednorázová oprava: starým výstupům modelu najde jejich výzvu (2026-11-08).

⚠ PROČ. Výstupy vrstvy 2 (`data/<zdroj>_out/grant_NN.json`) se párovaly se
vstupy podle čísla v názvu souboru. Vstupy se ale při každé obnově číslují
znovu podle pořadí na webu, takže po přidání výzvy se výstupy posunuly
o jednu a katalog dostal cizí název, lhůtu i podmínky (SFAV, SFŽP, MPSV,
Nadační fond Albert…). Od opravy nese každý výstup `_source_id` a spojí se
jen se svým vstupem (`extract_api.is_done`, `ingest_rich`).

Tenhle skript převede staré výstupy bez `_source_id`: ke každému najde vstup
podle kódu výzvy v názvu, jinak podle toho, kolik z názvu, který model napsal,
najde v textu dokumentu (kmeny slov vážené vzácností v rámci zdroje; slovo,
které má každý dokument zdroje, nerozhoduje). Název ze seznamu na webu bývá
krátký („Cyklostezky“), model píše plný, proto se nesrovnávají jen názvy.
Pár bere jen jednoznačný:
  · kód výzvy v názvu sedí (výstup s kódem, který žádný vstup nemá, je výzva,
    která z webu zmizela → odložit);
  · název je týž (bez diakritiky a velikosti písmen);
  · shoda názvů i pokrytí textu ukazují na týž dokument;
  · jeden signál jasně (názvy ≥ 0,4 o 0,15, text ≥ 0,5 o 0,2) a druhý
    jasně neukazuje jinam. Rozcestník („Státní fond audiovize“) obsahuje slova
    všech výzev, proto text sám nestačí, když názvy míří jinam.
Co se spárovat nedá, odloží do `data/<zdroj>_out_stale/` — vstup pak čeká na
nové přečtení (`extract_manual.py --tasks`). Nic se nemaže.

    python scripts/pair_model_outputs.py            # nanečisto, vypíše páry
    python scripts/pair_model_outputs.py --apply
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refresh_run import MODEL_SOURCES  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CODE = re.compile(r"(\d{2}_\d{2}_\d{3}|\d{4}-[A-Z]-[\d-]+\d|\d{1,2}\s*/\s*\d{4}\s*[A-Z]{2,})")


def _fold(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def words(s):
    return {w for w in re.findall(r"\w+", _fold(s)) if len(w) > 3}


def stems(s):
    """Kmeny slov: čeština skloňuje (údržba, údržbu), pět písmen stačí."""
    return {w[:5] for w in re.findall(r"\w+", _fold(s)) if len(w) > 3 or w.isdigit()}


def doc_stems(d):
    return stems(" ".join([d.get("title") or "", d.get("body") or "", (d.get("attachments_md") or "")[:40000]]))


def code(s):
    m = CODE.search(s or "")
    return re.sub(r"\s+", "", m.group(1)) if m else None


def pair_source(slug):
    in_dir, out_dir = f"data/{slug}_in", f"data/{slug}_out"
    ins = {}
    for p in sorted(glob.glob(f"{in_dir}/grant_*.json")):
        d = json.load(open(p, encoding="utf-8"))
        ins[os.path.basename(p)] = d
    outs = {}
    for p in sorted(glob.glob(f"{out_dir}/grant_*.json")):
        d = json.load(open(p, encoding="utf-8"))
        outs[os.path.basename(p)] = d
    import math
    dstem = {ib: doc_stems(d) for ib, d in ins.items()}
    n = max(len(ins), 1)
    df = {}
    for st in dstem.values():
        for w in st:
            df[w] = df.get(w, 0) + 1

    def idf(w):
        return math.log((n + 1) / (df.get(w, 0) + 0.5))

    def cover(t_out, ib):
        ws = [w for w in stems(t_out) if idf(w) > 0.05]
        tot = sum(idf(w) for w in ws)
        return sum(idf(w) for w in ws if w in dstem[ib]) / tot if tot else 0.0

    # názvy: totéž vážení, ale vzácnost mezi názvy vstupů („chorvatsko“
    # rozhoduje, „Výzva pro podávání“ ne)
    tstem = {ib: stems(d.get("title") or "") for ib, d in ins.items()}
    tdf = {}
    for st in tstem.values():
        for w in st:
            tdf[w] = tdf.get(w, 0) + 1

    def tidf(w):
        return math.log((n + 1) / (tdf.get(w, 0) + 0.5))

    def tsim(t_out, ib):
        # slova, která nemá žádný název vstupu, jsou upřesnění modelu
        # („– podpora průmyslového výzkumu…“), ne rozlišení mezi vstupy
        a, b = {w for w in stems(t_out) if w in tdf}, tstem[ib]
        den = sum(tidf(w) for w in a | b)
        return sum(tidf(w) for w in a & b) / den if den else 0.0

    pairs, stale, taken = {}, [], set()
    # už spárované (nový tvar) zůstávají, kde patří
    for ob, od in outs.items():
        sid = od.get("_source_id")
        if sid:
            hit = [ib for ib, idoc in ins.items() if idoc.get("id") == sid]
            if hit:
                pairs[ob] = (hit[0], "id")
                taken.add(hit[0])
            else:
                stale.append(ob)
    in_codes = {ib: code(d.get("title") or "") for ib, d in ins.items()}

    def pick(scored, floor, margin):
        scored = sorted(scored, reverse=True)
        if not scored:
            return None, 0.0, False
        best, second = scored[0], (scored[1][0] if len(scored) > 1 else 0.0)
        return best[1], best[0], best[0] >= floor and best[0] - second >= margin

    for ob, od in outs.items():
        if ob in pairs or ob in stale:
            continue
        t_out = od.get("title") or ""
        c_out = code(t_out)
        free = [ib for ib in ins if ib not in taken]
        if c_out:
            hit = [ib for ib in free if in_codes[ib] == c_out]
            if len(hit) == 1:
                pairs[ob] = (hit[0], "kód")
                taken.add(hit[0])
                continue
            if len(hit) > 1:
                free = hit  # týž kód má víc vstupů (SFŽP „2/2024 FN“ dvakrát) → mezi nimi rozhodne název
            elif not any(c == c_out for c in in_codes.values()) and any(in_codes.values()):
                stale.append(ob)
                continue
        same = [ib for ib in free if words(ins[ib].get("title") or "") == words(t_out)]
        if len(same) == 1:
            pairs[ob] = (same[0], "týž název")
            taken.add(same[0])
            continue
        j_ib, j_s, j_ok = pick([(tsim(t_out, ib), ib) for ib in free], 0.4, 0.15)
        c_ib, c_s, c_ok = pick([(cover(t_out, ib), ib) for ib in free], 0.5, 0.2)
        j_says = j_ib if j_s >= 0.25 else None
        c_says = c_ib if c_s >= 0.5 else None
        choice, how = None, ""
        if j_says and j_says == c_says:
            choice, how = j_says, f"oba {j_s:.2f}·{c_s:.2f}"
        elif j_ok and not (c_ok and c_ib != j_ib):
            choice, how = j_ib, f"názvy {j_s:.2f}"
        elif c_ok and not (j_ok and j_ib != c_ib) and j_says in (None, c_ib):
            choice, how = c_ib, f"text {c_s:.2f}"
        if choice:
            pairs[ob] = (choice, how)
            taken.add(choice)
        else:
            stale.append(ob)
    return ins, outs, pairs, stale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    total_ok = total_stale = total_moved = 0
    for slug in sorted(MODEL_SOURCES):
        if not os.path.isdir(f"data/{slug}_in"):
            continue
        ins, outs, pairs, stale = pair_source(slug)
        moved = sum(1 for ob, (ib, _) in pairs.items() if ob != ib)
        print(f"{slug:14} vstupů {len(ins):3}  výstupů {len(outs):3}  spárováno {len(pairs):3} (přesunuto {moved})  odloženo {len(stale)}")
        for ob, (ib, how) in sorted(pairs.items()):
            if ob != ib:
                print(f"   {ob} → {ib}  [{how}]  „{(outs[ob].get('title') or '')[:46]}“ ~ „{(ins[ib].get('title') or '')[:46]}“")
        for ob in stale:
            print(f"   ✗ {ob} odložen  „{(outs[ob].get('title') or '')[:60]}“")
        total_ok += len(pairs)
        total_stale += len(stale)
        total_moved += moved
        if a.apply:
            out_dir, stale_dir = f"data/{slug}_out", f"data/{slug}_out_stale"
            staged = {}
            for ob, (ib, _) in pairs.items():
                d = dict(outs[ob])
                d["_source_id"] = ins[ib].get("id")
                staged[ib] = d
            if stale:
                os.makedirs(stale_dir, exist_ok=True)
                for ob in stale:
                    shutil.copy2(os.path.join(out_dir, ob), os.path.join(stale_dir, ob))
            for p in glob.glob(f"{out_dir}/grant_*.json"):
                os.remove(p)
            for ib, d in staged.items():
                json.dump(d, open(os.path.join(out_dir, ib), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\ncelkem spárováno {total_ok} (z toho přesunuto {total_moved}), odloženo {total_stale}"
          + ("" if a.apply else "  · nanečisto, nic se nezměnilo"))


if __name__ == "__main__":
    main()
