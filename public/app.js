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

const ACTION = {
  id: "nepal-flash-floods-2026",
  title: "Nepal · Flash Floods 2026",
  lat: 28.15,
  lon: 85.3,
  status: "OPEN LOOP",
  updatedAt: "8 Sep 2026",
  responder: "IFRC + Nepal Red Cross Society",
  appeal: "https://www.ifrc.org/press-release/ifrc-launches-chf-25-million-emergency-appeal-response-devastating-nepal-flash-floods",
  outcome: "https://www.ifrc.org/press-release/nepal-floods-ifrc-delivers-safe-water-and-health-care-affected-communities",
  directory: "https://www.ifrc.org/national-societies-directory/nepal-red-cross-society",
  donate: "https://www.ifrc.org/donate",
  scenes: [
    {
      id: "signal",
      milestone: 0,
      kicker: "26 Aug 2026 · Pulse",
      composition: "left-monument",
      camera: {lat: 22, lng: 79, altitude: 1.78},
      offset: [245, -8],
      headline: "Flash floods struck <span class='attention'>northern Nepal.</span>",
      copy: "Homes, roads and bridges were damaged and communities were isolated. The first visual state is intentionally simple: a disturbance, not a conclusion.",
      source: "IFRC · 27 Aug 2026",
      duration: 5200
    },
    {
      id: "impact",
      milestone: 0,
      kicker: "Early estimate · Human impact",
      composition: "metric-left",
      camera: {lat: 28.1, lng: 85.3, altitude: 1.28},
      offset: [280, 0],
      value: "~93,000",
      tone: "attention",
      label: "people may have been affected",
      copy: "An early IFRC estimate while assessments were continuing. It is not presented as a final affected-population count.",
      source: "IFRC Emergency Appeal · 27 Aug 2026",
      duration: 5700
    },
    {
      id: "verify",
      milestone: 1,
      kicker: "27 Aug 2026 · Thread",
      composition: "right-whisper",
      camera: {lat: 27.9, lng: 84.8, altitude: 1.2},
      offset: [-250, -4],
      headline: "The signal became <span class='human'>a verified response.</span>",
      copy: "IFRC launched a formal Emergency Appeal alongside Nepal Red Cross Society operations. The luminous thread represents an accountable response pathway — not a tracked shipment route.",
      source: "Primary evidence · IFRC",
      duration: 5400
    },
    {
      id: "response",
      milestone: 1,
      kicker: "Verified response",
      composition: "center-monument",
      camera: {lat: 27.9, lng: 84.9, altitude: 1.34},
      offset: [0, 65],
      value: "CHF 25M",
      tone: "attention",
      label: "Emergency Appeal",
      copy: "Shelter, health, clean water, sanitation, cash assistance and recovery were named response priorities.",
      source: "IFRC + Nepal Red Cross Society",
      duration: 5600
    },
    {
      id: "outcome",
      milestone: 2,
      kicker: "08 Sep 2026 · Bloom",
      composition: "low-left",
      camera: {lat: 28.03, lng: 85.16, altitude: 1.04},
      offset: [260, -58],
      value: "~2,000",
      tone: "outcome",
      label: "people with safe drinking water restored in Nuwakot",
      copy: "This is evidence that the response reached people. It is not proof that any one contribution caused the outcome.",
      source: "IFRC outcome update · 8 Sep 2026",
      duration: 6500
    },
    {
      id: "capacity",
      milestone: 2,
      kicker: "Response capacity",
      composition: "metric-right",
      camera: {lat: 28.03, lng: 85.16, altitude: 1.1},
      offset: [-255, -10],
      value: "100/day",
      tone: "outcome",
      label: "mobile primary clinic capacity",
      copy: "A concrete piece of response capacity reported in the same IFRC update.",
      source: "IFRC · 8 Sep 2026",
      duration: 5200
    },
    {
      id: "meaning",
      milestone: 3,
      kicker: "Now · Open loop",
      composition: "center-monument",
      camera: {lat: 25.5, lng: 82.5, altitude: 1.58},
      offset: [0, 25],
      headline: "Pulse. Thread. <span class='outcome'>Bloom.</span>",
      copy: "Disturbance becomes legible. Response becomes visible. Improvement is only shown when evidence supports it.",
      source: "COMMONS visual grammar",
      duration: 5200
    },
    {
      id: "you",
      milestone: 3,
      kicker: "The loop remains open",
      composition: "final-center",
      camera: {lat: 24, lng: 78, altitude: 1.92},
      offset: [0, 30],
      headline: "What happens next is <span class='human'>still being written.</span>",
      copy: "Help through the verified response, inspect the evidence, or pass the story on with its provenance intact.",
      source: "Last outcome evidence in this story · 8 Sep 2026",
      duration: 12000,
      actions: true
    }
  ]
};

