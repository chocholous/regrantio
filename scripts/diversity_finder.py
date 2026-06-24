#!/usr/bin/env python3
"""Najdi ODLIŠNÉ zdroje (active learning pro coverage): skenuje korpus na
doménově-distinktivní markery (věda / EU-přeshraniční / půjčky / nadace /
slovenština / průběžné-rolling / voucher / de-minimis / bilingual) — zdroje
bohaté na ně přinesou NOVÉ formulace a záměny, které jsme zatím neviděli.
"""
import json, re, glob, os
from collections import defaultdict, Counter

# domény, které máme PODSAMPLOVANÉ + jejich markery (= jiný jazyk pole)
DOMAINS = {
    "věda/výzkum": r"\b(grantov\w+ projekt|návrh projektu|řešitel|spoluřešitel|panel|hodnoticí|ERC|excelen|juniorský|standardní projekt|GA ČR|postdok|badatel)",
    "EU/přeshraniční": r"\b(NFP|nenávratn\w+ finančn|spolufinancov|kohezn|EFRR|ERDF|mikroprojekt|přeshraničn|interreg|partner projektu|lead partner)",
    "půjčky/fin.nástroje": r"\b(zápůjčk|úvěr|návratn\w+ (?:finanční )?výpomoc|úroková sazba|splátk|ručení|finanční nástroj|revolving)",
    "nadace/dárcovství": r"\b(nadační příspěvek|nadační jmění|grantová výzva nadace|dárc|filantrop|nominac|sbírk|individuální dárce)",
    "slovenština": r"\b(žiadosť|oprávnen|výzva na predkladanie|poskytnut\w+ dotácie|prijímateľ|žiadateľ)",
    "průběžné/rolling": r"\b(průběžn\w+ (?:výzv|příjem)|kontinuáln|do vyčerpání (?:alokace|prostředků)|kdykoliv (?:během|v průběhu)|otevřená výzva bez)",
    "voucher/malé": r"\b(voucher|inovační poukázk|kreativní voucher|mikrogrant|malý grant|do 50 ?000)",
    "de-minimis/veř.podpora": r"\b(de minimis|veřejná podpora|blokov\w+ výjimk|GBER|notifik\w+ podpor|slučitelná podpora)",
    "bilingual_en": r"\b(call for proposals|eligible applicants|deadline|grant scheme|funding|applicant)",
}
COMP = {k: re.compile(v, re.I) for k, v in DOMAINS.items()}

# zdroje, které jsme UŽ vzorkovali (z coverage + type samplů) — vyloučit jako 'seen'
SEEN = set()
for p in glob.glob("coverage_sample/*.json") + glob.glob("type_sample/*.json"):
    for d in json.load(open(p)):
        SEEN.add(d.get("src", "").split("/")[0])

src_hits = defaultdict(Counter)   # zdroj -> domain -> počet
src_total = Counter()

def scan(src, text):
    if not text or len(text) < 100:
        return
    src_total[src] += 1
    for dom, rx in COMP.items():
        if rx.search(text):
            src_hits[src][dom] += 1

# wp_full
for f in glob.glob("data/wp_full/*.jsonl"):
    if os.path.getsize(f) == 0:
        continue
    web = os.path.basename(f).split("__")[0]
    for i, line in enumerate(open(f, encoding="utf-8")):
        if i >= 2500:
            break
        try:
            r = json.loads(line)
        except Exception:
            continue
        _t = r.get("title"); _t = _t if isinstance(_t, str) else r.get("title_text")  # nové kanonické vs legacy wp_full snapshot (title=raw objekt)
        scan(web, (_t or "") + " " + (r.get("text") or r.get("content_text") or ""))
# vismo dokumenty + přílohy
if os.path.exists("data/vismo_documents.jsonl"):
    for line in open("data/vismo_documents.jsonl", encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        t = r.get("body_text", "") + " " + " ".join(a.get("text_excerpt", "") for a in r.get("attachments", []))
        scan("vismo/" + r.get("web", "?"), t)
# dsw2 + sk-cz
for f, src in [("data/dsw2_programs.jsonl", "dsw2"), ("data/wp_full/sk-cz-eu__posts.jsonl", "sk-cz")]:
    if os.path.exists(f) and os.path.getsize(f) > 0:
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except Exception:
                continue
            scan(src, json.dumps(r, ensure_ascii=False))

# pro každou doménu: top zdroje (preferuj NEVZORKOVANÉ), density
print("=== ODLIŠNÉ ZDROJE per doména (kandidáti na další coverage dávky) ===\n")
out = {}
for dom in DOMAINS:
    ranked = sorted(((s, src_hits[s][dom], src_total[s]) for s in src_hits if src_hits[s][dom] >= 2),
                    key=lambda x: -x[1])
    out[dom] = [(s, h, t, s.split("/")[0] not in SEEN) for s, h, t in ranked[:6]]
    print(f"## {dom}")
    for s, h, t, novel in out[dom][:5]:
        mark = " ⭐NOVÝ" if novel else " (už vzorkováno)"
        print(f"   {s:26s} hitů={h:4d}/{t}{mark}")
    print()
json.dump({"seen": sorted(SEEN), "by_domain": {k: [(s, h, t, n) for s, h, t, n in v] for k, v in out.items()}},
          open("diversity_candidates.json", "w"), ensure_ascii=False, indent=1)
print("DIVERSITY_DONE")
