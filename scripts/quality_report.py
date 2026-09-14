#!/usr/bin/env python3
"""quality_report.py — KVALITA DATOVÉ ZÁKLADNY JAKO ČÍSLA, NE JAKO TVRZENÍ.

„Scraper funguje" není odpověď na otázku, jak dobrá jsou data. Tenhle skript
odpovídá čísly a vždy nad ŽIVÝMI záznamy zvlášť (open · announced · unknown),
protože právě ty uživatel vidí — uzavřený archiv vyplněnost průměruje nahoru
(naměřeno 2026‑09‑14: částka u 20 % všech záznamů, ale u 8 % živých).

Co měří
  • rozsah:        záznamy, zdroje, stavy k dnešku, dosah (`scope`)
  • vyplněnost:    lhůta, částka, žadatel, oblast, kraj, kontakt, dokumenty — u živých
  • druh lhůty:    fixed / rolling / recurring / unknown
  • čerstvost:     kdy byl záznam naposled viděn u zdroje (≤ 7 d, ≤ 30 d, starší, nevíme)
  • doložitelnost: kolik citací se ve zdroji skutečně našlo; původ polí (parser / model / dopočet)
  • rodiny:        kolik programů se opakuje, kolik starších ročníků je označených
  • zdroje:        po jednom — třída obnovy, počty, stáří, stav (ok · stárne · zmrazený · bez cesty)

Výstup
  docs/QUALITY.md   — čitelná zpráva (v gitu, aby se dal číst vývoj v čase)
  data/quality.json — táž čísla pro stroje

Spuštění (z kořene repa):  python scripts/quality_report.py [--today YYYY-MM-DD]
"""
import argparse
import collections
import datetime
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import dedup   # noqa: E402
import enrich  # noqa: E402

CATALOG = os.path.join(ROOT, "data", "opportunities.jsonl")
INVENTORY = os.path.join(ROOT, "data", "sources.json")
OUT_MD = os.path.join(ROOT, "docs", "QUALITY.md")
OUT_JSON = os.path.join(ROOT, "data", "quality.json")

# Zdroj „stárne", když od posledního ověření uplynulo víc než tohle. Kadence
# obnovy je týdenní (docs/REFRESH.md §2), takže 21 dní = tři zmeškané běhy.
STALE_DAYS = 21


def _status(rec, today):
    return dedup._status(rec, today)


def _pct(n, d):
    return round(100.0 * n / d, 1) if d else None


def _filled(rec, field):
    return rec.get(field) not in (None, "", [], {})


def _days_since(iso, today):
    try:
        return (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(iso)).days
    except (TypeError, ValueError):
        return None


