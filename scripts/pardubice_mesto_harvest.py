#!/usr/bin/env python3
"""Harvester dotačních programů statutárního města Pardubice (server-rendered HTML + PDF).

ZDROJ: https://pardubice.eu/dotace — jediná stránka-rozcestník, kde každý <h2> = jeden
městský dotační program (PPS, PPKU, PPCR, PPVVRA, PPB, sociální/zdravotní, prevence
kriminality, ekologická výchova, rezervy rady, Pardubičtí tahouni, + 2 programy MK ČR
administrované městem jako ORP). POZOR: dotace.pardubickykraj.cz je KRAJ, ne město — sem
nepatří.

Metoda (STRUKTURA PŘED PRÓZOU, ale tady je listing prostá HTML stránka bez inline JSON):
  1. curl /dotace → rozparsuj na bloky podle <h2>; v každém bloku posbírej odkazy na soubory.
  2. Pro každý program vyber "definiční" dokument výzvy v pořadí priority:
       podminky-dotacniho-programu-* > zamer-poskytnuti-* > vyhlaseni-* > pravidla-*
     (Termín/alokace/žadatelé NEJSOU v HTML — žijí v tomto PDF.)
  3. pdftotext -layout → parse štítkovaných polí:
       "Lhůta pro podání žádost(í)" / "Termín pro předlož..." → open_from + deadline
         (formáty: "od 16. 01. 2026 ... do 04. 02. 2026" i "16. ledna 2026 – 4. února 2026")
       "Předpokládaný celkový objem ..." → alokace_czk
       "Maximální výše dotace v jednotlivém případě" → max_czk (jen je-li číselné)
       "Žadatelé" → eligible
  Co se nepodaří vyčíst z PDF (sken, odlišný layout) = null. Status dopočítá ingest z termínů.

Cíl = OTEVŘENÉ výzvy města s termíny (NE awards / "výsledky dotačního řízení" / login).

Ukládá průběžně (po každém programu přepíše JSON). Lossless: ukládá i _text výňatek z PDF
a všechny přílohy bloku.

Usage:
  python3 scripts/pardubice_mesto_harvest.py [--out data/h_mesto_pardubice.json]
"""
import argparse, json, os, re, subprocess, sys, tempfile, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)

BASE = "https://pardubice.eu"
LISTING = BASE + "/dotace"
UA = {"User-Agent": "Mozilla/5.0"}

# bloky, které NEJSOU dotační program (rozcestníkové sekce na konci stránky)
SKIP_HEADING = re.compile(r"^Smlouvy o poskytnutí|^Sociální sítě|^Důležité odkazy", re.I)

# priorita "definičního" dokumentu výzvy v rámci jednoho bloku
DOC_PRIORITY = [
    r"podminky-dotacniho-programu",
    r"zamer-poskytnuti",
    r"vyhlaseni",
    r"pravidla.*202[6-9]",   # preferuj nejnovější pravidla
    r"pravidla",
]

CZ_MONTH = {
    "ledna": 1, "února": 2, "unora": 2, "března": 3, "brezna": 3, "dubna": 4,
    "května": 5, "kvetna": 5, "června": 6, "cervna": 6, "července": 7, "cervence": 7,
    "srpna": 8, "září": 9, "zari": 9, "října": 10, "rijna": 10, "listopadu": 11,
    "prosince": 12,
}


def fetch_bytes(url):
    req = urllib.request.Request(url, headers=UA)
    return http_util.urlopen(req, timeout=60).read()


def fetch_text(url):
    return fetch_bytes(url).decode("utf-8", "replace")


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h).replace("\xa0", " ").replace("&nbsp;", " ")
    h = re.sub(r"&amp;", "&", h).replace("&ndash;", "–").replace("&shy;", "")
    return re.sub(r"[ \t]+", " ", h).strip()


def pdftotext(data):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(data); path = f.name
    try:
        r = subprocess.run(["pdftotext", "-layout", path, "-"],
                           capture_output=True, timeout=120)
        return r.stdout.decode("utf-8", "replace")
    except Exception as e:
        print(f"  warn pdftotext: {str(e)[:60]}", file=sys.stderr); return ""
    finally:
        os.unlink(path)


def _iso(d, m, y):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def parse_dates(text):
    """Vrať (open_from, deadline) z věty o lhůtě pro podání žádostí, jinak (None, None)."""
    # vystřihni okolí štítku lhůty/termínu
    m = re.search(r"(Lhůta pro podání žádost\w*|Termín pro předlož\w*[^\n]*)([\s\S]{0,260})", text, re.I)
    if not m:
        return None, None
    seg = m.group(0)
    # 1) číselný formát: od 16. 01. 2026 ... do 04. 02. 2026
    nums = re.findall(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d{2})", seg)
    if len(nums) >= 2:
        return _iso(*nums[0]), _iso(*nums[1])
    if len(nums) == 1:
        # jen jedno datum → deadline
        return None, _iso(*nums[0])
    # 2) slovní měsíce: 16. ledna 2026 – 4. února 2026
    words = re.findall(r"(\d{1,2})\.\s*([a-zěščřžýáíéůúóďťňA-Z]+)\s*(20\d{2})", seg)
    iso = []
    for d, mon, y in words:
        mm = CZ_MONTH.get(mon.lower())
        if mm:
            iso.append(_iso(d, mm, y))
    if len(iso) >= 2:
        return iso[0], iso[1]
    if len(iso) == 1:
        return None, iso[0]
    return None, None


