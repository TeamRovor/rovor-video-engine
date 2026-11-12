import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {catalogBridgeStatus,refreshCatalogBridge,CATALOG_PROVIDERS}
 from '../integrations/hud-cloud/cloud-provider-catalog-bridge.mjs';
import {handle} from '../integrations/hud-cloud/worker.mjs';
import {verifyCatalogBridge} from '../integrations/hud-cloud/verify-cloud-provider-catalog-bridge.mjs';
import {buildHudSecretPayload} from '../integrations/hud-cloud/private-worker-secret-payload.mjs';
import {directProviderCatalog} from '../integrations/hud-cloud/direct-provider-catalog.mjs';

const R='r'.repeat(40),W='w'.repeat(40),S='s'.repeat(48);
const T=Date.parse('2026-11-11T20:00:00.000Z');
const SITE='https://rovor-private-hud.mm98z652cq.chatgpt.site/api/ghost/service';
function setup(){
 const sql=new DatabaseSync(':memory:');
 sql.exec(readFileSync(new URL('../integrations/hud-cloud/schema.sql',import.meta.url),'utf8'));
 const DB={prepare(statement){
  const stmt=sql.prepare(statement);let args=[];
  const bound={bind(...xs){args=xs;return bound;},
   async first(){return stmt.get(...args)||null;},
   async all(){return {results:stmt.all(...args)};},
   async run(){return {meta:{changes:Number(stmt.run(...args).changes)}};}};
  return bound;
 }};
 return {sql,DB,env:{DB,HUD_READER_TOKEN:R,HUD_WRITER_TOKEN:W,GHOST_SITE_SERVICE_TOKEN:S}};
}
function reply(sendAt,{receipt=true,statusOk=true,code=200,invalid=false}={}){
 const calls=[];
 const send=async(url,opts)=>{
  assert.equal(url,SITE);assert.equal(opts.method,'POST');
  assert.equal(opts.redirect,'manual');assert.equal(opts.headers.Authorization,'Bearer '+S);
  assert.equal(opts.headers['Content-Type'],'application/json');
  const body=JSON.parse(opts.body);
  assert.deepEqual(Object.keys(body).sort(),
   body.operation==='inventory'?['operation','provider']:['operation']);
  assert(['inventory','status'].includes(body.operation));
  calls.push(body);
  if(code!==200)return new Response('denied',{status:code});
  if(body.operation==='inventory')
   return Response.json({provider:body.provider,status:'catalog_received',
    observed_at:sendAt,
    models:invalid?[{id:'../../secret'}]:[{id:'vendor/model-v1'}],
    ...(receipt?{d1_persisted:true,d1_observed_at:sendAt}:{})});
  if(body.operation==='status')return Response.json({execution_source:'cloud_provider',
   providers:CATALOG_PROVIDERS.map(provider=>({provider,
    last_check:statusOk?{provider,status:'catalog_received',observed_at:sendAt}:
     {provider,status:'catalog_received',observed_at:sendAt-50000}}))});
  throw Error('unexpected_call');
 };
 return {send,calls};
}
test('nine exact providers rotate on independent clock and require both Site and Worker D1 readbacks',async()=>{
 const s=setup();const modelList=[];
 for(let i=0;i<9;i++){
  const at=T+i*300001;
  const q=reply(at);
  const done=await refreshCatalogBridge(s.env,at,q.send);
  assert.equal(done.provider,CATALOG_PROVIDERS[i]);
  assert.equal(done.status,'catalog_received');
  assert.equal(done.site_d1_verified,true);
  assert.equal(done.worker_d1_verified,true);
  assert.equal(done.inference_online_verified,false);
  assert.equal(q.calls.length,2,'one catalog request plus exact D1 status readback');
  assert.equal((await refreshCatalogBridge(s.env,at+1000,q.send)).state,'interval_not_due');
  assert.equal(q.calls.length,2,'same five-minute window never calls Site twice');
  modelList.push(done.provider);
 }
 assert.equal(new Set(modelList).size,9);
 const status=await catalogBridgeStatus(s.env,T+8*300001);
 assert.equal(status.source,'cloudflare_site_catalog_bridge');
 assert.equal(status.provider_count,9);
 assert.equal(status.site_d1_verified_count,9);
 assert.equal(status.inference_online_verified_count,0);
 assert(status.providers.every(x=>x.status==='catalog_received'&&
   x.site_d1_verified&&x.models.length===1&&x.inference_online_verified===false&&
   x.free_billing_verified===false&&x.quota_verified===false));
 const body=JSON.stringify(status);
 assert(!body.includes(S),'service token must never reach browser');
 assert(!body.includes(R));
});
test('adjacent native five-minute slots advance despite cron jitter, without same-window duplicates',async()=>{
 const s=setup();
 const first=T+10000; // cron at 20:00:10
 const firstReply=reply(first);
 const initial=await refreshCatalogBridge(s.env,first,firstReply.send);
 assert.equal(initial.provider,CATALOG_PROVIDERS[0]);
 assert.equal(initial.site_d1_verified,true);
 assert.equal((await refreshCatalogBridge(s.env,first+1000,firstReply.send)).state,'interval_not_due');
 assert.equal(firstReply.calls.length,2);
 const next=T+300000+2000; // next cron at 20:05:02; only 4m52s elapsed
 const nextReply=reply(next);
 const progressed=await refreshCatalogBridge(s.env,next,nextReply.send);
 assert.equal(progressed.provider,CATALOG_PROVIDERS[1],
  'short normal cron jitter must not delay the next provider by another five minutes');
 assert.equal(progressed.site_d1_verified,true);
 assert.equal(nextReply.calls.length,2);
 assert.equal((await refreshCatalogBridge(s.env,next+1000,nextReply.send)).state,'interval_not_due');
 assert.equal(nextReply.calls.length,2,'no second request within the same clock window');
});

