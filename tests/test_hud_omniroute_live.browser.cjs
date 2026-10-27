'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const http=require('node:http');
const {spawn,spawnSync}=require('node:child_process');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const root=path.resolve(__dirname,'../dashboard/command-center');
const file=path.join(root,'native-v8-9','index.html');
const output=path.join(root,'qa-screenshots','live-sync');
const sizes=[[430,932,'iphone-portrait',true],[820,1180,'ipad-portrait',true],[1180,820,'ipad-landscape',true],[1366,768,'laptop',false],[1672,941,'desktop',false]];
let server,publicServer,externalServer,chrome,socket,tmp,serial=0;
const pending=new Map();
const cmd=(method,params={})=>new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}))});
const evalJS=async source=>{const r=await cmd('Runtime.evaluate',{expression:'(()=>{'+source+'})()',returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error('Browser JS error: '+JSON.stringify(r.exceptionDetails));return r.result.value};
const poll=async fn=>{for(let i=0;i<600;i++){try{const v=await fn();if(v)return v}catch{}await delay(100)}throw Error('Browser operation timed out')};
async function screenshot(name){const r=await cmd('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(path.join(output,name+'.png'),Buffer.from(r.data,'base64'))}
async function main(){
 const quotaScript=path.join(root,'native-v8-9/live-quota-board.js');
 const syntax=spawnSync(process.execPath,['--check',quotaScript],{encoding:'utf8'});
 assert.equal(syntax.status,0,'Quota widget syntax: '+syntax.stderr);
 fs.mkdirSync(output,{recursive:true});
 const {createBridge}=await import('../tools/hud_omniroute_bridge.mjs');
 let offline=false,requests=7;
 const publicOriginHolder={origin:''};
 publicServer=http.createServer((req,res)=>{res.writeHead(200,{'Content-Type':'text/html'});let page=fs.readFileSync(file,'utf8');page=page.replace("const trusted=url=>url.protocol==='https:'","const trusted=url=>url.origin==='"+publicOriginHolder.bridge+"'||url.protocol==='https:'");res.end(page);});
 await new Promise(r=>publicServer.listen(0,'127.0.0.1',r));
 const publicOrigin='http://127.0.0.1:'+publicServer.address().port;
 const b=createBridge({viewerOrigin:publicOrigin,hud:fs.readFileSync(file,'utf8'),adapter:fs.readFileSync(path.join(root,'native-v8-9/live-omniroute.js'),'utf8'),quotaAddon:fs.readFileSync(path.join(root,'native-v8-9/live-quota-board.js'),'utf8'),pairCode:'test-only',collect:async period=>{if(offline)throw Error('offline');return {schema_version:1,source:'local_omniroute_read_only_bridge',snapshot_at:new Date().toISOString(),period,inventory_count:12,request_count:10,usage_coverage:'complete_aggregate',connections:Array.from({length:9},(_,i)=>({provider:i?'connected-'+i:'provider',name:i?'connected-'+i:'provider',connection_count:1,enabled_count:1})),quota:{records:[{provider:'provider',account_slot:1,model_id:'provider/model-0',used:25,total:100,used_percent:25,unit:'requests',reset_at:'2030-01-01T00:00:00Z',fetched_at:new Date().toISOString()},{provider:'provider',account_slot:1,model_id:'provider/model-1',used:10,total:100,used_percent:10,unit:'requests',reset_at:'2030-01-01T00:00:00Z',fetched_at:new Date().toISOString()},{provider:'provider',account_slot:1,model_id:'provider/model-2',used:40,total:100,used_percent:40,unit:'requests',reset_at:'2030-01-01T00:00:00Z',fetched_at:new Date().toISOString()}]},models:Array.from({length:12},(_,i)=>({id:'provider/model-'+i,name:'provider/model-'+i,provider:'provider',requests:i===0?requests:0,tokens:i===0?70:0,request_share_percent:i===0?requests*10:0}))};}});
 const port=await b.listen();server=b.server;
 const origin='http://127.0.0.1:'+port;publicOriginHolder.bridge=origin;
 const paired=await fetch(origin+'/pair',{method:'POST',headers:{Origin:origin},body:'{"code":"test-only"}'});
 assert.equal(paired.status,200);
 const session=paired.headers.get('set-cookie').split(';')[0].split('=')[1];
 const bin=process.env.CHROME_BIN||['google-chrome','chromium','chromium-browser'].find(x=>spawnSync('which',[x],{stdio:'ignore'}).status===0);
 assert(bin,'Chrome unavailable');
 tmp=fs.mkdtempSync(path.join(os.tmpdir(),'rovor-live-browser-'));
 chrome=spawn(bin,['--headless=new','--no-sandbox','--disable-dev-shm-usage','--disable-gpu','--remote-debugging-port=0','--user-data-dir='+tmp,'about:blank'],{stdio:'ignore'});
 const debugPort=await poll(()=>{const f=path.join(tmp,'DevToolsActivePort');return fs.existsSync(f)?fs.readFileSync(f,'utf8').split('\n')[0]:null});
 const targets=await poll(async()=>{const r=await fetch('http://127.0.0.1:'+debugPort+'/json/list');return r.ok?await r.json():null});
 socket=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise((r,j)=>{socket.addEventListener('open',r,{once:true});socket.addEventListener('error',j,{once:true})});
 socket.addEventListener('message',e=>{const m=JSON.parse(e.data),p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}});
 await cmd('Page.enable');await cmd('Runtime.enable');await cmd('Network.enable');
 await cmd('Network.setCookie',{name:'rovor_hud',value:session,url:origin,httpOnly:true,sameSite:'Strict'});
 for(const [width,height,name,mobile] of sizes){
  await cmd('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile});
  await cmd('Page.navigate',{url:origin+'/'});
  await poll(()=>evalJS('return document.querySelectorAll("#workloadPanel [data-live-details]").length===9'));
  const home=await evalJS('return {pageWidth:document.documentElement.scrollWidth,viewport:innerWidth,panels:document.querySelectorAll(".rail .panel").length,nav:document.querySelectorAll(".nav-item").length,text:document.querySelector("#workloadPanel").textContent}');
  assert(home.pageWidth<=home.viewport+2,name+': overflow');assert.equal(home.panels,6);assert.equal(home.nav,5);assert(home.text.includes('CONNECTED'));assert(home.text.includes('connected-8'));
  await evalJS('document.querySelector(".panel-expand[data-view=workload]").click();return true');
  await poll(()=>evalJS('return document.querySelectorAll("[data-live-model].wl-model-entry").length===12'));
  const quotaDiag=await evalJS('return {helper:typeof window.ROVOR_QUOTA_BOARD,panels:document.querySelectorAll(".rvq-provider").length,board:!!document.querySelector(".rvq-board"),card:document.querySelector("#rovor-workload-popup .wl-card")?.textContent.slice(0,95)}');
  console.log('QUOTA_WIDGET_DIAGNOSTIC',JSON.stringify(quotaDiag));
  const addonSource=await (await fetch(origin+'/hud-quota.js',{headers:{Cookie:'rovor_hud='+session}})).text();
  console.log('QUOTA_ADDON_SOURCE',addonSource.includes('ROVOR_QUOTA_BOARD'),addonSource.length);
  await poll(()=>evalJS('return document.querySelectorAll(".rvq-provider").length===9'));
  assert.equal(await evalJS('return document.querySelector(".rvq-ring[role=progressbar]")?.getAttribute("aria-valuenow")'),'25.0');
  assert(await evalJS('return !!document.querySelector(".rvq-ring-unknown")'));
  assert(await evalJS('return document.querySelector(".rvq-board").textContent.includes("RESET WINDOW")'));
  // Nine overview tiles remain visible and independent of detailed model rows.
  assert.equal(await evalJS('return document.querySelectorAll(".rvq-overview-tile").length'),9);
  if(name==='iphone-portrait'){
    // The original workload module may replace its own global; the shared
    // read-only snapshot hook must remain independent and correctly scoped.
    // A user reviewing a provider must not lose expanded state or keyboard
    // focus, even if both the popup and quota board refresh during inspection.
    assert(await evalJS('return !!document.querySelector(".rvq-more summary")'));
    const baseline=await evalJS('return performance.getEntriesByType("resource").filter(e=>e.name.includes("/api/hud/omniroute?period=24h")).length');
    await evalJS('const s=document.querySelector(".rvq-more summary");s.click();s.focus();return true');
    await delay(11500);
    assert(await evalJS('return !!document.querySelector(".rvq-more[open]")'),
      'expanded quota must survive all refreshes');
    const requestsNow=await evalJS('return performance.getEntriesByType("resource").filter(e=>e.name.includes("/api/hud/omniroute?period=24h")).length');
    assert(requestsNow-baseline<=4,'duplicate quota polling detected');
    await evalJS('document.querySelector(".rvq-more[open] summary").click();return true');
    assert(await evalJS('return !document.querySelector(".rvq-more").open'),
      'owner can close the expanded provider details');
  }

  assert(await evalJS('return document.querySelector("[role=meter]").getAttribute("aria-valuenow")==="70"'));
  const geometry=await evalJS('const r=document.querySelector(".drawer").getBoundingClientRect();return {width:r.width,height:r.height}');assert(geometry.width<=width+2&&geometry.height<=height+2);
  if(name==='iphone-portrait'||name==='desktop')await screenshot(name+'-live-models');
  await evalJS('document.querySelector("#rovor-workload-popup [data-live-tab=employees]").click();return true');
  assert.equal(await evalJS('return document.querySelectorAll(".wl-employees-live .wl-card").length'),8);
  assert(await evalJS('return document.querySelector(".wl-employees-live").textContent.includes("Actual upstream model")'));
  await evalJS('document.querySelector("#rovor-workload-popup [data-live-tab=models]").click();return true');
 }
 requests=8;
 await poll(()=>evalJS('return document.querySelector("[role=meter]")?.getAttribute("aria-valuenow")==="80"'));
 offline=true;
 await poll(()=>evalJS('return document.querySelector("#rovor-workload-popup").textContent.includes("DISCONNECTED")'));
 await poll(()=>evalJS('return document.querySelectorAll("[role=meter]").length===0'));
 const {normalize}=await import('../tools/hud_omniroute_bridge.mjs');
 const externalBridge=createBridge({viewerOrigin:publicOrigin,pairCode:'a'.repeat(64),hud:'<body></body>',adapter:'',collect:async period=>({...normalize({data:Array.from({length:12},(_,i)=>({id:'p/m'+i,owned_by:'p'}))},{summary:{totalRequests:1,uniqueModels:1},byModel:[{rawModel:'m0',provider:'p',requests:1,totalTokens:1}]}),period})});
 const extPort=await externalBridge.listen();externalServer=externalBridge.server;publicOriginHolder.bridge='http://127.0.0.1:'+extPort;
 await cmd('Page.navigate',{url:publicOrigin+'/'});
 await poll(()=>evalJS('return !!document.getElementById("connectOmniRoute")'));
 await evalJS('document.getElementById("connectOmniRoute").click();return true');
 await delay(6000);
 assert(await evalJS('return !!document.getElementById("omniBridgeLink")')); 
 await evalJS('document.getElementById("omniBridgeLink").value='+JSON.stringify(publicOriginHolder.bridge+'/#pair='+'a'.repeat(64))+';document.getElementById("omniConnectForm").requestSubmit();return true');
 await poll(()=>evalJS('return document.querySelectorAll("#workloadPanel [data-live-model]").length===1'));
 assert.equal(await evalJS('return location.origin'),publicOrigin);
 assert(await evalJS('return document.querySelector("#workloadPanel").textContent.includes("CONNECTED")'));
 console.log('PASS public HUD cross-origin pairing → bearer snapshot → 1 recorded model row at original origin.');
 console.log('PASS live adapter: 12 models, five responsive sizes, 70→80% measured update, disconnected meters cleared. Mocked gateway, not real Mac evidence.');
}
main().catch(e=>{console.error(e);process.exitCode=1}).finally(()=>{try{socket?.close()}catch{};try{chrome?.kill()}catch{};try{server?.close();publicServer?.close();externalServer?.close()}catch{};if(tmp){try{fs.rmSync(tmp,{recursive:true,force:true,maxRetries:8,retryDelay:200})}catch{}}});
