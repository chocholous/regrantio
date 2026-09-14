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
    }
