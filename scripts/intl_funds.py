#!/usr/bin/env python3
"""Mezinárodní fondy/nadace podporující ČR — layer-1 harvest (Visegrad Fund, ERSTE Foundation).

PROČ SPOLEČNÝ HARVESTER: oba weby jsou malé, server-rendered a mají PÁR programů (ne katalog
stovek výzev), takže vlastní parser per web by byl neúměrný. Sdílejí i stejnou překážku —
oba vracejí **HTTP 403 na default urllib User-Agent**; stačí realistické prohlížečové hlavičky
(ověřeno 2026-07-31: bez nich 403, s nimi 200).

Zdroje a jejich programy (seed URL, protože ani jeden nemá strojově čitelný katalog):
  visegradfund.org — Visegrad Grants / Scholarships / Residencies / Strategic Grants / V4 Gen
  erstestiftung.org — otevřené výzvy a programy nadace ERSTE (CEE region včetně ČR)

Termíny: Visegrad má PEVNÉ uzávěrky (1. 2. / 1. 6. / 1. 10.) uváděné textem „Opens Oct 1, 2026"
nebo „Deadline …" → parsují se anglické formáty. Když datum není, deadline zůstává None
(status unknown) — NEfabrikuje se.

Výstup (kontrakt jako ostatní *_documents.jsonl):
  data/intl_funds_documents.jsonl  {host, web, fond, title, url, kind, body_text,
                                    deadline_raw, attachments[], n_attachments}

Spuštění: python scripts/intl_funds.py [--fond visegrad|erste]
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):  # Windows cp1250 konzole neuveze non-ASCII diagnostiku
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse
import html as H
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util  # noqa: E402  (jednotná TLS politika)

# Bez realistických hlaviček oba weby vracejí 403 (ověřeno) — proto NE default urllib UA.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HDR = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
       "Accept-Language": "en,cs;q=0.9", "Accept-Encoding": "identity"}

FONDY = {
    "visegrad": {
        "name": "International Visegrad Fund",
        "host": "visegradfund.org",
        "seeds": [
            ("https://www.visegradfund.org/grants", "Visegrad Grants"),
            ("https://www.visegradfund.org/scholarships", "Visegrad Scholarships"),
            ("https://www.visegradfund.org/residencies", "Visegrad Residencies"),
            ("https://www.visegradfund.org/strategic-grants-apply", "Visegrad Strategic Grants"),
            ("https://www.visegradfund.org/v4-gen-apply", "V4 Generation"),
        ],
    },
    "erste": {
        "name": "ERSTE Foundation",
        "host": "erstestiftung.org",
        "seeds": [
            ("https://www.erstestiftung.org/en/calls/", "ERSTE Foundation – open calls"),
            ("https://www.erstestiftung.org/en/programs/", "ERSTE Foundation – programs"),
        ],
    },
}

DOC_RE = re.compile(r"\.(pdf|docx?|xlsx?)(\?|$)", re.I)
# anglické datumové formáty: "Deadline: 1 February 2027", "Opens Oct 1, 2026", "by 15 March 2027"
DATE_RE = re.compile(
    r"(?:deadline|opens?|closes?|by|until)\D{0,20}"
    r"(?:(\d{1,2})\s+([A-Z][a-z]+)\s+(20\d\d)|([A-Z][a-z]{2,})\s+(\d{1,2}),?\s+(20\d\d))", re.I)


def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers=HDR)
    with http_util.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace"), r.url


def strip_tags(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</h\d>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[ \t]+", " ", H.unescape(s)).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fond", choices=sorted(FONDY), help="jen jeden fond")
    ap.add_argument("--out", default="data/intl_funds_documents.jsonl")
    ap.add_argument("--timeout", type=int, default=40)
    a = ap.parse_args()

    recs = []
    for key, cfg in FONDY.items():
        if a.fond and key != a.fond:
            continue
        for url, label in cfg["seeds"]:
            try:
                page, final = fetch(url, a.timeout)
            except Exception as e:  # noqa: BLE001
                print(f"  [err] {label}: {type(e).__name__}", file=sys.stderr)
                continue
            body = strip_tags(page)
            if len(body) < 300:                      # prázdná/redirect stránka
                print(f"  [skip] {label}: jen {len(body)} znaků", file=sys.stderr)
                continue
            m = DATE_RE.search(body)
            atts, seen = [], set()
            for mm in re.finditer(r'href="([^"]+)"', page):
                u = H.unescape(mm.group(1))
                if DOC_RE.search(u) and u not in seen:
                    seen.add(u)
                    atts.append({"url": u if u.startswith("http") else final.rstrip("/") + "/" + u.lstrip("/"),
                                 "label": u.rsplit("/", 1)[-1][:120]})
            recs.append({
                "host": cfg["host"], "web": cfg["host"], "fond": cfg["name"],
                "kind": "vyzva", "title": label, "url": final, "date": None,
                "body_text": body, "deadline_raw": (m.group(0)[:80] if m else None),
                "attachments": atts, "n_attachments": len(atts),
            })
            print(f"  [{key}] {label}: {len(body)} znaků, deadline_raw={bool(m)}", file=sys.stderr)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(json.dumps({"MARKER": "INTL_FUNDS_HARVEST", "programy": len(recs),
                      "by_fond": dict(Counter(r["fond"] for r in recs)),
                      "out": a.out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
