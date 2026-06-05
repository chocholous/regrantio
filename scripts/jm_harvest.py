#!/usr/bin/env python3
"""Jihomoravský kraj — harvester dotačních programů přes GINIS úřední desku (USU).

KONTEXT (proč právě tudy):
- dotace.kr-jihomoravsky.cz i celý živý web www.jmk.cz jsou za F5 APM WAF (BIG-IP logout) → zazděno.
- www.kr-jihomoravsky.cz (KEVIS, curl 200) je ARCHIVNÍ web zamrzlý k 06/2021 ("Nový web → www.jmk.cz");
  Default.aspx?ID=NNN servíruje pro každé ID stejnou homepage shell, žádné aktuální programy. Slepá ulička.
- eud.jmk.cz GINIS úřední deska (USU) NENÍ za WAF a má ŽIVÁ data 2026. Má kategorii
  "Dotační programy a návratná finanční výpomoc" (KAT050) = VYHLÁŠENÍ programů (otevřené výzvy),
  oddělenou od "Veřejnoprávní smlouvy dotace" (KAT060) = awards/smlouvy s příjemci.

METODA: Playwright (GINIS skládá tabulku JS-em + session cookie + custom GClientRequest XHR; čistý
HTTP replay je křehký). Seznam.aspx?a=1 → select KAT050 → klik OK → stránkování "Další" → Detail.aspx
per řádek (přílohy = pravidla programu v PDF, kde je reálný termín/alokace/oprávněnost pro vrstvu 2).

PASTI:
- "Vyvěšení/Sejmutí dne" = okno vývěsky na desce, NE termín podání žádosti. Reálný deadline je v PDF
  pravidel → necháváme na vrstvě 2 (LLM nad přílohami). open_from/deadline plníme z vývěsky jako
  nejlepší strukturovaný signál; status dopočítá ingest, deeper pole (alokace/eligible) = null.
- KAT050 míchá vyhlášení programů s jednotlivými award-smlouvami ("DOT - Dotace z rozpočtu JMK, ...,
  FV do ...") a oznámeními. Award-smlouvy filtrujeme (AWARD_RE) — cíl = programy/výzvy, ne příjemci.

Lossless: ukládáme plný text detailu (_text) + všechny přílohy (_attachments: url+název). Nic nezahazujeme.

Setup: playwright install chromium
Usage: python3 scripts/jm_harvest.py [--out data/h_kraj_jm.json] [--headful]
"""
import argparse, json, re, sys
from playwright.sync_api import sync_playwright

BASE = "https://eud.jmk.cz/Gordic/Ginis/App/UDE01/"
SEZNAM = BASE + "Seznam.aspx?a=1"
KAT_DOTACE = "KAT050"  # "Dotační programy a návratná finanční výpomoc"

# Award-smlouvy / jednotliví příjemci (NE program/výzva) — odfiltrovat.
# Typicky: "DOT - Dotace z rozpočtu JMK, „<projekt>", FV do <datum>" nebo "...obec <X>".
AWARD_RE = re.compile(r"^\s*DOT\b.*(?:,\s*FV\b|Smlouva o poskytnutí|z rozpočtu JMK)", re.I)
# Bezpečnostní pojistka proti runaway stránkování (NAHLAS log při dosažení = bug, ne cap).
MAX_PAGES = 60

ROW_JS = """els=>els.slice(1).map(tr=>{
  const g=c=>{const e=tr.querySelector(c);return e?e.innerText.trim():null};
  const a=tr.querySelector('a.DetailLink');
  return {kat:g('td.KategorieTdL'),nazev:g('td.NazevTdL'),popis:g('td.PopisTdL'),
          znacka:g('td.ZnackaTdL'),vyv:g('td.VyveseniDneTdL'),sejm:g('td.SejmutiDneTdL'),
          zdroj:g('td.ZdrojTdL'),detail:a?a.getAttribute('href'):null};
}).filter(r=>r.nazev)"""

DETAIL_FILES_JS = """els=>els.map(e=>({url:e.getAttribute('href'),name:e.innerText.trim()}))"""


