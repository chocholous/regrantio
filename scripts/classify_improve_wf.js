export const meta = {
  name: 'classify-improve',
  description: 'Active-learning vylepšení klasifikačního promptu: Sonnet těží type_signals+confusables z dávek reálných dat (saturace), Opus syntetizuje nová pravidla proti současnému promptu.',
  phases: [
    { title: 'Mining', detail: 'Sonnet: signály + záměny per dávka' },
    { title: 'Synthesis', detail: 'Opus: destilát → nová pravidla do promptu' },
  ],
}

const BATCHES = Array.isArray(args) ? args : JSON.parse(args)
const TYPES = ['grant', 'project', 'news', 'foundation_mission', 'administrative', 'other']

const MINE_SCHEMA = {
  type: 'object', required: ['docs'],
  properties: {
    docs: {
      type: 'array',
      items: {
        type: 'object',
        required: ['assigned_type', 'type_signals', 'type_confusables'],
        properties: {
          title: { type: 'string' },
          assigned_type: { type: 'string', enum: TYPES },
          type_signals: { type: 'array', items: { type: 'string' }, description: 'krátké signály, co identifikovaly TENTO typ' },
          type_confusables: { type: 'array', items: { type: 'string' },
            description: 's jakým JINÝM typem by se reálně spletl a PROČ (konkrétně, ne obecně)' },
        },
      },
    },
  },
}

const MINE_SYS = `Jsi expert na klasifikaci českých dotačních/grantových webů. Načti Read tool dávku dokumentů (JSON pole; každý má src, title, body, attachments). Pro KAŽDÝ dokument urči base_type:
- grant = vyhlášená VÝZVA / dotační program, k němuž lze (nebo šlo) podat žádost
- project = financovaný PROJEKT / příjemce ("kdo dostal kolik na co")
- news = novinka / tisková zpráva / oznámení / pozvánka
- foundation_mission = poslání / oblast podpory (NE konkrétní výzva)
- administrative = zakázka, vyhláška, smlouva, úřední deska, usnesení, kontakt-úřední
- other = formulář, galerie, kontakt, nábor/inzerát, ostatní
Rozhoduj podle OBSAHU, ne obalu. U každého dokumentu nahlas assigned_type, type_signals (co rozhodlo) a HLAVNĚ type_confusables (s jakým typem by se reálně spletl a proč — to je nejcennější). Vycházej JEN z dané dávky.`

phase('Mining')
const mined = (await parallel(BATCHES.map((path, i) => () =>
  agent(`${MINE_SYS}\n\nNačti soubor: ${path} (dávka ${i}). Vrať docs pro každý dokument.`,
    { label: `mine:b${i}`, phase: 'Mining', model: 'sonnet', schema: MINE_SCHEMA })
    .then(r => r ? r.docs || [] : []).catch(() => [])
))).flat()

// agregace: distinct signály + záměny per typ + saturační křivka (kumulativně distinct záměny)
const norm = s => (s || '').toLowerCase().replace(/\s+/g, ' ').trim()
const sig = {}, conf = {}, cnt = {}, curve = []
for (const t of TYPES) { sig[t] = new Set(); conf[t] = new Set(); cnt[t] = 0 }
let cumConf = new Set()
for (const d of mined) {
  const t = d.assigned_type
  if (!sig[t]) continue
  cnt[t]++
  ;(d.type_signals || []).forEach(s => sig[t].add(norm(s)))
  ;(d.type_confusables || []).forEach(s => { conf[t].add(norm(s)); cumConf.add(norm(s)) })
  curve.push(cumConf.size)
}
const agg = {}
for (const t of TYPES) agg[t] = { n: cnt[t], signals: [...sig[t]], confusables: [...conf[t]] }
log(`mining: ${mined.length} dok, ${cumConf.size} distinct záměn; saturace tail: ${curve.slice(-6).join(',')}`)

// destilát záměn jako text pro syntézu
const confText = TYPES.filter(t => conf[t].size)
  .map(t => `### ${t} (${cnt[t]} dok)\nZÁMĚNY: ${[...conf[t]].join(' | ')}\nSIGNÁLY: ${[...sig[t]].slice(0, 12).join(' | ')}`)
  .join('\n\n')

phase('Synthesis')
const SYN_SYS = `Jsi expert na prompt-engineering pro klasifikaci českých dotačních dokumentů. Máš:
1) SOUČASNÝ prompt — přečti Read tool: prompts/classify_type.md a prompts/pitfalls.md
2) VYTĚŽENÉ ZÁMĚNY a signály z reálných dat (níže).
Úkol: navrhni KONKRÉTNÍ vylepšení klasifikačního promptu. Zaměř se na ZÁMĚNY, které v současném promptu CHYBÍ nebo jsou vágní. Každé pravidlo musí být akční ("X + Y → typ Z, NE typ W") a opřené o vytěžená data. Nevymýšlej obecnosti; jen to, co data ukazují jako reálný zdroj chyb.

VYTĚŽENÁ DATA:
${confText}`

const SYN_SCHEMA = {
  type: 'object', required: ['novel_rules', 'rewritten_zameny_section'],
  properties: {
    novel_rules: { type: 'array', items: { type: 'object',
      required: ['rule', 'covers_confusion', 'novel'],
      properties: {
        rule: { type: 'string', description: 'akční pravidlo do promptu' },
        covers_confusion: { type: 'string', description: 'jakou záměnu řeší' },
        novel: { type: 'boolean', description: 'true = v současném promptu chybí; false = už pokryto' },
      } } },
    rewritten_zameny_section: { type: 'string', description: 'kompletní přepsaná sekce "POZOR na záměny" pro classify_type.md (markdown odrážky)' },
    notes: { type: 'string' },
  },
}

const synth = await agent(SYN_SYS + '\n\nVrať novel_rules + rewritten_zameny_section.',
  { label: 'synthesis:opus', phase: 'Synthesis', model: 'opus', schema: SYN_SCHEMA })

return { mined_docs: mined.length, distinct_confusables: cumConf.size, saturation_tail: curve.slice(-6),
  per_type: Object.fromEntries(TYPES.map(t => [t, { n: cnt[t], n_confusables: conf[t].size }])),
  synthesis: synth }
