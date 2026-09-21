const $=id=>document.getElementById(id);

const BERLIN={lon:13.405,lat:52.52};
const BBOX={west:13.08,south:52.34,east:13.78,north:52.70};
const CENTER=[BERLIN.lon,BERLIN.lat];

const SOURCES={
  transit:{name:"VBB realtime",url:"https://v6.vbb.transport.rest",note:"Current public-transport vehicle positions from the VBB transport.rest interface."},
  air:{name:"Berlin Luftgütemessnetz",url:"https://luftdaten.berlin.de",note:"Measured Berlin air-quality stations. Open-Meteo CAMS is used only as fallback/context."},
  water:{name:"Wasserportal Berlin",url:"https://wasserportal.berlin.de",note:"Official Spree/Havel measurements. GloFAS is used if the browser cannot read the official endpoint."},
  traffic:{name:"VIZ Berlin",url:"https://viz.berlin.de",note:"Berlin traffic, construction, closures and disruptions."},
  population:{name:"Geoportal Berlin",url:"https://gdi.berlin.de/services/wfs/ua_einwohnerdichte_2024",note:"Official Berlin population-density WFS."},
  health:{name:"Geoportal Berlin",url:"https://gdi.berlin.de/services/wfs/krankenhaeuser",note:"Official hospital geodata."},
  fire:{name:"Berliner Feuerwehr / Geoportal",url:"https://gdi.berlin.de/services/wfs/feuerwehr",note:"Fire/rescue stations and operational areas."},
  green:{name:"Geoportal Berlin",url:"https://gdi.berlin.de/services/wfs/gruenanlagen",note:"Official public green-space layer."},
  trees:{name:"Geoportal Berlin",url:"https://gdi.berlin.de/services/wfs/baumbestand",note:"Official street-tree and selected park-tree data."},
  solar:{name:"Geoportal Berlin",url:"https://gdi.berlin.de/services/wfs/ua_solaranlagen_st",note:"Official solar-thermal installation context."},
  heat:{name:"Umweltatlas Berlin",url:"https://gdi.berlin.de/services/wfs/ua_klimaanalyse_2022",note:"Berlin climate-analysis / thermal-stress geodata."},
  justice:{name:"Umweltatlas Berlin",url:"https://gdi.berlin.de/services/wfs/ua_umweltgerechtigkeit2023",note:"Integrated environmental-justice layer: noise, air, green supply, heat and social burden."},
  noise:{name:"Umweltatlas Berlin",url:"https://www.berlin.de/umweltatlas/",note:"Strategic noise mapping. Kept source-only until a stable browser-readable feature service is verified."},
  bikes:{name:"Berlin Open Data",url:"https://daten.berlin.de/datensaetze/radzahldaten-in-berlin",note:"Official hourly permanent bike-counter history."},
  accidents:{name:"Berlin Open Data",url:"https://daten.berlin.de/datensaetze?tags=Strassenverkehrsunf%C3%A4lle",note:"Official historical road-traffic accident datasets."}
};

const MODES={
  now:[
    ["movement","Movement"],["air","Air"],["weather","Weather"],["water","Spree"],["traffic","Traffic"]
  ],
  city:[
    ["population","People"],["health","Hospitals"],["fire","Fire / Rescue"],["power","Power"],["green","Green"],["trees","Trees"],["solar","Solar"]
  ],
  pressure:[
    ["heat","Heat"],["justice","Environmental justice"],["air","Air"],["noise","Noise"]
  ],
  memory:[
    ["airhistory","Air history"],["waterhistory","Water history"],["bikes","Bike counts"],["accidents","Crashes"]
  ]
};

const LAYER_COPY={
  movement:["NOW · MOVEMENT","Berlin moves.","Where are public-transport vehicles right now?"],
  air:["NOW · AIR","Berlin breathes.","Measured local stations first; modeled air only fills the gaps."],
  weather:["NOW · WEATHER","The atmosphere above Berlin.","Temperature, apparent heat, rain and humidity through time."],
  water:["NOW · WATER","The Spree carries a memory.","Official water measurements when readable; hydrological model as fallback."],
  traffic:["NOW · TRAFFIC","Where the street network is under pressure.","The official VIZ system is the live authority; COMMONS shows the network and source boundary."],
  population:["CITY · PEOPLE","Where Berlin lives.","Population density is a spatial layer, not a single citywide number."],
  health:["CITY · HEALTH","Where care lives.","Hospitals become part of the city geometry."],
  fire:["CITY · FIRE / RESCUE","Where response begins.","Fire and rescue locations are mapped as operational city infrastructure."],
  power:["CITY · POWER","The electrical skeleton.","Substations and transmission infrastructure from OpenStreetMap."],
  green:["CITY · GREEN","Where the city can breathe.","Public green spaces become a physical cooling and access layer."],
  trees:["CITY · TREES","Berlin’s street canopy.","A sampled view of official tree locations; dense enough to feel the urban canopy."],
  solar:["CITY · SOLAR","Where buildings harvest light.","Official solar-installation context from Berlin’s environmental data."],
  heat:["PRESSURE · HEAT","Where summer presses hardest.","Official climate-analysis polygons make thermal stress spatial."],
  justice:["PRESSURE · ENVIRONMENTAL JUSTICE","Pressure is not evenly distributed.","Berlin’s integrated burden layer keeps heat, air, noise, green supply and social disadvantage visible together."],
  noise:["PRESSURE · NOISE","The city is not equally quiet.","Official strategic noise mapping is linked here; no synthetic noise score is invented."],
  airhistory:["MEMORY · AIR","What did Berlin breathe?","A measured station history is more useful than a generic city average."],
  waterhistory:["MEMORY · WATER","What did the Spree do?","Historical water observations become a city memory."],
  bikes:["MEMORY · CYCLING","How Berlin moved by bike.","Official hourly counting history is the source of record."],
  accidents:["MEMORY · CRASHES","Where movement became harm.","Official accident datasets belong in memory, not as a decorative danger score."]
};

