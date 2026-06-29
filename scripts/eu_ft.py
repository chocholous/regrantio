#!/usr/bin/env python3
"""EU Funding & Tenders Portal (ec.europa.eu) — vrstva 1: centrálně řízené programy EU (Brusel).

Horizon Europe, Erasmus+, Creative Europe, Digital Europe, CEF, LIFE, CERV, Single Market (COSME),
EU4Health… = P6, pro CZ žadatele (univerzity, firmy, NNO, města, umělci) klíčové. Strukturovaný
SEDIA search-api (objeven Playwrightem `scripts/lewis_discover` stylem → HTTP replay BEZ Apify).
Bere JEN OTEVŘENÉ výzvy (status 31094502) → 0 unknown. Programme + oblast z prefixu identifieru
(HORIZON-/ERASMUS-/CREA-/DIGITAL-/CEF-/LIFE-/CERV-/SMP-…). amount=null (rozpočet je v topic detailu/
pracovním programu — NEHALUCINUJEME). EuropeAid (externí akce, prog 111111) se vynechá (ne CZ granty).

Výstup (tvar pro build_extract_input --source-type harvest):
  {url, host, title, body_text, identifier, programme, oblast[], open_from, deadline, type}

Spuštění z kořene repa: python3 scripts/eu_ft.py --out data/eu_ft_documents.jsonl
"""
import argparse, json, os, re, sys, uuid, io, time, urllib.request
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import http_util

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

API = "https://api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA&text=***&pageSize={n}&pageNumber={p}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
# query přesně jako F&T SPA (každá část = file part s Content-Type application/json)
QUERY = {"bool": {"must": [{"terms": {"type": ["1", "2", "8"]}},
                           {"terms": {"status": ["31094502"]}},
                           {"terms": {"language": ["en"]}}]}}
DISPLAY = ["type", "identifier", "reference", "callccm2Id", "title", "status", "caName",
           "projectAcronym", "startDate", "deadlineDate", "deadlineModel", "frameworkProgramme", "typesOfAction"]

# prefix identifieru → (program, oblast[])
PROG = [
    (r"^HORIZON|^ERC-|^MSCA", "Horizon Europe", ["věda a výzkum", "inovace"]),
    (r"^ERASMUS", "Erasmus+", ["vzdělávání", "mládež", "sport"]),
    (r"^CREA", "Kreativní Evropa", ["kultura", "audiovize"]),
    (r"^DIGITAL", "Digital Europe", ["digitalizace", "technologie"]),
    (r"^CEF", "Nástroj pro propojení Evropy (CEF)", ["doprava", "energetika", "digitalizace"]),
    (r"^LIFE", "LIFE", ["životní prostředí", "klima"]),
    (r"^CERV", "Občané, rovnost, práva a hodnoty (CERV)", ["občanská společnost", "lidská práva"]),
    (r"^SMP|^COSME", "Program pro jednotný trh", ["podnikání", "konkurenceschopnost"]),
    (r"^EU4H|^EU4HEALTH", "EU4Health", ["zdraví"]),
    (r"^JUST", "Justice", ["spravedlnost"]),
    (r"^AMIF|^BMVI|^ISF", "Vnitřní věci / migrace", ["migrace", "bezpečnost"]),
    (r"^IMCAP|^AGRI", "Zemědělství (CAP)", ["zemědělství"]),
    (r"^EMFAF", "Námořnictví a rybolov (EMFAF)", ["rybolov"]),
    (r"^EDF|^EUDEF", "Evropský obranný fond (EDF)", ["obrana"]),
    (r"^RFCS", "Výzkumný fond pro uhlí a ocel", ["věda a výzkum"]),
    (r"^PERICLES|^CIDP|^SOCPL|^SMCS", "Program pro jednotný trh", ["podnikání"]),
]


def programme_of(ident):
    for pat, name, obl in PROG:
        if re.search(pat, ident or "", re.I):
            return name, obl
    return None, []


