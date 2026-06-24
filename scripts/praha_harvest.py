#!/usr/bin/env python3
"""Praha (HMP) harvester — otevřené dotační programy/granty Hlavního města Prahy.

praha.eu = Liferay JS-SPA (curl dostane jen JS shell) → render Playwrightem (chromium).
HMP nemá CENTRÁLNÍ katalog dotací ani JSON-REST: otevřené VÝZVY žijí jako editorial
stránky roztroušené po resortních Liferay sitech (kultura, portalzp, cestovniruch,
pamatky, …). Detail je neredukovatelně PRÓZA → status/datumy/alokaci parsujeme
regexy z renderovaného textu (status pak dopočítá ingest_kraj z termínů).

STRATEGIE (dvě vrstvy zdrojů, dedup přes URL+název):
  A) Liferay-render: ze seed dotačních HUB stránek vyber detail program-pages
     (odkazy obsahující program/dotac/vyhlášení/podpora), vyhoď award/seminář/komise
     šum, vyrenderuj každý detail, parsuj termíny + eligible + alokaci.
  B) eud.praha.eu RSS (úřední deska) jako DOPLNĚK: jen položky typu
     "Vyhlášení Programu…/Program podpory … pro rok" (NE "Poskytnuté dotace",
     NE "Rozpočtové opatření", NE awards). Datum = pubDate (announce), deadline null.

POKUS 1 = Liferay-render (primární), POKUS 2 = RSS (doplněk). Výstup: data/h_kraj_praha.json
dle kontraktu scripts/ingest_kraj.py.

Usage: python3 scripts/praha_harvest.py [--out data/h_kraj_praha.json] [--no-rss] [--no-render]
"""
import argparse, json, re, sys, urllib.request, xml.etree.ElementTree as ET
import http_util   # jednotná TLS politika (audit #7/#32)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# --- SEED dotační hub stránky (resortní Liferay sity, které reálně existují /web/<slug>) ---
# Sport/sociální/školství/zdravotnictví NEjsou samostatné sity (HTTP 500); jejich programy
# zachytí RSS doplněk (Vyhlášení Programu …). Hub = stránka, ze které čteme odkazy na detaily.
SEED_HUBS = [
    "https://praha.eu/web/kultura/granty",
    "https://praha.eu/web/kultura/programove-dotace-2027",
    "https://praha.eu/web/kultura/programove-dotace",
    "https://praha.eu/web/portalzp",
    "https://praha.eu/web/cestovniruch/dotace",
    "https://praha.eu/web/pamatky/dotace",
]

# odkaz je kandidát na program-detail, když matchne POS a nematchne NEG
DET_POS = re.compile(r"program|dotac|vyhlášen|podpor|grant|čistá energie|kotlík", re.I)
DET_NEG = re.compile(
    r"vyhlaseni-vyberoveho|reditel|prehled-poskytnut|poskytnutych|schvaleni-poskytnut"
    r"|nase-organizace|komise|seminar|seminář|webinar|webinář|jmenovani|nominac"
    r"|prispevkove-organizace|vernisaz|den-biodiverzity|vyukov|dalsi-moznosti|archiv", re.I)

# archivní/historické stránky: "Granty 2019", "Programové dotace 2023" pro ROK < CUR_YEAR.
# Otevřené výzvy jsou pro aktuální/příští rok → ber jen rok >= CUR_YEAR (nebo bez roku).
CUR_YEAR = 2026
_YEAR_IN_TITLE = re.compile(r"\b(20\d{2})\b")


def is_archive(title):
    yrs = [int(y) for y in _YEAR_IN_TITLE.findall(title or "")]
    if not yrs:
        return False
    # je-li v názvu rok a VŠECHNY zmíněné roky jsou < CUR_YEAR → archiv
    return max(yrs) < CUR_YEAR

