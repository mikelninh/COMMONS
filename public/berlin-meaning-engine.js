(() => {
  'use strict';

  const M=window.Meaning,$=M.$;
  const SOURCES=window.BERLIN_MEANING_SOURCES||{};
  const PERSONAS=window.BERLIN_MEANING_PERSONAS||{};
  const E=window.MeaningEngine={featureTypes:{},pulse:null,allCandidates:[],queryToken:0};

  const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
  const rad=d=>d*Math.PI/180;
  const haversine=(a,b)=>{
    const R=6371000,dLat=rad(b.lat-a.lat),dLon=rad(b.lon-a.lon);
    const x=Math.sin(dLat/2)**2+Math.cos(rad(a.lat))*Math.cos(rad(b.lat))*Math.sin(dLon/2)**2;
    return 2*R*Math.asin(Math.sqrt(x));
  };
  const coordsOf=geometry=>{
    const out=[];
    (function walk(v){
      if(!Array.isArray(v))return;
      if(v.length>=2&&typeof v[0]==='number'&&typeof v[1]==='number')out.push({lon:Number(v[0]),lat:Number(v[1])});
      else v.forEach(walk);
    })(geometry?.coordinates);
    return out.filter(p=>M.finite(p.lon)&&M.finite(p.lat));
  };
  const nearestGeometry=(feature,point)=>{
    const coords=coordsOf(feature?.geometry);
    if(!coords.length)return {distance:null,focus:null};
    let best={distance:Infinity,focus:null};
    for(const c of coords){const d=haversine(point,c);if(d<best.distance)best={distance:d,focus:c}}
    return best;
  };
  const prop=(obj,patterns)=>{
    const entries=Object.entries(obj||{});
    for(const pattern of patterns){
      const hit=entries.find(([k,v])=>pattern.test(String(k))&&v!==null&&v!==undefined&&String(v).trim());
      if(hit)return String(hit[1]).trim();
    }
    return null;
  };
  const ageText=props=>prop(props,[/bau.*alter/i,/alter.*klasse/i,/dekad/i,/zeit.*raum/i,/jahr/i,/age/i]);
  const greenType=props=>prop(props,[/objartname/i,/obj.*art/i,/art.*gruen/i,/bezeich/i,/name/i]);
  const placeName=props=>prop(props,[/name/i,/bezeich/i,/standort/i,/einrichtung/i,/adresse/i]);

  E.loadPulse=async()=>{
    if(E.pulse)return E.pulse;
    try{E.pulse=await M.getJSON('./data/berlin-pulse/latest.json?t='+Date.now(),7000)}catch{E.pulse={}}
    return E.pulse;
  };

  E.featureType=async key=>{
    if(E.featureTypes[key])return E.featureTypes[key];
    const s=SOURCES[key];if(!s?.endpoint)throw Error('no endpoint');
    const raw=await M.getText(s.endpoint+'?service=WFS&request=GetCapabilities',8000);
    const doc=new DOMParser().parseFromString(raw,'text/xml');
    const types=[...doc.querySelectorAll('FeatureType > Name, FeatureType Name')].map(n=>n.textContent.trim()).filter(Boolean);
    const chosen=types.find(type=>(s.patterns||[]).some(p=>p.test(type)))||types[0];
    if(!chosen)throw Error('no feature type');
    E.featureTypes[key]=chosen;return chosen;
  };

  E.wfs=async(key,point,radius=.012)=>{
    const s=SOURCES[key],type=await E.featureType(key);
    const dy=radius*.72,params=new URLSearchParams({
      service:'WFS',version:'2.0.0',request:'GetFeature',typeNames:type,outputFormat:'application/json',srsName:'EPSG:4326',
      count:'180',bbox:`${point.lon-radius},${point.lat-dy},${point.lon+radius},${point.lat+dy},EPSG:4326`
    });
    const raw=await M.getJSON(s.endpoint+'?'+params.toString(),8000);
    return {features:Array.isArray(raw.features)?raw.features:[],type};
  };

  E.liveWeather=async point=>{
    const url=`https://api.open-meteo.com/v1/forecast?latitude=${point.lat}&longitude=${point.lon}&current=temperature_2m,apparent_temperature,precipitation,wind_speed_10m&timezone=UTC`;
    const raw=await M.getJSON(url,7000);return raw.current||{};
  };
  E.liveAir=async point=>{
    const url=`https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${point.lat}&longitude=${point.lon}&current=pm2_5,nitrogen_dioxide,ozone&timezone=UTC`;
    const raw=await M.getJSON(url,7000);return raw.current||{};
  };
  E.liveTransit=async point=>{
    const d=.016,url=`https://v6.vbb.transport.rest/radar?north=${point.lat+d}&west=${point.lon-d}&south=${point.lat-d}&east=${point.lon+d}&results=220&duration=30`;
    const raw=await M.getJSON(url,7000);const a=raw.movements||raw||[];return Array.isArray(a)?a:[];
  };

  E.candidate=(key,overrides={})=>{
    const s=SOURCES[key];
    return {
      id:key,lens:s.lens,kind:s.kind,sourceKey:key,source:s.source,
      confidence:s.confidence,freshness:s.freshness,utility:s.utility,surprise:s.surprise,
      specificity:.72,distanceM:null,focus:null,...overrides
    };
  };

  E.fromWeather=(current,pulse)=>{
    if(!M.finite(current.temperature_2m))return null;
    const t=Number(current.temperature_2m),city=pulse?.signals?.temperature_2m?.value;
    const delta=M.finite(city)?t-Number(city):null;
    const meaningful=M.finite(delta)&&Math.abs(delta)>=.4;
    return E.candidate('weather',{
      title:meaningful?`This point is ${Math.abs(delta).toFixed(1)}°C ${delta>0?'warmer':'cooler'} than the city pulse.`:`It is ${t.toFixed(1)}°C here right now.`,
      body:`Modeled temperature at this point. ${M.finite(current.apparent_temperature)?'Feels like '+Number(current.apparent_temperature).toFixed(1)+'°C.':''}`,
      specificity:meaningful?.95:.68,surpriseBoost:meaningful?.78:.35
    });
  };
  E.fromAir=(current,pulse)=>{
    if(!M.finite(current.pm2_5))return null;
    const v=Number(current.pm2_5),city=pulse?.signals?.pm2_5?.value,delta=M.finite(city)?v-Number(city):null;
    const meaningful=M.finite(delta)&&Math.abs(delta)>=.6;
    return E.candidate('air',{
      title:meaningful?`Modeled PM2.5 is ${Math.abs(delta).toFixed(1)} µg/m³ ${delta>0?'higher':'lower'} than the city pulse.`:`Modeled PM2.5 here is ${v.toFixed(1)} µg/m³.`,
      body:'CAMS modeled air context at the selected point; this is not a local measurement station.',
      specificity:meaningful?.92:.62,surpriseBoost:meaningful?.72:.34
    });
  };
  E.fromTransit=vehicles=>E.candidate('transit',{
    title:vehicles.length?`${vehicles.length} live public-transport vehicles are moving nearby.`:'No live VBB vehicles were returned nearby.',
    body:'Vehicles returned by the VBB realtime radar in a small local box. Movement is not the same as punctuality.',
    specificity:.88,surpriseBoost:vehicles.length>70?.7:.4
  });

  E.fromWfs=(key,result,point)=>{
    const features=result?.features||[];if(!features.length)return null;
    const nearest=features.map(f=>({...nearestGeometry(f,point),feature:f})).filter(x=>M.finite(x.distance)).sort((a,b)=>a.distance-b.distance)[0];
    const near=nearest?.distance??null,focus=nearest?.focus??null,first=nearest?.feature||features[0],props=first?.properties||{};
    if(key==='wall')return E.candidate(key,{
      title:M.finite(near)?`The 1989 Wall ran about ${near<1000?Math.max(10,Math.round(near/10)*10)+' m':(near/1000).toFixed(1)+' km'} from here.`:'The 1989 Wall route crosses this local context.',
      body:'Historical border geometry digitized from the 1989 installations. Approximate distance is to returned geometry vertices.',
      distanceM:near,focus,specificity:.98,surpriseBoost:M.finite(near)&&near<600?1:.72
    });
    if(key==='buildingAge'){
      const age=ageText(props);
      return E.candidate(key,{
        title:age?`The residential fabric here is mapped mainly as ${age}.`:'Berlin’s building-age map covers this block.',
        body:'Dominant residential building-age class from an older Umweltatlas block dataset. Treat this as structural history, not a current building survey.',
        distanceM:near,focus,specificity:age?.94:.55,surpriseBoost:age?.88:.48
      });
    }
    if(key==='trees')return E.candidate(key,{
      title:`${features.length} mapped tree features appear in the local context.`,
      body:'Official tree features returned around this point. Count does not equal canopy coverage, shade or ecological quality.',
      distanceM:near,focus,specificity:.76,surpriseBoost:features.length>80?.72:.46
    });
    if(key==='green'){
      const kind=greenType(props);
      return E.candidate(key,{
        title:features.length===1?(kind?`A mapped ${kind.toLowerCase()} is nearby.`:'A public green-space feature is nearby.'):`${features.length} public green/playground features are nearby.`,
        body:'Dedicated public green-space and playground features in the local context.',
        distanceM:near,focus,specificity:.86,surpriseBoost:.66
      });
    }
    if(key==='heat')return E.candidate(key,{
      title:'Official heat-analysis context covers this place.',
      body:'This is planning/climate analysis, not the current temperature. Open the source before interpreting severity.',
      distanceM:near,focus,specificity:.82,surpriseBoost:.62
    });
    if(key==='justice')return E.candidate(key,{
      title:'Environmental-justice mapping covers this area.',
      body:'Official integrated burden context exists here. Deep City does not collapse it into a new score.',
      distanceM:near,focus,specificity:.78,surpriseBoost:.58
    });
    if(key==='hospitals'){
      const name=placeName(props);
      return E.candidate(key,{
        title:name?`${name} is in the nearby hospital context.`:`${features.length} hospital feature${features.length===1?' is':'s are'} nearby.`,
        body:'Mapped hospital proximity is not the same as capacity, speciality or availability.',
        distanceM:near,focus,specificity:.82,surpriseBoost:.38
      });
    }
    if(key==='sports'){
      const name=placeName(props);
      return E.candidate(key,{
        title:name?`${name} is a nearby public sports facility.`:`${features.length} public sports facilit${features.length===1?'y is':'ies are'} nearby.`,
        body:'Official public core sports facilities in the selected context.',
        distanceM:near,focus,specificity:.84,surpriseBoost:.55
      });
    }
    if(key==='bathing'){
      const name=placeName(props);
      return E.candidate(key,{
        title:name?`${name} appears in Berlin’s bathing-water context.`:`A designated bathing-water feature is nearby.`,
        body:'Official bathing-water context. Current suitability or warnings require the source’s latest quality information.',
        distanceM:near,focus,specificity:.9,surpriseBoost:.82
      });
    }
    return null;
  };

  E.query=async(point,{radius=.012,keys=null}={})=>{
    await E.loadPulse();
    const selected=keys||Object.keys(SOURCES),tasks=selected.map(async key=>{
      const s=SOURCES[key];
      try{
        let candidate=null;
        if(key==='weather')candidate=E.fromWeather(await E.liveWeather(point),E.pulse);
        else if(key==='air')candidate=E.fromAir(await E.liveAir(point),E.pulse);
        else if(key==='transit')candidate=E.fromTransit(await E.liveTransit(point));
        else candidate=E.fromWfs(key,await E.wfs(key,point,radius),point);
        M.sourceHealth[key]='ready';return candidate;
      }catch(error){M.sourceHealth[key]='unavailable';return null}
    });
    const values=(await Promise.all(tasks)).filter(Boolean);
    return values;
  };

  E.score=c=>{
    const p=PERSONAS[M.persona]||PERSONAS.local,s=SOURCES[c.sourceKey],distance=M.finite(c.distanceM)?clamp(1.15-Number(c.distanceM)/1800,.18,1.15):.68;
    const surprise=clamp((c.surpriseBoost??s.surprise)*p.surprise,0,1.4),utility=clamp(s.utility*p.utility,0,1.35),freshness=clamp(s.freshness*p.freshness,0,1.2);
    const lens=p.lensWeights?.[c.lens]||1;
    return (distance*.2+freshness*.14+s.confidence*.18+utility*.18+surprise*.23+c.specificity*.07)*lens;
  };

  E.select=candidates=>{
    const scored=candidates.map(c=>({...c,score:E.score(c)})).sort((a,b)=>b.score-a.score),picked=[],lensCounts={};
    for(const c of scored){
      if(picked.length>=5)break;
      if((lensCounts[c.lens]||0)>=2)continue;
      picked.push(c);lensCounts[c.lens]=(lensCounts[c.lens]||0)+1;
    }
    if(picked.length<5)for(const c of scored)if(!picked.some(p=>p.id===c.id)){picked.push(c);if(picked.length>=5)break}
    return {scored,picked};
  };

  E.inspect=async point=>{
    const inspectToken=++E.queryToken;
    M.setPoint(point);$('meaningHero').classList.add('hidden');$('meaningPanel').classList.remove('hidden');
    $('placeTitle').textContent=`${point.lat.toFixed(3)}° N · ${point.lon.toFixed(3)}° E`;
    $('placeSubtitle').textContent='Gathering context from 12 city sources…';
    $('meaningCards').innerHTML='<div class="meaning-loading"><i></i><span>Asking the city…</span></div>';
    try{
      const result=await E.query(point);
      if(inspectToken!==E.queryToken)return;
      E.allCandidates=result;
      E.rerank();
      const ready=Object.values(M.sourceHealth).filter(v=>v==='ready').length;
      $('placeSubtitle').textContent=`${ready}/12 sources answered · ${PERSONAS[M.persona]?.label||M.persona} lens`;
    }catch(error){
      $('meaningCards').innerHTML='<div class="meaning-loading"><span>This query was replaced or could not complete.</span></div>';
    }
  };

  E.rerank=()=>{
    const {scored,picked}=E.select(E.allCandidates);E.scored=scored;M.current=picked;E.render();E.renderFingerprint();E.renderExplain();
  };

  E.render=()=>{
    const list=(M.lens==='all'?M.current:(E.scored||[]).filter(c=>c.lens===M.lens).slice(0,5));
    $('meaningCards').innerHTML=list.length?list.map(c=>E.card(c)).join(''):'<div class="meaning-loading"><span>No readable evidence in this lens at this point.</span></div>';
    $('meaningCards').querySelectorAll('[data-rate]').forEach(b=>b.addEventListener('click',e=>{e.stopPropagation();M.rate(b.closest('.meaning-card').dataset.cardId,b.dataset.rate)}));
    $('meaningCards').querySelectorAll('.meaning-card').forEach(card=>card.addEventListener('click',()=>{const c=list.find(x=>x.id===card.dataset.cardId);if(c?.focus&&M.map)M.map.easeTo({center:[c.focus.lon,c.focus.lat],zoom:12.6,duration:650})}));
  };

  E.card=c=>{
    const rating=M.ratings[c.id],distance=M.finite(c.distanceM)?(c.distanceM<1000?`~${Math.max(10,Math.round(c.distanceM/10)*10)} m`:`~${(c.distanceM/1000).toFixed(1)} km`):'at this point';
    return `<article class="meaning-card" data-card-id="${M.esc(c.id)}">
      <div class="meaning-card-top"><span>${M.esc(c.lens)} · ${M.esc(c.kind)}</span><b>${M.esc(distance)}</b></div>
      <h3>${M.esc(c.title)}</h3><p>${M.esc(c.body)}</p>
      <div class="meaning-card-foot"><span>${M.esc(c.source)}</span><em>why this? ${Math.round(c.score*100)}</em></div>
      <div class="card-rating">
        <button type="button" data-rate="useful" class="${rating==='useful'?'active':''}">Useful</button>
        <button type="button" data-rate="surprising" class="${rating==='surprising'?'active':''}">Surprising</button>
        <button type="button" data-rate="skip" class="${rating==='skip'?'active':''}">Skip</button>
      </div>
    </article>`;
  };

  E.renderFingerprint=()=>{
    const lenses=['now','life','history','infrastructure','nature'];
    for(const lens of lenses){
      const candidates=(E.scored||[]).filter(c=>c.lens===lens),ready=Object.values(SOURCES).filter(s=>s.lens===lens).length;
      const el=document.querySelector(`[data-axis="${lens}"] b`);if(el)el.textContent=`${candidates.length}/${ready}`;
    }
  };

  E.renderExplain=()=>{
    const p=PERSONAS[M.persona]||PERSONAS.local;
    $('rankingExplain').innerHTML=`<p>Deep City ranks supported observations using proximity, source freshness, confidence, place-specificity, utility, surprise and your current perspective. It then limits repeated lenses so one data family cannot dominate.</p>
      <div class="rank-row"><span>Perspective</span><b>${M.esc(p.label)}</b></div>
      <div class="rank-row"><span>Readable sources</span><b>${Object.values(M.sourceHealth).filter(v=>v==='ready').length}/12</b></div>
      <div class="rank-row"><span>Candidate observations</span><b>${E.allCandidates.length}</b></div>
      <div class="rank-row"><span>Shown by default</span><b>${M.current.length}</b></div>`;
  };

  E.surpriseNearby=async()=>{
    if(!M.point)return E.inspect({lon:13.405,lat:52.52});
    $('meaningCards').innerHTML='<div class="meaning-loading"><i></i><span>Looking a little farther…</span></div>';
    const old=M.persona;M.persona='surprise';M.qsa('#meaningMode [data-persona]').forEach(x=>x.classList.toggle('active',x.dataset.persona==='surprise'));
    const structural=['wall','buildingAge','green','trees','sports','bathing','hospitals','heat'];
    const wider=await E.query(M.point,{radius:.03,keys:structural});
    E.allCandidates=[...E.allCandidates.filter(c=>!structural.includes(c.sourceKey)),...wider];
    E.rerank();
    const top=M.current.find(c=>c.focus&&M.finite(c.distanceM)&&c.distanceM>120);
    if(top?.focus&&M.map)M.map.easeTo({center:[top.focus.lon,top.focus.lat],zoom:12,duration:800});
    M.toast(top?'Found something nearby.':'The wider search did not add a stronger discovery.');
    if(old==='surprise')return;
  };

  E.runTest=async()=>{
    if(M.testRunning)return;M.testRunning=true;
    $('runMeaningTest').textContent='Testing 12 places…';$('runMeaningTest').disabled=true;
    $('testResults').innerHTML='<div class="meaning-loading"><i></i><span>Sampling structural context…</span></div>';
    const points=[
      [13.405,52.52],[13.36,52.51],[13.46,52.51],[13.32,52.53],[13.49,52.54],[13.39,52.56],
      [13.44,52.48],[13.29,52.49],[13.52,52.49],[13.35,52.57],[13.48,52.58],[13.41,52.46]
    ].map(([lon,lat],i)=>({lon,lat,i:i+1}));
    const keys=['buildingAge','wall','green','trees'];
    const rows=[];
    for(let i=0;i<points.length;i+=3){
      const batch=points.slice(i,i+3);
      const results=await Promise.all(batch.map(async p=>{
        const candidates=await E.query(p,{keys,radius:.015});
        const selected=E.select(candidates).picked;
        return {p,candidates,selected,health:keys.filter(k=>M.sourceHealth[k]==='ready').length};
      }));
      rows.push(...results);
      $('testResults').innerHTML=`<div class="meaning-loading"><i></i><span>Tested ${rows.length}/12 places…</span></div>`;
    }
    const covered=rows.filter(r=>r.candidates.length>=2).length,avg=rows.reduce((a,r)=>a+r.candidates.length,0)/rows.length;
    const diverse=rows.filter(r=>new Set(r.candidates.map(c=>c.lens)).size>=2).length;
    $('testResults').innerHTML=`
      <div class="test-metric"><span>2+ meaningful candidates</span><b>${covered}/12</b></div>
      <div class="test-metric"><span>Average candidate count</span><b>${avg.toFixed(1)}</b></div>
      <div class="test-metric"><span>2+ lenses represented</span><b>${diverse}/12</b></div>
      ${rows.map(r=>`<div class="test-place"><strong>Sample ${r.p.i}</strong><span>${r.candidates.length} candidates · ${new Set(r.candidates.map(c=>c.lens)).size} lenses</span></div>`).join('')}`;
    M.renderHumanScore();M.testRunning=false;$('runMeaningTest').textContent='Run 12-place test';$('runMeaningTest').disabled=false;
  };

  M.ready.then(()=>{M.renderRegistry();});
})();