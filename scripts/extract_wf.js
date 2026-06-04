export const meta = {
  name: 'layer2-extract',
  description: 'Vrstva 2 (LLM): extrakce polí oportunity z PLNÉHO textu+příloh. 2 typy: grant (výzva; výsledkový tvar přes prijemci[]) + foundation_mission. Vysvětlující prompt (jak to pozná člověk), ne slovník. Status NEvyplňuje (počítá kód). 1 oportunita = 1 agent.',
  phases: [{ title: 'Extract', detail: 'pole per typ, 1 dokument/agent' }],
}

// args = pole cest /tmp/.../<typ>_NN.json | {paths,model} | {dir,count} ; typ z názvu (grant_/mission_)
const ARG = (typeof args === 'string') ? JSON.parse(args) : args
const PATHS = Array.isArray(ARG) ? ARG
  : (ARG && ARG.dir && Array.isArray(ARG.indices))
    ? ARG.indices.map((i) => `${ARG.dir}/${ARG.prefix || 'g'}_${String(i).padStart(4, '0')}.json`)  // ARG.indices = konkrétní (roztroušené) indexy
    : (ARG && ARG.dir && ARG.count)
      ? Array.from({ length: ARG.count }, (_, i) => `${ARG.dir}/${ARG.prefix || 'g'}_${String((ARG.from || 0) + i).padStart(4, '0')}.json`)  // ARG.from = offset (dopočet souvislého bloku)
      : ((ARG && ARG.paths) || [])
const MODEL = (ARG && !Array.isArray(ARG) && ARG.model) || 'sonnet'   // Haiku na bohatém schématu malformuje → default sonnet; přepiš {paths|dir, model}
const typeOf = (p) => p.includes('/mission_') ? 'foundation_mission' : 'grant'

const SCHEMAS = {
  grant: {
    type: 'object', required: ['title'],
    properties: {
      title: { type: 'string' },
      oblast: { type: 'array', items: { type: 'string' } },
      focus_area: { type: ['string', 'null'] },
      open_from: { type: ['string', 'null'], description: 'YYYY-MM-DD | null' },
      deadline: { type: ['string', 'null'], description: 'HLAVNÍ lhůta podání: YYYY-MM-DD | průběžně | null' },
      deadliny: { type: 'array', items: { type: 'object', properties: { datum: { type: 'string' }, kontext: { type: 'string' } } }, description: 'všechny termíny podání (kola/podprogramy)' },
      obdobi_realizace: { type: ['string', 'null'], description: 'kdy se projekt realizuje (≠ lhůta podání)' },
      castky: { type: 'array', items: { type: 'object', properties: { typ: { type: 'string', description: 'alokace|max_zadatel|min_zadatel|mira_pct|jine' },
          hodnota: { type: ['number', 'string'] }, kontext: { type: 'string' } } } },
      vyse_hlavni_czk: { type: ['number', 'null'], description: 'headline strop na žadatele; jinak alokace; null' },
      spoluucast: { type: ['boolean', 'null'] },
      eligible_applicants: { type: ['string', 'null'] },
      typ_zadatele: { type: 'array', items: { type: 'string' } },
      cilova_skupina: { type: 'array', items: { type: 'string' } },
      region: { type: 'array', items: { type: 'object', properties: { nazev: { type: ['string', 'null'] }, obec: { type: ['string', 'null'] }, okres: { type: ['string', 'null'] },
          kraj: { type: ['string', 'null'] }, celostatni: { type: 'boolean' } } } },
      forma_podpory: { type: 'array', items: { type: 'string' } },
      zdroj_financovani: { type: 'array', items: { type: 'string' } },
      rezim_prijmu: { type: ['string', 'null'], description: 'jednorazova_vyzva|prubezna|kolova' },
      delka: { type: ['string', 'null'], description: 'jednoleta|viceleta' },
      how_to_apply: { type: ['string', 'null'] },
      required_attachments: { type: 'array', items: { type: 'string' }, description: 'co dokládá ŽADATEL' },
      dokumenty: { type: 'array', items: { type: 'object', properties: { popis: { type: 'string' },
          role: { type: 'string', description: 'vyhlaseni|formular_zadosti|pravidla_podminky|vzor_smlouvy|vysledky|metodika|priloha' } } } },
      kontakt: { type: 'object', properties: { osoba: { type: ['string', 'null'] }, email: { type: ['string', 'null'] }, telefon: { type: ['string', 'null'] } } },
      cislo_vyzvy: { type: ['string', 'null'] },
      hodnotici_kriteria: { type: ['string', 'null'] },
      prijemci: { type: 'array', items: { type: 'object', properties: { nazev: { type: 'string' }, ico: { type: ['string', 'null'] },
          castka_czk: { type: ['number', 'null'] }, ucel: { type: ['string', 'null'] }, rok: { type: ['string', 'null'] } } },
        description: 'JEN když dokument je výsledková listina (komu kolik přiděleno); jinak prázdné' },
      dalsi_datumy: { type: 'array', items: { type: 'object', properties: { datum: { type: 'string' }, popis: { type: 'string' } } }, description: 'každé další datum + co znamená' },
      dalsi_castky: { type: 'array', items: { type: 'object', properties: { castka: { type: ['number', 'string'] }, popis: { type: 'string' } } }, description: 'každá další částka + co znamená' },
      source_doc: { type: ['string', 'null'] },
      evidence: { type: 'object', additionalProperties: { type: 'string' }, description: 'pro KAŽDÉ vyplněné pole doslovná citace (klíč = název pole)' },
    },
  },
  foundation_mission: {
    type: 'object', required: ['name'],
    properties: {
      name: { type: ['string', 'null'] },
      mission: { type: ['string', 'null'] },
      support_topics: { type: 'array', items: { type: 'string' } },
      cilova_skupina: { type: 'array', items: { type: 'string' } },
      regions: { type: 'array', items: { type: 'string' } },
      forma_podpory: { type: 'array', items: { type: 'string' } },
      jak_oslovit: { type: ['string', 'null'], description: 'jak požádat o podporu / oslovit organizaci' },
      kontakt: { type: 'object', properties: { osoba: { type: ['string', 'null'] }, email: { type: ['string', 'null'] }, telefon: { type: ['string', 'null'] } } },
      source_doc: { type: ['string', 'null'] },
      evidence: { type: 'object', additionalProperties: { type: 'string' } },
    },
  },
}

