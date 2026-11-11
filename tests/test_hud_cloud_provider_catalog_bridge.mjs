import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {catalogBridgeStatus,refreshCatalogBridge,CATALOG_PROVIDERS}
 from '../integrations/hud-cloud/cloud-provider-catalog-bridge.mjs';
import {handle} from '../integrations/hud-cloud/worker.mjs';
import {buildHudSecretPayload} from '../integrations/hud-cloud/private-worker-secret-payload.mjs';

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
