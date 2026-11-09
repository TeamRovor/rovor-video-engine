import {groqCatalogEvidence} from './groq-quota-monitor.mjs';
// Mac-independent, owner-private Groq chat. Fixed endpoint/model; no paid fallback.
// This module never reads local OmniRoute, starts workers or stores raw prompts.
export const GROQ_CLOUD_ROUTE = 'groq/openai/gpt-oss-20b';
const UPSTREAM_MODEL = 'openai/gpt-oss-20b';
const ENDPOINT = 'https://api.groq.com/openai/v1/chat/completions';
const DAY = 86400000;
const error = (status,code) => Response.json({error:code},{status,headers:{'Cache-Control':'no-store'}});
const goodInteger=n=>Number.isSafeInteger(n)&&n>=0;
const digits=v=>typeof v==='string'&&/^(0|[1-9][0-9]{0,15})$/.test(v)?Number(v):null;

// All conditions are independent private operator attestations; the hash and
// booleans do NOT themselves prove billing or quota. Expiry fails closed.
// Provider catalogue presence and rate-limit headers do not prove Free billing.
// Every inference call must pass this current owner-verified admission gate.
export function groqAdmission(env,now=Date.now()){
  const denied=reason=>({ready:false,reason,verification_expires_at:null});
  if(env?.GROQ_HUD_CHAT_ENABLED!=='true')return denied('chat_disabled');
  if(typeof env?.GROQ_HUD_API_KEY!=='string'||env.GROQ_HUD_API_KEY.length<16)return denied('cloud_key_unavailable');
  if(env?.GROQ_HUD_FREE_TIER_VERIFIED!=='true')return denied('owner_free_tier_attestation_missing');
  if(!/^[a-f0-9]{64}$/.test(env?.GROQ_HUD_EVIDENCE_SHA256||''))return denied('owner_evidence_digest_missing');
  const verified=digits(env?.GROQ_HUD_VERIFIED_AT),valid=digits(env?.GROQ_HUD_VALID_UNTIL);
  if(!goodInteger(verified)||!goodInteger(valid)||verified>now||valid<=verified||valid>verified+DAY)
    return denied('attestation_dates_invalid');
  if(now-verified>DAY||valid<=now)return denied('owner_attestation_expired');
  const cap=digits(env?.GROQ_HUD_DAILY_BUDGET);
  if(!goodInteger(cap)||cap<1||cap>30)return denied('daily_budget_invalid');
  return {ready:true,reason:'ready',verification_expires_at:new Date(valid).toISOString(),local_daily_request_cap:cap};
}
export function groqCloudReady(env,now=Date.now()){return groqAdmission(env,now).ready;}

function validatedMessages(body) {
  if(!body||!Array.isArray(body.messages)||body.messages.length<1||body.messages.length>12)return null;
  let total=0;const out=[];
  for(const m of body.messages){
    if(!m||(m.role!=='user'&&m.role!=='assistant')||typeof m.content!=='string'||
       !m.content.trim()||m.content.length>3000)return null;
    total+=m.content.length;if(total>12000)return null;
    out.push({role:m.role,content:m.content});
  }
  return out[out.length-1].role==='user'?out:null;
}

async function reserve(db,now,limit){
  const day=Math.floor(now/DAY);
  // Atomic cross-isolate D1 request reservation. Failed calls still count;
  // other users of the same Groq organization are not measured here.
  return db.prepare(`INSERT INTO hud_groq_chat_admission(id,day_id,attempts,last_started_at)
    VALUES(1,?,1,?) ON CONFLICT(id) DO UPDATE SET
    day_id=excluded.day_id,
    attempts=CASE WHEN hud_groq_chat_admission.day_id=excluded.day_id
                  THEN hud_groq_chat_admission.attempts+1 ELSE 1 END,
    last_started_at=excluded.last_started_at
    WHERE hud_groq_chat_admission.day_id<excluded.day_id OR
      (hud_groq_chat_admission.day_id=excluded.day_id AND
       hud_groq_chat_admission.attempts<? AND
       hud_groq_chat_admission.last_started_at<=?)
    RETURNING attempts`).bind(day,now,limit,now-3000).first();
}

