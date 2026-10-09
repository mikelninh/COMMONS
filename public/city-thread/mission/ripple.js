/* CITY THREAD v0.6 · THE RIPPLE / Scenario Duel
 * Interaction-only module. It never invents observations or alters the WFS inputs.
 * A and B are each scored independently against the SAME inventoried-fountain baseline.
 * Lines terminate exclusively at actually modeled sample-grid points in range.
 * Sound is off by default, motion respects prefers-reduced-motion.
 */
(function(){
 'use strict';
 window.CityThreadRipple = function initRipple(ctx){
   const {S,model,dist,svg,add,pointCoord,PIX_PER_M,updateModel,record,toast,inWindow} = ctx;
   const byId=id=>document.getElementById(id);
   const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
   const DEEP='#505BCC',WARM='#EA8F78';
   let A=null,B=null,enabled=false,active='A',pulseAt=0,feedbackTimer=0,audioCtx=null,soundOn=false;
   const same=p=>p&&Number.isFinite(p.lon)&&Number.isFinite(p.lat)&&inWindow(p);
   const copy=p=>p?{lat:p.lat,lon:p.lon}:null;
   const score=p=>p?model(p).gain:null;
   const winnerText=(a,b)=>{
     if(a==null||b==null)return 'Wähle zwei Standorte, um ihre Modellwerte zu vergleichen.';
     const n=Math.abs(a-b);
     if(n===0)return 'Gleichstand: beide Positionen erreichen gleich viele zusätzliche Modellpunkte.';
     return (a>b?'A':'B')+' erreicht '+n+' Rasterpunkt'+(n===1?'':'e')+' mehr als '+(a>b?'B':'A')+' – im Modell, nicht in der Realität.';
   };
   const el=(tag,text)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;return x};
   function present(){
     const board=byId('duel-board'),button=byId('duel-toggle');
     if(!board||!button)return;
     board.hidden=!enabled;button.setAttribute('aria-pressed',String(enabled));
     button.querySelector('span').textContent=enabled?'↖':'↗';
     button.firstChild.textContent=enabled?'Duell beenden ':'Zweiten Ort vergleichen ';
     const buttons={A:byId('duel-a'),B:byId('duel-b')};
     for(const name of ['A','B']){
       const b=buttons[name];
       b.classList.toggle('active',enabled&&active===name);
       b.setAttribute('aria-pressed',String(enabled&&active===name));
       b.disabled=!enabled;
       const count=score(name==='A'?A:B);
       byId('duel-score-'+name.toLowerCase()).textContent=count==null?'—':'+'+count;
     }
     byId('duel-verdict').textContent=winnerText(score(A),score(B));
     const slotText=enabled?'Standort '+active+' bearbeiten':'Einzelner Standort';
     byId('duel-heading').setAttribute('aria-label','Scenario Duel · '+slotText);
   }
   function transient(text){
     const wrap=byId('ripple-message'),target=byId('ripple-message-text');
     if(!wrap||!target||reduced.matches)return;
     target.textContent=text;wrap.hidden=false;wrap.classList.remove('ripple-show');
     void wrap.offsetWidth;wrap.classList.add('ripple-show');
     clearTimeout(feedbackTimer);
     feedbackTimer=window.setTimeout(()=>{wrap.classList.remove('ripple-show');wrap.hidden=true},1550);
   }
   function pulse(reason){
     pulseAt=performance.now();
     if(soundOn)playTone();
     if(S.model?.gain!=null)transient('+'+S.model.gain+' echte Rasterpunkte im Modell erreicht');
   }
   function toggleDuel(){
     if(!S.loaded){toast('Die Quelldaten müssen erst laden.');return}
     enabled=!enabled;
     if(enabled){
       A=copy(A??S.site);
       B=copy(B??S.suggestions.find(p=>!A||dist(p,A)>380)??S.suggestions[1]??S.suggestions[0]??A);
       active='B';
       S.site=copy(B);
       S.compare='after';
       record('duel-on');
       S.interacted=true;
       byId('map-guidance')?.classList.add('hidden');
     }else{
       S.site=copy(A??S.site);
       active='A';S.compare='after';
       record('duel-off');
     }
     updateModel();pulse('duel');
   }
   function selectSlot(slot){
     if(!enabled||!['A','B'].includes(slot))return;
     active=slot;
     S.site=copy(slot==='A'?A:B);
     S.compare='after';
     record('duel-select-'+slot);
     updateModel();
   }
   function onPlace(p,action){
     if(!p)return;
     if(enabled&&active==='B')B=copy(p);
     else A=copy(p);
     if(action!=='map-place'&&action!=='map-drag')pulseAt=performance.now();
   }
   function onRelease(){
     if(!S.loaded||!S.site)return;
     pulse('release');
   }
   function onModelChange(){
     if(!S.loaded)return;
     if(!A&&S.site)A=copy(S.site);
     if(enabled){
       if(active==='A'&&S.site)A=copy(S.site);
       if(active==='B'&&S.site)B=copy(S.site);
     }else if(S.site){A=copy(S.site);}
     present();
   }
   function activeColor(){return enabled&&active==='B'?DEEP:WARM}
   function activeMapLabel(){return enabled?'STANDORT '+active+' ✳':'DEIN BRUNNEN ✳'}
   const svgText=(host,value,attrs)=>{const t=add(host,svg('text',attrs));t.textContent=value;return t};
   function drawConnections(host){
     if(S.compare!=='after'||!S.site||!S.model?.newly?.length)return;
     const p=pointCoord(S.site.lon,S.site.lat);
     const group=add(host,svg('g',{class:'ripple-threads','pointer-events':'none'}));
     const isBurst=!reduced.matches&&(performance.now()-pulseAt<800);
     // Visualise a max of 46 genuine reached samples, not an invented population.
     // The metric counts ALL newly reached sample-grid points, not just drawn threads.
     const arr=[...S.model.newly].sort((a,b)=>dist(a,S.site)-dist(b,S.site)).slice(0,46);
     arr.forEach((q,i)=>{
       const xy=pointCoord(q.lon,q.lat);
       const line=svg('line',{x1:p[0].toFixed(2),y1:p[1].toFixed(2),
         x2:xy[0].toFixed(2),y2:xy[1].toFixed(2),
         class:'ripple-thread'+(isBurst?' firing':''),
         style:'--delay:'+Math.min(i*15,450)+'ms','stroke':activeColor()});
       add(group,line);
     });
     if(isBurst){
       const r=Math.min(S.radius*PIX_PER_M,350);
       const wave=add(group,svg('circle',{cx:p[0],cy:p[1],r,
          fill:'none',stroke:activeColor(),'stroke-width':3,
          class:'ripple-wave',
          style:'transform-origin:'+p[0].toFixed(1)+'px '+p[1].toFixed(1)+'px'}));
     }
   }
   function drawOther(host){
     if(!enabled||S.compare!=='after')return;
     const other=active==='A'?B:A,slot=active==='A'?'B':'A';
     if(!other)return;
     const [x,y]=pointCoord(other.lon,other.lat);
     const g=add(host,svg('g',{'class':'duel-ghost'}));
     add(g,svg('circle',{cx:x,cy:y,r:S.radius*PIX_PER_M,fill:'none',stroke:slot==='A'?WARM:DEEP,
       'stroke-width':1.4,'stroke-dasharray':'4 10','stroke-opacity':'.38','pointer-events':'none'}));
     add(g,svg('circle',{cx:x,cy:y,r:17,fill:slot==='A'?WARM:DEEP,
       stroke:'#FFFEFB','stroke-width':3,opacity:'.78','pointer-events':'none'}));
     svgText(g,slot,{x,y:y+5,'text-anchor':'middle','font-size':13,
       'font-weight':850,fill:'#FFFFFF','pointer-events':'none'});
     const hit=add(g,svg('circle',{cx:x,cy:y,r:24,fill:'transparent',role:'button',tabindex:'0',
       'aria-label':'Standort '+slot+' zum Bearbeiten auswählen',class:'duel-other-hit'}));
     hit.addEventListener('pointerdown',e=>e.stopPropagation());
     hit.addEventListener('click',e=>{e.stopPropagation();selectSlot(slot)});
     hit.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectSlot(slot)}});
   }
   function restoreFromUrl(){
     const q=new URLSearchParams(location.search);
     if(q.get('duel')!=='1')return;
     const from=(prefix)=>{
       const lon=Number(q.get(prefix+'Lon')),lat=Number(q.get(prefix+'Lat'));
       return q.has(prefix+'Lon')&&q.has(prefix+'Lat')&&same({lon,lat})?{lon,lat}:null;
     };
     const a=from('a'),b=from('b');
     if(!a||!b)return;
     A=a;B=b;active=q.get('slot')==='A'?'A':'B';enabled=true;
     S.site=copy(active==='A'?A:B);S.compare='after';
     present();
   }
   function addQueryParams(u){
     for(const name of ['duel','aLon','aLat','bLon','bLat','slot'])u.searchParams.delete(name);
     if(enabled&&A&&B){
       u.searchParams.set('duel','1');
       u.searchParams.set('aLon',A.lon.toFixed(6));u.searchParams.set('aLat',A.lat.toFixed(6));
       u.searchParams.set('bLon',B.lon.toFixed(6));u.searchParams.set('bLat',B.lat.toFixed(6));
       u.searchParams.set('slot',active);
     }
   }
   function reportLines(){
     if(!enabled)return [];
     const a=score(A),b=score(B);
     return ['','## Scenario Duel – unabhängiger Vergleich','Beide Vorschläge nutzen dieselbe Ausgangslage und denselben angenommenen Radius.',
       'A: '+(A?A.lat.toFixed(6)+', '+A.lon.toFixed(6):'fehlt')+' | +'+(a??'—')+' neue Modellpunkte.',
       'B: '+(B?B.lat.toFixed(6)+', '+B.lon.toFixed(6):'fehlt')+' | +'+(b??'—')+' neue Modellpunkte.',
       winnerText(a,b),
       'Wichtig: Unterschiedliche Rasterpunktzahlen belegen keine Standortgenehmigung oder einen realen Versorgungsnutzen.',
       ''];
   }
   function reset(){
     enabled=false;active='A';B=null;A=null;pulseAt=0;present();
   }
   function playTone(){
     try{
       const Audio=window.AudioContext||window.webkitAudioContext;
       if(!Audio)return;
       audioCtx??=new Audio();
       if(audioCtx.state==='suspended')audioCtx.resume();
       const now=audioCtx.currentTime;
       for(const [hz,delay] of [[523.25,0],[783.99,.075]]){
         const o=audioCtx.createOscillator(),gain=audioCtx.createGain();
         o.type='sine';o.frequency.value=hz;gain.gain.setValueAtTime(.0001,now+delay);
         gain.gain.exponentialRampToValueAtTime(.033,now+delay+.022);
         gain.gain.exponentialRampToValueAtTime(.0001,now+delay+.3);
         o.connect(gain).connect(audioCtx.destination);o.start(now+delay);o.stop(now+delay+.32);
       }
     }catch(e){soundOn=false}
   }
   const soundButton=byId('ripple-sound');
   if(soundButton)soundButton.addEventListener('click',()=>{
     soundOn=!soundOn;
     soundButton.setAttribute('aria-pressed',String(soundOn));
     soundButton.setAttribute('aria-label','Ton '+(soundOn?'einschalten':'ausschalten'));
     soundButton.textContent=soundOn?'♪ An':'♪ Aus';
     if(soundOn)playTone();
   });
   byId('duel-toggle').addEventListener('click',toggleDuel);
   byId('duel-a').addEventListener('click',()=>selectSlot('A'));
   byId('duel-b').addEventListener('click',()=>selectSlot('B'));
   present();
   return {onPlace,onRelease,onModelChange,drawConnections,drawOther,activeColor,activeMapLabel,
       restoreFromUrl,addQueryParams,reportLines,reset,isEnabled:()=>enabled,
       getState:()=>({enabled,active,A:copy(A),B:copy(B),aGain:score(A),bGain:score(B)})};
 };
})();