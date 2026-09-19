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

function renderStoryLibrary(){
  $("storyCards").innerHTML=STORIES.map(story=>`
    <button class="story-card ${story.id===activeStory.id?"active":""}" data-story-id="${escapeHtml(story.id)}" style="--card-accent:${escapeHtml(story.colors.memory||story.colors.attention)}">
      <span class="story-card-number">${String(story.order).padStart(2,"0")}</span>
      <span class="story-card-body">
        <span class="story-card-country">${escapeHtml(story.country)} · ${escapeHtml(story.statusLabel)}</span>
        <span class="story-card-title">${escapeHtml(story.title)}</span>
        <span class="story-card-subtitle">${escapeHtml(story.subtitle)}</span>
      </span>
      <span class="story-card-status">${escapeHtml(story.updatedAt)}<span class="story-card-arrow">→</span></span>
    </button>
  `).join("");

  qsa(".story-card",$("storyCards")).forEach(card=>{
    card.onclick=()=>enterStory(card.dataset.storyId,0);
  });
}

function updateStoryChrome(){
  const root=document.documentElement;
  root.style.setProperty("--amber",activeStory.colors.attention);
  root.style.setProperty("--green",activeStory.colors.outcome);

  $("featuredMeta").textContent=activeStory.country+" · "+activeStory.statusLabel;
  $("featuredTitle").textContent=activeStory.title+" — "+activeStory.subtitle;
  $("currentStory").setAttribute("aria-label","Enter "+activeStory.country+" — "+activeStory.title);

  $("storyIndex").innerHTML=`<b>${escapeHtml(activeStory.country.toUpperCase())}</b> · ${escapeHtml(activeStory.title.toUpperCase())} · ${escapeHtml(activeStory.status)}`;
  $("story").dataset.status=activeStory.status.includes("ELIMINATION")?"elimination":"open";

  $("timeLabels").innerHTML=activeStory.timeLabels.map(label=>`<span>${escapeHtml(label)}</span>`).join("");
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

function sceneMarkup(scene){
  const body=scene.value
    ? `<div class="scene-number ${escapeHtml(scene.tone||"")}">${escapeHtml(scene.value)}</div>
       <div class="scene-label">${escapeHtml(scene.label)}</div>`
    : `<h2 class="scene-headline">${scene.headline}</h2>`;

  const following=nextStory();
  const actions=scene.actions?`
    <div class="scene-actions">
      <button class="word-button" data-action="primary">${escapeHtml(activeStory.primaryAction.label)}</button>
      <button class="word-button muted" data-action="belief">Why we believe this</button>
      <button class="word-button muted" data-action="pass">Pass this on</button>
      <button class="word-button muted" data-action="next">Next: ${escapeHtml(following.country)} →</button>
    </div>`:"";

  return `
    <div class="scene-kicker">${escapeHtml(scene.kicker)}</div>
    ${body}
    <div class="scene-copy">${escapeHtml(scene.copy)}</div>
    <div class="scene-source">${escapeHtml(scene.source)}</div>
    ${actions}
  `;
}

function bindScrollSceneActions(){
  qsa("[data-action]",$("scrollNarrative")).forEach(btn=>{
    btn.onclick=()=>{
      if(btn.dataset.action==="primary")window.open(activeStory.primaryAction.url,"_blank","noopener");
      if(btn.dataset.action==="belief")openEvidence();
      if(btn.dataset.action==="pass")openShare();
      if(btn.dataset.action==="next"){
        const following=nextStory();
        enterStory(following.id,0);
      }
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
    u.searchParams.set("action",activeStory.id);
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

  if(returnHome){
    $("home").classList.remove("hidden");
    const u=new URL(location.href);
    u.searchParams.delete("action");
    u.searchParams.delete("scene");
    history.replaceState(null,"",u);
    setHomeGlobe();
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
        <a href="${activeStory.appeal}" target="_blank" rel="noopener">IFRC Emergency Appeal — early affected-population estimate, appeal amount and named response priorities.</a>
      </div>
      <div class="evidence-row">
        <div class="evidence-date">08 Sep<br>2026</div>
        <a href="${activeStory.outcome}" target="_blank" rel="noopener">IFRC response update — safe drinking water restored for around 2,000 people and mobile primary clinic capacity.</a>
      </div>
      <div class="evidence-row">
        <div class="evidence-date">Responder</div>
        <a href="${activeStory.directory}" target="_blank" rel="noopener">Nepal Red Cross Society — IFRC National Society directory.</a>
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
      <h3>About the geographic descent</h3>
      <p>The Nepal country outline is projected from the public World Atlas geometry used by the globe. The internal contour field is a stylized visual treatment for depth and is not elevation, flood extent, damage mapping, or a factual topographic model. The response thread is also semantic rather than a literal route.</p>
    </section>

    <section class="evidence-section">
      <h3>Memory of Earth</h3>
      <p>The memory mark represents only this documented Nepal response story. It is not a score, rank, completion badge, or claim that the wider humanitarian operation is resolved.</p>
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
  u.searchParams.set("action",activeStory.id);
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
  $("soundBtn").onclick=toggleSound;
  $("storyPass").onclick=openShare;
  $("shareClose").onclick=closeShare;
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
  if(params.get("action")===activeStory.id){
    hideOpening();
    const id=params.get("scene");
    const index=Math.max(0,activeStory.scenes.findIndex(s=>s.id===id));
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