const COMMON = `Přečti celý dokument (Read tool): title, body (PLNÉ tělo), attachments_md (PLNÝ text VŠECH příloh), volitelně related_context (kontext napojeného programu — grounding, ne přepis). Dívej se jen na TUTO jednu oportunitu. Ber jen co v textu je (NEHALUCINUJ); co tam není, nech prázdné/null. Ke KAŽDÉMU vyplněnému poli vrať do \`evidence\` PŘESNOU doslovnou citaci ze zdroje (verbatim, ať ji lze najít fulltextem; klíč = název pole). Status (otevřeno/zavřeno) NEŘEŠ — dopočítá kód.`

const SYS = {
  grant: `Jsi extraktor české dotační výzvy. Poskládej obraz JEDNÉ výzvy tak, jak by si ho udělal člověk shánějící grant. ${COMMON}

NA CO SE PTÁŠ (a jak to v textu poznáš):

• Na co je podpora (oblast[], focus_area): jaký obor života grant rozvíjí — poznáš z účelu a aktivit, ne z toho, kdo vyhlašuje; klidně víc oborů zároveň. [kultura, sport/volný čas, sociální, zdraví, vzdělávání/mládež, prostředí, cest. ruch, věda, infrastruktura, bezpečnost, rodina… nesedí-li, pojmenuj vlastním krátkým termínem]. focus_area = totéž jednou věcnou větou.

• Časové údaje — lhůta podání ≠ období realizace (otevřené i uzavřené stejně):
  - open_from/deadline = okno pro PODÁNÍ žádosti; vytěž jak v textu stojí, ať je v budoucnu (otevřená) nebo v minulosti (uzavřená). Otevřenost NEROZHODUJEŠ — počítá kód z deadline vs dnešek.
  - U proběhlé výzvy text zdůrazňuje JINÁ data (vyhlášení, výsledky, realizace) — žádné z nich není deadline podání.
  - obdobi_realizace = kdy se projekt uskutečňuje/peníze utrácí; nezávislé na podání, u uzavřené klidně v budoucnu.
  - prodloužení → pozdější datum jako hlavní deadline; průběžný příjem → "průběžně"; víc kol → všechny do deadliny[].

• Kolik peněz a pro koho (castky[], vyse_hlavni_czk, spoluucast): rozliš kolik má program celkem (alokace) vs kolik nejvíc dostane jeden žadatel (strop) — dvě perspektivy. NEPATŘÍ sem: částka, kterou žadatel POŽADUJE; částka, kterou už někdo DOSTAL (to je výsledek → prijemci[]). Návratná půjčka/úvěr (jistina, úroky) ≠ dotace → forma_podpory. "Není stanovena" → prázdné. vyse_hlavni_czk = strop na žadatele, jinak alokace. Vlastní dofinancování → spoluucast=true.

• Kdo může žádat (eligible_applicants, typ_zadatele[]): subjekt, který o peníze žádá a projekt uskuteční. Pomůcka "kdo dostane a utratí peníze". [neziskovka (spolek/o.p.s./nadace/církev), fyzicka_osoba, osvc_podnikatel, firma, prispevkova_organizace, obec_verejny_subjekt, skola_vyzkumna_org — klidně víc; jemnější (sportovni_klub, cirkev…) pojmenuj]

• Komu to má pomoct (cilova_skupina[]): lidé, kterým má výsledek prospět — skoro vždy JINÝ subjekt než žadatel. Pomůcka "komu to pomůže". [deti_mladez, senioři, osoby_se_zdravotnim_postizenim, pacienti, rodiny, ohrožené skupiny, veřejnost…]

• Kde to platí (region[]): územní záběr — kde se smí čerpat / kde musí žadatel sídlit či působit ("se sídlem v…", "na území…"). Z místa dopočítej obec/okres/kraj svou znalostí české geografie; celostátní označ celostatni=true. NEZAMĚŇUJ s adresou podatelny. Víc území → víc záznamů.

• Jak je grant zarámovaný: forma_podpory[] (dotace / zapujcka_uver / stipendium / cena_soutez / vecny_dar) · zdroj_financovani[] (narodni_rozpocet / eu_fondy / npo / ehp_norsko / krajsky / vlastni_zdroje — poznáš ze zmínek o OP, NPO, dárci) · rezim_prijmu (jednorazova_vyzva / prubezna / kolova) · delka (jednoleta / viceleta).

• Jak požádat a co k tomu: how_to_apply (jakou cestou — datová schránka/portál/pošta/osobně) · required_attachments[] (co dokládá ŽADATEL — NEzaměňuj se soubory KE STAŽENÍ, ty → dokumenty[]) · dokumenty[] {popis, role: vyhlaseni|formular_zadosti|pravidla_podminky|vzor_smlouvy|vysledky|metodika|priloha} · kontakt {osoba,email,telefon} (na dotazy) · cislo_vyzvy · hodnotici_kriteria (podle čeho se hodnotí).

• VÝSLEDKOVÝ TVAR (prijemci[]): když dokument JE výsledková listina ("komu kolik přiděleno"), vyplň prijemci[] {nazev, ico, castka_czk, ucel, rok} — kdo už dostal, kolik, na co. Jde o ROZHODNUTÉ přidělení (ne požadovaná výše, ne strop programu). Když výsledky nejsou, nech prázdné.

• AŤ NIC NEZTRATÍME (dalsi_datumy[], dalsi_castky[]): každé DALŠÍ datum a částku v dokumentu ulož sem s krátkým popiskem, co znamenají. Nejistý údaj radši sem než natlačit do nesprávného hlavního pole.

HLAVNÍ vs VÍC: u dat a částek vrať operativní hlavní hodnotu + úplný seznam; u oblast/cílová/region/forma/zdroj vrať všechny relevantní.`,

  foundation_mission: `Jsi extraktor POSLÁNÍ organizace / oblasti podpory — dokument popisuje, ČEMU se nadace/fond trvale věnuje, ne konkrétní výzvu s termínem. ${COMMON}
• name: název organizace.
• mission: čemu se věnuje, jednou-dvěma větami jak by to řekl člověk.
• support_topics[]: oblasti, které obecně podporuje.
• cilova_skupina[]: komu pomáhá (komu projekty prospívají).
• regions[]: kde působí.
• forma_podpory[]: jak podporuje (dotace/dary/stipendia…).
• jak_oslovit: jak požádat o podporu / oslovit organizaci, je-li uvedeno. kontakt {osoba,email,telefon}.
⚠ Mise = TRVALÉ zaměření ("dlouhodobě podporujeme…"), ne jednorázová výzva. Má-li dokument konkrétní deadline a alokaci pro žadatele → není to mise (je to výzva).`,
}

