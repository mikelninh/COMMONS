(function(){
  const ALLOWED_CLAIM_TYPES = new Set(["observed","derived","inferred","proposed"]);

  function daysBetween(a,b){
    const start=new Date(a).getTime();
    const end=new Date(b).getTime();
    if(!Number.isFinite(start)||!Number.isFinite(end))return Infinity;
    return Math.max(0,(end-start)/86400000);
  }

  function degradedState(reason){
    return {
      status:"DEGRADED",
      reason:reason||"Trust registry unavailable",
      evaluatedAt:new Date().toISOString(),
      provenanceCoverage:0,
      staleCriticalClaims:[],
      unresolvedConflicts:[],
      openHighIncidents:[],
      checks:[{
        id:"degraded-mode",
        label:"Trust registry failure produces a degraded state",
        passed:true,
        detail:"Registry unavailable; COMMONS entered degraded mode instead of claiming health."
      }]
    };
  }

  async function load(url="./trust-registry.json"){
    try{
      const response=await fetch(url,{cache:"no-store"});
      if(!response.ok)throw new Error("trust registry "+response.status);
      const registry=await response.json();
      return {registry,error:null};
    }catch(error){
      return {registry:null,error:String(error?.message||error)};
    }
  }

  function evaluate(registry,actionLoops={},now=new Date()){
    if(!registry)return degradedState("Trust registry unavailable");

    const sourceMap=new Map((registry.sources||[]).map(source=>[source.id,source]));
    const activeClaims=(registry.claims||[]).filter(claim=>claim.status==="active");
    const sourced=activeClaims.filter(claim=>
      Array.isArray(claim.source_ids) &&
      claim.source_ids.length>0 &&
      claim.source_ids.every(id=>sourceMap.has(id))
    );
    const provenanceCoverage=activeClaims.length?sourced.length/activeClaims.length:0;

    const staleCriticalClaims=activeClaims.filter(claim=>{
      if(claim.criticality!=="high" || claim.freshness_days==null)return false;
      return daysBetween(claim.as_of,now)>Number(claim.freshness_days);
    });

    const missingSources=activeClaims.flatMap(claim=>
      (claim.source_ids||[])
        .filter(id=>!sourceMap.has(id))
        .map(id=>({claimId:claim.id,sourceId:id}))
    );

    const sourcesWithoutLimits=(registry.sources||[]).filter(source=>!String(source.limitations||"").trim());
    const unresolvedConflicts=(registry.conflicts||[]).filter(item=>item.status==="unresolved");
    const openHighIncidents=(registry.incidents||[]).filter(item=>
      item.status==="open" && ["high","critical"].includes(String(item.severity).toLowerCase())
    );
    const invalidClaims=activeClaims.filter(claim=>!ALLOWED_CLAIM_TYPES.has(claim.claim_type));

    const interventions=Object.values(actionLoops||{}).flatMap(loop=>loop?.interventions||[]);
    const actionCausalitySafe=interventions.every(item=>
      String(item.uncertainty||"").trim() &&
      String(item.measure||"").trim() &&
      item.causalClaim!==true
    );
    const externalVerificationSafe=interventions
      .filter(item=>item.type==="external" && item.actionability==="DIRECT")
      .every(item=>/cannot verify|not verified|external/i.test(String(item.uncertainty||"")));

    const noInventedAction=Object.values(actionLoops||{}).every(loop=>{
      if(!/No verified public action invented/i.test(String(loop?.statusLabel||"")))return true;
      return !(loop?.interventions||[]).some(item=>
        item.type==="external" && item.actionability==="DIRECT"
      );
    });

    const checks=[
      {
        id:"provenance-coverage",
        label:"Every active claim has registered provenance",
        passed:provenanceCoverage===1,
        detail:`${sourced.length}/${activeClaims.length} active claims have complete registered provenance.`
      },
      {
        id:"critical-freshness",
        label:"No active critical claim is stale",
        passed:staleCriticalClaims.length===0,
        detail:staleCriticalClaims.length
          ? `${staleCriticalClaims.length} critical claim(s) exceeded their freshness window.`
          :"No active critical claim has exceeded its declared freshness window."
      },
      {
        id:"source-integrity",
        label:"Every referenced source exists and declares limitations",
        passed:missingSources.length===0 && sourcesWithoutLimits.length===0,
        detail:missingSources.length||sourcesWithoutLimits.length
          ? `${missingSources.length} missing source reference(s); ${sourcesWithoutLimits.length} source(s) missing limitations.`
          :"All referenced sources are registered and state limitations."
      },
      {
        id:"conflict-safety",
        label:"No unresolved conflict is hidden",
        passed:unresolvedConflicts.length===0,
        detail:unresolvedConflicts.length
          ? `${unresolvedConflicts.length} unresolved source conflict(s).`
          :"No unresolved source conflict is currently registered."
      },
      {
        id:"incident-safety",
        label:"No open high-severity trust incident",
        passed:openHighIncidents.length===0,
        detail:openHighIncidents.length
          ? `${openHighIncidents.length} high-severity trust incident(s) remain open.`
          :"No high-severity trust incident is open."
      },
      {
        id:"claim-taxonomy",
        label:"Every claim has an explicit epistemic type",
        passed:invalidClaims.length===0,
        detail:invalidClaims.length
          ? `${invalidClaims.length} claim(s) use an invalid type.`
          :"Every active claim is observed, derived, inferred or proposed."
      },
      {
        id:"action-causality",
        label:"Action paths preserve uncertainty and avoid causal overclaiming",
        passed:actionCausalitySafe,
        detail:actionCausalitySafe
          ?"Every intervention declares uncertainty and a measurement target; no intervention declares itself causal."
          :"One or more interventions are missing uncertainty/measurement or declare causal certainty."
      },
      {
        id:"external-action-verification",
        label:"Direct external actions admit verification limits",
        passed:externalVerificationSafe,
        detail:externalVerificationSafe
          ?"Every direct external action explicitly admits external verification limits."
          :"A direct external action does not clearly disclose verification limits."
      },
      {
        id:"no-invented-action",
        label:"Stories may explicitly expose no verified direct action",
        passed:noInventedAction,
        detail:noInventedAction
          ?"No-action safety states contain no direct external execution path."
          :"A story marked as having no verified public action still exposes a direct external action."
      },
      {
        id:"degraded-mode",
        label:"Trust registry failure produces a degraded state",
        passed:degradedState().status==="DEGRADED",
        detail:"Evaluator has an explicit degraded state for registry failure."
      }
    ];

    const requiredIds=new Set((registry.evaluation_requirements||[])
      .filter(item=>item.required)
      .map(item=>item.id));
    const requiredChecks=checks.filter(check=>requiredIds.has(check.id));
    const allRequiredPass=requiredChecks.every(check=>check.passed);

    const status=(
      provenanceCoverage===1 &&
      staleCriticalClaims.length===0 &&
      unresolvedConflicts.length===0 &&
      openHighIncidents.length===0 &&
      allRequiredPass
    ) ? "HEALTHY" : "DEGRADED";

    return {
      status,
      reason:status==="HEALTHY"?"All required trust checks pass.":"One or more required trust checks fail.",
      evaluatedAt:new Date(now).toISOString(),
      provenanceCoverage,
      staleCriticalClaims,
      missingSources,
      sourcesWithoutLimits,
      unresolvedConflicts,
      openHighIncidents,
      invalidClaims,
      checks,
      passedChecks:checks.filter(check=>check.passed).length,
      totalChecks:checks.length
    };
  }

  function claimsForStory(registry,storyId){
    return (registry?.claims||[]).filter(claim=>claim.story_id===storyId);
  }

  function sourceById(registry,id){
    return (registry?.sources||[]).find(source=>source.id===id)||null;
  }

  window.COMMONS_TRUST={
    load,
    evaluate,
    degradedState,
    claimsForStory,
    sourceById,
    daysBetween
  };
})();