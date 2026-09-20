const $ = id => document.getElementById(id);
const qsa = (sel,root=document)=>[...root.querySelectorAll(sel)];

let currentSnapshot=null;
let currentPilot=null;
let replayFrames=[];
let loopCatalog=null;

async function getJson(url){
  const response=await fetch(url,{cache:"no-store"});
  if(!response.ok)throw new Error(url+" "+response.status);
  return response.json();
}

function fmt(value,suffix=""){
  return value===null||value===undefined||Number.isNaN(Number(value))
    ?"—"
    :Number(value).toFixed(Number(value)%1===0?0:1)+suffix;
}

function clamp(value,min=0,max=100){
  return Math.max(min,Math.min(max,Number(value)||0));
}

function shortModel(label){
  if(/ECMWF/i.test(label))return "ECMWF";
  if(/GFS/i.test(label))return "GFS";
  if(/ICON/i.test(label))return "ICON";
  return label;
}

function setMeter(id,value){
  const el=$(id);
  if(!el)return;
  requestAnimationFrame(()=>el.style.setProperty("--value",String(clamp(value))));
}

function renderSignal(loop){
  const memory=loop?.weather_memory||{};
  const flood=loop?.flood_signal||{};
  const rain=memory.status==="ok"?memory.seasonal_percentile:null;
  const river=flood.status==="ok"?flood.historical_percentile:null;

  $("signalPlace").textContent=loop?.watchpoint
    ? loop.watchpoint.name+" · "+loop.watchpoint.country
    : "Nuwakot · Nepal";

  $("signalRainPct").textContent=fmt(rain,"%");
  $("signalRiverPct").textContent=fmt(river,"%");
  $("whyRain").textContent=fmt(rain,"%");
  $("whyRiver").textContent=fmt(river,"%");
  setMeter("rainMeter",rain);
  setMeter("riverMeter",river);
}

function renderCouncilVisual(loop){
  const council=loop?.forecast_council||{};
  const members=council.members||[];
  if(!members.length){
    $("councilBars").innerHTML='<div class="empty-state">Waiting for live model data.</div>';
    $("councilAgreement").textContent="—";
    return;
  }
  const values=members.map(item=>Number(item.precip_72h_mm)||0);
  const max=Math.max(...values,1);
  $("councilBars").innerHTML=members.map((member,index)=>{
    const value=Number(member.precip_72h_mm)||0;
    const height=12+(value/max)*72;
    return '<div class="model-bar" style="--h:'+height+'%">'+
      '<strong>'+fmt(value," mm")+'</strong>'+
      '<small>72h rain</small>'+
      '<b>'+shortModel(member.label)+'</b>'+
    '</div>';
  }).join("");
  $("councilAgreement").textContent=(council.consensus?.precip_agreement||"unknown").toUpperCase();
  const errors=council.source_errors||[];
  $("councilSourceState").textContent=errors.length
    ? members.map(m=>shortModel(m.label)).join(" · ")+" · "+errors.length+" source unavailable"
    : members.map(m=>shortModel(m.label)).join(" · ");
}

function renderMemoryVisual(loop){
  const memory=loop?.weather_memory||{};
  if(memory.status!=="ok"){
    $("memoryPercentile").textContent="—";
    $("analogueChips").innerHTML='<span class="analogue-chip">memory unavailable</span>';
    return;
  }
  $("memoryPercentile").textContent=fmt(memory.seasonal_percentile,"%");
  $("memoryEnd").textContent=(memory.historical_period_end||"today").slice(0,4);
  setMeter("memoryRing",memory.seasonal_percentile);

  const startYear=Number((memory.historical_period_start||"1940").slice(0,4))||1940;
  const endYear=Number((memory.historical_period_end||String(new Date().getUTCFullYear())).slice(0,4))||new Date().getUTCFullYear();
  const span=Math.max(1,endYear-startYear);
  const timeline=$("memoryTimeline");
  qsa(".memory-dot",timeline).forEach(el=>el.remove());

  (memory.analogues||[]).forEach(item=>{
    const year=Number(String(item.start_date).slice(0,4));
    const pct=clamp(((year-startYear)/span)*100,0,100);
    const dot=document.createElement("i");
    dot.className="memory-dot";
    dot.style.left=pct+"%";
    dot.title=item.start_date+" · "+fmt(item.precip_72h_mm," mm / 72h");
    const label=document.createElement("span");
    label.textContent=String(year);
    dot.appendChild(label);
    timeline.appendChild(dot);
  });

  $("analogueChips").innerHTML=(memory.analogues||[]).map(item=>
    '<span class="analogue-chip">'+String(item.start_date).slice(0,4)+' · '+fmt(item.precip_72h_mm," mm")+'</span>'
  ).join("");
}

