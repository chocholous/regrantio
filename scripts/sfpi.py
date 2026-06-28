#!/usr/bin/env python3
"""Státní fond podpory investic (sfpi.cz, dříve SFRB – Státní fond rozvoje bydlení) — vrstva 1.

SFPI = státní fond pro podporu bydlení a investic (úvěry + dotace): Dostupné nájemní bydlení,
Výstavba pro obce, Nájemní byty, Regenerace sídlišť, Zateplování, Panel 2013+, Vlastní bydlení,
Živel, Úsporné bytové domy, Bytové domy bez bariér, Program 150/600 aj. WordPress; programy jsou
WP **pages** typu „program-hub" (akordeon: Aktuálně / Zaměření / Základní informace / Formuláře).
Status (otevřeno / pozastaveno / ukončeno) je v próze hubu → vrstva 2 + kód.

Vlastní parser: programy nejsou CPT (`project` je prázdný); discovery filtruje top-level pages
podle title (program-keyword) a VYLUČUJE sub-stránky (dokumenty/žádost/čerpání/výzva), archivy
a kariéru. Status NEpočítá (dopočte kód z deadline).

Výstup (shodný tvar jako sfzp/gacr → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění z kořene repa: python3 scripts/sfpi.py --out data/sfpi_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí české diagnostiky → UTF-8
    sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
B = "https://sfpi.cz"
HOST = "sfpi.cz"
# program hub title obsahuje téma bydlení/programu…
PROG_KW = re.compile(r"(byt|bydlen|nájemn|najemn|regenerac|zateplov|panel|živel|zivel|vlastní|vlastni|"
                     r"výstavb|vystavb|mlad|bariér|barier|úsporn|usporn|uprchlík|uprchlik|sídl|sidl|"
                     r"program\s*(150|600|pro))", re.I)
# …ale NE sub-stránka (dokumenty/žádost/čerpání/výzva), archiv, COVID, kariéra
EXCL_KW = re.compile(r"(dokument|žádost|zadost|čerpání|cerpani|ke stažení|stažen|stazen|výzv|vyzv|"
                     r"metodick|modernizac|draft|otázk|otazk|kalkulačk|kalkulack|portál|portal|"
                     r"referent|člen|clen|vedoucí|vedouci|stavební|stavebni|manažer|manazer|archiv|covid)", re.I)
DOC_RE = re.compile(r'href="([^"]+\.(?:pdf|docx?|xlsx?)[^"]*)"', re.I)


def fetch(url, timeout=30, retries=3):
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


def to_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def docs_from(content):
    out, seen = [], set()
    for href in DOC_RE.findall(content):
        u = html.unescape(href)
        if u not in seen:
            seen.add(u)
            out.append({"url": u, "label": u.rsplit("/", 1)[-1]})
    return out


def discover():
    """Top-level pages, jejichž title je program (PROG_KW) a NE sub-stránka/archiv (EXCL_KW)."""
    pages = []
    for pg in (1, 2):
        pages += getj(f"{B}/wp-json/wp/v2/pages?per_page=100&page={pg}&_fields=id,slug,link,title,parent")
    out = []
    for p in pages:
        t = html.unescape(re.sub(r"<[^>]+>", "", (p.get("title") or {}).get("rendered", ""))).strip()
        s = p.get("slug", "")
        if p.get("parent") == 0 and PROG_KW.search(t) and not EXCL_KW.search(t) and not s.startswith("archiv"):
            out.append((p, t))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sfpi_documents.jsonl")
    args = ap.parse_args()
    recs = []
    for stub, title in discover():
        try:
            d = getj(f"{B}/wp-json/wp/v2/pages/{stub['id']}?_fields=id,slug,link,title,content")
        except Exception as e:                   # alias/redirect stránka (timeout) → přeskoč, neshazuj běh
            print(f"  ⚠ {stub['slug']} (id={stub['id']}): fetch selhal → přeskakuji ({str(e)[:60]})", flush=True)
            continue
        content = (d.get("content") or {}).get("rendered", "")
        body = to_text(content)
        if len(body) < 150:                      # akordeon bez serverového obsahu → přeskoč (NAHLAS)
            print(f"  ⚠ {stub['slug']}: tělo {len(body)} zn → přeskakuji", flush=True)
            continue
        recs.append({"url": d.get("link") or f"{B}/{stub['slug']}/", "host": HOST,
                     "title": title, "body_text": body,
                     "attachments": docs_from(content), "n_attachments": len(docs_from(content))})
        time.sleep(0.2)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  att={r['n_attachments']:2} body={len(r['body_text']):5} :: {r['title'][:60]}", flush=True)
    print(f"SFPI_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