// SMĚR (B): SOUBOR je JEDINÝ kanál. StructuredOutput na bohatém vnořeném schématu láme XML tool-arg
// (→ prázdné {} → re-prompt smyčka 270×–1699×). Místo toho agent JSON ZAPÍŠE Write toolem do
// /tmp/out/<basename>.json (plochý string content = robustní, nelomí se). Návratová hodnota NENESE JSON
// (zdražoval by a re-emise láme escaping) — agent vrátí jen krátké `hotovo`. Velikost + vyplněnost polí
// měříme deterministicky ZE SOUBORŮ (scripts/repair_out.py), ne z textu. Drobné escaping vady v českých
// verbatim citacích v `evidence` srovná batch `json_repair` NAD soubory PO doběhu. Žádné ořezávání.
const OUTDIR = (ARG && !Array.isArray(ARG) && ARG.outdir) || '/tmp/out'
const KEYS = { grant: Object.keys(SCHEMAS.grant.properties), foundation_mission: Object.keys(SCHEMAS.foundation_mission.properties) }
// Kontrakt TVARU (jen názvy klíčů vnořených objektů) — text-režim jinak tříští tvar (region[] přišel
// jako {nazev,typ} i {obec,okres,kraj}). Odvozeno ze SCHEMAS → žádný drift. Je to FORMÁT, ne slovník hodnot.
const subKeys = (s) => {
  const it = s.type === 'array' ? (s.items || {}) : s
  return (it.type === 'object' && it.properties) ? Object.keys(it.properties) : null
}
const shapeHint = (t) => {
  const props = SCHEMAS[t].properties
  const parts = []
  for (const [k, s] of Object.entries(props)) {
    if (k === 'evidence') continue
    const sk = subKeys(s)
    if (sk) parts.push(`${k}${s.type === 'array' ? '[]' : ''}={${sk.join(',')}}`)
  }
  return parts.join('; ')
}
const SHAPE = { grant: shapeHint('grant'), foundation_mission: shapeHint('foundation_mission') }
phase('Extract')
const out = await parallel(PATHS.map((path) => () => {
  const t = typeOf(path)
  const base = path.split('/').pop()
  const outpath = `${OUTDIR}/${base}`
  return agent(
    `${SYS[t]}\n\nDokument k načtení (Read tool): ${path}\n` +
    `Sestav JEDEN JSON objekt se VŠEMI klíči (chybějící hodnota = null nebo []): ${KEYS[t].join(', ')}.\n` +
    `Tvar vnořených objektů (PŘESNĚ tyto klíče, nic nepřejmenovávej): ${SHAPE[t]}. evidence={nazev_pole: doslovná citace}.\n` +
    `Pak ho ZAPIŠ Write toolem rovnou do souboru: ${outpath} — adresář existuje a soubor zatím ne, takže NEvypisuj adresář (žádné ls/mkdir) a NEčti cílový soubor předem, jen Write. Obsahem souboru je POUZE ten JSON objekt (žádný \`\`\`json fence, žádný komentář, jen syrový JSON, UTF-8 s diakritikou).\n` +
    `Po zápisu odpověz JEN slovem \`hotovo\` — NEVRACEJ JSON ani žádný další text (soubor je výstup).`,
    { label: `${t}:${base}`, phase: 'Extract', model: MODEL }
  ).then(text => ({ path, outpath, type: t, ok: true })).catch(e => ({ path, outpath, type: t, ok: false, error: String(e) }))
}))

log(`hotovo: ${out.filter(r => r.text).length}/${PATHS.length}`)
return out
