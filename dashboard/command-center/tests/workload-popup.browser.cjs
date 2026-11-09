'use strict';
// Mocked same-origin authenticated Cloudflare HUD end-to-end responsive QA.
// Does not call paid/free inference, Cloudflare secrets, or any local bridge.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),
 os=require('node:os'),http=require('node:http');
const {spawn,spawnSync}=require('node:child_process');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const root=path.resolve(__dirname,'..'),native=path.join(root,'native-v8-9');
const output=path.join(root,'qa-screenshots','workload-popup');
const sizes=[[430,932,'iphone-portrait',true],[820,1180,'ipad-portrait',true],
 [1180,820,'ipad-landscape',true],[1366,768,'laptop',false],[1672,941,'desktop',false]];
let server,chrome,socket,tmp,serial=0;
const pending=new Map();
const cmd=(method,params={})=>new Promise((resolve,reject)=>{
 const id=++serial;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));
});
const evalJS=async script=>{
 const r=await cmd('Runtime.evaluate',{expression:'(()=>{'+script+'})()',returnByValue:true,awaitPromise:true});
 if(r.exceptionDetails)throw Error('Browser script: '+JSON.stringify(r.exceptionDetails));
 return r.result.value;
};
async function poll(fn,label){
 for(let i=0;i<150;i++){try{const v=await fn();if(v)return v;}catch{}await delay(100);}
 throw Error('Browser operation timed out: '+label);
}
async function screenshot(name){
 const r=await cmd('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
 fs.writeFileSync(path.join(output,name+'.png'),Buffer.from(r.data,'base64'));
}
function respond(res,data){
 res.writeHead(200,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(data));
}
async function main(){
 fs.mkdirSync(output,{recursive:true});
 let localQueries=0;
 server=http.createServer((req,res)=>{
  const pathname=new URL(req.url,'http://localhost').pathname,now=Date.now();
  if(pathname==='/hud'){
   let html=fs.readFileSync(path.join(native,'index.html'),'utf8');
   html=html.replace('</body>','<script src="/hud-quota.js"></script>'+
     '<script src="/workload-popup.js"></script><script>'+
     'window.ROVOR_WORKLOAD?.mountPreview?.(document.getElementById("workloadPanel"),()=>window.ROVOR_NATIVE?.open?.("workload"));'+
     'window.ROVOR_QUOTA_BOARD?.startCloud?.();</script></body>');
   res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'});return res.end(html);
  }
  if(pathname==='/hud-quota.js'||pathname==='/workload-popup.js'){
   const file=pathname==='/hud-quota.js'?'live-quota-board.js':'workload-popup.js';
   res.writeHead(200,{'Content-Type':'text/javascript','Cache-Control':'no-store'});
   return res.end(fs.readFileSync(path.join(native,file)));
  }
  if(pathname.startsWith('/api/hud/omniroute')||pathname.startsWith('/pair/')){
   localQueries++;res.writeHead(404).end();return;
  }
  if(pathname==='/api/ghost/status')return respond(res,{
   execution_source:'cloud_provider',observed_at:now,providers:[
    {provider:'mistral',admission:'eligible',recorded_24h:{requests:1}},
    {provider:'gemini',admission:'eligible'}],
   attempts:[{id:'abc-receipt',provider:'mistral',employee:'Gus',status:'needs_review',
     human_review:'not_recorded',started_at:now-1000,title:'Verified review task'}]});
  if(pathname==='/api/hud/gemini/models')return respond(res,{
   source:'google_gemini_cloud_direct',online:true,mac_required:false,
   models:['gemini-auto-free','gemini-3.1-flash-lite','gemini-3.5-flash'],
   directly_listed_models:['gemini-3.1-flash-lite','gemini-3.5-flash'],
   verified_model_count:1,
   model_evidence:[{model:'gemini-3.1-flash-lite',verification:'verified_recent_reply'},
    {model:'gemini-3.5-flash',verification:'listed_unverified'}]});
  if(pathname==='/api/hud/gemini/usage')return respond(res,{
   source:'cloud_gemini_direct',scope:'this_hud_direct_api_only',
   observed_at:new Date(now).toISOString(),attempts:3,completed:2,
   daily_local_cap:12,daily_local_remaining:9,daily_local_reset_at:new Date(now+86400000).toISOString(),
   models:[{model:'gemini-3.1-flash-lite',attempts:3,completed:2,failures:1,input_tokens:30,output_tokens:9}]});
  if(pathname==='/api/chat/groq/status')return respond(res,{
   source:'cloud_direct_groq',observed_at:new Date(now).toISOString(),ready:true,
   model:'groq/openai/gpt-oss-20b',last_cloud_completion_at:new Date(now-4000).toISOString()});
  if(pathname==='/api/chat/models')return respond(res,{models:['@cf/meta/llama-3.1-8b-instruct']});
  res.writeHead(404);res.end();
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const url='http://127.0.0.1:'+server.address().port+'/hud';
 const bin=[process.env.CHROME_BIN,'google-chrome','chromium','chromium-browser']
  .filter(Boolean).find(n=>spawnSync('which',[n],{stdio:'ignore'}).status===0);
 assert(bin,'Chrome is required');
 tmp=fs.mkdtempSync(path.join(os.tmpdir(),'rovor-cloud-workload-'));
 chrome=spawn(bin,['--headless=new','--no-sandbox','--disable-dev-shm-usage','--disable-gpu',
  '--remote-debugging-port=0','--user-data-dir='+tmp,'about:blank'],{stdio:'ignore'});
 const port=await poll(()=>{
  const f=path.join(tmp,'DevToolsActivePort');return fs.existsSync(f)?fs.readFileSync(f,'utf8').split('\n')[0]:null;
 },'Chromium debug port');
 const targets=await poll(async()=>{
  const r=await fetch('http://127.0.0.1:'+port+'/json/list');return r.ok?await r.json():null;
 },'browser targets');
 socket=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise((r,j)=>{socket.addEventListener('open',r,{once:true});socket.addEventListener('error',j,{once:true})});
 socket.addEventListener('message',e=>{
  const m=JSON.parse(e.data),p=pending.get(m.id);if(!p)return;
  pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);
 });
 await cmd('Page.enable');await cmd('Runtime.enable');
 const results=[];
 for(const [width,height,name,mobile] of sizes){
  await cmd('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile});
  await cmd('Page.navigate',{url});
  await poll(()=>evalJS('return !!window.ROVOR_NATIVE && document.querySelectorAll("#workloadPanel .wl-compact-row").length===4'),name+' cloud preview');
  const home=await evalJS('return {rows:document.querySelectorAll("#workloadPanel .wl-compact-row").length,nav:document.querySelectorAll(".nav-item").length,panels:document.querySelectorAll(".rail .panel").length,hidden:document.querySelector("#screen").hidden,width:document.documentElement.scrollWidth,vw:innerWidth,txt:document.querySelector("#workloadPanel").textContent}');
  assert.equal(home.rows,4);assert.equal(home.nav,5);assert.equal(home.panels,6);
  assert(home.hidden);assert(home.width<=home.vw+3,name+': horizontal page overflow');
  assert(!home.txt.includes('LAST MAC REPORT'),name+': archived preview visible');
  if(name==='iphone-portrait'||name==='desktop')await screenshot(name+'-compact');
  await evalJS('document.querySelector(".panel-expand[data-view=workload]").click();return true');
  await poll(()=>evalJS('return document.querySelectorAll("#rovor-workload-popup .rvq-v2-provider").length===9'),name+' nine cloud cards');
  const detail=await evalJS('const d=document.querySelector(".drawer").getBoundingClientRect(),h=document.querySelector("#rovor-workload-popup");return {width:d.width,height:d.height,count:h.querySelectorAll(".rvq-v2-provider").length,local:h.textContent.includes("Mac"),gemini:h.textContent.includes("3 / 12"),unverified:h.textContent.includes("Allowance unknown"),reviews:h.textContent.includes("OWNER PASS / FAIL")}');
  assert.equal(detail.count,9);
  assert(detail.width<=width+3&&detail.height<=height+3,name+': drawer overflow');
  assert.equal(detail.local,false,name+': local dependency displayed');
  assert(detail.gemini,name+': exact local reservation ring missing');
  assert(detail.unverified,name+': missing external quota must say unknown');
  assert(detail.reviews,name+': owner review link missing');
  await evalJS('document.querySelector(".rvq-v2-provider details summary").click();return true');
  assert(await evalJS('return !!document.querySelector(".rvq-v2-provider details[open]")'));
  await evalJS('document.querySelector("button[data-rvq-filter=attention]").click();return true');
  assert(await evalJS('return document.querySelectorAll(".rvq-v2-provider:not([hidden])").length>=1'));
  if(name==='iphone-portrait'||name==='desktop')await screenshot(name+'-cloud-workload');
  await evalJS('document.querySelector("#screen .close").click();document.querySelector("[data-cloud-tab=employees]").click();return true');
  assert.equal(await evalJS('return document.querySelectorAll("#workloadPanel .wl-compact-row").length'),4);
  results.push({name,width,height,pass:true});
 }
 assert.equal(localQueries,0,'active cloud workload must never fetch archived local endpoints');
 fs.writeFileSync(path.join(output,'results.json'),JSON.stringify(results,null,2));
 console.log('PASS cloud-only Workload browser QA: five viewports, nine provider cards, source-backed quota ring, owner reviews, no local polling.');
}
main().catch(e=>{console.error(e.stack||e);process.exitCode=1}).finally(()=>{
 try{socket?.close()}catch{};try{chrome?.kill()}catch{};try{server?.close()}catch{};
 if(tmp)try{fs.rmSync(tmp,{recursive:true,force:true,maxRetries:6,retryDelay:200})}catch{}
});