#!/usr/bin/env python3
"""vismo_refresh.py — obnova klasických obecních webů Vismo BEZ MODELU.

⚠ DO 2026‑10‑09 SE TYHLE WEBY OBNOVIT NEDALY (`docs/REFRESH.md` §6). Výpis
úřední desky sbírá `vismo.py`, ale krok, který z výpisu vybral výzvy, byl
jednorázový a lhůty pak četl model z příloh. Data byla z 30. 5.

Lhůta se tu čte PRAVIDLEM, ne odhadem: obecní dotační program ze zákona
(§ 10c zák. 250/2000 Sb.) uvádí „lhůtu pro podání žádosti“. Vezme se text od
té hlavičky po další článek (nebo „lhůtu pro rozhodnutí“) a z něj data
S ROKEM: lhůta = nejpozdější, začátek příjmu = nejdřívější. Datum bez roku
(„od 02.12. aktuálního roku“) se nedoplňuje. Čte se tělo stránky a PDF
přílohy, doslovná věta jde do `citations` jako doklad.

    python scripts/vismo_refresh.py harvest   # výpis 10 webů → data/vismo_listing.jsonl
    python scripts/vismo_refresh.py ingest    # detail + přílohy → upsert do katalogu

Co se zapíše:
  • záznam, který v katalogu JE (shodné `d-NNN`): lhůta a stav, když je program
    uvádí; obohacení z vrstvy 2 zůstává (`upsert.merge`);
  • NOVÝ dokument jen tehdy, když název zní jako program nebo výzva, není to
    seznam podpořených, pravidla ani výsledky, A přílohy nesou lhůtu s rokem,
    která neskončila dřív než před 90 dny. Bez lhůty se nic nového nepřidá:
    radši chybějící výzva než výpis úřední desky v katalogu.
"""
import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")
    if _sys.stderr:
        _sys.stderr.reconfigure(encoding="utf-8")
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opportunities import canon_key, compute_status  # noqa: E402
from upsert import upsert  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LISTING = os.path.join("data", "vismo_listing.jsonl")
CATALOG = os.path.join("data", "opportunities.jsonl")
FILES = os.path.join("data", "vismo_files")

LHUTA_HEAD = re.compile(
    r"lhůt\w*\s+(?:pro|k)\s+podání\s+žádost\w*"
    r"|termín\w*\s+(?:pro\s+)?podání\s+žádost\w*"
    r"|žádost\w*\s+(?:lze|je\s+možné|je\s+možno)\s+(?:podávat|podat|odevzdávat|předkládat)",
    re.I)
# Konec oddílu: další článek, jiná fáze (rozhodnutí, realizace, vyúčtování) nebo
# výpis příloh na stránce Visma („Odkazy“). Bez toho bral harmonogram v tabulce
# (Most) jako lhůtu podání nejpozdější datum, tedy vyúčtování.
STOP = re.compile(r"Čl\.\s*\d|článek\s+\d|rozhodnutí|realizac|vyúčtován|závěrečn|kritéri\w*\s+pro\s+hodnocení|\bOdkazy\b", re.I)
MONTHS = {"ledna": 1, "února": 2, "března": 3, "dubna": 4, "května": 5, "června": 6,
          "července": 7, "srpna": 8, "září": 9, "října": 10, "listopadu": 11, "prosince": 12}
NUM_DATE = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")
WORD_DATE = re.compile(r"(\d{1,2})\.\s*(" + "|".join(MONTHS) + r")\s+(20\d\d)", re.I)

# Název, který zní jako program nebo výzva …
CALL_TITLE = re.compile(r"program|výzv|vyzv|dotac|grant|fond|příspěv", re.I)
# … a není seznam podpořených, pravidla, výsledky ani úřední agenda.
NOT_A_CALL = re.compile(
    r"poskytnut|přidělen|podpořen|schválen|výsled|vyhodnoc|zásad|pravidl|logo|evidence|informace"
    r"|popis činnosti|smlouv|volby|seznam|vyúčtován|formulář|tiskopis|oznámení o|usnesení|rozpočt",
    re.I)


def _date(d, m, y):
    try:
        return datetime.date(int(y), int(m), int(d))
    except ValueError:
        return None


