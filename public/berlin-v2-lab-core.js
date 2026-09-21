(() => {
'use strict';
const $=id=>document.getElementById(id),qsa=s=>[...document.querySelectorAll(s)];
const V=window.V2={$,qsa,pulse:null,history:{snapshots:[]},map:null,pickMode:null,pointA:null,pointB:null,discoveryIndex:0};
V.concepts={layouts:'Layouts',discover:'Discovery home',why:'Why Here',compare:'Compare',time:'Time Machine',lab:'Hypothesis Lab',share:'Share Studio'};
V.shares={pulse:{label:'City Pulse',title:'The city is warming.'},discovery:{label:'Discovery',title:'Air is cleaner than usual.'},here:{label:'Why Here',title:'This place, in context.'},compare:{label:'Compare',title:'Same city. Different conditions.'},daily:{label:'Daily Berlin',title:'One thing changed. Two stayed quiet.'}};
V.selectedLayout=localStorage.getItem('commons-v2-layout')||'editorial';
try{V.ratings=JSON.parse(localStorage.getItem('commons-v2-ratings')||'{}')}catch{V.ratings={}}
V.note=localStorage.getItem('commons-v2-note')||'';
V.finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
V.fmt=(v,d=1)=>V.finite(v)?Number(v).toFixed(d):'—';
V.signed=(v,d=1)=>V.finite(v)?`${Number(v)>=0?'+':''}${Number(v).toFixed(d)}`:'—';
V.esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
V.localTime=v=>v?new Date(v).toLocaleString('en-GB',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Berlin'}):'—';
V.getJSON=async(url,timeout=9000)=>{const c=new AbortController(),t=setTimeout(()=>c.abort(),timeout);try{const r=await fetch(url,{cache:'no-store',signal:c.signal});if(!r.ok)throw Error('HTTP '+r.status);return await r.json()}finally{clearTimeout(t)}};
V.copy=async v=>{try{await navigator.clipboard.writeText(v)}catch{const t=document.createElement('textarea');t.value=v;document.body.append(t);t.select();document.execCommand('copy');t.remove()}};

V.loadData=async()=>{const[p,h]=await Promise.allSettled([V.getJSON('./data/berlin-pulse/latest.json?t='+Date.now()),V.getJSON('./data/berlin-pulse/history.json?t='+Date.now())]);if(p.status==='fulfilled')V.pulse=p.value;if(h.status==='fulfilled')V.history=h.value};

V.bootMap=async()=>{try{const lib=await import('./vendor/maplibre-6.10.0/maplibre-gl.mjs');lib.setWorkerUrl(new URL('./vendor/maplibre-6.10.0/maplibre-gl-worker.mjs',location.href).href);V.map=new lib.Map({container:'labMap',style:'https://tiles.openfreemap.org/styles/liberty',center:[13.405,52.52],zoom:10.15,pitch:42,bearing:-10,antialias:true,attributionControl:true});V.map.on('load',()=>{$('labMapStatus').textContent='MAP · LIVE';V.map.addSource('lab-points',{type:'geojson',data:{type:'FeatureCollection',features:[]}});V.map.addLayer({id:'lab-points',type:'circle',source:'lab-points',paint:{'circle-radius':['match',['get','kind'],'why',8,6],'circle-color':['match',['get','kind'],'A','#74d7ff','B','#ffd36a','#ffffff'],'circle-stroke-width':3,'circle-stroke-color':'rgba(185,255,112,.35)'}})});V.map.on('click',e=>{if(!V.pickMode)return;const p={lon:e.lngLat.lng,lat:e.lngLat.lat},m=V.pickMode;V.finishPick();if(m==='why'){V.setPoint('why',p);window.V2App.inspectWhy(p)}else if(m==='A'){V.pointA=p;V.setPoint('A',p);window.V2App.loadCompare('A',p)}else{V.pointB=p;V.setPoint('B',p);window.V2App.loadCompare('B',p)}})}catch{$('labMapStatus').textContent='MAP · FALLBACK'}};

V.points=(kind,p)=>{const f=[];if(V.pointA&&kind!=='A')f.push({type:'Feature',properties:{kind:'A'},geometry:{type:'Point',coordinates:[V.pointA.lon,V.pointA.lat]}});if(V.pointB&&kind!=='B')f.push({type:'Feature',properties:{kind:'B'},geometry:{type:'Point',coordinates:[V.pointB.lon,V.pointB.lat]}});if(p)f.push({type:'Feature',properties:{kind},geometry:{type:'Point',coordinates:[p.lon,p.lat]}});return f};
V.setPoint=(kind,p)=>{if(V.map?.getSource('lab-points'))V.map.getSource('lab-points').setData({type:'FeatureCollection',features:V.points(kind,p)});V.map?.easeTo({center:[p.lon,p.lat],zoom:11.7,duration:600})};
V.clearPoints=()=>{if(V.map?.getSource('lab-points'))V.map.getSource('lab-points').setData({type:'FeatureCollection',features:[]})};

V.showView=v=>{qsa('#labNav [data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===v));qsa('.lab-view').forEach(p=>p.classList.toggle('active',p.dataset.panel===v));V.cancelPick()};
V.applyLayout=v=>{V.selectedLayout=v;localStorage.setItem('commons-v2-layout',v);document.body.classList.remove('layout-editorial','layout-cinematic','layout-observatory');document.body.classList.add('layout-'+v);qsa('[data-layout]').forEach(c=>c.classList.toggle('selected',c.dataset.layout===v));V.renderPicks();if(V.map){const c={editorial:[13.405,52.52,10.15,42,-10],cinematic:[13.405,52.52,9.85,58,-18],observatory:[13.405,52.52,10.45,25,0]}[v];V.map.easeTo({center:c.slice(0,2),zoom:c[2],pitch:c[3],bearing:c[4],duration:650})}};

V.renderFeedback=()=>{qsa('.lab-feedback').forEach(box=>box.querySelectorAll('button').forEach(b=>b.classList.toggle('selected',V.ratings[box.dataset.feedbackFor]===b.dataset.rating)));$('labPickCount').textContent=Object.keys(V.ratings).length};
V.renderPicks=()=>{const n={editorial:'Editorial Pulse',cinematic:'Cinematic Explorer',observatory:'City Observatory'};let h=`<div class="picks-row"><span>Overall shell</span><b>${n[V.selectedLayout]}</b></div>`;for(const[k,v]of Object.entries(V.concepts))h+=`<div class="picks-row"><span>${V.esc(v)}</span><b>${V.esc(V.ratings[k]||'unrated')}</b></div>`;$('picksSummary').innerHTML=h;$('labPickCount').textContent=Object.keys(V.ratings).length};
V.startPick=(m,title,copy)=>{V.pickMode=m;$('mapPickTitle').textContent=title;$('mapPickCopy').textContent=copy;$('mapPickBanner').classList.remove('hidden');qsa('.experience-card').forEach(c=>c.style.opacity='.2');if(V.map)V.map.getCanvas().style.cursor='crosshair'};
V.finishPick=()=>{V.pickMode=null;$('mapPickBanner').classList.add('hidden');qsa('.experience-card').forEach(c=>c.style.opacity='');if(V.map)V.map.getCanvas().style.cursor=''};
V.cancelPick=()=>{if(V.pickMode)V.finishPick()};

function init(){
qsa('#labNav [data-view]').forEach(b=>b.addEventListener('click',()=>V.showView(b.dataset.view)));
qsa('[data-try-layout]').forEach(b=>b.addEventListener('click',()=>{V.applyLayout(b.dataset.tryLayout);V.showView('discover')}));
qsa('.lab-feedback').forEach(box=>{const k=box.dataset.feedbackFor;box.innerHTML=['love','maybe','no'].map(r=>`<button type="button" data-rating="${r}">${r==='love'?'Love':r==='maybe'?'Maybe':'Nope'}</button>`).join('');box.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{V.ratings[k]=b.dataset.rating;localStorage.setItem('commons-v2-ratings',JSON.stringify(V.ratings));V.renderFeedback();V.renderPicks()}))});
$('labPicksButton').addEventListener('click',()=>{$('picksDrawer').classList.remove('hidden');V.renderPicks()});$('closePicks').addEventListener('click',()=>$('picksDrawer').classList.add('hidden'));$('overallNote').value=V.note;$('overallNote').addEventListener('input',()=>{V.note=$('overallNote').value;localStorage.setItem('commons-v2-note',V.note)});$('copyFeedback').addEventListener('click',async()=>{const n={editorial:'Editorial Pulse',cinematic:'Cinematic Explorer',observatory:'City Observatory'},lines=['BERLIN DEEP CITY V2 FEEDBACK','Layout: '+n[V.selectedLayout],...Object.entries(V.concepts).map(([k,v])=>`${v}: ${V.ratings[k]||'unrated'}`),V.note?`Overall note: ${V.note}`:''].filter(Boolean);await V.copy(lines.join('\n'));$('copyStatus').textContent='Copied — paste it back into our chat.'});
$('cancelMapPick').addEventListener('click',V.cancelPick);
V.applyLayout(V.selectedLayout);V.renderFeedback();
Promise.allSettled([V.loadData(),V.bootMap()]).then(()=>window.V2App?.renderAll());
}
init();
})();