#!/usr/bin/env python3
"""Rozšíření consolidation_maps o free-text varianty z LLM extrakce (Haiku) → kanon.

Explicitní variant→kanon pro smysluplné; co tu není (šum / špatná fazeta), zahodí finální
drop-pass v consolidate-cyklu (vynutí facet ∈ kanonický slovník). Data-driven mapa (task #2),
ne runtime keyword. Po spuštění: re-consolidate + drop-rest.

Usage: python3 scripts/extend_maps_extract.py   (zapíše do data/consolidation_maps.json)
"""
import json

MAPS = "data/consolidation_maps.json"

OBLAST = {
 "Regionální rozvoj":"bydleni_infrastruktura","regionální rozvoj":"bydleni_infrastruktura","rozvoj":"bydleni_infrastruktura",
 "rozvoj kraje":"bydleni_infrastruktura","rozvoj_kraje":"bydleni_infrastruktura","rozvoj obcí":"bydleni_infrastruktura",
 "rozvoj venkova":"bydleni_infrastruktura","venkov":"bydleni_infrastruktura","venkov/rozvoj venkova":"bydleni_infrastruktura",
 "místní rozvoj":"bydleni_infrastruktura","komunální plánování":"bydleni_infrastruktura","veřejné prostory":"bydleni_infrastruktura",
 "architektura":"kultura_umeni","umění":"kultura_umeni","společenské akce":"kultura_umeni","společenské události":"kultura_umeni",
 "azyl":"socialni_sluzby","migrace":"socialni_sluzby","sociální péče":"socialni_sluzby","sociální péče a zdravotnictví":"socialni_sluzby",
 "bezpečnost a ochrana zdraví":"bezpecnost","bezpečnost dopravy":"bydleni_infrastruktura","prevence kriminality":"bezpecnost",
 "požární ochrana":"bezpecnost","kybernetická bezpečnost":"bezpecnost",
 "cyklistická doprava":"bydleni_infrastruktura","cyklistika":"sport_volny_cas","doprava":"bydleni_infrastruktura",
 "doprava/mobilita":"bydleni_infrastruktura","doprava_mobilita":"bydleni_infrastruktura","mobilita":"bydleni_infrastruktura",
 "telematika":"bydleni_infrastruktura","veřejná doprava":"bydleni_infrastruktura",
 "demokracie a lidská práva":"komunitni_rozvoj","lidská práva":"komunitni_rozvoj","participace veřejnosti":"komunitni_rozvoj",
 "komunita":"komunitni_rozvoj","komunitní život":"komunitni_rozvoj","podpora_komunity":"komunitni_rozvoj","filantropie":"komunitni_rozvoj",
 "fundraising":"komunitni_rozvoj","rozvoj neziskového sektoru":"komunitni_rozvoj","partnerské vztahy":"komunitni_rozvoj","kvalita života":"komunitni_rozvoj",
 "digitalizace":"veda_vyzkum","e-government":"veda_vyzkum","eGovernment":"veda_vyzkum","informatika":"veda_vyzkum",
 "it_digitalizace":"veda_vyzkum","inovace":"veda_vyzkum","výzkum":"veda_vyzkum",
 "duševní zdraví":"zdravi","ochrana zdraví":"zdravi","zdravotnictví":"zdravi","zdravotní":"zdravi","zdravotnické povolání":"zdravi","zdravotnické vzdělávání":"zdravi",
 "dětství":"vzdelavani_mladez","mládež":"vzdelavani_mladez","podpora mládeže":"vzdelavani_mladez","školské":"vzdelavani_mladez","školství a vzdělávání":"vzdelavani_mladez",
 "volný čas dětí a mládeže":"sport_volny_cas",
 "ekologická výchova":"zivotni_prostredi","energetika":"zivotni_prostredi","energie":"zivotni_prostredi","myslivost":"zivotni_prostredi",
 "ochrana přírody":"zivotni_prostredi","voda":"zivotni_prostredi","vodohospodářství":"zivotni_prostredi","zemědělství":"zivotni_prostredi",
 "zemědělství a chov zvířat":"zivotni_prostredi","Životní prostředí a zemědělství":"zivotni_prostredi",
 "ekonomika":"podnikani","ekonomika/podnikání":"podnikani","hospodářství":"podnikani","obchod":"podnikani","obchod a maloobchod":"podnikani",
 "obchod a podnikání":"podnikani","obchod a služby":"podnikani","podnikání a ekonomika":"podnikani","podnikání a inovace":"podnikani",
 "podnikání/obchod":"podnikani","průmysl a stavebnictví":"podnikani","řemesla":"podnikani","vzdělávání/podnikání":"podnikani","zaměstnanost":"podnikani",
 "lázeňství":"cestovni_ruch","turismus":"cestovni_ruch",
 "veřejná správa":"ostatni","správa":"ostatni","veřejné služby":"ostatni","technická pomoc":"ostatni","různé oblasti":"ostatni","rozvoj_kraje ":"ostatni",
}

