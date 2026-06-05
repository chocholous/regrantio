#!/usr/bin/env python3
"""Středočeský kraj harvester — dotační programy krajských fondů (server-rendered HTML, bez WAF).

Rozcestník https://stredoceskykraj.cz/web/urad/prehled-dotaci odkazuje na kategorie "Dle oblastí"
(sociální, zdravotnictví, bezpečnost, věda, cestovní ruch, kultura, sport, ŽP, kotlíkové, ostatní,
regionální rozvoj, doprava, ...). Každá kategorie má sekci "Dotační tituly" / "Rozcestník" s odkazy
na jednotlivé programy (/web/dotace/<slug>). Detail programu je čistě próza s blokem termínu:

  "Lhůta pro podávání žádostí je stanovena od DD. M. YYYY [od HH:MM] do DD. M. YYYY [do HH:MM]"
  "Termín podávání žádostí je od DD. <měsíc> YYYY do DD. <měsíc> YYYY"   (slovní měsíc taky)
  "Příjem žádostí od ... do ..."

→ strukturovaný regex-parse, žádný LLM. Datum ve dvou tvarech: numerické (4. 11. 2025)
i slovní (1. července 2026). Alokace ("... Kč") jen když je v kontextu objemu fondu/alokace
(jinak null — náhodné částky v textu = max_czk neznámé, contract dovoluje null).

Cíl = otevřené VÝZVY; harvest je ovšem LOSSLESS (bere všechny ročníky), status open/closed
dopočítá ingest z termínů (contract: status=null). Dedup dle URL.

POZOR: dotace.stredoceskykraj.cz = SPA login → NEPOUŽÍVAT. Vše jede přes statické HTML.

Usage: python3 scripts/stredocesky_harvest.py [--out data/h_kraj_stredocesky.json]
"""
import argparse, json, re, sys, time, urllib.request

BASE = "https://stredoceskykraj.cz"
ROZCESTNIK = "/web/urad/prehled-dotaci"
# safety pojistka proti runaway (NE coverage cap — při dosažení ⚠ log = bug)
MAX_DETAILS = 1000

MESICE = {
    "ledna": 1, "února": 2, "unora": 2, "března": 3, "brezna": 3, "dubna": 4,
    "května": 5, "kvetna": 5, "června": 6, "cervna": 6, "července": 7, "cervence": 7,
    "srpna": 8, "září": 9, "zari": 9, "října": 10, "rijna": 10, "listopadu": 11,
    "prosince": 12,
}

# blok "od <datum> [od HH:MM hodin] do <datum> [do HH:MM hodin]" — datum numerické i slovní
_DATE = r"\d{1,2}\.\s*(?:\d{1,2}\.\s*\d{4}|[a-zžščřďťňáéíóúůýě]+\s+\d{4})"
TERMIN_RE = re.compile(
    r"(?:Lhůta pro podávání žádostí|Lhůta pro podání žádostí|Termín podávání žádostí|"
    r"Termín pro podání žádostí|Termín pro podávání žádostí|Příjem žádostí|"
    r"Lhůta pro podávání projektů|Žádosti? bude možné podávat|Žádosti? (?:lze|je možné) podávat|"
    r"Žádosti? se přijímají|Žádosti? se podávají v termínu)"
    r".{0,60}?od\s+(?P<od>" + _DATE + r")(?:\s+od\s+[\d:]+\s*hod\w*)?"
    r"\.?\s+do\s+(?P<do>" + _DATE + r")",
    re.S | re.I,
)
# fallback: samostatné "od <datum> ... do <datum>" v okolí slova žádost (kratší okno)
TERMIN_FALLBACK = re.compile(
    r"žádost\w*\b.{0,40}?\bod\s+(?P<od>" + _DATE + r")(?:\s+od\s+[\d:]+\s*hod\w*)?\.?\s+do\s+(?P<do>" + _DATE + r")",
    re.S | re.I,
)
# alokace: "alokace/objem/celkem/navýšen ... <číslo> Kč"
ALOK_RE = re.compile(
    r"(?:alokac\w*|celkov\w*\s+(?:objem|výše|částk\w*)|objem finančních prostředků|navýšen\w*\s+na (?:částku|celkovou)?)"
    r"[^.]{0,80}?([\d][\d  \xa0]{4,}(?:,\d+)?)\s*Kč",
    re.S | re.I,
)


def fetch(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " ").replace("\xa0", " ")
    h = re.sub(r"[ \t]+", " ", h)
    return re.sub(r"\n\s*\n+", "\n", h).strip()


def body_of(text):
    """Hlavní obsah = od poslední drobečkové navigace po patičku ('Skrytá'/'Informace ')."""
    i = text.rfind("Drobečková navigace")
    seg = text[i:] if i >= 0 else text
    for end in ("\n Skrytá \n", "\nSkrytá\n", "Kontakty pro média"):
        j = seg.find(end)
        if j > 200:
            seg = seg[:j]
            break
    return seg


def _iso(s):
    """'4. 11. 2025' nebo '1. července 2026' → ISO."""
    s = (s or "").strip()
    m = re.match(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s)
    if m:
        return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}"
    m = re.match(r"(\d{1,2})\.\s*([a-zžščřďťňáéíóúůýě]+)\s+(\d{4})", s, re.I)
    if m:
        mes = MESICE.get(m.group(2).lower())
        if mes:
            return f"{int(m[3]):04d}-{mes:02d}-{int(m[1]):02d}"
    return None


def parse_termin(body):
    m = TERMIN_RE.search(body) or TERMIN_FALLBACK.search(body)
    if m:
        return _iso(m.group("od")), _iso(m.group("do"))
    return None, None