let map=null;
let mapReady=false;
let activeMode="now";
let activeLayer="movement";
let layerToken=0;
const dataCache={};
const officialCache={};

function fmt(v,d=1){const n=Number(v);return Number.isFinite(n)?n.toFixed(d):"—"}
function human(v){const n=Number(v);if(!Number.isFinite(n))return "—";if(Math.abs(n)>=1e6)return (n/1e6).toFixed(1)+"M";if(Math.abs(n)>=1e3)return Math.round(n/1e3)+"k";return n.toFixed(Math.abs(n)<10?1:0)}
function fc(features=[]){return {type:"FeatureCollection",features}}
function point(lon,lat,properties={}){return {type:"Feature",properties,geometry:{type:"Point",coordinates:[Number(lon),Number(lat)]}}}
function setHealth(id,state,label){const el=$(id);if(!el)return;el.textContent=label;el.classList.remove("ready","warn");if(state==="ready")el.classList.add("ready");if(state==="warn")el.classList.add("warn")}
async function fetchTimeout(url,options={},ms=12000){
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),ms);
  try{const response=await fetch(url,{cache:"no-store",signal:controller.signal,...options});if(!response.ok)throw new Error("HTTP "+response.status);return response}
  finally{clearTimeout(timer)}
}
async function json(url,options,ms){return (await fetchTimeout(url,options,ms)).json()}
async function textFetch(url,options,ms){return (await fetchTimeout(url,options,ms)).text()}
function sourceCards(keys){
  return keys.map(key=>{const s=SOURCES[key];if(!s)return "";return '<div class="source-card"><strong>'+s.name+'</strong><span>'+s.note+'</span><span><a href="'+s.url+'" target="_blank" rel="noreferrer">Open source ↗</a></span></div>'}).join("");
}
function resetPanel(){
  $("timeline").classList.add("hidden");$("cards").classList.add("hidden");$("cards").innerHTML="";
  $("insight")?.classList.remove("degraded");
  $("primaryValue").textContent="—";$("primaryCopy").textContent="Connecting…";
  for(const [id,label] of [["statA","—"],["statB","—"],["statC","—"]])$(id).textContent=label;
  $("statACopy").textContent="—";$("statBCopy").textContent="—";$("statCCopy").textContent="—";
  clearVisualLayers();
}
function clearVisualLayers(){
  if(!mapReady)return;
  ["dynamic-heat","transit-points","official-fill","official-line","official-point","power-line","power-point","air-points","water-point"].forEach(id=>setVisible(id,false));
}
function setVisible(id,on){if(mapReady&&map.getLayer(id))map.setLayoutProperty(id,"visibility",on?"visible":"none")}
function dataToSource(id,data){if(mapReady&&map.getSource(id))map.getSource(id).setData(data)}
function fitBerlin(){if(mapReady)map.flyTo({center:CENTER,zoom:10.6,pitch:52,bearing:-16,duration:1300,essential:true})}
function safePaint(layer,prop,value){try{if(mapReady&&map.getLayer(layer))map.setPaintProperty(layer,prop,value)}catch(e){}}

