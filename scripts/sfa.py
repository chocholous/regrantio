#!/usr/bin/env python3
"""Státní fond audiovize (sfa.gov.cz, dříve Státní fond kinematografie / fondkinematografie.cz) — vrstva 1.

Specifika vynucující vlastní parser:
  • Výzvy NEJSOU samostatné detail-stránky — VŠECHNY (otevřené i uzavřené) leží inline na
    stránce okruhu `/vyzvy/{1..4}` (1=A Kinematografie, 2=B Televizní díla, 3=C Animace &
    Videohry, 4=D Infrastruktura). Univerzální BFS/harvest by je neuměl rozdělit ani odlišit
    otevřené od uzavřených.
  • Sekce jsou oddělené textovými markery: „otevřené výzvy:" → „Čekáme na rozhodnutí" /
    „uzavřené výzvy:". Tady harvestujeme JEN otevřené (aktuálně žádatelné).
  • Každá výzva = blok začínající kódem `2026-B-2-3-39` + název, „Lhůta pro podání žádostí:
    od D do D", a sada dokumentů; klíčový je první „Vyzva-*.pdf" (/data/invitation/…) s alokací
    a oprávněnými žadateli → příloha pro vrstvu 2.

Výstup (shodný tvar jako marwel/eagri → konzumuje build_extract_input --source-type harvest):
  {url, host, title, body_text, attachments:[{url,label}], n_attachments}
  — 1 záznam „fond" (mission, /podpora-audiovize) + 1 záznam per OTEVŘENÁ výzva.

Spuštění: python3 scripts/sfa.py --out data/sfa_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
from urllib.parse import urljoin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util   # jednotná TLS politika (audit #7/#32)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
BASE = "https://sfa.gov.cz"
AREA = {1: "A Kinematografie", 2: "B Televizní díla", 3: "C Animace & Videohry", 4: "D Infrastruktura"}
CODE_RE = re.compile(r"(20\d\d-[A-D]-[\d-]+\d)\s+([^<\n]{4,160}?)\s*<", re.S)


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with http_util.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def to_text(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</tr>|</h[1-6]>|</div>|</td>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h)).replace("\xa0", " ")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", t)).strip()


def open_section(h):
    """Vrať HTML výseč jen s OTEVŘENÝMI výzvami (otevřené výzvy: → Čekáme/uzavřené)."""
    i = h.find("otevřené výzvy:")
    if i < 0:
        return ""
    ends = [x for x in (h.find("Čekáme na rozhodnutí", i + 10), h.find("uzavřené výzvy:", i + 10)) if x > 0]
    return h[i:min(ends)] if ends else h[i:]


def vyzvy_of_area(n):
    h = fetch(f"{BASE}/vyzvy/{n}")
    seg = open_section(h)
    if not seg:
        return []
    out, seen = [], set()
    marks = list(CODE_RE.finditer(seg))
    for k, m in enumerate(marks):
        code, name = m.group(1), html.unescape(m.group(2)).strip()
        if code in seen:                 # kód se v bloku opakuje (nadpis + detail) → ber 1×
            continue
        seen.add(code)
        block = seg[m.start():(marks[k + 1].start() if k + 1 < len(marks) else len(seg))]
        dl = re.search(r"od\s+([\d.\s]+?)\s+do\s+([\d.]+\s*\d{4})", block)
        pdf = re.search(r'href="(/data/[^"]*[Vv]yzva[^"]*\.pdf)"', block) or re.search(r'href="(/data/[^"]+\.pdf)"', block)
        atts = [{"url": urljoin(BASE, html.unescape(pdf.group(1))), "label": "Výzva"}] if pdf else []
        out.append({"url": f"{BASE}/vyzvy/{n}#{code}", "host": "sfa.gov.cz",
                    "title": f"{code} {name}",
                    "body_text": f"Okruh {AREA[n]}.\nVýzva {code} – {name}.\n"
                                 + (f"Lhůta pro podání žádostí: od {dl.group(1).strip()} do {dl.group(2).strip()}.\n" if dl else "")
                                 + to_text(block)[:1500],
                    "attachments": atts, "n_attachments": len(atts)})
    return out


def foundation_rec():
    txt = to_text(fetch(f"{BASE}/podpora-audiovize"))
    return {"url": f"{BASE}/podpora-audiovize", "host": "sfa.gov.cz",
            "title": "Státní fond audiovize", "body_text": txt, "attachments": [], "n_attachments": 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sfa_documents.jsonl")
    args = ap.parse_args()
    recs = [foundation_rec()]
    for n in AREA:
        recs += vyzvy_of_area(n)
        time.sleep(0.3)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  att={r['n_attachments']} body={len(r['body_text'])} :: {r['title'][:62]}", flush=True)
    print(f"SFA_DONE {len(recs)} -> {args.out}")


if __name__ == "__main__":
    main()
