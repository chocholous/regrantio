# Kvalita datové základny

Změřeno k **2026-10-09** skriptem `scripts/quality_report.py`. Čísla u živých záznamů (open · announced · unknown) jsou ta, která vidí uživatel; archiv je uvedený vedle.

## Rozsah

| | |
|---|---:|
| záznamů celkem | 4068 |
| z toho výzev | 4043 |
| **živých k dnešku** | **1824** |
| zdrojů | 137 |
| stav | open 519 · announced 353 · unknown 952 · closed 2219 |
| dosah živých | místní 490 · krajský 553 · celostátní 323 · mezinárodní 10 · EU centrální 448 |
| druh lhůty u živých | jedna lhůta 860 · průběžně 81 · opakovaně 147 · neuvedeno 736 |

## Vyplněnost polí

| pole | živé | archiv |
|---|---:|---:|
| lhůta | 47.8 % (872) | 76.5 % (3091) |
| částka pro žadatele | 5.0 % (92) | 6.6 % (265) |
| kdo smí žádat (text) | 70.8 % (1291) | 63.4 % (2564) |
| typ žadatele (faseta) | 31.9 % (582) | 33.5 % (1356) |
| oblast | 77.2 % (1409) | 87.0 % (3517) |
| území | 99.9 % (1823) | 100.0 % (4042) |
| jak podat | 81.0 % (1478) | 89.4 % (3613) |
| zdrojový dokument | 97.9 % (1786) | 97.8 % (3956) |
| kontakt | 12.6 % (229) | 13.9 % (561) |
| dokumenty | 13.9 % (253) | 16.4 % (665) |
| číslo výzvy | 38.1 % (695) | 47.2 % (1909) |

## Čerstvost živých záznamů

| ověřeno u zdroje | záznamů |
|---|---:|
| do 7 dnů | 1098 |
| do 30 dnů | 5 |
| starší | 4 |
| nevíme (bez razítka) | 717 |

## Doložitelnost

Citací celkem 17285, ve zdroji dohledaných **8253 (47.7 %)**. Nedohledaná citace nedokládá nic; produkt u takového pole původ neukazuje jako doložený.

| pole (živé) | má hodnotu | parser | model | dopočet | doloženo citací |
|---|---:|---:|---:|---:|---:|
| amount | 92 | 16 | 76 | 0 | 59.8 % |
| deadline | 872 | 67 | 803 | 2 | 63.9 % |
| eligible_applicants | 1291 | 380 | 911 | 0 | 16.0 % |
| focus_area | 1708 | 529 | 1179 | 0 | 17.6 % |
| oblast | 1409 | 174 | 1235 | 0 | 18.0 % |
| open_from | 883 | 77 | 806 | 0 | 5.0 % |
| region | 1823 | 586 | 1237 | 0 | 13.5 % |
| typ_zadatele | 582 | 135 | 447 | 0 | 12.0 % |

## Rodiny ročníků

332 programů má víc než jeden záznam; 273 z nich se vyhlašuje opakovaně (dva a víc ročníků); 368 starších ročníků nese `variant_of`.

## Zdroje

| stav | zdrojů | živých záznamů |
|---|---:|---:|
| ok (ověřeno do 21 dnů) | 59 | 1453 |
| stárne (nad 21 dnů) | 0 | 0 |
| má cestu, nikdy neověřeno | 55 | 288 |
| bez zapsané cesty k obnově | 20 | 60 |
| zmrazený | 3 | 23 |

