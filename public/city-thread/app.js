/* CITY THREAD v0.3 · Dawn edition
 * Source: official Berlin WFS geodata frozen to fountains.json (2026-10-09).
 * Browser query presets are fixed evaluators; full RDF + SHACL are separate files.
 * No tracking. No invented climate-data joins.
 */
(() => {
'use strict';
const $ = (q,host=document)=>host.querySelector(q);
const $$=(q,host=document)=>Array.from(host.querySelectorAll(q));
const SVG='http://www.w3.org/2000/svg';
const node=(tag,txt,cls)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=String(txt??'');if(cls)e.className=cls;return e;};
const add=(p,x)=>{p.appendChild(x);return x;};
const wipe=p=>{p.replaceChildren();return p;};
const ssvg=(tag,attrs={})=>{const e=document.createElementNS(SVG,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));return e;};
const fmt=n=>Number(n).toLocaleString('de-DE');
const slug=s=>String(s??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-zA-Z0-9]+/g,'-').replace(/^-|-$/g,'').toLowerCase();
const state={meta:null,records:[],filtered:[],selected:null,view:'discover',shown:8,question:0,scenario:'clean',graphFocus:'district',loaded:false};
const validViews=new Set(['discover','graph','ask','trust','learn']);
let toastTimer;
function toast(message){
  const target=$('#toast');target.textContent=message;target.classList.add('visible');
  window.clearTimeout(toastTimer);toastTimer=window.setTimeout(()=>target.classList.remove('visible'),3000);
}
function go(view,{push=true,scroll=true}={}){
  if(!validViews.has(view))return;
  state.view=view;
  $$('.view').forEach(e=>e.classList.toggle('active',e.id==='view-'+view));
  $$('[data-view].nav-item').forEach(b=>{const active=b.dataset.view===view;b.classList.toggle('active',active);if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
  if(push&&location.hash!==('#'+view))history.pushState({},'','#'+view);
  if(view==='graph')renderGraph();
  if(view==='ask')renderAnswers();
  if(view==='learn')renderLearningTriple();
  if(scroll)window.scrollTo({top:0,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
}
$$('[data-view]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.view)));
$('.brand').addEventListener('click',e=>{e.preventDefault();go('discover');});
window.addEventListener('popstate',()=>go(location.hash.slice(1)||'discover',{push:false}));
$('#start-explore').addEventListener('click',()=>$('#explore').scrollIntoView({behavior:'smooth',block:'start'}));
$('[data-goto]').forEach(b=>b.addEventListener('click',()=>{go('discover');requestAnimationFrame(()=>$('#explore').scrollIntoView({behavior:'smooth',block:'start'}));}));
$('#share').addEventListener('click',async()=>{
 const link=location.origin+location.pathname;
 try{await navigator.clipboard.writeText(link);toast('Der Link ist kopiert ✳');}
 catch{window.prompt('Teile diesen Link:',link);}
});
const mapBounds={west:13.10,east:13.77,south:52.35,north:52.69};
const mapX=lon=>30+(lon-mapBounds.west)/(mapBounds.east-mapBounds.west)*678;
const mapY=lat=>415-(lat-mapBounds.south)/(mapBounds.north-mapBounds.south)*366;
const gridColor='#AABACB';
function renderMap(){
  const host=wipe($('#atlas-svg'));
  const defs=add(host,ssvg('defs'));
  const grid=add(defs,ssvg('pattern',{id:'ct-map-grid',width:38,height:38,patternUnits:'userSpaceOnUse'}));
  add(grid,ssvg('path',{d:'M38 0H0V38',fill:'none',stroke:gridColor,'stroke-width':'.9','stroke-opacity':'.35'}));
  add(host,ssvg('rect',{width:740,height:450,fill:'url(#ct-map-grid)'}));
  for(let i=0;i<3;i++){
    add(host,ssvg('path',{d:'M'+(90+i*70)+' 450 Q'+(330+i*15)+' '+(190+i*35)+' 740 '+(90+i*44),fill:'none',stroke:'#A4BED5','stroke-width':1.4,'stroke-opacity':'.37','stroke-dasharray':'5 8'}));
  }
  for(const t of [
    ['13.2°',133,437],['13.4°',337,437],['13.6°',543,437],
    ['52.6°',13,95],['52.5°',13,209],['52.4°',13,322]
  ]){
    const label=add(host,ssvg('text',{x:t[1],y:t[2],fill:'#8A9DA8','font-size':11,'font-family':'sans-serif'}));
    label.textContent=t[0];
  }
  const points=add(host,ssvg('g',{class:'map-points'}));
  for(const r of state.filtered){
    if(!Number.isFinite(r.lon)||!Number.isFinite(r.lat))continue;
    const active=state.selected?.id===r.id,x=mapX(r.lon),y=mapY(r.lat);
    if(active){
      add(points,ssvg('circle',{cx:x,cy:y,r:22,fill:'#E77C66','fill-opacity':'.12'}));
      add(points,ssvg('circle',{cx:x,cy:y,r:15,fill:'none',stroke:'#EC957F','stroke-width':1.8,'stroke-dasharray':'3 4'}));
    }
    add(points,ssvg('circle',{cx:x,cy:y,r:active?7.3:4.3,fill:active?'#F0846D':'#454CBD',stroke:'#FFFDF9','stroke-width':active?2:1.4,'pointer-events':'none'}));
    // Larger invisible interactive targets retain precise dots but improve touch usability.
    const c=add(points,ssvg('circle',{cx:x,cy:y,r:14,fill:'transparent',stroke:'none',role:'button',tabindex:'0','aria-label':r.n+', '+r.d,class:'map-dot'}));
    const title=add(c,ssvg('title'));title.textContent=r.n+' · '+r.d;
    c.addEventListener('click',()=>selectPlace(r));
    c.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectPlace(r);}});
  }
  $('#map-count').textContent=state.filtered.length+' Punkte · Ausschnitt';
}
function updateSpotlight(){
 const host=wipe($('#spotlight'));const r=state.selected;
 if(!r){add(host,node('h3','Wähle einen Brunnen.'));add(host,node('p','Jeder Punkt erzählt einen Zusammenhang.'));return;}
 const bar=add(host,node('div',undefined,'spotlight-top'));
 add(bar,node('span','NR. '+String(r.id).padStart(3,'0')+' / '+r.d.toUpperCase(),'spotlight-tag'));
 add(bar,node('span','↗','spotlight-icon'));
 add(host,node('h3',r.n));
 add(host,node('p',r.r?'WFS meldet: '+r.r:'Kein Einschränkungsvermerk im Datenauszug · kein Live-Status'));
 const btn=add(host,node('button','Beziehungen entdecken →'));btn.type='button';btn.addEventListener('click',()=>go('graph'));
}
function selectPlace(rec,{keepScroll=true}={}){
 state.selected=rec;
 $$('.place').forEach(b=>b.classList.toggle('active',Number(b.dataset.id)===rec.id));
 renderMap();updateSpotlight();renderLearningTriple();
 if(state.view==='graph')renderGraph();
 if(!keepScroll)window.scrollTo({top:0});
}
function renderPlaces(){
 const query=$('#search').value.trim().toLocaleLowerCase('de-DE'),district=$('#district').value;
 state.filtered=state.records.filter(r=>(!district||r.d===district)&&(!query||[r.n,r.d,r.t,String(r.id)].join(' ').toLocaleLowerCase('de-DE').includes(query)));
 $('#result-count').textContent=state.filtered.length+' Orte';
 if(!state.filtered.some(r=>r.id===state.selected?.id))state.selected=state.filtered[0]??null;
 const list=wipe($('#place-list'));const slice=state.filtered.slice(0,state.shown);
 if(!slice.length)add(list,node('div','Keine Treffer. Probiere einen anderen Suchbegriff.','loading'));
 for(const r of slice){
   const b=add(list,node('button',undefined,'place'+(state.selected?.id===r.id?' active':'')));
   b.type='button';b.dataset.id=String(r.id);b.setAttribute('aria-pressed',String(state.selected?.id===r.id));
   add(b,node('span',String(r.id).padStart(3,'0'),'number'));
   const text=add(b,node('span',undefined,'place-text'));
   add(text,node('strong',r.n));add(text,node('small',r.d));
   add(b,node('span','↗','arrow'));b.addEventListener('click',()=>selectPlace(r));
 }
 $('#load-more').hidden=state.shown>=state.filtered.length||state.filtered.length===0;
 renderMap();updateSpotlight();
}
$('#search').addEventListener('input',()=>{state.shown=8;renderPlaces();});
$('#district').addEventListener('change',()=>{state.shown=8;renderPlaces();});
$('#load-more').addEventListener('click',()=>{state.shown+=8;renderPlaces();toast('Mehr Orte entdeckt ✳');});
const explanations={
 district:r=>'Dieser Brunnen ist dem Bezirk '+r.d+' zugeordnet. ct:inDistrict verbindet den Ort mit einer Bezirk-Ressource.',
 source:r=>'Die Beziehung prov:wasDerivedFrom verweist auf den offiziellen, eingefrorenen Berliner WFS-Auszug. So bleibt seine Herkunft nachvollziehbar.',
 type:r=>'Der WFS-Datensatz beschreibt den Brunnen als „'+(r.t||'nicht spezifiziert')+'“. Die Eigenschaft ct:fountainType verbindet eine Ressource mit diesem Typ.',
 coords:r=>'Diese beiden Zahlen sind geographische Koordinaten (WGS84), keine Aussage darüber, ob der Brunnen heute in Betrieb ist.',
 fountain:r=>'Der Brunnen ist das Subjekt unserer Aussagen: Name, Bezirk, Typ, Position und Herkunft werden explizit mit ihm verknüpft.'
};
function renderGraph(){
 const r=state.selected??state.records[0],host=wipe($('#graph-svg'));
 if(!r)return;
 $('#inspect-name').textContent=r.n;$('#inspect-location').textContent='Berlin · '+r.d+' · WFS Nr. '+r.id;
 $('#edge-explanation').textContent=explanations[state.graphFocus]?.(r)??explanations.district(r);
 const points=[
  {id:'fountain',x:385,y:250,r:54,label:'ORT',sub:'fountain:f'+r.id,color:'#484FC0'},
  {id:'district',x:130,y:115,r:40,label:'BEZIRK',sub:r.d.length>19?r.d.slice(0,17)+'…':r.d,color:'#EC987C'},
  {id:'source',x:644,y:117,r:40,label:'QUELLE',sub:'WFS 2026',color:'#7C95BA'},
  {id:'type',x:140,y:392,r:39,label:'TYP',sub:r.t||'Brunnen',color:'#8CAD94'},
  {id:'coords',x:645,y:391,r:39,label:'KOORD.',sub:'WGS84',color:'#DAB268'}];
 const idmap=Object.fromEntries(points.map(p=>[p.id,p]));
 const edges=[['fountain','district','ct:inDistrict'],['fountain','source','prov:wasDerivedFrom'],['fountain','type','ct:fountainType'],['fountain','coords','geo:lat / geo:long']];
 const center=add(host,ssvg('g'));
 for(let x=17;x<780;x+=37)add(center,ssvg('line',{x1:x,y1:0,x2:x,y2:500,stroke:'#BBC1BA','stroke-opacity':'.19','stroke-width':1}));
 for(let y=19;y<500;y+=37)add(center,ssvg('line',{x1:0,y1:y,x2:780,y2:y,stroke:'#BBC1BA','stroke-opacity':'.19','stroke-width':1}));
 for(const [a,b,label] of edges){
   const A=idmap[a],B=idmap[b];
   const active=state.graphFocus===b;
   add(host,ssvg('line',{x1:A.x,y1:A.y,x2:B.x,y2:B.y,stroke:active?'#4654C5':'#B7B8B0','stroke-width':active?3:1.5,'stroke-dasharray':active?'0':'5 7'}));
   const mid=add(host,ssvg('text',{x:(A.x+B.x)/2,y:(A.y+B.y)/2-13,'text-anchor':'middle',fill:active?'#454DB0':'#8F9598','font-size':11,'font-weight':active?800:500}));
   mid.textContent=label;
 }
 for(const p of points){
   const focus=state.graphFocus===p.id,grp=add(host,ssvg('g',{role:'button',tabindex:'0','aria-label':'Verbindung '+p.label+' erklären',style:'cursor:pointer'}));
   if(focus)add(grp,ssvg('circle',{cx:p.x,cy:p.y,r:p.r+13,fill:p.color,'fill-opacity':'.12'}));
   add(grp,ssvg('circle',{cx:p.x,cy:p.y,r:p.r,fill:p.id==='fountain'?'#FDFBF6':'#FFFDF8',stroke:p.color,'stroke-width':focus?4:2.4}));
   add(grp,ssvg('circle',{cx:p.x,cy:p.y-4,r:p.id==='fountain'?8:5,fill:p.color}));
   const t=add(grp,ssvg('text',{x:p.x,y:p.y+16,'text-anchor':'middle',fill:'#35475B','font-size':p.id==='fountain'?12:10,'font-family':'sans-serif','font-weight':'750','letter-spacing':1}));t.textContent=p.label;
   const t2=add(grp,ssvg('text',{x:p.x,y:p.y+p.r+21,'text-anchor':'middle',fill:'#74838C','font-size':11,'font-family':'sans-serif'}));t2.textContent=p.sub;
   grp.addEventListener('click',()=>{state.graphFocus=p.id;renderGraph();});
   grp.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();state.graphFocus=p.id;renderGraph();}});
 }
 const triples=[
  ['rdf:type','ct:DrinkingFountain'],['rdfs:label',r.n],
  ['ct:inDistrict','district:'+slug(r.d)],
  ['ct:fountainType',r.t||'—'],
  ['geo:lat',Number(r.lat).toFixed(6)],
  ['geo:long',Number(r.lon).toFixed(6)],
  ['prov:wasDerivedFrom','dataset:BerlinFountainsWFS20261009']
 ];
 if(r.y!==null&&r.y!==undefined)triples.push(['ct:yearBuilt',String(r.y)]);
 if(r.r)triples.push(['ct:reportedRestriction',r.r]);
 const target=wipe($('#triple-list'));
 for(const [k,v] of triples){
   const row=add(target,node('div',undefined,'triple-row'));
   add(row,node('b',k));add(row,node('span',v));
 }
}
const prefixes='PREFIX ct: <https://citythread.example/ontology#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n\n';
const questions=[
 {title:'Wo steht das Wasser?',sub:'Orte und Bezirke entdecken',heading:'Jeder Ort gehört irgendwohin.',
  summary:'Die ersten 12 verzeichneten Standorte unseres WFS-Ausschnitts – jeder mit seinem Bezirk. Ein <strong>Beispiel für die Relation</strong> ct:inDistrict.',
  code:'SELECT ?name ?district WHERE {\n  ?fountain a ct:DrinkingFountain ;\n            rdfs:label ?name ;\n            ct:inDistrict ?district .\n}\nLIMIT 12',
  run:rs=>({columns:['Brunnen','Bezirk'],rows:rs.slice(0,12).map(r=>[r.n,r.d])})},
 {title:'Wo wurden Einschränkungen gemeldet?',sub:'Nicht gleichbedeutend mit „heute geschlossen“',heading:'Manche Orte haben Hinweise.',
  summary:'Einige WFS-Einträge enthalten <strong>ausdrücklich gemeldete Einschränkungen</strong>. Das ist eine Aussage aus dem Datenstand vom 9.10.2026, keine Live-Prüfung.',
  code:'SELECT ?name ?restriction WHERE {\n  ?fountain a ct:DrinkingFountain ;\n            rdfs:label ?name ;\n            ct:reportedRestriction ?restriction .\n}',
  run:rs=>({columns:['Brunnen','Gemeldete Einschränkung'],rows:rs.filter(r=>r.r).map(r=>[r.n,r.r])})},
 {title:'Wie alt sind die Brunnen?',sub:'Nach bekannten Baujahren sortieren',heading:'Die Geschichte steckt in den Daten.',
  summary:'Ein Blick auf <strong>dokumentierte Baujahre</strong>, aufsteigend sortiert. Fehlende Baujahre bleiben bewusst unberücksichtigt.',
  code:'SELECT ?name ?year WHERE {\n  ?fountain a ct:DrinkingFountain ;\n            rdfs:label ?name ;\n            ct:yearBuilt ?year .\n}\nORDER BY ASC(?year)\nLIMIT 15',
  run:rs=>({columns:['Brunnen','Baujahr'],rows:rs.filter(r=>r.y!==null&&Number.isFinite(Number(r.y))).slice().sort((a,b)=>Number(a.y)-Number(b.y)).slice(0,15).map(r=>[r.n,String(r.y)])})},
 {title:'Welche Bezirke tauchen am häufigsten auf?',sub:'Gruppieren statt raten',heading:'Der Ausschnitt in Bezirken.',
  summary:'Diese Zählung betrifft <strong>nur unsere 120 WFS-Einträge</strong>. Sie ist kein Ranking der tatsächlichen Versorgung der Berliner Bezirke.',
  code:'SELECT ?district (COUNT(?fountain) AS ?count) WHERE {\n  ?fountain a ct:DrinkingFountain ;\n            ct:inDistrict ?district .\n}\nGROUP BY ?district\nORDER BY DESC(?count)',
  run:rs=>{const m=new Map();rs.forEach(r=>m.set(r.d,(m.get(r.d)??0)+1));return{columns:['Bezirk','Einträge im Ausschnitt'],rows:[...m].sort((a,b)=>b[1]-a[1]).map(([d,n])=>[d,String(n)])};}}
];
function renderAnswers(){
 const host=wipe($('#question-choices'));
 questions.forEach((q,i)=>{
  const b=add(host,node('button',undefined,'question-option'+(i===state.question?' active':'')));b.type='button';b.setAttribute('aria-pressed',String(i===state.question));
  add(b,node('span',String(i+1).padStart(2,'0'),'q-index'));
  const txt=add(b,node('span'));add(txt,node('strong',q.title));add(txt,node('small',q.sub));
  b.addEventListener('click',()=>{state.question=i;renderAnswers();});
 });
 const q=questions[state.question];$('#answer-title').textContent=q.heading;
 $('#sparql-code').textContent=prefixes+q.code;
 const summary=$('#answer-summary');wipe(summary);
 // Static, editor-controlled HTML only; never interpolate WFS values into HTML.
 summary.innerHTML=q.summary;
 const area=wipe($('#answer-table'));
 if(!state.loaded){add(area,node('p','Die Daten werden geladen …','loading'));return;}
 const {columns,rows}=q.run(state.records);
 $('#answer-pill').textContent=rows.length+' ERGEBNISSE';
 const table=add(area,node('table'));const header=add(add(table,node('thead')),node('tr'));
 columns.forEach(h=>add(header,node('th',h)));
 const tbody=add(table,node('tbody'));
 if(rows.length===0)add(area,node('p','Im Auszug gibt es zu dieser Frage keine Treffer.','loading'));
 for(const row of rows){
  const tr=add(tbody,node('tr'));
  row.forEach(v=>add(tr,node('td',v)));
 }
}
$('#toggle-code').addEventListener('click',()=>{
 const el=$('#code-panel'),nowOpen=el.hidden;
 el.hidden=!nowOpen;$('#toggle-code').setAttribute('aria-expanded',String(nowOpen));
 $('#toggle-code').innerHTML=nowOpen?'<span aria-hidden="true">{ }</span> SPARQL ausblenden <span class="chev">↑</span>':'<span aria-hidden="true">{ }</span> SPARQL ansehen <span class="chev">↓</span>';
});
$('#copy-code').addEventListener('click',async()=>{
 try{await navigator.clipboard.writeText($('#sparql-code').textContent);toast('SPARQL kopiert ✓');}
 catch{toast('Markiere den Code zum Kopieren.');}
});
$$('[data-scenario]').forEach(b=>b.addEventListener('click',()=>{
 state.scenario=b.dataset.scenario;$$('[data-scenario]').forEach(other=>other.classList.toggle('active',other===b));
 $('#validation-output').replaceChildren(node('span','Bereit für den Test.','terminal-placeholder'));
}));
function runValidation(){
 const target=wipe($('#validation-output'));
 if(!state.loaded){
   add(target,node('strong','Datensatz noch nicht geladen','fail'));
   add(target,node('p','Ohne Daten kann das System nichts verifizieren.'));return;
 }
 const sampled=state.records.slice(0,10).map(r=>({...r}));
 const meta={...state.meta};
 if(state.scenario==='source')meta.source='';
 if(state.scenario==='coords')sampled[0].lon=999;
 const problems=[];
 if(!meta.source||!meta.source.startsWith('https://'))problems.push('Provenienz fehlt: keine gültige Quell-URL.');
 for(const r of sampled){
   if(!r.n||!r.d)problems.push('Name oder Bezirk fehlt bei Datensatz '+r.id+'.');
   if(!Number.isFinite(r.lat)||r.lat < -90||r.lat>90||!Number.isFinite(r.lon)||r.lon< -180||r.lon>180)
      problems.push('Koordinaten ausserhalb von WGS84 bei Datensatz '+r.id+'.');
 }
 add(target,node('small','> CHECK source, labels, districts, lat/lon; sample_size=10'));
 if(problems.length===0){
   add(target,node('strong','✓ PASS — keine Regelverletzung gefunden','ok'));
   add(target,node('p','Zehn geprüfte Datensätze enthalten Quellnachweis, Namen, Bezirke und Koordinaten im gültigen Wertebereich.'));
   add(target,node('p','Wichtig: Gültige Zahlen bedeuten nicht automatisch richtige Geodaten oder aktuelle Betriebsbereitschaft.'));
 }else{
   add(target,node('strong','✕ FAIL — '+problems.length+' Problem erkannt','fail'));
   problems.forEach(x=>add(target,node('p','→ '+x)));
   add(target,node('p','Die Prüfung verhindert, dass dieser fehlerhafte Testdatensatz als vollständig gekennzeichnet wird.'));
 }
 add(target,node('small','Browser-Prüfregeln · kein ausgeführtes SHACL.'));
}
$('#run-validation').addEventListener('click',runValidation);
function renderLearningTriple(){
 const r=state.selected??state.records[0];if(!r)return;
 const holder=wipe($('#real-triple'));
 const items=['fountain:f'+r.id,'→','ct:inDistrict','→','district:'+slug(r.d)];
 for(const val of items){
   add(holder,node(val==='→'?'span':'code',val));
 }
}
$$('[data-choice]').forEach(b=>b.addEventListener('click',()=>{
 const ok=b.dataset.choice==='district';
 $$('[data-choice]').forEach(x=>x.classList.remove('correct','incorrect'));
 b.classList.add(ok?'correct':'incorrect');
 $('#quiz-feedback').textContent=ok?
  '✓ Genau! ct:inDistrict verbindet den Brunnen (Subjekt) mit seinem Bezirk (Objekt). Das ist bereits ein echtes RDF-Prädikat.':
  b.dataset.choice==='source'?
    'Fast! prov:wasDerivedFrom sagt, aus welcher Quelle eine Information stammt. „Liegt in“ wäre ct:inDistrict.':
    'Nicht ganz – ein Hitzeindex beschreibt etwas anderes. Für den Bezirk passt ct:inDistrict.';
}));
function loadFailure(msg){
 state.loaded=false;
 $('#metric-places').textContent='—';$('#metric-districts').textContent='—';
 wipe($('#place-list'));add($('#place-list'),node('p','Der Datenauszug ist gerade nicht erreichbar. Bitte die Seite neu laden.','loading'));
 wipe($('#spotlight'));add($('#spotlight'),node('h3','Daten fehlen.'));add($('#spotlight'),node('p','Keine erfundenen Orte: Wir zeigen erst dann Ergebnisse, wenn der WFS-Auszug geladen ist.'));
 $('#result-count').textContent='0 Orte';
 $('#map-count').textContent='Keine Daten';
 renderAnswers();
 console.error('City Thread data load failed:',msg);
}
async function init(){
 const routed=location.hash.replace('#','');
 go(validViews.has(routed)?routed:'discover',{push:false,scroll:false});
 renderAnswers();
 try{
   const response=await fetch('./fountains.json',{cache:'no-store'});
   if(!response.ok)throw Error('HTTP '+response.status);
   const data=await response.json();
   if(!data.meta||!Array.isArray(data.records))throw Error('Malformed WFS snapshot');
   state.meta=data.meta;
   state.records=data.records.filter(r=>Number.isFinite(r.lon)&&Number.isFinite(r.lat)&&r.lon>=-180&&r.lon<=180&&r.lat>=-90&&r.lat<=90&&r.n&&r.d);
   if(state.records.length===0)throw Error('No valid WFS records');
   state.loaded=true;
   $('#metric-places').textContent=fmt(state.records.length);
   const districts=[...new Set(state.records.map(r=>r.d))].sort((a,b)=>a.localeCompare(b,'de'));
   $('#metric-districts').textContent=fmt(districts.length);
   const select=$('#district');
   districts.forEach(d=>{const opt=node('option',d);opt.value=d;add(select,opt);});
   state.selected=state.records[0];
   renderPlaces();renderGraph();renderAnswers();renderLearningTriple();
   // v0.3 uses no AI, live fountain-status claims or heat-risk ranking.
 }catch(err){loadFailure(err);}
}
init();
})();
