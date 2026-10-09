/* CITY THREAD v0.3 browser smoke test. Runs on the same Chromium used by WORLD PULSE.
   Usage: node scripts/city-thread-smoke.mjs
   Deployed: SMOKE_BASE_URL=https://example.github.io/COMMONS/ SMOKE_LABEL=deployed node scripts/city-thread-smoke.mjs
*/
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const files = path.join(project,"public","city-thread");
const reportDir=path.join(project,"map-test-results");
const label=process.env.SMOKE_LABEL || "local";
const mime={".html":"text/html; charset=utf-8",".css":"text/css; charset=utf-8",".js":"text/javascript; charset=utf-8",".json":"application/json; charset=utf-8",".ttl":"text/turtle; charset=utf-8"};
let server;
let base=process.env.SMOKE_BASE_URL ? new URL("city-thread/",process.env.SMOKE_BASE_URL).toString() : null;
if(!base){
  server=createServer(async (req,res)=>{
    try{
      const pathname=decodeURIComponent(new URL(req.url,"http://127.0.0.1").pathname);
      const candidate=path.resolve(files,"."+pathname.replace(/^\/city-thread/,""));
      if(!candidate.startsWith(files+path.sep)&&candidate!==files)throw Error("Path outside site");
      const filename=candidate===files?path.join(files,"index.html"):candidate;
      const buffer=await readFile(filename);
      res.writeHead(200,{"Content-Type":mime[path.extname(filename)]||"application/octet-stream","Cache-Control":"no-store"});res.end(buffer);
    }catch(err){res.writeHead(404);res.end("Missing");}
  });
  await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
  base="http://127.0.0.1:"+server.address().port+"/city-thread/";
}
const browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
const errors=[];
const check=async(name,fn)=>{
 try{await fn();console.log("PASS:",name);}
 catch(e){console.error("FAIL:",name, e.message);errors.push({name,error:String(e)});}
};
let page, mobile;
try{
 await mkdir(reportDir,{recursive:true});
 const ctx=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1});
 page=await ctx.newPage();
 page.on("pageerror",e=>errors.push({name:"JavaScript exception",error:String(e)}));
 await check("Atlas, real WFS snapshot and visible map",async()=>{
  await page.goto(base,{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelector("#metric-places")?.textContent?.trim()==="120",{timeout:15000});
  assert.equal((await page.locator("#metric-districts").textContent()).trim(),"12");
  assert.equal(await page.locator("#atlas-svg .map-dot").count(),120);
  assert.match(await page.locator("#spotlight").textContent(),/WFS|AUSGEWÄHLTER|Kottbusser|Dennewitz/i);
 });
 await page.screenshot({path:path.join(reportDir,"city-thread-v03-"+label+"-desktop.png"),fullPage:true});
 await check("Click a fountain and trace its relationship",async()=>{
  await page.locator('#place-list .place[data-id="1"]').click();
  assert.match(await page.locator("#spotlight h3").textContent(),/Sangerhauser Weg/);
  await page.locator('.nav-item[data-view="graph"]').click();
  assert.match(await page.locator("#inspect-name").textContent(),/Sangerhauser Weg/);
  assert.match(await page.locator("#triple-list").textContent(),/prov:wasDerivedFrom/);
  await page.locator('#graph-svg [aria-label="Verbindung BEZIRK erklären"]').click();
  assert.match(await page.locator("#edge-explanation").textContent(),/Neukölln/);
 });
 await check("Question explorer and transparent SPARQL examples",async()=>{
  await page.locator('.nav-item[data-view="ask"]').click();
  assert.match(await page.locator("#answer-pill").textContent(),/12 ERGEBNISSE/);
  assert.equal(await page.locator("#answer-table tbody tr").count(),12);
  await page.locator("#toggle-code").click();
  assert.equal(await page.locator("#toggle-code").getAttribute("aria-expanded"),"true");
  assert.match(await page.locator("#sparql-code").textContent(),/SELECT \?name \?district/);
  await page.locator(".question-option").nth(3).click();
  assert.equal(await page.locator("#answer-table tbody tr").count(),12);
 });
 await check("Data provenance and injection-based checks",async()=>{
  await page.locator('.nav-item[data-view="trust"]').click();
  await page.locator("#run-validation").click();
  assert.match(await page.locator("#validation-output").textContent(),/PASS/);
  await page.locator('[data-scenario="coords"]').click();
  await page.locator("#run-validation").click();
  assert.match(await page.locator("#validation-output").textContent(),/FAIL/);
  assert.match(await page.locator("#validation-output").textContent(),/Koordinaten/);
  await page.locator('[data-scenario="source"]').click();
  await page.locator("#run-validation").click();
  assert.match(await page.locator("#validation-output").textContent(),/FAIL/);
  assert.match(await page.locator("#validation-output").textContent(),/Provenienz/);
 });
 await check("RDF lesson and quiz",async()=>{
  await page.locator('.nav-item[data-view="learn"]').click();
  assert.match(await page.locator("#real-triple").textContent(),/ct:inDistrict/);
  await page.locator('[data-choice="district"]').click();
  assert.match(await page.locator("#quiz-feedback").textContent(),/Genau!/);
 });
 const mobileContext=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true});
 mobile=await mobileContext.newPage();
 mobile.on("pageerror",e=>errors.push({name:"Mobile JavaScript exception",error:String(e)}));
 await check("Mobile onboarding with no horizontal overflow",async()=>{
  await mobile.goto(base,{waitUntil:"domcontentloaded"});
  await mobile.waitForFunction(()=>document.querySelector("#metric-places")?.textContent?.trim()==="120",{timeout:15000});
  const width=await mobile.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:window.innerWidth}));
  assert.ok(width.scroll<=width.viewport+2,JSON.stringify(width));
  assert.equal(await mobile.locator("#atlas-svg .map-dot").count(),120);
 });
 await mobile.screenshot({path:path.join(reportDir,"city-thread-v03-"+label+"-mobile.png"),fullPage:true});
 await mobileContext.close();await ctx.close();
}finally{await browser.close();if(server)await new Promise(resolve=>server.close(resolve));}
if(errors.length){console.error(JSON.stringify(errors,null,2));process.exitCode=1;}
else console.log("CITY THREAD v0.3: 6/6 browser checks PASS; desktop & mobile screenshots saved.");
