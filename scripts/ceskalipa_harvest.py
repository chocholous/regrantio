#!/usr/bin/env python3
"""Harvester dotačních programů statutárního města Česká Lípa (mucl.cz, vismo CMS).

METODA: server-rendered HTML (vismo). Curl/urllib stačí (vismo občas blokuje fetchery →
fallback hlavička Mozilla; Playwright nepotřeba — data jsou v HTML, ne v JS). Sekce
"Dary a dotace" (ms-46288) má v levém submenu seznam JEDNOTLIVÝCH dotačních programů
(v oblasti sportu / kultury / vzdělávání / ŽP / sociální / cestovního ruchu / prevence
kriminality / na obnovu nemovitostí / na podporu zdravotních služeb / DČOV / IFP / MK-UPP).
Submenu = autoritativní rozcestník na detaily programů → odtud bereme URL (ne homepage,
ta dotace nelinkuje).

Detail = próza. Z těla parsujeme:
  - název  = <title> (první segment před prvním ':')
  - okno příjmu = "od <datum> do <datum>" JEN v kontextu příjmu/posílání žádostí; podporuje
    numerický (09.03.2026) i slovní český měsíc (9. března 2026). Víc oken na stránce
    (sport: kat. I-IV vs kat. V) → víc záznamů, kód <kód kategorie> rozliší.
  - alokace = "finanční objem ... Kč"
  - popis   = první "Dotační program ... schválen ..." věta
Co není v textu (často v přiloženém PDF Pravidel) = null. Žádný LLM. Status dopočítá ingest.

Výstup dle KONTRAKTU pro scripts/ingest_kraj.py (uroven=obec). Ukládá průběžně.

Usage: python3 scripts/ceskalipa_harvest.py [--out data/h_mesto_ceskalipa.json]
"""
import argparse, json, re, sys, urllib.request

BASE = "https://www.mucl.cz"
# vstupní bod = sekce Dary a dotace; z jejího submenu vyčteme detaily programů
SECTION = "/dotace%2Da%2Ddary/ms-46288/p1=46576"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# odkazy detailů programů ve submenu Dary a dotace (ds-/ms- + slug grantové oblasti)
PROG_HREF = re.compile(
    r'href="(/[^"]*(?:oblasti|na%2Dobnovu|na%2Dpodporu|individualni%2Dfinancni|'
    r'program%2Ddcov|dotacni%2Dprogramy%2Dmk)[^"]*/(?:ds|ms|d)-\d+[^"]*)"',
    re.I)

CZ_MONTH = {"ledna": 1, "února": 2, "unora": 2, "března": 3, "brezna": 3, "dubna": 4,
            "května": 5, "kvetna": 5, "června": 6, "cervna": 6, "července": 7, "cervence": 7,
            "srpna": 8, "září": 9, "zari": 9, "října": 10, "rijna": 10, "listopadu": 11,
            "prosince": 12}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def title_name(html):
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    if not m:
        return None
    t = re.sub(r"\s+", " ", m.group(1)).strip()
    # "Dotační program v oblasti sportu: v oblasti sportu: Česká Lípa" → 1. segment
    name = t.split(":")[0].strip()
    return name or None


def body_text(html):
    """Hlavní obsah: od breadcrumb 'Cesta:' po 'Kontext'/'Umístění' (ořízne levé menu/patičku)."""
    i = html.find("Cesta:")
    seg = html[i:] if i >= 0 else html
    seg = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", seg, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", seg)
    t = (t.replace("&nbsp;", " ").replace("&ndash;", "-").replace("&ndash", "-")
          .replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
          .replace("&gt;", ">").replace("&lt;", "<"))
    t = re.sub(r"\s+", " ", t).strip()
    # tělo programu končí u kontextového bloku / patičky
    for stop in ("Kontext Umístění", "Umístění:", "Počet návštěv", "Hlavní nabídka: Dary"):
        j = t.find(stop)
        if j > 200:
            t = t[:j]
            break
    return t


def _iso(d, m, y):
    try:
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except Exception:
        return None


