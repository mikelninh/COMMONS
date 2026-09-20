const $ = id => document.getElementById(id);
const qs = (sel, root=document) => root.querySelector(sel);
const qsa = (sel, root=document) => [...root.querySelectorAll(sel)];
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson";
const EONET = "https://eonet.gsfc.nasa.gov/api/v3/events/geojson?status=open&limit=120";
const GDACS = "https://gdacs.org/xml/rss_7d.xml";
const WORLD_ATLAS = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

const sourceMeta = {
  "USGS": {
    freshness: "LIVE",
    cadence: "updated about every minute",
    url: "https://earthquake.usgs.gov/earthquakes/feed/",
    scope: "Rolling public earthquake feed. Magnitude is not a measure of human impact."
  },
  "NASA EONET": {
    freshness: "NEAR-REAL-TIME",
    cadence: "curated open-event feed",
    url: "https://eonet.gsfc.nasa.gov/",
    scope: "Curated natural-event tracking, not a complete census of every event on Earth."
  },
  "GDACS": {
    freshness: "NEAR-REAL-TIME",
    cadence: "7-day disaster alert feed",
    url: "https://gdacs.org/",
    scope: "Situational-awareness alerts. An alert is not itself a casualty or need estimate."
  }
};

const STORIES = Array.isArray(window.WORLD_PULSE_STORIES) ? window.WORLD_PULSE_STORIES : [];
const ACTION_LOOPS = window.WORLD_PULSE_ACTION_LOOPS || {};
const ACTION_LEDGER_KEY = "commons.action-ledger.v1";
if(!STORIES.length) throw new Error("WORLD PULSE story catalog is missing");

let activeStory = STORIES[0];
let TIME_SCENES = [];
let THREADS = [];
let BLOOM = [];

function storyById(id){
  return STORIES.find(story=>story.id===id || story.slug===id) || null;
}

function nextStory(){
  const index=STORIES.findIndex(story=>story.id===activeStory.id);
  return STORIES[(index+1)%STORIES.length];
}

function hexToRgba(hex,alpha=1){
  const clean=String(hex||"#ffffff").replace("#","");
  const value=parseInt(clean.length===3?clean.split("").map(c=>c+c).join(""):clean,16);
  const r=(value>>16)&255,g=(value>>8)&255,b=value&255;
  return `rgba(${r},${g},${b},${alpha})`;
}

function rebuildStoryAssets(){
  TIME_SCENES=[
    0,
    Math.max(1,Math.round((activeStory.scenes.length-1)*.34)),
    Math.max(2,Math.round((activeStory.scenes.length-1)*.67)),
    activeStory.scenes.length-1
  ];

  THREADS=activeStory.thread?[{
    startLat:activeStory.thread.startLat,
    startLng:activeStory.thread.startLng,
    endLat:activeStory.thread.endLat,
    endLng:activeStory.thread.endLng,
    note:"Semantic response pathway; not a literal tracked route."
  }]:[];

  BLOOM=(activeStory.bloom||[]).map(([lat,lon,radius],i)=>({
    kind:"bloom",
    id:"bloom:"+activeStory.id+":"+i,
    lat,lon,radius
  }));

  actionPoint={
    kind:"action",
    action:true,
    storyId:activeStory.id,
    id:activeStory.id,
    lat:activeStory.lat,
    lon:activeStory.lon,
    source:"COMMONS STORY",
    title:activeStory.country+" · "+activeStory.title
  };

  memoryPoint={
    kind:"memory",
    storyId:activeStory.id,
    id:"memory:"+activeStory.id,
    lat:activeStory.lat,
    lon:activeStory.lon,
    source:"COMMONS MEMORY",
    title:activeStory.country+" · "+activeStory.statusLabel
  };
}

let actionPoint;
let memoryPoint;
rebuildStoryAssets();

const storyPoints=STORIES.map(story=>({
  kind:"story",
  storyId:story.id,
  id:"story:"+story.id,
  lat:story.lat,
  lon:story.lon,
  source:"WORLD PULSE STORY",
  title:story.country+" · "+story.title,
  color:story.colors?.memory||story.colors?.attention||"#d2b06d"
}));

let countries = [];
let signals = [];
let sourceStates = [];
let storyIndex = 0;
let storyPlaying = false;
let storyTimer = null;
let scrollRAF = null;
let autoScrollRAF = null;
let lastAutoTime = 0;
let threadStrength = 0;
let bloomStrength = 0;
let memoryStrength = 0;
let lastSemanticFrame = "";
let lastScrollProgress = 0;
let lastScrollTime = performance.now();
let audioCtx = null;
let audioNodes = null;
let soundEnabled = false;
let lastSoundMilestone = -1;
let currentMilestone = 0;
let currentSignal = null;
let actionLabMode = "current";
let trustRegistry = null;
let trustLoadError = null;
let trustTab = "status";
let trustMode = "simple";
let trustReport = window.COMMONS_TRUST?.degradedState("Trust checks not loaded yet") || {
  status:"DEGRADED", provenanceCoverage:0, staleCriticalClaims:[], unresolvedConflicts:[],
  openHighIncidents:[], checks:[], passedChecks:0, totalChecks:0
};
let initialized = false;

const world = Globe({rendererConfig:{antialias:true,alpha:true}})($("globe"))
  .backgroundColor("rgba(0,0,0,0)")
  .showAtmosphere(true)
  .atmosphereColor("#667267")
  .atmosphereAltitude(.105)
  .showGraticules(true)
  .pointLat(d=>d.lat)
  .pointLng(d=>d.lon)
  .pointColor(d=>{
    if(d.kind==="bloom") return hexToRgba(activeStory.colors.outcome,0.05+bloomStrength*.38);
    if(d.kind==="action") return activeStory.colors.attention;
    if(d.kind==="memory") return hexToRgba(activeStory.colors.memory,0.42+memoryStrength*.52);
    if(d.kind==="story") return d.color;
    return sourceColor(d.source);
  })
  .pointAltitude(d=>d.kind==="bloom"?.0015:d.kind==="action"?.016:d.kind==="memory"?.012:d.kind==="story"?.012:.012)
  .pointRadius(d=>d.kind==="bloom"?d.radius*(0.18+bloomStrength*.82):d.kind==="action"?.15:d.kind==="memory"?(.06+memoryStrength*.08):d.kind==="story"?.085:Math.max(.05,Math.min(.13,.045+(Number(d.magnitude)||1)*.012)))
  .pointResolution(16)
  .pointLabel(()=>"")
  .onPointClick(d=>{
    if(d.kind==="action") return startStory(0);
    if(d.kind==="story") return enterStory(d.storyId,0);
    if(d.kind==="bloom"||d.kind==="memory") return;
    focusSignal(d);
  })
  .ringsData([])
  .ringLat(d=>d.lat)
  .ringLng(d=>d.lon)
  .ringAltitude(.003)
  .ringColor(d=>()=>d.kind==="memory"?hexToRgba(activeStory.colors.memory,.38):d.kind==="action"?hexToRgba(activeStory.colors.attention,.58):d.kind==="story"?hexToRgba(d.color,.26):"rgba(197,201,192,.18)")
  .ringMaxRadius(d=>d.kind==="memory"?2.2:d.kind==="action"?5.4:d.kind==="story"?1.8:2.25)
  .ringPropagationSpeed(d=>d.kind==="memory"?.26:d.kind==="action"?.62:d.kind==="story"?.22:.42)
  .ringRepeatPeriod(d=>d.kind==="memory"?4200:d.kind==="action"?2500:d.kind==="story"?5200:3900)
  .arcsData([])
  .arcStartLat("startLat")
  .arcStartLng("startLng")
  .arcEndLat("endLat")
  .arcEndLng("endLng")
  .arcColor(()=>[
    hexToRgba(activeStory.colors.attention,0.015+threadStrength*.06),
    hexToRgba(activeStory.colors.attention,threadStrength*.9)
  ])
  .arcAltitude(.035)
  .arcStroke(()=>.06+threadStrength*.42)
  .arcDashLength(.28)
  .arcDashGap(1.05)
  .arcDashAnimateTime(3300)
  .polygonsData([])
  .polygonCapColor(countryColor)
  .polygonSideColor(()=>"rgba(20,22,19,.15)")
  .polygonStrokeColor(()=>"rgba(239,238,231,.055)")
  .polygonAltitude(.004)
  .polygonLabel(()=>"");

world.controls().autoRotate = !reduceMotion;
world.controls().autoRotateSpeed = .032;
world.controls().enablePan = false;
world.controls().minDistance = 125;
world.controls().maxDistance = 560;
world.pointOfView({lat:14,lng:35,altitude:2.08},0);

function resize(){
  world.width(innerWidth).height(innerHeight);
}
window.addEventListener("resize",resize);
resize();

function countryColor(d){
  const id=String(d?.id??"").padStart(3,"0");
  const selected=id===activeStory.countryId;
  if(selected && currentMilestone>=2) return hexToRgba(activeStory.colors.outcome,.24);
  if(selected) return hexToRgba(activeStory.colors.attention,.18);
  return "rgba(139,142,130,.145)";
}

function sourceColor(source){
  return ({
    "USGS":"rgba(143,170,183,.72)",
    "NASA EONET":"rgba(154,203,151,.67)",
    "GDACS":"rgba(210,176,109,.73)"
  })[source] || "rgba(199,197,187,.55)";
}

function sceneOffset(scene){
  if(innerWidth<650) return [0,-105];
  return scene.offset || [0,0];
}

function renderCalmOrientation(){
  if(!$("calmOrientation"))return;
  const improving=STORIES.filter(story=>
    (story.bloom||[]).length>0 || String(story.status||"").includes("ELIMINATION")
  ).length;

  let directActions="—";
  let stale="—";
  if(trustRegistry){
    evaluateTrustNow();
    stale=String(trustReport.staleCriticalClaims?.length||0);
    directActions=String(STORIES.filter(story=>{
      const loop=ACTION_LOOPS[story.id];
      const hasDirect=(loop?.interventions||[]).some(item=>
        item.type==="external" && item.actionability==="DIRECT"
      );
      return hasDirect && trustGateForStory(story.id).allowed;
    }).length);
  }

  $("orientationStories").textContent=String(STORIES.length);
  $("orientationImproving").textContent=String(improving);
  $("orientationActions").textContent=directActions;
  $("orientationStale").textContent=stale;
}

function storyEditorialSummary(story){
  const summaries={
    "nepal-flash-floods-2026":"Floods hit northern Nepal. A verified response is underway, and new evidence shows safe water was restored for around 2,000 people.",
    "bhutan-rabies-elimination-2026":"Bhutan reached a rare public-health milestone: WHO validated the elimination of dog-transmitted human rabies as a public-health problem.",
    "drc-ebola-bundibugyo-2026":"The Ebola outbreak remains unresolved. There are encouraging signs in some places, but WHO says the epidemic is still growing overall."
  };
  return summaries[story.id] || story.subtitle;
}

function storyReadTime(story){
  return Math.max(1,Math.round((story.scenes?.length||6)*.18));
}

function renderReturnUpdates(){
  if(!$("returnUpdates"))return;
  const receipts=loadActionLedger();
  const grouped=STORIES.map(story=>{
    const related=receipts.filter(entry=>entry.storyId===story.id);
    if(!related.length)return null;
    const following=related.some(entry=>entry.status==="following");
    const acted=related.some(entry=>["self_reported_complete","external_opened","share_completed","share_prepared"].includes(entry.status));
    const newer=related.some(hasNewEvidence);
    if(!following&&!acted)return null;
    return {story,following,acted,newer};
  }).filter(Boolean);

  if(!grouped.length){
    $("returnUpdates").classList.add("hidden");
    $("returnUpdates").innerHTML="";
    return;
  }

  $("returnUpdates").classList.remove("hidden");
  $("returnUpdates").innerHTML=`
    <div class="return-heading">
      <span>SINCE YOU WERE HERE</span>
      <h2>${grouped.some(item=>item.newer)?"Something changed.":"You’re following "+grouped.length+" stor"+(grouped.length===1?"y":"ies")+"."}</h2>
    </div>
    <div class="return-list">
      ${grouped.map(({story,newer,following,acted})=>`
        <button class="return-item" data-return-story="${escapeHtml(story.id)}">
          <span class="return-dot ${newer?"new":""}"></span>
          <span>
            <b>${escapeHtml(story.country)} · ${escapeHtml(story.title)}</b>
            <small>${newer?"New official evidence is available":following?"You’re following this story":"You recorded an action here"}</small>
          </span>
          <strong>${newer?"SEE WHAT CHANGED":"OPEN"}</strong>
        </button>
      `).join("")}
    </div>
  `;

  qsa("[data-return-story]",$("returnUpdates")).forEach(button=>{
    button.onclick=()=>enterStory(button.dataset.returnStory,Math.max(0,(storyById(button.dataset.returnStory)?.scenes?.length||1)-2));
  });
}

function renderDailyHome(){
  if(!$("dailySummary"))return;
  const improving=STORIES.filter(story=>
    (story.bloom||[]).length>0 || String(story.status||"").includes("ELIMINATION")
  ).length;
  let direct=0;
  if(trustRegistry){
    direct=STORIES.filter(story=>{
      const loop=ACTION_LOOPS[story.id];
      return (loop?.interventions||[]).some(item=>
        item.type==="external" && item.actionability==="DIRECT" && trustGateForStory(story.id).allowed
      );
    }).length;
  }
  $("dailyStoryCount").textContent=String(STORIES.length);
  $("dailyActionCount").textContent=String(direct);
  $("dailyImprovedCount").textContent=String(improving);
  renderReturnUpdates();
}

