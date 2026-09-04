export const meta = {
  name: 'field-coverage',
  description: 'Sonnet čte reálné grantové dokumenty napříč typy, hlásí formulace + záludnosti per pole; měří saturaci pokrytí',
  phases: [{ title: 'Pozorování', detail: 'agent per dávka hlásí formulace+pitfally' }],
}

const manifest = [
  { batch: 0, path: '/Users/chocholous/Projects/re-grantio/coverage_sample/batch_0.json' },
  { batch: 1, path: '/Users/chocholous/Projects/re-grantio/coverage_sample/batch_1.json' },
  { batch: 2, path: '/Users/chocholous/Projects/re-grantio/coverage_sample/batch_2.json' },
  { batch: 3, path: '/Users/chocholous/Projects/re-grantio/coverage_sample/batch_3.json' },
  { batch: 4, path: '/Users/chocholous/Projects/re-grantio/coverage_sample/batch_4.json' },
  { batch: 5, path: '/Users/chocholous/Projects/re-grantio/coverage_sample/batch_5.json' },
]

const SCHEMA = {
  type: 'object', required: ['batch', 'observations'],
  properties: {
    batch: { type: 'integer' },
    observations: {
      type: 'array',
      items: {
        type: 'object',
        required: ['field', 'phrasings', 'pitfalls'],
        properties: {
          field: { type: 'string', enum: ['deadline', 'amount', 'eligible_applicants', 'status', 'required_attachments', 'how_to_apply'] },
          phrasings: { type: 'array', items: { type: 'string' }, description: 'KONKRÉTNÍ trigger-formulace JAK BYLO pole vyjádřeno v TĚCHTO dokumentech (krátká fráze/label, ne hodnota)' },
          pitfalls: { type: 'array', items: { type: 'string' }, description: 'záludnosti/confusably viděné v TĚCHTO dokumentech — formulace, co VYPADÁ jako pole ale NENÍ (krátce + proč)' },
        },
      },
    },
  },
}

const rubrika = `Jsi expert na české dotační výzvy. Přečteš JSON dávku reálných grantových dokumentů z RŮZNÝCH zdrojů/typů (agregátor, primární agentura, nadace, PDF pravidla, ministerstvo, EU fond). Cíl NENÍ extrahovat hodnoty, ale ZMAPOVAT JAZYK: pro každé základní pole nahlásit, JAK se o něm v těchto dokumentech mluví + na co si dát pozor.
Pole: deadline (termín podání žádosti), amount (výše/alokace výzvy), eligible_applicants (kdo může žádat), status (otevřená/uzavřená), required_attachments (povinné přílohy), how_to_apply (jak podat).
Pro KAŽDÉ pole, které se v dávce vyskytlo:
- phrasings: konkrétní formulace/labely, jakými je pole uvedeno (krátké fráze, ne hodnoty). Zachyť i NEOBVYKLÉ způsoby.
- pitfalls: formulace, které VYPADAJÍ jako to pole, ale NEJSOU (např. 'termín realizace' ≠ deadline podání; 'projekt byl podpořen částkou' = příjemce, ne alokace výzvy; 'výše odvodu za porušení' = sankce, ne částka dotace; 'lhůta pro rozhodnutí' = úřad, ne žadatel). Stručně + proč.
Buď konkrétní a vycházej JEN z těchto dokumentů. Přečti POUZE ten jeden zadaný soubor.`

phase('Pozorování')
const results = (await parallel(manifest.map(m => async () => {
  const out = await agent(
    `${rubrika}\n\nNačti soubor: ${m.path} (dávka ${m.batch}). Vrať observations pro pozorovaná pole.`,
    { label: `cover:b${m.batch}`, phase: 'Pozorování', model: 'sonnet', schema: SCHEMA })
  return out ? { batch: m.batch, observations: out.observations || [] } : null
}))).filter(Boolean)

// merge per pole + saturační křivka (kumulativně po dávkách v pořadí)
const FIELDS = ['deadline', 'amount', 'eligible_applicants', 'status', 'required_attachments', 'how_to_apply']
const norm = s => s.toLowerCase().replace(/\s+/g, ' ').trim()
const merged = {}, pitfalls = {}, curve = {}
for (const f of FIELDS) { merged[f] = new Set(); pitfalls[f] = new Set(); curve[f] = [] }
results.sort((a, b) => a.batch - b.batch)
for (const r of results) {
  for (const o of r.observations) {
    if (!merged[o.field]) continue
    ;(o.phrasings || []).forEach(p => merged[o.field].add(norm(p)))
    ;(o.pitfalls || []).forEach(p => pitfalls[o.field].add(norm(p)))
  }
  for (const f of FIELDS) curve[f].push(merged[f].size)
}

const summary = {}
for (const f of FIELDS) {
  const c = curve[f]
  const lastDelta = c.length > 1 ? c[c.length - 1] - c[c.length - 2] : c[0] || 0
  summary[f] = {
    distinct_phrasings: merged[f].size,
    distinct_pitfalls: pitfalls[f].size,
    saturation_curve: c,
    last_batch_new: lastDelta,
    verdict: lastDelta <= 1 ? 'NASYCENO (pokryto)' : 'JEŠTĚ ROSTE (více dat by pomohlo)',
    phrasings: [...merged[f]],
    pitfalls: [...pitfalls[f]],
  }
}
return { batches: results.length, per_field: summary }
