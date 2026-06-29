#!/usr/bin/env python3
# Vrstva 2 extrakce pro Nadaci Via (nadacevia.cz, parser scripts/nadacevia.py).
# Velká komunitní nadace: grantové výzvy = WP pages (Milion pro …, Komunita, Místo kde
# žijeme, mikrogranty, JRD …). DETERMINISTICKÁ extrakce s BEZPEČNÝM statusem:
#  • „průběžně" → deadline=průběžně (open);  • „PŘÍJEM … UKONČEN" → closed (poslední app-datum);
#  • datum JEN z řádků s app-cue (uzávěrka/podání/přihlášku…do), NIKDY ze „závěrečná zpráva/
#    vyúčtování/realizace" (past-pitfall). Bez spolehlivého app-data → deadline=null (unknown).
# o-nadaci → foundation_mission. Skip-list = hub/krátké popisy fondů/formuláře/duplicity.
import json, os, re, glob, datetime

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
KONT = {"osoba": None, "email": "via@nadacevia.cz", "telefon": "608 538 083"}
MONTHS = {"ledna": 1, "února": 2, "unora": 2, "března": 3, "brezna": 3, "dubna": 4,
          "května": 5, "kvetna": 5, "června": 6, "cervna": 6, "července": 7, "cervence": 7,
          "srpna": 8, "září": 9, "zari": 9, "října": 10, "rijna": 10, "listopadu": 11, "prosince": 12}
SKIP_TITLES = {"Milion pro", "Fond T-Mobile", "Fond Černošice", "Fond Tři sestry pomáhají",
               "Fond správní rady formulář přihláška", "Místo, kde žijeme", "Pomáhejme příběhům"}
ABOUT = "o-nadaci"

APP_CUE = re.compile(r"uzávěrk|termín pro podání|nejzazší termín|termín je|termín pro (?:odeslání|zaslání)|podání přihláš|přihlášk\w*\s*(?:je\s*potřeba\s*)?(?:vyplnit a )?(?:zaslat|odeslat|podat)|přihlášky\s+(?:přijímáme|zasílejte|podáv)|vyplňte\s+(?:jednoduchý\s+)?(?:vstupní\s+)?dotazník", re.I)
REPORT_CUE = re.compile(r"závěrečn|vyúčtov|realizac|zpráv|ukončení realizace|vyhodnocením", re.I)
CLOSED_SIG = re.compile(r"UKONČEN|ukončen příjem|příjem\s+\w*\s*ukončen|uzavřeno", re.I)
ROLLING_SIG = re.compile(r"průběžně|přijímáme průběžně|celý rok", re.I)


def iso(d, m, y):
    try:
        return datetime.date(int(y), int(m), int(d)).isoformat()
    except Exception:
        return None


def mon(tok):
    return int(tok) if tok.isdigit() else MONTHS.get(tok.lower())


def parse_date(s):
    m = re.search(r"(\d{1,2})\.\s*([^\s,.]+)\.?\s*(\d{4})", s)
    if not m:
        return None
    mm = mon(m.group(2))
    return iso(m.group(1), mm, m.group(3)) if mm else None


def app_deadline(body):
    """Nejpozdější APP-deadline z řádků s app-cue (ne report/realizace cue)."""
    cands = []
    for ln in body.split("\n"):
        if APP_CUE.search(ln) and not REPORT_CUE.search(ln):
            d = parse_date(ln)
            if d:
                cands.append((d, re.sub(r"\s+", " ", ln).strip()))
        # cue a datum na sousedním řádku (uzávěrka: \n DD. měsíc YYYY) řeší spojení níže
    return max(cands, key=lambda x: x[0]) if cands else (None, None)


def app_deadline_joined(body):
    """Cue a datum na DVOU řádcích (uzávěrka přihlášek:\n22. 2. 2026). JEN explicitní
    uzávěrka/termín-podání cue (NE bare „do" — to chytalo report/realizace data → false-open)."""
    joined = re.sub(r"\n+", " ", body)
    best = None
    for m in re.finditer(r"(uzávěrka[^.\n]{0,30}|termín pro podání[^.\n]{0,30})\s*[:–-]?\s*(\d{1,2})\.\s*([^\s,.]+)\.?\s*(\d{4})", joined, re.I):
        seg = m.group(0)
        if REPORT_CUE.search(seg):
            continue
        mm = mon(m.group(3))
        d = iso(m.group(2), mm, m.group(4)) if mm else None
        if d and (best is None or d > best[0]):
            best = (d, re.sub(r"\s+", " ", seg).strip())
    return best or (None, None)


