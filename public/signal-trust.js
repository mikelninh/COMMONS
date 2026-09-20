const $=id=>document.getElementById(id);
function pct(v){const n=Number(v);return Number.isFinite(n)?Math.round(n*100)+"%":"—"}
function pp(v){const n=Number(v);return Number.isFinite(n)?((n>0?"+":"")+Math.round(n*1000)/10+"pp"):"—"}
function falseCost(v){const n=Number(v);return Number.isFinite(n)?((n>0?"+":"")+n.toFixed(2)+"/100"):"—"}
async function loadReport(){
  const response=await fetch("./world-model/minority-convective-report.json",{cache:"no-store"});
  if(!response.ok)throw new Error("report not published");
  return response.json();
}
function verdict(el,status,passes,copy){
  el.className="verdict "+(passes?"pass":status==="insufficient"?"insufficient":"fail");
  el.textContent=copy;
}
function render(report){
  const h24=report.h24||{}, h25=report.h25||{};
  const h24h=h24.hypothesis||{}, h25h=h25.hypothesis||{};
  const h24t=h24.test||{}, h25t=h25.test||{};
  const h24m=h24t.selected||{}, h25m=h25t.selected||{};
  const h24c=h24t.comparison||{}, h25c=h25t.comparison||{};
  $("h24Status").textContent="H24 · "+String(h24h.status||"insufficient").replaceAll("_"," ").toUpperCase();
  $("h25Status").textContent="H25 · "+String(h25h.status||"insufficient").replaceAll("_"," ").toUpperCase();
  $("h24Rule").textContent=(h24.development?.selected_rule||"No rule selected").replaceAll("_"," ");
  $("h25Rule").textContent=(h25.development?.selected_rule||"No rule selected").replaceAll("_"," ");
  $("h24Update").textContent=h24h.product_update||"";
  $("h25Update").textContent=h25h.product_update||"";
  $("h24Recovery").textContent=pct(h24m.target_recovery_rate);
  $("h24False").textContent=falseCost(h24c.incremental_false_alerts_per_100);
  $("h24Precision").textContent=pp(h24c.precision_change);
  $("h24RescuePrecision").textContent=pct(h24m.rescue_only_precision);
  $("h25Recovery").textContent=pct(h25m.target_recovery_rate);
  $("h25Blind").textContent=h25t.baseline?.target_misses??"—";
  $("h25False").textContent=falseCost(h25c.incremental_false_alerts_per_100);
  const health=report.convective_evidence_health||{};
  $("convectiveHealth").textContent=String(health.status||"unknown").toUpperCase()+" · "+pct(health.bundle_ratio);
  verdict($("h24Verdict"),h24h.status,Boolean(h24t.passes_guardrails),h24t.passes_guardrails?"Passed the scarcity gates for a shadow experiment.":"Did not earn shadow ranking authority.");
  verdict($("h25Verdict"),h25h.status,Boolean(h25t.passes_guardrails),h25t.passes_guardrails?"Passed the scarcity gates for shadow convective context.":h25h.status==="insufficient"?"Evidence is insufficient; no rule change.":"Did not earn convective ranking authority.");
  const cases=h25t.blind_examples||[];
  $("blindCases").innerHTML=cases.map(item=>{
    const c=item.convective||{};
    return '<article class="case"><div class="case-head"><strong>'+item.point_id+' · '+item.decision_date+'</strong><span>'+(item.selected_rule_fired?'RULE FIRED':'RULE QUIET')+'</span></div>'+
    '<div class="case-metrics"><div><span>OBSERVED</span><b>'+item.observed_peak_mm+' mm</b></div><div><span>CAPE MAX</span><b>'+(c.cape_any_max==null?'—':Math.round(c.cape_any_max))+'</b></div><div><span>SHOWERS / GATE</span><b>'+pct(c.showers_any_ratio)+'</b></div></div></article>';
  }).join("")||'<article class="case">No evaluable blind cases in the final test.</article>';
}
loadReport().then(render).catch(()=>{
  $("h24Status").textContent="H24 · RUNNING";
  $("h25Status").textContent="H25 · RUNNING";
});
