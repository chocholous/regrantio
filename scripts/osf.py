#!/usr/bin/env python3
"""Nadace OSF (Open Society Fund Praha; osf.cz) — vrstva 1.

Jeden z největších nezávislých českých grantmakerů (občanská společnost, demokracie, lidská práva,
inkluzivní vzdělávání, nezávislá média). Rozděluje prostředky přes vlastní programy (Stronger Roots,
Advokační forum, Novinářská cena, Vzdělávání…) a donorské fondy (Fond pro moderní stát, Fond Generace
OSF, NF Hyundai, Fond Daniela Anýže, Active Citizens Fund). WordPress + Elementor (REST `pages`).

K 2026-06 NEMÁ otevřenou žadatelskou výzvu (Stronger Roots 2026–2027 už rozdělen 11/2025; ostatní jsou
donorské fondy, ne applicant-calls) → reprezentace = 1 `foundation_mission` (jako NROS/VDV/O2 v datasetu).
Harvester je ale FUTURE-PROOF: discoveruje i pages se slug „…vyzva…" aktuálního roku, které NEjsou
uzavřené (`--year`); až OSF vypíše novou výzvu, re-harvest ji zachytí jako grant. Status NEpočítá (kód).

Výstup (tvar pro build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments, _kind: about|grant}

Spuštění z kořene repa: python3 scripts/osf.py --out data/osf_documents.jsonl
"""
import argparse, json, os, re, sys, html, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí české diagnostiky → UTF-8
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
B = "https://osf.cz"
HOST = "osf.cz"
ABOUT_ID = 29446  # „Co děláme" — přehled programů a fondů (zdroj pro mission)
# uzavřená NEBO už rozhodnutá (oznámené výsledky / seznam podpořených) = není otevřená příležitost
CLOSED_RE = re.compile(r"byla\s+uzav[řr]ena|v[ýy]zva\s+(?:je\s+)?uzav[řr]en|ukon[čc]en[ao]?\s+p[řr][íi]jem|"
                       r"ozn[áa]mili\s+(?:jsme\s+)?v[ýy]sledky|podpo[řr]en[éy]\s+organizac|"
                       r"podporu[^.\n]{0,40}z[íi]skal", re.I)
# FAQ / dotazy / publikace nejsou výzva
NOT_CALL_SLUG = re.compile(r"casto-kladene-dotazy|faq|publikace|seminar|webinar|zaznam", re.I)


def fetch_json(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with http_util.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def clean_text(c):
    c = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", c or "")
    c = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</h[1-6]>|</div>|</td>", "\n", c)
    t = html.unescape(re.sub(r"<[^>]+>", " ", c))
    t = re.sub(r"[ \t ]+", " ", t)
    t = "\n".join(ln.strip() for ln in t.split("\n") if ln.strip())
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def page(pid, fields="link,title,content"):
    return fetch_json(f"{B}/wp-json/wp/v2/pages/{pid}?_fields={fields}")


def discover_calls(year):
    """Pages se slug obsahujícím 'vyzva'/'grantova-vyzva' a rokem == year (jen cs, ne /en/)."""
    out = []
    for pg in range(1, 8):
        d = fetch_json(f"{B}/wp-json/wp/v2/pages?per_page=100&page={pg}&_fields=id,slug,link,title")
        for p in d:
            link = p.get("link", "")
            if "/en/" in link:
                continue
            slug = p.get("slug", "")
            if NOT_CALL_SLUG.search(slug):
                continue
            if re.search(r"vyzva", slug, re.I) and str(year) in (slug + link):
                out.append(p)
        if len(d) < 100:
            break
    return out


def main():
    from datetime import date
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/osf_documents.jsonl")
    ap.add_argument("--year", type=int, default=date.today().year)
    args = ap.parse_args()

    recs = []
    # 1) foundation overview → mission
    ab = page(ABOUT_ID)
    recs.append({"url": ab["link"], "host": HOST, "_kind": "about",
                 "title": "Nadace OSF (Open Society Fund Praha)",
                 "body_text": clean_text((ab.get("content") or {}).get("rendered", "")),
                 "attachments": [], "n_attachments": 0})
    # 2) future-proof: otevřené žadatelské výzvy aktuálního roku (teď 0)
    for p in discover_calls(args.year):
        full = page(p["id"])
        body = clean_text((full.get("content") or {}).get("rendered", ""))
        if CLOSED_RE.search(body):
            print(f"  skip (uzavřená): {p['slug']}", flush=True)
            continue
        title = html.unescape(re.sub(r"<[^>]+>", "", (p.get("title") or {}).get("rendered", ""))).strip()
        recs.append({"url": p["link"], "host": HOST, "_kind": "grant", "title": title,
                     "body_text": body, "attachments": [], "n_attachments": 0})

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  {r['_kind']:5} body={len(r['body_text']):5} :: {r['title'][:55]}", flush=True)
    print(f"OSF_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
