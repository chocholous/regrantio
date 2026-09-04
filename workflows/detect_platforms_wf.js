export const meta = {
  name: 'detect-platforms',
  description: 'Hybridní re-detekce platforem: Sonnet agenti čtou důkazy UNKNOWN webů, sdílejí registr podpisů, pojmenují nové platformy',
  phases: [
    { title: 'Bootstrap', detail: 'načti manifest UNKNOWN hostů' },
    { title: 'Rozpoznání', detail: 'agenti čtou evidence a rozpoznají platformu + markery' },
    { title: 'Konsolidace', detail: 'sjednoť názvy přes sdílený registr, aplikuj na nejisté' },
  ],
}

const MANIFEST_PATH = '/Users/chocholous/Projects/re-grantio/unknown_manifest.json'

const BATCH_SCHEMA = {
  type: 'object', required: ['results'],
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        required: ['host', 'platform', 'confidence', 'markers'],
        properties: {
          host: { type: 'string' },
          platform: { type: 'string', description: 'kanonický název CMS/platformy (např. wordpress, drupal, joomla, plone, typo3, vismo, gordic_ginis, antee, galileo, marbes, asseco, webnode, wix, custom_spa, ...). UNKNOWN jen když opravdu nejde určit.' },
          vendor: { type: 'string', description: 'dodavatel/produkt pokud poznatelný (např. Webhouse, Antee, Galileo, Marbes, PilsCom)' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          is_novel: { type: 'boolean', description: 'true pokud to je platforma mimo běžné (wordpress/drupal/joomla/plone/typo3/vismo/dsw2/liferay/react/vue) — kandidát na novou registraci' },
          markers: { type: 'array', items: { type: 'string' }, description: '2-5 konkrétních důkazů z evidence (generator, cesta, script, cookie, footer text)' },
          grant_relevant: { type: 'boolean', description: 'naznačuje obsah dotace/granty/nadace?' },
        },
      },
    },
  },
}

phase('Bootstrap')
const manifestRaw = await agent(
  `Přečti soubor ${MANIFEST_PATH} (jeden Read) a vrať PŘESNĚ jeho JSON obsah, nic víc.`,
  { label: 'load-manifest', phase: 'Bootstrap' })
let manifest
try {
  const m = manifestRaw.match(/\[[\s\S]*\]/)
  manifest = JSON.parse(m ? m[0] : manifestRaw)
} catch (e) { return { error: 'nelze parsovat manifest', raw: manifestRaw.slice(0, 300) } }

const SIZE = 9
const batches = []
for (let i = 0; i < manifest.length; i += SIZE) batches.push(manifest.slice(i, i + SIZE))

phase('Rozpoznání')
const round1raw = await parallel(batches.map((b, bi) => async () => {
  const list = b.map(x => `- host=${x.host} (label_v_datasetu=${x.label}) evidence_soubor=${x.path}`).join('\n')
  const out = await agent(
    `Jsi expert na detekci webových CMS/platforem (čeští municipální i obecní dodavatelé). ` +
    `Pro KAŽDÝ host přečti jeho evidence_soubor (obsahuje HTTP hlavičky, meta, generator, link/script src, URL cesty, footer/powered-by, text) a urči platformu/CMS. ` +
    `Pozor: generator meta (Elementor/WP, Drupal, Joomla, TYPO3, Plone), charakteristické cesty (/wp-content, /sites/default, /typo3conf, /o/ liferay, resolveuid plone), JS bundly, cookie názvy, footer „redakční systém/provozuje/vytvořil". ` +
    `Rozpoznej i ČESKÉ municipální CMS dodavatele (Webhouse/vismo, Antee, Galileo, Marbes, PilsCom/bm, Gordic, Asseco). ` +
    `is_novel=true u platforem mimo běžnou sadu. UNKNOWN jen když fakt nejde.\n\nHOSTI:\n${list}\n\nVrať results pro všechny.`,
    { label: `detect:b${bi}`, phase: 'Rozpoznání', model: 'sonnet', schema: BATCH_SCHEMA })
  return out ? out.results : null
}))
const round1 = round1raw.filter(Boolean).flat()