function renderStoryLibrary(){
  $("storyCards").innerHTML=STORIES.map(story=>{
    const receipts=ledgerForStory(story.id);
    const newer=receipts.some(hasNewEvidence);
    const following=receipts.some(entry=>entry.status==="following");
    const acted=receipts.some(entry=>["self_reported_complete","external_opened","share_completed","share_prepared"].includes(entry.status));
    const state=newer?"NEW SINCE YOU FOLLOWED":following?"FOLLOWING":acted?"ACTION RECORDED":story.statusLabel;

    return `
      <button class="story-card daily-story-card" data-story-id="${escapeHtml(story.id)}" style="--card-accent:${escapeHtml(story.colors.memory||story.colors.attention)}">
        <span class="daily-story-top">
          <span class="story-card-country">${escapeHtml(story.country)} · ${escapeHtml(state)}</span>
          <span class="daily-read-time">${storyReadTime(story)} min</span>
        </span>
        <span class="story-card-title">${escapeHtml(story.title)}</span>
        <span class="daily-story-summary">${escapeHtml(storyEditorialSummary(story))}</span>
        <span class="daily-story-bottom"><span>Updated ${escapeHtml(story.updatedAt)}</span><strong>Read story →</strong></span>
      </button>
    `;
  }).join("");

  qsa(".story-card",$("storyCards")).forEach(card=>{
    card.onclick=()=>enterStory(card.dataset.storyId,0);
  });
  renderCalmOrientation();
  renderDailyHome();
}

function updateStoryChrome(){
  const root=document.documentElement;
  root.style.setProperty("--amber",activeStory.colors.attention);
  root.style.setProperty("--green",activeStory.colors.outcome);

  $("enterBtn").textContent="Enter "+activeStory.country+" →";
  $("featuredMeta").textContent=activeStory.country+" · "+activeStory.statusLabel;
  $("featuredTitle").textContent=activeStory.title+" — "+activeStory.subtitle;
  $("currentStory").setAttribute("aria-label","Enter "+activeStory.country+" — "+activeStory.title);

  $("storyIndex").innerHTML=`<b>${escapeHtml(activeStory.country.toUpperCase())}</b> · ${escapeHtml(activeStory.title.toUpperCase())} · ${escapeHtml(activeStory.status)}`;
  $("story").dataset.status=activeStory.status.includes("ELIMINATION")?"elimination":"open";

  $("timeLabels").innerHTML=["What happened","Response","Is it working?","What now?"].map(label=>`<span>${escapeHtml(label)}</span>`).join("");
  const sig=qsa(".signature span");
  activeStory.grammar.forEach((label,index)=>{
    if(sig[index]){
      const i=sig[index].querySelector("i");
      sig[index].innerHTML="";
      if(i)sig[index].appendChild(i);
      sig[index].append(document.createTextNode(label));
    }
  });

  $("terrainCaption").textContent=activeStory.terrain.caption;
  $("terrainDisclosure").textContent=activeStory.terrain.disclosure;
  $("memoryText").textContent=activeStory.country+" · 2026 · "+activeStory.statusLabel.toLowerCase();

  renderStoryLibrary();
  renderEvidence();
}

function selectStory(id){
  const story=storyById(id);
  if(!story)return false;
  activeStory=story;
  rebuildStoryAssets();
  storyIndex=0;
  currentMilestone=0;
  threadStrength=0;
  bloomStrength=0;
  memoryStrength=0;
  lastSemanticFrame="";
  $("scrollNarrative").innerHTML="";
  updateStoryChrome();
  if(countries.length)buildTerrainMap();
  world.polygonCapColor(countryColor);
  if(countries.length)world.polygonsData([...countries]);
  updateAtlasLayers($("story").classList.contains("active"));
  return true;
}

function enterStory(id,index=0){
  if(!selectStory(id))return;
  startStory(index);
}

function openStories(){
  hideOpening();
  if($("story").classList.contains("active"))stopStory(true);
  closeAuxiliaryLayers();
  $("home").classList.remove("hidden");
  setHomeGlobe();
  requestAnimationFrame(()=>$("storyLibrary")?.scrollIntoView({behavior:reduceMotion?"auto":"smooth",block:"end"}));
}

function setHomeGlobe(){
  resetCinematicVisuals();
  currentMilestone=0;
  world.controls().autoRotate=!reduceMotion;
  world.globeOffset(innerWidth<650?[0,-90]:[250,-5]);
  world.pointOfView({lat:14,lng:35,altitude:2.08},reduceMotion?0:950);
  updateAtlasLayers(false);
}

function flattenCoordinateRings(geometry){
  if(!geometry)return[];
  if(geometry.type==="Polygon")return geometry.coordinates;
  if(geometry.type==="MultiPolygon")return geometry.coordinates.flat();
  return[];
}

function buildTerrainMap(){
  const country=countries.find(d=>String(d?.id??"").padStart(3,"0")===activeStory.countryId);
  if(!country)return;

  const rings=flattenCoordinateRings(country.geometry);
  const points=rings.flat();
  if(!points.length)return;

  const lons=points.map(p=>p[0]);
  const lats=points.map(p=>p[1]);
  const minLon=Math.min(...lons),maxLon=Math.max(...lons);
  const minLat=Math.min(...lats),maxLat=Math.max(...lats);
  const pad=65;
  const width=1000-pad*2;
  const height=640-pad*2;
  const spanLon=Math.max(.001,maxLon-minLon);
  const spanLat=Math.max(.001,maxLat-minLat);
  const scale=Math.min(width/spanLon,height/spanLat);
  const drawnW=spanLon*scale,drawnH=spanLat*scale;
  const ox=(1000-drawnW)/2;
  const oy=(640-drawnH)/2;

  const project=([lon,lat])=>[
    ox+(lon-minLon)*scale,
    oy+(maxLat-lat)*scale
  ];

  const path=rings.map(ring=>{
    if(!ring.length)return"";
    const [x0,y0]=project(ring[0]);
    const tail=ring.slice(1).map(p=>{
      const [x,y]=project(p);
      return `L${x.toFixed(1)} ${y.toFixed(1)}`;
    }).join(" ");
    return `M${x0.toFixed(1)} ${y0.toFixed(1)} ${tail} Z`;
  }).join(" ");

  $("terrainCountry").setAttribute("d",path);
  $("terrainClipPath").setAttribute("d",path);

  const contourMarkup=Array.from({length:27},(_,i)=>{
    const y=58+i*21.5;
    const amp=16+(i%5)*5;
    const phase=(i%4)*37;
    const y1=y+Math.sin((i+1)*.81)*amp;
    const y2=y-Math.cos((i+2)*.63)*amp;
    return `<path d="M-80 ${y.toFixed(1)} C180 ${(y1-phase*.07).toFixed(1)} 325 ${(y2+phase*.04).toFixed(1)} 520 ${y.toFixed(1)} S820 ${(y1+12).toFixed(1)} 1080 ${(y2-8).toFixed(1)}"></path>`;
  }).join("");
  $("terrainContours").innerHTML=contourMarkup;
}

async function loadCountries(){
  try{
    const r=await fetch(WORLD_ATLAS,{cache:"force-cache"});
    if(!r.ok) throw new Error("world atlas "+r.status);
    const topo=await r.json();
    if(!window.topojson) throw new Error("topojson unavailable");
    countries=window.topojson.feature(topo,topo.objects.countries).features;
    world.polygonsData(countries);
    buildTerrainMap();
  }catch(e){
    countries=[];
  }
}

function iso(v){
  if(!v)return null;
  const d=new Date(v);
  return Number.isNaN(d.getTime())?null:d.toISOString();
}

function age(v){
  if(!v)return "time unknown";
  const m=Math.max(0,Math.round((Date.now()-new Date(v))/60000));
  if(m<60)return m+"m ago";
  const h=Math.round(m/60);
  if(h<48)return h+"h ago";
  return Math.round(h/24)+"d ago";
}

function attentionReasons(s){
  const r=[];
  if(s.source==="USGS"&&Number(s.magnitude)>=6)r.push("USGS magnitude ≥ 6.0");
  else if(s.source==="USGS"&&Number(s.magnitude)>=5)r.push("USGS magnitude ≥ 5.0");
  if(s.source==="GDACS"&&/red/i.test(s.severity||""))r.push("GDACS red alert");
  else if(s.source==="GDACS"&&/orange/i.test(s.severity||""))r.push("GDACS orange alert");
  return r;
}

async function fetchUSGS(){
  const r=await fetch(USGS,{cache:"no-store"});
  if(!r.ok)throw new Error("USGS "+r.status);
  const j=await r.json();
  return j.features.map(f=>({
    id:"usgs:"+f.id,source:"USGS",title:f.properties.title||"Earthquake",
    lat:f.geometry.coordinates[1],lon:f.geometry.coordinates[0],
    time:iso(f.properties.updated||f.properties.time),
    magnitude:f.properties.mag,severity:f.properties.alert||null,url:f.properties.url||null
  }));
}

async function fetchEONET(){
  const r=await fetch(EONET,{cache:"no-store"});
  if(!r.ok)throw new Error("NASA "+r.status);
  const j=await r.json();
  return j.features.map(f=>{
    const p=f.properties||{},g=f.geometry||{},c=g.coordinates||[];
    if(g.type!=="Point"||c.length<2)return null;
    return{
      id:"eonet:"+(p.id||f.id),source:"NASA EONET",title:p.title||"Natural event",
      lat:c[1],lon:c[0],time:iso(p.date),magnitude:p.magnitudeValue??null,
      severity:null,url:p.sources?.[0]?.url||null
    };
  }).filter(Boolean);
}

async function fetchGDACS(){
  const r=await fetch(GDACS,{cache:"no-store"});
  if(!r.ok)throw new Error("GDACS "+r.status);
  const txt=await r.text();
  const doc=new DOMParser().parseFromString(txt,"application/xml");
  return [...doc.querySelectorAll("item")].map((it,i)=>{
    const local=name=>[...it.getElementsByTagName("*")].find(n=>n.localName?.toLowerCase()===name.toLowerCase())?.textContent?.trim()||null;
    const point=local("point");
    if(!point)return null;
    const p=point.replace(","," ").split(/\s+/).map(Number);
    if(p.length<2||!Number.isFinite(p[0])||!Number.isFinite(p[1]))return null;
    return{
      id:"gdacs:"+(local("guid")||i),source:"GDACS",title:local("title")||"Disaster alert",
      lat:p[0],lon:p[1],time:iso(local("pubDate")||Date.now()),
      magnitude:null,severity:local("alertlevel"),url:local("link")
    };
  }).filter(Boolean);
}

function priority(s){
  let p=0;
  const reasons=attentionReasons(s);
  p+=reasons.length*8;
  if(s.source==="USGS"&&Number.isFinite(Number(s.magnitude)))p+=Number(s.magnitude);
  if(/red/i.test(s.severity||""))p+=7;
  else if(/orange/i.test(s.severity||""))p+=4;
  if(s.time)p+=Math.max(0,5-((Date.now()-new Date(s.time))/864e5));
  return p;
}

async function refreshSignals(){
  const results=await Promise.allSettled([fetchUSGS(),fetchEONET(),fetchGDACS()]);
  const entries=[["USGS",results[0]],["NASA EONET",results[1]],["GDACS",results[2]]];
  signals=[];sourceStates=[];
  entries.forEach(([name,res])=>{
    if(res.status==="fulfilled"){
      const enriched=res.value.map(s=>({...s,kind:"signal",reasons:attentionReasons(s)}));
      signals.push(...enriched);
      sourceStates.push({name,ok:true,count:enriched.length});
    }else sourceStates.push({name,ok:false,count:0});
  });
  renderSignalList();
  if(!$("story").classList.contains("active"))updateAtlasLayers(false);
  if(trustRegistry){
    renderTrustSnapshot();
    if($("trustCenter")?.classList.contains("open"))renderTrustCenter(trustTab);
  }
}

function updateAtlasLayers(storyMode=$("story").classList.contains("active")){
  let points;
  if(storyMode){
    points=[actionPoint];
    if(currentMilestone>=2)points.push(...BLOOM);
  }else{
    points=[...signals.slice(0,150),...storyPoints];
  }
  world.pointsData(points);

  const surfaced=[...signals]
    .sort((a,b)=>priority(b)-priority(a))
    .filter(s=>priority(s)>=5)
    .slice(0,14);
  world.ringsData(storyMode?[actionPoint]:[...surfaced,...storyPoints]);
  world.arcsData(storyMode&&currentMilestone>=1?THREADS:[]);
  world.polygonCapColor(countryColor);
  if(countries.length)world.polygonsData([...countries]);
}

function setMilestone(milestone){
  currentMilestone=Math.max(0,Math.min(3,Number(milestone)||0));
  $("timeScrubber").value=(currentMilestone/3).toFixed(3);
  updateSignature();
  updateAtlasLayers(true);
}

function updateSignature(){
  const spans=qsa(".signature span");
  spans.forEach((el,i)=>{
    const on=(i===0)||(i===1&&currentMilestone>=1)||(i===2&&currentMilestone>=2);
    el.style.opacity=on?"1":".24";
  });
}

