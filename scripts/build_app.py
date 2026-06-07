#!/usr/bin/env python3
"""Generovátko fasetové aplikace nad data/opportunities.jsonl (self-contained HTML/JS, offline).

Sloučí fasetové vyhledávání (z facets bloku — oblast, sektor→typ žadatele, poskytovatel,
kraj, forma/zdroj/režim/délka/způsob podání, výše-range, status, fulltext) s bohatým
detailem každé oportunity: VŠECHNA strukturovaná pole + facety + klasifikace (proč zařazeno)
+ grounding citace (exact/fragment/none) + provenance/dokumenty + extra (lossless) + raw JSON.

  python3 scripts/build_app.py  [--in data/opportunities.jsonl] [--out data/grants_app.html]
"""
import argparse, json

TPL = r"""<!doctype html><html lang=cs><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Granty — vyhledávání a detail (__N__)</title>
<style>
:root{--bg:#0f1115;--card:#1a1d24;--card2:#20242e;--mut:#8b93a7;--bd:#2a2f3a;--fg:#e6e9ef;--acc:#5b9dff}
*{box-sizing:border-box}body{margin:0;font:14px/1.55 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
.wrap{display:grid;grid-template-columns:300px 1fr}
aside{background:#12151c;border-right:1px solid var(--bd);padding:14px;height:100vh;overflow:auto;position:sticky;top:0}
main{padding:14px 18px;max-width:900px}
h1{font-size:16px;margin:0 0 4px}.sub{color:var(--mut);font-size:12px;margin-bottom:10px}
.q{width:100%;background:var(--card);color:var(--fg);border:1px solid var(--bd);border-radius:7px;padding:9px 10px;margin-bottom:10px}
details.fg{margin-bottom:8px;border-bottom:1px solid var(--bd);padding-bottom:6px}
details.fg>summary{font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--acc);cursor:pointer;padding:4px 0;list-style:none}
details.fg>summary::before{content:'▸ ';font-size:9px}details.fg[open]>summary::before{content:'▾ '}
details.fg>summary .fc{float:right;color:var(--mut);font-size:10px;letter-spacing:0}
details.fg>summary .fa-n{float:right;background:var(--acc);color:#0b1220;font-size:10px;border-radius:10px;padding:0 6px;letter-spacing:0;font-weight:600}
.opt{display:flex;align-items:center;gap:7px;padding:2px 4px;border-radius:5px;cursor:pointer;font-size:12.5px}
.opt:hover{background:var(--card2)}.opt.sub{padding-left:20px;font-size:12px;color:#c6cfe0}
.opt .c{margin-left:auto;color:var(--mut);font-size:11px}.opt.off{opacity:.3}
.rng{display:flex;gap:6px;margin-top:6px}.rng input{flex:1;width:100%;background:var(--card);color:var(--fg);border:1px solid var(--bd);border-radius:6px;padding:6px}
.clr{background:none;border:1px solid var(--bd);color:var(--mut);border-radius:6px;padding:6px;cursor:pointer;width:100%;margin-top:8px}
.cnt{color:var(--mut);font-size:12px;margin-bottom:10px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:9px;margin:8px 0;overflow:hidden}
.hd{padding:11px 14px;cursor:pointer}.hd:hover{background:var(--card2)}
.ti{font-weight:600;margin-bottom:2px}.meta{color:var(--mut);font-size:12px}
.chips{display:flex;gap:5px;flex-wrap:wrap;margin-top:7px}
.chip{font-size:11px;padding:2px 8px;border-radius:11px;background:#222732;color:#c6cfe0;border:1px solid var(--bd)}
.chip.ob{background:#1a2e3a;color:#74c2e0}.chip.se{background:#2e2a17;color:#e0cf74}.chip.kr{background:#173a2a;color:#74e0a8}.chip.po{background:#2a1f33;color:#c79fe0}.chip.low{opacity:.55;font-style:italic}
.badge{font-size:11px;padding:2px 7px;border-radius:10px}.s-open{background:#173a2a;color:#74e0a8}.s-closed{background:#3a1a1a;color:#e08a8a}.s-unknown{background:#2a2f3a;color:#9aa3b5}.s-announced{background:#1a2e3a;color:#74c2e0}.b-mise{background:#3a3417;color:#e0cf74}
.body{display:none;padding:0 14px 12px;border-top:1px solid var(--bd)}.card.open .body{display:block}
.sec{margin-top:11px;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--acc)}
.row{display:flex;gap:8px;padding:3px 0;border-bottom:1px solid var(--card2)}.k{color:var(--mut);min-width:150px;font-size:12px}.v{flex:1;white-space:pre-wrap;word-break:break-word}
.cite{font-size:12px;border-left:2px solid var(--bd);padding:2px 8px;margin:3px 0}.m-exact{border-color:#74e0a8}.m-fragment{border-color:#e0cf74}.m-none{border-color:#e08a8a}.cite .q{color:var(--mut)}
ul{margin:3px 0;padding-left:18px}li{margin:1px 0}a{color:var(--acc);font-size:12px}
pre{background:#0c0e12;border:1px solid var(--bd);border-radius:6px;padding:8px;overflow:auto;font-size:11px;max-height:320px}
.empty{color:var(--mut);padding:30px;text-align:center}
.morebtn{display:block;width:100%;margin:12px 0;padding:12px;cursor:pointer;border:1px solid var(--bd);border-radius:8px;background:var(--card);color:var(--fg);font-size:14px}
.morebtn:hover{background:var(--bg)}
.tabs{display:flex;gap:2px;background:#12151c;border-bottom:1px solid var(--bd);padding:0 14px}
.tab{background:none;border:none;color:var(--mut);padding:12px 18px;cursor:pointer;font-size:13px;border-bottom:2px solid transparent}
.tab:hover{color:var(--fg)}.tab.on{color:var(--acc);border-bottom-color:var(--acc)}
.panel{display:none}.panel.on{display:block}
.ctl{display:flex;flex-direction:column;gap:6px;margin-bottom:10px}
.ctl .tg{display:flex;align-items:center;gap:6px;font-size:12.5px;color:#c6cfe0;cursor:pointer}
.ctl select{width:100%;background:var(--card);color:var(--fg);border:1px solid var(--bd);border-radius:7px;padding:7px 9px;font-size:12.5px}
.ctl .rng input{font-size:12px}
.cov{max-width:1000px;margin:0 auto;padding:24px 28px}
.cov h2{font-size:20px;margin:0 0 4px}.cov h3{font-size:13px;text-transform:uppercase;letter-spacing:.5px;color:var(--acc);margin:22px 0 8px}
.cov .lead{color:var(--mut);font-size:13px;margin:0 0 6px}
.cov table{border-collapse:collapse;width:100%;font-size:12.5px;margin:4px 0}
.cov td,.cov th{text-align:left;padding:4px 8px;border-bottom:1px solid var(--card2)}
.cov th{color:var(--mut);font-weight:500;font-size:11px;text-transform:uppercase}
.cov .bar{display:inline-block;height:10px;border-radius:3px;background:var(--acc);vertical-align:middle}
.cov .bar.lo{background:#e08a8a}.cov .bar.mi{background:#e0cf74}.cov .bar.hi{background:#74e0a8}
.cov .num{color:var(--mut);font-size:11.5px;margin-left:6px}
.cov .g-exact{color:#74e0a8}.cov .g-frag{color:#e0cf74}.cov .g-none{color:#e08a8a}
.arch{max-width:1000px;margin:0 auto;padding:24px 28px}
.arch h2{font-size:20px;margin:0 0 4px}.arch .lead{color:var(--mut);margin:0 0 20px;font-size:13.5px}
.arch .stat{display:flex;gap:18px;margin:0 0 22px;flex-wrap:wrap}
.arch .stat div{background:var(--card);border:1px solid var(--bd);border-radius:9px;padding:10px 16px}
.arch .stat b{font-size:20px;color:var(--acc);display:block}.arch .stat span{font-size:11.5px;color:var(--mut)}
.arch pre{background:#0d1016;border:1px solid var(--bd);border-radius:8px;padding:10px 12px;overflow-x:auto;font-size:12px;line-height:1.5;color:#cdd6e4;margin:6px 0}
.arch pre .c{color:#6b7585}
.arch .ask{background:#141a22;border-left:3px solid var(--acc);border-radius:0 8px 8px 0;padding:8px 12px;margin:6px 0;font-size:12.5px;color:#d7e0ec;font-style:italic}
.arch .ask b{font-style:normal;color:var(--acc)}
.stage{position:relative;background:var(--card);border:1px solid var(--bd);border-radius:11px;padding:14px 16px 14px 54px;margin:0 0 6px}
.stage .num{position:absolute;left:14px;top:14px;width:28px;height:28px;border-radius:50%;background:var(--acc);color:#0b1220;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:13px}
.stage h3{margin:0 0 4px;font-size:14.5px}.stage p{margin:0 0 7px;font-size:13px;color:#c6cfe0}
.stage .meta{font-size:11.5px;color:var(--mut)}.stage .meta code{background:#0c0e12;border:1px solid var(--bd);border-radius:4px;padding:1px 5px;color:#9fd0ff}
.stage a{font-size:11.5px}.arrow{text-align:center;color:var(--bd);font-size:16px;line-height:1;margin:1px 0}
.lane{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}
.lane .l{flex:1;min-width:150px;background:var(--card2);border:1px solid var(--bd);border-radius:7px;padding:8px 10px;font-size:11.5px}
.lane .l b{color:#74c2e0;font-size:12px}
.princip{background:#15110a;border:1px solid #3a3417;border-radius:10px;padding:13px 16px;margin:18px 0 0}
.princip h3{margin:0 0 8px;font-size:13px;color:#e0cf74}.princip li{font-size:12.5px;margin:3px 0;color:#d8cda0}
</style></head><body>
<div class=tabs><button class="tab on" data-tab=browse>🔎 Vyhledávání</button><button class=tab data-tab=cov>📊 Analýza extrakce</button><button class=tab data-tab=arch>🛠 Jak sbíráme data</button></div>
<div id=tab-browse class="panel on"><div class=wrap>
<aside>
<h1>Granty</h1><div class=sub>__N__ oportunit · __NP__ poskytovatelů · LLM-fasety</div>
<input class=q id=q placeholder="hledat ve všem…">
<div class=ctl>
<label class=tg><input type=checkbox id=hideclosed checked> skrýt uzavřené / historické</label>
<select id=sort class=q style="margin:0"><option value=def>řadit: výchozí</option><option value=deadline>deadline (nejbližší)</option><option value=amount>částka (nejvyšší)</option></select>
<div class=rng><input id=dlfrom type=date title="deadline od"><input id=dlto type=date title="deadline do"></div>
</div>
<div id=facets></div>
<details class=fg open><summary>Max. na žadatele (Kč)</summary><div class=rng><input id=amin type=number placeholder=od><input id=amax type=number placeholder=do></div></details>
<button class=clr id=clr>× zrušit filtry</button>
</aside>
<main><div class=cnt id=cnt></div><div id=list></div></main></div></div>
<div id=tab-cov class=panel>__COVERAGE__</div>
<div id=tab-arch class=panel>__ARCH__</div>
<script>
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{
 document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));
 document.querySelectorAll('.panel').forEach(x=>x.classList.remove('on'));
 t.classList.add('on');document.getElementById('tab-'+t.dataset.tab).classList.add('on');});
const DATA=__DATA__;
const L=__LABELS__;
const lab=v=>L[v]||v;
// pořadí dle priority hledače: KDE → KDO může → komu → na co → status, pak rámec, pak nice-to-have
const GROUPS=[{k:'kraj',t:'Kraj',arr:0,drill:'okres'},{k:'sektor',t:'Sektor žadatele',arr:1,drill:'typ_zadatele'},
 {k:'cilova',t:'Cílová skupina',arr:1},{k:'oblast_super',t:'Oblast podpory',arr:1,drill:'oblast'},
 {k:'status',t:'Status',arr:0},
 {k:'forma',t:'Forma podpory',arr:1},{k:'zdroj',t:'Zdroj financování',arr:1},{k:'rezim',t:'Režim příjmu',arr:0},{k:'delka',t:'Délka',arr:0},
 {k:'spoluucast',t:'Spoluúčast',arr:0},{k:'doctype',t:'Typ dokumentu',arr:1},{k:'vysledky',t:'Výsledková listina',arr:0},
 {k:'poskytovatel',t:'Poskytovatel',arr:0,drill:'source'},{k:'kind',t:'Typ',arr:0},
 {k:'mira',t:'Míra podpory',arr:0},{k:'podani',t:'Způsob podání',arr:1}];
// mapování typ žadatele → sektor (2. úroveň hierarchie) — JEDINÁ PRAVDA z data/consolidation_maps.json
// (sektor_of), aby drill a sektor-rollup nedivergovaly. Injektuje build_app.py.
const SEKTOR_OF=__SEKTOR_OF__;
const OBLAST_SUPER=__OBLAST_SUPER__;
const SRC_TYPE={};
// zploštění facet bloku do top-level klíčů pro filtr
DATA.forEach(d=>{const f=d.facets||{};const r=f.region||{};const ex=d.extra||{};
 d.oblast=f.oblast||[];d.oblast_super=[...new Set((f.oblast||[]).map(o=>OBLAST_SUPER[o]).filter(Boolean))];
 d.sektor=f.sektor_zadatele||[];d.typ_zadatele=f.typ_zadatele||[];
 d.poskytovatel=f.typ_poskytovatele||null;d.kraj=r.kraj||(r.celostatni?'celostátní':((d.kind==='grant'||d.kind==='program')?'neuvedeno':null));d.okres=r.okres||null;d.celostatni=!!r.celostatni;
 d.kraj_conf=r._conf;d.forma=f.forma_podpory||[];d.zdroj=f.zdroj_financovani||[];d.rezim=f.rezim_prijmu||null;
 d.delka=f.delka||null;d.podani=f.zpusob_podani||[];d.vyse_max=f.vyse_max_zadatel_czk||null;
 // nové facety z bohaté extrakce
 d.cilova=f.cilova_skupina||[];
 d.doctype=[...new Set((ex.dokumenty||[]).map(x=>x&&x.role).filter(Boolean))];
 d.spoluucast=f.spoluucast===true?'ano':(f.spoluucast===false?'ne':null);
 d.vysledky=(ex.prijemci&&ex.prijemci.length)?'ano':(d.kind==='grant'?'ne':null);
 d.multireg=f.multi_region?'ano':(r.kraj||r.celostatni?'ne':null);
 d.obdobi=ex.obdobi_realizace?'uvedeno':(d.kind==='grant'?'neuvedeno':null);
 const mp=f.mira_podpory_pct;d.mira=mp==null?null:(mp<=50?'do 50 %':mp<=70?'51–70 %':mp<=90?'71–90 %':'nad 90 %');
 if(d.poskytovatel)SRC_TYPE[d.source]=d.poskytovatel;});
const sel={};GROUPS.forEach(g=>sel[g.k]=new Set());sel.typ_zadatele=new Set();sel.source=new Set();sel.oblast=new Set();sel.okres=new Set();
const $=s=>document.querySelector(s),esc=s=>(s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const fmt=n=>n==null?'':n.toLocaleString('cs-CZ')+' Kč';
const valsOf=(d,k)=>{const v=d[k];return Array.isArray(v)?v:(v==null?[]:[v])};
const isDate=s=>/^\d{4}-\d{2}-\d{2}$/.test(s||'');
function passes(d,except){const q=$('#q').value.toLowerCase();if(q&&!JSON.stringify(d).toLowerCase().includes(q))return false;
 // skrýt uzavřené + výsledkové listiny (historie) — hledač chce ŽÁDAT
 if($('#hideclosed').checked&&d.kind==='grant'&&(d.status==='closed'||d.vysledky==='ano'))return false;
 if($('#hideclosed').checked&&d.kind==='program')return false; // katalog programů (ne časově ohraničená výzva)
 for(const k of Object.keys(sel)){if(k===except||!sel[k].size)continue;
  if(k==='kraj'){if(![...sel[k]].some(v=>v===d.kraj)&&!d.celostatni)return false;continue;} // celostátní platí všude
  if(![...sel[k]].some(v=>valsOf(d,k).includes(v)))return false;}
 if($('#amin').value||$('#amax').value){const a=d.vyse_max,lo=+$('#amin').value||0,hi=+$('#amax').value||Infinity;if(a==null||a<lo||a>hi)return false;}
 const df=$('#dlfrom').value,dt=$('#dlto').value;
 if(df||dt){const dd=(d.deadline||'').slice(0,10);if(!isDate(dd))return false;if(df&&dd<df)return false;if(dt&&dd>dt)return false;}
 return true;}
function counts(k,ex){const m={};DATA.filter(d=>passes(d,ex)).forEach(d=>valsOf(d,k).forEach(v=>{if(v!=null)m[v]=(m[v]||0)+1}));return m;}
function optHTML(k,v,n,sub){return `<label class="opt ${sub?'sub':''} ${n?'':'off'}"><input type=checkbox data-k="${esc(k)}" data-v="${esc(v)}" ${sel[k].has(v)?'checked':''}>${esc(lab(v))}<span class=c>${n||0}</span></label>`;}
// děti dané rodičovské hodnoty: sektor→jeho členské typy; typ poskytovatele→jeho poskytovatelé
function childrenFor(g,v){
  if(g.drill==='typ_zadatele')return [...new Set(DATA.flatMap(d=>d.typ_zadatele))].filter(t=>SEKTOR_OF[t]===v);
  if(g.drill==='oblast')return [...new Set(DATA.flatMap(d=>d.oblast))].filter(o=>OBLAST_SUPER[o]===v);
  if(g.drill==='okres')return [...new Set(DATA.filter(d=>d.kraj===v).map(d=>d.okres).filter(Boolean))];
  if(g.drill==='source')return [...new Set(DATA.filter(d=>SRC_TYPE[d.source]===v).map(d=>d.source))];
  return [];}
function renderFacets(){const cont=$('#facets'),aside=document.querySelector('aside');
  const openK=new Set([...cont.querySelectorAll('details[open]')].map(d=>d.dataset.g));  // zachovej rozbalené
  const firstRender=!cont.children.length, sv=aside?aside.scrollTop:0;
  const DEF=['oblast_super','sektor','cilova','kraj'];
  cont.innerHTML=GROUPS.map(g=>{const c=counts(g.k,g.k);
  let vals=Object.keys(c).sort((a,b)=>(sel[g.k].has(b)-sel[g.k].has(a))||(c[b]-c[a]));  // VYBRANÉ první, pak dle počtu
  let body=vals.map(v=>{let h=optHTML(g.k,v,c[v]);
    if(g.drill&&sel[g.k].has(v)){const sc=counts(g.drill,g.drill);
      h+=childrenFor(g,v).filter(s=>sc[s]).sort((a,b)=>sc[b]-sc[a]).map(s=>optHTML(g.drill,s,sc[s],1)).join('');}
    return h;}).join('');
  const isOpen=firstRender?DEF.includes(g.k):(openK.has(g.k)||sel[g.k].size>0);  // drž otevřené + aktivní
  const act=sel[g.k].size?`<span class=fa-n>${sel[g.k].size}</span>`:`<span class=fc>${vals.length}</span>`;
  return `<details class=fg data-g="${g.k}" ${isOpen?'open':''}><summary>${esc(g.t)}${act}</summary>${body}</details>`;}).join('');
  if(aside)aside.scrollTop=sv;}
const GF={grant:['focus_area','open_from','deadline','amount','eligible_applicants','required_attachments','how_to_apply','source_doc'],
 program:['focus_area','open_from','deadline','eligible_applicants','how_to_apply','source_doc'],
 foundation_mission:['mission','support_topics','regions','source_doc']};
function row(k,v){if(v==null||v===''||(Array.isArray(v)&&!v.length))return '';
 const vv=Array.isArray(v)?'<ul>'+v.map(x=>`<li>${esc(typeof x==='object'?JSON.stringify(x):x)}</li>`).join('')+'</ul>':esc(v);
 return `<div class=row><div class=k>${esc(k)}</div><div class=v>${vv}</div></div>`;}
function detail(d){let h='';
 (GF[d.kind]||[]).forEach(k=>h+=row(k,d[k]));
 const f=d.facets;
 if(f){h+='<div class=sec>fasety (LLM)</div>';
  const FK={oblast:'oblast',sektor_zadatele:'sektor žadatele',typ_zadatele:'typ žadatele',typ_poskytovatele:'poskytovatel',
   forma_podpory:'forma',zdroj_financovani:'zdroj',rezim_prijmu:'režim',delka:'délka',zpusob_podani:'podání',
   cilova_skupina:'cílová skupina',mira_podpory_pct:'míra podpory %',spoluucast:'spoluúčast',vyse_alokace_czk:'alokace Kč',vyse_max_zadatel_czk:'max/žadatel Kč'};
  Object.entries(FK).forEach(([k,t])=>{let v=f[k];if(Array.isArray(v))v=v.map(lab).join(', ');else v=v!=null?lab(v):'';if(v!=='')h+=row(t,v);});
  const r=f.region||{};if(r.obec||r.kraj||r.celostatni)h+=row('region',(r.celostatni?'celostátní':[r.obec,r.okres,r.kraj].filter(Boolean).join(' / '))+(r._conf==='low'?' (z poskytovatele)':' (z textu)'));}
 const cl=(d.provenance||{}).classification;
 if(cl){h+=`<div class=sec>klasifikace: ${esc(cl.base_type)} · ${esc(cl.confidence)}</div>`;
  if(cl.reasoning&&cl.reasoning.length)h+='<ul>'+cl.reasoning.map(r=>`<li>${esc(r)}</li>`).join('')+'</ul>';}
 const ci=d.citations||[];
 if(ci.length){h+=`<div class=sec>grounding (${ci.filter(c=>c.match==='exact').length} exact / ${ci.filter(c=>c.match==='fragment').length} fragment / ${ci.filter(c=>c.match==='none').length} none)</div>`;
  ci.forEach(c=>h+=`<div class="cite m-${c.match}"><b>${esc(c.field)}</b>: ${esc(c.value)} <span class=q>„${esc(String(c.quote||'').slice(0,150))}"</span></div>`);}
 const ex=d.extra||{};if(Object.keys(ex).length){h+='<div class=sec>extra (lossless)</div>';Object.entries(ex).forEach(([k,v])=>h+=row(k,v));}
 const pr=d.provenance||{};h+='<div class=sec>provenance</div>'+row('zdroj',d.source)+row('platforma',pr.platform)+row('harvester',pr.harvester)+row('URL',pr.harvest_url||d.source_url);
 const docs=pr.documents||[];
 if(docs.length){h+='<div class=sec>dokumenty ('+docs.length+')</div>';
  docs.forEach((doc,i)=>{const L=[];
   if(doc.url)L.push(`<a href="${esc(doc.url)}" target=_blank>originál ↗</a>`);
   if(doc.raw_rel)L.push(`<a href="${esc(doc.raw_rel)}" target=_blank>stažený${doc.ext?' .'+esc(doc.ext):''}</a>`);
   if(doc.md_rel)L.push(`<a href="${esc(doc.md_rel)}" target=_blank>md</a>`);
   else if(doc.txt_rel)L.push(`<a href="${esc(doc.txt_rel)}" target=_blank>text</a>`);
   h+=`<div class=row><div class=k>dok ${i+1}</div><div class=v>${L.join(' · ')||esc(doc.url||'?')}</div></div>`;});}
 h+=`<details><summary style="color:var(--mut);font-size:12px;cursor:pointer">raw JSON</summary><pre>${esc(JSON.stringify(d,null,1))}</pre></details>`;
 return h;}
const dlkey=d=>{const s=(d.deadline||'').slice(0,10);return isDate(s)?Date.parse(s):9e15;};  // nedatum/null = nakonec
let SHOWN=300;const STEP=500;const reRender=()=>{SHOWN=300;render();};  // nový filtr = od začátku
function render(){let rows=DATA.filter(d=>passes(d));
 const so=$('#sort').value;
 if(so==='deadline')rows=rows.slice().sort((a,b)=>dlkey(a)-dlkey(b));         // nejbližší první
 else if(so==='amount')rows=rows.slice().sort((a,b)=>(b.vyse_max||-1)-(a.vyse_max||-1));  // nejvyšší první
 $('#cnt').textContent=`${rows.length} / ${DATA.length} · ${new Set(rows.map(d=>d.source)).size} poskytovatelů`;
 $('#list').innerHTML=rows.slice(0,SHOWN).map(d=>{const i=DATA.indexOf(d);const sc='s-'+(d.status||'unknown');
  const kc=d.kind==='grant'?'':'b-mise';
  const ch=[...(d.oblast||[]).map(o=>`<span class="chip ob">${esc(lab(o))}</span>`),
   d.kraj?`<span class="chip kr ${d.kraj_conf==='low'?'low':''}">📍 ${esc(d.kraj)}${d.kraj_conf==='low'?'?':''}</span>`:'',
   d.poskytovatel?`<span class="chip po">${esc(lab(d.poskytovatel))}</span>`:'',
   ...(d.forma||[]).filter(x=>x!=='dotace').map(x=>`<span class=chip>${esc(lab(x))}</span>`)].join('');
  return `<div class=card data-i=${i}><div class=hd><div class=ti>${esc(d.title||d.name||'(bez názvu)')}</div>
   <div class=meta>${esc(d.source)} ${d.deadline?'· do '+esc(d.deadline):''} ${d.vyse_max?'· max '+fmt(d.vyse_max):''}
    <span class="badge ${d.kind==='grant'?sc:kc}">${esc(d.kind==='grant'?d.status:(d.kind==='program'?'program':'mise'))}</span></div>
   <div class=chips>${ch}</div></div><div class=body></div></div>`;}).join('')
   +(rows.length>SHOWN?`<button id=more class=morebtn>Zobrazit dalších ${Math.min(STEP,rows.length-SHOWN)} (zbývá ${rows.length-SHOWN})</button>`:'')||'<div class=empty>nic neodpovídá</div>';
 renderFacets();}
$('#list').addEventListener('click',e=>{if(e.target.id==='more'){SHOWN+=STEP;render();return;}
 const c=e.target.closest('.card');if(!c||e.target.closest('a'))return;
 c.classList.toggle('open');const b=c.querySelector('.body');if(c.classList.contains('open')&&!b.dataset.f){b.innerHTML=detail(DATA[+c.dataset.i]);b.dataset.f=1;}});
document.addEventListener('change',e=>{const t=e.target;if(t.dataset&&t.dataset.k&&t.type==='checkbox'){sel[t.dataset.k][t.checked?'add':'delete'](t.dataset.v);reRender();}});
['q','amin','amax','dlfrom','dlto'].forEach(id=>$('#'+id).addEventListener('input',reRender));
['sort','hideclosed'].forEach(id=>$('#'+id).addEventListener('change',reRender));
$('#clr').onclick=()=>{Object.values(sel).forEach(s=>s.clear());$('#q').value='';$('#amin').value='';$('#amax').value='';$('#dlfrom').value='';$('#dlto').value='';$('#sort').value='def';$('#hideclosed').checked=true;reRender();};
render();
</script></body></html>"""

