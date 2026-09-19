const $ = (id) => document.getElementById(id);
const qs = (sel, root=document) => root.querySelector(sel);
const qsa = (sel, root=document) => [...root.querySelectorAll(sel)];
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson";
const EONET = "https://eonet.gsfc.nasa.gov/api/v3/events/geojson?status=open&limit=120";
const GDACS = "https://gdacs.org/xml/rss_7d.xml";

const sourceMeta = {
  "USGS": {
    freshness: "LIVE",
    cadence: "Updated about every minute",
    url: "https://earthquake.usgs.gov/earthquakes/feed/",
    scope: "Rolling public earthquake feed. Magnitude is not a measure of human impact."
  },
  "NASA EONET": {
    freshness: "NEAR-REAL-TIME",
    cadence: "Curated open-event feed",
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
      kicker: "01 · Signal",
      type: "headline",
      title: "Something changed in Nepal.",
      copy: "Flash floods struck northern Nepal on 26 August 2026, damaging homes, roads and bridges and isolating communities.",
      source: "IFRC · 27 Aug 2026",
      camera: {lat: 24, lng: 78, altitude: 1.95},
      duration: 5200
    },
    {
      id: "impact",
      kicker: "02 · Human impact",
      type: "metric",
      value: "~93,000",
      tone: "attention",
      label: "people may have been affected",
      copy: "This was an early IFRC estimate while assessments were still continuing — not a final affected-population count.",
      source: "IFRC Emergency Appeal · 27 Aug 2026",
      camera: {lat: 28.1, lng: 85.3, altitude: 1.35},
      duration: 5600
    },
    {
      id: "verify",
      kicker: "03 · Verify",
      type: "headline",
      title: "A verified humanitarian response began.",
      copy: "IFRC launched a formal Emergency Appeal alongside Nepal Red Cross Society operations on the ground.",
      source: "Primary source · IFRC",
      camera: {lat: 28.1, lng: 85.3, altitude: 1.18},
      duration: 5100
    },
    {
      id: "response",
      kicker: "04 · Response",
      type: "metric",
      value: "CHF 25M",
      tone: "attention",
      label: "Emergency Appeal",
      copy: "The response includes shelter, health, clean water, sanitation, cash assistance and longer-term recovery.",
      source: "IFRC · Nepal Red Cross Society",
      camera: {lat: 28.2, lng: 84.4, altitude: 1.28},
      duration: 5600
    },
    {
      id: "outcome",
      kicker: "05 · Evidence of response",
      type: "metric",
      value: "~2,000",
      tone: "outcome",
      label: "people with safe drinking water restored in Nuwakot",
      copy: "IFRC reported this on 8 September. This is evidence that the response reached people — not proof that any one donation caused the outcome.",
      source: "IFRC update · 8 Sep 2026",
      camera: {lat: 28.05, lng: 85.15, altitude: 1.08},
      duration: 6500
    },
    {
      id: "clinic",
      kicker: "06 · Capacity",
      type: "metric",
      value: "100/day",
      tone: "outcome",
      label: "mobile primary clinic capacity",
      copy: "A concrete piece of response capacity, reported by IFRC on 8 September.",
      source: "IFRC update · 8 Sep 2026",
      camera: {lat: 28.05, lng: 85.15, altitude: 1.06},
      duration: 5200
    },
    {
      id: "you",
      kicker: "07 · You",
      type: "cta",
      title: "The loop is still open.",
      copy: "You can help through the verified response, inspect every important claim, or follow this operation as newer outcome evidence appears.",
      source: "COMMONS keeps historical claims dated instead of silently rewriting them.",
      camera: {lat: 27.8, lng: 84.8, altitude: 1.26},
      duration: 12000
    }
  ]
};

const globeEl = $("globe");
let signals = [];
let sourceStates = [];
let storyIndex = 0;
let storyTimer = null;
let storyPlaying = false;
let currentSignal = null;
let currentSceneStartedAt = 0;
let progressRAF = null;

