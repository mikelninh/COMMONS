const $=id=>document.getElementById(id);
const ACTION_KEY="commons.impact.actions.v0.1";
let impactReport=null;
let liveBrief=null;

function pct(v){const n=Number(v);return Number.isFinite(n)?Math.round(n*100)+"%":"—"}
function num(v){const n=Number(v);return Number.isFinite(n)?n.toFixed(2):"—"}
function human(v){const n=Number(v);if(!Number.isFinite(n))return "—";if(n>=1e6)return (n/1e6).toFixed(1)+"M";if(n>=1e3)return Math.round(n/1e3)+"k";return Math.round(n)}
function component(label,value,copy){return '<div class="component"><span>'+label+'</span><b>'+value+'</b><p>'+copy+'</p></div>'}
async function getJson(url){const r=await fetch(url,{cache:"no-store"});if(!r.ok)throw new Error("HTTP "+r.status);return r.json()}
async function loadImpact(){return getJson("./world-model/impact-report.json")}
async function loadBrief(){
  const live="https://raw.githubusercontent.com/mikelninh/COMMONS/world-model-data/data/world-model/morning-brief.json";
  try{return await getJson(live)}catch(error){return null}
}
function actions(){
  try{const value=JSON.parse(localStorage.getItem(ACTION_KEY)||"[]");return Array.isArray(value)?value:[]}catch(error){return []}
}
function saveActions(items){localStorage.setItem(ACTION_KEY,JSON.stringify(items.slice(-200)))}
function actionId(pointId,actionId){return pointId+"::"+actionId}
function upsertAction(pointId,action,status){
  const items=actions();
  const id=actionId(pointId,action.id);
  const next=items.filter(item=>item.id!==id);
  next.push({
    id,
    point_id:pointId,
    action_id:action.id,
    label:action.label,
    status,
    updated_at:new Date().toISOString()
  });
  saveActions(next);
  renderProfiles();
  renderActionLog();
}
function actionState(pointId,actionIdValue){
  return actions().find(item=>item.id===actionId(pointId,actionIdValue))?.status||"unrecorded";
}
function bindActionButtons(){
  document.querySelectorAll("[data-action]").forEach(button=>{
    button.addEventListener("click",()=>{
      const point=button.dataset.point;
      const actionIdValue=button.dataset.action;
      const status=button.dataset.status;
      const profile=(impactReport?.profiles||[]).find(x=>x.point_id===point);
      const action=(profile?.action_options||[]).find(x=>x.id===actionIdValue);
      if(action)upsertAction(point,action,status);
    });
  });
}
function liveMonitor(pointId){
  return (liveBrief?.monitors||[]).find(item=>item.point_id===pointId)||null;
}
function hazardComponent(profile){
  const monitor=liveMonitor(profile.point_id);
  if(!monitor)return component("LIVE HAZARD","—","live Morning Brief unavailable");
  const state=String(monitor.state||"unknown").toUpperCase();
  return component(
    "LIVE HAZARD",
    state+" · "+pct(monitor.gate_ratio),
    (monitor.forecast_peak_daily_mm??"—")+" mm peak day · "+(monitor.forecast_peak_date||"—")+" · validated rainfall gate"
  );
}
function actionControls(profile){
  return (profile.action_options||[]).map(action=>{
    const state=actionState(profile.point_id,action.id);
    return '<div class="action-row">'+
      '<div class="action-copy"><strong>'+action.label+'</strong><small>'+action.why+'</small></div>'+
      '<div class="action-controls">'+
        '<button class="'+(state==="considered"?"active ":"")+'consider" data-point="'+profile.point_id+'" data-action="'+action.id+'" data-status="considered">CONSIDER</button>'+
        '<button class="'+(state==="done"?"active ":"")+'done" data-point="'+profile.point_id+'" data-action="'+action.id+'" data-status="done">DONE</button>'+
        '<button class="'+(state==="not_needed"?"active ":"")+'not-needed" data-point="'+profile.point_id+'" data-action="'+action.id+'" data-status="not_needed">NOT NEEDED</button>'+
      '</div>'+
    '</div>';
  }).join("");
}
function renderProfiles(){
  if(!impactReport)return;
  $("profiles").innerHTML=(impactReport.profiles||[]).map(profile=>{
    const c=profile.components||{}, exp=c.exposure||{}, infra=c.infrastructure||{}, hist=c.historical_consequence||{};
    const infraValue=infra.health_facilities==null?"—":(infra.health_facilities+" health · "+(infra.bridges||0)+" bridges");
    return '<article class="profile">'+
      '<div class="profile-head"><div><h3>'+profile.name+'</h3><small>'+profile.country+'</small></div><a href="./morning.html">Morning Brief →</a></div>'+
      hazardComponent(profile)+
      component("EXPOSURE",human(exp.population_within_radius)+" people","within ~"+(exp.radius_km??"—")+" km · context only")+
      component("CRITICAL INFRASTRUCTURE",infraValue,"nearby assets, not damage estimates")+
      component("HISTORICAL CONSEQUENCE",(hist.consequential_events??0)+" consequential precedents",(hist.nearby_events??0)+" nearby GDACS events reviewed")+
      '<div class="action-stack"><span class="action-stack-label">HUMAN CHECKS</span>'+actionControls(profile)+'</div>'+
    '</article>';
  }).join("");
  bindActionButtons();
}
function renderActionLog(){
  const items=actions().sort((a,b)=>String(b.updated_at).localeCompare(String(a.updated_at)));
  if(!items.length){
    $("actionLog").innerHTML='<div class="action-log-empty">No actions recorded on this device yet.</div>';
    return;
  }
  $("actionLog").innerHTML=items.slice(0,12).map(item=>{
    const profile=(impactReport?.profiles||[]).find(x=>x.point_id===item.point_id);
    return '<article class="action-log-item"><div><span>'+String(item.status).replaceAll("_"," ").toUpperCase()+'</span><strong>'+(profile?.name||item.point_id)+' · '+item.label+'</strong></div><time>'+new Date(item.updated_at).toLocaleString()+'</time></article>';
  }).join("");
}
function renderBenchmark(){
  const bench=impactReport?.benchmark||{}, h=bench.hypothesis||{}, health=impactReport?.source_health||{};
  $("h27Status").textContent="H27 · "+String(h.status||"insufficient").replaceAll("_"," ").toUpperCase();
  $("sourceHealth").textContent="EM-DAT LABEL COVERAGE · "+pct(health.emdat_coverage);
  $("briefHealth").textContent="LIVE HAZARD · "+(liveBrief?"CONNECTED":"UNAVAILABLE");
  $("benchmarkCopy").textContent=h.product_update||"Impact ordering remains context only.";
  $("hazardAP").textContent=num(bench.hazard_only?.average_precision);
  $("impactAP").textContent=num(bench.impact_aware?.average_precision);
  $("apGain").textContent=num(bench.comparison?.average_precision_gain);
  $("recallGain").textContent=pct(bench.comparison?.top20_recall_gain);
  $("trustList").innerHTML=(impactReport?.trust_contract||[]).map(x=>'<div class="trust-item">'+x+'</div>').join("");
}
async function init(){
  try{
    [impactReport,liveBrief]=await Promise.all([loadImpact(),loadBrief()]);
    renderBenchmark();
    renderProfiles();
    renderActionLog();
  }catch(error){
    $("h27Status").textContent="H27 · UNAVAILABLE";
    $("benchmarkCopy").textContent="Impact v0.1 could not load its evidence.";
  }
}
init();
