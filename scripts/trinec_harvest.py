#!/usr/bin/env python3
"""Třinec harvester — dotační programy statutárního města Třince (vismo, server-rendered HTML).

trinecko.cz je vismo. Sekce /dotace je rozcestník (hub) → dlaždice (tiles) na oblasti
(kultura+sport, sociální podpora→registrované soc. služby / návazné aktivity, kulturní
památky, kotlíkové, ovzduší). Pod každou oblastí jsou ročníkové dlaždice ("2026", "2025",
"Archiv") = listy s detailem programu (perex + přílohy).

Metoda: rekurzivní BFS crawl od /dotace přes `tile__link` (zůstává ve stromu dotace).
Program = list, jehož drobečková navigace končí ročníkem (4 číslice) NEBO jehož text nese
frázi "Termín předkládání žádostí". Termíny se parsují z fráze "od DD.MM.-DD.MM.YYYY"
(otevřeno-uzavřeno). Některé soc. programy mají termín jen v přílohách (PDF/DOCX) → null
(status dopočítá ingest z dat; výsledky hodnocení = de facto uzavřeno).

Vismo občas blokuje pythoní urllib → fallback na `curl`. Status NEpočítáme (kód v ingestu).
Lossless: ukládá parsed pole + perex + breadcrumb. Ukládá průběžně po každém uzlu.

Usage: python3 scripts/trinec_harvest.py [--out data/h_mesto_trinec.json] [--root /dotace]
"""
import argparse, html as H, json, re, subprocess, sys, urllib.request
from collections import deque

BASE = "https://www.trinecko.cz"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
# fráze termínu na vismo Třinec: "Termín předkládání žádostí: od 16.01.-31.01.2026"
RE_TERM = re.compile(
    r"Termín\s+předkládání\s+žádostí\s*:?\s*(?:od\s*)?"
    r"(\d{1,2})\.(\d{1,2})\.?(?:(\d{4}))?\s*[-–]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})",
    re.I | re.S)
# fallback: jediné datum "do DD.MM.YYYY"
RE_DO = re.compile(r"\bdo\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", re.I)
RE_YEAR = re.compile(r"^\s*(20\d{2})\s*$")
# rozcestníkové uzly bez vlastní výzvy (archiv/redirecty/info) — necrawl jako program
SKIP_TITLE = re.compile(r"\bArchiv\b", re.I)
# ročníkový list je PROGRAM jen když jeho rodič (oblast) je pojmenovaná výzva, ne
# generická "Dotace" ani stránka pravidel/odboru bez vlastní výzvy
SKIP_AREA = re.compile(r"^Dotace$|pravidl|^Odbor\b|zásady|statut", re.I)


