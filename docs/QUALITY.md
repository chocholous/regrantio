# Kvalita datové základny

Změřeno k **2026-11-16** skriptem `scripts/quality_report.py`. Čísla u živých záznamů (open · announced · unknown) jsou ta, která vidí uživatel; archiv je uvedený vedle.

## Rozsah

| | |
|---|---:|
| záznamů celkem | 4509 |
| z toho výzev | 4484 |
| **živých k dnešku** | **1887** |
| zdrojů | 136 |
| stav | open 555 · announced 374 · unknown 958 · closed 2597 |
| dosah živých | místní 515 · krajský 612 · celostátní 314 · mezinárodní 10 · EU centrální 436 |
| druh lhůty u živých | jedna lhůta 906 · průběžně 58 · opakovaně 167 · neuvedeno 756 |

## Vyplněnost polí

| pole | živé | archiv |
|---|---:|---:|
| lhůta | 49.2 % (929) | 78.6 % (3526) |
| částka pro žadatele | 4.8 % (91) | 9.4 % (421) |
| kdo smí žádat (text) | 65.8 % (1241) | 61.9 % (2776) |
| typ žadatele (faseta) | 40.9 % (771) | 39.6 % (1776) |
| oblast | 69.5 % (1311) | 83.3 % (3733) |
| území | 97.7 % (1844) | 98.8 % (4430) |
| jak podat | 82.5 % (1556) | 90.9 % (4075) |
| zdrojový dokument | 83.8 % (1582) | 88.3 % (3959) |
| kontakt | 10.9 % (205) | 13.2 % (593) |
| dokumenty | 20.6 % (389) | 30.5 % (1369) |
| číslo výzvy | 36.7 % (692) | 43.7 % (1961) |

## Čerstvost živých záznamů

| ověřeno u zdroje | záznamů |
|---|---:|
| do 7 dnů | 1435 |
| do 30 dnů | 15 |
| starší | 19 |
| nevíme (bez razítka) | 418 |

## Doložitelnost

Citací celkem 17959, ve zdroji dohledaných **9533 (53.1 %)**. Nedohledaná citace nedokládá nic; produkt u takového pole původ neukazuje jako doložený.

| pole (živé) | má hodnotu | parser | model | dopočet | doloženo citací |
|---|---:|---:|---:|---:|---:|
| amount | 91 | 25 | 66 | 0 | 54.9 % |
| deadline | 929 | 155 | 767 | 7 | 63.4 % |
| eligible_applicants | 1241 | 399 | 842 | 0 | 16.9 % |
| focus_area | 1779 | 689 | 1090 | 0 | 16.4 % |
| oblast | 1311 | 183 | 1128 | 0 | 17.8 % |
| open_from | 942 | 176 | 766 | 0 | 7.1 % |
| region | 1844 | 756 | 1088 | 0 | 12.4 % |
| typ_zadatele | 771 | 383 | 388 | 0 | 9.5 % |

## Rodiny ročníků

450 programů má víc než jeden záznam; 401 z nich se vyhlašuje opakovaně (dva a víc ročníků); 513 starších ročníků nese `variant_of`.

## Zdroje

| stav | zdrojů | živých záznamů |
|---|---:|---:|
| ok (ověřeno do 21 dnů) | 123 | 1819 |
| stárne (nad 21 dnů) | 1 | 2 |
| má cestu, nikdy neověřeno | 7 | 63 |
| bez zapsané cesty k obnově | 3 | 0 |
| zmrazený | 2 | 3 |

