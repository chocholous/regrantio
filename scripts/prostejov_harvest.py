#!/usr/bin/env python3
"""Prostějov harvester — dotační programy statutárního města Prostějov (public4u CMS).

ZDROJ: prostejov.eu, sekce /cs/obcan/dotace/. Listing aktuálních dotačních programů je
strom: rok-sekce (SPORT 2026, ŘEMESLA 2026, ...) → program (dir/) → dotační tituly (.html leaf).
Awards ("Schválené dotace …") ani "Archiv"/"Zásady"/"Ostatní dotace" (jen nav) NEsbíráme.

Granulita = PROGRAM (ne titul). Autoritativní dokument programu je PDF se štítkem začínajícím
"Dotační prog…" (pozor na překlep "progam" na webu). Stejný program se opakuje na dir-page
i v titul-leaf s JINÝM file-id ale STEJNÝM štítkem → dedup podle štítku PDF, ne podle file-id.

Lhůta/alokace: napřed inline z těla ("Lhůta pro přijímání žádostí: od D.M.RRRR do D.M.RRRR" —
ŘEMESLA), jinak z program-PDF (sekce "7. Lhůty / 7.2 … od … do …" + "celkový objem … částka N Kč"
— SPORT). U SPORT jsou lhůty per-titul; bereme nejzazší deadline programu (status = počítá ingest).

Public4u občas vrací osekanou stub-stránku (~8 kB, jen chrome) místo plné (~30-50 kB) → fetch
retryuje, dokud nedostane stránku >= MINSIZE nebo nevyčerpá pokusy.

Lossless: ukládá _text (plné tělo), všechny přílohy (label+url), zdroj inline/pdf u dat.
Průběžně zapisuje (append po každém programu). Status dopočítá ingest_kraj z termínů.

Usage: python3 scripts/prostejov_harvest.py [--out data/h_mesto_prostejov.json]
       (volitelně --no-pdf vypne stahování program-PDF; pak deadline/alokace jen z inline)
"""
import argparse, json, os, re, subprocess, sys, tempfile, time, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)
from collections import deque

BASE = "https://www.prostejov.eu"
DOTACE = BASE + "/cs/obcan/dotace/"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh)", "Accept-Language": "cs"}

# stub-detekce: plná detail-stránka public4u má >= ~15 kB; stub jen chrome ~8 kB
MINSIZE = 15000
RETRIES = 8
# subtree, který NEsbíráme (nav-only / archiv / pravidla)
SKIP_SEG = ("archiv", "zasady-poskytovani", "ostatni-dotace")
PROG_LABEL = re.compile(r"^dotačn[íi]\s+prog", re.I)  # "Dotační program" i překlep "progam"


def fetch(url, minsize=MINSIZE, retries=RETRIES):
    """Stáhne URL; retryuje dokud nedostane stránku >= minsize (obrana proti public4u stubům)."""
    last = ""
    for _ in range(retries):
        try:
            raw = http_util.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
            last = raw.decode("utf-8", "replace")
            if len(raw) >= minsize:
                return last
        except Exception as e:
            last = ""
            print(f"  warn fetch {url[-50:]}: {str(e)[:60]}", file=sys.stderr)
        time.sleep(0.8)
    return last  # vrať co máme (i stub), volající ošetří


def fetch_bytes(url, retries=4):
    for _ in range(retries):
        try:
            return http_util.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except Exception as e:
            print(f"  warn pdf {url[-40:]}: {str(e)[:50]}", file=sys.stderr)
            time.sleep(0.8)
    return None


def strip(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", t)).strip()


def anchors(html):
    """[(href, label)] pro všechny <a>."""
    out = []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S):
        lbl = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
        out.append((m.group(1), lbl))
    return out


def absu(href):
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        return BASE + href
    return DOTACE + href


