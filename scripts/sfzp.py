#!/usr/bin/env python3
"""Státní fond životního prostředí (sfzp.cz / sfzp.gov.cz) — vrstva 1.

Nejobjemnější český poskytovatel dotací (Modernizační fond, OPŽP, Národní program ŽP,
finanční nástroje/půjčky). Výzvy leží ve DVOU oddělených systémech jednoho WP webu —
proto vlastní parser (generický wp_harvest/harvest_site by je nesložil dohromady):

  A) NÁRODNÍ PROGRAM / FN / PU výzvy = samostatné WP **stránky** se slugem `vyzva-*`
     (REST `/wp-json/wp/v2/pages`). Bohatý content.rendered + přílohy (.pdf/.docx/.xlsx).
  B) MODERNIZAČNÍ FOND výzvy (HEAT, RES+, ENERG, KOMUNERG…) = NEjsou WP stránky, ale
     id-řízené detaily renderované SERVER-SIDE na pevné cestě
     `/dotace-a-pujcky/modernizacni-fond/vyzvy/detail-vyzvy/?id=NN`. Seznam id se škrábe
     z rozcestníku `…/modernizacni-fond/vyzvy/`. Obsah je v `div.challenge__description`
     (Na co / Kdo může žádat / Výše příspěvku / Termíny) + datum/alokace v `div.challenges__date`.

Výstup (shodný tvar jako sfa/marwel/eagri → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}
  — 1 záznam per výzva (oba systémy). Status NEpočítá (to dělá kód po vrstvě 2 z lhůt).

Spuštění z kořene repa: python3 scripts/sfzp.py --out data/sfzp_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util   # jednotná TLS politika (audit #7/#32; sfzp.cz posílá neúplný řetězec → auto-fallback)

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí české diagnostiky → vynuť UTF-8
    sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
WP = "https://www.sfzp.cz"                                    # WP REST (vrací 200)
GOV = "https://sfzp.gov.cz"                                   # kanonická doména (redirect target) pro MF detaily
MF_HUB = f"{GOV}/dotace-a-pujcky/modernizacni-fond/vyzvy/"
HOST = "sfzp.gov.cz"
DOC_RE = re.compile(r'href="([^"]+\.(?:pdf|docx?|xlsx?)[^"]*)"', re.I)


def fetch(url, timeout=30, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(retries):
        try:
            with http_util.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8", "replace")
            if body.strip():                    # prázdná odpověď (transient WAF/TLS-fallback) → opakuj
                return body
            last = "prázdná odpověď"
        except Exception as e:                  # timeout/reset → opakuj
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch selhal po {retries} pokusech: {url} ({last})")


def getj(url, timeout=30):
    body = fetch(url, timeout)
    if body.lstrip()[:1] not in ("[", "{"):    # WAF/HTML místo JSON (velký content payload na sfzp CDN) → chyba
        raise RuntimeError(f"očekáván JSON, dostal {body.lstrip()[:30]!r} z {url}")
    return json.loads(body)


def to_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def docs_from(htmlseg, base):
    """Reálné dokumenty (.pdf/.doc/.docx/.xls/.xlsx) z výseče HTML → [{url,label}], dedup."""
    out, seen = [], set()
    for href in DOC_RE.findall(htmlseg):
        u = urljoin(base, html.unescape(href))
        if u not in seen:
            seen.add(u)
            out.append({"url": u, "label": u.rsplit("/", 1)[-1]})
    return out


def slice_div(h, cls):
    """Balancovaná výseč <div ...class=…cls…> … </div> (správně i s vnořenými divy)."""
    m = re.search(r'<div\b[^>]*class=["\'][^"\']*' + re.escape(cls) + r'[^"\']*["\']', h)
    if not m:
        return ""
    start = m.start()
    depth = 0
    for t in re.finditer(r"<div\b|</div>", h[start:]):
        depth += 1 if t.group() == "<div" else -1
        if depth == 0:
            return h[start:start + t.end()]
    return h[start:]


# ---- A) národní/FN/PU výzvy = WP pages slug vyzva-* ----------------------------------
def wp_vyzva_pages():
    # 1) seznam stránek BEZ content (malý/spolehlivý); bulk `content` payload sfzp CDN vrací HTML WAF stránku
    pages = []
    for pg in (1, 2, 3):
        batch = getj(f"{WP}/wp-json/wp/v2/pages?per_page=100&page={pg}&_fields=id,slug,link")
        pages += batch
        if len(batch) < 100:
            break
    targets = [p for p in pages if re.match(r"vyzva", p.get("slug", "")) and p.get("slug") != "vyzvy"]
    # 2) content každé výzvy zvlášť (po id) — malé requesty, žádný WAF
    out = []
    for p in targets:
        d = getj(f"{WP}/wp-json/wp/v2/pages/{p['id']}?_fields=id,slug,link,title,content")
        content = (d.get("content") or {}).get("rendered", "")
        title = html.unescape(re.sub(r"<[^>]+>", "", (d.get("title") or {}).get("rendered", ""))).strip()
        body = to_text(content)
        if len(body) < 120:                                  # prázdná/redirect stránka → přeskoč
            continue
        atts = docs_from(content, d.get("link") or WP)
        out.append({"url": d.get("link") or f"{WP}/{p['slug']}/", "host": HOST,
                    "title": title, "body_text": body,
                    "attachments": atts, "n_attachments": len(atts)})
        time.sleep(0.2)
    return out


# ---- B) Modernizační fond výzvy = id-řízené server-rendered detaily -------------------
def mf_vyzvy():
    hub = fetch(MF_HUB)
    ids = sorted(set(int(x) for x in re.findall(r"detail-vyzvy/\?id=(\d+)", hub)))
    out = []
    for vid in ids:
        url = f"{MF_HUB}detail-vyzvy/?id={vid}"
        h = fetch(url)
        tm = re.search(r'<span class="title">(.*?)</span>', h, re.S)
        title = html.unescape(re.sub(r"<[^>]+>", "", tm.group(1))).strip() if tm else f"Výzva Modernizačního fondu id={vid}"
        desc = slice_div(h, "challenge__description")
        date = slice_div(h, "challenges__date")
        body = (to_text(date) + "\n\n" + to_text(desc)).strip()
        if len(body) < 120:                                  # nenaplněný detail → přeskoč (bug, ne ticho)
            print(f"  ⚠ MF id={vid}: prázdný detail ({len(body)} zn) → přeskakuji", flush=True)
            continue
        atts = docs_from(desc or h, GOV)
        out.append({"url": url, "host": HOST, "title": title, "body_text": body,
                    "attachments": atts, "n_attachments": len(atts)})
        time.sleep(0.3)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sfzp_documents.jsonl")
    args = ap.parse_args()
    recs = wp_vyzva_pages() + mf_vyzvy()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  att={r['n_attachments']:2} body={len(r['body_text']):5} :: {r['title'][:64]}", flush=True)
    print(f"SFZP_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
