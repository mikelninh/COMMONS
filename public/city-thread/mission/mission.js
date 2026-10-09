/* CITY THREAD v0.4 — THE MISSING FOUNTAIN
 * Independent civic learning scenario · Berlin open WFS snapshots, 09 Oct 2026.
 * The WFS sources are read-only; no city agency receives a proposal.
 * What-if engine: authoritative polygon point-in-ring classification;
 * 90m regular WGS84-anchored sample grid; haversine distances to 242 recorded sites;
 * scenario radius is a configurable straight-line HYPOTHESIS, not actual access.
 */
(()=>{'use strict';
const $=(q,root=document)=>root.querySelector(q);
const $$=(q,root=document)=>[...root.querySelectorAll(q)];
const NS='http://www.w3.org/2000/svg';
const svg=(tag,attrs={})=>{const x=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))x.setAttribute(k,String(v));return x};
const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=String(text??'');if(cls)x.className=cls;return x};
const add=(parent,child)=>{parent.appendChild(child);return child};
const empty=node=>{node.replaceChildren();return node};
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const num=n=>Number(n).toLocaleString('de-DE');
const fmt=n=>Number(n).toFixed(5);
const B=[13.385,52.490,13.407,52.512];
const CENTER_LAT=(B[1]+B[3])/2, RAD=Math.PI/180, METERS_PER_LAT=111132, METERS_PER_LON=111320*Math.cos(CENTER_LAT*RAD);
const S={loaded:false,fountains:[],zones:[],grid:[],heated:[],radius:300,site:null,visibleHeat:true,visibleWater:true,visibleReach:true,suggestions:[],model:null,dragging:null,snapshot:'2026-10-09',count:0,review:false,history:[],compare:'after',interacted:false,lastGain:null};
const W=720,H=700,TOP=55,BOTTOM=642;
const availableW=620,availableH=BOTTOM-TOP,zoneWidthM=(B[2]-B[0])*METERS_PER_LON,zoneHeightM=(B[3]-B[1])*METERS_PER_LAT;
const PIX_PER_M=Math.min(availableW/zoneWidthM,availableH/zoneHeightM);
const BOXW=zoneWidthM*PIX_PER_M,BOXH=zoneHeightM*PIX_PER_M;
const left=(W-BOXW)/2,top=TOP+(availableH-BOXH)/2,right=left+BOXW,bottom=top+BOXH;
const xCoord=lon=>left+(lon-B[0])*METERS_PER_LON*PIX_PER_M;
const yCoord=lat=>top+(B[3]-lat)*METERS_PER_LAT*PIX_PER_M;
const pointCoord=(lon,lat)=>[xCoord(lon),yCoord(lat)];
const invXY=(x,y)=>({lon:clamp(B[0]+(x-left)/(METERS_PER_LON*PIX_PER_M),B[0],B[2]),lat:clamp(B[3]-(y-top)/(METERS_PER_LAT*PIX_PER_M),B[1],B[3])});
const inWindow=p=>p.lon>=B[0]&&p.lon<=B[2]&&p.lat>=B[1]&&p.lat<=B[3];
function dist(a,b){
  const dp=(b.lat-a.lat)*RAD,dl=(b.lon-a.lon)*RAD,lat1=a.lat*RAD,lat2=b.lat*RAD;
  const h=Math.sin(dp/2)**2+Math.cos(lat1)*Math.cos(lat2)*Math.sin(dl/2)**2;
  return 2*6371008.8*Math.asin(Math.min(1,Math.sqrt(h)));
}
function inRing(lon,lat,ring){
  let inside=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){
   const A=ring[i],Z=ring[j];
   if(((A[1]>lat)!==(Z[1]>lat))&&lon<(Z[0]-A[0])*(lat-A[1])/(Z[1]-A[1])+A[0])inside=!inside;
  }return inside;
}
function inGeo(lon,lat,geo){
  const polygons=geo.type==='MultiPolygon'?geo.coordinates:geo.type==='Polygon'?[geo.coordinates]:[];
  return polygons.some(rings=>rings.length&&inRing(lon,lat,rings[0])&&!rings.slice(1).some(r=>inRing(lon,lat,r)));
}
function heatZoneAt(p){return S.zones.find(z=>inGeo(p.lon,p.lat,z.g))??null}
function isHeavy(c){return c==='ungünstig'||c==='sehr ungünstig'}
function baselineDistance(p){
  let min=Infinity,nearest=null;
  for(const f of S.fountains){const d=dist(p,f);if(d<min){min=d;nearest=f}}
  return {min,nearest};
}
function makeGrid(){
 const stepLat=90/METERS_PER_LAT,stepLon=90/METERS_PER_LON,grid=[];
 for(let lat=B[1]+stepLat/2;lat<B[3];lat+=stepLat){
  for(let lon=B[0]+stepLon/2;lon<B[2];lon+=stepLon){
    const p={lon,lat};const zone=heatZoneAt(p);
    if(!zone)continue;
    const near=baselineDistance(p);
    grid.push({lon,lat,heat:zone.heat,zoneId:zone.id,nearest:near.min,nearestId:near.nearest?.id});
  }
 }
 S.grid=grid;S.heated=grid.filter(p=>isHeavy(p.heat));
}
function model(site){
 const radius=S.radius,uncovered=S.heated.filter(p=>p.nearest>radius),
 newly=site?uncovered.filter(p=>dist(p,site)<=radius):[];
 const nearest=site?baselineDistance(site):null;
 const zone=site?heatZoneAt(site):null;
 return {radius,total:S.heated.length,baseline:uncovered.length,gain:newly.length,after:uncovered.length-newly.length,newly,nearest,zone,samples:S.grid.length};
}
function pickSuggestions(){
 const baseline=S.heated.filter(p=>p.nearest>S.radius),arr=[];
 for(const p of baseline){
    let score=0;for(const q of baseline)if(dist(p,q)<=S.radius)score++;
    arr.push({lon:p.lon,lat:p.lat,score,heat:p.heat});
 }
 arr.sort((a,b)=>b.score-a.score);
 const picks=[];
 for(const p of arr){
    if(picks.every(q=>dist(p,q)>470)){picks.push(p);if(picks.length===3)break}
 }
 S.suggestions=picks;
 const host=empty($('#suggestion-buttons'));
 for(let i=0;i<picks.length;i++){
   const s=picks[i];
   const b=add(host,el('button',undefined));b.type='button';b.dataset.suggestion=String(i);
   const title=add(b,el('span','Ort '+String.fromCharCode(65+i)+' · Testpunkt'));
   const count=add(b,el('span','+'+num(s.score)+' Punkte →'));
   title.style.color='#364C60';count.style.color='#5966B7';
   b.addEventListener('click',()=>setSite({lon:s.lon,lat:s.lat},'suggestion',true));
 }
 if(!picks.length)add(host,el('p','Keine zusätzlichen Rasterpunkte im angenommenen Radius.','loading'));
 highlightSuggestion();
}
function highlightSuggestion(){
 $$('#suggestion-buttons button').forEach((b,i)=>b.classList.toggle('selected',!!S.site&&dist(S.site,S.suggestions[i])<25));
}
function record(action){
  S.history.push({action,at:new Date().toISOString(),site:S.site?{lon:+S.site.lon.toFixed(6),lat:+S.site.lat.toFixed(6)}:null,radius:S.radius});
  if(S.history.length>40)S.history.shift();
}
let paintFrame=0;
function setSite(p,action='manual',log=true){
 if(!S.loaded)return;
 S.site={lon:clamp(p.lon,B[0],B[2]),lat:clamp(p.lat,B[1],B[3])};
 if(log)record(action);
 if(action!=='initial-demo-suggestion'&&action!=='shared-scenario-loaded'){
    S.interacted=true;
    $('#map-guidance')?.classList.add('hidden');
 }
 if(action==='map-drag'){
   if(!paintFrame)paintFrame=requestAnimationFrame(()=>{paintFrame=0;updateModel();});
 }else{
   if(paintFrame){cancelAnimationFrame(paintFrame);paintFrame=0;}
   updateModel();
 }
}
function updateModel(){
 if(!S.loaded)return;
 S.model=model(S.site);
 const M=S.model,zone=M.zone;
 $('#site-coordinate').textContent=S.site?fmt(S.site.lat)+'° N, '+fmt(S.site.lon)+'° E':'Noch kein Standort';
 $('#site-class').textContent=zone?'Historische Klimaklasse: '+zone.heat+' · 2022':'Ausserhalb bewerteter Siedlungsflächen';
 $('#radius-label').textContent=S.radius+' m';
 $('#before-count').textContent=num(M.baseline);
 $('#after-count').textContent=S.site?num(M.after):'—';
 $('#newly-covered').textContent=(S.site?'+'+num(M.gain):'—')+' Rasterpunkte neu in Reichweite';
 $('#uncovered-total').textContent=num(M.baseline)+' vorher ausserhalb';
 $('#improvement-bar').style.width=M.baseline>0?(100*M.gain/M.baseline).toFixed(1)+'%':'0%';
 let msg='';const active=M.gain>0;
 if(!S.site)msg='Tippe auf das Studiengebiet, um einen Standort zu setzen.';
 else if(active)msg='+'+M.gain+' Rasterpunkte im angenommene '+S.radius+'-m-Luftlinienradius. Was dies für Menschen bedeutet, ist ungeprüft.';
 else msg='In diesem Modell entsteht hier keine zusätzliche Abdeckung. Teste einen anderen Punkt.';
 $('#narrative').textContent=msg;
 $('#scenario-status').className='scenario-status '+(active?'ready':'warning');
 $('#scenario-status').lastElementChild.textContent=active?'Hypothese verändert · menschliche Prüfung erforderlich':'Keine belegte Verbesserung · Standort weiter prüfen';
 $('#report-coords').textContent=S.site?fmt(S.site.lat)+', '+fmt(S.site.lon):'—';
 $('#report-radius').textContent=S.radius+' m Luftlinie';
 $('#report-gain').textContent=S.site?'+'+M.gain+' von '+M.baseline+' Rasterpunkten':'—';
 $('#gain-value').textContent=S.site?num(M.gain):'—';
 $('#gain-overlay').textContent=S.site?'+'+num(M.gain):'+—';
 const stage=$('#map-stage');stage.classList.toggle('is-before',S.compare==='before');
 $('#view-before').classList.toggle('active',S.compare==='before');
 $('#view-after').classList.toggle('active',S.compare==='after');
 $('#view-before').setAttribute('aria-pressed',String(S.compare==='before'));
 $('#view-after').setAttribute('aria-pressed',String(S.compare==='after'));
 if(S.lastGain!==M.gain && S.interacted && S.compare==='after'){
   const impact=$('.impact-box');impact.classList.remove('just-changed');void impact.offsetWidth;
   impact.classList.add('just-changed');
 }
 S.lastGain=M.gain;
 const rows=empty($('#evidence-triples'));
 const triples=[
 ['rdf:type','ct:ScenarioProposal'],
 ['ct:inStudyArea','ct:kreuzbergStudy2026'],
 ['geo:lat',S.site?S.site.lat.toFixed(6):'—'],
 ['geo:long',S.site?S.site.lon.toFixed(6):'—'],
 ['ct:heatClass',zone?.heat??'unbekannt'],
 ['ct:assumedRadiusMeters',String(S.radius)],
 ['ct:nearestListedFountain',M.nearest?.nearest?.id!=null?'fountain:f'+M.nearest.nearest.id:'—'],
 ['ct:nearestDistanceMeters',M.nearest?Math.round(M.nearest.min)+' m':'—'],
 ['prov:wasDerivedFrom','climate:WFS2022 + water:WFS2026']
 ];
 for(const [k,v] of triples){const row=add(rows,el('div',undefined,'evidence-row'));add(row,el('span',k));add(row,el('span',v))}
 highlightSuggestion();renderMap();
}
function toast(msg){
 const t=$('#toast');t.textContent=msg;t.classList.add('visible');
 window.clearTimeout(toast.timer);toast.timer=window.setTimeout(()=>t.classList.remove('visible'),3200);
}
function pathOf(geo){
 const multipolys=geo.type==='MultiPolygon'?geo.coordinates:geo.type==='Polygon'?[geo.coordinates]:[];
 let out='';
 for(const poly of multipolys)for(const ring of poly){
   if(!ring.length)continue;out+='M'+pointCoord(ring[0][0],ring[0][1]).map(x=>x.toFixed(2)).join(' ');
   for(let j=1;j<ring.length;j++)out+='L'+pointCoord(ring[j][0],ring[j][1]).map(x=>x.toFixed(2)).join(' ');
   out+='Z';
 }
 return out;
}