function renderLabCouncil(loop){
  const council=loop?.forecast_council||{};
  $("forecastCouncil").innerHTML=(council.members||[]).map(member=>
    '<div class="dense-row"><b>'+member.label+'</b><span>'+
    fmt(member.precip_72h_mm," mm")+'</span><span>'+
    fmt(member.temp_max_72h_c,"°C")+'</span></div>'
  ).join("")||'<div class="empty-state">No live council available.</div>';

  const c=council.consensus||{};
  $("forecastConsensus").innerHTML=
    '72h rain median <b>'+fmt(c.precip_72h_mm_median," mm")+'</b> · '+
    'rain agreement <b>'+String(c.precip_agreement||"unknown")+'</b><br>'+
    'Agreement is model spread, not a calibrated probability.';
}

function renderLabMemory(loop){
  const memory=loop?.weather_memory||{};
  $("weatherMemory").innerHTML=memory.status==="ok"
    ? '<div class="lab-big">'+fmt(memory.seasonal_percentile,"%")+' <small>seasonal percentile</small></div>'+
      '<div class="lab-copy">ERA5 · '+memory.historical_period_start+' → '+memory.historical_period_end+
      '<br>Closest analogues: '+(memory.analogues||[]).map(a=>a.start_date.slice(0,4)).join(" · ")+
      '<br><br>'+memory.limitation+'</div>'
    : '<div class="empty-state">Historical memory unavailable.</div>';
}

function renderLabFlood(loop){
  const flood=loop?.flood_signal||{};
  $("floodSignal").innerHTML=flood.status==="ok"
    ? '<div class="lab-big">'+fmt(flood.historical_percentile,"%")+' <small>historical percentile</small></div>'+
      '<div class="lab-copy">Peak '+fmt(flood.forecast_peak_discharge_m3s," m³/s")+
      ' · '+flood.forecast_peak_date+'<br>Baseline '+flood.historical_start+' → '+(flood.historical_end||"2022")+
      '<br><br>'+flood.limitation+'</div>'
    : '<div class="empty-state">Flood signal unavailable.</div>';
}

function coverageLabel(value){
  return {
    live_pilot:"LIVE PILOT",
    physical_context:"PHYSICAL CONTEXT",
    story_layer_only:"STORY LAYER",
    ambient_live_source:"AMBIENT LIVE"
  }[value]||String(value||"planned").replaceAll("_"," ").toUpperCase();
}

function renderLoops(catalog,snapshot){
  const stateMap=new Map((snapshot?.loops||[]).map(loop=>[loop.id,loop]));
  $("loopsGrid").innerHTML=(catalog.loops||[]).map(loop=>{
    const state=stateMap.get(loop.id);
    const errors=state?.forecast_council?.source_errors?.length||0;
    return '<article class="loop-card">'+
      '<div class="loop-meta"><span>'+String(loop.order).padStart(2,"0")+' · '+loop.human_anchor+'</span>'+
      '<span class="coverage-'+loop.coverage+'">'+coverageLabel(loop.coverage)+'</span></div>'+
      '<h3>'+loop.title+'</h3>'+
      '<p>'+loop.question+'</p>'+
      '<div class="loop-sources">'+loop.live_sources.join(" · ")+(errors?' · '+errors+' source error(s)':'')+'</div>'+
    '</article>';
  }).join("");
}

function frameRain(frame){
  return Number(frame?.consensus?.precip_72h_mm_median);
}

function renderReplayFrame(index){
  if(!replayFrames.length)return;
  const safe=Math.max(0,Math.min(replayFrames.length-1,Number(index)||0));
  const frame=replayFrames[safe];
  const members=frame.members||[];
  const values=members.map(m=>Number(m.precip_72h_mm)||0);
  const max=Math.max(...values,1);

  $("replayTime").textContent=frame.generated_at
    ? new Date(frame.generated_at).toLocaleString([],{dateStyle:"medium",timeStyle:"short"})
    : "unknown";
  $("replayCount").textContent=(safe+1)+" of "+replayFrames.length+" archived frames";

  $("replayBars").innerHTML=members.map(member=>{
    const value=Number(member.precip_72h_mm)||0;
    const height=10+(value/max)*72;
    return '<div class="replay-bar" style="--h:'+height+'%">'+
      '<strong>'+fmt(value," mm")+'</strong><b>'+shortModel(member.label)+'</b></div>';
  }).join("")||'<div class="empty-state">No model members in this frame.</div>';

  const previous=replayFrames[safe-1];
  const currentRain=frameRain(frame);
  const previousRain=frameRain(previous);
  let delta="first archived frame";
  if(Number.isFinite(currentRain)&&Number.isFinite(previousRain)){
    const change=currentRain-previousRain;
    delta=(change>0?"+":"")+change.toFixed(1)+" mm median 72h rain";
  }
  $("replayDelta").querySelector("strong").textContent=delta;
  $("replaySlider").value=String(safe);
}

