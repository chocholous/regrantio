# Kvalita datové základny

Změřeno k **2026-09-23** skriptem `scripts/quality_report.py`. Čísla u živých záznamů (open · announced · unknown) jsou ta, která vidí uživatel; archiv je uvedený vedle.

## Rozsah

| | |
|---|---:|
| záznamů celkem | 3852 |
| z toho výzev | 3827 |
| **živých k dnešku** | **1851** |
| zdrojů | 135 |
| stav | open 632 · announced 303 · unknown 916 · closed 1976 |
| dosah živých | místní 470 · krajský 548 · celostátní 301 · mezinárodní 10 · EU centrální 522 |
| druh lhůty u živých | jedna lhůta 931 · průběžně 72 · opakovaně 142 · neuvedeno 706 |

## Vyplněnost polí

| pole | živé | archiv |
|---|---:|---:|
| lhůta | 50.5 % (935) | 76.1 % (2911) |
| částka pro žadatele | 8.2 % (151) | 20.4 % (779) |
| kdo smí žádat (text) | 73.3 % (1357) | 63.6 % (2433) |
| typ žadatele (faseta) | 31.8 % (588) | 33.8 % (1295) |
| oblast | 83.0 % (1537) | 89.3 % (3417) |
| území | 100.0 % (1851) | 100.0 % (3827) |
| jak podat | 80.4 % (1488) | 86.9 % (3327) |
| zdrojový dokument | 98.0 % (1814) | 97.9 % (3748) |
| kontakt | 13.0 % (240) | 14.7 % (561) |
| dokumenty | 14.3 % (265) | 17.4 % (665) |
| číslo výzvy | 41.2 % (763) | 47.9 % (1832) |

## Čerstvost živých záznamů

| ověřeno u zdroje | záznamů |
|---|---:|
| do 7 dnů | 853 |
| do 30 dnů | 24 |
| starší | 0 |
| nevíme (bez razítka) | 974 |

## Doložitelnost

Citací celkem 17008, ve zdroji dohledaných **7998 (47.0 %)**. Nedohledaná citace nedokládá nic; produkt u takového pole původ neukazuje jako doložený.

| pole (živé) | má hodnotu | parser | model | dopočet | doloženo citací |
|---|---:|---:|---:|---:|---:|
| amount | 151 | 18 | 133 | 0 | 73.5 % |
| deadline | 935 | 46 | 885 | 4 | 66.6 % |
| eligible_applicants | 1357 | 379 | 978 | 0 | 15.8 % |
| focus_area | 1751 | 493 | 1258 | 0 | 17.8 % |
| oblast | 1537 | 220 | 1317 | 0 | 17.0 % |
| open_from | 946 | 56 | 890 | 0 | 5.3 % |
| region | 1851 | 532 | 1319 | 0 | 13.7 % |
| typ_zadatele | 588 | 149 | 439 | 0 | 12.4 % |

## Rodiny ročníků

315 programů má víc než jeden záznam; 258 z nich se vyhlašuje opakovaně (dva a víc ročníků); 349 starších ročníků nese `variant_of`.

## Zdroje

| stav | zdrojů | živých záznamů |
|---|---:|---:|
| ok (ověřeno do 21 dnů) | 31 | 1172 |
| stárne (nad 21 dnů) | 0 | 0 |
| má cestu, nikdy neověřeno | 81 | 594 |
| bez zapsané cesty k obnově | 20 | 61 |
| zmrazený | 3 | 24 |