TYP = {
 # neziskovky
 **{k:"neziskovka" for k in ["NNO","NNO zakládané uvedenými typy oprávněných žadatelů","nno","npo","Právnická osoba - nestátní nezisková organizace (nadace a nadační fond, o.p.s., zapsaný spolek, ústav)",
   "nestátní nezisková organizace","nestátní neziskové organizace","neziskovka - spolek/sdružení","neziskovka_spolek","nezisková_organizace","niziskovka","nadační_fondy",
   "o.p.s.","o_p_s","obecne_prospesne_spolecnosti","obecně prospěšné společnosti","občanská_sdružení","obcinska_sdruzeni","ops_nadace_spolek","pobočné spolky","spolky",
   "sdruzeni","sdružení","zapsany_spolek","ustav_podle_zakona_89_2012","ustavy","ústavy","spolecnost_sdruzeni","sdruzenina_organizace","organizace veřejné prospěšnosti",
   "veřejně_prospěšné_organizace","organizace_nekomercniho_charakteru","mistni_akcni_skupiny","myslivecke_spolky","chovatelske_organizace","pacientska_organizace",
   "telovychovna_organizace","zajmove_soubory","sborjednotlivychhasicu","sbory_dobrovolných_hasičů","Sbory dobrovolných hasičů","osadni_vybor","komunitní uskupení",
   "organizace_deti_mladeze","organizace_ve_volnem_case_deti_mladeze","volnočasová_organizace","krouzky","socialni_podnik","poskytovatel sociálních služeb",
   "poskytovatel_socialni_sluzby","poskytovatel_socialnich_sluzeb","poskytovatele_socialnich_sluzeb","registrovane_socialni_sluzby","socialni_sluzba","socialni_sluzba_registrovana",
   "socialni_sluzbicka_organizace","socialni_sluzby_poskytovatel","socialni_sluzby_subjekt","sociální_organizace","sociální_sluzby_poskytovatel","organizace_v_socialni_peci",
   "realizátor_veřejně_prospěšných_činností","organizace_realizujici_verejne_prospesne_cinnosti"]},
 # církve
 **{k:"cirkev" for k in ["cirekevni_pravnicka_osoba","cirkevni_pravnicka_osoba","cirkvena_právnická_osoba","církevní právnické osoby","církevní společnost",
   "církevní společnosti","církevní_organizace","církve","náboženská společnost","náboženské společnosti","náboženské_společnosti"]},
 # firmy
 **{k:"firma" for k in ["Právnická osoba - obchodní společnost (a.s., s.r.o., v.o.s., státní podnik)","firma_obchodni_spolecnost","firma_s_r_o_nebo_jina_firma",
   "obchodna_spolecnost","obchodní_společnost","obchodní_společnosti","mala_stredni_podnik","velky_podnik","stat_podnik","státní podniky","dopravce","dopravni_subjekt",
   "subjekt podnikající v kultuře","sluzby_nadregionalni_pusobnosti"]},
 # OSVČ
 **{k:"osvc_podnikatel" for k in ["OSVČ","osvc","fyzicka_osoba_podnikajici","fyzicka_osoba_podnikatel","obchodní_podnikatel","podnikatel","podnikatelé","začínající pořadatelé"]},
 # fyzická osoba
 **{k:"fyzicka_osoba" for k in ["fyzicka_osoba_jako_zastupce","handicapovaný žadatel","student","vlastnici_obytnych_budov","vlastnik_nemovitosti","vlastnik_pamiatky",
   "vlastníci_loveckich_psu_a_dravcu","myslivci"]},
 # obec / veřejný subjekt / stát
 **{k:"obec_verejny_subjekt" for k in ["Organizační složky státu","organizační složka státu","organizační složky státu","OSS","oss","PO OSS","po_oss","hlavní město Praha",
   "kraj_verejny_subjekt","kraje","krajska_spravni_organizace","krajsky_subjekt","město","městské části","obce","stát_verejny_subjekt","státní organizace","stat_organizace",
   "svazek obcí","svazek_obci","svazky_obci","dobrovolne_svazky_obci","dobrovolny_svazek_obci","verejne_organizace","verejne_subjekty","verejny_subjekt","veřejné subjekty",
   "veřejný subjekt","veřejné subjekty","zarizeni_verejneho_sektoru","organizace poskytující veřejnou službu","Krajské hygienické stanice","turisticka_informacni_centra",
   "telo_vychodova_jednota","pospolu_pracujici_verejne_subjekty"]},
 # příspěvkové organizace
 **{k:"prispevkova_organizace" for k in ["Příspěvková organizace kraje","Příspěvková organizace obce nebo státu","pospevkova_organizace","prijspevkova_organizace",
   "prispevkova_organizace (zřizované obcemi)","příspěvkové organizace","příspěvkové organizace organizačních složek státu",
   "organizace zřizované nebo zakládané Prahou","organizace zřizované nebo zakládané kraji","organizace zřizované nebo zakládané obcemi","organizace zřízená nebo založená obcí",
   "organizace_zalozena_staty_nebo_krajem","organizace_zrizovana_krajem_nebo_obci","organizace_zrizovana_obci","organizace_zřizovaná_krajem_obcí","prispevkova_organizace_kraje",
   "divadelní instituce","divadlo","mestske_divadlo","profesionalni_divadla","professionalni_divadlo","symfonicke_orchestry","kulturni_organizace","kulturni_organizace_ochotnicka_skupina",
   "kultura_subjekt","zdravotnicka_organizace","zdravotnicka_zarizeni","zdravotnicky_subjekt","zdravotnická_organizace","organizace_v_oblasti_zdravotnictvi",
   "poskytovatel_zdravotni_sluzby","poskytovatelé zdravotnické záchranné služby","organizace_pemci_pamatok","organizace_ze_oblasti_kultury"]},
 # školy / výzkum
 **{k:"skola_vyzkumna_org" for k in ["skola","školy","základní školy","mateřské školy","univerzity","právnická osoba poskytující služby školám","organizace_ze_oblasti_skolstvi_a_vzdelavani"]},
 # sportovní klub
 **{k:"sportovni_klub" for k in ["sportovni_kluby","sportovni_organizace","sportovní organizace"]},
}

