"""Loader centrálního registru limitů (root limits.json).

PRAVIDLO: žádný limit/ořez/cap natvrdo v kódu — vše přes L('cesta.klic').
Použití:
    from limits import L
    max_pages = L('harvest.praha_max_pages_per_area')   # → 150
    if L('extract_layer2.input_truncation') is None: ...  # žádný ořez
"""
import json, os

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "limits.json")
with open(_PATH, encoding="utf-8") as _f:
    _REG = json.load(_f)


def L(path):
    """Vrať `value` limitu na tečkové cestě (např. 'harvest.eeagrants_max_pages')."""
    cur = _REG
    for key in path.split("."):
        cur = cur[key]
    return cur["value"] if isinstance(cur, dict) and "value" in cur else cur


def meta(path):
    """Vrať celý záznam limitu (value, why, used_in, kind…) pro logování/audit."""
    cur = _REG
    for key in path.split("."):
        cur = cur[key]
    return cur