| zdroj | typ | obnova | záznamů | živých | ověřeno | stav |
|---|---|---|---:|---:|---|---|
| Evropská komise (Funding & Tenders) (`eu_ft`) | evropska_komise | B | 749 | 448 | 2026-10-09 | ok |
| Kraj Vysočina (Fond Vysočiny) (`fondvysociny.cz`) | samosprava_kraj | A | 315 | 236 | 2026-10-09 | ok |
| Město Ústí nad Labem (`dotace.usti-nad-labem.cz`) | samosprava_obec | A | 87 | 83 | 2026-10-09 | ok |
| IROP (MMR) (`irop.gov.cz`) | ministerstvo | A | 120 | 55 | 2026-10-09 | ok |
| Liberecký kraj (`dotace.kraj-lbc.cz`) | samosprava_kraj | A | 138 | 48 | 2026-10-09 | ok |
| Středočeský kraj (`stredoceskykraj.cz`) | samosprava_kraj | A | 99 | 46 | 2026-10-09 | ok |
| Ministerstvo zdravotnictví (`mzcr`) | ministerstvo | C | 83 | 41 |  | neovereno |
| Město Hodonín (`hodonin.eu`) | samosprava_obec | A | 94 | 40 |  | neovereno |
| Hlavní město Praha (`praha.eu`) | samosprava_kraj | A | 38 | 37 | 2026-10-09 | ok |
| Praha 3 (`dotace.praha3.cz`) | samosprava_obec | A | 35 | 33 | 2026-10-09 | ok |
| Město Brno (`dotace.brno.cz`) | samosprava_obec | A | 51 | 31 | 2026-10-09 | ok |
| Moravskoslezský kraj (`msk.cz`) | samosprava_kraj | A | 108 | 28 | 2026-10-09 | ok |
| Karlovarský kraj (`kr-karlovarsky.cz`) | samosprava_kraj | A | 86 | 27 | 2026-10-09 | ok |
| Obec Chýně (`dotace.chyne.cz`) | samosprava_obec | A | 27 | 26 | 2026-10-09 | ok |
| Královéhradecký kraj (`dotace.khk.cz`) | samosprava_kraj | A | 148 | 26 | 2026-10-09 | ok |
| Ústecký kraj (`kr-ustecky.cz`) | samosprava_kraj | A | 111 | 21 | 2026-10-09 | ok |
| Město Tábor (`taborcz.eu`) | samosprava_obec | A | 21 | 21 |  | neovereno |
| Pardubický kraj (`dotace.pardubickykraj.cz`) | samosprava_kraj | A | 113 | 20 | 2026-10-09 | ok |
| Jihomoravský kraj (`kr-jihomoravsky.cz`) | samosprava_kraj | F | 34 | 20 |  | zmrazeny |
| Česko‑německý fond budoucnosti (`fondbudoucnosti`) | nadacni_fond | ? | 36 | 18 |  | bez_cesty |
| Město Mělník (`dotace.melnik.cz`) | samosprava_obec | A | 29 | 16 | 2026-10-09 | ok |
| Ministerstvo kultury (`mkcr`) | ministerstvo | C | 29 | 15 |  | neovereno |
| Brno‑Medlánky (`dotace.medlanky.cz`) | samosprava_obec | A | 15 | 14 | 2026-10-09 | ok |
| Město Nové Město na Moravě (`dotace.nmnm.cz`) | samosprava_obec | A | 21 | 14 | 2026-10-09 | ok |
| OPZ+ (MPSV) (`esfcr`) | ministerstvo | B | 234 | 14 | 2026-10-09 | ok |
| Ministerstvo školství, mládeže a tělovýchovy (`msmt`) | ministerstvo | B | 27 | 14 | 2026-10-09 | ok |
| Praha 12 (`dotace.praha12.cz`) | samosprava_obec | A | 16 | 13 | 2026-10-09 | ok |
| Nadace (OSF, Vodafone, Abakus, LPR, CLF) (`nadace_spa`) | nadace | B | 16 | 13 | 2026-10-09 | ok |
| Zlínský kraj (`zlinskykraj.cz`) | samosprava_kraj | A | 18 | 12 | 2026-10-09 | ok |
| Město Ostrava (`dotace.ostrava.cz`) | samosprava_obec | C | 20 | 11 |  | neovereno |
| Město Tišnov (`dotace.tisnov.cz`) | samosprava_obec | A | 13 | 11 | 2026-10-09 | ok |
| Město Havířov (`havirov-city.cz`) | samosprava_obec | C | 11 | 11 |  | neovereno |
| Státní fond životního prostředí (`sfzp`) | statni_fond | C | 19 | 11 |  | neovereno |
| Město Chomutov (`granty.chomutov.cz`) | samosprava_obec | C | 11 | 10 |  | neovereno |
| Ministerstvo životního prostředí (`mzp`) | ministerstvo | T | 16 | 10 |  | bez_cesty |
| Národní program Životní prostředí (`npzp`) | statni_fond | B | 10 | 10 | 2026-10-09 | ok |
| Národní rozvojová banka (`nrb`) | statni_fond | B | 9 | 9 | 2026-10-09 | ok |
| OP TAK (MPO) (`optak`) | ministerstvo | B | 60 | 9 | 2026-10-09 | ok |
| Město Dobříš (`dotace.mestodobris.cz`) | samosprava_obec | A | 9 | 8 | 2026-10-09 | ok |
| Praha 2 (`dotace.praha2.cz`) | samosprava_obec | A | 9 | 8 | 2026-10-09 | ok |
| Jihočeský kraj (`kraj-jihocesky.cz`) | samosprava_kraj | A | 11 | 8 | 2026-10-09 | ok |
| Česká rozvojová agentura (`czechaid`) | statni_agentura | B | 12 | 7 | 2026-10-09 | ok |
| Město Hradec Králové (`dotace.mmhk.cz`) | samosprava_obec | A | 23 | 7 |  | neovereno |
| Praha 11 (`dotace.praha11.cz`) | samosprava_obec | A | 11 | 7 | 2026-10-09 | ok |
| Praha 14 (`dotace.praha14.cz`) | samosprava_obec | A | 10 | 7 | 2026-10-09 | ok |
| Město Kladno (`mestokladno.cz`) | samosprava_obec | A | 7 | 7 |  | neovereno |
| Město Karlovy Vary (`mmkv.cz`) | samosprava_obec | C | 8 | 7 |  | neovereno |
| Ministerstvo průmyslu a obchodu (`mpo`) | ministerstvo | C | 9 | 7 |  | neovereno |
| Nadace Via (`nadacevia`) | nadace | B | 26 | 7 | 2026-10-09 | ok |
| OP Jan Amos Komenský (MŠMT) (`opjak`) | ministerstvo | B | 8 | 7 | 2026-10-09 | ok |
| OP Spravedlivá transformace (MŽP) (`opst`) | ministerstvo | B | 103 | 7 | 2026-10-09 | ok |
| OP Životní prostředí (SFŽP) (`opzp`) | ministerstvo | B | 107 | 7 | 2026-10-09 | ok |
| Městské obvody Ostravy (`plone_ostrava`) | samosprava_obec | B | 12 | 7 | 2026-10-09 | ok |
| Sociální nadační fond Praha (`socialninadacnifond`) | nadacni_fond | ? | 12 | 7 |  | bez_cesty |
| Technologická agentura ČR (`tacr`) | statni_agentura | B | 23 | 7 | 2026-10-09 | ok |
| Město Police nad Metují (`dotace.policenm.cz`) | samosprava_obec | A | 9 | 6 | 2026-10-09 | ok |
| Ministerstvo zemědělství (`eagri`) | ministerstvo | C | 10 | 6 |  | neovereno |
| Visegrad Fund / ERSTE Foundation (`intl_funds`) | zahranicni_fond | B | 6 | 6 | 2026-10-09 | ok |
| Město Kroměříž (`kromeriz.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 10 | 6 | 2026-10-09 | ok |
| Město Děčín (`mmdecin.cz`) | samosprava_obec | C | 13 | 6 |  | neovereno |
| Ministerstvo pro místní rozvoj (`mmr`) | ministerstvo | C | 9 | 6 |  | neovereno |
| Město Česká Lípa (`mucl.cz`) | samosprava_obec | A | 14 | 6 |  | neovereno |
| Nadace ČEZ (`nadacecez`) | firemni_nadace | C | 16 | 6 |  | neovereno |
| Nadace OKD (`nadaceokd`) | firemni_nadace | ? | 7 | 6 |  | bez_cesty |
| Město Bystřice (`dotace.mestobystrice.cz`) | samosprava_obec | A | 7 | 5 | 2026-10-09 | ok |
| Dotace EU (MMR) (`dotaceeu.cz`) | ministerstvo | A | 13 | 5 |  | neovereno |
| Město Jablonec nad Nisou (`mestojablonec.cz`) | samosprava_obec | C | 14 | 5 |  | neovereno |
| Město Kolín (`mukolin.cz`) | samosprava_obec | A | 10 | 5 |  | neovereno |
| Olomoucký kraj (`olkraj.cz`) | samosprava_kraj | A | 12 | 5 | 2026-10-09 | ok |
| Město Olomouc (`olomouc.eu`) | samosprava_obec | C | 19 | 5 |  | neovereno |
| OP Doprava (MD) (`opd`) | ministerstvo | B | 12 | 5 | 2026-10-09 | ok |
| Město Třinec (`trinecko.cz`) | samosprava_obec | A | 6 | 5 |  | neovereno |
| Hasičský záchranný sbor ČR (MV) (`hzs`) | ministerstvo | B | 4 | 4 |  | neovereno |
| Interreg (CZ‑PL, SK‑CZ) (`interreg`) | zahranicni_fond | B | 6 | 4 | 2026-10-09 | ok |
| Nadace Agrofert (`nadace-agrofert`) | firemni_nadace | ? | 7 | 4 |  | bez_cesty |
| Město Pardubice (`pardubice.eu`) | samosprava_obec | C | 12 | 4 |  | neovereno |
| Město Přerov (`prerov.eu`) | samosprava_obec | C | 9 | 4 |  | neovereno |
| Státní fond dopravní infrastruktury (`sfdi`) | statni_fond | C | 8 | 4 |  | neovereno |
| Výbor dobré vůle – Nadace Olgy Havlové (`vdv`) | nadace | ? | 5 | 4 |  | bez_cesty |
| Obec Štěpánov (`dotace.stepanov.cz`) | samosprava_obec | A | 4 | 3 | 2026-10-09 | ok |
| Město Hradec Králové (`hradeckralove.org`) | samosprava_obec | A | 4 | 3 |  | neovereno |
| Město Jihlava (`jihlava.cz`) | samosprava_obec | A | 11 | 3 |  | neovereno |
| Město Karviná (`karvina.cz`) | samosprava_obec | C | 15 | 3 |  | neovereno |
| Město Loket (`loket.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 6 | 3 | 2026-10-09 | ok |
| Ministerstvo práce a sociálních věcí (`mpsv`) | ministerstvo | C | 11 | 3 |  | neovereno |
| Nadace Naše dítě (`nasedite`) | nadace | ? | 4 | 3 |  | bez_cesty |
| Pardubický kraj (`pardubickykraj.cz`) | samosprava_kraj | C | 4 | 3 |  | neovereno |
| Státní fond podpory investic (`sfpi`) | statni_fond | F | 6 | 3 |  | zmrazeny |
| Město Plzeň (`dotace.plzen.eu`) | samosprava_obec | C | 20 | 2 |  | neovereno |
| Město Liberec (`granty.liberec.cz`) | samosprava_obec | C | 7 | 2 |  | neovereno |
| Nadace The Kellner Family Foundation (`kellner`) | firemni_nadace | ? | 5 | 2 |  | bez_cesty |
| Město Krnov (`krnov.cz`) | samosprava_obec | A | 3 | 2 |  | neovereno |
| Ministerstvo kultury (`mk`) | ministerstvo | B | 53 | 2 | 2026-10-09 | ok |
| Ministerstvo vnitra (`mv`) | ministerstvo | T | 7 | 2 |  | bez_cesty |
| Nadace ADRA (`nadace_adra`) | nadace | C | 3 | 2 |  | neovereno |
| Město Ostrava (`ostrava.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 4 | 2 | 2026-10-09 | ok |
| Středočeský kraj (`stredoceskykraj.dsw2.otevrenamesta.cz`) | samosprava_kraj | A | 3 | 2 | 2026-10-09 | ok |
| Město Teplice (`teplice.cz`) | samosprava_obec | A | 6 | 2 |  | neovereno |
| Plzeňský kraj (`dotace.plzensky-kraj.cz`) | samosprava_kraj | C | 20 | 1 |  | neovereno |
| Nadační fond pro rozvoj paliativní péče (`fondpaliativnipece`) | nadacni_fond | ? | 10 | 1 |  | bez_cesty |
| Město Frýdek‑Místek (`frydekmistek.cz`) | samosprava_obec | C | 10 | 1 |  | neovereno |
| Grantová agentura ČR (`gacr`) | statni_agentura | C | 14 | 1 |  | neovereno |
| Nadace Agrofert (`nadace-agrofert.cz`) | nadace | ? | 1 | 1 |  | bez_cesty |
| Nadace České spořitelny (`nadacecs`) | firemni_nadace | T | 2 | 1 |  | bez_cesty |
| Nadace Vodafone (`nadacevodafone.cz`) | nadace | ? | 1 | 1 |  | bez_cesty |
| Město Nové Město nad Metují (`novemestonm.dsw2.otevrenamesta.cz`) |  | A | 1 | 1 | 2026-10-09 | ok |
| Národní sportovní agentura (`nsa`) | statni_agentura | B | 21 | 1 | 2026-10-09 | ok |
| Praha 6 (`praha6.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 2 | 1 | 2026-10-09 | ok |
| Město Sokolov (`sokolov.cz`) | samosprava_obec | A | 3 | 1 |  | neovereno |
| Nadační fond Albert (`albert`) | firemni_nadace | C | 3 | 0 |  | neovereno |
| Praha 4 (`dotace.praha4.cz`) | samosprava_obec | A | 1 | 0 | 2026-10-09 | ok |
| Praha 8 (`dotace.praha8.cz`) | samosprava_obec | A | 3 | 0 | 2026-10-09 | ok |
| EHP a Norské fondy (`eeagrants`) | zahranicni_fond | F | 26 | 0 |  | zmrazeny |
| Nadání Josefa, Marie a Zdeňky Hlávkových (`hlavka`) | nadace | C | 4 | 0 |  | neovereno |
| Konto Bariéry (`kontobariery`) |  | ? | 1 | 0 |  | bez_cesty |
| Nadační fond Krása pomoci (`krasapomoci`) | nadacni_fond | ? | 2 | 0 |  | bez_cesty |
| Nadace Leontinka (`leontinka`) | nadace | C | 2 | 0 |  | neovereno |
| Praha 18 (Letňany) (`letnany.cz`) | samosprava_obec | A | 2 | 0 |  | neovereno |
| Praha‑Libuš (`libus.dsw2.otevrenamesta.cz`) | samosprava_obec | A | 4 | 0 | 2026-10-09 | ok |
| Město Mladá Boleslav (`mb-net.cz`) | samosprava_obec | A | 3 | 0 |  | neovereno |
| Město Most (`mesto-most.cz`) | samosprava_obec | A | 10 | 0 |  | neovereno |
| Město Litvínov (`mulitvinov.cz`) | samosprava_obec | A | 1 | 0 |  | neovereno |
| Nadace ČEZ (`nadacecez.cz`) | nadace | ? | 1 | 0 |  | bez_cesty |
| Nadace O2 (`nadaceo2.cz`) | nadace | ? | 1 | 0 |  | bez_cesty |
| Nadace táta a máma (`nadacetm`) |  | ? | 1 | 0 |  | bez_cesty |
| Nadace rozvoje občanské společnosti (`nros.cz`) | nadace | ? | 1 | 0 |  | bez_cesty |
| Město Opava (`opava-city.cz`) | samosprava_obec | C | 7 | 0 |  | neovereno |
| Nadace OSF (`osf`) |  | B | 1 | 0 | 2026-10-09 | ok |
| Nadace Partnerství (`partnerstvi`) |  | C | 1 | 0 |  | neovereno |
| Město Prostějov (`prostejov.eu`) | samosprava_obec | C | 3 | 0 |  | neovereno |
| Státní fond audiovize (`sfa`) | statni_fond | C | 8 | 0 |  | neovereno |
| Státní fond kultury (`sfk`) | statni_fond | C | 1 | 0 |  | neovereno |
| Nadace Sirius (`sirius`) |  | C | 1 | 0 |  | neovereno |
| Nadace Veronica (`veronica`) |  | C | 1 | 0 |  | neovereno |
| Vinařský fond (`vinarskyfond`) | statni_fond | C | 5 | 0 |  | neovereno |
| Úřad vlády ČR (`vlada`) | ministerstvo | B | 7 | 0 | 2026-10-09 | ok |
| Nadace Jakuba Voráčka (`voracek`) |  | ? | 1 | 0 |  | bez_cesty |

Třídy obnovy: A strukturní ingest · B vlastní parser · C model · T přepsaný extraktor (obnovu předstírá) · F zmrazený · ? bez zapsané cesty. Inventář: `data/sources.json`.
