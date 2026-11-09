// Cloud-only Gemini text chat for the EXISTING owner-private ROVOR HUD.
// Catalog discovery is not proof of inference access, free billing, or remaining
// quota. Permit only the reviewed text models with published free-tier pricing
// and an explicit Free-tier project attestation. Never invoke tools, paid tiers,
// batch/priority, fallbacks or retries. All model calls require reader auth at
// the worker entrypoint and atomic D1 project-wide reservations.
export const AUTO_GEMINI_MODEL='gemini-auto-free';
export const FREE_GEMINI_MODELS=Object.freeze([
  'gemini-3.8-flash',
  'gemini-3.7-flash',
  'gemini-3.6-flash',
  'gemini-3.5-flash',
  'gemini-3.5-flash-lite',
  'gemini-3.1-flash-lite',
  'gemini-2.5-flash',
  'gemini-2.5-flash-lite'
]);
const ENDPOINT='https://generativelanguage.googleapis.com/v1beta/models';
const DAY_CAP=12, MINUTE_CAP=2, MAX_PAGES=5;
const fixedError=(status,error)=>Response.json({error},{status,headers:{
  'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
const configured=env=>typeof env?.GEMINI_API_KEY==='string'&&
  env.GEMINI_API_KEY.length>=24&&env.ROVOR_GEMINI_FREE_TIER_VERIFIED==='confirmed';
const dayAt=now=>new Date(now).toISOString().slice(0,10);
const safeCount=n=>Number.isSafeInteger(n)&&n>=0?n:0;

const VERIFIED_WINDOW_MS=7*86400000;
const COOLDOWN_MS=60*60000;
// Dates in this ledger are UTC. Google's separate project RPD reset is
// midnight Pacific; we do not derive project remaining quota from these rows.
const localReset=(now)=>new Date(Math.floor(now/60000)*60000+60000).toISOString();
const localDayReset=(now)=>new Date(Date.parse(dayAt(now)+'T00:00:00.000Z')+86400000).toISOString();
const validTime=n=>Number.isSafeInteger(n)&&n>0?n:null;

export async function geminiModelEvidence(db,now=Date.now()){
  if(!db)throw Error('model_evidence_store_unavailable');
  const since=dayAt(now-VERIFIED_WINDOW_MS);
  const [historical,health]=await Promise.all([
    db.prepare('SELECT model,MAX(day) last_day FROM hud_gemini_chat_model_usage WHERE day>=? AND completed>0 GROUP BY model')
      .bind(since).all(),
    db.prepare('SELECT model,last_success_at,success_count,last_rate_limited_at,cooldown_until,last_failure_at,last_failure_code FROM hud_gemini_model_health')
      .all()
  ]);
  if(!Array.isArray(historical?.results)||!Array.isArray(health?.results))throw Error('model_evidence_store_invalid');
  const prior=new Map(historical.results.filter(x=>FREE_GEMINI_MODELS.includes(x.model)&&
    typeof x.last_day==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x.last_day)&&x.last_day<=dayAt(now))
    .map(x=>[x.model,x.last_day]));
  const records=new Map(health.results.filter(x=>FREE_GEMINI_MODELS.includes(x.model)).map(x=>[x.model,x]));
  return new Map(FREE_GEMINI_MODELS.map(model=>{
    const row=records.get(model)||{};
    const exact=validTime(row.last_success_at);
    const day=prior.get(model)||null;
    const recent=!!((exact&&exact<=now&&now-exact<=VERIFIED_WINDOW_MS)||
      (day&&day>=since));
    const until=validTime(row.cooldown_until);
    const cooling=!!until&&until>now;
    return [model,{
      model,
      verification:cooling?'provider_cooldown':recent?'verified_recent_reply':'listed_unverified',
      last_verified_at:exact&&exact<=now?new Date(exact).toISOString():null,
      last_verified_day:day,
      last_rate_limited_at:validTime(row.last_rate_limited_at)&&row.last_rate_limited_at<=now?
        new Date(row.last_rate_limited_at).toISOString():null,
      cooldown_until:cooling?new Date(until).toISOString():null,
      // All verifications derive from actual completed D1 model receipts.
      evidence:'private_hud_google_reply_receipt',verified_window_days:7
    }];
  }));
}
async function markGeminiSuccess(db,model,now){
  await db.prepare('INSERT INTO hud_gemini_model_health(model,last_success_at,success_count,cooldown_until,last_failure_at,last_failure_code) VALUES (?, ?,1,NULL,NULL,NULL) '+
    'ON CONFLICT(model) DO UPDATE SET last_success_at=excluded.last_success_at,success_count=success_count+1,cooldown_until=NULL,last_failure_code=NULL')
    .bind(model,now).run();
}
async function markGeminiRateLimit(db,model,now){
  await db.prepare('INSERT INTO hud_gemini_model_health(model,last_rate_limited_at,cooldown_until,last_failure_at,last_failure_code) VALUES (?,?,?,?,?) '+
    'ON CONFLICT(model) DO UPDATE SET last_rate_limited_at=excluded.last_rate_limited_at,cooldown_until=excluded.cooldown_until,last_failure_at=excluded.last_failure_at,last_failure_code=excluded.last_failure_code')
    .bind(model,now,now+COOLDOWN_MS,now,'provider_429').run();
}


export function ownerApprovedModels(env) {
  // An optional project-specific subset can narrow the known free-price
  // registry. Unknown/paid/invalid model IDs fail closed (no partial enable).
  if(!env?.ROVOR_GEMINI_FREE_MODELS)return [...FREE_GEMINI_MODELS];
  let chosen;
  try{chosen=JSON.parse(env.ROVOR_GEMINI_FREE_MODELS);}
  catch{return [];}
  if(!Array.isArray(chosen)||!chosen.length||chosen.length>FREE_GEMINI_MODELS.length||
     new Set(chosen).size!==chosen.length||
     chosen.some(m=>typeof m!=='string'||!FREE_GEMINI_MODELS.includes(m)))return [];
  return FREE_GEMINI_MODELS.filter(m=>chosen.includes(m));
}

export async function googleGeminiCatalog(env,send=fetch) {
  if(!configured(env))return {available:false,models:[],catalog_count:0,reason:'free_project_or_key_unconfigured'};
  const allowed=ownerApprovedModels(env);
  if(!allowed.length)return {available:false,models:[],catalog_count:0,reason:'owner_model_allowlist_invalid'};
  const found=new Set();
  const seenTokens=new Set();
  let pageToken=null,count=0;
  try {
    for(let page=0;page<MAX_PAGES;page++){
      const url=new URL(ENDPOINT);
      url.searchParams.set('pageSize','100');
      if(pageToken)url.searchParams.set('pageToken',pageToken);
      const response=await send(url.toString(),{
        method:'GET',redirect:'manual',signal:AbortSignal.timeout(12000),
        headers:{'x-goog-api-key':env.GEMINI_API_KEY,'Accept':'application/json'}
      });
      // Workers does not support redirect:'error'; manual means provider keys never follow redirects.
      if(response.status>=300&&response.status<400)return {available:false,models:[],catalog_count:0,reason:'google_catalog_redirect_denied'};
      if(!response.ok)return {available:false,models:[],catalog_count:0,reason:'google_catalog_http_'+
        (response.status===401||response.status===403?'auth_denied':'unavailable')};
      const body=await response.text();
      if(body.length>250000)throw Error('catalog_too_large');
      const data=JSON.parse(body);
      if(!Array.isArray(data.models)||data.models.length>1000)throw Error('catalog_invalid');
      count+=data.models.length;
      if(count>500)throw Error('catalog_too_large');
      for(const m of data.models){
        const id=typeof m?.name==='string'&&m.name.startsWith('models/')?m.name.slice(7):null;
        if(id&&allowed.includes(id)&&Array.isArray(m.supportedGenerationMethods)&&
           m.supportedGenerationMethods.includes('generateContent'))found.add(id);
      }
      const next=data.nextPageToken;
      if(next===undefined||next===null||next==='')break;
      if(typeof next!=='string'||next.length>300||seenTokens.has(next)||page===MAX_PAGES-1)
        throw Error('catalog_pagination_unverified');
      seenTokens.add(next);
      pageToken=next;
    }
  }catch{
    return {available:false,models:[],catalog_count:0,reason:'google_catalog_unavailable'};
  }
  const models=allowed.filter(id=>found.has(id));
  return {available:models.length>0,models,catalog_count:count,
    reason:models.length?'catalog_listed_unverified_for_inference':'no_approved_free_text_models_listed'};
}

export async function cloudGeminiModels(env,send=fetch,now=Date.now()){
  const cat=await googleGeminiCatalog(env,send);
  let evidence=new Map(),evidenceState='not_checked';
  if(cat.available){
    try {evidence=await geminiModelEvidence(env.DB,now);evidenceState='private_d1_verified';}
    catch {evidenceState='unavailable_no_automatic_routing';}
  }
  const rows=cat.models.map(model=>evidence.get(model)||{
    model,verification:'evidence_unavailable',last_verified_at:null,last_verified_day:null,
    last_rate_limited_at:null,cooldown_until:null,evidence:'unavailable',verified_window_days:7
  });
  const verified=rows.filter(r=>r.verification==='verified_recent_reply').length;
  return {source:'google_gemini_cloud_direct',provider:'google',
    online:cat.available,models:cat.available?[AUTO_GEMINI_MODEL,...cat.models]:[],
    directly_listed_models:cat.models, other_catalog_models:Math.max(0,cat.catalog_count-cat.models.length),
    model_evidence:rows,verified_model_count:verified,model_evidence_state:evidenceState,
    quota_state:'project_free_tier_owner_attested_remaining_quota_unknown',
    model_status:'catalog_listing_distinct_from_verified_reply',
    discovery_reason:cat.reason,mac_required:false,requires_zero_cost_project:true};
}

export function validateGeminiChat(body){
  if(!body||typeof body!=='object'||Array.isArray(body)||
     ![AUTO_GEMINI_MODEL,...FREE_GEMINI_MODELS].includes(body.model)||
     !Array.isArray(body.messages)||body.messages.length<1||body.messages.length>8)
    throw Error('invalid_gemini_chat');
  let chars=0;
  const contents=body.messages.map(row=>{
    if(!row||!['user','assistant'].includes(row.role)||typeof row.content!=='string'||
       !row.content.trim()||row.content.length>4000)throw Error('invalid_gemini_chat');
    chars+=row.content.length;
    return {role:row.role==='assistant'?'model':'user',parts:[{text:row.content}]};
  });
  if(chars>12000||body.messages.at(-1).role!=='user')throw Error('invalid_gemini_chat');
  return contents;
}

export function selectGeminiForTask(body,allowed){
  if(!Array.isArray(allowed)||!allowed.length)return null;
  if(body.model!==AUTO_GEMINI_MODEL)return allowed.includes(body.model)?body.model:null;
  // Capability selection, NOT round robin. One route is chosen once for each
  // request; no unapproved provider substitution on a failed or 429 response.
  const text=body.messages.filter(m=>m.role==='user').map(m=>m.content).join(' ').slice(0,12000);
  const complex=/\b(debug|refactor|architecture|design system|research|analy[sz]e|reason|compare|code|algorithm|database|security|github|technical)\b/i.test(text)||
    text.length>2000;
  const choices=complex?
    ['gemini-3.8-flash','gemini-3.7-flash','gemini-3.6-flash','gemini-3.5-flash','gemini-3.1-flash-lite','gemini-3.5-flash-lite']:
    ['gemini-3.5-flash-lite','gemini-3.1-flash-lite','gemini-2.5-flash-lite',
      'gemini-3.5-flash','gemini-3.8-flash'];
  return choices.find(x=>allowed.includes(x))||allowed[0];
}

export async function cloudGeminiUsage(env,now=Date.now()){
  if(!env?.DB)return fixedError(503,'private_store_unavailable');
  try{
    const day=dayAt(now);
    const [total,minute,used,rows,evidence]=await Promise.all([
      env.DB.prepare('SELECT attempts FROM hud_gemini_chat_budget WHERE bucket=?').bind('d:'+day).first(),
      env.DB.prepare('SELECT attempts FROM hud_gemini_chat_budget WHERE bucket=?').bind('m:'+new Date(now).toISOString().slice(0,16)).first(),
      env.DB.prepare('SELECT completed,input_tokens,output_tokens FROM hud_gemini_chat_usage WHERE day=?').bind(day).first(),
      env.DB.prepare('SELECT model,attempts,completed,failures,input_tokens,output_tokens,last_error_code FROM hud_gemini_chat_model_usage WHERE day=? ORDER BY model').bind(day).all(),
      geminiModelEvidence(env.DB,now)
    ]);
    const models=(rows?.results||[]).filter(m=>FREE_GEMINI_MODELS.includes(m.model)).map(m=>({
      model:m.model,attempts:safeCount(m.attempts),completed:safeCount(m.completed),
      failures:safeCount(m.failures),input_tokens:safeCount(m.input_tokens),
      output_tokens:safeCount(m.output_tokens),
      last_error_code:['provider_429','provider_error','invalid_response','no_completed_text',
        'transport_error','receipt_error',null].includes(m.last_error_code)?m.last_error_code:null
    }));
    return Response.json({source:'cloud_gemini_direct',provider:'google',mac_required:false,
      day,observed_at:new Date(now).toISOString(),scope:'this_hud_direct_api_only',
      attempts:safeCount(total?.attempts),completed:safeCount(used?.completed),
      input_tokens:safeCount(used?.input_tokens),output_tokens:safeCount(used?.output_tokens),
      models,model_evidence:[...evidence.values()].filter(x=>x.verification!=='listed_unverified'||models.some(m=>m.model===x.model)),
      daily_local_cap:DAY_CAP,minute_local_cap:MINUTE_CAP,
      daily_local_remaining:Math.max(0,DAY_CAP-safeCount(total?.attempts)),
      minute_local_remaining:Math.max(0,MINUTE_CAP-safeCount(minute?.attempts)),
      daily_local_reset_at:localDayReset(now),minute_local_reset_at:localReset(now),
      local_cap_time_zone:'UTC',local_attempts_include_reservations_not_only_provider_calls:true,
      quota_remaining:'not_verified_provider_wide',quota_reset:'not_verified_provider_wide'},
      {headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
  }catch{return fixedError(503,'private_store_unavailable');}
}

async function reserve(db,bucket,max){
  const row=await db.prepare('INSERT INTO hud_gemini_chat_budget(bucket,attempts) VALUES (?,1) '+
    'ON CONFLICT(bucket) DO UPDATE SET attempts=attempts+1 WHERE attempts < ? RETURNING attempts')
    .bind(bucket,max).first();
  return !!row;
}
async function modelAttempt(db,day,model){
  await db.prepare('INSERT INTO hud_gemini_chat_model_usage(day,model,attempts) VALUES (?,?,1) '+
    'ON CONFLICT(day,model) DO UPDATE SET attempts=attempts+1').bind(day,model).run();
}
async function modelFailed(db,day,model,code){
  try{
    await db.prepare('UPDATE hud_gemini_chat_model_usage SET failures=failures+1,last_error_code=? WHERE day=? AND model=?')
      .bind(code,day,model).run();
  }catch{/* A failed receipt cannot be counted as verified. No retry. */}
}

export async function cloudGeminiChat(body,env,now=Date.now(),send=fetch){
  if(!configured(env))return fixedError(503,'gemini_cloud_free_tier_not_configured');
  if(!env.DB)return fixedError(503,'private_store_unavailable');
  let contents;
  try{contents=validateGeminiChat(body);}catch{return fixedError(400,'invalid_gemini_chat');}
  const catalog=await googleGeminiCatalog(env,send);
  if(!catalog.available)return fixedError(503,catalog.reason);
  let evidence;
  try {evidence=await geminiModelEvidence(env.DB,now);}
  catch {return fixedError(503,'gemini_verification_store_unavailable');}
  const candidates=body.model===AUTO_GEMINI_MODEL?
    catalog.models.filter(m=>evidence.get(m)?.verification==='verified_recent_reply'):catalog.models;
  const model=selectGeminiForTask(body,candidates);
  if(!model)return fixedError(409,body.model===AUTO_GEMINI_MODEL?
    'gemini_auto_requires_recent_verified_model':'gemini_model_not_listed_for_project');
  if(evidence.get(model)?.verification==='provider_cooldown')
    return fixedError(429,'gemini_model_cooldown_active');
  const stamp=new Date(now).toISOString(),day=dayAt(now);
  try{
    if(!await reserve(env.DB,'d:'+day,DAY_CAP))return fixedError(429,'gemini_daily_local_cap_reached');
    if(!await reserve(env.DB,'m:'+stamp.slice(0,16),MINUTE_CAP))
      return fixedError(429,'gemini_minute_local_cap_reached');
    // Verify that private D1 has the forward-only model receipt table BEFORE
    // making any request that could spend the free project allowance.
    await modelAttempt(env.DB,day,model);
  }catch{return fixedError(503,'private_model_budget_unavailable');}
  let upstream;
  try{
    upstream=await send(ENDPOINT+'/'+model+':generateContent',{
      method:'POST',redirect:'manual',signal:AbortSignal.timeout(26000),
      headers:{'x-goog-api-key':env.GEMINI_API_KEY,'Content-Type':'application/json'},
      body:JSON.stringify({contents,generationConfig:{maxOutputTokens:model.endsWith('-lite')?1024:2048,temperature:0.25}})
    });
  }catch{
    await modelFailed(env.DB,day,model,'transport_error');
    return fixedError(502,'gemini_upstream_unavailable');
  }
  // Never forward the Google API key to a redirected destination.
  if(upstream.status>=300&&upstream.status<400){
    await modelFailed(env.DB,day,model,'provider_error');
    return fixedError(502,'gemini_upstream_redirect_denied');
  }
  if(upstream.status===429){
    await modelFailed(env.DB,day,model,'provider_429');
    try{await markGeminiRateLimit(env.DB,model,now);}
    catch{return fixedError(503,'gemini_rate_limit_evidence_not_stored');}
    return fixedError(429,'gemini_provider_rate_limited');
  }
  if(!upstream.ok){
    await modelFailed(env.DB,day,model,'provider_error');
    return fixedError(502,'gemini_upstream_failed');
  }
  let data;
  try{data=await upstream.json();}catch{
    await modelFailed(env.DB,day,model,'invalid_response');
    return fixedError(502,'gemini_invalid_response');
  }
  const candidate=data?.candidates?.[0];
  const output=candidate?.content?.parts?.filter(p=>typeof p?.text==='string').map(p=>p.text).join('')||'';
  if(!output.trim()||output.length>12000||candidate?.finishReason!=='STOP'){
    await modelFailed(env.DB,day,model,'no_completed_text');
    return fixedError(502,'gemini_no_completed_text');
  }
  const usage=data?.usageMetadata||{};
  if(!Number.isSafeInteger(usage.promptTokenCount)||usage.promptTokenCount<0||
     !Number.isSafeInteger(usage.candidatesTokenCount)||usage.candidatesTokenCount<0){
    await modelFailed(env.DB,day,model,'invalid_response');
    return fixedError(502,'gemini_token_usage_unverified');
  }
  const inTok=usage.promptTokenCount,outTok=usage.candidatesTokenCount;
  try{
    await env.DB.batch([
      env.DB.prepare('INSERT INTO hud_gemini_chat_usage(day,completed,input_tokens,output_tokens) VALUES (?,1,?,?) '+
        'ON CONFLICT(day) DO UPDATE SET completed=completed+1,input_tokens=input_tokens+excluded.input_tokens,'+
        'output_tokens=output_tokens+excluded.output_tokens').bind(day,inTok,outTok),
      env.DB.prepare('UPDATE hud_gemini_chat_model_usage SET completed=completed+1,input_tokens=input_tokens+?,'+
        'output_tokens=output_tokens+?,last_error_code=NULL WHERE day=? AND model=?').bind(inTok,outTok,day,model)
    ]);
    await markGeminiSuccess(env.DB,model,now);
  }catch{
    await modelFailed(env.DB,day,model,'receipt_error');
    return fixedError(503,'gemini_receipt_store_unavailable_no_replay');
  }
  // Existing Ask ROVOR reads SSE even for cloud model replies.
  const payload='data: '+JSON.stringify({choices:[{delta:{content:output}}]})+'\n\n'+'data: [DONE]\n\n';
  return new Response(payload,{status:200,headers:{
    'Content-Type':'text/event-stream','Cache-Control':'no-store',
    'X-Content-Type-Options':'nosniff','X-ROVOR-Provider':'google-gemini-cloud',
    'X-ROVOR-Requested-Model':body.model,'X-ROVOR-Resolved-Model':model
  }});
}
