const $ = id => document.getElementById(id);

async function getJson(url){
  const response=await fetch(url,{cache:"no-store"});
  if(!response.ok)throw new Error(url+" "+response.status);
  return response.json();
}

function fmt(value,unit=""){
  return value===null||value===undefined?"—":value+unit;
}

function coverageLabel(value){
  return {
    live_pilot:"LIVE PILOT",
    physical_context:"PHYSICAL CONTEXT",
    story_layer_only:"STORY LAYER",
    ambient_live_source:"AMBIENT LIVE"
  }[value]||String(value||"planned").replaceAll("_"," ").toUpperCase();
}

function renderCouncil(loop){
  const council=loop?.forecast_council;
  if(!council?.members?.length){
    $("forecastCouncil").innerHTML='<div class="empty-state">No live model snapshot is available yet.</div>';
    $("forecastConsensus").innerHTML="";
    return;
  }
  $("forecastCouncil").innerHTML=council.members.map(member=>
    '<div class="council-member">'+
      '<b>'+member.label+'</b>'+
      '<span>'+fmt(member.precip_72h_mm," mm rain")+'</span>'+
      '<span>'+fmt(member.temp_max_72h_c,"°C max")+'</span>'+
      '<strong>'+fmt(member.gust_max_72h_kmh," km/h gust")+'</strong>'+
    '</div>'
  ).join("");

  const c=council.consensus||{};
  $("forecastConsensus").innerHTML=
    '<div class="consensus-main">'+
      '<strong>'+fmt(c.precip_72h_mm_median," mm")+'</strong>'+
      '<span>median 72h precipitation</span>'+
    '</div>'+
    '<div class="agreement">'+
      'Rain agreement: <b>'+(c.precip_agreement||"unknown")+'</b> · '+
      'Temperature: <b>'+(c.temperature_agreement||"unknown")+'</b> · '+
      'Gusts: <b>'+(c.gust_agreement||"unknown")+'</b><br>'+
      (council.interpretation||"")+
    '</div>';
}

function renderMemory(loop){
  const memory=loop?.weather_memory;
  if(!memory||memory.status!=="ok"){
    $("weatherMemory").innerHTML='<div class="empty-state">Historical memory is not available in this snapshot yet.</div>';
    return;
  }
  const analogues=(memory.analogues||[]).map(item=>
    '<div class="analogue"><b>'+item.start_date+'</b><span>'+
    item.precip_72h_mm+' mm · Δ '+item.difference_mm+' mm</span></div>'
  ).join("");
  $("weatherMemory").innerHTML=
    '<div class="memory-number">'+fmt(memory.seasonal_percentile,"%")+
      ' <small>seasonal percentile</small></div>'+
    '<div class="memory-copy">Compared with three-day ERA5 precipitation totals within ±'+
      memory.season_window_days+' days of this time of year, across '+
      memory.historical_period_start+' → '+memory.historical_period_end+'.</div>'+
    '<div class="analogue-list">'+analogues+'</div>'+
    '<div class="truth-note">'+(memory.limitation||"")+'</div>';
}

function renderFlood(loop){
  const flood=loop?.flood_signal;
  if(!flood||flood.status!=="ok"){
    $("floodSignal").innerHTML='<div class="empty-state">Flood guidance is not available in this snapshot yet.</div>';
    return;
  }
  $("floodSignal").innerHTML=
    '<div class="memory-number">'+fmt(flood.historical_percentile,"%")+
      ' <small>historical discharge percentile</small></div>'+
    '<div class="memory-copy">Forecast peak: <b>'+
      fmt(flood.forecast_peak_discharge_m3s," m³/s")+'</b> on '+
      flood.forecast_peak_date+'. Historical baseline begins '+flood.historical_start+'.</div>'+
    '<div class="truth-note">'+(flood.limitation||"")+'</div>';
}

function renderLoops(catalog,snapshot){
  const snapshotMap=new Map((snapshot?.loops||[]).map(loop=>[loop.id,loop]));
  $("loopsGrid").innerHTML=(catalog.loops||[]).map(loop=>{
    const state=snapshotMap.get(loop.id);
    const errors=state?.forecast_council?.source_errors?.length||0;
    return '<article class="loop-card">'+
      '<div class="loop-meta">'+
        '<span>'+String(loop.order).padStart(2,"0")+' · '+loop.human_anchor+'</span>'+
        '<span class="coverage-'+loop.coverage+'">'+coverageLabel(loop.coverage)+'</span>'+
      '</div>'+
      '<h3>'+loop.title+'</h3>'+
      '<p>'+loop.question+'</p>'+
      '<div class="loop-sources">'+loop.live_sources.join(" · ")+
        (errors?' · '+errors+' source error(s)':'')+'</div>'+
    '</article>';
  }).join("");
}

async function init(){
  let snapshot;
  try{
    snapshot=await getJson("./world-model/latest.json");
  }catch(error){
    snapshot=await getJson("./world-model/seed.json");
  }
  const catalog=await getJson("./world-model/loops.json");
  const live=Boolean(snapshot.generated_at);
  $("wmStatus").textContent=live
    ? "Live research snapshot loaded. The model council and memory layer are source-derived, not generated prose."
    : "Waiting for the first scheduled live snapshot. No current weather values are fabricated.";
  $("wmUpdated").textContent=live
    ? "snapshot · "+new Date(snapshot.generated_at).toLocaleString()
    : "no live snapshot yet";

  const pilot=(snapshot.loops||[]).find(loop=>loop.id==="water-rises");
  if(pilot?.watchpoint){
    $("pilotLocation").textContent=pilot.watchpoint.name+" · "+pilot.watchpoint.country;
  }
  renderCouncil(pilot);
  renderMemory(pilot);
  renderFlood(pilot);
  renderLoops(catalog,snapshot);
}

init().catch(error=>{
  $("wmStatus").textContent="World Model data could not be loaded: "+error.message;
});
