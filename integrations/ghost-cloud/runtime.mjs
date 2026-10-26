// Runtime secrets and eligibility evidence are trusted operator configuration, never job input.
export const PROVIDERS = Object.freeze({
 groq: ['https://api.groq.com/openai/v1/chat/completions', 'GROQ_API_KEY'],
 gemini: ['https://generativelanguage.googleapis.com/v1beta/openai/chat/completions', 'GEMINI_API_KEY'],
 'cloudflare-ai': [null, 'CLOUDFLARE_AI_API_KEY'],
 mistral: ['https://api.mistral.ai/v1/chat/completions', 'MISTRAL_API_KEY'],
 nvidia: ['https://integrate.api.nvidia.com/v1/chat/completions', 'NVIDIA_API_KEY'],
 openrouter: ['https://openrouter.ai/api/v1/chat/completions', 'OPENROUTER_API_KEY'],
 sambanova: ['https://api.sambanova.ai/v1/chat/completions', 'SAMBANOVA_API_KEY'],
 cohere: ['https://api.cohere.ai/compatibility/v1/chat/completions', 'COHERE_API_KEY'],
 huggingface: ['https://router.huggingface.co/v1/chat/completions', 'HUGGINGFACE_API_KEY'],
});
const ROLES = new Set(['Walter','Mike','Jane','Jesse','Gale','Gus','Saul','Hank']);
const KINDS = new Set(['checklist','plan','code_review','research']);
const DAY = 86400000;
const validId = s => typeof s === 'string' && /^[a-z0-9][a-z0-9-]{0,149}$/.test(s);
const bytes = s => new TextEncoder().encode(s).byteLength;
const positive = (n, max) => Number.isSafeInteger(n) && n > 0 && n <= max;
const run = (db, sql, ...args) => db.prepare(sql).bind(...args);

export function validateJob(j) {
 if (!j || Object.keys(j).some(k => !['id','employee','task_id','kind','title','prompt','source_commit','data_class'].includes(k)) ||
     !validId(j.id) || !validId(j.task_id) || !ROLES.has(j.employee) || !KINDS.has(j.kind) ||
     j.data_class !== 'public_repository' || !/^[a-f0-9]{40}$/.test(j.source_commit || '') ||
     typeof j.title !== 'string' || !j.title.trim() || j.title.length > 160 || /[\x00-\x1f]/.test(j.title) ||
     typeof j.prompt !== 'string' || !j.prompt.trim() || bytes(j.prompt) > 14500) throw Error('invalid_job');
 return j;
}

export function eligibility(provider, cfg, env, now) {
 if (!Object.hasOwn(PROVIDERS, provider)) return 'unknown_provider';
 if (!cfg || cfg.enabled !== true) return 'not_configured';
 if (typeof env[PROVIDERS[provider][1]] !== 'string' || env[PROVIDERS[provider][1]].length < 16) return 'missing_secret';
 if (typeof cfg.model !== 'string' || !/^[a-zA-Z0-9@][a-zA-Z0-9_./:@-]{0,199}$/.test(cfg.model) || /(^|[/:-])(auto|latest)([/:-]|$)/i.test(cfg.model)) return 'unpinned_model';
 if (cfg.zero_cost !== true || cfg.commercial_use !== true || !/^[a-f0-9]{64}$/.test(cfg.evidence_sha256 || '')) return 'eligibility_unverified';
 if (!Number.isSafeInteger(cfg.verified_at) || cfg.verified_at > now || now - cfg.verified_at > DAY ||
     !Number.isSafeInteger(cfg.valid_until) || cfg.valid_until <= now || cfg.valid_until > cfg.verified_at + DAY) return 'eligibility_expired';
 if (!Number.isSafeInteger(cfg.canary_at) || cfg.canary_at < cfg.verified_at || cfg.canary_at > now || !/^[a-f0-9]{64}$/.test(cfg.canary_sha256 || '')) return 'canary_unverified';
 if (!validId(cfg.pool) || !positive(cfg.requests_per_day,144) || !positive(cfg.tokens_per_day,10000000) ||
     !positive(cfg.min_interval_ms,DAY) || !positive(cfg.max_input_bytes,14500) || !positive(cfg.max_output_tokens,2400) ||
     !Array.isArray(cfg.roles) || !cfg.roles.length || cfg.roles.some(r => !ROLES.has(r)) ||
     !Array.isArray(cfg.kinds) || !cfg.kinds.length || cfg.kinds.some(k => !KINDS.has(k))) return 'invalid_limits';
 if (provider === 'cloudflare-ai' && !/^[a-f0-9]{32}$/.test(env.CLOUDFLARE_ACCOUNT_ID || '')) return 'missing_account';
 if (provider === 'openrouter' && !cfg.model.endsWith(':free')) return 'paid_route_denied';
 // Pin an HF upstream too: its default router can silently change provider.
 if (provider === 'huggingface' && !/:[a-z0-9-]+$/.test(cfg.model)) return 'unpinned_upstream';
 return null;
}

