#!/usr/bin/env python3
"""Karlovy Vary (MĚSTO) harvester — dotační programy statut. města z rozpočtu (Drupal).

ZDROJ: https://mmkv.cz/cs/dotace (Drupal, server-rendered HTML). Stránka NEMÁ per-program
node ani API; je to rozcestník: dotační OBLASTI jsou definované přílohou "Návod - Dotace na/do
<oblast>" (PDF/DOC). Jedna oblast = jeden stálý (každoroční) dotační program z rozpočtu města.
Termíny ani alokace na listing page NEJSOU ("TERMÍNY ... JSOU UVEDENY V JEDNOTLIVÝCH NÁVODECH").

METODA (struktura před prózou):
  1) vrstva 1 — z listing HTML vytáhni odkazy "Návod - Dotace ..." (PDF) → jména programů
     (data-driven, žádný hardcoded seznam oblastí).
  2) vrstva 2 — z každého Návod PDF (pdftotext -layout) parsuj strukturovaná pole:
     oprávněný žadatel (eligible) + podporovaná oblast + text termínu.

POZOR — co zdroj NEDÁVÁ a proč pole zůstávají null:
  - deadline: Návody uvádějí "Termín pro podávání žádostí je do 31.10." — DEN.MĚSÍC bez ROKU
    (každoroční opakující se program). ISO deadline by vyžadoval vymyslet rok → NEDĚLÁME to;
    deadline=null, recurring termín se zachová v popisu (lossless, bez ztráty informace).
  - alokace/max: v Návodech nejsou číselně (řídí se rozpočtem odboru pro daný rok) → null.
  - "Program primátorky" = úřední hodiny primátorky (NE grant) → vyloučeno.
  - "Program regenerace MPZ 2014-2024" = strategický dokument s prošlým rozsahem, bez otevřené
    výzvy/termínu → vyloučeno (není to otevřená dotační výzva).

Lossless: ukládá parsed pole + URL Návod PDF v extra. Status dopočítá ingest (zde null → ingest
spočítá z dat; bez dat → "unknown"). Dedup dle URL+oblasti.

Usage: python3 scripts/kv_mesto_harvest.py --out data/h_mesto_kv.json
"""
import argparse, json, os, re, subprocess, sys, tempfile, urllib.request
import html as _html
import http_util   # jednotná TLS politika (audit #7/#32)

LISTING = "https://mmkv.cz/cs/dotace"
UA = "Mozilla/5.0"
# odkaz na Návod přílohu = definice dotační oblasti/programu (vrstva 1, data-driven)
NAVOD_RE = re.compile(r'href="([^"]+\.pdf)"[^>]*>\s*((?:Návod\s*-\s*)?Dotace[^<]*?)\s*-?\s*pdf', re.I)


def fetch_bytes(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return http_util.urlopen(req, timeout=timeout).read()


def fetch_text(url, timeout=40):
    return fetch_bytes(url, timeout).decode("utf-8", "replace")


def clean_name(s):
    s = _html.unescape(re.sub(r"\s+", " ", s)).strip()
    s = re.sub(r"^Návod\s*-\s*", "", s, flags=re.I).strip()
    return s


def pdf_text(pdf_bytes):
    """pdftotext -layout přes dočasný soubor; vrať text nebo ''."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes); path = f.name
    try:
        r = subprocess.run(["pdftotext", "-layout", path, "-"],
                           capture_output=True, timeout=60)
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""
    except Exception:
        return ""
    finally:
        try: os.unlink(path)
        except OSError: pass


def parse_navod(text):
    """Strukturovaný parse Návod PDF → eligible / oblast / termín-text."""
    t = re.sub(r"[ \t]+", " ", text)
    out = {}
    m = re.search(r"Kdo je oprávněn v této věci jednat\s+(.+?)(?:\n|\s*Žadatel\b|\s*$)", t)
    if not m:
        m = re.search(r"(Fyzické a právnické osoby[^\n]{0,120})", t)
    if m:
        out["eligible"] = re.sub(r'\s*\(dále[^)]*\)\s*$', '', re.sub(r"\s+", " ", m.group(1)).strip()).strip()
    m = re.search(r'podporovaná oblast [„"]([^"“”\n]{3,80})', t)
    if m:
        out["oblast"] = re.sub(r"\s+", " ", m.group(1)).strip()
    m = re.search(r"(Termín pro podávání žádostí[^.\n]*\.(?:\s*\d{1,2}\.)?)", t)
    if m:
        out["termin_text"] = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(".") + "."
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_kv.json")
    a = ap.parse_args()

    out = {"source": "mmkv.cz", "kraj": "Karlovarský kraj", "obec": "Karlovy Vary",
           "uroven": "obec", "platform": "kv_drupal", "programs": []}

    def save():
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    save()  # vytvoř soubor hned (průběžné ukládání)

    html = fetch_text(LISTING)
    seen = set()
    navody = []
    for m in NAVOD_RE.finditer(html):
        url, name = m.group(1), clean_name(m.group(2))
        if url in seen or not name:
            continue
        seen.add(url)
        navody.append((name, url))
    print(json.dumps({"MARKER": "KV_NAVODY_FOUND", "count": len(navody),
                      "names": [n for n, _ in navody]}, ensure_ascii=False), file=sys.stderr)

    seen_prog = set()
    for name, pdf_url in navody:
        rec = {"nazev": name, "open_from": None, "deadline": None, "status": None,
               "alokace_czk": None, "max_czk": None, "popis": None, "eligible": None,
               "kod": None, "url": LISTING}
        try:
            parsed = parse_navod(pdf_text(fetch_bytes(pdf_url)))
        except Exception as e:
            print(f"  warn {name}: {str(e)[:60]}", file=sys.stderr)
            parsed = {}
        rec["eligible"] = parsed.get("eligible")
        popis_bits = []
        if parsed.get("oblast"):
            popis_bits.append(f"Podporovaná oblast: {parsed['oblast']}.")
        if parsed.get("termin_text"):
            # každoroční termín bez roku — uchovej textově, deadline zůstává null
            popis_bits.append(parsed["termin_text"] + " (každoročně, rok není v Návodu uveden)")
        rec["popis"] = " ".join(popis_bits) or None
        rec["extra_navod_url"] = pdf_url
        key = (name, pdf_url)
        if key in seen_prog:
            continue
        seen_prog.add(key)
        out["programs"].append(rec)
        save()  # ukládej po každém programu

    save()
    print(json.dumps({"MARKER": "KV_MESTO_HARVEST", "source": out["source"],
                      "kept": len(out["programs"]), "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
