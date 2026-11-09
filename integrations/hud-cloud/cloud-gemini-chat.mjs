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
        method:'GET',redirect:'error',signal:AbortSignal.timeout(12000),
        headers:{'x-goog-api-key':env.GEMINI_API_KEY,'Accept':'application/json'}
      });
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

export async function cloudGeminiModels(env,send=fetch){
  const cat=await googleGeminiCatalog(env,send);
  return {source:'google_gemini_cloud_direct',provider:'google',
    online:cat.available,models:cat.available?[AUTO_GEMINI_MODEL,...cat.models]:[],
    directly_listed_models:cat.models, other_catalog_models:Math.max(0,cat.catalog_count-cat.models.length),
    quota_state:'project_free_tier_owner_attested_remaining_quota_unknown',
    model_status:'listed_in_key_catalog_not_proof_of_successful_inference',
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
    const [total,used,rows]=await Promise.all([
      env.DB.prepare('SELECT attempts FROM hud_gemini_chat_budget WHERE bucket=?').bind('d:'+day).first(),
      env.DB.prepare('SELECT completed,input_tokens,output_tokens FROM hud_gemini_chat_usage WHERE day=?').bind(day).first(),
      env.DB.prepare('SELECT model,attempts,completed,failures,input_tokens,output_tokens,last_error_code FROM hud_gemini_chat_model_usage WHERE day=? ORDER BY model').bind(day).all()
    ]);
    const models=(rows?.results||[]).filter(m=>FREE_GEMINI_MODELS.includes(m.model)).map(m=>({
      model:m.model,attempts:safeCount(m.attempts),completed:safeCount(m.completed),
      failures:safeCount(m.failures),input_tokens:safeCount(m.input_tokens),
      output_tokens:safeCount(m.output_tokens),
      last_error_code:['provider_429','provider_error','invalid_response','no_completed_text',
        'transport_error','receipt_error',null].includes(m.last_error_code)?m.last_error_code:null
    }));
    return Response.json({source:'cloud_gemini_direct',provider:'google',mac_required:false,
      day,attempts:safeCount(total?.attempts),completed:safeCount(used?.completed),
      input_tokens:safeCount(used?.input_tokens),output_tokens:safeCount(used?.output_tokens),
      models,daily_local_cap:DAY_CAP,minute_local_cap:MINUTE_CAP,
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
  const model=selectGeminiForTask(body,catalog.models);
  if(!model)return fixedError(409,'gemini_model_not_listed_for_project');
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
      method:'POST',redirect:'error',signal:AbortSignal.timeout(26000),
      headers:{'x-goog-api-key':env.GEMINI_API_KEY,'Content-Type':'application/json'},
      body:JSON.stringify({contents,generationConfig:{maxOutputTokens:768,temperature:0.25}})
    });
  }catch{
    await modelFailed(env.DB,day,model,'transport_error');
    return fixedError(502,'gemini_upstream_unavailable');
  }
  if(upstream.status===429){
    await modelFailed(env.DB,day,model,'provider_429');
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
  if(!output.trim()||output.length>12000||!['STOP','MAX_TOKENS'].includes(candidate?.finishReason)){
    await modelFailed(env.DB,day,model,'no_completed_text');
    return fixedError(502,'gemini_no_completed_text');
  }
  const usage=data?.usageMetadata||{};
  const inTok=safeCount(usage.promptTokenCount),outTok=safeCount(usage.candidatesTokenCount);
  try{
    await env.DB.batch([
      env.DB.prepare('INSERT INTO hud_gemini_chat_usage(day,completed,input_tokens,output_tokens) VALUES (?,1,?,?) '+
        'ON CONFLICT(day) DO UPDATE SET completed=completed+1,input_tokens=input_tokens+excluded.input_tokens,'+
        'output_tokens=output_tokens+excluded.output_tokens').bind(day,inTok,outTok),
      env.DB.prepare('UPDATE hud_gemini_chat_model_usage SET completed=completed+1,input_tokens=input_tokens+?,'+
        'output_tokens=output_tokens+?,last_error_code=NULL WHERE day=? AND model=?').bind(inTok,outTok,day,model)
    ]);
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