LABELS = {
 "kultura_umeni":"Kultura","sport_volny_cas":"Sport/volný čas","socialni_sluzby":"Sociální","zdravi":"Zdraví",
 "vzdelavani_mladez":"Vzdělávání/mládež","zivotni_prostredi":"Životní prostředí","cestovni_ruch":"Cest. ruch",
 "veda_vyzkum":"Věda/výzkum","bydleni_infrastruktura":"Infrastruktura","bezpecnost":"Bezpečnost","rodina":"Rodina",
 "mezinarodni_spoluprace":"Mezinár. spolupráce","media":"Média","pamatkova_pece":"Památková péče",
 "doprava_mobilita":"Doprava/mobilita","it_digitalizace":"IT/digitalizace","nabozenstvi_cirkve":"Náboženství","ostatni":"Ostatní","mensiny":"Menšiny","komunitni_rozvoj":"Komunitní rozvoj","student":"Student","zakonny_zastupce":"Zákonný zástupce",
 "neziskovy":"Neziskový sektor","verejny":"Veřejný sektor","podnikatele":"Podnikatelé","fyzicke_osoby":"Fyzické osoby",
 "poskytovatele_sluzeb":"Poskytovatelé služeb","vlastnici":"Vlastníci","jine":"Jiné",
 "neziskovka":"nezisk. (obecně)","spolek":"spolek","sportovni_klub":"sportovní klub","cirkev":"církev",
 "pacientska_organizace":"pacientská org.","prispevkova_organizace":"příspěvková org.","obec_verejny_subjekt":"obec/veřejný",
 "skola_vyzkumna_org":"škola/VO","firma":"firma","osvc_podnikatel":"OSVČ","fyzicka_osoba":"fyzická osoba",
 "vlastnik_nemovitosti":"vlastník nemovitosti","poskytovatel_zdrav_sluzeb":"zdrav. zařízení","poskytovatel_soc_sluzeb":"poskyt. soc. služeb",
 "spolecenstvi_vlastniku":"SVJ","sdruzeni_obci":"sdružení obcí","zakonny_zastupce":"zákonný zástupce","organizator_akci":"organizátor akcí",
 "ministerstvo":"Ministerstvo","samosprava_obec":"Obec/město","samosprava_kraj":"Kraj","statni_fond":"Státní fond",
 "nadace":"Nadace","firemni_nadace":"Firemní nadace","nadacni_fond":"Nadační fond","eu_mezinarodni":"EU/mezinár.","skola_univerzita":"Škola/univerzita",
 "dotace":"Dotace","zapujcka_uver":"Zápůjčka/úvěr","stipendium":"Stipendium","cena_soutez":"Cena/soutěž","vecny_dar":"Věcný dar",
 "narodni_rozpocet":"Národní rozpočet","eu_fondy":"EU fondy","npo":"NPO","ehp_norsko":"EHP/Norsko","krajsky":"Krajský/obecní","vlastni_zdroje":"Vlastní zdroje",
 "jednorazova_vyzva":"Jednorázová výzva","prubezna":"Průběžná","kolova":"Kolová","jednoleta":"Jednoletá","viceleta":"Víceletá",
 "datova_schranka":"Datová schránka","posta":"Pošta","osobne":"Osobně","online_portal":"Online portál","email":"E-mail",
 "verejnost":"Veřejnost","osoby_se_zdravotnim_postizenim":"Osoby se zdrav. postižením","seniori":"Senioři","pacienti":"Pacienti",
 "ohrozene_skupiny":"Ohrožené skupiny","sportovci":"Sportovci","kulturni_pracovnici":"Kulturní pracovníci","rodiny":"Rodiny",
 "vlastnici_najemnici_bytu":"Vlastníci/nájemníci bytů","uzivatele_socialnich_sluzeb":"Uživatelé soc. služeb","zdravotnici":"Zdravotníci",
 "studenti":"Studenti","narodnostni_mensiny":"Národnostní menšiny","pecujici":"Pečující osoby","cizinci_migranti":"Cizinci/migranti",
 "dobrovolnici":"Dobrovolníci","veda_vyzkum_komunita":"Vědecká komunita",
 "pravidla_podminky":"Pravidla/podmínky","vyhlaseni":"Vyhlášení výzvy","formular_zadosti":"Formulář žádosti","vzor_smlouvy":"Vzor smlouvy",
 "vysledky":"Výsledky","metodika":"Metodika","priloha":"Příloha",
 "lide_socialni":"Lidé a sociální","kultura_vzdelavani":"Kultura a vzdělávání","sport_volny_cas_super":"Sport a volný čas",
 "prostredi_infra":"Prostředí a infrastruktura","ekonomika_inovace":"Ekonomika a inovace","komunita_ostatni":"Komunita a ostatní","podnikani":"Podnikání",
 "grant":"výzva","foundation_mission":"mise","program":"program (katalog)"}

