#!/usr/bin/env python3
"""Grantová agentura ČR (gacr.cz) — vrstva 1.

GA ČR = hlavní český poskytovatel účelové podpory základního výzkumu. Grantové výzvy jsou
WP **posty** typu „Vyhlášení veřejné soutěže <PROGRAM> <ROK>" (Standardní projekty, JUNIOR STAR,
EXPRO, POSTDOC INDIVIDUAL FELLOWSHIP IN/OUT, Mezinárodní-bilaterální, Návratové granty) +
bilaterální LA výzvy „Výzva pro podávání <X>-českých projektů" (iniciativa Weave). Vlastní parser,
protože výzvy jsou posty rozeseté v kategorii Oznámení (ne CPT) — discovery přes fulltext title.

Bohatý a strukturovaný body: „Soutěžní lhůta začíná D" (open_from) · „Návrhy projektů je možné
podávat do D" (deadline) · „Vyhlášení výsledků … D" · IS (GRIS/GRITA). Přílohy = /download-attachment/N
(Vyhlášení soutěže, Zadávací dokumentace, …). Status NEpočítá (dopočte kód z deadline vs dnešek).

Výstup (shodný tvar jako sfzp/sfa/marwel → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění z kořene repa: python3 scripts/gacr.py --out data/gacr_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí české diagnostiky → UTF-8
    sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
B = "https://gacr.cz"
HOST = "gacr.cz"
# Tituly skutečných výzev (ne agregátní „Vyhlášení soutěží …", ne news):
TITLE_RE = re.compile(r"^(Vyhlášení veřejné soutěže|Výzva pro podávání)", re.I)


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


def attachments_of(content):
    """Přílohy = <a href=/download-attachment/N>LABEL</a> + přímé .pdf; label = text odkazu."""
    out, seen = [], set()
    for m in re.finditer(r'href="(https?://gacr\.cz/download-attachment/\d+|[^"]+\.pdf[^"]*)"[^>]*>(.*?)</a>',
                         content, re.I | re.S):
        url = html.unescape(m.group(1))
        label = html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).strip()
        if url not in seen and (label or "download-attachment" in url):
            seen.add(url)
            out.append({"url": url, "label": label or url.rsplit("/", 1)[-1]})
    return out


def discover_calls(since):
    """Fulltext discovery postů jejichž title = skutečná výzva, jen AKTUÁLNÍ cyklus (date >= since).
    Bez date-filtru WP fulltext vrátí všechny ročníky 2022+ (6× tytéž programy) → šum; `since`
    (~10 měsíců) izoluje poslední roční kolo + aktuální bilaterální LA výzvy. Year-agnostic."""
    ids = {}
    for q in ("vyhlášení veřejné soutěže", "výzva pro podávání"):
        for r in getj(f"{B}/wp-json/wp/v2/posts?search={quote(q)}&per_page=50&after={since}T00:00:00"
                      "&_fields=id,slug,link,title,date"):
            title = html.unescape(re.sub(r"<[^>]+>", "", (r.get("title") or {}).get("rendered", ""))).strip()
            if TITLE_RE.match(title):
                ids[r["id"]] = (r, title)
    return list(ids.values())


def main():
    from datetime import date, timedelta
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/gacr_documents.jsonl")
    ap.add_argument("--since", default=(date.today() - timedelta(days=300)).isoformat(),
                    help="jen výzvy publikované od tohoto data (default ~10 měsíců = aktuální roční kolo)")
    args = ap.parse_args()
    recs = []
    for stub, title in discover_calls(args.since):
        d = getj(f"{B}/wp-json/wp/v2/posts/{stub['id']}?_fields=id,slug,link,title,content")
        content = (d.get("content") or {}).get("rendered", "")
        body = to_text(content)
        if len(body) < 120:
            print(f"  ⚠ {stub['slug']}: prázdné tělo ({len(body)}) → přeskakuji", flush=True)
            continue
        atts = attachments_of(content)
        recs.append({"url": d.get("link") or f"{B}/{stub['slug']}/", "host": HOST,
                     "title": title, "body_text": body,
                     "attachments": atts, "n_attachments": len(atts)})
        time.sleep(0.2)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  att={r['n_attachments']:2} body={len(r['body_text']):5} :: {r['title'][:66]}", flush=True)
    print(f"GACR_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
