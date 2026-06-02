export const meta = {
  name: 'layer2-extract',
  description: 'Vrstva 2 (LLM): Haiku agenti extrahují pole oportunity do schématu podle typu (grant/project/foundation_mission). 1 oportunita = 1 agent, plný text bez stropů. Status NEvyplňuje (počítá kód).',
  phases: [{ title: 'Extract', detail: 'Haiku: pole per typ, 1 dokument/agent' }],
}

// args = pole cest /tmp/q/<typ>_NN.json NEBO {paths, model}; typ se odvodí z názvu (grant_/project_/mission_)
const ARG = (typeof args === 'string') ? JSON.parse(args) : args
const PATHS = Array.isArray(ARG) ? ARG : ((ARG && ARG.paths) || [])
const MODEL = (ARG && !Array.isArray(ARG) && ARG.model) || 'haiku'   // extrakce default Haiku (levné); přepiš {paths, model}
const typeOf = (p) =>
  p.includes('/grant_') ? 'grant' :
  p.includes('/project_') ? 'project' :
  p.includes('/mission_') ? 'foundation_mission' : 'grant'

const SCHEMAS = {
  grant: {
    type: 'object', required: ['title'],
    properties: {
      title: { type: 'string' }, focus_area: { type: ['string', 'null'] },
      open_from: { type: ['string', 'null'], description: 'YYYY-MM-DD nebo null' },
      deadline: { type: ['string', 'null'], description: 'YYYY-MM-DD | průběžně | null' },
      amount: { type: ['string', 'null'], description: 'věta o alokaci/výši; nestanoveno; null' },
      eligible_applicants: { type: ['string', 'null'] },
      required_attachments: { type: 'array', items: { type: 'string' } },
      how_to_apply: { type: ['string', 'null'] },
      source_doc: { type: ['string', 'null'] },
      evidence: { type: 'object', additionalProperties: { type: 'string' },
        description: 'pro KAŽDÉ vyplněné pole PŘESNÁ doslovná citace ze zdroje (verbatim, ať ji lze najít v textu); klíč = název pole' },
    },
  },
  project: {
    type: 'object', required: ['title'],
    properties: {
      title: { type: 'string' }, grantee: { type: ['string', 'null'] },
      grantee_ico: { type: ['string', 'null'] }, amount: { type: ['string', 'null'] },
      year: { type: ['string', 'null'] }, focus_area: { type: ['string', 'null'] },
      source_doc: { type: ['string', 'null'] },
      evidence: { type: 'object', additionalProperties: { type: 'string' },
        description: 'verbatim citace ze zdroje per pole (klíč = název pole)' },
    },
  },
  foundation_mission: {
    type: 'object', required: ['name'],
    properties: {
      name: { type: ['string', 'null'] }, mission: { type: ['string', 'null'] },
      support_topics: { type: 'array', items: { type: 'string' } },
      regions: { type: 'array', items: { type: 'string' } },
      source_doc: { type: ['string', 'null'] },
      evidence: { type: 'object', additionalProperties: { type: 'string' },
        description: 'verbatim citace ze zdroje per pole (klíč = název pole)' },
    },
  },
}

const COMMON = `Načti Read tool dokument na zadané cestě. JSON má: title, body (PLNÉ tělo), attachments_md (PLNÝ text VŠECH příloh — vyhlášení/podmínky/žádost), volitelně related_context (raw kontext napojeného programu — GROUNDING, ne přepis). Dívej se VŽDY jen na tuto JEDNU oportunitu. Extrahuj POUZE co je v textu (NEHALUCINUJ); co nejde určit = null. Status NEvyplňuj (dopočítá kód).
DŮLEŽITÉ — EVIDENCE: pro KAŽDÉ vyplněné pole vrať do objektu \`evidence\` PŘESNOU DOSLOVNOU citaci ze zdroje (verbatim — zkopíruj větu/úsek, ze kterého hodnotu bereš, BEZ úprav, ať ji lze najít fulltextem v dokumentu). Klíč = název pole (např. "deadline", "amount"). Když pole odvozuješ z více míst, dej nejvýstižnější citaci. Necituj, co v textu doslova není.`

const SYS = {
  grant: `Jsi extraktor české dotační VÝZVY. ${COMMON}
POLE: title, focus_area (na co), open_from (zahájení příjmu YYYY-MM-DD), deadline (ukončení příjmu; rolling="průběžně"), amount (opiš větu o alokaci/výši/míře), eligible_applicants (kdo MŮŽE žádat), required_attachments (co dokládá ŽADATEL), how_to_apply, source_doc.
⚠ NEPLEŤ: deadline ≠ termín realizace/"platnost:"/vyhlášení výsledků/ZoR-ŽoP/open_from (při prodloužení POZDĚJŠÍ datum). amount ≠ odvod/jistina-úroky(úvěr)/"požadovaná výše"(žadatel)/"podpořen částkou"(projekt); "není stanovena"→"nestanoveno". eligible ≠ cílová skupina(příjemci služby)/typy aktivit. required_attachments ≠ soubory KE STAŽENÍ (jen co dokládá žadatel).`,
  project: `Jsi extraktor financovaného PROJEKTU (kdo dostal kolik na co). ${COMMON}
POLE: title, grantee (příjemce), grantee_ico (IČO), amount (PŘIDĚLENÁ/vyúčtovaná částka), year (rok podpory), focus_area, source_doc.
⚠ amount = co příjemce DOSTAL (ne požadoval). Nepleť výzvu s projektem.`,
  foundation_mission: `Jsi extraktor POSLÁNÍ organizace / oblasti podpory (NE konkrétní výzva). ${COMMON}
POLE: name (název organizace), mission (poslání/čemu se věnují), support_topics (oblasti podpory), regions (území působnosti), source_doc.
⚠ Mise = trvalé zaměření, ne jednorázová výzva s datem/částkou.`,
}

phase('Extract')
const out = await parallel(PATHS.map((path) => () => {
  const t = typeOf(path)
  return agent(
    `${SYS[t]}\n\nDokument k načtení: ${path}\nExtrahuj pole do schématu.`,
    { label: `${t}:${path.split('/').pop()}`, phase: 'Extract', schema: SCHEMAS[t], model: MODEL }
  ).then(fields => ({ path, type: t, fields })).catch(e => ({ path, type: t, fields: null, error: String(e) }))
}))

log(`hotovo: ${out.filter(r => r.fields).length}/${PATHS.length} extrahováno`)
return out.filter(Boolean)
