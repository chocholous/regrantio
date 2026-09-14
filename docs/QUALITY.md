# Kvalita datové základny

Změřeno k **2026-09-14** skriptem `scripts/quality_report.py`. Čísla u živých záznamů (open · announced · unknown) jsou ta, která vidí uživatel; archiv je uvedený vedle.

## Rozsah

| | |
|---|---:|
| záznamů celkem | 3822 |
| z toho výzev | 3797 |
| **živých k dnešku** | **1971** |
| zdrojů | 135 |
| stav | open 739 · announced 308 · unknown 924 · closed 1826 |
| dosah živých | místní 473 · krajský 544 · celostátní 305 · mezinárodní 10 · EU centrální 639 |
| druh lhůty u živých | jedna lhůta 1043 · průběžně 72 · opakovaně 148 · neuvedeno 708 |

## Vyplněnost polí

| pole | živé | archiv |
|---|---:|---:|
| lhůta | 53.1 % (1047) | 75.7 % (2873) |
| částka pro žadatele | 7.9 % (156) | 20.5 % (778) |
| kdo smí žádat (text) | 75.2 % (1483) | 63.7 % (2418) |
| typ žadatele (faseta) | 30.3 % (597) | 34.0 % (1291) |
| oblast | 84.3 % (1662) | 89.5 % (3397) |
| území | 100.0 % (1971) | 100.0 % (3797) |
| jak podat | 81.3 % (1603) | 86.8 % (3297) |
| zdrojový dokument | 98.1 % (1934) | 97.9 % (3718) |
| kontakt | 12.2 % (241) | 14.8 % (561) |
| dokumenty | 13.8 % (272) | 17.5 % (665) |
| číslo výzvy | 45.0 % (886) | 47.9 % (1819) |

## Čerstvost živých záznamů

| ověřeno u zdroje | záznamů |
|---|---:|
| do 7 dnů | 256 |
| do 30 dnů | 724 |
| starší | 0 |
| nevíme (bez razítka) | 991 |

## Doložitelnost

Citací celkem 16972, ve zdroji dohledaných **7970 (47.0 %)**. Nedohledaná citace nedokládá nic; produkt u takového pole původ neukazuje jako doložený.

| pole (živé) | má hodnotu | parser | model | dopočet | doloženo citací |
|---|---:|---:|---:|---:|---:|
| amount | 156 | 18 | 138 | 0 | 71.2 % |
| deadline | 1047 | 30 | 1013 | 4 | 70.8 % |
| eligible_applicants | 1483 | 379 | 1104 | 0 | 14.5 % |
| focus_area | 1873 | 491 | 1382 | 0 | 16.6 % |
| oblast | 1662 | 220 | 1442 | 0 | 15.7 % |
| open_from | 1059 | 41 | 1018 | 0 | 4.8 % |
| region | 1971 | 527 | 1444 | 0 | 12.8 % |
| typ_zadatele | 597 | 149 | 448 | 0 | 12.2 % |

## Rodiny ročníků

313 programů má víc než jeden záznam; 257 z nich se vyhlašuje opakovaně (dva a víc ročníků); 344 starších ročníků nese `variant_of`.

## Zdroje

| stav | zdrojů | živých záznamů |
|---|---:|---:|
| ok (ověřeno do 21 dnů) | 30 | 1274 |
| stárne (nad 21 dnů) | 0 | 0 |
| má cestu, nikdy neověřeno | 66 | 569 |
| bez zapsané cesty k obnově | 37 | 104 |
| zmrazený | 2 | 24 |

