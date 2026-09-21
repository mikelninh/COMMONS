(() => {
  'use strict';

  const PULSE_DATA = './data/berlin-pulse/latest.json';
  const CITY = { lat:52.52, lon:13.405 };
  const layerBySignal = {
    temperature_2m:'weather', pm2_5:'air', river_discharge:'water', transit_vehicles:'movement'
  };
  let pulse = null;
  let whyHereArmed = false;
  let mapClickBound = false;

  const $p = id => document.getElementById(id);
  const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
  const fmt = (value, digits=1) => finite(value) ? Number(value).toFixed(digits) : '—';
  const signed = (value, digits=1) => finite(value) ? `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(digits)}` : '—';
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

  function waitForBerlin() {
    const ready = window.__COMMONS_MAP_BOOT__?.app === 'ready' && document.getElementById('modeTabs');
    if (!ready) return setTimeout(waitForBerlin, 80);
    installPulse();
  }

  function installPulse() {
    if ($p('pulsePanel')) return;
    const tabs = $p('modeTabs');
    const button = document.createElement('button');
    button.id = 'pulseMode';
    button.type = 'button';
    button.className = 'pulse-tab';
    button.textContent = 'PULSE';
    button.setAttribute('aria-controls','pulsePanel');
    tabs.prepend(button);

    const panel = document.createElement('section');
    panel.id = 'pulsePanel';
    panel.className = 'pulse-panel hidden';
    panel.innerHTML = `
      <div class="pulse-eyebrow"><span class="pulse-live-dot"></span> BERLIN PULSE <b id="pulseFreshness">connecting</b></div>
      <button class="pulse-close" id="pulseClose" type="button" aria-label="Close Berlin Pulse">×</button>
      <h2 id="pulseHeadline">Listening to Berlin.</h2>
      <p class="pulse-explain" id="pulseExplanation">The tape is connecting live signals to recent context.</p>
      <div class="pulse-signals" id="pulseSignals"></div>
      <section class="pulse-discovery">
        <div class="pulse-section-head"><span>WHAT CHANGED?</span><b>since the previous tape</b></div>
        <div class="pulse-changes" id="pulseChanges"></div>
      </section>
      <div class="pulse-lower">
        <article class="pulse-module">
          <span class="pulse-module-label">FORECAST TEST</span>
          <strong id="pulseForecastTitle">Warming up</strong>
          <p id="pulseForecastCopy">Every forecast is compared with a dumb persistence baseline. If it cannot beat that, it does not earn trust.</p>
          <div class="pulse-score" id="pulseForecastScore"></div>
        </article>
        <article class="pulse-module">
          <span class="pulse-module-label">THE TAPE</span>
          <strong id="pulseTapeTitle">Recording begins now.</strong>
          <p id="pulseTapeCopy">Snapshots accumulate automatically. Missing sources stay missing.</p>
          <div class="pulse-tape-meta" id="pulseTapeMeta"></div>
        </article>
      </div>
      <article class="pulse-here">
        <div>
          <span class="pulse-module-label">WHY HERE? · V2</span>
          <strong id="pulseHereTitle">Ask the map about a place.</strong>
          <p id="pulseHereCopy">Live weather, modeled air and transit are combined with nearby official Berlin trees, green space, heat-analysis and environmental-justice features — without collapsing them into a score.</p>
        </div>
        <button id="pulseHereButton" type="button">Choose a place on the map</button>
        <div id="pulseHereResult" class="pulse-here-result hidden"></div>
      </article>
      <section class="pulse-hypothesis">
        <div class="pulse-section-head"><span>HYPOTHESIS LAB</span><b>the tape tries to falsify these</b></div>
        <div class="pulse-hypothesis-grid" id="pulseHypotheses"></div>
      </section>
      <footer class="pulse-foot">OBSERVE → DETECT → EXPLAIN → HYPOTHESIZE → FORECAST → VERIFY</footer>`;
    document.body.append(panel);

    button.addEventListener('click', openPulse);
    $p('pulseClose').addEventListener('click', closePulse);
    $p('pulseHereButton').addEventListener('click', armWhyHere);
    document.querySelectorAll('[data-mode]').forEach(el => el.addEventListener('click', closePulseQuiet));

    bindMapClickWhenReady();
    refreshPulse();
    setInterval(refreshPulse, 5 * 60 * 1000);
  }

  function openPulse() {
    $p('intro')?.classList.add('hidden');
    $p('insight')?.classList.add('hidden');
    $p('layerRail')?.classList.add('hidden');
    $p('timeline')?.classList.add('hidden');
    $p('cards')?.classList.add('hidden');
    document.querySelectorAll('[data-mode]').forEach(el => el.classList.remove('active'));
    $p('pulseMode')?.classList.add('active');
    $p('pulsePanel')?.classList.remove('hidden');
    if (typeof clearVisualLayers === 'function') clearVisualLayers();
    if (typeof fitBerlin === 'function') fitBerlin();
    refreshPulse();
  }

  function closePulseQuiet() {
    $p('pulsePanel')?.classList.add('hidden');
    $p('pulsePanel')?.classList.remove('map-picking');
    $p('pulseMode')?.classList.remove('active');
    $p('pulseMapPrompt')?.remove();
    whyHereArmed = false;
  }

  function closePulse() {
    closePulseQuiet();
    $p('insight')?.classList.remove('hidden');
    $p('layerRail')?.classList.remove('hidden');
    if (typeof setMode === 'function') setMode('now');
  }

  async function refreshPulse() {
    try {
      const response = await fetch(`${PULSE_DATA}?t=${Date.now()}`, {cache:'no-store'});
      if (!response.ok) throw new Error(`tape ${response.status}`);
      const stored = await response.json();
      if (!stored?.generated_at || !stored?.signals || !Object.keys(stored.signals).length) throw new Error('tape warming up');
      pulse = stored;
    } catch {
      pulse = await livePulseFallback();
    }
    renderPulse();
  }

  async function livePulseFallback() {
    const weatherUrl = `https://api.open-meteo.com/v1/forecast?latitude=${CITY.lat}&longitude=${CITY.lon}&current=temperature_2m,apparent_temperature,precipitation,wind_speed_10m&hourly=temperature_2m,apparent_temperature,precipitation&forecast_hours=13&timezone=UTC`;
    const airUrl = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${CITY.lat}&longitude=${CITY.lon}&current=pm2_5,nitrogen_dioxide,ozone&hourly=pm2_5&forecast_hours=13&timezone=UTC`;
    const floodUrl = `https://flood-api.open-meteo.com/v1/flood?latitude=${CITY.lat}&longitude=${CITY.lon}&daily=river_discharge&past_days=7&forecast_days=3&timezone=UTC`;
    const transitUrl = 'https://v6.vbb.transport.rest/radar?north=52.70&west=13.08&south=52.34&east=13.78&results=600&duration=30';
    const [weather, air, flood, transit] = await Promise.allSettled([
      fetch(weatherUrl,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject(new Error('weather'))),
      fetch(airUrl,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject(new Error('air'))),
      fetch(floodUrl,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject(new Error('water'))),
      fetch(transitUrl,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject(new Error('transit')))
    ]);
    const w = weather.status === 'fulfilled' ? weather.value : {};
    const a = air.status === 'fulfilled' ? air.value : {};
    const f = flood.status === 'fulfilled' ? flood.value : {};
    const t = transit.status === 'fulfilled' ? transit.value : {};
    const targetIndex = Math.min(12, Math.max(0,(w.hourly?.time||[]).length-1));
    const airTargetIndex = Math.min(12, Math.max(0,(a.hourly?.time||[]).length-1));
    const movements = Array.isArray(t.movements) ? t.movements : Array.isArray(t) ? t : [];
    return {
      generated_at:new Date().toISOString(),
      status:'live-only',
      sample_count:0,
      history_basis:'Live browser fallback; no stored tape baseline was available.',
      headline:{level:'learning',title:'Berlin Pulse is live, but the tape is still warming up.',explanation:'Current signals are visible. Anomaly claims wait for a recorded baseline.'},
      signals:{
        temperature_2m:{label:'Temperature',value:w.current?.temperature_2m,unit:'°C',source:'Open-Meteo weather model',anomaly:{label:'learning',score:null,n:0},forecast:{hours:12,value:w.hourly?.temperature_2m?.[targetIndex],unit:'°C',source:'Open-Meteo'}},
        pm2_5:{label:'PM2.5',value:a.current?.pm2_5,unit:'µg/m³',source:'CAMS via Open-Meteo · modeled',anomaly:{label:'learning',score:null,n:0},forecast:{hours:12,value:a.hourly?.pm2_5?.[airTargetIndex],unit:'µg/m³',source:'CAMS'}},
        river_discharge:{label:'Spree / river',value:f.daily?.river_discharge?.[Math.min(7,(f.daily?.river_discharge||[]).length-1)],unit:'m³/s',source:'GloFAS fallback · modeled',anomaly:{label:'learning',score:null,n:0}},
        transit_vehicles:{label:'Transit movement',value:movements.length,unit:'vehicles',source:'VBB realtime radar',anomaly:{label:'learning',score:null,n:0}}
      },
      forecast_score:{resolved:0},
      source_health:{weather:weather.status,air:air.status,water:flood.status,transit:transit.status}
    };
  }

  function renderPulse() {
    if (!pulse || !$p('pulsePanel')) return;
    const headline = pulse.headline || {};
    $p('pulseHeadline').textContent = headline.title || 'Berlin Pulse is listening.';
    $p('pulseExplanation').textContent = headline.explanation || 'Signals stay separate until the evidence supports a connection.';
    const generated = pulse.generated_at ? new Date(pulse.generated_at) : null;
    const ageMinutes = generated ? Math.max(0, Math.round((Date.now()-generated.getTime())/60000)) : null;
    $p('pulseFreshness').textContent = pulse.status === 'live-only' ? 'live browser fallback' : ageMinutes == null ? 'warming up' : ageMinutes < 2 ? 'just recorded' : `${ageMinutes}m old`;

    const order = ['temperature_2m','pm2_5','river_discharge','transit_vehicles'];
    $p('pulseSignals').innerHTML = order.map(key => signalCard(key,pulse.signals?.[key])).join('');
    $p('pulseSignals').querySelectorAll('[data-pulse-layer]').forEach(el => el.addEventListener('click', () => openLayer(el.dataset.pulseLayer)));
    renderChanges();
    renderForecastScore();
    renderTape();
    renderHypotheses();
  }

  function renderChanges() {
    const changes = Array.isArray(pulse.changes) ? pulse.changes.slice(0,4) : [];
    if (!changes.length) {
      $p('pulseChanges').innerHTML = '<div class="pulse-empty">The tape needs one more comparable snapshot before it can rank what changed.</div>';
      return;
    }
    $p('pulseChanges').innerHTML = changes.map(change => {
      const digits = Number(change.digits ?? 1);
      const delta = finite(change.delta) ? signed(change.delta,digits) : '—';
      const percent = finite(change.percent) ? ` · ${signed(change.percent,1)}%` : '';
      const arrow = change.direction === 'up' ? '↑' : change.direction === 'down' ? '↓' : '→';
      return `<button class="pulse-change" data-pulse-layer="${escapeHtml(layerBySignal[change.metric]||'')}">
        <span>${escapeHtml(change.label||change.metric)}</span>
        <b>${arrow} ${delta} ${escapeHtml(change.unit||'')}${percent}</b>
        <small>${escapeHtml(change.basis||'since the previous tape')}</small>
      </button>`;
    }).join('');
    $p('pulseChanges').querySelectorAll('[data-pulse-layer]').forEach(el => el.addEventListener('click',()=>openLayer(el.dataset.pulseLayer)));
  }

  function renderHypotheses() {
    const hypotheses = Array.isArray(pulse.hypotheses) ? pulse.hypotheses : [];
    if (!hypotheses.length) {
      $p('pulseHypotheses').innerHTML = '<div class="pulse-empty">The first hypotheses will appear after the next recorded tape run.</div>';
      return;
    }
    $p('pulseHypotheses').innerHTML = hypotheses.map(h => `<article class="pulse-h-card ${escapeHtml(h.status||'learning')}">
      <div><span>${escapeHtml((h.status||'learning').replaceAll('_',' '))}</span><small>${escapeHtml(h.kind||'observational')}</small></div>
      <strong>${escapeHtml(h.question||'Untitled hypothesis')}</strong>
      <p>${escapeHtml(h.evidence||'Learning.')}</p>
    </article>`).join('');
  }

  function signalCard(key, signal={}) {
    const anomaly = signal.anomaly || {};
    const state = anomaly.label || 'learning';
    const score = finite(anomaly.score) ? `z ${signed(anomaly.score,1)}` : state === 'learning' ? 'learning' : '—';
    const forecast = signal.forecast && finite(signal.forecast.value)
      ? `<span class="pulse-next">+${escapeHtml(signal.forecast.hours || 12)}h ${fmt(signal.forecast.value, signal.unit === 'vehicles' ? 0 : 1)} ${escapeHtml(signal.forecast.unit || signal.unit || '')}</span>` : '<span class="pulse-next">no forecast claim</span>';
    return `<button class="pulse-signal ${escapeHtml(state)}" data-pulse-layer="${escapeHtml(layerBySignal[key]||'')}">
      <span class="pulse-signal-top"><b>${escapeHtml(signal.label || key)}</b><em>${escapeHtml(state)}</em></span>
      <strong>${fmt(signal.value, signal.unit === 'vehicles' ? 0 : 1)} <small>${escapeHtml(signal.unit || '')}</small></strong>
      <span class="pulse-anomaly">${escapeHtml(score)} · n=${escapeHtml(anomaly.n ?? 0)}</span>
      ${forecast}
      <span class="pulse-source">${escapeHtml(signal.source || 'source unavailable')}</span>
    </button>`;
  }

  function renderForecastScore() {
    const score = pulse.forecast_score || {};
    const resolved = Number(score.resolved || 0);
    if (resolved < 3) {
      $p('pulseForecastTitle').textContent = `${resolved} forecast${resolved===1?'':'s'} scored`;
      $p('pulseForecastCopy').textContent = 'We need at least three resolved forecasts before comparing the candidate with persistence. No victory lap on tiny samples.';
      $p('pulseForecastScore').innerHTML = '<span>candidate</span><b>learning</b><span>baseline</span><b>learning</b>';
      return;
    }
    const candidate = Number(score.candidate_mae);
    const baseline = Number(score.baseline_mae);
    const better = Number(score.candidate_better_rate);
    const verdict = candidate < baseline ? 'Forecast source is beating persistence so far.' : 'Persistence is still hard to beat.';
    $p('pulseForecastTitle').textContent = verdict;
    $p('pulseForecastCopy').textContent = `${resolved} resolved 12-hour forecasts. This is an experiment, not a guarantee; errors are kept visible.`;
    $p('pulseForecastScore').innerHTML = `<span>candidate MAE</span><b>${fmt(candidate,2)}</b><span>persistence MAE</span><b>${fmt(baseline,2)}</b><span>candidate wins</span><b>${fmt(better*100,0)}%</b>`;
  }

  function renderTape() {
    const n = Number(pulse.sample_count || 0);
    $p('pulseTapeTitle').textContent = n ? `${n} recorded snapshot${n===1?'':'s'}.` : 'Recording begins now.';
    $p('pulseTapeCopy').textContent = pulse.history_basis || 'The collector stores real snapshots, resolves old forecasts, then issues new ones.';
    const health = pulse.source_health || {};
    const parts = Object.entries(health).map(([k,v]) => `${k} ${String(v).replace('fulfilled','✓').replace('rejected','×')}`);
    $p('pulseTapeMeta').textContent = parts.length ? parts.join(' · ') : 'weather · air · water · transit';
  }

  function openLayer(layer) {
    if (!layer || typeof setLayer !== 'function') return;
    closePulseQuiet();
    $p('insight')?.classList.remove('hidden');
    $p('layerRail')?.classList.remove('hidden');
    const mode = layer === 'weather' || layer === 'air' || layer === 'water' || layer === 'movement' ? 'now' : 'pressure';
    if (typeof setMode === 'function') setMode(mode);
    setTimeout(() => setLayer(layer), 0);
  }

  function bindMapClickWhenReady() {
    if (mapClickBound) return;
    if (typeof map === 'undefined' || !map || typeof map.on !== 'function') return setTimeout(bindMapClickWhenReady, 250);
    mapClickBound = true;
    map.on('click', event => {
      if (!whyHereArmed) return;
      whyHereArmed = false;
      endMapPick();
      $p('pulseHereButton').textContent = 'Choose another place';
      inspectHere(event.lngLat.lng, event.lngLat.lat);
    });
  }

  function armWhyHere() {
    whyHereArmed = true;
    $p('pulseHereButton').textContent = 'Click anywhere on Berlin…';
    $p('pulseHereTitle').textContent = 'The map is listening.';
    $p('pulseHereCopy').textContent = 'Choose a point. The answer will stay explicit about what is modeled, measured and merely nearby.';
    if(window.innerWidth<=900){
      $p('pulsePanel')?.classList.add('map-picking');
      $p('pulseMapPrompt')?.remove();
      const prompt=document.createElement('div');
      prompt.id='pulseMapPrompt';prompt.className='pulse-map-prompt';
      prompt.innerHTML='<strong>Tap a place on Berlin</strong><span>Why Here will inspect this point.</span><button type="button">Cancel</button>';
      prompt.querySelector('button').addEventListener('click',()=>{whyHereArmed=false;endMapPick()});
      document.body.append(prompt);
    }
  }

  function endMapPick(){
    $p('pulsePanel')?.classList.remove('map-picking');
    $p('pulseMapPrompt')?.remove();
  }

  async function wfsAround(key,lon,lat) {
    if(typeof WFS_CONFIG==='undefined'||typeof discoverFeatureTypes!=='function')throw new Error('Berlin WFS helpers unavailable');
    const cfg=WFS_CONFIG[key];if(!cfg)throw new Error('unknown WFS layer');
    const types=await discoverFeatureTypes(cfg.endpoint);
    const typeName=types.find(type=>cfg.patterns.some(pattern=>pattern.test(type)))||types[0];
    if(!typeName)throw new Error('no feature type');
    const dx=.010,dy=.007;
    const params=new URLSearchParams({
      service:'WFS',version:'2.0.0',request:'GetFeature',typeNames:typeName,
      outputFormat:'application/json',srsName:'EPSG:4326',count:'140',
      bbox:`${lon-dx},${lat-dy},${lon+dx},${lat+dy},EPSG:4326`
    });
    const response=await fetch(cfg.endpoint+'?'+params.toString(),{cache:'no-store'});
    if(!response.ok)throw new Error('WFS '+response.status);
    const raw=await response.json();
    return {count:Array.isArray(raw.features)?raw.features.length:0,typeName};
  }

  async function inspectHere(lon,lat) {
    const result = $p('pulseHereResult');
    result.classList.remove('hidden');
    result.innerHTML = '<span>Reading live + structural context…</span>';
    addHereMarker(lon,lat);
    const delta = .018;
    const weatherUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,apparent_temperature,precipitation&timezone=UTC`;
    const airUrl = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}&current=pm2_5,nitrogen_dioxide,ozone&timezone=UTC`;
    const transitUrl = `https://v6.vbb.transport.rest/radar?north=${lat+delta}&west=${lon-delta}&south=${lat-delta}&east=${lon+delta}&results=180&duration=30`;
    const [weather,air,transit,trees,green,heat,justice] = await Promise.allSettled([
      fetch(weatherUrl,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()),
      fetch(airUrl,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()),
      fetch(transitUrl,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()),
      wfsAround('trees',lon,lat),wfsAround('green',lon,lat),wfsAround('heat',lon,lat),wfsAround('justice',lon,lat)
    ]);
    const w = weather.status==='fulfilled' ? weather.value.current||{} : {};
    const a = air.status==='fulfilled' ? air.value.current||{} : {};
    const t = transit.status==='fulfilled' ? (transit.value.movements||transit.value||[]) : [];
    const count = settled => settled.status==='fulfilled' ? settled.value.count : null;
    const treeCount=count(trees),greenCount=count(green),heatCount=count(heat),justiceCount=count(justice);
    const cityTemp = pulse?.signals?.temperature_2m?.value;
    const cityPm = pulse?.signals?.pm2_5?.value;
    const tempDelta = finite(w.temperature_2m) && finite(cityTemp) ? Number(w.temperature_2m)-Number(cityTemp) : null;
    const pmDelta = finite(a.pm2_5) && finite(cityPm) ? Number(a.pm2_5)-Number(cityPm) : null;
    $p('pulseHereTitle').textContent = `${lat.toFixed(3)}° N · ${lon.toFixed(3)}° E`;
    const structuralReadable=[treeCount,greenCount,heatCount,justiceCount].some(v=>v!==null);
    $p('pulseHereCopy').textContent = structuralReadable
      ? 'Live context plus official Berlin features in a small box around this point. Feature presence is context, not a severity score.'
      : 'Live context is readable. Official structural WFS layers did not answer in this browser, so no structural claim is made.';
    result.innerHTML = `
      <div><span>modeled temperature</span><b>${fmt(w.temperature_2m,1)}°C</b><small>${finite(tempDelta)?`${signed(tempDelta,1)}° vs city pulse`:'city comparison unavailable'}</small></div>
      <div><span>modeled PM2.5</span><b>${fmt(a.pm2_5,1)}</b><small>${finite(pmDelta)?`${signed(pmDelta,1)} µg/m³ vs city pulse`:'city comparison unavailable'}</small></div>
      <div><span>live transit nearby</span><b>${Array.isArray(t)?t.length:'—'}</b><small>VBB vehicles in roughly a 2 km box</small></div>
      <div><span>official mapped trees nearby</span><b>${treeCount??'—'}</b><small>features returned in the local Berlin WFS box</small></div>
      <div><span>official green-space features</span><b>${greenCount??'—'}</b><small>nearby feature count, not area or quality</small></div>
      <div><span>official pressure context</span><b>${heatCount===null&&justiceCount===null?'—':`${heatCount??0} · ${justiceCount??0}`}</b><small>heat-analysis · environmental-justice features nearby; presence ≠ burden level</small></div>`;
  }

  function addHereMarker(lon,lat) {
    if (typeof map === 'undefined' || !map || !map.getStyle?.()) return;
    const data = {type:'FeatureCollection',features:[{type:'Feature',properties:{},geometry:{type:'Point',coordinates:[lon,lat]}}]};
    if (!map.getSource('pulse-here')) map.addSource('pulse-here',{type:'geojson',data}); else map.getSource('pulse-here').setData(data);
    if (!map.getLayer('pulse-here')) map.addLayer({id:'pulse-here',type:'circle',source:'pulse-here',paint:{'circle-radius':10,'circle-color':'#ffffff','circle-opacity':.95,'circle-stroke-width':4,'circle-stroke-color':'rgba(185,255,112,.42)'}});
    map.easeTo({center:[lon,lat],zoom:Math.max(map.getZoom(),12),duration:650});
  }

  waitForBerlin();
})();
