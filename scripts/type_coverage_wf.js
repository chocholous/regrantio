export const meta = {
  name: 'type-field-coverage',
  description: 'Dvouvrstvé pokrytí: (1) typ obsahu + signály/záměny, (2) per typ jeho pole + formulace/záludnosti; saturace obou vrstev',
  phases: [{ title: 'Pozorování', detail: 'agent per dávka klasifikuje typ a mapuje pole' }],
}

const manifest = [
  { batch: 0, path: '/Users/chocholous/Projects/re-grantio/type_sample/batch_0.json' },
  { batch: 1, path: '/Users/chocholous/Projects/re-grantio/type_sample/batch_1.json' },
  { batch: 2, path: '/Users/chocholous/Projects/re-grantio/type_sample/batch_2.json' },
  { batch: 3, path: '/Users/chocholous/Projects/re-grantio/type_sample/batch_3.json' },
  { batch: 4, path: '/Users/chocholous/Projects/re-grantio/type_sample/batch_4.json' },
  { batch: 5, path: '/Users/chocholous/Projects/re-grantio/type_sample/batch_5.json' },
]

const TYPES = ['grant_open', 'grant_closed', 'grant_announced', 'news', 'mise_tema', 'administrativa', 'projekt_open', 'projekt_done', 'ostatni']

const SCHEMA = {
  type: 'object', required: ['batch', 'docs'],
  properties: {
    batch: { type: 'integer' },
    docs: {
      type: 'array',
      items: {
        type: 'object',
        required: ['assigned_type', 'type_signals', 'type_confusables', 'fields'],
        properties: {
          assigned_type: { type: 'string', enum: TYPES },
          type_signals: { type: 'array', items: { type: 'string' }, description: 'co identifikovalo TENTO typ (krátké signály)' },
          type_confusables: { type: 'array', items: { type: 'string' }, description: 's jakým jiným typem by se mohl splést a proč' },
          fields: {
            type: 'array',
            items: {
              type: 'object',
              required: ['field', 'phrasings', 'pitfalls'],
              properties: {
                field: { type: 'string', description: 'pole relevantní pro tento typ (grant: deadline/amount/eligible/status; projekt: grantee/amount/year/status; mise: mission/topics/regions; news: date; administrativa: nic_grantového)' },
                phrasings: { type: 'array', items: { type: 'string' } },
                pitfalls: { type: 'array', items: { type: 'string' } },
              },
            },
          },
        },
      },
    },
  },
}

const rubrika = `Jsi expert na klasifikaci obsahu českých dotačních/grantových webů. Přečteš JSON dávku reálných dokumentů z RŮZNÝCH zdrojů. Pracuješ ve DVOU VRSTVÁCH:
VRSTVA 1 — TYP OBSAHU. Zařaď každý dokument do jednoho z typů:
- grant_open / grant_closed / grant_announced = VÝZVA/dotace (otevřená příjem běží / uzavřená po termínu / oznámená zatím nelze)
- news = novinka/aktualita/tisková zpráva/oznámení
- mise_tema = poslání/vize/oblast podpory/dotační téma nadace (NE konkrétní výzva)
- administrativa = veřejná zakázka, vyhláška, smlouva, FOI (106/1999), úřední deska, organizační — NENÍ to grant
- projekt_open / projekt_done = financovaný projekt / příjemce (probíhající / dokončený)
- ostatni = formulář, galerie, kontakt, ostatní
U každého dokumentu nahlas: assigned_type, type_signals (co typ prozradilo), type_confusables (s čím by se spletl).
VRSTVA 2 — POLE TYPU. Pro přiřazený typ nahlas jeho relevantní pole (grant→deadline/amount/eligible/status; projekt→grantee/amount/year/status; mise→mission/topics/regions; news→date; administrativa→žádná grantová), a u každého: phrasings (jak vyjádřeno) + pitfalls (záludnosti).
Vycházej JEN z těchto dokumentů. Přečti POUZE ten jeden zadaný soubor.`

phase('Pozorování')
const results = (await parallel(manifest.map(m => async () => {
  const out = await agent(
    `${rubrika}\n\nNačti soubor: ${m.path} (dávka ${m.batch}). Vrať docs pro každý dokument.`,
    { label: `type:b${m.batch}`, phase: 'Pozorování', model: 'sonnet', schema: SCHEMA })
  return out ? { batch: m.batch, docs: out.docs || [] } : null
}))).filter(Boolean)
results.sort((a, b) => a.batch - b.batch)

const norm = s => (s || '').toLowerCase().replace(/\s+/g, ' ').trim()
// VRSTVA 1: per typ signály + záměny + saturace
const typeSig = {}, typeConf = {}, typeCurve = {}, typeCount = {}
// VRSTVA 2: per (typ,pole) formulace + záludnosti
const fieldPhr = {}, fieldPit = {}
for (const t of TYPES) { typeSig[t] = new Set(); typeConf[t] = new Set(); typeCurve[t] = []; typeCount[t] = 0 }

for (const r of results) {
  for (const d of r.docs) {
    const t = d.assigned_type
    if (!typeSig[t]) continue
    typeCount[t]++
    ;(d.type_signals || []).forEach(s => typeSig[t].add(norm(s)))
    ;(d.type_confusables || []).forEach(s => typeConf[t].add(norm(s)))
    for (const f of (d.fields || [])) {
      const key = t + '::' + norm(f.field)
      fieldPhr[key] = fieldPhr[key] || new Set()
      fieldPit[key] = fieldPit[key] || new Set()
      ;(f.phrasings || []).forEach(p => fieldPhr[key].add(norm(p)))
      ;(f.pitfalls || []).forEach(p => fieldPit[key].add(norm(p)))
    }
  }
  for (const t of TYPES) typeCurve[t].push(typeSig[t].size)
}

const layer1 = {}
for (const t of TYPES) {
  if (!typeCount[t]) continue
  const c = typeCurve[t]
  layer1[t] = { n_docs: typeCount[t], distinct_signals: typeSig[t].size, distinct_confusables: typeConf[t].size,
    saturation: c, last_new: c.length > 1 ? c[c.length - 1] - c[c.length - 2] : c[0],
    signals: [...typeSig[t]], confusables: [...typeConf[t]] }
}
const layer2 = {}
for (const k of Object.keys(fieldPhr)) {
  layer2[k] = { phrasings: [...fieldPhr[k]], pitfalls: [...fieldPit[k]] }
}
return { batches: results.length, layer1_types: layer1, layer2_type_fields: layer2 }