def parse_alokace(body):
    m = ALOK_RE.search(body)
    if not m:
        return None
    digits = re.sub(r"[^\d]", "", m.group(1).split(",")[0])
    return int(digits) if digits else None


def title_of(html, body, fallback):
    """Titulek programu: <h1> nebo poslední položka drobečkové navigace."""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    if m:
        t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()
        if t and len(t) > 4:
            return t
    # drobečková navigace: "... Hlavní stránka <oblast> <TITULEK> <první věta>"
    head = body.split("\n", 12)
    cand = [ln.strip() for ln in head if 8 < len(ln.strip()) < 200]
    return cand[0] if cand else fallback


def category_urls(rozcestnik_html):
    """Odkazy 'Dle oblastí' z rozcestníku → kategorie. Bere /web/urad/* i /web/dotace/*
    s grant-kontextem; vynechá EDP portál, dokumenty, poskytnuté dotace (awards)."""
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", rozcestnik_html, flags=re.S)
    urls, seen = [], set()
    SKIP = ("prehled-poskytnutych", "dotace.stredoceskykraj", "/documents/",
            "metodicky-pokyn", "prehled-dotaci", "/dotace1", "/web/urad/dotace\"")
    for m in re.finditer(r'<a\b[^>]*href="([^"]+)"', h):
        href = m.group(1)
        if not (("/web/urad/" in href and "dotac" in href.lower())
                or ("/web/dotace/" in href)
                or ("kotlikove" in href) or ("obchudek" in href) or ("obedy" in href)):
            continue
        if any(s in href for s in SKIP):
            continue
        full = href if href.startswith("http") else BASE + href
        if full not in seen:
            seen.add(full)
            urls.append(full)
    return urls


def program_links(cat_html):
    """Z kategorie vytáhni odkazy na jednotlivé programy (/web/dotace/<slug>)."""
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", cat_html, flags=re.S)
    out = {}
    for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', h, re.S):
        href, txt = m.group(1), re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
        if not txt or len(txt) < 8 or href == "#":
            continue
        if "/web/dotace/" not in href:
            continue
        full = href if href.startswith("http") else BASE + href
        out.setdefault(full, txt)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_stredocesky.json")
    a = ap.parse_args()

    rz = fetch(BASE + ROZCESTNIK)
    cats = category_urls(rz)
    print(f"kategorií: {len(cats)}", file=sys.stderr)

    # 1) posbírej kandidátní program-odkazy ze všech kategorií (+ kategorie samotná jako kandidát)
    cand = {}            # url -> hint title (z listingu)
    cat_bodies = {}      # url -> body (pro inline-date kategorie typu Fond prevence)
    for c in cats:
        try:
            html = fetch(c)
        except Exception as e:
            print(f"  warn kategorie {c}: {str(e)[:60]}", file=sys.stderr)
            continue
        cat_bodies[c] = body_of(detext(html))
        links = program_links(html)
        for u, t in links.items():
            cand.setdefault(u, t)
        # kategorie sama může nést program s termínem inline (Fond prevence)
        cand.setdefault(c, "")
    print(f"kandidátních programů: {len(cand)}", file=sys.stderr)

    catset = set(cats)
    # rozcestníkové/navigační „popisky" kategorií (NE programy)
    NAV_HINT = re.compile(r"Informace o dotacích vypsaných|Dotace a fondy pro|Dotace a projekty|"
                          r"^Přehled dotací|Ostatní dotace nezařad|Informace o (?:možnostech|dotačních)",
                          re.I)

    progs, seen = [], set()
    fetched = 0
    for url, hint in cand.items():
        if url in seen:
            continue
        seen.add(url)
        if fetched >= MAX_DETAILS:
            print("⚠ MAX_DETAILS dosažen — runaway/uniklé programy", file=sys.stderr)
            break
        if url in cat_bodies:
            body, html = cat_bodies[url], None
        else:
            try:
                html = fetch(url)
            except Exception as e:
                print(f"  warn detail {url}: {str(e)[:50]}", file=sys.stderr)
                continue
            fetched += 1
            body = body_of(detext(html))

        of, dl = parse_termin(body)
        nazev = hint or (title_of(html, body, url.rsplit("/", 1)[-1]) if html else url.rsplit("/", 1)[-1])
        # vyřaď navigační rozcestníkové stránky kategorií (popisek bez termínu = ne program)
        if NAV_HINT.search(nazev) and of is None and dl is None:
            continue
        # kategorie sama (cat_bodies) bez termínu = jen listing, ne program
        if url in catset and of is None and dl is None:
            continue
        # bez termínu i bez hint titulku = nezajímavé (prázdné rozcestníky)
        if of is None and dl is None and not hint:
            continue
        first_para = ""
        for ln in body.split("\n"):
            ln = ln.strip()
            if len(ln) > 80:
                first_para = ln
                break
        progs.append({
            "nazev": re.sub(r"\s+", " ", nazev).strip(),
            "open_from": of,
            "deadline": dl,
            "status": None,
            "alokace_czk": parse_alokace(body),
            "max_czk": None,
            "popis": (first_para[:500] or None),
            "eligible": None,
            "kod": None,
            "url": url,
            "_text": body[:2500],
        })

    # dedup dle (nazev,url)
    uniq, ks = [], set()
    for p in progs:
        k = (p["nazev"], p["url"])
        if k in ks:
            continue
        ks.add(k)
        uniq.append(p)

    out = {
        "source": "stredoceskykraj.cz",
        "kraj": "Středočeský kraj",
        "platform": "stredocesky_html",
        "programs": uniq,
    }
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with_dates = sum(1 for p in uniq if p["open_from"] or p["deadline"])
    print(json.dumps({"MARKER": "STREDOCESKY_HARVEST", "kept": len(uniq),
                      "with_dates": with_dates, "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
