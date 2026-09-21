const maplibregl=window.maplibregl;

const $=id=>document.getElementById(id);

const CITIES={
  hanoi:{
    name:"Hanoi",country:"Vietnam",coords:[105.8542,21.0285],river:[105.89,21.05],
    zoom:9.7,bearing:-8,pitch:48,defaultLayer:"wetness",
    kicker:"WATER · MONSOON · RED RIVER",
    story:"A city where the interesting question is not only how much rain falls, but how wet the system already is before the next storm arrives.",
    context:"Rain, near-surface soil moisture, river discharge and historical flood memory are the dominant signals here."
  },
  saigon:{
    name:"Saigon",country:"Vietnam",coords:[106.6297,10.8231],river:[106.72,10.80],
    zoom:10,bearing:15,pitch:52,defaultLayer:"heat",
    kicker:"HEAT · RAIN · DENSE SYSTEMS",
    story:"Heat, humidity and tropical rain interact with one of Southeast Asia’s densest urban systems.",
    context:"Apparent temperature, rainfall, river context, hospitals, bridges and power infrastructure tell different parts of the same story."
  },
  berlin:{
    name:"Berlin",country:"Germany",coords:[13.405,52.52],river:[13.41,52.52],
    zoom:10.2,bearing:-16,pitch:50,defaultLayer:"air",
    kicker:"AIR · WATER · URBAN SYSTEMS",
    story:"Berlin tells a quieter story: air quality, heat, the Spree/Havel system and the infrastructure of an everyday city.",
    context:"Air pollution becomes visible as atmosphere, while rivers and urban systems remain explorable underneath."
  },
  manila:{
    name:"Manila",country:"Philippines",coords:[120.9842,14.5995],river:[120.99,14.59],
    zoom:9.7,bearing:-18,pitch:48,defaultLayer:"rain",
    kicker:"STORM · SYSTEMS · MEMORY",
    story:"A coastal megacity where rainfall can become consequential when it intersects with dense infrastructure and a long memory of storms.",
    context:"Rainfall, critical systems, river context and nearby disaster history are the central layers."
  }
};

const FIELD_STYLES={
  rain:{label:"RAIN",unit:"mm/h",colorStops:[[0,"rgba(0,0,0,0)"],[.2,"rgba(44,134,195,.12)"],[.45,"rgba(71,185,244,.4)"],[.72,"rgba(104,220,255,.68)"],[1,"rgba(239,250,255,.92)"]]},
  heat:{label:"APPARENT HEAT",unit:"°C",colorStops:[[0,"rgba(0,0,0,0)"],[.2,"rgba(255,192,93,.14)"],[.48,"rgba(255,137,77,.42)"],[.75,"rgba(255,85,65,.7)"],[1,"rgba(255,220,155,.9)"]]},
  wetness:{label:"SOIL WETNESS",unit:"m³/m³",colorStops:[[0,"rgba(0,0,0,0)"],[.22,"rgba(75,180,145,.14)"],[.48,"rgba(86,234,188,.4)"],[.75,"rgba(102,255,204,.7)"],[1,"rgba(220,255,241,.9)"]]},
  air:{label:"PM2.5",unit:"µg/m³",colorStops:[[0,"rgba(0,0,0,0)"],[.2,"rgba(137,94,210,.12)"],[.48,"rgba(178,126,244,.4)"],[.75,"rgba(207,157,255,.66)"],[1,"rgba(244,224,255,.9)"]]}
};

let map;
let activeCity=null;
let activeLayer=null;
const cache={};
let gdacsAll=null;

