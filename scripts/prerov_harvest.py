#!/usr/bin/env python3
"""Přerov harvester — dotační programy statutárního města Přerov (public4u CMS, server-rendered HTML).

prerov.eu/cs/magistrat/dotacni-programy/dotacni-programy-statutarniho-mesta-prerova/ = sekce s
dotačními programy města. Listing obsahuje detailní stránky programů (`.html`) + pod-složky (`/`),
do kterých se rekurzivně sestupuje. KAŽDÝ program = jedna server-rendered HTML stránka (<article>),
obsah je próza: vyhlášení, "O dotaci mohou žádat" (eligible), "Termín pro podání žádosti od ... do ..."
(open_from/deadline), "v maximální výši N Kč" (max_czk) + přílohy na /filemanager/files/NNNNN.{pdf,docx,...}.

Žádný login (dotace.prerov.eu = GINIS portál se loginem — VYNECHÁNO). Žádné awards
("prehledy-schvalenych-financnich-prostredku" = schválené prostředky → VYNECHÁNO).

Strukturovaný parse, žádný LLM. Status dopočítá ingest_kraj z termínů. Lossless: ukládá parsed pole +
plný text <article> + seznam příloh. Co nezjistí (deadline/alokace u stránek bez termínu) = null = upřímně.

Usage: python3 scripts/prerov_harvest.py [--out data/h_mesto_prerov.json]
  (spouštěj z kořene repa)
"""
import argparse, json, re, sys, time, urllib.request

BASE = "https://www.prerov.eu"
ROOT = "/cs/magistrat/dotacni-programy/dotacni-programy-statutarniho-mesta-prerova/"
# pod-stránky, které NEJSOU otevřené výzvy (awards / přehledy / jiné subjekty)
SKIP_SLUG = re.compile(r"prehledy-schvalenych|dotace-jine-zdroje", re.I)

CZ_MONTHS = {"ledna": 1, "února": 2, "unora": 2, "března": 3, "brezna": 3, "dubna": 4,
             "května": 5, "kvetna": 5, "června": 6, "cervna": 6, "července": 7, "cervence": 7,
             "srpna": 8, "září": 9, "zari": 9, "října": 10, "rijna": 10, "listopadu": 11,
             "prosince": 12}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")


def article(html):
    """Vrať jen obsah <article> (hlavní obsah public4u), bez navigace/patičky."""
    m = re.search(r"<article\b.*?</article>", html, re.S)
    return m.group(0) if m else html


def detext(seg):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", seg, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h)
    h = (h.replace("&nbsp;", " ").replace("&gt;", ">").replace("&lt;", "<")
           .replace("&amp;", "&").replace("&ndash;", "–").replace("&bdquo;", "„")
           .replace("&ldquo;", """).replace("&rdquo;", """).replace("&quot;", '"'))
    h = re.sub(r"[ \t\xa0]+", " ", h)
    return re.sub(r"\n\s*\n+", "\n", h).strip()


def iso(d, m, y):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def _dmy(s):
    m = re.match(r"(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})", s.strip())
    return iso(m[1], m[2], m[3]) if m else None


def _cz_word_date(s):
    # "27. dubna 2026"
    m = re.match(r"(\d{1,2})\.\s*([a-zěščřžýáíéúůóďťň]+)\s+(\d{4})", s.strip(), re.I)
    if m and m.group(2).lower() in CZ_MONTHS:
        return iso(m[1], CZ_MONTHS[m.group(2).lower()], m[3])
    return None


def parse_term(text):
    """open_from + deadline z 'Termín pro podání žádosti ... od DD.MM.YYYY do DD.MM.YYYY'.

    Okno = od slova 'Termín'/'lhůt'/'uzávěrk' k podání žádosti po dalších ~200 znaků (pozn.: data
    obsahují tečky, proto NESMÍ být [^.] limiter). Mimo toto okno data neparsujeme (vyhneme se
    metadatům Vytvořeno/Aktualizováno a historickým datům vyhlášení)."""
    of = dl = None
    DATE = r"\d{1,2}\.\s?\d{1,2}\.\s?\d{4}"
    win = ""
    mw = re.search(r"(?:[Tt]ermín|[Ll]hůt[ay]|uzávěrk)[^\n]{0,40}?(?:podání|podat|uzávěrk)[^\n]{0,200}", text)
    if mw:
        win = mw.group(0)
    scope = win or text
    rng = re.search(r"od\s+(" + DATE + r")\s+do\s+(" + DATE + r")", scope)
    if rng:
        of, dl = _dmy(rng.group(1)), _dmy(rng.group(2))
    elif win:
        # jen koncové datum: "do DD.MM.YYYY" / "nejpozději DD.MM.YYYY"
        md = re.search(r"(?:do|nejpozději)\s+(" + DATE + r")", win)
        if md:
            dl = _dmy(md.group(1))
    return of, dl