| zdroj | typ | obnova | záznamů | živých | ověřeno | stav |
|---|---|---|---:|---:|---|---|
| Evropská komise (Funding & Tenders) (`eu_ft`) | evropska_komise | B | 787 | 436 | 2026-11-16 | ok |
| Kraj Vysočina (Fond Vysočiny) (`fondvysociny.cz`) | samosprava_kraj | A | 322 | 240 | 2026-11-16 | ok |
| Královéhradecký kraj (`dotace.khk.cz`) | samosprava_kraj | A | 206 | 84 | 2026-11-16 | ok |
| Město Ústí nad Labem (`dotace.usti-nad-labem.cz`) | samosprava_obec | A | 90 | 80 | 2026-11-16 | ok |
| IROP (MMR) (`irop.gov.cz`) | ministerstvo | A | 120 | 55 | 2026-11-16 | ok |
| Středočeský kraj (`stredoceskykraj.cz`) | samosprava_kraj | A | 99 | 45 | 2026-11-16 | ok |
| Liberecký kraj (`dotace.kraj-lbc.cz`) | samosprava_kraj | A | 138 | 44 | 2026-11-16 | ok |
| Ministerstvo zdravotnictví (`mzcr`) | ministerstvo | C | 83 | 41 |  | neovereno |
| Hlavní město Praha (`praha.eu`) | samosprava_kraj | A | 39 | 38 | 2026-11-16 | ok |
| Město Ostrava (`dotace.ostrava.cz`) | samosprava_obec | A | 46 | 34 | 2026-11-16 | ok |
| Praha 3 (`dotace.praha3.cz`) | samosprava_obec | A | 35 | 33 | 2026-11-16 | ok |
| Jihočeský kraj (`kraj-jihocesky.cz`) | samosprava_kraj | A | 37 | 29 | 2026-11-16 | ok |
| Moravskoslezský kraj (`msk.cz`) | samosprava_kraj | A | 111 | 28 | 2026-11-16 | ok |
| Obec Chýně (`dotace.chyne.cz`) | samosprava_obec | A | 27 | 25 | 2026-11-16 | ok |
| Karlovarský kraj (`kr-karlovarsky.cz`) | samosprava_kraj | A | 86 | 23 | 2026-11-16 | ok |
| Místní akční skupina (`mas`) | mistni_akcni_skupina | C | 25 | 22 | 2026-11-15 | ok |
| Město Tábor (`taborcz.eu`) | samosprava_obec | A | 21 | 21 | 2026-11-15 | ok |
| Město Hodonín (`hodonin.eu`) | samosprava_obec | A | 105 | 20 | 2026-11-16 | ok |
| Ústecký kraj (`kr-ustecky.cz`) | samosprava_kraj | A | 115 | 20 | 2026-11-16 | ok |
| Ministerstvo školství, mládeže a tělovýchovy (`msmt`) | ministerstvo | B | 32 | 19 | 2026-11-16 | ok |
| Město Hradec Králové (`dotace.mmhk.cz`) | samosprava_obec | A | 33 | 17 | 2026-11-16 | ok |
| Město Brno (`dotace.brno.cz`) | samosprava_obec | A | 51 | 16 | 2026-11-16 | ok |
| Město Mělník (`dotace.melnik.cz`) | samosprava_obec | A | 29 | 16 | 2026-11-16 | ok |
| Město Nové Město na Moravě (`dotace.nmnm.cz`) | samosprava_obec | A | 29 | 15 | 2026-11-16 | ok |
| Brno‑Medlánky (`dotace.medlanky.cz`) | samosprava_obec | A | 15 | 14 | 2026-11-16 | ok |
| OPZ+ (MPSV) (`esfcr`) | ministerstvo | B | 234 | 14 | 2026-11-16 | ok |
| Město Chomutov (`granty.chomutov.cz`) | samosprava_obec | A | 17 | 14 | 2026-11-16 | ok |
| Město Plzeň (`dotace.plzen.eu`) | samosprava_obec | A | 31 | 13 | 2026-11-16 | ok |
| Praha 12 (`dotace.praha12.cz`) | samosprava_obec | A | 16 | 13 | 2026-11-16 | ok |
| Dotace EU (MMR) (`dotaceeu.cz`) | ministerstvo | B | 21 | 12 | 2026-11-16 | ok |
| Nadace (OSF, Vodafone, Abakus, LPR, CLF) (`nadace_spa`) | nadace | B | 16 | 12 | 2026-11-16 | ok |
| Město Dobříš (`dotace.mestodobris.cz`) | samosprava_obec | A | 12 | 11 | 2026-11-16 | ok |
| Město Tišnov (`dotace.tisnov.cz`) | samosprava_obec | A | 13 | 11 | 2026-11-16 | ok |
| Město Havířov (`havirov-city.cz`) | samosprava_obec | A | 11 | 11 | 2026-11-16 | ok |
| Město Děčín (`mmdecin.cz`) | samosprava_obec | A | 19 | 11 | 2026-11-16 | ok |
| Město Frýdek‑Místek (`frydekmistek.cz`) | samosprava_obec | A | 21 | 10 | 2026-11-16 | ok |
| Národní program Životní prostředí (`npzp`) | statni_fond | B | 10 | 10 | 2026-11-16 | ok |
| Zlínský kraj (`zlinskykraj.cz`) | samosprava_kraj | A | 18 | 10 | 2026-11-16 | ok |
| Pardubický kraj (`dotace.pardubickykraj.cz`) | samosprava_kraj | A | 117 | 9 | 2026-11-16 | ok |
| Město Police nad Metují (`dotace.policenm.cz`) | samosprava_obec | A | 10 | 9 | 2026-11-16 | ok |
| Ministerstvo kultury (`mkcr`) | ministerstvo | C | 23 | 9 |  | neovereno |
| Národní rozvojová banka (`nrb`) | statni_fond | B | 9 | 9 | 2026-11-16 | ok |
| OP Spravedlivá transformace (MŽP) (`opst`) | ministerstvo | B | 106 | 9 | 2026-11-16 | ok |
| Státní fond životního prostředí (`sfzp`) | statni_fond | C | 20 | 9 | 2026-11-09 | ok |
| Praha 2 (`dotace.praha2.cz`) | samosprava_obec | A | 9 | 8 | 2026-11-16 | ok |
| Nadace rozvoje občanské společnosti (`nros.cz`) | nadace | A | 11 | 8 | 2026-11-16 | ok |
| OP TAK (MPO) (`optak`) | ministerstvo | B | 61 | 8 | 2026-11-16 | ok |
| Praha 11 (`dotace.praha11.cz`) | samosprava_obec | A | 11 | 7 | 2026-11-16 | ok |
| Praha 14 (`dotace.praha14.cz`) | samosprava_obec | A | 10 | 7 | 2026-11-16 | ok |
| Česko‑německý fond budoucnosti (`fondbudoucnosti`) | nadacni_fond | P | 23 | 7 | 2026-11-16 | ok |
| Město Kladno (`mestokladno.cz`) | samosprava_obec | A | 7 | 7 | 2026-11-16 | ok |
| Ministerstvo pro místní rozvoj (`mmr`) | ministerstvo | C | 19 | 7 | 2026-11-16 | ok |
| Nadace Via (`nadacevia`) | nadace | B | 27 | 7 | 2026-11-16 | ok |
| OP Jan Amos Komenský (MŠMT) (`opjak`) | ministerstvo | B | 8 | 7 | 2026-11-16 | ok |
| Městské obvody Ostravy (`plone_ostrava`) | samosprava_obec | B | 12 | 7 | 2026-11-16 | ok |
| Ministerstvo zemědělství (`eagri`) | ministerstvo | C | 9 | 6 | 2026-11-16 | ok |
| Visegrad Fund / ERSTE Foundation (`intl_funds`) | zahranicni_fond | B | 6 | 6 | 2026-11-16 | ok |
| Město Kroměříž (`kromeriz.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 10 | 6 | 2026-11-16 | ok |
| Ministerstvo průmyslu a obchodu (`mpo`) | ministerstvo | C | 8 | 6 | 2026-11-16 | ok |
| Město Česká Lípa (`mucl.cz`) | samosprava_obec | A | 14 | 6 | 2026-11-16 | ok |
| Nadace ČEZ (`nadacecez`) | firemni_nadace | C | 16 | 6 |  | neovereno |
| OP Životní prostředí (SFŽP) (`opzp`) | ministerstvo | B | 107 | 6 | 2026-11-16 | ok |
| Sociální nadační fond Praha (`socialninadacnifond`) | nadacni_fond | P | 10 | 6 | 2026-11-16 | ok |
| Technologická agentura ČR (`tacr`) | statni_agentura | B | 26 | 6 | 2026-11-16 | ok |
| Město Bystřice (`dotace.mestobystrice.cz`) | samosprava_obec | A | 7 | 5 | 2026-11-16 | ok |
| Město Jablonec nad Nisou (`mestojablonec.cz`) | samosprava_obec | A | 14 | 5 | 2026-11-16 | ok |
| Město Karlovy Vary (`mmkv.cz`) | samosprava_obec | A | 8 | 5 | 2026-11-16 | ok |
| OP Doprava (MD) (`opd`) | ministerstvo | B | 12 | 5 | 2026-11-16 | ok |
| Město Pardubice (`pardubice.eu`) | samosprava_obec | A | 12 | 5 | 2026-11-16 | ok |
| Státní fond audiovize (`sfa`) | statni_fond | C | 8 | 5 | 2026-11-16 | ok |
| Město Třinec (`trinecko.cz`) | samosprava_obec | A | 6 | 5 | 2026-11-16 | ok |
| Česká rozvojová agentura (`czechaid`) | statni_agentura | B | 9 | 4 | 2026-11-16 | ok |
| Město Hradec Králové (`hradeckralove.org`) | samosprava_obec | A | 4 | 4 | 2026-11-16 | ok |
| Hasičský záchranný sbor ČR (MV) (`hzs`) | ministerstvo | B | 4 | 4 |  | neovereno |
| Interreg (CZ‑PL, SK‑CZ) (`interreg`) | zahranicni_fond | B | 6 | 4 | 2026-11-16 | ok |
| Olomoucký kraj (`olkraj.cz`) | samosprava_kraj | A | 72 | 4 | 2026-11-16 | ok |
| Město Olomouc (`olomouc.eu`) | samosprava_obec | A | 23 | 4 | 2026-11-16 | ok |
| Státní fond dopravní infrastruktury (`sfdi`) | statni_fond | C | 8 | 4 | 2026-11-16 | ok |
| Obec Štěpánov (`dotace.stepanov.cz`) | samosprava_obec | A | 4 | 3 | 2026-11-16 | ok |
| Grantová agentura ČR (`gacr`) | statni_agentura | C | 16 | 3 | 2026-11-16 | ok |
| Město Jihlava (`jihlava.cz`) | samosprava_obec | A | 11 | 3 | 2026-11-15 | ok |
| Město Karviná (`karvina.cz`) | samosprava_obec | A | 15 | 3 | 2026-11-16 | ok |
| Nadace The Kellner Family Foundation (`kellner`) | firemni_nadace | P | 4 | 3 | 2026-11-16 | ok |
| Město Loket (`loket.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 6 | 3 | 2026-11-16 | ok |
| Pardubický kraj (`pardubickykraj.cz`) | samosprava_kraj | C | 4 | 3 |  | neovereno |
| Město Přerov (`prerov.eu`) | samosprava_obec | A | 10 | 3 | 2026-11-16 | ok |
| Město Prostějov (`prostejov.eu`) | samosprava_obec | A | 5 | 3 | 2026-11-16 | ok |
| Státní fond podpory investic (`sfpi`) | statni_fond | F | 6 | 3 |  | zmrazeny |
| Město Teplice (`teplice.cz`) | samosprava_obec | A | 7 | 3 | 2026-11-16 | ok |
| Město Liberec (`granty.liberec.cz`) | samosprava_obec | A | 7 | 2 | 2026-11-16 | ok |
| Jihomoravský kraj (`jmk_edotace`) | samosprava_kraj | B | 3 | 2 | 2026-11-16 | ok |
| Ministerstvo kultury (`mk`) | ministerstvo | B | 53 | 2 | 2026-10-09 | starne |
| Ministerstvo vnitra (`mv`) | ministerstvo | P | 7 | 2 | 2026-11-16 | ok |
| Ministerstvo životního prostředí (`mzp`) | ministerstvo | P | 8 | 2 | 2026-11-16 | ok |
| Nadace Agrofert (`nadace-agrofert`) | firemni_nadace | P | 5 | 2 | 2026-11-16 | ok |
| Nadace ADRA (`nadace_adra`) | nadace | C | 3 | 2 | 2026-11-16 | ok |
| Nadace OKD (`nadaceokd`) | firemni_nadace | P | 3 | 2 | 2026-11-16 | ok |
| Nadace Naše dítě (`nasedite`) | nadace | P | 3 | 2 | 2026-11-16 | ok |
| Město Opava (`opava-city.cz`) | samosprava_obec | A | 14 | 2 | 2026-11-16 | ok |
| Město Ostrava (`ostrava.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 4 | 2 | 2026-11-16 | ok |
| Středočeský kraj (`stredoceskykraj.dsw2.otevrenamesta.cz`) | samosprava_kraj | A | 3 | 2 | 2026-11-16 | ok |
| Plzeňský kraj (`dotace.plzensky-kraj.cz`) | samosprava_kraj | A | 159 | 1 | 2026-11-16 | ok |
| Nadání Josefa, Marie a Zdeňky Hlávkových (`hlavka`) | nadace | C | 4 | 1 | 2026-11-16 | ok |
| Město Krnov (`krnov.cz`) | samosprava_obec | A | 3 | 1 | 2026-11-16 | ok |
| Nadace Leontinka (`leontinka`) | nadace | C | 2 | 1 | 2026-11-16 | ok |
| Město Mladá Boleslav (`mb-net.cz`) | samosprava_obec | A | 4 | 1 | 2026-11-16 | ok |
| Město Kolín (`mukolin.cz`) | samosprava_obec | A | 10 | 1 | 2026-11-15 | ok |
| Nadace České spořitelny (`nadacecs`) | firemni_nadace | P | 2 | 1 | 2026-11-16 | ok |
| Nadace Vodafone (`nadacevodafone.cz`) |  | P | 1 | 1 | 2026-11-16 | ok |
| Město Nové Město nad Metují (`novemestonm.dsw2.otevrenamesta.cz`) |  | A | 1 | 1 | 2026-11-16 | ok |
| Národní sportovní agentura (`nsa`) | statni_agentura | B | 21 | 1 | 2026-11-16 | ok |
| Praha 6 (`praha6.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 2 | 1 | 2026-11-16 | ok |
| Město Sokolov (`sokolov.cz`) | samosprava_obec | A | 3 | 1 | 2026-11-16 | ok |
| Nadační fond Albert (`albert`) | firemni_nadace | C | 3 | 0 | 2026-11-16 | ok |
| Praha 4 (`dotace.praha4.cz`) | samosprava_obec | A | 1 | 0 | 2026-11-16 | ok |
| Praha 8 (`dotace.praha8.cz`) | samosprava_obec | A | 3 | 0 | 2026-11-16 | ok |
| EHP a Norské fondy (`eeagrants`) | zahranicni_fond | F | 26 | 0 |  | zmrazeny |
| Nadační fond pro rozvoj paliativní péče (`fondpaliativnipece`) | nadacni_fond | P | 9 | 0 | 2026-11-16 | ok |
| Konto Bariéry (`kontobariery`) |  | ? | 1 | 0 |  | bez_cesty |
| Nadační fond Krása pomoci (`krasapomoci`) | nadacni_fond | P | 2 | 0 | 2026-11-16 | ok |
| Praha 18 (Letňany) (`letnany.cz`) | samosprava_obec | A | 2 | 0 |  | neovereno |
| Praha‑Libuš (`libus.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 4 | 0 | 2026-11-16 | ok |
| Město Most (`mesto-most.cz`) | samosprava_obec | A | 10 | 0 | 2026-11-15 | ok |
| Ministerstvo práce a sociálních věcí (`mpsv`) | ministerstvo | C | 11 | 0 | 2026-11-16 | ok |
| Město Litvínov (`mulitvinov.cz`) | samosprava_obec | A | 1 | 0 | 2026-11-16 | ok |
| Nadace O2 (`nadaceo2.cz`) | nadace | P | 1 | 0 | 2026-11-16 | ok |
| Nadace táta a máma (`nadacetm`) |  | ? | 1 | 0 |  | bez_cesty |
| Nadace OSF (`osf`) |  | B | 1 | 0 | 2026-11-16 | ok |
| Nadace Partnerství (`partnerstvi`) |  | C | 1 | 0 | 2026-11-16 | ok |
| Státní fond kultury (`sfk`) | statni_fond | C | 1 | 0 | 2026-11-16 | ok |
| Nadace Sirius (`sirius`) |  | C | 1 | 0 | 2026-11-16 | ok |
| Výbor dobré vůle – Nadace Olgy Havlové (`vdv`) |  | P | 1 | 0 |  | neovereno |
| Nadace Veronica (`veronica`) |  | C | 1 | 0 | 2026-11-16 | ok |
| Vinařský fond (`vinarskyfond`) | statni_fond | C | 5 | 0 | 2026-11-16 | ok |
| Úřad vlády ČR (`vlada`) | ministerstvo | B | 7 | 0 | 2026-11-16 | ok |
| Nadace Jakuba Voráčka (`voracek`) |  | ? | 1 | 0 |  | bez_cesty |

Třídy obnovy: A strukturní ingest · B vlastní parser · C model · T přepsaný extraktor (obnovu předstírá) · F zmrazený · ? bez zapsané cesty. Inventář: `data/sources.json`.
