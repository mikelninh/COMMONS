(() => {
  'use strict';

  const $=id=>document.getElementById(id);
  const qsa=s=>[...document.querySelectorAll(s)];
  const M=window.Meaning={
    $,qsa,map:null,persona:'local',lens:'all',point:null,picking:false,current:[],sourceHealth:{},
    ratings:loadJSON('meaning-card-ratings',{}),testRunning:false,expanded:false
  };

  function loadJSON(key,fallback){try{return JSON.parse(localStorage.getItem(key)||'')||fallback}catch{return fallback}}
  M.finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
  M.fmt=(v,d=1)=>M.finite(v)?Number(v).toFixed(d):'—';
  M.signed=(v,d=1)=>M.finite(v)?`${Number(v)>=0?'+':''}${Number(v).toFixed(d)}`:'—';
  M.esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  M.getJSON=async(url,timeout=10000,options={})=>{
    const c=new AbortController(),t=setTimeout(()=>c.abort(),timeout);
    try{const r=await fetch(url,{cache:'no-store',signal:c.signal,...options});if(!r.ok)throw Error('HTTP '+r.status);return await r.json()}
    finally{clearTimeout(t)}
  };
  M.getText=async(url,timeout=10000)=>{
    const c=new AbortController(),t=setTimeout(()=>c.abort(),timeout);
    try{const r=await fetch(url,{cache:'no-store',signal:c.signal});if(!r.ok)throw Error('HTTP '+r.status);return await r.text()}
    finally{clearTimeout(t)}
  };
  M.copy=async value=>{try{await navigator.clipboard.writeText(value)}catch{const t=document.createElement('textarea');t.value=value;document.body.append(t);t.select();document.execCommand('copy');t.remove()}};
  M.toast=message=>{const el=$('meaningToast');el.textContent=message;el.classList.remove('hidden');clearTimeout(M.toastTimer);M.toastTimer=setTimeout(()=>el.classList.add('hidden'),2200)};

  M.bootMap=async()=>{
    try{
      const lib=await import('./vendor/maplibre-6.10.0/maplibre-gl.mjs');
      lib.setWorkerUrl(new URL('./vendor/maplibre-6.10.0/maplibre-gl-worker.mjs',location.href).href);
      M.map=new lib.Map({
        container:'meaningMap',style:'https://tiles.openfreemap.org/styles/liberty',
        center:[13.405,52.52],zoom:10.15,pitch:46,bearing:-12,antialias:true,attributionControl:true
      });
      await new Promise((resolve,reject)=>{M.map.once('load',resolve);M.map.once('error',e=>reject(e.error||e))});
      M.map.addSource('meaning-point',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
      M.map.addLayer({id:'meaning-point-halo',type:'circle',source:'meaning-point',paint:{'circle-radius':17,'circle-color':'#b9ff70','circle-opacity':.13}});
      M.map.addLayer({id:'meaning-point-core',type:'circle',source:'meaning-point',paint:{'circle-radius':6,'circle-color':'#ffffff','circle-stroke-width':3,'circle-stroke-color':'rgba(185,255,112,.48)'}});
      M.map.addControl(new lib.NavigationControl({showCompass:true,showZoom:true,visualizePitch:true}),'top-right');
      M.map.on('click',e=>{if(!M.picking)return;M.finishPick();window.MeaningEngine?.inspect({lon:e.lngLat.lng,lat:e.lngLat.lat})});
      $('meaningStatus').textContent='MAP · LIVE';
    }catch(error){
      $('meaningStatus').textContent='MAP · FALLBACK';
      M.map=null;
    }
  };

  M.setPoint=p=>{
    M.point=p;
    if(M.map?.getSource('meaning-point')){
      M.map.getSource('meaning-point').setData({type:'FeatureCollection',features:[{type:'Feature',properties:{},geometry:{type:'Point',coordinates:[p.lon,p.lat]}}]});
      M.map.easeTo({center:[p.lon,p.lat],zoom:11.7,pitch:50,duration:650});
    }
  };

  M.startPick=copy=>{
    M.picking=true;
    $('pickCopy').textContent=copy||'The engine will inspect this place.';
    $('meaningPick').classList.remove('hidden');
    $('meaningHero').style.opacity='.08';$('meaningHero').style.pointerEvents='none';
    $('meaningPanel').style.opacity='.08';$('meaningPanel').style.pointerEvents='none';
    if(M.map)M.map.getCanvas().style.cursor='crosshair';
  };
  M.finishPick=()=>{
    M.picking=false;$('meaningPick').classList.add('hidden');
    $('meaningHero').style.opacity='';$('meaningHero').style.pointerEvents='';
    $('meaningPanel').style.opacity='';$('meaningPanel').style.pointerEvents='';
    if(M.map)M.map.getCanvas().style.cursor='';
  };

  M.renderRegistry=()=>{
    const registry=window.BERLIN_MEANING_SOURCES||{};
    $('sourceRegistryView').innerHTML=Object.values(registry).map(s=>`<article class="source-item">
      <div><b>${M.esc(s.label)}</b><em>${M.esc(s.kind)} · ${M.esc(s.lens)}</em></div>
      <p>${M.esc(s.note)}</p>
      <small>${M.esc(s.source)} · freshness weight ${Math.round((s.freshness||0)*100)}%</small>
    </article>`).join('');
  };

  M.renderHumanScore=()=>{
    const values=Object.values(M.ratings);
    const useful=values.filter(v=>v==='useful').length,surprising=values.filter(v=>v==='surprising').length,skip=values.filter(v=>v==='skip').length;
    $('humanScore').innerHTML=values.length
      ? `Your card ratings: <strong>${useful} useful</strong> · <strong>${surprising} surprising</strong> · ${skip} skipped. This is the human part of the engine test.`
      : 'Rate cards while exploring: <strong>Useful</strong>, <strong>Surprising</strong>, or <strong>Skip</strong>. The engine should earn your attention.';
  };

  M.rate=(id,value)=>{
    M.ratings[id]=value;localStorage.setItem('meaning-card-ratings',JSON.stringify(M.ratings));M.renderHumanScore();
    qsa(`[data-card-id="${CSS.escape(id)}"] .card-rating button`).forEach(b=>b.classList.toggle('active',b.dataset.rate===value));
  };

  M.shareCurrent=async()=>{
    if(!M.point||!M.current.length)return M.toast('Pick a place first.');
    const top=M.current.slice(0,3).map(c=>'• '+c.title).join('\n');
    const value=`Berlin Deep City — this place\n${M.point.lat.toFixed(3)}° N · ${M.point.lon.toFixed(3)}° E\n${top}`;
    if(navigator.share){try{await navigator.share({title:'Berlin Deep City',text:value})}catch{}}
    else{await M.copy(value);M.toast('Place summary copied.')}
  };

  M.initChrome=()=>{
    qsa('#meaningMode [data-persona]').forEach(b=>b.addEventListener('click',()=>{
      M.persona=b.dataset.persona;M.expanded=false;qsa('#meaningMode [data-persona]').forEach(x=>x.classList.toggle('active',x===b));
      if(M.point)window.MeaningEngine?.rerank();
    }));
    qsa('#lensTabs [data-lens]').forEach(b=>b.addEventListener('click',()=>{
      M.lens=b.dataset.lens;M.expanded=false;qsa('#lensTabs [data-lens]').forEach(x=>x.classList.toggle('active',x===b));window.MeaningEngine?.render();
    }));

    qsa('[data-jump-lens]').forEach(tile=>tile.addEventListener('click',()=>{
      const lens=tile.dataset.jumpLens;M.lens=lens;M.expanded=false;
      qsa('#lensTabs [data-lens]').forEach(x=>x.classList.toggle('active',x.dataset.lens===lens));
      window.MeaningEngine?.render();
    }));
    $('meaningMore').addEventListener('click',()=>{M.expanded=!M.expanded;window.MeaningEngine?.render()});

    $('startMeaning').addEventListener('click',()=>M.startPick('Pick anywhere. Meaning changes with place.'));
    $('toolPick').addEventListener('click',()=>M.startPick('Ask any point in Berlin.'));
    $('pickAnother').addEventListener('click',()=>M.startPick('Choose another place.'));
    $('cancelPick').addEventListener('click',M.finishPick);
    $('startCenter').addEventListener('click',()=>window.MeaningEngine?.inspect({lon:13.405,lat:52.52}));
    $('closeMeaning').addEventListener('click',()=>{
      $('meaningPanel').classList.add('hidden');
      if(window.BerlinXray?.active)return;
      $('meaningHero').classList.remove('hidden');
    });
    $('surpriseNearby').addEventListener('click',()=>window.MeaningEngine?.surpriseNearby());
    $('toolSurprise').addEventListener('click',()=>{M.persona='surprise';qsa('#meaningMode [data-persona]').forEach(x=>x.classList.toggle('active',x.dataset.persona==='surprise'));if(M.point)window.MeaningEngine?.surpriseNearby();else window.MeaningEngine?.inspect({lon:13.405,lat:52.52})});
    $('shareMeaning').addEventListener('click',M.shareCurrent);

    $('toolSources').addEventListener('click',()=>{$('sourceDrawer').classList.remove('hidden');M.renderRegistry()});
    $('closeSources').addEventListener('click',()=>$('sourceDrawer').classList.add('hidden'));
    $('toolTest').addEventListener('click',()=>{$('testDrawer').classList.remove('hidden');M.renderHumanScore()});
    $('closeTest').addEventListener('click',()=>$('testDrawer').classList.add('hidden'));
    $('runMeaningTest').addEventListener('click',()=>window.MeaningEngine?.runTest());
  };

  M.ready=(async()=>{M.initChrome();M.renderRegistry();M.renderHumanScore();await M.bootMap();return true})();
})();