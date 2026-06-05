#!/usr/bin/env python3
"""Statutární město Brno — harvester vyhlášených dotačních programů (server-rendered HTML + PDF výzvy).

dotace.brno.cz je rozcestník (hub) → samotné výzvy s termíny žijí ve TŘECH archetypech zdrojů:

  A) WordPress subdomény (ekodotace / socialnipece / zdravi .brno.cz):
     hub `/dotace/` → detail `/dotace/<slug>/`. Termín bývá INLINE v HTML
     ("Lhůta pro podání žádosti ... : 1.2.2026 – 31.10.2026", "v termínu od ... do ..."),
     u zdravi.brno.cz až v linkované "Výzva ... .pdf".
  B) Portál oblastkultury (dotace.brno.cz/oblastkultury): `/vyzvy` listuje pojmenované
     programy (PDF), společné okno příjmu žádostí je oznámeno na `/oblastkultury/`
     ("Podávat žádosti bude možné od 15. 8. 2026 do 30. 9. 2026").
  C) brno.cz/w/<sekce> (sport, mládež, památky, doprava, kreativní průmysl):
     pojmenované programy = nadpis + odkaz "Výzva ... .pdf"; termín JEN uvnitř PDF
     na kanonickém řádku ("Termín podání: od X do Y" / "Lhůta pro podání žádostí\n
     Žádosti se předkládají od X do Y").

Strategie termínů: VYSOKOPRECIZNÍ — kotvíme na štítek (Lhůta/Termín podání/Žádosti se
předkládají), pak bereme PRVNÍ rozsah "od DATUM do DATUM" v okně ~220 znaků. Podporuje
numerické (6.10.2025, 01.02.2026) i slovní české měsíce ("1. října 2025"). Když štítek/
rozsah chybí → datumy null (NEVYMÝŠLÍME). Status dopočítá ingest_kraj.py z termínů.

PDF termíny přes pdftotext -layout (stejně jako dsw2_fetch). Žádný Playwright netřeba —
vše je statické HTTP (HTML inline nebo PDF). Lossless: ukládá _text úryvek + harvest URL.
Bez LLM, bez ořezu sběru; jediné limity jsou safety pojistky (runaway craw l).

Kontrakt (konzumuje scripts/ingest_kraj.py): viz jeho docstring — uroven=obec, kraj=
Jihomoravský kraj, obec=Brno. Ukládá průběžně po každém zdroji do --out.

Usage: python3 scripts/brno_harvest.py [--out data/h_mesto_brno.json]
"""
import argparse, json, os, re, subprocess, sys, tempfile, urllib.request

# ---------------------------------------------------------------- safety pojistky
# NE coverage cap — runaway-ochrana; při dosažení ⚠ log = bug, ne strop.
MAX_DETAIL_PER_HUB = 200      # programů na jeden hub
PDF_FETCH_BYTES_MAX = 30_000_000  # 30 MB / PDF (ochrana proti runaway downloadu)

UA = {"User-Agent": "Mozilla/5.0 (compatible; re-grantio-harvester)"}

# WordPress subdomény: (host, label oblasti pro popis). Detailní URL se objevují z hubu.
WP_SUBDOMAINS = [
    ("https://ekodotace.brno.cz", "životní prostředí / energetika"),
    ("https://socialnipece.brno.cz", "sociální péče"),
    ("https://zdravi.brno.cz", "zdraví a rodinná politika"),
]
# brno.cz/w sekce: (slug, popis oblasti)
BRNO_W_SECTIONS = [
    ("dotace-v-oblasti-sportu", "sport"),
    ("zakladni-informace-o-dotacich-na-volnocasove-aktivity-deti-a-mladeze", "volnočasové aktivity dětí a mládeže"),
    ("dotace-z-oblasti-pamatkove-pece", "památková péče"),
    ("dotace-v-oblasti-dopravy", "doprava"),
    ("mesto-brno-podporuje-projekty-z-kreativnich-odvetvi-formou-dotacniho-programu", "kreativní průmysl"),
]
OBLASTKULTURY = "https://dotace.brno.cz/oblastkultury"

CZ_MONTHS = {
    # genitiv (1. října) i nominativ (1. říjen) — výzvy užívají obojí
    "ledna": 1, "leden": 1, "února": 2, "unora": 2, "únor": 2, "unor": 2,
    "března": 3, "brezna": 3, "březen": 3, "brezen": 3, "dubna": 4, "duben": 4,
    "května": 5, "kvetna": 5, "květen": 5, "kveten": 5, "června": 6, "cervna": 6,
    "červen": 6, "cerven": 6, "července": 7, "cervence": 7, "červenec": 7, "cervenec": 7,
    "srpna": 8, "srpen": 8, "září": 9, "zari": 9, "října": 10, "rijna": 10,
    "říjen": 10, "rijen": 10, "listopadu": 11, "listopad": 11, "prosince": 12, "prosinec": 12,
}

