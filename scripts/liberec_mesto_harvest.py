#!/usr/bin/env python3
"""Harvester dotačních fondů (grantových výzev) statutárního města Liberec.

POZOR — METODA: Grantys SPA na granty.liberec.cz NENÍ použitelná pro otevřené výzvy:
home route přesměruje na sign.in a `GET api/appeal` (seznam výzev) vrací 403 (login-gate).
Veřejně dostupné JSON tam není. Proto zdrojem JE veřejný listing města na www.liberec.cz
(sekce Fondy města, server-rendered HTML CMS), kde město každoročně VYHLAŠUJE jednotlivé
fondy s termíny příjmu žádostí ("Lhůta pro podávání žádostí od D.M.YYYY do D.M.YYYY").
Samotné podání pak běží přes Grantys, ale popis výzvy + termíny jsou na webu města veřejné.

Listing: /cz/mesto-samosprava/granty-dotace/fondy-mesta/ → detailní stránky jednotlivých
fondů (fond*.html / ekofond*.html). Detail = próza; z těla parsujeme název (H1), termín
příjmu (první "od ... do ..." pár u "lhůta/podávání žádostí"), případně alokaci a kódy
programů. Co nejde z textu (často v přiloženém PDF Vyhlášení) = null. Žádný LLM.

Výstup dle KONTRAKTU pro scripts/ingest_kraj.py (status=null → dopočítá ingest z termínů).
Ukládá průběžně po každém fondu.

Usage: python3 scripts/liberec_mesto_harvest.py [--out data/h_mesto_liberec.json]
"""
import argparse, json, re, sys, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)