/* Optional georeferenced map context, © OpenStreetMap contributors.
   The WFS overlays and all calculations are valid even if tiles cannot load.
   Only tiles visible within this viewport are requested, with no prefetching. */
function initBasemap(){
 const host=empty($('#basemap-map'));
 const z=15,scale=Math.pow(2,z);
 const tx=lon=>(lon+180)/360*scale;
 const ty=lat=>(1-Math.asinh(Math.tan(lat*RAD))/Math.PI)/2*scale;
 const lonOf=x=>x/scale*360-180;
 const latOf=y=>Math.atan(Math.sinh(Math.PI*(1-2*y/scale)))/RAD;
 const westLon=B[0]-(left/(METERS_PER_LON*PIX_PER_M));
 const eastLon=B[0]+(W-left)/(METERS_PER_LON*PIX_PER_M);
 const northLat=B[3]+top/(METERS_PER_LAT*PIX_PER_M);
 const southLat=B[3]-(H-top)/(METERS_PER_LAT*PIX_PER_M);
 const xmin=Math.floor(tx(westLon)),xmax=Math.ceil(tx(eastLon));
 const ymin=Math.floor(ty(northLat)),ymax=Math.ceil(ty(southLat));
 for(let x=xmin;x<=xmax;x++)for(let y=ymin;y<=ymax;y++){
   if(x<0||x>=scale||y<0||y>=scale)continue;
   const leftX=xCoord(lonOf(x)),rightX=xCoord(lonOf(x+1));
   const topY=yCoord(latOf(y)),bottomY=yCoord(latOf(y+1));
   const image=add(host,svg('image',{x:leftX,y:topY,width:rightX-leftX,height:bottomY-topY,
    href:'https://tile.openstreetmap.org/'+z+'/'+x+'/'+y+'.png',
    preserveAspectRatio:'none','pointer-events':'none',class:'osm-tile'}));
   // No analytics, API keys, bulk prefetches or cross-origin canvas readback.
 }
 syncBasemap();
}
function syncBasemap(){
 const bg=$('#basemap-map'),front=$('#mission-map');
 if(bg&&front)bg.setAttribute('viewBox',front.getAttribute('viewBox'));
}

