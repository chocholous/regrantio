#!/usr/bin/env python3
"""Plzeň (statutární město) harvester — dotační tituly portálu dotace.plzen.eu (edotace).

Stejná rodina jako dotace.plzensky-kraj.cz. Veřejný listing je na /verejnost/dotacni-tituly/,
ale TABULKA je prázdná v HTML (<table id="Tituly"></table>) — plní ji jqGrid přes JSON-XHR:
  GET https://dotace.plzen.eu/verejnost/dotacni-tituly/?_name=Tituly&_search=false&rows=...&page=1
Vrací {"rows":[{"cell":{utvar,zkratka,cislotitulu,nazev,rokod,rokdo,zadostiod,zadostido,
stav,otevreno, buttons=<a href="/verejnost/titul/{uuid}/">}}]}. Čistý HTTP replay, BEZ Playwrightu.

Detail (/verejnost/titul/{uuid}/) je server-rendered štítkovaný HTML → přidává Anotaci (popis),
Typ titulu (Jednoletý/Víceletý), Typ dotace (Investiční/Neinvestiční). POZOR: platforma NEMÁ
pole alokace ani max na žadatele → alokace_czk a max_czk jsou VŽDY null (kontrakt). 'otevreno'
ze zelené barvy listingu se NEpřebírá jako status — status dopočítá ingest z termínů.

Cíl = vyhlášené VÝZVY (dotační tituly) s termíny, NE žádostní login, NE awards.

Usage: python3 scripts/plzen_mesto_harvest.py [--out data/h_mesto_plzen.json]
"""
import argparse, json, re, sys, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)

BASE = "https://dotace.plzen.eu"
GRID = BASE + "/verejnost/dotacni-tituly/?_name=Tituly"
# safety pojistka proti runaway (NE coverage cap) — listing má ~20 titulů; bereme vše na 1 stránku
GRID_ROWS = 100000
DETAIL_LABELS = {
    "popis": r"Anotace\s+(.+?)\s+Termíny",
    "typ_titulu": r"Typ titulu\s+(.+?)\s+Typ dotace",
    "typ_dotace": r"Typ dotace\s+(.+?)\s+Anotace",
}


def fetch(url, as_json=False):
    headers = {"User-Agent": "Mozilla/5.0"}
    if as_json:
        headers["X-Requested-With"] = "XMLHttpRequest"
        headers["Accept"] = "application/json"
    req = urllib.request.Request(url, headers=headers)
    raw = http_util.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    return json.loads(raw) if as_json else raw


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " ")
    h = re.sub(r"[ \t]+", " ", h)
    return re.sub(r"\n\s*\n+", "\n", h).strip()


def _iso(s):
    """'2026-06-15 12:00:00' nebo '15.06.2026 ...' → 'YYYY-MM-DD'."""
    s = (s or "").strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m[1]}-{m[2]}-{m[3]}"
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def parse_detail(html):
    """Z detailu vytáhne Anotaci (popis) + typ titulu/dotace. Anotace '-' → None."""
    text = detext(html)
    seg = text[text.find("Základní informace"):] if "Základní informace" in text else text
    rec = {}
    for k, pat in DETAIL_LABELS.items():
        m = re.search(pat, seg, re.S)
        if m:
            v = re.sub(r"[ \t]+", " ", m.group(1)).strip()
            rec[k] = v if v and v != "-" else None
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_plzen.json")
    a = ap.parse_args()

    grid = fetch(f"{GRID}&_search=false&rows={GRID_ROWS}&page=1&sidx=&sord=asc", as_json=True)
    rows = grid.get("rows", [])
    records = int(grid.get("records") or 0)
    print(f"jqGrid vrátil {len(rows)} řádků (records={records}, total_pages={grid.get('total')})",
          file=sys.stderr)
    if records and len(rows) < records:
        print(f"⚠ staženo méně řádků než records ({len(rows)}<{records}) — možná stránkování",
              file=sys.stderr)

    progs, seen = [], set()
    for r in rows:
        c = r.get("cell", {})
        nazev = (c.get("nazev") or "").strip()
        if not nazev:
            continue
        # detail URL z 'buttons' HTML; fallback z rowId
        m = re.search(r'href="(/verejnost/titul/[^"]+)"', c.get("buttons") or "")
        rid = c.get("rowId") or r.get("id")
        href = m.group(1) if m else (f"/verejnost/titul/{rid}/" if rid else None)
        url = BASE + href if href else None

        key = c.get("cislotitulu") or rid or url or nazev
        if key in seen:
            continue
        seen.add(key)

        rec = {
            "nazev": nazev,
            "open_from": _iso(c.get("zadostiod")),
            "deadline": _iso(c.get("zadostido")),
            "status": None,                       # dopočítá ingest z termínů
            "alokace_czk": None,                  # platforma nemá pole alokace
            "max_czk": None,                      # platforma nemá max na žadatele
            "popis": None,
            "eligible": None,                     # platforma nemá čisté pole oprávněnosti
            "kod": c.get("cislotitulu") or None,
            "url": url,
            "_utvar": (c.get("utvar") or "").strip() or None,
            "_zkratka": (c.get("zkratka") or "").strip() or None,
        }

        # detail → Anotace (popis) + typ titulu/dotace
        if url:
            try:
                d = parse_detail(fetch(url))
                rec["popis"] = d.get("popis")
                if d.get("typ_titulu"):
                    rec["_typ_titulu"] = d["typ_titulu"]
                if d.get("typ_dotace"):
                    rec["_typ_dotace"] = d["typ_dotace"]
            except Exception as e:
                print(f"  warn detail {key}: {str(e)[:60]}", file=sys.stderr)

        progs.append(rec)
        # průběžné ukládání
        json.dump({"source": "dotace.plzen.eu", "kraj": "Plzeňský kraj", "obec": "Plzeň",
                   "uroven": "obec", "platform": "plzen_edotace", "programs": progs},
                  open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    out = {"source": "dotace.plzen.eu", "kraj": "Plzeňský kraj", "obec": "Plzeň",
           "uroven": "obec", "platform": "plzen_edotace", "programs": progs}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "PLZEN_MESTO_HARVEST", "kept": len(progs),
                      "records_reported": records, "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
