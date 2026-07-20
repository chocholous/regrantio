#!/usr/bin/env python3
"""Grantový diář (grantovydiar.cz, Vue SPA + server-rendered detaily) — layer-1 lossless harvest výzev.

STRUKTURA (ověřeno sondou 2026-06-10):
  - Vue SPA (frontapp.js), ALE detail výzvy je SERVER-RENDERED na předvídatelné URL:
      https://grantovydiar.cz/muj-diar/detail-vyzvy?id=N   (N = celé číslo, hustá sekvence)
  - PŘÍSTUP: id 1..~12499 = VEŘEJNÉ (plný detail), id 12500..~13940 = za LOGINEM
    (redirect na ?action=login). Hranice je podle ID, NE podle data → nejčerstvější
    výzvy bývají zamčené. 404 = neexistující id (řídké mezery + nad stropem).
  - Detail = DIGEST původní výzvy (NE PDF přílohy): strukturované labely
      „Organizace:", „Zaměření programu:", „Podmínky pro získání dotace:",
      „Webové stránky programu:" (= ODKAZ na originální výzvu = source_url!),
      „Zaměření výzvy:", „Cílová skupina:", „Místní působnost:", „Poslední aktualizace:",
      „Termín podávání žádostí:" (= DEADLINE), „Finanční alokace výzvy:", „Granty:".
    Titul = název výzvy (nad blokem Organizace). Vyhlašovatel = Organizace.
  - BALAST k vyřazení: odkazy na svetneziskovek.cz/kurzy a onlineproneziskovky.thinkific
    (reklama na kurzy v patičce), svetneziskovek.cz (provozovatel). Ty NEJSOU source_url.

Status (počítá KÓD, ne LLM): deadline = „Termín podávání žádostí" (parse_cz_date);
today > deadline → closed; bez deadline → unknown. (Diář needviduje open_from konzistentně.)

Výstup (kontrakt jako *_documents.jsonl + open_from/deadline/status):
  data/grantovydiar_documents.jsonl  {host, web, title, url, date, kind, provider,
      source_url, deadline, open_from, status, status_source, region, body_text,
      attachments[], n_attachments, raw_fields{}}

Spuštění (z kořene repa, .venv):
  python3 scripts/grantovydiar_harvest.py --ids 12400-12499         # rozsah
  python3 scripts/grantovydiar_harvest.py --ids 12400-12499 --today 2026-06-10
  python3 scripts/grantovydiar_harvest.py --extra-ids 5,100,12000   # konkrétní id (append+dedup)
Po harvestu: python3 scripts/coverage_verify.py data/grantovydiar_documents.jsonl
"""
import argparse, datetime, html as H, json, os, re, sys, time
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from limits import L

BASE = "https://grantovydiar.cz"
HOST = "grantovydiar.cz"
DETAIL = BASE + "/muj-diar/detail-vyzvy?id={}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
OUT = "data/grantovydiar_documents.jsonl"
# domény provozovatele/reklamy — NIKDY source_url výzvy
JUNK_HOSTS = ("svetneziskovek.cz", "onlineproneziskovky.thinkific.com", "grantovydiar.cz")
LABELS = ["Zaměření programu", "Podmínky pro získání dotace", "Webové stránky programu",
          "Zaměření výzvy", "Cílová skupina", "Místní působnost", "Poslední aktualizace",
          "Termín podávání žádostí", "Finanční alokace výzvy", "Granty", "Organizace"]
CZ_MONTHS = None  # diář používá číselné datum D.M.YYYY


RETRYABLE_HTTP = {429, 500, 502, 503, 504}   # rate-limit / dočasná serverová chyba → retry


def fetch(url, timeout):
    """→ (status:int|None, final_url, body). Exponential backoff (0.5→1→2→4 s) na
    síťové výjimky I na retryable HTTP (429/5xx — proxy/nginx rate-limit). 404/302
    se vrací hned (nejsou to chyby — 302=login-gate, 404=neexistuje)."""
    retries = (L("http.default_retries") or 3) + 1
    last = (None, "", "")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.geturl(), r.read(3_000_000).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in RETRYABLE_HTTP and attempt < retries - 1:
                last = (e.code, "", f"http{e.code}")
                time.sleep(0.5 * (2 ** attempt))
                continue
            return e.code, "", ""
        except Exception as e:
            last = (None, "", str(e)[:80])
            if attempt < retries - 1:
                time.sleep(0.5 * (2 ** attempt))
    return last


def strip_text(seg):
    seg = re.sub(r"<script.*?</script>|<style.*?</style>", " ", seg, flags=re.S | re.I)
    return H.unescape(re.sub(r"<[^>]+>", " ", seg))


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def parse_cz_date(s):
    if not s:
        return None
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", s)
    if not m:
        return None
    d, mo, y = map(int, m.groups())
    try:
        return datetime.date(y, mo, d).isoformat()
    except ValueError:
        return None


def compute_status(deadline, today):
    if not deadline:
        return "unknown", "no_deadline"
    return ("closed" if today > deadline else "open"), "deadline_vs_today"


def main_segment(body):
    """Hlavní obsahový blok detailu (od „Popis výzvy" po patičku)."""
    m = re.search(r"(Popis\s+výzvy.*?)(<footer|Můj grantový diář|Newsletter|Vzdělávání se Světem|©)",
                  body, re.S)
    return m.group(1) if m else body


