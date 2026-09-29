#!/usr/bin/env python3
"""enrich.py — ODVOZENÁ POLE KONTRAKTU 1.2, počítaná deterministicky z katalogu.

Regrantio do 2026‑09‑14 publikovalo záznam tak, jak ho vytěžila vrstva 2: pole
ze zdroje a fasety. Produkt z toho nedokázal odpovědět na čtyři otázky, které
si klade každý žadatel, a odpovídal na ně sám, každý na jiném místě, nebo
vůbec:

    1. Je to pro subjekt naší velikosti, nebo je to Horizon Europe?     → `scope`
    2. Má výzva JEDNU lhůtu, bere se průběžně, nebo se vyhlašuje
       každý rok znovu?                                                 → `deadline_kind`
    3. Je tenhle záznam nový program, nebo další ročník toho, co už
       vidím o řádek výš?                                               → `program_key`, `variant_of`
    4. Odkud ten údaj je — přečtený strojem ze struktury, vytěžený
       modelem z prózy, nebo dopočítaný?                                → `field_provenance`

Odpovědi jsou ODVOZENINY: nic z toho není nový sběr, všechno se počítá z polí,
která katalog už nese (`facets`, `extra`, `citations`, `provenance`). Proto
leží v jednom modulu, mají testy a do otisku obsahu (`content_hash`) NEVSTUPUJÍ:
změna pravidla odvození není změna výzvy.

⚠ NEHÁDAT. Kde pravidlo nemá podklad, vrací `unknown` / null. `deadline_kind`
je `recurring` jen tehdy, když zdroj opakování skutečně uvádí (věta o lhůtě
v `extra.deadliny`, kolový režim, odvozený termín) — ne proto, že „obce to tak
mívají".

Kontrakt polí je popsaný v `docs/EXPORT.md` §2b.
"""
import hashlib
import re
import unicodedata

# ---------------------------------------------------------------- scope
# Dosah výzvy podle toho, KDO ji vyhlašuje a PRO KOHO. Není to relevance, je to
# měřítko: obec vyhlašuje pro své území, Evropská komise pro konsorcia z celé
# Unie. Produkt podle toho řadí, ne filtruje — Horizon je pro univerzitu
# správná odpověď a pro spolek s třemi lidmi šum.
SCOPE_EU_CENTRAL = "eu_central"
SCOPE_INTERNATIONAL = "international"
SCOPE_NATIONAL = "national"
SCOPE_REGIONAL = "regional"
SCOPE_LOCAL = "local"


def scope(rec):
    f = rec.get("facets") or {}
    prov_type = f.get("typ_poskytovatele")
    region = f.get("region") or {}
    if prov_type == "evropska_komise":
        return SCOPE_EU_CENTRAL
    if prov_type == "zahranicni_fond":
        return SCOPE_INTERNATIONAL
    if prov_type == "samosprava_obec":
        return SCOPE_LOCAL
    if prov_type == "samosprava_kraj":
        return SCOPE_REGIONAL
    # Ministerstvo, fond, agentura, nadace: celostátní, pokud se samo neomezí
    # na kraj nebo obec (krajské pobočky nadací, programy pro jedno město).
    if region.get("obec") and not region.get("celostatni"):
        return SCOPE_LOCAL
    if region.get("kraj") and not region.get("celostatni"):
        return SCOPE_REGIONAL
    return SCOPE_NATIONAL


# ---------------------------------------------------------------- deadline_kind
ROLLING_WORDS = {"průběžně", "prubezne", "průběžný", "rolling"}
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Slovní opakování v kontextu lhůty: „každoročně", „každý rok", „ročně", den bez roku
_RECURRING_WORDS = re.compile(r"každoročn|každý rok|ročně|každého roku|daného (kalendářního )?roku", re.I)
_DAY_MONTH_NO_YEAR = re.compile(r"^\s*\d{1,2}\.\s*\d{1,2}\.\s*$")


