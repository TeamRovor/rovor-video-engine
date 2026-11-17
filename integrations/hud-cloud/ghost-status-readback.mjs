// Read-only bridge for the *existing* owner-private Site workforce ledger.
// No provider calls, dispatch, credential forwarding to browsers, or new clock.
// The owner-private destination is a protected deployment binding, never a public repo literal.
// Validate before using the independent service credential; do not follow redirects.
export function privateServiceUrl(value) {
  if(typeof value!=='string'||value.length>300||!/^https:\/\//.test(value))return null;
  try {
    const url=new URL(value);
    if(url.protocol!=='https:'||url.port||url.username||url.password||
       url.search||url.hash||url.pathname!=='/api/ghost/service'||
       !/^[a-z0-9-]+\.[a-z0-9-]+\.chatgpt\.site$/.test(url.hostname)||
       url.href!==value)return null;
    return value;
  } catch {return null;}
}
const PROVIDERS = Object.freeze([
  'groq','gemini','cloudflare-ai','mistral','nvidia',
  'openrouter','sambanova','cohere','huggingface'
]);
const MAX_BODY_BYTES = 96 * 1024;
const error = (reason, status=502) => ({status,body:{error:reason}});
const string = (value,max=140) => typeof value==='string' ? value.slice(0,max) : null;
const nonnegative = value => Number.isSafeInteger(value) && value>=0 ? value : null;
const timestamp = value => Number.isSafeInteger(value) && value>0 ? value : null;

async function boundedJson(response) {
  const length=Number(response.headers.get('content-length')||0);
  if(Number.isFinite(length) && length>MAX_BODY_BYTES) throw Error('oversized');
  const reader=response.body?.getReader();
  if(!reader) throw Error('missing_body');
  const parts=[];let size=0;
  try {
    for(;;) {
      const {done,value}=await reader.read();
      if(done)break;
      size+=value.length;
      if(size>MAX_BODY_BYTES)throw Error('oversized');
      parts.push(value);
    }
  } finally { try{await reader.cancel();}catch{} }
  const bytes=new Uint8Array(size);let offset=0;
  for(const part of parts){bytes.set(part,offset);offset+=part.length;}
  return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
}

function providerView(p, now) {
  // The provider-readiness HUD needs the Site's authenticated catalog receipt
  // and the *separate* recent-inference proof, not a guessed "online" state.
  // Only forward exact public evidence fields; never relay a raw D1 row.
  const catalog=p.catalog_connection;
  const catalogState=['authenticated','failed','stale','unknown'].includes(catalog?.state)
    ? catalog.state : 'unknown';
  const catalogAt=timestamp(catalog?.observed_at);
  const quota=p.quota;
  const validQuota=quota?.status==='verified' &&
    timestamp(quota.observed_at)!==null &&
    quota.observed_at<=now+120000 && now-quota.observed_at<=900000 &&
    nonnegative(quota.used)!==null &&
    Number.isSafeInteger(quota.limit) && quota.limit>0 && quota.used<=quota.limit &&
    // An internally inconsistent allowance must never be shown as verified.
    (quota.remaining==null || (nonnegative(quota.remaining)!==null &&
      quota.remaining===quota.limit-quota.used)) &&
    (quota.resets_at==null || (timestamp(quota.resets_at)!==null &&
      quota.resets_at>quota.observed_at && quota.resets_at>now));
  return {
    provider:p.provider,
    credentials_configured:p.credentials_configured===true,
    configured_model:string(p.configured_model,200),
    // A fresh catalog response proves key-level catalog access only. It is
    // neither a verified free allowance nor permission to run inference.
    catalog_connection:{state:catalogState,
      observed_at:catalogAt!==null&&catalogAt<=now+60000?catalogAt:null},
    admission:string(p.admission,70)||'unverified',
    online_verified:p.online_verified===true,
    // The existing private Site publishes a last_check D1 record, rather than
    // catalog_connection. Preserve only fresh successful catalog evidence so
    // the HUD can distinguish 9/9 catalog responses from 0/9 admitted models.
    last_check:p.last_check?.status==='catalog_received' &&
      timestamp(p.last_check.observed_at)!==null &&
      p.last_check.observed_at<=now+60000 &&
      now-p.last_check.observed_at<=75*60000
      ? {status:'catalog_received',observed_at:p.last_check.observed_at} : null,
    // Forward a private verified flag only; never infer it from a configured key
    // or historical attempt. HUD additionally requires a fresh model receipt.
    recent_inference_verified:p.recent_inference_verified===true,
    last_inference_at:timestamp(p.last_inference_at),
    setup_blocker:string(p.setup_blocker,80),
    dispatch_gate:p.dispatch_gate && typeof p.dispatch_gate==='object'
      ? {reason:string(p.dispatch_gate.reason,100)} : null,
    // Unknown account allowance stays unknown; do not substitute local caps.
    quota:validQuota ? {
      status:'verified', observed_at:quota.observed_at,
      used:quota.used,limit:quota.limit,
      unit:string(quota.unit,25),resets_at:timestamp(quota.resets_at),
      source:string(quota.source,80),scope:string(quota.scope,80)
    } : null,
    recorded_24h:p.recorded_24h &&
      nonnegative(p.recorded_24h.requests)!==null
      ? {requests:p.recorded_24h.requests} : null
  };
}

function attemptView(a) {
  if(!a||typeof a!=='object'||!PROVIDERS.includes(a.provider)||
     !timestamp(a.started_at)||!string(a.id,120))return null;
  return {
    id:string(a.id,120),job_id:string(a.job_id,160),provider:a.provider,
    requested_model:string(a.requested_model,200),
    actual_model:string(a.actual_model,200),
    started_at:a.started_at,finished_at:timestamp(a.finished_at),
    status:string(a.status,40)||'unverified',
    error_code:string(a.error_code,80),
    tokens_input:nonnegative(a.tokens_input),
    tokens_output:nonnegative(a.tokens_output),
    human_review:string(a.human_review,40),
    employee:string(a.employee,70),task_id:string(a.task_id,160),
    title:string(a.title,180)
  };
}

export async function readGhostStatus(env, fetcher=fetch, now=Date.now()) {
  const token=env?.GHOST_SITE_SERVICE_TOKEN;
  const serviceUrl=privateServiceUrl(env?.GHOST_SITE_SERVICE_URL);
  if(!serviceUrl||typeof token!=='string'||token.length<32 ||
     token===env?.HUD_READER_TOKEN||token===env?.HUD_WRITER_TOKEN)
    return error('cloud_readback_not_configured',503);
  try {
    const remote=await fetcher(serviceUrl,{
      method:'POST',
      headers:{'Authorization':'Bearer '+token,'Content-Type':'application/json'},
      body:JSON.stringify({operation:'status'}),
      redirect:'error',
      signal:AbortSignal.timeout(7000)
    });
    if(!remote.ok)return error('cloud_readback_unavailable');
    const data=await boundedJson(remote);
    if(data?.execution_source!=='cloud_provider' ||
       !timestamp(data.observed_at) ||
       Math.abs(now-data.observed_at)>120000 ||
       !Array.isArray(data.providers) || data.providers.length!==PROVIDERS.length ||
       !Array.isArray(data.attempts) || data.attempts.length>100)
      return error('cloud_readback_invalid');
    const seen=new Set();
    for(const p of data.providers) {
      if(!p||!PROVIDERS.includes(p.provider)||seen.has(p.provider))
        return error('cloud_readback_invalid');
      seen.add(p.provider);
    }
    // Construct an allowlisted DTO. Never blindly forward private Site data:
    // extra response fields may contain prompts, secrets or internal metadata.
    return {status:200,body:{
      schema_version:1,
      execution_source:'cloud_provider',
      observed_at:data.observed_at,
      enabled:data.enabled===true,
      providers:data.providers.map(p=>providerView(p,now)),
      attempts:data.attempts.map(attemptView).filter(Boolean).slice(0,50),
      queue_pending:nonnegative(data.queue_pending),
      native_clock_verified:data.native_clock_verified===true
    }};
  } catch {return error('cloud_readback_unavailable');}
}
