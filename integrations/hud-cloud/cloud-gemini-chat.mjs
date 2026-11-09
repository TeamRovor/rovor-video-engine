// Cloud-native, owner-private Google Gemini text chat; no Mac/OmniRoute dependency.
// Strict single free-tier model, no tools, fallback, retries, or secrets in output.
// A project-level Free-tier attestation is REQUIRED; no API can infer billing tier from a key.
const MODEL='gemini-3.1-flash-lite';
const ORIGIN='https://generativelanguage.googleapis.com/v1beta/models/';
const DAY_CAP=12, MINUTE_CAP=2;
const json=(status,body)=>Response.json(body,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
const configured=env=>typeof env.GEMINI_API_KEY==='string'&&env.GEMINI_API_KEY.length>=24&&
  env.ROVOR_GEMINI_FREE_TIER_VERIFIED==='confirmed';
const dayAt=now=>new Date(now).toISOString().slice(0,10);
const safeCount=n=>Number.isSafeInteger(n)&&n>=0?n:0;

export function cloudGeminiModels(env) {
  const ready=configured(env);
  return {source:'google_gemini_cloud_direct',online:ready,models:ready?[MODEL]:[],
    quota_state:'free_tier_owner_attested_not_live_remaining_quota',
    mac_required:false,provider:'google',requires_zero_cost_project:true};
}
export function validateGeminiChat(body) {
  if(!body||typeof body!=='object'||Array.isArray(body)||body.model!==MODEL||
     !Array.isArray(body.messages)||body.messages.length<1||body.messages.length>8)
    throw Error('invalid_gemini_chat');
  let chars=0;
  const messages=body.messages.map(row=>{
    if(!row||!['user','assistant'].includes(row.role)||typeof row.content!=='string'||
       !row.content.trim()||row.content.length>4000)throw Error('invalid_gemini_chat');
    chars+=row.content.length;
    return {role:row.role==='assistant'?'model':'user',parts:[{text:row.content}]};
  });
  if(chars>12000||body.messages.at(-1).role!=='user')throw Error('invalid_gemini_chat');
  return messages;
}
export async function cloudGeminiUsage(env,now=Date.now()) {
  if(!env.DB)return json(503,{error:'private_store_unavailable'});
  try {
    const day=dayAt(now);
    const [total,used]=await Promise.all([
      env.DB.prepare("SELECT attempts FROM hud_gemini_chat_budget WHERE bucket=?").bind('d:'+day).first(),
      env.DB.prepare("SELECT completed,input_tokens,output_tokens FROM hud_gemini_chat_usage WHERE day=?").bind(day).first()
    ]);
    return json(200,{source:'cloud_gemini_direct',model:MODEL,provider:'google',
      mac_required:false,day,attempts:safeCount(total?.attempts),
      completed:safeCount(used?.completed),input_tokens:safeCount(used?.input_tokens),
      output_tokens:safeCount(used?.output_tokens),daily_local_cap:DAY_CAP,
      quota_remaining:'not_verified_provider_wide',quota_reset:'not_verified_provider_wide'});
  }catch{return json(503,{error:'private_store_unavailable'});}
}
// D1 reservations are atomic. A denied minute check may still consume a day slot:
// conservative fail-closed admission is intentional. No automatic retries.
async function reserve(db,bucket,max) {
  const row=await db.prepare(`INSERT INTO hud_gemini_chat_budget(bucket,attempts) VALUES (?,1)
    ON CONFLICT(bucket) DO UPDATE SET attempts=attempts+1 WHERE attempts < ?
    RETURNING attempts`).bind(bucket,max).first();
  return !!row;
}
export async function cloudGeminiChat(body,env,now=Date.now(),send=fetch) {
  if(!configured(env))return json(503,{error:'gemini_cloud_free_tier_not_configured'});
  if(!env.DB)return json(503,{error:'private_store_unavailable'});
  let contents;
  try{contents=validateGeminiChat(body);}catch{return json(400,{error:'invalid_gemini_chat'});}
  const stamp=new Date(now).toISOString(),day=dayAt(now);
  try{
    if(!await reserve(env.DB,'d:'+day,DAY_CAP))return json(429,{error:'gemini_daily_local_cap_reached'});
    if(!await reserve(env.DB,'m:'+stamp.slice(0,16),MINUTE_CAP))return json(429,{error:'gemini_minute_local_cap_reached'});
  }catch{return json(503,{error:'private_budget_unavailable'});}
  let upstream;
  try{
    upstream=await send(ORIGIN+MODEL+':generateContent',{
      method:'POST',redirect:'manual',signal:AbortSignal.timeout(26000),
      headers:{'x-goog-api-key':env.GEMINI_API_KEY,'Content-Type':'application/json'},
      body:JSON.stringify({contents,generationConfig:{maxOutputTokens:256,temperature:0.2}})
    });
  }catch{return json(502,{error:'gemini_upstream_unavailable'});}
  // Explicitly reject 3xx: redirect:"error" is unsupported in Workers.
  if(upstream.status>=300&&upstream.status<400)return json(502,{error:'gemini_upstream_redirect_denied'});
  if(upstream.status===429)return json(429,{error:'gemini_provider_rate_limited'});
  if(!upstream.ok)return json(502,{error:'gemini_upstream_failed'});
  let document;
  try{document=await upstream.json();}catch{return json(502,{error:'gemini_invalid_response'});}
  const candidate=document?.candidates?.[0];
  const output=candidate?.content?.parts?.filter(p=>typeof p?.text==='string').map(p=>p.text).join('')||'';
  // Do not report a blocked, unfinished, or empty response as a completed answer.
  if(!output.trim()||output.length>12000||
     !['STOP','MAX_TOKENS'].includes(candidate?.finishReason))
    return json(502,{error:'gemini_no_completed_text'});
  const tokens=document?.usageMetadata||{};
  const inTok=safeCount(tokens.promptTokenCount),outTok=safeCount(tokens.candidatesTokenCount);
  try{
    await env.DB.prepare(`INSERT INTO hud_gemini_chat_usage(day,completed,input_tokens,output_tokens)
      VALUES (?,1,?,?) ON CONFLICT(day) DO UPDATE SET
      completed=completed+1,input_tokens=input_tokens+excluded.input_tokens,
      output_tokens=output_tokens+excluded.output_tokens`).bind(day,inTok,outTok).run();
  }catch{return json(503,{error:'gemini_receipt_store_unavailable_no_replay'});}
  // The existing Ask ROVOR UI consumes OpenAI-style SSE; Gemini returns JSON.
  const data='data: '+JSON.stringify({choices:[{delta:{content:output}}]})+'\n\n'+'data: [DONE]\n\n';
  return new Response(data,{status:200,headers:{'Content-Type':'text/event-stream',
    'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
    'X-ROVOR-Provider':'google-gemini-cloud','X-ROVOR-Requested-Model':MODEL}});
}