BASE = "https://www.liberec.cz"
LISTING = "/cz/mesto-samosprava/granty-dotace/fondy-mesta/"
# fond-detail odkazy (obě cesty: nové mesto-samosprava i starší obcan); ne manuál/formuláře
DETAIL_RE = re.compile(
    r'href="(/cz/[^"]*(?:granty-dotace|obcan)[^"]*/(?:fond|ekofond)[a-z0-9\-/]*\.html)"'
)
SKIP_HREF = re.compile(r"formulare-dokumenty|manual", re.I)
UA = {"User-Agent": "Mozilla/5.0"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    return http_util.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def content_text(html):
    """Tělo stránky z id='content' po footer; navigaci (levé menu) ořízne až parser přes breadcrumb."""
    i = html.find('id="content"')
    seg = html[i:] if i >= 0 else html
    fi = seg.find('id="footer-content"')
    if fi > 0:
        seg = seg[:fi]
    seg = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", seg, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", seg)
    txt = (txt.replace("&nbsp;", " ").replace("&ndash;", "-")
              .replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'"))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", txt)).strip()


def h1(html):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    if not m:
        return None
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip() or None


# tolerantní datum: "16. 3. 2026" i překlep bez tečky "24 4. 2026"
DATE = r"(\d{1,2})\.?\s*(\d{1,2})\.?\s*(\d{4})"
# volitelný název dne mezi "od/do" a datem ("od pondělí 2. 2. 2026", "do pátku 20. 2.")
DOW = r"(?:pondělí|úterý|středy?|čtvrtka?|pátku?|soboty?|neděle)?\s*"


def _iso(d, mth, y):
    try:
        return f"{int(y):04d}-{int(mth):02d}-{int(d):02d}"
    except Exception:
        return None


def parse_window(body):
    """'od <datum> ... do <datum>' pár — JEN v kontextu příjmu/lhůty/podávání žádostí.

    Bez ukotvení na žádostní frázi NEBER žádné datum (stránky obsahují i nesouvisející
    'do D.M.YYYY' = termín čerpání/vyúčtování → falešný deadline). Tolerantní k překlepu
    bez tečky a k názvu dne mezi 'od/do' a datem.
    """
    # mezera mezi 'od <datum>' a 'do <datum>' smí obsahovat čas/"hod." — proto . místo [^.],
    # ale krátká (do 60 zn.), ať nepřeskočí do nesouvisející věty
    win = (r"(?:lhůt\w*|podáv\w*|příjem|předkl\w*).{0,40}?"
           r"\bod\s+" + DOW + DATE + r".{0,60}?\bdo\s+" + DOW + DATE)
    m = re.search(win, body, re.I | re.S)
    if m:
        of = _iso(m.group(1), m.group(2), m.group(3))
        de = _iso(m.group(4), m.group(5), m.group(6))
        if of and de:
            return of, de
    # fallback: 'do <datum>' JEN těsně u žádostní fráze (ne obecné 'do' v textu)
    m = re.search(r"(?:žádost\w*|podáv\w*|příjem)[^.]{0,40}?\b(?:do|nejpozději do)\s+"
                  + DOW + DATE, body, re.I)
    if m:
        return None, _iso(m.group(1), m.group(2), m.group(3))
    return None, None


def parse_alokace(body):
    m = re.search(r"(?:alokac\w*|celkov\w*\s+(?:částk\w*|objem\w*|rozpočt\w*)|"
                  r"k rozdělení|rozpočet fondu)[^.\d]{0,40}([\d  \xa0\.]{4,})\s*Kč",
                  body, re.I)
    if not m:
        return None
    digs = re.sub(r"[^\d]", "", m.group(1))
    return int(digs) if digs else None


def parse_kody(body):
    """Kódy programů, např. '6.1', '5.2' z věty o vyhlášení."""
    seg = body[:600]
    kk = re.findall(r"\bprogram\w*\s+((?:\d+\.\d+(?:,?\s*(?:a|i)?\s*)?)+)", seg, re.I)
    out = []
    for chunk in kk:
        out += re.findall(r"\d+\.\d+", chunk)
    return list(dict.fromkeys(out)) or None


def parse_detail(html, url):
    nazev = h1(html)
    body = content_text(html)
    # ořízni levé nav menu: ber tělo od posledního výskytu názvu po breadcrumb
    bc = body.rfind("| " + (nazev or "ZZZ"))
    main = body[bc:] if bc > 0 else body
    of, de = parse_window(main)
    kody = parse_kody(main)
    # popis = první "vyhlašuje ... žádostí" věta
    pm = re.search(r"((?:Statutární město|Zastupitelstvo|Rada)\s+[^\n]{40,400}?žádost\w*[^\n]{0,80}?\.)",
                   main, re.S)
    popis = re.sub(r"\s+", " ", pm.group(1)).strip() if pm else None
    rec = {
        "nazev": nazev,
        "open_from": of,
        "deadline": de,
        "status": None,
        "alokace_czk": parse_alokace(main),
        "max_czk": None,
        "popis": popis,
        "eligible": None,
        "kod": ", ".join(kody) if kody else None,
        "url": url,
    }
    return rec


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_liberec.json")
    a = ap.parse_args()

    out = {"source": "granty.liberec.cz", "kraj": "Liberecký kraj", "obec": "Liberec",
           "uroven": "obec", "platform": "liberec_grantys", "programs": []}

    def save():
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    save()  # založ soubor hned

    lst = fetch(BASE + LISTING)
    hrefs = []
    for m in DETAIL_RE.finditer(lst):
        h = m.group(1)
        if SKIP_HREF.search(h):
            continue
        if h not in hrefs:
            hrefs.append(h)
    print(f"listing: {len(hrefs)} fond-detail odkazů", file=sys.stderr)

    seen = set()       # dedup dle normalizovaného názvu
    seen_href = set()
    for href in hrefs:
        if href in seen_href:
            continue
        seen_href.add(href)
        url = BASE + href
        try:
            html = fetch(url)
        except Exception as e:
            print(f"  warn {href}: {str(e)[:60]}", file=sys.stderr)
            continue
        rec = parse_detail(html, url)
        if not rec["nazev"]:
            print(f"  skip (no H1): {href}", file=sys.stderr)
            continue
        key = norm(rec["nazev"])
        if key in seen:
            # už máme fond s tímhle názvem; preferuj záznam, který MÁ termín
            prev = next(p for p in out["programs"] if norm(p["nazev"]) == key)
            if not prev.get("deadline") and rec.get("deadline"):
                out["programs"].remove(prev)
                out["programs"].append(rec)
                save()
            continue
        seen.add(key)
        out["programs"].append(rec)
        save()
        print(f"  + {rec['nazev']}  open={rec['open_from']} deadline={rec['deadline']}",
              file=sys.stderr)

    save()
    print(json.dumps({"MARKER": "LIBEREC_MESTO_HARVEST", "kept": len(out["programs"]),
                      "with_deadline": sum(1 for p in out["programs"] if p["deadline"]),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
