import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
import { chromium } from 'playwright';

const output='map-test-results/meaning-engine';
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

const typeByPath={
  baumbestand:'baumbestand:baeume',
  gruenanlagen:'gruenanlagen:anlagen',
  ua_gebaeudealter:'ua_gebaeudealter:baualter',
  berlinermauer:'berlinermauer:mauer',
  ua_klimaanalyse_2022:'ua_klimaanalyse_2022:klima',
  ua_umweltgerechtigkeit2023:'ua_umweltgerechtigkeit2023:umwelt',
  ua_einwohnerdichte_2024:'ua_einwohnerdichte_2024:einwohnerdichte',
  krankenhaeuser:'krankenhaeuser:standorte',
  sportstandorte:'sportstandorte:sport',
  badegewaesser:'badegewaesser:badestellen'
};

const square=(x,y,d=.004)=>({type:'Polygon',coordinates:[[[x-d,y-d],[x+d,y-d],[x+d,y+d],[x-d,y+d],[x-d,y-d]]]});
function featuresFor(path){
  const center=[13.405,52.52];
  if(path.includes('baumbestand'))return Array.from({length:28},(_,i)=>({type:'Feature',properties:{name:'tree '+i},geometry:{type:'Point',coordinates:[center[0]+((i%7)-3)*.0012,center[1]+(Math.floor(i/7)-2)*.0011]}}));
  if(path.includes('gruenanlagen'))return [{type:'Feature',properties:{objartname:'Grünanlage'},geometry:square(13.408,52.522,.003)}];
  if(path.includes('ua_gebaeudealter'))return [{type:'Feature',properties:{baualtersklasse:'1890–1918'},geometry:square(13.405,52.52,.006)}];
  if(path.includes('berlinermauer'))return [{type:'Feature',properties:{name:'Berliner Mauer'},geometry:{type:'LineString',coordinates:[[13.399,52.515],[13.403,52.519],[13.408,52.524]]}}];
  if(path.includes('ua_klimaanalyse_2022'))return [{type:'Feature',properties:{klasse:'planning context'},geometry:square(13.405,52.52,.008)}];
  if(path.includes('ua_umweltgerechtigkeit2023'))return [{type:'Feature',properties:{klasse:'context'},geometry:square(13.406,52.519,.007)}];
  if(path.includes('ua_einwohnerdichte_2024'))return [{type:'Feature',properties:{density:11200},geometry:square(13.405,52.52,.012)}];
  if(path.includes('krankenhaeuser'))return [{type:'Feature',properties:{name:'Test Hospital'},geometry:{type:'Point',coordinates:[13.414,52.521]}}];
  if(path.includes('sportstandorte'))return [{type:'Feature',properties:{name:'Test Sportanlage'},geometry:{type:'Point',coordinates:[13.411,52.517]}}];
  if(path.includes('badegewaesser'))return [{type:'Feature',properties:{name:'Test Badestelle'},geometry:{type:'Point',coordinates:[13.43,52.52]}}];
  return [];
}