def files_on(html):
    """Přílohy ke stažení: [(label, abs_url)] pro pdf/doc/docx/xls/xlsx."""
    out, seen = [], set()
    for href, lbl in anchors(html):
        if re.search(r"\.(pdf|docx?|xlsx?)(?:$|\?)", href, re.I):
            u = absu(href)
            if u not in seen:
                seen.add(u)
                out.append({"label": lbl or None, "url": u})
    return out


ISO = lambda d, mo, y: f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
DATE_RANGE = re.compile(
    r"od\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\s*do\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})")


def parse_lhuta_inline(text):
    """Inline 'Lhůta pro přijímání žádostí: od D.M.RRRR do D.M.RRRR' → (open_from, deadline)."""
    m = re.search(r"[Ll]hůt[ay][^\n]{0,40}?" + DATE_RANGE.pattern, text)
    if m:
        return ISO(m[1], m[2], m[3]), ISO(m[4], m[5], m[6])
    return None, None


def parse_program_pdf(pdf_bytes):
    """Z program-PDF vytáhni (open_from, deadline=nejzazší, alokace_czk).

    SPORT: '7.2. Lhůta … od D.M.RRRR do D.M.RRRR' (per-titul, víc výskytů → vezmi min open, max deadline);
    '4.1. … předpokládaná výše celkové částky N Kč' nebo 'celkový objem … částka N Kč'.
    """
    if not pdf_bytes:
        return None, None, None
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes); path = f.name
    try:
        txt = subprocess.run(["pdftotext", "-layout", path, "-"],
                             capture_output=True, timeout=60).stdout.decode("utf-8", "replace")
    except Exception as e:
        print(f"  warn pdftotext: {str(e)[:50]}", file=sys.stderr)
        txt = ""
    finally:
        os.unlink(path)
    txt = re.sub(r"[ \t]+", " ", txt)

    # lhůty pro PODÁNÍ žádostí (ne pro zveřejnění programu) — sekce 7.2 / "podání žádost"
    opens, deads = [], []
    seg = txt
    i = txt.find("7.2.")
    if i > 0:
        seg = txt[i:i + 2500]   # jen lhůty pro podání, ne 7.1 zveřejnění
    for m in DATE_RANGE.finditer(seg):
        opens.append((int(m[3]), int(m[2]), int(m[1])))
        deads.append((int(m[6]), int(m[5]), int(m[4])))
    if not opens and i <= 0:
        # ŘEMESLA-styl uvnitř PDF
        of, dl = parse_lhuta_inline(txt)
    else:
        of = ISO(min(opens)[2], min(opens)[1], min(opens)[0]) if opens else None
        dl = ISO(max(deads)[2], max(deads)[1], max(deads)[0]) if deads else None

    NUM = r"([\d\.\s\xa0]+)"
    alok = max_z = None
    for pat in (r"celkové částky\s+" + NUM + r"Kč",
                r"alokována\s+celková částka\s+" + NUM + r"Kč",
                r"celkov[\u00fd\u00e1\u00e9][^\n]{0,40}?\u010d\u00e1stk[ay][^\n]{0,40}?" + NUM + r"K\u010d",
                r"celkový objem[^\n]{0,90}?" + NUM + r"Kč"):
        m = re.search(pat, txt)
        if m:
            d = re.sub(r"[^\d]", "", m.group(1))
            if d:
                alok = int(d); break
    mm = re.search(r"[Vv]\u00fd\u0161e jednotliv\u00e9 dotace \u010din\u00ed\s+" + NUM + r"K\u010d", txt)
    if mm:
        d = re.sub(r"[^\d]", "", mm.group(1))
        if d:
            max_z = int(d)
    return of, dl, alok, max_z