const world = Globe()(globeEl)
  .backgroundColor("rgba(0,0,0,0)")
  .globeImageUrl("https://unpkg.com/three-globe@2.45.2/example/img/earth-night.jpg")
  .backgroundImageUrl("https://unpkg.com/three-globe@2.45.2/example/img/night-sky.png")
  .showAtmosphere(true)
  .atmosphereColor("#7f9383")
  .atmosphereAltitude(.12)
  .pointLat(d => d.lat)
  .pointLng(d => d.lon)
  .pointColor(d => d.action ? "#d9bb7a" : sourceColor(d.source))
  .pointAltitude(d => d.action ? .055 : .025)
  .pointRadius(d => d.action ? .28 : Math.max(.08, Math.min(.22, .07 + (Number(d.magnitude)||1) * .02)))
  .pointLabel(() => "")
  .ringsData([])
  .ringLat(d => d.lat)
  .ringLng(d => d.lon)
  .ringColor(d => () => d.action ? "rgba(217,187,122,.68)" : "rgba(200,205,199,.28)")
  .ringMaxRadius(d => d.action ? 4.6 : 2.4)
  .ringPropagationSpeed(d => d.action ? .72 : .46)
  .ringRepeatPeriod(d => d.action ? 2400 : 3400)
  .onPointClick(d => d.action ? startActionStory() : focusSignal(d));

world.controls().autoRotate = !reduceMotion;
world.controls().autoRotateSpeed = .055;
world.controls().enablePan = false;
world.controls().minDistance = 135;
world.controls().maxDistance = 520;
world.pointOfView({lat: 15, lng: 22, altitude: 2.15}, 0);

function resize(){
  world.width(innerWidth).height(innerHeight);
}
window.addEventListener("resize", resize);
resize();

function sourceColor(source){
  return ({
    "USGS":"#9eb8c9",
    "NASA EONET":"#9fd59d",
    "GDACS":"#d9bb7a"
  })[source] || "#c7c9c1";
}

