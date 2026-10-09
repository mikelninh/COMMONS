/* CITY THREAD v0.6 · Ripple + Scenario Duel browser QA.
   Local: node scripts/city-thread-v06-smoke.mjs
   Deployed: SMOKE_BASE_URL=https://mikelninh.github.io/COMMONS/ SMOKE_LABEL=deployed node scripts/city-thread-v06-smoke.mjs
   Does not rely on external basemap tiles or collect analytics. */
import assert from "node:assert/strict";
import {createServer} from "node:http";
import {readFile,stat,mkdir} from "node:fs/promises";
import {join,resolve,extname,dirname} from "node:path";
import {fileURLToPath} from "node:url";
import {chromium} from "playwright";

const root=resolve(dirname(fileURLToPath(import.meta.url)),".."),pub=join(root,"public");
const screenshots=join(root,"map-test-results"),label=process.env.SMOKE_LABEL||"local";
let base=process.env.SMOKE_BASE_URL?new URL("city-thread/mission/",process.env.SMOKE_BASE_URL).toString():null,server;
const mime={".html":"text/html; charset=utf-8",".js":"text/javascript; charset=utf-8",".css":"text/css; charset=utf-8",".json":"application/json; charset=utf-8",".ttl":"text/turtle; charset=utf-8"};
if(!base){
 server=createServer(async(req,res)=>{
  try{
   const q=decodeURIComponent(new URL(req.url,"http://localhost").pathname).replace(/^\/+/,"");
   if(q.includes(".."))throw Error("Invalid path");
   let target=resolve(pub,q);
   if(!target.startsWith(pub+"/"))throw Error("Outside root");
   if((await stat(target)).isDirectory())target=join(target,"index.html");
   res.writeHead(200,{"content-type":mime[extname(target)]||"application/octet-stream","cache-control":"no-store"});
   res.end(await readFile(target));
  }catch(e){res.writeHead(404);res.end("Missing");}
 });
 await new Promise(done=>server.listen(0,"127.0.0.1",done));
 base="http://127.0.0.1:"+server.address().port+"/city-thread/mission/";
}
const browser=await chromium.launch({headless:true,args:["--no-sandbox"]}),errors=[];
const check=async(name,fn)=>{try{await fn();console.log("PASS",name);}catch(e){errors.push({name,error:String(e)});console.error("FAIL",name,e.message)}};
async function loaded(page){await page.goto(base,{waitUntil:"domcontentloaded"});await page.waitForFunction(()=>document.querySelector("#map-data-status")?.textContent?.includes("242 STANDORTE / 154 POLYGONE"),null,{timeout:17000})}
const count=async locator=>Number((await locator.textContent()).replace(/[^\d]/g,""));
try{
 await mkdir(screenshots,{recursive:true});
 const desktopContext=await browser.newContext({viewport:{width:1440,height:900},acceptDownloads:true,permissions:["clipboard-read","clipboard-write"]});
 const page=await desktopContext.newPage();
 page.on("pageerror",e=>errors.push({name:"Desktop JS exception",error:String(e)}));
 await check("Real WFS data, immediate connections and sound opt-in only",async()=>{
  await loaded(page);
  const gain=Number((await page.locator("#gain-value").textContent()).replaceAll(".",""));
  assert.ok(gain>0,"Initial scenario must have a useful non-zero model result");
  assert.equal(await page.locator("#mission-map .ripple-thread").count(),gain>46?46:gain);
  assert.equal(await page.locator("#ripple-sound").getAttribute("aria-pressed"),"false");
  assert.match(await page.locator("#duel-toggle").textContent(),/Zweiten Ort vergleichen/);
 });
 await page.screenshot({path:join(screenshots,"city-thread-v06-"+label+"-solo-desktop.png"),fullPage:true});
 await check("Ripple on actual suggestion changes, not imaginary endpoints",async()=>{
  await page.locator("#suggestion-buttons button").nth(1).click();
  const g=Number(await page.locator("#gain-value").textContent());
  assert.ok(g>=0);
  assert.equal(await page.locator("#mission-map .ripple-thread").count(),Math.min(g,46));
  assert.equal(await page.locator("#mission-map .ripple-wave").count(),g?1:0);
  assert.equal(await page.locator("#ripple-message").isVisible(),g>0);
  await page.locator("#ripple-sound").click();
  assert.equal(await page.locator("#ripple-sound").getAttribute("aria-pressed"),"true");
  await page.locator("#ripple-sound").click();
  assert.equal(await page.locator("#ripple-sound").getAttribute("aria-pressed"),"false");
 });
 await check("Duel: two independent scores and genuinely editable B",async()=>{
  await page.locator("#duel-toggle").click();
  assert.equal(await page.locator("#duel-toggle").getAttribute("aria-pressed"),"true");
  assert.equal(await page.locator("#duel-board").isVisible(),true);
  assert.equal(await page.locator("#duel-b").getAttribute("aria-pressed"),"true");
  assert.equal(await page.locator("#mission-map .duel-other-hit").count(),1);
  const a=await count(page.locator("#duel-score-a"));
  const b=await count(page.locator("#duel-score-b"));
  assert.ok(a>=0&&b>=0);
  const activeScore=Number(await page.locator("#gain-value").textContent());
  assert.equal(activeScore,b,"Visible active-score must match B");
  const beforeB=await page.locator("#site-coordinate").textContent();
  await page.locator("#suggestion-buttons button").nth(2).click();
  assert.notEqual(await page.locator("#site-coordinate").textContent(),beforeB);
  assert.equal(await count(page.locator("#duel-score-a")),a,"Editing B must preserve A");
  await page.locator("#duel-a").click();
  assert.equal(await page.locator("#duel-a").getAttribute("aria-pressed"),"true");
  assert.equal(await page.locator("#gain-value").textContent(),String(a));
 });
 await page.screenshot({path:join(screenshots,"city-thread-v06-"+label+"-duel-desktop.png"),fullPage:true});
 await check("Before/after hides proposals, return restores A and B",async()=>{
  await page.locator("#view-before").click();
  assert.equal(await page.locator("#candidate-hit").count(),0);
  assert.equal(await page.locator("#mission-map .duel-other-hit").count(),0);
  assert.equal(await page.locator("#mission-map .ripple-thread").count(),0);
  await page.locator("#view-after").click();
  assert.equal(await page.locator("#candidate-hit").count(),1);
  assert.equal(await page.locator("#mission-map .duel-other-hit").count(),1);
  await page.locator("#radius").fill("400");
  assert.equal(await page.locator("#radius-label").textContent(),"400 m");
  assert.equal(await page.locator("#gain-value").textContent(),String(await count(page.locator("#duel-score-a"))));
 });
 await check("Duel URL is reproducible and retains both locations",async()=>{
  await page.locator("#copy-scenario").click();
  const link=await page.evaluate(()=>navigator.clipboard.readText());
  const u=new URL(link);
  assert.equal(u.searchParams.get("duel"),"1");
  for(const p of ["aLon","aLat","bLon","bLat","radius","slot"])assert.ok(u.searchParams.has(p),p+" missing");
  const a=await page.locator("#duel-score-a").textContent(),b=await page.locator("#duel-score-b").textContent();
  await page.goto(link,{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelector("#map-data-status")?.textContent?.includes("242 STANDORTE"),null,{timeout:17000});
  assert.equal(await page.locator("#duel-board").isVisible(),true);
  assert.equal(await page.locator("#duel-score-a").textContent(),a);
  assert.equal(await page.locator("#duel-score-b").textContent(),b);
  assert.equal(await page.locator("#radius-label").textContent(),"400 m");
 });
 await check("Duel report respects human review and documents A/B",async()=>{
  await page.locator("#jump-evidence").click();
  assert.equal(await page.locator("#evidence").getAttribute("open"),"");
  await page.locator("#download-report").click();
  assert.match(await page.locator("#review-hint").textContent(),/Bitte zuerst bestätigen/);
  await page.locator("#review-checkbox").check();
  const [dl]=await Promise.all([page.waitForEvent("download"),page.locator("#download-report").click()]);
  const file=join(screenshots,"city-thread-v06-audit.md");await dl.saveAs(file);
  const report=await readFile(file,"utf8");
  assert.match(report,/Scenario Duel/);
  assert.match(report,/A: 52\./);
  assert.match(report,/B: 52\./);
  assert.match(report,/keine Bauempfehlung/);
  assert.match(report,/yes \(not official approval\)/);
  await page.locator("#close-evidence").click();
 });
 await check("Responsive mobile duel controls and map-first accessibility",async()=>{
  const mobileCtx=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true});
  const mobile=await mobileCtx.newPage();
  mobile.on("pageerror",e=>errors.push({name:"Mobile JS exception",error:String(e)}));
  await loaded(mobile);
  const metrics=await mobile.evaluate(()=>({
   scrollWidth:document.documentElement.scrollWidth,width:innerWidth,
   mapY:document.querySelector("#mission-map").getBoundingClientRect().y,
   mapHeight:document.querySelector("#mission-map").getBoundingClientRect().height
  }));
  assert.ok(metrics.scrollWidth<=metrics.width+2,JSON.stringify(metrics));
  assert.ok(metrics.mapY<844,"Map must appear on first screen");
  assert.equal(await mobile.locator("#mobile-feedback").isVisible(),true);
  await mobile.locator("#duel-toggle").click();
  assert.equal(await mobile.locator("#duel-board").isVisible(),true);
  await mobile.locator("#duel-a").click();
  assert.equal(await mobile.locator("#duel-a").getAttribute("aria-pressed"),"true");
  await mobile.screenshot({path:join(screenshots,"city-thread-v06-"+label+"-mobile.png"),fullPage:true});
  await mobileCtx.close();
 });
 await desktopContext.close();
}finally{await browser.close();if(server)await new Promise(done=>server.close(done))}
if(errors.length){console.error(JSON.stringify(errors,null,2));process.exitCode=1}
else console.log("CITY THREAD v0.6: 7/7 browser checks PASS.");
