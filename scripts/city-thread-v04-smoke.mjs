/* CITY THREAD v0.4 Playwright smoke gate. */
import assert from "node:assert/strict";
import {createServer} from "node:http";
import {readFile,stat,mkdir} from "node:fs/promises";
import {join,resolve,extname,dirname} from "node:path";
import {fileURLToPath} from "node:url";
import {chromium} from "playwright";
const root=resolve(dirname(fileURLToPath(import.meta.url)),".."),pub=join(root,"public"),out=join(root,"map-test-results");
const label=process.env.SMOKE_LABEL||"local";
let base=process.env.SMOKE_BASE_URL?new URL("city-thread/mission/",process.env.SMOKE_BASE_URL).toString():null,server;
const mime={".html":"text/html; charset=utf-8",".js":"text/javascript; charset=utf-8",".css":"text/css; charset=utf-8",".json":"application/json; charset=utf-8",".ttl":"text/turtle; charset=utf-8"};
if(!base){
 server=createServer(async(req,res)=>{try{
  const q=decodeURIComponent(new URL(req.url,"http://localhost").pathname).replace(/^\/+/,"");
  if(q.includes(".."))throw Error("Invalid pathname");
  let file=resolve(pub,q);if(!file.startsWith(pub+"/"))throw Error("Outside root");
  if((await stat(file)).isDirectory())file=join(file,"index.html");
  res.writeHead(200,{"content-type":mime[extname(file)]||"application/octet-stream","cache-control":"no-store"});
  res.end(await readFile(file));
 }catch{res.writeHead(404);res.end("Missing")}});
 await new Promise(done=>server.listen(0,"127.0.0.1",done));
 base="http://127.0.0.1:"+server.address().port+"/city-thread/mission/";
}
const browser=await chromium.launch({headless:true,args:["--no-sandbox"]}),errors=[];
const check=async(name,fn)=>{try{await fn();console.log("PASS",name)}catch(e){errors.push({name,error:String(e)});console.error("FAIL",name,e.message)}};
async function load(page){await page.goto(base,{waitUntil:"domcontentloaded"});await page.waitForFunction(()=>document.querySelector("#map-data-status")?.textContent?.includes("242 STANDORTE / 154 POLYGONE"),null,{timeout:16000});}
try{
 await mkdir(out,{recursive:true});
 const context=await browser.newContext({viewport:{width:1440,height:900},acceptDownloads:true,permissions:["clipboard-read","clipboard-write"]}),page=await context.newPage();
 page.on("pageerror",e=>errors.push({name:"Uncaught desktop JS",error:String(e)}));
 await check("Load full original WFS snapshots and calculate before/after",async()=>{
  await load(page);
  const before=Number(await page.locator("#before-count").textContent()),after=Number(await page.locator("#after-count").textContent());
  assert.ok(before>after&&after>=0,"Expected actual improvement, got "+before+" to "+after);
  assert.equal(await page.locator("#suggestion-buttons button").count(),3);
  assert.equal(await page.locator("#mission-map .heat-polygon").count(),154);
 });
 await page.screenshot({path:join(out,"city-thread-v04-"+label+"-desktop.png"),fullPage:true});
 await check("Map layers, alternative locations and distance sensitivity",async()=>{
  const initial=await page.locator("#site-coordinate").textContent();
  await page.locator("#suggestion-buttons button").nth(1).click();
  assert.notEqual(await page.locator("#site-coordinate").textContent(),initial);
  await page.locator("#layers-menu summary").click();
  await page.locator("label:has(#layer-heat)").click();
  assert.equal(await page.locator("#mission-map .heat-polygon").count(),0);
  await page.locator("label:has(#layer-heat)").click();
  assert.equal(await page.locator("#mission-map .heat-polygon").count(),154);
  await page.locator("label:has(#layer-water)").click();
  assert.equal(await page.locator("#mission-map .fountain-dot").count(),0);
  await page.locator("label:has(#layer-water)").click();
  await page.locator("#layers-menu summary").click();
  await page.locator("#radius").fill("400");
  assert.equal(await page.locator("#radius-label").textContent(),"400 m");
 });
 await check("Compare shows a real before and after map state",async()=>{
  const before=await page.locator("#before-count").textContent(),after=await page.locator("#after-count").textContent();
  await page.locator("#view-before").click();
  assert.equal(await page.locator("#view-before").getAttribute("aria-pressed"),"true");
  assert.equal(await page.locator("#candidate-hit").count(),0);
  await page.locator("#view-after").click();
  assert.equal(await page.locator("#view-after").getAttribute("aria-pressed"),"true");
  assert.equal(await page.locator("#candidate-hit").count(),1);
  assert.equal(await page.locator("#before-count").textContent(),before);
  assert.equal(await page.locator("#after-count").textContent(),after);
 });
 await check("Click map to update site and trace its semantic evidence",async()=>{
  const initial=await page.locator("#site-coordinate").textContent();
  const map=page.locator("#mission-map"),rect=await map.boundingBox();
  await map.click({position:{x:rect.width*.53,y:rect.height*.49},force:true});
  assert.notEqual(await page.locator("#site-coordinate").textContent(),initial);
  assert.match(await page.locator("#evidence-triples").textContent(),/ct:heatClass/);
  assert.match(await page.locator("#evidence-triples").textContent(),/ct:nearestDistanceMeters/);
 });
 await check("Explicit human acknowledgement gates actual Markdown download",async()=>{
  await page.locator("#jump-evidence").click();
  assert.equal(await page.locator("#evidence").getAttribute("open"),"");
  await page.locator("#download-report").click();
  assert.match(await page.locator("#review-hint").textContent(),/Bitte zuerst bestätigen/);
  await page.locator("#review-checkbox").check();
  const [download]=await Promise.all([page.waitForEvent("download"),page.locator("#download-report").click()]);
  assert.equal(download.suggestedFilename(),"city-thread-standortpruefung-v04.md");
  const local=join(out,"city-thread-v04-report-test.md");await download.saveAs(local);
  const content=await readFile(local,"utf8");
  assert.match(content,/242 WFS-Inventarstandorte/);assert.match(content,/keine Bauempfehlung/);
  assert.match(content,/yes \(not official approval\)/);
  await page.locator("#close-evidence").click();
  assert.equal(await page.locator("#evidence").getAttribute("open"),null);
 });
 await check("Round-trip shared scenario and homepage discovery",async()=>{
  await page.locator("#copy-scenario").click();
  const link=await page.evaluate(()=>navigator.clipboard.readText());
  assert.ok(link.includes("lon=")&&link.includes("radius=400"));
  const coords=await page.locator("#site-coordinate").textContent();
  await page.goto(link,{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelector("#map-data-status")?.textContent?.includes("242 STANDORTE"),null,{timeout:16000});
  assert.equal(await page.locator("#radius-label").textContent(),"400 m");
  assert.equal(await page.locator("#site-coordinate").textContent(),coords);
  await page.goto(new URL("../",base).toString());
  await page.locator(".mission-feature .btn").click();
  await page.waitForURL(/\/city-thread\/mission\//);
  await page.waitForFunction(()=>document.querySelector("#map-data-status")?.textContent?.includes("242 STANDORTE"),null,{timeout:16000});
 });
 const mobileContext=await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true}),mobile=await mobileContext.newPage();
 mobile.on("pageerror",e=>errors.push({name:"Uncaught mobile JS",error:String(e)}));
 await check("Mobile touch layout, source loading and no horizontal overflow",async()=>{
  await load(mobile);
  const widths=await mobile.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:innerWidth}));
  assert.ok((await mobile.locator("#mission-map").boundingBox()).y<844,"Primary map must be visible without scrolling");
  assert.equal(await mobile.locator("#mobile-feedback").isVisible(),true);
  assert.match(await mobile.locator("#gain-overlay").textContent(),/\+\d+/);
  assert.ok(widths.scroll<=widths.viewport+2,JSON.stringify(widths));
  await mobile.locator("#suggestion-buttons button").nth(1).click();
  assert.match(await mobile.locator("#site-coordinate").textContent(),/52\./);
 });
 await mobile.screenshot({path:join(out,"city-thread-v04-"+label+"-mobile.png"),fullPage:true});
 await mobileContext.close();await context.close();
}finally{await browser.close();if(server)await new Promise(done=>server.close(done));}
if(errors.length){console.error(JSON.stringify(errors,null,2));process.exitCode=1;}
else console.log("CITY THREAD v0.5: 7/7 checks PASS (desktop and mobile).");