function iso(v){
  if(!v) return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

function age(v){
  if(!v) return "time unknown";
  const m = Math.max(0, Math.round((Date.now()-new Date(v))/60000));
  if(m < 60) return m + "m ago";
  const h = Math.round(m/60);
  if(h < 48) return h + "h ago";
  return Math.round(h/24) + "d ago";
}

function attentionReasons(s){
  const r = [];
  if(s.source === "USGS" && Number(s.magnitude) >= 6) r.push("USGS magnitude ≥ 6.0");
  else if(s.source === "USGS" && Number(s.magnitude) >= 5) r.push("USGS magnitude ≥ 5.0");
  if(s.source === "GDACS" && /red/i.test(s.severity || "")) r.push("GDACS red alert");
  else if(s.source === "GDACS" && /orange/i.test(s.severity || "")) r.push("GDACS orange alert");
  return r;
}

async function fetchUSGS(){
  const r = await fetch(USGS,{cache:"no-store"});
  if(!r.ok) throw new Error("USGS " + r.status);
  const j = await r.json();
  return j.features.map(f => ({
    id:"usgs:"+f.id,
    source:"USGS",
    title:f.properties.title || "Earthquake",
    lat:f.geometry.coordinates[1],
    lon:f.geometry.coordinates[0],
    time:iso(f.properties.updated || f.properties.time),
    magnitude:f.properties.mag,
    severity:f.properties.alert || null,
    url:f.properties.url || null
  }));
}

async function fetchEONET(){
  const r = await fetch(EONET,{cache:"no-store"});
  if(!r.ok) throw new Error("NASA " + r.status);
  const j = await r.json();
  return j.features.map(f => {
    const p=f.properties||{}, g=f.geometry||{}, c=g.coordinates||[];
    if(g.type!=="Point" || c.length<2) return null;
    return {
      id:"eonet:"+(p.id||f.id),
      source:"NASA EONET",
      title:p.title || "Natural event",
      lat:c[1], lon:c[0],
      time:iso(p.date),
      magnitude:p.magnitudeValue ?? null,
      severity:null,
      url:p.sources?.[0]?.url || null
    };
  }).filter(Boolean);
}

async function fetchGDACS(){
  const r = await fetch(GDACS,{cache:"no-store"});
  if(!r.ok) throw new Error("GDACS " + r.status);
  const txt = await r.text();
  const doc = new DOMParser().parseFromString(txt,"application/xml");
  return [...doc.querySelectorAll("item")].map((it,i) => {
    const local = name => [...it.getElementsByTagName("*")].find(n => n.localName?.toLowerCase()===name.toLowerCase())?.textContent?.trim() || null;
    const point = local("point");
    if(!point) return null;
    const p = point.replace(","," ").split(/\s+/).map(Number);
    if(p.length<2 || !Number.isFinite(p[0]) || !Number.isFinite(p[1])) return null;
    return {
      id:"gdacs:"+(local("guid")||i),
      source:"GDACS",
      title:local("title") || "Disaster alert",
      lat:p[0], lon:p[1],
      time:iso(local("pubDate") || Date.now()),
      magnitude:null,
      severity:local("alertlevel"),
      url:local("link")
    };
  }).filter(Boolean);
}

function priority(s){
  let p = 0;
  const reasons = attentionReasons(s);
  p += reasons.length * 8;
  if(s.source==="USGS" && Number.isFinite(Number(s.magnitude))) p += Number(s.magnitude);
  if(/red/i.test(s.severity||"")) p += 7;
  else if(/orange/i.test(s.severity||"")) p += 4;
  if(s.time) p += Math.max(0, 5 - ((Date.now()-new Date(s.time))/864e5));
  return p;
}

async function refreshSignals(){
  $("sourceHealthText").textContent = "Checking public Earth feeds…";
  $("sourceHealth").classList.remove("online");

  const results = await Promise.allSettled([fetchUSGS(),fetchEONET(),fetchGDACS()]);
  const entries = [["USGS",results[0]],["NASA EONET",results[1]],["GDACS",results[2]]];
  signals = [];
  sourceStates = [];

  entries.forEach(([name,res]) => {
    if(res.status==="fulfilled"){
      const enriched = res.value.map(s => ({...s,reasons:attentionReasons(s)}));
      signals.push(...enriched);
      sourceStates.push({name,ok:true,count:enriched.length});
    } else {
      sourceStates.push({name,ok:false,count:0});
    }
  });

  const healthy = sourceStates.filter(s=>s.ok).length;
  $("sourceHealthText").textContent = healthy + "/3 public sources responding";
  if(healthy) $("sourceHealth").classList.add("online");

  renderGlobe();
  renderSignals();
  setTimeout(() => $("loading").classList.add("hide"), 500);
}

function renderGlobe(){
  const actionPoint = {
    id:ACTION.id, action:true, lat:ACTION.lat, lon:ACTION.lon,
    source:"COMMONS ACTION", title:ACTION.title
  };
  world.pointsData([...signals.slice(0,160),actionPoint]);
  const surfaced = [...signals]
    .sort((a,b)=>priority(b)-priority(a))
    .filter(s=>priority(s)>=5)
    .slice(0,18);
  world.ringsData([...surfaced, actionPoint]);
}

function renderSignals(){
  const top = [...signals].sort((a,b)=>priority(b)-priority(a)).slice(0,3);
  $("signalList").innerHTML = top.map(s => `
    <button class="signal" data-id="${escapeHtml(s.id)}">
      <div class="signal-source">${escapeHtml(s.source)}</div>
      <div class="signal-title">${escapeHtml(s.title)}</div>
      <div class="signal-time">${escapeHtml(age(s.time))}</div>
    </button>
  `).join("");
  qsa(".signal", $("signalList")).forEach(el => {
    el.addEventListener("click", () => {
      const s = signals.find(x=>x.id===el.dataset.id);
      if(s) focusSignal(s);
    });
  });
}

function focusSignal(s){
  currentSignal = s;
  stopStory(false);
  $("landing").classList.add("hidden");
  $("explorePanel").classList.add("open");
  world.controls().autoRotate = false;
  world.pointOfView({lat:s.lat,lng:s.lon,altitude:1.35}, reduceMotion?0:900);

  const detail = $("signalFocus");
  const why = s.reasons?.length ? s.reasons.join(" · ") : "Current source signal";
  detail.innerHTML = `
    <div class="explore-head">
      <span>${escapeHtml(s.source)} · ${escapeHtml(sourceMeta[s.source]?.freshness || "PUBLIC")}</span>
      <button class="icon-button" id="signalClose" aria-label="Close signal">×</button>
    </div>
    <div style="padding:2px 2px 4px">
      <div style="font-size:24px;line-height:1.08;letter-spacing:-.035em;font-weight:520">${escapeHtml(s.title)}</div>
      <div style="margin-top:8px;color:#7f867f;font-size:10px;line-height:1.5">${escapeHtml(why)} · ${escapeHtml(age(s.time))}</div>
      <div style="display:flex;gap:8px;margin-top:14px;flex-wrap:wrap">
        <button class="cta dark" id="signalSource">Open source ↗</button>
        <button class="cta dark" id="signalShare">Share provenance</button>
      </div>
    </div>
  `;
  $("signalClose").onclick = exitExplore;
  $("signalSource").onclick = () => s.url && window.open(s.url,"_blank","noopener");
  $("signalShare").onclick = () => shareSignal(s);
}

function exitExplore(){
  $("explorePanel").classList.remove("open");
  $("signalFocus").innerHTML = "";
  $("landing").classList.remove("hidden");
  world.controls().autoRotate = !reduceMotion;
  world.pointOfView({lat:15,lng:22,altitude:2.15},reduceMotion?0:850);
  const u = new URL(location.href);
  u.searchParams.delete("signal");
  history.replaceState(null,"",u);
}

function startActionStory(scene=0){
  closeDrawer();
  $("explorePanel").classList.remove("open");
  $("landing").classList.add("hidden");
  $("story").classList.add("active");
  world.controls().autoRotate = false;
  storyPlaying = !reduceMotion;
  storyIndex = clamp(scene,0,ACTION.scenes.length-1);

  const u = new URL(location.href);
  u.searchParams.delete("signal");
  u.searchParams.set("action",ACTION.id);
  u.searchParams.set("scene",ACTION.scenes[storyIndex].id);
  history.replaceState(null,"",u);

  renderProgress();
  renderScene(storyIndex);
}

function stopStory(returnHome=true){
  clearTimeout(storyTimer);
  cancelAnimationFrame(progressRAF);
  storyTimer = null;
  progressRAF = null;
  storyPlaying = false;
  $("story").classList.remove("active");
  if(returnHome){
    $("landing").classList.remove("hidden");
    world.controls().autoRotate = !reduceMotion;
    world.pointOfView({lat:15,lng:22,altitude:2.15},reduceMotion?0:900);
    const u = new URL(location.href);
    u.searchParams.delete("action");
    u.searchParams.delete("scene");
    history.replaceState(null,"",u);
  }
}

function renderScene(index){
  clearTimeout(storyTimer);
  cancelAnimationFrame(progressRAF);
  storyIndex = clamp(index,0,ACTION.scenes.length-1);
  const scene = ACTION.scenes[storyIndex];

  qsa(".progress-segment").forEach((el,i)=>{
    el.classList.toggle("past",i<storyIndex);
    el.classList.toggle("current",i===storyIndex);
  });

  $("progressCurrent").textContent = String(storyIndex+1).padStart(2,"0");
  $("progressTotal").textContent = String(ACTION.scenes.length).padStart(2,"0");

  $("scene").classList.remove("enter");
  void $("scene").offsetWidth;
  $("scene").innerHTML = sceneMarkup(scene);
  $("scene").classList.add("enter");

  world.pointOfView(scene.camera, reduceMotion?0:1250);

  const u = new URL(location.href);
  u.searchParams.set("action",ACTION.id);
  u.searchParams.set("scene",scene.id);
  history.replaceState(null,"",u);

  bindSceneActions();

  if(storyPlaying && !reduceMotion){
    currentSceneStartedAt = performance.now();
    animateProgress(scene.duration);
    storyTimer = setTimeout(() => {
      if(storyIndex < ACTION.scenes.length-1) renderScene(storyIndex+1);
      else {
        storyPlaying = false;
        renderProgress();
      }
    }, scene.duration);
  } else {
    renderProgress();
  }
}

function sceneMarkup(scene){
  if(scene.type==="metric"){
    return `
      <div class="scene-kicker">${escapeHtml(scene.kicker)}</div>
      <div class="scene-value ${escapeHtml(scene.tone||"")}">${escapeHtml(scene.value)}</div>
      <div class="scene-label">${escapeHtml(scene.label)}</div>
      <div class="scene-copy">${escapeHtml(scene.copy)}</div>
      <div class="scene-source"><i></i><span>${escapeHtml(scene.source)}</span></div>
      ${storySceneActions(scene)}
    `;
  }
  const title = scene.title
    .replace("Something changed","<span class='attention'>Something changed</span>")
    .replace("verified humanitarian response","<span class='soft'>verified humanitarian response</span>")
    .replace("The loop is still open.","The loop is <span class='accent'>still open.</span>");

  return `
    <div class="scene-kicker">${escapeHtml(scene.kicker)}</div>
    <h2 class="scene-title">${title}</h2>
    <div class="scene-copy">${escapeHtml(scene.copy)}</div>
    <div class="scene-source"><i></i><span>${escapeHtml(scene.source)}</span></div>
    ${storySceneActions(scene)}
  `;
}

function storySceneActions(scene){
  if(scene.id==="you"){
    return `
      <div class="scene-actions">
        <button class="cta light" data-action="help">Help through IFRC ↗</button>
        <button class="cta dark" data-action="verify">Verify</button>
        <button class="cta dark" data-action="follow">Follow</button>
        <button class="cta dark" data-action="share">Share</button>
      </div>
    `;
  }
  if(scene.id==="verify"){
    return `
      <div class="scene-actions">
        <button class="cta dark" data-action="verify">Inspect primary source ↗</button>
        <button class="cta dark" data-action="details">Evidence notes</button>
      </div>
    `;
  }
  if(scene.id==="outcome"){
    return `
      <div class="scene-actions">
        <button class="cta dark" data-action="outcome">Read outcome update ↗</button>
      </div>
    `;
  }
  return "";
}

function bindSceneActions(){
  qsa("[data-action]", $("scene")).forEach(btn => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      if(action==="help") window.open(ACTION.donate,"_blank","noopener");
      if(action==="verify") window.open(ACTION.appeal,"_blank","noopener");
      if(action==="outcome") window.open(ACTION.outcome,"_blank","noopener");
      if(action==="details" || action==="follow") openDrawer();
      if(action==="share") openSharePreview();
    });
  });
}

