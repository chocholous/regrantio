#!/usr/bin/env python3
"""dsw2 / Otevřená města extraktor — granty, výzvy, přidělené dotace, číselníky.

Veřejné zdroje dsw2 (vše bez loginu, ověřeno ze zdrojáku CakePHP app):
1) /explore/fonds  — KATALOG: JS proměnné fonds/realms/programs/treeData.
     Hierarchie Fond → Realm(oblast) → Program → ChildProgram (parent_id).
2) /explore/appeals — VÝZVY jako HTML karty .card (name, description, link,
     open_from/open_to, created/modified, seznam souvisejících programů).
3) /opendata        — PŘIDĚLENÉ DOTACE/vyúčtování (entita project): tabulka
     {název, výzva, žadatel+IČO, částka vyúčtovaná, datum}. Plněno jen na části webů.
4) /csu/*.json      — číselníky (countries, legal_forms, municipalities, ...).

POZN. alokace/max výzvy (budget_size/max_request_budget) je v DB, ale veřejná
šablona ji NErenderuje → není zde; bývá v dokumentu odkazovaném z výzvy.

Výstupy (JSONL, 1 entita/řádek) + sběr odkazů ke stažení (dsw2_links.jsonl).
Konfigurace přes CLI; zabudované cesty /explore|/opendata|/csu jsou konvence
platformy Otevřená města (obdoba WP REST cesty), přepsatelné přes CLI.
"""
import argparse
import datetime
import html
import json
import os
import re
import socket
import sys
import urllib.error
import http_util   # jednotná TLS politika (audit #7/#32)
import urllib.request

# Standardní dsw2 cesty (konvence platformy, ne projektové hodnoty).
DEFAULT_FONDS_PATH = "/explore/fonds"
DEFAULT_APPEALS_PATH = "/explore/appeals"
DEFAULT_OPENDATA_PATH = "/opendata"
# Číselníky ČSÚ vystavované dsw2 jako JSON (viz routes.php / sitemap()).
CSU_ENDPOINTS = ("countries", "legal_forms", "municipalities", "municipality_parts")
# Přípony považované za stažitelný dokument (pro klasifikaci odkazů).
DOC_EXTS = ("pdf", "doc", "docx", "rtf", "odt", "ods", "xls", "xlsx", "ppt", "pptx", "zip")

UA = "Mozilla/5.0 (compatible; grantio-research/0.1)"

URL_RE = re.compile(r'https?://[^\s"\'<>)]+')
DOC_EXT_RE = re.compile(r"\.(" + "|".join(DOC_EXTS) + r")(?:$|\?)", re.I)


# ---- pomocné ---------------------------------------------------------------

def base_of(u: str) -> str:
    m = re.match(r"(https?://[^/]+)", u or "")
    return m.group(1) if m else u


def slug_of(u: str) -> str:
    host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", base_of(u)))
    return re.sub(r"[^a-z0-9]+", "-", host.lower()).strip("-")