function showFallback(message){
  $("mapFallback").classList.remove("hidden");
  $("mapFallback").querySelector("span").textContent=message||"The Berlin data panels still work. Reload to retry the map renderer.";
  setHealth("mapHealth","warn","MAP · OFFLINE");
}
function initMap(){
  if(!window.maplibregl){showFallback("MapLibre could not load from either CDN. The rest of Berlin Deep City remains readable.");return}
  try{
    map=new window.maplibregl.Map({
      container:"map",style:"https://tiles.openfreemap.org/styles/liberty",
      center:[13.405,52.52],zoom:9.9,pitch:45,bearing:-12,antialias:true,attributionControl:true
    });
    map.on("load",()=>{
      mapReady=true;setHealth("mapHealth","ready","MAP · LIVE");addMapLayers();fitBerlin();
      if(!$("intro").classList.contains("hidden"))renderBerlinOutline();
    });
    map.on("error",e=>{if(!mapReady&&String(e?.error||"").includes("style"))showFallback("The basemap style could not load. Data panels are still available.")});
  }catch(e){showFallback("The map renderer failed to initialize. Data panels are still available.")}
}
function addMapLayers(){
  const sources=["dynamic","transit","official","power","air","water"];
  sources.forEach(id=>map.addSource(id,{type:"geojson",data:fc()}));
  map.addLayer({id:"dynamic-heat",type:"heatmap",source:"dynamic",paint:{
    "heatmap-weight":["coalesce",["get","weight"],.3],"heatmap-intensity":1.15,
    "heatmap-radius":["interpolate",["linear"],["zoom"],8,28,13,70],"heatmap-opacity":.82,
    "heatmap-color":["interpolate",["linear"],["heatmap-density"],0,"rgba(0,0,0,0)",.25,"rgba(90,160,210,.12)",.5,"rgba(100,205,255,.42)",.75,"rgba(184,255,112,.68)",1,"rgba(245,255,238,.9)"]
  }});
  map.addLayer({id:"transit-points",type:"circle",source:"transit",paint:{
    "circle-radius":["interpolate",["linear"],["zoom"],8,2.5,12,4.5],
    "circle-color":["match",["get","mode"],"subway","#63cfff","tram","#ffd36a","bus","#b9ff70","train","#ff786b","#f3f5f1"],
    "circle-opacity":.85,"circle-stroke-width":.8,"circle-stroke-color":"rgba(0,0,0,.55)"
  }});
  map.addLayer({id:"official-fill",type:"fill",source:"official",paint:{"fill-color":"#b9ff70","fill-opacity":.18}});
  map.addLayer({id:"official-line",type:"line",source:"official",paint:{"line-color":"#b9ff70","line-opacity":.72,"line-width":1.4}});
  map.addLayer({id:"official-point",type:"circle",source:"official",paint:{"circle-radius":4.5,"circle-color":"#eef4e8","circle-opacity":.9,"circle-stroke-width":1,"circle-stroke-color":"rgba(0,0,0,.5)"}});
  map.addLayer({id:"power-line",type:"line",source:"power",paint:{"line-color":"#ffd36a","line-width":1.4,"line-opacity":.65}});
  map.addLayer({id:"power-point",type:"circle",source:"power",paint:{"circle-radius":4,"circle-color":"#ffd36a","circle-opacity":.85}});
  map.addLayer({id:"air-points",type:"circle",source:"air",paint:{
    "circle-radius":8,"circle-color":["interpolate",["linear"],["coalesce",["get","value"],0],0,"#b9ff70",25,"#ffd36a",50,"#ff786b",100,"#c69cff"],
    "circle-stroke-color":"rgba(255,255,255,.65)","circle-stroke-width":1.2,"circle-opacity":.9
  }});
  map.addLayer({id:"water-point",type:"circle",source:"water",paint:{"circle-radius":8,"circle-color":"#64cfff","circle-stroke-color":"rgba(255,255,255,.7)","circle-stroke-width":1.5}});
  clearVisualLayers();
  map.on("click","transit-points",e=>{
    const p=e.features?.[0]?.properties||{};new window.maplibregl.Popup().setLngLat(e.lngLat).setHTML('<div class="vehicle-popup"><strong>'+String(p.line||"Vehicle")+'</strong><br>'+String(p.direction||"")+'</div>').addTo(map);
  });
}
function renderBerlinOutline(){fitBerlin()}

function setMode(mode){
  activeMode=mode;document.querySelectorAll("[data-mode]").forEach(b=>b.classList.toggle("active",b.dataset.mode===mode));
  renderLayerRail();const first=MODES[mode]?.[0]?.[0];if(first)setLayer(first);
}
function renderLayerRail(){
  $("layerRail").innerHTML=(MODES[activeMode]||[]).map(([id,label])=>'<button data-layer="'+id+'">'+label+'</button>').join("");
  $("layerRail").querySelectorAll("[data-layer]").forEach(b=>b.addEventListener("click",()=>setLayer(b.dataset.layer)));
}
async function setLayer(layer){
  activeLayer=layer;const token=++layerToken;resetPanel();document.querySelectorAll("[data-layer]").forEach(b=>b.classList.toggle("active",b.dataset.layer===layer));
  const copy=LAYER_COPY[layer]||["BERLIN",layer,""]; $("insightKicker").textContent=copy[0];$("insightTitle").textContent=copy[1];$("insightStory").textContent=copy[2];
  $("sourceDetail").innerHTML="";
  const handlers={movement:showMovement,air:showAir,weather:showWeather,water:showWater,traffic:showTraffic,population:()=>showOfficialWFS("population"),health:()=>showOfficialWFS("health"),fire:()=>showOfficialWFS("fire"),power:showPower,green:()=>showOfficialWFS("green"),trees:()=>showOfficialWFS("trees"),solar:()=>showOfficialWFS("solar"),heat:()=>showOfficialWFS("heat"),justice:()=>showOfficialWFS("justice"),noise:showNoise,airhistory:showAirHistory,waterhistory:showWaterHistory,bikes:showBikes,accidents:showAccidents};
  try{
    await (handlers[layer]?.()||Promise.resolve())
  }catch(e){
    if(token!==layerToken)return;
    const retryable=e?.name==="AbortError"||/abort|timeout|network|fetch/i.test(String(e?.message||e));
    if(retryable){
      await new Promise(resolve=>setTimeout(resolve,650));
      if(token!==layerToken)return;
      try{await (handlers[layer]?.()||Promise.resolve());return}catch(second){e=second}
    }
    if(token!==layerToken)return;
    renderUnavailable(layer,e);
  }
}
function friendlyFailure(error){
  const raw=String(error?.message||error||"").trim();
  if(error?.name==="AbortError"||/aborted|timeout/i.test(raw))return "The live source timed out.";
  if(/failed to fetch|network/i.test(raw))return "The browser could not reach the live source.";
  return raw&&raw!=="signal is aborted without reason"?raw:"The live source did not answer.";
}
async function renderUnavailable(layer,error){
  $("insight")?.classList.add("degraded");
  $("primaryLabel").textContent="LIVE SOURCE";
  $("primaryValue").textContent="Reconnecting…";
  $("primaryCopy").textContent="Live data failed. Looking for the last recorded observation instead.";
  $("storyNote").innerHTML="COMMONS keeps the failure visible and never invents a replacement. "+friendlyFailure(error)+' <button class="inline-retry" type="button" data-layer-retry>Retry live source</button>';
  $("sourceDetail").innerHTML=sourceCards(layer==="air"||layer==="airhistory"?["air"]:layer==="water"||layer==="waterhistory"?["water"]:layer==="traffic"?["traffic"]:layer==="noise"?["noise"]:layer==="bikes"?["bikes"]:layer==="accidents"?["accidents"]:[layer]);
  $("storyNote").querySelector("[data-layer-retry]")?.addEventListener("click",()=>setLayer(layer));
  await renderTapeFallback(layer,error);
}
async function renderTapeFallback(layer,error){
  const key={movement:"transit_vehicles",weather:"temperature_2m",air:"pm2_5",water:"river_discharge"}[layer];
  if(!key){$("primaryValue").textContent="Unavailable";$("primaryCopy").textContent="No trustworthy recorded fallback exists for this layer yet.";return}
  try{
    const response=await fetch("./data/berlin-pulse/latest.json?t="+Date.now(),{cache:"no-store"});
    if(!response.ok)throw new Error("tape "+response.status);
    const tape=await response.json(),signal=tape?.signals?.[key];
    if(!signal||signal.value==null)throw new Error("no recorded value");
    const age=Math.max(0,Math.round((Date.now()-new Date(tape.generated_at).getTime())/60000));
    $("primaryLabel").textContent="LAST RECORDED · "+String(signal.source||"COMMONS TAPE").toUpperCase();
    $("primaryValue").textContent=human(signal.value)+(signal.unit?" "+signal.unit:"");
    $("primaryCopy").textContent="Recorded "+(age<60?age+" min ago":Math.round(age/60)+" h ago")+" · not live.";
    $("statA").textContent=signal.anomaly?.label||"learning";$("statACopy").textContent="recent pattern";
    $("statB").textContent=signal.anomaly?.score==null?"—":fmt(signal.anomaly.score,1);$("statBCopy").textContent="robust z";
    $("statC").textContent=tape.sample_count||"—";$("statCCopy").textContent="tape samples";
    $("storyNote").innerHTML="Live failed, so this panel is showing a clearly dated recording instead. "+friendlyFailure(error)+' <button class="inline-retry" type="button" data-layer-retry>Try live again</button>';
    $("storyNote").querySelector("[data-layer-retry]")?.addEventListener("click",()=>setLayer(layer));
  }catch{
    $("primaryValue").textContent="Unavailable";
    $("primaryCopy").textContent="Neither the live source nor the recorded tape is readable right now.";
  }
}

