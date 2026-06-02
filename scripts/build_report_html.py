#!/usr/bin/env python3
"""Vygeneruj self-contained HTML prohlížeč data/opportunities.jsonl (offline, data embedded).
Filtry (platforma/typ/status/poskytovatel + fulltext), karty s kompletním detailem
(všechna pole + provenance.classification.reasoning + citace/grounding + extra + raw JSON).

  python3 scripts/build_report_html.py  [--in data/opportunities.jsonl] [--out data/opportunities.html]
"""
import argparse, json, html

TPL = """<!doctype html><html lang=cs><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Grantové oportunity — %(n)d od %(np)d poskytovatelů</title>
<style>
:root{--bg:#0f1115;--card:#1a1d24;--mut:#8b93a7;--bd:#2a2f3a;--fg:#e6e9ef;--acc:#5b9dff}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
header{position:sticky;top:0;background:#12151c;border-bottom:1px solid var(--bd);padding:10px 16px;z-index:5}
h1{font-size:16px;margin:0 0 8px}.stats{color:var(--mut);font-size:12px}
.ctl{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.ctl input,.ctl select{background:var(--card);color:var(--fg);border:1px solid var(--bd);border-radius:6px;padding:6px 8px}
.ctl input{flex:1;min-width:180px}
main{padding:12px 16px;max-width:1100px;margin:0 auto}
.card{background:var(--card);border:1px solid var(--bd);border-radius:8px;margin:8px 0;overflow:hidden}
.hd{padding:10px 12px;cursor:pointer;display:flex;gap:8px;align-items:flex-start}
.hd:hover{background:#20242e}.ti{font-weight:600;flex:1}
.badge{font-size:11px;padding:2px 7px;border-radius:10px;white-space:nowrap}
.b-grant{background:#173a2a;color:#74e0a8}.b-mise{background:#3a3417;color:#e0cf74}
.s-open{background:#173a2a;color:#74e0a8}.s-closed{background:#3a1a1a;color:#e08a8a}
.s-unknown{background:#2a2f3a;color:#9aa3b5}.s-announced{background:#1a2e3a;color:#74c2e0}
.src{font-size:12px;color:var(--mut)}
.body{display:none;padding:0 12px 12px;border-top:1px solid var(--bd)}
.card.open .body{display:block}
.row{display:flex;gap:8px;padding:3px 0;border-bottom:1px solid #20242e}
.k{color:var(--mut);min-width:140px;font-size:12px}.v{flex:1;white-space:pre-wrap;word-break:break-word}
.sec{margin-top:10px;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--acc)}
ul{margin:3px 0;padding-left:18px}li{margin:1px 0}
.cite{font-size:12px;border-left:2px solid var(--bd);padding:2px 8px;margin:3px 0}
.m-exact{border-color:#74e0a8}.m-fragment{border-color:#e0cf74}.m-none{border-color:#e08a8a}
.cite .q{color:var(--mut)}a{color:var(--acc)}details{margin-top:8px}summary{cursor:pointer;color:var(--mut);font-size:12px}
pre{background:#0c0e12;border:1px solid var(--bd);border-radius:6px;padding:8px;overflow:auto;font-size:11px;max-height:300px}
.hide{display:none}
</style></head><body>
<header>
<h1>Grantové oportunity</h1>
<div class=stats id=stats></div>
<div class=ctl>
<input id=q placeholder="hledat (titul, zdroj, text…)">
<select id=fplat></select><select id=fkind></select><select id=fstatus></select><select id=fsrc></select>
</div></header>
<main id=list></main>
<script>
const DATA = %(data)s;
const $=s=>document.querySelector(s);
const esc=s=>(s==null?'':String(s)).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const host=u=>(u||'').replace(/^https?:\\/\\/(www\\.)?/,'').split('/')[0];
function uniq(f){return [...new Set(DATA.map(f).filter(x=>x!=null))].sort();}
function opt(sel,vals,label){sel.innerHTML='<option value="">'+label+' (vše)</option>'+vals.map(v=>`<option>${esc(v)}</option>`).join('');}
opt($('#fplat'),uniq(d=>(d.provenance||{}).platform||'přímý web'),'platforma');
opt($('#fkind'),uniq(d=>d.kind),'typ');
opt($('#fstatus'),uniq(d=>d.status||'—'),'status');
opt($('#fsrc'),uniq(d=>d.source),'poskytovatel');

const FIELDS={grant:['focus_area','open_from','deadline','amount','eligible_applicants','required_attachments','how_to_apply','source_doc'],
 foundation_mission:['mission','support_topics','regions','source_doc']};
function row(k,v){if(v==null||v===''||(Array.isArray(v)&&!v.length))return '';
 const vv=Array.isArray(v)?'<ul>'+v.map(x=>`<li>${esc(typeof x==='object'?JSON.stringify(x):x)}</li>`).join('')+'</ul>':esc(v);
 return `<div class=row><div class=k>${esc(k)}</div><div class=v>${vv}</div></div>`;}
function detail(d){let h='';
 (FIELDS[d.kind]||[]).forEach(k=>h+=row(k,d[k]));
 const cl=(d.provenance||{}).classification;
 if(cl){h+=`<div class=sec>klasifikace: ${esc(cl.base_type)} · ${esc(cl.confidence)}</div>`;
  if(cl.reasoning&&cl.reasoning.length)h+='<ul>'+cl.reasoning.map(r=>`<li>${esc(r)}</li>`).join('')+'</ul>';}
 const ci=d.citations||[];
 if(ci.length){h+=`<div class=sec>citace / grounding (${ci.filter(c=>c.match==='exact').length} exact, ${ci.filter(c=>c.match==='fragment').length} fragment, ${ci.filter(c=>c.match==='none').length} none)</div>`;
  ci.forEach(c=>{h+=`<div class="cite m-${c.match}"><b>${esc(c.field)}</b>: ${esc(c.value)} <span class=q>„${esc((c.quote||'').slice(0,160))}"</span> [${esc(c.match)}]</div>`;});}
 const ex=d.extra||{};
 if(Object.keys(ex).length){h+='<div class=sec>extra (lossless)</div>';Object.entries(ex).forEach(([k,v])=>h+=row(k,v));}
 const pr=d.provenance||{};
 h+='<div class=sec>provenance</div>';
 h+=row('platform',pr.platform)+row('harvester',pr.harvester)+row('harvest_file',pr.harvest_file)+row('zdroj URL',pr.harvest_url||d.source_url);
 (pr.documents||[]).forEach((doc,i)=>h+=row('dokument '+(i+1),(doc.url||'')+(doc.txt_path?'  ✓txt':'')));
 h+=`<details><summary>raw JSON</summary><pre>${esc(JSON.stringify(d,null,1))}</pre></details>`;
 return h;}
function render(){
 const q=$('#q').value.toLowerCase(),fp=$('#fplat').value,fk=$('#fkind').value,fs=$('#fstatus').value,fr=$('#fsrc').value;
 const rows=DATA.filter(d=>{
  const plat=(d.provenance||{}).platform||'přímý web';
  if(fp&&plat!==fp)return false; if(fk&&d.kind!==fk)return false;
  if(fs&&(d.status||'—')!==fs)return false; if(fr&&d.source!==fr)return false;
  if(q){const blob=JSON.stringify(d).toLowerCase();if(!blob.includes(q))return false;} return true;});
 $('#stats').textContent=`${rows.length} / ${DATA.length} oportunit · ${new Set(rows.map(d=>d.source)).size} poskytovatelů zobrazeno`;
 $('#list').innerHTML=rows.map((d,i)=>{
  const kc=d.kind==='grant'?'b-grant':'b-mise',sc='s-'+(d.status||'unknown');
  const plat=(d.provenance||{}).platform;
  return `<div class=card data-i=${DATA.indexOf(d)}>
   <div class=hd><div class=ti>${esc(d.title||d.name||'(bez názvu)')}
     <div class=src>${esc(d.source)}${plat?' · '+esc(plat):''} · ${esc(d.deadline||d.open_from||'')}</div></div>
   <span class="badge ${kc}">${esc(d.kind==='grant'?'grant':'mise')}</span>
   ${d.status?`<span class="badge ${sc}">${esc(d.status)}</span>`:''}</div>
   <div class=body></div></div>`;}).join('')||'<p style="color:var(--mut)">nic nenalezeno</p>';
}
$('#list').addEventListener('click',e=>{const c=e.target.closest('.card');if(!c)return;
 c.classList.toggle('open');const b=c.querySelector('.body');if(c.classList.contains('open')&&!b.dataset.f){b.innerHTML=detail(DATA[+c.dataset.i]);b.dataset.f=1;}});
['q','fplat','fkind','fstatus','fsrc'].forEach(id=>$('#'+id).addEventListener('input',render));
render();
</script></body></html>"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/opportunities.jsonl")
    ap.add_argument("--out", default="data/opportunities.html")
    args = ap.parse_args()
    recs = [json.loads(l) for l in open(args.inp, encoding="utf-8")]
    providers = len({r.get("source") for r in recs})
    out = TPL % {"n": len(recs), "np": providers,
                 "data": json.dumps(recs, ensure_ascii=False)}
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(out)
    print(json.dumps({"MARKER": "REPORT_HTML", "records": len(recs), "providers": providers,
                      "out": args.out, "kb": round(len(out) / 1024)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
