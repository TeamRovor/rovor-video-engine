// Read-only project quota observations from Google Cloud Monitoring.
// No inference, IAM mutation, billing change, or exposure of OAuth credentials.
// Google publishes quota/limit gauges and quota/usage delta intervals; a delta
// sample is NOT the account's remaining balance or current window utilization.
const ROOT='https://monitoring.googleapis.com/v3/';
const TYPES=Object.freeze([
 ['requests','generativelanguage.googleapis.com/quota/generate_content_free_tier_requests'],
 ['input_tokens','generativelanguage.googleapis.com/quota/generate_content_free_tier_input_token_count']
]);
const SAFE_MODEL=/^(?:models\/)?[A-Za-z0-9][A-Za-z0-9._:/-]{0,149}$/;
const SAFE_LABEL=/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,149}$/;
const SAFE_PROJECT=/^[a-z][a-z0-9-]{4,61}[a-z0-9]$/;
const MAX_BODY=131072;
const bounded=async(response)=>{
 if(!response.ok)throw Error(response.status===403?'permission_denied':response.status===401?'authentication_failed':'upstream_unavailable');
 const length=Number(response.headers?.get?.('content-length'));
 if(Number.isFinite(length)&&length>MAX_BODY)throw Error('oversized_response');
 const body=await response.text();
 if(body.length>MAX_BODY)throw Error('oversized_response');
 return JSON.parse(body);
};
const encode64=text=>{
 const bytes=new TextEncoder().encode(text);let value='';
 for(const byte of bytes)value+=String.fromCharCode(byte);
 return btoa(value).replace(/\+/g,'-').replace(/\//g,'_').replace(/=/g,'');
};
export async function googleServiceToken(env,fetcher=fetch,now=Date.now()){
 const email=env.GEMINI_MONITOR_SERVICE_ACCOUNT_EMAIL,key=env.GEMINI_MONITOR_SERVICE_ACCOUNT_KEY;
 if(typeof email!=='string'||!email.endsWith('.gserviceaccount.com')||
    typeof key!=='string'||!key.includes('BEGIN PRIVATE KEY'))throw Error('not_configured');
 const pem=key.replace(/-----BEGIN PRIVATE KEY-----|-----END PRIVATE KEY-----|\s+/g,'');
 const bytes=Uint8Array.from(atob(pem),c=>c.charCodeAt(0));
 const privateKey=await crypto.subtle.importKey('pkcs8',bytes,{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['sign']);
 const issued=Math.floor(now/1000);
 const header=encode64(JSON.stringify({alg:'RS256',typ:'JWT'}));
 const claims=encode64(JSON.stringify({iss:email,scope:'https://www.googleapis.com/auth/monitoring.read',
  aud:'https://oauth2.googleapis.com/token',iat:issued,exp:issued+1800}));
 const signing=header+'.'+claims;
 const sig=new Uint8Array(await crypto.subtle.sign('RSASSA-PKCS1-v1_5',privateKey,new TextEncoder().encode(signing)));
 let binary='';for(const n of sig)binary+=String.fromCharCode(n);
 const assertion=signing+'.'+btoa(binary).replace(/\+/g,'-').replace(/\//g,'_').replace(/=/g,'');
 const response=await fetcher('https://oauth2.googleapis.com/token',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
  body:new URLSearchParams({grant_type:'urn:ietf:params:oauth:grant-type:jwt-bearer',assertion}).toString(),
  redirect:'error',signal:AbortSignal.timeout(8000)});
 const value=await bounded(response);
 if(typeof value.access_token!=='string'||value.access_token.length<20||value.token_type!=='Bearer')throw Error('authentication_failed');
 return value.access_token;
}
function sample(series,now,kind){
 if(!Array.isArray(series?.points)||!SAFE_MODEL.test(series?.metric?.labels?.model||'')||
    !SAFE_LABEL.test(series?.metric?.labels?.limit_name||''))return null;
 const model=series.metric.labels.model.replace(/^models\//,'');
 const name=series.metric.labels.limit_name;
 const resource=series.resource?.labels?.location||'global';
 if(!SAFE_LABEL.test(resource))return null;
 const points=series.points.map(point=>{
  const started=Date.parse(point?.interval?.startTime),ended=Date.parse(point?.interval?.endTime);
  const raw=point?.value?.int64Value;
  const value=typeof raw==='string'&&/^(0|[1-9][0-9]{0,12})$/.test(raw)?Number(raw):null;
  return {started,ended,value};
 }).filter(p=>Number.isFinite(p.ended)&&p.ended<=now+10000&&now-p.ended<=300000&&
   Number.isSafeInteger(p.value)&&p.value>=0&&(!kind||Number.isFinite(p.started)&&
     p.started<p.ended&&p.ended-p.started<=3600000));
 if(!points.length)return null;
 points.sort((a,b)=>b.ended-a.ended);
 return {model,limit_name:name,location:resource,...points[0]};
}
export function reduceGoogleMonitoringMetrics(documents,now=Date.now()){
 if(!Array.isArray(documents)||documents.length!==4)throw Error('invalid_metric_response');
 const evidence=[];
 for(let n=0;n<4;n+=2){
  const unit=TYPES[n/2][0], limits=documents[n]?.timeSeries,usage=documents[n+1]?.timeSeries;
  if(!Array.isArray(limits)||!Array.isArray(usage)||limits.length>200||usage.length>200)throw Error('invalid_metric_response');
  const indices=new Map();
  for(const entry of limits){
   const v=sample(entry,now,false);if(!v||v.value<1)continue;
   const k=JSON.stringify([v.model,v.limit_name,v.location]);
   if(indices.has(k)){indices.set(k,null);continue;}
   indices.set(k,v);
  }
  const byUsage=new Map();
  for(const entry of usage){
   const v=sample(entry,now,true);if(!v)continue;
   const k=JSON.stringify([v.model,v.limit_name,v.location]);
   if(byUsage.has(k)){byUsage.set(k,null);continue;}
   byUsage.set(k,v);
  }
  for(const [k,limit] of indices){
   const used=byUsage.get(k);
   if(!limit||!used||used.value>limit.value||evidence.length>=40)continue;
   evidence.push({model:used.model,limit_name:used.limit_name,location:used.location,unit,
    limit:limit.value,sampled_usage:used.value,
    sample_started_at:used.started,sample_ended_at:used.ended,limit_observed_at:limit.ended,
    source:'google_cloud_monitoring_free_tier_project_metrics',
    scope:'google_project_sample',reset_at:null});
  }
 }
 return evidence;
}
export async function readGoogleGeminiQuota(env,{fetcher=fetch,tokenProvider=googleServiceToken,now=Date.now()}={}){
 const project=env.GEMINI_MONITOR_PROJECT;
 if(typeof project!=='string'||!SAFE_PROJECT.test(project)||
    typeof env.GEMINI_MONITOR_SERVICE_ACCOUNT_EMAIL!=='string'||
    typeof env.GEMINI_MONITOR_SERVICE_ACCOUNT_KEY!=='string')
  return {source:'google_cloud_monitoring',status:'not_configured',models:[]};
 try{
  const token=await tokenProvider(env,fetcher,now);
  if(typeof token!=='string'||token.length<20)throw Error('authentication_failed');
  const docs=[];
  for(const [,name] of TYPES){
   for(const suffix of ['/limit','/usage']){
    const qs=new URLSearchParams({filter:'metric.type = "'+name+suffix+'"',
      'interval.startTime':new Date(now-360000).toISOString(),
      'interval.endTime':new Date(now).toISOString(),view:'FULL',pageSize:'200'});
    const response=await fetcher(ROOT+'projects/'+encodeURIComponent(project)+'/timeSeries?'+qs,
      {method:'GET',headers:{Authorization:'Bearer '+token,Accept:'application/json'},
       redirect:'error',signal:AbortSignal.timeout(8000)});
    docs.push(await bounded(response));
    if(docs.at(-1).nextPageToken)throw Error('metric_page_incomplete');
   }
  }
  const models=reduceGoogleMonitoringMetrics(docs,now);
  return {source:'google_cloud_monitoring',status:models.length?'sampled_project_quota':'no_paired_current_samples',
   project,observed_at:now,models};
 }catch(error){
  const reason=['permission_denied','authentication_failed','not_configured','oversized_response',
   'metric_page_incomplete','invalid_metric_response'].includes(error?.message)?error.message:'unavailable';
  return {source:'google_cloud_monitoring',status:reason,models:[]};
 }
}