async function showMovement(){
  $("sourceDetail").innerHTML=sourceCards(["transit"]);
  const url="https://v6.vbb.transport.rest/radar?north="+BBOX.north+"&west="+BBOX.west+"&south="+BBOX.south+"&east="+BBOX.east+"&results=600&duration=30";
  const raw=await json(url,{},12000);const movements=raw.movements||raw||[];
  const features=(Array.isArray(movements)?movements:[]).map(m=>{
    const loc=m.location||m.currentLocation||{};const lat=Number(loc.latitude),lon=Number(loc.longitude);if(!Number.isFinite(lat)||!Number.isFinite(lon))return null;
    const product=String(m.line?.product||m.line?.mode||m.line?.productName||"").toLowerCase();
    const mode=product.includes("subway")||product.includes("u-bahn")?"subway":product.includes("tram")?"tram":product.includes("bus")?"bus":product.includes("train")||product.includes("regional")||product.includes("suburban")?"train":"other";
    return point(lon,lat,{line:m.line?.name||m.line?.id||"Vehicle",direction:m.direction||"",mode});
  }).filter(Boolean);
  dataToSource("transit",fc(features));setVisible("transit-points",true);fitBerlin();setHealth("transitHealth","ready","TRANSIT · LIVE");
  $("primaryLabel").textContent="VEHICLES NOW";$("primaryValue").textContent=human(features.length);$("primaryCopy").textContent="Vehicles returned inside the Berlin viewport by VBB’s realtime radar.";
  const counts={bus:0,tram:0,subway:0,train:0};features.forEach(f=>{if(counts[f.properties.mode]!=null)counts[f.properties.mode]++});
  $("statA").textContent=counts.train+counts.subway;$("statACopy").textContent="rail / U-Bahn";$("statB").textContent=counts.tram;$("statBCopy").textContent="trams";$("statC").textContent=counts.bus;$("statCCopy").textContent="buses";
  $("storyNote").textContent="This is movement, not punctuality. A vehicle on the map may still be delayed or short-turned.";
}
function weatherGrid(){
  const pts=[];for(let y=0;y<5;y++)for(let x=0;x<5;x++){pts.push({lat:52.34+(y/4)*(52.70-52.34),lon:13.08+(x/4)*(13.78-13.08)})}return pts
}
async function getWeather(){
  if(dataCache.weather)return dataCache.weather;const pts=weatherGrid(),lats=pts.map(p=>p.lat.toFixed(4)).join(","),lons=pts.map(p=>p.lon.toFixed(4)).join(",");
  const url="https://api.open-meteo.com/v1/forecast?latitude="+encodeURIComponent(lats)+"&longitude="+encodeURIComponent(lons)+"&hourly=temperature_2m,apparent_temperature,precipitation&current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation&past_days=1&forecast_days=4&timezone=Europe%2FBerlin";
  const raw=await json(url,{},12000),rows=Array.isArray(raw)?raw:[raw];dataCache.weather=rows.map((r,i)=>({point:pts[i],current:r.current||{},hourly:r.hourly||{}}));setHealth("officialHealth","ready","BERLIN OPEN DATA · READY");return dataCache.weather
}
async function showWeather(){
  $("sourceDetail").innerHTML=sourceCards([])+'<div class="source-card"><strong>Open-Meteo</strong><span>Live modeled weather context over a 5×5 Berlin grid.</span></div>';
  const rows=await getWeather(),times=rows[0]?.hourly?.time||[];showTemporal(rows,times,"temperature_2m","TEMPERATURE","°C","#64cfff","#ff786b");
  const c=rows[Math.floor(rows.length/2)]?.current||{};$("statA").textContent=fmt(c.apparent_temperature)+"°";$("statACopy").textContent="feels like";$("statB").textContent=fmt(c.precipitation)+" mm";$("statBCopy").textContent="current rain";$("statC").textContent=fmt(c.relative_humidity_2m,0)+"%";$("statCCopy").textContent="humidity";
  $("storyNote").textContent="Weather is modeled context. For environmental burden we prefer Berlin’s own measured or official mapped layers.";
}
function showTemporal(rows,times,key,label,unit,c1,c2,index){
  if(!times.length)throw new Error("No time series");let i=index;if(i==null){const now=Date.now();i=times.reduce((best,t,k)=>Math.abs(new Date(t).getTime()-now)<Math.abs(new Date(times[best]).getTime()-now)?k:best,0)}
  const vals=rows.map(r=>Number(r.hourly?.[key]?.[i])).filter(Number.isFinite);const min=Math.min(...vals),max=Math.max(...vals),span=Math.max(.001,max-min);
  const features=rows.map(r=>{const value=Number(r.hourly?.[key]?.[i]);return Number.isFinite(value)?point(r.point.lon,r.point.lat,{value,weight:Math.max(.03,(value-min)/span)}):null}).filter(Boolean);
  dataToSource("dynamic",fc(features));setVisible("dynamic-heat",true);safePaint("dynamic-heat","heatmap-color",["interpolate",["linear"],["heatmap-density"],0,"rgba(0,0,0,0)",.25,c1,.7,c2,1,"rgba(255,255,255,.85)"]);
  const avg=vals.reduce((a,b)=>a+b,0)/(vals.length||1);$("primaryLabel").textContent=label;$("primaryValue").textContent=fmt(avg,1)+" "+unit;$("primaryCopy").textContent="Average across the displayed Berlin model grid.";
  $("timeline").classList.remove("hidden");$("timelineLabel").textContent=label;$("timelineTime").textContent=new Date(times[i]).toLocaleString("en-GB",{weekday:"short",hour:"2-digit",minute:"2-digit"});$("timelineMetric").textContent=fmt(max,1)+" "+unit+" max";
  const slider=$("timeSlider");slider.max=times.length-1;slider.value=i;slider.oninput=()=>showTemporal(rows,times,key,label,unit,c1,c2,Number(slider.value));
}
async function getAirStations(){
  if(dataCache.airStations)return dataCache.airStations;
  const raw=await json("https://luftdaten.berlin.de/api/stations?active=true",{},9000);
  const arr=Array.isArray(raw)?raw:(raw.stations||raw.data||raw.results||[]);
  dataCache.airStations=arr;return arr
}
function stationCoords(s){
  const lat=Number(s.latitude??s.lat??s.location?.latitude??s.geometry?.coordinates?.[1]);const lon=Number(s.longitude??s.lon??s.lng??s.location?.longitude??s.geometry?.coordinates?.[0]);return Number.isFinite(lat)&&Number.isFinite(lon)?[lon,lat]:null
}
function stationCode(s){return String(s.code??s.station_code??s.id??s.station??"")}
function findLatestNumber(value,preferred=["no2","value","measurement"]){
  const candidates=[];
  function walk(v,key=""){
    if(v==null)return;if(typeof v==="number"&&Number.isFinite(v))candidates.push({key:key.toLowerCase(),value:v});
    else if(typeof v==="string"&&v.trim()&&!Number.isNaN(Number(v.replace(",","."))))candidates.push({key:key.toLowerCase(),value:Number(v.replace(",","."))});
    else if(Array.isArray(v))v.forEach(x=>walk(x,key));
    else if(typeof v==="object")Object.entries(v).forEach(([k,x])=>walk(x,k));
  }walk(value);
  for(const p of preferred){const hit=[...candidates].reverse().find(c=>c.key.includes(p));if(hit)return hit.value}
  return candidates.at(-1)?.value??null
}
async function showAir(){
  $("sourceDetail").innerHTML=sourceCards(["air"]);
  try{
    const stations=await getAirStations();const selected=stations.filter(s=>stationCoords(s)&&stationCode(s)).slice(0,14);
    const values=await Promise.all(selected.map(async s=>{
      try{const code=encodeURIComponent(stationCode(s));const raw=await json("https://luftdaten.berlin.de/api/stations/"+code+"/data?core=no2&period=1h&timespan=currentday",{},6500);return {s,value:findLatestNumber(raw,["no2","value"])}}
      catch(e){return {s,value:null}}
    }));
    const features=values.map(({s,value})=>{const c=stationCoords(s);return c&&Number.isFinite(value)?point(c[0],c[1],{value,name:s.name||stationCode(s)}):null}).filter(Boolean);
    if(!features.length)throw new Error("Berlin station API returned no browser-readable current values");
    dataToSource("air",fc(features));setVisible("air-points",true);fitBerlin();setHealth("airHealth","ready","AIR · MEASURED");
    const vals=features.map(f=>f.properties.value),avg=vals.reduce((a,b)=>a+b,0)/vals.length,max=Math.max(...vals);
    $("primaryLabel").textContent="NO₂ · MEASURED";$("primaryValue").textContent=fmt(avg,0)+" µg/m³";$("primaryCopy").textContent="Average of currently readable Berlin monitoring stations.";
    $("statA").textContent=features.length;$("statACopy").textContent="stations read";$("statB").textContent=fmt(max,0);$("statBCopy").textContent="highest NO₂";$("statC").textContent="BLUME";$("statCCopy").textContent="official network";
    $("storyNote").textContent="Station values are measurements at specific places, not a seamless citywide surface.";
  }catch(e){await showAirFallback(e)}
}
async function showAirFallback(reason){
  const pts=weatherGrid(),lats=pts.map(p=>p.lat.toFixed(4)).join(","),lons=pts.map(p=>p.lon.toFixed(4)).join(",");
  const raw=await json("https://air-quality-api.open-meteo.com/v1/air-quality?latitude="+encodeURIComponent(lats)+"&longitude="+encodeURIComponent(lons)+"&hourly=pm2_5&current=pm2_5,nitrogen_dioxide,ozone&past_days=1&forecast_days=4&timezone=Europe%2FBerlin",{},12000);
  const rows=(Array.isArray(raw)?raw:[raw]).map((r,i)=>({point:pts[i],current:r.current||{},hourly:r.hourly||{}}));dataCache.airFallback=rows;const times=rows[0]?.hourly?.time||[];
  showTemporal(rows,times,"pm2_5","PM2.5","µg/m³","#8b65d0","#d9b3ff");setHealth("airHealth","warn","AIR · MODELED FALLBACK");
  const c=rows[Math.floor(rows.length/2)]?.current||{};$("statA").textContent=fmt(c.pm2_5,0);$("statACopy").textContent="PM2.5";$("statB").textContent=fmt(c.nitrogen_dioxide,0);$("statBCopy").textContent="NO₂";$("statC").textContent=fmt(c.ozone,0);$("statCCopy").textContent="ozone";
  $("storyNote").textContent="Berlin’s measured station endpoint was not readable in this browser, so COMMONS fell back to modeled CAMS air. The layer is explicitly marked as fallback. "+(reason?.message||"");
}
async function showAirHistory(){
  $("sourceDetail").innerHTML=sourceCards(["air"]);
  try{
    const stations=await getAirStations();const s=stations.find(x=>stationCoords(x)&&stationCode(x));if(!s)throw new Error("No active station");
    const raw=await json("https://luftdaten.berlin.de/api/stations/"+encodeURIComponent(stationCode(s))+"/data?core=no2&period=24h&timespan=currentmonth",{},9000);
    const pairs=extractSeries(raw);if(pairs.length<2)throw new Error("No parsed station history");
    renderLineCards("Measured NO₂ history",pairs,s.name||stationCode(s),"µg/m³");setHealth("airHealth","ready","AIR · HISTORY");
  }catch(e){await showAirFallback(e)}
}
function extractSeries(raw){
  const pairs=[];function walk(v){if(Array.isArray(v)){for(const x of v){if(x&&typeof x==="object"){const t=x.time??x.timestamp??x.datetime??x.date;const val=findLatestNumber(x,["no2","value","measurement"]);if(t&&Number.isFinite(val))pairs.push([String(t),val]);walk(x)}}}else if(v&&typeof v==="object")Object.values(v).forEach(walk)}walk(raw);return pairs.slice(-60)
}
function renderLineCards(title,pairs,subtitle,unit){
  $("primaryLabel").textContent=title.toUpperCase();$("primaryValue").textContent=fmt(pairs.at(-1)?.[1],0)+" "+unit;$("primaryCopy").textContent=subtitle;
  $("cards").classList.remove("hidden");const vals=pairs.map(p=>p[1]),min=Math.min(...vals),max=Math.max(...vals);
  $("cards").innerHTML='<div class="data-card"><strong>'+title+'</strong><span>'+pairs.length+' observations · min '+fmt(min,0)+' · max '+fmt(max,0)+' · latest '+fmt(vals.at(-1),0)+' '+unit+'</span></div>';
}
function germanDate(d){return String(d.getDate()).padStart(2,"0")+"."+String(d.getMonth()+1).padStart(2,"0")+"."+d.getFullYear()}
async function getOfficialWaterSeries(){
  const start=new Date(Date.now()-14*86400000);
  const url="https://wasserportal.berlin.de/station.php?anzeige=d&station=582720&thema=odf&sreihe=tw&smode=c&sdatum="+germanDate(start);
  const raw=await textFetch(url,{},9000);const rows=raw.split(/\r?\n/).map(line=>line.split(";")).filter(r=>r.length>=2);
  const pairs=[];for(const r of rows){const joined=r.join(" ");const nums=r.map(x=>Number(String(x).replace(",",".").replace(/[^0-9.\-]/g,""))).filter(Number.isFinite);if(nums.length){const v=nums.at(-1);if(Number.isFinite(v)&&v>=0&&v<10000)pairs.push([r[0],v])}}
  if(pairs.length<3)throw new Error("Official Wasserportal response was not a readable CSV series");return pairs.slice(-60)
}
async function getGlofas(){
  const raw=await json("https://flood-api.open-meteo.com/v1/flood?latitude=52.52&longitude=13.41&daily=river_discharge&past_days=7&forecast_days=7&timezone=Europe%2FBerlin",{},10000);return (raw.daily?.time||[]).map((t,i)=>[t,Number(raw.daily?.river_discharge?.[i])]).filter(p=>Number.isFinite(p[1]))
}
async function showWater(){await showWaterCommon(false)}
async function showWaterHistory(){await showWaterCommon(true)}
async function showWaterCommon(history){
  $("sourceDetail").innerHTML=sourceCards(["water"]);let pairs,official=true;
  try{pairs=await getOfficialWaterSeries();setHealth("waterHealth","ready","WATER · MEASURED")}
  catch(e){pairs=await getGlofas();official=false;setHealth("waterHealth","warn","WATER · GLOFAS FALLBACK")}
  dataToSource("water",fc([point(13.408,52.515,{name:"Spree / Mühlendamm"})]));setVisible("water-point",true);mapReady&&map.flyTo({center:[13.408,52.515],zoom:12.4,pitch:48,bearing:-15,duration:1000});
  const vals=pairs.map(p=>p[1]);$("primaryLabel").textContent=official?"SPREE · MEASURED DISCHARGE":"SPREE · MODELED DISCHARGE";$("primaryValue").textContent=human(vals.at(-1))+" m³/s";$("primaryCopy").textContent=official?"Wasserportal Berlin · station 582720 (Mühlendamm OP).":"GloFAS fallback near central Berlin.";
  $("statA").textContent=fmt(Math.min(...vals),1);$("statACopy").textContent="min";$("statB").textContent=fmt(Math.max(...vals),1);$("statBCopy").textContent="max";$("statC").textContent=pairs.length;$("statCCopy").textContent="observations";
  $("storyNote").textContent=official?"Raw official water observations can be provisional; COMMONS shows the source rather than hiding that caveat.":"Official water data was not browser-readable, so this is explicitly a modeled fallback.";
  if(history)renderLineCards(official?"Spree measured history":"Spree modeled history",pairs,official?"Mühlendamm":"GloFAS","m³/s");
}
async function showTraffic(){
  $("sourceDetail").innerHTML=sourceCards(["traffic"]);
  $("primaryLabel").textContent="LIVE AUTHORITY";$("primaryValue").textContent="VIZ Berlin";$("primaryCopy").textContent="Construction, closures, disruptions and traffic are maintained by Berlin’s official VIZ service.";
  $("statA").textContent="240+";$("statACopy").textContent="detector sites";$("statB").textContent="hourly";$("statBCopy").textContent="historical detector data";$("statC").textContent="live";$("statCCopy").textContent="VIZ city view";
  $("storyNote").innerHTML='COMMONS does not fabricate a traffic heatmap when the live JSON feed is not verified. <a href="'+SOURCES.traffic.url+'" target="_blank" rel="noreferrer">Open VIZ ↗</a>';
  try{await renderWFS("https://gdi.berlin.de/services/wfs/detailnetz",[/detail/i,/netz/i],450,"line","#ffcf67");}catch(e){}
}
const WFS_CONFIG={
  population:{endpoint:SOURCES.population.url,patterns:[/einwohner/i,/dichte/i],count:350,kind:"polygon",color:"#8ed8ff",sources:["population"]},
  health:{endpoint:SOURCES.health.url,patterns:[/kranken/i,/hospital/i],count:200,kind:"point",color:"#f4f7f1",sources:["health"]},
  fire:{endpoint:SOURCES.fire.url,patterns:[/standort/i,/feuer/i,/wache/i],count:180,kind:"point",color:"#ff786b",sources:["fire"]},
  green:{endpoint:SOURCES.green.url,patterns:[/gruen/i,/anlage/i],count:350,kind:"polygon",color:"#80e596",sources:["green"]},
  trees:{endpoint:SOURCES.trees.url,patterns:[/strassenbaeume/i,/anlagenbaeume/i,/baum/i],count:800,kind:"point",color:"#a8ef78",sources:["trees"]},
  solar:{endpoint:SOURCES.solar.url,patterns:[/solar/i,/anlage/i],count:450,kind:"point",color:"#ffd36a",sources:["solar"]},
  heat:{endpoint:SOURCES.heat.url,patterns:[/pet/i,/utci/i,/klima/i,/therm/i,/block/i],count:350,kind:"polygon",color:"#ff786b",sources:["heat"]},
  justice:{endpoint:SOURCES.justice.url,patterns:[/umwelt/i,/gerecht/i,/belast/i,/mehrfach/i],count:350,kind:"polygon",color:"#c69cff",sources:["justice"]}
};
async function discoverFeatureTypes(endpoint){
  if(officialCache[endpoint]?.types)return officialCache[endpoint].types;
  const raw=await textFetch(endpoint+"?service=WFS&request=GetCapabilities",{},10000);const doc=new DOMParser().parseFromString(raw,"text/xml");
  const types=[...doc.querySelectorAll("FeatureType > Name, FeatureType Name")].map(x=>x.textContent.trim()).filter(Boolean);officialCache[endpoint]={...(officialCache[endpoint]||{}),types};return types
}
async function loadWFS(endpoint,patterns,count=300){
  const types=await discoverFeatureTypes(endpoint);if(!types.length)throw new Error("No WFS feature types");
  let name=types.find(t=>patterns.some(p=>p.test(t)))||types[0];
  const params=new URLSearchParams({service:"WFS",version:"2.0.0",request:"GetFeature",typeNames:name,outputFormat:"application/json",srsName:"EPSG:4326",count:String(count)});
  const raw=await json(endpoint+"?"+params.toString(),{},13000);return {data:raw,name}
}
function geometryKind(feature){
  const t=feature?.geometry?.type||"";if(t.includes("Polygon"))return"polygon";if(t.includes("LineString"))return"line";return"point"
}
async function renderWFS(endpoint,patterns,count,preferredKind,color){
  const result=await loadWFS(endpoint,patterns,count),features=result.data.features||[];dataToSource("official",fc(features));
  const kinds=new Set(features.map(geometryKind));setVisible("official-fill",kinds.has("polygon"));setVisible("official-line",kinds.has("line"));setVisible("official-point",kinds.has("point"));
  if(color){safePaint("official-fill","fill-color",color);safePaint("official-line","line-color",color);safePaint("official-point","circle-color",color)}
  return {features,typeName:result.name,kinds}
}
async function showOfficialWFS(key){
  const cfg=WFS_CONFIG[key];$("sourceDetail").innerHTML=sourceCards(cfg.sources);const result=await renderWFS(cfg.endpoint,cfg.patterns,cfg.count,cfg.kind,cfg.color);fitBerlin();setHealth("officialHealth","ready","BERLIN OPEN DATA · LIVE");
  $("primaryLabel").textContent="OFFICIAL FEATURES";$("primaryValue").textContent=human(result.features.length);$("primaryCopy").textContent="Browser-loaded sample from "+result.typeName+".";
  $("statA").textContent=result.features.length;$("statACopy").textContent="features loaded";$("statB").textContent=[...result.kinds].join(" / ");$("statBCopy").textContent="geometry";$("statC").textContent="WFS";$("statCCopy").textContent="Berlin Geoportal";
  $("storyNote").textContent=key==="justice"?"This is an official integrated burden layer. COMMONS does not collapse it further into its own morality score.":key==="heat"?"This is historical/planning climate analysis, not today’s temperature.":"Mapped context is not the same as service availability, capacity or impact.";
}
async function showPower(){
  $("sourceDetail").innerHTML='<div class="source-card"><strong>OpenStreetMap / Overpass</strong><span>Power substations and transmission lines. Berlin official grid-detail feeds are not substituted with guessed network topology.</span></div>';
  const q='[out:json][timeout:25];(nwr(around:22000,52.52,13.405)[power="substation"];way(around:26000,52.52,13.405)[power="line"];);out center geom tags;';
  const body=new URLSearchParams({data:q});let raw=null;for(const url of ["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter"]){try{raw=await json(url,{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body},12000);break}catch(e){}}
  if(!raw)throw new Error("Overpass unavailable");
  const features=[];for(const el of raw.elements||[]){const t=el.tags||{};if(el.geometry?.length){features.push({type:"Feature",properties:{kind:"line",name:t.name||"power line"},geometry:{type:"LineString",coordinates:el.geometry.map(p=>[p.lon,p.lat])}})}else{const lat=el.lat??el.center?.lat,lon=el.lon??el.center?.lon;if(Number.isFinite(lat)&&Number.isFinite(lon))features.push(point(lon,lat,{kind:"substation",name:t.name||"substation"}))}}
  dataToSource("power",fc(features));setVisible("power-line",true);setVisible("power-point",true);fitBerlin();$("primaryLabel").textContent="POWER FEATURES";$("primaryValue").textContent=human(features.length);$("primaryCopy").textContent="Mapped substations and transmission-line geometries.";
  const lines=features.filter(f=>geometryKind(f)==="line").length;$("statA").textContent=features.length-lines;$("statACopy").textContent="substations";$("statB").textContent=lines;$("statBCopy").textContent="line features";$("statC").textContent="OSM";$("statCCopy").textContent="community map";
}
function showNoise(){
  $("sourceDetail").innerHTML=sourceCards(["noise"]);$("primaryLabel").textContent="OFFICIAL SOURCE";$("primaryValue").textContent="Strategic noise maps";$("primaryCopy").textContent="Road, tram, U-Bahn and other major noise sources are mapped by Berlin.";
  $("statA").textContent="2022";$("statACopy").textContent="strategic map";$("statB").textContent="multiple";$("statBCopy").textContent="transport sources";$("statC").textContent="official";$("statCCopy").textContent="Umweltatlas";
  $("storyNote").innerHTML='The exact stable feature endpoint is not yet verified in-browser, so COMMONS links the official layer instead of inventing a raster. <a href="'+SOURCES.noise.url+'" target="_blank">Open Umweltatlas ↗</a>';
}
function showBikes(){
  $("sourceDetail").innerHTML=sourceCards(["bikes"]);$("primaryLabel").textContent="OFFICIAL HISTORY";$("primaryValue").textContent="Hourly bike counts";$("primaryCopy").textContent="Permanent Berlin counters, published as historical open data.";
  $("statA").textContent="hourly";$("statACopy").textContent="granularity";$("statB").textContent="through 2025";$("statBCopy").textContent="published series";$("statC").textContent="official";$("statCCopy").textContent="Berlin Open Data";
  $("storyNote").innerHTML='This should become a true time-series layer after ingesting the XLSX into COMMONS’ own static data pipeline. <a href="'+SOURCES.bikes.url+'" target="_blank">Open dataset ↗</a>';
}
function showAccidents(){
  $("sourceDetail").innerHTML=sourceCards(["accidents"]);$("primaryLabel").textContent="OFFICIAL MEMORY";$("primaryValue").textContent="Traffic crashes";$("primaryCopy").textContent="Geolocated historical accident datasets are available from Berlin Open Data.";
  $("statA").textContent="GPS";$("statACopy").textContent="historical data";$("statB").textContent="annual";$("statBCopy").textContent="official releases";$("statC").textContent="memory";$("statCCopy").textContent="not risk score";
  $("storyNote").innerHTML='Next step: ingest the geolocated CSVs into a stable historical layer. COMMONS will show events, not label neighborhoods as dangerous. <a href="'+SOURCES.accidents.url+'" target="_blank">Open datasets ↗</a>';
}

function bindUI(){
  $("enterBerlin").addEventListener("click",()=>{$("intro").classList.add("hidden");$("insight").classList.remove("hidden");$("layerRail").classList.remove("hidden");setMode("now")});
  document.querySelectorAll("[data-mode]").forEach(b=>b.addEventListener("click",()=>setMode(b.dataset.mode)));
}
initMap();bindUI();
