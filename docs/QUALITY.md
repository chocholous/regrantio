# Kvalita datové základny

Změřeno k **2026-11-24** skriptem `scripts/quality_report.py`. Čísla u živých záznamů (open · announced · unknown) jsou ta, která vidí uživatel; archiv je uvedený vedle.

## Rozsah

| | |
|---|---:|
| záznamů celkem | 4579 |
| z toho výzev | 4554 |
| **živých k dnešku** | **1925** |
| zdrojů | 136 |
| stav | open 606 · announced 321 · unknown 998 · closed 2629 |
| dosah živých | místní 514 · krajský 635 · celostátní 317 · mezinárodní 10 · EU centrální 449 |
| druh lhůty u živých | jedna lhůta 904 · průběžně 62 · opakovaně 176 · neuvedeno 783 |

## Vyplněnost polí

| pole | živé | archiv |
|---|---:|---:|
| lhůta | 48.2 % (927) | 78.1 % (3556) |
| částka pro žadatele | 4.8 % (93) | 9.3 % (422) |
| kdo smí žádat (text) | 65.9 % (1269) | 61.9 % (2820) |
| typ žadatele (faseta) | 40.8 % (785) | 39.4 % (1796) |
| oblast | 69.1 % (1330) | 83.0 % (3779) |
| území | 97.8 % (1883) | 98.8 % (4498) |
| jak podat | 82.6 % (1591) | 90.9 % (4138) |
| zdrojový dokument | 83.2 % (1601) | 88.1 % (4010) |
| kontakt | 11.3 % (217) | 13.4 % (611) |
| dokumenty | 20.6 % (396) | 30.5 % (1388) |
| číslo výzvy | 36.8 % (709) | 43.9 % (2000) |

## Čerstvost živých záznamů

| ověřeno u zdroje | záznamů |
|---|---:|
| do 7 dnů | 1479 |
| do 30 dnů | 5 |
| starší | 26 |
| nevíme (bez razítka) | 415 |

## Doložitelnost

Citací celkem 18176, ve zdroji dohledaných **9744 (53.6 %)**. Nedohledaná citace nedokládá nic; produkt u takového pole původ neukazuje jako doložený.

| pole (živé) | má hodnotu | parser | model | dopočet | doloženo citací |
|---|---:|---:|---:|---:|---:|
| amount | 93 | 25 | 68 | 0 | 58.1 % |
| deadline | 927 | 153 | 767 | 7 | 64.3 % |
| eligible_applicants | 1269 | 411 | 858 | 0 | 17.0 % |
| focus_area | 1810 | 702 | 1108 | 0 | 16.5 % |
| oblast | 1330 | 184 | 1146 | 0 | 17.1 % |
| open_from | 939 | 174 | 765 | 0 | 6.3 % |
| region | 1883 | 774 | 1109 | 0 | 12.2 % |
| typ_zadatele | 785 | 395 | 390 | 0 | 8.4 % |

## Rodiny ročníků

458 programů má víc než jeden záznam; 408 z nich se vyhlašuje opakovaně (dva a víc ročníků); 520 starších ročníků nese `variant_of`.

## Zdroje

| stav | zdrojů | živých záznamů |
|---|---:|---:|
| ok (ověřeno do 21 dnů) | 123 | 1858 |
| stárne (nad 21 dnů) | 1 | 2 |
| má cestu, nikdy neověřeno | 7 | 62 |
| bez zapsané cesty k obnově | 3 | 0 |
| zmrazený | 2 | 3 |

