#!/usr/bin/env python3
# Vrstva 2 extrakce pro Ministerstvo zdravotnictví (mzd.gov.cz) — ČISTÝ cílený pull.
# Nahrazuje šumný BFS (3353 stránek). Zpracuje VŠECHNY výzvy z cíleného WP-REST pullu
# (dotační/výzkumné/EU kategorie): 6 aktuálně otevřených ručně bohatě, ostatní (archiv)
# DETERMINISTICKY (datum/název/oprávnění/cíl + verbatim citace z těla). status dopočítá kód.
# Čte data/mzcr_in/grant_*.json, píše data/mzcr_out/grant_*.json (basename-join).
import json, os, re, glob

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
B = "https://mzd.gov.cz/"
MONTHS = {"ledna": 1, "února": 2, "unora": 2, "března": 3, "brezna": 3, "dubna": 4,
          "května": 5, "kvetna": 5, "června": 6, "cervna": 6, "července": 7, "cervence": 7,
          "srpna": 8, "září": 9, "zari": 9, "října": 10, "rijna": 10, "listopadu": 11, "prosince": 12}


def _iso(d, m, y):
    try:
        import datetime
        return datetime.date(int(y), int(m), int(d)).isoformat()
    except Exception:
        return None


def _mon(tok):
    return int(tok) if tok.isdigit() else MONTHS.get(tok.lower())


def _find(body, patterns):
    """Vrať (iso_datum, verbatim_span) prvního pasujícího vzoru, jinak (None, None)."""
    for pat in patterns:
        m = re.search(pat, body, re.I)
        if not m:
            continue
        d, mo, y = m.group("d"), m.group("m"), m.group("y")
        mm = _mon(mo)
        if mm:
            iso = _iso(d, mm, y)
            if iso:
                return iso, re.sub(r"\s+", " ", m.group(0)).strip()
    return None, None


DL_PATS = [
    r"(?i)datum ukončení příjmu \w+[^:\n]*:\s*(?P<d>\d{1,2})\.\s*(?P<m>[^\s,.]+)\.?\s*(?P<y>\d{4})",
    r"(?i)full proposals?\s*:?\s*(?P<d>\d{1,2})\.\s*(?P<m>\d{1,2})\.\s*(?P<y>\d{4})",
    r"(?i)končí dne\s*(?P<d>\d{1,2})\.\s*(?P<m>\d{1,2})\.\s*(?P<y>\d{4})",
    r"(?i)uzávěrka[^:\n]{0,40}:\s*(?P<d>\d{1,2})\.\s*(?P<m>[^\s,.]+)\.?\s*(?P<y>\d{4})",
    r"(?i)otevřena\s+od\s+\d{1,2}\.\s*\S+\s+(?:\d{4}\s+)?do\s+(?P<d>\d{1,2})\.\s*(?P<m>[^\s,.]+)\.?\s*(?P<y>\d{4})",
    r"(?i)\bdo\s+(?P<d>\d{1,2})\.\s*(?P<m>\d{1,2})\.\s*(?P<y>\d{4})\s*(?:23:59|včetně|\(včetně)",
    r"(?i)(?:termín|lhůt[ay])[^.\n]{0,60}?(?P<d>\d{1,2})\.\s*(?P<m>\d{1,2})\.\s*(?P<y>\d{4})",
]
OF_PATS = [
    r"(?i)datum zahájení příjmu \w+[^:\n]*:\s*(?P<d>\d{1,2})\.\s*(?P<m>[^\s,.]+)\.?\s*(?P<y>\d{4})",
    r"(?i)období[^.\n]{0,40}začíná[^.\n]{0,40}tj\.\s*(?P<d>\d{1,2})\.\s*(?P<m>\d{1,2})\.\s*(?P<y>\d{4})",
    r"(?i)začíná dne\s*(?P<d>\d{1,2})\.\s*(?P<m>\d{1,2})\.\s*(?P<y>\d{4})",
    r"(?i)otevřena\s+od\s+(?P<d>\d{1,2})\.\s*(?P<m>[^\s,.]+)\.?\s*(?P<y>\d{4})?\s*do",
]


