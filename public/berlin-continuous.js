(() => {
  'use strict';

  const M=window.Meaning,E=window.MeaningEngine,X=window.BerlinXray;
  if(!M||!E||!X)return;
  const $=M.$,qsa=M.qsa;
  const MODES=['live','people','nature','infra','history'];
  const LENS={live:'now',people:'life',nature:'nature',infra:'infrastructure',history:'history'};
  const State=window.DeepCityState={
    place:null,camera:null,lens:'live',time:1,comparison:null,selectedInsight:null,
    sheet:'peek',comparePicking:false
  };

  const coords=p=>p?`${p.lat.toFixed(3)}° N · ${p.lon.toFixed(3)}° E`:'Berlin';
  const lensFor=mode=>LENS[mode]||'now';
  const topFor=(candidates,mode)=>{
    const lens=lensFor(mode),pool=(candidates||[]).filter(c=>c.lens===lens);
    const sorted=(pool.length?pool:candidates||[]).slice().sort((a,b)=>(b.score??E.score(b))-(a.score??E.score(a)));
    return sorted[0]||null;
  };

  function setSheet(state){
    State.sheet=state;
    const sheet=$('continuousSheet');
    if(sheet)sheet.dataset.sheetState=state;
  }

  function syncPlace(point){
    if(!point)return;
    State.place=point;State.comparison=null;State.selectedInsight=null;
    $('continuousPlace').textContent=coords(point);
    $('comparePlaceA').textContent=coords(point);
    closeCompare();
    setSheet('peek');
  }

  function syncMeaning(detail){
    const top=topFor(detail?.candidates||E.scored||[],State.lens);
    State.selectedInsight=top;
    $('continuousInsightTitle').textContent=top?.title||'No strong place-specific insight yet.';
    if(State.comparison)renderComparison();
  }

  function syncMode(mode){
    State.lens=mode;
    const top=topFor(E.scored||[],mode);
    State.selectedInsight=top;
    $('continuousInsightTitle').textContent=top?.title||'Reading this layer of the city…';
    $('continuousStatus').querySelector('span').textContent=`BERLIN · ${mode.toUpperCase()} · ${State.time===0?'PAST':State.time===2?'FUTURE':'NOW'}`;
    if(State.comparison)renderComparison();
  }

  function syncTime(value){
    State.time=Number(value);
    $('continuousStatus').querySelector('span').textContent=`BERLIN · ${State.lens.toUpperCase()} · ${State.time===0?'PAST':State.time===2?'FUTURE':'NOW'}`;
  }

  // Wrap state-changing engine calls so there is one canonical interaction state.
  const inspect=E.inspect.bind(E);
  E.inspect=async point=>{syncPlace(point);return inspect(point)};

  const setMode=X.setMode.bind(X);
  X.setMode=mode=>{syncMode(mode);return setMode(mode)};

  const setTime=X.setTime.bind(X);
  X.setTime=value=>{syncTime(value);return setTime(value)};

  const activate=X.activate.bind(X);
  X.activate=point=>{if(point)syncPlace(point);const result=activate(point);setSheet('peek');return result};

  window.addEventListener('deepcity:place',event=>syncPlace(event.detail?.point));
  window.addEventListener('deepcity:meaning',event=>syncMeaning(event.detail));

  // Sheet: one surface, three depths.
  const sheet=$('continuousSheet'),handle=$('sheetHandle');
  handle.addEventListener('click',()=>setSheet(State.sheet==='expanded'?'peek':'expanded'));
  let dragStart=null;
  handle.addEventListener('pointerdown',event=>{dragStart=event.clientY;handle.setPointerCapture?.(event.pointerId)});
  handle.addEventListener('pointerup',event=>{
    if(dragStart==null)return;
    const dy=event.clientY-dragStart;dragStart=null;
    if(dy<-28)setSheet('expanded');
    if(dy>28)setSheet('peek');
  });

  $('openMeaningDetails').addEventListener('click',()=>{setSheet('expanded');$('meaningPanel').classList.remove('hidden')});
  $('closeMeaning').addEventListener('click',()=>setSheet('peek'));

  // Contextual actions.
  $('continuousRepick').addEventListener('click',()=>M.startPick('Choose a new place. Everything will stay anchored there.'));
  $('continuousSurprise').addEventListener('click',()=>E.surpriseNearby());
  $('continuousShare').addEventListener('click',shareContinuous);
  $('continuousCompare').addEventListener('click',startCompare);
  $('closeContinuousCompare').addEventListener('click',closeCompare);

  async function shareContinuous(){
    if(State.comparison){
      const a=topFor(E.scored||[],State.lens),b=topFor(State.comparison.candidates||[],State.lens);
      const value=`Berlin Deep City — compare\nA: ${coords(State.place)}\n${a?.title||'No strong insight'}\n\nB: ${coords(State.comparison.point)}\n${b?.title||'No strong insight'}\n\nSame city. Different context.`;
      if(navigator.share){try{await navigator.share({title:'Berlin Deep City',text:value})}catch{}}
      else{await M.copy(value);M.toast('Comparison copied.')}
      return;
    }
    M.shareCurrent();
  }

  function ensureCompareLayer(){
    if(!M.map||!M.map.loaded?.())return;
    if(!M.map.getSource('continuous-compare'))M.map.addSource('continuous-compare',{type:'geojson',data:{type:'FeatureCollection',features:[]}});
    if(!M.map.getLayer('continuous-compare-halo'))M.map.addLayer({id:'continuous-compare-halo',type:'circle',source:'continuous-compare',paint:{'circle-radius':15,'circle-color':'#73d8ff','circle-opacity':.16}});
    if(!M.map.getLayer('continuous-compare-core'))M.map.addLayer({id:'continuous-compare-core',type:'circle',source:'continuous-compare',paint:{'circle-radius':6,'circle-color':'#73d8ff','circle-stroke-width':3,'circle-stroke-color':'rgba(255,255,255,.75)'}});
  }

  function startCompare(){
    if(!State.place)return M.toast('Choose a place first.');
    State.comparePicking=true;
    document.body.classList.add('continuous-comparing');
    $('meaningPick').classList.remove('hidden');
    $('meaningPick').querySelector('strong').textContent='Tap a second place';
    $('pickCopy').textContent='The camera stays put. We will compare context, not declare a winner.';
    if(M.map)M.map.getCanvas().style.cursor='crosshair';
  }

  function stopComparePick(){
    State.comparePicking=false;document.body.classList.remove('continuous-comparing');
    $('meaningPick').classList.add('hidden');
    if(M.map)M.map.getCanvas().style.cursor='';
  }

  function closeCompare(){
    stopComparePick();State.comparison=null;
    $('continuousCompareResult').classList.add('hidden');
    try{M.map?.getSource('continuous-compare')?.setData({type:'FeatureCollection',features:[]})}catch{}
  }

  async function chooseCompare(point){
    stopComparePick();ensureCompareLayer();
    try{M.map?.getSource('continuous-compare')?.setData({type:'FeatureCollection',features:[{type:'Feature',properties:{},geometry:{type:'Point',coordinates:[point.lon,point.lat]}}]})}catch{}
    $('continuousCompareResult').classList.remove('hidden');
    $('comparePlaceB').textContent=coords(point);
    $('compareInsightB').textContent='Reading this place…';
    const candidates=await E.query(point);
    const scored=candidates.map(c=>({...c,score:E.score(c)})).sort((a,b)=>b.score-a.score);
    State.comparison={point,candidates:scored};
    renderComparison();
  }

  function renderComparison(){
    if(!State.comparison)return;
    const a=topFor(E.scored||[],State.lens),b=topFor(State.comparison.candidates||[],State.lens);
    $('comparePlaceA').textContent=coords(State.place);
    $('comparePlaceB').textContent=coords(State.comparison.point);
    $('compareInsightA').textContent=a?.title||'No strong evidence in this lens.';
    $('compareInsightB').textContent=b?.title||'No strong evidence in this lens.';
  }

  M.ready.then(()=>{
    ensureCompareLayer();
    if(M.map){
      const center=M.map.getCenter();
      State.camera={center:[center.lng,center.lat],zoom:M.map.getZoom(),bearing:M.map.getBearing(),pitch:M.map.getPitch()};
      M.map.on('moveend',()=>{
        const c=M.map.getCenter();
        State.camera={center:[c.lng,c.lat],zoom:M.map.getZoom(),bearing:M.map.getBearing(),pitch:M.map.getPitch()};
      });
    }
    M.map?.on('click',event=>{
      if(!State.comparePicking)return;
      chooseCompare({lon:event.lngLat.lng,lat:event.lngLat.lat});
    });
  });

  // Existing Cancel button also cancels comparison selection.
  $('cancelPick').addEventListener('click',()=>{if(State.comparePicking)stopComparePick()});

  // Rail can be clicked, scrolled or keyboarded without becoming a new screen.
  const rail=$('xrayRail');
  let wheelLock=false;
  rail.addEventListener('wheel',event=>{
    const delta=Math.abs(event.deltaX)>Math.abs(event.deltaY)?event.deltaX:event.deltaY;
    if(Math.abs(delta)<8||wheelLock)return;
    event.preventDefault();wheelLock=true;
    const i=MODES.indexOf(State.lens),next=Math.max(0,Math.min(MODES.length-1,i+(delta>0?1:-1)));
    if(next!==i)X.setMode(MODES[next]);
    setTimeout(()=>wheelLock=false,280);
  },{passive:false});
  rail.addEventListener('keydown',event=>{
    if(!['ArrowLeft','ArrowRight'].includes(event.key))return;
    const i=MODES.indexOf(State.lens),next=Math.max(0,Math.min(MODES.length-1,i+(event.key==='ArrowRight'?1:-1)));
    X.setMode(MODES[next]);qsa('[data-xray]')[next]?.focus();
  });

  // Compact menu: secondary choices are available, never permanently in the way.
  $('continuousMenu').addEventListener('click',()=>$('continuousMenuDrawer').classList.toggle('hidden'));
  qsa('[data-menu-action]').forEach(button=>button.addEventListener('click',()=>{
    const action=button.dataset.menuAction;
    $('continuousMenuDrawer').classList.add('hidden');
    if(action==='visitor')document.querySelector('[data-persona="visitor"]')?.click();
    if(action==='local')document.querySelector('[data-persona="local"]')?.click();
    if(action==='sources'){$('sourceDrawer').classList.remove('hidden');M.renderRegistry()}
    if(action==='test'){$('testDrawer').classList.remove('hidden');M.renderHumanScore()}
  }));

  // Keep compact user state aligned with direct rail/time interactions already bound by X-Ray.
  qsa('[data-xray]').forEach(button=>button.addEventListener('click',()=>syncMode(button.dataset.xray)));
  $('xrayTimeSlider').addEventListener('input',event=>syncTime(event.target.value));

  syncMode('live');syncTime(1);
})();