function renderReplay(frames,currentLoop){
  replayFrames=(frames||[]).filter(Boolean);
  if(!replayFrames.length&&currentLoop){
    replayFrames=[{
      generated_at:currentSnapshot?.generated_at,
      members:currentLoop.forecast_council?.members||[],
      consensus:currentLoop.forecast_council?.consensus||{},
      flood_signal:currentLoop.flood_signal||{},
      weather_memory:currentLoop.weather_memory||{}
    }];
  }
  const slider=$("replaySlider");
  slider.max=String(Math.max(0,replayFrames.length-1));
  slider.value=String(Math.max(0,replayFrames.length-1));
  renderReplayFrame(replayFrames.length-1);
}

function updateSceneRail(sceneIndex){
  qsa("[data-scene-jump]").forEach(btn=>{
    btn.classList.toggle("active",Number(btn.dataset.sceneJump)===sceneIndex);
  });
}

function setupStoryObserver(){
  const scenes=qsa(".wm-scene");
  if(!("IntersectionObserver" in window)){
    updateSceneRail(0);
    return;
  }
  const observer=new IntersectionObserver(entries=>{
    const visible=entries
      .filter(entry=>entry.isIntersecting)
      .sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];
    if(visible)updateSceneRail(Number(visible.target.dataset.scene));
  },{threshold:[.35,.55,.75]});
  scenes.forEach(scene=>observer.observe(scene));

  qsa("[data-scene-jump]").forEach(btn=>{
    btn.onclick=()=>scenes[Number(btn.dataset.sceneJump)]?.scrollIntoView({behavior:"smooth"});
  });
}

function setMode(mode){
  const story=mode==="story";
  $("storyExperience").classList.toggle("hidden",!story);
  $("labExperience").classList.toggle("hidden",story);
  $("sceneRail").classList.toggle("hidden",!story);
  $("storyModeBtn").classList.toggle("active",story);
  $("labModeBtn").classList.toggle("active",!story);
  window.scrollTo({top:0,behavior:"smooth"});
}

async function loadLatest(){
  const liveUrl="https://raw.githubusercontent.com/mikelninh/COMMONS/world-model-data/data/world-model/latest.json";
  try{return await getJson(liveUrl)}
  catch(firstError){
    try{return await getJson("./world-model/latest.json")}
    catch(secondError){return getJson("./world-model/seed.json")}
  }
}

async function loadReplay(){
  const url="https://raw.githubusercontent.com/mikelninh/COMMONS/world-model-data/data/world-model/replay.json";
  try{
    const replay=await getJson(url);
    return replay.frames||[];
  }catch(error){
    return [];
  }
}

async function init(){
  const [snapshot,catalog,frames]=await Promise.all([
    loadLatest(),
    getJson("./world-model/loops.json"),
    loadReplay()
  ]);
  currentSnapshot=snapshot;
  loopCatalog=catalog;
  currentPilot=(snapshot.loops||[]).find(loop=>loop.id==="water-rises")||null;

  const live=Boolean(snapshot.generated_at);
  $("wmStatus").textContent=live
    ? "LIVE RESEARCH SNAPSHOT · "+new Date(snapshot.generated_at).toLocaleString()
    : "NO LIVE SNAPSHOT · seed state only";
  $("wmUpdated").textContent=live
    ? new Date(snapshot.generated_at).toLocaleString()
    : "no live snapshot";

  renderSignal(currentPilot);
  renderCouncilVisual(currentPilot);
  renderMemoryVisual(currentPilot);
  renderReplay(frames,currentPilot);
  renderLabCouncil(currentPilot);
  renderLabMemory(currentPilot);
  renderLabFlood(currentPilot);
  renderLoops(catalog,snapshot);

  $("replaySlider").oninput=e=>renderReplayFrame(e.target.value);
  $("storyModeBtn").onclick=()=>setMode("story");
  $("labModeBtn").onclick=()=>setMode("lab");
  $("openLabBtn").onclick=()=>setMode("lab");
  $("backToStoryBtn").onclick=()=>setMode("story");
  setupStoryObserver();
}

init().catch(error=>{
  $("wmStatus").textContent="WORLD MODEL ERROR · "+error.message;
});