def clean_name(s: str) -> str:
    """Odstraní koncový typový tag ` [program]`/`[oblast]` a zkrátí mezery."""
    s = re.sub(r"\s*\[[^\]]+\]\s*$", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def html_to_text(s: str) -> str:
    """HTML → prostý text (strip tagů + unescape entit)."""
    s = re.sub(r"(?i)</p>|<br\s*/?>|</li>", "\n", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def fetch(url: str, timeout: int, retries: int, accept: str = "text/html"):
    """Vrátí (status:int|None, body:bytes, err:str|None). Redirecty se následují."""
    last_err = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": accept})
            with http_util.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(), None
        except urllib.error.HTTPError as e:
            return e.code, b"", None
        except Exception as e:  # noqa: BLE001 — síťové chyby různorodé, retry
            last_err = f"{type(e).__name__}: {str(e)[:80]}"
    return None, b"", last_err


def harvest_links(text: str):
    """Vrátí množinu http(s) URL nalezených v textu/HTML fragmentu."""
    return {u.rstrip(".,);") for u in URL_RE.findall(text or "")}


def link_kind(u: str) -> str:
    return "doc" if DOC_EXT_RE.search(u) else "web"


# ---- 1) /explore/fonds — katalog programů (s hierarchií) -------------------

def parse_var(text: str, name: str):
    m = re.search(r"var\s+" + re.escape(name) + r"\s*=\s*(.+?);\s*$",
                  text, re.MULTILINE)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def extract_programs(text: str, fid: str, url: str) -> list:
    programs = parse_var(text, "programs")
    if not programs:
        return []
    fonds = parse_var(text, "fonds") or {}
    realms = parse_var(text, "realms") or {}
    out = []
    for pid, p in programs.items():
        realm = realms.get(str(p.get("realm")), {})
        fond = fonds.get(str(realm.get("fond")), {})
        parent = str(p.get("parent") or "0")
        desc = html_to_text(p.get("description"))
        out.append({
            "foundation_id": fid,
            "program_id": pid,
            "parent_id": parent if parent != "0" else None,
            "is_subprogram": parent != "0",
            "title": clean_name(p.get("name")),
            "url": url,  # dsw2 nemá per-program deep-link (SPA na klik)
            "realm_id": str(p.get("realm")) if p.get("realm") is not None else None,
            "focus_area": clean_name(realm.get("name")) or None,
            "focus_area_description": html_to_text(realm.get("description")) or None,
            "fond": clean_name(fond.get("name")) or None,
            "fond_description": html_to_text(fond.get("description")) or None,
            "description": desc or None,
            "links": sorted(harvest_links(p.get("description"))),
        })
    return out


# ---- 2) /explore/appeals — výzvy -------------------------------------------

CARD_SPLIT_RE = re.compile(r'<div class="card m-2">')
H2_RE = re.compile(r"<h2>(.*?)</h2>", re.S)
HEADER_RE = re.compile(r'<div class="card-header">(.*?)</div>', re.S)
BODY_RE = re.compile(r'<div class="card-body">(.*?)<div class="card-footer">', re.S)
LI_RE = re.compile(r"<li>(.*?)</li>", re.S)
WINDOW_RE = re.compile(
    r"od\s*(\d{1,2})\.\s*(\d{1,2})\.?\s*(?:(\d{4}))?\s*"
    r"do\s*(\d{1,2})\.\s*(\d{1,2})\.?\s*(\d{4})", re.S)
LINK_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*class="link"', re.S)
FOOTER_RE = re.compile(r'<div class="card-footer">(.*?)</div>', re.S)


def _iso(d, m, y):
    try:
        return datetime.date(y, m, d).isoformat()
    except ValueError:
        return None


def derive_status(start, end, today):
    if end and end < today:
        return "closed"
    if start and start > today:
        return "announced"
    if start and end and start <= today <= end:
        return "open"
    return None


def extract_appeals(text: str, fid: str, url: str, today) -> list:
    out = []
    for card in CARD_SPLIT_RE.split(text)[1:]:
        h2 = H2_RE.search(card)
        title = html_to_text(h2.group(1)) if h2 else None
        if not title:
            continue
        hm = HEADER_RE.search(card)
        header = hm.group(1) if hm else card
        start_iso = end_iso = None
        w = WINDOW_RE.search(html_to_text(header))
        if w:
            d1, m1, y1, d2, m2, y2 = w.groups()
            d1, m1, d2, m2 = int(d1), int(m1), int(d2), int(m2)
            year_end = int(y2)
            if y1:
                year_start = int(y1)
            elif (m1, d1) > (m2, d2):
                year_start = year_end - 1  # okno přes přelom roku
            else:
                year_start = year_end
            start_iso = _iso(d1, m1, year_start)
            end_iso = _iso(d2, m2, year_end)
        # popis výzvy + související programy (card-body bez nadpisu a odkazu)
        bm = BODY_RE.search(card)
        body_html = bm.group(1) if bm else ""
        related = [html_to_text(x) for x in LI_RE.findall(body_html)]
        related = [r for r in related if r]
        body_txt = html_to_text(body_html)
        link = LINK_RE.search(card)
        footer = FOOTER_RE.search(card)
        start_d = datetime.date.fromisoformat(start_iso) if start_iso else None
        end_d = datetime.date.fromisoformat(end_iso) if end_iso else None
        src = link.group(1) if link else None
        links = sorted(harvest_links(body_html) | ({src} if src else set()))
        out.append({
            "foundation_id": fid,
            "title": title,
            "url": url,
            "description": body_txt or None,
            "related_programs": related,
            "open_from": start_iso,
            "deadline": end_iso,
            "status": derive_status(start_d, end_d, today),
            "source_url": src,
            "published_note": html_to_text(footer.group(1)) if footer else None,
            "links": links,
        })
    return out


# ---- 3) /opendata — přidělené dotace (entita project) ----------------------

TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
ICO_RE = re.compile(r"\((\d{6,8})\)\s*$")
ODID_RE = re.compile(r"/opendata/(\d+)")


def parse_amount(s: str):
    """„40 000,00 Kč" → 40000.0 (None když nelze)."""
    s = re.sub(r"[^\d,.-]", "", s or "").replace(" ", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s) if s else None
    except ValueError:
        return None


def extract_projects(text: str, fid: str, base: str) -> list:
    """Tabulka /opendata (entita project). Hlavička má 9 sloupců, datové řádky
    ale 10 buněk (1 sloupec navíc), proto mapujeme od KONCE — koncové pořadí
    [..., Žadatel, Částka k vyúčtování, Částka vyúčtovaná, Datum] je stabilní.
    Pořadí od konce: -1 datum, -2 vyúčtovaná, -3 k vyúčtování, -4 žadatel,
    -5 výzva, -6 název žádosti; settlement_id = první buňka."""
    out = []
    for tr in TR_RE.findall(text):
        cells = [html_to_text(x) for x in TD_RE.findall(tr)]
        if len(cells) < 9:  # přeskoč hlavičku (th) i neúplné řádky
            continue
        odid = ODID_RE.search(tr)
        grantee = cells[-4]
        ico = ICO_RE.search(grantee)
        out.append({
            "foundation_id": fid,
            "settlement_id": cells[0] or None,
            "title": cells[-6] or None,
            "appeal_name": cells[-5] or None,
            "grantee": re.sub(r"\s*\(\d{6,8}\)\s*$", "", grantee) or None,
            "grantee_ico": ico.group(1) if ico else None,
            "amount_to_settle": parse_amount(cells[-3]),
            "amount_settled": parse_amount(cells[-2]),
            "last_change": cells[-1] or None,
            "detail_url": f"{base}/opendata/{odid.group(1)}" if odid else None,
        })
    return out


# ---- orchestrace -----------------------------------------------------------

def extract_site(base: str, args, today) -> dict:
    fid = slug_of(base)
    res = {"foundation_id": fid, "base": base, "programs": [], "appeals": [],
           "projects": [], "status": {}}

    s1, b1, e1 = fetch(f"{base}{args.fonds_path}", args.timeout, args.retries)
    res["status"]["fonds"] = s1 or e1
    if s1 == 200:
        res["programs"] = extract_programs(b1.decode("utf-8", "replace"), fid,
                                           f"{base}{args.fonds_path}")

    s2, b2, e2 = fetch(f"{base}{args.appeals_path}", args.timeout, args.retries)
    res["status"]["appeals"] = s2 or e2
    if s2 == 200:
        res["appeals"] = extract_appeals(b2.decode("utf-8", "replace"), fid,
                                         f"{base}{args.appeals_path}", today)

    if not args.no_opendata:
        s3, b3, e3 = fetch(f"{base}{args.opendata_path}", args.timeout, args.retries)
        res["status"]["opendata"] = s3 or e3
        if s3 == 200:
            res["projects"] = extract_projects(b3.decode("utf-8", "replace"), fid, base)
    return res


def collect_links(res: dict) -> list:
    """Sběr stažitelných/scrapovatelných odkazů z výzev, programů, projektů."""
    rows = []
    fid = res["foundation_id"]
    for a in res["appeals"]:
        for u in a["links"]:
            rows.append({"foundation_id": fid, "entity_type": "appeal",
                         "entity_title": a["title"], "url": u, "kind": link_kind(u)})
    for p in res["programs"]:
        for u in p["links"]:
            rows.append({"foundation_id": fid, "entity_type": "program",
                         "entity_title": p["title"], "url": u, "kind": link_kind(u)})
    for pr in res["projects"]:
        if pr.get("detail_url"):
            rows.append({"foundation_id": fid, "entity_type": "project_detail",
                         "entity_title": pr["title"], "url": pr["detail_url"], "kind": "web"})
    return rows


def fetch_csu(base: str, args) -> dict:
    """Stáhne JSON číselníky (jednou; jsou per organizaci shodné)."""
    out = {}
    for name in CSU_ENDPOINTS:
        st, body, err = fetch(f"{base}{args.csu_prefix}/{name}.json",
                              args.timeout, args.retries, accept="application/json")
        if st == 200:
            try:
                out[name] = json.loads(body)
            except json.JSONDecodeError:
                pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", default="data/merged_dataset.json")
    ap.add_argument("--out-dir", default="data", help="adresář pro výstupní jsonl")
    ap.add_argument("--limit", type=int, default=0, help="max počet webů (0=vše)")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--fonds-path", default=DEFAULT_FONDS_PATH)
    ap.add_argument("--appeals-path", default=DEFAULT_APPEALS_PATH)
    ap.add_argument("--opendata-path", default=DEFAULT_OPENDATA_PATH)
    ap.add_argument("--csu-prefix", default="/csu")
    ap.add_argument("--no-opendata", action="store_true")
    ap.add_argument("--no-csu", action="store_true")
    args = ap.parse_args()

    socket.setdefaulttimeout(args.timeout)
    today = datetime.date.today()
    ds = json.load(open(args.dataset, encoding="utf-8"))
    seen, sites = set(), []
    for r in ds:
        if r.get("platform") != "dsw2_otevrena_mesta":
            continue
        b = base_of(r["url"])
        if b not in seen:
            seen.add(b)
            sites.append(b)
    if args.limit:
        sites = sites[: args.limit]

    os.makedirs(args.out_dir, exist_ok=True)
    paths = {k: os.path.join(args.out_dir, f"dsw2_{k}.jsonl")
             for k in ("programs", "appeals", "projects", "links")}
    files = {k: open(v, "w", encoding="utf-8") for k, v in paths.items()}

    n = {"programs": 0, "appeals": 0, "projects": 0, "links": 0}
    summary = []
    csu_saved = False
    for base in sites:
        res = extract_site(base, args, today)
        links = collect_links(res)
        for k, items in (("programs", res["programs"]), ("appeals", res["appeals"]),
                         ("projects", res["projects"]), ("links", links)):
            for it in items:
                files[k].write(json.dumps(it, ensure_ascii=False) + "\n")
                n[k] += 1
        summary.append({"base": base, "status": res["status"],
                        "programs": len(res["programs"]), "appeals": len(res["appeals"]),
                        "projects": len(res["projects"]), "links": len(links)})
        print(f"  {base:<42} prog={len(res['programs']):<3} výzvy={len(res['appeals']):<2}"
              f" projekty={len(res['projects']):<4} linky={len(links)}", file=sys.stderr)
        # číselníky stáhni z prvního dostupného webu (jsou společné)
        if not args.no_csu and not csu_saved and res["status"].get("fonds") == 200:
            csu = fetch_csu(base, args)
            if csu:
                cdir = os.path.join(args.out_dir, "dsw2_codelists")
                os.makedirs(cdir, exist_ok=True)
                for name, data in csu.items():
                    json.dump(data, open(os.path.join(cdir, f"{name}.json"), "w",
                                         encoding="utf-8"), ensure_ascii=False, indent=1)
                csu_saved = True
                print(f"  [csu] uloženo {len(csu)} číselníků z {base}", file=sys.stderr)

    for f in files.values():
        f.close()
    print(json.dumps({"MARKER": "DSW2_RUN", "sites": len(sites), **n,
                      "csu_saved": csu_saved, "summary": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
