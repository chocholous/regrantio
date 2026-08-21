# Archiv: plán přepisu pipeline do TypeScriptu

> **Nic z toho není implementované a podle ničeho z toho se dnes neřídíme.**
> Je to archiv, ne zadání.

## Co to je

Čtrnáct dokumentů z doby, kdy se uvažovalo o přepsání téhle pipeline z Pythonu
do TypeScriptu nad Claude Agent SDK — orchestrátor jako agent, třináct
sub‑agentů, CLI `grantio scout <zdroj>`, kvalitativní brány a workspace UI.

Součástí je i `knowledge-summary.md`, což je jediný dokument, který má cenu
i dnes: shrnutí 67 odpovědí o tom, **jak se ten Python prototyp choval** —
kolik zdrojů jede přes HTTP a kolik přes Playwright, jaké transformace
existují, kolik stojí extrakce jednoho zdroje. To jsou naměřená čísla
o skutečném provozu, ne plán.

## Proč to leží tady, a ne v repozitáři produktu

Do 2026‑08‑21 tyhle soubory ležely ve složce `migrate/` v repozitáři
[the-machine-app](https://github.com/chocholous/the-machine-app), tedy
v repozitáři **SaaS produktu**. Popisují ale přestavbu **datové pipeline** —
tedy tenhle projekt. Kdo je tam našel, musel z názvu složky usoudit, že jde
o migraci aplikace, a mýlil se.

Přesunuty sem, protože pokud se k té úvaze někdy někdo vrátí, vrátí se k ní
tady.

## Co z toho platí

| | |
|---|---|
| Rozhodnutí o architektuře | **neplatí** — pipeline zůstává v Pythonu, bez frameworku |
| Čísla o Python prototypu (`knowledge-summary.md`) | **historicky platná**, stav k době extrakce |
| CLI `grantio …`, sub‑agenti, gates, workspace UI | **neexistuje** |
| Hranice regrantio ↔ Grantio | popsaná jinde a **jinak** — dnes platí [`EXPORT.md`](../../EXPORT.md) |
