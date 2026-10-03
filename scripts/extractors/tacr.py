#!/usr/bin/env python3
# Vrstva 2 extrakce pro TA ČR (tacr.gov.cz; parser scripts/tacr.py). Veřejné soutěže národních
# programů (PRODEF, SIGMA, DOPRAVA 2030, Prostředí pro život 2, THÉTA 2) a od 2026‑10‑03 i české
# části mezinárodních výzev (Eurostars, Water4All, DUT, CET, FOREST, Biodiversa, M-ERA.NET, LUKE)
# a národní výzvy Seal of Excellence: dřív je harvester přeskakoval, katalog měl z TA ČR 2 otevřené.
# Deterministicky parsuje z labelovaného těla (Vyhlášení / Soutěžní lhůta [od] do / Uchazeči /
# Strop na projekt / Alokace / focus).
# typ_poskytovatele=statni_agentura, zdroj=narodni_rozpocet. Status NEvyplňuji (kód z deadline).
import json, os, re

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW = "Návrh projektu se podává elektronicky v informačním systému TA ČR – SISTA; způsobilost se dokládá samostatně."
D = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")
# program → tematická oblast nad rámec „aplikovaný výzkum"
PROG_OBLAST = {
    "PRODEF": ["obrana", "bezpečnost"], "DOPRAVA 2030": ["doprava"],
    "Prostředí pro život 2": ["životní prostředí", "klima"], "THÉTA 2": ["energetika"],
}


def iso(s):
    m = D.search(s or "")
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def amount(s):
    """Sečti všechny 'N mil./mld. Kč' v textu alokace → CZK (int) nebo None."""
    tot = 0
    for num, unit in re.findall(r"([\d ]+(?:,\d+)?)\s*(mil|mld)", s or ""):
        n = float(num.replace(" ", "").replace(",", "."))
        tot += int(n * (1_000_000 if unit == "mil" else 1_000_000_000))
    return tot or None


def main():
    recs = [json.loads(l) for l in open("data/tacr_documents.jsonl", encoding="utf-8")]
    os.makedirs("data/tacr_out", exist_ok=True)
    for i, r in enumerate(recs):
        b = r.get("body_text", "")
        title = re.sub(r"[⁠​‌‍]+", "", r.get("title", "")).strip()
        prog = re.sub(r"^Program\s+", "", title.split(" – ")[0]).strip()
        # „od X do Y“ (národní soutěž) nebo jen „do Y“ (mezinárodní výzva, 2026‑10‑03).
        sl = re.search(r"Soutěžní lhůta:\s*(?:od\s*(" + D.pattern + r")\s*)?do\s*(" + D.pattern + ")", b)
        open_from = iso(sl.group(1)) if sl and sl.group(1) else None
        deadline = iso(sl.group(5)) if sl else None
        # Kdo smí žádat podle řádku stránky; bez něj obecné pravidlo programů TA ČR.
        uch = re.search(r"Uchazeči:\s*([^\n]+)", b)
        typy = []
        if uch and re.search(r"podnik", uch.group(1), re.I):
            typy.append("firma")
        if uch and re.search(r"výzkumn\w+ organizac", uch.group(1), re.I):
            typy.append("skola_vyzkumna_org")
        typy = typy or ["firma", "skola_vyzkumna_org"]
        # Mezinárodní výzva: česká část konsorcia, kterou platí TA ČR.
        mezi = bool(re.search(r"konsorci|\bCall\b|Partnerství", b + title))
        am = re.search(r"Alokace:\s*([^\n]+)", b)
        vyse = amount(am.group(1)) if am else None
        # Strop na projekt jen jednoznačný: „PP1: 15 mil. Kč, PP2: neomezeno“ strop nemá.
        st = re.search(r"Strop na projekt:\s*([^\n]+)", b)
        strop = amount(st.group(1)) if st and not re.search(r"PP\d|neomezen", st.group(1)) else None
        foc = re.search(r"\n((?:Hlavním cílem|je zaměřen|jsou zaměřen|se zaměřuje)[^\n]+)", b)
        focus = foc.group(1).strip() if foc else f"Veřejná soutěž TA ČR v programu {prog} na podporu aplikovaného výzkumu a inovací."
        f = {
            "title": title,
            "oblast": ["věda a výzkum", "aplikovaný výzkum"] + PROG_OBLAST.get(prog, []),
            "focus_area": focus,
            "open_from": open_from, "deadline": deadline,
            "castky": ([{"typ": "max_zadatel", "hodnota": strop}] if strop else [])
                      + ([{"typ": "alokace", "hodnota": vyse}] if vyse else []),
            "vyse_hlavni_czk": vyse, "spoluucast": True,
            "eligible_applicants": (
                (f"{uch.group(1).strip()}. " if uch else "")
                + ("Česká část mezinárodního konsorcia; TA ČR podporuje české uchazeče podle národních podmínek výzvy."
                   if mezi else
                   "Podniky (vč. malých a středních) a výzkumné organizace, samostatně nebo "
                   "v konsorciu; dle podmínek zadávací dokumentace programu " + prog + ".")),
            "typ_zadatele": typy,
            "cilova_skupina": ["podniky", "výzkumní pracovníci"], "region": CR,
            "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
            "rezim_prijmu": "jednorazova_vyzva", "delka": "viceleta",
            "how_to_apply": HOW, "required_attachments": [], "source_doc": r.get("url"),
            "cislo_vyzvy": title.split(" – ", 1)[-1] if " – " in title else prog,
            "evidence": {"title": title[:80],
                         **({"deadline": sl.group(5).strip()} if sl else {}),
                         **({"vyse_hlavni_czk": am.group(1).strip()[:60]} if am and vyse else {})},
        }
        json.dump(f, open(f"data/tacr_out/grant_{i:02d}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"wrote {len(recs)} grants to data/tacr_out/")


if __name__ == "__main__":
    main()