function renderSignalList(){
  const top=[...signals].sort((a,b)=>priority(b)-priority(a)).slice(0,3);
  $("signalList").innerHTML=top.map(s=>`
    <button class="signal" data-id="${escapeHtml(s.id)}">
      <div class="signal-source">${escapeHtml(s.source)} · ${escapeHtml(sourceMeta[s.source]?.freshness||"PUBLIC")}</div>
      <div class="signal-title">${escapeHtml(s.title)}</div>
      <div class="signal-time">${escapeHtml(age(s.time))}</div>
    </button>
  `).join("");
  qsa(".signal",$("signalList")).forEach(el=>{
    el.onclick=()=>{
      const s=signals.find(x=>x.id===el.dataset.id);
      if(s)focusSignal(s);
    };
  });
}

function closeAuxiliaryLayers(except=null){
  if(except!=="evidence") closeEvidence();
  if(except!=="look") $("look").classList.remove("open");
  if(except!=="share") $("share").classList.remove("open");
  if(except!=="actionLab") closeActionLab();
  if(except!=="trustCenter") closeTrustCenter();
  if(except!=="handoff") closeHandoff();
}

function openLook(){
  document.body.classList.remove("story-mode");
  stopStory(false);
  closeAuxiliaryLayers("look");
  $("home").classList.add("hidden");
  $("look").classList.add("open");
  $("signalListArea").style.display="";
  $("signalFocus").innerHTML="";
  currentSignal=null;
  world.controls().autoRotate=!reduceMotion;
  world.globeOffset([0,-70]);
  world.pointOfView({lat:12,lng:18,altitude:2.02},reduceMotion?0:900);
  updateAtlasLayers(false);
}

function closeLook(){
  $("look").classList.remove("open");
  $("signalFocus").innerHTML="";
  $("signalListArea").style.display="";
  $("home").classList.remove("hidden");
  setHomeGlobe();
}

function focusSignal(s){
  currentSignal=s;
  $("signalListArea").style.display="none";
  world.controls().autoRotate=false;
  world.globeOffset(innerWidth<650?[0,-100]:[240,-20]);
  world.pointOfView({lat:s.lat,lng:s.lon,altitude:1.35},reduceMotion?0:850);
  const why=s.reasons?.length?s.reasons.join(" · "):"Current public source signal";
  $("signalFocus").innerHTML=`
    <div class="look-head">
      <div class="look-title">${escapeHtml(s.source)} · ${escapeHtml(sourceMeta[s.source]?.freshness||"PUBLIC")}</div>
      <button class="text-nav" id="signalBack">Back to signals</button>
    </div>
    <div class="signal-focus">
      <h2>${escapeHtml(s.title)}</h2>
      <p>${escapeHtml(why)} · ${escapeHtml(age(s.time))}. WORLD PULSE shows the source signal; it does not infer human impact from event size alone.</p>
      <div class="signal-focus-actions">
        <button class="word-button" id="signalSource">Open source ↗</button>
        <button class="word-button muted" id="signalShare">Pass signal on</button>
      </div>
    </div>
  `;
  $("signalBack").onclick=()=>{
    $("signalFocus").innerHTML="";
    $("signalListArea").style.display="";
    world.controls().autoRotate=!reduceMotion;
    world.pointOfView({lat:12,lng:18,altitude:2.02},reduceMotion?0:800);
  };
  $("signalSource").onclick=()=>s.url&&window.open(s.url,"_blank","noopener");
  $("signalShare").onclick=()=>shareSignal(s);
}

function hideOpening(){
  $("opening").classList.add("hidden");
}

function clamp01(v){return Math.max(0,Math.min(1,v))}
function lerp(a,b,t){return a+(b-a)*t}
function smoothstep(a,b,v){
  const t=clamp01((v-a)/(b-a));
  return t*t*(3-2*t);
}
function easeCinema(t){
  return t<.5 ? 4*t*t*t : 1-Math.pow(-2*t+2,3)/2;
}

function buildScrollNarrative(){
  if($("scrollNarrative").children.length)return;
  $("scrollNarrative").innerHTML=activeStory.scenes.map((scene,index)=>`
    <div class="scroll-scene ${escapeHtml(scene.composition)}" data-scene-index="${index}" aria-hidden="true">
      <article class="scene">${sceneMarkup(scene)}</article>
    </div>
  `).join("");
  bindScrollSceneActions();
}

function primaryDirectIntervention(story=activeStory){
  const loop=ACTION_LOOPS[story.id];
  return (loop?.interventions||[]).find(item=>
    item.type==="external" && item.actionability==="DIRECT"
  ) || null;
}

function followIntervention(story=activeStory){
  const loop=ACTION_LOOPS[story.id];
  return (loop?.interventions||[]).find(item=>item.type==="follow") || null;
}

function decisionMarkup(){
  const direct=primaryDirectIntervention();
  const follow=followIntervention();
  const gate=direct?interventionTrustGate(direct):{allowed:false,reason:"No verified direct public action is currently surfaced for this story."};
  const hasDirect=Boolean(direct&&gate.allowed);

  return `
    <div class="story-decision">
      <div class="decision-kicker">WHAT NOW?</div>
      <h3>Does this need anything from you?</h3>
      <p>${hasDirect
        ? "Yes — there is a verified public way to help. You can also simply follow the story and come back when something changes."
        : "No direct public action is verified tightly enough right now. Following the story is useful; inventing an action is not."}</p>
      ${hasDirect?`
        <button class="decision-primary" data-action="direct">${escapeHtml(direct.cta.replace("↗","").trim())} →</button>
      `:""}
      ${follow?`<button class="decision-secondary" data-action="follow">${escapeHtml(follow.cta||"Follow this story")}</button>`:""}
      <button class="decision-secondary" data-action="done">I’m caught up</button>
      <button class="decision-evidence" data-action="belief">How do we know?</button>
      ${direct&&!gate.allowed?`<div class="decision-note">${escapeHtml(gate.reason)}</div>`:""}
    </div>
  `;
}

function sceneMarkup(scene){
  const body=scene.value
    ? `<div class="scene-number ${escapeHtml(scene.tone||"")}">${escapeHtml(scene.value)}</div>
       <div class="scene-label">${escapeHtml(scene.label)}</div>`
    : `<h2 class="scene-headline">${scene.headline}</h2>`;

  return `
    <div class="scene-kicker">${escapeHtml(scene.kicker)}</div>
    ${body}
    <div class="scene-copy">${escapeHtml(scene.copy)}</div>
    <button class="scene-source inline-evidence" data-action="belief">Reported by / sourced from ${escapeHtml(scene.source||"primary evidence")} · How do we know?</button>
    ${scene.actions?decisionMarkup():""}
  `;
}

function showExternalHandoff(intervention){
  const gate=interventionTrustGate(intervention);
  if(!gate.allowed){
    toast(gate.reason);
    return;
  }
  $("handoffTitle").textContent=intervention.title;
  $("handoffBody").textContent="The action itself happens outside COMMONS. We’ll hand you to the verified official path and keep the story available for follow-up.";
  $("handoffVerify").textContent=intervention.evidenceStrength+" · "+intervention.actor;
  $("handoffCannot").textContent=intervention.uncertainty;
  $("handoffContinue").textContent=intervention.cta.replace("↗","").trim()+" →";
  $("handoff").dataset.interventionId=intervention.id;
  $("handoff").classList.add("open");
  $("handoff").setAttribute("aria-hidden","false");
}

function closeHandoff(){
  if(!$("handoff"))return;
  $("handoff").classList.remove("open");
  $("handoff").setAttribute("aria-hidden","true");
  delete $("handoff").dataset.interventionId;
}

function continueExternalHandoff(){
  const loop=actionLoopForStory();
  const intervention=loop?.interventions.find(item=>item.id===$("handoff").dataset.interventionId);
  if(!intervention)return closeHandoff();
  const gate=interventionTrustGate(intervention);
  if(!gate.allowed){
    closeHandoff();
    toast(gate.reason);
    return;
  }
  addLedgerReceipt(intervention,"external_opened","external_unverified");
  closeHandoff();
  renderStoryLibrary();
  window.open(intervention.url,"_blank","noopener");
}

function followCurrentStoryInline(){
  const intervention=followIntervention();
  if(!intervention){
    toast("No follow action is defined for this story yet");
    return;
  }
  addLedgerReceipt(intervention,"following","browser_local");
  renderStoryLibrary();
  toast("Following this story");
}

function bindScrollSceneActions(){
  qsa("[data-action]",$("scrollNarrative")).forEach(btn=>{
    btn.onclick=()=>{
      if(btn.dataset.action==="direct"){
        const direct=primaryDirectIntervention();
        if(direct)showExternalHandoff(direct);
      }
      if(btn.dataset.action==="follow")followCurrentStoryInline();
      if(btn.dataset.action==="done")stopStory(true);
      if(btn.dataset.action==="belief")openEvidence();
    };
  });
}

function storyMaxScroll(){
  return Math.max(1,document.documentElement.scrollHeight-innerHeight);
}

function storyProgress(){
  return clamp01(window.scrollY/storyMaxScroll());
}

function updateSemanticVisuals(thread,bloom,memory){
  threadStrength=clamp01(thread);
  bloomStrength=clamp01(bloom);
  memoryStrength=clamp01(memory);
  const key=[
    Math.round(threadStrength*24),
    Math.round(bloomStrength*24),
    Math.round(memoryStrength*24)
  ].join("|");
  if(key===lastSemanticFrame)return;
  lastSemanticFrame=key;

  const points=[];
  if(memoryStrength<.55)points.push(actionPoint);
  if(bloomStrength>.01&&memoryStrength<.6)points.push(...BLOOM);
  if(memoryStrength>.02)points.push(memoryPoint);
  world.pointsData(points);
  world.arcsData(threadStrength>.01&&memoryStrength<.5?THREADS:[]);
  world.ringsData(memoryStrength>.18?[memoryPoint]:[actionPoint]);
}

function syncScrollCinema(){
  scrollRAF=null;
  if(!$("story").classList.contains("active"))return;

  const progress=storyProgress();
  const maxIndex=activeStory.scenes.length-1;
  const position=progress*maxIndex;
  const floorIndex=Math.min(maxIndex,Math.floor(position));
  const ceilIndex=Math.min(maxIndex,floorIndex+1);
  const rawT=position-floorIndex;
  const t=easeCinema(rawT);
  const a=activeStory.scenes[floorIndex];
  const b=activeStory.scenes[ceilIndex];
  const nearest=Math.max(0,Math.min(maxIndex,Math.round(position)));

  qsa(".scroll-scene",$("scrollNarrative")).forEach((el,index)=>{
    const delta=index-position;
    const distance=Math.abs(delta);
    const opacity=clamp01(1-smoothstep(.12,1.02,distance));
    const translate=delta*74;
    const scale=1-Math.min(distance,1)*.018;
    const blur=reduceMotion?0:Math.min(7,distance*6.5);
    el.style.opacity=opacity.toFixed(3);
    el.style.transform=`translate3d(0,${translate.toFixed(1)}px,0) scale(${scale.toFixed(4)})`;
    el.style.filter=`blur(${blur.toFixed(2)}px)`;
    el.style.setProperty("--scene-depth",delta.toFixed(4));
    const interactive=distance<.3;
    el.classList.toggle("is-interactive",interactive);
    el.setAttribute("aria-hidden",interactive?"false":"true");
  });

  const cam={
    lat:lerp(a.camera.lat,b.camera.lat,t),
    lng:lerp(a.camera.lng,b.camera.lng,t),
    altitude:lerp(a.camera.altitude,b.camera.altitude,t)
  };
  const ao=sceneOffset(a),bo=sceneOffset(b);
  world.globeOffset([
    lerp(ao[0],bo[0],t),
    lerp(ao[1],bo[1],t)
  ]);
  world.pointOfView(cam,0);

  const terrainMix=clamp01(lerp(a.terrain||0,b.terrain||0,t));
  const globeOpacity=1-smoothstep(.18,.9,terrainMix)*.94;
  const terrainOpacity=smoothstep(.08,.72,terrainMix);
  document.documentElement.style.setProperty("--globe-opacity",globeOpacity.toFixed(3));
  document.documentElement.style.setProperty("--globe-blur",(terrainMix*4.5).toFixed(2)+"px");
  document.documentElement.style.setProperty("--terrain-opacity",terrainOpacity.toFixed(3));
  document.documentElement.style.setProperty("--terrain-content-opacity",smoothstep(.18,.62,terrainMix).toFixed(3));
  document.documentElement.style.setProperty("--terrain-scale",lerp(.7,1.04,easeCinema(terrainMix)).toFixed(4));
  document.documentElement.style.setProperty("--terrain-tilt",lerp(46,8,easeCinema(terrainMix)).toFixed(2)+"deg");
  document.documentElement.style.setProperty("--terrain-rotate",lerp(-5,-1,easeCinema(terrainMix)).toFixed(2)+"deg");
  document.documentElement.style.setProperty("--terrain-y",lerp(80,-5,easeCinema(terrainMix)).toFixed(1)+"px");
  document.documentElement.style.setProperty("--terrain-blur",(reduceMotion?0:lerp(14,0,easeCinema(terrainMix))).toFixed(2)+"px");

  const semantic=activeStory.semantic;
  const thread=smoothstep(semantic.threadStart,semantic.threadEnd,position);
  const bloom=BLOOM.length?smoothstep(semantic.bloomStart,semantic.bloomEnd,position):0;
  const memory=smoothstep(semantic.memoryStart,semantic.memoryEnd,position);
  updateSemanticVisuals(thread,bloom,memory);

  document.documentElement.style.setProperty("--terrain-thread-opacity",(thread*terrainOpacity).toFixed(3));
  document.documentElement.style.setProperty("--terrain-thread-offset",(1-thread).toFixed(4));
  document.documentElement.style.setProperty("--terrain-bloom-opacity",((BLOOM.length?bloom:0)*terrainOpacity).toFixed(3));
  document.documentElement.style.setProperty("--terrain-bloom-scale",lerp(.62,1,bloom).toFixed(3));
  document.documentElement.style.setProperty("--memory-opacity",memory.toFixed(3));

  const silenceDistance=Math.abs(position-activeStory.semantic.silenceIndex);
  const silence=1-smoothstep(.12,.76,silenceDistance);
  const chrome=1-silence*.94;
  document.documentElement.style.setProperty("--cinema-chrome-opacity",chrome.toFixed(3));
  document.documentElement.style.setProperty("--cinema-header-opacity",(1-silence*.78).toFixed(3));
  document.documentElement.style.setProperty("--silence-label-opacity",smoothstep(.08,.55,Math.abs(position-activeStory.semantic.silenceIndex)).toFixed(3));
  document.documentElement.style.setProperty("--silence-detail-opacity","0");

  const [m1,m2,m3]=activeStory.semantic.milestones;
  const milestone=position<m1?0:position<m2?1:position<m3?2:3;
  if(milestone!==currentMilestone){
    currentMilestone=milestone;
    updateSignature();
  }

  $("timeScrubber").value=progress.toFixed(3);
  $("timeFill").style.width=(progress*100).toFixed(2)+"%";
  $("scrollCue").classList.toggle("hidden",progress>.025);
  document.documentElement.style.setProperty("--globe-scale",(1+Math.sin(progress*Math.PI*3)*.0035).toFixed(4));
  document.documentElement.style.setProperty("--vignette-opacity",(0.82+Math.sin(progress*Math.PI)*.12).toFixed(3));

  const now=performance.now();
  const dt=Math.max(16,now-lastScrollTime);
  const velocity=Math.min(1.5,Math.abs(progress-lastScrollProgress)/(dt/1000));
  updateSoundscape(progress,velocity,milestone);
  lastScrollProgress=progress;
  lastScrollTime=now;

  qsa(".time-labels span").forEach((el,index)=>{
    el.style.color=index===milestone?"#bfc1b9":"";
  });

  if(nearest!==storyIndex){
    storyIndex=nearest;
    const scene=activeStory.scenes[storyIndex];
    $("story").dataset.composition=scene.composition;
    const u=new URL(location.href);
    u.searchParams.delete("signal");
    u.searchParams.delete("action");
    u.searchParams.set("story",activeStory.id);
    u.searchParams.set("scene",scene.id);
    history.replaceState(null,"",u);
  }
}