test('missing/shared service credentials fail without network or pretending online',async()=>{
 for(const key of [null,R,W,'short']){
  const s=setup();if(key===null)delete s.env.GHOST_SITE_SERVICE_TOKEN;
  else s.env.GHOST_SITE_SERVICE_TOKEN=key;
  const done=await refreshCatalogBridge(s.env,T,()=>{throw Error('never_call');});
  assert.equal(done.status,'bridge_unconfigured');
  assert.equal(done.model_count,0);
  assert.equal(done.site_d1_verified,false);
  const snapshot=await catalogBridgeStatus(s.env,T);
  assert.equal(snapshot.provider_count,9);
  assert.equal(snapshot.inference_online_verified_count,0);
  assert.equal(snapshot.providers[0].status,'bridge_unconfigured');
  assert.equal(snapshot.providers[0].direct_setup_blocker,'no_provider_key');
 }
});
test('service denial, missing Site D1 receipt, mismatched timestamp and unsafe model names are fail-closed',async()=>{
 for(const [params,expected,requests] of [
  [{code:403},'site_auth_denied',1],
  [{receipt:false},'site_receipt_missing',1],
  [{statusOk:false},'site_readback_mismatch',2],
  [{invalid:true},'invalid_contract',1]
 ]){
  const s=setup(),q=reply(T,params);
  const receipt=await refreshCatalogBridge(s.env,T,q.send);
  assert.equal(receipt.status,expected);assert.equal(q.calls.length,requests);
  assert.equal(receipt.site_d1_verified,false);
  const snapshot=await catalogBridgeStatus(s.env,T);
  assert.equal(snapshot.site_d1_verified_count,0);
  assert.equal(snapshot.providers[0].direct_setup_blocker,'no_provider_key');
  assert.equal(snapshot.providers[0].inference_online_verified,false);
 }
});
test('viewer-only catalog GET and optional secret transfer never expose keys or authorize paid models',async()=>{
 const s=setup();
 const anonymous=await handle(new Request('https://hud.test/api/hud/provider-catalogs'),s.env,T);
 assert.equal(anonymous.status,401);
 const viewer=await handle(new Request('https://hud.test/api/hud/provider-catalogs',{
  headers:{Authorization:'Bearer '+R}}),s.env,T);
 assert.equal(viewer.status,200);
 const data=await viewer.json();
 assert.equal(data.providers.length,9);
 assert.equal(data.inference_online_verified_count,0);
 const payload=buildHudSecretPayload({ROVOR_HUD_READER_TOKEN:R,
  ROVOR_HUD_WRITER_TOKEN:W,ROVOR_GHOST_SERVICE_TOKEN:S});
 assert.equal(payload.GHOST_SITE_SERVICE_TOKEN,S);
 assert(!Object.hasOwn(payload,'ROVOR_GHOST_SERVICE_TOKEN'));
 assert.throws(()=>buildHudSecretPayload({ROVOR_HUD_READER_TOKEN:R,
  ROVOR_HUD_WRITER_TOKEN:W,ROVOR_GHOST_SERVICE_TOKEN:R}));
});


