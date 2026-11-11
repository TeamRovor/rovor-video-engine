#!/usr/bin/env node
'use strict';
// Actual responsive Chromium UI, mocked private API. Never touches real reviews.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const http=require('node:http');
const {spawn,spawnSync}=require('node:child_process');
const {createHash}=require('node:crypto');
const assets=path.resolve(__dirname,'../dashboard/command-center/native-v8-9');
const html=fs.readFileSync(path.join(assets,'workforce-review.html'),'utf8');
const js=fs.readFileSync(path.join(assets,'workforce-review.js'),'utf8');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const views=[[390,844,'iPhone'],[820,1180,'iPad portrait'],[1180,820,'iPad landscape'],[1440,900,'Windows/Mac desktop']];
let server,chrome,ws,tmp,serial=0,chromeLog='',chromeExit=null;
const callbacks=new Map();
const cmd=(method,params={})=>new Promise((resolve,reject)=>{
  const id=++serial;callbacks.set(id,{resolve,reject});
  ws.send(JSON.stringify({id,method,params}));
});
async function evaluate(script){
  const result=await cmd('Runtime.evaluate',{expression:'(()=>{'+script+'})()',returnByValue:true,awaitPromise:true});
  if(result.exceptionDetails)throw Error('Browser JS exception: '+JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function waitFor(fn,label,attempts=100){
  for(let i=0;i<attempts;i++){try{const v=await fn();if(v)return v;}catch{}await delay(100);}
  throw Error('Browser timed out: '+label);
}
const respond=(res,data,status=200)=>{res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(data));};

const now=Date.now(),output='## Bottom line\nA failed check may block a release.\n## What was done\nA plan only, no repair.\n## What is still unknown\nThe cause is not verified.\n## Recommended next step\nReview the most recent check.\n<img src=x onerror=alert(1)>',legacy='Old draft: prepare an investigation, not a fix.',hash=s=>createHash('sha256').update(s).digest('hex');
const records=[
 {id:'gc-rec-one',task_id:'cloud-discovery-run-1234',employee:'Mike',kind:'code_review',title:'Investigate verified GitHub discovery run-1234',state:'needs_review',human_review:'not_recorded',created_at:now-10,finished_at:now,actual_model:'gemini-3.5-flash-lite',output_sha256:hash(output),provider:'google-gemini-cloud',tokens_input:34,tokens_output:51},
 {id:'gc-rec-two',task_id:'cloud-discovery-issue-88',employee:'Mike',kind:'code_review',title:'Review issue 88',state:'needs_review',human_review:'not_recorded',created_at:now-20,finished_at:now,actual_model:'gemini-3.5-flash-lite',output_sha256:hash(legacy)},
 {id:'gc-old',task_id:'old',employee:'Gus',kind:'plan',title:'Old approved result',state:'needs_review',human_review:'passed',created_at:now-30,finished_at:now,actual_model:'gemini-3.5-flash-lite',output_sha256:hash(legacy)},
 {id:'gc-rec-skipped',task_id:'cloud-discovery-run-5678',employee:'Mike',kind:'code_review',
  title:'Outdated check 5678',state:'failed',human_review:'not_recorded',
  error_code:'discovery_no_longer_actionable',started_at:null,created_at:now-45,finished_at:now,
  actual_model:null,output_sha256:null}
];
const writes=[];let corrupt=false;
async function main(){
 server=http.createServer(async(req,res)=>{
  const route=new URL(req.url,'http://127.0.0.1').pathname;
  if(route==='/workforce-review.html'){res.writeHead(200,{'Content-Type':'text/html','Cache-Control':'no-store'});return res.end(html);}
  if(route==='/workforce-review.js'){res.writeHead(200,{'Content-Type':'text/javascript','Cache-Control':'no-store'});return res.end(js);}
  if(route==='/api/hud/workforce/status')return respond(res,{source:'existing_cloudflare_hud_gemini_workforce',mac_required:false,enabled:true,recurring_execution_authorized:true,site_review_ledger_synced:false,items:records,
   standing_plan:{max_pending_reviews:3,expires_at:now+600000},native_schedule:{source:'cloudflare_scheduled_event',last_tick:null}});
  if(route==='/api/hud/owner/session')return respond(res,{configured:false,owner_authenticated:false});
  if(route==='/api/hud/workforce/github-patch')return respond(res,{configured:false});
  if(route==='/api/hud/workforce/native-discovery')return respond(res,{source:'rovor_native_github_discovery',configured:true,enabled:true,mac_required:false,chatgpt_required:false,github_actions_required:false,last_check:null});
  if(route.startsWith('/api/hud/workforce/evidence/')){
   const r=records.find(x=>x.id===route.split('/').at(-1));
   if(!r)return respond(res,{error:'not_found'},404);
   return respond(res,{source:'rovor_private_review_evidence',job_id:r.id,source_key:r.task_id.slice('cloud-discovery-'.length),
    state:r.id==='gc-rec-one'?'newer_check_passed':'issue_open',title:r.id==='gc-rec-one'?'Private HUD release check':'Open issue',
    related_id:r.id==='gc-rec-one'?5678:null,finished_at:now,model_called:false,github_written:false});
  }
  if(route.startsWith('/api/hud/workforce/draft/')){
   const r=records.find(x=>x.id===route.split('/').at(-1));
   if(!r)return respond(res,{error:'not_found'},404);
   return respond(res,{...r,output:r.id==='gc-rec-one'?(corrupt?output+' tampered':output):legacy});
  }
  if(route==='/api/hud/workforce/review'&&req.method==='POST'){
   let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw);writes.push(body);
   const r=records.find(x=>x.id===body.job_id);
   assert(r);assert.equal(r.output_sha256,body.output_sha256);assert.equal(r.human_review,'not_recorded');
   r.human_review=body.verdict;return respond(res,{id:r.id,human_review:r.human_review,output_sha256:r.output_sha256});
  }
  if(req.method!=='GET')throw Error('unexpected mutation '+route);
  return respond(res,{error:'not_found'},404);
 });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const origin='http://127.0.0.1:'+server.address().port;
  const chromeBin=process.env.CHROME_BIN||['google-chrome','chromium','chromium-browser'].find(bin=>spawnSync('which',[bin],{stdio:'ignore'}).status===0);
  assert(chromeBin,'Chrome/Chromium unavailable on browser QA runner');
  tmp=fs.mkdtempSync(path.join(os.tmpdir(),'rovor-ask-browser-'));
  chrome=spawn(chromeBin,['--headless=new','--no-sandbox','--disable-dev-shm-usage','--disable-gpu',
    '--remote-debugging-port=0','--user-data-dir='+tmp,'about:blank'],{stdio:['ignore','ignore','pipe']});
  chrome.stderr?.on('data',chunk=>{chromeLog=(chromeLog+chunk.toString()).slice(-5000);});
  chrome.on('error',err=>{chromeLog+=' Chrome process error: '+err.message;});
  chrome.on('exit',(code,signal)=>{chromeExit={code,signal};});
  let port;
  try {
    port=await waitFor(()=>{
      const f=path.join(tmp,'DevToolsActivePort');
      if(chromeExit)throw Error('Chrome exited '+JSON.stringify(chromeExit));
      return fs.existsSync(f)?fs.readFileSync(f,'utf8').split('\n')[0]:null;
    },'Chrome debug port',400);
  }catch(error){
    throw Error(error.message+'; browser='+chromeBin+'; exit='+JSON.stringify(chromeExit)+'; stderr='+chromeLog);
  }
  const targets=await waitFor(async()=>{
    const r=await fetch('http://127.0.0.1:'+port+'/json/list');
    return r.ok?await r.json():null;
  },'browser target');
  ws=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{
    ws.addEventListener('open',resolve,{once:true});
    ws.addEventListener('error',reject,{once:true});
  });
  ws.addEventListener('message',event=>{
    const m=JSON.parse(event.data),callback=callbacks.get(m.id);
    if(!callback)return;callbacks.delete(m.id);
    m.error?callback.reject(Error(JSON.stringify(m.error))):callback.resolve(m.result);
  });
  await cmd('Page.enable');await cmd('Runtime.enable');

 for(const [width,height,name] of views){
  await cmd('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:name!=='Windows/Mac desktop'});
  await cmd('Page.navigate',{url:origin+'/workforce-review.html?v='+encodeURIComponent(name)});
  await waitFor(()=>evaluate('return document.querySelectorAll("#jobs .draft").length===2'),name+' automatic verified drafts');
  const info=await evaluate('return {overflow:document.documentElement.scrollWidth>innerWidth+3,buttons:Array.from(document.querySelectorAll("#jobs button")).map(b=>b.getBoundingClientRect().height),history:document.querySelector("#history-panel").open,summary:document.querySelector(".draft-summary").textContent,images:document.querySelectorAll("#jobs img").length,stop:document.querySelector("#stop-fallback").getBoundingClientRect().height,details:document.querySelector("#jobs .receipt-details").open}');
  assert(!info.overflow,name+' horizontal overflow');
  assert(info.buttons.every(h=>h>=44),name+' tap targets too small');
  assert.equal(info.history,false);assert.equal(info.details,false);assert.equal(info.images,0);
  assert(await evaluate('return document.querySelector("#first-pr-state").textContent.includes("not been verified")'),
   name+' no false permission claim when the mock Worker lacks a write proof');
  const skipped=await evaluate('return document.querySelector("#history").textContent');
  assert(skipped.includes('SKIPPED · OUTDATED')&&skipped.includes('No provider tokens were spent'),
    name+' skipped work is not explained to the owner');
  assert(!await evaluate('return !!document.querySelector("#history button.approve,#history button.reject")'),
    'skipped job cannot be accidentally reviewed');
  assert(info.summary.includes('The cause is not verified.'));
  const reviewClaims=await evaluate('return Array.from(document.querySelectorAll("#jobs .report-claims")).map(e=>e.textContent)');
  assert.equal(reviewClaims.length,2,name+' missing employee report detail');
  assert(reviewClaims[0].includes('A plan only, no repair.')&&reviewClaims[0].includes('The cause is not verified.'),
    name+' historical report excerpts were lost');
  assert(reviewClaims[0].includes('No specific benefit was provided.'),
    name+' missing historical benefit not clearly disclosed');
  assert(reviewClaims[1].includes('This result lacks a complete structured report.'),
    name+' unstructured report not flagged');
  const safeClaims=await evaluate('return {images:document.querySelectorAll("#jobs img").length,untrusted:document.querySelector("#jobs .report-claims").textContent.includes("<img src=x") }');
  assert.equal(safeClaims.images,0);
  assert.equal(safeClaims.untrusted,true,'hostile text is shown literally, not executed');
  const briefing=await evaluate('return document.querySelector("#jobs .owner-brief").textContent');
  for(const label of ['What ROVOR investigated','What it actually produced','How it might benefit ROVOR','Concerns and missing proof','What your PASS will do'])
   assert(briefing.includes(label),name+' missing '+label);
  assert(briefing.includes('No code, fix, independent test run')&&briefing.includes('not the actual code'),'honest no-fix limitations missing');
  assert(briefing.includes('No improvement has been demonstrated')||briefing.includes('This benefit has not been demonstrated'),'unmeasured benefit not disclosed');
  await waitFor(()=>evaluate('return !!document.querySelector(".source-status[data-evidence-state=newer_check_passed]")'),name+' current evidence');
  assert(await evaluate('return document.querySelector(".source-status[data-evidence-state=newer_check_passed]").textContent.includes("may already be addressed")'));
  assert.equal(writes.length,0,'current GitHub evidence never makes a review decision');
  assert(info.stop>0,'STOP fallback must stay visible outside advanced details');
  assert.equal(writes.length,0,'opening and verifying must not make decisions');
 }
 await evaluate('document.querySelector("#jobs .defer").click();return true');
 assert.equal(await evaluate('return getComputedStyle(document.querySelector("#jobs .draft .actions")).display'),'none');
 assert.equal(writes.length,0);
 await evaluate('Array.from(document.querySelectorAll("#jobs button")).find(b=>b.textContent==="Resume review").click();return true');
 assert.equal(await evaluate('return getComputedStyle(document.querySelector("#jobs .draft .actions")).display'),'flex');
 await evaluate('document.querySelector("#jobs .approve").click();return true');
 assert.equal(writes.length,0,'first click is not approval');
 assert.equal(await evaluate('return document.querySelector("#jobs .approve").textContent'),'Confirm PASS decision');
 await evaluate('document.querySelector("#jobs .reject").click();return true');
 assert.equal(await evaluate('return document.querySelector("#jobs .approve").textContent'),'Keep this work (PASS)');
 assert.equal(writes.length,0,'switching verdict must not write');
 await evaluate('document.querySelector("#jobs .reject").click();return true');
 await waitFor(()=>evaluate('return document.querySelector("#pending").textContent==="1"&&document.querySelectorAll("#jobs .draft").length===1'),'rejected result moves to history');
 assert.deepEqual(writes,[{job_id:'gc-rec-one',verdict:'failed',output_sha256:hash(output)}]);
 await evaluate('document.querySelector("#jobs .approve").click();document.querySelector("#jobs .approve").click();return true');
 await waitFor(()=>evaluate('return document.querySelector("#pending").textContent==="0"'),'accepted result moves to history');
 assert.equal(writes.length,2);assert.equal(writes[1].verdict,'passed');
 records[0].human_review='not_recorded';corrupt=true;
 await evaluate('document.querySelector("#refresh").click();return true');
 await waitFor(()=>evaluate('return !!document.querySelector("#jobs .draft-load-error")'),'corrupted output blocked');
 assert.equal(await evaluate('return document.querySelectorAll("#jobs .approve,#jobs .reject").length'),0);
 assert.equal(writes.length,2);
 console.log('PASS decision-first review on iPhone, iPad portrait/landscape and desktop; defer, resume, mutually exclusive confirmation, hash rejection, PASS/FAIL readback, history, no auto-mutation.');
}
main().catch(e=>{console.error(e.stack||e);process.exitCode=1;}).finally(()=>{
  try{ws?.close();}catch{}
  try{chrome?.kill();}catch{}
  try{server?.close();}catch{}
  try{if(tmp)fs.rmSync(tmp,{recursive:true,force:true});}catch{}
});