def _elig(body):
    for pat in [r"(?i)(výzkumná organizace,\s*podnik[^\n.]{0,60})",
                r"(?i)(Oprávněnými žadateli[^\n]{0,140})",
                r"(?i)oprávnění žadatelé o dotaci:\s*\n+\s*([^\n]{8,140})"]:
        m = re.search(pat, body)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip(" :,")
    return None


def _focus(body):
    """První věcný odstavec/věta (přeskoč krátké navigační zbytky)."""
    for para in re.split(r"\n\s*\n", body):
        p = re.sub(r"\s+", " ", para).strip()
        if len(p) > 90 and not p.lower().startswith(("ministerstvo zdravotnictví čr vyhlašuje", "ministerstvo zdravotnictví (")):
            return p[:400]
    p = re.sub(r"\s+", " ", body).strip()
    return p[:400] if len(p) > 40 else None


def _two_phase(body):
    return bool(re.search(r"(?i)pre-proposals?|full proposals?", body))


# ---- RICH overrides (6 aktuálně otevřených výzev — ruční bohatá extrakce) ----
RICH = {
 "335-721": {
  "title": "Výzva 335 721 – Podpora rozvoje přístupnosti a zkvalitňování zdravotních služeb (Vyrovnávání příležitostí pro občany se zdravotním postižením) 2026",
  "oblast": ["zdravotnictví", "sociální", "zdravotní postižení"],
  "focus_area": "Národní dotační program 335 72 „Podpora rozvoje přístupnosti a zkvalitňování zdravotních služeb“, podprogram 335 721 „Vyrovnávání příležitostí pro občany se zdravotním postižením“. Investiční dotace na stavební akce.",
  "open_from": "2026-06-30", "deadline": "2026-09-15",
  "eligible_applicants": "Příspěvkové organizace zřízené územním samosprávným celkem, obce a nestátní neziskové organizace (spolky a ústavy podle zákona č. 89/2012 Sb.).",
  "typ_zadatele": ["prispevkova_organizace", "obec_verejny_subjekt", "neziskovka"],
  "cilova_skupina": ["občané se zdravotním postižením", "poskytovatelé zdravotních a sociálních služeb"],
  "rezim_prijmu": "jednorazova_vyzva", "cislo_vyzvy": "335 721",
  "evidence": {"open_from": "Datum zahájení příjmu žádostí o dotaci: 30. června 2026",
               "deadline": "Datum ukončení příjmu žádostí o dotaci: 15. září 2026",
               "eligible_applicants": "příspěvkové organizace zřízené územním samosprávným celkem,"}},
 "thcs-transforming-health-and-care-system-access-to-care-2026": {
  "title": "THCS – 4. nadnárodní výzva „Access to Care 2026“ (Transforming Health and Care Systems)",
  "oblast": ["zdravotnictví", "výzkum a vývoj", "sociální péče"],
  "focus_area": "Nadnárodní výzva evropského partnerství THCS „Access to Care 2026“ – výzkumné a inovační projekty zlepšující přístup ke zdravotní a sociální péči na všech úrovních.",
  "open_from": None, "deadline": "2026-06-30",
  "eligible_applicants": "Čeští uchazeči: výzkumná organizace, podnik, pacientské organizace (v mezinárodním konsorciu).",
  "typ_zadatele": ["skola_vyzkumna_org", "firma", "neziskovka"],
  "cilova_skupina": ["výzkumné organizace", "podniky", "pacientské organizace"],
  "rezim_prijmu": "kolova", "cislo_vyzvy": None,
  "evidence": {"focus_area": "podpořit projekty, které se zaměří na zlepšení přístupu ke zdravotní a sociální péči na všech úrovních",
               "eligible_applicants": "výzkumná organizace, podnik, pacientské organizace",
               "deadline": "Full proposals: 30. 6. 2026, 14:00 CEST"}},
 "erdera-resolving-unsolved-cases": {
  "title": "ERDERA – 2. nadnárodní výzva „Resolving unsolved cases in rare genetic and non-genetic diseases“ (vzácná onemocnění)",
  "oblast": ["zdravotnictví", "výzkum a vývoj", "vzácná onemocnění"],
  "focus_area": "Druhá společná nadnárodní výzva partnerství ERDERA zaměřená na řešení dosud nevyřešených případů vzácných genetických i negenetických onemocnění.",
  "open_from": None, "deadline": "2026-07-08",
  "eligible_applicants": "Čeští uchazeči: výzkumná organizace, podnik, pacientské organizace (v mezinárodním konsorciu).",
  "typ_zadatele": ["skola_vyzkumna_org", "firma", "neziskovka"],
  "cilova_skupina": ["výzkumné organizace", "podniky", "pacientské organizace"],
  "rezim_prijmu": "kolova", "cislo_vyzvy": None,
  "evidence": {"focus_area": "Resolving unsolved cases in rare genetic and non-genetic diseases",
               "eligible_applicants": "výzkumná organizace, podnik, pacientské organizace",
               "deadline": "Full proposals: 8. 7. 2026, 14:00 CEST"}},
 "be-ready-european-partnership-on-pandemic": {
  "title": "BE READY – 1. nadnárodní výzva (European Partnership on Pandemic Preparedness)",
  "oblast": ["zdravotnictví", "výzkum a vývoj", "pandemická připravenost"],
  "focus_area": "Společná nadnárodní výzva partnerství BE READY – prohloubení vědeckých poznatků o nově/znovu se objevujících patogenech s pandemickým potenciálem.",
  "open_from": None, "deadline": "2026-08-20",
  "eligible_applicants": "Čeští uchazeči: výzkumná organizace, podnik, pacientská organizace (v mezinárodním konsorciu).",
  "typ_zadatele": ["skola_vyzkumna_org", "firma", "neziskovka"],
  "cilova_skupina": ["výzkumné organizace", "podniky", "pacientské organizace"],
  "rezim_prijmu": "kolova", "cislo_vyzvy": None,
  "evidence": {"focus_area": "Cílem výzvy je prohloubit vědecké poznatky a znalosti založené na důkazech o nově či znovu se objevujících patogenech s pandemickým potenciálem",
               "eligible_applicants": "výzkumná organizace, podnik, pacientská organizace",
               "deadline": "Full proposals: 20. 8. 2026, 13:00 CEST"}},
 "na-leta-2026-2030-podprogram-4": {
  "title": "Veřejná soutěž o účelovou podporu MZd 2026–2030, podprogram 4 – Podpora národních autorit v prioritních oblastech zdravotnického výzkumu",
  "oblast": ["zdravotnictví", "výzkum a vývoj"],
  "focus_area": "Jednostupňová veřejná soutěž o účelovou podporu aplikovaného výzkumu – podprogram 4: Podpora národních autorit (návaznost na program EXCELES 2022–2025).",
  "open_from": "2026-04-30", "deadline": "2026-07-28",
  "eligible_applicants": "Pouze příjemce podpory, jemuž byla na vybudování Národní autority v letech 2022–2025 poskytnuta podpora v rámci programu EXCELES.",
  "typ_zadatele": ["skola_vyzkumna_org"],
  "cilova_skupina": ["národní autority ve zdravotnickém výzkumu", "výzkumné organizace"],
  "rezim_prijmu": "jednorazova_vyzva", "cislo_vyzvy": None,
  "evidence": {"focus_area": "Účelová podpora MZd je určena na řešení projektů aplikovaného výzkumu",
               "eligible_applicants": "Uchazečem může být pouze příjemce podpory, jemuž jmenovitě byla na vybudování Národní autority",
               "deadline": "končí dne 28. 7. 2026"}},
 "ucelovou-podporu-mzd-na-leta-2027-2030": {
  "title": "Veřejná soutěž o účelovou podporu MZd na léta 2027–2030 (zdravotnický aplikovaný výzkum)",
  "oblast": ["zdravotnictví", "výzkum a vývoj"],
  "focus_area": "Jednostupňová veřejná soutěž o účelovou podporu projektů zdravotnického aplikovaného výzkumu a vývoje (Program 2024–2030).",
  "open_from": "2026-02-06", "deadline": "2026-11-18",
  "eligible_applicants": "Uchazeči (výzkumné organizace a podniky) způsobilí dle § 18 zákona č. 130/2002 Sb.",
  "typ_zadatele": ["skola_vyzkumna_org", "firma"],
  "cilova_skupina": ["výzkumné organizace", "podniky"],
  "rezim_prijmu": "jednorazova_vyzva", "cislo_vyzvy": None,
  "evidence": {"focus_area": "Účelová podpora MZd je určena na řešení projektů aplikovaného výzkumu",
               "deadline": "končí dne 18. 11. 2026"}},
}


