// Bound to the existing owner-private Site; model eligibility remains in runtime.mjs.
export function createCloudOperations(base, cloud) {
 const json=(x,status=200)=>Response.json(x,{status,headers:{'Cache-Control':'no-store'}});
 const id=x=>typeof x==='string'&&/^[a-z0-9][a-z0-9-]{0,149}$/.test(x);
 const sql=(env,text,...args)=>env.DB.prepare(text).bind(...args);
 const config=(env,key,fallback={})=>JSON.parse(env[key]||JSON.stringify(fallback));
 const owner=req=>{const x=req.headers.get('oai-authenticated-user-id');return x&&x.length<=200?x:null;};
 async function bounded(response,max=32768) {
  const reader=response.body?.getReader();if(!reader)throw Error('missing_body');
  const chunks=[];let n=0;try{for(;;){const r=await reader.read();if(r.done)break;n+=r.value.length;if(n>max)throw Error('body_too_large');chunks.push(r.value);}}
  finally{await reader.cancel().catch(()=>{});}
  const all=new Uint8Array(n);let at=0;for(const chunk of chunks){all.set(chunk,at);at+=chunk.length;}
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(all));
 }
 async function proxy(request,env,writer=false) {
  const key=env[writer?'GHOST_WRITER_TOKEN':'GHOST_READER_TOKEN'];
  if(typeof key!=='string'||key.length<32)return json({error:'runtime_secret_missing'},503);
  const headers=new Headers(request.headers);headers.set('Authorization','Bearer '+key);
  return cloud.worker.fetch(new Request(request,{headers}),env);
 }
 async function status(env) {
  const response=await proxy(new Request('https://ghost.internal/api/ghost/status'),env);
  if(!response.ok)throw Error('cloud_status_unavailable');
  const data=await response.json();
  const {results}=await sql(env,`SELECT a.id,a.job_id,a.provider,a.model requested_model,a.actual_model,
   a.started_at,a.finished_at,a.status,a.error_code,a.tokens_input,a.tokens_output,a.retry_after,a.human_review,
   j.employee,j.task_id,j.title FROM ghost_cloud_attempts a JOIN ghost_cloud_jobs j ON a.job_id=j.id
   ORDER BY a.started_at DESC,a.id DESC LIMIT 50`).all();
  const cfg=config(env,'GHOST_FLEET_CONFIG');
  const providers=data.providers.map(p=>({...p,credentials_configured:!!env[cloud.PROVIDERS[p.provider][1]],
   admission:cfg[p.provider]?.enabled!==true&&env[cloud.PROVIDERS[p.provider][1]]?'disabled_pending_verification':p.admission}));
  return {...data,providers,attempts:results};
 }
 async function control(env,enabled) {
  if(typeof enabled!=='boolean')throw Error('invalid_control');
  await sql(env,'INSERT INTO ghost_cloud_control(id,enabled) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET enabled=excluded.enabled',enabled?1:0).run();
  return {enabled};
 }
 async function replenish(env) {
  if((await sql(env,'SELECT enabled FROM ghost_cloud_control WHERE id=1').first())?.enabled!==1)return {status:'stopped',queued:0};
  // These are approved cached public packets from the canonical GitHub queue,
  // not an independent ownership record or prompts supplied by a model.
  const jobs=config(env,'GHOST_APPROVED_JOBS',[]);
  if(!Array.isArray(jobs)||jobs.length>9)throw Error('invalid_approved_packets');
  jobs.forEach(cloud.validateJob);if(new Set(jobs.map(j=>j.id)).size!==jobs.length)throw Error('duplicate_packet');
  let queued=0,duplicates=0;
  for(const job of jobs){
   if((await sql(env,'SELECT enabled FROM ghost_cloud_control WHERE id=1').first())?.enabled!==1)break;
   const response=await proxy(new Request('https://ghost.internal/api/ghost/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(job)}),env,true);
   if(!response.ok)throw Error('packet_rejected');const receipt=await response.json();
   if(receipt.queued===true)queued++;else if(receipt.duplicate===true)duplicates++;else throw Error('invalid_packet_receipt');
  }
  return {queued,duplicates};
 }
 const endpoints={
  groq:'https://api.groq.com/openai/v1/models',
  gemini:'https://generativelanguage.googleapis.com/v1beta/openai/models',
  mistral:'https://api.mistral.ai/v1/models',
  nvidia:'https://integrate.api.nvidia.com/v1/models',
  openrouter:'https://openrouter.ai/api/v1/models',
  sambanova:'https://api.sambanova.ai/v1/models',
  cohere:'https://api.cohere.ai/v1/models',
  huggingface:'https://router.huggingface.co/v1/models'
 };
 async function inventory(env,provider,fetcher=fetch) {
  if(!Object.hasOwn(cloud.PROVIDERS,provider))throw Error('unknown_provider');
  const key=env[cloud.PROVIDERS[provider][1]];if(typeof key!=='string'||key.length<16)return {provider,status:'missing_secret'};
  const url=provider==='cloudflare-ai'&&/^[a-f0-9]{32}$/.test(env.CLOUDFLARE_ACCOUNT_ID||'')?
   `https://api.cloudflare.com/client/v4/accounts/${env.CLOUDFLARE_ACCOUNT_ID}/ai/models/search`:endpoints[provider];
  if(!url)return {provider,status:'account_metadata_missing'};
  try{
   const response=await fetcher(url,{method:'GET',redirect:'error',headers:{Authorization:'Bearer '+key},signal:AbortSignal.timeout(15000)});
   if(!response.ok){await response.body?.cancel();return {provider,status:'http_'+response.status};}
   const data=await bounded(response,4194304),rows=data.data||data.models||data.result;
   if(!Array.isArray(rows))return {provider,status:'unrecognized_catalog'};
   const models=rows.filter(m=>m&&typeof(m.id||m.name)==='string').filter(m=>provider!=='openrouter'||(m.id.endsWith(':free')&&m.pricing?.prompt!=null&&m.pricing?.completion!=null&&Number(m.pricing.prompt)===0&&Number(m.pricing.completion)===0)).slice(0,20).map(m=>({
    id:String(m.id||m.name).slice(0,200),context_length:Number.isSafeInteger(m.context_length)?m.context_length:null,
    catalog_zero_price:provider==='openrouter'?true:null
   }));
   return {provider,status:'catalog_received',observed_at:Date.now(),models,billing_verified:false,quota_verified:false,canary_verified:false};
  }catch(error){const message=String(error?.message||'');const category=/timeout|timed out/i.test(message)?'timeout':/network|fetch|connect|dns|resolve/i.test(message)?'network':/abort/i.test(message)?'aborted':'runtime_or_catalog';return {provider,status:'catalog_unavailable',error_category:category,error_name:['TypeError','ReferenceError','TimeoutError','AbortError','SyntaxError','Error'].includes(error?.name)?error.name:'unknown'};}
 }
 const tools=[
  {name:'rovor_cloud_workforce_status',description:'Read actual private cloud job/model/token receipts. Missing or disabled providers are explicit.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true}},
  {name:'rovor_provider_inventory',description:'Read a fixed provider models endpoint without inference. Does not establish account billing, remaining quota or successful inference.',inputSchema:{type:'object',properties:{provider:{type:'string',enum:Object.keys(cloud.PROVIDERS)}},required:['provider'],additionalProperties:false},annotations:{readOnlyHint:true}},
  {name:'rovor_cloud_control',description:'Pause or resume the existing cloud job ledger. Provider eligibility and private approvals still apply.',inputSchema:{type:'object',properties:{enabled:{type:'boolean'}},required:['enabled'],additionalProperties:false},annotations:{readOnlyHint:false,destructiveHint:false}},
  {name:'rovor_cloud_replenish',description:'Enqueue at most nine privately approved public packets copied from the canonical task queue; unchanged jobs deduplicate.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:false,destructiveHint:false}},
  {name:'rovor_cloud_tick',description:'Execute a bounded existing cloud shift only through current verified zero-cost routes, quotas, STOP and immutable claims. No automatic replay.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:false,destructiveHint:false}},
  {name:'rovor_cloud_canary',description:'Run one pre-approved private canary ID. Exact billing/quota/model evidence and short-lived approval must already be configured server-side.',inputSchema:{type:'object',properties:{canary_id:{type:'string'}},required:['canary_id'],additionalProperties:false},annotations:{readOnlyHint:false,destructiveHint:false}}
 ];
 async function call(name,args,env) {
  const allowed={rovor_cloud_workforce_status:[],rovor_provider_inventory:['provider'],rovor_cloud_control:['enabled'],rovor_cloud_replenish:[],rovor_cloud_tick:[],rovor_cloud_canary:['canary_id']};
  if(!args||typeof args!=='object'||Array.isArray(args)||Object.keys(args).some(k=>!allowed[name].includes(k)))throw Error('invalid_arguments');
  if(name==='rovor_cloud_workforce_status')return status(env);
  if(name==='rovor_provider_inventory')return inventory(env,args.provider);
  if(name==='rovor_cloud_control')return control(env,args.enabled);
  if(name==='rovor_cloud_replenish')return replenish(env);
  if(name==='rovor_cloud_tick')return cloud.tick(env);
  if(name==='rovor_cloud_canary'){
   if(!id(args.canary_id))throw Error('invalid_canary_id');
   const record=config(env,'GHOST_CANARY_APPROVALS')[args.canary_id];
   if(!record||record.approval?.canary_id!==args.canary_id)return {status:'denied',reason:'private_approval_missing'};
   return cloud.canary({...record,env});
  }
 }
 async function review(request,env,actor) {
  const origin=new URL(request.url).origin;
  if(request.headers.get('Sec-Fetch-Site')!=='same-origin'||request.headers.get('Origin')!==origin)return json({error:'owner_browser_required'},403);
  const value=await bounded(request);
  if(Object.keys(value).sort().join(',')!=='job_id,verdict'||!id(value.job_id)||!['passed','failed'].includes(value.verdict))throw Error('invalid_review');
  const attempt=await sql(env,"SELECT id,output FROM ghost_cloud_attempts WHERE job_id=? AND status='needs_review' AND human_review='not_recorded'",value.job_id).first();
  if(!attempt||typeof attempt.output!=='string'||!attempt.output.trim())return json({error:'reviewable_output_missing'},409);
  const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(attempt.output));
  const digest=[...new Uint8Array(hash)].map(b=>b.toString(16).padStart(2,'0')).join('');
  const reviewId=crypto.randomUUID();
  const [insert,update]=await env.DB.batch([
   sql(env,"INSERT INTO ghost_cloud_reviews(id,attempt_id,actor,verdict,output_sha256,reviewed_at) SELECT ?,id,?,?,?,? FROM ghost_cloud_attempts WHERE id=? AND status='needs_review' AND human_review='not_recorded' AND output=? ON CONFLICT(attempt_id) DO NOTHING",reviewId,actor,value.verdict,digest,Date.now(),attempt.id,attempt.output),
   sql(env,"UPDATE ghost_cloud_attempts SET human_review=? WHERE id=? AND human_review='not_recorded' AND EXISTS(SELECT 1 FROM ghost_cloud_reviews WHERE attempt_id=? AND id=?)",value.verdict,attempt.id,attempt.id,reviewId)
  ]);
  if(insert.meta.changes!==1||update.meta.changes!==1)return json({error:'review_already_decided'},409);
  return json({saved:true,job_id:value.job_id,verdict:value.verdict});
 }
 function browserUI(){
  let busy=false,data=null,painted='',connection='connecting',lastOk=null;
  const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
  function linkState(){
   const panel=document.getElementById('workloadPanel');if(!panel)return;
   let status=document.getElementById('rovor-cloud-link-state');
   if(!status){status=el('p');status.id='rovor-cloud-link-state';status.className='wl-card';panel.prepend(status);}
   if(connection==='connected'){
    const recent=data?.attempts?.[0];
    const date=recent&&Number.isSafeInteger(recent.finished_at||recent.started_at)?new Date(recent.finished_at||recent.started_at).toLocaleString():null;
    status.textContent='CLOUD LEDGER REACHABLE · checked '+new Date(lastOk).toLocaleTimeString()+
     (date?' · last recorded AI attempt '+date:' · no recorded AI attempts')+' · reachability does not prove agents online';
   }else{
    status.textContent='CLOUD TELEMETRY '+(connection==='connecting'?'CONNECTING':'OFFLINE')+
     ' · last successful check '+(lastOk?new Date(lastOk).toLocaleTimeString():'never')+' · cached AI activity hidden';
   }
  }
  function disconnect(){
   connection='offline';data=null;painted='';
   for(const name of ['rovor-cloud-live','rovor-cloud-results'])document.getElementById(name)?.remove();
   linkState();
  }
  function paint(){
   linkState();
   const panel=document.getElementById('workloadPanel'),activity=document.getElementById('activityPanel');if(!panel||!activity||!data)return;
   const key=JSON.stringify([data.enabled,data.providers,data.attempts]);
   if(key===painted&&document.getElementById('rovor-cloud-live')&&document.getElementById('rovor-cloud-results'))return;
   painted=key;
   const section=el('section');section.id='rovor-cloud-live';section.className='wl-card';
   section.append(el('strong','CLOUD EMPLOYEES · '+(data.enabled?'DISPATCH ENABLED':'DISPATCH PAUSED')));
   const pause=el('button',data.enabled?'PAUSE':'RESUME');pause.className='wl-button';pause.onclick=async()=>{try{const r=await fetch('/api/ghost/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:!data.enabled})});if(!r.ok)throw Error('control_unavailable');await poll();}catch{disconnect();}};section.append(pause);
   for(const p of data.providers){const last=data.attempts.find(a=>a.provider===p.provider);section.append(el('p',p.provider+' · '+p.admission+(last?' · '+last.status:' · no execution receipt')));}
   const old=document.getElementById(section.id);if(old)old.replaceWith(section);else panel.prepend(section);
   const results=el('section');results.id='rovor-cloud-results';results.append(el('strong','RECORDED CLOUD WORK'));
   if(!data.attempts.length)results.append(el('p','No cloud request has completed yet.'));
   for(const a of data.attempts.slice(0,12)){
    const row=el('details');row.className='wl-card';row.append(el('summary',a.employee+' · '+a.provider+' · '+a.status+' · '+a.human_review));
    row.append(el('p',a.title));row.append(el('p','Actual model: '+(a.actual_model||'unknown')+' · tokens: '+(a.tokens_input??'?')+' / '+(a.tokens_output??'?')));
    if(a.finished_at)row.append(el('p',new Date(a.finished_at).toLocaleString()));
    if(a.status==='needs_review'){
     const view=el('button','VIEW OUTPUT');view.className='wl-button';const output=el('pre');output.style.cssText='white-space:pre-wrap;max-height:240px;overflow:auto';
     const controls=el('div');controls.hidden=true;
     for(const [label,verdict] of [['PASS','passed'],['FAIL','failed']]){const b=el('button',label);b.className='wl-button';b.onclick=async()=>{const r=await fetch('/api/ghost/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:a.job_id,verdict})});if(r.ok)await poll();else output.textContent='Review could not be saved.';};controls.append(b);}
     view.onclick=async()=>{const r=await fetch('/api/ghost/jobs/'+encodeURIComponent(a.job_id));if(r.ok){const j=await r.json();output.textContent=j.output||'No reviewable draft.';controls.hidden=!j.output;}};
     row.append(view,output,controls);
    }
    results.append(row);
   }
   const prior=document.getElementById(results.id);if(prior)prior.replaceWith(results);else activity.prepend(results);
  }
  async function poll(){
   if(busy||document.hidden)return;busy=true;
   try{
    const r=await fetch('/api/ghost/status',{cache:'no-store',signal:AbortSignal.timeout(8000)});
    if(!r.ok)throw Error('cloud_telemetry_unavailable');
    const snapshot=await r.json();
    if(!snapshot||snapshot.execution_source!=='cloud_provider'||!Number.isSafeInteger(snapshot.observed_at)||
       typeof snapshot.enabled!=='boolean'||!Array.isArray(snapshot.providers)||snapshot.providers.length!==9||
       !Array.isArray(snapshot.attempts))throw Error('cloud_telemetry_invalid');
    data=snapshot;connection='connected';lastOk=Date.now();paint();
   }catch{disconnect();}finally{busy=false;}
  }
  linkState();poll();setInterval(poll,15000);document.addEventListener('visibilitychange',poll);
  for(const name of ['workloadPanel','activityPanel']){const panel=document.getElementById(name);if(panel)new MutationObserver(()=>{if(!document.getElementById(name==='workloadPanel'?'rovor-cloud-live':'rovor-cloud-results'))paint();}).observe(panel,{childList:true});}
 }
 const script='<script>('+browserUI.toString()+')();</script>';
 return {
  inventory,status,control,replenish,
  async fetch(request,env){
   const url=new URL(request.url),actor=owner(request);
   // Only the registered owner-private Site's dispatch may invoke this shared
   // service route. Platform service access is separate from browser identity.
   if(url.pathname==='/api/ghost/service'&&request.method==='POST'){
    try {
     const body=await bounded(request);
     if(Object.keys(body).some(k=>!['operation','provider'].includes(k)))throw Error('invalid_service');
     if(body.operation==='status')return json(await status(env));
     if(body.operation==='inventory')return json(await inventory(env,body.provider));
     if(body.operation==='shift'){
      const intake=await replenish(env);
      const result=await cloud.tick(env);
      return json({intake,result,observed_at:Date.now()});
     }
     return json({error:'unsupported_service_operation'},400);
    }catch{return json({error:'service_operation_failed'},503);}
   }
   if(url.pathname.startsWith('/api/ghost/')){
    if(!actor)return json({error:'site_identity_required'},401);
    try{
     if(url.pathname==='/api/ghost/status'&&request.method==='GET')return json(await status(env));
     if(url.pathname==='/api/ghost/control'&&request.method==='POST'){
      const body=await bounded(request);if(Object.keys(body).join(',')!=='enabled')throw Error('invalid_control');return json(await control(env,body.enabled));
     }
     if(url.pathname==='/api/ghost/review'&&request.method==='POST')return review(request,env,actor);
     if(request.method==='GET'&&/^\/api\/ghost\/jobs\/[a-z0-9-]+$/.test(url.pathname))return proxy(request,env);
     return json({error:'unsupported_operation'},404);
    }catch{return json({error:'cloud_operation_failed'},503);}
   }
   if(url.pathname==='/mcp'&&request.method==='POST'&&actor){
    let rpc;try{rpc=await bounded(request.clone());}catch{return json({error:'invalid_rpc'},400);}
    if(rpc.method==='tools/list'){
     const response=await base(request,env),data=await response.json();if(Array.isArray(data.result?.tools))data.result.tools.push(...tools);return json(data,response.status);
    }
    if(rpc.method==='tools/call'&&tools.some(t=>t.name===rpc.params?.name)){
     try{return json({jsonrpc:'2.0',id:rpc.id??null,result:{content:[{type:'text',text:JSON.stringify(await call(rpc.params.name,rpc.params.arguments||{},env))}]}});}
     catch{return json({jsonrpc:'2.0',id:rpc.id??null,result:{isError:true,content:[{type:'text',text:'Cloud operation failed; no automatic retry.'}]}});}
    }
    if(rpc.method==='tools/call'&&rpc.params?.name==='rovor_workforce_status'){
     const response=await base(request,env),data=await response.json();
     try{data.result.content.push({type:'text',text:JSON.stringify({cloud:await status(env)})});}catch{}
     return json(data,response.status);
    }
   }
   const response=await base(request,env);
   if(actor&&request.method==='GET'&&['/','/index.html'].includes(url.pathname)&&response.ok&&(response.headers.get('Content-Type')||'').includes('text/html')){
    const html=await response.text();return new Response(html.replace('</body>',script+'</body>'),{status:response.status,headers:response.headers});
   }
   return response;
  }
 };
}
