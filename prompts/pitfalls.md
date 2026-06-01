# Záludnosti (negativní pravidla) — vytěžené z reálných dat

Destilát z coverage workflow (typ+pole) + active-learning na odlišných doménách
(výzkum/půjčky/de-minimis/rolling). Vkládat do extrakčních promptů jako „NEPLEŤ si".
Plné seznamy: `platform_data/{field,type,divergent}_cov_result.json`.

## VRSTVA 1 — typové záměny (klasifikace base_type)
- **grant ↔ administrativa:** úřednědeskový obal (úřední deska, metadata MěÚ, „odbor ekonomiky") NEZNAMENÁ administrativa, když OBSAH je dotační program s žádostí/vyúčtováním. Rozhoduj podle obsahu, ne obalu.
- **grant ↔ mise_tema:** abstraktní název programu vypadá jako poslání — ale má-li datum příjmu + částku, je to grant. A naopak: stránka mise může zmínit konkrétní grant (11 000 Kč, uzávěrka) → to je grant, ne mise.
- **grant_open ↔ grant_closed:** TEXTOVĚ IDENTICKÉ (zvlášť dotacni.info) — rozlišuje JEN datum. → NEklasifikuj status, dopočítej ho z dat (viz fáze 5).
- **projekt_open ↔ projekt_done:** identická struktura — rozlišuje vyúčtovaná částka / signál dokončení. → status projektu taky dopočítej.
- **news ↔ administrativa:** usnesení rady = úřední zápis (administrativa), ne aktualita.
- **grant ↔ projekt:** „projekt byl podpořen částkou / ocenila zlatým rýčem" = PROJEKT (příjemce), ne výzva.

## VRSTVA 2 — pole grantu

### deadline (termín podání žádosti)
NENÍ to:
- „**termín realizace** / dokončení / ukončení stavebních prací / délka projektu 18 měsíců" — realizace, ne podání
- „**platnost: DATUM**" u dokumentů ke stažení (OPŽP/OPST tagují přílohy) — verze dokumentu, ne deadline
- „**vyhlášení výsledků** / zveřejněno dne / datum přidání / aktualizace" — publikace/výsledky
- „**ZoR / ŽoP** / termín podání žádosti o platbu" — reporting probíhajícího projektu
- „**počátek řešení** v roce / řešení začne v dubnu" — zahájení projektu (výzkum)
- „**lhůta pro rozhodnutí** / bez zbytečného odkladu" — lhůta ÚŘADU, ne žadatele
- „**konalo se / webinář / jednání komise** dne" — akce, ne deadline
- „**open_from**" — datum OTEVŘENÍ příjmu (≠ uzávěrka; je to párové pole)
- **prodloužení:** je-li v textu víc dat (původní + prodloužené) → vezmi POZDĚJŠÍ (aktuální)

### amount (výše/alokace výzvy)
NENÍ to:
- „výše **odvodu** za porušení rozpočtové kázně" — sankce
- „výše **půjčky** / snížení **jistiny úvěru** / **subvence úroků** / sazba % uhrazeného **pojistného**" — úvěrový/finanční nástroj, ne dotace (PGRLF/SFPI)
- „**požadovaná** výše dotace / celkové pořizovací náklady" — pole ŽADATELE ve formuláři, ne alokace
- „**projekt byl podpořen** částkou" — příjemce (projekt), ne alokace výzvy
- „**over CZK 3.5 billion** / celkem 3 mld." — objem VŠECH projektů/výzev, ne jedné výzvy
- „**správní poplatek** / poplatek žadatele" — poplatek
- „**minimální/maximální výše NENÍ stanovena**" — explicitní negace → NEvyplňuj 0/null naslepo, zaznamenej „nestanoveno"
- „% struktura zdrojů (50% EFRR + 50% národní)" — zdroje financování, ne výše pro žadatele
- vágní tiskové „60 mil. nachystáno / program měl by být vyhlášen" — neformální/budoucí, ne závazná alokace aktivní výzvy

### eligible_applicants (kdo může žádat)
NENÍ to:
- „**cílová skupina** (pro koho je projekt určen)" — koncoví příjemci služby, ne žadatel
- „typy **podporovaných aktivit/projektů**" — obsah projektu, ne kdo žádá
- „**hlavní uchazeči podpořených** návrhů / příjemce dotace" — výsledky/po schválení, ne způsobilost
- „**prostřednictvím krajů**" — administrace/průtok, ne výčet žadatelů
- „kontaktní osoba pro dotazy" — administrátor výzvy

### required_attachments (povinné přílohy žádosti)
NENÍ to:
- „**attachments / n_attachments=38**" v Kentico/IROP — soubory výzvy ke STAŽENÍ (pravidla, manuály), ne checklist příloh ŽÁDOSTI! (velmi pravděpodobná záměna)
- název přílohy výzvy ≠ seznam povinných příloh žadatele

### status
- **POČÍTEJ z dat, neklasifikuj z textu.** Agregátor (dotacni.info) status v textu nemá — odvoď z okna příjmu.
- „status_conf" (Kentico) = míra spolehlivosti detekce, ne status.
- deadline v minulosti bez slova „uzavřeno" = stejně closed (dopočítej).
- **rolling/kontinuální** výzvy („do vyčerpání alokace / průběžně") = open bez fixního deadline → status open, deadline=null/„průběžně".

### how_to_apply
- „kontakt na agregátor (neváhejte nás kontaktovat)" ≠ jak podat u poskytovatele
- „post-hodnoticí instrukce / ISKP21+ dokládání" ≠ prvotní podání žádosti