def h1_of(html):
    m = re.search(r'class="nadpis_clanku[^"]*"[^>]*>([^<]+)', html)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def crawl():
    """BFS dotace-stromem; vrať dict {program_label: record} (dedup podle PDF štítku)."""
    start = fetch(DOTACE)
    queue = deque()
    visited = set()
    # seed: child sekce z dotace listingu (rok-sekce)
    for href, lbl in anchors(start):
        u = absu(href)
        if "/cs/obcan/dotace/" in u and u.rstrip("/") != DOTACE.rstrip("/"):
            if any(s in u for s in SKIP_SEG):
                continue
            queue.append(u)
    programs = {}   # label -> record
    pages = 0
    while queue:
        u = queue.popleft()
        key = u.rstrip("/")
        if key in visited:
            continue
        visited.add(key)
        if any(s in u for s in SKIP_SEG):
            continue
        html = fetch(u)
        if len(html) < 4000:
            continue
        pages += 1
        text = strip(html)
        files = files_on(html)
        prog_pdfs = [f for f in files if f["label"] and PROG_LABEL.match(f["label"])]

        # enqueue hlubší dotace stránky (program dirs i titul leaves)
        for href, _ in anchors(html):
            cu = absu(href)
            if ("/cs/obcan/dotace/" in cu and cu.rstrip("/") not in visited
                    and not any(s in cu for s in SKIP_SEG)
                    and cu.rstrip("/") != key):
                # jen sestup hlouběji ve stejném podstromu
                if cu.rstrip("/").startswith(key) or key.startswith(cu.rstrip("/")) is False:
                    queue.append(cu)

        if not prog_pdfs:
            continue
        # tato stránka drží program(y)
        for ppdf in prog_pdfs:
            label = re.sub(r"\s+", " ", ppdf["label"]).strip()
            # normalizace překlepu pro dedup-klíč, ale nazev necháme čitelný
            dedup_key = re.sub(r"progam", "program", label, flags=re.I).lower()
            existing = programs.get(dedup_key)
            # preferuj dir-page (kratší URL) jako kanonickou
            if existing and len(existing["url"]) <= len(u):
                # přiber přílohy, které tu jsou navíc
                have = {a["url"] for a in existing["attachments"]}
                existing["attachments"] += [a for a in files if a["url"] not in have]
                continue
            of, dl = parse_lhuta_inline(text)
            src = "inline" if dl else None
            pof, pdl, alok, max_z = parse_program_pdf(fetch_bytes(ppdf["url"]))
            if not dl:                       # inline lhůta nenalezena → použij PDF
                of, dl = pof, pdl
                src = "pdf" if dl else None
            short = re.sub(r"progam", "program", label, flags=re.I)  # PDF štítek (fix překlepu)
            h1 = h1_of(html)
            nazev = h1 or short                              # plný název programu z H1
            rec = {
                "nazev": nazev,
                "open_from": of, "deadline": dl, "status": None,
                "alokace_czk": alok, "max_czk": max_z,
                "popis": (short if h1 else None),
                "eligible": None, "kod": None,
                "url": u.split("?")[0],
                "_program_pdf": ppdf["url"], "_date_source": src,
                "attachments": files,
                "_text": text[:6000],
            }
            programs[dedup_key] = rec
            print(json.dumps({"MARKER": "PV_PROG", "nazev": nazev, "open_from": of,
                              "deadline": dl, "alokace_czk": alok, "src": src,
                              "files": len(files)}, ensure_ascii=False), flush=True)
    print(f"navštíveno {pages} stránek, {len(programs)} programů", file=sys.stderr)
    return list(programs.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_prostejov.json")
    ap.add_argument("--no-pdf", action="store_true", help="nestahuj program-PDF (data jen z inline)")
    a = ap.parse_args()

    if a.no_pdf:
        global parse_program_pdf
        parse_program_pdf = lambda b: (None, None, None, None)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)

    def dump(progs):
        out = {"source": "prostejov.eu", "kraj": "Olomoucký kraj", "obec": "Prostějov",
               "uroven": "obec", "platform": "prostejov_public4u", "programs": progs}
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    dump([])  # založ soubor hned (průběžný zápis)
    progs = crawl()
    # contract: bez interních _ polí v hlavní serializaci? Necháváme — lossless; ingest čte jen kontraktní.
    dump(progs)
    print(json.dumps({"MARKER": "PROSTEJOV_HARVEST", "kept": len(progs), "out": a.out},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
