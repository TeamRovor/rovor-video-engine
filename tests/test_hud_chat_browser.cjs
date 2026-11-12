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
let server,chrome,ws,tmp,serial=0,submits=0,polls=0,submittedPayload=null,chromeLog='',chromeExit=null;
const submittedJobs=new Map();
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
    if(route==='/home-layout'){
      const assets=path.resolve(__dirname,'../dashboard/command-center/native-v8-9');
      const home=fs.readFileSync(path.join(assets,'index.html'),'utf8');
      const css=fs.readFileSync(path.join(assets,'hud-mobile.css'),'utf8');
      res.writeHead(200,{'Content-Type':'text/html','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; img-src data:"});
      return res.end(home.replace('</head>','<style>'+css+'</style></head>'));
    }
    if(route==='/hud-chat.js'){res.writeHead(200,{'Content-Type':'text/javascript'});return res.end(js);}
    if(route==='/api/hud/chat/models')return respond(res,{online:true,models:[model,otherModel]});
    if(route==='/api/chat/models')return respond(res,{models:['@cf/meta/llama-3.1-8b-instruct','groq/openai/gpt-oss-20b']});
    if(route==='/api/chat/groq/status')return respond(res,{source:'cloud_direct_groq',model:'groq/openai/gpt-oss-20b',ready:true,mac_required:false,locally_admitted_today:1,last_cloud_completion_at:new Date().toISOString()});
    if(route==='/api/hud/omniroute')return respond(res,{snapshot_at:new Date().toISOString(),
      transport:{connection:'fresh'},connections:['gemini','groq','nvidia','mistral','cohere','sambanova',
        'cloudflare-ai','openrouter','huggingface'].map(provider=>({provider,name:provider,enabled_count:1,connection_count:1}))});
    if(route==='/api/hud/chat/submit'){submits++;
      let raw='';for await(const part of req)raw+=part.toString();
      submittedPayload=JSON.parse(raw);
      const id='051bf69b-cc2d-4453-825e-'+(0x8d10f16556b3+submits).toString(16).padStart(12,'0');
      submittedJobs.set(id,{model:submittedPayload.model,polls:0});
      return respond(res,{job_id:id},202);}
    if(route.startsWith('/api/hud/chat/status/')){
      const id=route.slice('/api/hud/chat/status/'.length),job=submittedJobs.get(id);
      if(!job)return respond(res,{error:'not_found'},404);
      polls++;job.polls++;
      return respond(res,job.polls===1?{state:'queued',requested_model:job.model}:
        job.polls===2?{state:'running',requested_model:job.model}:
        {state:'complete',requested_model:job.model,output:'Confirmed mocked backend response. '+job.model});}
    if(route.startsWith('/api/hud/chat/cancel/'))return respond(res,{cancelled:false,error:'request_already_running'},409);
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
  for(const [width,height] of [[360,780],[390,844],[844,390],[820,1180],[1440,900]]){
    const mobile=width<1200;
    await cmd('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile});
    await cmd('Emulation.setTouchEmulationEnabled',{enabled:mobile});
    await cmd('Page.navigate',{url:origin+'/home-layout'});
    await waitFor(()=>evaluate('return location.pathname==="/home-layout" && document.readyState==="complete" && !!document.querySelector("#hud .panel-expand")'),'HUD home');
    const layout=await evaluate(`
      const panels=[...document.querySelectorAll("#hud .rail > .panel")];
      const sizes=panels.map(p=>p.getBoundingClientRect());
      const expands=panels.map(p=>p.querySelector(".panel-expand").getBoundingClientRect());
      return {count:panels.length,width:document.documentElement.scrollWidth,
        fits:sizes.every(r=>r.width>0 && r.left>=-1 && r.right<=innerWidth+1),
        touch:expands.every(r=>r.height>=44 && r.width>=44)};
    `);
    assert.equal(layout.count,6,'HUD panel count');
    assert(layout.fits&&layout.width<=width+2,'HUD home overflow at '+width+'x'+height+' '+JSON.stringify(layout));
    if(width<=780 || (mobile && height<=560))assert(layout.touch,'HUD expand targets at '+width);
    console.log('PASS actual HUD home layout '+width+'x'+height);
  }
  await cmd('Emulation.setTouchEmulationEnabled',{enabled:false});
  for(const [width,height,name] of views){
    await cmd('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:name!=='Windows/Mac desktop'});
    await cmd('Page.navigate',{url:origin+'/?v='+encodeURIComponent(name)});
    await waitFor(()=>evaluate('return !!document.querySelector("#rvc-fab")'),name+' launcher');
    await evaluate('document.querySelector("#rvc-fab").click();return true');
    if(name==='iPhone'){
      assert.equal(await evaluate('return document.querySelector("#rvc-source").value'),'gemini','new conversations default to Mac-independent cloud');
      await evaluate('const p=document.querySelector("#rvc-source");p.value="groq";p.dispatchEvent(new Event("change",{bubbles:true}));return true');
      await waitFor(()=>evaluate('return Array.from(document.querySelectorAll("#rvc-model option")).some(x=>x.value==="groq/openai/gpt-oss-20b")'),'Groq direct cloud route');
      await waitFor(()=>evaluate('return document.querySelector(".rvc-provider-inspect summary").textContent.includes("NO MAC REQUIRED")'),'Groq direct no Mac');
    }
    await evaluate('const source=document.querySelector("#rvc-source");source.value="omniroute";source.dispatchEvent(new Event("change",{bubbles:true}));return true');
    await waitFor(()=>evaluate('return Array.from(document.querySelectorAll("#rvc-model option")).some(x=>x.value==="openrouter/example:free")'),name+' model');
    const info=await evaluate('const p=document.querySelector("#rvc"),r=p.getBoundingClientRect();return {width:r.width,height:r.height,vw:innerWidth,vh:innerHeight,textarea:parseFloat(getComputedStyle(document.querySelector("#rvc textarea")).fontSize),select:parseFloat(getComputedStyle(document.querySelector("#rvc-source")).fontSize),overflow:document.documentElement.scrollWidth>innerWidth+3}');
    assert(info.width<=info.vw+3,name+': horizontal overflow');
    assert(info.height<=info.vh+4,name+': vertical overflow');
    assert(!info.overflow,name+': document overflow');
    assert(info.textarea>=16&&info.select>=16,name+': Safari focus zoom risk');
    await waitFor(()=>evaluate('return document.querySelector(".rvc-provider-inspect summary").textContent.includes("9 CONFIGURED")'),name+' provider inventory');
    if(name==='iPhone'){
      // Prompts are suggestions, not permission to submit a model job.
      await evaluate('document.querySelector(".rvc-chips button").click();return true');
      assert(await evaluate('return document.querySelector("#rvc textarea").value.length>4'),
        'suggestion did not fill the composer');
      assert.equal(submits,0,'suggestion must not call OmniRoute without Send');
      await evaluate('document.querySelector(".rvc-mobile-menu").click();return true');
      assert.equal(await evaluate('return document.querySelector("#rvc").dataset.sideOpen'),'true');
      await evaluate('document.querySelector(".rvc-side-backdrop").click();return true');
      assert.equal(await evaluate('return document.querySelector("#rvc").dataset.sideOpen'),'false');
      await evaluate('document.querySelector(".rvc-model-browse").click();return true');
      assert.equal(await evaluate('return document.querySelector(".rvc-model-sheet").hidden'),false);
      const groups=await evaluate('return Array.from(document.querySelectorAll(".rvc-model-group h3")).map(x=>x.textContent)');
      for(const name of ['Google Gemini','Mistral','NVIDIA','Cohere','SambaNova','Cloudflare Workers AI','Groq','OpenRouter','Hugging Face'])
        assert(groups.some(s=>s.startsWith(name)),name+': missing provider family in model browser');
      assert.equal(await evaluate('return document.querySelectorAll(".rvc-model-notready").length'),7,
        'seven unadvertised providers must not appear as callable routes');
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
  await evaluate('const source=document.querySelector("#rvc-source");source.value="omniroute";source.dispatchEvent(new Event("change",{bubbles:true}));return true');
  await waitFor(()=>evaluate('return !!document.querySelector("#rvc-model option[value=\\"openrouter/example:free\\"]")'),'conversation catalog');
  await evaluate('document.querySelector("#rvc-repo-file").value="integrations/hud-cloud/worker.mjs";document.querySelector("#rvc textarea").value="Say hello";document.querySelector("#rvc form").requestSubmit();return true');
  await waitFor(()=>evaluate('return !!document.querySelector(".rvc-receipt")&&document.querySelector(".rvc-receipt").textContent.includes("REPLY RECEIVED")'),'confirmed receipt');
  assert.equal(submits,1,'one chat submission expected');
  assert.equal(submittedPayload?.repo_file,'integrations/hud-cloud/worker.mjs',
    'only the explicitly selected, allowlisted GitHub source may be attached');
  assert(polls>=3,'queued/running/complete must be polled');
  assert(await evaluate('return document.querySelector("#rvc-log").textContent.includes("Confirmed mocked backend response.")'));
  assert(await evaluate('return !!document.querySelector(".rvc-copy")'),'copy response action missing');
  await evaluate('document.querySelector("#rvc button[aria-label=\\"Close chat\\"]").click();document.querySelector("#rvc-fab").click();return true');
  assert(await evaluate('return document.querySelector("#rvc-log").textContent.includes("REPLY RECEIVED")'),'receipt disappeared from history');
  // A completed receipt can paint before ask() finally unlocks the composer.
  // A programmatic requestSubmit() while busy is correctly ignored; model
  // this test as an actual user's next enabled Send, not a rushed hidden click.
  await waitFor(()=>evaluate('return !document.querySelector("#rvc form button[type="submit"]').disabled && !document.querySelector("#rvc textarea").disabled'),
    'composer unlocked after first private job receipt');
  // Explicit Send and opted-in two-model review produce two independent
  // D1 job IDs. This is mocked Chrome QA, not proof of actual Mac parallelism.
  await evaluate(`const picker=document.querySelector("#rvc-model");picker.value="__rovor_smart_route__";
    picker.dispatchEvent(new Event("change",{bubbles:true}));
    const team=document.querySelector("#rvc-team-review");team.checked=true;
    team.dispatchEvent(new Event("change",{bubbles:true}));
    const box=document.querySelector("#rvc textarea");box.value="Compare two approaches to fixing this code";
    box.dispatchEvent(new Event("input",{bubbles:true}));return true`);
  // Check the actual two-route plan and enabled Send, then submit once.
  // This preserves separate receipt assertions rather than extending a
  // timeout that could mask a lost/invalid second model request.
  await waitFor(()=>evaluate('return document.querySelector(".rvc-routing-note").textContent.startsWith("Two-model review:") && !document.querySelector("#rvc form button[type="submit"]').disabled'),
    'two-model route plan and Send ready');
  await evaluate('document.querySelector("#rvc form").requestSubmit();return true');
  await waitFor(()=>evaluate('return Array.from(document.querySelectorAll(".rvc-receipt")).filter(e=>e.textContent.includes("REPLY RECEIVED")).length>=3'),
    'two independent model receipts',200);
  assert.equal(submits,3,'one first request plus two team requests required');
  assert.equal(submittedJobs.size,3,'each mock model request must have a separate job id');
  assert(await evaluate('return document.querySelector("#rvc-log").textContent.includes("mistral/owner-approved-test-route")'),
    'second model reply missing from transcript');
  console.log('PASS opt-in two-model task routing: two distinct requested IDs and separate completion receipts.');
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