function requestScrollCinema(){
  if(scrollRAF!==null)return;
  scrollRAF=requestAnimationFrame(syncScrollCinema);
}

function jumpToScene(index,smooth=true){
  const target=Math.max(0,Math.min(activeStory.scenes.length-1,index));
  const p=target/(activeStory.scenes.length-1);
  window.scrollTo({top:p*storyMaxScroll(),behavior:smooth&&!reduceMotion?"smooth":"auto"});
}

function startStory(index=0){
  document.documentElement.classList.add("story-mode");
  document.body.classList.add("story-mode");
  hideOpening();
  closeAuxiliaryLayers();
  $("home").classList.add("hidden");
  $("story").classList.add("active");
  world.controls().autoRotate=false;
  buildScrollNarrative();
  storyIndex=Math.max(0,Math.min(activeStory.scenes.length-1,index));
  storyPlaying=false;
  stopAutoScroll();
  updatePlayLabel();

  requestAnimationFrame(()=>{
    jumpToScene(storyIndex,false);
    requestScrollCinema();
  });
}

function stopStory(returnHome=true){
  stopAutoScroll();
  cancelAnimationFrame(scrollRAF);
  scrollRAF=null;
  clearTimeout(storyTimer);
  storyTimer=null;
  storyPlaying=false;
  $("story").classList.remove("active");
  document.documentElement.classList.remove("story-mode");
  document.body.classList.remove("story-mode");
  window.scrollTo(0,0);
  lastSemanticFrame="";
  threadStrength=0;
  bloomStrength=0;
  memoryStrength=0;
  resetCinematicVisuals();

  if(returnHome){
    $("home").classList.remove("hidden");
    const u=new URL(location.href);
    u.searchParams.delete("action");
    u.searchParams.delete("story");
    u.searchParams.delete("scene");
    history.replaceState(null,"",u);
    setHomeGlobe();
    renderStoryLibrary();
  }
}

function nextScene(){
  stopAutoScroll();
  jumpToScene(Math.min(activeStory.scenes.length-1,storyIndex+1));
}
function prevScene(){
  stopAutoScroll();
  jumpToScene(Math.max(0,storyIndex-1));
}

function autoScrollTick(now){
  if(!storyPlaying)return;
  if(!lastAutoTime)lastAutoTime=now;
  const dt=Math.min(50,now-lastAutoTime);
  lastAutoTime=now;
  const pxPerMs=storyMaxScroll()/52000;
  const next=Math.min(storyMaxScroll(),window.scrollY+dt*pxPerMs);
  window.scrollTo(0,next);
  requestScrollCinema();
  if(next>=storyMaxScroll()-2){
    stopAutoScroll();
    return;
  }
  autoScrollRAF=requestAnimationFrame(autoScrollTick);
}

function stopAutoScroll(){
  storyPlaying=false;
  lastAutoTime=0;
  if(autoScrollRAF!==null)cancelAnimationFrame(autoScrollRAF);
  autoScrollRAF=null;
  updatePlayLabel();
}

function togglePlay(){
  if(storyPlaying){
    stopAutoScroll();
    return;
  }
  storyPlaying=true;
  lastAutoTime=0;
  updatePlayLabel();
  autoScrollRAF=requestAnimationFrame(autoScrollTick);
}

function updatePlayLabel(){
  if(!$("playToggle"))return;
  $("playToggle").textContent=storyPlaying?"Pause":"Auto";
  $("playToggle").setAttribute("aria-label",storyPlaying?"Pause auto-scroll":"Auto-play scroll story");
}

function scrubTime(value){
  stopAutoScroll();
  const progress=clamp01(Number(value)||0);
  window.scrollTo(0,progress*storyMaxScroll());
  requestScrollCinema();
}

function createAudioNodeGraph(){
  if(audioCtx&&audioNodes)return true;
  const Ctx=window.AudioContext||window.webkitAudioContext;
  if(!Ctx)return false;

  audioCtx=new Ctx();
  const master=audioCtx.createGain();
  const filter=audioCtx.createBiquadFilter();
  const air=audioCtx.createBiquadFilter();
  const low=audioCtx.createOscillator();
  const fifth=audioCtx.createOscillator();
  const shimmer=audioCtx.createOscillator();

  master.gain.value=0;
  filter.type="lowpass";
  filter.frequency.value=260;
  filter.Q.value=.35;
  air.type="highpass";
  air.frequency.value=28;

  low.type="sine";
  fifth.type="sine";
  shimmer.type="triangle";
  low.frequency.value=48;
  fifth.frequency.value=72;
  shimmer.frequency.value=144;

  const lowGain=audioCtx.createGain();
  const fifthGain=audioCtx.createGain();
  const shimmerGain=audioCtx.createGain();
  lowGain.gain.value=.64;
  fifthGain.gain.value=.19;
  shimmerGain.gain.value=.028;

  low.connect(lowGain).connect(filter);
  fifth.connect(fifthGain).connect(filter);
  shimmer.connect(shimmerGain).connect(filter);
  filter.connect(air).connect(master).connect(audioCtx.destination);

  low.start();
  fifth.start();
  shimmer.start();

  audioNodes={master,filter,air,low,fifth,shimmer};
  return true;
}

function soundAccent(freq=120,amount=.035){
  if(!soundEnabled||!audioCtx)return;
  const osc=audioCtx.createOscillator();
  const gain=audioCtx.createGain();
  const now=audioCtx.currentTime;
  osc.type="sine";
  osc.frequency.setValueAtTime(freq,now);
  osc.frequency.exponentialRampToValueAtTime(freq*.78,now+.7);
  gain.gain.setValueAtTime(.0001,now);
  gain.gain.exponentialRampToValueAtTime(Math.max(.001,amount),now+.035);
  gain.gain.exponentialRampToValueAtTime(.0001,now+.9);
  osc.connect(gain).connect(audioNodes.master);
  osc.start(now);
  osc.stop(now+.95);
}

async function toggleSound(){
  if(!soundEnabled){
    if(!createAudioNodeGraph()){
      toast("Sound is not supported in this browser");
      return;
    }
    if(audioCtx.state==="suspended")await audioCtx.resume();
    soundEnabled=true;
    lastSoundMilestone=-1;
  }else{
    soundEnabled=false;
    if(audioNodes&&audioCtx){
      audioNodes.master.gain.setTargetAtTime(.0001,audioCtx.currentTime,.08);
    }
  }
  updateSoundButton();
}

function updateSoundButton(){
  if(!$("soundBtn"))return;
  $("soundBtn").textContent=soundEnabled?"Sound on":"Sound off";
  $("soundBtn").setAttribute("aria-pressed",soundEnabled?"true":"false");
}

function updateSoundscape(progress,velocity,milestone){
  if(!soundEnabled||!audioCtx||!audioNodes)return;
  const now=audioCtx.currentTime;
  const movement=Math.min(1,velocity*.85);
  const terrain=Number(getComputedStyle(document.documentElement).getPropertyValue("--terrain-opacity"))||0;
  const baseGain=.008+movement*.012+terrain*.004;

  audioNodes.master.gain.setTargetAtTime(baseGain,now,.12);
  audioNodes.filter.frequency.setTargetAtTime(190+progress*180+movement*1100,now,.12);
  audioNodes.low.frequency.setTargetAtTime(46+progress*9,now,.2);
  audioNodes.fifth.frequency.setTargetAtTime(69+progress*14,now,.2);
  audioNodes.shimmer.frequency.setTargetAtTime(138+progress*36+movement*70,now,.18);

  if(milestone!==lastSoundMilestone){
    lastSoundMilestone=milestone;
    const tones=[72,96,132,166];
    soundAccent(tones[milestone]||110,milestone===2?.052:.027);
  }
}

function resetCinematicVisuals(){
  const root=document.documentElement;
  [
    "--globe-opacity","--globe-blur","--terrain-opacity","--terrain-content-opacity",
    "--terrain-scale","--terrain-tilt","--terrain-rotate","--terrain-y","--terrain-blur",
    "--terrain-thread-opacity","--terrain-thread-offset","--terrain-bloom-opacity",
    "--terrain-bloom-scale","--memory-opacity","--cinema-chrome-opacity",
    "--cinema-header-opacity","--silence-label-opacity","--silence-detail-opacity"
  ].forEach(name=>root.style.removeProperty(name));
  if(soundEnabled&&audioNodes&&audioCtx){
    audioNodes.master.gain.setTargetAtTime(.0001,audioCtx.currentTime,.1);
  }
}

function actionLoopForStory(story=activeStory){
  return ACTION_LOOPS[story.id] || null;
}

function loadActionLedger(){
  try{
    const parsed=JSON.parse(localStorage.getItem(ACTION_LEDGER_KEY)||"[]");
    return Array.isArray(parsed)?parsed:[];
  }catch(e){
    return [];
  }
}

function saveActionLedger(entries){
  try{
    localStorage.setItem(ACTION_LEDGER_KEY,JSON.stringify(entries));
  }catch(e){}
  updateLedgerCount();
  renderStoryLibrary();
}

function updateLedgerCount(){
  const entries=loadActionLedger();
  const count=new Set(entries.filter(entry=>entry.status==="following").map(entry=>entry.storyId)).size;
  if($("ledgerCount"))$("ledgerCount").textContent=String(entries.length);
  if($("actionLedgerBtn"))$("actionLedgerBtn").textContent=count?"Following · "+count:"Following";
}

function storyForReceipt(receipt){
  return storyById(receipt.storyId);
}

function interventionForReceipt(receipt){
  const loop=ACTION_LOOPS[receipt.storyId];
  return loop?.interventions?.find(item=>item.id===receipt.interventionId) || null;
}

function ledgerForStory(storyId){
  return loadActionLedger().filter(entry=>entry.storyId===storyId);
}

function hasNewEvidence(receipt){
  const story=storyForReceipt(receipt);
  return Boolean(story && receipt.evidenceAsOf && story.updatedAt!==receipt.evidenceAsOf);
}

function receiptTime(value){
  const date=new Date(value);
  if(Number.isNaN(date.getTime()))return "time unavailable";
  return new Intl.DateTimeFormat("en",{dateStyle:"medium",timeStyle:"short"}).format(date);
}

function statusLabel(status){
  return ({
    external_opened:"Official path opened",
    self_reported_complete:"Self-reported complete",
    following:"Following",
    share_completed:"Share completed",
    share_prepared:"Share prepared"
  })[status] || String(status||"Recorded");
}

function addLedgerReceipt(intervention,status,verification){
  const entries=loadActionLedger();
  const now=new Date().toISOString();
  const existingIndex=entries.findIndex(entry=>
    entry.storyId===activeStory.id &&
    entry.interventionId===intervention.id &&
    (intervention.type==="follow" || entry.status==="external_opened")
  );

  const receipt={
    id:existingIndex>=0?entries[existingIndex].id:"act-"+Date.now()+"-"+Math.random().toString(36).slice(2,7),
    storyId:activeStory.id,
    storyTitle:activeStory.country+" — "+activeStory.title,
    interventionId:intervention.id,
    interventionTitle:intervention.title,
    interventionType:intervention.type,
    status,
    verification,
    evidenceAsOf:activeStory.updatedAt,
    startedAt:existingIndex>=0?entries[existingIndex].startedAt||now:now,
    updatedAt:now
  };

  if(status==="self_reported_complete" || status==="following" || status==="share_completed" || status==="share_prepared"){
    receipt.completedAt=now;
  }

  if(existingIndex>=0)entries[existingIndex]=receipt;
  else entries.unshift(receipt);
  saveActionLedger(entries);
  return receipt;
}

