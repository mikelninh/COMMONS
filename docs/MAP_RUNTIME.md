# Berlin / Atlas map runtime

MapLibre GL JS 6.10.0 is ESM-only. The previous classic `dist/maplibre-gl.js` URLs did not exist; changing CDN could not fix that. The same-origin loader now imports the module before starting the existing city application, and explicitly sets the same-origin worker URL.

## Build and local preview

```sh
node scripts/vendor-maplibre.mjs
python -m http.server 8000 --directory public
# Open http://localhost:8000/berlin.html or /atlas.html
```

The build vendors the pinned main module, worker, sibling shared module, CSS and license. The generated manifest records package integrity and file SHA-256 hashes. npm lifecycle scripts are disabled. Both GitHub Pages and Netlify run the vendor step. The browser makes no jsDelivr or unpkg requests for the renderer.

The basemap still comes from OpenFreeMap; this is not an offline map. Live data providers also remain external, subject to their own availability and browser access rules. No paid API, subscription or new billing integration is introduced.

## Browser verification

```sh
npm install --no-save --package-lock=false --ignore-scripts playwright@1.55.0
npx playwright install --with-deps chromium
node scripts/browser-map-smoke.mjs
# Optional, after deployment:
SMOKE_BASE_URL=https://mikelninh.github.io/COMMONS/ SMOKE_LABEL=deployed node scripts/browser-map-smoke.mjs
```

Tests use actual Chromium, MapLibre and OpenFreeMap geography; they do not use substitute maps or invented city data. Both former CDNs and all city data feeds are deliberately blocked. Desktop/mobile Berlin, desktop Atlas, and desktop/mobile Berlin module-failure-and-recovery are exercised. Passing requires rendered basemap features, working city controls, no uncaught browser errors, and no runtime CDN requests. Fault tests verify that the notice does not block Enter Berlin, source panels remain usable, and Retry restores the map when its local files become available.

GitHub Pages deployment is gated on the pre-deployment browser test. The same tests run against the actual Pages URL after deployment. Screenshots and JSON reports are retained in the `map-browser-proof` workflow artifact. A post-deployment failure is reported as a failed workflow; it does not automatically roll back an already published site.

These checks certify the tested rendering and interaction paths, not uptime or correctness of every live feed. NOW/CITY/PRESSURE/MEMORY source policy is unchanged. Noise, cycling and crash views that only link to their official sources are not represented as completed data ingestion.

Runtime diagnostics: `window.__COMMONS_MAP_BOOT__` reports module/app readiness, version, source, and loading errors.

Reference: https://maplibre.org/maplibre-gl-js/docs/
