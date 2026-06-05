#!/usr/bin/env python3
"""Olomoucký kraj harvester — aktuální dotační programy 2026 (Nette CMS, server-rendered HTML).

Zdroj: olkraj.cz/.../aktualni-dotacni-programy = tabulka, kde každá kategorie (10_ Zdraví,
13_ ...) má v pravé buňce seznam programů. Každý program = <h3><strong>KÓD Název</strong></h3>
následovaný <ul><li><a href=".../KÓD-slug-prijem-zadosti-DD-MM-DD-MM-YYYY">. Termíny jsou
zakódované v URL slugu detailu (od–do). Strukturovaný parse, žádný LLM. Status dopočítá ingest.

Lossless v rozsahu listingu: ukládá nazev/kod/url + open_from/deadline z URL. Pole nezjištěná
z listingu (alokace, popis, eligible, max) = null — nevymýšlí se.

Usage: python3 scripts/olomoucky_harvest.py [--out data/h_kraj_olomoucky.json]
"""
import argparse, json, re, sys, urllib.request

URL = ("https://www.olkraj.cz/dotace-granty-prispevky-krajske-dotacni-programy-2026"
       "/aktualni-dotacni-programy")
# detail-link prefix = jednotlivé programy (ne rozcestníky/awards)
LINK_PREFIX = "https://www.olkraj.cz/dotace-granty-prispevky-krajske-dotacni-programy-2026/"
# program header: KÓD (NN_NN nebo NN_NN_NN) + název; podtržítko za kódem volitelné
CODE_RE = re.compile(r"^(\d{2}_\d{2}(?:_\d{2})?)_?\s*(.+)$")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).replace("\xa0", " ").strip()


def iso(d, m, y):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def dates_from_slug(url):
    """Termíny zakódované v URL slugu: ...-prijem-zadosti-[od-]<tail>, kde tail je sekvence
    čísel oddělených '-' s rokem na konci. Reálné tvary:
      DD-MM-DD-MM-YYYY        (od d/m, do d/m, společný rok)
      DD-MM-YYYY-DD-MM-YYYY   (od i do mají vlastní rok)
    Vrací (open_from, deadline) ISO; pokud termín ve slugu není → (None, None)."""
    m = re.search(r"prijem-zadosti-(?:od-)?(.+)$", url)
    if not m:
        return None, None
    nums = re.findall(r"\d+", m.group(1))
    if len(nums) == 5:  # DD MM DD MM YYYY (sdílený rok)
        y = nums[4]
        return iso(nums[0], nums[1], y), iso(nums[2], nums[3], y)
    if len(nums) == 6:  # DD MM YYYY DD MM YYYY
        return iso(nums[0], nums[1], nums[2]), iso(nums[3], nums[4], nums[5])
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_olomoucky.json")
    ap.add_argument("--url", default=URL)
    a = ap.parse_args()

    html = fetch(a.url)

    # Posbírej headery a detail-linky v pořadí výskytu; spáruj link s nejbližším
    # předcházejícím headerem (1 program = 1 header + 1 link).
    tokens = []
    for m in re.finditer(r"<strong>([^<]*\d{2}_\d{2}[^<]*)</strong>", html):
        tokens.append((m.start(), "H", clean(m.group(1))))
    for m in re.finditer(r'href="(' + re.escape(LINK_PREFIX) + r'[^"]+)"', html):
        tokens.append((m.start(), "L", m.group(1)))
    tokens.sort()

    progs, seen = [], set()
    pending_header = None
    for _, t, v in tokens:
        if t == "H":
            pending_header = v
        else:  # link — spáruj s posledním headerem
            cm = CODE_RE.match(pending_header) if pending_header else None
            if cm:
                kod, nazev = cm.group(1), clean(cm.group(2))
            else:
                kod, nazev = None, pending_header
            url = v
            key = kod or url
            if key in seen:
                continue
            seen.add(key)
            of, dl = dates_from_slug(url)
            progs.append({
                "nazev": nazev, "open_from": of, "deadline": dl,
                "status": None, "alokace_czk": None, "max_czk": None,
                "popis": None, "eligible": None, "kod": kod, "url": url,
            })
            pending_header = None

    out = {"source": "olkraj.cz", "kraj": "Olomoucký kraj",
           "platform": "olomoucky_html", "programs": progs}
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "OLOMOUCKY_HARVEST", "kept": len(progs),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