function updateLedgerReceipt(id,patch){
  const entries=loadActionLedger();
  const index=entries.findIndex(entry=>entry.id===id);
  if(index<0)return null;
  entries[index]={...entries[index],...patch,updatedAt:new Date().toISOString()};
  saveActionLedger(entries);
  return entries[index];
}

function clearActionLedger(){
  if(!window.confirm("Clear the local COMMONS action ledger from this browser?"))return;
  try{localStorage.removeItem(ACTION_LEDGER_KEY)}catch(e){}
  updateLedgerCount();
  renderActionLab("ledger");
  toast("Local action ledger cleared");
}

function loopProgress(entries){
  const acted=entries.some(entry=>["self_reported_complete","share_completed","share_prepared"].includes(entry.status));
  const followed=entries.some(entry=>entry.status==="following");
  const learned=entries.some(hasNewEvidence);
  return [
    {label:"Understand",done:true},
    {label:"Decide",done:true},
    {label:"Coordinate",done:true},
    {label:"Act",done:acted},
    {label:"Follow",done:followed},
    {label:"Learn",done:learned}
  ];
}

function renderLoopChain(entries){
  return `<div class="loop-chain">${loopProgress(entries).map(step=>`
    <div class="loop-step ${step.done?"done":"future"}"><i></i>${escapeHtml(step.label)}</div>
  `).join("")}</div>`;
}

function trustGateForStory(storyId=activeStory.id){
  evaluateTrustNow();
  if(!trustRegistry){
    return {allowed:false,reason:"Trust registry unavailable. Direct external action is disabled."};
  }
  if((trustReport.openHighIncidents||[]).length){
    return {allowed:false,reason:"A high-severity trust incident is open. Direct external action is disabled."};
  }
  const stale=(trustReport.staleCriticalClaims||[]).filter(claim=>claim.story_id===storyId);
  if(stale.length){
    return {allowed:false,reason:stale.length+" critical claim(s) for this story are stale. Refresh evidence before acting."};
  }
  const missing=(trustReport.missingSources||[]).filter(item=>{
    const claim=(trustRegistry.claims||[]).find(candidate=>candidate.id===item.claimId);
    return claim?.story_id===storyId;
  });
  if(missing.length){
    return {allowed:false,reason:"This story has a missing source reference. Direct external action is disabled."};
  }
  return {allowed:true,reason:"Story-specific critical trust checks pass."};
}

function interventionTrustGate(intervention){
  if(intervention?.type!=="external" || intervention?.actionability!=="DIRECT"){
    return {allowed:true,reason:"No direct external execution is being requested."};
  }
  return trustGateForStory(activeStory.id);
}

function interventionLabel(item,index){
  if(index===0 && item.actionability==="DIRECT")return "BEST VERIFIED NEXT MOVE";
  if(item.type==="follow")return "KEEP THE LOOP OPEN";
  if(item.type==="share")return "HELP THE EVIDENCE TRAVEL";
  return item.actionability;
}

function renderInvestigationActor(actor){
  return `
    <a class="case-actor" href="${actor.url}" target="_blank" rel="noopener">
      <div class="case-actor-mark"></div>
      <div>
        <div class="case-actor-name">${escapeHtml(actor.name)}</div>
        <div class="case-actor-role">${escapeHtml(actor.role)}</div>
        <p>${escapeHtml(actor.evidence)}</p>
      </div>
      <span>↗</span>
    </a>
  `;
}

function renderIntervention(item,index,entries){
  const existing=entries.find(entry=>entry.interventionId===item.id);
  const gate=interventionTrustGate(item);
  const primary=index===0 && item.actionability==="DIRECT";
  const state=!gate.allowed?"BLOCKED · TRUST":existing?statusLabel(existing.status):item.actionability;

  return `
    <article class="case-action ${primary?"primary":""} ${gate.allowed?"":"trust-blocked"}">
      <div class="case-action-top">
        <div>
          <div class="case-eyebrow">${escapeHtml(interventionLabel(item,index))}</div>
          <h4>${escapeHtml(item.title)}</h4>
          <div class="case-action-actor">${escapeHtml(item.actor)}</div>
        </div>
        <span class="case-state">${escapeHtml(state)}</span>
      </div>

      <p class="case-action-why">${escapeHtml(item.why)}</p>

      <div class="case-action-notes">
        <div>
          <b>What supports this</b>
          <span>${escapeHtml(item.evidenceStrength)}</span>
        </div>
        <div>
          <b>What we still don’t know</b>
          <span>${escapeHtml(item.uncertainty)}</span>
        </div>
        <div>
          <b>What we’ll look for next</b>
          <span>${escapeHtml(item.measure)}</span>
        </div>
      </div>

      <div class="case-action-cta">
        <button class="case-primary-button" data-intervention-id="${escapeHtml(item.id)}" ${gate.allowed?"":"disabled aria-disabled=\"true\""}>
          ${escapeHtml(gate.allowed?item.cta:"Unavailable until trust checks pass")}
        </button>
      </div>

      ${gate.allowed?"":`<div class="case-caution">${escapeHtml(gate.reason)}</div>`}
    </article>
  `;
}

function renderActionLabCurrent(){
  const loop=actionLoopForStory();
  if(!loop){
    $("actionLabBody").innerHTML='<div class="ledger-empty">No accountable action loop has been defined for this story yet.</div>';
    return;
  }

  const entries=ledgerForStory(activeStory.id);
  const pending=entries.find(entry=>entry.status==="external_opened");
  const actors=loop.actors.map(renderInvestigationActor).join("");
  const interventions=loop.interventions.map((item,index)=>renderIntervention(item,index,entries)).join("");

  const prompt=pending?`
    <div class="case-confirmation">
      <div class="case-eyebrow">QUICK CHECK</div>
      <h4>Did you actually complete “${escapeHtml(pending.interventionTitle)}”?</h4>
      <p>WORLD PULSE cannot see the external transaction. Mark it complete only if you really did it. The receipt will stay explicitly self-reported.</p>
      <div class="receipt-actions">
        <button class="case-primary-button" data-confirm-receipt="${escapeHtml(pending.id)}">Yes, I completed it</button>
        <button class="word-button muted" data-opened-only="${escapeHtml(pending.id)}">I only opened the link</button>
      </div>
    </div>
  `:"";

  const newestClaim=trustRegistry
    ? (trustRegistry.claims||[])
        .filter(claim=>claim.story_id===activeStory.id && claim.status==="active")
        .sort((a,b)=>String(b.as_of).localeCompare(String(a.as_of)))[0]
    : null;

  $("actionLabTitle").textContent=activeStory.country+" — "+activeStory.title;
  $("actionLabBody").innerHTML=`
    <section class="case-hero">
      <div class="case-file-line">
        <span>CASE FILE · ${String(activeStory.order||1).padStart(2,"0")}</span>
        <span>Last verified ${escapeHtml(activeStory.updatedAt)}</span>
      </div>
      <h3>${escapeHtml(loop.problem)}</h3>
      <p class="case-lede">${escapeHtml(loop.goal)}</p>
      <div class="case-status-line">
        <span class="case-status-dot"></span>
        <b>${escapeHtml(loop.statusLabel)}</b>
        <span>${escapeHtml(activeStory.statusLabel)}</span>
      </div>
    </section>

    <nav class="case-spine" aria-label="Case progress">
      ${renderLoopChain(entries)}
    </nav>

    <section class="case-section">
      <div class="case-section-kicker">01 · THE PEOPLE ALREADY RESPONDING</div>
      <div class="case-section-heading">
        <h3>Who is on the ground?</h3>
        <p>These are the actors we can currently verify as part of the response.</p>
      </div>
      <div class="case-actors">${actors}</div>
    </section>

    <section class="case-section">
      <div class="case-section-kicker">02 · WHAT YOU CAN DO</div>
      <div class="case-section-heading">
        <h3>Start with the strongest verified path.</h3>
        <p>Not every useful move has the same evidence or directness. The most defensible option comes first.</p>
      </div>
      <div class="case-actions">${interventions}</div>
      ${prompt}
    </section>

    <section class="case-section case-outcome-section">
      <div class="case-section-kicker">03 · WHAT HAS CHANGED SO FAR</div>
      <div class="case-outcome">
        <div class="case-outcome-date">${escapeHtml(loop.latestOutcome.asOf)}</div>
        <h3>${escapeHtml(loop.latestOutcome.headline)}</h3>
        <p>${escapeHtml(loop.latestOutcome.detail)}</p>
        <a href="${loop.latestOutcome.url}" target="_blank" rel="noopener">Read the official update ↗</a>
      </div>
    </section>

    <section class="case-section">
      <div class="case-section-kicker">04 · WHAT WE STILL NEED TO LEARN</div>
      <div class="case-questions">
        ${loop.measures.map(item=>`<div class="case-question"><span>?</span><p>${escapeHtml(item)}</p></div>`).join("")}
      </div>
      <div class="case-field-note">
        <b>How the loop closes</b>
        <p>When newer official evidence arrives, COMMONS compares it with the evidence snapshot stored when you acted. We call this <strong>“evidence after your action.”</strong> We will never call it <strong>“evidence caused by your action”</strong> without causal evidence.</p>
      </div>
    </section>

    <section class="case-section">
      <div class="case-section-kicker">05 · EVIDENCE DESK</div>
      <div class="case-evidence-strip">
        <div><b>Latest claim</b><span>${escapeHtml(newestClaim?.statement||"Open the Trust Center to inspect the current claim ledger.")}</span></div>
        <button class="word-button" id="caseOpenEvidence">Inspect the evidence →</button>
      </div>
    </section>

    <div class="privacy-note">PRIVATE ACTION LEDGER · stored only in this browser · no amount, payment information or identity is collected.</div>
  `;

  if($("caseOpenEvidence"))$("caseOpenEvidence").onclick=()=>openTrustCenter("claims","audit");
  bindActionLabControls();
}

function renderActionLedger(){
  const entries=loadActionLedger().sort((a,b)=>String(b.updatedAt).localeCompare(String(a.updatedAt)));
  $("actionLabTitle").textContent="Following & actions";

  if(!entries.length){
    $("actionLabBody").innerHTML=`
      <div class="ledger-empty">Nothing recorded yet.<br>Open a story and choose an accountable next action.</div>
      <div class="privacy-note">The ledger lives only in this browser.</div>
    `;
    return;
  }

  $("actionLabBody").innerHTML=`
    <div class="ledger-list">
      ${entries.map(entry=>{
        const story=storyForReceipt(entry);
        const intervention=interventionForReceipt(entry);
        const newer=hasNewEvidence(entry);
        const loop=story?ACTION_LOOPS[story.id]:null;
        const outcome=loop?.latestOutcome;
        return `
          <article class="ledger-card">
            <div class="ledger-top">
              <div>
                <div class="ledger-story">${escapeHtml(entry.storyTitle||story?.title||"WORLD PULSE")}</div>
                <div class="ledger-title">${escapeHtml(entry.interventionTitle||intervention?.title||"Recorded action")}</div>
              </div>
              <div class="ledger-status">${escapeHtml(statusLabel(entry.status))}</div>
            </div>
            <div class="ledger-meta">
              <div><b>Recorded</b><span>${escapeHtml(receiptTime(entry.completedAt||entry.startedAt))}</span></div>
              <div><b>Verification</b><span>${escapeHtml(entry.verification==="self_reported"?"Self-reported by you":entry.verification==="browser_local"?"Recorded in this browser":entry.verification==="browser_share"?"Browser share completed":"External completion not verified")}</span></div>
              <div><b>Evidence snapshot</b><span>${escapeHtml(entry.evidenceAsOf||"unknown")}</span></div>
              <div><b>Current story evidence</b><span>${escapeHtml(story?.updatedAt||"story unavailable")}</span></div>
            </div>
            <div class="ledger-update">
              ${newer && outcome
                ? `<strong>NEWER OFFICIAL EVIDENCE</strong><br>${escapeHtml(outcome.headline)}<br><br>This evidence came after your recorded action. It does not prove your action caused the outcome.`
                : `No newer official outcome is recorded in WORLD PULSE yet. The loop remains open for follow-up.`
              }
            </div>
            ${story?`<div class="intervention-actions" style="margin-top:13px"><button class="word-button muted" data-open-ledger-story="${escapeHtml(story.id)}">Open story →</button></div>`:""}
          </article>
        `;
      }).join("")}
    </div>
    <div class="intervention-actions" style="margin-top:24px"><button class="word-button muted" data-clear-ledger>Clear local ledger</button></div>
    <div class="privacy-note">This ledger is a private browser-side prototype. It is not a receipt from an NGO, payment provider or health authority.</div>
  `;

  bindActionLabControls();
}

function renderActionLab(mode=actionLabMode){
  actionLabMode=mode;
  const current=mode==="current";
  $("actionCurrentTab").classList.toggle("active",current);
  $("actionLedgerTab").classList.toggle("active",!current);
  $("actionCurrentTab").setAttribute("aria-selected",current?"true":"false");
  $("actionLedgerTab").setAttribute("aria-selected",current?"false":"true");
  updateLedgerCount();
  if(current)renderActionLabCurrent();
  else renderActionLedger();
}