function animateProgress(duration){
  const fill = qs(".progress-segment.current span");
  if(!fill) return;
  fill.style.width = "0%";
  const tick = now => {
    if(!storyPlaying || !qs(".progress-segment.current")) return;
    const p = Math.min(1,(now-currentSceneStartedAt)/duration);
    fill.style.width = (p*100).toFixed(2)+"%";
    if(p<1) progressRAF=requestAnimationFrame(tick);
  };
  progressRAF=requestAnimationFrame(tick);
}

function renderProgress(){
  qsa(".progress-segment").forEach((el,i)=>{
    const fill=qs("span",el);
    if(fill) fill.style.width = i<=storyIndex ? "100%" : "0%";
  });
  $("playToggle").textContent = storyPlaying ? "Ⅱ" : "▶";
  $("playToggle").setAttribute("aria-label",storyPlaying?"Pause story":"Play story");
}

function buildProgress(){
  $("progressTrack").innerHTML = ACTION.scenes.map((s,i)=>`
    <button class="progress-segment" data-index="${i}" aria-label="Go to ${escapeHtml(s.kicker)}"><span></span></button>
  `).join("");
  qsa(".progress-segment").forEach(el => el.onclick = () => {
    storyPlaying = false;
    renderScene(Number(el.dataset.index));
  });
}

