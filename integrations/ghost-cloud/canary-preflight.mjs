// One-shot operator-only provider canary. Not a public endpoint, scheduler, or dispatch fallback.
// The caller must supply private, independently checked billing/quota evidence and a unique approval.
// A successful probe is NOT human approval or proof of future free-tier availability.
import {PROVIDERS,requestFor} from './runtime.mjs';

const DAY=86400000, WINDOW=900000;
const id=s=>typeof s==='string'&&/^[a-z0-9][a-z0-9-]{0,149}$/.test(s);
const positive=(n,max)=>Number.isSafeInteger(n)&&n>0&&n<=max;
const digest=s=>typeof s==='string'&&/^[a-f0-9]{64}$/.test(s);
const bytes=s=>new TextEncoder().encode(s).length;
const ROLES=new Set(['Walter','Mike','Jane','Jesse','Gale','Gus','Saul','Hank']);
const KINDS=new Set(['checklist','plan','code_review','research']);
const dbq=(db,sql,...args)=>db.prepare(sql).bind(...args);
const count=n=>Number.isSafeInteger(n)&&n>=0?n:null;

export function preflight(provider,cfg,env,approval,now) {
 if(!Object.hasOwn(PROVIDERS,provider))return 'unknown_provider';
 if(!cfg||cfg.enabled!==true||typeof env?.[PROVIDERS[provider][1]]!=='string'||env[PROVIDERS[provider][1]].length<16)return 'not_configured';
 if(typeof cfg.model!=='string'||!/^[a-zA-Z0-9@][a-zA-Z0-9_./:@-]{0,199}$/.test(cfg.model)||/(^|[/:-])(auto|latest)([/:-]|$)/i.test(cfg.model))return 'unpinned_model';
 if(provider==='openrouter'&&!cfg.model.endsWith(':free'))return 'paid_route_denied';
 if(provider==='huggingface'&&!/:[a-z0-9-]+$/.test(cfg.model))return 'unpinned_upstream';
 if(provider==='cloudflare-ai'&&!/^[a-f0-9]{32}$/.test(env.CLOUDFLARE_ACCOUNT_ID||''))return 'missing_account';
 if(cfg.zero_cost!==true||cfg.commercial_use!==true||!digest(cfg.evidence_sha256))return 'eligibility_unverified';
 if(!Number.isSafeInteger(now)||!Number.isSafeInteger(cfg.verified_at)||cfg.verified_at>now||now-cfg.verified_at>DAY||
    !Number.isSafeInteger(cfg.valid_until)||cfg.valid_until<=now||cfg.valid_until>cfg.verified_at+DAY)return 'eligibility_expired';
 if(!id(cfg.pool)||!positive(cfg.requests_per_day,144)||!positive(cfg.tokens_per_day,10000000)||
    !positive(cfg.min_interval_ms,DAY)||!positive(cfg.max_input_bytes,14500)||!positive(cfg.max_output_tokens,2400)||
    !Array.isArray(cfg.roles)||!cfg.roles.length||cfg.roles.some(r=>!ROLES.has(r))||
    !Array.isArray(cfg.kinds)||!cfg.kinds.length||cfg.kinds.some(k=>!KINDS.has(k)))return 'invalid_limits';
 // This private approval is an operator attestation, not proof from the provider.
 if(!approval||approval.execute_once!==true||approval.zero_spend_verified!==true||
    approval.commercial_terms_verified!==true||approval.quota_verified!==true||
    approval.provider!==provider||approval.model!==cfg.model||approval.evidence_sha256!==cfg.evidence_sha256||
    !id(approval.canary_id)||!approval.canary_id.startsWith('canary-'+provider+'-')||
    !id(approval.task_id)||!/^[a-f0-9]{40}$/.test(approval.source_commit||'')||
    !Number.isSafeInteger(approval.approved_at)||approval.approved_at>now||now-approval.approved_at>WINDOW||
    !Number.isSafeInteger(approval.expires_at)||approval.expires_at<=now||
    approval.expires_at>approval.approved_at+WINDOW)return 'operator_approval_missing';
 if(!positive(approval.remaining_requests,10000000)||!positive(approval.remaining_tokens,100000000)||
    cfg.requests_per_day>approval.remaining_requests||cfg.tokens_per_day>approval.remaining_tokens||
    approval.remaining_tokens<Math.min(cfg.max_output_tokens,64)+512)return 'quota_unverified';
 return null;
}

async function boundedResponse(response) {
 if(!response.body)throw Error('invalid_response');
 const reader=response.body.getReader(),parts=[];let total=0;
 try {for(;;){const {done,value}=await reader.read();if(done)break;total+=value.length;
   if(total>32768)throw Error('oversized_response');parts.push(value);}}
 finally{await reader.cancel().catch(()=>{});}
 const all=new Uint8Array(total);let at=0;for(const part of parts){all.set(part,at);at+=part.length;}
 return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(all));
}
async function sha256(text) {
 const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));
 return [...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,'0')).join('');
}

