#!/usr/bin/env python3
"""Univerzální doc → MARKDOWN (vrstva 1 / fáze 2). Nahrazuje pdftotext/textutil .txt.

Routing (ověřeno empiricky — viz proč u každého):
  pdf (s textem)     → docling CPU (do_ocr=False, tabulky on)
  pdf (sken)         → docling CPU + OcrMacOptions(force_full_page_ocr=True)   # ocrmac = Apple Vision
  docx, pptx         → docling CPU
  xls, xlsx, ods     → soffice → CSV ve fenced bloku   # docling md-tabulky mrší slučované buňky + .xls neumí
  doc, odt, rtf      → soffice → docx → docling          # docling legacy formáty neumí

CPU je VYNUCENO: docling layout model padá na Apple MPS (float64 nepodporováno;
PYTORCH_ENABLE_MPS_FALLBACK ten TypeError nezachytí). CPU = 0.4 s/strana, korektní.

Výstup: vedle <sha>.<ext> vznikne <sha>.md; manifest dostane md_path/md_chars/md_method.
Paralelní batch (--workers); každý proces 1× načte docling model (amortizace), torch 1 vlákno/proces.
Soffice běží s per-task UserInstallation profilem (žádný single-instance lock).

Spuštění:
  python3 scripts/to_markdown.py                       # vše z manifestu (ok + raw na disku)
  python3 scripts/to_markdown.py --only pdf --limit 5  # test
  python3 scripts/to_markdown.py --workers 16
"""
import argparse, json, os, re, subprocess, sys, tempfile, zipfile
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limits import L

MANIFEST = "data/files/manifest.jsonl"
ROUTABLE = {"pdf", "docx", "pptx", "xls", "xlsx", "ods", "doc", "odt", "rtf"}
_CONV = {}   # per-proces cache docling converterů dle ocr příznaku
_PATCHED = False


def _patch_rtdetr_float32():
    """RT-DETR-v2 poziční embedding (transformers) tvoří omega/grid jako float64 →
    MPS padá (float64 nepodporuje) a PYTORCH_ENABLE_MPS_FALLBACK to nezachytí (tvrdá konverze dtype).
    Přepíšeme na float32 — výstup se stejně castuje na float32, numericky neškodné i pro CPU.
    Pozn.: pro BATCH stejně jedeme CPU (6 paralelních workerů > 1 sdílená GPU); patch umožní MPS pro single-dok."""
    global _PATCHED
    if _PATCHED:
        return
    try:
        import torch
        from transformers.models.rt_detr_v2 import modeling_rt_detr_v2 as M

        def build_pe(height, width, embed_dim=256, temperature=10000.0, cls_token=False, device=None, dtype=torch.float32):
            pos_dim = embed_dim // 4
            omega = torch.arange(pos_dim, dtype=torch.float32, device=device) / pos_dim
            omega = 1.0 / temperature ** omega
            gh = torch.arange(height, dtype=torch.float32, device=device)
            gw = torch.arange(width, dtype=torch.float32, device=device)
            gh, gw = torch.meshgrid(gh, gw, indexing="ij")
            emb_h = gh.flatten().outer(omega)
            emb_w = gw.flatten().outer(omega)
            pe = torch.cat([emb_h.sin(), emb_h.cos(), emb_w.sin(), emb_w.cos()], dim=1)
            if cls_token:
                pe = torch.cat([torch.zeros(1, embed_dim, dtype=torch.float32, device=device), pe], dim=0)
            return pe.to(dtype)

        M.build_2d_sinusoidal_position_embedding = build_pe
        _PATCHED = True
    except Exception:
        pass


def _converter(ocr):
    key = bool(ocr)
    if key in _CONV:
        return _CONV[key]
    _patch_rtdetr_float32()
    import torch
    torch.set_num_threads(1)
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    try:
        from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
    except Exception:
        from docling.datamodel.pipeline_options import AcceleratorOptions, AcceleratorDevice
    dev = {"cpu": AcceleratorDevice.CPU, "mps": AcceleratorDevice.MPS,
           "cuda": AcceleratorDevice.CUDA}.get(os.environ.get("DOCLING_DEVICE", "cpu"), AcceleratorDevice.CPU)
    po = PdfPipelineOptions()
    po.do_table_structure = True
    po.accelerator_options = AcceleratorOptions(device=dev)
    if ocr:
        from docling.datamodel.pipeline_options import OcrMacOptions
        po.do_ocr = True
        po.ocr_options = OcrMacOptions(force_full_page_ocr=True)
    else:
        po.do_ocr = False
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=po)})
    _CONV[key] = conv
    return conv