def _iso(s):
    m = re.match(r"\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", s or "")
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def _abs(href):
    return BASE + href.lstrip("/") if href and not href.startswith("http") else href


def collect_listing(pg):
    """Vyber KAT050, projdi všechny stránky (Další), vrať deduplikované řádky."""
    pg.goto(SEZNAM, wait_until="networkidle", timeout=45000)
    pg.wait_for_timeout(2000)
    pg.select_option("select#m_oKategorie", KAT_DOTACE)
    pg.click('input[value="OK"]', timeout=10000)
    pg.wait_for_timeout(4000)

    seen, rows, page = set(), [], 0
    while True:
        page += 1
        batch = pg.eval_on_selector_all("table#m_oMainTable tr", ROW_JS)
        first = batch[0]["nazev"] if batch else None
        for r in batch:
            key = (r.get("znacka"), r.get("nazev"))
            if key not in seen:
                seen.add(key); rows.append(r)
        if page >= MAX_PAGES:
            print(f"⚠ MAX_PAGES={MAX_PAGES} dosaženo — pravděpodobně bug ve stránkování", file=sys.stderr)
            break
        nxt = pg.query_selector('a:has-text("Další")')
        if not nxt:
            break
        try:
            nxt.click(); pg.wait_for_timeout(3500)
        except Exception as e:
            print(f"  (pager konec: {str(e)[:50]})", file=sys.stderr); break
        after = pg.eval_on_selector_all("table#m_oMainTable tr", ROW_JS)
        if (after[0]["nazev"] if after else None) == first:
            break  # poslední stránka (obsah se nezměnil)
    print(f"KAT050: {len(rows)} unikátních řádků přes {page} stránek", file=sys.stderr)
    return rows


def fetch_detail(pg, href):
    """Otevři Detail.aspx, vrať (plný_text, [přílohy])."""
    pg.goto(_abs(href), wait_until="networkidle", timeout=45000)
    pg.wait_for_timeout(1500)
    text = pg.inner_text("body")
    files = pg.eval_on_selector_all('a[href*="Dokument.aspx"]', DETAIL_FILES_JS)
    atts = [{"url": _abs(f["url"]), "name": f["name"]} for f in files if f.get("url")]
    return text, atts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_jm.json")
    ap.add_argument("--headful", action="store_true")
    a = ap.parse_args()

    with sync_playwright() as p:
        b = p.chromium.launch(headless=not a.headful)
        pg = b.new_page()
        rows = collect_listing(pg)

        progs, skipped_award = [], 0
        for r in rows:
            nazev = re.sub(r"\s+", " ", r["nazev"]).strip()
            if AWARD_RE.match(nazev):
                skipped_award += 1; continue
            text, atts = ("", [])
            if r.get("detail"):
                try:
                    text, atts = fetch_detail(pg, r["detail"])
                except Exception as e:
                    print(f"  warn detail {nazev[:40]}: {str(e)[:50]}", file=sys.stderr)
            progs.append({
                "nazev": nazev,
                # vývěska (NE termín podání) — strukturovaný proxy; reálný deadline řeší vrstva 2 z PDF
                "open_from": _iso(r.get("vyv")),
                "deadline": _iso(r.get("sejm")),
                "status": None,                         # dopočítá ingest
                "alokace_czk": None,                    # v PDF pravidel → vrstva 2
                "max_czk": None,
                "popis": (re.sub(r"\s+", " ", r["popis"]).strip() or None) if r.get("popis") else None,
                "eligible": None,                       # v PDF pravidel → vrstva 2
                "kod": (r.get("znacka") or None),
                "url": _abs(r["detail"]) if r.get("detail") else BASE + "Seznam.aspx?a=1",
                "_zdroj": r.get("zdroj"),               # odbor (lossless meta)
                "_text": text,
                "_attachments": atts,
            })
        b.close()

    out = {"source": "kr-jihomoravsky.cz", "kraj": "Jihomoravský kraj",
           "platform": "jm_kevis", "programs": progs}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "JM_HARVEST", "kept": len(progs),
                      "skipped_award": skipped_award, "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