// === SDÍLENÝ REGISTR: slouč markery napříč agenty (orchestrátor) ===
const registry = {}
for (const f of round1) {
  if (!f.platform || f.platform === 'UNKNOWN') continue
  const key = f.platform.toLowerCase().trim()
  registry[key] = registry[key] || { markers: new Set(), hosts: [], vendor: f.vendor, novel: false, count: 0 }
  registry[key].count++
  ;(f.markers || []).forEach(m => registry[key].markers.add(m))
  registry[key].hosts.push(f.host)
  if (f.is_novel) registry[key].novel = true
  if (f.vendor && !registry[key].vendor) registry[key].vendor = f.vendor
}
const registryText = Object.entries(registry)
  .sort((a, b) => b[1].count - a[1].count)
  .map(([p, v]) => `${p}${v.vendor ? ' (' + v.vendor + ')' : ''} ×${v.count}${v.novel ? ' [NOVEL]' : ''}: markery=[${[...v.markers].slice(0, 6).join(' | ')}]`)
  .join('\n')

log(`registr: ${Object.keys(registry).length} platforem; round1 klasifikoval ${round1.length} hostů`)

// === ROUND 2: konsolidace přes sdílený registr ===
phase('Konsolidace')
const uncertain = round1.filter(f => f.confidence === 'low' || f.platform === 'UNKNOWN')
const consolidated = await agent(
  `Tady je SDÍLENÝ REGISTR podpisů platforem sestavený ze všech agentů (round 1):\n\n${registryText}\n\n` +
  `A tady jsou NEJISTÉ hosty (low confidence nebo UNKNOWN) i s jejich markery:\n${JSON.stringify(uncertain, null, 1)}\n\n` +
  `Úkol: (1) Sjednoť názvy platforem — pokud round1 použil pro stejnou věc různá jména, urči kanonický název. ` +
  `(2) U nejistých hostů zkus přiřadit platformu z registru podle shody markerů. ` +
  `(3) Vrať finální seznam (host → platforma, confidence) jen pro tyto nejisté hosty + seznam kanonických přejmenování.`,
  { label: 'consolidate', phase: 'Konsolidace', model: 'sonnet',
    schema: {
      type: 'object', required: ['reassigned', 'canonical_renames'],
      properties: {
        reassigned: { type: 'array', items: { type: 'object', required: ['host', 'platform', 'confidence'],
          properties: { host: { type: 'string' }, platform: { type: 'string' }, confidence: { type: 'string' } } } },
        canonical_renames: { type: 'array', items: { type: 'object',
          properties: { from: { type: 'string' }, to: { type: 'string' } } } },
      },
    } })

// finální mapa platforem
const finalByHost = {}
for (const f of round1) finalByHost[f.host] = { platform: f.platform, confidence: f.confidence, vendor: f.vendor, novel: f.is_novel, grant: f.grant_relevant }
for (const r of (consolidated?.reassigned || [])) if (finalByHost[r.host]) { finalByHost[r.host].platform = r.platform; finalByHost[r.host].confidence = r.confidence; finalByHost[r.host].via = 'registr' }

const dist = {}
for (const h in finalByHost) dist[finalByHost[h].platform] = (dist[finalByHost[h].platform] || 0) + 1
const novel = Object.entries(registry).filter(([p, v]) => v.novel).map(([p, v]) => ({ platform: p, vendor: v.vendor, count: v.count, hosts: v.hosts.slice(0, 4) }))

return {
  unknown_hosts: manifest.length,
  classified: round1.length,
  still_unknown: Object.values(finalByHost).filter(x => x.platform === 'UNKNOWN').length,
  distribution: Object.fromEntries(Object.entries(dist).sort((a, b) => b[1] - a[1])),
  novel_platforms: novel,
  registry_size: Object.keys(registry).length,
  canonical_renames: consolidated?.canonical_renames || [],
  grant_relevant_unknown: Object.entries(finalByHost).filter(([h, v]) => v.grant).map(([h]) => h),
  per_host: finalByHost,
}
