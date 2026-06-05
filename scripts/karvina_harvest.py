#!/usr/bin/env python3
"""Karviná harvester — dotační programy statutárního města Karviná (QCM portál, server-rendered).

karvina.cz/magistrat/poskytovane-mestem = listing dotačních programů POSKYTOVANÝCH městem
(= výzvy, NE awards/realizované). Každý program je QCM "článek" → detail je próza s vloženými
termíny ("Lhůta/Termín pro podání žádostí je od D.M.YYYY do D.M.YYYY") a částkou
("stanovena částkou X,- Kč" | "rozmezím X - Y Kč"). Strukturovaný regex parse, žádný LLM.

Pozn.: kontrakt žádá platform="karvina_marwel"; CMS je fakticky QCM (vismo-příbuzný), ale
štítek držíme dle kontraktu.

Lossless: ukládá parsed pole + plný text detailu (_text). Status dopočítá ingest z termínů.
Ukládá průběžně (po každém detailu přepíše JSON).

Usage: python3 scripts/karvina_harvest.py [--out data/h_mesto_karvina.json]
       (spouštěj z kořene repa)
"""
import argparse, json, re, sys, urllib.request, html as H

BASE = "https://www.karvina.cz"
LISTING = BASE + "/magistrat/poskytovane-mestem"

# Jen skutečné dotační programy/výzvy poskytované městem. Listing míchá i navigaci a
# jeden cizí odkaz (vyřízené žádosti OP/CD/ŘP) → filtr na anchor text.
PROG_RE = re.compile(r"dotac|grant|voucher|podpora\s+(?:tělovýchov|činnosti)|kreativní business|"
                     r"sociální služby|individuální dotace", re.I)
SKIP_RE = re.compile(r"vyřízené žádosti|granty a dotace$|dotace a granty$", re.I)

# Termíny: 'Lhůta pro podání žádostí je od D.M.YYYY do D.M.YYYY' / 'Termín podání žádosti je od ... do ...'
# 'do' i en-dash/pomlčka jako oddělovač rozsahu; \xa0 normalizováno na space v detextu
TERMIN_RE = re.compile(
    r"(?:lhůta\s+pro\s+podání\s+žádost\w*|termín\s+podání\s+žádost\w*)[^\n]*?"
    r"od\s*(\d{1,2}\.\s?\d{1,2}\.\s?\d{4})\s*(?:do|[-–—])\s*(\d{1,2}\.\s?\d{1,2}\.\s?\d{4})",
    re.I)
# Částka: 'stanovena částkou X,- Kč' (max) nebo 'rozmezím X - Y Kč' (max=Y)
# open date bez roku: 'od D.M. do D.M.YYYY' → rok se zdědí z deadlinu
TERMIN_NOYEAR_RE = re.compile(
    r"(?:lhůta\s+pro\s+podání\s+žádost\w*|termín\s+podání\s+žádost\w*)[^\n]*?"
    r"od\s*(\d{1,2}\.\s?\d{1,2}\.)\s*(?:do|[-–—])\s*(\d{1,2}\.\s?\d{1,2}\.\s?\d{4})",
    re.I)
CASTKA_CASTKOU = re.compile(r"stanoven[aá]\s+částkou\s*([\d\s. ]+?)\s*,?-?\s*Kč", re.I)
CASTKA_ROZMEZI = re.compile(r"rozmez[íi]m?\s*([\d\s. ]+?)\s*,?-?\s*Kč\s*[-–]\s*([\d\s. ]+?)\s*,?-?\s*Kč", re.I)
ALOKACE_RE = re.compile(r"(?:celková\s+výše|alokac\w*|celkový\s+objem)[^\n]*?([\d\s. ]{4,})\s*,?-?\s*Kč", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def detext(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", h)
    t = H.unescape(t).replace("\xa0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def _iso(s):
    m = re.match(r"(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})", (s or "").strip())
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def _num(s):
    if not s:
        return None
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else None


def listing_programs(html):
    """Vrať [(url, anchor_text)] unikátní dotační programy z listingu."""
    out, seen = [], set()
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', h, re.S):
        href = m.group(1)
        txt = re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        if not href.startswith(BASE + "/magistrat/"):
            continue
        if len(txt) < 6 or txt.lower() == "celý článek":
            continue
        if SKIP_RE.search(txt) or not PROG_RE.search(txt):
            continue
        url = href.split("#")[0]
        if url in seen:
            continue
        seen.add(url)
        out.append((url, txt))
    return out


def parse_detail(text, title, url):
    rec = {"nazev": title, "open_from": None, "deadline": None, "status": None,
           "alokace_czk": None, "max_czk": None, "popis": None, "eligible": None,
           "kod": None, "url": url}
    mt = TERMIN_RE.search(text)
    if mt:
        rec["open_from"], rec["deadline"] = _iso(mt.group(1)), _iso(mt.group(2))
    else:
        # fallback: 'od D.M. do D.M.YYYY' (open date bez roku) → rok zděď z deadlinu
        mf = TERMIN_NOYEAR_RE.search(text)
        if mf:
            rec["deadline"] = _iso(mf.group(2))
            yr = (mf.group(2).strip().split(".")[-1])
            rec["open_from"] = _iso(mf.group(1).strip().rstrip(".") + "." + yr)
    mr = CASTKA_ROZMEZI.search(text)
    if mr:
        rec["max_czk"] = _num(mr.group(2))
    else:
        mc = CASTKA_CASTKOU.search(text)
        if mc:
            rec["max_czk"] = _num(mc.group(1))
    ma = ALOKACE_RE.search(text)
    if ma:
        rec["alokace_czk"] = _num(ma.group(1))
    # Popis = první věc "Cílem ... programu je ..." nebo úvodní odstavec po vyhlášení
    mc = re.search(r"(Cílem[^\n]{20,400}?\.)", text)
    if mc:
        rec["popis"] = re.sub(r"\s+", " ", mc.group(1)).strip()
    # eligible: heuristika z prózy
    me = re.search(r"(žadatel\w*[^\n]{5,200}?|cílov\w*\s+skupin\w*[^\n]{5,200}?)\.", text, re.I)
    if me:
        rec["eligible"] = re.sub(r"\s+", " ", me.group(1)).strip()
    return rec


def save(out_path, source_obj):
    json.dump(source_obj, open(out_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_karvina.json")
    a = ap.parse_args()

    lst = fetch(LISTING)
    progs_links = listing_programs(lst)
    print(f"nalezeno {len(progs_links)} dotačních programů v listingu", file=sys.stderr)

    obj = {"source": "karvina.cz", "kraj": "Moravskoslezský kraj", "obec": "Karviná",
           "uroven": "obec", "platform": "karvina_marwel", "programs": []}
    save(a.out, obj)

    for url, title in progs_links:
        try:
            html = fetch(url)
        except Exception as e:
            print(f"  warn {url}: {str(e)[:60]}", file=sys.stderr)
            continue
        text = detext(html)
        rec = parse_detail(text, title, url)
        # full text detailu (od těla článku), bounded jen safety na velikost
        i = text.find(title)
        rec["_text"] = text[i:i + 6000] if i >= 0 else text[:6000]
        obj["programs"].append(rec)
        save(a.out, obj)  # průběžné ukládání
        print(f"  + {title[:60]} | od={rec['open_from']} do={rec['deadline']} max={rec['max_czk']}",
              file=sys.stderr)

    print(json.dumps({"MARKER": "KARVINA_HARVEST", "kept": len(obj["programs"]),
                      "with_deadline": sum(1 for p in obj["programs"] if p["deadline"]),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
