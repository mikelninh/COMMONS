const $=id=>document.getElementById(id);
function pct(v){const n=Number(v);return Number.isFinite(n)?Math.round(n*100)+"%":"—"}
function signed(v,suffix=""){const n=Number(v);if(!Number.isFinite(n))return "—";return (n>0?"+":"")+n.toFixed(2)+suffix}
async function getReport(){
  const response=await fetch("./world-model/deep-miss-report.json",{cache:"no-store"});
  if(!response.ok)throw new Error("H23 report not published yet");
  return response.json();
}
function guard(label,value,limit,pass,detail){
  return '<article class="guard '+(pass?'pass':'fail')+'"><span>'+label+'</span><b>'+value+'</b><small>'+detail+' · '+(pass?'PASS':'FAIL')+'</small></article>';
}
function render(report){
  const h=report.hypothesis||{};
  const test=report.test||{};
  const selected=test.selected||{};
  const comparison=test.comparison||{};
  const semantics=report.live_semantics_correction||{};
  $("status").textContent="H23 · "+String(h.status||"insufficient").replaceAll("_"," ").toUpperCase();
  $("h21Deep").textContent=semantics.h21_exact_day_deep_cases??"—";
  $("semanticsResolved").textContent=(semantics.no_longer_deep_under_live_72h_window??"—");
  $("recovery").textContent=pct(selected.deep_miss_recovery_rate);
  $("falseCost").textContent=comparison.incremental_false_alerts_per_100==null?"—":signed(comparison.incremental_false_alerts_per_100,"");
  $("strategy").textContent=(test.selected_strategy||"No strategy selected").replaceAll("_"," ");
  $("decisionCopy").textContent=h.product_update||"No product-rule update yet.";
  const rec=Number(selected.deep_miss_recovery_rate);
  const burden=Number(comparison.incremental_false_alerts_per_100);
  const precision=Number(comparison.precision_change);
  $("guardrails").innerHTML=
    guard("DEEP-MISS RECOVERY",pct(rec),"≥20%",Number.isFinite(rec)&&rec>=.20,"target ≥20%")+
    guard("EXTRA FALSE ALERTS",Number.isFinite(burden)?burden.toFixed(2)+"/100":"—","≤3/100",Number.isFinite(burden)&&burden<=3,"budget ≤3/100")+
    guard("PRECISION CHANGE",Number.isFinite(precision)?signed(precision*100,"pp"):"—","≥−5pp",Number.isFinite(precision)&&precision>=-.05,"floor −5pp");
  const counts=(report.failure_taxonomy||{}).counts||{};
  const entries=[
    ["MODEL + SPATIAL",counts.model_and_spatial||0],
    ["ONE MODEL SAW IT",counts.one_model_saw_it||0],
    ["SPATIAL DISPLACEMENT",counts.spatial_displacement||0],
    ["CONSENSUS BLIND",counts.consensus_blind||0]
  ];
  const max=Math.max(1,...entries.map(x=>x[1]));
  $("taxonomy").innerHTML=entries.map(([name,count])=>
    '<div class="bar-row"><label>'+name+'</label><div class="track"><i style="width:'+((count/max)*100)+'%"></i></div><b>'+count+'</b></div>'
  ).join("");
  const examples=(report.failure_taxonomy||{}).examples||[];
  $("cases").innerHTML=examples.slice(0,12).map(item=>
    '<article class="case"><div class="case-head"><strong>'+item.point_id+' · '+item.decision_date+'</strong><span>'+String(item.failure_mode||"").replaceAll("_"," ").toUpperCase()+'</span></div>'+
    '<div class="case-metrics"><div><span>OBSERVED PEAK</span><b>'+item.observed_peak_mm+' mm</b></div><div><span>HEAVY GATE</span><b>'+item.heavy_gate_mm+' mm</b></div><div><span>BASELINE</span><b>'+pct(item.baseline_score)+'</b></div></div></article>'
  ).join("")||'<div class="case">No final-test deep misses to display.</div>';
}
getReport().then(render).catch(error=>{
  $("status").textContent="H23 · RUNNING";
  $("strategy").textContent="The experiment is still running.";
  $("decisionCopy").textContent="This page will populate automatically when deep-miss-report.json lands.";
});