function openActionLab(mode="current"){
  closeAuxiliaryLayers("actionLab");
  actionLabMode=mode;
  renderActionLab(mode);
  $("actionLab").classList.add("open");
  $("actionLab").setAttribute("aria-hidden","false");
}

function closeActionLab(){
  if(!$("actionLab"))return;
  $("actionLab").classList.remove("open");
  $("actionLab").setAttribute("aria-hidden","true");
}

function beginExternalAction(intervention){
  const gate=interventionTrustGate(intervention);
  if(!gate.allowed){
    toast(gate.reason);
    renderActionLab("current");
    return;
  }
  addLedgerReceipt(intervention,"external_opened","external_unverified");
  renderActionLab("current");
  window.open(intervention.url,"_blank","noopener");
}

function followAction(intervention){
  addLedgerReceipt(intervention,"following","browser_local");
  renderActionLab("current");
  toast("Following this loop in this browser");
}

let pendingShareInterventionId=null;

function prepareActionShare(intervention){
  pendingShareInterventionId=intervention.id;
  openShare();
}

function confirmExternalAction(id,completed){
  if(completed){
    updateLedgerReceipt(id,{
      status:"self_reported_complete",
      verification:"self_reported",
      completedAt:new Date().toISOString()
    });
    toast("Self-reported action recorded");
  }else{
    updateLedgerReceipt(id,{status:"external_opened",verification:"external_unverified"});
    toast("Kept as link opened only");
  }
  renderActionLab("current");
}

function recordActionShare(status,verification){
  if(!pendingShareInterventionId)return;
  const loop=actionLoopForStory();
  const intervention=loop?.interventions.find(item=>item.id===pendingShareInterventionId);
  if(intervention)addLedgerReceipt(intervention,status,verification);
  pendingShareInterventionId=null;
}

function bindActionLabControls(){
  qsa("[data-intervention-id]",$("actionLabBody")).forEach(button=>{
    button.onclick=()=>{
      const loop=actionLoopForStory();
      const intervention=loop?.interventions.find(item=>item.id===button.dataset.interventionId);
      if(!intervention)return;
      if(intervention.type==="external")beginExternalAction(intervention);
      else if(intervention.type==="follow")followAction(intervention);
      else if(intervention.type==="share")prepareActionShare(intervention);
    };
  });

  qsa("[data-confirm-receipt]",$("actionLabBody")).forEach(button=>{
    button.onclick=()=>confirmExternalAction(button.dataset.confirmReceipt,true);
  });
  qsa("[data-opened-only]",$("actionLabBody")).forEach(button=>{
    button.onclick=()=>confirmExternalAction(button.dataset.openedOnly,false);
  });
  qsa("[data-open-ledger-story]",$("actionLabBody")).forEach(button=>{
    button.onclick=()=>{
      closeActionLab();
      enterStory(button.dataset.openLedgerStory,0);
    };
  });
  const clear=qs("[data-clear-ledger]",$("actionLabBody"));
  if(clear)clear.onclick=clearActionLedger;
}

function formatTrustDate(value){
  if(!value)return "unknown";
  const date=new Date(value);
  if(Number.isNaN(date.getTime()))return String(value);
  return new Intl.DateTimeFormat("en",{day:"2-digit",month:"short",year:"numeric"}).format(date);
}

function storyLabel(storyId){
  const story=storyById(storyId);
  return story?story.country+" — "+story.title:storyId;
}

function evaluateTrustNow(){
  if(!window.COMMONS_TRUST){
    trustReport={status:"DEGRADED",reason:"Trust evaluator unavailable",provenanceCoverage:0,staleCriticalClaims:[],unresolvedConflicts:[],openHighIncidents:[],checks:[],passedChecks:0,totalChecks:0};
    return trustReport;
  }
  trustReport=window.COMMONS_TRUST.evaluate(trustRegistry,ACTION_LOOPS,new Date());
  return trustReport;
}

async function loadTrustSystem(){
  if(!window.COMMONS_TRUST){
    trustLoadError="Trust evaluator unavailable";
    evaluateTrustNow();
    renderTrustSnapshot();
    return;
  }
  const loaded=await window.COMMONS_TRUST.load("./trust-registry.json");
  trustRegistry=loaded.registry;
  trustLoadError=loaded.error;
  evaluateTrustNow();
  renderTrustSnapshot();
}

function renderTrustSnapshot(){
  if(!$("trustSnapshot"))return;
  evaluateTrustNow();
  $("trustSnapshot").dataset.status=trustReport.status;
  $("trustSnapshotStatus").textContent=trustReport.status;
  const coverage=Math.round((trustReport.provenanceCoverage||0)*100);
  const stale=trustReport.staleCriticalClaims?.length||0;
  const evalText=trustReport.totalChecks?trustReport.passedChecks+"/"+trustReport.totalChecks+" checks":"checks unavailable";
  $("trustSnapshotDetail").textContent=trustReport.status==="HEALTHY"
    ? coverage+"% sourced · "+stale+" stale"
    : (trustLoadError||trustReport.reason||"Evidence needs attention.");
  renderCalmOrientation();
  renderDailyHome();
}

function renderTrustCenterStatus(){
  evaluateTrustNow();
  const coverage=Math.round((trustReport.provenanceCoverage||0)*100);
  const stale=trustReport.staleCriticalClaims?.length||0;
  const conflicts=trustReport.unresolvedConflicts?.length||0;

  if(trustMode==="simple"){
    $("trustCenterStatus").innerHTML=`
      <div class="trust-simple-statusbar ${trustReport.status==="HEALTHY"?"":"degraded"}">
        <div class="trust-simple-status-main"><i></i><div><b>${escapeHtml(trustReport.status)}</b><span>${escapeHtml(trustReport.status==="HEALTHY"?"All required trust checks pass.":"Attention required before relying on some capabilities.")}</span></div></div>
        <div class="trust-simple-status-meta">${coverage}% sourced · ${stale} stale critical · ${conflicts} conflicts</div>
      </div>
    `;
    return;
  }

  $("trustCenterStatus").innerHTML=`
    <div class="trust-status-grid">
      <div class="trust-status-primary ${trustReport.status==="HEALTHY"?"":"degraded"}">
        <div class="status-line"><i></i><b>${escapeHtml(trustReport.status)}</b></div>
        <small>${escapeHtml(trustReport.reason||"Trust status unavailable.")}</small>
      </div>
      <div class="trust-metric"><b>${coverage}%</b><span>active claims with provenance</span></div>
      <div class="trust-metric"><b>${stale}</b><span>stale critical claims</span></div>
      <div class="trust-metric"><b>${conflicts}</b><span>unresolved conflicts</span></div>
      <div class="trust-metric"><b>${trustReport.passedChecks||0}/${trustReport.totalChecks||0}</b><span>trust evaluations passing</span></div>
    </div>
  `;
}

function claimWhyItMatters(claim){
  const byId={
    "nepal-donation-path":"This establishes that a direct, official public action path currently exists.",
    "nepal-water-outcome":"This is the clearest documented evidence in this case that the response reached people.",
    "nepal-clinic-capacity":"This shows response capacity on the ground, but not how many patients were actually treated.",
    "nepal-flood-date":"This anchors the beginning of the case timeline.",
    "nepal-affected-estimate":"This gives an early sense of scale, while remaining explicitly provisional.",
    "nepal-appeal-amount":"This shows the scale of the formal emergency appeal, not how much has already been funded.",
    "bhutan-who-validation":"This is the central independent milestone supporting the elimination story.",
    "bhutan-zero-deaths":"This makes the outcome tangible: the story is about harm no longer occurring, not merely programme activity.",
    "bhutan-prevention-continues":"This prevents an elimination milestone from being mistaken for the end of prevention work.",
    "drc-confirmed-cases":"This is one of the core measures of the outbreak’s current scale.",
    "drc-confirmed-deaths":"This is why the case cannot be narrated as a success story.",
    "drc-recoveries":"This is meaningful response evidence, but cannot by itself establish overall improvement.",
    "drc-mixed-signals":"This is the key interpretive constraint: local progress and national deterioration can coexist.",
    "drc-no-direct-public-action":"This protects users from a convenient but weakly verified call to action."
  };
  return byId[claim.id] || "This claim materially changes how the current case should be understood.";
}

function claimSourceLinks(claim){
  return (claim.source_ids||[]).map(id=>{
    const source=window.COMMONS_TRUST.sourceById(trustRegistry,id);
    return source?`<a class="claim-source-link" href="${escapeHtml(source.url)}" target="_blank" rel="noopener">${escapeHtml(source.name)} ↗</a>`
      :`<span class="claim-source-link">MISSING SOURCE · ${escapeHtml(id)}</span>`;
  }).join("");
}

function renderInvestigativeClaim(claim,{compact=false,stale=false}={}){
  const source=window.COMMONS_TRUST.sourceById(trustRegistry,claim.source_ids?.[0]);
  const freshness=claim.freshness_days==null?"durable milestone":claim.freshness_days+" day freshness window";
  return `
    <article class="${compact?"trust-story-claim":"claim-card investigative-claim"} ${stale?"stale":""}">
      <div class="claim-top">
        <div>
          <div class="claim-statement">${escapeHtml(claim.statement)}</div>
          <div class="claim-meta">${escapeHtml(claim.claim_type.toUpperCase())} · ${escapeHtml(source?.organization||storyLabel(claim.story_id))} · ${escapeHtml(formatTrustDate(claim.as_of))}${compact?"":" · "+escapeHtml(freshness)+" · "+escapeHtml(claim.criticality)+" criticality"}${stale?" · STALE":""}</div>
        </div>
        <span class="claim-type ${escapeHtml(claim.claim_type)}">${escapeHtml(claim.claim_type)}</span>
      </div>
      <div class="claim-meaning">
        <b>Why this matters</b>
        <p>${escapeHtml(claimWhyItMatters(claim))}</p>
      </div>
      <div class="claim-limit">
        <b>What to keep in mind</b>
        <p>${escapeHtml(claim.limitations)}</p>
      </div>
      ${compact?"":`<div class="claim-sources">${claimSourceLinks(claim)}</div>`}
    </article>
  `;
}

function renderTrustSimpleTab(){
  if(!trustRegistry){
    $("trustCenterBody").innerHTML=`
      <div class="trust-simple-hero">
        <div class="trust-simple-kicker">DEGRADED MODE</div>
        <h3>I can’t prove the trust state right now.</h3>
        <p>The trust registry is unavailable, so COMMONS refuses to present itself as healthy. Direct trust-gated action remains disabled.</p>
      </div>
      <div class="correction-rule">${escapeHtml(trustLoadError||"Unknown trust registry error")}</div>
    `;
    return;
  }

  evaluateTrustNow();
  const coverage=Math.round((trustReport.provenanceCoverage||0)*100);
  const stale=trustReport.staleCriticalClaims?.length||0;
  const conflicts=trustReport.unresolvedConflicts?.length||0;
  const passing=(trustReport.passedChecks||0)+"/"+(trustReport.totalChecks||0);
  const currentClaims=(trustRegistry.claims||[])
    .filter(claim=>claim.story_id===activeStory.id && claim.status==="active")
    .sort((a,b)=>{
      const weight={high:3,medium:2,low:1};
      return (weight[b.criticality]||0)-(weight[a.criticality]||0) || String(b.as_of).localeCompare(String(a.as_of));
    })
    .slice(0,3);

  $("trustCenterBody").innerHTML=`
    <section class="investigation-intro">
      <div class="case-file-line"><span>EVIDENCE DESK · ${escapeHtml(activeStory.country.toUpperCase())}</span><span>Last verified ${escapeHtml(activeStory.updatedAt)}</span></div>
      <h3>${trustReport.status==="HEALTHY"?"Here’s why this case is currently safe to rely on.":"Here’s what needs attention before relying on this case."}</h3>
      <p>Healthy does not mean infallible. It means the evidence currently meets the rules COMMONS has declared for provenance, freshness, conflicts and safety.</p>
    </section>

    <div class="trust-proof-list">
      <div class="trust-proof ${coverage===100?"":"warn"}"><i></i><div><b>We can trace the claims</b><span>Every active material claim should lead back to registered evidence.</span></div><strong>${coverage}%</strong></div>
      <div class="trust-proof ${stale===0?"":"warn"}"><i></i><div><b>The critical evidence is current</b><span>Emergency numbers cannot stay silently “current” after their freshness window.</span></div><strong>${stale}</strong></div>
      <div class="trust-proof ${conflicts===0?"":"warn"}"><i></i><div><b>Disagreements are not hidden</b><span>If reliable sources conflict, the conflict belongs in the product.</span></div><strong>${conflicts}</strong></div>
      <div class="trust-proof ${trustReport.passedChecks===trustReport.totalChecks?"":"warn"}"><i></i><div><b>The safety checks pass</b><span>Provenance and action-safety rules are evaluated independently of this design.</span></div><strong>${passing}</strong></div>
    </div>

    <section class="trust-current-claims investigative-current">
      <div class="trust-current-claims-head">
        <div><span>WHAT WE CURRENTLY KNOW</span><h4>${escapeHtml(activeStory.country)} · the three claims that shape this case</h4></div>
      </div>
      <div class="trust-story-claims">${currentClaims.map(claim=>renderInvestigativeClaim(claim,{compact:true,stale:(trustReport.staleCriticalClaims||[]).some(item=>item.id===claim.id)})).join("")}</div>
    </section>

    <section class="case-uncertainty">
      <div class="case-section-kicker">WHAT THIS DOESN’T PROVE</div>
      <h4>Good evidence still has edges.</h4>
      <p>${escapeHtml(activeStory.guardrails?.[0]||"The current evidence should not be extended beyond what its sources support.")}</p>
      <p>${escapeHtml(activeStory.guardrails?.[1]||"Newer evidence may revise this story.")}</p>
    </section>

    <div class="trust-simple-actions">
      <button class="case-primary-button" id="simpleOpenAudit">Open the full evidence file →</button>
      <a class="word-button muted" href="${escapeHtml(trustRegistry.reporting?.issue_url||"https://github.com/mikelninh/COMMONS/issues/new")}" target="_blank" rel="noopener">Something looks wrong? Report it ↗</a>
    </div>
  `;

  if($("simpleOpenAudit"))$("simpleOpenAudit").onclick=()=>setTrustMode("audit","claims");
}