function renderMap(){
 const host=empty($('#mission-map'));
 // Crop the decorative horizontal margins on small screens without changing map projection.
 host.setAttribute('viewBox',window.innerWidth<=600?'155 0 410 700':'0 0 720 700');
 syncBasemap();
 const defs=add(host,svg('defs'));
 const tile=add(defs,svg('pattern',{id:'paper-grid',width:42,height:42,patternUnits:'userSpaceOnUse'}));
 add(tile,svg('path',{d:'M42 0H0V42',fill:'none',stroke:'#ABB9BD','stroke-width':'1','stroke-opacity':'.09'}));
 add(host,svg('rect',{width:W,height:H,fill:'url(#paper-grid)'}));
 // Street context is optional and never used in the model.
 const halo=add(host,svg('rect',{x:left,y:top,width:BOXW,height:BOXH,fill:'#FAF8F0','fill-opacity':'.49',stroke:'#9CA6AF','stroke-width':1.5,'stroke-dasharray':'6 7',rx:2}));
 const clip=add(defs,svg('clipPath',{id:'study-clip'}));add(clip,svg('rect',{x:left,y:top,width:BOXW,height:BOXH}));
 const north=add(host,svg('text',{x:left+7,y:top-13,fill:'#647682','font-size':10,'font-weight':'750','letter-spacing':'2'}));north.textContent='STUDY WINDOW';
 const edge=add(host,svg('text',{x:right+7,y:bottom+14,fill:'#83939B','font-size':9,'letter-spacing':'1'}));edge.textContent='BBOX / EPSG:4326';
 if(S.visibleHeat){
   const land=add(host,svg('g',{'clip-path':'url(#study-clip)'}));
   const col={'sehr ungünstig':'#D98471','ungünstig':'#EDB39B','weniger günstig':'#F0D79E','günstig':'#C9DBBB'};
   for(const z of S.zones){
     const p=add(land,svg('path',{d:pathOf(z.g),fill:col[z.heat]??'#D5D5CB','fill-opacity':'.79',stroke:'#F9F3E8','stroke-width':'.95','fill-rule':'evenodd',class:'heat-polygon','pointer-events':'none'}));
     add(p,svg('title')).textContent='Klima-Gesamtbewertung 2022: '+z.heat;
   }
 }
 if(S.visibleReach){
   const pts=add(host,svg('g',{'clip-path':'url(#study-clip)'}));
   // Faint circles around listed fountains are modeled air-line radii, not walkable service areas.
   for(const f of S.fountains){
    const xy=pointCoord(f.lon,f.lat);
    if(Math.abs(xy[0]-W/2)>W/2+120||Math.abs(xy[1]-H/2)>H/2+120)continue;
    add(pts,svg('circle',{cx:xy[0],cy:xy[1],r:S.radius*PIX_PER_M,fill:'#667BC5','fill-opacity':'.045',stroke:'#8D9ED2','stroke-width':'.7','stroke-opacity':'.22','stroke-dasharray':'2 7','pointer-events':'none'}));
   }
 }
 const cells=add(host,svg('g',{'clip-path':'url(#study-clip)'}));
 for(const p of S.heated){
   const baselineUncovered=p.nearest>S.radius,reachable=baselineUncovered&&S.compare==='after'&&S.site&&dist(p,S.site)<=S.radius;
   if(!baselineUncovered&&!reachable)continue;
   const xy=pointCoord(p.lon,p.lat);
   add(cells,svg('circle',{cx:xy[0],cy:xy[1],r:reachable?4.1:2.25,fill:reachable?'#4D58C9':'#A7694F','fill-opacity':reachable?'.92':'.31',stroke:reachable?'#fff': 'none','stroke-width':1.1,class:'sample-dot'}));
 }
 if(S.visibleWater){
   const pts=add(host,svg('g'));
   for(const f of S.fountains){
     const xy=pointCoord(f.lon,f.lat);
     if(xy[0]<0||xy[0]>W||xy[1]<0||xy[1]>H)continue;
     add(pts,svg('circle',{cx:xy[0],cy:xy[1],r:5.3,fill:'#4B5CC8',stroke:'#FFFFFF','stroke-width':2,class:'fountain-dot'}));
     // A dark ring indicates a reported restriction, not a live outage.
     if(f.r)add(pts,svg('circle',{cx:xy[0],cy:xy[1],r:8.4,fill:'none',stroke:'#BA6955','stroke-width':1.2,'stroke-dasharray':'2 2','pointer-events':'none'}));
   }
 }
 if(S.site&&S.compare==='after'){
   const [x,y]=pointCoord(S.site.lon,S.site.lat);
   const proposal=add(host,svg('g',{'pointer-events':'none'}));
   if(S.visibleReach){
    add(proposal,svg('circle',{cx:x,cy:y,r:S.radius*PIX_PER_M,fill:'#545FC8','fill-opacity':'.095',stroke:'#434CC2','stroke-width':2.2,'stroke-dasharray':'8 7',class:'scenario-reach'}));
   }
   add(proposal,svg('circle',{cx:x,cy:y,r:22,fill:'#4557C6','fill-opacity':'.16'}));
   add(proposal,svg('circle',{cx:x,cy:y,r:10,fill:'#E78A72',stroke:'#FFFEFA','stroke-width':3}));
   add(proposal,svg('circle',{cx:x,cy:y,r:3.3,fill:'#FFFFFF'}));
   const hit=add(host,svg('circle',{id:'candidate-hit',cx:x,cy:y,r:23,fill:'transparent',role:'button',tabindex:0,class:'candidate-marker', 'aria-label':'Vorgeschlagenen Trinkbrunnen ziehen oder mit Pfeiltasten um 30 Meter bewegen'}));
   hit.addEventListener('keydown',e=>{
     if(!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key))return;
     e.preventDefault();
     const delta=30, dlon=delta/METERS_PER_LON,dlat=delta/METERS_PER_LAT;
     const n={...S.site};
     if(e.key==='ArrowRight')n.lon+=dlon;if(e.key==='ArrowLeft')n.lon-=dlon;
     if(e.key==='ArrowUp')n.lat+=dlat;if(e.key==='ArrowDown')n.lat-=dlat;
     setSite(n,'keyboard');$('#candidate-hit')?.focus();
   });
   const label=add(host,svg('text',{x:Math.max(80,Math.min(W-80,x)),y:y-31,fill:'#3B47A8','font-weight':850,'font-size':12,'text-anchor':'middle','pointer-events':'none'}));label.textContent='DEIN BRUNNEN ✳';
 }
 const bar=$('.scale-mark');if(bar){
   const bounds=host.getBoundingClientRect(),view=host.viewBox.baseVal;
   const zoom=Math.min(bounds.width/view.width,bounds.height/view.height);
   bar.style.width=(200*PIX_PER_M*zoom).toFixed(1)+'px';
 }
 $('#scale-caption').textContent='200 m';
}
function svgPoint(evt){
 const host=$('#mission-map'),rect=host.getBoundingClientRect(),view=host.viewBox.baseVal;
 if(!rect.width||!rect.height)return null;
 // Account for the actual dynamic viewBox and preserveAspectRatio letterboxing.
 const ratio=Math.min(rect.width/view.width,rect.height/view.height);
 const ox=(rect.width-view.width*ratio)/2,oy=(rect.height-view.height*ratio)/2;
 return {x:view.x+(evt.clientX-rect.left-ox)/ratio,y:view.y+(evt.clientY-rect.top-oy)/ratio};
}
let resizeRaf=0;
window.addEventListener('resize',()=>{window.cancelAnimationFrame(resizeRaf);resizeRaf=requestAnimationFrame(()=>{if(S.loaded)renderMap()});});
const canvas=$('#mission-map');
canvas.addEventListener('pointerdown',e=>{
 if(!S.loaded||!(e.isPrimary??true)||e.button>0)return;
 const p=svgPoint(e);if(!p)return;
 if(p.x<left||p.x>right||p.y<top||p.y>bottom){toast('Standort bitte innerhalb des hervorgehobenen Studiengebiets setzen.');return;}
 e.preventDefault();
 if(S.compare==='before'){S.compare='after';}
 S.dragging=e.pointerId;
 S.dragStart=S.site?{...S.site}:null;
 try{canvas.setPointerCapture(e.pointerId)}catch{}
 setSite(invXY(p.x,p.y),'map-place');
});
canvas.addEventListener('pointermove',e=>{
 if(S.dragging!==e.pointerId||!S.loaded)return;
 const p=svgPoint(e);if(!p)return;
 setSite(invXY(p.x,p.y),'map-drag',false);
});
function endDrag(e){if(S.dragging!==e.pointerId)return;S.dragging=null;record('map-drag-complete');updateModel();try{canvas.releasePointerCapture(e.pointerId)}catch{}}
canvas.addEventListener('pointerup',endDrag);
canvas.addEventListener('pointercancel',e=>{if(S.dragging!==e.pointerId)return;S.dragging=null;if(S.dragStart){S.site=S.dragStart;record('drag-cancelled');updateModel();}try{canvas.releasePointerCapture(e.pointerId)}catch{}});
$('#layer-heat').addEventListener('change',e=>{S.visibleHeat=e.target.checked;renderMap()});
$('#layer-water').addEventListener('change',e=>{S.visibleWater=e.target.checked;renderMap()});
$('#layer-reach').addEventListener('change',e=>{S.visibleReach=e.target.checked;renderMap()});
$('#radius').addEventListener('input',e=>{
 S.radius=Number(e.target.value);
 if(!S.loaded){$('#radius-label').textContent=S.radius+' m';return;}
 pickSuggestions();record('radius-changed');updateModel();
});
function openEvidence(scrollToMethod=false){
 const d=$('#evidence');if(!d.open)d.showModal();
 if(scrollToMethod)requestAnimationFrame(()=>$('#methodology-note').scrollIntoView({behavior:'smooth',block:'center'}));
}
$('#about-metric').addEventListener('click',()=>openEvidence(true));
$('#read-method').addEventListener('click',()=>openEvidence(true));
$('#jump-evidence').addEventListener('click',()=>openEvidence(false));
$('#close-evidence').addEventListener('click',()=>$('#evidence').close());
$('#evidence').addEventListener('click',e=>{if(e.target===$('#evidence'))$('#evidence').close()});
$('#dismiss-tip').addEventListener('click',()=>{$('#map-guidance').classList.add('hidden');});
function compare(mode){
 S.compare=mode;record('compare-'+mode);
 $('#map-stage').classList.toggle('is-before',mode==='before');
 $('#view-before').classList.toggle('active',mode==='before');$('#view-after').classList.toggle('active',mode==='after');
 $('#view-before').setAttribute('aria-pressed',String(mode==='before'));
 $('#view-after').setAttribute('aria-pressed',String(mode==='after'));
 renderMap();
}
$('#view-before').addEventListener('click',()=>compare('before'));
$('#view-after').addEventListener('click',()=>compare('after'));
document.addEventListener('keydown',e=>{
 if(e.key==='Escape')$('#layers-menu').open=false;
});
document.addEventListener('click',e=>{const d=$('#layers-menu');if(d.open&&!d.contains(e.target))d.open=false});
$('#reset-scenario').addEventListener('click',()=>{
 S.radius=300;S.compare='after';$('#radius').value='300';S.site=S.suggestions[0]??null;
 record('reset');pickSuggestions();if(!S.site&&S.suggestions.length)S.site=S.suggestions[0];
 updateModel();toast('Szenario zurückgesetzt.');
});

