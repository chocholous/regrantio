#!/usr/bin/env python3
"""Kladno harvester — dotační programy Statutárního města Kladna (vismo, id_org=6506).

mestokladno.cz/dotace-mesta = rozcestník. Dotace tu NEJSOU dated "výzvy" s rozsahem
open_from–deadline; jsou to TRVALÉ (evergreen) dotační tituly:
  - Přímé dotace z rozpočtu města (ds-200999) — jediný s opakovaným termínem "do 30. listopadu",
    oblasti sport/kultura/volný čas + sociální; žádost písemně / posta@mestokladno.cz
  - Fond primátora města (formuláře ds-29853) — průběžný, bez termínu
  - 5 fondů komisí Rady města (sport / výchova-vzdělávání-osvěta / sociální / kultura /
    životní prostředí) — každý je dokument d-NNN s formuláři, průběžné, bez termínu

Metoda: vismo blokuje běžné fetchery → curl s UA. Listing fondů komisí je v obsahu stránky
ds-29275 (odkazy d-NNN). Strukturovaný parse z #stred bloku, žádný LLM. Deadline (30.11.)
se parsuje z textu jen tam, kde web uvádí; jinak null (status dopočítá ingest).

Lossless: ukládá nazev/url/popis/deadline + plný text #stred bloku do _text.
Ukládá průběžně (flush po každém programu).

Usage: python3 scripts/kladno_harvest.py [--out data/h_mesto_kladno.json]
"""
import argparse, json, re, subprocess, sys
from datetime import date

BASE = "https://www.mestokladno.cz"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# rozcestník fondů komisí — z něj čteme odkazy d-NNN na jednotlivé fondy
KOMISE_LISTING = "/formulare-fondy-komisi-rady-mesta-kladna/ds-29275"
# přímé dotace z rozpočtu (recurring, deadline 30.11.)
PRIME = ("/prime-dotace-z-rozpoctu-mesta/ds-200999", "Přímé dotace z rozpočtu města Kladna")
# fond primátora (formuláře = jediná info stránka, průběžný)
PRIMATOR = ("/formulare-fond-primatora-mesta/ds-29853", "Fond primátora města Kladna")

MONTHS = {"ledna":1,"února":2,"března":3,"dubna":4,"května":5,"června":6,"července":7,
          "srpna":8,"září":9,"října":10,"listopadu":11,"prosince":12}


def fetch(url):
    """Vismo blokuje urllib → curl s prohlížečovým UA, follow redirects."""
    r = subprocess.run(["curl", "-sL", "-A", UA, "--max-time", "40", url],
                       capture_output=True, timeout=60)
    return r.stdout.decode("utf-8", "replace")


def stred(html):
    """Vytáhne hlavní obsahový blok #stred (bez navigace) jako čistý text."""
    i = html.find('id="stred"')
    if i < 0:
        return ""
    j = html.find("Kontext", i)
    seg = html[i:j if j > 0 else i + 20000]
    seg = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", seg, flags=re.S)
    seg = seg.replace('id="stred">', " ", 1)
    txt = re.sub(r"<[^>]+>", " ", seg).replace("&nbsp;", " ")
    import html as _h
    return re.sub(r"\s+", " ", _h.unescape(txt)).strip()


def komise_links(html):
    """Z rozcestníku fondů komisí vytáhne (nazev, abs_url) jednotlivých fondů (d-NNN)."""
    import html as _h
    i = html.find('id="stred"'); j = html.find("Kontext", i)
    c = html[i:j if j > 0 else i + 15000]
    out = []
    for m in re.finditer(r'href="([^"]*d-[0-9][^"]*)"[^>]*>([^<]+)</a>', c):
        nazev = _h.unescape(m.group(2)).strip()
        if len(nazev) < 4:
            continue
        href = _h.unescape(m.group(1))
        url = href if href.startswith("http") else BASE + href
        out.append((nazev, url.split("?")[0]))
    # dedup podle url
    seen, uniq = set(), []
    for n, u in out:
        if u not in seen:
            seen.add(u); uniq.append((n, u))
    return uniq


def parse_deadline(text):
    """Najde 'do 30. listopadu' apod. → vrátí (day, month) nebo None. Bez roku (recurring)."""
    m = re.search(r"do\s+(\d{1,2})\.\s*(" + "|".join(MONTHS) + r")", text, re.I)
    if m:
        return int(m.group(1)), MONTHS[m.group(2).lower()]
    return None


def deadline_iso(dm, today):
    """(den,měsíc) recurring termín → nejbližší budoucí ISO datum (letos/příští rok)."""
    if not dm:
        return None
    d, mo = dm
    try:
        cand = date(today.year, mo, d)
    except ValueError:
        return None
    if cand < today:
        cand = date(today.year + 1, mo, d)
    return cand.isoformat()


def popis(text, nazev):
    """Krátký popis = obsah do prvního 'Odkazy'/'Vložil'/'Sdílet', bez #stred markeru/nadpisu."""
    body = re.split(r"\bOdkazy\b|\bVložil:|\bSdílet na", text)[0].strip()
    body = re.sub(r"\s+", " ", body)
    return body[:600] or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_kladno.json")
    a = ap.parse_args()
    today = date.today()

    out = {"source": "mestokladno.cz", "kraj": "Středočeský kraj", "obec": "Kladno",
           "uroven": "obec", "platform": "kladno_vismo", "programs": []}

    def flush():
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    seen = set()

    def add(nazev, url, text, deadline=None, eligible=None):
        key = (nazev, url)
        if key in seen or not nazev:
            return
        seen.add(key)
        out["programs"].append({
            "nazev": nazev, "open_from": None, "deadline": deadline, "status": None,
            "alokace_czk": None, "max_czk": None, "popis": popis(text, nazev),
            "eligible": eligible, "kod": None, "url": url,
            "_text": text[:3000],
        })
        flush()
        print(f"  + {nazev[:60]}  deadline={deadline}", file=sys.stderr)

    # 1) Přímé dotace z rozpočtu (recurring deadline)
    try:
        t = stred(fetch(BASE + PRIME[0]))
        dl = deadline_iso(parse_deadline(t), today)
        elig = None
        if re.search(r"neziskov|spolk|NNO", t, re.I):
            elig = "nestátní neziskové organizace, spolky"
        add(PRIME[1], BASE + PRIME[0].split("?")[0], t, deadline=dl, eligible=elig)
    except Exception as e:
        print(f"warn PRIME: {str(e)[:80]}", file=sys.stderr)

    # 2) Fond primátora města (průběžný)
    try:
        t = stred(fetch(BASE + PRIMATOR[0]))
        add(PRIMATOR[1], BASE + PRIMATOR[0].split("?")[0], t)
    except Exception as e:
        print(f"warn PRIMATOR: {str(e)[:80]}", file=sys.stderr)

    # 3) Fondy komisí Rady města — rozcestník → jednotlivé fondy
    try:
        listing = fetch(BASE + KOMISE_LISTING)
        links = komise_links(listing)
        print(f"nalezeno {len(links)} fondů komisí", file=sys.stderr)
        for nazev, url in links:
            try:
                t = stred(fetch(url))
            except Exception as e:
                print(f"  warn {nazev[:40]}: {str(e)[:50]}", file=sys.stderr); continue
            dl = deadline_iso(parse_deadline(t), today)
            add(nazev, url, t, deadline=dl)
    except Exception as e:
        print(f"warn KOMISE listing: {str(e)[:80]}", file=sys.stderr)

    flush()
    print(json.dumps({"MARKER": "KLADNO_HARVEST", "kept": len(out["programs"]),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
