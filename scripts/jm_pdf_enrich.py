#!/usr/bin/env python3
"""JMK vrstva 2: stáhni PDF pravidel z GINIS USU (session-bound) a vytěž REÁLNÝ
termín podání žádostí + alokaci + oprávněné žadatele → přepiš do data/h_kraj_jm.json.

KONTEXT: _attachments PDF na eud.jmk.cz jsou session-bound (přímý curl → 302 login).
Reuse session jako jm_harvest.py: Playwright otevře Seznam.aspx (získá ASP.NET_SessionId),
pak per program Detail.aspx (registruje soubory) → ctx.request.get na Dokument.aspx (sdílí cookies).

open_from/deadline v souboru = OKNO VÝVĚSKY, NE termín podání. Tady to opravujeme z PDF
pravidel ("Lhůta pro podávání žádostí: od DD.MM.YYYY ... do DD.MM.YYYY").

Lossless kontrakt h_kraj_jm.json: NEMĚNÍME klíče ani pole, jen přepisujeme hodnoty,
co najdeme v PDF; co nenajdeme, NEMĚNÍME. Ukládáme PRŮBĚŽNĚ po každém programu.
"""
import json, re, sys, subprocess, tempfile, os
from playwright.sync_api import sync_playwright

DATA = "data/h_kraj_jm.json"
SEZNAM = "https://eud.jmk.cz/Gordic/Ginis/App/UDE01/Seznam.aspx?a=1"

# normalizace mezer v číslech (NBSP, narrow NBSP, thin space → obyčejná mezera)
SPACES = "    "

# Hlavní PDF pravidel: jméno ~ název programu / "Dotační program" / "Pravidla" / "Výzva".
# NE vzory/přílohy/smlouvy.
NEG_RE = re.compile(r"(vzor|příloha\s*č|priloh|smlouv|rozpočet|žádost(i|í)\b|čestn[éá]|"
                    r"manuál|finanční\s*vypořád|finanční\s*plán|potvrzení|projektov[ýé]\s*záměr)", re.I)
POS_RE = re.compile(r"(dotačn[íě]\s*program|pravidl|výzv|podpor|program)", re.I)

# --- termín podání ---------------------------------------------------------
LHUTA_HDR = re.compile(r"lhůt[ae].{0,40}?podáv[áa]n[íi].{0,40}?žádost", re.I | re.S)
TERMIN_HDR = re.compile(r"(termín|lhůt[ae]).{0,30}?(pro\s+)?podán[íi]", re.I | re.S)
OD_DO = re.compile(r"od\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})"
                   r"(?:[^\d]{0,40}?\d{1,2}[:.]\d{2})?"
                   r"[^\d]{0,40}?do\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", re.I | re.S)
DO_ONLY = re.compile(r"do\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", re.I)

# --- alokace ---------------------------------------------------------------
# Anchory pro "kolik je na program celkem". Číslo bývá až o pár vět dál → okno 0..220.
# Vstup je předem normalizovaný (NBSP→mezera), takže v číslu stačí [\d .].
ALOK_RE = re.compile(
    r"(?:celkov[áé]\s*výše\s*alokace"
    r"|(?:předpokládan[ýé]\s*)?celkov[ýá]\s*objem\s*(?:peněžních|finančních)?\s*prostředků"
    r"|objem\s*(?:peněžních|finančních)\s*prostředků\s*vyčleněn"
    r"|celkov[áé]\s*částka\s*(?:určená|vyčleněná)"
    r"|vyčleněna\s*částka"
    r"|alokace\s*(?:programu|dotačního\s*programu))"
    r"[^0-9]{0,220}?([\d .]{6,})\s*(?:,-\s*)?Kč", re.I | re.S)

# --- oprávnění žadatelé ----------------------------------------------------
ELIG_HDR = re.compile(r"okruh\s+(?:oprávněných|způsobilých)\s+žadatel", re.I)


def iso(d, m, y):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def parse_amount(raw):
    digits = re.sub(r"[^\d]", "", raw)
    return int(digits) if digits else None


def extract_deadline(text):
    """Vrať (open_from, deadline) z PDF, nebo (None,None). Hledá poblíž nadpisu Lhůta."""
    for hdr in (LHUTA_HDR, TERMIN_HDR):
        for m in hdr.finditer(text):
            window = text[m.start(): m.start() + 400]
            od = OD_DO.search(window)
            if od:
                return iso(od[1], od[2], od[3]), iso(od[4], od[5], od[6])
            do = DO_ONLY.search(window)
            if do:
                return None, iso(do[1], do[2], do[3])
    # fallback: kdekoli "od ... do ..." s kontextem podání žádosti poblíž
    for od in OD_DO.finditer(text):
        ctx = text[max(0, od.start() - 120): od.start()]
        if re.search(r"podáv|podán[íi]|žádost", ctx, re.I):
            return iso(od[1], od[2], od[3]), iso(od[4], od[5], od[6])
    return None, None


def extract_alokace(text):
    m = ALOK_RE.search(text)
    if not m:
        return None
    amt = parse_amount(m[1])
    if amt and 50_000 <= amt <= 10_000_000_000:
        return amt
    return None


