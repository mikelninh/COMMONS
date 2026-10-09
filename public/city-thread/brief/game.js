/* CITY THREAD v0.7 — THE BRIEF
 * A three-candidate narrative DECISION GAME, not an operational city-planning tool.
 * All quantities are recomputed from authoritative WFS-snapshot geometries in the
 * user's browser; reference candidate values are verified at boot.
 * The one available field-review slot is FICTIONAL; no real budget or permit is claimed.
 * No authentication, cookies, external analytics, persistence or submissions.
 */
(()=>{
'use strict';
const $=(q,root=document)=>root.querySelector(q);
const $$=(q,root=document)=>[...root.querySelectorAll(q)];
const E=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=String(text);if(cls)x.className=cls;return x};
const SVG='http://www.w3.org/2000/svg';
const SE=(tag,attrs={})=>{const x=document.createElementNS(SVG,tag);for(const [k,v] of Object.entries(attrs))x.setAttribute(k,String(v));return x};
const add=(p,child)=>{p.appendChild(child);return child};
const clear=p=>{p.replaceChildren();return p};
const F=n=>Math.round(n).toLocaleString('de-DE');
const RAD=Math.PI/180,B=[13.385,52.49,13.407,52.512],mlat=111132,mlon=111320*Math.cos((B[1]+B[3])/2*RAD),R=300,GRID=90;
const s={loaded:false,stage:0,furthest:0,selected:null,first:null,priority:null,check:null,confirmed:false,completed:false,
    zones:[],fountains:[],sample:[],high:[],baseline:[],candidates:[],byId:new Map(),changes:0};
const priorityText={coverage:'Mehr Rasterpunkte in Reichweite',severity:'Mehr Punkte der Klasse „sehr ungünstig“',gap:'Grössere Abstandslücke zum nächsten Brunnen'};
const checkText={operation:'Aktuellen Betriebsstatus bestehender Brunnen prüfen',access:'Fusswege und barrierefreie Erreichbarkeit prüfen',feasibility:'Grundstück, Anschluss und Genehmigungen prüfen'};
const weights={coverage:'gain',severity:'severe',gap:'nearestMeters'};
const stages=['brief','evidence','decision','result'];
const reduceMotion=()=>window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const pSVG=(tag,attrs,host)=>add(host,SE(tag,attrs));
const W=800,H=650,zoneWidth=(B[2]-B[0])*mlon,zoneHeight=(B[3]-B[1])*mlat,PIX=Math.min(470/zoneWidth,540/zoneHeight);
const bw=zoneWidth*PIX,bh=zoneHeight*PIX,left=(W-bw)/2,top=(H-bh)/2;
const xOf=lon=>left+(lon-B[0])*mlon*PIX,yOf=lat=>top+(B[3]-lat)*mlat*PIX;
const xy=p=>[xOf(p.lon),yOf(p.lat)];
function toast(message){
 const target=$('#toast');target.textContent=message;target.classList.add('visible');window.clearTimeout(toast.timer);
 toast.timer=window.setTimeout(()=>target.classList.remove('visible'),2900);
}
function dist(a,b){
 const dp=(b.lat-a.lat)*RAD,dl=(b.lon-a.lon)*RAD,h=Math.sin(dp/2)**2+
 Math.cos(a.lat*RAD)*Math.cos(b.lat*RAD)*Math.sin(dl/2)**2;
 return 2*6371008.8*Math.asin(Math.min(1,Math.sqrt(h)));
}
function inRing(lon,lat,ring){let inside=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){
 const a=ring[i],b=ring[j];if((a[1]>lat)!==(b[1]>lat)&&lon<(b[0]-a[0])*(lat-a[1])/(b[1]-a[1])+a[0])inside=!inside;
}return inside}
function inGeo(lon,lat,g){const polys=g.type==='MultiPolygon'?g.coordinates:g.type==='Polygon'?[g.coordinates]:[];
 return polys.some(r=>r.length&&inRing(lon,lat,r[0])&&!r.slice(1).some(h=>inRing(lon,lat,h)));
}
function pathGeo(g){
 const polygons=g.type==='MultiPolygon'?g.coordinates:g.type==='Polygon'?[g.coordinates]:[];
 let path='';
 for(const rings of polygons)for(const ring of rings){
   if(!ring.length)continue;
   const start=xy({lon:ring[0][0],lat:ring[0][1]});path+='M'+start[0].toFixed(2)+' '+start[1].toFixed(2);
   for(let i=1;i<ring.length;i++){const pt=xy({lon:ring[i][0],lat:ring[i][1]});path+='L'+pt[0].toFixed(2)+' '+pt[1].toFixed(2)}
   path+='Z';
 }
 return path;
}
function assignModel(){
 const grid=[];
 for(let lat=B[1]+(GRID/mlat)/2;lat<B[3];lat+=GRID/mlat)
  for(let lon=B[0]+(GRID/mlon)/2;lon<B[2];lon+=GRID/mlon){
    const zone=s.zones.find(z=>inGeo(lon,lat,z.g));if(!zone)continue;
    let nearest=Infinity,waterId=null;
    for(const f of s.fountains){const m=dist({lon,lat},f);if(m<nearest){nearest=m;waterId=f.id}}
    grid.push({lon,lat,heat:zone.heat,nearest,waterId});
  }
 s.sample=grid;s.high=grid.filter(x=>x.heat==='ungünstig'||x.heat==='sehr ungünstig');
 s.baseline=s.high.filter(x=>x.nearest>R);
 if(grid.length!==290||s.high.length!==192||s.baseline.length!==126)throw Error('Study grid count differs from reference geo-verification');
 for(const c of s.candidates){
   c.newly=s.baseline.filter(p=>dist(c,p)<=R);
   c.gain=c.newly.length;
   c.severe=c.newly.filter(p=>p.heat==='sehr ungünstig').length;
   let nearest={metres:Infinity,fountain:null};
   for(const f of s.fountains){const d=dist(c,f);if(d<nearest.metres)nearest={metres:d,fountain:f}}
   c.nearestMeters=Math.round(nearest.metres);
   c.nearestFountainId=nearest.fountain?.id??null;
   c.heatClass=s.zones.find(z=>inGeo(c.lon,c.lat,z.g))?.heat??'unbekannt';
   const want=c.expected;
   if(c.gain!==want.gain||c.severe!==want.severe||Math.abs(c.nearestMeters-want.nearestMeters)>2||
       c.nearestFountainId!==want.nearestId||c.heatClass!==want.heatClass)
     throw Error('Candidate reference mismatch: '+c.id);
 }
 s.byId=new Map(s.candidates.map(c=>[c.id,c]));
}
function bestFor(priority){const metric=weights[priority];return s.candidates.slice().sort((a,b)=>b[metric]-a[metric])[0]}
function chosen(){return s.selected?s.byId.get(s.selected):null}
function pick(id,{mapFocus=false}={}){
 if(!s.loaded||s.completed||!s.byId.has(id))return;
 s.selected=id;s.changes++;
 renderUI();renderMap({animate:true});
 if(mapFocus){
    const mapText=$('#map-caption');
    if(mapText)mapText.classList.add('map-caption-changed');
 }
}
function describeMetric(k,val){return k==='gap'?F(val)+' m':(k==='coverage'?'+'+F(val):F(val))}
function metricFor(c,k){return c[weights[k]]}
function effectTradeoff(c){
 if(!c||!s.priority)return 'Eine gute Empfehlung benennt auch die Alternative.';
 const leader=bestFor(s.priority);
 const a=s.byId.get('A'),b=s.byId.get('B'),g=s.byId.get('C');
 if(c.id===leader.id){
   const others=[];
   if(c.id!=='A')others.push('A erreicht '+(a.gain-c.gain)+' zusätzliche Rasterpunkte mehr'.replace('+-','-'));
   if(c.id!=='B')others.push('B erreicht '+(b.severe-c.severe)+' Punkte der Klasse „sehr ungünstig“ mehr'.replace('+-','-'));
   if(c.id!=='C')others.push('C hat einen '+F(g.nearestMeters-c.nearestMeters)+' m grösseren Abstand zum nächsten Inventarbrunnen');
   const useful=others.filter(x=>!x.includes(' -')&&!x.includes(' 0 '));
   return 'Dein Kriterium spricht im Modell für '+c.id+'. Aber auch andere Werte zählen: '+(useful[0]??'Die anderen Orte haben andere Stärken')+'.';
 }
 const delta=metricFor(leader,s.priority)-metricFor(c,s.priority);
 const units=s.priority==='gap'?' Meter':' Rasterpunkte';
 return 'Nach deinem Kriterium wäre '+leader.id+' um '+F(delta)+units+' stärker. Du kannst trotzdem '+c.id+' zur Prüfung wählen – wichtig ist, diese Abwägung offenzulegen.';
}
function revealText(){
 const first=s.byId.get(s.first);
 const a=s.byId.get('A'),b=s.byId.get('B'),c=s.byId.get('C');
 return 'Bei '+first.id+' siehst du zunächst +'+first.gain+' Rasterpunkte. Aber B erreicht '+b.severe+' Punkte in der Klasse „sehr ungünstig“ (A: '+a.severe+'). Und C liegt rund '+F(c.nearestMeters)+' m vom nächsten inventarisierten Brunnen entfernt.';
}
function renderCards(){
 const target=clear($('#brief-options')),final=clear($('#decision-options'));
 for(const c of s.candidates){
   for(const [host,kind] of [[target,'initial'],[final,'decision']]){
     const card=add(host,E('button',undefined,'candidate-card'+(s.selected===c.id?' selected':'')));
     card.type='button';card.dataset.pick=c.id;card.setAttribute('aria-pressed',String(s.selected===c.id));
     const letter=add(card,E('span',c.id,'letter'));letter.setAttribute('aria-hidden','true');
     const body=add(card,E('span',undefined,'body'));
     add(body,E('strong',c.title));
     add(body,E('small',kind==='initial'?c.subtitle:('+'+c.gain+' Rasterpunkte · '+c.severe+' „sehr ungünstig“'));
     const score=add(card,E('span',undefined,'score'));
     add(score,E('b','+'+c.gain));add(score,E('span','Modellpunkte'));
     add(card,E('span','✓','tick'));
     card.addEventListener('click',()=>pick(c.id));
   }
 }
}
function renderEvidence(){
 const rows=clear($('#evidence-rows'));
 for(const c of s.candidates){
   const r=add(rows,E('div',undefined,'evidence-row'+(c.id===s.selected?' active':'')));
   r.dataset.id=c.id;
   const l=add(r,E('span',c.id,'evi-letter'));
   add(r,E('span',c.title,'evi-name'));
   const stat=(n,label)=>{const w=add(r,E('span',undefined,'evi-stat'));add(w,E('strong',n));add(w,E('small',label))};
   stat('+'+c.gain,'neu im Radius');
   stat(String(c.severe),'sehr ungünstig');
   stat(F(c.nearestMeters)+'m','nächster WFS');
 }
}
function renderPriority(){
 $$('.priority').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.priority===s.priority)));
 const info=$('#priority-feedback');
 if(!s.priority){info.textContent='Entscheide, welche Art von Hinweis dich bei der ersten Prüfung besonders interessiert.';return}
 const best=bestFor(s.priority);
 info.textContent='Für „'+priorityText[s.priority]+'“ liefert '+best.id+' den höchsten Modellwert. Das ist ein Anhaltspunkt – keine automatisch richtige Entscheidung.';
}
function renderDecision(){
 $('#tradeoff-copy').textContent=effectTradeoff(chosen());
 $$('.check-options button').forEach(b=>b.setAttribute('aria-pressed',String(s.check===b.dataset.check)));
 $('#consent').checked=s.confirmed;
 $('#commit').disabled=!(s.selected&&s.priority&&s.check&&s.confirmed);
 const feedback=$('#decision-feedback');
 feedback.textContent=s.check?'Du priorisierst: '+checkText[s.check]+'. Prüfe noch die Einordnung des Modells.':'Wähle einen Prüfschritt und bestätige die Modellgrenze.';
}
function renderReceipt(){
 const c=chosen();if(!c)return;
 $('#result-letter').textContent=c.id;
 $('#result-name').textContent=c.title;
 $('#result-gain').textContent='+'+c.gain+' Rasterpunkte (Modell)';
 $('#result-priority').textContent=priorityText[s.priority]??'—';
 $('#result-check').textContent=checkText[s.check]??'—';
 $('#result-unknown').textContent='Unsicher bleiben reale Zugänglichkeit, Betriebsbereitschaft, Grundstücke, Kosten und Genehmigungen. Deine Wahl verändert diese Wissenslücken nicht.';
 $('#result-reflection').textContent=c.id===bestFor(s.priority).id
  ?'Du hast deiner Priorität eine klare Richtung gegeben. Der nächste Schritt ist keine Umsetzung, sondern eine fachliche Gegenprüfung.'
  :'Du hast trotz einer anderen Modellspitze begründet gewählt. Gerade deshalb sollten die Zielkonflikte im Prüfgespräch sichtbar bleiben.';
}
function renderUI(){
 if(!s.loaded)return;
 renderCards();renderEvidence();renderPriority();renderDecision();renderReceipt();
 $('#first-choice').textContent=s.first??'—';
 $('#reveal-copy').textContent=s.first?revealText():'Die zweite Kennzahl verändert die Perspektive.';
 $('#initial-hint').textContent=s.selected?('Deine erste Idee: '+s.selected+'. Du kannst sie gleich noch überdenken.'):'Wähle A, B oder C auf der Karte oder hier.';
 $('#to-evidence').disabled=!s.selected;
 $('#to-decision').disabled=!s.priority;
 $('#caption-text').textContent=s.completed?'Deine Wahl: '+s.selected+' · zur Prüfung, nicht zum Bau.':s.selected?
   (s.selected+': +'+chosen().gain+' Modellpunkte im Radius. Welche Frage folgt daraus?'):'Tippe auf A, B oder C – auf der Karte oder links.';
}
function go(stage,{scroll=true}={}){
 if(stage!==3&&stage>s.furthest)return;
 s.stage=stage;s.furthest=Math.max(s.furthest,stage);
 for(let i=0;i<stages.length;i++)$('#stage-'+stages[i]).hidden=i!==stage;
 $$('.step').forEach(b=>{
    const i=Number(b.dataset.step);
    b.disabled=i>s.furthest||s.completed;
    b.classList.toggle('active',stage===i);
    if(stage===i)b.setAttribute('aria-current','step');else b.removeAttribute('aria-current');
 });
 if(stage===3)renderReceipt();
 if(stage===1)renderEvidence();
 renderMap({animate:false});
 if(scroll)window.scrollTo({top:0,behavior:reduceMotion()?'auto':'smooth'});
 const focus=stage===3?'#stage-result .result-title':stage===0?'#stage-brief h1':stage===1?'#stage-evidence h2':'#stage-decision h2';
 $(focus)?.setAttribute('tabindex','-1');$(focus)?.focus({preventScroll:true});
}
function shareLink(){
 const u=new URL(location.href);
 for(const k of ['site','priority','check','done'])u.searchParams.delete(k);
 if(s.selected)u.searchParams.set('site',s.selected);
 if(s.priority)u.searchParams.set('priority',s.priority);
 if(s.check)u.searchParams.set('check',s.check);
 if(s.completed)u.searchParams.set('done','1');
 u.hash='';return u.toString();
}
function downloadCase(){
 if(!s.completed){toast('Schliesse zuerst deine Entscheidung ab.');return}
 const c=chosen(),best=bestFor(s.priority);
 const lines=[
  '# CITY THREAD / THE BRIEF — FIELD NOTE 007',
  '',
  '**Spielerische Priorisierung für eine fachliche Vor-Ort-Prüfung.** Kein Bauauftrag, keine Behördengenehmigung, keine Einreichung.',
  '',
  'Fiktive Ausgangslage: genau eine vertiefte Vor-Ort-Prüfung kann priorisiert werden. Es liegen keine echten Budgetdaten vor.',
  'Gewählter Standort: '+c.id+' – '+c.title+' ('+c.lat.toFixed(6)+', '+c.lon.toFixed(6)+')',
  'Prioritätsprinzip: '+priorityText[s.priority],
  'Erster notwendiger Prüfschritt: '+checkText[s.check],
  'Breite Modellwirkung: +'+c.gain+' bisher unberücksichtigte 90-m-Rasterpunkte in 300 m Luftlinie.',
  'Davon historische bioklimatische Klasse „sehr ungünstig“: '+c.severe+' Punkte.',
  'Nächster WFS-inventarisierter Trinkbrunnen: '+c.nearestMeters+' m Luftlinie (WFS-ID '+c.nearestFountainId+').',
  '',
  '## Andere untersuchte Standorte',
  ...s.candidates.map(v=>'- '+v.id+': +'+v.gain+' Rasterpunkte, '+v.severe+' „sehr ungünstig“, '+v.nearestMeters+' m zum nächsten inventarisierten Brunnen'),
  '',
  '## Zielkonflikt und Lernmoment',
  effectTradeoff(c),
  'Leitwert deiner Priorität: Standort '+best.id+' nach '+priorityText[s.priority]+'.',
  '',
  '## Was dieses Experiment NICHT zeigt',
  '- Keine Bevölkerungszahl, Wärme-/Abkühlungswirkung, Gehstrecke oder gesicherte Trinkwasserversorgung.',
  '- Keine geprüfte Betriebsbereitschaft der inventarisierten Brunnen, Barrierefreiheit, Eigentum, Wasseranschluss, Kosten oder Genehmigungen.',
  '- Keine tatsächliche Finanzierung oder behördliche Auswahl; das eine Zeitfenster ist eine fiktive Spielregel.',
  '',
  '## Reproduzierbare Datenbasis / Lizenz',
  'Berliner Trinkwasserbrunnen WFS, 242 Datensätze, Abruf 2026-10-09: https://daten.berlin.de/datensaetze/trinkwasserbrunnen-wfs-47dba2c3',
  'Berliner Umweltatlas bioklimatische Gesamtbewertung Siedlungsflächen 2022, 154 Studienfenster-Polygone: https://daten.berlin.de/datensaetze/klimabewertungskarten-2022-umweltatlas-wfs-ac0751a2',
  'Geometrieprüfung: 90-m-Raster, Point-in-Polygon, Distanz Haversine (300 m); verifiziert im Repository.',
  'Datenlizenz Deutschland – Zero – Version 2.0.',
  'Keine Daten wurden an Behörden gesendet.',
  '',
  'Spielbarer Link: '+shareLink()
 ];
 const blob=new Blob([lines.join('\n')],{type:'text/markdown;charset=utf-8'});
 const a=E('a');a.href=URL.createObjectURL(blob);a.download='CITY_THREAD_THE_BRIEF_Fallakte.md';
 document.body.appendChild(a);a.click();a.remove();
 window.setTimeout(()=>URL.revokeObjectURL(a.href),1200);toast('Deine Fallakte wurde lokal erstellt. ✳');
}
async function copyLink(){
 const link=shareLink();
 try{await navigator.clipboard.writeText(link);toast('Dein Entscheidungslink ist kopiert. ✳')}
 catch{window.prompt('Link zur Mission kopieren:',link)}
}
function complete(){
 if(!(s.selected&&s.priority&&s.check&&s.confirmed)){toast('Wähle einen Kandidaten, einen Prüfschritt und bestätige den Hinweis.');return}
 s.completed=true;s.furthest=3;
 renderUI();go(3);history.replaceState({},'',shareLink());
}
function reset(){
 s.stage=0;s.furthest=0;s.selected=null;s.first=null;s.priority=null;s.check=null;
 s.confirmed=false;s.completed=false;s.changes=0;
 history.replaceState({},'',location.pathname);
 renderUI();go(0);toast('Neue Mission. Eine neue Frage.');
}
function restoreFromUrl(){
 const q=new URLSearchParams(location.search);
 const candidate=q.get('site'),prio=q.get('priority'),check=q.get('check'),done=q.get('done');
 if(!candidate||!s.byId.has(candidate))return;
 s.selected=candidate;s.first=candidate;
 if(prio in weights){s.priority=prio;s.furthest=1}
 if(check in checkText&&s.priority){s.check=check;s.furthest=2}
 if(done==='1'&&s.check){s.completed=true;s.confirmed=true;s.furthest=3;s.stage=3}
 else if(s.check)s.stage=2;
 else if(s.priority)s.stage=1;
 else s.stage=0;
}
const layerColors={'sehr ungünstig':'#D17D70','ungünstig':'#E8AB94','weniger günstig':'#E9D7AC','günstig':'#C5DBCA'};
function worldMapPath(g){
 const ps=g.type==='MultiPolygon'?g.coordinates:g.type==='Polygon'?[g.coordinates]:[];
 let path='';
 for(const rings of ps)for(const ring of rings){
   if(!ring.length)continue;
   const p=[xOf(ring[0][0]),yOf(ring[0][1])];path+='M'+p[0].toFixed(2)+' '+p[1].toFixed(2);
   for(let i=1;i<ring.length;i++)path+='L'+xOf(ring[i][0]).toFixed(2)+' '+yOf(ring[i][1]).toFixed(2);
   path+='Z';
 }
 return path;
}
function renderMap({animate=false}={}){
 if(!s.loaded)return;
 const host=clear($('#map-svg'));
 host.setAttribute('viewBox',window.innerWidth<=620?'170 0 455 650':'0 0 800 650');
 $('#basemap').setAttribute('viewBox',host.getAttribute('viewBox'));
 const defs=add(host,SE('defs'));
 const lines=add(defs,SE('pattern',{id:'brief-grid',width:43,height:43,patternUnits:'userSpaceOnUse'}));
 pSVG('path',{d:'M43 0H0V43',stroke:'#8E9EA9','stroke-opacity':'.14',fill:'none','stroke-width':1},lines);
 pSVG('rect',{x:0,y:0,width:W,height:H,fill:'url(#brief-grid)'},host);
 const clip=add(defs,SE('clipPath',{id:'brief-clip'}));
 pSVG('rect',{x:left,y:top,width:bw,height:bh},clip);
 pSVG('rect',{x:left,y:top,width:bw,height:bh,fill:'#FAF6EB', 'fill-opacity':'.40',stroke:'#9FA9A7','stroke-opacity':'.5','stroke-width':1.5,'stroke-dasharray':'6 6'},host);
 const polys=add(host,SE('g',{'clip-path':'url(#brief-clip)'}));
 for(const zone of s.zones){
  pSVG('path',{d:worldMapPath(zone.g),fill:layerColors[zone.heat]??'#C9D5C9','fill-opacity':'.65',
    stroke:'#F9F4E8','stroke-width':1,'fill-rule':'evenodd','pointer-events':'none',class:'climate-polygon'},polys);
 }
 for(const f of s.fountains){
   const [x,y]=xy(f);
   if(x<left-17||x>left+bw+17||y<top-17||y>top+bh+17)continue;
   const p=pSVG('circle',{cx:x,cy:y,r:4.8,fill:'#6369CB',stroke:'#FFFEFB','stroke-width':1.6,'pointer-events':'none',class:'fountain-dot'},host);
   add(p,SE('title')).textContent='Dokumentierter Trinkbrunnen (WFS): '+f.n;
 }
 const selected=chosen();
 if(selected){
   const [x,y]=xy(selected);
   const area=add(host,SE('g',{'pointer-events':'none'}));
   pSVG('circle',{cx:x,cy:y,r:R*PIX,fill:'#525EC0','fill-opacity':'.055',
      stroke:'#545EC8','stroke-width':2.1,'stroke-dasharray':'7 7'},area);
   const group=add(host,SE('g',{'pointer-events':'none'}));
   for(let i=0;i<selected.newly.length;i++){
     const cell=selected.newly[i],[cx,cy]=xy(cell);
     const connection=pSVG('line',{x1:x,y1:y,x2:cx,y2:cy,class:'connection'+(animate&&!reduceMotion()?' revealed':''),
       style:'--delay:'+Math.min(i*17,390)+'ms','stroke-opacity':.38},group);
     const dot=pSVG('circle',{cx,cy,r:cell.heat==='sehr ungünstig'?3.9:3.3,
        fill:cell.heat==='sehr ungünstig'?'#E3B867':'#555ECC',
        class:'new-point',style:'--delay:'+Math.min(i*15,390)+'ms'},group);
   }
   pSVG('circle',{cx:x,cy:y,r:36,fill:'none',stroke:'#4C58C3','stroke-width':1.5,'stroke-opacity':'.65','stroke-dasharray':'3 7',class:'selected-ring'},host);
 }
 for(const c of s.candidates){
   const [x,y]=xy(c),active=s.selected===c.id;
   const g=add(host,SE('g',{role:'button',tabindex:'0',class:'map-marker','data-pin':c.id,'aria-label':'Standort '+c.id+' – '+c.title+' auswählen'}));
   const fill=c.id==='A'?'#D98F77':c.id==='B'?'#505ACC':'#8FA782';
   if(active)pSVG('circle',{cx:x,cy:y,r:31,fill:fill,'fill-opacity':'.12',stroke:fill,'stroke-opacity':'.30','stroke-width':2},g);
   pSVG('circle',{cx:x,cy:y,r:active?20:17,fill,stroke:'#FFFEFB','stroke-width':3,style:'filter:drop-shadow(0 4px 4px rgba(52,56,85,.15))'},g);
   const text=add(g,SE('text',{x,y:y+5,'text-anchor':'middle','font-family':'Georgia,serif','font-size':18,'font-weight':750,fill:'#FFFDF9','pointer-events':'none'}));text.textContent=c.id;
   pSVG('circle',{cx:x,cy:y,r:30,fill:'transparent',class:'marker-hit'},g);
   add(g,SE('title')).textContent=c.id+' – '+c.title+' ('+c.gain+' Rasterpunkte)';
   g.addEventListener('click',()=>pick(c.id));
   g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();pick(c.id);window.requestAnimationFrame(()=>$('#map-svg [data-pin="'+c.id+'"]')?.focus())}});
 }
 $('#world-stat').textContent=s.completed?'DEINE WAHL: '+s.selected+' · FACHPRÜFUNG':s.selected?
   ('+'+selected.gain+' MODELLPUNKTE / '+s.selected+' GEWÄHLT'):'03 KANDIDATEN / 01 PRÜFUNG';
}
function initBasemap(){
 const host=clear($('#basemap'));
 // Optional street context: OpenStreetMap raster tiles, NOT used for any calculations.
 // Only request tiles within the study rectangle; no hidden prefetch or analytics.
 const z=15,N=2**z,tx=lon=>(lon+180)/360*N,ty=lat=>(1-Math.asinh(Math.tan(lat*RAD))/Math.PI)/2*N;
 const lonOf=x=>x/N*360-180,latOf=y=>Math.atan(Math.sinh(Math.PI*(1-2*y/N)))/RAD;
 const lonWest=B[0]-left/(mlon*PIX),lonEast=B[0]+(W-left)/(mlon*PIX);
 const north=B[3]+top/(mlat*PIX),south=B[3]-(H-top)/(mlat*PIX);
 for(let x=Math.floor(tx(lonWest));x<=Math.ceil(tx(lonEast));x++)for(let y=Math.floor(ty(north));y<=Math.ceil(ty(south));y++){
  if(x<0||y<0||x>=N||y>=N)continue;
  const px=xOf(lonOf(x)),py=yOf(latOf(y)),pw=xOf(lonOf(x+1))-px,ph=yOf(latOf(y+1))-py;
  pSVG('image',{x:px,y:py,width:pw,height:ph,href:'https://tile.openstreetmap.org/'+z+'/'+x+'/'+y+'.png',preserveAspectRatio:'none'},host);
 }
 host.setAttribute('viewBox',$('#map-svg').getAttribute('viewBox'));
}
function handleStageControls(){
 $('#to-evidence').addEventListener('click',()=>{
  if(!s.selected)return;
  s.first=s.selected;s.furthest=1;
  renderUI();go(1);
 });
 $('#to-decision').addEventListener('click',()=>{
  if(!s.priority)return;
  s.furthest=2;renderUI();go(2);
 });
 $('#commit').addEventListener('click',complete);
 $$('.step').forEach(b=>b.addEventListener('click',()=>{
  const step=Number(b.dataset.step);if(step<=s.furthest&&!s.completed)go(step);
 }));
 $$('[data-back]').forEach(b=>b.addEventListener('click',()=>go(Number(b.dataset.back))));
 $$('.priority').forEach(b=>b.addEventListener('click',()=>{
  if(s.completed)return;s.priority=b.dataset.priority;renderUI();renderMap();
 }));
 $$('.check-options button').forEach(b=>b.addEventListener('click',()=>{
  if(s.completed)return;s.check=b.dataset.check;renderDecision();
 }));
 $('#consent').addEventListener('change',e=>{s.confirmed=e.target.checked;renderDecision()});
 $('#download-case').addEventListener('click',downloadCase);
 $('#share-case').addEventListener('click',copyLink);
 $('#header-share').addEventListener('click',copyLink);
 $('#play-again').addEventListener('click',reset);
 const dlg=$('#method-dialog');
 $('#open-method-1').addEventListener('click',()=>dlg.showModal());
 $('#open-method-2').addEventListener('click',()=>dlg.showModal());
 $('#close-method').addEventListener('click',()=>dlg.close());
 dlg.addEventListener('click',e=>{if(e.target===dlg)dlg.close()});
 $('#retry').addEventListener('click',()=>window.location.reload());
 window.addEventListener('resize',()=>{
    if(s.loaded)renderMap();
 });
}
async function fetchData(){
 const all=[...Array.from({length:4},(_,i)=>'../fountains-all-'+i+'.json'),
            ...Array.from({length:4},(_,i)=>'../heat-'+i+'.json'),'./candidates.json'];
 const files=await Promise.all(all.map(async path=>{
    const r=await fetch(path,{cache:'no-store'});if(!r.ok)throw Error('WFS asset '+path+': '+r.status);return r.json();
 }));
 const water=files.slice(0,4),heat=files.slice(4,8),mission=files[8];
 if(!water.every((x,i)=>x.page===i&&x.matched===242)||!heat.every((x,i)=>x.page===i&&x.totalMatched===154))throw Error('WFS pagination metadata inconsistent');
 const fountains=water.flatMap(x=>x.records),zones=heat.flatMap(x=>x.features);
 if(fountains.length!==242||new Set(fountains.map(x=>x.id)).size!==242||zones.length!==154||new Set(zones.map(x=>x.id)).size!==154)throw Error('Dataset size or identity validation failed');
 if(!mission.fictionalBrief||mission.candidates?.length!==3||mission.dataSource?.hypotheticalRadiusMetres!==300)throw Error('Mission integrity failed');
 if(mission.candidates.map(x=>x.id).join('')!=='ABC')throw Error('Candidate IDs or order changed');
 if(!fountains.every(x=>x.n&&x.d&&Number.isFinite(x.lat)&&Number.isFinite(x.lon))||
    !zones.every(x=>x.id&&x.heat&&x.g))throw Error('Missing mandatory data fields');
 s.fountains=fountains;s.zones=zones;s.candidates=mission.candidates;s.loaded=true;
 assignModel();
}
async function boot(){
 $('#loading').hidden=false;
 try{
  await fetchData();initBasemap();restoreFromUrl();
  $('#loading').hidden=true;renderUI();
  go(s.completed?3:s.stage,{scroll:false});
  $('#world-stat').textContent=s.completed?'FALLAKTE BEREIT':'03 KANDIDATEN · ECHTE WFS-DATEN';
  // All choices and the hypothetical task are local; no report is sent anywhere.
 }catch(e){
  console.error('CITY THREAD brief failed:',e);
  s.loaded=false;$('#loading').hidden=true;$('#error').hidden=false;
  $('#error-message').textContent='Wir konnten die WFS-Snapshots nicht konsistent prüfen. Ohne belastbare Daten gibt es hier keine spielbare Empfehlung.';
  $('#world-stat').textContent='DATENQUELLE NICHT PRÜFBAR';
  $('#caption-text').textContent='Die Quelldaten konnten nicht verifiziert werden.';
 }
}
handleStageControls();boot();
})();