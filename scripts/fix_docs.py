#!/usr/bin/env python3
"""Oprava balastních doc-store .txt (vrstva-2 doc-extrakce čte .xls jako syrové byty → šum).

Příčina: dsw2_fetch.py routuje xls/xlsx na macOS `textutil`, který Excel NEUMÍ → 1:1 byty→text =
balast (`}A } , 0 0 0`). Tady to opravíme správným nástrojem dle typu RAW sourozence (.xls vedle .txt
ve stejném sha-adresáři):
  - xls/xlsx → openpyxl/xlrd, VŠECHNY listy (hodonin sešity jsou z 98 % multi-sheet → 1. list nestačí)
  - doc/docx → soffice --headless --convert-to txt:Text (líp než textutil na legacy .doc)
  - pdf      → OCR (pdftoppm → tesseract ces+eng); pdftotext selhal kvůli Identity-H bez ToUnicode

Detekce balastu = podíl znaků mimo {alfanum, whitespace, běžná interpunkce}. Práh je DETEKČNÍ sonda
(ne acquisition limit) → CLI --garbage-threshold. Přepisuje .txt IN PLACE (data/ je gitignored cache;
balast nemá hodnotu). Hlásí počty + garbage PŘED/PO. Suchý běh: --dry-run.

Usage:
  python3 scripts/fix_docs.py [--dirs data/vismo_files data/files data/dsw2_files] [--garbage-threshold 0.20] [--dry-run]
"""
import argparse, glob, os, re, subprocess, sys, tempfile

OK_PUNCT = set('.,;:%()[]-–—/+=@"\'§!?°×#&*<>|~`_')   # _ patří k textu (fill-in čáry ve formulářích), ne balast
RAW_EXTS = ("xlsx", "xls", "docx", "doc", "pdf")   # pořadí = priorita hledání sourozence


def garbage_ratio(s):
    if not s:
        return 0.0
    return sum(1 for c in s if not (c.isalnum() or c.isspace() or c in OK_PUNCT)) / len(s)


def conv_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f"## List: {ws.title}")
        for row in ws.iter_rows(values_only=True):
            cells = [("" if c is None else str(c)) for c in row]
            if any(c.strip() for c in cells):
                out.append("\t".join(cells).rstrip())
    wb.close()
    return "\n".join(out)


def conv_xls(path):
    import xlrd
    wb = xlrd.open_workbook(path)
    out = []
    for sh in wb.sheets():
        out.append(f"## List: {sh.name}")
        for r in range(sh.nrows):
            cells = [("" if v == "" else str(v)) for v in sh.row_values(r)]
            if any(str(c).strip() for c in cells):
                out.append("\t".join(cells).rstrip())
    return "\n".join(out)


def conv_office(path):
    """doc/docx přes soffice → txt."""
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["/opt/homebrew/bin/soffice", "--headless", "--convert-to", "txt:Text",
                        "--outdir", td, path], capture_output=True, timeout=120)
        outs = glob.glob(os.path.join(td, "*.txt"))
        return open(outs[0], encoding="utf-8", errors="replace").read() if outs else ""


def conv_pdf_ocr(path, lang="ces+eng", dpi=200):
    """PDF s rozbitým font-encodingem → rasterizace + tesseract OCR."""
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", path, os.path.join(td, "pg")],
                       capture_output=True, timeout=600)
        pages = sorted(glob.glob(os.path.join(td, "pg*.png")))
        out = []
        for pg in pages:
            # tesseract/leptonica neumí absolutní cestu z tempdiru → cwd=td + basename
            r = subprocess.run(["tesseract", os.path.basename(pg), "-", "-l", lang],
                               capture_output=True, timeout=120, cwd=td)
            out.append(r.stdout.decode("utf-8", "replace"))
        return "\n".join(out)


def find_raw(txt_path):
    base = txt_path.rsplit(".", 1)[0]
    for e in RAW_EXTS:
        if os.path.exists(f"{base}.{e}"):
            return f"{base}.{e}", e
    return None, None


def convert(raw_path, ext):
    if ext == "xlsx":
        return conv_xlsx(raw_path)
    if ext == "xls":
        return conv_xls(raw_path)
    if ext in ("doc", "docx"):
        return conv_office(raw_path)
    if ext == "pdf":
        return conv_pdf_ocr(raw_path)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", default=["data/vismo_files", "data/files", "data/dsw2_files"])
    ap.add_argument("--garbage-threshold", type=float, default=0.20, help="DETEKČNÍ práh (sonda), ne limit")
    ap.add_argument("--min-len", type=int, default=500)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    stat = {e: 0 for e in RAW_EXTS}
    fixed = noraw = failed = still = 0
    fails, noraws = [], []
    for d in a.dirs:
        for tp in glob.glob(d + "/**/*.txt", recursive=True):
            try:
                s = open(tp, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if len(s) < a.min_len or garbage_ratio(s) <= a.garbage_threshold:
                continue
            raw, ext = find_raw(tp)
            if not raw:
                noraw += 1; noraws.append(tp); continue
            try:
                txt = convert(raw, ext)
            except Exception as e:
                failed += 1; fails.append(f"{os.path.basename(raw)}: {e}"); continue
            if not txt or not txt.strip():
                failed += 1; fails.append(f"{os.path.basename(raw)}: prázdný výstup"); continue
            after = garbage_ratio(txt)
            tag = "DRY" if a.dry_run else "FIX"
            if not a.dry_run:
                open(tp, "w", encoding="utf-8").write(txt)
            fixed += 1; stat[ext] += 1
            if after > a.garbage_threshold:
                still += 1
            print(f"  {tag} {ext:4} {os.path.basename(raw):>22}  {len(s):>7}→{len(txt):>7}B  garbage {round(100*garbage_ratio(s))}%→{round(100*after)}%")

    print(f"\nopraveno {fixed} (xlsx={stat['xlsx']} xls={stat['xls']} docx={stat['docx']} doc={stat['doc']} pdf={stat['pdf']})  "
          f"failed={failed} bez_raw={noraw} stále_balast={still}")
    if fails:  print("  FAILED:", "; ".join(fails[:10]))
    if noraws: print("  BEZ RAW:", " ".join(os.path.basename(x) for x in noraws[:10]))


if __name__ == "__main__":
    main()
