#!/usr/bin/env python3
"""Operační program Spravedlivá transformace 2021–2027 (opst.cz) — vrstva 1.

OP ST = EU Fond pro spravedlivou transformaci (Just Transition Fund); řídící orgán MŽP. Podporuje
zmírnění socio-ekonomických a environmentálních dopadů odklonu od uhlí ve 3 uhelných krajích
(Karlovarský, Ústecký, Moravskoslezský): rekvalifikace, nové podnikání, výzkum/inovace, brownfieldy,
čistá energetika, oběhové hospodářství. TÉŽE platforma jako OPŽP (WordPress + CPT `call` + front-end
blok 'Detail výzvy') → REUSE `scripts/opzp.py:harvest_op` beze změny harvest logiky.

Spuštění z kořene repa: python3 scripts/opst.py --out data/opst_documents.jsonl
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opzp import harvest_op

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/opst_documents.jsonl")
    args = ap.parse_args()
    harvest_op("https://opst.cz", "opst.cz", args.out)


if __name__ == "__main__":
    main()
