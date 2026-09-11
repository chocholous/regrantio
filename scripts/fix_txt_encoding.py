#!/usr/bin/env python3
"""Oprava textů z PDF, které pdftotext na Windows zapsal v Latin‑1.

⚠ CO SE STALO (naměřeno 2026‑09‑11). `pdftotext` bez `-enc UTF-8` používá na
Windows výstupní kódování Latin‑1 a znaky, které v něm nejsou — ř ž ě č š ů
ň ť ď — prostě ZAHODÍ. Z „předkládání žádostí" je „pedkládání zádostí".
Konverze se pak četla jako UTF‑8 s `errors="replace"`, takže do textu přibyly
ještě znaky � za á/é/í (ty Latin‑1 má, ale UTF‑8 je v jednom bajtu nepřečte).

Postihlo to všechno, co se konvertovalo po přechodu na Windows: 3 854 z 8 513
textů v korpusu (esfcr 1 714, hzs 586, czechaid 127, mk 211, plone_ostrava
244, msmt 203, files 727, vismo 39). Vrstva 2 (model) z toho ještě vytěžila
správnou češtinu, deterministické parsery ne: vzor „Příjem žádostí" v takovém
textu nikdy nesedne, a to potichu.

CO DĚLÁ: projde `data/*files*/**/*.txt`, ty, které nejsou platné UTF‑8,
překonvertuje znovu z vedle ležícího originálu (`.pdf`) s `-enc UTF-8`. Text
bez originálu (jen txt) nechá a vypíše — ten se opraví až re‑harvestem.
Idempotentní: opravený soubor je UTF‑8 a podruhé se přeskočí.

    python scripts/fix_txt_encoding.py            # oprav
    python scripts/fix_txt_encoding.py --dry-run  # jen spočítej
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
import argparse
import glob
import os
import subprocess

PDF_EXTS = (".pdf",)


def is_utf8(path: str) -> bool:
    with open(path, "rb") as f:
        raw = f.read()
    try:
        raw.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root", default="data")
    args = ap.parse_args()

    dirs = [p for p in glob.glob(os.path.join(args.root, "*files*")) if os.path.isdir(p)]
    total = bad = fixed = orphan = failed = 0
    for d in sorted(dirs):
        d_bad = d_fixed = 0
        for root, _, files in os.walk(d):
            for name in files:
                if not name.endswith(".txt"):
                    continue
                total += 1
                txt = os.path.join(root, name)
                if is_utf8(txt):
                    continue
                bad += 1
                d_bad += 1
                stem = txt[:-4]
                pdf = next((stem + e for e in PDF_EXTS if os.path.exists(stem + e)), None)
                if not pdf:
                    orphan += 1
                    continue
                if args.dry_run:
                    continue
                r = subprocess.run(["pdftotext", "-q", "-enc", "UTF-8", pdf, txt], timeout=180, check=False)
                if r.returncode == 0 and is_utf8(txt):
                    fixed += 1
                    d_fixed += 1
                else:
                    failed += 1
        if d_bad:
            print(f"{d:32} poškozených {d_bad:5}  opraveno {d_fixed:5}")
    print(f"\ntextů {total}, poškozených {bad}, opraveno {fixed}, bez originálu {orphan}, selhalo {failed}")
    if orphan:
        print("⚠ texty bez originálu se opraví až re-harvestem (originál se stáhne znovu)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