def max_year(body):
    ys = [int(y) for y in re.findall(r"\b(20\d\d)\b", body)]
    return max(ys) if ys else 0


def amount(body):
    for pat in [r"ve výši\s*([\d  ]+)\s*až\s*([\d  ]+)\s*Kč",
                r"([\d  ]+)\s*Kč\s*až\s*([\d  ]+)\s*Kč",
                r"(?:maximální výši|do výše|maximálně)\s*([\d  ]+)\s*Kč",
                r"[Mm]ikrogranty do výše\s*([\d  ]+)\s*Kč"]:
        m = re.search(pat, body)
        if m:
            nums = [int(re.sub(r"\D", "", g)) for g in m.groups() if g and re.sub(r"\D", "", g)]
            if nums:
                return max(nums), re.sub(r"\s+", " ", m.group(0)).strip()
    return None, None


def eligibility(body):
    for pat in [r"(obce do [\d  ]+ obyvatel)",
                r"Kdo může žádat[^\n?]*\?\s*\n+\s*([^\n]{8,140})",
                r"(Žádat mohou[^\n]{8,140})",
                r"KDO MŮŽE ŽÁDAT[^\n?]*\?\s*\n+\s*([^\n]{8,140})"]:
        m = re.search(pat, body, re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip(" :,")
    return None


def focus(body):
    for para in re.split(r"\n\s*\n", body):
        p = re.sub(r"\s+", " ", para).strip()
        if len(p) > 80 and not re.match(r"(O fondu|O programu|Fond Kaufland|Podpořené)", p):
            return p[:380]
    return None


def build(title, body):
    if "JRD" in title:  # deadline 31. 7. 2026 ověřen freshness-scanem (na stránce ve form-poli, ne v content.rendered)
        return {
            "title": "Fond pro udržitelný život (JRD Group) – Nadace Via",
            "oblast": ["udržitelnost", "životní prostředí", "komunitní rozvoj"],
            "focus_area": "Fond JRD Group při Nadaci Via: šíření tématu udržitelnosti a zdravého životního stylu; podpora komunitních a osvětových projektů (komunitní život – školy, knihovny, příspěvkové organizace obcí, farní charity aj.).",
            "open_from": None, "deadline": "2026-07-31", "deadliny": [],
            "obdobi_realizace": None, "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
            "eligible_applicants": "Neziskové organizace a další organizace podporující komunitní život (školy, knihovny, příspěvkové organizace obcí, farní charity aj.).",
            "typ_zadatele": ["neziskovka", "prispevkova_organizace"],
            "cilova_skupina": ["komunity", "neziskové organizace"], "region": CR,
            "forma_podpory": ["dotace"], "zdroj_financovani": ["vlastni_zdroje"],
            "rezim_prijmu": "jednorazova_vyzva", "delka": None,
            "how_to_apply": "Přihláška se podává online přes systém Nadace Via; nejzazší termín 31. 7. 2026.",
            "required_attachments": [], "cislo_vyzvy": None, "source_doc": None, "kontakt": KONT,
            "evidence": {"focus_area": "Posláním fondu je šířit téma udržitelnosti a zdravého životního stylu"}}
    rolling = bool(ROLLING_SIG.search(body))
    closed = bool(CLOSED_SIG.search(body))
    d1, q1 = app_deadline(body)
    d2, q2 = app_deadline_joined(body)
    # vyber pozdější ze dvou metod
    cand = max([x for x in [(d1, q1), (d2, q2)] if x[0]], default=(None, None), key=lambda x: x[0])
    dl, dlq = cand
    deadline = None
    ev = {}
    cur_year = datetime.date.today().year
    # rolling→open jen když stránka NENÍ stará (zmiňuje letošní/příští rok) — vyřadí archiv „průběžně 2021"
    if rolling and max_year(body) >= cur_year and not (dl and dl >= datetime.date.today().isoformat()):
        deadline = "průběžně"
        m = re.search(r"[^.\n]*(?:průběžně|přijímáme průběžně|celý rok)[^.\n]*", body, re.I)
        if m:
            ev["deadline"] = re.sub(r"\s+", " ", m.group(0)).strip()
    elif dl:
        deadline = dl
        if dlq:
            ev["deadline"] = dlq
    # closed override: pokud UKONČEN a deadline je budoucí/None → srovnej na closed přes app-datum,
    # ale NIKDY nevyrob open; když není past datum, nech null (unknown) a zaznamenej signál
    if closed and (deadline == "průběžně" or deadline is None or deadline >= datetime.date.today().isoformat()):
        if dl and dl < datetime.date.today().isoformat():
            deadline = dl
        else:
            deadline = None  # neumíme bezpečně → unknown (radši než špatně open)
    amt, amtq = amount(body)
    elig = eligibility(body)
    foc = focus(body)
    if elig:
        ev["eligible_applicants"] = elig
    if amtq:
        ev["castky"] = amtq
    if foc and "focus_area" not in ev:
        ev["focus_area"] = foc
    return {
        "title": title, "oblast": ["komunitní rozvoj", "občanská společnost"],
        "focus_area": foc or title, "open_from": None, "deadline": deadline, "deadliny": [],
        "obdobi_realizace": None,
        "castky": ([{"typ": "max_zadatel", "hodnota": amt, "kontext": amtq}] if amt else []),
        "vyse_hlavni_czk": amt, "spoluucast": None,
        "eligible_applicants": elig, "typ_zadatele": [], "cilova_skupina": [],
        "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["vlastni_zdroje"],
        "rezim_prijmu": "prubezna" if deadline == "průběžně" else "jednorazova_vyzva",
        "delka": None,
        "how_to_apply": "Žádost/přihláška se podává online přes systém Nadace Via (viz zdrojová stránka); některé fondy mají vstupní dotazník a 2 kola.",
        "required_attachments": [], "cislo_vyzvy": None,
        "source_doc": None, "kontakt": KONT, "evidence": ev}


def mission(body):
    m = re.search(r"(Jsme nezávislá nadace[^.]*\.[^.]*\.)", body)
    j = re.search(r"(Prostředky na svoji činnost[^.]*\.|programy pro aktivní[^.]*\.)", body)
    ev = {}
    if m:
        ev["mission"] = re.sub(r"\s+", " ", m.group(1)).strip()
    return {
        "name": "Nadace Via",
        "mission": "Nezávislá nadace, která rozvíjí komunitní život a filantropii v Česku; podporuje lidi, kteří společně pečují o své okolí a kteří darují druhým. Nabízí programy pro aktivní děti i dospělé a provozuje platformu pro online dárcovství Darujme.cz.",
        "support_topics": ["komunitní život a sousedské projekty", "péče o veřejný prostor", "filantropie a dárcovství", "aktivní občanství"],
        "cilova_skupina": ["aktivní občané a komunity", "neziskové organizace", "obce"],
        "regions": ["Česká republika"], "forma_podpory": ["dotace"],
        "jak_oslovit": "Rozděluje prostředky prostřednictvím grantových programů (Milion pro …, Místo kde žijeme, komunitní zahrady, mikrogranty aj.) a fondů firemních i rodinných dárců; provozuje dárcovskou platformu Darujme.cz.",
        "kontakt": KONT, "source_doc": "https://www.nadacevia.cz/o-nadaci/",
        "evidence": ev or {"mission": "Nadace Via"}}


def main():
    os.makedirs("data/nadacevia_out", exist_ok=True)
    n_g = n_skip = 0
    mission_idx = None
    for path in sorted(glob.glob("data/nadacevia_in/grant_*.json")):
        d = json.load(open(path, encoding="utf-8"))
        url, title, body = d.get("id") or d.get("web"), (d.get("title") or "").strip(), d.get("body") or ""
        base = os.path.basename(path)
        if ABOUT in (url or ""):
            mission_idx = base
            continue
        if title in SKIP_TITLES:
            n_skip += 1
            continue
        rec = build(title, body)
        rec["source_doc"] = url
        json.dump(rec, open(f"data/nadacevia_out/{base}", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        n_g += 1
    # mission via basename-join: zkopíruj about grant_NN → mission_00 v _in, zapiš mission_00 do _out
    if mission_idx:
        import shutil
        ab = json.load(open(f"data/nadacevia_in/{mission_idx}", encoding="utf-8"))
        shutil.copyfile(f"data/nadacevia_in/{mission_idx}", "data/nadacevia_in/mission_00.json")
        json.dump(mission(ab.get("body") or ""), open("data/nadacevia_out/mission_00.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"wrote {n_g} grants + {'1 mission' if mission_idx else '0 mission'} (skipped {n_skip}) -> data/nadacevia_out/")


if __name__ == "__main__":
    main()