# parse patterny pro prózu detailu — JEN explicitní štítky (žádné vágní "do", to chytá šum)
P_OPEN = re.compile(r"(?:Zahájení příjmu žádostí|Příjem žádostí od|Zahájení příjmu|Žádosti lze podávat od)\D{0,15}?(\d{1,2}\.\s?\d{1,2}\.\s?20\d{2})", re.I)
P_DEAD = re.compile(r"(?:Ukončení příjmu žádostí|Termín pro podání žádost\w*|Uzávěrka(?: pro podání)?|Konec příjmu žádostí|Žádosti lze podávat do)\D{0,15}?(\d{1,2}\.\s?\d{1,2}\.\s?20\d{2})", re.I)
P_ELIG = re.compile(r"(?:Komu je Program určen|Program je určen|Oprávněn[íý]\s*žadatel\w*|Žadatel\w* mohou být)[:\s]*(.+?)(?:\n\n|\bVýše|\bPodmínk|\bAlokac|\bZpůsob|\bKontakt)", re.I | re.S)
P_ALOK = re.compile(r"(?:Celková (?:alokace|částka)|Alokace|Objem (?:finančních )?prostředků|Pro Program (?:je )?vyčleněn\w*)\D{0,40}?([\d   \.]{4,})\s*(?:Kč|korun)", re.I)
P_DATEANY = re.compile(r"\d{1,2}\.\s?\d{1,2}\.\s?20\d{2}")

RSS_URL = "https://eud.praha.eu/pub/rss/6000004/4/?pocet=500"
# RSS doplněk: jen reálná VYHLÁŠENÍ programů, ne awards / rozpočtová opatření
RSS_POS = re.compile(r"vyhlášení (?:programu|grant)|^program podpory|grantov[ýé] program|dotační program k projektu", re.I)
RSS_NEG = re.compile(r"rozpočtov|usnesení|poskytnut|výsledky|schválen|informace|odpověď|žádost dle|106/1999|komise", re.I)


def iso(s):
    if not s: return None
    m = re.match(r"(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})", s)
    return f"{int(m[3]):04d}-{int(m[2]):02d}-{int(m[1]):02d}" if m else None


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def num(s):
    d = re.sub(r"[^\d]", "", s or "")
    return int(d) if d else None


def parse_detail(url, title, text):
    """Z renderovaného textu detailu vytěž pole. Status dopočítá ingest z termínů."""
    mo, md = P_OPEN.search(text), P_DEAD.search(text)
    of = iso(mo.group(1)) if mo else None
    dl = iso(md.group(1)) if md else None
    elig = None
    me = P_ELIG.search(text)
    if me:
        elig = clean(me.group(1))[:400] or None
    alok = None
    ma = P_ALOK.search(text)
    if ma:
        alok = num(ma.group(1))
    # popis = první věcný odstavec (po nadpisu, ne UI prvky)
    popis = None
    for para in re.split(r"\n+", text):
        para = clean(para)
        if len(para) > 60 and not re.search(r"minut.*čtení|Sdílet|Facebook|Rychlé odkazy", para):
            popis = para[:500]; break
    return {"nazev": clean(title), "open_from": of, "deadline": dl, "status": None,
            "alokace_czk": alok, "max_czk": None, "popis": popis, "eligible": elig,
            "kod": None, "url": url.split("?")[0]}


