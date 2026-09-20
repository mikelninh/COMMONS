const $=id=>document.getElementById(id);
function pct(v){const n=Number(v);return Number.isFinite(n)?Math.round(n*100)+"%":"—"}
function num(v){const n=Number(v);return Number.isFinite(n)?n.toFixed(2):"—"}
function human(v){const n=Number(v);if(!Number.isFinite(n))return "—";if(n>=1e6)return (n/1e6).toFixed(1)+"M";if(n>=1e3)return Math.round(n/1e3)+"k";return Math.round(n)}
async function load(){const r=await fetch("./world-model/impact-report.json",{cache:"no-store"});if(!r.ok)throw new Error("impact report not published");return r.json()}
function component(label,value,copy){return '<div class="component"><span>'+label+'</span><b>'+value+'</b><p>'+copy+'</p></div>'}
function render(report){
  const bench=report.benchmark||{}, h=bench.hypothesis||{}, health=report.source_health||{};
  $("h27Status").textContent="H27 · "+String(h.status||"insufficient").replaceAll("_"," ").toUpperCase();
  $("sourceHealth").textContent="EM-DAT LABEL COVERAGE · "+pct(health.emdat_coverage);
  $("benchmarkCopy").textContent=h.product_update||"Impact ordering remains context only.";
  $("hazardAP").textContent=num(bench.hazard_only?.average_precision);
  $("impactAP").textContent=num(bench.impact_aware?.average_precision);
  $("apGain").textContent=num(bench.comparison?.average_precision_gain);
  $("recallGain").textContent=pct(bench.comparison?.top20_recall_gain);
  $("profiles").innerHTML=(report.profiles||[]).map(profile=>{
    const c=profile.components||{}, exp=c.exposure||{}, infra=c.infrastructure||{}, hist=c.historical_consequence||{};
    const infraValue=infra.health_facilities==null?"—":(infra.health_facilities+" health · "+(infra.bridges||0)+" bridges");
    const actions=(profile.action_options||[]).map(a=>'<span class="action">'+a.label+'</span>').join("");
    return '<article class="profile"><h3>'+profile.name+'</h3><small>'+profile.country+'</small>'+
      component("EXPOSURE",human(exp.population_within_radius)+" people","within ~"+(exp.radius_km??"—")+" km · context only")+
      component("CRITICAL INFRASTRUCTURE",infraValue,"nearby assets, not damage estimates")+
      component("HISTORICAL CONSEQUENCE",(hist.consequential_events??0)+" consequential precedents",(hist.nearby_events??0)+" nearby GDACS events reviewed")+
      '<div class="actions">'+actions+'</div></article>';
  }).join("");
  $("trustList").innerHTML=(report.trust_contract||[]).map(x=>'<div class="trust-item">'+x+'</div>').join("");
}
load().then(render).catch(()=>{$("h27Status").textContent="H27 · RUNNING";$("benchmarkCopy").textContent="Impact v0 is collecting consequence and infrastructure evidence.";});