def arch_html(n, np):
    """Vizuální README pipeline (self-contained, odkazy relativní z data/ na ../scripts a ../docs)."""
    S = "../scripts/"; D = "../docs/"
    def lnk(path, label=None):
        return f'<a href="{path}" target=_blank>{label or path.split("/")[-1]}</a>'
    return f"""<div class=arch>
<h2>🛠 Jak sbíráme grantová data</h2>
<p class=lead>Dvouvrstvý model: tenké per-CMS harvestery (jen TEXT+dokumenty) → jeden univerzální LLM extraktor (próza+PDF → strukturované pole). Status počítá KÓD, ne model. Každé pole má doslovnou citaci (grounding). Plný recept: {lnk('../README.md','README.md')} · {lnk('../CLAUDE.md','CLAUDE.md')}.</p>
<div class=stat>
 <div><b>{np}</b><span>poskytovatelů</span></div>
 <div><b>{n}</b><span>oportunit</span></div>
 <div><b>~83</b><span>CMS platforem</span></div>
 <div><b>5</b><span>přístupových archetypů</span></div>
 <div><b>2</b><span>vrstvy (harvest → LLM)</span></div>
</div>

<div class=stage><div class=num>0</div><h3>Zdroje &amp; detekce platformy</h3>
<p>Grantové weby obcí, krajů, ministerstev a nadací. Platformu neurčuje label, ale <b>strukturální otisk</b> (slité labely schovávaly ~65 grantových zdrojů v UNKNOWN).</p>
<div class=meta>skripty: {lnk(S+'cms_similarity.py')} · {lnk(S+'platform_refingerprint.py')} · {lnk(S+'diversity_finder.py')} &nbsp;|&nbsp; docs: {lnk(D+'platform_playbook.md')} · {lnk(D+'detection.md')}</div></div>
<div class=arrow>▼</div>

<div class=stage><div class=num>1</div><h3>Vrstva 1 — Harvest (lossless)</h3>
<p>~12 tenkých parserů per CMS-rodina. Vytahují jen <b>TEXT + odkazy na dokumenty</b> — nic nezahazují (plný raw). 5 přístupových archetypů:</p>
<div class=lane>
 <div class=l><b>REST</b> WordPress /wp-json (85 webů) — {lnk(S+'wp_harvest.py')}</div>
 <div class=l><b>inline-JS</b> dsw2/Otevřená města (var fonds=…) — {lnk(S+'dsw2.py')}</div>
 <div class=l><b>HTML-listing</b> vismo úřední deska — {lnk(S+'vismo.py')} · {lnk(S+'vismo_detail.py')}</div>
 <div class=l><b>Kentico/ASP.NET</b> IROP, MV — {lnk(S+'kentico_irop.py')} · {lnk(S+'mv_cms.py')}</div>
 <div class=l><b>SPA-grid → XHR replay</b> 1× odposlech Playwrightem → čistý HTTP — {lnk(S+'lewis_discover.py')}</div>
</div></div>
<div class=arrow>▼</div>

<div class=stage><div class=num>2</div><h3>Doc-store — dokumenty → text</h3>
<p>Stažení příloh (PDF/DOC/XLS) a převod na text. Univerzální napříč handlery (File.ashx, /getmedia, přímé .pdf). Konvertory dle typu:</p>
<div class=lane>
 <div class=l><b>PDF</b> pdftotext; skeny → OCR (tesseract ces+eng)</div>
 <div class=l><b>Excel</b> openpyxl/xlrd, všechny listy <span style=color:#74e0a8>(textutil Excel neumí → dřív balast)</span></div>
 <div class=l><b>DOC/DOCX/ODT</b> textutil / soffice</div>
</div>
<div class=meta style=margin-top:7px>skripty: {lnk(S+'dsw2_fetch.py')} · {lnk(S+'docstore.py')} · {lnk(S+'fix_docs.py')} (oprava balastu)</div></div>
<div class=arrow>▼</div>

<div class=stage><div class=num>3</div><h3>Vrstva 2 — Klasifikace (LLM)</h3>
<p>Sonnet agent určí <b>base_type</b> dokumentu z obsahu (tělo+přílohy): grant / news / foundation_mission / administrative / other. Odfiltruje ne-oportunity. 1 dokument = 1 agent.</p>
<div class=meta>workflow: {lnk(S+'classify_wf.js')} &nbsp;|&nbsp; prompt: kaskádový návod (ne slovník), kotva = „jsou tu konkrétní peníze pro žadatele?"</div></div>
<div class=arrow>▼</div>

<div class=stage><div class=num>4</div><h3>Vrstva 2 — Extrakce (LLM)</h3>
<p>Jeden univerzální extraktor: z <b>PLNÉHO textu + všech příloh</b> (neořezáváno, cap 150k jen safety) do bohatého schématu — oblast, cílová skupina, částky, deadliny, region→geo, dokumenty s rolí, kontakt, příjemci (výsledkové listiny), sběrače. <b>1 oportunita = 1 Sonnet agent.</b> Ke každému poli doslovná <b>evidence</b>.</p>
<div class=meta>workflow: {lnk(S+'extract_wf.js')} &nbsp;|&nbsp; serializace: agent zapíše JSON Write toolem do souboru → batch {lnk(S+'repair_out.py','json_repair')} (StructuredOutput se na bohatém schématu láme) &nbsp;|&nbsp; schéma: {lnk('../schema/opportunity_schema.md','opportunity_schema.md')}</div></div>
<div class=arrow>▼</div>

<div class=stage><div class=num>5</div><h3>Status v kódu (ne LLM)</h3>
<p>Otevřená a uzavřená výzva jsou textově identické — liší se jen datem vs. dnešek. Proto <b>status (announced/open/closed) počítá kód</b> z open_from/deadline, ne model (ten by halucinoval).</p>
<div class=meta>kód: {lnk(S+'opportunities.py')} → compute_status()</div></div>
<div class=arrow>▼</div>

<div class=stage><div class=num>6</div><h3>Ingest — kanonické úložiště</h3>
<p>Sjednocení do <code>opportunities.jsonl</code>: ploché pole + <b>sběrače</b> (deadline+deadliny[], vyse+castky[]), <b>region→geo</b>, <b>provenance</b> (vazba na zdroj + stažené soubory) a <b>citations</b> (grounding: evidence lokalizovaná v souboru → klikni a ověř; exact/fragment/none). Nic se nezahazuje (extra).</p>
<div class=meta>skripty: {lnk(S+'ingest_rich.py')} · {lnk(S+'opportunities.py')}</div></div>
<div class=arrow>▼</div>

<div class=stage><div class=num>7</div><h3>Konsolidace facet</h3>
<p>Otevřená extrakce tříští hodnoty (diakritika, varianty, hyperspecifika). Deterministický remap <b>varianta→kanon</b> + sektor rollup + normalizace krajů.</p>
<div class=meta>skript: {lnk(S+'consolidate.py')} &nbsp;|&nbsp; mapy: {lnk('../data/consolidation_maps.json','consolidation_maps.json')}</div></div>
<div class=arrow>▼</div>

<div class=stage><div class=num>8</div><h3>Tato aplikace</h3>
<p>Fasetový prohlížeč nad <code>opportunities.jsonl</code> — filtry (oblast, sektor, cílová skupina, kraj, forma, …), detail s grounding citacemi a odkazy na originální dokumenty.</p>
<div class=meta>generátor: {lnk(S+'build_app.py')} &nbsp;|&nbsp; coverage cyklus: {lnk(D+'coverage.md')}</div></div>

<div class=princip><h3>Pevná pravidla pipeline</h3><ul>
<li><b>Status v kódu, ne LLM</b> — model klasifikuje TYP, datum vs. dnešek počítá kód.</li>
<li><b>Neořezávat vstup do LLM</b> — plný text + přílohy (ořez sráží přesnost částek z 90 % na 27 %); limity jen na sondy/safety.</li>
<li><b>Lossless</b> — co se nevejde do schématu, jde do <code>extra</code>; zdroj pravdy zůstává vrstva 1.</li>
<li><b>Grounding</b> — každé pole má doslovnou citaci lokalizovanou ve zdroji; verdikt necháváme na člověku.</li>
<li><b>Struktura před prózou</b> — nejdřív strukturovaný endpoint (API/XHR/inline-JS), LLM až když je detail neredukovatelně próza/PDF.</li>
</ul></div>

<div class=princip style="background:#0a1518;border-color:#173a3a"><h3 style=color:#74c2e0>📦 Data v repozitáři (reprodukovatelnost)</h3><ul style=color:#a8cdd0>
<li>Raw data jsou komprimovaná v <code>data_bundle/</code> (~1,9 GB) — rozbal {lnk('../scripts/unpack_data.sh','unpack_data.sh')} → <code>data/</code>.</li>
<li><b>core</b> (opportunities.jsonl + harvest jsonl + configy + app) · <b>doctext</b> (vytěžený text z PDF/xls) · <b>wpfull</b> (WP korpus) · <b>originals</b> (PDF/xls/doc originály, split na 95 MB kvůli GitHub limitu 100 MB/soubor).</li>
<li>PDF originály se nekomprimují (interně DEFLATE) → 1,8 GB; jejich TEXT je ale v <code>doctext</code>, takže pipeline jede i bez nich.</li>
</ul></div>
</div>"""