function renderTrustStatusTab(){
  if(!trustRegistry){
    $("trustCenterBody").innerHTML=`
      <div class="trust-section">
        <div class="trust-section-label">DEGRADED MODE</div>
        <h3>Trust registry unavailable.</h3>
        <p>COMMONS will not present itself as healthy when the registry that supports its trust status cannot be loaded.</p>
        <div class="correction-rule" style="margin-top:16px">${escapeHtml(trustLoadError||"Unknown registry error")}</div>
      </div>
    `;
    return;
  }

  const live=sourceStates.length
    ? sourceStates.map(state=>`<div class="source-card">
        <div class="source-top">
          <div><div class="source-name">${escapeHtml(state.name)}</div><div class="source-meta">Runtime public feed · ${state.ok?state.count+" records received":"currently unavailable"}</div></div>
          <span class="eval-state ${state.ok?"pass":"fail"}">${state.ok?"responding":"unavailable"}</span>
        </div>
      </div>`).join("")
    : '<p>Live source health has not been checked yet.</p>';

  const capabilities=(trustRegistry.capability_levels||[]).map(item=>`
    <div class="capability-card ${item.enabled?"":"disabled"}">
      <div class="capability-level">${escapeHtml(item.level)} · ${item.enabled?"ENABLED":"LOCKED"}</div>
      <h4>${escapeHtml(item.name)}</h4>
      <p>${escapeHtml(item.description)}</p>
    </div>
  `).join("");

  $("trustCenterBody").innerHTML=`
    <div class="trust-section">
      <div class="trust-intro"><strong>COMMONS does not ask you to trust an AI.</strong> It exposes the evidence, limits and checks that support each claim — and degrades visibly when those checks fail.</div>
    </div>

    <section class="trust-section">
      <div class="trust-section-label">Current authority ceiling</div>
      <h3>Power stops before consequential execution.</h3>
      <p>COMMONS currently observes, explains, proposes and hands actions back to the user. Reversible and consequential autonomous execution remain locked.</p>
      <div class="capability-grid">${capabilities}</div>
    </section>

    <section class="trust-section">
      <div class="trust-section-label">Runtime source health</div>
      <h3>Live feeds fail visibly.</h3>
      <p>These feeds support the ambient Earth layer. A feed outage does not silently become a model estimate.</p>
      <div class="source-list">${live}</div>
    </section>

    <section class="trust-section">
      <div class="trust-section-label">Correction rule</div>
      <div class="correction-rule">${escapeHtml(trustRegistry.correction_policy?.description||"Material corrections preserve history and explain why a claim changed.")}</div>
      <div class="trust-actions">
        <a class="word-button" href="./trust-registry.json" target="_blank" rel="noopener">Open raw trust registry ↗</a>
        <a class="word-button muted" href="${escapeHtml(trustRegistry.reporting?.issue_url||"https://github.com/mikelninh/COMMONS/issues/new")}" target="_blank" rel="noopener">Report an issue ↗</a>
      </div>
    </section>
  `;
}

function renderTrustClaimsTab(){
  if(!trustRegistry)return renderTrustStatusTab();
  const staleIds=new Set((trustReport.staleCriticalClaims||[]).map(claim=>claim.id));
  const current=(trustRegistry.claims||[])
    .filter(claim=>claim.story_id===activeStory.id && claim.status==="active")
    .sort((a,b)=>String(b.as_of).localeCompare(String(a.as_of)));
  const other=(trustRegistry.claims||[])
    .filter(claim=>claim.story_id!==activeStory.id && claim.status==="active")
    .sort((a,b)=>String(b.as_of).localeCompare(String(a.as_of)));

  $("trustCenterBody").innerHTML=`
    <section class="audit-case-header">
      <div class="case-file-line"><span>FULL EVIDENCE FILE · ${escapeHtml(activeStory.country.toUpperCase())}</span><span>${current.length} active claims</span></div>
      <h3>Follow each claim back to the source.</h3>
      <p>Observed is not inferred. Inferred is not fact. Proposed is not reality. Every note below explains both <strong>why it matters</strong> and <strong>where it stops.</strong></p>
    </section>

    <section class="audit-case-section">
      <div class="case-section-kicker">CURRENT CASE NOTES</div>
      <div class="claim-list investigative-ledger">
        ${current.map(claim=>renderInvestigativeClaim(claim,{stale:staleIds.has(claim.id)})).join("")}
      </div>
    </section>

    <section class="audit-case-section other-case-notes">
      <div class="case-section-kicker">OTHER STORIES IN THE ATLAS</div>
      <p class="audit-section-note">These claims remain part of the same public ledger, but they do not drive the case you are currently reading.</p>
      <div class="claim-list investigative-ledger">
        ${other.map(claim=>renderInvestigativeClaim(claim,{stale:staleIds.has(claim.id)})).join("")}
      </div>
    </section>
  `;
}

function renderTrustSourcesTab(){
  if(!trustRegistry)return renderTrustStatusTab();
  const cards=(trustRegistry.sources||[]).map(source=>`
    <article class="source-card">
      <div class="source-top">
        <div>
          <div class="source-name"><a href="${escapeHtml(source.url)}" target="_blank" rel="noopener">${escapeHtml(source.name)} ↗</a></div>
          <div class="source-meta">${escapeHtml(source.organization)} · ${escapeHtml(source.domain)} · updates: ${escapeHtml(source.update_pattern)}</div>
        </div>
        <span class="source-class">${escapeHtml(source.class.replaceAll("_"," "))}</span>
      </div>
      <div class="source-limits"><strong>KNOWN LIMIT:</strong> ${escapeHtml(source.limitations)}</div>
    </article>
  `).join("");
  $("trustCenterBody").innerHTML=`
    <div class="trust-section">
      <div class="trust-intro">Sources are not interchangeable. The registry records <strong>who produced the information, what role it plays, how it updates and where it can mislead.</strong></div>
      <div class="source-list">${cards}</div>
    </div>
  `;
}

function renderTrustEvaluationsTab(){
  evaluateTrustNow();
  const cards=(trustReport.checks||[]).map(check=>`
    <article class="eval-card ${check.passed?"pass":"fail"}">
      <div class="eval-top">
        <div class="eval-name">${escapeHtml(check.label)}</div>
        <span class="eval-state ${check.passed?"pass":"fail"}">${check.passed?"PASS":"FAIL"}</span>
      </div>
      <div class="eval-detail">${escapeHtml(check.detail)}</div>
    </article>
  `).join("");
  $("trustCenterBody").innerHTML=`
    <div class="trust-section">
      <div class="trust-intro">A release should answer a harder question than “does the page load?”: <strong>does COMMONS still deserve trust?</strong></div>
      <div class="eval-list">${cards||"<p>No evaluations available.</p>"}</div>
    </div>
  `;
}

function renderTrustIncidentsTab(){
  if(!trustRegistry)return renderTrustStatusTab();
  const incidents=(trustRegistry.incidents||[]);
  const cards=incidents.map(item=>`
    <article class="incident-card">
      <div class="incident-top">
        <div>
          <div class="incident-title">${escapeHtml(item.title)}</div>
          <div class="incident-meta">opened ${escapeHtml(formatTrustDate(item.opened_at))}${item.resolved_at?" · resolved "+escapeHtml(formatTrustDate(item.resolved_at)):""} · ${escapeHtml(item.severity)} severity</div>
        </div>
        <span class="incident-state ${item.status==="open"?"open":""}">${escapeHtml(item.status)}</span>
      </div>
      <div class="incident-detail">
        <strong>IMPACT</strong> · ${escapeHtml(item.impact)}<br><br>
        <strong>ROOT CAUSE</strong> · ${escapeHtml(item.root_cause)}<br><br>
        <strong>CORRECTION</strong> · ${escapeHtml(item.correction)}<br><br>
        <strong>PREVENTION</strong> · ${escapeHtml(item.prevention)}
      </div>
    </article>
  `).join("");
  $("trustCenterBody").innerHTML=`
    <div class="trust-section">
      <div class="trust-intro">Trust is not the absence of mistakes. It is <strong>visible failure, correction, preserved history and prevention.</strong></div>
      <div class="incident-list">${cards||'<div class="ledger-empty">No trust incidents recorded.</div>'}</div>
      <div class="trust-actions">
        <a class="word-button" href="${escapeHtml(trustRegistry.reporting?.issue_url||"https://github.com/mikelninh/COMMONS/issues/new")}" target="_blank" rel="noopener">Report a problem ↗</a>
      </div>
    </div>
  `;
}

function updateTrustModeChrome(){
  if(!$("trustCenter"))return;
  $("trustCenter").dataset.mode=trustMode;
  const simple=trustMode==="simple";
  $("trustModeSimple").classList.toggle("active",simple);
  $("trustModeAudit").classList.toggle("active",!simple);
  $("trustModeSimple").setAttribute("aria-pressed",simple?"true":"false");
  $("trustModeAudit").setAttribute("aria-pressed",simple?"false":"true");
  document.body.classList.toggle("trust-audit",!simple);
}

function setTrustMode(mode,tab=trustTab){
  trustMode=mode==="audit"?"audit":"simple";
  if(tab)trustTab=tab;
  updateTrustModeChrome();
  renderTrustCenter(trustTab);
}

function renderTrustCenter(tab=trustTab){
  trustTab=tab;
  evaluateTrustNow();
  renderTrustSnapshot();
  updateTrustModeChrome();
  renderTrustCenterStatus();

  qsa("[data-trust-tab]",$("trustCenter")).forEach(button=>{
    const active=button.dataset.trustTab===tab;
    button.classList.toggle("active",active);
    button.setAttribute("aria-selected",active?"true":"false");
  });

  if(trustMode==="simple"){
    renderTrustSimpleTab();
    return;
  }

  if(tab==="claims")renderTrustClaimsTab();
  else if(tab==="sources")renderTrustSourcesTab();
  else if(tab==="evaluations")renderTrustEvaluationsTab();
  else if(tab==="incidents")renderTrustIncidentsTab();
  else renderTrustStatusTab();
}

function openTrustCenter(tab="status",mode=null){
  closeAuxiliaryLayers("trustCenter");
  trustTab=tab;
  trustMode=mode || (tab==="status"?"simple":"audit");
  document.body.classList.add("trust-inspection");
  document.body.classList.toggle("trust-audit",trustMode==="audit");
  $("trustCenter").classList.add("open");
  $("trustCenter").setAttribute("aria-hidden","false");
  renderTrustCenter(tab);
}

function closeTrustCenter(){
  if(!$("trustCenter"))return;
  $("trustCenter").classList.remove("open");
  $("trustCenter").setAttribute("aria-hidden","true");
  document.body.classList.remove("trust-inspection","trust-audit");
}

function openEvidence(){
  closeAuxiliaryLayers("evidence");
  renderEvidence();
  $("evidence").classList.add("open");
  $("evidence").setAttribute("aria-hidden","false");
}
function closeEvidence(){
  $("evidence").classList.remove("open");
  $("evidence").setAttribute("aria-hidden","true");
}

