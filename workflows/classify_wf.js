export const meta = {
  name: 'layer1-classify',
  description: 'Vrstva 1 (LLM): agenti klasifikují base_type dokumentu naslepo (produkční model = Sonnet, default; Haiku pod-rozpoznává granty). 1 dokument = 1 agent. Slouží k routingu/měření accuracy (odfiltrování news/administrative/other od oportunit).',
  phases: [{ title: 'Classify', detail: 'Sonnet: base_type per dokument' }],
}

const ARG = (typeof args === 'string') ? JSON.parse(args) : args
const PATHS = Array.isArray(ARG) ? ARG : ((ARG && ARG.paths) || [])
const MODEL = (ARG && !Array.isArray(ARG) && ARG.model) || 'sonnet'   // produkční model klasifikace (kvalita 91 %); přepiš {paths, model}

const SCHEMA = {
  type: 'object', required: ['base_type', 'confidence'],
  properties: {
    base_type: { type: 'string', enum: ['grant', 'news', 'foundation_mission', 'administrative', 'other'] },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    reasoning: { type: 'array', items: { type: 'string' }, description: 'stručné body, podle čeho ses rozhodl' },
  },
}

const SYS = `Urči base_type dokumentu (Read JSON: title, body, web, attachments_md = PLNÝ text stažených příloh/PDF) podle toho, CO dokument DĚLÁ — z PRIMÁRNÍHO obsahu, ne z titulku, obalu, sidebaru ani formátu. Status (otevřeno/uzavřeno) NEřeš, počítá kód.
OBSAH = TĚLO + PŘÍLOHY dohromady: tenká stránka odkazující na „Výzva.pdf" je grant, když to vyhlášení v attachments_md JE výzva. Nehleď jen na body. (Přílohy ber jako obsah té JEDNÉ oportunity; metodika/formulář v příloze ale samy o sobě grant nedělají — viz KOTVA.)

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

phase('Classify')
const out = await parallel(PATHS.map((path) => () => agent(
  `${SYS}\n\nDokument k načtení: ${path}\nVrať base_type, confidence, reasoning.`,
  { label: `cls:${path.split('/').pop()}`, phase: 'Classify', schema: SCHEMA, model: MODEL }
).then(c => ({ path, classify: c })).catch(e => ({ path, classify: null, error: String(e) }))))

log(`hotovo: ${out.filter(r => r.classify).length}/${PATHS.length} klasifikováno`)
return out.filter(Boolean)