def coverage_html(recs):
    """Tab „Analýza extrakce" — pokrytí polí/facet z různých pohledů (pole, grounding, zdroj, oblast, čas, bohatost)."""
    from collections import Counter
    g = [r for r in recs if r.get("kind") == "grant"]
    N = max(len(g), 1)
    nonempty = lambda v: v not in (None, "", [], {})

    def bar(pct):
        cls = "lo" if pct < 40 else ("mi" if pct < 70 else "hi")
        return f'<span class="bar {cls}" style="width:{max(2, round(pct*1.1))}px"></span><span class=num>{pct}%</span>'

    def cov(getter):
        c = sum(1 for r in g if nonempty(getter(r)))
        return c, round(100 * c / N)

    # 1) pokrytí polí
    top = [("deadline", "deadline (lhůta podání)"), ("open_from", "začátek příjmu"),
           ("eligible_applicants", "kdo může žádat"), ("how_to_apply", "jak podat"),
           ("required_attachments", "povinné přílohy"), ("focus_area", "zaměření")]
    fac = [("typ_zadatele", "typ žadatele"), ("cilova_skupina", "cílová skupina"),
           ("vyse_max_zadatel_czk", "max na žadatele (Kč)"), ("vyse_alokace_czk", "alokace (Kč)"),
           ("spoluucast", "spoluúčast"), ("mira_podpory_pct", "míra podpory %"),
           ("rezim_prijmu", "režim příjmu"), ("delka", "délka")]
    col = [("castky", "částky (sběrač)"), ("deadliny", "deadliny (sběrač)"),
           ("dokumenty", "dokumenty"), ("prijemci", "příjemci (výsledky)")]
    rows = ""
    for k, lab in top:
        c, p = cov(lambda r, k=k: r.get(k)); rows += f"<tr><td>{lab}</td><td>{bar(p)}</td><td class=num>{c}/{N}</td></tr>"
    for k, lab in fac:
        c, p = cov(lambda r, k=k: (r.get('facets', {}) or {}).get(k)); rows += f"<tr><td>{lab}</td><td>{bar(p)}</td><td class=num>{c}/{N}</td></tr>"
    for k, lab in col:
        c, p = cov(lambda r, k=k: (r.get('extra', {}) or {}).get(k)); rows += f"<tr><td>{lab}</td><td>{bar(p)}</td><td class=num>{c}/{N}</td></tr>"
    t_fields = f"<table><tr><th>pole</th><th>pokrytí (% z {N} grantů)</th><th></th></tr>{rows}</table>"

    # 2) grounding per pole
    gm = Counter()
    for r in g:
        for c in r.get("citations", []):
            gm[(c.get("field"), c.get("match"))] += 1
    grows = ""
    for fld in ["deadline", "eligible_applicants", "focus_area", "open_from", "amount", "title"]:
        e, fr, no = gm.get((fld, "exact"), 0), gm.get((fld, "fragment"), 0), gm.get((fld, "none"), 0)
        t = e + fr + no
        if t:
            grows += (f"<tr><td>{fld}</td><td class=g-exact>{round(100*e/t)}% exact</td>"
                      f"<td class=g-frag>{round(100*fr/t)}% fragment</td><td class=g-none>{round(100*no/t)}% none</td><td class=num>n={t}</td></tr>")
    t_ground = f"<table><tr><th>pole</th><th colspan=3>grounding (lokalizace citace ve zdroji)</th><th></th></tr>{grows}</table>"

    # 3) per zdroj (kvalita extrakce dle poskytovatele)
    src = Counter(r["source"] for r in g)
    srows = ""
    for s, c in src.most_common(12):
        gg = [r for r in g if r["source"] == s]
        dl = round(100 * sum(1 for r in gg if r.get("deadline")) / c)
        am = round(100 * sum(1 for r in gg if (r.get('facets', {}) or {}).get('vyse_max_zadatel_czk')) / c)
        srows += f"<tr><td>{s}</td><td class=num>{c}</td><td>{bar(dl)}</td><td>{bar(am)}</td></tr>"
    t_src = f"<table><tr><th>poskytovatel</th><th>grantů</th><th>deadline %</th><th>částka %</th></tr>{srows}</table>"

    # 4) per oblast (liší se pokrytí dle domény?)
    orows = ""
    obl = Counter()
    for r in g:
        for o in ((r.get('facets', {}) or {}).get('oblast') or []):
            obl[o] += 1
    for o, c in obl.most_common(10):
        gg = [r for r in g if o in ((r.get('facets', {}) or {}).get('oblast') or [])]
        dl = round(100 * sum(1 for r in gg if r.get("deadline")) / c)
        am = round(100 * sum(1 for r in gg if (r.get('facets', {}) or {}).get('vyse_max_zadatel_czk')) / c)
        orows += f"<tr><td>{o}</td><td class=num>{c}</td><td>{bar(dl)}</td><td>{bar(am)}</td></tr>"
    t_obl = f"<table><tr><th>oblast</th><th>grantů</th><th>deadline %</th><th>částka %</th></tr>{orows}</table>"

    # 5) status & temporální použitelnost
    import re as _re
    st = Counter(r.get("status") for r in g)
    fut = past = roll = noparse = 0
    for r in g:
        dd = r.get("deadline") or ""
        if dd in ("průběžně", "rolling"):
            roll += 1; continue
        m = _re.match(r"(\d{4})-(\d{2})-(\d{2})", dd)
        if not m:
            noparse += 1
        elif dd >= "2026-06-05":
            fut += 1
        else:
            past += 1
    t_temp = (f"<p class=lead><b>Status</b> (počítá kód z dat, ne LLM): "
              + " · ".join(f"{k}={v}" for k, v in st.most_common())
              + f"</p><p class=lead><b>Deadline</b>: 🟢 v budoucnu (akční) <b>{fut}</b> · průběžně {roll} · 🔴 v minulosti {past} · bez data {noparse}</p>")

    # 6) bohatost facet (distinct + singletony = tříštivost)
    facets = ["oblast", "typ_zadatele", "cilova_skupina", "forma_podpory", "zdroj_financovani"]
    frows = ""
    for fk in facets:
        cc = Counter()
        for r in g:
            for v in ((r.get('facets', {}) or {}).get(fk) or []):
                cc[v] += 1
        sing = sum(1 for v, n in cc.items() if n == 1)
        frows += f"<tr><td>{fk}</td><td class=num>{len(cc)} hodnot</td><td class=num>{sing} singletonů</td></tr>"
    t_facet = f"<table><tr><th>facet</th><th>distinct</th><th>tříštivost</th></tr>{frows}</table>"

    return (f"<div class=cov><h2>📊 Analýza extrakce</h2>"
            f"<p class=lead>Pokrytí polí a facet z {N} grantů — z různých pohledů. Bary: 🔴&lt;40 % · 🟡40–70 % · 🟢&gt;70 %.</p>"
            f"<h3>Pokrytí polí (kolik grantů má danou hodnotu)</h3>{t_fields}"
            f"<h3>Grounding — verifikovatelnost citací</h3>{t_ground}"
            f"<h3>Temporální použitelnost (lze ještě žádat?)</h3>{t_temp}"
            f"<h3>Kvalita extrakce dle poskytovatele</h3>{t_src}"
            f"<h3>Pokrytí dle oblasti (liší se podle domény?)</h3>{t_obl}"
            f"<h3>Bohatost / tříštivost facet</h3>{t_facet}</div>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/opportunities.jsonl")
    ap.add_argument("--out", default="data/grants_app.html")
    a = ap.parse_args()
    recs = [json.loads(l) for l in open(a.inp, encoding="utf-8")]
    np = len({r.get("source") for r in recs})
    import os
    mp = os.path.join(os.path.dirname(a.inp) or ".", "consolidation_maps.json")
    M = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    html = (TPL.replace("__DATA__", json.dumps(recs, ensure_ascii=False))
               .replace("__LABELS__", json.dumps(LABELS, ensure_ascii=False))
               .replace("__SEKTOR_OF__", json.dumps(M.get("sektor_of", {}), ensure_ascii=False))
               .replace("__OBLAST_SUPER__", json.dumps(M.get("oblast_super", {}), ensure_ascii=False))
               .replace("__ARCH__", arch_html(len(recs), np))
               .replace("__COVERAGE__", coverage_html(recs))
               .replace("__NP__", str(np)).replace("__N__", str(len(recs))))
    open(a.out, "w", encoding="utf-8").write(html)
    print(json.dumps({"MARKER": "APP", "records": len(recs), "providers": np,
                      "out": a.out, "kb": round(len(html)/1024)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
