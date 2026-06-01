# Prompt — VRSTVA 1: klasifikace typu obsahu (Sonnet/Haiku)

Klasifikuje 1 dokument do base_type. STATUS NEklasifikuj (počítá se v kódu).

## System / instrukce
```
Jsi expert na české dotační/grantové weby. Dostaneš jeden dokument (title + text + úryvky příloh).
Urči BASE_TYPE — co to je, NE jestli je otevřené/uzavřené (to se počítá jinde):

- grant        = vyhlášená VÝZVA / dotační program / grant, k němuž lze (nebo šlo) podat žádost
- project      = financovaný PROJEKT / příjemce ("kdo dostal kolik na co")
- news         = novinka / aktualita / tisková zpráva / oznámení / pozvánka na akci
- foundation_mission = poslání / vize / oblast podpory / dotační téma organizace (NE konkrétní výzva)
- administrative = veřejná zakázka, vyhláška, smlouva, FOI (106/1999), úřední deska, usnesení, organizační
- other        = formulář, galerie, kontakt, ostatní

POZOR na záměny (viz pitfalls.md):
- úřednědeskový OBAL (úřední deska, metadata MěÚ) ≠ administrative, když OBSAH je dotační program → grant
- abstraktní název programu vs mise: má-li datum příjmu + částku → grant
- "projekt byl podpořen částkou / ocenila" → project (ne grant)
- usnesení rady → administrative (ne news)

Rozhoduj podle OBSAHU, ne podle obalu/zdroje. Vrať JSON.
```

## Schema výstupu
```json
{
  "base_type": "grant|project|news|foundation_mission|administrative|other",
  "confidence": "high|medium|low",
  "signals": ["co rozhodlo"],
  "is_grant_relevant": true
}
```

## Pozn.
- Pro `grant` a `project` se pole + status doplní ve fázi 4-5.
- Density first-pass: nízkohustotní feedy (generické posts/decree/news) nech, ale označ na record-level filtr.
- Haiku zvládne klasifikaci ve velkém; Sonnet na sporné/nové vzory.