def pdf_is_scanned(raw):
    """Probe: pdftotext → málo znaků/strana = sken (bez textové vrstvy) → OCR."""
    try:
        txt = subprocess.run(["pdftotext", "-q", raw, "-"], capture_output=True, timeout=90).stdout
        txt = txt.decode("utf-8", "replace")
    except Exception:
        return True
    info = subprocess.run(["pdfinfo", raw], capture_output=True, text=True).stdout
    m = re.search(r"Pages:\s+(\d+)", info)
    pages = int(m.group(1)) if m else 1
    return len(txt.strip()) < pages * L("probe.scanned_pdf_min_chars_per_page")


def soffice_csv(raw, ext, wd):
    out = os.path.join(wd, "out"); os.makedirs(out, exist_ok=True)
    prof = f"file://{wd}/lo_profile"
    subprocess.run(["soffice", "--headless", f"-env:UserInstallation={prof}",
                    "--convert-to", "csv", "--outdir", out, raw],
                   capture_output=True, timeout=180)
    csvs = [f for f in os.listdir(out) if f.endswith(".csv")]
    if not csvs:
        return None, "soffice-no-csv"
    csv_text = open(os.path.join(out, csvs[0]), encoding="utf-8", errors="replace").read().strip()
    note = ""
    if ext == "xlsx":   # CSV nese jen 1. list — když je listů víc, NAHLAS (no silent truncation)
        try:
            with zipfile.ZipFile(raw) as z:
                sheets = [n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml", n)]
            if len(sheets) > 1:
                note = f"\n\n> ⚠ workbook má {len(sheets)} listů; CSV obsahuje jen první (soffice --convert-to csv limit)\n"
        except Exception:
            pass
    return f"```csv\n{csv_text}\n```{note}", "soffice_csv"


def office_via_docx(raw, ext, wd):
    out = os.path.join(wd, "docx"); os.makedirs(out, exist_ok=True)
    prof = f"file://{wd}/lo_profile"
    subprocess.run(["soffice", "--headless", f"-env:UserInstallation={prof}",
                    "--convert-to", "docx", "--outdir", out, raw],
                   capture_output=True, timeout=180)
    docxs = [f for f in os.listdir(out) if f.endswith(".docx")]
    if not docxs:
        return None, "soffice-no-docx"
    md = _converter(False).convert(os.path.join(out, docxs[0])).document.export_to_markdown()
    return md, "soffice_docx+docling"


def _pdf_summary(raw, sz):
    """Velký NE-grantový dokument (kniha/manuál/přednáška): neukládej celý, jen shrnutí —
    titul + 1. strana (identifikace) + metadata + ukazatel na plný soubor. Bez OCR."""
    info = subprocess.run(["pdfinfo", raw], capture_output=True, text=True).stdout
    pm = re.search(r"Pages:\s+(\d+)", info)
    tm = re.search(r"Title:\s+(.+)", info)
    pages = pm.group(1) if pm else "?"
    first = subprocess.run(["pdftotext", "-q", "-l", "1", raw, "-"], capture_output=True, timeout=120).stdout
    first = first.decode("utf-8", "replace").strip()
    head = f"> ⚠ Velký dokument ({sz/1e6:.0f} MB, {pages} stran) — uloženo jen shrnutí (titul + 1. strana). Plný soubor: {raw}\n"
    if tm and tm.group(1).strip():
        head += f">\n> Titul: {tm.group(1).strip()}\n"
    return head + "\n" + (first or "_(1. strana bez textové vrstvy — obrázkové PDF)_")


def to_md(raw, ext):
    ext = (ext or "").lower()
    if ext == "pdf":
        summary_mb = float(os.environ.get("PDF_SUMMARY_MB", "0") or 0)
        sz = os.path.getsize(raw)
        if summary_mb > 0 and sz >= summary_mb * 1_000_000:
            return _pdf_summary(raw, sz), "summary_large"
        ocr = pdf_is_scanned(raw)
        fast_mb = float(os.environ.get("PDF_FAST_MB", "0") or 0)
        # velké TEXTOVÉ PDF (prezentace/e-knihy/nařízení/velké zprávy): docling layout tabulkově nepřidá,
        # jen žere čas → rychlý pdftotext→text. Skeny (ocr) musí zůstat na docling+ocrmac.
        if fast_mb > 0 and not ocr and os.path.getsize(raw) >= fast_mb * 1_000_000:
            txt = subprocess.run(["pdftotext", "-q", raw, "-"], capture_output=True, timeout=180).stdout
            txt = txt.decode("utf-8", "replace").strip()
            if txt:
                return txt, "pdftotext_fast"
            # prázdný výstup → přece jen sken, spadni na docling OCR
            ocr = True
        md = _converter(ocr).convert(raw).document.export_to_markdown()
        return md, ("docling_ocr" if ocr else "docling")
    if ext in ("docx", "pptx"):
        return _converter(False).convert(raw).document.export_to_markdown(), "docling"
    with tempfile.TemporaryDirectory() as wd:
        if ext in ("xls", "xlsx", "ods"):
            return soffice_csv(raw, ext, wd)
        if ext in ("doc", "odt", "rtf"):
            return office_via_docx(raw, ext, wd)
    return None, f"no-route-{ext}"


def _task(arg):
    url, raw, ext = arg
    md_path = os.path.splitext(raw)[0] + ".md"
    try:
        md, method = to_md(raw, ext)
        if md is None:
            return {"url": url, "md_ok": False, "md_method": method}
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md)
        return {"url": url, "md_ok": True, "md_path": md_path, "md_chars": len(md), "md_method": method}
    except Exception as e:  # noqa: BLE001
        return {"url": url, "md_ok": False, "md_method": f"{type(e).__name__}: {str(e)[:90]}"}