def measure(records, today, inventory):
    grants = [r for r in records if r.get("kind") == "grant"]
    live = [r for r in grants if _status(r, today) != "closed"]
    n, nl = len(grants), len(live)

    status = collections.Counter(_status(r, today) for r in grants)
    scope = collections.Counter(enrich.scope(r) for r in live)
    kinds = collections.Counter(enrich.deadline_kind(r) for r in live)
    fam = dedup.assign_families(records, today)
    for r in live:
        f = fam.get(r["id"])
        if f and f["family"] and len(f["family"]["years"]) >= 2 and enrich.deadline_kind(r) == "unknown":
            kinds["unknown"] -= 1
            kinds["recurring"] += 1

    def fill(field, rs):
        return sum(1 for r in rs if _filled(r, field))

    def ffill(field, rs):
        return sum(1 for r in rs if (r.get("facets") or {}).get(field) not in (None, "", [], {}))

    fields = {
        "deadline": (fill("deadline", live), fill("deadline", grants)),
        "amount": (fill("amount", live), fill("amount", grants)),
        "eligible_applicants": (fill("eligible_applicants", live), fill("eligible_applicants", grants)),
        "typ_zadatele": (ffill("typ_zadatele", live), ffill("typ_zadatele", grants)),
        "oblast": (ffill("oblast", live), ffill("oblast", grants)),
        "kraj_nebo_celostatni": (
            sum(1 for r in live if ((r.get("facets") or {}).get("region") or {}).get("kraj")
                or ((r.get("facets") or {}).get("region") or {}).get("celostatni")),
            sum(1 for r in grants if ((r.get("facets") or {}).get("region") or {}).get("kraj")
                or ((r.get("facets") or {}).get("region") or {}).get("celostatni"))),
        "how_to_apply": (fill("how_to_apply", live), fill("how_to_apply", grants)),
        "source_doc": (fill("source_doc", live), fill("source_doc", grants)),
        "contact": (sum(1 for r in live if enrich.contact(r)), sum(1 for r in grants if enrich.contact(r))),
        "documents": (sum(1 for r in live if enrich.documents(r)), sum(1 for r in grants if enrich.documents(r))),
        "call_number": (sum(1 for r in live if enrich.call_number(r)), sum(1 for r in grants if enrich.call_number(r))),
    }

    fresh = collections.Counter()
    for r in live:
        d = _days_since((r.get("provenance") or {}).get("fetched_at"), today)
        fresh["nevime" if d is None else "do_7" if d <= 7 else "do_30" if d <= 30 else "starsi"] += 1

    cit = collections.Counter(c.get("match") for r in grants for c in (r.get("citations") or []) if isinstance(c, dict))
    located = cit.get("exact", 0) + cit.get("fragment", 0)
    prov = collections.Counter()
    cited = collections.Counter()
    present = collections.Counter()
    for r in live:
        for k, v in enrich.field_provenance(r).items():
            present[k] += 1
            prov[(k, v["method"])] += 1
            cited[k] += 1 if v["cited"] else 0

    families = sum(1 for v in fam.values() if v["family"])
    variants = sum(1 for v in fam.values() if v["variant_of"])
    recurring = sum(1 for v in fam.values() if v["family"] and len(v["family"]["years"]) >= 2)

    # Zdroje: stav z inventáře + stáří.
    per_live = collections.Counter(r.get("source") for r in live)
    sources = []
    for slug, e in sorted(inventory.items()):
        d = _days_since(e.get("last_fetched"), today)
        if e["refresh"] == "F":
            state = "zmrazeny"
        elif e["refresh"] in ("?", "T"):
            state = "bez_cesty"
        elif d is None:
            state = "neovereno"
        elif d > STALE_DAYS:
            state = "starne"
        else:
            state = "ok"
        sources.append({"slug": slug, "name": e.get("name"), "type": e.get("type"), "refresh": e["refresh"],
                        "records": e["records"], "live": per_live.get(slug, 0),
                        "last_fetched": e.get("last_fetched"), "days": d, "state": state})
    by_state = collections.Counter(s["state"] for s in sources)
    live_by_state = collections.Counter()
    for s in sources:
        live_by_state[s["state"]] += s["live"]

    return {
        "today": today,
        "records": len(records), "grants": n, "live": nl, "sources": len(inventory),
        "status": dict(status), "scope_live": dict(scope), "deadline_kind_live": dict(kinds),
        "fields": {k: {"live": v[0], "live_pct": _pct(v[0], nl), "all": v[1], "all_pct": _pct(v[1], n)}
                   for k, v in fields.items()},
        "freshness_live": dict(fresh),
        "citations": {"total": sum(cit.values()), "located": located, "located_pct": _pct(located, sum(cit.values()))},
        "provenance_live": {k: {"present": present[k],
                                "parsed": prov[(k, "parsed")], "model": prov[(k, "model")], "derived": prov[(k, "derived")],
                                "cited": cited[k], "cited_pct": _pct(cited[k], present[k])}
                            for k in sorted(present)},
        "families": {"families": families, "variants": variants, "recurring": recurring},
        "sources_by_state": dict(by_state), "live_by_source_state": dict(live_by_state),
        "sources_table": sources,
    }