# kanonické štítky uvozující okno příjmu žádostí (na pořadí záleží — specifické první)
TERMIN_ANCHORS = re.compile(
    r"(?:lhůta\s+pro\s+podá(?:ní|vání)\s+žádost\w*"
    r"|termín\s+podání"
    r"|žádosti\s+se\s+předkládají"
    r"|(?:je\s+)?v\s+termínu"
    r"|příjem\s+žádost\w*"
    r"|podávat\s+žádosti\s+bude\s+možné)",
    re.I,
)


def fetch(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    data = urllib.request.urlopen(req, timeout=45).read()
    if binary:
        if len(data) > PDF_FETCH_BYTES_MAX:
            print(f"⚠ {url}: {len(data)}B > PDF_FETCH_BYTES_MAX", file=sys.stderr)
        return data
    return data.decode("utf-8", "replace")


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    for ent, ch in (("&nbsp;", " "), ("\xa0", " "), ("&#8211;", "–"), ("&#8212;", "—"),
                    ("&#8222;", "„"), ("&#8220;", '"'), ("&amp;", "&")):
        h = h.replace(ent, ch)
    h = re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", h))
    return h.strip()


def og_title(html):
    for pat in (r'property="og:title"\s+content="([^"]+)"',
                r"<h1[^>]*>(.*?)</h1>", r"<title[^>]*>(.*?)</title>"):
        m = re.search(pat, html, re.S)
        if m:
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(1))).strip()
            for ent, ch in (("&#8211;", "–"), ("&#8222;", "„"), ("&#8220;", '"'),
                            ("&#8211", "–"), ("&amp;", "&")):
                t = t.replace(ent, ch)
            # odstřihni site-suffix " – Ekodotace" / " – Zdraví Brno" / " - Brno"
            t = re.split(r"\s[–-]\s(?:Ekodotace|Zdraví Brno|PSP|Brno)\b", t)[0].strip()
            if t and t.lower() != "dotace":
                return t
    return None


def _iso(s):
    """'6.10.2025' / '01. 02. 2026' / '1. října 2025' → ISO; jinak None."""
    s = (s or "").strip().rstrip(".")
    m = re.match(r"(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})", s)
    if m:
        return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}"
    m = re.match(r"(\d{1,2})\.\s+([a-zá-žěščřžýáíé]+)\s+(\d{4})", s, re.I)
    if m and m.group(2).lower() in CZ_MONTHS:
        return f"{int(m[3]):04d}-{CZ_MONTHS[m.group(2).lower()]:02d}-{int(m[1]):02d}"
    return None


# rozsah za štítkem: "od DATUM do DATUM" nebo "DATUM – DATUM" (numerický i slovní)
_DATE = r"(\d{1,2}\.\s?\d{1,2}\.\s?\d{4}|\d{1,2}\.\s+[a-zá-žěščřžýáíé]+\s+\d{4})"
# rozsah 'od X do Y'; 'X – Y' / 'X až Y' (oddělovač pomlčka NEBO "až")
RANGE_OD_DO = re.compile(r"od\s+" + _DATE + r"\s+(?:do|až)\s+" + _DATE, re.I)
RANGE_DASH = re.compile(_DATE + r"\s*(?:[–—-]|až)\s*" + _DATE, re.I)
SINGLE_OD = re.compile(r"od\s+" + _DATE, re.I)   # jen začátek příjmu
SINGLE_DO = re.compile(r"do\s+" + _DATE, re.I)   # jen konec příjmu
SINGLE_ANY = re.compile(_DATE)


def extract_window(text):
    """Najdi kanonický štítek termínu, pak v okně ~220 znaků za ním vytěž okno příjmu.
    Priorita: rozsah 'od X do/až Y' / 'X – Y' (→open_from+deadline), pak samostatné
    'od X' (→open_from), 'do X' nebo holé datum (→deadline). Směr respektujeme — datum
    NEpřiřazujeme do špatného slotu. Vrací (open_from, deadline) nebo (None, None)."""
    text = text.replace("\xa0", " ")
    for am in TERMIN_ANCHORS.finditer(text):
        win = text[am.end(): am.end() + 220]
        m = RANGE_OD_DO.search(win) or RANGE_DASH.search(win)
        if m:
            of, dl = _iso(m.group(1)), _iso(m.group(2))
            if of or dl:
                return of, dl
        mdo, mod = SINGLE_DO.search(win), SINGLE_OD.search(win)
        if mdo and _iso(mdo.group(1)):
            return None, _iso(mdo.group(1))           # "do X" → deadline
        if mod and _iso(mod.group(1)):
            return _iso(mod.group(1)), None           # "od X" → open_from
        many = SINGLE_ANY.search(win)
        if many and _iso(many.group(1)):
            return None, _iso(many.group(1))          # holé datum u štítku lhůty → deadline
    return None, None