function nextScene(){
  storyPlaying = false;
  renderScene(Math.min(ACTION.scenes.length-1,storyIndex+1));
}
function prevScene(){
  storyPlaying = false;
  renderScene(Math.max(0,storyIndex-1));
}
function toggleStory(){
  if(storyPlaying){
    storyPlaying=false;
    clearTimeout(storyTimer);
    cancelAnimationFrame(progressRAF);
    renderProgress();
  } else {
    storyPlaying=true;
    renderScene(storyIndex);
  }
}

function openDrawer(){
  renderDrawer();
  $("drawer").classList.add("open");
  $("drawer").setAttribute("aria-hidden","false");
}
function closeDrawer(){
  $("drawer").classList.remove("open");
  $("drawer").setAttribute("aria-hidden","true");
}

function renderDrawer(){
  const liveSources = sourceStates.map(s => {
    const m=sourceMeta[s.name];
    return `
      <a class="source-link" href="${m.url}" target="_blank" rel="noopener">
        <small>${escapeHtml(s.name)} · ${escapeHtml(m.freshness)} · ${s.ok?"responding":"unavailable"}</small>
        <span>${escapeHtml(m.scope)}</span>
      </a>
    `;
  }).join("");

  $("drawerBody").innerHTML = `
    <p class="trust-intro">Every important claim should have somewhere you can go to inspect it.</p>

    <section class="trust-section">
      <h3>Action 001 · Nepal</h3>
      <div class="source-list">
        <a class="source-link" href="${ACTION.appeal}" target="_blank" rel="noopener">
          <small>Primary evidence · IFRC · 27 Aug 2026</small>
          <span>Emergency Appeal, early affected-population estimate and response priorities.</span>
        </a>
        <a class="source-link" href="${ACTION.outcome}" target="_blank" rel="noopener">
          <small>Outcome evidence · IFRC · 8 Sep 2026</small>
          <span>Safe-water restoration for around 2,000 people and mobile clinic capacity.</span>
        </a>
        <a class="source-link" href="${ACTION.directory}" target="_blank" rel="noopener">
          <small>Responder identity</small>
          <span>Nepal Red Cross Society in the IFRC National Society directory.</span>
        </a>
      </div>
    </section>

    <section class="trust-section">
      <h3>What we are not claiming</h3>
      <div class="not-claiming">
        <div><b>—</b><span>~93,000 is not presented as a final affected-population count.</span></div>
        <div><b>—</b><span>We do not claim every affected person has been reached.</span></div>
        <div><b>—</b><span>We do not show a funding percentage without a current authoritative source.</span></div>
        <div><b>—</b><span>We do not imply that a specific user's donation caused the displayed outcomes.</span></div>
        <div><b>—</b><span>The loop remains open; newer dated evidence should update the story.</span></div>
      </div>
    </section>

    <section class="trust-section">
      <h3>Live Earth layer</h3>
      <div class="source-list">${liveSources || "<p>Source status will appear after the feeds respond.</p>"}</div>
    </section>

    <section class="trust-section">
      <h3>Update contract</h3>
      <p>Historical facts retain their original date. Newer outcome evidence is added only when it is attributable to the operation, dated, specific enough to interpret, and supported by a primary or first-party source.</p>
    </section>
  `;
}

