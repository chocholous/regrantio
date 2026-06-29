#!/usr/bin/env python3
# Vrstva 2 extrakce pro MPO – národní programy (mpo.gov.cz; parser scripts/mpo.py). 9 programů.
# POZN: OP TAK / OP PIK (EU) sem NEpatří (P3). Program-level záznamy: konkrétní lhůty výzev jsou
# v navázaných aktualitách (ne na landing) → u programů „mezi koly"/V&V soutěží deadline=null=unknown;
# ukončené dle dat z obsahu (TRIO 2022, Czech Rise Up 2024) → closed; průběžné → open. amount většinou
# null (výše v podmínkách výzvy). Status NEvyplňuji (počítá kód).
import json, os

CR = [{"nazev": "Česká republika", "obec": None, "okres": None, "kraj": None, "celostatni": True}]
HOW_VS = "Žádost se podává v rámci veřejné soutěže ve výzkumu, vývoji a inovacích dle podmínek příslušné výzvy programu (elektronicky přes informační systém poskytovatele)."
HOW_VYZVA = "Žádost se podává dle podmínek vyhlášené výzvy programu (elektronicky)."
out = {}
def g(idx, **f):
    out[f"grant_{idx:02d}"] = f

g(0, title="Program Obchůdek 2021+ (podpora provozu venkovských prodejen)",
  oblast=["vnitřní obchod", "venkov", "regionální rozvoj"],
  focus_area="Dotace na financování provozních výdajů maloobchodních prodejen s potravinami a smíšeným zbožím v obcích do 1 000 obyvatel (příp. místních částech); rozdělováno prostřednictvím krajů. V. výzva 2026, program prodloužen do roku 2028.",
  open_from=None, deadline="průběžně",
  castky=[{"typ": "max_zadatel", "hodnota": 130000}, {"typ": "alokace", "hodnota": 49400000}],
  vyse_hlavni_czk=130000, spoluucast=True,
  eligible_applicants="Provozovatelé maloobchodních prodejen potravin a smíšeného zboží v obcích do 1 000 obyvatel; žádosti se podávají prostřednictvím krajů (kraj získá až 3,8 mil. Kč).",
  typ_zadatele=["firma", "osvc_podnikatel", "obec_verejny_subjekt"], cilova_skupina=["obyvatelé venkova"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="prubezna", delka="jednoleta", how_to_apply="Žádost podává provozovatel prodejny prostřednictvím svého kraje dle krajské výzvy programu Obchůdek 2021+.",
  cislo_vyzvy="Obchůdek 2021+ (V. výzva 2026)",
  evidence={"title": "Program Obchůdek 2021+", "vyse_hlavni_czk": "prodejna, která je pouze jediná v obci, může získat až 130 tisíc Kč"})

g(1, title="Program TREND – podpora průmyslového výzkumu a experimentálního vývoje",
  oblast=["věda a výzkum", "průmysl"],
  focus_area="Podpora průmyslového výzkumu a experimentálního vývoje pro zvýšení mezinárodní konkurenceschopnosti podniků; garant MPO, poskytovatel Technologická agentura ČR (TAČR). Schválen 2019, prodloužen usnesením vlády 2025.",
  open_from=None, deadline=None,
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Podniky (včetně malých a středních) samostatně nebo ve spolupráci s výzkumnými organizacemi.",
  typ_zadatele=["firma", "skola_vyzkumna_org"], cilova_skupina=["podniky", "výzkumní pracovníci"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="kolova", delka="viceleta", how_to_apply=HOW_VS, cislo_vyzvy="TREND",
  evidence={"title": "Program na podporu průmyslového výzkumu a experimentálního vývoje TREND", "eligible_applicants": "poskytovatelem podpory je Technologická agentura České republiky"})

g(2, title="Program TRIO – podpora průmyslového výzkumu a vývoje (ukončený)",
  oblast=["věda a výzkum", "průmysl"],
  focus_area="Podpora projektů průmyslového výzkumu a experimentálního vývoje se zaměřením na klíčové technologie (KETs). Program realizován formou veřejných soutěží; financování projektů do roku 2022 včetně (ukončen).",
  open_from=None, deadline="2022-12-31",
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Podniky ve spolupráci s výzkumnými organizacemi.",
  typ_zadatele=["firma", "skola_vyzkumna_org"], cilova_skupina=["podniky", "výzkumní pracovníci"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="kolova", delka="viceleta", how_to_apply=HOW_VS, cislo_vyzvy="TRIO",
  evidence={"title": "Program TRIO", "deadline": "prodloužení trvání programu (financování vybraných projektů výzkumu a vývoje) o jeden rok, tj. do roku 2022 včetně"})

g(3, title="Program TWIST – Transfer, Výzkum, Vývoj a Inovace pro Strategické Technologie",
  oblast=["věda a výzkum", "strategické technologie"],
  focus_area="Program MPO na podporu výzkumu, vývoje a inovací v oblasti strategických technologií (TWIST). Realizace formou veřejných soutěží; proběhla 2. veřejná soutěž (hodnocení návrhů).",
  open_from=None, deadline=None,
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Podniky a výzkumné organizace v oblasti strategických technologií.",
  typ_zadatele=["firma", "skola_vyzkumna_org"], cilova_skupina=["podniky", "výzkumní pracovníci"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="kolova", delka="viceleta", how_to_apply=HOW_VS, cislo_vyzvy="TWIST (2. veřejná soutěž)",
  evidence={"title": "Program MPO na podporu výzkumu, vývoje a inovací TWIST"})

g(4, title="Program The Country for the Future – podpora inovací",
  oblast=["věda a výzkum", "inovace"],
  focus_area="Program MPO na podporu inovací (zavádění inovací do praxe, digitalizace, inovační infrastruktura). Schválen usnesením vlády 2019; realizován formou veřejných soutěží (FX01–FX05).",
  open_from=None, deadline=None,
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Podniky (zejména malé a střední) zavádějící inovace; dle podmínek konkrétní veřejné soutěže.",
  typ_zadatele=["firma", "osvc_podnikatel"], cilova_skupina=["podniky"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="kolova", delka="viceleta", how_to_apply=HOW_VS, cislo_vyzvy="The Country for the Future",
  evidence={"title": "Program na podporu inovací The Country for the Future"})

g(5, title="Technologická inkubace start-upů",
  oblast=["inovace", "start-upy"],
  focus_area="Systémový projekt MPO (realizovaný agenturou CzechInvest) v rámci programu The Country for the Future – přímá i nepřímá podpora vybraných inovativních start-upů (inkubace).",
  open_from=None, deadline="průběžně",
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Inovativní začínající podniky (start-upy) vybrané do programu Technologická inkubace.",
  typ_zadatele=["firma", "osvc_podnikatel"], cilova_skupina=["začínající podnikatelé", "start-upy"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="prubezna", delka="viceleta", how_to_apply="Přihlášky do programu Technologická inkubace přijímá agentura CzechInvest dle aktuálních výzev (technologickainkubace.cz).",
  cislo_vyzvy="Technologická inkubace",
  evidence={"title": "Technologická inkubace start-upů", "eligible_applicants": "operátorem projektu Technologická inkubace je Agentura pro podporu podnikání a investic CzechInvest"})

g(6, title="Program Czech Rise Up 3.0 (ukončený – digitální transformace a inovace, NPO)",
  oblast=["inovace", "digitalizace"],
  focus_area="Dotační program Czech Rise Up 3.0 z Národního plánu obnovy (poradenství pro digitální transformaci podniků, výzkum medicínských řešení). Realizace výzev úspěšně ukončena 26. 3. 2024.",
  open_from=None, deadline="2024-03-26",
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Podniky (digitální transformace, výzkum medicínských řešení).",
  typ_zadatele=["firma"], cilova_skupina=["podniky"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["npo"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW_VYZVA, cislo_vyzvy="Czech Rise Up 3.0",
  evidence={"title": "Program Czech Rise Up 3.0", "deadline": "Realizace výzev Czech Rise Up 3.0 v rámci Národního plánu obnovy byla úspěšně ukončena"})

g(7, title="Program Strategické investice pro klimaticky neutrální hospodářství (NZIA)",
  oblast=["průmysl", "čisté technologie", "energetika"],
  focus_area="Dotace na strategické investice do čistých technologií a klimaticky neutrálního hospodářství (návaznost na Net-Zero Industry Act). Výzva pro předkládání žádostí vyhlášena MPO (1. 12. 2025).",
  open_from=None, deadline=None,
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Podniky realizující strategické investiční projekty v oblasti čistých technologií / klimaticky neutrálního hospodářství.",
  typ_zadatele=["firma"], cilova_skupina=["podniky"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW_VYZVA, cislo_vyzvy="Strategické investice (výzva 2025)",
  dalsi_datumy=[{"datum": "2025-12-01", "popis": "vyhlášení výzvy pro předkládání žádostí"}],
  evidence={"title": "Program Strategické investice pro klimaticky neutrální hospodářství"})

g(8, title="Podpora regenerace brownfieldů pro podnikatelské využití",
  oblast=["regionální rozvoj", "brownfieldy", "průmysl"],
  focus_area="Dotace na projektovou přípravu a regeneraci brownfieldů pro podnikatelské využití (program Podpora projektové přípravy regenerací brownfieldů – Výzva I, a Regenerace brownfieldů pro podnikatelské využití – Výzva II z NPO).",
  open_from=None, deadline=None,
  castky=[], vyse_hlavni_czk=None, spoluucast=True,
  eligible_applicants="Podnikatelé (vlastníci či nabyvatelé brownfieldů) a obce realizující regeneraci brownfieldů pro podnikatelské využití.",
  typ_zadatele=["firma", "obec_verejny_subjekt"], cilova_skupina=["podniky", "obyvatelé"], region=CR,
  forma_podpory=["dotace"], zdroj_financovani=["narodni_rozpocet"],
  rezim_prijmu="jednorazova_vyzva", delka="viceleta", how_to_apply=HOW_VYZVA, cislo_vyzvy="Brownfieldy (Výzva I/II)",
  dalsi_datumy=[{"datum": "2025-09-18", "popis": "Výzva I – Podpora projektové přípravy regenerací brownfieldů"},
                {"datum": "2025-04-28", "popis": "Výzva II – Regenerace brownfieldů pro podnikatelské využití (NPO)"}],
  evidence={"title": "Podpora brownfieldů"})

os.makedirs("data/mpo_out", exist_ok=True)
for k, v in out.items():
    json.dump(v, open(f"data/mpo_out/{k}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(out)} grants to data/mpo_out/ (národní programy; OP TAK/PIK = P3 EU, mimo)")