def deadline_kind(rec):
    """`fixed` · `rolling` · `recurring` · `unknown`.

    fixed      — jedna ISO lhůta (`deadline`)
    rolling    — příjem průběžný (slovní termín, nebo režim `prubezna`)
    recurring  — bez jedné lhůty, ale zdroj říká, že se program vyhlašuje
                 opakovaně (kolový režim, „každoročně", den bez roku,
                 termín odvozený z opakující se lhůty)
    unknown    — zdroj o lhůtě mlčí
    """
    d = rec.get("deadline")
    f = rec.get("facets") or {}
    extra = rec.get("extra") or {}
    if isinstance(d, str) and d.strip().lower() in ROLLING_WORDS:
        return "rolling"
    if isinstance(d, str) and _ISO.match(d):
        # Odvozený termín (derive_deadlines) = opakující se lhůta promítnutá na
        # nejbližší výskyt. Je to skutečné datum, ale příští rok bude zase.
        if extra.get("deadline_derived_rule") or rec.get("status_confidence") == "derived":
            return "recurring"
        return "fixed"
    if f.get("rezim_prijmu") == "prubezna":
        return "rolling"
    if f.get("rezim_prijmu") == "kolova":
        return "recurring"
    for item in extra.get("deadliny") or []:
        if not isinstance(item, dict):
            continue
        datum = str(item.get("datum") or "")
        ctx = str(item.get("kontext") or "")
        if _DAY_MONTH_NO_YEAR.match(datum) or _RECURRING_WORDS.search(datum) or _RECURRING_WORDS.search(ctx):
            return "recurring"
        if any(w in (datum + " " + ctx).lower() for w in ROLLING_WORDS):
            return "rolling"
    return "unknown"


def deadline_note(rec):
    """Věta ze zdroje o lhůtě tam, kde ISO datum chybí. Jinak null.

    Uživatel má vidět, CO zdroj říká („uzávěrka každoročně 15. 11."), ne jen
    „neuvedeno". Bere se první položka `extra.deadliny` s kontextem.
    """
    d = rec.get("deadline")
    if isinstance(d, str) and _ISO.match(d):
        return None
    extra = rec.get("extra") or {}
    for item in extra.get("deadliny") or []:
        if not isinstance(item, dict):
            continue
        ctx = (item.get("kontext") or "").strip()
        datum = (item.get("datum") or "").strip() if isinstance(item.get("datum"), str) else ""
        if ctx:
            return ctx[:240]
        if datum:
            return datum[:240]
    return None


