/** Real Chromium + real MapLibre + real basemap. Data feeds are deliberately unavailable. */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { chromium } from 'playwright';

const output = `map-test-results/${process.env.SMOKE_LABEL || 'build'}`;
await mkdir(output, { recursive: true });
let server;
let base = process.env.SMOKE_BASE_URL;
if (!base) {
  const root = resolve('public');
  const mime = { '.html':'text/html', '.css':'text/css', '.js':'text/javascript', '.mjs':'text/javascript', '.json':'application/json' };
  server = createServer(async (request, response) => {
    try {
      const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
      if (!pathname.startsWith('/COMMONS/')) throw new Error('Unknown path');
      const path = resolve(root, pathname.slice('/COMMONS/'.length));
      if (!path.startsWith(root + '/')) throw new Error('Unknown path');
      const bytes = await readFile(path);
      response.writeHead(200, { 'Content-Type':mime[extname(path)] || 'application/octet-stream', 'Cache-Control':'no-store' });
      response.end(bytes);
    } catch { response.writeHead(404); response.end('Not found'); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}/COMMONS/`;
}
if (!base.endsWith('/')) base += '/';
const report = { base, generatedAt:new Date().toISOString(), note:'Real browser/renderer/basemap. All data feeds blocked; this does not certify feed availability.', tests:[] };
const browser = await chromium.launch({ headless:true, args:['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
try {
  for (const test of [
    { name:'berlin-desktop-cdns-blocked', app:'berlin', width:1440, height:960 },
    { name:'berlin-mobile-cdns-blocked', app:'berlin', width:390, height:844 },
    { name:'atlas-desktop-cdns-blocked', app:'atlas', width:1440, height:960 },
    { name:'berlin-local-module-failure', app:'berlin', width:1440, height:960, brokenModule:true }
  ]) {
    const context = await browser.newContext({ viewport:{width:test.width,height:test.height}, reducedMotion:'reduce' });
    const page = await context.newPage();
    const exceptions = [];
    const cdnRequests = [];
    const localFailures = [];
    page.on('pageerror', error => exceptions.push(error.message));
    page.on('response', response => { if (response.url().startsWith(base) && response.status() >= 400) localFailures.push({url:response.url(),status:response.status()}); });
    await context.route('**/*', route => {
      const url = new URL(route.request().url());
      if (['cdn.jsdelivr.net','unpkg.com'].includes(url.hostname)) { cdnRequests.push(url.href); return route.abort(); }
      if (test.brokenModule && url.pathname.includes('/vendor/')) return route.abort();
      // Geography is real. Live feeds are unavailable on purpose, never replaced by invented values.
      if (url.origin === new URL(base).origin || url.hostname.endsWith('openfreemap.org') || !['http:','https:'].includes(url.protocol)) return route.continue();
      return route.abort();
    });
    const result = { name:test.name, status:'running', exceptions, cdnRequests, localFailures };
    report.tests.push(result);
    try {
      await page.goto(`${base}${test.app}.html?mapSmoke=${Date.now()}`, { waitUntil:'domcontentloaded', timeout:45000 });
      await page.waitForFunction(() => window.__COMMONS_MAP_BOOT__?.app === 'ready', null, { timeout:25000 });
      const boot = await page.evaluate(() => window.__COMMONS_MAP_BOOT__);
      result.boot = boot;
      assert.equal(boot.release, 'map6-local-1');
      if (test.brokenModule) {
        assert.equal(boot.module, 'failed');
        assert.equal(await page.locator('#mapFallback').isVisible(), true);
        assert.equal(await page.locator('[data-map-retry]').count(), 1);
        await page.locator('#enterBerlin').click();
        await page.waitForFunction(() => document.getElementById('primaryValue').textContent === 'Unavailable');
        assert.equal(await page.locator('#insight').isVisible(), true);
      } else {
        assert.equal(boot.module, 'ready');
        assert.equal(boot.version, '6.10.0');
        const layer = test.app === 'berlin' ? 'transit-points' : 'city-pins-core';
        await page.waitForFunction(id => typeof map !== 'undefined' && typeof map.getLayer === 'function' && map.getLayer(id), layer, { timeout:60000 });
        await page.waitForFunction(() => map.queryRenderedFeatures().some(f => f.sourceLayer), null, { timeout:60000 });
        result.render = await page.evaluate(() => ({ width:map.getCanvas().width, height:map.getCanvas().height, basemapFeatures:map.queryRenderedFeatures().filter(f=>f.sourceLayer).length, sources:Object.keys(map.getStyle().sources) }));
        assert.ok(result.render.width > 0 && result.render.height > 0);
        assert.ok(result.render.basemapFeatures > 0);
        assert.equal(await page.locator(test.app === 'berlin' ? '#mapFallback' : '#atlasFallback').isVisible(), false);
        await page.screenshot({ path:`${output}/${test.name}.png` });
        if (test.app === 'berlin') {
          await page.locator('#enterBerlin').click();
          await page.waitForFunction(() => document.getElementById('primaryValue').textContent === 'Unavailable');
          for (const mode of ['city','pressure','memory','now']) {
            await page.locator(`[data-mode="${mode}"]`).click();
            assert.equal(await page.locator(`[data-mode="${mode}"]`).getAttribute('class'), 'active');
            assert.ok(await page.locator('#layerRail button').count());
          }
        } else {
          await page.locator('#cityTabs [data-city="berlin"]').click();
          await page.waitForFunction(() => document.getElementById('cityName').textContent === 'Berlin');
          await page.locator('#worldButton').click();
          assert.equal(await page.locator('#worldIntro').isVisible(), true);
        }
      }
      assert.deepEqual(cdnRequests, [], 'The map must make zero CDN requests.');
      assert.deepEqual(localFailures, [], 'Local assets must not return HTTP errors.');
      assert.deepEqual(exceptions, [], 'No uncaught browser JavaScript errors.');
      result.status = 'passed';
    } catch (error) {
      result.status = 'failed'; result.error = String(error.stack || error);
      await page.screenshot({ path:`${output}/${test.name}-failure.png` }).catch(()=>{});
    } finally { await context.close(); }
  }
} finally {
  await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
  await writeFile(`${output}/report.json`, JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
}
if (report.tests.some(test=>test.status !== 'passed')) process.exitCode = 1;
