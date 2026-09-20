const $=id=>document.getElementById(id);
const ACTION_KEY="commons.impact.actions.v0.3";
let impactReport=null;
let liveBrief=null;

const placeMeta={
  nuwakot:{pin:[39,38],scene:"mountain valleys",accent:"#b6ff69"},
  manila:{pin:[69,53],scene:"coastal megacity",accent:"#6dc8ff"},
  delhi:{pin:[58,42],scene:"dense inland city",accent:"#ffd56a"}
};

function pct(v){const n=Number(v);return Number.isFinite(n)?Math.round(n*100)+"%":"—"}
function human(v){const n=Number(v);if(!Number.isFinite(n))return "—";if(n>=1e6)return (n/1e6).toFixed(1)+"M";if(n>=1e3)return Math.round(n/1e3)+"k";return Math.round(n)}
async function getJson(url){const r=await fetch(url,{cache:"no-store"});if(!r.ok)throw new Error("HTTP "+r.status);return r.json()}
async function loadImpact(){return getJson("./world-model/impact-report.json")}
async function loadBrief(){
  const live="https://raw.githubusercontent.com/mikelninh/COMMONS/world-model-data/data/world-model/morning-brief.json";
  try{return await getJson(live)}catch(error){return null}
}
function actions(){
  try{
    const current=JSON.parse(localStorage.getItem(ACTION_KEY)||"[]");
    if(Array.isArray(current)&&current.length)return current;
    const old=JSON.parse(localStorage.getItem("commons.impact.actions.v0.2")||"[]");
    return Array.isArray(old)?old:[];
  }catch(error){return []}
}
function saveActions(items){localStorage.setItem(ACTION_KEY,JSON.stringify(items.slice(-200)))}
function actionKey(pointId,actionId){return pointId+"::"+actionId}
function actionState(pointId,actionId){return actions().find(item=>item.id===actionKey(pointId,actionId))?.status||"unrecorded"}
function setAction(pointId,action,status){
  const current=actionState(pointId,action.id);
  const items=actions().filter(item=>item.id!==actionKey(pointId,action.id));
  if(current!==status){
    items.push({id:actionKey(pointId,action.id),point_id:pointId,action_id:action.id,label:action.label,status,updated_at:new Date().toISOString()});
  }
  saveActions(items);
  renderStories();
  renderActionLog();
}
function liveMonitor(pointId){return (liveBrief?.monitors||[]).find(item=>item.point_id===pointId)||null}
function hazardLanguage(monitor){
  if(!monitor)return {state:"unavailable",title:"The live signal is unavailable.",copy:"We can still show consequence context, but not today’s rainfall state."};
  const state=String(monitor.state||"quiet");
  const ratio=Number(monitor.gate_ratio);
  if(state==="alert"||ratio>=1)return {state:"alert",title:"This deserves attention now.",copy:"Forecast rain is beyond the locally learned heavy-rain level. Confirm with official local warnings before acting."};
  if(state==="priority"||ratio>=.8)return {state:"priority",title:"The signal is getting close.",copy:"Forecast rain is approaching a historically unusual local level."};
  if(ratio>=.5)return {state:"quiet",title:"Still calm, but moving closer.",copy:"Forecast rain remains below the alert level, with some movement toward it."};
  return {state:"quiet",title:"No immediate weather concern.",copy:"The current rainfall forecast is comfortably below the local alert level."};
}
function infraSummary(infra){
  if(!infra)return {value:"unknown",copy:"Infrastructure coverage is incomplete here."};
  const health=Number(infra.health_facilities)||0;
  const bridges=Number(infra.bridges)||0;
  const roads=Number(infra.major_road_segments)||0;
  const power=Number(infra.power_substations)||0;
  const total=health+bridges+power;
  return {
    value:human(total),
    copy:health+" health facilities · "+bridges+" bridges · "+power+" substations · "+roads+" major road segments"
  };
}
function deterministicPositions(count,seed){
  const values=[];
  let x=seed;
  for(let i=0;i<count;i++){
    x=(x*9301+49297)%233280;
    const a=x/233280;
    x=(x*9301+49297)%233280;
    const b=x/233280;
    values.push([12+a*76,14+b*68]);
  }
  return values;
}
function rainMarkup(ratio,seed){
  const count=Math.max(6,Math.min(34,Math.round(7+(Number(ratio)||0)*25)));
  return deterministicPositions(count,seed).map((p,i)=>
    '<i class="rain-streak" style="left:'+p[0]+'%;top:'+(p[1]-30)+'%;animation-delay:-'+((i%9)*.21).toFixed(2)+'s;animation-duration:'+(1.5+(i%5)*.17).toFixed(2)+'s"></i>'
  ).join("");
}
function populationMarkup(pop,seed){
  const n=Number(pop)||0;
  const count=Math.max(3,Math.min(9,Math.round(Math.log10(Math.max(n,1000))-1)));
  return deterministicPositions(count,seed+17).map((p,i)=>{
    const size=70+(i%4)*34;
    return '<i class="population-glow" style="left:'+(p[0]-size/12)+'%;top:'+(p[1]-size/12)+'%;width:'+size+'px;height:'+size+'px;animation-delay:-'+(i*.55).toFixed(2)+'s"></i>';
  }).join("");
}
function infraMarkup(infra,seed){
  if(!infra)return "";
  const count=Math.max(4,Math.min(14,Math.round(Math.log10(1+(infra.health_facilities||0)+(infra.bridges||0)+(infra.power_substations||0))*3)));
  return deterministicPositions(count,seed+31).map((p,i)=>
    '<i class="infra-node" style="left:'+p[0]+'%;top:'+p[1]+'%;--angle:'+((i*37)%170-85)+'deg"></i>'
  ).join("");
}
function historyMarkup(hist,seed){
  const count=Math.max(0,Math.min(5,Number(hist?.nearby_events)||0));
  return deterministicPositions(count,seed+61).map((p,i)=>
    '<i class="history-ring" style="left:'+p[0]+'%;top:'+p[1]+'%;animation-delay:-'+(i*1.1).toFixed(1)+'s"></i>'
  ).join("");
}
function actionRows(profile){
  return (profile.action_options||[]).map(action=>{
    const state=actionState(profile.point_id,action.id);
    return '<div class="action-row"><div class="action-copy"><strong>'+action.label+'</strong><small>'+action.why+'</small></div><div class="action-controls">'+
      '<button class="done '+(state==="done"?"active":"")+'" data-point="'+profile.point_id+'" data-action="'+action.id+'" data-status="done">Done</button>'+
      '<button class="skip '+(state==="not_needed"?"active":"")+'" data-point="'+profile.point_id+'" data-action="'+action.id+'" data-status="not_needed">Not needed</button>'+
      '</div></div>';
  }).join("");
}
function timelineMarkup(hist){
  const examples=hist?.examples||[];
  const past=examples.slice(0,3).map((event,i)=>{
    const x=14+i*20;
    const label=(event.start_date||"past").slice(0,4);
    return '<i class="timeline-past" style="--x:'+x+'%" data-label="'+label+'"></i>';
  }).join("");
  return '<div class="timeline"><div class="timeline-label">PAST → NOW → NEXT 72H</div><div class="timeline-track">'+past+'<i class="timeline-now"></i><span class="timeline-next">FORECAST</span></div></div>';
}
function renderPlanetPins(){
  $("planetPins").innerHTML=(impactReport?.profiles||[]).map(profile=>{
    const meta=placeMeta[profile.point_id]||{pin:[50,50]};
    const monitor=liveMonitor(profile.point_id);
    const state=hazardLanguage(monitor).state;
    return '<button class="world-pin '+state+'" data-jump="'+profile.point_id+'" style="left:'+meta.pin[0]+'%;top:'+meta.pin[1]+'%" aria-label="Go to '+profile.name+'"><span class="pin-label">'+profile.name+'</span></button>';
  }).join("");
  document.querySelectorAll("[data-jump]").forEach(pin=>pin.addEventListener("click",()=>{
    document.getElementById("place-"+pin.dataset.jump)?.scrollIntoView({behavior:"smooth",block:"center"});
  }));
}
function renderWorld(){
  const monitors=liveBrief?.monitors||[];
  const alerts=monitors.filter(x=>x.state==="alert").length;
  const priority=monitors.filter(x=>x.state==="priority").length;
  const summary=$("worldSummary");
  if(alerts){
    summary.dataset.state="alert";
    $("worldSummaryTitle").textContent=alerts+" place"+(alerts===1?"":"s")+" needs attention.";
    $("worldSummaryCopy").textContent="The world view is focusing on what may matter most.";
  }else if(priority){
    summary.dataset.state="priority";
    $("worldSummaryTitle").textContent=priority+" place"+(priority===1?" is":"s are")+" worth a closer look.";
    $("worldSummaryCopy").textContent="Nothing has crossed the alert gate yet.";
  }else if(monitors.length){
    summary.dataset.state="quiet";
    $("worldSummaryTitle").textContent="The monitored world is quiet right now.";
    $("worldSummaryCopy").textContent=monitors.length+" validated places are below their alert thresholds.";
  }else{
    $("worldSummaryTitle").textContent="Live hazard data is unavailable.";
    $("worldSummaryCopy").textContent="The consequence story remains visible, but today’s signal is missing.";
  }
  $("topStatus").textContent=alerts?"ATTENTION NEEDED":priority?"WATCHING CHANGE":"WORLD QUIET";
  const updated=liveBrief?.generated_at;
  $("planetUpdated").textContent=updated?"UPDATED "+new Date(updated).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}):"LIVE";
  renderPlanetPins();
}
function storyChapter(profile,index){
  const c=profile.components||{};
  const exp=c.exposure||{};
  const infra=c.infrastructure||null;
  const hist=c.historical_consequence||{};
  const monitor=liveMonitor(profile.point_id);
  const language=hazardLanguage(monitor);
  const ratio=Number(monitor?.gate_ratio)||0;
  const infraView=infraSummary(infra);
  const meta=placeMeta[profile.point_id]||{scene:"monitored place",accent:"#b6ff69"};
  const seed=(index+1)*101;
  const historicalCount=Number(hist.consequential_events)||0;
  const historyHeadline=historicalCount?historicalCount+" serious precedent"+(historicalCount===1?"":"s")+" nearby":"No confirmed serious precedent nearby";
  return '<article class="place-chapter" id="place-'+profile.point_id+'" data-point="'+profile.point_id+'">'+
    '<div class="place-visual">'+
      '<div class="scene-grid"></div><div class="scene-contour"></div><div class="scene-water"></div>'+
      '<div class="rain-layer">'+rainMarkup(ratio,seed)+'</div>'+
      '<div class="population-layer">'+populationMarkup(exp.population_within_radius,seed)+'</div>'+
      '<div class="infra-layer">'+infraMarkup(infra,seed)+'</div>'+
      '<div class="history-layer">'+historyMarkup(hist,seed)+'</div>'+
      '<div class="scene-label">'+meta.scene.toUpperCase()+'</div>'+
      '<div class="scene-state '+language.state+'">'+language.state.toUpperCase()+'</div>'+
      '<div class="scene-footer"><div><strong>'+profile.name+'</strong><small>'+profile.country+' · '+pct(ratio)+' of heavy-rain gate</small></div>'+
        '<div class="layer-legend"><span class="layer-chip on">RAIN</span><span class="layer-chip on">PEOPLE</span><span class="layer-chip on">SYSTEMS</span><span class="layer-chip on">MEMORY</span></div>'+
      '</div>'+
    '</div>'+
    '<div class="place-copy">'+
      '<span class="chapter-count">0'+(index+1)+' / 0'+(impactReport?.profiles?.length||3)+'</span>'+
      '<h3>'+profile.name+'</h3><span class="country">'+profile.country+'</span>'+
      '<div class="situation-block"><span>RIGHT NOW</span><h4>'+language.title+'</h4><p>'+language.copy+'</p></div>'+
      '<div class="story-beats">'+
        '<div class="story-beat"><div class="beat-icon">◎</div><div><span>PEOPLE</span><strong>'+human(exp.population_within_radius)+' nearby</strong><p>Within roughly '+(exp.radius_km??"—")+' km. Nearby does not mean affected.</p></div></div>'+
        '<div class="story-beat"><div class="beat-icon">⌂</div><div><span>CRITICAL SYSTEMS</span><strong>'+infraView.value+' mapped assets</strong><p>'+infraView.copy+'</p></div></div>'+
        '<div class="story-beat"><div class="beat-icon">↺</div><div><span>MEMORY</span><strong>'+historyHeadline+'</strong><p>'+(hist.nearby_events??0)+' historical GDACS events reviewed around this place.</p></div></div>'+
      '</div>'+
      timelineMarkup(hist)+
      '<details class="action-drawer"><summary>If this changes, what would we check? <b>+</b></summary><div class="action-list">'+actionRows(profile)+'</div></details>'+
    '</div>'+
  '</article>';
}
function renderStories(){
  $("storyChapters").innerHTML=(impactReport?.profiles||[]).map(storyChapter).join("");
  bindActions();
  observeChapters();
}
function bindActions(){
  document.querySelectorAll("[data-action]").forEach(button=>button.addEventListener("click",()=>{
    const profile=(impactReport?.profiles||[]).find(x=>x.point_id===button.dataset.point);
    const action=(profile?.action_options||[]).find(x=>x.id===button.dataset.action);
    if(action)setAction(profile.point_id,action,button.dataset.status);
  }));
}
function observeChapters(){
  if(!("IntersectionObserver" in window))return;
  const observer=new IntersectionObserver(entries=>{
    entries.forEach(entry=>{
      if(!entry.isIntersecting)return;
      document.querySelectorAll(".world-pin").forEach(pin=>pin.classList.toggle("active",pin.dataset.jump===entry.target.dataset.point));
      entry.target.classList.add("in-view");
    });
  },{threshold:.35});
  document.querySelectorAll(".place-chapter").forEach(chapter=>observer.observe(chapter));
}
function renderActionLog(){
  const items=actions().sort((a,b)=>String(b.updated_at).localeCompare(String(a.updated_at)));
  $("actionMemory").classList.toggle("hidden",!items.length);
  if(!items.length)return;
  $("actionLog").innerHTML=items.slice(0,12).map(item=>{
    const profile=(impactReport?.profiles||[]).find(x=>x.point_id===item.point_id);
    return '<article class="action-log-item"><div><span>'+String(item.status).replaceAll("_"," ").toUpperCase()+'</span><strong>'+(profile?.name||item.point_id)+' · '+item.label+'</strong></div><time>'+new Date(item.updated_at).toLocaleString()+'</time></article>';
  }).join("");
}
function renderTrust(){
  const bench=impactReport?.benchmark||{};
  const h=bench.hypothesis||{};
  const health=impactReport?.source_health||{};
  $("h27Status").textContent=String(h.status||"insufficient").replaceAll("_"," ").toUpperCase();
  $("sourceHealth").textContent=pct(health.emdat_coverage);
  $("briefHealth").textContent=liveBrief?"CONNECTED":"UNAVAILABLE";
  $("trustSummary").textContent=h.status==="supported"
    ?"Historical testing currently supports impact-aware context."
    :"COMMONS does not yet have enough complete consequence labels to prove that impact-aware ordering beats hazard alone. So the beautiful story stays context—not authority.";
  $("trustList").innerHTML=(impactReport?.trust_contract||[]).map(x=>'<div class="trust-item">'+x+'</div>').join("");
}
async function init(){
  try{
    [impactReport,liveBrief]=await Promise.all([loadImpact(),loadBrief()]);
    renderWorld();
    renderStories();
    renderActionLog();
    renderTrust();
  }catch(error){
    $("worldSummaryTitle").textContent="The world view could not load.";
    $("worldSummaryCopy").textContent="COMMONS could not connect to its current evidence.";
    $("topStatus").textContent="DATA UNAVAILABLE";
  }
}
init();