def rich_key(url):
    u = url.lower()
    for k in RICH:
        if k in u:
            return k
    return None


def build_record(url, title, body):
    k = rich_key(url)
    base = {
     "oblast": ["zdravotnictví"], "focus_area": None, "open_from": None, "deadline": None,
     "deadliny": [], "obdobi_realizace": None, "castky": [], "vyse_hlavni_czk": None, "spoluucast": None,
     "eligible_applicants": None, "typ_zadatele": [], "cilova_skupina": [],
     "region": CR, "forma_podpory": ["dotace"], "zdroj_financovani": ["narodni_rozpocet"],
     "rezim_prijmu": "jednorazova_vyzva", "delka": None,
     "how_to_apply": "Žádost se podává způsobem a ve lhůtě stanovené výzvou (viz zdrojová stránka MZd).",
     "required_attachments": [], "cislo_vyzvy": None,
     "source_doc": url, "kontakt": {"osoba": None, "email": None, "telefon": None}, "evidence": {}}
    if k:
        r = dict(base); r.update(RICH[k]); return r
    # --- deterministická extrakce ---
    dl, dl_q = _find(body, DL_PATS)
    of, of_q = _find(body, OF_PATS)
    elig = _elig(body)
    foc = _focus(body)
    ev = {}
    if dl_q:
        ev["deadline"] = dl_q
    if of_q:
        ev["open_from"] = of_q
    if elig:
        ev["eligible_applicants"] = elig
    if foc:
        ev["focus_area"] = foc
    r = dict(base)
    r.update({
        "title": title,
        "focus_area": foc or title,
        "deadline": dl, "open_from": of,
        "eligible_applicants": elig,
        "rezim_prijmu": "kolova" if _two_phase(body) else "jednorazova_vyzva",
        "evidence": ev,
    })
    return r


def main():
    os.makedirs("data/mzcr_out", exist_ok=True)
    n_rich = n_det = n_nodl = 0
    for path in sorted(glob.glob("data/mzcr_in/grant_*.json")):
        d = json.load(open(path, encoding="utf-8"))
        url, title, body = d.get("id") or d.get("web"), d.get("title"), d.get("body") or ""
        rec = build_record(url, title, body)
        if rich_key(url):
            n_rich += 1
        else:
            n_det += 1
            if not rec["deadline"]:
                n_nodl += 1
        json.dump(rec, open(os.path.join("data/mzcr_out", os.path.basename(path)), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"wrote {n_rich+n_det} grants ({n_rich} rich, {n_det} deterministic; {n_nodl} bez deadline) -> data/mzcr_out/")


if __name__ == "__main__":
    main()