# numerické datum (toleruje mezery/chybějící tečku): 09.03.2026 | 9. 3. 2026
DNUM = r"(\d{1,2})\.?\s*(\d{1,2})\.?\s*(\d{4})"
# slovní datum: 9. března 2026 (rok smí chybět u 'od' → doplní se z 'do')
DTXT = r"(\d{1,2})\.?\s*([a-zěščřžýáíéúůóďťňA-ZĚŠČŘŽÝÁÍÉÚŮÓ]+)(?:\s+(\d{4}))?"
# fráze uvozující okno příjmu žádostí
RECV = r"(?:posílat|posíláte|přijímán\w*|příjm\w*|podáv\w*|předkl\w*|posláte|posílá\w*)"


def _txt_iso(d, mon, y):
    m = CZ_MONTH.get(mon.lower())
    return _iso(d, m, y) if m else None


def parse_windows(body):
    """Vrať list (open_from, deadline, kontext_kódu) párů 'od ... do ...' u příjmu žádostí.

    Bere JEN okna ukotvená frází o příjmu/posílání žádostí (jinde 'od/do' = čerpání/
    vyúčtování → falešný deadline). Kategorie (I./II./V.) bere jako kód-kontext, pokud
    se okno váže ke konkrétní kategorii.
    """
    out = []
    # 1) okno s numerickými daty: 'od 09.03.2026 do 23.03.2026'
    pat_num = (RECV + r".{0,80}?\bod\s+" + DNUM + r".{0,40}?\bdo\s+" + DNUM)
    for m in re.finditer(pat_num, body, re.I | re.S):
        of = _iso(m.group(1), m.group(2), m.group(3))
        de = _iso(m.group(4), m.group(5), m.group(6))
        kod = _cat_before(body, m.start())
        if of and de:
            out.append((of, de, kod))
    # 2) okno se slovními měsíci: 'od 9. března do 23. března 2026'
    pat_txt = (RECV + r".{0,80}?\bod\s+" + DTXT + r".{0,40}?\bdo\s+" + DTXT)
    for m in re.finditer(pat_txt, body, re.I | re.S):
        y2 = m.group(6)
        of = _txt_iso(m.group(1), m.group(2), m.group(3) or y2)
        de = _txt_iso(m.group(4), m.group(5), y2 or m.group(3))
        kod = _cat_before(body, m.start())
        if of and de:
            out.append((of, de, kod))
    # dedup (of,de)
    seen, ded = set(), []
    for of, de, kod in out:
        if (of, de) in seen:
            continue
        seen.add((of, de)); ded.append((of, de, kod))
    return ded


def _cat_before(body, pos):
    """Nejbližší předchozí 'Žádosti v kategoriích I. – IV.' / 'v kategorii V.' label."""
    seg = body[max(0, pos - 120):pos]
    m = re.findall(r"kategori\w*\s+([IVX]+\.(?:\s*[–\-]\s*[IVX]+\.)?)", seg)
    return m[-1].strip() if m else None


def parse_alokace(body):
    """CELKOVÁ alokace programu. Pozor: u sportu je 'finanční objem' i u jednotlivých
    kategorií (13/0,5/5/2,4 mil.) — celek je 'Celkový předpokládaný finanční objem ...
    činí 21 000 000 Kč'. Proto napřed zkus celkovou větu (delší mezera k číslu), až pak
    první 'finanční objem'."""
    # 1) celková alokace: 'Celkový ... finanční objem ... činí <num> Kč' — uvnitř JEDNÉ věty
    #    (žádná tečka mezi 'celkov' a číslem), aby se nechytla kategorie 'finanční objem 13 mil.'
    m = re.search(r"celkov\w*[^.]{0,200}?finanč\w*\s+objem[^.]{0,160}?"
                  r"([\d  \xa0\.]{6,})\s*Kč", body, re.I)
    if m:
        digs = re.sub(r"[^\d]", "", m.group(1))
        if digs:
            return int(digs)
    # 2) fallback: první 'finanční objem <num> Kč' (program bez kategorií)
    m = re.search(r"finanč\w*\s+objem[^.\d]{0,30}?([\d  \xa0\.]{4,})\s*Kč", body, re.I)
    if not m:
        return None
    digs = re.sub(r"[^\d]", "", m.group(1))
    return int(digs) if digs else None


