/* CITY THREAD v0.2 · Independent semantic city learning experiment
 * Verified public fountain WFS snapshot; this shared edition runs local query evaluators.
 * Full SPARQL and SHACL are available in the Python reference edition.
 */
(() => {
  'use strict';
  const $ = (selector, scope=document) => scope.querySelector(selector);
  const $$ = (selector, scope=document) => [...scope.querySelectorAll(selector)];
  const svgNS = 'http://www.w3.org/2000/svg';
  const esc = (s) => String(s ?? '');
  const el = (tag, text, className) => {
    const node=document.createElement(tag); if(text!==undefined)node.textContent=esc(text);
    if(className)node.className=className;return node;
  };
  const svg = (tag, attrs={}) => {
    const n=document.createElementNS(svgNS,tag);
    for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));
    return n;
  };
  const put=(parent,node)=>{parent.appendChild(node);return node;};
  const clear=(parent)=>parent.replaceChildren();
  const S={meta:null,records:[],filtered:[],selected:null,tab:'atlas',query:0,scenario:'clean'};
  const titlecase={atlas:'Atlas',graph:'Knowledge graph',query:'Query lab',trust:'Trust & evidence',learn:'Learn by doing'};
  function nav(name){
    if(!titlecase[name])return;
    S.tab=name;
    $$('.page').forEach(p=>p.classList.toggle('active',p.id==='page-'+name));
    $$('[data-nav]').forEach(b=>b.classList.toggle('active',b.dataset.nav===name));
    $('#crumb').textContent=titlecase[name];
    window.scrollTo({top:0,behavior:'smooth'});
    if(name==='graph')drawGraph();
    if(name==='query')renderQuery();
  }
  $$('[data-nav]').forEach(b=>b.addEventListener('click',()=>nav(b.dataset.nav)));
  $$('[data-goto]').forEach(b=>b.addEventListener('click',()=>{
    nav('atlas');requestAnimationFrame(()=>document.getElementById(b.dataset.goto)?.scrollIntoView({behavior:'smooth',block:'start'}));
  }));
  $('#share').addEventListener('click',async()=>{
    const url=location.href.split('#')[0];
    let copied=false;
    try{await navigator.clipboard.writeText(url);copied=true;}catch(e){}
    $('#share').textContent=copied?'Link copied ✓':'Open share link ↗';
    if(!copied)window.prompt('Copy this share link',url);
    window.setTimeout(()=>{$('#share').textContent='Share experiment ↗';},3200);
  });
  function selectPlace(rec,move=false){
    S.selected=rec;
    $$('.place').forEach(b=>b.classList.toggle('active',Number(b.dataset.id)===rec.id));
    drawMap();drawGraph();
    const box=$('#map-inspector');clear(box);
    put(box,el('div','SELECTED / WFS '+rec.id,'eyebrow'));
    put(box,el('strong',rec.n));
    const sub=rec.d+' · '+(rec.r?'Restriction in WFS: '+rec.r:'No restriction reported in extract (not live status)');
    put(box,el('span',sub));
    if(move && S.tab!=='atlas')nav('atlas');
  }
  function buildList(){
    const district=$('#district').value;
    const search=$('#search').value.trim().toLocaleLowerCase('de-DE');
    S.filtered=S.records.filter(r=>(!district||r.d===district)&&(!search||[r.n,r.d,r.t,String(r.id)].join(' ').toLocaleLowerCase('de-DE').includes(search)));
    $('#results-count').textContent=S.filtered.length+' LOCATIONS';
    const list=$('#place-list');clear(list);
    if(!S.filtered.length)put(list,el('p','No locations match this filter.','muted'));
    for(const r of S.filtered){
      const b=el('button',undefined,'place'+(S.selected?.id===r.id?' active':''));b.type='button';b.dataset.id=String(r.id);
      put(b,el('span',String(r.id).padStart(3,'0'),'place-index'));
      const box=el('span');put(box,el('strong',r.n));put(box,el('small',r.d));put(b,box);
      put(b,el('span','↗','place-arrow'));b.addEventListener('click',()=>selectPlace(r));put(list,b);
    }
    drawMap();
  }
  $('#district').addEventListener('change',buildList);
  $('#search').addEventListener('input',buildList);
  const mapW=720,mapH=490,west=13.11,east=13.76,south=52.35,north=52.69;
  const xp=lon=>35+(lon-west)/(east-west)*(mapW-70);
  const yp=lat=>mapH-29-(lat-south)/(north-south)*(mapH-56);
  function drawMap(){
    const host=$('#atlas-svg');clear(host);
    const defs=put(host,svg('defs'));
    const radial=put(defs,svg('radialGradient',{id:'watermap-glow'}));
    put(radial,svg('stop',{offset:'0%', 'stop-color':'#2b4a3b', 'stop-opacity':'.66'}));
    put(radial,svg('stop',{offset:'100%', 'stop-color':'#0e2420', 'stop-opacity':'.03'}));
    put(host,svg('rect',{x:0,y:0,width:720,height:490,fill:'url(#watermap-glow)'}));
    for(let x=62;x<mapW;x+=48)put(host,svg('line',{x1:x,x2:x,y1:0,y2:mapH,stroke:'#91b69b','stroke-opacity':'.09','stroke-width':'1'}));
    for(let y=40;y<mapH;y+=48)put(host,svg('line',{x1:0,x2:mapW,y1:y,y2:y,stroke:'#91b69b','stroke-opacity':'.09','stroke-width':'1'}));
    const city=put(host,svg('g',{'stroke':'#557d6b','stroke-opacity':'.22',fill:'none','stroke-width':1.5}));
    [120,190,270].forEach(r=>put(city,svg('ellipse',{cx:358,cy:246,rx:r,ry:r*.66,'stroke-dasharray':'2 9'})));
    const labels=put(host,svg('g',{fill:'#668878','font-size':10,'letter-spacing':2}));
    [['52.60 N',20,90],['52.50 N',20,225],['52.40 N',20,365],['13.20 E',135,478],['13.50 E',456,478]].forEach(v=>{
      const t=put(labels,svg('text',{x:v[1],y:v[2]}));t.textContent=v[0];
    });
    const collection=put(host,svg('g'));
    for(const r of S.filtered){
      if(!Number.isFinite(r.lon)||!Number.isFinite(r.lat))continue;
      const selected=S.selected?.id===r.id;
      const dot=put(collection,svg('circle',{cx:xp(r.lon),cy:yp(r.lat),r:selected?9:4.5,fill:selected?'#e1bd90':'#9bccac',stroke:selected?'#f7e8c6':'#233e2f','stroke-width':selected?2.6:1.4,'fill-opacity':selected?1:.83,tabindex:0,role:'button','aria-label':r.n+', '+r.d,class:'map-dot'}));
      const t=put(dot,svg('title'));t.textContent=r.n+', '+r.d;
      dot.addEventListener('click',()=>selectPlace(r));
      dot.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectPlace(r);}});
      if(selected)put(host,svg('circle',{cx:xp(r.lon),cy:yp(r.lat),r:16,fill:'none',stroke:'#e2bc8a','stroke-opacity':'.62','stroke-width':1,'stroke-dasharray':'2 4','pointer-events':'none'}));
    }
    $('#map-count').textContent=S.filtered.length+' POINTS SHOWN';
  }
  const predicates=[
    ['rdf:type','ct:DrinkingFountain'],
    ['rdfs:label',null],
    ['ct:inDistrict',null],
    ['ct:fountainType',null],
    ['geo:lat',null],
    ['geo:long',null],
    ['prov:wasDerivedFrom','dataset:BerlinFountains2026']
  ];
  function drawGraph(){
    const host=$('#graph-svg');clear(host);
    const rec=S.selected??S.records[0];if(!rec)return;
    $('#inspect-title').textContent=rec.n;
    $('#inspect-description').textContent='WFS feature '+rec.id+' · '+rec.d+'. Follow the explicit relationships and their source.';
    const triples=$('#triple-list');clear(triples);
    const entries=[
      ['rdf:type','ct:DrinkingFountain'],
      ['rdfs:label',rec.n],
      ['ct:inDistrict','district:'+rec.d.replaceAll(' ','-')],
      ['ct:fountainType',rec.t],
      ['geo:lat',rec.lat.toFixed(5)],
      ['geo:long',rec.lon.toFixed(5)],
      ['prov:wasDerivedFrom','dataset:BerlinFountains2026']
    ];
    if(rec.r)entries.push(['ct:reportedRestriction',rec.r]);
    for(const [p,v] of entries){const row=put(triples,el('div',undefined,'triple'));put(row,el('b',p));put(row,el('span',v));}
    for(let x=40;x<660;x+=48)put(host,svg('line',{x1:x,x2:x,y1:0,y2:420,stroke:'#729580','stroke-opacity':'.075'}));
    for(let y=22;y<420;y+=48)put(host,svg('line',{x1:0,x2:700,y1:y,y2:y,stroke:'#729580','stroke-opacity':'.075'}));
    const nodes=[
      {x:346,y:203,r:45,label:'FOUNTAIN',fill:'#d5e9bb'},
      {x:130,y:104,r:31,label:'DISTRICT',fill:'#c2a988'},
      {x:565,y:100,r:31,label:'DATASET',fill:'#8fc5bc'},
      {x:128,y:324,r:29,label:'TYPE',fill:'#9cbd9c'},
      {x:573,y:330,r:29,label:'COORDS',fill:'#a8bbd3'}
    ];
    const edges=[[0,1,'inDistrict'],[0,2,'derivedFrom'],[0,3,'fountainType'],[0,4,'geo:location']];
    for(const [a,b,label] of edges){
      const A=nodes[a],B=nodes[b];put(host,svg('line',{x1:A.x,y1:A.y,x2:B.x,y2:B.y,stroke:'#91ae98','stroke-opacity':'.52','stroke-width':1.5}));
      const tx=put(host,svg('text',{x:(A.x+B.x)/2,y:(A.y+B.y)/2-9,'text-anchor':'middle',fill:'#a5b9a9','font-size':10}));tx.textContent=label;
    }
    for(const n of nodes){
      put(host,svg('circle',{cx:n.x,cy:n.y,r:n.r,fill:'#1d362c',stroke:n.fill,'stroke-width':1.6}));
      put(host,svg('circle',{cx:n.x,cy:n.y,r:n.r*.18,fill:n.fill}));
      const t=put(host,svg('text',{x:n.x,y:n.y+n.r+19,'text-anchor':'middle',fill:'#e1eadd','font-size':11,'letter-spacing':1.3}));t.textContent=n.label;
    }
    const ft=put(host,svg('text',{x:346,y:283,'text-anchor':'middle',fill:'#b4cbb6','font-size':11}));ft.textContent='feature:'+rec.id;
  }
  const prefixes='PREFIX ct: <https://citythread.example/ontology#>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\nPREFIX prov: <http://www.w3.org/ns/prov#>\n\n';
  const queries=[
   {title:'Where is the water?',desc:'Fountains and their district',name:'Water by district',
    code:'SELECT ?name ?district WHERE {\n  ?fountain a ct:DrinkingFountain ;\n    rdfs:label ?name ;\n    ct:inDistrict ?district .\n}\nLIMIT 12',
    run:rs=>({heads:['Fountain','District'],rows:rs.slice(0,12).map(r=>[r.n,r.d])})},
   {title:'What might be unavailable?',desc:'Explicitly reported restrictions',name:'Reported restrictions',
    code:'SELECT ?name ?restriction WHERE {\n  ?fountain a ct:DrinkingFountain ;\n    rdfs:label ?name ;\n    ct:reportedRestriction ?restriction .\n}',
    run:rs=>({heads:['Fountain','Reported restriction'],rows:rs.filter(r=>r.r).map(r=>[r.n,r.r])})},
   {title:'How old is the infrastructure?',desc:'Known build years · ascending',name:'Oldest known',
    code:'SELECT ?name ?year WHERE {\n  ?fountain a ct:DrinkingFountain ;\n    rdfs:label ?name ;\n    ct:yearBuilt ?year .\n}\nORDER BY ASC(?year)\nLIMIT 15',
    run:rs=>({heads:['Fountain','Year built'],rows:rs.filter(r=>Number.isFinite(Number(r.y))).sort((a,b)=>Number(a.y)-Number(b.y)).slice(0,15).map(r=>[r.n,String(r.y)])})},
   {title:'Which district appears most?',desc:'Group by district · extract only',name:'Count by district',
    code:'SELECT ?district (COUNT(?fountain) AS ?count) WHERE {\n  ?fountain a ct:DrinkingFountain ;\n    ct:inDistrict ?district .\n}\nGROUP BY ?district\nORDER BY DESC(?count)',
    run:rs=>{const m=new Map();rs.forEach(r=>m.set(r.d,(m.get(r.d)||0)+1));return{heads:['District','Count in snapshot'],rows:[...m.entries()].sort((a,b)=>b[1]-a[1]).map(([d,n])=>[d,String(n)])};}}
  ];
  function renderQuery(){
    const panel=$('#presets');clear(panel);
    queries.forEach((q,i)=>{
      const b=el('button',undefined,'preset'+(S.query===i?' active':''));b.type='button';
      put(b,el('span','QUESTION 0'+(i+1),'id'));put(b,el('strong',q.title));put(b,el('small',q.desc));
      b.addEventListener('click',()=>{S.query=i;renderQuery();});
      put(panel,b);
    });
    $('#sparql').textContent=prefixes+queries[S.query].code;
    $('#query-count').textContent='PRESS RUN';
    clear($('#query-results'));put($('#query-results'),el('p','The query pattern is ready. Press Run to inspect results.','muted')).style.padding='15px 23px';
  }
  $('#run-query').addEventListener('click',()=>{
    const q=queries[S.query],result=q.run(S.records);
    $('#query-count').textContent=result.rows.length+' ROWS';
    const area=$('#query-results');clear(area);
    const table=put(area,el('table'));const tr=put(put(table,el('thead')),el('tr'));
    for(const h of result.heads)put(tr,el('th',h));
    const body=put(table,el('tbody'));
    if(!result.rows.length){put(area,el('p','No results found in the 120-record extract.','muted')).style.padding='15px';return;}
    for(const row of result.rows){const t=put(body,el('tr'));for(const value of row)put(t,el('td',value));}
  });
  $('#copy-sparql').addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText($('#sparql').textContent);$('#copy-sparql').textContent='Copied ✓';}
    catch(e){$('#copy-sparql').textContent='Select and copy';}
    window.setTimeout(()=>{$('#copy-sparql').textContent='Copy query ↗';},2000);
  });
  $$('[data-scenario]').forEach(b=>b.addEventListener('click',()=>{
    S.scenario=b.dataset.scenario;$$('[data-scenario]').forEach(s=>s.classList.toggle('selected',s===b));
  }));
  function validate(){
    const testData=S.records.slice(0,10).map(r=>({...r}));
    const m={...S.meta};
    if(S.scenario==='missing')m.source='';
    if(S.scenario==='invalid')testData[0].lon=999;
    const issues=[];
    if(!m.source||!/^https:\/\//.test(m.source))issues.push('Missing required provenance: source URL');
    for(const r of testData){
      if(!r.n||!r.d)issues.push('Missing name or district on feature '+r.id);
      if(!Number.isFinite(r.lon)||r.lon< -180||r.lon>180||!Number.isFinite(r.lat)||r.lat< -90||r.lat>90)issues.push('Coordinate out of WGS84 range on feature '+r.id);
    }
    const box=$('#validation-output');clear(box);
    if(!issues.length){put(box,el('strong','✓ PASS · Sample checks complete')).style.color='#c7edaf';put(box,el('div','10 sample records have a source, name, district and coordinate values in range. Valid coordinates do not prove positional accuracy.'));}
    else{put(box,el('strong','✕ FAIL · '+issues.length+' issue(s) found')).style.color='#ecc5a6';issues.forEach(s=>put(box,el('div','• '+s)));}
  }
  $('#validate').addEventListener('click',validate);
  $$('[data-choice]').forEach(button=>button.addEventListener('click',()=>{
    $$('[data-choice]').forEach(b=>b.classList.remove('right','wrong'));
    const ok=button.dataset.choice==='district';
    button.classList.add(ok?'right':'wrong');
    $('#quiz-feedback').textContent=ok?'✓ Exactly! ct:inDistrict connects a fountain (subject) to a district (object). You have just read your first RDF predicate.':'Not quite. That predicate describes something else. Try ct:inDistrict: in = „in einem Bezirk gelegen“.';
  }));
  async function boot(){
    try{
      const response=await fetch('./fountains.json',{cache:'no-store'});
      if(!response.ok)throw Error('HTTP '+response.status);
      const data=await response.json();S.meta=data.meta;
      S.records=(data.records??[]).filter(r=>Number.isFinite(r.lat)&&Number.isFinite(r.lon)&&r.n&&r.d);
      if(!S.records.length)throw Error('No valid records');
      $('#m-locations').textContent=S.records.length;
      const districts=[...new Set(S.records.map(r=>r.d))].sort((a,b)=>a.localeCompare(b,'de'));
      $('#m-districts').textContent=districts.length;
      $('#record-sample').textContent=S.records.length;$('#record-total').textContent=S.meta.total??'unknown';
      districts.forEach(d=>{const opt=el('option',d);opt.value=d;put($('#district'),opt);});
      S.selected=S.records.find(r=>r.id===24)??S.records[0];
      buildList();selectPlace(S.selected);renderQuery();validate();
    }catch(err){
      console.error('Data load error',err);
      clear($('#place-list'));put($('#place-list'),el('p','Data could not be loaded. Please reopen the public preview URL, not a local file:// copy.','muted'));
      $('#m-locations').textContent='—';$('#m-districts').textContent='—';
      $('#map-count').textContent='SOURCE UNAVAILABLE';
      const box=$('#validation-output');clear(box);put(box,el('span','Source unavailable. No results can be verified.'));
    }
  }
  boot();
})();