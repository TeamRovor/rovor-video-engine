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
 // Atomic D1 clock rotates exactly one of nine fixed providers each five
 // minutes. Overlapping Cloudflare cron isolates cannot fan out 9 calls.
 const lease=await db.prepare(`INSERT INTO hud_site_catalog_clock(id,next_index,last_started_at)
  VALUES(1,0,?) ON CONFLICT(id) DO UPDATE SET
  next_index=(hud_site_catalog_clock.next_index+1)%9,
  last_started_at=excluded.last_started_at
  WHERE hud_site_catalog_clock.last_started_at<=?
  RETURNING next_index`).bind(now,now-INTERVAL).first();
 if(!lease)return {state:'interval_not_due',network_calls:0};
 const provider=CATALOG_PROVIDERS[lease.next_index];
 if(!provider)throw Error('catalog_clock_invalid');
 const found=await inspect(env,provider,now,send);
 const modelsJSON=JSON.stringify(found.models);
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
  status:found.status,site_d1_verified:found.siteD1,
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
  let models=[];
  if(row)try{
   const value=JSON.parse(row.models_json);
   if(Array.isArray(value)&&value.length<=20&&value.every(safeModel))models=value;
  }catch{}
  const checked=validTime(row?.checked_at)?row.checked_at:null;
  return {provider,status:row?.status||'never_checked',
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
  inference_online_verified_count:0,providers};
}
