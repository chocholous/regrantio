#!/usr/bin/env python3
"""Mladá Boleslav harvester — dotační programy statutárního města (vismo mb-net.cz).

Listing dotačních programů žije v jednom vismo článku:
  /podpora-skolstvi-kultura-a-volny-cas/d-819/p1=63313 ("Dotace a granty")
Programy NEJSOU samostatné HTML detaily — každý "PROGRAM ... PRO ROK YYYY" je odkaz na
dokument (File.ashx → DOCX/PDF). Termíny/alokace/max-na-žadatele jsou JEN uvnitř těch
dokumentů, ne v HTML. Proto: z článku posbírej odkazy na programové dokumenty, každý stáhni
(curl-UA; vismo občas blokuje fetchery, Playwright fallback), převeď na text (textutil/pdftotext)
a vyparsuj strukturované věty:
  "... od DD.MM.YYYY s uzávěrkou dne DD.MM.YYYY ..."  → open_from / deadline
  "... pro rok YYYY je <částka> Kč."                   → alokace_czk
  "... maximálně <částka> Kč"                           → max_czk

Filtruje NE-programové odkazy (vzory žádostí, přílohy, smlouvy, manuál, schválené granty=awards).
Status dopočítá ingest_kraj z termínů. Lossless: ukládá parsed pole + plný text dokumentu.
Ukládá průběžně po každém programu.

Usage:
  python3 scripts/mb_harvest.py [--out data/h_mesto_mb.json] [--article <url>]
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)

BASE = "https://www.mb-net.cz"
ARTICLE = f"{BASE}/podpora-skolstvi-kultura-a-volny-cas/d-819/p1=63313"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

# Odkaz je PROGRAM (výzva), když text obsahuje "PROGRAM"/"GRANTOVÝ PROGRAM" + "PRO ROK".
# Vyřaď balast: vzory žádostí, přílohy, smlouvy, manuál, podmínky, schválené granty (=awards).
PROG_RE = re.compile(r"\bprogram\b.*\bpro\s+rok\b|grantov[ýé]\s+program", re.I)
SKIP_RE = re.compile(
    r"\b(vzor|příloh|smlouv|manuál|podmínk|žádost|souhlas|schválen|seznam|tréninkov|formulář|rezerv)",
    re.I,
)


def fetch_html(url):
    """vismo: zkus curl-UA, fallback Playwright (vismo občas blokuje urllib)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        return http_util.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  urllib selhalo ({str(e)[:50]}), zkouším Playwright", file=sys.stderr)
        return fetch_playwright(url)


