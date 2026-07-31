#!/usr/bin/env python3
"""czech.py — KANONICKÉ parsování českých textů pro harvestery a extraktory.

PROČ EXISTUJE: audit 2026-07-31 napočítal **38 vlastních kopií** funkce „české datum → ISO"
napříč skripty, z toho **24 bez validace rozsahu** (uměly vyrobit 2026-13-45). Dataset je
sice čistý, protože to zachytí sanitizace ve `fix_dataset.py`, ale to je záchranná síť —
datum se tam ZAHODÍ, místo aby se správně přečetlo. Tenhle modul je jedno správné místo.

POUŽÍVEJ V NOVÉM KÓDU. Staré harvestery se migrují oportunisticky (fungují, jen si nesou
vlastní kopii) — nikdy ne plošným přepisem, který by rozbil ověřené parsery.

Funkce:
    cz_date_to_iso("15. 11. 2026")     → "2026-11-15"   (validuje rozsah i existenci dne)
    cz_date_to_iso("31. ledna 2027")   → "2027-01-31"   (slovní měsíce vč. bez diakritiky)
    strip_tags("<p>a<br>b</p>")        → "a\\nb"          (odstraní i <script>/<style>)
    sentence_at(text, pos)             → věta kolem pozice (pro doslovné citace/evidence)

Pasti, které modul řeší (viz REMAINING „Stálé pasti"):
  • české datum má TEČKY → nikdy nepoužívat `[^.]` v regexu kolem něj
  • „31. 2." neexistuje → musí vrátit None, ne fiktivní datum
  • dvojciferné roky se NEDOPLŇUJÍ (2 26 by dalo nesmysl)
"""
import html as _html
import re
from datetime import date

MONTHS = {
    "ledna": 1, "leden": 1, "února": 2, "unora": 2, "únor": 2, "unor": 2,
    "března": 3, "brezna": 3, "březen": 3, "brezen": 3, "dubna": 4, "duben": 4,
    "května": 5, "kvetna": 5, "květen": 5, "kveten": 5, "června": 6, "cervna": 6,
    "červen": 6, "cerven": 6, "července": 7, "cervence": 7, "červenec": 7, "cervenec": 7,
    "srpna": 8, "srpen": 8, "září": 9, "zari": 9, "října": 10, "rijna": 10, "říjen": 10,
    "rijen": 10, "listopadu": 11, "listopad": 11, "prosince": 12, "prosinec": 12,
}
_MN = "|".join(sorted(MONTHS, key=len, reverse=True))

# „15. 11. 2026", „15.11.2026", „1. 3. 2026 (od 15.00)"
_NUM = re.compile(r"(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(20\d\d)")
# „31. ledna 2027", „15. listopadu 2026"
_WORD = re.compile(r"(\d{1,2})\s*\.\s*(" + _MN + r")\s+(20\d\d)", re.I)

_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
_BREAK = re.compile(r"<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>", re.I)


def _mk(day, month, year):
    """Sestav ISO datum jen když REÁLNĚ existuje (31. 2. → None)."""
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except (ValueError, TypeError):
        return None


def cz_date_to_iso(text, first=True):
    """První (nebo poslední) české datum v textu → 'YYYY-MM-DD', jinak None.

    Rozumí číselnému i slovnímu zápisu měsíce. Neexistující datum vrací None —
    NIKDY nevymýšlí náhradu.
    """
    if not text:
        return None
    s = str(text)
    found = []
    for m in _NUM.finditer(s):
        iso = _mk(m.group(1), m.group(2), m.group(3))
        if iso:
            found.append(iso)
    for m in _WORD.finditer(s):
        iso = _mk(m.group(1), MONTHS[m.group(2).lower()], m.group(3))
        if iso:
            found.append(iso)
    if not found:
        return None
    return found[0] if first else found[-1]


def cz_dates_all(text):
    """Všechna platná data v textu, seřazená (pro výběr nejbližšího/nejzazšího termínu)."""
    if not text:
        return []
    s = str(text)
    out = {iso for m in _NUM.finditer(s) if (iso := _mk(m.group(1), m.group(2), m.group(3)))}
    out |= {iso for m in _WORD.finditer(s)
            if (iso := _mk(m.group(1), MONTHS[m.group(2).lower()], m.group(3)))}
    return sorted(out)


def strip_tags(markup):
    """HTML → čitelný text. Blokové tagy dělají nový řádek, <script>/<style> mizí celé."""
    if not markup:
        return ""
    s = _SCRIPT.sub(" ", str(markup))
    s = _BREAK.sub("\n", s)
    s = _TAG.sub(" ", s)
    s = _html.unescape(s)
    s = re.sub(r"[ \t\xa0]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)          # bez tohohle zůstane po zalomení mezera („\n druhá")
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def sentence_at(text, pos, before=200, after=120, limit=280):
    """Věta kolem pozice — pro `evidence` (doslovná citace ze zdroje)."""
    if not text:
        return None
    start = max(0, text.rfind("\n", 0, pos), text.rfind(". ", max(0, pos - before), pos))
    seg = text[start:pos + after]
    return re.sub(r"\s+", " ", seg).strip(" .;\n")[:limit] or None