test('release reports per-provider blockers without exposing secrets or model names',async()=>{
 const s=setup();
 delete s.env.GHOST_SITE_SERVICE_TOKEN;
 await refreshCatalogBridge(s.env,T,()=>{throw Error('no network');});
 const status=await catalogBridgeStatus(s.env,T);
 const send=async(url,init)=>{
  assert.equal(url,'https://rovor-hud-telemetry.rovordigital.workers.dev/api/hud/provider-catalogs');
  return init.headers.Authorization?Response.json(status):new Response('',{status:401});
 };
 const report=await verifyCatalogBridge(R,send,{attempts:1});
 assert.equal(report.checked_provider_slots,1);
 assert.equal(report.fresh_provider_slots,1);
 assert.equal(report.recent_site_d1_catalog_receipts,0);
 assert.equal(report.catalog_check_states.gemini,'bridge_unconfigured');
 assert.equal(report.direct_setup_blockers.gemini,'no_provider_key');
 assert.equal(report.catalog_check_states.groq,'never_checked');
 assert.equal(report.verified_online_inference_providers,0);
 assert(!JSON.stringify(report).includes(S));
 assert(!Object.hasOwn(report,'models'));
 const ui=readFileSync(new URL('../dashboard/command-center/native-v8-9/workforce-review.js',import.meta.url),'utf8');
 assert.match(ui,/Direct cloud key missing; private Site relay denied/);
});


test('native Cloudflare direct Gemini/Groq catalogs authenticate with fixed GET and bypass denied Site',async()=>{
 const s=setup(),calls=[];
 s.env.GEMINI_API_KEY='g'.repeat(40);
 s.env.GROQ_HUD_API_KEY='q'.repeat(40);
 const send=async(url,opts)=>{
  calls.push({url,method:opts.method,redirect:opts.redirect,
   auth:opts.headers.Authorization,google:opts.headers['x-goog-api-key']});
  if(url==='https://generativelanguage.googleapis.com/v1beta/models')
   return Response.json({models:[{name:'models/gemini-2.5-flash'},{name:'models/gemini-2.5-flash'}]});
  if(url==='https://api.groq.com/openai/v1/models')
   return Response.json({data:[{id:'openai/gpt-oss-20b'}]});
  throw Error('unexpected Site request');
 };
 const first=await refreshCatalogBridge(s.env,T,send);
 const second=await refreshCatalogBridge(s.env,T+300001,send);
 assert.equal(first.provider,'gemini');assert.equal(second.provider,'groq');
 assert.equal(first.catalog_source,'direct_provider');
 assert.equal(first.site_d1_verified,false);
 assert.equal(first.worker_d1_verified,true);
 assert.equal(second.status,'catalog_received');
 assert.equal(calls.length,2);
 assert.equal(calls[0].method,'GET');assert.equal(calls[0].redirect,'manual');
 assert.equal(calls[0].google,s.env.GEMINI_API_KEY);
 assert.equal(calls[0].auth,undefined);
 assert.equal(calls[1].auth,'Bearer '+s.env.GROQ_HUD_API_KEY);
 const status=await catalogBridgeStatus(s.env,T+300001);
 assert.equal(status.direct_catalog_received_count,2);
 assert.equal(status.site_d1_verified_count,0);
 assert.equal(status.inference_online_verified_count,0);
 assert.equal(status.providers[0].catalog_source,'direct_provider');
 assert.deepEqual(status.providers[0].models,['gemini-2.5-flash']);
 assert.deepEqual(status.providers[1].models,['openai/gpt-oss-20b']);
 assert(status.providers.every(x=>x.free_billing_verified===false&&x.quota_verified===false));
 const proof=await verifyCatalogBridge(R,async(url,opts)=>opts.headers.Authorization?
  Response.json(status):new Response('',{status:401}),{attempts:1});
 assert.equal(proof.direct_provider_catalog_receipts,2);
 assert.equal(proof.catalog_sources.gemini,'direct_provider');
 assert.equal(proof.verified_online_inference_providers,0);
 assert(!JSON.stringify(proof).includes(s.env.GROQ_HUD_API_KEY));
});