def pdf_to_text(data):
    f = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        f.write(data); f.close()
        r = subprocess.run(["pdftotext", "-layout", f.name, "-"],
                           capture_output=True, timeout=90)
        return r.stdout.decode("utf-8", "replace")
    except Exception as e:
        print(f"  warn pdftotext: {str(e)[:60]}", file=sys.stderr)
        return ""
    finally:
        try: os.unlink(f.name)
        except OSError: pass


def _abs(base, href):
    if href.startswith("http"):
        return href
    if href.startswith("/"):
        m = re.match(r"(https?://[^/]+)", base)
        return (m.group(1) if m else base) + href
    return base.rstrip("/") + "/" + href


# PDF, který POPISUJE program/výzvu (ne formulář žádosti / vyúčtování / smlouva / koncepce)
PROG_PDF_POS = re.compile(r"výzv|dotační program|program\s+\d{4}|pro kreativní brno|na obnovu", re.I)
PROG_PDF_NEG = re.compile(
    r"žádost o (?:dotaci|poskytnutí)|formulář|vzor|závěrečná zpráva|vyúčtování|finanč\w*\s+vypořád"
    r"|návrh smlouvy|oznámení|koncepce|metodik|prezentace|bodové hodnocení|příloha", re.I)


def vyzva_pdf_links(html, base):
    """Odkazy na PDF popisující program/výzvu + text odkazu (= název programu). Vyřazuje
    formuláře žádostí, vyúčtování, smlouvy, koncepce. Dedup dle URL."""
    out, seen = [], set()
    for m in re.finditer(r'<a[^>]+href="([^"]+\.pdf[^"]*)"[^>]*>(.*?)</a>', html, re.S):
        href, txt = m.group(1), re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2))).strip()
        for ent, ch in (("&#8211;", "–"), ("&amp;", "&")):
            txt = txt.replace(ent, ch)
        blob = href + " " + txt
        if PROG_PDF_NEG.search(txt):
            continue
        if PROG_PDF_POS.search(blob) and href not in seen:
            seen.add(href)
            out.append((_abs(base, href), txt))
    return out


# ----------------------------------------------------------------- A) WordPress
def harvest_wp(host, oblast):
    progs = []
    try:
        hub = fetch(host + "/dotace/")
    except Exception as e:
        print(f"⚠ {host}/dotace/: {str(e)[:60]}", file=sys.stderr)
        return progs
    detail_urls, seen = [], set()
    for m in re.finditer(r'href="(' + re.escape(host) + r'/dotace/[a-z0-9\-]+/)"', hub):
        u = m.group(1)
        if u.rstrip("/") == (host + "/dotace") or u in seen:
            continue
        if re.search(r"/(individualni|prehled|schvalen)", u):  # ne-výzvové sekce
            continue
        seen.add(u); detail_urls.append(u)
    if len(detail_urls) >= MAX_DETAIL_PER_HUB:
        print(f"⚠ {host}: MAX_DETAIL_PER_HUB", file=sys.stderr)
    for u in detail_urls[:MAX_DETAIL_PER_HUB]:
        try:
            html = fetch(u)
        except Exception as e:
            print(f"  warn {u}: {str(e)[:50]}", file=sys.stderr); continue
        text = detext(html)
        nazev = og_title(html) or u.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
        of, dl = extract_window(text)
        # fallback: termín v linkované Výzva PDF (zdravi.brno.cz)
        used_pdf = None
        if not (of or dl):
            for purl, _t in vyzva_pdf_links(html, u):
                try:
                    pof, pdl = extract_window(pdf_to_text(fetch(purl, binary=True)))
                except Exception as e:
                    print(f"  warn pdf {purl}: {str(e)[:50]}", file=sys.stderr); continue
                if pof or pdl:
                    of, dl, used_pdf = pof, pdl, purl; break
        progs.append({
            "nazev": nazev, "open_from": of, "deadline": dl, "status": None,
            "alokace_czk": None, "max_czk": None, "popis": oblast,
            "eligible": None, "kod": None, "url": u,
            "_text": text[:1500], "_termin_pdf": used_pdf,
        })
    return progs