def parse_alokace(text):
    m = re.search(r"Předpokládaný celkový objem[^\n]*\n?([\s\S]{0,160})", text, re.I)
    seg = m.group(1) if m else ""
    am = re.search(r"([\d][\d\.\s ]{4,})\s*,?-?\s*Kč", seg)
    if am:
        d = re.sub(r"[^\d]", "", am.group(1))
        if d:
            return int(d)
    return None


def parse_max(text):
    m = re.search(r"Maximální výše dotace v jednotlivém případě[^\n]*([\s\S]{0,140})", text, re.I)
    if not m:
        return None
    am = re.search(r"([\d][\d\.\s ]{4,})\s*,?-?\s*Kč", m.group(1))
    if am:
        d = re.sub(r"[^\d]", "", am.group(1))
        if d:
            return int(d)
    return None


def parse_eligible(text):
    m = re.search(r"\nŽadatelé:?\s*\n?([\s\S]{0,400}?)(?:\n\s*\n|Lhůta pro|Termín pro|Maximální výše|Forma podání)", text, re.I)
    if m:
        e = re.sub(r"\s+", " ", m.group(1)).strip(" .–-")
        if 5 < len(e) < 400:
            return e
    return None


def pick_doc(links):
    """links: list of (href, anchor). Vrať href definičního dokumentu výzvy podle priority."""
    for pat in DOC_PRIORITY:
        for href, _ in links:
            name = href.rsplit("/", 1)[-1].lower()
            if re.search(pat, name) and name.endswith(".pdf"):
                return href
    # fallback: první PDF
    for href, _ in links:
        if href.lower().endswith(".pdf"):
            return href
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_pardubice.json")
    a = ap.parse_args()

    html = fetch_text(LISTING)
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    start = h.find("Program podpory Pardubičtí tahouni")
    end = h.find("Sociální sítě")
    if start < 0:
        print(json.dumps({"MARKER": "PARDUBICE_HARVEST", "error": "listing layout changed"}))
        sys.exit(2)
    seg = h[start - 300:end if end > 0 else len(h)]

    parts = re.split(r"(<h2[^>]*>.*?</h2>)", seg, flags=re.S | re.I)
    blocks = []  # (heading, html_block)
    cur = None
    for p in parts:
        if re.match(r"<h2", p, re.I):
            cur = detext(p)
        elif cur:
            blocks.append((cur, p)); cur = None

    out = {"source": "pardubice.eu", "kraj": "Pardubický kraj", "obec": "Pardubice",
           "uroven": "obec", "platform": "pardubice_mesto", "programs": []}

    seen = set()
    for heading, block in blocks:
        if not heading or SKIP_HEADING.search(heading):
            continue
        if heading in seen:
            continue
        seen.add(heading)

        # všechny soubory bloku (href + kotva)
        files = []
        for m in re.finditer(r'href="(/data/files/[^"]+\.(?:pdf|docx?|xlsx?))"', block, re.I):
            href = m.group(1)
            if href not in [f[0] for f in files]:
                files.append((href, ""))
        if not files:
            continue

        doc = pick_doc(files)
        prog = {
            "nazev": re.sub(r"\s+", " ", heading).strip(),
            "open_from": None, "deadline": None, "status": None,
            "alokace_czk": None, "max_czk": None, "popis": None,
            "eligible": None, "kod": None,
            "url": (BASE + doc) if doc else LISTING,
            "_attachments": [BASE + f[0] for f in files],
        }
        # kód z názvu (zkratka v závorce)
        km = re.search(r"\(zkratka ([A-ZČŘŠ]+)\)", heading)
        if km:
            prog["kod"] = km.group(1)

        if doc:
            try:
                txt = pdftotext(fetch_bytes(BASE + doc))
            except Exception as e:
                print(f"  warn fetch {doc[:40]}: {str(e)[:50]}", file=sys.stderr); txt = ""
            if txt:
                of, dl = parse_dates(txt)
                prog["open_from"] = of
                prog["deadline"] = dl
                prog["alokace_czk"] = parse_alokace(txt)
                prog["max_czk"] = parse_max(txt)
                prog["eligible"] = parse_eligible(txt)
                prog["_text"] = txt[:4000]

        out["programs"].append(prog)
        # ukládej průběžně
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  + {prog['nazev'][:55]:55} dl={prog['deadline']} alok={prog['alokace_czk']}",
              file=sys.stderr)

    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with_dl = sum(1 for p in out["programs"] if p["deadline"])
    print(json.dumps({"MARKER": "PARDUBICE_HARVEST", "kept": len(out["programs"]),
                      "with_deadline": with_dl, "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