def fetch(url):
    """urllib s fallbackem na curl (vismo občas blokuje fetchery)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"  urllib fail {url}: {str(e)[:50]} → curl", file=sys.stderr)
        r = subprocess.run(["curl", "-sSL", "-A", UA, "--max-time", "40", url],
                           capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(f"curl rc={r.returncode}: {r.stderr.decode()[:80]}")
        return r.stdout.decode("utf-8", "replace")


def detext(fragment):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", fragment, flags=re.S)
    t = H.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", t)).strip()


def _iso(d, m, y):
    if not (d and m and y):
        return None
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def article(html):
    m = re.search(r"<article.*?</article>", html, re.S)
    return m.group(0) if m else html


def perex(html):
    m = re.search(r'class="article__perex"[^>]*>(.*?)</div>', html, re.S)
    return detext(m.group(1)) if m else ""


def breadcrumb(html):
    m = re.search(r'class="list breadcrumb-nav">(.*?)</ul>', html, re.S)
    if not m:
        return []
    items = re.findall(r'breadcrumb-nav__link[^>]*>(.*?)</a>', m.group(1), re.S)
    out = []
    for it in items:
        s = H.unescape(re.sub(r"<[^>]+>", " ", it)).strip()
        if s:
            out.append(s)
    return out


def tiles(html):
    """[(title, href, description)] z vismo dlaždic."""
    out = []
    for m in re.finditer(r'<li class="tile__item">(.*?)</li>', html, re.S):
        blk = m.group(1)
        href = re.search(r'href="([^"]+)"', blk)
        title = re.search(r'tile__title">([^<]*)<', blk)
        desc = re.search(r'tile__description[^>]*>(.*?)</p>', blk, re.S)
        out.append((
            H.unescape(title.group(1)).strip() if title else "",
            href.group(1) if href else None,
            detext(desc.group(1)) if desc else "",
        ))
    return out


def attachments(html):
    """Názvy příloh (pro odvození bohatšího názvu programu)."""
    art = article(html)
    return [H.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).strip()
            for m in re.finditer(r'global-attachment__title"[^>]*>(.*?)</', art, re.S)]


def parse_term(text):
    """→ (open_from, deadline) ISO nebo (None, None)."""
    m = RE_TERM.search(text or "")
    if m:
        od_d, od_m, od_y, dl_d, dl_m, dl_y = m.groups()
        od_y = od_y or dl_y  # otevření často bez roku ("od 16.01.-31.01.2026")
        return _iso(od_d, od_m, od_y), _iso(dl_d, dl_m, dl_y)
    m = RE_DO.search(text or "")
    if m:
        return None, _iso(m.group(1), m.group(2), m.group(3))
    return None, None


def program_name(bc, perex_txt, atts):
    """Bohatý název programu: ze záhlaví přílohy ('Program na podporu...') nebo perexu;
    jinak z drobečku (oblast + ročník)."""
    blob = (perex_txt or "") + " " + " ".join(atts or [])
    m = re.search(r"„?Program(?:ov[^“\"]*|u)? na podporu([^“\".\n]{5,120})", blob)
    if m:
        return ("Program na podporu" + m.group(1)).strip("„").strip()
    m = re.search(r"(Dotačního? programu[^“\".\n]{5,120})", blob)
    if m:
        return "Dotační program " + m.group(1).split("programu", 1)[-1].strip()
    # drobeček: oblast (předposlední ne-ročník) + ročník
    parts = [p for p in bc if p not in ("Titulní stránka", "Třinec")]
    year = next((p for p in reversed(parts) if RE_YEAR.match(p)), None)
    area = None
    for p in reversed(parts):
        if not RE_YEAR.match(p) and p not in ("Dotace", "Drobečková navigace"):
            area = p
            break
    if area:
        return f"{area}{' ' + year if year else ''}".strip()
    return (bc[-1] if bc else "Dotace Třinec")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_trinec.json")
    ap.add_argument("--root", default="/dotace")
    a = ap.parse_args()

    out = {"source": "trinecko.cz", "kraj": "Moravskoslezský kraj", "obec": "Třinec",
           "uroven": "obec", "platform": "trinec_vismo", "programs": []}

    def flush():
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    seen_url, seen_prog = set(), set()
    q = deque([a.root])
    pages = 0
    while q:
        path = q.popleft()
        url = path if path.startswith("http") else BASE + path
        if url in seen_url or not url.startswith(BASE):
            continue
        seen_url.add(url)
        try:
            html = fetch(url)
        except Exception as e:
            print(f"  warn {url}: {str(e)[:60]}", file=sys.stderr)
            continue
        pages += 1
        bc = breadcrumb(html)
        px = perex(html)
        body = detext(article(html))
        atts = attachments(html)
        leaf_title = bc[-1] if bc else ""

        # enqueue dlaždice (zůstaň ve stromu dotace; přeskoč Archiv větve a externí)
        for t_title, t_href, t_desc in tiles(html):
            if not t_href or t_href.startswith(("http", "mailto:", "#")):
                continue
            if SKIP_TITLE.search(t_title or ""):
                continue
            if (BASE + t_href) not in seen_url:
                q.append(t_href)

        # je tenhle uzel program? = list s ročníkem v drobečku NEBO nese frázi termínu
        is_year_leaf = bool(bc) and bool(RE_YEAR.match(leaf_title or ""))
        has_term = bool(RE_TERM.search(px + " " + body))
        if not (is_year_leaf or has_term):
            continue
        # ročníkový list bez termínu: ber jen když rodič=pojmenovaná oblast výzvy
        if is_year_leaf and not has_term:
            area = next((p for p in reversed(bc[:-1])
                         if not RE_YEAR.match(p) and p not in ("Titulní stránka", "Třinec")),
                        "")
            if SKIP_AREA.search(area):
                continue
        # přeskoč archivní/staré ročníky → cíl jsou aktuální výzvy (nejnovější ročník)
        # ponecháme všechny nalezené, dedup řeší duplicitu; status dopočítá ingest
        of, dl = parse_term(px + " " + body)
        nazev = program_name(bc, px, atts)
        # přidej ročník do názvu, pokud chybí a je v drobečku
        ym = RE_YEAR.match(leaf_title or "")
        if ym and ym.group(1) not in nazev:
            nazev = f"{nazev} {ym.group(1)}".strip()

        key = nazev.lower()
        if key in seen_prog:
            continue
        seen_prog.add(key)

        prog = {
            "nazev": nazev,
            "open_from": of,
            "deadline": dl,
            "status": None,
            "alokace_czk": None,
            "max_czk": None,
            "popis": (px or None),
            "eligible": None,
            "kod": None,
            "url": url,
        }
        out["programs"].append(prog)
        flush()  # ukládej průběžně
        print(json.dumps({"PROG": nazev, "of": of, "dl": dl, "url": url},
                         ensure_ascii=False), file=sys.stderr)

    flush()
    print(json.dumps({"MARKER": "TRINEC_HARVEST", "pages_crawled": pages,
                      "programs": len(out["programs"]), "out": a.out},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
