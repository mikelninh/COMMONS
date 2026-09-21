import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { chromium } from 'playwright';

const output='map-test-results/v2-lab';
await mkdir(output,{recursive:true});
const root=resolve('public');
const mime={'.html':'text/html','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json'};
const server=createServer(async(req,res)=>{
  try{
    const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    if(!pathname.startsWith('/COMMONS/'))throw new Error('path');
    const path=resolve(root,pathname.slice('/COMMONS/'.length));
    if(!path.startsWith(root+'/'))throw new Error('path');
    const bytes=await readFile(path);
    res.writeHead(200,{'Content-Type':mime[extname(path)]||'application/octet-stream','Cache-Control':'no-store'});res.end(bytes);
  }catch{res.writeHead(404);res.end('Not found')}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const base=`http://127.0.0.1:${server.address().port}/COMMONS/`;
const browser=await chromium.launch({headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const report={base,tests:[]};
try{
 for(const spec of [{name:'desktop',width:1440,height:960},{name:'mobile',width:390,height:844}]){
  const context=await browser.newContext({viewport:{width:spec.width,height:spec.height},reducedMotion:'reduce'});
  const page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await context.route('**/*',route=>{
    const u=new URL(route.request().url());
    if(u.origin===new URL(base).origin||u.hostname.endsWith('openfreemap.org')||!['http:','https:'].includes(u.protocol))return route.continue();
    return route.abort();
  });
  const result={name:spec.name,status:'running',errors};report.tests.push(result);
  try{
    await page.goto(base+'berlin-v2-lab.html',{waitUntil:'domcontentloaded',timeout:45000});
    await page.waitForFunction(()=>window.V2&&window.V2App&&document.querySelectorAll('.layout-option').length===3,null,{timeout:15000});
    assert.equal(await page.locator('.layout-option').count(),3);
    await page.locator('[data-try-layout="editorial"]').click();
    await page.locator('[data-panel="discover"]').waitFor({state:'visible'});
    assert.ok(await page.locator('#changedRail').count());
    await page.locator('#surpriseMe').click();

    await page.locator('[data-view="why"]').click();
    await page.locator('#whyPick').click();
    await page.waitForFunction(()=>document.getElementById('mapPickBanner')&&!document.getElementById('mapPickBanner').classList.contains('hidden'));
    await page.mouse.click(Math.round(spec.width*.62),Math.round(spec.height*.56));
    await page.waitForFunction(()=>document.getElementById('whyAnswer')?.textContent?.includes('EVIDENCE HEALTH'),null,{timeout:12000});
    assert.ok((await page.locator('#whyAnswer').textContent()).includes('EVIDENCE HEALTH'));

    await page.locator('[data-view="time"]').click();
    assert.ok(await page.locator('#timeMetrics div').count());

    await page.locator('[data-view="share"]').click();
    assert.equal(await page.locator('[data-share]').count(),5);
    await page.locator('[data-share="daily"]').click();
    assert.ok((await page.locator('#sharePreview').textContent()).includes('Daily Berlin'));

    await page.locator('[data-view="discover"]').click();
    const feedback=page.locator('[data-feedback-for="discover"] [data-rating="love"]');
    await feedback.click();
    assert.ok((await feedback.getAttribute('class')||'').includes('selected'));
    await page.locator('#labPicksButton').click();
    assert.equal(await page.locator('#picksDrawer').isVisible(),true);

    assert.deepEqual(errors,[]);
    await page.screenshot({path:`${output}/${spec.name}.png`});
    result.status='passed';
  }catch(e){result.status='failed';result.error=String(e.stack||e);await page.screenshot({path:`${output}/${spec.name}-failure.png`}).catch(()=>{})}
  await context.close();
 }
}finally{
 await browser.close();
 await new Promise(r=>server.close(r));
 await writeFile(`${output}/report.json`,JSON.stringify(report,null,2));
 console.log(JSON.stringify(report,null,2));
}
if(report.tests.some(t=>t.status!=='passed'))process.exitCode=1;
