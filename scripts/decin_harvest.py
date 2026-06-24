#!/usr/bin/env python3
"""Děčín harvester — dotační programy statutárního města Děčín (VERA Portál občana).

ZDROJ / METODA: data o dotačních programech jsou inline JSON embedovaný ve statickém
HTML portálu VERA (https://portal.mmdecin.cz/wab/dotace/Dotace.action) jako
const oblastiJson = `[...]`. ŽÁDNÝ Playwright/render není potřeba — stačí čistý
curl/urllib + regex extrakce JSON. (joomla web dotace.mmdecin.cz má jen prózu bez
termínů; strukturovaná data včetně termínů/alokací/příloh jsou jen v portálu.)

Struktura: oblasti[] → vyzvy[] (rok) → dotacniProgramy[] s poli:
  nazev, stav, platnostOd/Do, prijemZadostiOd/Do (ms epoch, lokální čas Europe/Prague),
  castkaCelkem (alokace), ucel, pokyny, prilohyDotacnihoProgramu[].

Mapování na kontrakt ingest_kraj.py:
  open_from = prijemZadostiOd, deadline = prijemZadostiDo  (okno PŘÍJMU žádostí)
  alokace_czk = castkaCelkem; popis = pokyny (kontaktní/termínový text)
  url = veřejná oblastní stránka na dotace.mmdecin.cz (portál deep-link vyžaduje login)
  status = null → dopočítá ingest z termínů (stav="V realizaci" je lifecycle programu,
           NE open/closed okna příjmu — proto se nepředává).
Cíl = OTEVŘENÉ výzvy (programy s oknem příjmu žádostí), NE awards/příjemci.

Lossless: ukládá parsed pole + plný ucel/pokyny + seznam příloh + epoch + stav.

Usage: python3 scripts/decin_harvest.py [--out data/h_mesto_decin.json]
"""
import argparse, json, re, sys, urllib.request
import http_util   # jednotná TLS politika (audit #7/#32)
from datetime import datetime
from zoneinfo import ZoneInfo

PORTAL = "https://portal.mmdecin.cz/wab/dotace/Dotace.action"
# veřejné (bez loginu) oblastní stránky na joomla webu — stabilní URL pro člověka
JOOMLA = "https://dotace.mmdecin.cz/index.php/dotacni-programy"
OBLAST_SLUG = {
    "Sport": "sport", "Kultura": "kultura", "Zájmová činnost": "zajmova-cinnost",
    "Sociální oblast": "socialni-oblast", "Čistírny odpadních vod": "cistirny-odpadnich-vod",
    "Inženýrské sítě": "inzenyrske-site", "Ostatní": "ostatni",
}
TZ = ZoneInfo("Europe/Prague")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return http_util.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def iso(ms):
    """ms epoch (lokální Europe/Prague) → ISO datum, jinak None."""
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, TZ).strftime("%Y-%m-%d")


def oblast_url(nazev):
    slug = OBLAST_SLUG.get(nazev)
    return f"{JOOMLA}/{slug}" if slug else PORTAL


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/h_mesto_decin.json")
    a = ap.parse_args()

    html = fetch(PORTAL)
    m = re.search(r"const oblastiJson = `(\[.*?\])`;", html, re.S)
    if not m:
        print(json.dumps({"MARKER": "DECIN_HARVEST_ERR",
                          "err": "oblastiJson nenalezen v portálu (změna struktury?)"},
                         ensure_ascii=False))
        sys.exit(1)
    data = json.loads(m.group(1))

    progs, seen = [], set()
    for ob in data:
        oblast = ob.get("oblastNazev")
        url = oblast_url(oblast)
        # programy mohou viset přímo na oblasti i pod výzvami (rok)
        buckets = [("", ob.get("dotacniProgramy", []))]
        for v in ob.get("vyzvy", []):
            buckets.append((v.get("nazev"), v.get("dotacniProgramy", [])))
        for vyzva_nazev, plist in buckets:
            for p in plist:
                pid = p.get("id")
                if pid in seen:
                    continue
                seen.add(pid)
                alok = p.get("castkaCelkem")
                rec = {
                    "nazev": (p.get("nazev") or "").strip(),
                    "open_from": iso(p.get("prijemZadostiOd")),
                    "deadline": iso(p.get("prijemZadostiDo")),
                    "status": None,  # dopočítá ingest z termínů
                    "alokace_czk": int(alok) if alok else None,
                    "max_czk": None,  # není v datech portálu (max/žadatel je až v PDF)
                    "popis": (p.get("pokyny") or p.get("ucel") or "").replace("\\n", "\n").strip() or None,
                    "eligible": None,  # není strukturovaně (jen próza v oblastní stránce)
                    "kod": None,  # portál nemá veřejný kód programu
                    "url": url,
                    # lossless extra (ingest je ignoruje, ale neztrácíme data)
                    "_oblast": oblast,
                    "_vyzva": vyzva_nazev or None,
                    "_program_id": pid,
                    "_stav": p.get("stav"),
                    "_platnost_od": iso(p.get("platnostOd")),
                    "_platnost_do": iso(p.get("platnostDo")),
                    "_castka_schvaleno": p.get("castkaShvaleno"),
                    "_castka_zbyva": p.get("castkaZbyva"),
                    "_prilohy": [{"nazev": x.get("nazev"), "id": x.get("id"),
                                  "velikost_kb": x.get("velikost")}
                                 for x in p.get("prilohyDotacnihoProgramu", [])],
                }
                progs.append(rec)
                # průběžné ukládání
                json.dump({"source": "mmdecin.cz", "kraj": "Ústecký kraj", "obec": "Děčín",
                           "uroven": "obec", "platform": "decin_joomla", "programs": progs},
                          open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(json.dumps({"MARKER": "DECIN_HARVEST", "kept": len(progs), "oblasti": len(data),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