def parse_max(body):
    """max výše dotace na žadatele — JEN když je na stránce jednoznačná (1 hodnota).
    U programů s kategoriemi (sport) je max per-kategorie různý → ponech null (neslévej)."""
    vals = re.findall(r"[Mm]aximální výše[^.]{0,60}?dotace[^.]{0,40}?([\d  \xa0]{4,})\s*Kč", body)
    digs = list(dict.fromkeys(re.sub(r"[^\d]", "", v) for v in vals if re.sub(r"[^\d]", "", v)))
    return int(digs[0]) if len(digs) == 1 else None


def parse_popis(body):
    """'Dotační program ... byl schválen ... usnesením č. ...' věta. Tečky uvnitř data
    (26. 1. 2026) a č. usnesení nesmí větu uťat → konec až 'usnesením/usnesení č. <kód>'."""
    m = re.search(r"(Dotační program\s+(?:pro\s+|na\s+|v\s+)?[^\n]{20,400}?"
                  r"schválen[^\n]{0,200}?(?:usnesení\w*\s+č\.\s*\S+|\d{1,2}\.\s*\d{1,2}\.\s*\d{4})\.?)",
                  body, re.S)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    m = re.search(r"(Dotační program[^.]{20,260}?\.)", body, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None


def parse_detail(html, url):
    name = title_name(html)
    body = body_text(html)
    wins = parse_windows(body)
    alok = parse_alokace(body)
    popis = parse_popis(body)
    base = {"nazev": name, "status": None, "alokace_czk": alok, "max_czk": parse_max(body),
            "popis": popis, "eligible": None, "url": url}
    recs = []
    if wins:
        multi = len(wins) > 1
        for of, de, kod in wins:
            r = dict(base)
            r["open_from"] = of
            r["deadline"] = de
            # u víc oken rozliš kategorií, ať se dedup neslijí na 1 grant
            r["kod"] = kod
            if multi and kod:
                r["nazev"] = f"{name} (kategorie {kod})"
            recs.append(r)
    else:
        r = dict(base)
        r.update({"open_from": None, "deadline": None, "kod": None})
        recs.append(r)
    return recs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_ceskalipa.json")
    a = ap.parse_args()

    out = {"source": "mucl.cz", "kraj": "Liberecký kraj", "obec": "Česká Lípa",
           "uroven": "obec", "platform": "ceskalipa_vismo", "programs": []}

    def save():
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    save()  # založ soubor hned

    sec = fetch(BASE + SECTION)
    hrefs = []
    for m in PROG_HREF.finditer(sec):
        h = m.group(1)
        if h not in hrefs:
            hrefs.append(h)
    print(f"submenu Dary a dotace: {len(hrefs)} programových detailů", file=sys.stderr)

    seen = set()  # dedup dle (nazev)
    for href in hrefs:
        url = BASE + href
        try:
            html = fetch(url)
        except Exception as e:
            print(f"  warn {href}: {str(e)[:60]}", file=sys.stderr)
            continue
        for rec in parse_detail(html, url):
            if not rec["nazev"]:
                print(f"  skip (no title): {href}", file=sys.stderr); continue
            key = re.sub(r"[^a-z0-9]", "", rec["nazev"].lower())
            if key in seen:
                continue
            seen.add(key)
            out["programs"].append(rec)
            save()
            print(f"  + {rec['nazev']}  open={rec['open_from']} dl={rec['deadline']} "
                  f"alok={rec['alokace_czk']}", file=sys.stderr)

    save()
    print(json.dumps({"MARKER": "CESKALIPA_HARVEST", "kept": len(out["programs"]),
                      "with_deadline": sum(1 for p in out["programs"] if p["deadline"]),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