export function requestFor(provider, cfg, env, prompt) {
 const [url,key] = PROVIDERS[provider];
 const endpoint = url || `https://api.cloudflare.com/client/v4/accounts/${env.CLOUDFLARE_ACCOUNT_ID}/ai/v1/chat/completions`;
 const body = {model:cfg.model, messages:[{role:'user',content:prompt}], max_tokens:cfg.max_output_tokens, stream:false};
 if (provider === 'openrouter') body.provider = {allow_fallbacks:false, require_parameters:true, max_price:{prompt:0,completion:0}};
 return [endpoint,{method:'POST',redirect:'manual',headers:{Authorization:`Bearer ${env[key]}`,'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(45000)}];
}

async function boundedJson(response) {
 if (!response.body) throw Error('invalid_response');
 const reader=response.body.getReader(), chunks=[]; let total=0;
 try { for (;;) {const {done,value}=await reader.read();if(done)break;total+=value.byteLength;if(total>131072)throw Error('oversized_response');chunks.push(value);} }
 finally {await reader.cancel().catch(()=>{});}
 const all=new Uint8Array(total);let offset=0;for(const chunk of chunks){all.set(chunk,offset);offset+=chunk.length;}
 return JSON.parse(new TextDecoder().decode(all));
}

export async function infer(provider,cfg,env,prompt,fetcher=(...args)=>globalThis.fetch(...args),now=Date.now()) {
 const denied=eligibility(provider,cfg,env,now);if(denied)throw Error(denied);
 if(bytes(prompt)>cfg.max_input_bytes)throw Error('input_too_large');
 try {
  const response=await fetcher(...requestFor(provider,cfg,env,prompt));
  if(!response.ok){
   const raw=response.headers.get('Retry-After'); const n=Number(raw);
   const delay=raw && Number.isFinite(n) && n>=0 ? n*1000 : Date.parse(raw || '')-now;
   await response.body?.cancel();
   return {status:'failed',error_code:response.status===429?'rate_limited':response.status===401||response.status===403?'auth_rejected':'upstream_http',retry_after:response.status===429?now+Math.max(60000,Number.isFinite(delay)?Math.min(delay,DAY):60000):null};
  }
  const data=await boundedJson(response), choice=data.choices?.[0], text=choice?.message?.content;
  const usage=data.usage || {}, count=n=>Number.isSafeInteger(n)&&n>=0?n:null;
  const info={actual_model:typeof data.model==='string'&&data.model.length<=200?data.model:null,tokens_input:count(usage.prompt_tokens),tokens_output:count(usage.completion_tokens)};
  if(typeof text!=='string'||!text.trim()||bytes(text)>32768||choice.finish_reason!=='stop')return {...info,status:'failed',error_code:'incomplete_output',retry_after:null};
  return {...info,status:'needs_review',error_code:null,output:text,retry_after:null};
 } catch { return {status:'uncertain',error_code:'transport_or_response_failure',retry_after:null}; }
}

export async function claim(db,provider,cfg,now) {
 // One SQL write is the lock: UNIQUE(job_id) prevents replay; subqueries enforce
 // global, shared-account and provider admission even during overlapping ticks.
 const roles=JSON.stringify(cfg.roles), kinds=JSON.stringify(cfg.kinds), id=crypto.randomUUID();
 return await run(db,`INSERT INTO ghost_cloud_attempts(id,job_id,provider,model,pool,started_at,reserved_tokens,status)
 SELECT ?,j.id,?,?,?,?,j.input_bytes+?+256,'running' FROM ghost_cloud_jobs j
 WHERE (SELECT enabled FROM ghost_cloud_control WHERE id=1)=1
 AND j.employee IN (SELECT value FROM json_each(?)) AND j.kind IN (SELECT value FROM json_each(?)) AND j.input_bytes<=?
 AND NOT EXISTS(SELECT 1 FROM ghost_cloud_attempts WHERE job_id=j.id)
 AND (SELECT count(*) FROM ghost_cloud_attempts WHERE started_at>?)<144
 AND (SELECT count(*) FROM ghost_cloud_attempts WHERE pool=? AND started_at>?)<?
 AND COALESCE((SELECT sum(reserved_tokens) FROM ghost_cloud_attempts WHERE pool=? AND started_at>?),0)+j.input_bytes+?+256<=?
 AND NOT EXISTS(SELECT 1 FROM ghost_cloud_attempts WHERE pool=? AND (status='running' OR started_at>? OR retry_after>?))
 AND (SELECT count(*) FROM ghost_cloud_attempts WHERE pool=? AND status IN ('failed','uncertain')
      AND started_at>COALESCE((SELECT max(started_at) FROM ghost_cloud_attempts WHERE pool=? AND status='needs_review'),0))<3
 ORDER BY j.created_at,j.id LIMIT 1 RETURNING *`,id,provider,cfg.model,cfg.pool,now,cfg.max_output_tokens,roles,kinds,cfg.max_input_bytes,
 now-DAY,cfg.pool,now-DAY,cfg.requests_per_day,cfg.pool,now-DAY,cfg.max_output_tokens,cfg.tokens_per_day,
 cfg.pool,now-cfg.min_interval_ms,now,cfg.pool,cfg.pool).first();
}

// Read only when an otherwise eligible route has no successful atomic claim.
// Reasons derive from the SAME durable constraints as claim(); they never
// license retries, reset a circuit, expose prompts, or relax provider limits.
async function diagnoseNoClaim(db,cfg,now) {
 const candidate=await run(db,`SELECT COUNT(*) n,MIN(j.input_bytes) min_bytes FROM ghost_cloud_jobs j
   WHERE j.employee IN (SELECT value FROM json_each(?))
     AND j.kind IN (SELECT value FROM json_each(?))
     AND j.input_bytes<=?
     AND NOT EXISTS(SELECT 1 FROM ghost_cloud_attempts a WHERE a.job_id=j.id)`,
   JSON.stringify(cfg.roles),JSON.stringify(cfg.kinds),cfg.max_input_bytes).first();
 if(!candidate?.n)return {reason:'no_matching_unattempted_job'};
 const globalCount=await run(db,'SELECT COUNT(*) n FROM ghost_cloud_attempts WHERE started_at>?',now-DAY).first();
 if(globalCount.n>=144)return {reason:'global_daily_safety_cap'};
 const pool=await run(db,`SELECT COUNT(*) n,COALESCE(SUM(reserved_tokens),0) reserved
   FROM ghost_cloud_attempts WHERE pool=? AND started_at>?`,cfg.pool,now-DAY).first();
 if(pool.n>=cfg.requests_per_day)return {reason:'account_request_cap'};
 if(pool.reserved+candidate.min_bytes+cfg.max_output_tokens+256>cfg.tokens_per_day)
   return {reason:'account_reserved_token_cap'};
 const lock=await run(db,`SELECT
   COALESCE(SUM(CASE WHEN status='running' THEN 1 ELSE 0 END),0) running,
   MAX(CASE WHEN started_at>? THEN started_at ELSE NULL END) recent,
   MAX(CASE WHEN retry_after>? THEN retry_after ELSE NULL END) retry_until
   FROM ghost_cloud_attempts WHERE pool=?`,
   now-cfg.min_interval_ms,now,cfg.pool).first();
 if(lock.running>0)return {reason:'account_inflight_claim'};
 if(lock.recent!==null)return {reason:'account_minimum_interval',next_eligible_at:lock.recent+cfg.min_interval_ms};
 if(lock.retry_until!==null)return {reason:'account_retry_after',next_eligible_at:lock.retry_until};
 const circuit=await run(db,`SELECT COUNT(*) n FROM ghost_cloud_attempts
   WHERE pool=? AND status IN ('failed','uncertain')
   AND started_at>COALESCE((SELECT MAX(started_at) FROM ghost_cloud_attempts
     WHERE pool=? AND status='needs_review'),0)`,cfg.pool,cfg.pool).first();
 if(circuit.n>=3)return {reason:'failure_circuit_requires_review'};
 return {reason:'claim_contention_or_unclassified_gate'};
}

// Read-only snapshot of provider admission and atomic claim gates.
// Evaluating a gate does not claim a job or prove live model availability.
export async function diagnosePending(env,now=Date.now()) {
 if(!env?.DB||!Number.isSafeInteger(now)||now<0)throw Error('diagnostics_unavailable');
 let config;
 try{config=JSON.parse(env.GHOST_FLEET_CONFIG||'{}');}
 catch{throw Error('invalid_fleet_config');}
 const control=await run(env.DB,'SELECT enabled FROM ghost_cloud_control WHERE id=1').first();
 const providers=[];
 for(const provider of Object.keys(PROVIDERS)){
  const cfg=config[provider],rejected=eligibility(provider,cfg,env,now);
  if(rejected){providers.push({provider,state:'ineligible',reason:rejected});continue;}
  if(control?.enabled!==1){providers.push({provider,state:'paused',reason:'global_stop'});continue;}
  const result=await diagnoseNoClaim(env.DB,cfg,now);
  const {reason,next_eligible_at}=result;
  // A read-only "open" SQL gate does not prove a claim will succeed under
  // contention or that inference would produce a complete response.
  providers.push({provider,
   state:reason==='claim_contention_or_unclassified_gate'?'claim_conditions_met_unverified':'blocked',
   reason:reason==='claim_contention_or_unclassified_gate'?'claim_conditions_met_unverified':reason,
   ...(Number.isSafeInteger(next_eligible_at)?{next_eligible_at}:{})
  });
 }
 return {source:'read_only_cloud_claim_gates',observed_at:now,providers};
}

export async function tick(env,fetcher=(...args)=>globalThis.fetch(...args),now=Date.now()) {
 const startedClock=Date.now();
 const db=env.DB; if(!db)throw Error('missing_database');
 // An interrupted request is uncertain, never returned to the ready queue.
 await run(db,"UPDATE ghost_cloud_attempts SET status='uncertain',error_code='interrupted_attempt',finished_at=? WHERE status='running' AND started_at<?",now,now-120000).run();
 if(!(await run(db,'SELECT enabled FROM ghost_cloud_control WHERE id=1').first())?.enabled)return {enabled:false,dispatched:0};
 let config;try{config=JSON.parse(env.GHOST_FLEET_CONFIG || '{}');}catch{throw Error('invalid_fleet_config');}
 // Every shared pool must use identical caps: a second connection cannot raise them.
 const pools=new Map(), denied={};
 for(const provider of Object.keys(PROVIDERS)){
  const cfg=config[provider],reason=eligibility(provider,cfg,env,now);if(reason){denied[provider]=reason;continue;}
  const limits=JSON.stringify([cfg.requests_per_day,cfg.tokens_per_day,cfg.min_interval_ms]);
  if(pools.has(cfg.pool)&&pools.get(cfg.pool)!==limits)throw Error('conflicting_pool_limits');pools.set(cfg.pool,limits);
 }
 let dispatched=0;
 const blocked={};
 for(const provider of Object.keys(PROVIDERS)){
  if(denied[provider])continue;const cfg=config[provider];
  // Recheck STOP and evidence clocks immediately before each external call.
  const clock=now+(Date.now()-startedClock);
  if(eligibility(provider,cfg,env,clock))continue;
  const attempt=await claim(db,provider,cfg,clock);
  if(!attempt){blocked[provider]=await diagnoseNoClaim(db,cfg,clock);continue;}
  if(!(await run(db,'SELECT enabled FROM ghost_cloud_control WHERE id=1').first())?.enabled){
   await run(db,"UPDATE ghost_cloud_attempts SET status='failed',error_code='stopped_before_request',finished_at=? WHERE id=? AND status='running'",clock,attempt.id).run();break;
  }
  const job=await run(db,'SELECT prompt FROM ghost_cloud_jobs WHERE id=?',attempt.job_id).first();
  const outcome=await infer(provider,cfg,env,job.prompt,fetcher,clock);dispatched++;
  await run(db,`UPDATE ghost_cloud_attempts SET status=?,error_code=?,actual_model=?,tokens_input=?,tokens_output=?,output=?,retry_after=?,finished_at=? WHERE id=? AND status='running'`,outcome.status,outcome.error_code,outcome.actual_model??null,outcome.tokens_input??null,outcome.tokens_output??null,outcome.output??null,outcome.retry_after??null,now+(Date.now()-startedClock),attempt.id).run();
 }
 return {enabled:true,dispatched,denied,blocked};
}