CILOVA = {
 **{k:"deti_mladez" for k in ["deti","děti","malé děti","mladiství","mladí lidé","mladi_dospeli","dětství","děti_v_kroužcích","absolventi řemeslných oborů"]},
 **{k:"rodiny" for k in ["matky","ohrožené rodiny","rodice_a_deti","rodiny s dětmi","domácnosti","domácnosti nízkopříjmové"]},
 **{k:"ohrozene_skupiny" for k in ["LGBTIQ+ lidé","dlouhodobe_nezamestnaní","osoby bez přístřeší","osoby_bez_pristresí","osoby v krizi","osoby v náročných životních situacích",
   "osoby v obtížné životní situaci","osoby v sociální krizi","osoby v sociální nouzi","osoby v sociální potřebě","osoby v sociální tísni","osoby_v_nepriaznive_socialni_situaci",
   "osoby_v_neprizive_socialni_situaci","osoby_v_ohrozeni","osoby_v_ohrozeni_socialni_vylucenim","osoby_v_ohrození","osoby_v_socialne_neprizive_situaci","osoby_v_socialne_nevyhovujicim_stavu",
   "osoby_v_socialni_nouzi","osoby_v_tezke_situaci","osoby_v_tezke_socialni_situaci","osoby_z_ohrozenych_skupin","rizikové_skupiny","socialne_znevyhodne_skupiny","sociálně znevýhodněné osoby",
   "obeti_trestne_cinnosti","oběti_trestných_činů","osoby_ohrožené_nasilim","osoby_ohrožené_predluženosti","osoby_ohrožené_zavislostmi","osoby_se_zavi_slosti_na_drogach",
   "osoby_v_trestu","děti_v_sociální_nouzi","deti_v_nouzi","děti_z_rodin_ohrožených_chudobou","děti_s_materiální_deprivací","děti_s_potravinou_deprivací","nízkopříjmové domácnosti",
   "domácnosti se spalovacími zdroji na pevná paliva","uprchlíci/osoby zasažené válkou na Ukrajině"]},
 **{k:"osoby_se_zdravotnim_postizenim" for k in ["lidé s duševním onemocněním","lidé se smyslovým postižením","osoby s duševním onemocněním","osoby s mentálním postižením",
   "osoby s PAS","děti s poruchou autistického spektra","osoby_s_poruchami_autistickeho_spektra","osoby se smyslovým postižením","osoby se zdravotním postižením",
   "osoby_s_dusevnim_onemocnenim","osoby_duševního_onemocnění","osoby_s_omezenou_schopnosti_orientace","osoby_s_omezenou_schopnosti_pohybu"]},
 **{k:"uzivatele_socialnich_sluzeb" for k in ["osoby náročné na péči","osoby ve věku vyžadující sociální péči","osoby_v_pece","osoby_vyrustajici_v_nahradni_rodinne_peci"]},
 **{k:"cizinci_migranti" for k in ["migranti_a_azylanti","uprchlíci"]},
 **{k:"verejnost" for k in ["cestující","cestující v přepravě","cestující veřejné dopravy","cyklisté","chodci","turiste","turisti","turisté","turizmus","účastníci cestovního ruchu",
   "rezidenti","rezidenti_města","fyzické osoby","fyzicke_osoby_se_sídlem_na_území_města","dospeli","dospělí","dobrovolnici","komunita","komunity","místní komunita","místní komunity",
   "koneční uživatelé energií","verejna_verejnost"]},
 **{k:"dobrovolni_hasici" for k in ["jednotky_sdh_obci","složky IZS"]},
 **{k:"kulturni_pracovnici" for k in ["neprofesionální umělecké soubory","umělci","tradičníí řemeslníci"]},
 **{k:"studenti" for k in ["univerzity","školy"]},
 **{k:"zdravotnici" for k in ["osoby_vzdělaní_v_oborech_klinická_psychologie_klinická_logopedie"]},
}


