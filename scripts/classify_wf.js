export const meta = {
  name: 'layer1-classify',
  description: 'Vrstva 1 (LLM): Haiku agenti klasifikují base_type dokumentu naslepo. 1 dokument = 1 agent. Slouží k měření routing accuracy (zejm. odfiltrování news/administrative/other od oportunit).',
  phases: [{ title: 'Classify', detail: 'Haiku: base_type per dokument' }],
}

const PATHS = Array.isArray(args) ? args : (typeof args === 'string' ? JSON.parse(args) : [])

const SCHEMA = {
  type: 'object', required: ['base_type', 'confidence'],
  properties: {
    base_type: { type: 'string', enum: ['grant', 'project', 'news', 'foundation_mission', 'administrative', 'other'] },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    signals: { type: 'array', items: { type: 'string' } },
  },
}

const SYS = `Jsi expert na české dotační/grantové weby. Načti Read tool dokument na zadané cestě (JSON: title, body, web). Urči BASE_TYPE — CO to je (NE jestli otevřené/uzavřené):
- grant = vyhlášená VÝZVA / dotační program / grant, k němuž lze (nebo šlo) podat žádost
- project = financovaný PROJEKT / příjemce ("kdo dostal kolik na co")
- news = novinka / aktualita / tisková zpráva / pozvánka na akci
- foundation_mission = poslání / oblast podpory organizace (NE konkrétní výzva)
- administrative = veřejná zakázka, vyhláška, smlouva, úřední deska, usnesení, záměr, rozpočtové opatření
- other = formulář, galerie, kontakt, ceník, ostatní
ZÁMĚNY (kritické): úřednědeskový OBAL ≠ administrative když OBSAH je dotační program → grant; "projekt byl podpořen částkou/ocenila" → project; usnesení rady → administrative (ne news); abstraktní téma bez data/částky → foundation_mission ne grant. Rozhoduj podle OBSAHU, ne obalu. Ignoruj případné interní/pomocné klíče v JSONu.`

phase('Classify')
const out = await parallel(PATHS.map((path) => () => agent(
  `${SYS}\n\nDokument k načtení: ${path}\nVrať base_type, confidence, signals.`,
  { label: `cls:${path.split('/').pop()}`, phase: 'Classify', schema: SCHEMA, model: 'haiku' }
).then(c => ({ path, classify: c })).catch(e => ({ path, classify: null, error: String(e) }))))

log(`hotovo: ${out.filter(r => r.classify).length}/${PATHS.length} klasifikováno`)
return out.filter(Boolean)
