#!/usr/bin/env python3
"""Operační program Životní prostředí 2021–2027 (opzp.cz) — vrstva 1.

OPŽP = velký EU operační program (řídící orgán MŽP, zprostředkující SFŽP). Energetické úspory, OZE,
adaptace na klima a prevence rizik, vodovody/kanalizace, odpady/oběhové hospodářství, příroda a
biodiverzita. WordPress s CPT `call` (121 výzev 2021–2027). POZOR: `call` content.rendered nese jen
„Popis" (Specifický cíl / Opatření) + dokumenty; STRUKTURNÍ blok (Stav · Druh výzvy · Podání žádosti
od-do · Alokace) je renderovaný JEN ve FRONT-END HTML → harvest HTML (jako tacr.py). Status NEpočítá
(kód z deadline = konec příjmu žádostí). zdroj=eu_fondy, typ_poskytovatele=ministerstvo (jako IROP).

Výstup (tvar pro build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění z kořene repa: python3 scripts/opzp.py --out data/opzp_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí české diagnostiky → UTF-8
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
B = "https://opzp.cz"
HOST = "opzp.cz"
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


def getj(url):
    body = fetch(url)
    return json.loads(body)


def clean(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</h[1-6]>|</div>|</td>|</th>|</a>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    t = re.sub(r"[ \t ]+", " ", t)
    t = "\n".join(ln.strip() for ln in t.split("\n") if ln.strip())
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def detail_block(full_text, title):
    """Vyřízni detailní region (perex+Stav+Druh+Podání+Alokace+Popis) — kotva na breadcrumb „Detail výzvy"
    (na rozdíl od názvu, který je i v <title>/menu). Konec u „Dokumenty k výzvě"/„Základní dokumenty"."""
    m = re.search(r"Detail v[ýy]zvy\s*\n(.{40,2000}?)(?:Dokumenty k v[ýy]zv|Z[áa]kladn[íi] dokumenty|Sdílet|Souvisej[íi]c[íi])",
                  full_text, re.S)
    seg = m.group(1).strip() if m else ""
    if "Alokace" not in seg:  # fallback: přímo blok Stav→Alokace + Popis
        m2 = re.search(r"(Stav v[ýy]zvy.{40,1500}?)(?:Dokumenty k v[ýy]zv|Z[áa]kladn[íi] dokumenty|Sd[íi]let)", full_text, re.S)
        seg = m2.group(1).strip() if m2 else seg
    return seg


def discover():
    calls = []
    for pg in range(1, 4):
        batch = getj(f"{B}/wp-json/wp/v2/call?per_page=100&page={pg}&_fields=id,slug,link,title")
        calls += batch
        if len(batch) < 100:
            break
    return calls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/opzp_documents.jsonl")
    args = ap.parse_args()
    calls = discover()
    print(f"  discovery: {len(calls)} výzev (CPT call)", flush=True)
    recs = []
    for c in calls:
        url = c.get("link") or ""
        title = html.unescape(re.sub(r"<[^>]+>", "", (c.get("title") or {}).get("rendered", ""))).strip()
        try:
            h = fetch(url)
        except Exception as e:
            print(f"  ⚠ {c['slug']}: fetch selhal → přeskakuji ({str(e)[:40]})", flush=True)
            continue
        ft = clean(h)
        body = detail_block(ft, title)
        if "Alokace" not in body and "Podán" not in body and "Podan" not in body:
            print(f"  ⚠ {c['slug']}: bez strukturního bloku → přeskakuji", flush=True)
            continue
        atts, seen = [], set()
        for href, label in DOC_RE.findall(h):
            u = urljoin(B, html.unescape(href))
            lab = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", label))).strip()
            if u in seen:
                continue
            if re.search(r"text v[ýy]zvy|pravidl|p[řr][íi]loh", lab, re.I):
                seen.add(u)
                atts.append({"url": u, "label": lab or u.rsplit("/", 1)[-1]})
        recs.append({"url": url, "host": HOST, "title": title, "body_text": body,
                     "attachments": atts[:3], "n_attachments": min(len(atts), 3)})
        time.sleep(0.15)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"OPZP_DONE {len(recs)}/{len(calls)} -> {args.out}")


if __name__ == "__main__":
    main()