# forma_podpory kanon: dotace, zapujcka_uver, stipendium, cena_soutez, vecny_dar (služby/mise nadací → drop)
FORMA = {
 **{k:"stipendium" for k in ["stipendia","sociální stipendia","stipendium"]},
 **{k:"dotace" for k in ["nadační příspěvky","nadační příspěvky (granty)","nadační příspěvek","grant","granty","finanční granty",
   "finanční dary","finanční podpora","finanční podpora (operační programy, komunitární programy)","Dotace / granty","kreativní vouchery",
   "dotace na bilaterální projekty","granty neziskovým organizacím","individuální finanční příspěvky","jednorázové finanční příspěvky",
   "finanční příspěvky jednotlivcům (přímá podpora žadatelů)","finanční podpora (granty/dary) partnerským organizacím a projektům",
   "zaměstnanecké granty","mimořádné výzvy","individuální finanční příspěvky"]},
 **{k:"zapujcka_uver" for k in ["úvěry","záruky","kvazikapitálové nástroje (mezaninové financování, podřízené úvěry)",
   "finanční nástroje ze zdrojů EU (ESIF, InvestEU)"]},
 **{k:"cena_soutez" for k in ["novinářská cena"]},
 **{k:"vecny_dar" for k in ["dárcovské certifikáty"]},
}
# rezim_prijmu kanon: jednorazova_vyzva, kolova, prubezna (delka hodnoty mis-zařazené → drop)
REZIM = {"vyzva":"jednorazova_vyzva","jednorocni":"jednorazova_vyzva","kontinuální":"prubezna","individuální":"prubezna",
 "mimořádné žádosti":"prubezna","mimořádné žádosti v průběhu roku":"prubezna","rocni_vyzvy":"kolova","hromadne":"kolova"}
DELKA = {"jednoleté":"jednoleta"}


def main():
    m = json.load(open(MAPS, encoding="utf-8"))
    added = {"oblast": 0, "typ_zadatele": 0, "cilova_skupina": 0, "forma_podpory": 0, "rezim_prijmu": 0, "delka": 0}
    for facet, add in (("oblast", OBLAST), ("typ_zadatele", TYP), ("cilova_skupina", CILOVA),
                       ("forma_podpory", FORMA), ("rezim_prijmu", REZIM), ("delka", DELKA)):
        for k, v in add.items():
            if m[facet].get(k) != v:
                m[facet][k] = v; added[facet] += 1
    json.dump(m, open(MAPS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"MARKER": "EXTEND_MAPS", "added": added}, ensure_ascii=False))


if __name__ == "__main__":
    main()