$('#review-checkbox').addEventListener('change',e=>{S.review=e.target.checked;$('#review-hint').classList.remove('error');record(e.target.checked?'human-reviewed-disclaimer':'review-unchecked');$('#review-hint').textContent=e.target.checked?'✓ Kenntnisnahme im Browser protokolliert. Keine Einreichung, kein offizieller Freigabeschritt.':'Ein Mensch muss diesen Vorschlag beurteilen. Der Bericht wird ausschliesslich lokal erstellt und nirgendwo eingereicht.'});
function scenarioUrl(){
 const u=new URL(location.href);u.searchParams.delete('lon');u.searchParams.delete('lat');u.searchParams.delete('radius');
 if(S.site){u.searchParams.set('lon',S.site.lon.toFixed(6));u.searchParams.set('lat',S.site.lat.toFixed(6));}
 u.searchParams.set('radius',String(S.radius));u.hash='mission-workbench';return u.toString();
}
function reportMarkdown(){
 const M=S.model;
 const site=S.site;
 const now=new Date().toISOString();
 const answer=[
 '# CITY THREAD v0.5 | THE MISSING FOUNTAIN',
 '',
 '**Unabhängiger, hypothetischer Untersuchungsentwurf – keine Bauempfehlung und keine Einreichung.**',
 '',
 'Erstellt: '+now,
 'Studienfenster Kreuzberg/Umgebung: 13.385–13.407° E, 52.490–52.512° N',
 'Standort: '+(site?site.lat.toFixed(6)+', '+site.lon.toFixed(6):'keiner'),
 'Annahme: '+S.radius+' m Luftlinie, gleichmässiges 90-m-Raster',
 'Klimaklasse am Vorschlag (2022): '+(M.zone?.heat??'nicht im bewerteten Siedlungspolygon'),
 'Nächster inventarisierter Trinkbrunnen: '+(M.nearest?Math.round(M.nearest.min)+' m Luftlinie, WFS-ID '+M.nearest.nearest.id:'unbekannt'),
 '',
 '## Modellvergleich (nur Rasterpunkte)',
 '- Insgesamt '+M.samples+' Rasterpunkte fallen auf bewertete Siedlungsflächen im Studienfenster.',
 '- Davon '+M.total+' Rasterpunkte in Klassen ungünstig / sehr ungünstig (Gesamtbewertung 2022).',
 '- Vorher ohne inventarisierten Brunnen in '+S.radius+' m Luftlinie: '+M.baseline,
 '- Mit vorgeschlagenem Brunnen vorher ausserhalb: '+M.after,
 '- Zusätzlich im hypothetischen Radius: '+M.gain+' Rasterpunkte.',
 '',
 'Diese Punkte sind keine Einwohnerzahlen, keine gemessenen Temperaturveränderungen und keine überprüften Fussweg- oder Versorgungseffekte.',
 'Alle 242 WFS-Inventarstandorte zählen als vorhandene Punkte. Betriebsbereitschaft nicht verifiziert.',
 '',
 '## Wie berechnet?',
 '1. 154 Siedlungs-Klimapolygone, WFS BBOX vollständig paginiert (2022), räumlich auf das Studienfenster beschränkt.',
 '2. 90-m-Rasterpunkte auf Flächen, für die eine Polygon-Zuordnung gelingt (Point-in-Polygon, WGS84).',
 '3. Hitzeklassen ungünstig / sehr ungünstig nach phk_gesamt selektiert.',
 '4. Kürzester Abstand zu allen 242 inventarisierten Trinkbrunnen (Haversine/Luftlinie).',
 '5. Szenario erweitert den Vergleich um einen hypothetischen neuen Brunnen.',
 '',
 '## Nicht nachgewiesen und vor Entscheidung zu prüfen',
 '- Vor-Ort-Betriebsstatus der inventarisierten Brunnen, Erreichbarkeit über Fusswege, barrierefreie Zugänge.',
 '- Standortverfügbarkeit, öffentliches und privates Eigentum, Genehmigungen und zuständige Fachstellen.',
 '- Wasseranschluss, Unterhalt, Baukosten und alternative Klimaanpassungsmassnahmen.',
 '- Bevölkerungs- und Nutzungsdaten, Bedarfsentwicklung, Gerechtigkeits- und Verteilungseffekte.',
 '- Validierung mit aktuellen Informationen, Originalgeometrien und lokaler Kenntnis.',
 '',
 '## Datenquellen (Lizenz dl-de-zero-2.0)',
 '1. Trinkwasserbrunnen Berlin, WFS · Abruf 2026-10-09 · https://daten.berlin.de/datensaetze/trinkwasserbrunnen-wfs-47dba2c3',
 '2. Planungshinweiskarten Stadtklima 2022 · WFS-Polygone · Abruf 2026-10-09 · https://daten.berlin.de/datensaetze/klimabewertungskarten-2022-umweltatlas-wfs-ac0751a2',
 '3. Materialisiertes semantisches RDF-Modell: https://mikelninh.github.io/COMMONS/city-thread/mission.ttl',
 '',
 'Human-review acknowledgement in browser: '+(S.review?'yes (not official approval)':'no'),
 'Teilbares Szenario: '+scenarioUrl(),
 '',
 '### Lokale Interaktionen (nicht persistent)',
 ...S.history.slice(-15).map(h=>'- '+h.at+' | '+h.action+' | '+h.radius+' m'+(h.site?' | '+h.site.lat+','+h.site.lon:'')),
 '',
 'Created as a public civic AI learning exercise. Not a product of DKSR/CIVORA or Berlin.'
 ];
 return answer.join('\n');
}
$('#download-report').addEventListener('click',()=>{
 if(!S.loaded||!S.model||!S.site){toast('Bitte zuerst einen Standort wählen.');return}
 if(!S.review){$('#review-hint').textContent='Bitte zuerst bestätigen: Dies ist ein hypothetisches Szenario, keine Bauempfehlung.';$('#review-hint').classList.add('error');$('#review-checkbox').focus();return}
 record('report-generated');
 const data=reportMarkdown(),blob=new Blob([data],{type:'text/markdown;charset=utf-8'});
 const a=el('a');a.href=URL.createObjectURL(blob);a.download='city-thread-standortpruefung-v04.md';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
 $('#review-hint').textContent='✓ Dein Prüfprotokoll wurde lokal erstellt. Es wurde nichts an Behörden übermittelt.';
});
async function copyText(text){
 try{await navigator.clipboard.writeText(text);return true}catch{window.prompt('Link kopieren:',text);return false}
}
$('#copy-scenario').addEventListener('click',async()=>{if(!S.loaded){toast('Lade erst die Quelldaten.');return}record('scenario-link-copied');if(await copyText(scenarioUrl()))toast('Szenario-Link kopiert ✳')});
$('#share-mission').addEventListener('click',async()=>{if(await copyText(S.loaded?scenarioUrl():location.href))toast('Link kopiert ✳')});
function parseLink(){
 const q=new URLSearchParams(location.search),r=Number(q.get('radius'));
 if(Number.isFinite(r)&&r>=150&&r<=500&&r%50===0){S.radius=r;$('#radius').value=String(r)}
 const lon=Number(q.get('lon')),lat=Number(q.get('lat'));
 if(q.has('lon')&&q.has('lat')&&Number.isFinite(lon)&&Number.isFinite(lat)&&inWindow({lon,lat}))return {lon,lat};
 return null;
}
function loadError(error){
 console.error('Failed to load source data',error);
 S.loaded=false;
 const box=$('#scenario-status');box.className='scenario-status error';box.lastElementChild.textContent='Keine Daten verfügbar. Keine Berechnung möglich.';
 $('#map-data-status').textContent='QUELLE NICHT VERFÜGBAR';
 $('#narrative').textContent='Wir behaupten ohne Quelldaten keine Verbesserung. Bitte die Seite später erneut laden.';
 empty($('#suggestion-buttons')).appendChild(el('p','Datenabruf fehlgeschlagen.','loading'));
 $('#download-report').disabled=true;
}
async function boot(){
 try{
   const waterFiles=[0,1,2,3].map(i=>'../fountains-all-'+i+'.json');
   const heatFiles=[0,1,2,3].map(i=>'../heat-'+i+'.json');
   const urls=[...waterFiles,...heatFiles];
   const files=await Promise.all(urls.map(async u=>{
      const response=await fetch(u,{cache:'no-store'});if(!response.ok)throw Error(u+' '+response.status);return response.json();
   }));
   const waters=files.slice(0,4),heats=files.slice(4);
   if(!waters.every(d=>d.matched===242)||!heats.every(d=>d.totalMatched===154))throw Error('Source WFS metadata mismatch');
   const f=waters.flatMap(d=>d.records),zones=heats.flatMap(d=>d.features);
   if(f.length!==242||new Set(f.map(x=>x.id)).size!==242||zones.length!==154||new Set(zones.map(z=>z.id)).size!==154)
     throw Error('Paginated dataset incomplete or contains duplicate IDs');
   if(!f.every(p=>Number.isFinite(p.lon)&&Number.isFinite(p.lat)&&p.n&&p.d)||!zones.every(z=>z.g&&z.heat&&z.id))
     throw Error('Malformed WFS snapshot');
   S.fountains=f;S.zones=zones;S.loaded=true;
   makeGrid();initBasemap();const fromLink=parseLink();
   pickSuggestions();
   S.site=fromLink??(S.suggestions[0]?{lon:S.suggestions[0].lon,lat:S.suggestions[0].lat}:null);
   record(fromLink?'shared-scenario-loaded':'initial-demo-suggestion');
   updateModel();
   $('#map-data-status').textContent='242 STANDORTE / 154 POLYGONE · WFS-SNAPSHOT';
   $('#scenario-status').classList.add('ready');
   if(location.hash==='#mission-workbench')setTimeout(()=>$('#mission-workbench').scrollIntoView({block:'start'}),200);
   // No request modifies live WFS, and the only generated output is a local Markdown file.
 }catch(error){loadError(error)}
}
boot();
})();
