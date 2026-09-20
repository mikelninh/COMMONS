const $=id=>document.getElementById(id);

function fmt(value,suffix="",digits=1){
  const n=Number(value);
  return Number.isFinite(n)?n.toFixed(digits)+suffix:"—";
}
function pct(value){
  const n=Number(value);
  return Number.isFinite(n)?Math.round(n*100)+"%":"—";
}
function ago(iso){
  if(!iso)return "no live timestamp";
  const ms=Date.now()-new Date(iso).getTime();
  if(!Number.isFinite(ms))return "unknown freshness";
  const minutes=Math.max(0,Math.round(ms/60000));
  if(minutes<60)return minutes+" min ago";
  const hours=Math.round(minutes/60);
  return hours+"h ago";
}
function greeting(){
  const hour=new Date().getHours();
  return hour<12?"Good morning.":hour<18?"Good afternoon.":"Good evening.";
}
async function getJson(url){
  const response=await fetch(url,{cache:"no-store"});
  if(!response.ok)throw new Error("HTTP "+response.status);
  return response.json();
}
async function loadBrief(){
  const live="https://raw.githubusercontent.com/mikelninh/COMMONS/world-model-data/data/world-model/morning-brief.json";
  try{return await getJson(live)}
  catch(first){return getJson("./world-model/morning-brief-seed.json")}
}
function revisionText(revision){
  if(!revision||revision.models_compared<2)return "revision history collecting";
  if(revision.direction==="up")return revision.supporting_models+"/"+revision.models_compared+" models revised rain upward";
  if(revision.direction==="down")return revision.supporting_models+"/"+revision.models_compared+" models revised rain downward";
  return "no shared model revision direction";
}
function monitorContext(item){
  const tags=[];
  tags.push('<span class="tag">'+revisionText(item.revision)+'</span>');
  if(item.flood_context?.historical_percentile!=null){
    tags.push('<span class="tag">river '+fmt(item.flood_context.historical_percentile,"th pct",0)+'</span>');
  }
  if(item.models_available<item.models_expected){
    tags.push('<span class="tag">'+item.models_available+'/'+item.models_expected+' models available</span>');
  }
  return tags.join("");
}
function card(item){
  const ratio=Number(item.gate_ratio);
  const meter=Number.isFinite(ratio)?Math.max(0,Math.min(1.25,ratio))*80:0;
  return '<article class="monitor-card '+item.state+'">'+
    '<div class="monitor-head"><div class="place"><strong>'+item.name+'</strong><span>'+item.country+' · '+item.signal+'</span></div>'+
    '<span class="pill '+item.state+'">'+item.state.toUpperCase()+'</span></div>'+
    '<div class="meter" style="--pct:'+meter+'%"><i></i></div>'+
    '<div class="signal-row">'+
      '<div class="signal"><span>PEAK FORECAST DAY</span><b>'+fmt(item.forecast_peak_daily_mm," mm",1)+'</b><small>'+String(item.forecast_peak_date||"—")+'</small></div>'+
      '<div class="signal"><span>HEAVY GATE</span><b>'+fmt(item.heavy_rain_gate_mm," mm",1)+'</b></div>'+
      '<div class="signal"><span>GATE RATIO</span><b>'+pct(item.gate_ratio)+'</b></div>'+
    '</div>'+
    '<p class="why">'+item.why+'</p><p class="next">'+item.next_step+'</p>'+
    '<div class="context">'+monitorContext(item)+'</div>'+
  '</article>';
}
function queueItem(item){
  return '<article class="queue-item">'+
    '<div class="rank">'+String(item.rank).padStart(2,"0")+'</div>'+
    '<div class="queue-main"><strong>'+item.name+' · '+item.country+'</strong><p>'+item.why+'</p></div>'+
    '<div class="queue-score"><b>'+pct(item.gate_ratio)+'</b><span>of heavy-rain gate</span></div>'+
  '</article>';
}
function render(brief){
  $("morningGreeting").textContent=greeting();
  $("briefHeadline").textContent=brief.headline||"Morning Brief unavailable.";
  $("briefUpdated").textContent=brief.generated_at
    ?"Updated "+new Date(brief.generated_at).toLocaleString()+" · "+ago(brief.generated_at)
    :"Waiting for live brief";
  const evidence=brief.evidence||{};
  $("evidenceHealth").textContent="Evidence health: "+String(evidence.status||"unknown").toUpperCase();

  const summary=brief.summary||{};
  const alerts=Number(summary.alerts)||0;
  const priority=Number(summary.priority)||0;
  const state=alerts?"alert":priority?"priority":"quiet";
  $("statusOrb").dataset.state=state;
  $("orbLabel").textContent=alerts?"ALERT":priority?"PRIORITY":"CALM";
  $("orbCount").textContent=alerts||priority||0;
  $("orbDetail").textContent=alerts?"needs inspection":priority?"worth a glance":"interruptions";

  const monitors=brief.monitors||[];
  const alertItems=monitors.filter(item=>item.state==="alert");
  $("interruptSection").classList.toggle("hidden",!alertItems.length);
  $("alertGrid").innerHTML=alertItems.map(card).join("");
  $("queueList").innerHTML=monitors.map(queueItem).join("");
  $("closeMessage").textContent=brief.close_message||"You are caught up.";

  const unranked=brief.unranked_loops||[];
  $("coverageGrid").innerHTML=unranked.map(loop=>
    '<article class="coverage-card"><b>'+loop.title+'</b><span>'+String(loop.coverage||"planned").replaceAll("_"," ")+' · not ranked yet</span></article>'
  ).join("");

  $("trustList").innerHTML=(brief.trust_contract||[]).map(item=>
    '<div class="trust-item">'+item+'</div>'
  ).join("");

  $("loading").classList.add("hidden");
}
async function init(){
  try{render(await loadBrief())}
  catch(error){
    $("briefHeadline").textContent="Morning Brief could not load.";
    $("briefUpdated").textContent="Live data unavailable.";
    $("loading").textContent="Brief unavailable";
  }
}
init();
setInterval(init,5*60*1000);
