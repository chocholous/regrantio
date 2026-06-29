#!/usr/bin/env python3
"""Úřad vlády ČR — dotační programy pro NNO (vlada.gov.cz) — vrstva 1.

Ústřední orgán; rady/zmocněnci vlády rozdělují národní dotace NNO v oblastech lidských práv, rovnosti
žen a mužů, romské integrace, národnostních menšin, zdravotně postižených a protidrogové politiky.
Programy jsou ROZTŘÍŠTĚNÉ po radách (custom PHP CMS, bez centrálního listingu) → seed-driven (jako mpo/
eagri). Detail = próza; deadline ČESKÁ jména měsíců „do DD. měsíce RRRR"; alokace bývá jen ve výzvě/PDF
(amount=null — nehalucinujeme). typ_poskytovatele=ministerstvo (Úřad vlády = ústřední správní úřad),
zdroj=narodni_rozpocet. Status NEpočítá (kód z deadline).

Spuštění z kořene repa: python3 scripts/vlada.py --out data/vlada_documents.jsonl
"""
import argparse, json, os, re, sys, time, html, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
HOST = "vlada.gov.cz"
B = "https://vlada.gov.cz"
MONTH = (r"(?:ledna|února|unora|března|brezna|dubna|května|kvetna|června|cervna|července|cervence|"
         r"srpna|září|zari|října|rijna|listopadu|prosince)")
MONTHS = {"ledna": 1, "února": 2, "unora": 2, "března": 3, "brezna": 3, "dubna": 4, "května": 5,
          "kvetna": 5, "června": 6, "cervna": 6, "července": 7, "cervence": 7, "srpna": 8,
          "září": 9, "zari": 9, "října": 10, "rijna": 10, "listopadu": 11, "prosince": 12}

# (cesta, program (čistý titul), oblast[]) — 2026 dotační řízení napříč radami/zmocněnci vlády
SEEDS = [
    ("/cz/ppov/rvppa/dotace/vyhlaseni-dotacniho-rizeni-na-rok-2026-v-ramci-dotacniho-programu-podpora-pametovych-agend-221505/",
     "Podpora paměťových agend", ["lidská práva", "paměť národa"]),
    ("/ppov/rovne-prilezitosti-zen-a-muzu/dotace/vyhlaseni-dotacniho-rizeni-na-rok-2026-program-podpora-verejne-prospesnych-aktivit-v-oblasti-rovnosti-zen-a-muzu-a-prevence-nasili-221851/",
     "Podpora veřejně prospěšných aktivit v oblasti rovnosti žen a mužů a prevence násilí", ["rovnost žen a mužů", "prevence násilí"]),
    ("/cz/ppov/rnm/dotace/vyhlaseni-dotacniho-rizeni-na-rok-2026-v-ramci-programu-podpora-implementace-evropske-charty-regionalnich-ci-mensinovych-jazyku-221587/",
     "Podpora implementace Evropské charty regionálních či menšinových jazyků", ["národnostní menšiny"]),
    ("/cz/ppov/zalezitosti-romske-komunity/dotace/prevence/vyhlaseni-dotacniho-rizeni-na-rok-2026-v-ramci-programu-prevence-socialniho-vylouceni-a-komunitni-prace-221595/",
     "Prevence sociálního vyloučení a komunitní práce", ["romská integrace", "sociální začleňování"]),
    ("/cz/ppov/zalezitosti-romske-komunity/dotace/podpora-terenni-prace/vyhlaseni-dotacniho-rizeni-na-rok-2026-v-ramci-dotacniho-programu-podpora-terenni-prace-221627/",
     "Podpora terénní práce", ["romská integrace", "sociální práce"]),
    ("/cz/ppov/vvozp/aktuality/vyhlaseni-dotacniho-rizeni-na-rok-2026-v-ramci-programu-podpora-verejne-prospesnych-aktivit-spolku-osob-se-zdravotnim-postizenim--221580/",
     "Podpora veřejně prospěšných aktivit spolků osob se zdravotním postižením", ["zdravotně postižení"]),
    ("/cz/ppov/zavislosti/dotace/2026/vyzva-k-podani-zadosti-o-poskytnuti-neinvesticni-dotace-v-ramci-programu-_protidrogova-politika_-z-rozpoctove-kapitoly-uradu-vlady-cr-na-rok-2026-221794",
     "Protidrogová politika", ["protidrogová politika", "závislosti"]),
]


def fetch(url, timeout=25, retries=3):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for a in range(retries):
        try:
            with http_util.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(1.2 * (a + 1))
    raise RuntimeError(f"fetch selhal: {url} ({last})")


def clean(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h or "")
    h = re.sub(r"(?i)</p>|<br\s*/?>|</li>|</h[1-6]>|</div>|</td>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    t = re.sub(r"[ \t ]+", " ", t)
    return "\n".join(ln.strip() for ln in t.split("\n") if ln.strip())


def deadline_of(text):
    """Termín pro podání žádostí: 'do DD. měsíce RRRR' / 'nejpozději do DD. M. RRRR'."""
    pats = [r"(?:termín[^.\n]{0,40}?|nejpozději\s+|žádost[^.\n]{0,40}?)do\s+(\d{1,2})\.\s*(" + MONTH + r")\s*(20\d\d)",
            r"(?:do|nejpozději do)\s+(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)"]
    best = None
    for pat in pats:
        for m in re.finditer(pat, text, re.I):
            g = m.groups()
            mon = MONTHS.get(g[1].lower()) if not g[1].isdigit() else int(g[1])
            if not mon:
                continue
            iso = f"{g[2]}-{mon:02d}-{int(g[0]):02d}"
            cue = re.sub(r"\s+", " ", m.group(0)).strip()
            if best is None or iso > best[0]:
                best = (iso, cue)
    return best or (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/vlada_documents.jsonl")
    args = ap.parse_args()
    recs = []
    for path, prog, oblast in SEEDS:
        url = B + path
        try:
            t = clean(fetch(url))
        except Exception as e:
            print(f"  ⚠ {prog[:35]}: fetch selhal ({str(e)[:40]})", flush=True)
            continue
        dl, cue = deadline_of(t)
        # perex = první věcný odstavec po nadpisu (pro grounding/popis)
        perex = ""
        m = re.search(r"(Úřad vlády[^\n]{40,400}|Cílem [^\n]{40,400}|Program[^\n]{40,400})", t)
        if m:
            perex = re.sub(r"\s+", " ", m.group(1)).strip()
        body = (f"Úřad vlády ČR – dotační program {prog} na rok 2026.\n"
                f"{perex}\n" + (f"Termín pro podání žádostí: {cue}\n" if cue else ""))
        recs.append({"url": url, "host": HOST, "title": f"{prog} – dotace Úřadu vlády ČR na rok 2026",
                     "body_text": body, "programme": prog, "oblast": oblast,
                     "deadline": dl, "deadline_cue": cue,
                     "attachments": [], "n_attachments": 0})
        print(f"  dl={dl or '-':12} :: {prog[:55]}", flush=True)
        time.sleep(0.3)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"VLADA_DONE {len(recs)}/{len(SEEDS)} -> {args.out}")


if __name__ == "__main__":
    main()