function human(v){const n=Number(v);if(!Number.isFinite(n))return "—";if(Math.abs(n)>=1e6)return (n/1e6).toFixed(1)+"M";if(Math.abs(n)>=1e3)return Math.round(n/1e3)+"k";return n.toFixed(n<10?1:0)}
function fmt(v,d=1){const n=Number(v);return Number.isFinite(n)?n.toFixed(d):"—"}
function health(id,ready,label){const el=$(id);el.textContent=label;el.classList.toggle("ready",!!ready)}
async function getJson(url,options){const r=await fetch(url,{cache:"no-store",...(options||{})});if(!r.ok)throw new Error("HTTP "+r.status);return r.json()}
function haversine(a,b,c,d){const R=6371,toRad=x=>x*Math.PI/180;const dLat=toRad(c-a),dLon=toRad(d-b);const q=Math.sin(dLat/2)**2+Math.cos(toRad(a))*Math.cos(toRad(c))*Math.sin(dLon/2)**2;return 2*R*Math.asin(Math.sqrt(q))}
function gridAround(city,steps=5,radius=.8){const pts=[];for(let y=0;y<steps;y++)for(let x=0;x<steps;x++){const fx=x/(steps-1)-.5,fy=y/(steps-1)-.5;pts.push({lon:city.coords[0]+fx*2*radius,lat:city.coords[1]+fy*2*radius})}return pts}
function emptyFC(){return {type:"FeatureCollection",features:[]}}
function fc(features){return {type:"FeatureCollection",features}}