const browser=await chromium.launch({headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const report={base,tests:[]};

try{
  for(const spec of [{name:'desktop',width:1440,height:960},{name:'mobile',width:390,height:844}]){
    const context=await browser.newContext({viewport:{width:spec.width,height:spec.height},reducedMotion:'reduce'});
    const page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));

    await context.route('**/*',async route=>{
      const req=route.request(),u=new URL(req.url());
      if(u.origin===new URL(base).origin||u.hostname.endsWith('openfreemap.org')||!['http:','https:'].includes(u.protocol))return route.continue();
      if(u.hostname==='api.open-meteo.com')return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({current:{temperature_2m:16.4,apparent_temperature:15.9,precipitation:0,wind_speed_10m:8.2}})});
      if(u.hostname==='air-quality-api.open-meteo.com')return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({current:{pm2_5:3.2,nitrogen_dioxide:4.1,ozone:58}})});
      if(u.hostname==='v6.vbb.transport.rest')return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({movements:Array.from({length:24},(_,i)=>({id:i}))})});
      if(u.hostname==='gdi.berlin.de'&&u.pathname.includes('/services/wfs/')){
        const key=u.pathname.split('/').pop();
        const request=(u.searchParams.get('request')||u.searchParams.get('REQUEST')||'').toLowerCase();
        if(request==='getcapabilities'){
          const type=typeByPath[key]||`${key}:features`;
          return route.fulfill({status:200,contentType:'text/xml',body:`<?xml version="1.0"?><WFS_Capabilities><FeatureTypeList><FeatureType><Name>${type}</Name></FeatureType></FeatureTypeList></WFS_Capabilities>`});
        }
        if(request==='getfeature'){
          return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({type:'FeatureCollection',features:featuresFor(key)})});
        }
      }
      return route.abort();
    });

    const result={name:spec.name,status:'running',errors};report.tests.push(result);
    try{
      await page.goto(base+'berlin-meaning.html',{waitUntil:'domcontentloaded',timeout:45000});
      await page.waitForFunction(()=>window.Meaning&&window.MeaningEngine&&window.Meaning?.map?.loaded?.()===true,null,{timeout:30000});
      await page.waitForFunction(()=>window.BerlinXray?.ready===true,null,{timeout:10000});

      await page.locator('#startCenter').click();
      await page.waitForFunction(()=>window.BerlinXray?.active===true && !document.getElementById('xrayStage').classList.contains('hidden'),null,{timeout:15000});
      assert.equal(await page.locator('#xrayStage').isVisible(),true);
      assert.equal(await page.locator('#meaningPanel').isVisible(),false);

      await page.locator('[data-xray="history"]').click();
      await page.waitForFunction(()=>document.getElementById('xrayReadoutMeta')?.textContent?.includes('historical/structural evidence'),null,{timeout:15000});
      assert.ok((await page.locator('#xrayStory').textContent()).includes('Old Berlin still leaks through'));

      await page.locator('#xrayTimeSlider').fill('0');
      await page.waitForFunction(()=>document.body.classList.contains('xray-past'));
      assert.ok((await page.locator('#xrayReadoutLabel').textContent()).includes('BUILT / 1989'));

      await page.locator('[data-xray="nature"]').click();
      await page.waitForFunction(()=>document.body.classList.contains('xray-nature'));
      await page.waitForFunction(()=>document.getElementById('xrayReadoutMeta')?.textContent?.includes('official Berlin WFS'),null,{timeout:15000});
      assert.ok((await page.locator('#xrayReadoutMeta').textContent()).includes('official Berlin WFS'));

      await page.locator('[data-xray="live"]').click();
      await page.locator('#xrayTimeSlider').fill('2');
      await page.waitForFunction(()=>document.body.classList.contains('xray-future'));
      assert.ok((await page.locator('#xrayStory').textContent()).includes('twelve hours from now'));

      const cameraBefore=await page.evaluate(()=>({center:window.Meaning.map.getCenter().toArray(),zoom:window.Meaning.map.getZoom()}));
      await page.locator('[data-xray="people"]').click();
      await page.waitForFunction(()=>document.body.classList.contains('xray-people'));
      const cameraAfterLens=await page.evaluate(()=>({center:window.Meaning.map.getCenter().toArray(),zoom:window.Meaning.map.getZoom()}));
      assert.ok(Math.abs(cameraBefore.center[0]-cameraAfterLens.center[0])<0.0001);
      assert.ok(Math.abs(cameraBefore.center[1]-cameraAfterLens.center[1])<0.0001);
      assert.ok(Math.abs(cameraBefore.zoom-cameraAfterLens.zoom)<0.001);

      await page.locator('#openMeaningDetails').click();
      await page.waitForFunction(()=>!document.getElementById('meaningPanel').classList.contains('hidden'));
      assert.equal(await page.locator('#continuousSheet').getAttribute('data-sheet-state'),'expanded');
      assert.ok((await page.locator('#meaningCards .meaning-card').count())>=4);

      await page.locator('#closeMeaning').click();
      assert.equal(await page.locator('#continuousSheet').getAttribute('data-sheet-state'),'peek');

      await page.locator('#continuousMenu').click();
      await page.locator('[data-menu-action="visitor"]').click();
      assert.ok((await page.locator('[data-persona="visitor"]').getAttribute('class')||'').includes('active'));
      await page.locator('#openMeaningDetails').click();
      await page.waitForFunction(()=>!document.getElementById('meaningPanel').classList.contains('hidden'));

      const firstCard=page.locator('#meaningCards .meaning-card').first();
      await firstCard.locator('[data-why]').click();
      assert.ok((await firstCard.getAttribute('class')||'').includes('open'));
      const firstRating=firstCard.locator('[data-rate="useful"]');
      await firstRating.click();
      assert.ok((await firstRating.getAttribute('class')||'').includes('active'));

      if(spec.name==='desktop'){
        await page.locator('#continuousCompare').click();
        await page.waitForFunction(()=>!document.getElementById('meaningPick').classList.contains('hidden'));
        const canvas=page.locator('#meaningMap canvas');
        const box=await canvas.boundingBox();
        assert.ok(box);
        await page.mouse.click(Math.round(box.x+box.width*.72),Math.round(box.y+box.height*.42));
        await page.waitForFunction(()=>!document.getElementById('continuousCompareResult').classList.contains('hidden'),null,{timeout:15000});
        assert.ok((await page.locator('#compareInsightB').textContent()).length>3);
        await page.locator('#closeContinuousCompare').click();

        await page.locator('#continuousMenu').click();
        await page.locator('[data-menu-action="test"]').click();
        await page.locator('#runMeaningTest').click();
        await page.waitForFunction(()=>document.getElementById('testResults')?.textContent?.includes('Average candidate count'),null,{timeout:30000});
        assert.ok((await page.locator('#testResults').textContent()).includes('2+ lenses represented'));
        await page.locator('#closeTest').click();
      }

      await page.screenshot({path:`${output}/${spec.name}.png`});
      assert.deepEqual(errors,[]);
      result.status='passed';
    }catch(error){
      result.status='failed';result.error=String(error.stack||error);
      await page.screenshot({path:`${output}/${spec.name}-failure.png`}).catch(()=>{});
    }
    await context.close();
  }
}finally{
  await browser.close();
  await new Promise(r=>server.close(r));
  await writeFile(`${output}/report.json`,JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
}
if(report.tests.some(t=>t.status!=='passed'))process.exitCode=1;