def _dates(text):
    """[(datum, je to konec „do …“, je to začátek „od …“)] v pořadí výskytu."""
    out = []
    for m in list(NUM_DATE.finditer(text)) + list(WORD_DATE.finditer(text)):
        g = m.groups()
        d = _date(g[0], MONTHS[g[1].lower()], g[2]) if m.re is WORD_DATE else _date(*g)
        if d:
            # Rozhoduje slovo NEJBLÍŽ před datem („od 19.10. do 02.11.2026“: konec, ne začátek).
            near = re.findall(r"\b(od|do)\b", text[max(0, m.start() - 14): m.start()].lower())
            last = near[-1] if near else None
            out.append((m.start(), d, last == "do", last == "od"))
    return [(d, end, start) for _, d, end, start in sorted(out)]


def submission_window(text, today=None):
    """→ (open_from, deadline, doslovná věta) z oddílu „lhůta pro podání žádosti“, nebo (None, None, None).

    Lhůta je NEJBLIŽŠÍ konec („do …“), který ještě neminul; když minuly všechny,
    poslední z nich (Hradec Králové: dvě kola, 1. 11. 2026 a 1. 4. 2027). Text
    v závorce se nepočítá („akce konané od … do …“ není lhůta podání).
    """
    today = today or datetime.date.today()
    found = []
    for h in LHUTA_HEAD.finditer(text or ""):
        tail = text[h.start(): h.start() + 700]
        stop = STOP.search(tail, h.end() - h.start())
        win = tail[: stop.start()] if stop else tail
        flat = re.sub(r"\([^()]*\)", " ", win)
        dates = _dates(flat)
        if not dates:
            continue
        ends = [d for d, end, _ in dates if end] or [d for d, _, _ in dates]
        upcoming = [d for d in ends if d >= today]
        dl = min(upcoming) if upcoming else max(ends)
        starts = [d for d, _, start in dates if start and d <= dl]
        of = max(starts) if starts else None
        found.append((of, dl, re.sub(r"\s+", " ", win).strip()[:300]))
    if not found:
        return None, None, None
    # Víc oddílů (program a jeho příloha): přednost má ten s nejbližší nadcházející lhůtou.
    up = [f for f in found if f[1] >= today]
    of, dl, q = min(up, key=lambda f: f[1]) if up else max(found, key=lambda f: f[1])
    return (of.isoformat() if of else None), dl.isoformat(), q


def closer(d, best, today):
    """Je lhůta `d` lepší než `best`? Nadcházející před minulou; z nadcházejících
    nejbližší, z minulých nejpozdější. (Tělo stránky a přílohy, ISO řetězce.)"""
    if best is None:
        return True
    if (d >= today) != (best >= today):
        return d >= today
    return d < best if d >= today else d > best


def catalog_vismo():
    """id → záznam pro klasické Vismo v katalogu (platforma `vismo`)."""
    out = {}
    for line in open(CATALOG, encoding="utf-8").read().split("\n"):
        if not line.strip():
            continue
        r = json.loads(line)
        if (r.get("provenance") or {}).get("platform") == "vismo":
            out[r["id"]] = r
    return out


def harvest(args):
    hosts = sorted({r["source"] for r in catalog_vismo().values()})
    if os.path.exists(LISTING):
        os.remove(LISTING)
    for h in hosts:
        cmd = [sys.executable, os.path.join("scripts", "vismo.py"), "--base", f"https://{h}", "--out", LISTING]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=args.timeout)
        line = next((ln for ln in r.stdout.splitlines() if "MARKER" in ln), r.stderr.strip()[-200:])
        print(line, flush=True)
    n = sum(1 for _ in open(LISTING, encoding="utf-8")) if os.path.exists(LISTING) else 0
    print(json.dumps({"MARKER": "VISMO_REFRESH_HARVEST", "hosts": len(hosts), "docs": n, "out": LISTING}, ensure_ascii=False))
    return 0 if n else 1


def texts_of(detail, max_pdf):
    """Tělo stránky + text PDF příloh (nejvýš `max_pdf`)."""
    out = [detail.get("body_text") or ""]
    pdfs = 0
    for a in detail.get("attachments") or []:
        if a.get("ext") == "pdf" and a.get("txt_path") and pdfs < max_pdf:
            pdfs += 1
            out.append(open(a["txt_path"], encoding="utf-8", errors="replace").read())
    return out