| zdroj | typ | obnova | záznamů | živých | ověřeno | stav |
|---|---|---|---:|---:|---|---|
| Evropská komise (Funding & Tenders) (`eu_ft`) | evropska_komise | B | 696 | 522 | 2026-09-23 | ok |
| Kraj Vysočina (Fond Vysočiny) (`fondvysociny.cz`) | samosprava_kraj | A | 314 | 235 | 2026-09-23 | ok |
| Město Ústí nad Labem (`dotace.usti-nad-labem.cz`) | samosprava_obec | A | 72 | 71 |  | neovereno |
| IROP (MMR) (`irop.gov.cz`) | ministerstvo | A | 120 | 52 |  | neovereno |
| Liberecký kraj (`dotace.kraj-lbc.cz`) | samosprava_kraj | A | 137 | 49 | 2026-09-23 | ok |
| Město Hodonín (`hodonin.eu`) | samosprava_obec | A | 94 | 46 |  | neovereno |
| Středočeský kraj (`stredoceskykraj.cz`) | samosprava_kraj | A | 95 | 42 | 2026-09-23 | ok |
| Ministerstvo zdravotnictví (`mzcr`) | ministerstvo | C | 83 | 41 |  | neovereno |
| Město Brno (`dotace.brno.cz`) | samosprava_obec | A | 49 | 38 | 2026-09-23 | ok |
| Hlavní město Praha (`praha.eu`) | samosprava_kraj | A | 38 | 37 | 2026-09-23 | ok |
| Karlovarský kraj (`kr-karlovarsky.cz`) | samosprava_kraj | A | 86 | 28 | 2026-09-23 | ok |
| Moravskoslezský kraj (`msk.cz`) | samosprava_kraj | A | 105 | 28 | 2026-09-23 | ok |
| Královéhradecký kraj (`dotace.khk.cz`) | samosprava_kraj | A | 148 | 26 | 2026-09-23 | ok |
| Praha 3 (`dotace.praha3.cz`) | samosprava_obec | A | 26 | 25 |  | neovereno |
| Ústecký kraj (`kr-ustecky.cz`) | samosprava_kraj | A | 111 | 24 | 2026-09-23 | ok |
| Pardubický kraj (`dotace.pardubickykraj.cz`) | samosprava_kraj | A | 108 | 23 | 2026-09-23 | ok |
| Jihomoravský kraj (`kr-jihomoravsky.cz`) | samosprava_kraj | F | 34 | 21 |  | zmrazeny |
| Město Tábor (`taborcz.eu`) | samosprava_obec | A | 21 | 21 |  | neovereno |
| Obec Chýně (`dotace.chyne.cz`) | samosprava_obec | A | 21 | 20 |  | neovereno |
| Česko‑německý fond budoucnosti (`fondbudoucnosti`) | nadacni_fond | ? | 36 | 18 |  | bez_cesty |
| OPZ+ (MPSV) (`esfcr`) | ministerstvo | B | 234 | 16 | 2026-09-23 | ok |
| Město Mělník (`dotace.melnik.cz`) | samosprava_obec | A | 26 | 15 |  | neovereno |
| Ministerstvo kultury (`mkcr`) | ministerstvo | C | 29 | 15 |  | neovereno |
| Nadace (OSF, Vodafone, Abakus, LPR, CLF) (`nadace_spa`) | nadace | B | 16 | 14 | 2026-09-23 | ok |
| Město Nové Město na Moravě (`dotace.nmnm.cz`) | samosprava_obec | A | 20 | 13 |  | neovereno |
| Město Ostrava (`dotace.ostrava.cz`) | samosprava_obec | C | 20 | 12 |  | neovereno |
| Město Tišnov (`dotace.tisnov.cz`) | samosprava_obec | A | 13 | 12 |  | neovereno |
| OP Životní prostředí (SFŽP) (`opzp`) | ministerstvo | B | 107 | 12 | 2026-09-23 | ok |
| Brno‑Medlánky (`dotace.medlanky.cz`) | samosprava_obec | A | 12 | 11 |  | neovereno |
| Město Havířov (`havirov-city.cz`) | samosprava_obec | C | 11 | 11 |  | neovereno |
| Státní fond životního prostředí (`sfzp`) | statni_fond | C | 19 | 11 |  | neovereno |
| Město Chomutov (`granty.chomutov.cz`) | samosprava_obec | C | 11 | 10 |  | neovereno |
| Ministerstvo životního prostředí (`mzp`) | ministerstvo | T | 16 | 10 |  | bez_cesty |
| Město Dobříš (`dotace.mestodobris.cz`) | samosprava_obec | A | 9 | 8 |  | neovereno |
| Jihočeský kraj (`kraj-jihocesky.cz`) | samosprava_kraj | A | 11 | 8 | 2026-09-23 | ok |
| Ministerstvo školství, mládeže a tělovýchovy (`msmt`) | ministerstvo | B | 14 | 8 |  | neovereno |
| Zlínský kraj (`zlinskykraj.cz`) | samosprava_kraj | A | 14 | 8 | 2026-09-23 | ok |
| Město Hradec Králové (`dotace.mmhk.cz`) | samosprava_obec | A | 23 | 7 |  | neovereno |
| Město Police nad Metují (`dotace.policenm.cz`) | samosprava_obec | A | 9 | 7 |  | neovereno |
| Praha 11 (`dotace.praha11.cz`) | samosprava_obec | A | 9 | 7 |  | neovereno |
| Praha 14 (`dotace.praha14.cz`) | samosprava_obec | A | 9 | 7 |  | neovereno |
| Praha 2 (`dotace.praha2.cz`) | samosprava_obec | A | 8 | 7 |  | neovereno |
| Město Kladno (`mestokladno.cz`) | samosprava_obec | A | 7 | 7 |  | neovereno |
| Město Karlovy Vary (`mmkv.cz`) | samosprava_obec | C | 8 | 7 |  | neovereno |
| Ministerstvo průmyslu a obchodu (`mpo`) | ministerstvo | C | 9 | 7 |  | neovereno |
| Nadace Via (`nadacevia`) | nadace | B | 26 | 7 | 2026-09-23 | ok |
| OP Jan Amos Komenský (MŠMT) (`opjak`) | ministerstvo | B | 8 | 7 | 2026-09-23 | ok |
| Sociální nadační fond Praha (`socialninadacnifond`) | nadacni_fond | ? | 12 | 7 |  | bez_cesty |
| Česká rozvojová agentura (`czechaid`) | statni_agentura | B | 11 | 6 | 2026-09-23 | ok |
| Praha 12 (`dotace.praha12.cz`) | samosprava_obec | A | 9 | 6 |  | neovereno |
| Ministerstvo zemědělství (`eagri`) | ministerstvo | C | 10 | 6 |  | neovereno |
| Visegrad Fund / ERSTE Foundation (`intl_funds`) | zahranicni_fond | B | 6 | 6 | 2026-09-23 | ok |
| Město Kroměříž (`kromeriz.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 10 | 6 |  | neovereno |
| Město Jablonec nad Nisou (`mestojablonec.cz`) | samosprava_obec | C | 14 | 6 |  | neovereno |
| Město Děčín (`mmdecin.cz`) | samosprava_obec | C | 13 | 6 |  | neovereno |
| Ministerstvo pro místní rozvoj (`mmr`) | ministerstvo | C | 9 | 6 |  | neovereno |
| Město Česká Lípa (`mucl.cz`) | samosprava_obec | A | 14 | 6 |  | neovereno |
| Nadace ČEZ (`nadacecez`) | firemni_nadace | C | 16 | 6 |  | neovereno |
| Nadace OKD (`nadaceokd`) | firemni_nadace | ? | 7 | 6 |  | bez_cesty |
| Olomoucký kraj (`olkraj.cz`) | samosprava_kraj | A | 12 | 6 | 2026-09-23 | ok |
| Městské obvody Ostravy (`plone_ostrava`) | samosprava_obec | B | 9 | 6 | 2026-09-23 | ok |
| Město Bystřice (`dotace.mestobystrice.cz`) | samosprava_obec | A | 5 | 5 |  | neovereno |
| Dotace EU (MMR) (`dotaceeu.cz`) | ministerstvo | A | 13 | 5 |  | neovereno |
| Město Kolín (`mukolin.cz`) | samosprava_obec | A | 10 | 5 |  | neovereno |
| Město Olomouc (`olomouc.eu`) | samosprava_obec | C | 19 | 5 |  | neovereno |
| OP Doprava (MD) (`opd`) | ministerstvo | B | 12 | 5 | 2026-09-23 | ok |
| OP Spravedlivá transformace (MŽP) (`opst`) | ministerstvo | B | 101 | 5 | 2026-09-23 | ok |
| OP TAK (MPO) (`optak`) | ministerstvo | B | 17 | 5 | 2026-09-23 | ok |
| Město Třinec (`trinecko.cz`) | samosprava_obec | A | 6 | 5 |  | neovereno |
| Hasičský záchranný sbor ČR (MV) (`hzs`) | ministerstvo | B | 4 | 4 |  | neovereno |
| Interreg (CZ‑PL, SK‑CZ) (`interreg`) | zahranicni_fond | B | 6 | 4 | 2026-09-23 | ok |
| Nadace Agrofert (`nadace-agrofert`) | firemni_nadace | ? | 7 | 4 |  | bez_cesty |
| Město Pardubice (`pardubice.eu`) | samosprava_obec | C | 12 | 4 |  | neovereno |
| Město Přerov (`prerov.eu`) | samosprava_obec | C | 9 | 4 |  | neovereno |
| Státní fond dopravní infrastruktury (`sfdi`) | statni_fond | C | 8 | 4 |  | neovereno |
| Výbor dobré vůle – Nadace Olgy Havlové (`vdv`) | nadace | ? | 5 | 4 |  | bez_cesty |
| Město Plzeň (`dotace.plzen.eu`) | samosprava_obec | C | 20 | 3 |  | neovereno |
| Obec Štěpánov (`dotace.stepanov.cz`) | samosprava_obec | A | 4 | 3 |  | neovereno |
| Město Hradec Králové (`hradeckralove.org`) | samosprava_obec | A | 4 | 3 |  | neovereno |
| Město Jihlava (`jihlava.cz`) | samosprava_obec | A | 11 | 3 |  | neovereno |
| Město Karviná (`karvina.cz`) | samosprava_obec | C | 15 | 3 |  | neovereno |
| Město Loket (`loket.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 6 | 3 |  | neovereno |
| Ministerstvo práce a sociálních věcí (`mpsv`) | ministerstvo | C | 11 | 3 |  | neovereno |
| Ministerstvo vnitra (`mv`) | ministerstvo | T | 7 | 3 |  | bez_cesty |
| Nadace Naše dítě (`nasedite`) | nadace | ? | 4 | 3 |  | bez_cesty |
| Pardubický kraj (`pardubickykraj.cz`) | samosprava_kraj | C | 4 | 3 |  | neovereno |
| Státní fond podpory investic (`sfpi`) | statni_fond | F | 6 | 3 |  | zmrazeny |
| Středočeský kraj (`stredoceskykraj.dsw2.otevrenamesta.cz`) | samosprava_kraj | A | 3 | 3 |  | neovereno |
| Grantová agentura ČR (`gacr`) | statni_agentura | C | 14 | 2 |  | neovereno |
| Město Liberec (`granty.liberec.cz`) | samosprava_obec | C | 7 | 2 |  | neovereno |
| Nadace The Kellner Family Foundation (`kellner`) | firemni_nadace | ? | 5 | 2 |  | bez_cesty |
| Město Krnov (`krnov.cz`) | samosprava_obec | A | 3 | 2 |  | neovereno |
| Ministerstvo kultury (`mk`) | ministerstvo | B | 53 | 2 | 2026-09-23 | ok |
| Nadace ADRA (`nadace_adra`) | nadace | C | 3 | 2 |  | neovereno |
| Město Ostrava (`ostrava.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 4 | 2 |  | neovereno |
| Státní fond audiovize (`sfa`) | statni_fond | C | 8 | 2 |  | neovereno |
| Technologická agentura ČR (`tacr`) | statni_agentura | B | 11 | 2 | 2026-09-23 | ok |
| Město Teplice (`teplice.cz`) | samosprava_obec | A | 6 | 2 |  | neovereno |
| Plzeňský kraj (`dotace.plzensky-kraj.cz`) | samosprava_kraj | C | 20 | 1 |  | neovereno |
| Nadační fond pro rozvoj paliativní péče (`fondpaliativnipece`) | nadacni_fond | ? | 10 | 1 |  | bez_cesty |
| Město Frýdek‑Místek (`frydekmistek.cz`) | samosprava_obec | C | 10 | 1 |  | neovereno |
| Město Most (`mesto-most.cz`) | samosprava_obec | A | 10 | 1 |  | neovereno |
| Nadace Agrofert (`nadace-agrofert.cz`) | nadace | ? | 1 | 1 |  | bez_cesty |
| Nadace České spořitelny (`nadacecs`) | firemni_nadace | T | 2 | 1 |  | bez_cesty |
| Nadace Vodafone (`nadacevodafone.cz`) | nadace | ? | 1 | 1 |  | bez_cesty |
| Město Nové Město nad Metují (`novemestonm.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 1 | 1 |  | neovereno |
| Národní sportovní agentura (`nsa`) | statni_agentura | B | 21 | 1 | 2026-09-23 | ok |
| Praha 6 (`praha6.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 2 | 1 |  | neovereno |
| Město Sokolov (`sokolov.cz`) | samosprava_obec | A | 3 | 1 |  | neovereno |
| Nadační fond Albert (`albert`) | firemni_nadace | C | 3 | 0 |  | neovereno |
| Praha 4 (`dotace.praha4.cz`) | samosprava_obec | A | 1 | 0 |  | neovereno |
| Praha 8 (`dotace.praha8.cz`) | samosprava_obec | A | 3 | 0 |  | neovereno |
| EHP a Norské fondy (`eeagrants`) | zahranicni_fond | F | 26 | 0 |  | zmrazeny |
| Nadání Josefa, Marie a Zdeňky Hlávkových (`hlavka`) | nadace | C | 4 | 0 |  | neovereno |
| Konto Bariéry (`kontobariery`) |  | ? | 1 | 0 |  | bez_cesty |
| Nadační fond Krása pomoci (`krasapomoci`) | nadacni_fond | ? | 2 | 0 |  | bez_cesty |
| Nadace Leontinka (`leontinka`) | nadace | C | 2 | 0 |  | neovereno |
| Praha 18 (Letňany) (`letnany.cz`) | samosprava_obec | A | 2 | 0 |  | neovereno |
| Praha‑Libuš (`libus.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 4 | 0 |  | neovereno |
| Město Mladá Boleslav (`mb-net.cz`) | samosprava_obec | A | 3 | 0 |  | neovereno |
| Město Litvínov (`mulitvinov.cz`) | samosprava_obec | A | 1 | 0 |  | neovereno |
| Nadace ČEZ (`nadacecez.cz`) | nadace | ? | 1 | 0 |  | bez_cesty |
| Nadace O2 (`nadaceo2.cz`) | nadace | ? | 1 | 0 |  | bez_cesty |
| Nadace táta a máma (`nadacetm`) |  | ? | 1 | 0 |  | bez_cesty |
| Nadace rozvoje občanské společnosti (`nros.cz`) | nadace | ? | 1 | 0 |  | bez_cesty |
| Město Opava (`opava-city.cz`) | samosprava_obec | C | 7 | 0 |  | neovereno |
| Nadace OSF (`osf`) |  | B | 1 | 0 | 2026-09-23 | ok |
| Nadace Partnerství (`partnerstvi`) |  | C | 1 | 0 |  | neovereno |
| Město Prostějov (`prostejov.eu`) | samosprava_obec | C | 3 | 0 |  | neovereno |
| Státní fond kultury (`sfk`) | statni_fond | C | 1 | 0 |  | neovereno |
| Nadace Sirius (`sirius`) |  | C | 1 | 0 |  | neovereno |
| Nadace Veronica (`veronica`) |  | C | 1 | 0 |  | neovereno |
| Vinařský fond (`vinarskyfond`) | statni_fond | C | 5 | 0 |  | neovereno |
| Úřad vlády ČR (`vlada`) | ministerstvo | B | 7 | 0 | 2026-09-23 | ok |
| Nadace Jakuba Voráčka (`voracek`) |  | ? | 1 | 0 |  | bez_cesty |

Třídy obnovy: A strukturní ingest · B vlastní parser · C model · T přepsaný extraktor (obnovu předstírá) · F zmrazený · ? bez zapsané cesty. Inventář: `data/sources.json`.
