#!/usr/bin/env python3
"""Technologická agentura ČR (tacr.cz → tacr.gov.cz) — vrstva 1.

TA ČR = hlavní český poskytovatel ÚČELOVÉ podpory aplikovaného výzkumu (miliardy/rok). Veřejné
soutěže jako GA ČR, ale napříč ~10 aktivními programy (SIGMA, TREND, DOPRAVA 2030, THÉTA 2,
Prostředí pro život 2, Národní centra kompetence, PRODEF, Eurostars, mezinárodní CET/DUT/QuantERA…).

WordPress s CPT `call` (veřejné soutěže) + `programme`. POZOR: `call` content.rendered nese JEN
„Dokumenty ke stažení" (Kadence builder); strukturované info (Vyhlášení · Soutěžní lhůta od-do ·
Alokace · Termín výsledků) je renderované JEN ve FRONT-END HTML → harvest HTML. Program se odvodí
z URL výzvy `/soutez/<programme-slug>/`. Discovery `call` CPT + filtr aktuálního cyklu (--since).
Status NEpočítá (kód z deadline = konec soutěžní lhůty).

Výstup (shodný tvar jako gacr/sfdi → build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění z kořene repa: python3 scripts/tacr.py --out data/tacr_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí české diagnostiky → UTF-8
    sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
B = "https://tacr.gov.cz"
HOST = "tacr.gov.cz"
DOC_RE = re.compile(r'href="([^"]+\.(?:pdf|docx?|xlsx?)[^"]*)"', re.I)


def fetch(url, timeout=35, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(retries):
        try:
            with http_util.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8", "replace")
            if body.strip():
                return body
            last = "prázdná odpověď"
        except Exception as e:
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch selhal po {retries} pokusech: {url} ({last})")


def getj(url):
    body = fetch(url)
    if body.lstrip()[:1] not in ("[", "{"):
        raise RuntimeError(f"očekáván JSON, dostal {body.lstrip()[:30]!r} z {url}")
    return json.loads(body)


def page_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    # vyhoď zbytkové Kadence CSS řádky
    t = "\n".join(ln for ln in t.split("\n") if not re.search(r"\.(kt-|wp-block|kadence)|#kt-|font-size|height:|width:|[{}]", ln))
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


D = r"\d{1,2}\.\s*\d{1,2}\.\s*20\d\d"  # POZOR: české datum obsahuje tečky → ne [^.]


def info_block(t):
    """Klíčové údaje do čistého labelovaného bloku (date-aware, lhůta může být daleko od „Vyhlášení")."""
    out = []
    v = re.search(r"vyhlásila[^0-9]{0,150}?dne\s*(" + D + ")", t)
    if v:
        out.append(f"Vyhlášení: {re.sub(r'\\s+', ' ', v.group(1))}")
    sl = re.search(r"Soutěžní lhůta začíná dnem\s*(" + D + r")[\s\S]{0,90}?končí dnem\s*(" + D + ")", t)
    if sl:
        out.append(f"Soutěžní lhůta: od {re.sub(r'\\s+', ' ', sl.group(1))} do {re.sub(r'\\s+', ' ', sl.group(2))}")
    al = re.search(r"Alokace[\s:]*([^.\n]{0,130}?(?:mil\.?|mld\.?)\s*Kč[^.\n]{0,15}|[^.\n]{0,90}?\d[\d  ]{4,}\s*Kč)", t)
    if al:
        out.append(f"Alokace: {re.sub(r'\\s+', ' ', al.group(1)).strip()}")
    if re.search(r"výsledk[ůy] formální kontroly|Vyhlášení výsledků", t):
        out.append("Stav: příjem žádostí ukončen (probíhá hodnocení).")
    if re.search(r"odkládá|informuje o přípravě", t) and not sl:
        out.append("Stav: vyhlášení odloženo / soutěž v přípravě.")
    cil = re.search(r"((?:Hlavním cílem|je zaměřen|jsou zaměřen|se zaměřuje)[^.]{0,320}\.)", t)
    if cil:
        out.append(re.sub(r"\s+", " ", cil.group(1)).strip())
    return "\n".join(out)


def discover(since):
    progs = {}
    for p in getj(f"{B}/wp-json/wp/v2/programme?per_page=100&_fields=id,slug,title"):
        progs[p["slug"]] = html.unescape(re.sub(r"<[^>]+>", "", (p.get("title") or {}).get("rendered", ""))).strip()
    calls = []
    for pg in (1, 2, 3):
        batch = getj(f"{B}/wp-json/wp/v2/call?per_page=100&page={pg}&after={since}T00:00:00"
                     "&_fields=id,slug,link,title,date")
        calls += batch
        if len(batch) < 100:
            break
    return progs, calls


def main():
    from datetime import date, timedelta
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/tacr_documents.jsonl")
    ap.add_argument("--since", default=(date.today() - timedelta(days=420)).isoformat(),
                    help="jen výzvy vyhlášené od (default ~14 měsíců = aktuální cyklus soutěží)")
    args = ap.parse_args()
    progs, calls = discover(args.since)
    recs = []
    for c in calls:
        url = c.get("link") or ""
        m = re.search(r"/soutez/([^/]+)/", url)
        prog = progs.get(m.group(1), m.group(1).replace("-", " ").title()) if m else ""
        ctitle = html.unescape(re.sub(r"<[^>]+>", "", (c.get("title") or {}).get("rendered", ""))).strip()
        try:
            h = fetch(url)
        except Exception as e:
            print(f"  ⚠ {c['slug']}: fetch selhal → přeskakuji ({str(e)[:45]})", flush=True)
            continue
        info = info_block(page_text(h))
        if "Soutěžní lhůta" not in info and "Vyhlášení" not in info:
            print(f"  ⚠ {c['slug']}: bez info bloku → přeskakuji", flush=True)
            continue
        body = f"{prog} – {ctitle}\n\n{info}"
        atts, seen = [], set()
        for href in DOC_RE.findall(h):
            u = urljoin(B, html.unescape(href))
            if re.search(r"zadavaci|pravidla|prirucka|výzv|vyzv", u, re.I) and u not in seen:
                seen.add(u)
                atts.append({"url": u, "label": u.rsplit("/", 1)[-1]})
        recs.append({"url": url, "host": HOST, "title": f"{prog} – {ctitle}".strip(" –"),
                     "body_text": body, "attachments": atts[:3], "n_attachments": min(len(atts), 3)})
        time.sleep(0.3)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  att={r['n_attachments']:2} body={len(r['body_text']):5} :: {r['title'][:60]}", flush=True)
    print(f"TACR_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
