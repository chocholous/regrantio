export const meta = {
  name: 'layer2-facet',
  description: 'Vrstva 2 (LLM): z PLNÉHO textu grantu (tělo+přílohy) mapuje do KONTROLOVANÝCH číselníků pro fasetové filtrování (oblast, typ žadatele/poskytovatele, forma/režim/zdroj/délka podpory, výše, region, cílová skupina). 1 oportunita = 1 agent.',
  phases: [{ title: 'Facet', detail: 'Sonnet: plný text → číselníky' }],
}

const ARG = (typeof args === 'string') ? JSON.parse(args) : args
const PATHS = Array.isArray(ARG) ? ARG
  : (ARG && ARG.dir && ARG.count)
    ? Array.from({ length: ARG.count }, (_, i) => `${ARG.dir}/g_${String(i).padStart(4, '0')}.json`)  // sekvenční g_NNNN
    : ((ARG && ARG.paths) || [])
const MODEL = (ARG && !Array.isArray(ARG) && ARG.model) || 'sonnet'

const SCHEMA = {
  type: 'object', required: ['oblast', 'typ_zadatele', 'typ_poskytovatele', 'forma_podpory'],
  properties: {
    oblast: { type: 'array', items: { type: 'string' }, description: 'oblast(i) podpory — OTEVŘENÝ slovník (seed v SYS, smíš přidat vlastní snake_case)' },
    typ_zadatele: { type: 'array', items: { type: 'string' }, description: 'kdo SMÍ žádat — OTEVŘENÝ slovník (seed v SYS, smíš přidat); prázdné když nejde určit' },
    typ_poskytovatele: { type: 'string', description: 'povaha poskytovatele — OTEVŘENÝ slovník (seed v SYS, smíš přidat)' },
    forma_podpory: { type: 'array', items: { type: 'string' }, description: 'OTEVŘENÝ slovník (seed v SYS)' },
    rezim_prijmu: { type: 'string', description: 'OTEVŘENÝ (seed: jednorazova_vyzva/prubezna/kolova/neuvedeno)' },
    zdroj_financovani: { type: 'array', items: { type: 'string' }, description: 'OTEVŘENÝ slovník (seed v SYS)' },
    delka: { type: 'string', description: 'OTEVŘENÝ (seed: jednoleta/viceleta/neuvedeno)' },
    zpusob_podani: { type: 'array', items: { type: 'string' }, description: 'OTEVŘENÝ slovník (seed v SYS)' },
    mira_podpory_pct: { type: ['number','null'], description: 'max % dotace z nákladů (70 → 70), null' },
    spoluucast: { type: ['boolean','null'], description: 'vyžaduje vlastní spoluúčast? true/false/null' },
    cilova_skupina: { type: 'array', items: { type: 'string' }, description: 'KOMU projekt slouží (senioři, děti, hendikepovaní…) — NE žadatel; krátké pojmy' },
    vyse_alokace_czk: { type: ['number','null'] },
    vyse_max_zadatel_czk: { type: ['number','null'] },
    region: { type: 'object', description: 'územní stopa z prózy, RESOLVOVANÁ na geo-strom tvou znalostí české geografie',
      properties: {
        nazev: { type: ['string','null'], description: 'nejkonkrétnější místo jak stojí v textu (obec/MČ/okres/kraj)' },
        obec: { type: ['string','null'], description: 'kanonický název obce, když plyne; jinak null' },
        okres: { type: ['string','null'], description: 'okres (doplň dle své znalosti i když text uvádí jen obec); null' },
        kraj: { type: ['string','null'], description: 'kraj (doplň dle své znalosti); null' },
        celostatni: { type: 'boolean', description: 'true = platí pro celou ČR / bez územního omezení' },
      } },
    region_evidence: { type: ['string','null'], description: 'doslovná citace územní stopy z textu; null když žádná' },
    reasoning: { type: 'array', items: { type: 'string' } },
  },
}