const TIME_SCENES = [0,2,4,7];
const THREADS = [
  {
    startLat: 27.7172, startLng: 85.3240,
    endLat: 27.95, endLng: 85.18,
    note: "Visual response pathway inside Nepal; not a tracked logistics route."
  }
];
const BLOOM = [
  [27.94,85.13,.64],[27.97,85.17,.52],[27.92,85.20,.46],[28.00,85.10,.38],
  [27.90,85.15,.33],[27.96,85.24,.29],[28.03,85.18,.25],[27.88,85.09,.24],
  [28.01,85.27,.22],[27.86,85.22,.2]
].map(([lat,lon,radius],i)=>({kind:"bloom",id:"bloom-"+i,lat,lon,radius}));

let countries = [];
let signals = [];
let sourceStates = [];
let storyIndex = 0;
let storyPlaying = false;
let storyTimer = null;
let currentMilestone = 0;
let currentSignal = null;
let initialized = false;

const actionPoint = {
  kind:"action",
  action:true,
  id:ACTION.id,
  lat:ACTION.lat,
  lon:ACTION.lon,
  source:"COMMONS ACTION",
  title:ACTION.title
};

const world = Globe({rendererConfig:{antialias:true,alpha:true}})($("globe"))
  .backgroundColor("rgba(0,0,0,0)")
  .showAtmosphere(true)
  .atmosphereColor("#667267")
  .atmosphereAltitude(.105)
  .showGraticules(true)
  .pointLat(d=>d.lat)
  .pointLng(d=>d.lon)
  .pointColor(d=>{
    if(d.kind==="bloom") return "rgba(154,203,151,.18)";
    if(d.kind==="action") return "#d2b06d";
    return sourceColor(d.source);
  })
  .pointAltitude(d=>d.kind==="bloom"?.0015:d.kind==="action"?.016:.012)
  .pointRadius(d=>d.kind==="bloom"?d.radius:d.kind==="action"?.15:Math.max(.05,Math.min(.13,.045+(Number(d.magnitude)||1)*.012)))
  .pointResolution(16)
  .pointLabel(()=>"")
  .onPointClick(d=>d.kind==="action"?startStory(0):d.kind==="bloom"?null:focusSignal(d))
  .ringsData([])
  .ringLat(d=>d.lat)
  .ringLng(d=>d.lon)
  .ringAltitude(.003)
  .ringColor(d=>()=>d.kind==="action"?"rgba(210,176,109,.58)":"rgba(197,201,192,.18)")
  .ringMaxRadius(d=>d.kind==="action"?5.4:2.25)
  .ringPropagationSpeed(d=>d.kind==="action"?.62:.42)
  .ringRepeatPeriod(d=>d.kind==="action"?2500:3900)
  .arcsData([])
  .arcStartLat("startLat")
  .arcStartLng("startLng")
  .arcEndLat("endLat")
  .arcEndLng("endLng")
  .arcColor(()=>["rgba(210,176,109,.03)","rgba(210,176,109,.88)"])
  .arcAltitude(.035)
  .arcStroke(.38)
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
  const nepal = String(d?.id)==="524";
  if(nepal && currentMilestone>=2) return "rgba(154,203,151,.25)";
  if(nepal) return "rgba(210,176,109,.18)";
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

