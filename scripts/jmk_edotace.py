#!/usr/bin/env python3
"""Jihomoravský kraj, dotační portál e‑dotace.jmk.cz — vrstva 1 (2026‑11‑10).

Proč: úřední deska kraje (`kr-jihomoravsky.cz`, `jm_harvest.py`) je od 1. 9.
za přihlášením (HTTP 401) a zdroj byl zmrazený. Starý výpis desky navíc nesl
data sejmutí z desky místo lhůt a smlouvy či oznámení místo programů. Dotační
portál kraje je veřejný a má u každého programu strukturované údaje: objem,
účel, příjem žádostí od–do, dotační tituly s příjemcem, rozpětím podpory
a spoluúčastí, dokumenty ke stažení.

Portál je Next.js; obsah se nevykresluje v HTML, ale přijde jako datový proud
React Server Components, když se o stránku požádá s hlavičkou `RSC: 1`. To je
týž požadavek, který posílá prohlížeč při přechodu mezi stránkami; nic se
neobchází. Strom komponent se tu převede na řádky „štítek: hodnota“.

Objev programů: stránky „Dotační programy dle právní formy žadatele“
(`/web/legalForms/<id>`) a „Dotační oblasti“ (`/web/categories/<název>`)
odkazují na `/web/programDetail/<id>`.

Výstup (tvar jako gacr/npzp → build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}

Spuštění z kořene repa: python scripts/jmk_edotace.py --out data/jmk_edotace_documents.jsonl
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from urllib.parse import quote, unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

B = "https://e-dotace.jmk.cz/web"
HOST = "e-dotace.jmk.cz"
UA = "Mozilla/5.0 (compatible; regrantio; +https://grantio.cz)"


def fetch_rsc(path, retries=3):
    req = urllib.request.Request(B + path, headers={"User-Agent": UA, "RSC": "1"})
    last = None
    for attempt in range(retries):
        try:
            with http_util.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch selhal: {path} ({last})")


def rows_of(payload):
    """Řádky proudu RSC `klíč:JSON` → slovník klíč → hodnota (jen platný JSON)."""
    out = {}
    for ln in payload.split("\n"):
        m = re.match(r"^([0-9a-z]+):(.*)$", ln)
        if not m:
            continue
        try:
            out[m.group(1)] = json.loads(m.group(2))
        except ValueError:
            pass
    return out


def text_of(rows):
    """Strom komponent → řádky textu a odkazy v pořadí na stránce.

    Mobilní kopie tabulky (`md:hidden`) se přeskočí, jinak by každý údaj byl
    dvakrát. Odkazy na jiné řádky proudu (`$L…`) se rozbalí.
    """
    lines, cur, links, seen = [], [], [], set()

    def flush():
        t = re.sub(r"\s+:", ":", " ".join(cur)).strip()
        if t:
            lines.append(t)
        cur.clear()

    def walk(n):
        if isinstance(n, str):
            if n.startswith("$L") or n.startswith("$@"):
                k = n[2:]
                if k in rows and k not in seen:
                    seen.add(k)
                    walk(rows[k])
                return
            if n.strip() and not n.startswith("$"):
                cur.append(n.strip())
            return
        if isinstance(n, list):
            if len(n) == 4 and n[0] == "$" and isinstance(n[3], dict):
                p, tag = n[3], n[1]
                cl = p.get("className") or ""
                if re.search(r"(^|\s)md:hidden", cl):
                    return
                block = "main-table-row" in cl or tag in ("h1", "h2", "h3", "p", "li")
                if block:
                    flush()
                href = p.get("href")
                if tag == "a" and href and "/api/attachment/" in href:
                    links.append(href)
                walk(p.get("children"))
                if block:
                    flush()
            else:
                for x in n:
                    walk(x)

    # Obsah stránky je v řádku, který nese nadpis sekce; ostatní jsou kostra.
    for k, v in rows.items():
        if '"section-title"' in json.dumps(v, ensure_ascii=False)[:4000]:
            seen.add(k)
            walk(v)
            break
    flush()
    return lines, links


def discover():
    ids = {}
    legal = fetch_rsc("/legalForms")
    for lf in sorted(set(re.findall(r"legalForms/(\d+)", legal))):
        for pid in re.findall(r"programDetail/(\d+)", fetch_rsc(f"/legalForms/{lf}")):
            ids.setdefault(pid, "legalForms")
        time.sleep(0.2)
    cats = fetch_rsc("/categories")
    for c in sorted(set(re.findall(r"categories/([^\"/?]+)", cats))):
        if c.endswith(".js"):
            continue
        for pid in re.findall(r"programDetail/(\d+)", fetch_rsc("/categories/" + quote(unquote(c)))):
            ids.setdefault(pid, "categories")
        time.sleep(0.2)
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/jmk_edotace_documents.jsonl")
    args = ap.parse_args()
    recs = []
    for pid in discover():
        lines, links = text_of(rows_of(fetch_rsc(f"/programDetail/{pid}")))
        if not lines:
            print(f"  · program {pid}: detail portál zatím nezveřejnil (404) → příště", flush=True)
            continue
        title, body = lines[0], "\n".join(lines)
        atts, seen = [], set()
        for href in links:
            u = "https://" + HOST + href if href.startswith("/") else href
            if u in seen:
                continue
            seen.add(u)
            m = re.search(r"[?&]name=([^&]+)", u)
            atts.append({"url": u, "label": unquote(m.group(1)) if m else u.rsplit("/", 1)[-1]})
        recs.append({"url": f"{B}/programDetail/{pid}", "host": HOST, "title": title, "body_text": body,
                     "attachments": atts, "n_attachments": len(atts)})
        time.sleep(0.2)
    if not recs:
        print("✖ JMK e‑dotace: žádný program (změna portálu?)", file=sys.stderr)
        sys.exit(1)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  att={r['n_attachments']:2} body={len(r['body_text']):5} :: {r['title'][:70]}", flush=True)
    print(f"JMK_EDOTACE_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