def multipart_body():
    parts = {"sort": json.dumps({"order": "DESC", "field": "startDate"}),
             "query": json.dumps(QUERY), "languages": json.dumps(["en"]),
             "displayFields": json.dumps(DISPLAY)}
    boundary = "----wb" + uuid.uuid4().hex
    buf = io.BytesIO()
    for name, val in parts.items():
        buf.write(("--" + boundary + "\r\n").encode())
        buf.write(('Content-Disposition: form-data; name="%s"; filename="blob"\r\n' % name).encode())
        buf.write(b"Content-Type: application/json\r\n\r\n")
        buf.write(val.encode() + b"\r\n")
    buf.write(("--" + boundary + "--\r\n").encode())
    return boundary, buf.getvalue()


def fetch_page(p, n=100, retries=3):
    boundary, body = multipart_body()
    req = urllib.request.Request(API.format(n=n, p=p), data=body, headers={
        "User-Agent": UA, "Content-Type": "multipart/form-data; boundary=" + boundary})
    last = None
    for a in range(retries):
        try:
            with http_util.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:
            last = e
            time.sleep(1.5 * (a + 1))
    raise RuntimeError(f"page {p} selhala: {last}")


def g(m, k):
    v = m.get(k)
    return v[0] if isinstance(v, list) and v else v


def iso(dt):
    if not dt:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(dt))
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def main():
    from datetime import date
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/eu_ft_documents.jsonl")
    ap.add_argument("--min-deadline", default=date.today().isoformat(),
                    help="ber jen výzvy s deadline >= (default dnešek) — EC status 'open' nese i staré "
                         "prošlé cutoffy multi-stage výzev; ty nejsou aktuální příležitost")
    args = ap.parse_args()
    first = fetch_page(1, 100)
    total = first.get("totalResults", 0)
    pages = (total + 99) // 100
    print(f"  discovery: {total} otevřených výzev → {pages} stran", flush=True)
    results = list(first.get("results", []))
    for p in range(2, pages + 1):
        results += fetch_page(p, 100).get("results", [])
        time.sleep(0.2)
    recs, skip = [], 0
    seen = set()
    for r in results:
        m = r.get("metadata", {})
        ident = g(m, "identifier") or ""
        if ident in seen:
            continue
        seen.add(ident)
        prog, obl = programme_of(ident)
        if prog is None or ident.startswith("EuropeAid"):   # externí akce / netříděné → ne CZ grant
            skip += 1
            continue
        dl = iso(g(m, "deadlineDate"))
        if not dl or dl < args.min_deadline:   # prošlý cutoff (i když EC říká „open") = ne aktuální
            skip += 1
            continue
        title = re.sub(r"\s+", " ", str(g(m, "title") or "")).strip()
        toa = g(m, "typesOfAction")
        body = (f"{prog} – {ident}\n{title}\n\nTyp akce: {toa or '-'}\n"
                f"Zahájení: {iso(g(m, 'startDate')) or '-'} · Uzávěrka: {iso(g(m, 'deadlineDate')) or '-'}\n"
                f"Centrálně řízený program EU (Evropská komise), otevřený pro žadatele z ČR.")
        recs.append({"url": r.get("url") or f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{ident}",
                     "host": "ec.europa.eu", "title": f"{title} ({ident})" if title else ident,
                     "body_text": body, "identifier": ident, "programme": prog, "oblast": obl,
                     "open_from": iso(g(m, "startDate")), "deadline": iso(g(m, "deadlineDate")),
                     "type": g(m, "type"), "typesOfAction": toa,
                     "attachments": [], "n_attachments": 0})
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as o:
        for r in recs:
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    print(f"EU_FT_DONE {len(recs)} (skip {skip}) -> {args.out}", flush=True)
    print("  programy:", dict(Counter(r["programme"] for r in recs).most_common()), flush=True)


if __name__ == "__main__":
    main()
