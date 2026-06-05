#!/usr/bin/env python3
"""Zlínský kraj harvester — aktuálně vyhlášené výzvy dotačních programů (server-rendered HTML).

zlinskykraj.cz/aktualne-vyhlasene-vyzvy-dotacnich-programu-zlinskeho-kraje = listing
vyhlášených dotačních programů na rok ~2026. Každý blok má řádek s názvem (vč. kódu),
"Oblast <...> Finanční alokace <...> Označení <KÓD>" a "Příjem žádostí od DD.MM.YYYY do
DD.MM.YYYY" + odkaz "Detail dotace" → absolutní URL. Vše přímo v HTML (HTTP 200), žádný
LLM, žádný rendering.

Cíl = vyhlášené VÝZVY, ne awards. Status dopočítá ingest z termínů (kontrakt: status=null).
Stránkuje (?page=N) dokud stránka vrací bloky. Dedup dle (kod|url|nazev).

POZOR: dotace.zlinskykraj.cz je zakázaný subdoména — nepoužívat.

Usage: python3 scripts/zlinsky_harvest.py [--out data/h_kraj_zlinsky.json]
"""
import argparse, json, re, sys, urllib.request

BASE = "https://zlinskykraj.cz"
LISTING = "/aktualne-vyhlasene-vyzvy-dotacnich-programu-zlinskeho-kraje"
# safety pojistka proti runaway stránkování (NE coverage cap — při dosažení ⚠ log)
MAX_PAGES = 50

# kód programu: RP30-25, SOC02-26, KUL01-26, MaS01-26, NFV01-26 apod.
CODE_RE = re.compile(r"^[A-Za-z]{2,4}\d{2,}(?:-\d{2})?$")
# blok: <nazev> Oblast <oblast> Finanční alokace <alok> Označení <kod-radek> Termín ...
#       Příjem žádostí od DD.MM.YYYY do DD.MM.YYYY ... DETAILURL=<url>
BLOCK_RE = re.compile(
    r"(?P<nazev>.+?)\s*"
    r"Oblast\s+(?P<oblast>.+?)\s+"
    r"Finanční alokace\s+(?P<alok>.+?)\s+"
    r"Označení\s+(?P<oznaceni>.+?)\s+"
    r"Termín vyhlášení programu\s+(?P<vyhlaseno>[\d.]+)\s+"
    r"Příjem žádostí\s+(?P<termin>.+?)\s+"
    r"DETAILURL=(?P<url>\S+)",
    re.S,
)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def detext(html):
    """HTML → text, ale 'Detail dotace' linky převede na inline DETAILURL=<href>."""
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = re.sub(
        r'<a[^>]+href="(' + re.escape(BASE) + r'/dotace/[^"]+)"[^>]*>\s*Detail dotace\s*</a>',
        r" DETAILURL=\1 ",
        h,
    )
    h = re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " ")
    h = re.sub(r"[ \t]+", " ", h)
    return re.sub(r"\n\s*\n+", "\n", h).strip()


def _iso(s):
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", (s or "").strip())
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def parse_termin(s):
    """'od DD.MM.YYYY do DD.MM.YYYY' → (open_from, deadline); 'do DD.MM.YYYY' → (None, deadline)."""
    s = s or ""
    m = re.search(r"od\s+([\d.]+)\s+do\s+([\d.]+)", s)
    if m:
        return _iso(m.group(1)), _iso(m.group(2))
    m = re.search(r"do\s+([\d.]+)", s)
    if m:
        return None, _iso(m.group(1))
    m = re.search(r"od\s+([\d.]+)", s)
    if m:
        return _iso(m.group(1)), None
    return None, None


def parse_alokace(s):
    """'70 mil. Kč'→70000000; '7,67 mil.Kč'→7670000; '500 000 Kč'→500000; nečíselné→None."""
    s = (s or "").replace("\xa0", " ").strip()
    m = re.search(r"([\d  ]+(?:[.,]\d+)?)\s*mil\.?\s*Kč", s, re.I)
    if m:
        num = m.group(1).replace(" ", "").replace(",", ".")
        try:
            return int(round(float(num) * 1_000_000))
        except ValueError:
            return None
    m = re.search(r"([\d  ]+)\s*Kč", s)
    if m:
        digits = re.sub(r"[^\d]", "", m.group(1))
        return int(digits) if digits else None
    return None


def parse_oznaceni(s):
    """'Označení' řádek: buď kód (RP30-25) nebo text ('Individuální dotace')."""
    s = (s or "").strip()
    first = s.split()[0] if s else ""
    return first if CODE_RE.match(first) else None


def parse_listing(text):
    progs = []
    for m in BLOCK_RE.finditer(text):
        # nazev může mít před sebou navigační smetí (breadcrumb/header) na předchozích
        # řádcích; vezmi poslední neprázdný řádek a teprve pak srovnej whitespace.
        lines = [ln.strip() for ln in m.group("nazev").splitlines() if ln.strip()]
        nazev = re.sub(r"\s+", " ", lines[-1]) if lines else ""
        open_from, deadline = parse_termin(m.group("termin"))
        progs.append({
            "nazev": nazev,
            "open_from": open_from,
            "deadline": deadline,
            "status": None,
            "alokace_czk": parse_alokace(m.group("alok")),
            "max_czk": None,
            "popis": None,
            "eligible": None,
            "kod": parse_oznaceni(m.group("oznaceni")),
            "url": m.group("url").strip(),
            "_oblast": re.sub(r"\s+", " ", m.group("oblast")).strip(),
        })
    return progs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_zlinsky.json")
    a = ap.parse_args()

    all_progs, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        url = f"{BASE}{LISTING}" + (f"?page={page - 1}" if page > 1 else "")
        try:
            html = fetch(url)
        except Exception as e:
            print(f"  warn page {page}: {str(e)[:60]}", file=sys.stderr)
            break
        text = detext(html)
        progs = parse_listing(text)
        if not progs:
            break
        added = 0
        for p in progs:
            key = p["kod"] or p["url"] or p["nazev"]
            if key in seen:
                continue
            seen.add(key)
            all_progs.append(p)
            added += 1
        print(f"page {page}: {len(progs)} bloků, {added} nových", file=sys.stderr)
        if added == 0:  # stejná stránka dokola → konec
            break
        if page == MAX_PAGES:
            print("⚠ MAX_PAGES dosažen — možný runaway/uniklé stránky", file=sys.stderr)

    out = {
        "source": "zlinskykraj.cz",
        "kraj": "Zlínský kraj",
        "platform": "zlinsky_html",
        "programs": all_progs,
    }
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "ZLINSKY_HARVEST", "kept": len(all_progs), "out": a.out},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