def harvest_render(out_path, write_cb):
    from playwright.sync_api import sync_playwright
    progs, seen = [], set()
    detail_urls = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(user_agent=UA)

        # fáze 1: posbírej detail-URL z hubů
        for hub in SEED_HUBS:
            try:
                r = pg.goto(hub, wait_until="domcontentloaded", timeout=45000)
                if r and r.status >= 500:
                    print(f"  hub {hub} -> {r.status}, skip", file=sys.stderr); continue
                pg.wait_for_timeout(2000)
                anchors = pg.query_selector_all("a")
            except Exception as e:
                print(f"  hub ERR {hub}: {str(e)[:60]}", file=sys.stderr); continue
            for a in anchors:
                try:
                    h = a.get_attribute("href") or ""
                    t = clean(a.inner_text())
                except Exception:
                    continue
                if "/web/" not in h:
                    continue
                if not h.startswith("http"):
                    h = "https://praha.eu" + h
                h = h.split("?")[0].split("#")[0]
                blob = h + " " + t
                if DET_POS.search(blob) and not DET_NEG.search(blob) and not is_archive(t) and not is_archive(h):
                    # vyřaď samotné huby/landing bez konkrétního programu
                    if h.rstrip("/") in (hb.rstrip("/") for hb in SEED_HUBS):
                        continue
                    if h not in [u for u, _ in detail_urls]:
                        detail_urls.append((h, t))
        print(f"  detail kandidátů: {len(detail_urls)}", file=sys.stderr)

        # fáze 2: vyrenderuj každý detail
        for url, link_t in detail_urls:
            try:
                r = pg.goto(url, wait_until="domcontentloaded", timeout=45000)
                if r and r.status >= 400:
                    print(f"  detail {url} -> {r.status}", file=sys.stderr); continue
                pg.wait_for_timeout(1800)
                h1el = pg.query_selector("h1")
                title = clean(h1el.inner_text()) if h1el else link_t
                main = pg.query_selector("main") or pg.query_selector("#main-content") or pg.query_selector("body")
                text = main.inner_text() if main else ""
            except Exception as e:
                print(f"  detail ERR {url}: {str(e)[:60]}", file=sys.stderr); continue
            if is_archive(title):
                continue
            if not text or not P_DATEANY.search(text):
                # bez jakéhokoli data těžko poznáme výzvu — ale ber, pokud titul zní jako program
                if not re.search(r"program|grant|dotac", title, re.I):
                    continue
            rec = parse_detail(url, title, text)
            key = rec["url"]
            if key in seen:
                continue
            seen.add(key)
            progs.append(rec)
            write_cb(progs)  # PRŮBĚŽNÝ zápis (síťová odolnost)
            print(f"    + {rec['nazev'][:60]} | open={rec['open_from']} dl={rec['deadline']}", file=sys.stderr)
        b.close()
    return progs


def harvest_rss():
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": UA})
    raw = http_util.urlopen(req, timeout=30).read()
    x = ET.fromstring(raw)
    out, seen = [], set()
    for it in x.findall(".//item"):
        t = clean(it.findtext("title"))
        if not (RSS_POS.search(t) and not RSS_NEG.search(t)):
            continue
        link = (it.findtext("link") or "").replace("http://", "https://")
        if t in seen:
            continue
        seen.add(t)
        # pubDate -> open_from (announce); deadline neznáme z RSS
        pd = it.findtext("pubDate") or ""
        of = None
        m = re.search(r"(\d{1,2})\s+(\w{3})\s+(\d{4})", pd)
        MON = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
        if m and m.group(2) in MON:
            of = f"{int(m[3]):04d}-{MON[m[2]]:02d}-{int(m[1]):02d}"
        out.append({"nazev": t, "open_from": of, "deadline": None, "status": None,
                    "alokace_czk": None, "max_czk": None, "popis": None,
                    "eligible": None, "kod": None, "url": link})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_kraj_praha.json")
    ap.add_argument("--no-rss", action="store_true")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()

    method = []
    render_progs, rss_progs = [], []

    def dump(render_list, rss_list):
        # dedup mezi vrstvami podle URL i názvu
        combined, seen_url, seen_nm = [], set(), set()
        for src in (render_list, rss_list):
            for p in src:
                u = (p.get("url") or "").rstrip("/")
                nm = clean(p.get("nazev")).lower()
                if u and u in seen_url:
                    continue
                if nm and nm in seen_nm:
                    continue
                seen_url.add(u); seen_nm.add(nm)
                combined.append(p)
        plat = "praha_liferay" if render_list else "praha_rss"
        obj = {"source": "praha.eu", "kraj": "Hlavní město Praha", "platform": plat, "programs": combined}
        json.dump(obj, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return combined

    if not a.no_render:
        try:
            render_progs = harvest_render(a.out, lambda lst: dump(lst, rss_progs))
            method.append("Liferay-render")
        except Exception as e:
            print(f"RENDER FAILED: {str(e)[:120]}", file=sys.stderr)

    if not a.no_rss:
        try:
            rss_progs = harvest_rss()
            method.append("RSS")
        except Exception as e:
            print(f"RSS FAILED: {str(e)[:120]}", file=sys.stderr)

    combined = dump(render_progs, rss_progs)
    print(json.dumps({"MARKER": "PRAHA_HARVEST", "method": "+".join(method) or "nepodařilo",
                      "render": len(render_progs), "rss": len(rss_progs),
                      "combined": len(combined), "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