# ---------------------------------------------------------------- early_close
# PUBLIKOVANÁ UZÁVĚRKA NENÍ VŽDY SKUTEČNÁ (kontrakt 1.3, 2026‑09‑28).
#
# STEP – Výzkum a vývoj kritických technologií (OP TAK) měl uzávěrku
# 30. 9. 2026 a příjem skončil 11. 8. po převisu 300 % alokace. Databáze, která
# počítá stav jen z data, by ho sedm týdnů ukazovala jako otevřený. Opačný
# případ jsou výzvy „do vyčerpání alokace" a „podle pořadí podání": uzávěrka
# platí, ale čekat na ni je chyba.
#
# ⚠ NENÍ TO SKÓRE NALÉHAVOSTI. Odhad „vysoké riziko předčasného ukončení"
# by potřeboval čerpání alokace a počet žádostí, které zdroje nezveřejňují
# (naměřeno 2026‑09‑28: větu o předčasném konci mělo ve vytěžených datech
# 16 záznamů z 3 852). Pole nese jen to, co zdroj ŘEKL, a tu větu.
#
#   {"state": "closed", "on": "2026-08-11" | None, "note": "…", "planned": "2026-09-30" | None}
#       zdroj říká, že příjem UŽ skončil, a skončil dřív než uzávěrka;
#       `on` a `planned` jen tehdy, když věta uvádí den konce
#   {"state": "may", "on": None, "note": "…", "planned": None}
#       zdroj říká, že příjem může skončit před uzávěrkou
#
# ⚠ „Dočasně pozastaven pro online podání" konec příjmu NENÍ (Nadace AGROFERT
# bere dál poštou) a „posuzovány v pořadí podání" je pořadí hodnocení, ne
# konec; obojí by v katalogu tvrdilo víc, než zdroj řekl.
_CLOSED = re.compile(
    r"výzva\s+(byla\s+)?(předčasně\s+)?(ukončena|uzavřena)\b"
    r"|příjem\s+žádost\w*\s+(\S+\s+){0,4}?(předčasně\s+)?(ukončen|uzavřen)\b"
    # slovosled STEP 2026: „byl dne 11.8.2026 v 0:01 ukončen příjem žádostí“
    r"|\b(ukončen|uzavřen)\s+příjem\s+žádost"
    # NRB 2025: „Příjem žádostí byl k 15.9. 2025 z důvodu zarezervování celé
    # programové alokace pozastaven.“ Pozastavení KVŮLI ALOKACI je konec příjmu;
    # „dočasně pozastaven pro online podání“ bez důvodu v alokaci konec není.
    # (Mezi „žádostí“ a „z důvodu“ bývá datum s tečkami, proto `[^\n]`, ne `[^.]`.)
    r"|příjem\s+žádost\w*\s+[^\n]{0,60}?z\s+důvodu\s+(zarezervování|vyčerpání|naplnění|převisu)[^\n]{0,80}?(pozastaven|ukončen|uzavřen)"
    r"|(ukončen|uzavřen)\w*\s+(příjm\w+\s+žádost\w*\s+)?z\s+důvodu\s+(vyčerpání|převisu|dosažení)",
    re.I,
)
# „bude ukončen 30. 9." je obyčejná uzávěrka a „může být ukončen dříve" patří
# do `may`; ani jedno neříká, že příjem UŽ skončil.
_FUTURE = re.compile(r"\b(bude|budou|může|mohou|lze|by|bylo\s+by|nebude)\b", re.I)
_MAY = re.compile(
    r"do\s+vyčerpání\s+(\S+\s+){0,2}(alokace|prostředků|finančních)"
    r"|first\s+come,?\s+first\s+serve"
    r"|(ukončit|ukončen\w*|uzavř\w+)\s+(\S+\s+){0,5}(dříve|předčasně)"
    r"|(při|po)\s+(dosažení|překročení)\s+(\S+\s+){0,4}\d+\s*%\s+(\S+\s+){0,3}alokace",
    re.I,
)
_PARTIAL = re.compile(r"(méně\s+rozvinut|přechodov|více\s+rozvinut)\w*\s+region|pro\s+část\s+žadatel", re.I)
_MONTHS = {"ledna": 1, "února": 2, "března": 3, "dubna": 4, "května": 5, "června": 6, "července": 7,
           "srpna": 8, "září": 9, "října": 10, "listopadu": 11, "prosince": 12}
_DATE_NUM = re.compile(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)")
_DATE_WORD = re.compile(r"(\d{1,2})\.\s*(" + "|".join(_MONTHS) + r")\s+(20\d\d)", re.I)


def _texts(rec):
    """Věty ze zdroje, ve kterých se o konci příjmu mluví: titulek, zaměření,
    způsob podání a všechny řetězce v `extra` (lhůty, další data, kritéria)."""
    out = [rec.get(k) for k in ("title", "focus_area", "how_to_apply")]

    def walk(v):
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(rec.get("extra") or {})
    return [t for t in out if isinstance(t, str) and t.strip()]


# Konec věty je tečka před velkým písmenem, ne každá tečka: „dne 11. 8. 2026"
# by jinak větu uřízlo za dnem a datum by se ztratilo.
_SENT_END = re.compile(r"[.!?](?=\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ])|\n")


def _sentence(text, start, end):
    """Věta kolem nálezu, nejvýš 240 znaků."""
    a = 0
    for m in _SENT_END.finditer(text, 0, start):
        a = m.end()
    m = _SENT_END.search(text, end)
    b = m.end() if m else len(text)
    s = re.sub(r"\s+", " ", text[a:b]).strip()
    return s if len(s) <= 240 else s[:239].rstrip() + "…"


