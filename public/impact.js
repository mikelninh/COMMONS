const $=id=>document.getElementById(id);
const ACTION_KEY="commons.impact.actions.v0.2";
let impactReport=null;
let liveBrief=null;

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
    const old=JSON.parse(localStorage.getItem("commons.impact.actions.v0.1")||"[]");
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
  renderProfiles();
  renderActionLog();
}
function liveMonitor(pointId){return (liveBrief?.monitors||[]).find(item=>item.point_id===pointId)||null}
function hazardLanguage(monitor){
  if(!monitor)return {state:"unavailable",title:"Live weather is unavailable.",copy:"The consequence context is still useful, but COMMONS cannot assess the current rainfall signal."};
  const state=String(monitor.state||"quiet");
  const ratio=Number(monitor.gate_ratio);
  if(state==="alert"||ratio>=1)return {state:"alert",title:"This deserves attention now.",copy:"Forecast rain crosses the locally learned heavy-rain level. Confirm with official local warnings before acting."};
  if(state==="priority"||ratio>=.8)return {state:"priority",title:"This is worth checking.",copy:"Forecast rain is getting close to the local heavy-rain level."};
  if(ratio>=.5)return {state:"quiet",title:"No immediate concern, but it is getting closer.",copy:"Forecast rain is still below the local heavy-rain level."};
  return {state:"quiet",title:"No immediate weather concern.",copy:"Forecast rain is well below the local heavy-rain level."};
}
function infraFact(infra){
  if(!infra)return {value:"Not available",copy:"We leave missing infrastructure data blank."};
  const health=Number(infra.health_facilities)||0;
  const bridges=Number(infra.bridges)||0;
  if(health||bridges)return {value:human(health+bridges)+" mapped",copy:health+" health facilities · "+bridges+" bridges nearby"};
  return {value:"No mapped count",copy:"Nearby infrastructure context is limited."};
}
function fact(label,value,copy){return '<div class="fact"><span>'+label+'</span><b>'+value+'</b><small>'+copy+'</small></div>'}
function actionRows(profile){
  return (profile.action_options||[]).map(action=>{
    const state=actionState(profile.point_id,action.id);
    return '<div class="check-row"><div class="check-copy"><strong>'+action.label+'</strong><small>'+action.why+'</small></div><div class="check-actions">'+
      '<button class="done '+(state==="done"?"active":"")+'" data-point="'+profile.point_id+'" data-action="'+action.id+'" data-status="done">Done</button>'+
      '<button class="skip '+(state==="not_needed"?"active":"")+'" data-point="'+profile.point_id+'" data-action="'+action.id+'" data-status="not_needed">Not needed</button>'+
      '</div></div>';
  }).join("");
}
function bindActions(){
  document.querySelectorAll("[data-action]").forEach(button=>{
    button.addEventListener("click",()=>{
      const profile=(impactReport?.profiles||[]).find(x=>x.point_id===button.dataset.point);
      const action=(profile?.action_options||[]).find(x=>x.id===button.dataset.action);
      if(action)setAction(profile.point_id,action,button.dataset.status);
    });
  });
}
function renderOverview(){
  const monitors=liveBrief?.monitors||[];
  const alerts=monitors.filter(x=>x.state==="alert").length;
  const priority=monitors.filter(x=>x.state==="priority").length;
  const overview=$("overview");
  if(alerts){
    overview.dataset.state="alert";
    $("overviewTitle").textContent=alerts+" place"+(alerts===1?"":"s")+" needs attention.";
    $("overviewCopy").textContent="Start there, then use the consequence context to understand what could be affected.";
  }else if(priority){
    overview.dataset.state="priority";
    $("overviewTitle").textContent=priority+" place"+(priority===1?" is":"s are")+" worth checking.";
    $("overviewCopy").textContent="Nothing has crossed the alert gate, but one or more places are getting closer.";
  }else if(monitors.length){
    overview.dataset.state="quiet";
    $("overviewTitle").textContent="Nothing needs immediate attention.";
    $("overviewCopy").textContent=monitors.length+" validated places are currently below their alert thresholds.";
  }else{
    overview.dataset.state="";
    $("overviewTitle").textContent="Live hazard data is unavailable.";
    $("overviewCopy").textContent="You can still review consequence context, but not today’s weather state.";
  }
}
function renderProfiles(){
  if(!impactReport)return;
  $("profiles").innerHTML=(impactReport.profiles||[]).map(profile=>{
    const c=profile.components||{};
    const exp=c.exposure||{};
    const infra=c.infrastructure||null;
    const hist=c.historical_consequence||{};
    const language=hazardLanguage(liveMonitor(profile.point_id));
    const infraView=infraFact(infra);
    const peopleCopy=exp.radius_km!=null?"within about "+exp.radius_km+" km · nearby, not necessarily affected":"nearby population context";
    const historyValue=(hist.consequential_events??0)===0?"None confirmed":String(hist.consequential_events);
    const historyCopy=(hist.nearby_events??0)+" nearby historical events reviewed";
    return '<article class="profile">'+
      '<div class="profile-top"><div class="place"><h3>'+profile.name+'</h3><small>'+profile.country+'</small></div><span class="state-pill '+language.state+'">'+language.state.toUpperCase()+'</span></div>'+
      '<div class="situation"><strong>'+language.title+'</strong><p>'+language.copy+'</p></div>'+
      '<div class="fact-grid">'+
        fact("PEOPLE NEARBY",human(exp.population_within_radius),peopleCopy)+
        fact("CRITICAL PLACES",infraView.value,infraView.copy)+
        fact("PAST SERIOUS EVENTS",historyValue,historyCopy)+
      '</div>'+
      '<div class="next-checks"><span>NEXT HUMAN CHECKS</span><div class="check-list">'+actionRows(profile)+'</div></div>'+
    '</article>';
  }).join("");
  bindActions();
}
function renderActionLog(){
  const items=actions().sort((a,b)=>String(b.updated_at).localeCompare(String(a.updated_at)));
  $("yourChecks").classList.toggle("hidden",!items.length);
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
  $("briefHealth").textContent=liveBrief?"Connected":"Unavailable";
  $("trustSummary").textContent=h.status==="supported"
    ?"Historical testing currently supports using these impact components as additional context."
    :"We do not yet have enough complete historical consequence labels to prove that impact-aware ranking beats hazard alone. So this page does not change the Morning Brief alert order.";
  $("trustList").innerHTML=(impactReport?.trust_contract||[]).map(x=>'<div class="trust-item">'+x+'</div>').join("");
}
async function init(){
  try{
    [impactReport,liveBrief]=await Promise.all([loadImpact(),loadBrief()]);
    renderOverview();
    renderProfiles();
    renderActionLog();
    renderTrust();
  }catch(error){
    $("overviewTitle").textContent="Impact context could not load.";
    $("overviewCopy").textContent="The page could not connect to its current evidence.";
  }
}
init();