def parse_detail(idn, status_code, final_url, body, today):
    """→ rec dict | None (None = login/404/prázdné)."""
    if status_code == 404 or not body:
        return None
    if "action=login" in (final_url or "") or "Pro přístup do Grantového" in body:
        return None
    if "Popis výzvy" not in body or "Vyhlašovatel" not in body:
        return None

    seg = main_segment(body)
    txt = clean(strip_text(seg))

    # raw_fields podle labelů (label: hodnota až po další label nebo tečku-blok)
    raw = {}
    stop = "|".join(re.escape(l) for l in LABELS)
    for lbl in LABELS:
        m = re.search(re.escape(lbl) + r"\s*:?\s*(.*?)(?=\s*(?:" + stop + r")\s*:|$)", txt)
        if m:
            v = clean(m.group(1))
            if v and v not in (":", "-"):
                raw[lbl] = v[:1500]

    # titul: za blokem „Vyhlašovatel" bývá název výzvy, pak „Organizace:"
    title = None
    mt = re.search(r"Vyhlašovatel\s+(.+?)\s+Organizace\s*:", txt)
    if mt:
        title = clean(mt.group(1))
    if not title:
        mt = re.search(r"<title>\s*(.+?)\s*\|", body)
        title = clean(strip_text(mt.group(1))) if mt else None
    if title in (None, "", "Detail výzvy"):
        # fallback: první větší nadpis v segmentu
        mh = re.search(r"<h[12][^>]*>\s*([^<]{5,120})\s*</h", seg)
        title = clean(mh.group(1)) if mh else f"výzva id={idn}"

    # Organizace bývá uvedena dvakrát (záhlaví karty + blok Vyhlašovatel); hodnota
    # zachytí i začátek dalšího bloku „Popis výzvy"/„Termíny…" → odřízni.
    provider = raw.get("Organizace")
    if provider:
        provider = clean(re.split(r"\s*(?:Popis výzvy|Termíny uzávěrek|Zaměření)\b", provider)[0])
        raw["Organizace"] = provider

    # source_url = první „real" odkaz mimo JUNK_HOSTS (typicky „Webové stránky programu")
    source_url = None
    for href in re.findall(r'href="(https?://[^"]+)"', seg):
        if not any(j in href for j in JUNK_HOSTS):
            source_url = H.unescape(href)
            break

    deadline = parse_cz_date(raw.get("Termín podávání žádostí"))
    status, ssrc = compute_status(deadline, today)
    region = raw.get("Místní působnost")
    last_upd = parse_cz_date(raw.get("Poslední aktualizace"))

    return {
        "host": HOST, "web": BASE,
        "title": title, "url": DETAIL.format(idn), "id": idn,
        "date": last_upd, "kind": "vyzva",
        "provider": provider, "source_url": source_url,
        "deadline": deadline, "open_from": None,
        "status": status, "status_source": ssrc,
        "region": region,
        "body_text": txt,
        "attachments": [], "n_attachments": 0,
        "raw_fields": raw,
    }


def expand_ids(spec):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="rozsah/seznam, např. 12400-12499 nebo 5,100,12000")
    ap.add_argument("--extra-ids", help="konkrétní id k doplnění (append+dedup)")
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--timeout", type=int, default=L("http.default_timeout_s") or 20)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    today = args.today
    ids = expand_ids(args.ids or "") + expand_ids(args.extra_ids or "")
    if not ids:
        ap.error("zadej --ids nebo --extra-ids")

    done = set()
    if os.path.exists(args.out):
        for ln in open(args.out):
            try:
                done.add(json.loads(ln).get("id"))
            except Exception:
                pass
    ids = [i for i in ids if i not in done]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    counts = {"public": 0, "login": 0, "notfound": 0, "ratelimit": 0, "err": 0}

    def work(idn):
        st, fin, body = fetch(DETAIL.format(idn), args.timeout)
        rec = parse_detail(idn, st, fin, body, today)
        if rec:
            return ("public", rec)
        if st == 404:
            return ("notfound", None)
        if st is None:
            return ("err", None)
        if st in RETRYABLE_HTTP:          # vyčerpal retries → NEzaměňuj s login-gate
            return ("ratelimit", None)
        return ("login", None)            # 302 (a jiné) = skutečný login-gate

    total = len(ids)
    recs_n = 0
    started = time.time()
    # PRŮBĚŽNÝ ZÁPIS: append + flush po každé dávce; výsledky řadíme po blocích,
    # ať soubor roste a běh přežije pád. Log [N/total] do stdout (→ log soubor).
    out = open(args.out, "a", buffering=1)
    done = 0
    with ThreadPoolExecutor(args.workers) as ex:
        for kind, rec in ex.map(work, ids):
            counts[kind] += 1
            done += 1
            if rec:
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
                recs_n += 1
            if done % 100 == 0 or done == total:
                rate = done / max(0.1, time.time() - started)
                eta = (total - done) / max(0.1, rate)
                print(f"[{done}/{total}] public={counts['public']} login={counts['login']} "
                      f"404={counts['notfound']} rl={counts['ratelimit']} err={counts['err']} "
                      f"| {rate:.1f} req/s ETA {eta/60:.0f}m", flush=True)
    out.close()

    # MARKER souhrn — status rozpad + source_url dočti ze souboru (celý, vč. dřívějších)
    by_status = {}
    with_src = file_total = 0
    for ln in open(args.out):
        try:
            r = json.loads(ln)
        except Exception:
            continue
        file_total += 1
        by_status[r.get("status")] = by_status.get(r.get("status"), 0) + 1
        if r.get("source_url"):
            with_src += 1
    marker = {"MARKER": "GRANTOVYDIAR_HARVEST", "today": today, "requested": total,
              "public": counts["public"], "login_gated": counts["login"],
              "ratelimit": counts["ratelimit"], "notfound": counts["notfound"],
              "err": counts["err"], "appended_this_run": recs_n,
              "file_total": file_total, "by_status": by_status,
              "with_source_url": with_src, "out": args.out}
    print(json.dumps(marker, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