function openExplore(){
  stopStory(false);
  closeDrawer();
  $("landing").classList.add("hidden");
  $("explorePanel").classList.add("open");
  $("signalFocus").innerHTML = "";
  world.controls().autoRotate = !reduceMotion;
  world.pointOfView({lat:12,lng:15,altitude:2.0},reduceMotion?0:800);
}

function openSharePreview(){
  drawShareCard();
  $("sharePreview").classList.add("open");
}
function closeSharePreview(){
  $("sharePreview").classList.remove("open");
}

function drawShareCard(){
  const canvas = $("shareCanvas");
  const scale=2;
  canvas.width=1600*scale;
  canvas.height=900*scale;
  const ctx=canvas.getContext("2d");
  ctx.scale(scale,scale);

  const g=ctx.createLinearGradient(0,0,1600,900);
  g.addColorStop(0,"#050605");
  g.addColorStop(.62,"#0b0d0b");
  g.addColorStop(1,"#12130f");
  ctx.fillStyle=g;ctx.fillRect(0,0,1600,900);

  const earth=ctx.createRadialGradient(1250,390,40,1250,390,420);
  earth.addColorStop(0,"rgba(159,213,157,.18)");
  earth.addColorStop(.48,"rgba(90,110,96,.11)");
  earth.addColorStop(.73,"rgba(217,187,122,.06)");
  earth.addColorStop(1,"rgba(0,0,0,0)");
  ctx.fillStyle=earth;ctx.beginPath();ctx.arc(1250,390,420,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle="rgba(242,241,235,.12)";ctx.lineWidth=1.5;
  ctx.beginPath();ctx.arc(1250,390,260,0,Math.PI*2);ctx.stroke();
  ctx.strokeStyle="rgba(217,187,122,.44)";ctx.lineWidth=3;
  ctx.beginPath();ctx.arc(1325,325,10,0,Math.PI*2);ctx.stroke();

  ctx.fillStyle="#f2f1eb";ctx.font="700 28px Helvetica Neue, Arial";
  ctx.fillText("COMMONS / WORLD PULSE",90,86);

  ctx.fillStyle="#d9bb7a";ctx.font="600 22px Helvetica Neue, Arial";
  ctx.fillText("NEPAL · FLASH FLOODS 2026",90,170);

  ctx.fillStyle="#f2f1eb";ctx.font="600 118px Helvetica Neue, Arial";
  ctx.fillText("~2,000",86,340);

  ctx.fillStyle="#c7c9c1";ctx.font="400 43px Helvetica Neue, Arial";
  ctx.fillText("people with safe drinking water restored",90,405);

  ctx.fillStyle="#8d948d";ctx.font="400 26px Helvetica Neue, Arial";
  wrapText(ctx,"A verified humanitarian response, with the evidence chain kept visible.",90,500,720,40);

  ctx.fillStyle="#9fd59d";ctx.font="600 24px Helvetica Neue, Arial";
  ctx.fillText("SIGNAL  →  RESPONSE  →  OUTCOME",90,690);

  ctx.fillStyle="#767d76";ctx.font="400 21px Helvetica Neue, Arial";
  ctx.fillText("Evidence update · 8 Sep 2026 · Loop status: OPEN",90,750);
  ctx.fillText("mikelninh.github.io/COMMONS",90,806);
}

function wrapText(ctx,text,x,y,maxWidth,lineHeight){
  const words=text.split(" ");
  let line="";
  words.forEach((word,i)=>{
    const test=line+word+" ";
    if(ctx.measureText(test).width>maxWidth && i>0){
      ctx.fillText(line,x,y);
      line=word+" ";
      y+=lineHeight;
    } else line=test;
  });
  ctx.fillText(line,x,y);
}

async function shareAction(){
  const text = [
    "COMMONS / WORLD PULSE",
    "Nepal · Flash Floods 2026",
    "",
    "~93,000 people may have been affected · IFRC estimate, 27 Aug 2026",
    "CHF 25M Emergency Appeal · IFRC + Nepal Red Cross Society",
    "By 8 Sep: safe drinking water restored for ~2,000 people",
    "Mobile clinic capacity: 100 patients/day",
    "",
    "Signal → verified response → outcome evidence",
    actionUrl()
  ].join("\n");

  const shareData={title:"WORLD PULSE — Nepal",text,url:actionUrl()};
  try{
    if(navigator.share) await navigator.share(shareData);
    else{
      await navigator.clipboard.writeText(text);
      toast("Share story copied with provenance");
    }
  }catch(e){}
}

async function shareCardImage(){
  const canvas=$("shareCanvas");
  const blob=await new Promise(resolve=>canvas.toBlob(resolve,"image/png",.94));
  if(!blob) return;
  const file=new File([blob],"world-pulse-nepal.png",{type:"image/png"});
  try{
    if(navigator.canShare?.({files:[file]}) && navigator.share){
      await navigator.share({files:[file],title:"WORLD PULSE — Nepal",text:"Signal → response → outcome"});
    } else {
      const a=document.createElement("a");
      a.href=URL.createObjectURL(blob);
      a.download="world-pulse-nepal.png";
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
    s.reasons?.length ? "Surfaced because: "+s.reasons.join(" · ") : "Current source signal",
    s.url ? "Primary source: "+s.url : "",
    "",
    "COMMONS / WORLD PULSE"
  ].filter(Boolean).join("\n");
  const u=new URL(location.href);
  u.searchParams.set("signal",s.id);
  try{
    if(navigator.share) await navigator.share({title:"WORLD PULSE",text,url:u.toString()});
    else{
      await navigator.clipboard.writeText(text+"\n"+u);
      toast("Signal copied with provenance");
    }
  }catch(e){}
}

function actionUrl(){
  const u=new URL(location.href);
  u.searchParams.delete("signal");
  u.searchParams.set("action",ACTION.id);
  u.searchParams.set("scene","signal");
  return u.toString();
}

function toast(message){
  $("toast").textContent=message;
  $("toast").classList.add("show");
  clearTimeout(toast._t);
  toast._t=setTimeout(()=>$("toast").classList.remove("show"),2200);
}

function escapeHtml(v){
  return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));
}
function clamp(v,min,max){return Math.max(min,Math.min(max,v))}