export async function cloudGroqStatus(env,db,now=Date.now()) {
  const admission=groqAdmission(env,now),ready=admission.ready;
  const usage=await db.prepare('SELECT day_id,attempts,last_started_at FROM hud_groq_chat_admission WHERE id=1').bind().first();
  const receipt=await db.prepare('SELECT created_at,model,prompt_tokens,completion_tokens FROM hud_groq_chat_receipts ORDER BY created_at DESC LIMIT 1').bind().first();
  const catalog=await groqCatalogEvidence(db,now);
  return {source:'cloud_direct_groq',model:GROQ_CLOUD_ROUTE,ready,admission,mac_required:false,
    credentials_present:typeof env?.GROQ_HUD_API_KEY==='string'&&env.GROQ_HUD_API_KEY.length>=16,
    catalog,
    observed_at:new Date(now).toISOString(),
    locally_admitted_today:usage?.day_id===Math.floor(now/DAY)?usage.attempts:0,
    last_cloud_completion_at:receipt?.created_at?new Date(receipt.created_at).toISOString():null,
    last_completion_model:receipt?.model||null,
    last_prompt_tokens:receipt?.prompt_tokens??null,
    last_completion_tokens:receipt?.completion_tokens??null,
    remaining_provider_quota:'unknown'};
}

export async function cloudGroqChat(body,env,db,now=Date.now(),fetcher=fetch){
  if(!groqCloudReady(env,now))return error(503,'groq_free_eligibility_unverified_or_expired');
  if(body?.model!==GROQ_CLOUD_ROUTE)return error(400,'model_not_available');
  const messages=validatedMessages(body);
  if(!messages)return error(400,'invalid_chat');
  let admitted;
  try{admitted=await reserve(db,now,Number(env.GROQ_HUD_DAILY_BUDGET));}
  catch{return error(503,'groq_cloud_admission_unavailable');}
  if(!admitted)return error(429,'groq_local_budget_or_spacing_exceeded');
  let upstream;
  try {
    upstream=await fetcher(ENDPOINT,{method:'POST',redirect:'manual',
      headers:{'Authorization':'Bearer '+env.GROQ_HUD_API_KEY,'Content-Type':'application/json','Accept':'application/json'},
      body:JSON.stringify({model:UPSTREAM_MODEL,
        messages:[{role:'system',content:'You are Ask ROVOR. Answer the user. You have no tools, repository write access, background task authority, or employee dispatch capability. Do not claim actions you did not perform.'},...messages],
        stream:false,max_tokens:512,tool_choice:'none'}),
      signal:AbortSignal.timeout(25000)});
  }catch{return error(502,'groq_upstream_unavailable');}
  // Cloudflare Workers does not support redirect:"error". Manual redirect
  // handling rejects 3xx without forwarding provider credentials to a new host.
  if(upstream.status>=300&&upstream.status<400){
    try{await upstream.body?.cancel();}catch{}
    return error(502,'groq_upstream_redirect_denied');
  }
  if(upstream.status===429){await upstream.body?.cancel();return error(429,'groq_provider_rate_limited');}
  if(!upstream.ok){await upstream.body?.cancel();return error(502,'groq_upstream_failed');}
  let doc;
  try{const raw=await upstream.text();if(raw.length>65536)throw Error();doc=JSON.parse(raw);}
  catch{return error(502,'groq_response_invalid');}
  const answer=doc?.choices?.[0]?.message?.content;
  if(doc?.model!==UPSTREAM_MODEL||typeof answer!=='string'||!answer.trim()||
      answer.length>16000||doc.choices[0].finish_reason!=='stop')return error(502,'groq_response_incomplete_or_mismatched');
  const input=doc?.usage?.prompt_tokens,output=doc?.usage?.completion_tokens;
  if(!goodInteger(input)||!goodInteger(output))return error(502,'groq_usage_missing');
  try {
    await db.prepare('INSERT INTO hud_groq_chat_receipts(id,created_at,model,prompt_tokens,completion_tokens) VALUES(?,?,?,?,?)')
      .bind(crypto.randomUUID(),now,UPSTREAM_MODEL,input,output).run();
  }catch{return error(503,'groq_receipt_not_persisted');}
  const sse='data: '+JSON.stringify({choices:[{delta:{content:answer}}]})+'\n\ndata: [DONE]\n\n';
  return new Response(sse,{status:200,headers:{'Content-Type':'text/event-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
}
