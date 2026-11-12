import {directProviderCatalog} from './direct-provider-catalog.mjs';
// Read-only, Mac-independent bridge from the EXISTING owner-private Site.
// Never sends prompts, calls chat completions, changes STOP, or grants free-tier
// eligibility. Site D1 and Cloudflare D1 are DISTINCT trust boundaries.
export const CATALOG_PROVIDERS=Object.freeze([
 'gemini','groq','mistral','nvidia','cohere','sambanova',
 'cloudflare-ai','openrouter','huggingface'
]);
const ORIGIN='https://rovor-private-hud.mm98z652cq.chatgpt.site';
const SERVICE=ORIGIN+'/api/ghost/service';
const INTERVAL=300000;
const FRESH=3600000;
const MAX_BODY=110000;
const safeModel=s=>typeof s==='string'&&/^[a-zA-Z0-9@][a-zA-Z0-9_./:@+-]{0,199}$/.test(s);
const validTime=n=>Number.isSafeInteger(n)&&n>0;
const secret=env=>{
 const v=env?.GHOST_SITE_SERVICE_TOKEN;
 return typeof v==='string'&&/^[!-~]{32,1024}$/.test(v)&&
   v!==env.HUD_READER_TOKEN&&v!==env.HUD_WRITER_TOKEN?v:null;
};
async function jsonBounded(response){
 if(!response.body)throw Error('invalid_body');
 const reader=response.body.getReader(),chunks=[];let size=0;
 try{
  for(;;){
   const {done,value}=await reader.read();
   if(done)break;
   size+=value.byteLength;
   if(size>MAX_BODY)throw Error('oversized_body');
   chunks.push(value);
  }
 }finally{await reader.cancel().catch(()=>{});}
 const bytes=new Uint8Array(size);let offset=0;
 for(const part of chunks){bytes.set(part,offset);offset+=part.byteLength;}
 return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
}
async function siteCall(token,body,send){
 const response=await send(SERVICE,{method:'POST',redirect:'manual',
  headers:{Authorization:'Bearer '+token,Accept:'application/json',
   'Content-Type':'application/json'},
  body:JSON.stringify(body),signal:AbortSignal.timeout(12000)});
 if(response.status===401||response.status===403)return {error:'site_auth_denied'};
 if(!response.ok){await response.body?.cancel();return {error:'upstream_unavailable'};}
 try{return {value:await jsonBounded(response)};}
 catch{return {error:'invalid_contract'};}
}
async function inspect(env,provider,now,send){
 const key=secret(env);
 if(!key)return {status:'bridge_unconfigured',models:[],siteD1:false};
 try{
  const r=await siteCall(key,{operation:'inventory',provider},send);
  if(r.error)return {status:r.error,models:[],siteD1:false};
  const data=r.value;
  if(data?.provider!==provider||data.status!=='catalog_received'||
     !validTime(data.observed_at)||data.observed_at<now-300000||
     data.observed_at>now+60000||!Array.isArray(data.models)||
     data.models.length>20)
   return {status:'invalid_contract',models:[],siteD1:false};
  const models=[];
  for(const m of data.models){
   if(!safeModel(m?.id))return {status:'invalid_contract',models:[],siteD1:false};
   if(!models.includes(m.id))models.push(m.id);
  }
  // The *inventory* flag alone is not proof that the original Site's D1
  // readback is current. Confirm the exact row through an independent status
  // call. A cached Site check or provider catalog never enables inference.
  if(data.d1_persisted!==true||data.d1_observed_at!==data.observed_at)
   return {status:'site_receipt_missing',models,siteD1:false};
  const checked=await siteCall(key,{operation:'status'},send);
  if(checked.error)return {status:'site_readback_mismatch',models,siteD1:false};
  const state=checked.value;
  const rows=state?.execution_source==='cloud_provider'&&
   Array.isArray(state.providers)?state.providers:[];
  const row=rows.find(x=>x?.provider===provider);
  const valid=row?.last_check?.provider===provider&&
   row.last_check.status==='catalog_received'&&
   row.last_check.observed_at===data.observed_at;
  return {status:valid?'catalog_received':'site_readback_mismatch',
   models,siteD1:valid};
 }catch{return {status:'upstream_unavailable',models:[],siteD1:false};}
}
export async function refreshCatalogBridge(env,now=Date.now(),send=fetch){
 if(!env?.DB||!validTime(now))throw Error('catalog_bridge_unavailable');
 const db=env.DB;
 // Atomic D1 clock rotates at most one provider per native five-minute
 // window. A rolling 300-second lock can skip a clock tick when scheduling
 // jitter makes adjacent invocations less than 300 seconds apart.
 // The D1 row condition remains atomic, so concurrent isolates cannot fan out.
 const windowStart=Math.floor(now/INTERVAL)*INTERVAL;
 const lease=await db.prepare(`INSERT INTO hud_site_catalog_clock(id,next_index,last_started_at)
  VALUES(1,0,?) ON CONFLICT(id) DO UPDATE SET
  next_index=(hud_site_catalog_clock.next_index+1)%9,
  last_started_at=excluded.last_started_at
  WHERE hud_site_catalog_clock.last_started_at<?
  RETURNING next_index`).bind(now,windowStart).first();
 if(!lease)return {state:'interval_not_due',network_calls:0};
 const provider=CATALOG_PROVIDERS[lease.next_index];
 if(!provider)throw Error('catalog_clock_invalid');
 // Prefer the exact provider's own read-only HTTPS catalog when its
 // credential already exists on this Worker. The Site is optional fallback,
 // not a prerequisite for Groq/Gemini or a reason to call completions.
 const direct=await directProviderCatalog(env,provider,send);
 const found=direct.status==='unconfigured'?
  {...await inspect(env,provider,now,send),source:'original_site',error_category:null}:
  {status:direct.status==='catalog_received'?'catalog_received':'upstream_unavailable',
   source:'direct_provider',error_category:direct.error_category||null,
   models:direct.models,siteD1:false};
 const modelsJSON=JSON.stringify({source:found.source,
  error_category:found.error_category,models:found.models});
 const saved=await db.prepare(`INSERT INTO hud_site_catalog_rows
  (provider,checked_at,status,site_d1_verified,models_json)
  VALUES(?,?,?,?,?) ON CONFLICT(provider) DO UPDATE SET
  checked_at=excluded.checked_at,status=excluded.status,
  site_d1_verified=excluded.site_d1_verified,
  models_json=excluded.models_json`)
  .bind(provider,now,found.status,found.siteD1?1:0,modelsJSON).run();
 if(saved.meta?.changes!==1)throw Error('catalog_bridge_write_unconfirmed');
 const row=await db.prepare(`SELECT checked_at,status,site_d1_verified,models_json
  FROM hud_site_catalog_rows WHERE provider=?`).bind(provider).first();
 if(!row||row.checked_at!==now||row.status!==found.status||
  row.site_d1_verified!==(found.siteD1?1:0)||row.models_json!==modelsJSON)
  throw Error('catalog_bridge_readback_unconfirmed');
 return {source:'cloudflare_site_catalog_bridge',provider,
  status:found.status,catalog_source:found.source,
  site_d1_verified:found.siteD1,
  model_count:found.models.length,worker_d1_verified:true,
  inference_online_verified:false};
}
export async function catalogBridgeStatus(env,now=Date.now()){
 if(!env?.DB||!validTime(now))throw Error('catalog_bridge_unavailable');
 const rows=(await env.DB.prepare(`SELECT provider,checked_at,status,
  site_d1_verified,models_json FROM hud_site_catalog_rows`).all()).results||[];
 const known=new Map(rows.map(r=>[r.provider,r]));
 const providers=CATALOG_PROVIDERS.map(provider=>{
  const row=known.get(provider);
  let models=[],catalogSource='original_site',directErrorCategory=null;
  if(row)try{
   const value=JSON.parse(row.models_json);
   const list=Array.isArray(value)?value:value?.models;
   if(Array.isArray(list)&&list.length<=20&&list.every(safeModel))models=list;
   if(!Array.isArray(value)&&value?.source==='direct_provider'){
    catalogSource='direct_provider';
    const allowed=['no_provider_key','transport_unavailable',
     'provider_auth_denied','provider_rate_limited',
     'provider_http_unavailable','invalid_catalog_body',
     'invalid_catalog_shape','missing_account','unknown_provider'];
    directErrorCategory=allowed.includes(value.error_category)?value.error_category:null;
   }
  }catch{}
  const checked=validTime(row?.checked_at)?row.checked_at:null;
  return {provider,status:row?.status||'never_checked',
   catalog_source:catalogSource,direct_error_category:directErrorCategory,
   checked_at:checked===null?null:new Date(checked).toISOString(),
   freshness:checked!==null&&checked<=now&&now-checked<=FRESH?'fresh':'stale_or_unavailable',
   model_count:models.length,models,
   site_d1_verified:row?.site_d1_verified===1,
   // This endpoint is intentionally NOT an inference admission source.
   free_billing_verified:false,quota_verified:false,canary_verified:false,
   inference_online_verified:false};
 });
 return {source:'cloudflare_site_catalog_bridge',mac_required:false,
  provider_count:providers.length,site_d1_verified_count:providers.filter(x=>x.site_d1_verified&&x.freshness==='fresh').length,
  direct_catalog_received_count:providers.filter(x=>x.catalog_source==='direct_provider'&&
   x.freshness==='fresh'&&x.status==='catalog_received').length,
  inference_online_verified_count:0,providers};
}
