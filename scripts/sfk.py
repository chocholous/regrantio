#!/usr/bin/env python3
"""Státní fond kultury ČR (SFK) — vrstva 1.

SFK = státní fond pro projektovou podporu kultury (zákon č. 239/1992 Sb.). Dedikované domény
(sfkultury.cz, fondkultury.cz) jsou MRTVÉ (bez DNS) → SFK žije na webu Ministerstva kultury
mk.gov.cz (bespoke CMS). Dotace SFK se podávají přes Dotační portál MK (DP MK) ve 3 výzvách
ročně (uzávěrky po „třetinách" roku). Vlastní parser: discovery aktuální stránky „Žádosti o
dotace SFK na rok <ROK>" z SFK rozcestníku (year-agnostic), extrakce oznámení výzev z bespoke
HTML (obsah je amid nav → ořez od „Rada SFK vyhlašuje" po patičku). Status NEpočítá (kód z deadline).

Výstup (shodný tvar jako sfdi/sfzp → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění z kořene repa: python3 scripts/sfk.py --out data/sfk_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí české diagnostiky → UTF-8
    sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
B = "https://mk.gov.cz"
HOST = "mk.gov.cz"
HUB = f"{B}/statni-fond-kultury-cr-cs-42"
FOOT = ("Napište nám", "Spojte se s námi", "HOME |", "INFORMACE O WEBU", "Informace o webu")
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


def to_text(h):
    # POZOR: NEodstraňovat <form> — mk.gov.cz je ASP.NET WebForms a celý obsah je v jednom <form>.
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def discover_dotace_page():
    """Z SFK rozcestníku najdi aktuální stránku 'zadosti-o-dotace-sfk-na-rok-<ROK>'."""
    h = fetch(HUB)
    slugs = re.findall(r'href="(/zadosti-o-dotace-sfk-na-rok-\d{4}[^"]*)"', h)
    if not slugs:
        raise RuntimeError("nenalezena stránka 'Žádosti o dotace SFK na rok …' v rozcestníku")
    # nejnovější rok = nejvyšší číslo v slugu
    return urljoin(B, sorted(slugs, key=lambda s: re.search(r"(\d{4})", s).group(1))[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sfk_documents.jsonl")
    args = ap.parse_args()
    url = discover_dotace_page()
    h = fetch(url)
    full = to_text(h)
    i = full.find("Rada SFK vyhlašuje")              # ořež nav → začni u oznámení výzev
    body = full[i:] if i >= 0 else full
    for end in FOOT:
        j = body.find(end)
        if j > 200:
            body = body[:j].strip()
    m = re.search(r"na rok\s+(\d{4})", url) or re.search(r"na rok (\d{4})", full)
    year = m.group(1) if m else ""
    title = f"Dotace Státního fondu kultury ČR na rok {year}".strip()
    atts, seen = [], set()
    for href in DOC_RE.findall(h):
        u = urljoin(B, html.unescape(href))
        if u not in seen:
            seen.add(u)
            atts.append({"url": u, "label": u.rsplit("/", 1)[-1]})
    rec = {"url": url, "host": HOST, "title": title, "body_text": body,
           "attachments": atts, "n_attachments": len(atts)}
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        o.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"  att={rec['n_attachments']} body={len(rec['body_text'])} :: {rec['title']}", flush=True)
    print(f"SFK_DONE 1 -> {args.out}")


if __name__ == "__main__":
    main()