function initEvents(){
  $("watchBtn").onclick=()=>startActionStory(0);
  $("actionPeek").onclick=()=>startActionStory(0);
  $("exploreBtn").onclick=openExplore;
  $("detailsBtn").onclick=openDrawer;
  $("drawerClose").onclick=closeDrawer;
  $("storyClose").onclick=()=>stopStory(true);
  $("storyDetails").onclick=openDrawer;
  $("storyShare").onclick=openSharePreview;
  $("prevScene").onclick=prevScene;
  $("nextScene").onclick=nextScene;
  $("playToggle").onclick=toggleStory;
  $("shareClose").onclick=closeSharePreview;
  $("shareLinkBtn").onclick=shareAction;
  $("shareImageBtn").onclick=shareCardImage;
  $("homeShareBtn").onclick=openSharePreview;

  document.addEventListener("keydown",e=>{
    if(e.key==="Escape"){
      if($("sharePreview").classList.contains("open")) return closeSharePreview();
      if($("drawer").classList.contains("open")) return closeDrawer();
      if($("story").classList.contains("active")) return stopStory(true);
      if($("explorePanel").classList.contains("open")) return exitExplore();
    }
    if(!$("story").classList.contains("active")) return;
    if(e.key==="ArrowRight") nextScene();
    if(e.key==="ArrowLeft") prevScene();
    if(e.key===" "){e.preventDefault();toggleStory();}
  });

  $("sharePreview").addEventListener("click",e=>{
    if(e.target===$("sharePreview")) closeSharePreview();
  });
}

function routeFromUrl(){
  const params=new URLSearchParams(location.search);
  const action=params.get("action");
  const sceneId=params.get("scene");
  const signalId=params.get("signal");

  if(action===ACTION.id){
    const i=Math.max(0,ACTION.scenes.findIndex(s=>s.id===sceneId));
    setTimeout(()=>startActionStory(i),650);
    return;
  }
  if(signalId){
    const findAndFocus=()=>{
      const s=signals.find(x=>x.id===signalId);
      if(s) focusSignal(s);
      else setTimeout(findAndFocus,400);
    };
    findAndFocus();
  }
}

buildProgress();
initEvents();
renderDrawer();
refreshSignals().finally(routeFromUrl);
setInterval(refreshSignals,60000);
