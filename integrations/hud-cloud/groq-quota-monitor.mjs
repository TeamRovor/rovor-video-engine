// Read-only Groq account-key diagnostics. GET /models is NOT inference and
// does NOT prove the billing tier or future zero-cost eligibility.
const CATALOG='https://api.groq.com/openai/v1/models';
const MODEL='openai/gpt-oss-20b';
const PROBE_INTERVAL_MS=60000;
const MAX_QUOTA_AGE_MS=120000;

const whole=v=>typeof v==='string'&&/^(0|[1-9][0-9]{0,11})$/.test(v)&&Number.isSafeInteger(Number(v))?Number(v):null;
function resetAt(raw,now){
  if(typeof raw!=='string'||raw.length>40)return null;
  const match=/^(?:(\d+(?:\.\d+)?)h)?(?:(\d+(?:\.\d+)?)m)?(?:(\d+(?:\.\d+)?)s)?$/.exec(raw);
  if(!match||!match.slice(1).some(Boolean))return null;
  const n=(Number(match[1]||0)*3600+Number(match[2]||0)*60+Number(match[3]||0))*1000;
  return Number.isFinite(n)&&n>=0&&n<=2*86400000?new Date(now+Math.ceil(n)).toISOString():null;
}
// Groq's documented headers are RPD for requests and TPM for tokens.
// Do not infer RPM, TPD, billing tier or money from these headers.
export function groqRateHeaders(headers,now){
  const metric=(label,unit,window)=>{
    const limit=whole(headers.get('x-ratelimit-limit-'+label));
    const remaining=whole(headers.get('x-ratelimit-remaining-'+label));
    if(limit===null||remaining===null||limit===0||remaining>limit)return null;
    return {unit,window,limit,remaining,used:limit-remaining,
      reset_at:resetAt(headers.get('x-ratelimit-reset-'+label),now)};
  };
  return {requests_per_day:metric('requests','requests','day'),
    tokens_per_minute:metric('tokens','tokens','minute')};
}

async function stored(db) {
  return db.prepare('SELECT checked_at,observed_at,status,model_present,rpd_limit,rpd_remaining,rpd_reset_at,tpm_limit,tpm_remaining,tpm_reset_at FROM hud_groq_quota_probe WHERE id=1').bind().first();
}
export async function groqCatalogEvidence(db,now=Date.now()){
  const row=await stored(db);
  if(!row)return {source:'groq_api_models_catalog',state:'not_checked',observed_at:null,model_present:null,
    requests_per_day:null,tokens_per_minute:null,scope:'Groq API response headers; billing unknown'};
  const age=now-(row.observed_at??0);
  const fresh=row.status==='catalog_received'&&age>=0&&age<=MAX_QUOTA_AGE_MS;
  const metric=(prefix,unit,window)=>{
    const limit=row[prefix+'_limit'],remaining=row[prefix+'_remaining'],reset=row[prefix+'_reset_at'];
    return fresh&&Number.isSafeInteger(limit)&&limit>0&&Number.isSafeInteger(remaining)&&remaining>=0&&remaining<=limit?
      {unit,window,limit,remaining,used:limit-remaining,reset_at:typeof reset==='string'?reset:null}:null;
  };
  return {source:'groq_api_models_catalog',state:row.status==='catalog_received'&&!fresh?'stale':row.status,
    observed_at:row.observed_at?new Date(row.observed_at).toISOString():null,
    model_present:fresh?row.model_present===1:null,
    requests_per_day:metric('rpd','requests','day'),
    tokens_per_minute:metric('tpm','tokens','minute'),
    scope:'Groq API response headers; billing unknown'};
}

export async function probeGroqCatalogue(env,db,now=Date.now(),fetcher=fetch){
  // No key, no external call. Key material never leaves this private Worker
  // except in the fixed HTTPS Authorization header to api.groq.com.
  if(typeof env?.GROQ_HUD_API_KEY!=='string'||env.GROQ_HUD_API_KEY.length<16)return;
  // D1 lease prevents polling storms across Worker isolates and devices.
  const claimed=await db.prepare(`INSERT INTO hud_groq_quota_probe (id,checked_at,status)
    VALUES (1,?,'checking') ON CONFLICT(id) DO UPDATE SET
    checked_at=excluded.checked_at,status='checking'
    WHERE hud_groq_quota_probe.checked_at<=? RETURNING id`)
    .bind(now,now-PROBE_INTERVAL_MS).first();
  if(!claimed)return;
  let state='unavailable',model=null,limits={requests_per_day:null,tokens_per_minute:null};
  try{
    const upstream=await fetcher(CATALOG,{method:'GET',redirect:'error',
      headers:{Authorization:'Bearer '+env.GROQ_HUD_API_KEY,Accept:'application/json'},
      signal:AbortSignal.timeout(7000)});
    if(upstream.status===401||upstream.status===403)state='auth_rejected';
    else if(upstream.status===429)state='rate_limited';
    else if(!upstream.ok)state='upstream_error';
    else{
      const raw=await upstream.text();
      if(raw.length<=192000){
        const parsed=JSON.parse(raw);
        if(Array.isArray(parsed?.data)&&parsed.data.length<=300&&
           parsed.data.every(x=>x&&typeof x.id==='string'&&x.id.length<=200)){
          state='catalog_received';model=parsed.data.some(x=>x.id===MODEL);
          limits=groqRateHeaders(upstream.headers,now);
        }else state='invalid_catalog';
      }else state='invalid_catalog';
    }
    if(state!=='catalog_received')await upstream.body?.cancel();
  }catch{state='unavailable';}
  const rpd=limits.requests_per_day,tpm=limits.tokens_per_minute;
  // Stale/slower responses can never override a newer lease's result.
  await db.prepare(`UPDATE hud_groq_quota_probe SET status=?,observed_at=?,model_present=?,
    rpd_limit=?,rpd_remaining=?,rpd_reset_at=?,
    tpm_limit=?,tpm_remaining=?,tpm_reset_at=?
    WHERE id=1 AND checked_at=?`).bind(state,now,model===null?null:model?1:0,
      rpd?.limit??null,rpd?.remaining??null,rpd?.reset_at??null,
      tpm?.limit??null,tpm?.remaining??null,tpm?.reset_at??null,now).run();
}