def _init():
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[v] = "1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=MANIFEST)
    ap.add_argument("--workers", type=int, default=L("http.download_workers"))
    ap.add_argument("--only", help="jen daná přípona (test)")
    ap.add_argument("--limit", type=int, help="max N souborů (test)")
    ap.add_argument("--skip-existing", action="store_true", help="přeskoč soubory s už existujícím neprázdným .md (resume)")
    ap.add_argument("--device", default="cpu", choices=["cpu", "mps", "cuda"],
                    help="docling accelerator (default cpu; mps funguje díky float32 patchi, ale pro BATCH je 6 CPU workerů rychlejší)")
    ap.add_argument("--pdf-fast-mb", type=float, default=0,
                    help="textové PDF >= N MB konvertuj rychle pdftotext→text místo docling (0=vyp; skeny vždy docling OCR)")
    ap.add_argument("--pdf-summary-mb", type=float, default=0,
                    help="PDF >= N MB neukládej celé, jen shrnutí (titul+1.strana); knihy/manuály/přednášky (0=vyp)")
    args = ap.parse_args()
    os.environ["DOCLING_DEVICE"] = args.device
    os.environ["PDF_FAST_MB"] = str(args.pdf_fast_mb)
    os.environ["PDF_SUMMARY_MB"] = str(args.pdf_summary_mb)

    import hashlib
    entries = [json.loads(l) for l in open(args.manifest, encoding="utf-8")]
    # 1) všechny routable (url,raw,ext), dedup URL
    routable, seen = [], set()
    for e in entries:
        raw, ext, url = e.get("raw_path"), (e.get("ext") or "").lower(), e.get("url")
        if not (e.get("ok") and raw and os.path.exists(raw) and ext in ROUTABLE):
            continue
        if args.only and ext != args.only:
            continue
        if url in seen:
            continue
        seen.add(url)
        routable.append((url, raw, ext))

    # 2) dedup dle OBSAHU (sha souboru): identický obsah konvertuj 1×, ostatní → reprezentant
    def _fh(p):
        try:
            with open(p, "rb") as f:
                return hashlib.sha1(f.read()).hexdigest()
        except Exception:
            return None
    rep_by_hash, dup_to_rep, uniq = {}, {}, []
    for t in routable:
        h = _fh(t[1])
        if h is None:
            uniq.append(t)
        elif h in rep_by_hash:
            dup_to_rep[t[0]] = rep_by_hash[h][0]   # url → rep_url
        else:
            rep_by_hash[h] = t
            uniq.append(t)

    # 3) ke konverzi jen reprezentanti bez .md; ŘAZENÍ: nejmenší první, giganti NAKONEC
    tasks = []
    sum_mb = args.pdf_summary_mb
    for t in uniq:
        mp = os.path.splitext(t[1])[0] + ".md"
        # velké PDF na shrnutí: NEpřeskakuj (přepiš případný starý plný .md shrnutím)
        force = (t[2] == "pdf" and sum_mb > 0 and os.path.getsize(t[1]) >= sum_mb * 1_000_000)
        if args.skip_existing and not force and os.path.exists(mp) and os.path.getsize(mp) > 0:
            continue
        tasks.append(t)
    tasks.sort(key=lambda t: os.path.getsize(t[1]))   # malé první, obří PDF nakonec
    if args.limit:
        tasks = tasks[:args.limit]
    print(f"routable={len(routable)}, unikátních obsahů={len(uniq)}, dup→rep={len(dup_to_rep)}, "
          f"ke konverzi={len(tasks)}, workers={args.workers}", file=sys.stderr)

    results = {}
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init) as ex:
        for r in ex.map(_task, tasks):
            results[r["url"]] = r
            done += 1
            if done % 50 == 0:
                print(f"  ... {done}/{len(tasks)}", file=sys.stderr)

    raw_by_url = {u: rw for (u, rw, _x) in routable}

    def _rep_md(rep_url):
        r = results.get(rep_url)
        if r and r.get("md_ok"):
            return r["md_path"], r.get("md_chars")
        mp = os.path.splitext(raw_by_url.get(rep_url, "x"))[0] + ".md"
        return (mp, os.path.getsize(mp)) if os.path.exists(mp) and os.path.getsize(mp) > 0 else (None, None)

    # zapiš md_* zpět do manifestu (zachovej .txt pole)
    for e in entries:
        url = e.get("url")
        r = results.get(url)
        if r:
            for k in ("md_path", "md_chars", "md_method"):
                if k in r:
                    e[k] = r[k]
            e["md_ok"] = r["md_ok"]
            continue
        if url in dup_to_rep:                        # bajtově identické → ukaž na .md reprezentanta
            mp, ch = _rep_md(dup_to_rep[url])
            if mp:
                e["md_path"], e["md_chars"], e["md_method"], e["md_ok"] = mp, ch, "dup_content", True
            continue
        raw = e.get("raw_path")                      # backfill z disku (dřívější běh)
        if raw and not e.get("md_ok"):
            mp = os.path.splitext(raw)[0] + ".md"
            if os.path.exists(mp) and os.path.getsize(mp) > 0:
                e["md_path"] = mp
                e["md_chars"] = os.path.getsize(mp)
                e["md_method"] = e.get("md_method") or "prior_run"
                e["md_ok"] = True
    with open(args.manifest, "w", encoding="utf-8") as o:
        for e in entries:
            o.write(json.dumps(e, ensure_ascii=False) + "\n")

    import collections
    by_method = collections.Counter(r["md_method"].split(":")[0] for r in results.values() if r["md_ok"])
    fails = [r for r in results.values() if not r["md_ok"]]
    total_md = sum(r.get("md_chars", 0) for r in results.values() if r["md_ok"])
    print(json.dumps({"MARKER": "TO_MARKDOWN", "converted": len(results) - len(fails),
                      "failed": len(fails), "total_md_mb": round(total_md / 1e6, 1),
                      "by_method": dict(by_method),
                      "fail_sample": [{"url": f["url"][-50:], "why": f["md_method"]} for f in fails[:10]]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
