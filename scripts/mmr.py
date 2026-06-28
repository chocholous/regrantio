#!/usr/bin/env python3
"""Ministerstvo pro místní rozvoj (mmr.cz → mmr.gov.cz) — vrstva 1, NÁRODNÍ dotace.

MMR = velký víceagendový web (Kentico, server-rendered). Národní dotace jsou pod /cs/narodni-dotace
v kategoriích (Podpora a rozvoj regionů, Cestovní ruch, NNO, ŽIVEL, Územní plánování…); jednotlivé
programy = stránky /Narodni-dotace/<Kategorie>/<Program-ROK>. Detail nese SEZNAM dokumentů (Výzva
+ přílohy) — konkrétní lhůta/alokace/oprávnění žadatelé jsou ve Výzva PDF → vrstva 2 z příloh.

Vlastní parser: discovery programů z kategorií + filtr na AKTUÁLNÍ ROČNÍK (2026/2025+; archiv 2019–2024
a evergreen ŽIVEL). POZOR scope:
  • IROP / OP / fondy EU NEjsou (P3 EU) — jen národní zdroje.
  • Kategorie „Podpora bydlení" je převážně SFPI (už máme scripts/sfpi.py) → VYNECHÁNA.
Status NEpočítá (kód z deadline z Výzvy).

Výstup (shodný tvar jako sfdi/mpo → build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění z kořene repa: python3 scripts/mmr.py --out data/mmr_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):  # Windows cp1250 konzole neumí české diagnostiky → UTF-8
    sys.stdout.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
B = "https://mmr.gov.cz"
HOST = "mmr.gov.cz"
# kategorie národních dotací k procházení (bez „podpora-bydleni" = SFPI overlap, bez EU/IROP)
CATEGORIES = [
    "podpora-a-rozvoj-regionu", "cestovni-ruch",
    "dotace-pro-nestatni-neziskove-organizace", "zivel-2",
    "zivel-1-obnova-majetku-po-krizovych-stavech", "zivel-pomoc-v-nouzi-zivel-4",
]
PROG_RE = re.compile(r'<a[^>]+href="(/Narodni-dotace/[^"]+)"[^>]*>(.*?)</a>', re.S)
DOC_RE = re.compile(r'href="([^"]+\.(?:pdf|docx?|xlsx?)[^"]*)"', re.I)
YEAR_RE = re.compile(r"\b(20\d\d)\b")


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
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def is_current(label):
    """Aktuální ročník: obsahuje 2026 nebo 2025; nebo bez roku (evergreen, ŽIVEL); ne archiv 2019–2024."""
    years = [int(y) for y in YEAR_RE.findall(label)]
    if label.strip().lower() in ("archiv",):
        return False
    if not years:
        return True
    return max(years) >= 2025


def discover():
    """Programy z kategorií, jen aktuální ročník. Vrátí list (url, label)."""
    seen, out = {}, []
    for cat in CATEGORIES:
        try:
            h = fetch(f"{B}/cs/narodni-dotace/{cat}")
        except Exception as e:
            print(f"  ⚠ kategorie {cat}: {str(e)[:50]}", flush=True)
            continue
        for m in PROG_RE.finditer(h):
            href = m.group(1).split("?")[0]
            label = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
            if not label or len(label) < 6 or href in seen:
                continue
            if href.rstrip("/").lower().endswith(("/archiv", "narodni-dotace")):
                continue
            if is_current(label):
                seen[href] = label
                out.append((urljoin(B, href), label))
        time.sleep(0.2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/mmr_documents.jsonl")
    args = ap.parse_args()
    recs = []
    for url, label in discover():
        try:
            h = fetch(url)
        except Exception as e:
            print(f"  ⚠ {label}: fetch selhal → přeskakuji ({str(e)[:45]})", flush=True)
            continue
        # tělo: od 2. výskytu názvu programu po patičku (Odebírejte/Kontakty)
        full = to_text(h)
        base = re.split(r"\s+20\d\d", label)[0][:30]
        k = full.find(base, 2500)
        body = full[k:] if k > 0 else full[2500:]
        for end in ("Odebírejte aktualizace", "Kontakty\nMinisterstvo", "\nKontakty"):
            j = body.find(end)
            if j > 150:
                body = body[:j].strip()
        if len(body) < 80:
            body = full[2500:5000].strip()
        atts, seen = [], set()
        for href in DOC_RE.findall(h):
            u = urljoin(B, html.unescape(href))
            if u not in seen:
                seen.add(u)
                atts.append({"url": u, "label": u.rsplit("/", 1)[-1]})
        # přednost Výzva dokumenty (lhůta/alokace tam) — když jsou, vezmi jen je
        key = [a for a in atts if re.search(r"vyzv|výzv", a["label"], re.I)]
        atts = key or atts[:3]
        recs.append({"url": url, "host": HOST, "title": label,
                     "body_text": body, "attachments": atts, "n_attachments": len(atts)})
        time.sleep(0.3)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  att={r['n_attachments']:2} body={len(r['body_text']):5} :: {r['title'][:56]}", flush=True)
    print(f"MMR_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