export async function runCanary({provider,cfg,env,approval,fetcher=(...args)=>globalThis.fetch(...args),now=Date.now(),clock=Date.now}) {
 const denied=preflight(provider,cfg,env,approval,now);
 if(denied)return {status:'denied',reason:denied,provider};
 if(!env.DB)return {status:'denied',reason:'missing_database',provider};
 const db=env.DB;
 if((await dbq(db,'SELECT enabled FROM ghost_cloud_control WHERE id=1').first())?.enabled!==1)
   return {status:'denied',reason:'stopped',provider};
 // The probe is a real, public-only model request; a unique ID prevents reuse/replay.
 const marker='ROVOR-CANARY-'+approval.canary_id;
 const prompt='Return exactly '+marker+' and nothing else.';
 if(bytes(prompt)>cfg.max_input_bytes)return {status:'denied',reason:'input_too_large',provider};
 const outputCap=Math.min(cfg.max_output_tokens,64),reservation=bytes(prompt)+outputCap+256;
 if(reservation>approval.remaining_tokens)return {status:'denied',reason:'quota_unverified',provider};
 // A preexisting ID is permanently consumed, even if its earlier write was interrupted.
 const inserted=await dbq(db,`INSERT OR IGNORE INTO ghost_cloud_jobs
   (id,employee,task_id,kind,title,prompt,input_bytes,source_commit,created_at)
   VALUES (?,'Walter',?,'canary','PROVIDER CANARY (not task output)',?,?,?,?)`,
   approval.canary_id,approval.task_id,prompt,bytes(prompt),approval.source_commit,now).run();
 if(inserted.meta.changes!==1)return {status:'denied',reason:'canary_id_used',provider};
 const attemptId=crypto.randomUUID();
 // Same global/shared-pool quota, cooldown and circuit as the production claim.
 // Atomic INSERT prevents concurrent probes from exceeding the shared account budget.
 const attempt=await dbq(db,`INSERT INTO ghost_cloud_attempts
   (id,job_id,provider,model,pool,started_at,reserved_tokens,status)
   SELECT ?,j.id,?,?,?,?,?,'running' FROM ghost_cloud_jobs j
   WHERE j.id=? AND (SELECT enabled FROM ghost_cloud_control WHERE id=1)=1
   AND NOT EXISTS(SELECT 1 FROM ghost_cloud_attempts WHERE job_id=j.id)
   AND (SELECT count(*) FROM ghost_cloud_attempts WHERE started_at>?)<144
   AND (SELECT count(*) FROM ghost_cloud_attempts WHERE pool=? AND started_at>?)<?
   AND COALESCE((SELECT sum(reserved_tokens) FROM ghost_cloud_attempts WHERE pool=? AND started_at>?),0)+?<=?
   AND NOT EXISTS(SELECT 1 FROM ghost_cloud_attempts WHERE pool=? AND
     (status='running' OR started_at>? OR retry_after>?))
   AND (SELECT count(*) FROM ghost_cloud_attempts WHERE pool=? AND status IN ('failed','uncertain')
     AND started_at>COALESCE((SELECT max(started_at) FROM ghost_cloud_attempts
       WHERE pool=? AND status='needs_review'),0))<3
   RETURNING id`,
   attemptId,provider,cfg.model,cfg.pool,now,reservation,approval.canary_id,
   now-DAY,cfg.pool,now-DAY,cfg.requests_per_day,
   cfg.pool,now-DAY,reservation,cfg.tokens_per_day,
   cfg.pool,now-cfg.min_interval_ms,now,cfg.pool,cfg.pool).first();
 if(!attempt)return {status:'denied',reason:'shared_pool_or_stop_admission',provider};
 let status='uncertain',error_code='transport_or_response_failure',actual_model=null;
 let tokens_input=null,tokens_output=null,canary_sha256=null,retry_after=null;
 // STOP is checked again after the atomic reservation and before any HTTPS request.
 if((await dbq(db,'SELECT enabled FROM ghost_cloud_control WHERE id=1').first())?.enabled!==1){
   status='failed';error_code='stopped_before_request';
 }else if(preflight(provider,cfg,env,approval,Math.max(now,clock()))){
   status='failed';error_code='evidence_expired_before_request';
 }else{
   try{
     const requestCfg={...cfg,max_output_tokens:outputCap};
     const response=await fetcher(...requestFor(provider,requestCfg,env,prompt));
     if(!response.ok){
       error_code=response.status===429?'rate_limited':response.status===401||response.status===403?'auth_rejected':'upstream_http';
       // A rate-limited canary cannot authorize more requests; require operator review.
       if(response.status===429)retry_after=Number.MAX_SAFE_INTEGER;
       status='failed';await response.body?.cancel();
     }else{
       const data=await boundedResponse(response),choice=data?.choices?.[0];
       actual_model=typeof data?.model==='string'&&data.model.length<=200?data.model:null;
       tokens_input=count(data?.usage?.prompt_tokens);
       tokens_output=count(data?.usage?.completion_tokens);
       if(actual_model!==cfg.model){status='failed';error_code='model_mismatch';}
       else if(choice?.finish_reason!=='stop'||choice?.message?.content!==marker){
         status='failed';error_code='canary_mismatch';
       }else{
         status='needs_review';error_code=null;
         canary_sha256=await sha256(JSON.stringify({provider,model:cfg.model,canary_id:approval.canary_id,marker,observed_at:now}));
       }
     }
   }catch{status='uncertain';error_code='transport_or_response_failure';}
 }
 await dbq(db,`UPDATE ghost_cloud_attempts SET status=?,error_code=?,actual_model=?,
   tokens_input=?,tokens_output=?,output=NULL,retry_after=?,finished_at=?
   WHERE id=? AND status='running'`,
   status,error_code,actual_model,tokens_input,tokens_output,retry_after,now,attemptId).run();
 return {execution_source:'cloud_provider_canary',provider,requested_model:cfg.model,actual_model,
   status,reason:error_code,observed_at:now,tokens_input,tokens_output,
   canary_sha256:status==='needs_review'?canary_sha256:null,
   canary_at:status==='needs_review'?now:null,job_id:approval.canary_id,
   human_review:'not_recorded'};
}
