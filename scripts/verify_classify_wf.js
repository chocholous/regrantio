export const meta = {
  name: 'verify-classify',
  description: 'Cross-model audit klasifikace: každý vzorek překlasifikuje Opus i Sonnet nezávisle (stejný prompt jako classify_wf). Pro porovnání proti Haiku.',
  phases: [{ title: 'Verify', detail: 'Opus + Sonnet per dokument' }],
}

const PATHS = Array.isArray(args) ? args : (typeof args === 'string' ? JSON.parse(args) : [])

const SCHEMA = {
  type: 'object', required: ['base_type', 'confidence'],
  properties: {
    base_type: { type: 'string', enum: ['grant', 'news', 'foundation_mission', 'administrative', 'other'] },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    reasoning: { type: 'array', items: { type: 'string' }, description: 'stručné body, podle čeho ses rozhodl' },
  },
}

// IDENTICKÝ prompt jako classify_wf.js (fair cross-model check)
const SYS = `Urči base_type dokumentu (Read JSON: title, body, web) podle toho, CO dokument DĚLÁ — z PRIMÁRNÍHO obsahu TĚLA, ne z titulku, obalu, sidebaru ani formátu. Status (otevřeno/uzavřeno) NEřeš, počítá kód.

KOTVA — jsou v dokumentu konkrétní peníze pro žadatele? Ať NABÍDKA (budeš moct / můžeš / mohl jsi požádat) nebo UDĚLENÍ („komu kolik dali") → grant.
  Patří sem: výzva i financovaný projekt; průběžný program s pravidly, na který lze žádat (pravidla = popis té nabídky); výsledková listina / tabulka příjemců s částkami / „schválení dotací se jmény".

Když konkrétní peníze pro žadatele NEJSOU, rozliš podle funkce:
- foundation_mission = popisuje, ČEMU se organizace věnuje / co obecně podporuje, bez konkrétní nabídky i příjemce. (I sbírka DARŮ pro nadaci — peníze tečou K nadaci, ne k žadateli.)
- news = VYPRÁVÍ o události / výsledku: příběh, tisková zpráva, pozvánka na akci, ocenění osoby, souhrn výsledků BEZ konkrétních příjemců a částek.
- administrative = ŘÍDÍ proces, sám peníze nenabízí: metodika, pokyny, vyúčtování, monitorovací/závěrečná zpráva, usnesení bez seznamu příjemců.
- other = kontakt, formulář, galerie, nábor pracovní pozice, přihláška na akci, NEBO prázdné tělo / čistá navigace bez obsahu.

KDE SE TO PLETE:
- grant × administrative: nabízí/uděluje peníze (grant) × jen popisuje JAK proces běží (admin). Pravidla PROGRAMU, na který lze žádat = grant; pravidla vyúčtování/realizace = admin.
- grant × news: konkrétní příjemci + částky = grant × narativ / souhrn bez nich = news.
- foundation_mission × news: trvalý stav „podporujeme…" = mission × jednorázová událost „stalo se / získal" = news.
- grant × other: financování VLASTNÍ aktivity žadatele = grant (i stipendium na vlastní studium) × placená pozice / přihláška na akci = other.

Když nic nesedí jednoznačně → nejbližší + confidence=low. Vrať base_type, confidence a reasoning (body, podle čeho ses rozhodl).`

phase('Verify')
const out = await parallel(PATHS.map((path) => () =>
  parallel([
    () => agent(`${SYS}\n\nDokument k načtení: ${path}\nVrať base_type, confidence, reasoning.`,
      { label: `opus:${path.split('/').slice(-2).join('/')}`, phase: 'Verify', schema: SCHEMA, model: 'opus' })
      .then(c => c).catch(() => null),
    () => agent(`${SYS}\n\nDokument k načtení: ${path}\nVrať base_type, confidence, reasoning.`,
      { label: `sonnet:${path.split('/').slice(-2).join('/')}`, phase: 'Verify', schema: SCHEMA, model: 'sonnet' })
      .then(c => c).catch(() => null),
  ]).then(([opus, sonnet]) => ({ path, opus, sonnet }))
))

log(`ověřeno: ${out.length} vzorků (Opus+Sonnet)`)
return out.filter(Boolean)
