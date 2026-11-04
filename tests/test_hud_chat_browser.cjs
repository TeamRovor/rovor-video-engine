#!/usr/bin/env node
'use strict';
// Headless Chromium responsive QA with MOCKED private OmniRoute responses.
// This is not proof that real Mac inference or iOS Safari hardware works.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const http=require('node:http');
const {spawn,spawnSync}=require('node:child_process');
const js=fs.readFileSync(path.resolve(__dirname,'../dashboard/command-center/native-v8-9/hud-chat.js'),'utf8');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const model='openrouter/example:free',otherModel='mistral/owner-approved-test-route',jobId='051bf69b-cc2d-4453-825e-8d10f16556b4';
const views=[[390,844,'iPhone'],[820,1180,'iPad portrait'],[1180,820,'iPad landscape'],[1440,900,'Windows/Mac desktop']];
let server,chrome,ws,tmp,serial=0,submits=0,polls=0,chromeLog='',chromeExit=null;
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
async function main(){
  server=http.createServer(async(req,res)=>{
    const route=new URL(req.url,'http://127.0.0.1').pathname;
    if(route==='/hud-chat.js'){res.writeHead(200,{'Content-Type':'text/javascript'});return res.end(js);}
    if(route==='/api/hud/chat/models')return respond(res,{online:true,models:[model,otherModel]});
    if(route==='/api/chat/models')return respond(res,{models:['@cf/meta/llama-3.1-8b-instruct']});
    if(route==='/api/hud/omniroute')return respond(res,{snapshot_at:new Date().toISOString(),
      transport:{connection:'fresh'},connections:['gemini','groq','nvidia','mistral','cohere','sambanova',
        'cloudflare-ai','openrouter','huggingface'].map(provider=>({provider,name:provider,enabled_count:1,connection_count:1}))});
    if(route==='/api/hud/chat/submit'){submits++;return respond(res,{job_id:jobId},202);}
    if(route==='/api/hud/chat/status/'+jobId){polls++;
      return respond(res,polls===1?{state:'queued'}:polls===2?{state:'running'}:
        {state:'complete',requested_model:model,output:'Confirmed mocked backend response.'});}
    if(route==='/api/hud/chat/cancel/'+jobId)return respond(res,{cancelled:false,error:'request_already_running'},409);
    if(route==='/api/chat'){res.writeHead(200,{'Content-Type':'text/event-stream'});
      return res.end('data: {"choices":[{"delta":{"content":"Cloud reply"}}]}\n\ndata: [DONE]\n\n');}
    if(route.startsWith('/api/'))return respond(res,{error:'not_found'},404);
    res.writeHead(200,{'Content-Type':'text/html'});
    res.end('<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;background:#020916"><script src="/hud-chat.js"></script></body></html>');
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
    await cmd('Page.navigate',{url:origin+'/?v='+encodeURIComponent(name)});
    await waitFor(()=>evaluate('return !!document.querySelector("#rvc-fab")'),name+' launcher');
    await evaluate('document.querySelector("#rvc-fab").click();return true');
    await waitFor(()=>evaluate('return Array.from(document.querySelectorAll("#rvc-model option")).some(x=>x.value==="openrouter/example:free")'),name+' model');
    const info=await evaluate('const p=document.querySelector("#rvc"),r=p.getBoundingClientRect();return {width:r.width,height:r.height,vw:innerWidth,vh:innerHeight,textarea:parseFloat(getComputedStyle(document.querySelector("#rvc textarea")).fontSize),select:parseFloat(getComputedStyle(document.querySelector("#rvc-source")).fontSize),overflow:document.documentElement.scrollWidth>innerWidth+3}');
    assert(info.width<=info.vw+3,name+': horizontal overflow');
    assert(info.height<=info.vh+4,name+': vertical overflow');
    assert(!info.overflow,name+': document overflow');
    assert(info.textarea>=16&&info.select>=16,name+': Safari focus zoom risk');
    await waitFor(()=>evaluate('return document.querySelector(".rvc-provider-inspect summary").textContent.includes("9 CONFIGURED")'),name+' provider inventory');
    if(name==='iPhone'){
      await evaluate('document.querySelector(".rvc-mobile-menu").click();return true');
      assert.equal(await evaluate('return document.querySelector("#rvc").dataset.sideOpen'),'true');
      await evaluate('document.querySelector(".rvc-side-backdrop").click();return true');
      assert.equal(await evaluate('return document.querySelector("#rvc").dataset.sideOpen'),'false');
      await evaluate('document.querySelector(".rvc-model-browse").click();return true');
      assert.equal(await evaluate('return document.querySelector(".rvc-model-sheet").hidden'),false);
      await evaluate('document.querySelector(".rvc-model-search").value="mistral";document.querySelector(".rvc-model-search").dispatchEvent(new Event("input",{bubbles:true}));return true');
      const result=await evaluate('return Array.from(document.querySelectorAll(".rvc-model-option")).map(x=>x.textContent)');
      assert.equal(result.length,1,'provider search should filter to one available route');
      await evaluate('document.querySelector(".rvc-model-option").click();return true');
      assert.equal(await evaluate('return document.querySelector("#rvc-model").value'),otherModel);
      assert.equal(await evaluate('return document.querySelector(".rvc-model-sheet").hidden'),true);
      await evaluate('const select=document.querySelector("#rvc-model");select.value="openrouter/example:free";select.dispatchEvent(new Event("change",{bubbles:true}));return true');
    }
    await evaluate('document.querySelector("#rvc button[aria-label=\\"Close chat\\"]").click();return true');
    assert.equal(await evaluate('return document.querySelector("#rvc").dataset.open'),'false');
  }
  await cmd('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await cmd('Page.navigate',{url:origin+'/conversation'});
  await waitFor(()=>evaluate('return !!document.querySelector("#rvc-fab")'),'conversation launcher');
  await evaluate('document.querySelector("#rvc-fab").click();return true');
  await waitFor(()=>evaluate('return !!document.querySelector("#rvc-model option[value=\\"openrouter/example:free\\"]")'),'conversation catalog');
  await evaluate('document.querySelector("#rvc textarea").value="Say hello";document.querySelector("#rvc form").requestSubmit();return true');
  await waitFor(()=>evaluate('return !!document.querySelector(".rvc-receipt")&&document.querySelector(".rvc-receipt").textContent.includes("REPLY RECEIVED")'),'confirmed receipt');
  assert.equal(submits,1,'one chat submission expected');
  assert(polls>=3,'queued/running/complete must be polled');
  assert(await evaluate('return document.querySelector("#rvc-log").textContent.includes("Confirmed mocked backend response.")'));
  assert(await evaluate('return !!document.querySelector(".rvc-copy")'),'copy response action missing');
  await evaluate('document.querySelector("#rvc button[aria-label=\\"Close chat\\"]").click();document.querySelector("#rvc-fab").click();return true');
  assert(await evaluate('return document.querySelector("#rvc-log").textContent.includes("REPLY RECEIVED")'),'receipt disappeared from history');
  console.log('PASS Ask ROVOR responsive Chromium: iPhone, iPad portrait/landscape, Mac/Windows desktop.');
  console.log('PASS model discovery, nine historical provider slots, keyboard-safe font sizing, receipts and history.');
  console.log('All model responses were mocked; real iOS Safari and private Mac inference remain unverified.');
}
main().catch(e=>{console.error(e.stack||e);process.exitCode=1;}).finally(()=>{
  try{ws?.close();}catch{}
  try{chrome?.kill();}catch{}
  try{server?.close();}catch{}
  try{if(tmp)fs.rmSync(tmp,{recursive:true,force:true});}catch{}
});
