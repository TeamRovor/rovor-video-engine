// Native Cloudflare read-only catalog discovery. Never calls a completion,
// asserts Free billing, transfers keys to browsers, or depends on a Mac/Site.
// A returned model ID is NOT admission evidence. All destinations are fixed.
const ENDPOINTS=Object.freeze({
 gemini:'https://generativelanguage.googleapis.com/v1beta/models',
 groq:'https://api.groq.com/openai/v1/models',
 mistral:'https://api.mistral.ai/v1/models',
 nvidia:'https://integrate.api.nvidia.com/v1/models',
 cohere:'https://api.cohere.ai/v1/models',
 sambanova:'https://api.sambanova.ai/v1/models',
 'cloudflare-ai':null,
 openrouter:'https://openrouter.ai/api/v1/models',
 huggingface:'https://router.huggingface.co/v1/models'
});
const KEYS=Object.freeze({
 gemini:'GEMINI_API_KEY',groq:'GROQ_HUD_API_KEY',
 mistral:'MISTRAL_API_KEY',nvidia:'NVIDIA_API_KEY',
 cohere:'COHERE_API_KEY',sambanova:'SAMBANOVA_API_KEY',
 'cloudflare-ai':'CLOUDFLARE_AI_API_KEY',
 openrouter:'OPENROUTER_API_KEY',huggingface:'HUGGINGFACE_API_KEY'
});
const MODEL=/^[a-zA-Z0-9@][a-zA-Z0-9_./:@+-]{0,199}$/;
const MAX_RESPONSE=4194304;
const goodKey=value=>typeof value==='string'&&value.length>=16&&
  value.length<=512&&!/[\s\x00-\x1f\x7f]/.test(value);
async function readJSON(response){
 if(!response.body)throw Error('invalid_catalog_body');
 const chunks=[];let total=0,reader=response.body.getReader();
 try{
  for(;;){
   const {done,value}=await reader.read();
   if(done)break;
   total+=value.byteLength;
   if(total>MAX_RESPONSE)throw Error('oversized_catalog_body');
   chunks.push(value);
  }
 }finally{await reader.cancel().catch(()=>{});}
 const out=new Uint8Array(total);let index=0;
 for(const part of chunks){out.set(part,index);index+=part.byteLength;}
 return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(out));
}
const result=(status,models=[],error_category=null)=>({
 source:'direct_provider',status,models,siteD1:false,error_category
});
export async function directProviderCatalog(env,provider,send=fetch){
 if(!Object.hasOwn(ENDPOINTS,provider))return result('unavailable',[],'unknown_provider');
 const key=env?.[KEYS[provider]];
 if(!goodKey(key)||key===env.HUD_READER_TOKEN||key===env.HUD_WRITER_TOKEN)
  return result('unconfigured',[],'no_provider_key');
 let url=ENDPOINTS[provider];
 if(provider==='cloudflare-ai'){
  const account=env?.CLOUDFLARE_ACCOUNT_ID;
  if(typeof account!=='string'||!/^[a-f0-9]{32}$/i.test(account))
   return result('unconfigured',[],'missing_account');
  url='https://api.cloudflare.com/client/v4/accounts/'+account+'/ai/models/search';
 }
 // OpenRouter's model catalog is public unless an organization opts into
 // key-scoped filtering. A 200 from /models alone cannot authenticate the
 // configured key. Verify the real API key through its documented read-only
 // endpoint first; this never grants free-tier billing or inference admission.
 if(provider==='openrouter'){
  let probe;
  try{
   probe=await send('https://openrouter.ai/api/v1/key',{
    method:'GET',redirect:'manual',
    headers:{Authorization:'Bearer '+key,Accept:'application/json'},
    signal:AbortSignal.timeout(12000)});
  }catch{return result('unavailable',[],'transport_unavailable');}
  if(probe.status===401||probe.status===403){
   await probe.body?.cancel().catch(()=>{});
   return result('unavailable',[],'provider_auth_denied');
  }
  if(probe.status===429){
   await probe.body?.cancel().catch(()=>{});
   return result('unavailable',[],'provider_rate_limited');
  }
  if(!probe.ok){
   await probe.body?.cancel().catch(()=>{});
   return result('unavailable',[],'provider_http_unavailable');
  }
  let keyInfo;
  try{keyInfo=await readJSON(probe);}
  catch{return result('invalid',[],'invalid_catalog_body');}
  if(!keyInfo?.data||typeof keyInfo.data!=='object'||
    Array.isArray(keyInfo.data))
   return result('invalid',[],'invalid_catalog_shape');
 }
 let response;
 try{
  const headers=provider==='gemini'
   ?{'x-goog-api-key':key,Accept:'application/json'}
   :{Authorization:'Bearer '+key,Accept:'application/json'};
  response=await send(url,{method:'GET',redirect:'manual',headers,
   signal:AbortSignal.timeout(12000)});
 }catch{return result('unavailable',[],'transport_unavailable');}
 if(response.status===401||response.status===403){
  if(response.body)await response.body.cancel().catch(()=>{});
  return result('unavailable',[],'provider_auth_denied');
 }
 if(response.status===429){
  if(response.body)await response.body.cancel().catch(()=>{});
  return result('unavailable',[],'provider_rate_limited');
 }
 if(!response.ok){
  if(response.body)await response.body.cancel().catch(()=>{});
  return result('unavailable',[],'provider_http_unavailable');
 }
 let rows;
 try{
  const document=await readJSON(response);
  rows=provider==='cloudflare-ai'?document?.result:
   provider==='gemini'?document?.models:
   (document?.data||document?.models||document?.result);
 }catch{return result('invalid',[],'invalid_catalog_body');}
 if(!Array.isArray(rows))return result('invalid',[],'invalid_catalog_shape');
 const models=[],seen=new Set();
 for(const entry of rows){
  if(!entry||typeof entry!=='object'||Array.isArray(entry))continue;
  const raw=provider==='cloudflare-ai'?entry.name:(entry.id||entry.name);
  if(typeof raw!=='string')continue;
  const model=provider==='gemini'&&raw.startsWith('models/')?raw.slice(7):raw;
  if(!MODEL.test(model))continue;
  if(provider==='cloudflare-ai'&&!model.startsWith('@cf/'))continue;
  // OpenRouter's public price tags constrain the visible names only. They
  // do NOT attest an account's $0 terms or grant inference authorization.
  if(provider==='openrouter'&&(!model.endsWith(':free')||
    entry.pricing?.prompt==null||entry.pricing?.completion==null||
    !Number.isFinite(Number(entry.pricing.prompt))||
    !Number.isFinite(Number(entry.pricing.completion))||
    Number(entry.pricing.prompt)!==0||Number(entry.pricing.completion)!==0))
   continue;
  if(seen.has(model))continue;
  seen.add(model);models.push(model);
  if(models.length===20)break;
 }
 return result('catalog_received',models);
}
