import * as maplibregl from 'https://unpkg.com/maplibre-gl@6.10.0/dist/maplibre-gl.mjs';

const $=id=>document.getElementById(id);
const MANILA={lat:14.5995,lon:120.9842};
const GRID_RADIUS_DEG=1.2;
const GRID_STEPS=7;
let map;
let liveBrief=null;
let impactReport=null;
let weatherData=null;
let weatherTimes=[];
let nowIndex=0;
let infrastructure=[];
let historyEvents=[];

function pct(v){const n=Number(v);return Number.isFinite(n)?Math.round(n*100)+"%":"—"}
function human(v){const n=Number(v);if(!Number.isFinite(n))return "—";if(n>=1e6)return (n/1e6).toFixed(1)+"M";if(n>=1e3)return Math.round(n/1e3)+"k";return Math.round(n)}
async function getJson(url,options){const r=await fetch(url,{cache:"no-store",...(options||{})});if(!r.ok)throw new Error("HTTP "+r.status);return r.json()}
async function loadBrief(){
  const url="https://raw.githubusercontent.com/mikelninh/COMMONS/world-model-data/data/world-model/morning-brief.json";
  try{return await getJson(url)}catch(error){return null}
}
async function loadImpact(){try{return await getJson("./world-model/impact-report.json")}catch(error){return null}}
function manilaMonitor(){return (liveBrief?.monitors||[]).find(x=>x.point_id==="manila")||null}
function manilaProfile(){return (impactReport?.profiles||[]).find(x=>x.point_id==="manila")||null}