| zdroj | typ | obnova | záznamů | živých | ověřeno | stav |
|---|---|---|---:|---:|---|---|
| Evropská komise (Funding & Tenders) (`eu_ft`) | evropska_komise | B | 684 | 639 | 2026-09-04 | ok |
| Kraj Vysočina (Fond Vysočiny) (`fondvysociny.cz`) | samosprava_kraj | A | 314 | 235 | 2026-09-09 | ok |
| Město Ústí nad Labem (`dotace.usti-nad-labem.cz`) | samosprava_obec | A | 72 | 71 |  | neovereno |
| IROP (MMR) (`irop.gov.cz`) | ministerstvo | A | 120 | 57 |  | neovereno |
| Liberecký kraj (`dotace.kraj-lbc.cz`) | samosprava_kraj | A | 135 | 49 | 2026-09-11 | ok |
| Město Hodonín (`hodonin.eu`) | samosprava_obec | A | 94 | 46 |  | neovereno |
| Ministerstvo zdravotnictví (`mzcr`) | ministerstvo | C | 83 | 42 |  | neovereno |
| Středočeský kraj (`stredoceskykraj.cz`) | samosprava_kraj | A | 92 | 40 | 2026-09-09 | ok |
| Hlavní město Praha (`praha.eu`) | samosprava_kraj | A | 37 | 36 | 2026-09-11 | ok |
| Město Brno (`dotace.brno.cz`) | samosprava_obec | A | 49 | 35 | 2026-09-11 | ok |
| Karlovarský kraj (`kr-karlovarsky.cz`) | samosprava_kraj | A | 86 | 27 | 2026-09-11 | ok |
| Moravskoslezský kraj (`msk.cz`) | samosprava_kraj | A | 104 | 27 | 2026-09-11 | ok |
| Královéhradecký kraj (`dotace.khk.cz`) | samosprava_kraj | A | 148 | 26 | 2026-09-11 | ok |
| Praha 3 (`dotace.praha3.cz`) | samosprava_obec | A | 26 | 25 |  | neovereno |
| Ústecký kraj (`kr-ustecky.cz`) | samosprava_kraj | A | 110 | 24 | 2026-09-11 | ok |
| Pardubický kraj (`dotace.pardubickykraj.cz`) | samosprava_kraj | A | 107 | 23 | 2026-09-11 | ok |
| Jihomoravský kraj (`kr-jihomoravsky.cz`) | samosprava_kraj | F | 34 | 21 |  | zmrazeny |
| Město Tábor (`taborcz.eu`) | samosprava_obec | A | 21 | 21 |  | neovereno |
| Obec Chýně (`dotace.chyne.cz`) | samosprava_obec | A | 21 | 20 |  | neovereno |
| Česko‑německý fond budoucnosti (`fondbudoucnosti`) | nadacni_fond | ? | 36 | 18 |  | bez_cesty |
| OPZ+ (MPSV) (`esfcr`) | ministerstvo | B | 234 | 17 | 2026-09-03 | ok |
| Město Mělník (`dotace.melnik.cz`) | samosprava_obec | A | 26 | 15 |  | neovereno |
| Ministerstvo kultury (`mkcr`) | ministerstvo | C | 29 | 15 |  | neovereno |
| Město Ostrava (`dotace.ostrava.cz`) | samosprava_obec | C | 20 | 14 |  | neovereno |
| Město Nové Město na Moravě (`dotace.nmnm.cz`) | samosprava_obec | A | 20 | 13 |  | neovereno |
| Nadace (OSF, Vodafone, Abakus, LPR, CLF) (`nadace_spa`) | nadace | B | 15 | 13 | 2026-09-03 | ok |
| Město Tišnov (`dotace.tisnov.cz`) | samosprava_obec | A | 13 | 12 |  | neovereno |
| OP Životní prostředí (SFŽP) (`opzp`) | ministerstvo | B | 107 | 12 | 2026-09-04 | ok |
| Brno‑Medlánky (`dotace.medlanky.cz`) | samosprava_obec | A | 12 | 11 |  | neovereno |
| Město Havířov (`havirov-city.cz`) | samosprava_obec | C | 11 | 11 |  | neovereno |
| Státní fond životního prostředí (`sfzp`) | statni_fond | T | 19 | 11 |  | bez_cesty |
| Město Chomutov (`granty.chomutov.cz`) | samosprava_obec | C | 11 | 10 |  | neovereno |
| Ministerstvo životního prostředí (`mzp`) | ministerstvo | T | 16 | 10 |  | bez_cesty |
| Jihočeský kraj (`kraj-jihocesky.cz`) | samosprava_kraj | A | 11 | 9 | 2026-09-11 | ok |
| Město Dobříš (`dotace.mestodobris.cz`) | samosprava_obec | A | 9 | 8 |  | neovereno |
| Ministerstvo školství, mládeže a tělovýchovy (`msmt`) | ministerstvo | B | 14 | 8 |  | neovereno |
| Město Přerov (`prerov.eu`) | samosprava_obec | C | 9 | 8 |  | neovereno |
| Město Hradec Králové (`dotace.mmhk.cz`) | samosprava_obec | A | 23 | 7 |  | neovereno |
| Město Police nad Metují (`dotace.policenm.cz`) | samosprava_obec | A | 9 | 7 |  | neovereno |
| Praha 11 (`dotace.praha11.cz`) | samosprava_obec | A | 9 | 7 |  | neovereno |
| Praha 14 (`dotace.praha14.cz`) | samosprava_obec | A | 9 | 7 |  | neovereno |
| Praha 2 (`dotace.praha2.cz`) | samosprava_obec | A | 8 | 7 |  | neovereno |
| Město Kladno (`mestokladno.cz`) | samosprava_obec | A | 7 | 7 |  | neovereno |
| Město Karlovy Vary (`mmkv.cz`) | samosprava_obec | C | 8 | 7 |  | neovereno |
| Ministerstvo průmyslu a obchodu (`mpo`) | ministerstvo | T | 9 | 7 |  | bez_cesty |
| Nadace Via (`nadacevia`) | nadace | B | 26 | 7 | 2026-09-03 | ok |
| Olomoucký kraj (`olkraj.cz`) | samosprava_kraj | A | 12 | 7 | 2026-09-11 | ok |
| OP Jan Amos Komenský (MŠMT) (`opjak`) | ministerstvo | B | 8 | 7 | 2026-09-04 | ok |
| Sociální nadační fond Praha (`socialninadacnifond`) | nadacni_fond | ? | 12 | 7 |  | bez_cesty |
| Zlínský kraj (`zlinskykraj.cz`) | samosprava_kraj | A | 13 | 7 | 2026-09-11 | ok |
| Praha 12 (`dotace.praha12.cz`) | samosprava_obec | A | 9 | 6 |  | neovereno |
| Ministerstvo zemědělství (`eagri`) | ministerstvo | T | 10 | 6 |  | bez_cesty |
| Visegrad Fund / ERSTE Foundation (`intl_funds`) | zahranicni_fond | B | 6 | 6 | 2026-09-03 | ok |
| Město Kroměříž (`kromeriz.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 10 | 6 |  | neovereno |
| Město Jablonec nad Nisou (`mestojablonec.cz`) | samosprava_obec | C | 14 | 6 |  | neovereno |
| Město Děčín (`mmdecin.cz`) | samosprava_obec | C | 13 | 6 |  | neovereno |
| Ministerstvo pro místní rozvoj (`mmr`) | ministerstvo | T | 9 | 6 |  | bez_cesty |
| Město Česká Lípa (`mucl.cz`) | samosprava_obec | A | 14 | 6 |  | neovereno |
| Nadace ČEZ (`nadacecez`) | firemni_nadace | C | 16 | 6 |  | neovereno |
| Nadace OKD (`nadaceokd`) | firemni_nadace | ? | 7 | 6 |  | bez_cesty |
| OP TAK (MPO) (`optak`) | ministerstvo | B | 17 | 6 | 2026-09-04 | ok |
| Město Bystřice (`dotace.mestobystrice.cz`) | samosprava_obec | A | 5 | 5 |  | neovereno |
| Dotace EU (MMR) (`dotaceeu.cz`) | ministerstvo | A | 13 | 5 |  | neovereno |
| Město Kolín (`mukolin.cz`) | samosprava_obec | A | 10 | 5 |  | neovereno |
| Město Olomouc (`olomouc.eu`) | samosprava_obec | C | 19 | 5 |  | neovereno |
| OP Doprava (MD) (`opd`) | ministerstvo | B | 12 | 5 | 2026-09-04 | ok |
| OP Spravedlivá transformace (MŽP) (`opst`) | ministerstvo | B | 101 | 5 | 2026-09-04 | ok |
| Městské obvody Ostravy (`plone_ostrava`) | samosprava_obec | B | 5 | 5 |  | neovereno |
| Město Třinec (`trinecko.cz`) | samosprava_obec | A | 6 | 5 |  | neovereno |
| Česká rozvojová agentura (`czechaid`) | statni_agentura | B | 9 | 4 | 2026-09-11 | ok |
| Hasičský záchranný sbor ČR (MV) (`hzs`) | ministerstvo | B | 4 | 4 |  | neovereno |
| Interreg (CZ‑PL, SK‑CZ) (`interreg`) | zahranicni_fond | B | 6 | 4 | 2026-09-03 | ok |
| Město Karviná (`karvina.cz`) | samosprava_obec | C | 15 | 4 |  | neovereno |
| Nadace Agrofert (`nadace-agrofert`) | firemni_nadace | ? | 7 | 4 |  | bez_cesty |
| Město Pardubice (`pardubice.eu`) | samosprava_obec | C | 12 | 4 |  | neovereno |
| Státní fond dopravní infrastruktury (`sfdi`) | statni_fond | T | 8 | 4 |  | bez_cesty |
| Výbor dobré vůle – Nadace Olgy Havlové (`vdv`) | nadace | ? | 5 | 4 |  | bez_cesty |
| Město Plzeň (`dotace.plzen.eu`) | samosprava_obec | C | 20 | 3 |  | neovereno |
| Obec Štěpánov (`dotace.stepanov.cz`) | samosprava_obec | A | 4 | 3 |  | neovereno |
| Město Hradec Králové (`hradeckralove.org`) | samosprava_obec | A | 4 | 3 |  | neovereno |
| Město Jihlava (`jihlava.cz`) | samosprava_obec | A | 11 | 3 |  | neovereno |
| Město Loket (`loket.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 6 | 3 |  | neovereno |
| Ministerstvo práce a sociálních věcí (`mpsv`) | ministerstvo | T | 11 | 3 |  | bez_cesty |
| Ministerstvo vnitra (`mv`) | ministerstvo | T | 7 | 3 |  | bez_cesty |
| Nadace Naše dítě (`nasedite`) | nadace | ? | 4 | 3 |  | bez_cesty |
| Pardubický kraj (`pardubickykraj.cz`) | samosprava_kraj | C | 4 | 3 |  | neovereno |
| Státní fond podpory investic (`sfpi`) | statni_fond | F | 6 | 3 |  | zmrazeny |
| Středočeský kraj (`stredoceskykraj.dsw2.otevrenamesta.cz`) | samosprava_kraj | A | 3 | 3 |  | neovereno |
| Grantová agentura ČR (`gacr`) | statni_agentura | T | 14 | 2 |  | bez_cesty |
| Město Liberec (`granty.liberec.cz`) | samosprava_obec | C | 7 | 2 |  | neovereno |
| Nadace The Kellner Family Foundation (`kellner`) | firemni_nadace | ? | 5 | 2 |  | bez_cesty |
| Město Krnov (`krnov.cz`) | samosprava_obec | A | 3 | 2 |  | neovereno |
| Ministerstvo kultury (`mk`) | ministerstvo | B | 53 | 2 | 2026-09-03 | ok |
| Nadace ADRA (`nadace_adra`) | nadace | T | 3 | 2 |  | bez_cesty |
| Město Ostrava (`ostrava.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 4 | 2 |  | neovereno |
| Státní fond audiovize (`sfa`) | statni_fond | T | 8 | 2 |  | bez_cesty |
| Město Teplice (`teplice.cz`) | samosprava_obec | A | 6 | 2 |  | neovereno |
| Plzeňský kraj (`dotace.plzensky-kraj.cz`) | samosprava_kraj | C | 20 | 1 |  | neovereno |
| Nadační fond pro rozvoj paliativní péče (`fondpaliativnipece`) | nadacni_fond | ? | 10 | 1 |  | bez_cesty |
| Město Frýdek‑Místek (`frydekmistek.cz`) | samosprava_obec | C | 10 | 1 |  | neovereno |
| Město Most (`mesto-most.cz`) | samosprava_obec | A | 10 | 1 |  | neovereno |
| Nadace Agrofert (`nadace-agrofert.cz`) | nadace | ? | 1 | 1 |  | bez_cesty |
| Nadace České spořitelny (`nadacecs`) | firemni_nadace | T | 2 | 1 |  | bez_cesty |
| Nadace Vodafone (`nadacevodafone.cz`) | nadace | ? | 1 | 1 |  | bez_cesty |
| Město Nové Město nad Metují (`novemestonm.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 1 | 1 |  | neovereno |
| Národní sportovní agentura (`nsa`) | statni_agentura | B | 21 | 1 | 2026-09-04 | ok |
| Praha 6 (`praha6.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 2 | 1 |  | neovereno |
| Město Sokolov (`sokolov.cz`) | samosprava_obec | A | 3 | 1 |  | neovereno |
| Technologická agentura ČR (`tacr`) | statni_agentura | B | 10 | 1 | 2026-09-04 | ok |
| Nadační fond Albert (`albert`) | firemni_nadace | T | 3 | 0 |  | bez_cesty |
| Praha 4 (`dotace.praha4.cz`) | samosprava_obec | A | 1 | 0 |  | neovereno |
| Praha 8 (`dotace.praha8.cz`) | samosprava_obec | A | 3 | 0 |  | neovereno |
| EHP a Norské fondy (`eeagrants`) | zahranicni_fond | B | 26 | 0 |  | neovereno |
| Nadání Josefa, Marie a Zdeňky Hlávkových (`hlavka`) | nadace | T | 4 | 0 |  | bez_cesty |
| Konto Bariéry (`kontobariery`) |  | ? | 1 | 0 |  | bez_cesty |
| Nadační fond Krása pomoci (`krasapomoci`) | nadacni_fond | ? | 2 | 0 |  | bez_cesty |
| Nadace Leontinka (`leontinka`) | nadace | T | 2 | 0 |  | bez_cesty |
| Praha 18 (Letňany) (`letnany.cz`) | samosprava_obec | A | 2 | 0 |  | neovereno |
| Praha‑Libuš (`libus.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 4 | 0 |  | neovereno |
| Město Mladá Boleslav (`mb-net.cz`) | samosprava_obec | A | 3 | 0 |  | neovereno |
| Město Litvínov (`mulitvinov.cz`) | samosprava_obec | A | 1 | 0 |  | neovereno |
| Nadace ČEZ (`nadacecez.cz`) | nadace | ? | 1 | 0 |  | bez_cesty |
| Nadace O2 (`nadaceo2.cz`) | nadace | ? | 1 | 0 |  | bez_cesty |
| Nadace táta a máma (`nadacetm`) |  | ? | 1 | 0 |  | bez_cesty |
| Nadace rozvoje občanské společnosti (`nros.cz`) | nadace | ? | 1 | 0 |  | bez_cesty |
| Město Opava (`opava-city.cz`) | samosprava_obec | C | 7 | 0 |  | neovereno |
| Nadace OSF (`osf`) |  | B | 1 | 0 | 2026-09-03 | ok |
| Nadace Partnerství (`partnerstvi`) |  | T | 1 | 0 |  | bez_cesty |
| Město Prostějov (`prostejov.eu`) | samosprava_obec | C | 3 | 0 |  | neovereno |
| Státní fond kultury (`sfk`) | statni_fond | T | 1 | 0 |  | bez_cesty |
| Nadace Sirius (`sirius`) |  | T | 1 | 0 |  | bez_cesty |
| Nadace Veronica (`veronica`) |  | T | 1 | 0 |  | bez_cesty |
| Vinařský fond (`vinarskyfond`) | statni_fond | T | 5 | 0 |  | bez_cesty |
| Úřad vlády ČR (`vlada`) | ministerstvo | B | 7 | 0 | 2026-09-03 | ok |
| Nadace Jakuba Voráčka (`voracek`) |  | ? | 1 | 0 |  | bez_cesty |

Třídy obnovy: A strukturní ingest · B vlastní parser · C model · T přepsaný extraktor (obnovu předstírá) · F zmrazený · ? bez zapsané cesty. Inventář: `data/sources.json`.