function setHomeGlobe(){
  currentMilestone=0;
  world.controls().autoRotate=!reduceMotion;
  world.globeOffset(innerWidth<650?[0,-90]:[250,-5]);
  world.pointOfView({lat:14,lng:35,altitude:2.08},reduceMotion?0:950);
  updateAtlasLayers(false);
}

async function loadCountries(){
  try{
    const r=await fetch(WORLD_ATLAS,{cache:"force-cache"});
    if(!r.ok) throw new Error("world atlas "+r.status);
    const topo=await r.json();
    if(!window.topojson) throw new Error("topojson unavailable");
    countries=window.topojson.feature(topo,topo.objects.countries).features;
    world.polygonsData(countries);
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
}

function updateAtlasLayers(storyMode=$("story").classList.contains("active")){
  let points;
  if(storyMode){
    points=[actionPoint];
    if(currentMilestone>=2)points.push(...BLOOM);
  }else{
    points=[...signals.slice(0,150),actionPoint];
  }
  world.pointsData(points);

  const surfaced=[...signals]
    .sort((a,b)=>priority(b)-priority(a))
    .filter(s=>priority(s)>=5)
    .slice(0,14);
  world.ringsData(storyMode?[actionPoint]:[...surfaced,actionPoint]);
  world.arcsData(storyMode&&currentMilestone>=1?THREADS:[]);
  world.polygonCapColor(countryColor);
  if(countries.length)world.polygonsData([...countries]);
}

function setMilestone(milestone){
  currentMilestone=Math.max(0,Math.min(3,Number(milestone)||0));
  $("timeScrubber").value=String(currentMilestone);
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

function startStory(index=0){
  document.body.classList.add("story-mode");
  hideOpening();
  closeAuxiliaryLayers();
  $("home").classList.add("hidden");
  $("story").classList.add("active");
  world.controls().autoRotate=false;
  storyIndex=Math.max(0,Math.min(ACTION.scenes.length-1,index));
  storyPlaying=!reduceMotion;
  renderScene(storyIndex);
}

function stopStory(returnHome=true){
  document.body.classList.remove("story-mode");
  clearTimeout(storyTimer);
  storyTimer=null;
  storyPlaying=false;
  $("story").classList.remove("active");
  if(returnHome){
    $("home").classList.remove("hidden");
    const u=new URL(location.href);
    u.searchParams.delete("action");
    u.searchParams.delete("scene");
    history.replaceState(null,"",u);
    setHomeGlobe();
  }
}

function renderScene(index){
  clearTimeout(storyTimer);
  storyIndex=Math.max(0,Math.min(ACTION.scenes.length-1,index));
  const scene=ACTION.scenes[storyIndex];
  setMilestone(scene.milestone);

  $("story").dataset.composition=scene.composition;
  $("sceneStage").className="scene-stage "+scene.composition;
  $("scene").classList.remove("enter");
  void $("scene").offsetWidth;
  $("scene").innerHTML=sceneMarkup(scene);
  $("scene").classList.add("enter");

  world.globeOffset(sceneOffset(scene));
  world.pointOfView(scene.camera,reduceMotion?0:1200);

  const u=new URL(location.href);
  u.searchParams.delete("signal");
  u.searchParams.set("action",ACTION.id);
  u.searchParams.set("scene",scene.id);
  history.replaceState(null,"",u);

  bindSceneActions();
  updatePlayLabel();

  if(storyPlaying&&!reduceMotion){
    storyTimer=setTimeout(()=>{
      if(storyIndex<ACTION.scenes.length-1)renderScene(storyIndex+1);
      else{
        storyPlaying=false;
        updatePlayLabel();
      }
    },scene.duration);
  }
}

function sceneMarkup(scene){
  const body=scene.value
    ? `<div class="scene-number ${escapeHtml(scene.tone||"")}">${escapeHtml(scene.value)}</div>
       <div class="scene-label">${escapeHtml(scene.label)}</div>`
    : `<h2 class="scene-headline">${scene.headline}</h2>`;

  const actions=scene.actions?`
    <div class="scene-actions">
      <button class="word-button" data-action="help">Help through IFRC ↗</button>
      <button class="word-button muted" data-action="belief">Why we believe this</button>
      <button class="word-button muted" data-action="pass">Pass this on</button>
    </div>`:"";

  return `
    <div class="scene-kicker">${escapeHtml(scene.kicker)}</div>
    ${body}
    <div class="scene-copy">${escapeHtml(scene.copy)}</div>
    <div class="scene-source">${escapeHtml(scene.source)}</div>
    ${actions}
  `;
}

function bindSceneActions(){
  qsa("[data-action]",$("scene")).forEach(btn=>{
    btn.onclick=()=>{
      if(btn.dataset.action==="help")window.open(ACTION.donate,"_blank","noopener");
      if(btn.dataset.action==="belief")openEvidence();
      if(btn.dataset.action==="pass")openShare();
    };
  });
}

function nextScene(){
  storyPlaying=false;
  renderScene(Math.min(ACTION.scenes.length-1,storyIndex+1));
}
function prevScene(){
  storyPlaying=false;
  renderScene(Math.max(0,storyIndex-1));
}
function togglePlay(){
  storyPlaying=!storyPlaying;
  renderScene(storyIndex);
}
function updatePlayLabel(){
  $("playToggle").textContent=storyPlaying?"Pause":"Play";
  $("playToggle").setAttribute("aria-label",storyPlaying?"Pause story":"Play story");
}

function scrubTime(value){
  storyPlaying=false;
  clearTimeout(storyTimer);
  const milestone=Math.max(0,Math.min(3,Number(value)||0));
  setMilestone(milestone);
  renderScene(TIME_SCENES[milestone]);
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
  const live=sourceStates.map(s=>{
    const m=sourceMeta[s.name];
    return `
      <div class="evidence-row">
        <div class="evidence-date">${escapeHtml(m.freshness)}<br>${s.ok?"responding":"unavailable"}</div>
        <a href="${m.url}" target="_blank" rel="noopener">${escapeHtml(s.name)} — ${escapeHtml(m.scope)}</a>
      </div>`;
  }).join("");

  $("evidenceBody").innerHTML=`
    <p class="evidence-intro">Beauty is allowed to move you. It is not allowed to hide where a claim came from.</p>

    <section class="evidence-section">
      <h3>Nepal · evidence chain</h3>
      <div class="evidence-row">
        <div class="evidence-date">27 Aug<br>2026</div>
        <a href="${ACTION.appeal}" target="_blank" rel="noopener">IFRC Emergency Appeal — early affected-population estimate, appeal amount and named response priorities.</a>
      </div>
      <div class="evidence-row">
        <div class="evidence-date">08 Sep<br>2026</div>
        <a href="${ACTION.outcome}" target="_blank" rel="noopener">IFRC response update — safe drinking water restored for around 2,000 people and mobile primary clinic capacity.</a>
      </div>
      <div class="evidence-row">
        <div class="evidence-date">Responder</div>
        <a href="${ACTION.directory}" target="_blank" rel="noopener">Nepal Red Cross Society — IFRC National Society directory.</a>
      </div>
    </section>

    <section class="evidence-section">
      <h3>What the visual language means</h3>
      <div class="grammar-note">
        <div><b>◉ Pulse</b><span>A sourced disturbance or signal. It does not by itself establish human impact.</span></div>
        <div><b>— Thread</b><span>A verified response pathway. The line is a visual grammar, not a tracked shipment or causal trace.</span></div>
        <div><b>✦ Bloom</b><span>Documented improvement or response evidence. It appears only after a dated source supports it.</span></div>
      </div>
    </section>

    <section class="evidence-section">
      <h3>Claims deliberately not made</h3>
      <div class="guardrails">
        <div class="guardrail">~93,000 is not presented as a final affected-population count.</div>
        <div class="guardrail">We do not claim every affected person has been reached.</div>
        <div class="guardrail">We do not show a funding percentage without a current authoritative source.</div>
        <div class="guardrail">We do not imply that a particular donation caused the displayed outcomes.</div>
        <div class="guardrail">The loop remains open. Newer evidence should extend the timeline instead of rewriting history.</div>
      </div>
    </section>

    <section class="evidence-section">
      <h3>Current Earth layer</h3>
      ${live||"<p>Source health appears after the public feeds respond.</p>"}
    </section>
  `;
}

function openShare(){
  closeAuxiliaryLayers("share");
  drawShareCard();
  $("share").classList.add("open");
}
function closeShare(){
  $("share").classList.remove("open");
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

  ctx.fillStyle="#d2b06d";
  ctx.beginPath();ctx.arc(1295,335,6,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle="rgba(210,176,109,.5)";
  ctx.beginPath();ctx.arc(1295,335,28,0,Math.PI*2);ctx.stroke();

  ctx.strokeStyle="rgba(210,176,109,.68)";ctx.lineWidth=2;
  ctx.beginPath();ctx.moveTo(1208,392);ctx.quadraticCurveTo(1246,350,1295,335);ctx.stroke();

  const bloom=ctx.createRadialGradient(1320,373,0,1320,373,68);
  bloom.addColorStop(0,"rgba(154,203,151,.4)");
  bloom.addColorStop(1,"rgba(154,203,151,0)");
  ctx.fillStyle=bloom;ctx.beginPath();ctx.arc(1320,373,68,0,Math.PI*2);ctx.fill();

  ctx.fillStyle="#efeee7";
  ctx.font="700 24px Helvetica Neue, Arial";
  ctx.fillText("COMMONS / WORLD PULSE",82,78);
  ctx.fillStyle="#686d67";
  ctx.font="600 18px Helvetica Neue, Arial";
  ctx.fillText("LIVING ATLAS",82,110);

  ctx.fillStyle="#d2b06d";
  ctx.font="600 20px Helvetica Neue, Arial";
  ctx.fillText("NEPAL · FLASH FLOODS 2026",82,187);

  ctx.fillStyle="#efeee7";
  ctx.font="500 112px Helvetica Neue, Arial";
  ctx.fillText("~2,000",76,360);

  ctx.fillStyle="#c7c5bb";
  ctx.font="italic 38px Georgia, serif";
  wrapText(ctx,"people with safe drinking water restored in Nuwakot",82,420,710,48);

  ctx.fillStyle="#71766f";
  ctx.font="400 22px Helvetica Neue, Arial";
  wrapText(ctx,"A documented response outcome. Not a claim that any single contribution caused it.",82,560,660,34);

  ctx.fillStyle="#d2b06d";ctx.font="600 18px Helvetica Neue, Arial";
  ctx.fillText("◉ PULSE",82,720);
  ctx.fillText("— THREAD",210,720);
  ctx.fillStyle="#9acb97";ctx.fillText("✦ BLOOM",370,720);

  ctx.fillStyle="#5d635c";ctx.font="400 18px Helvetica Neue, Arial";
  ctx.fillText("Outcome evidence · IFRC · 8 Sep 2026 · Loop open",82,783);
  ctx.fillText("mikelninh.github.io/COMMONS",82,824);
}

function wrapText(ctx,text,x,y,maxWidth,lineHeight){
  const words=text.split(" ");
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
  u.searchParams.set("action",ACTION.id);
  u.searchParams.set("scene","signal");
  return u.toString();
}

async function shareAction(){
  const text=[
    "WORLD PULSE / LIVING ATLAS",
    "Nepal · Flash Floods 2026",
    "",
    "~93,000 people may have been affected · IFRC estimate, 27 Aug 2026",
    "CHF 25M Emergency Appeal",
    "~2,000 people with safe drinking water restored · IFRC, 8 Sep 2026",
    "Mobile clinic capacity: 100/day",
    "",
    "Pulse → Thread → Bloom",
    "Signal → response → outcome evidence",
    actionUrl()
  ].join("\n");
  try{
    if(navigator.share)await navigator.share({title:"WORLD PULSE / LIVING ATLAS",text,url:actionUrl()});
    else{
      await navigator.clipboard.writeText(text);
      toast("Evidence chain copied");
    }
  }catch(e){}
}

async function shareCardImage(){
  const canvas=$("shareCanvas");
  const blob=await new Promise(resolve=>canvas.toBlob(resolve,"image/png",.94));
  if(!blob)return;
  const file=new File([blob],"world-pulse-living-atlas-nepal.png",{type:"image/png"});
  try{
    if(navigator.canShare?.({files:[file]})&&navigator.share){
      await navigator.share({files:[file],title:"WORLD PULSE / LIVING ATLAS",text:"Pulse → Thread → Bloom"});
    }else{
      const a=document.createElement("a");
      a.href=URL.createObjectURL(blob);
      a.download="world-pulse-living-atlas-nepal.png";
      a.click();
      setTimeout(()=>URL.revokeObjectURL(a.href),1000);
      toast("Share image created");
    }
  }catch(e){}
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
  $("openingEnter").onclick=()=>startStory(0);
  $("enterBtn").onclick=()=>startStory(0);
  $("currentStory").onclick=()=>startStory(0);
  $("homeLookBtn").onclick=openLook;
  $("lookBtn").onclick=openLook;
  $("lookClose").onclick=closeLook;
  $("beliefBtn").onclick=openEvidence;
  $("storyBelief").onclick=openEvidence;
  $("evidenceClose").onclick=closeEvidence;
  $("passBtn").onclick=openShare;
  $("storyPass").onclick=openShare;
  $("shareClose").onclick=closeShare;
  $("shareStory").onclick=shareAction;
  $("shareImage").onclick=shareCardImage;
  $("storyClose").onclick=()=>stopStory(true);
  $("prevScene").onclick=prevScene;
  $("nextScene").onclick=nextScene;
  $("playToggle").onclick=togglePlay;
  $("timeScrubber").oninput=e=>scrubTime(e.target.value);

  $("share").addEventListener("click",e=>{if(e.target===$("share"))closeShare();});

  document.addEventListener("keydown",e=>{
    if(e.key==="Escape"){
      if($("share").classList.contains("open"))return closeShare();
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
  if(params.get("action")===ACTION.id){
    hideOpening();
    const id=params.get("scene");
    const index=Math.max(0,ACTION.scenes.findIndex(s=>s.id===id));
    startStory(index);
    return;
  }
  const signalId=params.get("signal");
  if(signalId){
    hideOpening();
    openLook();
    const s=signals.find(x=>x.id===signalId);
    if(s)focusSignal(s);
  }
}

async function init(){
  $("openingDate").textContent=new Intl.DateTimeFormat("en",{month:"long",year:"numeric"}).format(new Date()).toUpperCase();
  bindEvents();
  renderEvidence();
  updateSignature();
  await Promise.allSettled([loadCountries(),refreshSignals()]);
  initialized=true;
  setHomeGlobe();
  $("loading").classList.add("hide");
  routeFromUrl();
}

init();
setInterval(()=>{if(initialized)refreshSignals();},60000);