def _date_in(s):
    m = _DATE_NUM.search(s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = _DATE_WORD.search(s)
        if not m:
            return None
        d, mo, y = int(m.group(1)), _MONTHS[m.group(2).lower()], int(m.group(3))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return None
    return f"{y}-{mo:02d}-{d:02d}"


def early_close(rec):
    """Co zdroj říká o konci příjmu před uzávěrkou. Jinak None. Viz výš."""
    deadline = rec.get("deadline") if isinstance(rec.get("deadline"), str) and _ISO.match(rec.get("deadline")) else None
    seen = (rec.get("provenance") or {}).get("fetched_at") or rec.get("fetched_at")
    seen = seen[:10] if isinstance(seen, str) and _ISO.match(seen[:10]) else None
    texts = _texts(rec)

    for t in texts:
        for m in _CLOSED.finditer(t):
            if _FUTURE.search(t[max(0, m.start() - 30):m.end()]):
                continue
            note = _sentence(t, m.start(), m.end())
            # ⚠ KONEC PRO ČÁST ŽADATELŮ NENÍ KONEC VÝZVY. STEP – Investice 2026:
            # „Méně rozvinuté regiony: … byl dne 1.8.2026 ukončen příjem žádostí“,
            # přechodové regiony podávají dál do 15. 10. Posunout uzávěrku by
            # výzvu vzalo těm, pro které pořád běží; věta jde do „může skončit dřív“.
            if _PARTIAL.search(t[max(0, m.start() - 200):m.end()]):
                return {"state": "may", "on": None, "note": note, "planned": None}
            # ⚠ DEN KONCE JEN Z VĚTY, NIKDY ZE DNE ČTENÍ. Den čtení se posouvá
            # s každou obnovou; uzávěrka odvozená z něj by se každý týden
            # posunula a sledujícím by chodila falešná „změna lhůty"
            # (naměřeno při zavedení na Podpoře výsadby zeleně MSK).
            on = _date_in(note)
            # Konec v den uzávěrky nebo po ní je obyčejný konec, ne předčasný.
            if deadline and on and on >= deadline:
                return None
            # Uzávěrka prošla dřív, než jsme zdroj četli: věta o konci je
            # historie (Kotlíkové dotace LK: uzávěrka 2020, „ukončen 30. 4.
            # 2017"), o předčasném konci nic neříká.
            if deadline and seen and deadline < seen:
                return None
            # Bez data ve větě a bez dne čtení nejde poznat, jestli konec
            # přišel před uzávěrkou.
            if deadline and not on and not seen:
                return None
            open_from = rec.get("open_from") if isinstance(rec.get("open_from"), str) else None
            if on and open_from and _ISO.match(open_from) and on < open_from:
                return None
            return {"state": "closed", "on": on, "note": note, "planned": deadline if on else None}

    for t in texts:
        m = _MAY.search(t)
        if m:
            return {"state": "may", "on": None, "note": _sentence(t, m.start(), m.end()), "planned": None}
    return None


# ---------------------------------------------------------------- program_key
_YEAR = re.compile(r"\b(19|20)\d{2}(\s*[/–-]\s*(19|20)?\d{2})?\b")
_ROUND = re.compile(r"\b(\d+|[ivx]+)\.?\s*(kolo|výzva|vyzva|ročník|rocnik|etapa)\b", re.I)
_ORDINAL_PREFIX = re.compile(r"^\s*\d+\.\s*")
_NOISE = re.compile(r"\b(č|c|no|nr)\.?\s*\d+[a-z]?\b", re.I)


def normalize_title(title):
    s = unicodedata.normalize("NFKD", title or "").encode("ascii", "ignore").decode().lower()
    s = _ORDINAL_PREFIX.sub("", s)
    s = _YEAR.sub(" ", s)
    s = _ROUND.sub(" ", s)
    s = _NOISE.sub(" ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def program_key(rec):
    """Rodina záznamů téhož programu u téhož poskytovatele.

    Klíč = zdroj + titul bez ročníku, čísla kola a pořadového čísla. „Dotační
    program na podporu sportu 2025" a „… 2026" od téhož města jsou jeden
    program se dvěma ročníky; totéž jméno u dvou různých měst jsou dva
    programy (proto je ve klíči `source`).
    """
    base = normalize_title(rec.get("title"))
    if not base:
        return None
    blob = f"{rec.get('source') or ''}|{base}"
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------- field_provenance
# Pole, u kterých produkt ukazuje původ. Ne všechna — jen ta, podle kterých se
# člověk rozhoduje a která se dají doložit citací.
PROVENANCE_FIELDS = ("deadline", "open_from", "amount", "eligible_applicants", "focus_area",
                     "typ_zadatele", "oblast", "region")
# Jména polí, pod kterými vrstva 2 cituje totéž, co export nazývá jinak.
_CITATION_ALIASES = {
    "amount": ("amount", "vyse_hlavni_czk", "castky", "castky_strop", "castky_max"),
    "region": ("region", "region_kraj", "regions"),
}


def field_provenance(rec):
    """Pro každé sledované pole: `{"method": parsed|model|derived, "cited": bool}`.

    method
      parsed   — vrstva 1, deterministický parser nad strukturou zdroje
      model    — vrstva 2, jazykový model nad prózou / PDF
      derived  — dopočítáno z jiného údaje (odvozená lhůta z opakujícího se termínu)
    cited
      True, když k poli existuje doslovná citace, která se ve zdroji NAŠLA
      (`match` exact nebo fragment). Citace, kterou se nepodařilo dohledat,
      nedokládá nic.

    Pole, které záznam nemá, ve výsledku není — původ prázdna neexistuje.
    """
    prov = rec.get("provenance") or {}
    layer = prov.get("layer")
    base_method = "parsed" if layer == 1 else "model" if layer == 2 else None
    cited = set()
    for c in rec.get("citations") or []:
        if not isinstance(c, dict) or c.get("match") not in ("exact", "fragment"):
            continue
        cited.add(c.get("field"))
    f = rec.get("facets") or {}
    extra = rec.get("extra") or {}
    out = {}
    for field in PROVENANCE_FIELDS:
        if field in ("typ_zadatele", "oblast"):
            present = bool(f.get(field))
        elif field == "region":
            region = f.get("region") or {}
            present = bool(region.get("kraj") or region.get("obec") or region.get("celostatni"))
        else:
            present = rec.get(field) not in (None, "", [], {})
        if not present:
            continue
        method = base_method
        if field == "deadline" and (extra.get("deadline_derived_rule") or rec.get("status_confidence") == "derived"):
            method = "derived"
        if method is None:
            continue
        aliases = _CITATION_ALIASES.get(field, (field,))
        out[field] = {"method": method, "cited": any(a in cited for a in aliases)}
    return out


# ---------------------------------------------------------------- content ze `extra`
def call_number(rec):
    v = (rec.get("extra") or {}).get("cislo_vyzvy")
    if isinstance(v, str) and v.strip():
        return v.strip()[:80]
    return None


def contact(rec):
    """`{osoba, email, telefon}` nebo null. Bere první použitelný kontakt."""
    v = (rec.get("extra") or {}).get("kontakt")
    items = v if isinstance(v, list) else [v]
    for item in items:
        if not isinstance(item, dict):
            continue
        out = {k: (item.get(k).strip() if isinstance(item.get(k), str) and item.get(k).strip() else None)
               for k in ("osoba", "email", "telefon")}
        if any(out.values()):
            return out
    return None


_DOC_ROLES = ("pravidla_podminky", "vyzva", "formular", "vzor_smlouvy", "priloha", "metodika", "ostatni")


def documents(rec):
    """Dokumenty, které zdroj u výzvy jmenuje: `[{popis, role, url?}]`.

    Většina má jen popis (jméno souboru z listingu), url jen kde ho zdroj dal.
    Prázdný seznam se nepublikuje jako null, ale jako `[]` — „zdroj žádné
    nejmenuje" je informace.
    """
    v = (rec.get("extra") or {}).get("dokumenty")
    out = []
    if isinstance(v, list):
        for item in v:
            if not isinstance(item, dict):
                continue
            popis = item.get("popis")
            if not isinstance(popis, str) or not popis.strip():
                continue
            role = item.get("role") if item.get("role") in _DOC_ROLES else "ostatni"
            doc = {"popis": popis.strip()[:200], "role": role}
            url = item.get("url")
            if isinstance(url, str) and url.startswith("http"):
                doc["url"] = url
            out.append(doc)
    return out[:20]


def realization_period(rec):
    v = (rec.get("extra") or {}).get("obdobi_realizace")
    if isinstance(v, str) and v.strip():
        return v.strip()[:120]
    return None


def enrich(rec):
    """Všechna odvozená pole jednoho záznamu (bez `variant_of`, to chce celý katalog)."""
    return {
        "scope": scope(rec),
        "deadline_kind": deadline_kind(rec),
        "deadline_note": deadline_note(rec),
        "program_key": program_key(rec),
        "call_number": call_number(rec),
        "contact": contact(rec),
        "documents": documents(rec),
        "realization_period": realization_period(rec),
        "field_provenance": field_provenance(rec),
        "early_close": early_close(rec),
    }
