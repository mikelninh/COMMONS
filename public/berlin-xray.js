(() => {
  'use strict';

  const M=window.Meaning;
  const E=window.MeaningEngine;
  const $=M.$;
  const X=window.BerlinXray={
    mode:'live',time:1,ready:false,point:{lon:13.405,lat:52.52},
    cache:{},typeCache:{},active:false
  };

  const BBOX={west:13.08,south:52.34,east:13.78,north:52.70};
  const fc=features=>({type:'FeatureCollection',features:features||[]});
  const cloneFeature=(f,type)=>({type:'Feature',properties:{...(f.properties||{}),_xrayType:type},geometry:f.geometry});
  const setText=(id,value)=>{const el=$(id);if(el)el.textContent=value};
  const safePaint=(id,prop,value)=>{try{if(M.map?.getLayer(id))M.map.setPaintProperty(id,prop,value)}catch{}};
  const show=(id,on)=>{try{if(M.map?.getLayer(id))M.map.setLayoutProperty(id,'visibility',on?'visible':'none')}catch{}};
  const source=(id,data)=>{try{M.map?.getSource(id)?.setData(data)}catch{}};

  const CONFIG={
    live:{
      title:'Berlin is happening now.',
      copy:'Movement, weather and air become one live surface. Move vertically through −12h, now and +12h.',
      labels:['−12H','NOW','+12H']
    },
    people:{
      title:'Where Berlin lives.',
      copy:'Population density, environmental burden and care infrastructure reveal how unevenly the city is experienced.',
      labels:['2024 BASE','NOW','NO MODEL']
    },
    nature:{
      title:'Where the city breathes.',
      copy:'Green space, trees and heat structure become visible together. The future adds a +12h weather field where available.',
      labels:['CLIMATE BASE','NOW','+12H']
    },
    infra:{
      title:'The city’s supporting skeleton.',
      copy:'Transit movement, hospitals and public sports infrastructure show how the city supports everyday life.',
      labels:['NO TAPE','NOW','STRUCTURE']
    },
    history:{
      title:'The city underneath the city.',
      copy:'Building-age context and the 1989 Wall turn the current map into a palimpsest.',
      labels:['BUILT / 1989','TRACES NOW','—']
    }
  };

  function gridPoints(){
    const pts=[];
    for(let y=0;y<5;y++)for(let x=0;x<5;x++){
      pts.push({lat:BBOX.south+(y/4)*(BBOX.north-BBOX.south),lon:BBOX.west+(x/4)*(BBOX.east-BBOX.west)});
    }
    return pts;
  }

  async function weatherGrid(){
    if(X.cache.weather)return X.cache.weather;
    const pts=gridPoints();
    const lats=pts.map(p=>p.lat.toFixed(4)).join(','),lons=pts.map(p=>p.lon.toFixed(4)).join(',');
    const url='https://api.open-meteo.com/v1/forecast?latitude='+encodeURIComponent(lats)+'&longitude='+encodeURIComponent(lons)+'&hourly=temperature_2m,pm10&current=temperature_2m&past_hours=13&forecast_hours=13&timezone=Europe%2FBerlin';
    const raw=await M.getJSON(url,12000);
    const rows=(Array.isArray(raw)?raw:[raw]).map((r,i)=>({point:pts[i],current:r.current||{},hourly:r.hourly||{}}));
    X.cache.weather=rows;return rows;
  }

  function nearestIndex(times,targetMs){
    if(!times?.length)return 0;
    let best=0,delta=Infinity;
    times.forEach((t,i)=>{const d=Math.abs(new Date(t).getTime()-targetMs);if(d<delta){best=i;delta=d}});
    return best;
  }

  async function renderWeather(time){
    const rows=await weatherGrid(),times=rows[0]?.hourly?.time||[];
    const target=Date.now()+(time===0?-12:time===2?12:0)*3600000;
    const index=nearestIndex(times,target);
    const vals=rows.map(r=>Number(r.hourly?.temperature_2m?.[index])).filter(Number.isFinite);
    const min=Math.min(...vals),max=Math.max(...vals),span=Math.max(.1,max-min);
    const features=rows.map(r=>{
      const value=Number(r.hourly?.temperature_2m?.[index]);
      if(!Number.isFinite(value))return null;
      return {type:'Feature',properties:{value,weight:Math.max(.05,(value-min)/span)},geometry:{type:'Point',coordinates:[r.point.lon,r.point.lat]}};
    }).filter(Boolean);
    source('xray-heat',fc(features));show('xray-heat-layer',true);
    const avg=vals.reduce((a,b)=>a+b,0)/(vals.length||1);
    setText('xrayReadoutValue',M.fmt(avg,1)+' °C');
    setText('xrayReadoutMeta',(time===0?'Modeled Berlin field ~12h ago':time===2?'Modeled Berlin field ~12h ahead':'Modeled Berlin field now')+' · '+M.fmt(min,1)+'–'+M.fmt(max,1)+' °C');
    return {avg,min,max,time:times[index]};
  }

  async function transit(){
    if(X.cache.transit&&Date.now()-X.cache.transit.at<120000)return X.cache.transit.features;
    const url=`https://v6.vbb.transport.rest/radar?north=${BBOX.north}&west=${BBOX.west}&south=${BBOX.south}&east=${BBOX.east}&results=600&duration=30`;
    const raw=await M.getJSON(url,10000),moves=raw.movements||raw||[];
    const features=(Array.isArray(moves)?moves:[]).map(m=>{
      const loc=m.location||m.currentLocation||{},lat=Number(loc.latitude),lon=Number(loc.longitude);
      if(!Number.isFinite(lat)||!Number.isFinite(lon))return null;
      return {type:'Feature',properties:{mode:String(m.line?.product||m.line?.mode||'other'),line:m.line?.name||''},geometry:{type:'Point',coordinates:[lon,lat]}};
    }).filter(Boolean);
    X.cache.transit={at:Date.now(),features};return features;
  }

  async function featureType(endpoint,patterns){
    if(X.typeCache[endpoint])return X.typeCache[endpoint];
    const raw=await M.getText(endpoint+'?service=WFS&request=GetCapabilities',9000);
    const doc=new DOMParser().parseFromString(raw,'text/xml');
    const types=[...doc.querySelectorAll('FeatureType > Name, FeatureType Name')].map(n=>n.textContent.trim()).filter(Boolean);
    const type=types.find(t=>(patterns||[]).some(p=>p.test(t)))||types[0];
    if(!type)throw Error('No WFS feature type');
    X.typeCache[endpoint]=type;return type;
  }

  async function wfs(endpoint,patterns,point,radius=.055,count=350){
    const type=await featureType(endpoint,patterns),dy=radius*.72;
    const params=new URLSearchParams({
      service:'WFS',version:'2.0.0',request:'GetFeature',typeNames:type,outputFormat:'application/json',srsName:'EPSG:4326',count:String(count),
      bbox:`${point.lon-radius},${point.lat-dy},${point.lon+radius},${point.lat+dy},EPSG:4326`
    });
    const raw=await M.getJSON(endpoint+'?'+params.toString(),11000);
    return Array.isArray(raw.features)?raw.features:[];
  }

  async function loadWfsSet(key,defs){
    const cacheKey=key+':'+X.point.lon.toFixed(3)+':'+X.point.lat.toFixed(3);
    if(X.cache[cacheKey])return X.cache[cacheKey];
    const settled=await Promise.allSettled(defs.map(async d=>{
      const features=await wfs(d.endpoint,d.patterns,X.point,d.radius||.055,d.count||350);
      return features.map(f=>cloneFeature(f,d.type));
    }));
    const features=settled.flatMap(r=>r.status==='fulfilled'?r.value:[]);
    X.cache[cacheKey]=features;return features;
  }

  function clear(){
    ['xray-area-layer','xray-line-layer','xray-point-layer','xray-transit-layer','xray-heat-layer'].forEach(id=>show(id,false));
    source('xray-area',fc());source('xray-line',fc());source('xray-point',fc());source('xray-transit',fc());source('xray-heat',fc());
  }

  function splitGeometry(features){
    const area=[],line=[],point=[];
    for(const f of features){
      const type=f.geometry?.type||'';
      if(type.includes('Polygon'))area.push(f);
      else if(type.includes('Line'))line.push(f);
      else point.push(f);
    }
    return {area,line,point};
  }

  function renderGeo(features,style){
    const g=splitGeometry(features);
    source('xray-area',fc(g.area));source('xray-line',fc(g.line));source('xray-point',fc(g.point));
    show('xray-area-layer',g.area.length>0);show('xray-line-layer',g.line.length>0);show('xray-point-layer',g.point.length>0);
    if(style?.area)safePaint('xray-area-layer','fill-color',style.area);
    if(style?.areaOpacity!=null)safePaint('xray-area-layer','fill-opacity',style.areaOpacity);
    if(style?.line)safePaint('xray-line-layer','line-color',style.line);
    if(style?.point)safePaint('xray-point-layer','circle-color',style.point);
  }

  async function renderLive(time){
    const weather=await renderWeather(time);
    if(time===1){
      try{
        const vehicles=await transit();source('xray-transit',fc(vehicles));show('xray-transit-layer',vehicles.length>0);
        setText('xrayReadoutMeta',`${vehicles.length} live VBB vehicles · modeled temperature ${M.fmt(weather.avg,1)} °C`);
      }catch{setText('xrayReadoutMeta','VBB unavailable · weather field remains visible')}
    }
    setText('xrayTitle',time===0?'Berlin, twelve hours ago.':time===2?'Berlin, twelve hours from now.':'Berlin is moving right now.');
    setText('xrayCopy',time===1?'Weather is a modeled field; transit points are live VBB movement.':time===0?'This is the modeled atmospheric past, not reconstructed human movement.':'This is a weather forecast. We do not invent future transit movement.');
  }

  async function renderPeople(time){
    const defs=[
      {type:'population',endpoint:'https://gdi.berlin.de/services/wfs/ua_einwohnerdichte_2024',patterns:[/einwohner/i,/dichte/i]},
      {type:'justice',endpoint:'https://gdi.berlin.de/services/wfs/ua_umweltgerechtigkeit2023',patterns:[/umwelt/i,/gerecht/i,/belast/i]},
      {type:'hospital',endpoint:'https://gdi.berlin.de/services/wfs/krankenhaeuser',patterns:[/kranken/i,/hospital/i],radius:.08,count:180}
    ];
    if(time===2){
      setText('xrayTitle','We do not have a trustworthy future population layer yet.');
      setText('xrayCopy','Deep City leaves this future blank rather than turning planning assumptions into reality.');
      setText('xrayReadoutValue','NO MODEL');setText('xrayReadoutMeta','Future people-state intentionally unavailable.');return;
    }
    const features=await loadWfsSet('people',defs);renderGeo(features,{area:['match',['get','_xrayType'],'population','#73d8ff','justice','#c49cff','#8aa88b'],areaOpacity:.19,point:'#f5f8f4'});
    setText('xrayTitle',time===0?'Berlin’s population baseline.':'People are not evenly distributed.');
    setText('xrayCopy',time===0?'2024 population density and recent environmental-justice structure form the baseline.':'Population, burden context and nearby care infrastructure overlap here.');
    setText('xrayReadoutValue',features.length+' features');setText('xrayReadoutMeta','Population + environmental justice + hospitals · official Berlin WFS');
  }

  async function renderNature(time){
    const defs=[
      {type:'green',endpoint:'https://gdi.berlin.de/services/wfs/gruenanlagen',patterns:[/gruen/i,/anlage/i],count:350},
      {type:'trees',endpoint:'https://gdi.berlin.de/services/wfs/baumbestand',patterns:[/baum/i],radius:.035,count:700},
      {type:'heat',endpoint:'https://gdi.berlin.de/services/wfs/ua_klimaanalyse_2022',patterns:[/klima/i,/therm/i,/pet/i,/utci/i],count:300}
    ];
    const features=await loadWfsSet('nature',defs);
    renderGeo(features,{area:['match',['get','_xrayType'],'green','#70df86','heat','#ff8d7f','#76b987'],areaOpacity:.2,point:'#9df56d'});
    if(time===2){
      await renderWeather(2);
      setText('xrayTitle','Tomorrow’s atmosphere meets today’s green structure.');
      setText('xrayCopy','The +12h temperature field is forecast; green, trees and heat-analysis context remain structural.');
    }else{
      setText('xrayTitle',time===0?'The climate structure underneath today.':'Where Berlin can breathe.');
      setText('xrayCopy',time===0?'Official heat analysis is a planning baseline, not a historical weather observation.':'Green space, mapped trees and heat-analysis context become one physical layer.');
      setText('xrayReadoutValue',features.length+' features');setText('xrayReadoutMeta','Green + trees + heat analysis · official Berlin WFS');
    }
  }

  async function renderInfra(time){
    const defs=[
      {type:'hospital',endpoint:'https://gdi.berlin.de/services/wfs/krankenhaeuser',patterns:[/kranken/i,/hospital/i],radius:.09,count:180},
      {type:'sport',endpoint:'https://gdi.berlin.de/services/wfs/sportstandorte',patterns:[/sport/i,/standort/i],radius:.09,count:220}
    ];
    const features=await loadWfsSet('infra',defs);renderGeo(features,{point:['match',['get','_xrayType'],'hospital','#f4f7f1','sport','#ffd06a','#9df56d']});
    if(time===1){
      try{const vehicles=await transit();source('xray-transit',fc(vehicles));show('xray-transit-layer',vehicles.length>0);setText('xrayReadoutValue',vehicles.length+' moving');setText('xrayReadoutMeta',features.length+' structural facilities nearby · VBB live now')}
      catch{setText('xrayReadoutValue',features.length+' facilities');setText('xrayReadoutMeta','Live transit unavailable · structural infrastructure remains')}
      setText('xrayTitle','The city’s supporting skeleton is active.');
      setText('xrayCopy','Live movement sits on top of hospitals and public sports infrastructure.');
    }else if(time===0){
      setText('xrayTitle','Infrastructure memory is still thin.');
      setText('xrayCopy','We have current infrastructure geometry, but no trustworthy historical tape for these facilities yet.');
      setText('xrayReadoutValue','NO TAPE');setText('xrayReadoutMeta','Current facilities shown as reference only.');
    }else{
      setText('xrayTitle','Structure persists. Movement does not.');
      setText('xrayCopy','Hospitals and sports facilities remain mapped; Deep City does not forecast future VBB movement yet.');
      setText('xrayReadoutValue',features.length+' facilities');setText('xrayReadoutMeta','Structure only · no invented movement forecast.');
    }
  }

  async function renderHistory(time){
    const defs=[
      {type:'buildingAge',endpoint:'https://gdi.berlin.de/services/wfs/ua_gebaeudealter',patterns:[/gebaeude/i,/alter/i,/bau/i],count:320},
      {type:'wall',endpoint:'https://gdi.berlin.de/services/wfs/berlinermauer',patterns:[/mauer/i,/grenz/i],radius:.08,count:300}
    ];
    if(time===2){
      setText('xrayTitle','History has no future layer.');
      setText('xrayCopy','Move back down the time axis to read the traces that still shape Berlin.');
      setText('xrayReadoutValue','—');setText('xrayReadoutMeta','No synthetic future history.');return;
    }
    const features=await loadWfsSet('history',defs);
    renderGeo(features,{area:'#9d7bb6',areaOpacity:time===0?.22:.09,line:'#ffd06a',point:'#c49cff'});
    setText('xrayTitle',time===0?'Berlin before the present map.':'Old Berlin still leaks through.');
    setText('xrayCopy',time===0?'Residential building-age context and the 1989 Wall are pulled forward over today’s geography.':'Historical geometry becomes a ghost layer against the current city.');
    setText('xrayReadoutValue',features.length+' traces');setText('xrayReadoutMeta','Building-age context + 1989 Wall · historical/structural evidence');
  }

  X.render=async()=>{
    if(!X.ready||!X.active)return;
    clear();
    document.body.classList.remove('xray-live','xray-people','xray-nature','xray-infra','xray-history','xray-past','xray-future');
    document.body.classList.add('xray-'+X.mode);
    if(X.time===0)document.body.classList.add('xray-past');
    if(X.time===2)document.body.classList.add('xray-future');
    const cfg=CONFIG[X.mode],labels=cfg.labels;
    setText('xrayKicker','CITY X-RAY · '+X.mode.toUpperCase());
    setText('xrayTimeBottom',labels[0]);setText('xrayTimeNow',labels[1]);setText('xrayTimeTop',labels[2]);
    setText('xrayReadoutLabel',X.mode.toUpperCase()+' / '+labels[X.time]);
    setText('xrayReadoutValue','…');setText('xrayReadoutMeta','Reading this layer of Berlin…');
    setText('xrayTitle',cfg.title);setText('xrayCopy',cfg.copy);
    try{
      if(X.mode==='live')await renderLive(X.time);
      else if(X.mode==='people')await renderPeople(X.time);
      else if(X.mode==='nature')await renderNature(X.time);
      else if(X.mode==='infra')await renderInfra(X.time);
      else if(X.mode==='history')await renderHistory(X.time);
    }catch(error){
      setText('xrayReadoutValue','PARTIAL');
      setText('xrayReadoutMeta','One or more sources did not answer. The map keeps only readable evidence.');
    }
  };

  X.setMode=mode=>{
    X.mode=mode;
    M.qsa('[data-xray]').forEach(b=>b.classList.toggle('active',b.dataset.xray===mode));
    X.render();
  };
  X.setTime=value=>{X.time=Number(value);X.render()};

  X.activate=point=>{
    if(point)X.point=point;
    X.active=true;
    $('meaningHero').classList.add('hidden');
    $('meaningPanel').classList.add('hidden');
    $('xrayStage').classList.remove('hidden');
    X.render();
  };
  X.deactivate=()=>{
    X.active=false;$('xrayStage').classList.add('hidden');clear();
    document.body.classList.remove('xray-live','xray-people','xray-nature','xray-infra','xray-history','xray-past','xray-future');
  };

  function addLayers(){
    const map=M.map;
    for(const id of ['xray-heat','xray-area','xray-line','xray-point','xray-transit']){
      if(!map.getSource(id))map.addSource(id,{type:'geojson',data:fc()});
    }
    if(!map.getLayer('xray-heat-layer'))map.addLayer({id:'xray-heat-layer',type:'heatmap',source:'xray-heat',paint:{
      'heatmap-weight':['coalesce',['get','weight'],.4],'heatmap-intensity':1.2,'heatmap-radius':['interpolate',['linear'],['zoom'],8,35,13,85],
      'heatmap-opacity':.72,'heatmap-color':['interpolate',['linear'],['heatmap-density'],0,'rgba(0,0,0,0)',.2,'rgba(76,137,200,.12)',.48,'rgba(115,216,255,.42)',.72,'rgba(255,208,106,.64)',1,'rgba(255,141,127,.9)']
    }});
    if(!map.getLayer('xray-area-layer'))map.addLayer({id:'xray-area-layer',type:'fill',source:'xray-area',paint:{'fill-color':'#9df56d','fill-opacity':.2,'fill-outline-color':'rgba(255,255,255,.12)'}});
    if(!map.getLayer('xray-line-layer'))map.addLayer({id:'xray-line-layer',type:'line',source:'xray-line',paint:{'line-color':'#ffd06a','line-width':['interpolate',['linear'],['zoom'],9,1.4,13,3],'line-opacity':.9}});
    if(!map.getLayer('xray-point-layer'))map.addLayer({id:'xray-point-layer',type:'circle',source:'xray-point',paint:{'circle-radius':['interpolate',['linear'],['zoom'],9,3,13,5.5],'circle-color':'#9df56d','circle-opacity':.88,'circle-stroke-width':1,'circle-stroke-color':'rgba(0,0,0,.55)'}});
    if(!map.getLayer('xray-transit-layer'))map.addLayer({id:'xray-transit-layer',type:'circle',source:'xray-transit',paint:{'circle-radius':['interpolate',['linear'],['zoom'],8,2.2,12,4.3],'circle-color':'#73d8ff','circle-opacity':.82,'circle-stroke-width':.7,'circle-stroke-color':'rgba(0,0,0,.6)'}});
    clear();X.ready=true;
  }

  async function init(){
    await M.ready;
    if(M.map?.loaded?.())addLayers();
    else M.map?.once('load',addLayers);

    M.qsa('[data-xray]').forEach(b=>b.addEventListener('click',()=>X.setMode(b.dataset.xray)));
    $('xrayTimeSlider').addEventListener('input',e=>X.setTime(e.target.value));
    $('toolXray').addEventListener('click',()=>X.activate(M.point||{lon:13.405,lat:52.52}));
    $('openMeaningDetails').addEventListener('click',()=>{$('meaningPanel').classList.remove('hidden')});
  }

  init();
})();