function renderEvidence(){
  const claims=trustRegistry
    ? (trustRegistry.claims||[])
        .filter(claim=>claim.story_id===activeStory.id && claim.status==="active")
        .sort((a,b)=>String(b.as_of).localeCompare(String(a.as_of)))
        .slice(0,4)
    : [];

  const claimRows=claims.map(claim=>{
    const source=window.COMMONS_TRUST?.sourceById(trustRegistry,claim.source_ids?.[0]);
    return `
      <article class="evidence-peek-claim">
        <div class="evidence-peek-type">${escapeHtml(claim.claim_type)} · ${escapeHtml(formatTrustDate(claim.as_of))}</div>
        <h3>${escapeHtml(claim.statement)}</h3>
        <p>${escapeHtml(claim.limitations)}</p>
        ${source?`<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener">${escapeHtml(source.organization)} · open source ↗</a>`:""}
      </article>
    `;
  }).join("");

  const fallbackRows=activeStory.evidence.map(item=>`
    <article class="evidence-peek-claim">
      <div class="evidence-peek-type">${escapeHtml(item.date)}</div>
      <h3>${escapeHtml(item.label)}</h3>
      <p>${escapeHtml(item.note)}</p>
      <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">Open source ↗</a>
    </article>
  `).join("");
  const guardrails=activeStory.guardrails.map(item=>`<p>— ${escapeHtml(item)}</p>`).slice(0,3).join("");

  $("evidenceBody").innerHTML=`
    <div class="evidence-peek-intro">
      <span>HOW DO WE KNOW?</span>
      <h2>${escapeHtml(activeStory.country)} · ${escapeHtml(activeStory.title)}</h2>
      <p>These are the pieces of evidence doing the most work in this story. You should be able to inspect the source and see where each claim stops.</p>
    </div>

    <div class="evidence-peek-list">${claimRows||fallbackRows}</div>

    <section class="evidence-peek-guardrails">
      <span>WHAT THIS DOESN’T PROVE</span>
      ${guardrails}
    </section>

    <section class="evidence-peek-visual">
      <span>MAP NOTE</span>
      <p>${escapeHtml(activeStory.terrain.disclosure)}. Internal contour lines are a cinematic depth treatment, not factual elevation, damage, transmission-intensity or intervention data. Response threads are semantic rather than literal routes.</p><p>The Memory of Earth mark records a documented story state; it is not a score, rank, completion badge or proof that the wider problem is solved.</p>
    </section>

    <div class="evidence-peek-actions">
      <button class="word-button" id="evidenceTrustBtn">Open full evidence file →</button>
      <button class="word-button muted" id="evidenceDoneBtn">Back to story</button>
    </div>
  `;

  if($("evidenceTrustBtn"))$("evidenceTrustBtn").onclick=()=>openTrustCenter("claims","audit");
  if($("evidenceDoneBtn"))$("evidenceDoneBtn").onclick=closeEvidence;
}

function openShare(){
  closeAuxiliaryLayers("share");
  drawShareCard();
  $("share").classList.add("open");
}
function closeShare(){
  $("share").classList.remove("open");
  pendingShareInterventionId=null;
}

function drawShareCard(){
  const canvas=$("shareCanvas");
  const scale=2;
  canvas.width=1600*scale;
  canvas.height=900*scale;
  const ctx=canvas.getContext("2d");
  ctx.setTransform(scale,0,0,scale,0,0);

  ctx.fillStyle="#030403";
  ctx.fillRect(0,0,1600,900);

  const earth=ctx.createRadialGradient(1210,415,40,1210,415,365);
  earth.addColorStop(0,"#171a15");
  earth.addColorStop(.67,"#0b0d0a");
  earth.addColorStop(1,"#050605");
  ctx.fillStyle=earth;
  ctx.beginPath();ctx.arc(1210,415,330,0,Math.PI*2);ctx.fill();

  ctx.strokeStyle="rgba(239,238,231,.08)";ctx.lineWidth=1;
  for(let r=95;r<=280;r+=62){ctx.beginPath();ctx.arc(1210,415,r,0,Math.PI*2);ctx.stroke();}

  ctx.fillStyle=activeStory.colors.attention;
  ctx.beginPath();ctx.arc(1295,335,6,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle=hexToRgba(activeStory.colors.attention,.5);
  ctx.beginPath();ctx.arc(1295,335,28,0,Math.PI*2);ctx.stroke();

  ctx.strokeStyle=hexToRgba(activeStory.colors.attention,.68);ctx.lineWidth=2;
  ctx.beginPath();ctx.moveTo(1208,392);ctx.quadraticCurveTo(1246,350,1295,335);ctx.stroke();

  if((activeStory.bloom||[]).length){
    const bloom=ctx.createRadialGradient(1320,373,0,1320,373,68);
    bloom.addColorStop(0,hexToRgba(activeStory.colors.outcome,.4));
    bloom.addColorStop(1,hexToRgba(activeStory.colors.outcome,0));
    ctx.fillStyle=bloom;ctx.beginPath();ctx.arc(1320,373,68,0,Math.PI*2);ctx.fill();
  }

  ctx.fillStyle="#efeee7";
  ctx.font="700 24px Helvetica Neue, Arial";
  ctx.fillText("COMMONS / WORLD PULSE",82,78);
  ctx.fillStyle="#686d67";
  ctx.font="600 18px Helvetica Neue, Arial";
  ctx.fillText("STORIES OF RESPONSE · VOL. 01",82,110);

  ctx.fillStyle=activeStory.colors.attention;
  ctx.font="600 20px Helvetica Neue, Arial";
  ctx.fillText((activeStory.country+" · "+activeStory.title).toUpperCase(),82,187);

  ctx.fillStyle="#efeee7";
  ctx.font="500 112px Helvetica Neue, Arial";
  ctx.fillText(activeStory.share.value,76,360);

  ctx.fillStyle="#c7c5bb";
  ctx.font="italic 38px Georgia, serif";
  wrapText(ctx,activeStory.share.label,82,420,710,48);

  ctx.fillStyle="#71766f";
  ctx.font="400 22px Helvetica Neue, Arial";
  wrapText(ctx,activeStory.share.note,82,560,690,34);

  const grammarX=[82,255,455];
  activeStory.grammar.forEach((label,index)=>{
    ctx.fillStyle=index===2?activeStory.colors.outcome:activeStory.colors.attention;
    ctx.font="600 18px Helvetica Neue, Arial";
    ctx.fillText((index===0?"◉ ":index===1?"— ":"✦ ")+label.toUpperCase(),grammarX[index],720);
  });

  ctx.fillStyle="#5d635c";ctx.font="400 18px Helvetica Neue, Arial";
  ctx.fillText(activeStory.share.evidenceLine,82,783);
  ctx.fillText("mikelninh.github.io/COMMONS",82,824);
}

function wrapText(ctx,text,x,y,maxWidth,lineHeight){
  const words=String(text).split(" ");
  let line="";
  for(let i=0;i<words.length;i++){
    const test=line+words[i]+" ";
    if(ctx.measureText(test).width>maxWidth&&i>0){
      ctx.fillText(line,x,y);
      line=words[i]+" ";
      y+=lineHeight;
    }else line=test;
  }
  ctx.fillText(line,x,y);
}

function actionUrl(){
  const u=new URL(location.href);
  u.searchParams.delete("signal");
  u.searchParams.delete("action");
  u.searchParams.set("story",activeStory.id);
  u.searchParams.set("scene","signal");
  return u.toString();
}

async function shareAction(){
  const sourceLines=activeStory.evidence.slice(0,2).map(item=>item.date+" · "+item.label);
  const text=[
    "WORLD PULSE / STORIES OF RESPONSE",
    activeStory.country+" — "+activeStory.title,
    "",
    activeStory.share.value+" · "+activeStory.share.label,
    activeStory.share.note,
    "",
    activeStory.grammar.join(" → "),
    ...sourceLines,
    actionUrl()
  ].join("\n");
  try{
    if(navigator.share){
      await navigator.share({title:"WORLD PULSE — "+activeStory.title,text,url:actionUrl()});
      recordActionShare("share_completed","browser_share");
      toast("Share completed");
    }else{
      await navigator.clipboard.writeText(text);
      recordActionShare("share_prepared","browser_local");
      toast("Story copied with provenance");
    }
  }catch(e){
    pendingShareInterventionId=null;
  }
}

async function shareCardImage(){
  const canvas=$("shareCanvas");
  const blob=await new Promise(resolve=>canvas.toBlob(resolve,"image/png",.94));
  if(!blob)return;
  const file=new File([blob],"world-pulse-"+activeStory.slug+".png",{type:"image/png"});
  try{
    if(navigator.canShare?.({files:[file]})&&navigator.share){
      await navigator.share({files:[file],title:"WORLD PULSE — "+activeStory.title,text:activeStory.grammar.join(" → ")});
      recordActionShare("share_completed","browser_share");
      toast("Share completed");
    }else{
      const a=document.createElement("a");
      a.href=URL.createObjectURL(blob);
      a.download="world-pulse-"+activeStory.slug+".png";
      a.click();
      setTimeout(()=>URL.revokeObjectURL(a.href),1000);
      recordActionShare("share_prepared","browser_local");
      toast("Share image created");
    }
  }catch(e){
    pendingShareInterventionId=null;
  }
}

async function shareSignal(s){
  const m=sourceMeta[s.source]||{freshness:"PUBLIC"};
  const text=[
    s.title,
    s.source+" · "+m.freshness+" · "+age(s.time),
    s.reasons?.length?"Surfaced because: "+s.reasons.join(" · "):"Current public source signal",
    s.url?"Primary source: "+s.url:"",
    "",
    "COMMONS / WORLD PULSE"
  ].filter(Boolean).join("\n");
  try{
    if(navigator.share)await navigator.share({title:"WORLD PULSE signal",text,url:s.url||location.href});
    else{
      await navigator.clipboard.writeText(text);
      toast("Signal copied with provenance");
    }
  }catch(e){}
}

function toast(message){
  $("toast").textContent=message;
  $("toast").classList.add("show");
  clearTimeout(toast._t);
  toast._t=setTimeout(()=>$("toast").classList.remove("show"),2100);
}

function escapeHtml(v){
  return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
}

function bindEvents(){
  $("openingEnter").onclick=()=>enterStory(STORIES[0].id,0);
  $("openingBrowse").onclick=openStories;
  $("enterBtn").onclick=()=>startStory(0);
  $("currentStory").onclick=()=>startStory(0);
  $("storiesBtn").onclick=openStories;
  $("homeLookBtn").onclick=openLook;
  $("lookBtn").onclick=openLook;
  $("lookClose").onclick=closeLook;
  $("beliefBtn").onclick=()=>openTrustCenter("claims","simple");
  $("storyBelief").onclick=openEvidence;
  $("storyActionBtn").onclick=()=>jumpToScene(activeStory.scenes.length-1);
  $("actionLedgerBtn").onclick=()=>openActionLab("ledger");
  $("trustBtn").onclick=()=>openTrustCenter("status","simple");
  $("trustSnapshot").onclick=()=>openTrustCenter("status","simple");
  $("trustCenterClose").onclick=closeTrustCenter;
  $("trustModeSimple").onclick=()=>setTrustMode("simple","status");
  $("trustModeAudit").onclick=()=>setTrustMode("audit",trustTab||"claims");
  if($("browseStoriesInline"))$("browseStoriesInline").onclick=()=>openStories();
  qsa("[data-trust-tab]",$("trustCenter")).forEach(button=>{
    button.onclick=()=>renderTrustCenter(button.dataset.trustTab);
  });
  $("actionLabClose").onclick=closeActionLab;
  $("actionCurrentTab").onclick=()=>renderActionLab("current");
  $("actionLedgerTab").onclick=()=>renderActionLab("ledger");
  $("evidenceClose").onclick=closeEvidence;
  $("passBtn").onclick=openShare;
  $("soundBtn").onclick=toggleSound;
  $("storyPass").onclick=openShare;
  $("shareClose").onclick=closeShare;
  $("handoffClose").onclick=closeHandoff;
  $("handoffContinue").onclick=continueExternalHandoff;
  $("handoffFollow").onclick=()=>{
    closeHandoff();
    followCurrentStoryInline();
  };
  $("shareStory").onclick=shareAction;
  $("shareImage").onclick=shareCardImage;
  $("storyClose").onclick=()=>stopStory(true);
  $("prevScene").onclick=prevScene;
  $("nextScene").onclick=nextScene;
  $("playToggle").onclick=togglePlay;
  $("timeScrubber").oninput=e=>scrubTime(e.target.value);

  window.addEventListener("scroll",requestScrollCinema,{passive:true});
  window.addEventListener("resize",requestScrollCinema,{passive:true});
  window.addEventListener("wheel",()=>{if(storyPlaying)stopAutoScroll()},{passive:true});
  window.addEventListener("touchstart",()=>{if(storyPlaying)stopAutoScroll()},{passive:true});

  $("share").addEventListener("click",e=>{if(e.target===$("share"))closeShare();});
  $("handoff").addEventListener("click",e=>{if(e.target===$("handoff"))closeHandoff();});

  document.addEventListener("keydown",e=>{
    if(e.key==="Escape"){
      if($("share").classList.contains("open"))return closeShare();
      if($("handoff").classList.contains("open"))return closeHandoff();
      if($("actionLab").classList.contains("open"))return closeActionLab();
      if($("trustCenter").classList.contains("open"))return closeTrustCenter();
      if($("evidence").classList.contains("open"))return closeEvidence();
      if($("look").classList.contains("open"))return closeLook();
      if($("story").classList.contains("active"))return stopStory(true);
      if(!$("opening").classList.contains("hidden"))return hideOpening();
    }
    if(!$("story").classList.contains("active"))return;
    if(e.key==="ArrowRight")nextScene();
    if(e.key==="ArrowLeft")prevScene();
    if(e.key===" "){e.preventDefault();togglePlay();}
  });
}

function routeFromUrl(){
  const params=new URLSearchParams(location.search);
  const storyId=params.get("story")||params.get("action");
  const routedStory=storyId?storyById(storyId):null;

  if(routedStory){
    selectStory(routedStory.id);
    hideOpening();
    const id=params.get("scene");
    const index=Math.max(0,activeStory.scenes.findIndex(scene=>scene.id===id));
    startStory(index);
    return;
  }

  const signalId=params.get("signal");
  if(signalId){
    hideOpening();
    openLook();
    const signal=signals.find(item=>item.id===signalId);
    if(signal)focusSignal(signal);
  }
}

async function init(){
  $("openingDate").textContent=new Intl.DateTimeFormat("en",{month:"long",year:"numeric"}).format(new Date()).toUpperCase();
  bindEvents();
  updateLedgerCount();
  updateStoryChrome();
  updateSignature();
  await Promise.allSettled([loadTrustSystem(),loadCountries(),refreshSignals()]);
  initialized=true;
  renderTrustSnapshot();
  buildTerrainMap();
  setHomeGlobe();
  $("loading").classList.add("hide");
  routeFromUrl();
}

init();
setInterval(()=>{if(initialized)refreshSignals();},60000);