def ingest(args):
    import vismo_detail as vd   # stahuje a převádí přílohy (dsw2_fetch)
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    vd.TODAY = today
    known = catalog_vismo()
    region_of = {}
    for r in known.values():
        region_of.setdefault(r["source"], (r.get("facets") or {}))
    listing = [json.loads(ln) for ln in open(LISTING, encoding="utf-8") if ln.strip()]
    recs, stats = [], {"known": 0, "known_dated": 0, "candidates": 0, "new": 0, "fetch_fail": 0}
    for doc in listing:
        host = doc["foundation_id"]
        gid = canon_key("grant", doc["title"], doc["url"])
        old = known.get(gid)
        if not old:
            if not CALL_TITLE.search(doc["title"]) or NOT_A_CALL.search(doc["title"]):
                continue
            stats["candidates"] += 1
        else:
            stats["known"] += 1
        call = dict(doc, web=host)
        detail = vd.process(call, FILES, True, args.fetch_timeout, args.max_mb * 1024 * 1024)
        if detail.get("error"):
            stats["fetch_fail"] += 1
            continue
        of = dl = quote = None
        for t in texts_of(detail, args.max_pdf):
            o, d, q = submission_window(t, today)
            if d and closer(d, dl, today.isoformat()):
                of, dl, quote = o, d, q
        if not old and (not dl or datetime.date.fromisoformat(dl) < today - datetime.timedelta(days=90)):
            continue
        st, conf = compute_status(of, dl, today, title=doc["title"]) if dl else ("unknown", "low")
        docs = [{"url": a.get("url"), "txt_path": a.get("txt_path")} for a in detail.get("attachments") or []]
        rec = {
            "kind": "grant", "source": host, "id": gid,
            # Adresa známého záznamu zůstává: výpis ji kóduje jinak (%2D) a `id` je totéž.
            "source_url": (old or {}).get("source_url") or doc["url"],
            "title": doc["title"], "open_from": of, "deadline": dl,
            "status": st, "status_confidence": conf,
            "provenance": {"layer": 1, "harvester": "vismo_refresh.py", "platform": "vismo",
                           "harvest_file": LISTING, "harvest_url": doc["url"], "documents": docs},
        }
        if dl:
            rec["citations"] = [{"field": "deadline", "value": dl, "quote": quote}]
        if old:
            stats["known_dated"] += bool(dl)
            # Známý záznam: z jeho kopie se mění JEN lhůta a stav, a to jen když je
            # program uvádí. Obohacení (fasety, popis, citace) zůstává celé; u
            # obohaceného záznamu to hlídá i `upsert.merge`.
            rec = dict(old)
            if dl:
                rec.update(open_from=of or old.get("open_from"), deadline=dl, status=st, status_confidence=conf)
        else:
            stats["new"] += 1
            facets = region_of.get(host) or {}
            rec.update({
                "focus_area": None, "amount": None, "eligible_applicants": None,
                "required_attachments": [], "how_to_apply": None, "source_doc": doc["url"],
                "facets": {"oblast": [], "typ_zadatele": [], "sektor_zadatele": [],
                           "typ_poskytovatele": facets.get("typ_poskytovatele"),
                           "forma_podpory": ["dotace"], "zdroj_financovani": facets.get("zdroj_financovani") or [],
                           "region": facets.get("region")},
                "extra": {"section": doc.get("section")} if doc.get("section") else {},
            })
        recs.append(rec)
        print(f"  {'NOVÝ ' if not old else '     '}{host[:16]:16} {st:9} {dl or '—':10}  {doc['title'][:70]}", flush=True)
        if dl and (not old or old.get("deadline") != dl):
            # Každou novou nebo změněnou lhůtu doložit větou: kontroluje se čtením, ne vírou.
            print(f"        {(old or {}).get('deadline') or '—'} → {dl}  «{quote}»", flush=True)
    if not recs:
        print("✖ nic ke zápisu: prázdný výpis nebo všechny detaily selhaly", file=sys.stderr)
        return 1
    res = upsert(args.out, recs)
    print(json.dumps({"MARKER": "VISMO_REFRESH_INGEST", **stats, **{k: res[k] for k in ("new", "updated", "unchanged")}},
                     ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["harvest", "ingest"])
    ap.add_argument("--out", default=CATALOG)
    ap.add_argument("--today")
    ap.add_argument("--timeout", type=int, default=600, help="strop na sběr jednoho webu (s)")
    ap.add_argument("--fetch-timeout", type=int, default=30, help="strop na jeden požadavek (s)")
    ap.add_argument("--max-mb", type=int, default=25)
    ap.add_argument("--max-pdf", type=int, default=3)
    args = ap.parse_args()
    os.chdir(ROOT)
    return harvest(args) if args.step == "harvest" else ingest(args)


if __name__ == "__main__":
    sys.exit(main())