def render_md(q):
    L = []
    L.append("# Kvalita datové základny\n")
    L.append(f"Změřeno k **{q['today']}** skriptem `scripts/quality_report.py`. Čísla u živých záznamů "
             f"(open · announced · unknown) jsou ta, která vidí uživatel; archiv je uvedený vedle.\n")
    L.append("## Rozsah\n")
    L.append("| | |\n|---|---:|")
    L.append(f"| záznamů celkem | {q['records']} |")
    L.append(f"| z toho výzev | {q['grants']} |")
    L.append(f"| **živých k dnešku** | **{q['live']}** |")
    L.append(f"| zdrojů | {q['sources']} |")
    st = q["status"]
    L.append(f"| stav | open {st.get('open', 0)} · announced {st.get('announced', 0)} · unknown {st.get('unknown', 0)} · closed {st.get('closed', 0)} |")
    sc = q["scope_live"]
    L.append(f"| dosah živých | místní {sc.get('local', 0)} · krajský {sc.get('regional', 0)} · celostátní {sc.get('national', 0)} · mezinárodní {sc.get('international', 0)} · EU centrální {sc.get('eu_central', 0)} |")
    dk = q["deadline_kind_live"]
    L.append(f"| druh lhůty u živých | jedna lhůta {dk.get('fixed', 0)} · průběžně {dk.get('rolling', 0)} · opakovaně {dk.get('recurring', 0)} · neuvedeno {dk.get('unknown', 0)} |\n")

    L.append("## Vyplněnost polí\n")
    L.append("| pole | živé | archiv |\n|---|---:|---:|")
    names = {"deadline": "lhůta", "amount": "částka pro žadatele", "eligible_applicants": "kdo smí žádat (text)",
             "typ_zadatele": "typ žadatele (faseta)", "oblast": "oblast", "kraj_nebo_celostatni": "území",
             "how_to_apply": "jak podat", "source_doc": "zdrojový dokument", "contact": "kontakt",
             "documents": "dokumenty", "call_number": "číslo výzvy"}
    for k, v in q["fields"].items():
        L.append(f"| {names.get(k, k)} | {v['live_pct']} % ({v['live']}) | {v['all_pct']} % ({v['all']}) |")
    L.append("")

    L.append("## Čerstvost živých záznamů\n")
    fr = q["freshness_live"]
    L.append("| ověřeno u zdroje | záznamů |\n|---|---:|")
    L.append(f"| do 7 dnů | {fr.get('do_7', 0)} |")
    L.append(f"| do 30 dnů | {fr.get('do_30', 0)} |")
    L.append(f"| starší | {fr.get('starsi', 0)} |")
    L.append(f"| nevíme (bez razítka) | {fr.get('nevime', 0)} |\n")

    L.append("## Doložitelnost\n")
    c = q["citations"]
    L.append(f"Citací celkem {c['total']}, ve zdroji dohledaných **{c['located']} ({c['located_pct']} %)**. "
             "Nedohledaná citace nedokládá nic; produkt u takového pole původ neukazuje jako doložený.\n")
    L.append("| pole (živé) | má hodnotu | parser | model | dopočet | doloženo citací |\n|---|---:|---:|---:|---:|---:|")
    for k, v in q["provenance_live"].items():
        L.append(f"| {k} | {v['present']} | {v['parsed']} | {v['model']} | {v['derived']} | {v['cited_pct']} % |")
    L.append("")

    f = q["families"]
    L.append("## Rodiny ročníků\n")
    L.append(f"{f['families']} programů má víc než jeden záznam; {f['recurring']} z nich se vyhlašuje opakovaně "
             f"(dva a víc ročníků); {f['variants']} starších ročníků nese `variant_of`.\n")

    L.append("## Zdroje\n")
    bs, lb = q["sources_by_state"], q["live_by_source_state"]
    L.append("| stav | zdrojů | živých záznamů |\n|---|---:|---:|")
    for key, label in (("ok", "ok (ověřeno do 21 dnů)"), ("starne", "stárne (nad 21 dnů)"),
                       ("neovereno", "má cestu, nikdy neověřeno"), ("bez_cesty", "bez zapsané cesty k obnově"),
                       ("zmrazeny", "zmrazený")):
        L.append(f"| {label} | {bs.get(key, 0)} | {lb.get(key, 0)} |")
    L.append("")
    L.append("| zdroj | typ | obnova | záznamů | živých | ověřeno | stav |\n|---|---|---|---:|---:|---|---|")
    for s in sorted(q["sources_table"], key=lambda s: (-s["live"], s["slug"])):
        L.append(f"| {s['name'] or s['slug']} (`{s['slug']}`) | {s['type'] or ''} | {s['refresh']} | {s['records']} | {s['live']} | {s['last_fetched'] or ''} | {s['state']} |")
    L.append("")
    L.append("Třídy obnovy: A strukturní ingest · B vlastní parser · C model · T přepsaný extraktor (obnovu předstírá) · F zmrazený · ? bez zapsané cesty. "
             "Inventář: `data/sources.json`.\n")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args()
    records = [json.loads(l) for l in open(CATALOG, encoding="utf-8") if l.strip()]
    inventory = {k: v for k, v in json.load(open(INVENTORY, encoding="utf-8")).items() if not k.startswith("_")}
    q = measure(records, a.today, inventory)
    md = render_md(q)
    if not a.no_write:
        with open(OUT_MD, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(md)
        with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(q, fh, ensure_ascii=False, indent="\t")
            fh.write("\n")
    print(f"✓ živých {q['live']} z {q['grants']} · lhůta {q['fields']['deadline']['live_pct']} % · částka {q['fields']['amount']['live_pct']} % · "
          f"žadatel {q['fields']['typ_zadatele']['live_pct']} % · zdroje ok {q['sources_by_state'].get('ok', 0)}/{q['sources']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