def extract_eligible(text):
    m = ELIG_HDR.search(text)
    if not m:
        return None
    tail = text[m.end(): m.end() + 1400]
    # dojeď do konce nadpisové věty (zbytek řádku nadpisu, např. "ů a lokalizace...")
    nl = tail.find("\n")
    if 0 <= nl <= 80:
        tail = tail[nl:]
    # ořízni u dalšího číslovaného nadpisu sekce
    cut = re.search(r"\n\s*\d{1,2}(?:\.\d+)?\.\s+[A-ZČŠŘŽÁÉÍÓÚŮ]", tail)
    if cut:
        tail = tail[:cut.start()]
    tail = re.sub(r"\s+", " ", tail).strip()
    # zahoď zbytkový fragment nadpisu na začátku (malé písmeno / "ů")
    tail = re.sub(r"^[a-zěščřžýáíéúůóďťň]{0,3}\s+", "", tail)
    if len(tail) < 25:
        return None
    return tail[:600]


def pdftotext(pdf_bytes):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        path = f.name
    try:
        r = subprocess.run(["pdftotext", "-layout", path, "-"],
                           capture_output=True, timeout=60)
        raw = r.stdout.decode("utf-8", "replace")
        # normalizuj exotické mezery (NBSP atd.) na obyčejnou — kvůli číslům a regexům
        return re.sub(f"[{SPACES}]", " ", raw)
    finally:
        os.unlink(path)


def pick_main_pdf(prog):
    """Vyber hlavní PDF pravidel z _attachments."""
    atts = [a for a in prog.get("_attachments", []) if a.get("url")]
    if not atts:
        return None
    pdfs = [a for a in atts if a["name"].lower().endswith(".pdf")] or atts
    scored = []
    for a in pdfs:
        n = a["name"]
        if NEG_RE.search(n):
            score = -10
        elif POS_RE.search(n):
            score = 5
        else:
            score = 0
        scored.append((score, a))
    scored.sort(key=lambda x: -x[0])
    best = scored[0]
    return best[1] if best[0] > -10 else pdfs[0]


def main():
    data = json.load(open(DATA, encoding="utf-8"))
    progs = data["programs"]

    stats = {"pdf_dl": 0, "pdf_fail": 0, "no_text": 0,
             "deadline": 0, "alokace": 0, "eligible": 0}
    samples = []

    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context()
        pg = ctx.new_page()
        pg.goto(SEZNAM, wait_until="networkidle", timeout=45000)
        print(f"session cookies: {[c['name'] for c in ctx.cookies()]}", file=sys.stderr)

        for i, prog in enumerate(progs):
            nazev = prog["nazev"]
            main_att = pick_main_pdf(prog)
            if not main_att:
                print(f"[{i}] NO-ATT {nazev[:55]}", file=sys.stderr)
                continue
            try:
                if prog.get("url") and "Detail.aspx" in prog["url"]:
                    pg.goto(prog["url"], wait_until="networkidle", timeout=45000)
            except Exception as e:
                print(f"[{i}] detail warn: {str(e)[:50]}", file=sys.stderr)
            try:
                r = ctx.request.get(main_att["url"], timeout=60000)
                if r.status != 200:
                    print(f"[{i}] PDF HTTP {r.status} {nazev[:45]}", file=sys.stderr)
                    stats["pdf_fail"] += 1
                    continue
                body = r.body()
                if not body.startswith(b"%PDF"):
                    print(f"[{i}] not-PDF (magic {body[:8]!r}) {nazev[:45]}", file=sys.stderr)
                    stats["pdf_fail"] += 1
                    continue
                stats["pdf_dl"] += 1
                open(f"/tmp/jm_{i:02d}.pdf", "wb").write(body)
            except Exception as e:
                print(f"[{i}] PDF dl err: {str(e)[:60]}", file=sys.stderr)
                stats["pdf_fail"] += 1
                continue

            text = pdftotext(body)
            if len(text.strip()) < 200:
                print(f"[{i}] NO-TEXT (scan?) {nazev[:45]} | {main_att['name'][:40]}", file=sys.stderr)
                stats["no_text"] += 1
                continue

            old_dl = prog.get("deadline")
            of, dl = extract_deadline(text)
            alok = extract_alokace(text)
            elig = extract_eligible(text)

            changed = []
            if dl:
                prog["deadline"] = dl
                if of:
                    prog["open_from"] = of
                prog["_deadline_source"] = "pdf"
                stats["deadline"] += 1
                changed.append("deadline")
            if alok and not prog.get("alokace_czk"):
                prog["alokace_czk"] = alok
                stats["alokace"] += 1
                changed.append("alokace")
            if elig and not prog.get("eligible"):
                prog["eligible"] = elig
                stats["eligible"] += 1
                changed.append("eligible")

            if len(samples) < 8 and dl:
                samples.append({"nazev": nazev[:60], "old_deadline": old_dl,
                                "new_deadline": dl, "alokace": alok})

            print(f"[{i}] OK {nazev[:45]:45} | dl:{old_dl}->{dl} | alok:{alok} | {','.join(changed) or '-'}",
                  file=sys.stderr)

            json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

        b.close()

    json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "JM_PDF_ENRICH", "stats": stats, "samples": samples},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
