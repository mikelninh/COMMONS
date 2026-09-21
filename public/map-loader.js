/* MapLibre v6 is ESM-only. Load the exact same-origin module and worker before the app. */
(() => {
  'use strict';
  const tag = document.currentScript;
  const app = tag?.dataset.mapApp;
  const base = new URL('.', tag?.src || location.href);
  const release = 'map6-local-1';
  const status = window.__COMMONS_MAP_BOOT__ = {
    release, module: 'loading', app: 'waiting', source: 'same-origin', errors: []
  };
  if (!['berlin', 'atlas'].includes(app)) {
    console.error('Unknown COMMONS map entry point.');
    return;
  }
  const fallback = () => document.getElementById(app === 'berlin' ? 'mapFallback' : 'atlasFallback');
  function showError(message) {
    const el = fallback();
    if (!el) return;
    // A map outage must never turn the notice into a full-screen modal.
    el.style.cssText = 'position:fixed;inset:auto;top:116px;right:16px;width:min(330px,calc(100vw - 32px));box-sizing:border-box;padding:18px;display:block;text-align:left;border:1px solid #374639;border-radius:16px;background:#101810;z-index:25';
    el.classList.remove('hidden');
    el.setAttribute('role', 'status');
    el.querySelector('strong').textContent = 'Map renderer unavailable.';
    el.querySelector('strong').style.fontSize = '18px';
    el.querySelector('span').style.display = 'block';
    el.querySelector('span').textContent = message;
    if (!el.querySelector('[data-map-retry]')) {
      const retry = document.createElement('button');
      retry.type = 'button';
      retry.dataset.mapRetry = '';
      retry.textContent = 'Retry map';
      retry.style.cssText = 'margin-top:12px;padding:8px 14px;border:1px solid currentColor;background:transparent;color:inherit;border-radius:6px;cursor:pointer';
      retry.onclick = () => { const url = new URL(location.href); url.searchParams.set('mapRetry', Date.now()); location.replace(url); };
      const dismiss = document.createElement('button');
      dismiss.type = 'button';
      dismiss.textContent = 'Dismiss';
      dismiss.style.cssText = retry.style.cssText + ';margin-left:8px';
      dismiss.onclick = () => { el.style.display = 'none'; };
      el.append(retry, dismiss);
      // Once Berlin is opened, put the notice inside the scrollable evidence panel.
      // This preserves access to all four mode tabs and all source-layer buttons.
      document.getElementById('enterBerlin')?.addEventListener('click', () => {
        const panel = document.getElementById('insight');
        if (panel) {
          panel.append(el);
          el.style.position = 'static';
          el.style.width = 'auto';
          el.style.marginTop = '16px';
        }
      }, { once:true });
    }
  }
  function deadline(promise, milliseconds) {
    let timer;
    return Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error('Local map module timed out.')), milliseconds);
    })]).finally(() => clearTimeout(timer));
  }
  async function boot() {
    try {
      const directory = new URL('./vendor/maplibre-6.10.0/', base);
      const lib = await deadline(import(new URL('maplibre-gl.mjs', directory).href), 12000);
      if (typeof lib.Map !== 'function' || typeof lib.setWorkerUrl !== 'function') {
        throw new Error('Invalid MapLibre module.');
      }
      // The worker imports its sibling shared module. Both are copied during the build.
      lib.setWorkerUrl(new URL('maplibre-gl-worker.mjs', directory).href);
      lib.setWorkerCount(2);
      window.maplibregl = lib;
      status.module = 'ready';
      status.version = lib.getVersion();
    } catch (error) {
      status.module = 'failed';
      status.errors.push(String(error?.message || error));
    }
    // A separate, ordered classic script preserves the existing application's scope.
    const script = document.createElement('script');
    script.src = new URL(`./${app}.js?v=${release}`, base).href;
    script.onload = () => {
      status.app = 'ready';
      if (status.module === 'failed') showError(app === 'berlin' ? 'The local map files could not be loaded. Berlin’s source panels remain available. Retry the map to reconnect.' : 'The local map files could not be loaded. Retry the map to explore the city atlas.');
    };
    script.onerror = () => {
      status.app = 'failed';
      showError('The city application could not be loaded. Retry to reconnect.');
    };
    document.head.append(script);
  }
  boot();
})();
