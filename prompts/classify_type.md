# Prompt — VRSTVA 1: klasifikace base_type (Haiku/Sonnet)

Logika je **kaskáda, jak by to rozlišil člověk**: jedna kotevní otázka („jsou tu konkrétní peníze pro žadatele?")
+ vodopád podle toho, CO dokument dělá. Rozhoduje **obsah a funkce těla**, ne titulek/formát.
Status (otevřeno/uzavřeno) NEklasifikuj — počítá kód. **Grant = výzva i projekt** (tentýž tok peněz, dvě strany).

## System prompt
```
Urči base_type dokumentu (Read JSON: title, body, web) podle toho, CO dokument DĚLÁ — z PRIMÁRNÍHO obsahu TĚLA, ne z titulku, obalu, sidebaru ani formátu. Status (otevřeno/uzavřeno) NEřeš, počítá kód.

KOTVA — jsou v dokumentu konkrétní peníze pro žadatele? Ať NABÍDKA (budeš moct / můžeš / mohl jsi požádat) nebo UDĚLENÍ („komu kolik dali") → grant.
  Patří sem: výzva i financovaný projekt; průběžný program s pravidly, na který lze žádat (pravidla = popis té nabídky); výsledková listina / tabulka příjemců s částkami / „schválení dotací se jmény".

Když konkrétní peníze pro žadatele NEJSOU, rozliš podle funkce:
- foundation_mission = popisuje, ČEMU se organizace věnuje / co obecně podporuje, bez konkrétní nabídky i příjemce. (I sbírka DARŮ pro nadaci — peníze tečou K nadaci, ne k žadateli.)
- news = VYPRÁVÍ o události / výsledku: příběh, tisková zpráva, pozvánka na akci, ocenění osoby, souhrn výsledků BEZ konkrétních příjemců a částek.
- administrative = ŘÍDÍ proces, sám peníze nenabízí: metodika, pokyny, vyúčtování, monitorovací/závěrečná zpráva, usnesení bez seznamu příjemců.
- other = kontakt, formulář, galerie, nábor pracovní pozice, přihláška na akci, NEBO prázdné tělo / čistá navigace bez obsahu.

KDE SE TO PLETE:
- grant × administrative: nabízí/uděluje peníze (grant) × jen popisuje JAK proces běží (admin). Pravidla PROGRAMU, na který lze žádat = grant; pravidla vyúčtování/realizace = admin.
- grant × news: konkrétní příjemci + částky = grant × narativ / souhrn bez nich = news.
- foundation_mission × news: trvalý stav „podporujeme…" = mission × jednorázová událost „stalo se / získal" = news.
- grant × other: financování VLASTNÍ aktivity žadatele = grant (i stipendium na vlastní studium) × placená pozice / přihláška na akci = other.

Když nic nesedí jednoznačně → nejbližší + confidence=low. Vrať base_type, confidence a reasoning (body, podle čeho ses rozhodl).
```

## Schema
```json
{ "base_type": "grant|news|foundation_mission|administrative|other",
  "confidence": "high|medium|low",
  "reasoning": ["body, podle čeho ses rozhodl"] }
```