| zdroj | typ | obnova | záznamů | živých | ověřeno | stav |
|---|---|---|---:|---:|---|---|
| Evropská komise (Funding & Tenders) (`eu_ft`) | evropska_komise | B | 810 | 449 | 2026-11-24 | ok |
| Kraj Vysočina (Fond Vysočiny) (`fondvysociny.cz`) | samosprava_kraj | A | 333 | 251 | 2026-11-23 | ok |
| Královéhradecký kraj (`dotace.khk.cz`) | samosprava_kraj | A | 208 | 85 | 2026-11-23 | ok |
| Město Ústí nad Labem (`dotace.usti-nad-labem.cz`) | samosprava_obec | A | 90 | 80 | 2026-11-24 | ok |
| IROP (MMR) (`irop.gov.cz`) | ministerstvo | A | 120 | 55 | 2026-11-23 | ok |
| Středočeský kraj (`stredoceskykraj.cz`) | samosprava_kraj | A | 99 | 44 | 2026-11-24 | ok |
| Liberecký kraj (`dotace.kraj-lbc.cz`) | samosprava_kraj | A | 139 | 43 | 2026-11-24 | ok |
| Ministerstvo zdravotnictví (`mzcr`) | ministerstvo | C | 83 | 40 |  | neovereno |
| Hlavní město Praha (`praha.eu`) | samosprava_kraj | A | 40 | 39 | 2026-11-24 | ok |
| Město Ostrava (`dotace.ostrava.cz`) | samosprava_obec | A | 46 | 34 | 2026-11-23 | ok |
| Praha 3 (`dotace.praha3.cz`) | samosprava_obec | A | 35 | 33 | 2026-11-24 | ok |
| Jihočeský kraj (`kraj-jihocesky.cz`) | samosprava_kraj | A | 37 | 29 | 2026-11-23 | ok |
| Místní akční skupina (`mas`) | mistni_akcni_skupina | C | 38 | 28 | 2026-11-24 | ok |
| Moravskoslezský kraj (`msk.cz`) | samosprava_kraj | A | 111 | 28 | 2026-11-24 | ok |
| Obec Chýně (`dotace.chyne.cz`) | samosprava_obec | A | 27 | 25 | 2026-11-24 | ok |
| Karlovarský kraj (`kr-karlovarsky.cz`) | samosprava_kraj | A | 89 | 25 | 2026-11-24 | ok |
| Město Tábor (`taborcz.eu`) | samosprava_obec | A | 21 | 21 | 2026-11-17 | ok |
| Město Hodonín (`hodonin.eu`) | samosprava_obec | A | 105 | 20 | 2026-11-17 | ok |
| Ústecký kraj (`kr-ustecky.cz`) | samosprava_kraj | A | 115 | 20 | 2026-11-23 | ok |
| Ministerstvo školství, mládeže a tělovýchovy (`msmt`) | ministerstvo | B | 32 | 19 | 2026-11-24 | ok |
| Město Brno (`dotace.brno.cz`) | samosprava_obec | A | 52 | 17 | 2026-11-24 | ok |
| Město Hradec Králové (`dotace.mmhk.cz`) | samosprava_obec | A | 33 | 17 | 2026-11-23 | ok |
| Město Nové Město na Moravě (`dotace.nmnm.cz`) | samosprava_obec | A | 29 | 15 | 2026-11-24 | ok |
| Brno‑Medlánky (`dotace.medlanky.cz`) | samosprava_obec | A | 15 | 14 | 2026-11-24 | ok |
| Město Mělník (`dotace.melnik.cz`) | samosprava_obec | A | 29 | 14 | 2026-11-24 | ok |
| Město Chomutov (`granty.chomutov.cz`) | samosprava_obec | A | 17 | 14 | 2026-11-23 | ok |
| Praha 12 (`dotace.praha12.cz`) | samosprava_obec | A | 16 | 13 | 2026-11-24 | ok |
| OPZ+ (MPSV) (`esfcr`) | ministerstvo | B | 234 | 13 | 2026-11-24 | ok |
| Dotace EU (MMR) (`dotaceeu.cz`) | ministerstvo | B | 21 | 12 | 2026-11-24 | ok |
| Ministerstvo pro místní rozvoj (`mmr`) | ministerstvo | C | 20 | 12 | 2026-11-24 | ok |
| Nadace (OSF, Vodafone, Abakus, LPR, CLF) (`nadace_spa`) | nadace | B | 16 | 12 | 2026-11-24 | ok |
| Město Dobříš (`dotace.mestodobris.cz`) | samosprava_obec | A | 12 | 11 | 2026-11-24 | ok |
| Město Tišnov (`dotace.tisnov.cz`) | samosprava_obec | A | 13 | 11 | 2026-11-24 | ok |
| Město Havířov (`havirov-city.cz`) | samosprava_obec | A | 11 | 11 | 2026-11-23 | ok |
| Město Děčín (`mmdecin.cz`) | samosprava_obec | A | 20 | 11 | 2026-11-24 | ok |
| Město Plzeň (`dotace.plzen.eu`) | samosprava_obec | A | 31 | 10 | 2026-11-23 | ok |
| Město Frýdek‑Místek (`frydekmistek.cz`) | samosprava_obec | A | 21 | 10 | 2026-11-23 | ok |
| Národní program Životní prostředí (`npzp`) | statni_fond | B | 10 | 10 | 2026-11-24 | ok |
| Státní fond životního prostředí (`sfzp`) | statni_fond | C | 21 | 10 | 2026-11-24 | ok |
| Zlínský kraj (`zlinskykraj.cz`) | samosprava_kraj | A | 18 | 10 | 2026-11-24 | ok |
| Pardubický kraj (`dotace.pardubickykraj.cz`) | samosprava_kraj | A | 118 | 9 | 2026-11-23 | ok |
| Město Police nad Metují (`dotace.policenm.cz`) | samosprava_obec | A | 10 | 9 | 2026-11-24 | ok |
| Ministerstvo kultury (`mkcr`) | ministerstvo | C | 23 | 9 |  | neovereno |
| Národní rozvojová banka (`nrb`) | statni_fond | B | 9 | 9 | 2026-11-24 | ok |
| OP Spravedlivá transformace (MŽP) (`opst`) | ministerstvo | B | 106 | 9 | 2026-11-24 | ok |
| OP TAK (MPO) (`optak`) | ministerstvo | B | 64 | 9 | 2026-11-24 | ok |
| Praha 2 (`dotace.praha2.cz`) | samosprava_obec | A | 9 | 8 | 2026-11-24 | ok |
| Nadace Via (`nadacevia`) | nadace | B | 28 | 8 | 2026-11-24 | ok |
| Nadace rozvoje občanské společnosti (`nros.cz`) | nadace | A | 11 | 8 | 2026-11-24 | ok |
| Praha 11 (`dotace.praha11.cz`) | samosprava_obec | A | 11 | 7 | 2026-11-24 | ok |
| Praha 14 (`dotace.praha14.cz`) | samosprava_obec | A | 10 | 7 | 2026-11-24 | ok |
| Ministerstvo zemědělství (`eagri`) | ministerstvo | C | 9 | 7 | 2026-11-24 | ok |
| Česko‑německý fond budoucnosti (`fondbudoucnosti`) | nadacni_fond | P | 23 | 7 | 2026-11-24 | ok |
| Město Kladno (`mestokladno.cz`) | samosprava_obec | A | 7 | 7 | 2026-11-24 | ok |
| OP Jan Amos Komenský (MŠMT) (`opjak`) | ministerstvo | B | 9 | 7 | 2026-11-24 | ok |
| Městské obvody Ostravy (`plone_ostrava`) | samosprava_obec | B | 12 | 7 | 2026-11-24 | ok |
| Sociální nadační fond Praha (`socialninadacnifond`) | nadacni_fond | P | 10 | 7 | 2026-11-24 | ok |
| Visegrad Fund / ERSTE Foundation (`intl_funds`) | zahranicni_fond | B | 6 | 6 | 2026-11-24 | ok |
| Město Kroměříž (`kromeriz.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 10 | 6 | 2026-11-24 | ok |
| Ministerstvo průmyslu a obchodu (`mpo`) | ministerstvo | C | 8 | 6 | 2026-11-24 | ok |
| Město Česká Lípa (`mucl.cz`) | samosprava_obec | A | 14 | 6 | 2026-11-24 | ok |
| Nadace ČEZ (`nadacecez`) | firemni_nadace | C | 16 | 6 |  | neovereno |
| Město Bystřice (`dotace.mestobystrice.cz`) | samosprava_obec | A | 7 | 5 | 2026-11-24 | ok |
| Město Jablonec nad Nisou (`mestojablonec.cz`) | samosprava_obec | A | 14 | 5 | 2026-11-23 | ok |
| Město Karlovy Vary (`mmkv.cz`) | samosprava_obec | A | 8 | 5 | 2026-11-24 | ok |
| OP Doprava (MD) (`opd`) | ministerstvo | B | 12 | 5 | 2026-11-24 | ok |
| OP Životní prostředí (SFŽP) (`opzp`) | ministerstvo | B | 107 | 5 | 2026-11-24 | ok |
| Město Pardubice (`pardubice.eu`) | samosprava_obec | A | 12 | 5 | 2026-11-24 | ok |
| Technologická agentura ČR (`tacr`) | statni_agentura | B | 26 | 5 | 2026-11-24 | ok |
| Město Třinec (`trinecko.cz`) | samosprava_obec | A | 6 | 5 | 2026-11-24 | ok |
| Česká rozvojová agentura (`czechaid`) | statni_agentura | B | 9 | 4 | 2026-11-24 | ok |
| Město Hradec Králové (`hradeckralove.org`) | samosprava_obec | A | 4 | 4 | 2026-11-24 | ok |
| Hasičský záchranný sbor ČR (MV) (`hzs`) | ministerstvo | B | 4 | 4 |  | neovereno |
| Interreg (CZ‑PL, SK‑CZ) (`interreg`) | zahranicni_fond | B | 6 | 4 | 2026-11-24 | ok |
| Jihomoravský kraj (`jmk_edotace`) | samosprava_kraj | B | 5 | 4 | 2026-11-24 | ok |
| Město Karviná (`karvina.cz`) | samosprava_obec | A | 16 | 4 | 2026-11-24 | ok |
| Olomoucký kraj (`olkraj.cz`) | samosprava_kraj | A | 72 | 4 | 2026-11-24 | ok |
| Město Olomouc (`olomouc.eu`) | samosprava_obec | A | 23 | 4 | 2026-11-24 | ok |
| Státní fond audiovize (`sfa`) | statni_fond | C | 9 | 4 | 2026-11-24 | ok |
| Státní fond dopravní infrastruktury (`sfdi`) | statni_fond | C | 8 | 4 | 2026-11-24 | ok |
| Obec Štěpánov (`dotace.stepanov.cz`) | samosprava_obec | A | 4 | 3 | 2026-11-24 | ok |
| Město Jihlava (`jihlava.cz`) | samosprava_obec | A | 11 | 3 | 2026-11-17 | ok |
| Nadace The Kellner Family Foundation (`kellner`) | firemni_nadace | P | 4 | 3 | 2026-11-24 | ok |
| Město Loket (`loket.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 6 | 3 | 2026-11-17 | ok |
| Pardubický kraj (`pardubickykraj.cz`) | samosprava_kraj | C | 4 | 3 |  | neovereno |
| Město Přerov (`prerov.eu`) | samosprava_obec | A | 10 | 3 | 2026-11-24 | ok |
| Město Prostějov (`prostejov.eu`) | samosprava_obec | A | 5 | 3 | 2026-11-24 | ok |
| Státní fond podpory investic (`sfpi`) | statni_fond | F | 6 | 3 |  | zmrazeny |
| Město Teplice (`teplice.cz`) | samosprava_obec | A | 7 | 3 | 2026-11-24 | ok |
| Plzeňský kraj (`dotace.plzensky-kraj.cz`) | samosprava_kraj | A | 160 | 2 | 2026-11-23 | ok |
| Grantová agentura ČR (`gacr`) | statni_agentura | C | 16 | 2 | 2026-11-24 | ok |
| Město Liberec (`granty.liberec.cz`) | samosprava_obec | A | 7 | 2 | 2026-11-23 | ok |
| Ministerstvo kultury (`mk`) | ministerstvo | B | 53 | 2 | 2026-10-09 | starne |
| Ministerstvo vnitra (`mv`) | ministerstvo | P | 7 | 2 | 2026-11-24 | ok |
| Ministerstvo životního prostředí (`mzp`) | ministerstvo | P | 8 | 2 | 2026-11-24 | ok |
| Nadace Agrofert (`nadace-agrofert`) | firemni_nadace | P | 5 | 2 | 2026-11-24 | ok |
| Nadace ADRA (`nadace_adra`) | nadace | C | 3 | 2 | 2026-11-24 | ok |
| Nadace OKD (`nadaceokd`) | firemni_nadace | P | 3 | 2 | 2026-11-24 | ok |
| Nadace Naše dítě (`nasedite`) | nadace | P | 3 | 2 | 2026-11-24 | ok |
| Národní sportovní agentura (`nsa`) | statni_agentura | B | 22 | 2 | 2026-11-24 | ok |
| Město Opava (`opava-city.cz`) | samosprava_obec | A | 14 | 2 | 2026-11-24 | ok |
| Město Ostrava (`ostrava.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 4 | 2 | 2026-11-24 | ok |
| Středočeský kraj (`stredoceskykraj.dsw2.otevrenamesta.cz`) | samosprava_kraj | A | 3 | 2 | 2026-11-24 | ok |
| Nadační fond Albert (`albert`) | firemni_nadace | C | 3 | 1 | 2026-11-24 | ok |
| Nadání Josefa, Marie a Zdeňky Hlávkových (`hlavka`) | nadace | C | 4 | 1 | 2026-11-24 | ok |
| Město Krnov (`krnov.cz`) | samosprava_obec | A | 3 | 1 | 2026-11-24 | ok |
| Nadace Leontinka (`leontinka`) | nadace | C | 2 | 1 | 2026-11-24 | ok |
| Město Mladá Boleslav (`mb-net.cz`) | samosprava_obec | A | 4 | 1 | 2026-11-17 | ok |
| Město Kolín (`mukolin.cz`) | samosprava_obec | A | 10 | 1 | 2026-11-17 | ok |
| Nadace České spořitelny (`nadacecs`) | firemni_nadace | P | 2 | 1 | 2026-11-24 | ok |
| Nadace Vodafone (`nadacevodafone.cz`) |  | P | 1 | 1 | 2026-11-24 | ok |
| Město Nové Město nad Metují (`novemestonm.dsw2.otevrenamesta.cz`) |  | A | 1 | 1 | 2026-11-24 | ok |
| Praha 6 (`praha6.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 2 | 1 | 2026-11-24 | ok |
| Město Sokolov (`sokolov.cz`) | samosprava_obec | A | 3 | 1 | 2026-11-17 | ok |
| Praha 4 (`dotace.praha4.cz`) | samosprava_obec | A | 1 | 0 | 2026-11-24 | ok |
| Praha 8 (`dotace.praha8.cz`) | samosprava_obec | A | 3 | 0 | 2026-11-24 | ok |
| EHP a Norské fondy (`eeagrants`) | zahranicni_fond | F | 26 | 0 |  | zmrazeny |
| Nadační fond pro rozvoj paliativní péče (`fondpaliativnipece`) | nadacni_fond | P | 9 | 0 | 2026-11-24 | ok |
| Konto Bariéry (`kontobariery`) |  | ? | 1 | 0 |  | bez_cesty |
| Nadační fond Krása pomoci (`krasapomoci`) | nadacni_fond | P | 2 | 0 | 2026-11-24 | ok |
| Praha 18 (Letňany) (`letnany.cz`) | samosprava_obec | A | 2 | 0 |  | neovereno |
| Praha‑Libuš (`libus.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 4 | 0 | 2026-11-24 | ok |
| Město Most (`mesto-most.cz`) | samosprava_obec | A | 10 | 0 | 2026-11-17 | ok |
| Ministerstvo práce a sociálních věcí (`mpsv`) | ministerstvo | C | 11 | 0 | 2026-11-24 | ok |
| Město Litvínov (`mulitvinov.cz`) | samosprava_obec | A | 1 | 0 | 2026-11-24 | ok |
| Nadace O2 (`nadaceo2.cz`) | nadace | P | 1 | 0 | 2026-11-24 | ok |
| Nadace táta a máma (`nadacetm`) |  | ? | 1 | 0 |  | bez_cesty |
| Nadace OSF (`osf`) |  | B | 1 | 0 | 2026-11-24 | ok |
| Nadace Partnerství (`partnerstvi`) |  | C | 1 | 0 | 2026-11-24 | ok |
| Státní fond kultury (`sfk`) | statni_fond | C | 1 | 0 | 2026-11-24 | ok |
| Nadace Sirius (`sirius`) |  | C | 1 | 0 | 2026-11-24 | ok |
| Výbor dobré vůle – Nadace Olgy Havlové (`vdv`) |  | P | 1 | 0 |  | neovereno |
| Nadace Veronica (`veronica`) |  | C | 1 | 0 | 2026-11-24 | ok |
| Vinařský fond (`vinarskyfond`) | statni_fond | C | 5 | 0 | 2026-11-24 | ok |
| Úřad vlády ČR (`vlada`) | ministerstvo | B | 7 | 0 | 2026-11-24 | ok |
| Nadace Jakuba Voráčka (`voracek`) |  | ? | 1 | 0 |  | bez_cesty |

Třídy obnovy: A strukturní ingest · B vlastní parser · C model · T přepsaný extraktor (obnovu předstírá) · F zmrazený · ? bez zapsané cesty. Inventář: `data/sources.json`.