function initMap(){
  if(!maplibregl){
    const fallback=document.getElementById("atlasFallback");
    if(fallback)fallback.classList.remove("hidden");
    return;
  }
  try{
  map=new maplibregl.Map({
    container:"map",
    style:"https://tiles.openfreemap.org/styles/liberty",
    center:[80,26],zoom:1.3,pitch:0,bearing:0,antialias:true,attributionControl:true
  });
  map.on("style.load",()=>{
    map.setProjection({type:"globe"});
    addSources();
    renderCityPins();
    showWorld(false);
  });
  map.on("error",event=>{
    if(!map.loaded() && String(event?.error||"").includes("style")){
      const fallback=document.getElementById("atlasFallback");
      if(fallback)fallback.classList.remove("hidden");
    }
  });
  }catch(error){
    const fallback=document.getElementById("atlasFallback");
    if(fallback)fallback.classList.remove("hidden");
  }
}
function addSources(){
  map.addSource("city-pins",{type:"geojson",data:emptyFC()});
  map.addLayer({id:"city-pins-glow",type:"circle",source:"city-pins",paint:{"circle-radius":14,"circle-color":"rgba(184,255,114,.08)","circle-blur":.5}});
  map.addLayer({id:"city-pins-core",type:"circle",source:"city-pins",paint:{"circle-radius":4,"circle-color":"#b8ff72","circle-stroke-width":1,"circle-stroke-color":"rgba(255,255,255,.65)"}});
  map.addSource("field",{type:"geojson",data:emptyFC()});
  map.addLayer({id:"field-heat",type:"heatmap",source:"field",maxzoom:14,paint:{
    "heatmap-weight":["get","weight"],"heatmap-intensity":1.15,"heatmap-radius":["interpolate",["linear"],["zoom"],4,34,11,78],"heatmap-opacity":.86,
    "heatmap-color":["interpolate",["linear"],["heatmap-density"],0,"rgba(0,0,0,0)",.25,"rgba(60,160,220,.15)",.5,"rgba(90,200,255,.45)",.75,"rgba(140,230,255,.7)",1,"rgba(245,252,255,.92)"]
  }});
  map.addSource("systems",{type:"geojson",data:emptyFC()});
  map.addLayer({id:"systems-points",type:"circle",source:"systems",paint:{
    "circle-radius":["match",["get","kind"],"health",5,"power",4,"bridge",3,3],
    "circle-color":["match",["get","kind"],"health","#f4f7f1","power","#ffd36a","bridge","#61ccff","#d3d9d1"],
    "circle-opacity":.9,"circle-stroke-width":1,"circle-stroke-color":"rgba(0,0,0,.55)"
  }});
  map.addSource("memory",{type:"geojson",data:emptyFC()});
  map.addLayer({id:"memory-rings",type:"circle",source:"memory",paint:{
    "circle-radius":["interpolate",["linear"],["zoom"],4,7,10,14],"circle-color":"rgba(0,0,0,0)","circle-stroke-width":2,
    "circle-stroke-color":["match",["get","alert"],"red","#ff786b","orange","#ffd36a","#b8ff72"],"circle-stroke-opacity":.72
  }});
  map.addSource("river-point",{type:"geojson",data:emptyFC()});
  map.addLayer({id:"river-glow",type:"circle",source:"river-point",paint:{"circle-radius":22,"circle-color":"rgba(85,170,255,.16)","circle-blur":.6}});
  map.addLayer({id:"river-core",type:"circle",source:"river-point",paint:{"circle-radius":6,"circle-color":"#55aaff","circle-stroke-width":2,"circle-stroke-color":"rgba(255,255,255,.7)"}});
  ["field-heat","systems-points","memory-rings","river-glow","river-core"].forEach(id=>setVisible(id,false));
  map.on("click","city-pins-core",e=>{const id=e.features?.[0]?.properties?.id;if(id)selectCity(id)});
  map.on("mouseenter","city-pins-core",()=>map.getCanvas().style.cursor="pointer");
  map.on("mouseleave","city-pins-core",()=>map.getCanvas().style.cursor="");
}
function setVisible(id,on){if(map.getLayer(id))map.setLayoutProperty(id,"visibility",on?"visible":"none")}
function renderCityPins(){
  const features=Object.entries(CITIES).map(([id,c])=>({type:"Feature",properties:{id,name:c.name},geometry:{type:"Point",coordinates:c.coords}}));
  map.getSource("city-pins")?.setData(fc(features));
}
function showWorld(animate=true){
  activeCity=null;activeLayer=null;
  document.body.dataset.mode="world";
  $("worldIntro").classList.remove("hidden");$("cityPanel").classList.add("hidden");$("layerDock").classList.add("hidden");$("timeline").classList.add("hidden");$("systemsLegend").classList.add("hidden");$("memoryStrip").classList.add("hidden");
  document.querySelectorAll("[data-city]").forEach(b=>b.classList.remove("active"));
  ["field-heat","systems-points","memory-rings","river-glow","river-core"].forEach(id=>setVisible(id,false));
  setVisible("city-pins-glow",true);setVisible("city-pins-core",true);
  map.setProjection({type:"globe"});
  map.flyTo({center:[88,24],zoom:1.25,pitch:0,bearing:0,duration:animate?1700:0,essential:true});
}
async function selectCity(id){
  const city=CITIES[id];if(!city)return;
  activeCity=id;
  $("worldIntro").classList.add("hidden");$("cityPanel").classList.remove("hidden");$("layerDock").classList.remove("hidden");
  document.querySelectorAll("[data-city]").forEach(b=>b.classList.toggle("active",b.dataset.city===id));
  setVisible("city-pins-glow",false);setVisible("city-pins-core",false);
  map.setProjection({type:"mercator"});
  map.flyTo({center:city.coords,zoom:city.zoom,pitch:city.pitch,bearing:city.bearing,duration:1800,essential:true});
  $("cityKicker").textContent=city.kicker;$("cityName").textContent=city.name;$("cityStory").textContent=city.story;$("contextCopy").textContent=city.context;
  $("primaryLabel").textContent="CONNECTING";$("primaryValue").textContent="—";$("primaryCopy").textContent="Loading live city state.";
  ["weatherHealth","airHealth","riverHealth","systemsHealth","memoryHealth"].forEach(id=>health(id,false,id.replace("Health","").toUpperCase()+" · …"));
  await ensureCityData(id);
  setLayer(city.defaultLayer);
}
async function ensureCityData(id){
  if(cache[id])return cache[id];
  const city=CITIES[id];const data={};
  cache[id]=data;
  await Promise.allSettled([
    loadWeather(id,city,data),loadAir(id,city,data),loadRiver(id,city,data),loadSystems(id,city,data),loadMemory(id,city,data)
  ]);
  renderBaseMetrics(id);
  return data;
}
async function loadWeather(id,city,data){
  const pts=gridAround(city,5,.8);
  const lats=pts.map(p=>p.lat.toFixed(4)).join(","),lons=pts.map(p=>p.lon.toFixed(4)).join(",");
  const vars="precipitation,apparent_temperature,soil_moisture_0_to_1cm";
  const url="https://api.open-meteo.com/v1/forecast?latitude="+encodeURIComponent(lats)+"&longitude="+encodeURIComponent(lons)+"&hourly="+vars+"&current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation&past_days=1&forecast_days=4&timezone=UTC";
  const raw=await getJson(url);const rows=Array.isArray(raw)?raw:[raw];
  data.weather=rows.map((r,i)=>({point:pts[i],hourly:r.hourly||{},current:r.current||{}}));
  data.weatherTimes=data.weather[0]?.hourly?.time||[];
  health("weatherHealth",true,"WEATHER · LIVE");
}
async function loadAir(id,city,data){
  const pts=gridAround(city,5,.8);
  const lats=pts.map(p=>p.lat.toFixed(4)).join(","),lons=pts.map(p=>p.lon.toFixed(4)).join(",");
  const url="https://air-quality-api.open-meteo.com/v1/air-quality?latitude="+encodeURIComponent(lats)+"&longitude="+encodeURIComponent(lons)+"&hourly=pm2_5,nitrogen_dioxide,ozone&current=pm2_5,pm10,nitrogen_dioxide,ozone&past_days=1&forecast_days=4&timezone=UTC";
  const raw=await getJson(url);const rows=Array.isArray(raw)?raw:[raw];
  data.air=rows.map((r,i)=>({point:pts[i],hourly:r.hourly||{},current:r.current||{}}));
  data.airTimes=data.air[0]?.hourly?.time||[];
  health("airHealth",true,"AIR · LIVE");
}
async function loadRiver(id,city,data){
  const url="https://flood-api.open-meteo.com/v1/flood?latitude="+city.river[1]+"&longitude="+city.river[0]+"&daily=river_discharge&past_days=7&forecast_days=7&timezone=UTC";
  const raw=await getJson(url);data.river=raw.daily||{};
  health("riverHealth",true,"RIVER · GLOFAS");
}
async function loadSystems(id,city,data){
  const [lon,lat]=city.coords;
  const q='[out:json][timeout:25];('+
    'nwr(around:16000,'+lat+','+lon+')[amenity~"^(hospital|clinic)$"];'+
    'nwr(around:16000,'+lat+','+lon+')[power="substation"];'+
    'nwr(around:16000,'+lat+','+lon+')[bridge="yes"];'+
  ');out center tags;';
  const body=new URLSearchParams({data:q});let raw=null;
  for(const endpoint of ["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter"]){
    try{raw=await getJson(endpoint,{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body});break}catch(e){}
  }
  if(!raw)throw new Error("Overpass unavailable");
  data.systems=(raw.elements||[]).map(el=>{
    const elat=el.lat??el.center?.lat,elon=el.lon??el.center?.lon,t=el.tags||{};if(elat==null||elon==null)return null;
    let kind="other";if(["hospital","clinic"].includes(t.amenity))kind="health";else if(t.power==="substation")kind="power";else if(t.bridge==="yes")kind="bridge";
    return {type:"Feature",properties:{kind,name:t.name||kind},geometry:{type:"Point",coordinates:[elon,elat]}};
  }).filter(Boolean);
  health("systemsHealth",true,"SYSTEMS · OSM");
}
async function fetchGdacs(){
  if(gdacsAll)return gdacsAll;
  const end=new Date(),start=new Date(end.getTime()-1000*60*60*24*365*3),iso=d=>d.toISOString().slice(0,10);
  const url="https://www.gdacs.org/gdacsapi/api/Events/geteventlist/SEARCH?eventlist=FL%3BTC%3BWF&fromdate="+iso(start)+"&todate="+iso(end)+"&alertlevel=green%3Borange%3Bred&pagesize=100&pagenumber=1";
  const raw=await getJson(url);gdacsAll=raw.features||raw.data||raw.events||[];return gdacsAll;
}
async function loadMemory(id,city,data){
  const raw=await fetchGdacs();
  data.memory=(raw||[]).map(item=>{
    const p=item.properties||item,c=item.geometry?.coordinates||[];const lon=Number(c[0]??p.longitude??p.lon),lat=Number(c[1]??p.latitude??p.lat);if(!Number.isFinite(lat)||!Number.isFinite(lon))return null;
    const dist=haversine(city.coords[1],city.coords[0],lat,lon);if(dist>350)return null;
    return {type:"Feature",properties:{name:p.name||p.eventname||p.title||"Historical event",alert:String(p.alertlevel||p.alertLevel||"").toLowerCase(),event_type:p.eventtype||p.eventType||"",start_date:String(p.fromdate||p.fromDate||p.startdate||"").slice(0,10),distance_km:Math.round(dist)},geometry:{type:"Point",coordinates:[lon,lat]}};
  }).filter(Boolean).slice(0,20);
  health("memoryHealth",true,"MEMORY · GDACS");
}
function renderBaseMetrics(id){
  if(id!==activeCity)return;const data=cache[id],city=CITIES[id];
  const centerW=data.weather?.[Math.floor((data.weather?.length||1)/2)]?.current||{};
  const centerA=data.air?.[Math.floor((data.air?.length||1)/2)]?.current||{};
  $("metricA").textContent=Number.isFinite(Number(centerW.temperature_2m))?fmt(centerW.temperature_2m)+"°":"—";
  $("metricB").textContent=Number.isFinite(Number(centerW.precipitation))?fmt(centerW.precipitation)+" mm":"—";
  $("metricC").textContent=Number.isFinite(Number(centerA.pm2_5))?fmt(centerA.pm2_5,0)+" PM₂.₅":"—";
}
function setLayer(layer){
  activeLayer=layer;
  document.querySelectorAll("[data-layer]").forEach(b=>b.classList.toggle("active",b.dataset.layer===layer));
  ["field-heat","systems-points","memory-rings","river-glow","river-core"].forEach(id=>setVisible(id,false));
  $("timeline").classList.add("hidden");$("systemsLegend").classList.add("hidden");$("memoryStrip").classList.add("hidden");$("riverCard").classList.add("hidden");
  if(["rain","heat","wetness","air"].includes(layer)){setVisible("field-heat",true);renderTemporalLayer(layer)}
  if(layer==="river"){setVisible("river-glow",true);setVisible("river-core",true);renderRiver()}
  if(layer==="systems"){setVisible("systems-points",true);renderSystems()}
  if(layer==="memory"){setVisible("memory-rings",true);renderMemory()}
}
function setVisible(id,on){if(map.getLayer(id))map.setLayoutProperty(id,"visibility",on?"visible":"none")}
function temporalDataset(layer){
  const data=cache[activeCity];if(layer==="air")return {rows:data.air||[],times:data.airTimes||[],key:"pm2_5"};
  const key=layer==="rain"?"precipitation":layer==="heat"?"apparent_temperature":"soil_moisture_0_to_1cm";
  return {rows:data.weather||[],times:data.weatherTimes||[],key};
}
function renderTemporalLayer(layer,index){
  const ds=temporalDataset(layer);if(!ds.times.length)return;
  const now=Date.now();let i=index;
  if(i==null)i=ds.times.reduce((best,t,k)=>Math.abs(new Date(t+"Z").getTime()-now)<Math.abs(new Date(ds.times[best]+"Z").getTime()-now)?k:best,0);
  i=Math.max(0,Math.min(ds.times.length-1,i));
  const values=ds.rows.map(r=>Number(r.hourly?.[ds.key]?.[i])).filter(Number.isFinite);
  const min=Math.min(...values),max=Math.max(...values),span=Math.max(.0001,max-min);
  const features=ds.rows.map(r=>{const value=Number(r.hourly?.[ds.key]?.[i]);return {type:"Feature",properties:{value,weight:Number.isFinite(value)?Math.max(.02,(value-min)/span):0},geometry:{type:"Point",coordinates:[r.point.lon,r.point.lat]}}}).filter(f=>Number.isFinite(f.properties.value));
  map.getSource("field")?.setData(fc(features));
  applyFieldStyle(layer);
  const style=FIELD_STYLES[layer],avg=values.reduce((a,b)=>a+b,0)/(values.length||1);
  $("primaryLabel").textContent=style.label;$("primaryValue").textContent=(layer==="wetness"?fmt(avg,2):fmt(avg,1))+" "+style.unit;
  $("primaryCopy").textContent=layer==="rain"?"Average across the visible forecast grid.":layer==="heat"?"Average apparent temperature across the city grid.":layer==="wetness"?"Near-surface modeled soil moisture.":"Average modeled PM2.5 across the city grid.";
  $("timeline").classList.remove("hidden");$("timelineLayer").textContent=style.label;$("timelineTime").textContent=new Date(ds.times[i]+"Z").toLocaleString([], {weekday:"short",hour:"2-digit",minute:"2-digit"});$("timelineValue").textContent=(layer==="wetness"?fmt(max,2):fmt(max,1))+" "+style.unit+" peak";
  const slider=$("timeSlider");slider.max=ds.times.length-1;slider.value=i;slider.oninput=()=>renderTemporalLayer(layer,Number(slider.value));
}
function applyFieldStyle(layer){
  const stops=FIELD_STYLES[layer].colorStops;const expr=["interpolate",["linear"],["heatmap-density"]];stops.forEach(([v,c])=>expr.push(v,c));map.setPaintProperty("field-heat","heatmap-color",expr);
}
function renderRiver(){
  const city=CITIES[activeCity],data=cache[activeCity],times=data.river?.time||[],vals=data.river?.river_discharge||[];
  map.getSource("river-point")?.setData(fc([{type:"Feature",properties:{},geometry:{type:"Point",coordinates:city.river}}]));
  $("riverCard").classList.remove("hidden");
  const valid=vals.map(Number).filter(Number.isFinite),mid=Math.min(7,valid.length-1),current=valid[mid]??valid[0];
  $("primaryLabel").textContent="RIVER";$("primaryValue").textContent=Number.isFinite(current)?human(current)+" m³/s":"—";$("primaryCopy").textContent="GloFAS simulated discharge at the selected river grid cell.";
  $("riverNow").textContent=Number.isFinite(current)?human(current)+" m³/s":"—";$("riverRange").textContent=valid.length?"7d past → 7d forecast":"No river series";
  renderSpark(valid);
}
function renderSpark(vals){
  const svg=$("riverSpark");if(!vals.length){svg.innerHTML="";return}const w=320,h=70,min=Math.min(...vals),max=Math.max(...vals),span=Math.max(1,max-min);
  const pts=vals.map((v,i)=>[(i/(vals.length-1||1))*w,h-8-((v-min)/span)*(h-16)]);
  const d=pts.map((p,i)=>(i?"L":"M")+p[0].toFixed(1)+" "+p[1].toFixed(1)).join(" ");
  svg.innerHTML='<path d="'+d+'" fill="none" stroke="#61ccff" stroke-width="2"/><line x1="'+((Math.min(7,vals.length-1)/(vals.length-1||1))*w).toFixed(1)+'" x2="'+((Math.min(7,vals.length-1)/(vals.length-1||1))*w).toFixed(1)+'" y1="0" y2="70" stroke="rgba(255,255,255,.16)" stroke-dasharray="3 4"/>';
}
function renderSystems(){
  const systems=cache[activeCity].systems||[];map.getSource("systems")?.setData(fc(systems));
  const h=systems.filter(x=>x.properties.kind==="health").length,b=systems.filter(x=>x.properties.kind==="bridge").length,p=systems.filter(x=>x.properties.kind==="power").length;
  $("healthCount").textContent=h;$("bridgeCount").textContent=b;$("powerCount").textContent=p;$("systemsLegend").classList.remove("hidden");
  $("primaryLabel").textContent="SYSTEMS";$("primaryValue").textContent=human(systems.length)+" mapped";$("primaryCopy").textContent="Hospitals/clinics, bridges and power substations within roughly 16 km.";
}
function renderMemory(){
  const mem=cache[activeCity].memory||[];map.getSource("memory")?.setData(fc(mem));$("memoryStrip").classList.remove("hidden");
  $("memoryStrip").innerHTML=mem.slice(0,8).map(e=>'<div class="memory-chip"><strong>'+e.properties.name+'</strong><small>'+e.properties.start_date+' · '+e.properties.distance_km+' km · '+(e.properties.alert||"unknown")+'</small></div>').join("")||'<div class="memory-chip"><strong>No nearby events loaded</strong><small>GDACS · last 3 years</small></div>';
  $("primaryLabel").textContent="MEMORY";$("primaryValue").textContent=mem.length+" events";$("primaryCopy").textContent="Flood, cyclone and wildfire events within 350 km in the loaded GDACS window.";
}
function bindUI(){
  document.querySelectorAll("[data-city]").forEach(b=>b.addEventListener("click",()=>selectCity(b.dataset.city)));
  document.querySelectorAll("[data-layer]").forEach(b=>b.addEventListener("click",()=>setLayer(b.dataset.layer)));
  $("worldButton").addEventListener("click",()=>showWorld());
}
initMap();bindUI();
