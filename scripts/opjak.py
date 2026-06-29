#!/usr/bin/env python3
"""Operační program Jan Amos Komenský 2021–2027 (opjak.cz) — vrstva 1.

OP JAK = velký EU operační program MŠMT (vzdělávání + výzkum/vývoj, ~90 mld Kč): MSCA Fellowships,
Teaming, Smart Akcelerátor, Open Science, akční plánování v území (MAP), špičkový výzkum, AI ve školách.
WordPress, ale výzvy NEjsou v REST (privátní CPT bez show_in_rest) → harvest přes listing `/vyzvy/`
(jen aktuální/otevřené, ~8) → front-end detail. Strukturní blok: název · datumové rozpětí (ČESKÁ jména
měsíců „17. srpna 2022 - 29. června 2029") · Celková alokace · Cíl výzvy. Status NEpočítá (kód z deadline).
Liší se od OPŽP/OPST (nemá CPT `call`, jiný formát data) → vlastní tenký parser. zdroj=eu_fondy, typ=ministerstvo.

Výstup (tvar pro build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění z kořene repa: python3 scripts/opjak.py --out data/opjak_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
B = "https://opjak.cz"
HOST = "opjak.cz"
VYZVA_RE = re.compile(r'href="(https://opjak\.cz/vyzvy/vyzva-[^"?]+)"')
DOC_RE = re.compile(r'<a[^>]+href="([^"]+\.(?:pdf|docx?|xlsx?)[^"]*)"[^>]*>(.*?)</a>', re.I | re.S)


def fetch(url, timeout=30, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(retries):
        try:
            with http_util.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"fetch selhal: {url} ({last})")


def clean(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</h[1-6]>|</td>|</th>|</a>", "\n", h)
    h = re.sub(r"(?i)</div>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    t = re.sub(r"[ \t ]+", " ", t)
    t = "\n".join(ln.strip() for ln in t.split("\n") if ln.strip())
    return re.sub(r"\n{3,}", "\n\n", t).strip()


MONTH = (r"(?:ledna|února|unora|března|brezna|dubna|května|kvetna|června|cervna|"
         r"července|cervence|srpna|září|zari|října|rijna|listopadu|prosince)")
DATERANGE = re.compile(r"\d{1,2}\.\s*" + MONTH + r"\s*20\d\d\s*-\s*\d{1,2}\.\s*" + MONTH + r"\s*20\d\d")


def detail_region(full_text):
    """Slice kolem datumového rozpětí (unikátní v obsahu): od „Výzva č." řádku před ním po ~1600 znaků
    za (zahrnuje alokaci + Cíl výzvy + oprávněného žadatele). Vyhne se nav (Přihlásit/Kontakt nahoře)."""
    m = DATERANGE.search(full_text)
    if not m:
        return ""
    start = m.start()
    # posuň začátek zpět na nejbližší předchozí „Výzva č. NN_NN_NNN" (název výzvy)
    head = full_text.rfind("Výzva č.", max(0, start - 200), start)
    if head == -1:
        head = full_text.rfind("Výzva", max(0, start - 200), start)
    s = head if head != -1 else max(0, start - 80)
    return full_text[s:m.end() + 1600].strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/opjak_documents.jsonl")
    args = ap.parse_args()
    listing = fetch(f"{B}/vyzvy/")
    urls = sorted(set(VYZVA_RE.findall(listing)))
    print(f"  discovery: {len(urls)} výzev (/vyzvy/ listing)", flush=True)
    recs = []
    for url in urls:
        try:
            h = fetch(url)
        except Exception as e:
            print(f"  ⚠ {url.split('/vyzvy/')[-1][:30]}: fetch selhal ({str(e)[:35]})", flush=True)
            continue
        body = detail_region(clean(h))
        if "alokace" not in body.lower() and not re.search(r"20\d\d\s*-\s*\d", body):
            print(f"  ⚠ {url.split('/vyzvy/')[-1][:30]}: bez bloku → skip", flush=True)
            continue
        title = ""
        mt = re.search(r"(V[ýy]zva [čc]\.\s*\d\d_\d\d_\d\d\d[^\n]{0,80})", body)
        if mt:
            title = re.sub(r"\s*-\s*OP JAK\s*$", "", mt.group(1).strip())
        atts, seen = [], set()
        for href, label in DOC_RE.findall(h):
            u = urljoin(B, html.unescape(href))
            lab = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", label))).strip()
            if u not in seen and re.search(r"text v[ýy]zvy|pravidl|p[řr][íi]loh|v[ýy]zva", lab, re.I):
                seen.add(u)
                atts.append({"url": u, "label": lab or u.rsplit("/", 1)[-1]})
        recs.append({"url": url, "host": HOST, "title": title or url.split("/vyzvy/")[-1],
                     "body_text": body, "attachments": atts[:3], "n_attachments": min(len(atts), 3)})
        time.sleep(0.2)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  body={len(r['body_text']):5} :: {r['title'][:55]}", flush=True)
    print(f"OPJAK_DONE {len(recs)}/{len(urls)} -> {args.out}")


if __name__ == "__main__":
    main()