const SYS = `Z PLNÉHO textu dotačního grantu vyplň číselníky pro filtrování. Read JSON: title, body (plné tělo), attachments_md (plný text příloh), případně focus_area/eligible_applicants/amount/how_to_apply. Vyplň POUZE z textu (NEHALUCINUJ); co nejde určit → prázdné / null / „neuvedeno".

⚠ VŠECHNY číselníky jsou OTEVŘENÉ (průzkumná fáze): seed hodnoty níže PREFERUJ kvůli konzistenci, ale když hodnota do žádné seed nezapadá, PŘIDEJ vlastní výstižnou (snake_case, bez diakritiky). Nehas do „ostatni/jine", když existuje přesnější nový pojem.

OBLAST (multi): kultura_umeni · sport_volny_cas · socialni_sluzby (péče, senioři, znevýhodnění, samoživitelé, hospic) · zdravi (zdravotnictví, prevence, ambulance) · vzdelavani_mladez (školství, děti/mládež, talenti) · zivotni_prostredi · cestovni_ruch · veda_vyzkum · bydleni_infrastruktura (stavby, opravy, sportoviště) · bezpecnost (hasiči, prevence) · ostatni.

TYP_ZADATELE (multi, kdo SMÍ žádat) — OTEVŘENÝ slovník. SEED hodnoty (preferuj je): neziskovka (spolek/o.p.s./nadace/ústav/církev) · fyzicka_osoba · osvc_podnikatel · firma (s.r.o./a.s./družstvo) · prispevkova_organizace · obec_verejny_subjekt · skola_vyzkumna_org. Když žadatel NEzapadá do žádné seed hodnoty, PŘIDEJ vlastní krátkou (snake_case, např. sdruzeni_obci, cirkev, startup). ⚠ cílová skupina (komu služba slouží) ≠ žadatel.

TYP_POSKYTOVATELE (jeden, kdo dotaci dává): ministerstvo · samosprava_obec · samosprava_kraj · statni_fond (SFŽP apod.) · nadace · firemni_nadace (nadace zřízená firmou — ČEZ, AGROFERT, Kellner…) · nadacni_fond · eu_mezinarodni (EU/EHP/mezinárodní operátor) · skola_univerzita · jine.

FORMA_PODPORY (multi): dotace · zapujcka_uver (návratná, půjčka) · stipendium · cena_soutez · vecny_dar. ⚠ zápůjčka/úvěr ≠ dotace.

REZIM_PRIJMU (jeden): jednorazova_vyzva (jeden termín) · prubezna (rolling, „průběžně") · kolova (víc kol) · neuvedeno.

ZDROJ_FINANCOVANI (multi): narodni_rozpocet · eu_fondy (OP, Horizon, IROP) · npo (Národní plán obnovy) · ehp_norsko (Fondy EHP a Norska) · krajsky · vlastni_zdroje (rozpočet nadace/firmy).

DELKA (jeden): jednoleta · viceleta (projekt přes víc let / „víceletý grant") · neuvedeno.

ZPUSOB_PODANI (multi): datova_schranka · posta · osobne · online_portal (GRANTYS/portál/aplikace) · email · neuvedeno.

MIRA_PODPORY_PCT = max % dotace z celkových nákladů („max 70 % nákladů" → 70); null když není. SPOLUUCAST = true když text vyžaduje vlastní spoluúčast/dofinancování, jinak false/null.

CILOVA_SKUPINA = komu projekt PROSPÍVÁ (senioři, děti a mládež, osoby se zdravotním postižením, pacienti, …) — NE žadatel. Krátké pojmy; prázdné když neuvedeno.

VÝŠE (čísla v Kč): vyse_alokace_czk = celkový objem programu; vyse_max_zadatel_czk = max na žadatele; null když chybí.

REGION (z prózy → geo-strom): najdi V TEXTU jakoukoli územní stopu (sídlo žadatele, území realizace, „se sídlem v Hodoníně", „na území MČ Praha 11", „okres Mělník", „v Jihomoravském kraji", „celostátně"). Pak ji RESOLVUJ svou znalostí české geografie:
- nazev = nejkonkrétnější místo jak stojí v textu; obec/okres/kraj = doplň kanonicky (i když text uvádí jen obec, dopočítej okres+kraj; MČ → obec=Praha, kraj=Hlavní město Praha).
- celostatni=true, když platí pro celou ČR / bez územního omezení (typicky ministerstva, celostátní nadace).
- region_evidence = doslovná citace té stopy.
- Když text ŽÁDNOU územní stopu nemá → nazev/obec/okres/kraj=null, celostatni=false, region_evidence=null (kód pak doplní z poskytovatele s nižší confidence).`

phase('Facet')
const out = await parallel(PATHS.map((path) => () => agent(
  `${SYS}\n\nDokument k načtení: ${path}\nVrať číselníky dle schématu.`,
  { label: `facet:${path.split('/').pop()}`, phase: 'Facet', schema: SCHEMA, model: MODEL }
).then(f => ({ path, facet: f })).catch(e => ({ path, facet: null, error: String(e) }))))

log(`hotovo: ${out.filter(r => r.facet).length}/${PATHS.length}`)
return out.filter(Boolean)