# --------------------------------------------------------- B) oblastkultury portál
def harvest_oblastkultury():
    progs = []
    try:
        portal = detext(fetch(OBLASTKULTURY + "/"))
        vyzvy_html = fetch(OBLASTKULTURY + "/vyzvy")
    except Exception as e:
        print(f"⚠ oblastkultury: {str(e)[:60]}", file=sys.stderr)
        return progs
    of, dl = extract_window(portal)   # společné okno příjmu pro všechny programy kultury
    vtext = detext(vyzvy_html)
    # programy = řádky "Dotační program pro poskytování dotací v oblasti ..."
    for m in re.finditer(r"(Dotační program pro poskytování dotací[^\n]+?)(?:,?\s*form[áa]t PDF[^\n]*)?$",
                         vtext, re.M):
        nazev = re.sub(r",?\s*form[áa]t PDF.*$", "", m.group(1)).strip()
        if len(nazev) < 25:
            continue
        progs.append({
            "nazev": nazev, "open_from": of, "deadline": dl, "status": None,
            "alokace_czk": None, "max_czk": None, "popis": "kultura",
            "eligible": None, "kod": None, "url": OBLASTKULTURY + "/vyzvy",
            "_text": nazev, "_termin_pdf": None,
        })
    return progs


# -------------------------------------------------------------- C) brno.cz/w sekce
def harvest_brno_w(slug, oblast):
    progs = []
    url = "https://www.brno.cz/w/" + slug
    try:
        html = fetch(url)
    except Exception as e:
        print(f"⚠ {url}: {str(e)[:60]}", file=sys.stderr)
        return progs
    links = vyzva_pdf_links(html, "https://www.brno.cz")
    if len(links) >= MAX_DETAIL_PER_HUB:
        print(f"⚠ {url}: MAX_DETAIL_PER_HUB", file=sys.stderr)
    # brno.cz/w listuje aktuální i archivní ročníky téhož programu (…_2026.pdf vs
    # …_2025.pdf). Cíl = aktuálně vyhlášené → drž jen NEJVYŠŠÍ ročník přítomný v sekci
    # (data-driven, žádný natvrdo zadaný rok). Výzvy bez roku v URL ponech vždy.
    years = [int(y) for purl, _ in links for y in re.findall(r"_(20\d\d)[._]", purl)]
    max_year = max(years) if years else None
    for purl, nazev in links[:MAX_DETAIL_PER_HUB]:
        yy = re.findall(r"_(20\d\d)[._]", purl)
        if max_year is not None and yy and int(yy[-1]) < max_year:
            continue  # archivní ročník
        try:
            of, dl = extract_window(pdf_to_text(fetch(purl, binary=True)))
        except Exception as e:
            print(f"  warn pdf {purl}: {str(e)[:50]}", file=sys.stderr); of = dl = None
        nazev = re.sub(r"\s*[–-]\s*Výzva k podání žádost.*$", "", nazev).strip()
        nazev = re.sub(r"\s*\((?:PDF|DOCX?|XLSX?)[^)]*\)\s*$", "", nazev, flags=re.I).strip() or nazev
        progs.append({
            "nazev": nazev, "open_from": of, "deadline": dl, "status": None,
            "alokace_czk": None, "max_czk": None, "popis": oblast,
            "eligible": None, "kod": None, "url": url,
            "_text": nazev, "_termin_pdf": purl,
        })
    return progs


def dedup(progs):
    out, seen = [], set()
    for p in progs:
        key = (p.get("url"), (p.get("nazev") or "").strip().lower(),
               p.get("open_from"), p.get("deadline"))
        if key in seen:
            continue
        seen.add(key); out.append(p)
    return out


def save(out_path, all_progs):
    out = {
        "source": "dotace.brno.cz", "kraj": "Jihomoravský kraj", "obec": "Brno",
        "uroven": "obec", "platform": "brno_nette",
        "programs": dedup(all_progs),
    }
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_brno.json")
    a = ap.parse_args()

    all_progs = []

    for host, oblast in WP_SUBDOMAINS:
        ps = harvest_wp(host, oblast)
        all_progs += ps
        save(a.out, all_progs)  # průběžné ukládání
        print(f"WP {host}: {len(ps)}", file=sys.stderr)

    ps = harvest_oblastkultury()
    all_progs += ps; save(a.out, all_progs)
    print(f"oblastkultury: {len(ps)}", file=sys.stderr)

    for slug, oblast in BRNO_W_SECTIONS:
        ps = harvest_brno_w(slug, oblast)
        all_progs += ps; save(a.out, all_progs)
        print(f"brno.cz/w/{slug}: {len(ps)}", file=sys.stderr)

    final = save(a.out, all_progs)
    with_dl = sum(1 for p in final["programs"] if p["deadline"])
    print(json.dumps({"MARKER": "BRNO_HARVEST", "kept": len(final["programs"]),
                      "with_deadline": with_dl, "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