def parse_max(text):
    m = re.search(r"maximáln[íě][^.]{0,40}?výši\s+([\d \xa0]+)\s*Kč", text)
    if not m:
        m = re.search(r"výši\s+([\d \xa0]+)\s*Kč", text)
    if m:
        d = re.sub(r"[^\d]", "", m.group(1))
        return int(d) if d else None
    return None


def parse_eligible(text):
    m = re.search(r"O dotaci mohou žádat\s+(.+?)(?:\n|Dotace bude|Termín|Přílohy|Tisk stránky)", text, re.S)
    if m:
        e = re.sub(r"\s+", " ", m.group(1)).strip(" .,")
        return e[:600] if e else None
    return None


def clean_text(text):
    """Odstraň breadcrumb na začátku a metadata patičky (Vytvořeno/Aktualizováno/přečteno/Tisk)."""
    t = text
    # breadcrumb: "Úvodní strana > ... > <složka>" na prvním řádku — zahoď celý úvodní řádek s >
    t = re.sub(r"^[^\n]*?>[^\n]*\n", "", t, count=1)
    t = re.sub(r"^Úvodní strana.*?(?:\n|Přerova\s)", "", t, flags=re.S)
    t = re.split(r"\bTisk stránky\b|\bVytvořeno\s+\d", t)[0]
    return t.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_prerov.json")
    a = ap.parse_args()

    # rekurzivní crawl listingu: složky (/) → sbírej .html programy + ponoř se do dotace-* pod-složek
    to_visit = [ROOT]
    visited_dir = set()
    detail_urls = []  # zachovat pořadí, dedup
    seen_detail = set()
    while to_visit:
        d = to_visit.pop(0)
        if d in visited_dir:
            continue
        visited_dir.add(d)
        try:
            html = fetch(BASE + d)
        except Exception as e:
            print(f"  warn listing {d}: {str(e)[:60]}", file=sys.stderr)
            continue
        seg = article(html)
        for m in re.finditer(r'href="([^"]+)"', seg):
            href = m.group(1)
            href = href.replace("http://www.prerov.eu", "").replace("https://www.prerov.eu", "")
            if not href.startswith(ROOT):
                continue
            if SKIP_SLUG.search(href):
                continue
            if href.endswith(".html"):
                if href not in seen_detail:
                    seen_detail.add(href); detail_urls.append(href)
            elif href.endswith("/") and href != d and href.startswith(ROOT) and len(href) > len(ROOT):
                # pod-složka s dotačními programy (např. oblast kultury/sportu/...)
                to_visit.append(href)
    print(f"nalezeno {len(detail_urls)} detailních programů, {len(visited_dir)} listingů", file=sys.stderr)

    progs = []
    for href in detail_urls:
        url = BASE + href
        try:
            html = fetch(url)
        except Exception as e:
            print(f"  warn detail {href}: {str(e)[:60]}", file=sys.stderr); continue
        seg = article(html)
        full = detext(seg)
        body = clean_text(full)

        # název = <title> bez sufixu " - Město Přerov"; fallback = první nadpis uvnitř <article>
        nazev = None
        mt = re.search(r"<title>(.*?)</title>", html, re.S)
        if mt:
            nazev = re.sub(r"\s*-\s*Město Přerov\s*$", "", detext(mt.group(1))).strip()
        if not nazev:
            mh = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", seg, re.S)
            nazev = detext(mh.group(1)).strip() if mh else href.rsplit("/", 1)[-1]

        of, dl = parse_term(body)
        rec = {
            "nazev": nazev,
            "open_from": of,
            "deadline": dl,
            "status": None,
            "alokace_czk": None,
            "max_czk": parse_max(body),
            "popis": (re.sub(r"\s+", " ", body).strip()[:500] or None),
            "eligible": parse_eligible(body),
            "kod": None,
            "url": url,
        }
        # přílohy (lossless, do _files) — /filemanager/files/NNNNN.ext
        files = []
        for fm in re.finditer(r'href="([^"]+\.(?:pdf|docx?|xlsx?|odt))"[^>]*>(.*?)</a>', html, re.S | re.I):
            fu = fm.group(1)
            if not fu.startswith("http"):
                fu = BASE + fu
            label = detext(fm.group(2))[:120]
            files.append({"url": fu, "label": label})
        rec["_files"] = files
        rec["_text"] = body[:4000]
        progs.append(rec)
        # ukládej průběžně
        out = {"source": "prerov.eu", "kraj": "Olomoucký kraj", "obec": "Přerov", "uroven": "obec",
               "platform": "prerov_public4u", "programs": progs}
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        time.sleep(0.3)

    with_dl = sum(1 for p in progs if p["deadline"])
    print(json.dumps({"MARKER": "PREROV_HARVEST", "kept": len(progs), "with_deadline": with_dl,
                      "with_max": sum(1 for p in progs if p["max_czk"]), "out": a.out},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
