/* CITY THREAD v0.7 / THE BRIEF — playtest gate
 * Makes real decisions against immutable Berlin-WFS-derived metrics.
 * Each screenshot captures actual Chromium output, not a concept mockup.
 */
import assert from "node:assert/strict";
import {createServer} from "node:http";
import {readFile,mkdir,stat} from "node:fs/promises";
import {join,resolve,dirname,extname} from "node:path";
import {fileURLToPath} from "node:url";
import {chromium} from "playwright";

const root=resolve(dirname(fileURLToPath(import.meta.url)),"..");
const pub=join(root,"public");
const out=join(root,"map-test-results");
const label=process.env.SMOKE_LABEL||"local";
let server,base=process.env.SMOKE_BASE_URL?new URL("city-thread/brief/",process.env.SMOKE_BASE_URL).toString():null;
const mime={".html":"text/html; charset=utf-8",".js":"text/javascript; charset=utf-8",".css":"text/css; charset=utf-8",".json":"application/json; charset=utf-8"};
if(!base){
 server=createServer(async(req,res)=>{
  try{
   const url=decodeURIComponent(new URL(req.url,"http://localhost").pathname).replace(/^\/+/,"");
   if(url.includes(".."))throw Error("Invalid path");
   let file=resolve(pub,url);
   if(!file.startsWith(pub+"/"))throw Error("Outside public root");
   if((await stat(file)).isDirectory())file=join(file,"index.html");
   res.writeHead(200,{"content-type":mime[extname(file)]||"application/octet-stream","cache-control":"no-store"});
   res.end(await readFile(file));
  }catch(e){res.writeHead(404);res.end("Missing")}
 });
 await new Promise(done=>server.listen(0,"127.0.0.1",done));
 base="http://127.0.0.1:"+server.address().port+"/city-thread/brief/";
}
const browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
const issues=[];
async function check(name,fn){
 try{await fn();console.log("PASS",name);}
 catch(e){issues.push({name,error:String(e)});console.error("FAIL",name,e.message);}
}
async function ready(page){
 await page.goto(base,{waitUntil:"domcontentloaded"});
 await page.waitForFunction(()=>document.querySelector("#stage-brief")?.hidden===false||document.querySelector("#error")?.hidden===false,null,{timeout:18000});
 assert.equal(await page.locator("#error").isVisible(),false,"Data was rejected; do not show a usable mission");
}
async function screenshot(page,part){
 await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:join(out,"city-thread-v07-"+label+"-"+part+".png"),fullPage:true});
}
try{
 await mkdir(out,{recursive:true});
 const ctx=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1,acceptDownloads:true,permissions:["clipboard-read","clipboard-write"]});
 await ctx.route(/^https:\/\/tile\.openstreetmap\.org\//,route=>route.abort());
 const page=await ctx.newPage();
 page.on("pageerror",e=>issues.push({name:"Uncaught desktop JS",error:String(e)}));
 await check("Real WFS data and genuine three-candidate opening mission",async()=>{
  await ready(page);
  assert.equal(await page.locator("#brief-options button").count(),3);
  assert.equal(await page.locator("#map-svg [data-pin]").count(),3);
  assert.equal(await page.locator("#map-svg .climate-polygon").count(),154);
  assert.equal(await page.locator("#to-evidence").isDisabled(),true);
  assert.match(await page.locator("#stage-brief").textContent(),/FIKTIVE MISSION/);
  assert.match(await page.locator("#world-stat").textContent(),/03 KANDIDATEN/);
  assert.match(await page.locator("#brief-options").textContent(),/\+24/);
  assert.match(await page.locator("#brief-options").textContent(),/\+21/);
  assert.match(await page.locator("#brief-options").textContent(),/\+20/);
 });
 await screenshot(page,"brief-desktop");

 await check("Your first choice activates real, finite connections",async()=>{
  await page.locator('#brief-options [data-pick="A"]').click();
  assert.equal(await page.locator("#to-evidence").isDisabled(),false);
  assert.match(await page.locator("#initial-hint").textContent(),/Deine erste Idee: A/);
  assert.equal(await page.locator("#map-svg .connection").count(),24);
  assert.equal(await page.locator("#map-svg .new-point").count(),24);
  await page.locator("#to-evidence").click();
  assert.equal(await page.locator("#stage-evidence").isVisible(),true);
  assert.match(await page.locator("#first-choice").textContent(),/A/);
  assert.equal(await page.locator("#to-decision").isDisabled(),true);
 });
 await screenshot(page,"reveal-desktop");

 await check("Second evidence layer creates a real A/B/C trade-off",async()=>{
  const evidence=await page.locator("#evidence-rows").textContent();
  assert.match(evidence,/738m/);
  assert.match(evidence,/24/);
  assert.match(evidence,/10/);
  assert.match(await page.locator("#reveal-copy").textContent(),/C liegt rund 738 m/);
  await page.locator('[data-priority="severity"]').click();
  assert.match(await page.locator("#priority-feedback").textContent(),/liefert B den höchsten Modellwert/);
  assert.equal(await page.locator("#to-decision").isDisabled(),false);
  await page.locator("#to-decision").click();
  assert.equal(await page.locator("#stage-decision").isVisible(),true);
  assert.equal(await page.locator("#commit").isDisabled(),true);
 });
 await screenshot(page,"decision-desktop");

 await check("Human choice remains free, with explicit next check and acknowledgement",async()=>{
  await page.locator('#decision-options [data-pick="B"]').click();
  assert.match(await page.locator("#tradeoff-copy").textContent(),/Dein Kriterium spricht im Modell für B/);
  assert.equal(await page.locator("#commit").isDisabled(),true);
  await page.locator('[data-check="access"]').click();
  assert.equal(await page.locator("#commit").isDisabled(),true);
  await page.locator("#consent").check();
  assert.equal(await page.locator("#commit").isDisabled(),false);
  await page.locator("#commit").click();
  assert.equal(await page.locator("#stage-result").isVisible(),true);
  assert.equal(await page.locator("#result-letter").textContent(),"B");
  assert.match(await page.locator("#result-gain").textContent(),/\+21/);
  assert.match(await page.locator("#stage-result").textContent(),/NICHT EINGEREICHT/);
  assert.match(await page.locator("#result-check").textContent(),/Fusswege/);
 });
 await screenshot(page,"receipt-desktop");

 await check("Local case file and reproducible share URL",async()=>{
  const [dl]=await Promise.all([page.waitForEvent("download"),page.locator("#download-case").click()]);
  assert.equal(dl.suggestedFilename(),"CITY_THREAD_THE_BRIEF_Fallakte.md");
  const local=join(out,"city-thread-v07-case.md");await dl.saveAs(local);
  const txt=await readFile(local,"utf8");
  assert.match(txt,/Gewählter Standort: B/);
  assert.match(txt,/Erster notwendiger Prüfschritt: Fusswege/);
  assert.match(txt,/21 bisher unberücksichtigte/);
  assert.match(txt,/Keine tatsächliche Finanzierung oder behördliche Auswahl/);
  await page.locator("#share-case").click();
  const url=await page.evaluate(()=>navigator.clipboard.readText());
  assert.equal(new URL(url).searchParams.get("site"),"B");
  assert.equal(new URL(url).searchParams.get("priority"),"severity");
  assert.equal(new URL(url).searchParams.get("check"),"access");
  assert.equal(new URL(url).searchParams.get("done"),"1");
  await page.goto(url,{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelector("#stage-result")?.hidden===false,null,{timeout:18000});
  assert.equal(await page.locator("#result-letter").textContent(),"B");
  assert.match(await page.locator("#result-priority").textContent(),/stärkere|sehr ungünstig/i);
 });

 await check("Replay and principled disagreement: own choice vs model leader",async()=>{
  await page.locator("#play-again").click();
  assert.equal(await page.locator("#stage-brief").isVisible(),true);
  assert.equal(await page.locator("#to-evidence").isDisabled(),true);
  assert.equal(new URL(page.url()).searchParams.has("done"),false);
  await page.locator('#map-svg [data-pin="C"]').click();
  assert.match(await page.locator("#initial-hint").textContent(),/C/);
  await page.locator("#to-evidence").click();
  await page.locator('[data-priority="coverage"]').click();
  assert.match(await page.locator("#priority-feedback").textContent(),/liefert A/);
  await page.locator("#to-decision").click();
  assert.match(await page.locator("#tradeoff-copy").textContent(),/A um 4 Rasterpunkte stärker/);
  await page.locator('[data-check="operation"]').click();
  await page.locator("#consent").check();
  await page.locator("#commit").click();
  assert.equal(await page.locator("#result-letter").textContent(),"C");
  assert.match(await page.locator("#result-reflection").textContent(),/anderen Modellspitze/);
 });

 await check("Lost WFS data results in an honest stop, not invented recommendations",async()=>{
  const blocked=await ctx.newPage();
  await blocked.route("**/heat-3.json",route=>route.abort());
  blocked.on("pageerror",e=>issues.push({name:"Offline fallback JS",error:String(e)}));
  await blocked.goto(base,{waitUntil:"domcontentloaded"});
  await blocked.waitForFunction(()=>document.querySelector("#error")?.hidden===false,null,{timeout:18000});
  assert.equal(await blocked.locator("#stage-brief").isVisible(),false);
  assert.equal(await blocked.locator("#brief-options button").count(),0);
  assert.match(await blocked.locator("#error-message").textContent(),/Ohne belastbare Daten/);
  await blocked.close();
 });

 const mobileCtx=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true,reducedMotion:"reduce"});
 await mobileCtx.route(/^https:\/\/tile\.openstreetmap\.org\//,route=>route.abort());
 const mobile=await mobileCtx.newPage();
 mobile.on("pageerror",e=>issues.push({name:"Uncaught mobile JS",error:String(e)}));
 await check("Accessible mobile decision loop, real map pins, no sideways overflow",async()=>{
  await ready(mobile);
  const dim=await mobile.evaluate(()=>({scroll:document.documentElement.scrollWidth,inner:innerWidth}));
  assert.ok(dim.scroll<=dim.inner+2,JSON.stringify(dim));
  assert.equal(await mobile.locator("#brief-options button").count(),3);
  await mobile.locator('#brief-options [data-pick="B"]').click();
  assert.equal(await mobile.locator("#map-svg .connection").count(),21);
  await mobile.locator("#to-evidence").click();
  await mobile.locator('[data-priority="gap"]').click();
  assert.match(await mobile.locator("#priority-feedback").textContent(),/liefert C/);
  await mobile.locator("#to-decision").click();
  await mobile.locator('#decision-options [data-pick="C"]').click();
  await mobile.locator('[data-check="feasibility"]').click();
  await mobile.locator("#consent").check();
  await mobile.locator("#commit").click();
  assert.equal(await mobile.locator("#result-letter").textContent(),"C");
 });
 await screenshot(mobile,"receipt-mobile");
 await mobileCtx.close();await ctx.close();
}finally{await browser.close();if(server)await new Promise(done=>server.close(done))}
if(issues.length){console.error(JSON.stringify(issues,null,2));process.exitCode=1}
else console.log("CITY THREAD v0.7: 8/8 narrative, evidence, governance and responsive browser checks PASS.");
