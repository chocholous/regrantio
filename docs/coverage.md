# Coverage & active learning — jak VĚDĚT, že pokrýváme formulace polí (a na co pozor)

Řeší napětí: nepřemíňovat (ruční slovník synonym = nora) vs nepodcenit (neznáme všechny formulace).
**Pokrytí se MĚŘÍ, nehádá.** Self-terminating (stop na saturaci).

## Cyklus (měřený, ne nekonečný)
1. **Najdi nejodlišnější zdroje** — `scripts/diversity_finder.py` skenuje korpus na doménové markery
   (věda/výzkum, půjčky/fin.nástroje, de-minimis, rolling, voucher; EU/SK mimo scope) → nejodlišnější
   DOSUD NEVZORKOVANÉ zdroje. Cílit divergentní >> náhodné.
2. **Vytěž formulace + záludnosti** — `scripts/type_coverage_wf.js` (dvouvrstvě: typ + per-typ pole).
   Sonnet čte stratifikovaný vzorek reálných dokumentů, hlásí (a) formulace jak viděl pole/typ,
   (b) confusably. Orchestrátor měří **saturační křivku** (distinct kumulativně po dávkách).
3. **Diff proti minulému** — kolik NOVÝCH formulací/záludností přibylo = informační zisk.
4. **Stop, až zisk klesne** (saturace). Nové záludnosti → `prompts/pitfalls.md`.

## Co se naměřilo (2026-06-01)
- 1. běh (41 dok, 6 typů): 129 formulací + 97 záludností — **žádné pole nenasyceno** (křivky rostou).
- active-learning běh (39 DIVERGENTNÍCH dok): **+144 formulací / +101 záludností** (~zdvojnásobení)
  → zacílení na odlišné domény je řádově efektivnější než náhoda.
- Dvouvrstvý výsledek: TYP (signály+záměny) + POLE per typ. Klíč: STATUS = výpočet, ne klasifikace.

## Dvě vrstvy
- **Vrstva 1 (typ):** signály co identifikují typ + záměny mezi typy (úřednědeskový obal, abstraktní názvy).
- **Vrstva 2 (pole):** per typ jeho pole + formulace (recall) + záludnosti (precision).

## Proč to není nora
| Nora | Tady |
|---|---|
| ruční slepý slovník synonym | silný model čte reálná data |
| „kdy přestat?" neznámo | saturační křivka + diff = stop-signál |
| jen recall | obě strany (recall+precision) |
| neměřené | měřené proti ground-truth (dotacni.info/IROP) |

LLM už zná běžné formulace — cenná je jen **bounded sada záludností** (negativní pravidla) + definice
polí + pár few-shot. Ne exhaustivní synonyma.