test('native direct provider catalog failures are recorded without Site fallback or Free admission',async()=>{
 const cases=[
  [401,'provider_auth_denied'],
  [429,'provider_rate_limited'],
  [500,'provider_http_unavailable']
 ];
 for(const [code,category] of cases){
  const s=setup();s.env.GEMINI_API_KEY='g'.repeat(40);
  let calls=0;
  const result=await refreshCatalogBridge(s.env,T,async(url,opts)=>{
   calls++;assert.equal(url,'https://generativelanguage.googleapis.com/v1beta/models');
   return new Response('denied',{status:code});
  });
  assert.equal(calls,1,'configured direct key never silently routes to Site');
  assert.equal(result.status,'upstream_unavailable');
  const read=await catalogBridgeStatus(s.env,T);
  assert.equal(read.providers[0].catalog_source,'direct_provider');
  assert.equal(read.providers[0].direct_error_category,category);
  assert.equal(read.direct_catalog_received_count,0);
  assert.equal(read.providers[0].inference_online_verified,false);
 }
});
test('OpenRouter public zero-price names and Cloudflare model name use exact catalog IDs only',async()=>{
 const env={OPENROUTER_API_KEY:'o'.repeat(40),CLOUDFLARE_AI_API_KEY:'c'.repeat(40),
  CLOUDFLARE_ACCOUNT_ID:'a'.repeat(32)};
 const openCalls=[];
 const open=await directProviderCatalog(env,'openrouter',async(url,opts)=>{
  openCalls.push(url);
  assert.equal(opts.method,'GET');
  assert.equal(opts.headers.Authorization,'Bearer '+env.OPENROUTER_API_KEY);
  if(url==='https://openrouter.ai/api/v1/key')
   return Response.json({data:{is_free_tier:true}});
  assert.equal(url,'https://openrouter.ai/api/v1/models');
  return Response.json({data:[
   {id:'vendor/preview:free',pricing:{prompt:'0',completion:'0'}},
   {id:'vendor/paid',pricing:{prompt:'0.1',completion:'0'}},
   {id:'vendor/not-actually-free:free',pricing:{prompt:'0',completion:'0.03'}}
  ]});
 });
 assert.deepEqual(openCalls,['https://openrouter.ai/api/v1/key',
  'https://openrouter.ai/api/v1/models']);
 assert.deepEqual(open.models,['vendor/preview:free']);
 const cf=await directProviderCatalog(env,'cloudflare-ai',async(url,opts)=>{
  assert.equal(url,'https://api.cloudflare.com/client/v4/accounts/'+'a'.repeat(32)+'/ai/models/search');
  return Response.json({result:[{id:'deadbeef-uuid',name:'@cf/meta/llama-3.1-8b-instruct'},
   {id:'not-model',name:'javascript:bad'}]});
 });
 assert.deepEqual(cf.models,['@cf/meta/llama-3.1-8b-instruct']);
 assert.equal(cf.status,'catalog_received');
});
test('optional provider catalog secrets remain server-only and never use Cloudflare deployment token',()=>{
 const env={ROVOR_HUD_READER_TOKEN:R,ROVOR_HUD_WRITER_TOKEN:W,
  ROVOR_CLOUD_MISTRAL_API_KEY:'m'.repeat(40),
  ROVOR_CLOUD_OPENROUTER_API_KEY:'o'.repeat(40),
  CLOUDFLARE_API_TOKEN:'deployment-is-not-ai'};
 const payload=buildHudSecretPayload(env);
 assert.equal(payload.MISTRAL_API_KEY,env.ROVOR_CLOUD_MISTRAL_API_KEY);
 assert.equal(payload.OPENROUTER_API_KEY,env.ROVOR_CLOUD_OPENROUTER_API_KEY);
 assert(!Object.hasOwn(payload,'CLOUDFLARE_API_TOKEN'));
 assert(!Object.hasOwn(payload,'CLOUDFLARE_AI_API_KEY'));
 assert.throws(()=>buildHudSecretPayload({...env,ROVOR_CLOUD_MISTRAL_API_KEY:R}));
});

test('OpenRouter public model catalog cannot falsely authenticate a rejected key',async()=>{
 const env={OPENROUTER_API_KEY:'o'.repeat(40)};
 const calls=[];
 const denied=await directProviderCatalog(env,'openrouter',async(url,opts)=>{
  calls.push(url);
  assert.equal(opts.headers.Authorization,'Bearer '+env.OPENROUTER_API_KEY);
  if(url==='https://openrouter.ai/api/v1/key')
   return new Response('denied',{status:401});
  throw Error('unauthenticated model catalog must not be queried');
 });
 assert.equal(denied.status,'unavailable');
 assert.equal(denied.error_category,'provider_auth_denied');
 assert.deepEqual(denied.models,[]);
 assert.deepEqual(calls,['https://openrouter.ai/api/v1/key']);
 const malformed=await directProviderCatalog(env,'openrouter',async(url)=>{
  assert.equal(url,'https://openrouter.ai/api/v1/key');
  return Response.json({data:[]});
 });
 assert.equal(malformed.status,'invalid');
 assert.equal(malformed.error_category,'invalid_catalog_shape');
});