function circlePolygon(lon,lat,radiusKm,steps=80){
  const coords=[];
  const earth=6371;
  const lat1=lat*Math.PI/180;
  const lon1=lon*Math.PI/180;
  for(let i=0;i<=steps;i++){
    const bearing=2*Math.PI*i/steps;
    const d=radiusKm/earth;
    const lat2=Math.asin(Math.sin(lat1)*Math.cos(d)+Math.cos(lat1)*Math.sin(d)*Math.cos(bearing));
    const lon2=lon1+Math.atan2(Math.sin(bearing)*Math.sin(d)*Math.cos(lat1),Math.cos(d)-Math.sin(lat1)*Math.sin(lat2));
    coords.push([lon2*180/Math.PI,lat2*180/Math.PI]);
  }
  return {type:"Feature",properties:{radius_km:radiusKm},geometry:{type:"Polygon",coordinates:[coords]}};
}
function haversine(a,b,c,d){
  const R=6371,toRad=x=>x*Math.PI/180;
  const dLat=toRad(c-a),dLon=toRad(d-b);
  const q=Math.sin(dLat/2)**2+Math.cos(toRad(a))*Math.cos(toRad(c))*Math.sin(dLon/2)**2;
  return 2*R*Math.asin(Math.sqrt(q));
}
function gridPoints(){
  const points=[];
  for(let y=0;y<GRID_STEPS;y++){
    for(let x=0;x<GRID_STEPS;x++){
      const fx=x/(GRID_STEPS-1)-.5;
      const fy=y/(GRID_STEPS-1)-.5;
      points.push({lat:MANILA.lat+fy*2*GRID_RADIUS_DEG,lon:MANILA.lon+fx*2*GRID_RADIUS_DEG});
    }
  }
  return points;
}
async function loadWeather(){
  const points=gridPoints();
  const latitudes=points.map(p=>p.lat.toFixed(4)).join(",");
  const longitudes=points.map(p=>p.lon.toFixed(4)).join(",");
  const url="https://api.open-meteo.com/v1/forecast?latitude="+encodeURIComponent(latitudes)+"&longitude="+encodeURIComponent(longitudes)+"&hourly=precipitation&past_days=1&forecast_days=4&timezone=UTC";
  const payload=await getJson(url);
  const rows=Array.isArray(payload)?payload:[payload];
  weatherData=rows.map((row,i)=>({point:points[i],times:row.hourly?.time||[],precip:row.hourly?.precipitation||[]}));
  weatherTimes=weatherData[0]?.times||[];
  const now=Date.now();
  nowIndex=weatherTimes.reduce((best,t,i)=>Math.abs(new Date(t+"Z").getTime()-now)<Math.abs(new Date(weatherTimes[best]+"Z").getTime()-now)?i:best,0);
  const slider=$("timeSlider");
  slider.max=Math.max(0,weatherTimes.length-1);
  slider.value=nowIndex;
  slider.disabled=!weatherTimes.length;
  slider.addEventListener("input",()=>renderWeather(Number(slider.value)));
  renderWeather(nowIndex);
  $("weatherLayerStatus").textContent="RAIN · LIVE";
  $("weatherLayerStatus").classList.add("ready");
}
function weatherGeoJSON(index){
  const features=(weatherData||[]).map(row=>({
    type:"Feature",
    properties:{precip:Number(row.precip[index])||0},
    geometry:{type:"Point",coordinates:[row.point.lon,row.point.lat]}
  }));
  return {type:"FeatureCollection",features};
}
function renderWeather(index){
  if(!weatherTimes.length)return;
  const geo=weatherGeoJSON(index);
  const source=map.getSource("weather-grid");
  if(source)source.setData(geo);
  const when=new Date(weatherTimes[index]+"Z");
  $("timeLabel").textContent=when.toLocaleString([], {weekday:"short",hour:"2-digit",minute:"2-digit",day:"2-digit",month:"short"});
  const peak=Math.max(...geo.features.map(f=>f.properties.precip));
  $("rainPeak").textContent=peak.toFixed(1)+" mm/h";
}
async function loadInfrastructure(){
  const q='[out:json][timeout:25];('+
    'nwr(around:18000,'+MANILA.lat+','+MANILA.lon+')[amenity~"^(hospital|clinic)$"];'+
    'nwr(around:18000,'+MANILA.lat+','+MANILA.lon+')[power="substation"];'+
    'nwr(around:18000,'+MANILA.lat+','+MANILA.lon+')[bridge="yes"];'+
  ');out center tags;';
  const body=new URLSearchParams({data:q});
  const endpoints=["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter"];
  let payload=null;
  for(const endpoint of endpoints){
    try{payload=await getJson(endpoint,{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body});break}catch(error){}
  }
  if(!payload)throw new Error("Overpass unavailable");
  infrastructure=(payload.elements||[]).map(el=>{
    const lat=el.lat??el.center?.lat,lon=el.lon??el.center?.lon,tags=el.tags||{};
    if(lat==null||lon==null)return null;
    let kind="other";
    if(["hospital","clinic"].includes(tags.amenity))kind="health";
    else if(tags.power==="substation")kind="power";
    else if(tags.bridge==="yes")kind="bridge";
    return {type:"Feature",properties:{kind,name:tags.name||kind},geometry:{type:"Point",coordinates:[lon,lat]}};
  }).filter(Boolean);
  const source=map.getSource("infrastructure");
  if(source)source.setData({type:"FeatureCollection",features:infrastructure});
  $("healthCount").textContent=infrastructure.filter(x=>x.properties.kind==="health").length;
  $("bridgeCount").textContent=infrastructure.filter(x=>x.properties.kind==="bridge").length;
  $("powerCount").textContent=infrastructure.filter(x=>x.properties.kind==="power").length;
  $("infraLayerStatus").textContent="SYSTEMS · OSM";
  $("infraLayerStatus").classList.add("ready");
}
async function loadHistory(){
  const end=new Date();
  const start=new Date(end.getTime()-1000*60*60*24*365*3);
  const iso=d=>d.toISOString().slice(0,10);
  const url="https://www.gdacs.org/gdacsapi/api/Events/geteventlist/SEARCH?eventlist=FL%3BTC&fromdate="+iso(start)+"&todate="+iso(end)+"&alertlevel=green%3Borange%3Bred&pagesize=100&pagenumber=1";
  const payload=await getJson(url);
  const features=payload.features||payload.data||payload.events||[];
  historyEvents=(features||[]).map(item=>{
    const p=item.properties||item;
    const coords=item.geometry?.coordinates||[];
    const lon=Number(coords[0]??p.longitude??p.lon),lat=Number(coords[1]??p.latitude??p.lat);
    if(!Number.isFinite(lat)||!Number.isFinite(lon))return null;
    const distance=haversine(MANILA.lat,MANILA.lon,lat,lon);
    if(distance>350)return null;
    return {type:"Feature",properties:{
      name:p.name||p.eventname||p.title||"Historical event",
      event_type:p.eventtype||p.eventType||"",
      alert:String(p.alertlevel||p.alertLevel||"").toLowerCase(),
      start_date:String(p.fromdate||p.fromDate||p.startdate||"").slice(0,10),
      distance_km:Math.round(distance)
    },geometry:{type:"Point",coordinates:[lon,lat]}};
  }).filter(Boolean).slice(0,20);
  const source=map.getSource("history-events");
  if(source)source.setData({type:"FeatureCollection",features:historyEvents});
  $("historyCopy").textContent=historyEvents.length
    ?historyEvents.length+" flood / cyclone events from the last three years fall within 350 km of Manila."
    :"No nearby GDACS flood / cyclone events loaded in this window.";
  $("memoryList").innerHTML=historyEvents.slice(0,5).map(e=>
    '<div class="memory-item"><strong>'+e.properties.name+'</strong><small>'+e.properties.start_date+' · '+e.properties.distance_km+' km away · '+(e.properties.alert||"unknown")+'</small></div>'
  ).join("");
  $("historyLayerStatus").textContent="MEMORY · GDACS";
  $("historyLayerStatus").classList.add("ready");
}
function addSourcesAndLayers(){
  map.addSource("weather-grid",{type:"geojson",data:{type:"FeatureCollection",features:[]}});
  map.addLayer({
    id:"weather-heat",type:"heatmap",source:"weather-grid",maxzoom:13,
    paint:{
      "heatmap-weight":["interpolate",["linear"],["get","precip"],0,0,1,.15,5,.55,15,1],
      "heatmap-intensity":["interpolate",["linear"],["zoom"],4,.6,10,1.4],
      "heatmap-radius":["interpolate",["linear"],["zoom"],4,28,10,70],
      "heatmap-opacity":.82,
      "heatmap-color":["interpolate",["linear"],["heatmap-density"],0,"rgba(0,0,0,0)",.15,"rgba(40,120,170,.08)",.35,"rgba(62,169,230,.32)",.6,"rgba(82,207,255,.54)",.82,"rgba(173,230,255,.72)",1,"rgba(255,255,255,.86)"]
    }
  });
  map.addSource("exposure-area",{type:"geojson",data:{type:"FeatureCollection",features:[]}});
  map.addLayer({id:"exposure-fill",type:"fill",source:"exposure-area",paint:{"fill-color":"#b8ff72","fill-opacity":.14}});
  map.addLayer({id:"exposure-line",type:"line",source:"exposure-area",paint:{"line-color":"#b8ff72","line-opacity":.5,"line-width":1.2}});
  map.addSource("infrastructure",{type:"geojson",data:{type:"FeatureCollection",features:[]}});
  map.addLayer({id:"infra-points",type:"circle",source:"infrastructure",paint:{
    "circle-radius":["match",["get","kind"],"health",5,"power",4,"bridge",3,3],
    "circle-color":["match",["get","kind"],"health","#f6f7f2","power","#ffd56e","bridge","#7ad7ff","#d6ddd3"],
    "circle-opacity":.86,"circle-stroke-width":1,"circle-stroke-color":"rgba(0,0,0,.5)"
  }});
  map.addSource("history-events",{type:"geojson",data:{type:"FeatureCollection",features:[]}});
  map.addLayer({id:"history-rings",type:"circle",source:"history-events",paint:{
    "circle-radius":["interpolate",["linear"],["zoom"],4,6,9,12],
    "circle-color":"rgba(0,0,0,0)","circle-stroke-width":2,
    "circle-stroke-color":["match",["get","alert"],"red","#ff7b6e","orange","#ffd56e","#b8ff72"],
    "circle-stroke-opacity":.7
  }});
  setLayerVisibility("weather-heat",false);
  setLayerVisibility("exposure-fill",false);setLayerVisibility("exposure-line",false);
  setLayerVisibility("infra-points",false);setLayerVisibility("history-rings",false);
}
function setLayerVisibility(id,visible){if(map.getLayer(id))map.setLayoutProperty(id,"visibility",visible?"visible":"none")}
function fly(options){map.flyTo({essential:true,duration:1700,...options})}
function setScene(scene){
  if(scene==="world"){
    map.setProjection({type:"globe"});
    fly({center:[105,12],zoom:1.25,pitch:0,bearing:0});
  }else{
    map.setProjection({type:"mercator"});
    if(scene==="manila")fly({center:[MANILA.lon,MANILA.lat],zoom:9.1,pitch:48,bearing:-18});
    if(scene==="rain")fly({center:[121.02,14.66],zoom:8.6,pitch:38,bearing:-9});
    if(scene==="people")fly({center:[MANILA.lon,MANILA.lat],zoom:9.4,pitch:52,bearing:12});
    if(scene==="systems")fly({center:[120.99,14.60],zoom:11.1,pitch:58,bearing:-22});
    if(scene==="memory")fly({center:[121.0,14.8],zoom:6.9,pitch:22,bearing:5});
    if(scene==="future")fly({center:[MANILA.lon,MANILA.lat],zoom:9.0,pitch:45,bearing:-6});
    if(scene==="trust")fly({center:[116,13],zoom:4.1,pitch:18,bearing:0});
  }
  setLayerVisibility("weather-heat",["rain","future"].includes(scene));
  setLayerVisibility("exposure-fill",scene==="people");setLayerVisibility("exposure-line",scene==="people");
  setLayerVisibility("infra-points",scene==="systems");
  setLayerVisibility("history-rings",scene==="memory");
}
function observeScenes(){
  const observer=new IntersectionObserver(entries=>{
    const visible=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];
    if(visible)setScene(visible.target.dataset.scene);
  },{threshold:[.35,.55,.75]});
  document.querySelectorAll(".scene").forEach(scene=>observer.observe(scene));
}
function renderImpactContext(){
  const monitor=manilaMonitor();
  const profile=manilaProfile();
  const ratio=Number(monitor?.gate_ratio)||0;
  const state=monitor?.state||"quiet";
  if(state==="alert"||ratio>=1){
    $("manilaState").textContent="Manila deserves attention now.";
    $("manilaStateCopy").textContent="Forecast rain is beyond the locally learned heavy-rain threshold. Confirm with official local warnings before acting.";
  }else if(state==="priority"||ratio>=.8){
    $("manilaState").textContent="The signal is getting close.";
    $("manilaStateCopy").textContent="Rain is approaching a locally unusual level, but has not crossed the alert gate.";
  }else{
    $("manilaState").textContent="Manila is quiet right now.";
    $("manilaStateCopy").textContent="Forecast rain is below the locally learned heavy-rain threshold.";
  }
  const exp=profile?.components?.exposure||{};
  $("populationHeadline").textContent=human(exp.population_within_radius)+" people live within the wider "+(exp.radius_km||20)+" km context area.";
  const radius=Number(exp.radius_km)||20;
  const source=map.getSource("exposure-area");
  if(source)source.setData({type:"FeatureCollection",features:[circlePolygon(MANILA.lon,MANILA.lat,radius)]});
  $("actionList").innerHTML=(profile?.action_options||[]).map(a=>'<div class="action-row"><div><strong>'+a.label+'</strong><small>'+a.why+'</small></div></div>').join("");
}
function initMap(){
  map=new maplibregl.Map({
    container:"map",
    style:"https://tiles.openfreemap.org/styles/liberty",
    center:[105,12],
    zoom:1.25,
    attributionControl:true,
    antialias:true
  });
  map.dragRotate.disable();
  map.touchZoomRotate.disableRotation();
  map.on("style.load",()=>{
    map.setProjection({type:"globe"});
    addSourcesAndLayers();
    renderImpactContext();
    observeScenes();
    Promise.allSettled([loadWeather(),loadInfrastructure(),loadHistory()]);
  });
}
async function init(){
  [liveBrief,impactReport]=await Promise.all([loadBrief(),loadImpact()]);
  initMap();
}
init();