def fetch_playwright(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(user_agent=UA)
        pg.goto(url, wait_until="domcontentloaded", timeout=45000)
        h = pg.content()
        b.close()
        return h


def fetch_bytes(url):
    """Stáhni dokument: curl-UA, fallback Playwright request context."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        return http_util.urlopen(req, timeout=60).read()
    except Exception as e:
        print(f"  doc urllib selhalo ({str(e)[:50]}), Playwright", file=sys.stderr)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            ctx = b.new_context(user_agent=UA)
            r = ctx.request.get(url, timeout=60000)
            data = r.body()
            b.close()
            return data


def doc_to_text(data):
    """Bytes → text. Sniff dle magic: PDF=pdftotext, jinak textutil (DOC/DOCX/ODT/RTF)."""
    is_pdf = data[:5] == b"%PDF-"
    is_zip = data[:2] == b"PK"  # DOCX/ODT
    suffix = ".pdf" if is_pdf else (".docx" if is_zip else ".doc")
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        with open(tmp, "wb") as f:
            f.write(data)
        if is_pdf:
            if not shutil.which("pdftotext"):
                return ""
            out = subprocess.run(["pdftotext", "-layout", tmp, "-"],
                                 capture_output=True, timeout=60)
            return out.stdout.decode("utf-8", "replace")
        else:
            if not shutil.which("textutil"):
                return ""
            out = subprocess.run(["textutil", "-convert", "txt", "-stdout", tmp],
                                 capture_output=True, timeout=60)
            return out.stdout.decode("utf-8", "replace")
    finally:
        os.unlink(tmp)


def _iso(dd, mm, yyyy):
    return f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"


def _czk(s):
    """'600.000 Kč' / '13.000.000' / '1 000 000' → int CZK."""
    d = re.sub(r"[^\d]", "", s or "")
    return int(d) if d else None


def parse_program(text):
    """Vyparsuj termíny / alokaci / max z textu dokumentu programu."""
    rec = {"open_from": None, "deadline": None, "alokace_czk": None, "max_czk": None}
    t = re.sub(r"[ \t\xa0]+", " ", text)

    # "... od DD.MM.YYYY s uzávěrkou dne DD.MM.YYYY ..."
    m = re.search(r"od\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\s+s\s+uzávěrkou\s+dne\s+"
                  r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", t, re.I)
    if m:
        rec["open_from"] = _iso(m.group(1), m.group(2), m.group(3))
        rec["deadline"] = _iso(m.group(4), m.group(5), m.group(6))
    else:
        m = re.search(r"uzávěrk\w*\s+(?:dne\s+)?(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", t, re.I)
        if m:
            rec["deadline"] = _iso(m.group(1), m.group(2), m.group(3))

    # alokace: "... pro rok YYYY je <částka> Kč."
    m = re.search(r"pro\s+rok\s+\d{4}\s+je\s+(?:cca\s+)?([\d.\s\xa0]+)\s*Kč", t, re.I)
    if m:
        rec["alokace_czk"] = _czk(m.group(1))

    # max na žadatele/projekt: "maximálně <částka> Kč"
    m = re.search(r"maximáln[ěí][^.]{0,40}?([\d.\s\xa0]{4,})\s*Kč", t, re.I)
    if m:
        rec["max_czk"] = _czk(m.group(1))

    return rec


def parse_listing(html):
    """Z článku posbírej (název, abs-url) programových dokumentů. Dedup dle url."""
    import html as _h
    i = html.find('id="stranka"')
    seg = html[i:i + 40000] if i >= 0 else html
    progs, seen = [], set()
    for m in re.finditer(r'href="([^"]*File\.ashx[^"]*)"[^>]*>([^<]+)', seg):
        url = _h.unescape(m.group(1))
        if not url.startswith("http"):
            url = BASE + url
        name = _h.unescape(re.sub(r"\s+", " ", m.group(2))).strip()
        # ořízni přípony typu ".docx"/" [PDF, 492 kB]" z viditelného názvu
        name = re.sub(r"\.(docx|pdf|doc|xlsx|xls)\b", "", name, flags=re.I).strip()
        if not name or url in seen:
            continue
        if SKIP_RE.search(name) or not PROG_RE.search(name):
            continue
        seen.add(url)
        progs.append((name, url))
    return progs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_mb.json")
    ap.add_argument("--article", default=ARTICLE)
    a = ap.parse_args()

    out = {
        "source": "mb-net.cz", "kraj": "Středočeský kraj", "obec": "Mladá Boleslav",
        "uroven": "obec", "platform": "mb_vismo", "programs": [],
    }

    def save():
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    html = fetch_html(a.article)
    cands = parse_listing(html)
    print(f"nalezeno {len(cands)} programových odkazů", file=sys.stderr)
    save()  # ulož i kdyby žádný doc nešel stáhnout

    for name, url in cands:
        # url = per-program dokument (distinct), NE sdílený článek → ingest dedup je nesléva.
        # (canon_key bere z článku jen /d-819, takže všechny programy by jinak kolidovaly.)
        rec = {"nazev": name, "open_from": None, "deadline": None, "status": None,
               "alokace_czk": None, "max_czk": None, "popis": None, "eligible": None,
               "kod": None, "url": url, "_article": a.article}
        try:
            data = fetch_bytes(url)
            text = doc_to_text(data)
        except Exception as e:
            print(f"  warn {name[:40]}: {str(e)[:60]}", file=sys.stderr)
            text = ""
        if text:
            rec.update(parse_program(text))
            # popis = první smysluplný odstavec (čl. I deklarace), eligible = okruh žadatelů
            rec["_text"] = text[:6000]
            mp = re.search(r"O\s+dotaci\s+mohou\s+žádat[^.]+\.", text)
            if not mp:
                mp = re.search(r"Žadatel\w*\s+o\s+(?:grant|dotaci)[^.]+\.", text)
            if mp:
                rec["eligible"] = re.sub(r"\s+", " ", mp.group(0)).strip()[:400]
        out["programs"].append(rec)
        save()  # průběžné ukládání
        print(f"  + {name[:45]} | open={rec['open_from']} dl={rec['deadline']} "
              f"alok={rec['alokace_czk']} max={rec['max_czk']}", file=sys.stderr)

    save()
    print(json.dumps({"MARKER": "MB_HARVEST", "kept": len(out["programs"]),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
