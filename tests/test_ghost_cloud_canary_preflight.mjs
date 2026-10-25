import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {PROVIDERS,tick} from '../integrations/ghost-cloud/runtime.mjs';
import {preflight,runCanary} from '../integrations/ghost-cloud/canary-preflight.mjs';

const NOW=Date.now();
const hash='a'.repeat(64);
const config=(provider='groq',more={})=>({
 enabled:true,model:provider==='openrouter'?'vendor/model:free':provider==='huggingface'?'vendor/model:pinned':'vendor-model-1',
 pool:'pool-'+provider,zero_cost:true,commercial_use:true,evidence_sha256:hash,
 verified_at:NOW-1000,valid_until:NOW+3600000,requests_per_day:9,tokens_per_day:10000,
 min_interval_ms:1000,max_input_bytes:500,max_output_tokens:64,roles:['Walter'],kinds:['checklist'],...more
});
const approval=(provider='groq',cfg=config(provider),more={})=>({
 execute_once:true,zero_spend_verified:true,commercial_terms_verified:true,quota_verified:true,
 provider,model:cfg.model,evidence_sha256:cfg.evidence_sha256,
 canary_id:'canary-'+provider+'-test',task_id:'walter-cloud-canary-preflight-20261025',
 source_commit:'c'.repeat(40),approved_at:NOW-1000,expires_at:NOW+60000,
 remaining_requests:9,remaining_tokens:10000,...more
});
function setup(enabled=true){
 const sqlite=new DatabaseSync(':memory:');
 sqlite.exec(readFileSync(new URL('../integrations/ghost-cloud/schema.sql',import.meta.url),'utf8'));
 if(enabled)sqlite.exec('UPDATE ghost_cloud_control SET enabled=1');
 const db={prepare(sql){const stmt=sqlite.prepare(sql);let args=[];
   const out={bind(...a){args=a;return out;},async first(){return stmt.get(...args)||null;},
    async run(){const x=stmt.run(...args);return {meta:{changes:Number(x.changes)}};},
    async all(){return {results:stmt.all(...args)};}};return out;}};
 const env={DB:db,CLOUDFLARE_ACCOUNT_ID:'b'.repeat(32)};
 for(const [,key] of Object.values(PROVIDERS))env[key]='private-test-key-not-for-real-use';
 return {sqlite,env};
}
const success=(marker,model)=>Response.json({
 model,choices:[{message:{content:marker},finish_reason:'stop'}],
 usage:{prompt_tokens:17,completion_tokens:9}
});
const marker=a=>'ROVOR-CANARY-'+a.canary_id;

test('nine exact provider routes can each produce a bounded, private, quota-counted canary',async()=>{
 for(const provider of Object.keys(PROVIDERS)){
  const {sqlite,env}=setup(),cfg=config(provider),a=approval(provider,cfg);
  let called=0;
  const result=await runCanary({provider,cfg,env,approval:a,now:NOW,
   fetcher:async(url,opts)=>{
    called++;assert.match(url,/^https:\/\//);assert.equal(opts.redirect,'error');
    assert.equal(JSON.parse(opts.body).model,cfg.model);
    assert.equal(JSON.parse(opts.body).max_tokens,64);
    assert.equal(JSON.parse(opts.body).messages[0].content,'Return exactly '+marker(a)+' and nothing else.');
    return success(marker(a),cfg.model);
   }});
  assert.equal(called,1,provider);assert.equal(result.status,'needs_review',provider);
  assert.equal(result.actual_model,cfg.model);assert.equal(result.tokens_input,17);
  assert.match(result.canary_sha256,/^[a-f0-9]{64}$/);assert.equal(result.human_review,'not_recorded');
  assert.equal(sqlite.prepare('SELECT count(*) n FROM ghost_cloud_attempts').get().n,1);
  const row=sqlite.prepare('SELECT status,output,model,actual_model,reserved_tokens FROM ghost_cloud_attempts').get();
  assert.equal(row.status,'needs_review');assert.equal(row.output,null);
  assert.equal(row.model,cfg.model);assert.equal(row.actual_model,cfg.model);assert.ok(row.reserved_tokens>0);
  assert.equal(JSON.stringify(result).includes(env[PROVIDERS[provider][1]]),false);
 }
});

test('no call without persistent enabled control or exact explicit private approval',async()=>{
 for(const [enabled,alter,expected] of [
  [false,{},'stopped'],[true,{execute_once:false},'operator_approval_missing'],
  [true,{zero_spend_verified:false},'operator_approval_missing'],
  [true,{quota_verified:false},'operator_approval_missing'],
  [true,{model:'different'},'operator_approval_missing'],
  [true,{evidence_sha256:'b'.repeat(64)},'operator_approval_missing'],
  [true,{expires_at:NOW-1},'operator_approval_missing'],
  [true,{remaining_requests:0},'quota_unverified'],
  [true,{remaining_tokens:10},'quota_unverified']
 ]){
  const {env,sqlite}=setup(enabled),cfg=config(),a=approval('groq',cfg,alter);
  const result=await runCanary({provider:'groq',cfg,env,approval:a,now:NOW,
    fetcher:async()=>{throw Error('should not call');}});
  assert.equal(result.reason,expected,JSON.stringify(alter));
  assert.equal(sqlite.prepare('SELECT count(*) n FROM ghost_cloud_attempts').get().n,0);
 }
});

test('paid, unpinned, expired, unsupported upstream and missing secrets fail closed',()=>{
 const {env}=setup();
 for(const [provider,cfg,expected] of [
  ['groq',config('groq',{zero_cost:false}),'eligibility_unverified'],
  ['groq',config('groq',{valid_until:NOW}),'eligibility_expired'],
  ['groq',config('groq',{model:'auto'}),'unpinned_model'],
  ['openrouter',config('openrouter',{model:'vendor/model'}),'paid_route_denied'],
  ['huggingface',config('huggingface',{model:'vendor/model'}),'unpinned_upstream'],
  ['groq',config('groq',{max_output_tokens:2401}),'invalid_limits'],
 ]){
  const a=approval(provider,cfg);
  assert.equal(preflight(provider,cfg,env,a,NOW),expected);
 }
 assert.equal(preflight('groq',config(),{...env,GROQ_API_KEY:''},approval(),NOW),'not_configured');
});

test('canary IDs are immutable and never replay even after success',async()=>{
 const {env,sqlite}=setup(),cfg=config(),a=approval();let calls=0;
 const options={provider:'groq',cfg,env,approval:a,now:NOW,
  fetcher:async()=>{calls++;return success(marker(a),cfg.model);}};
 assert.equal((await runCanary(options)).status,'needs_review');
 assert.equal((await runCanary(options)).reason,'canary_id_used');
 assert.equal(calls,1);
 assert.equal(sqlite.prepare('SELECT count(*) n FROM ghost_cloud_attempts').get().n,1);
});

test('overlapping same-account probes cannot both dispatch',async()=>{
 const {env,sqlite}=setup();
 const c1=config('groq',{pool:'same'}),c2=config('mistral',{pool:'same'});
 const a1=approval('groq',c1),a2=approval('mistral',c2);
 let release;const waiting=new Promise(resolve=>{release=resolve;});
 let started;const start=new Promise(resolve=>{started=resolve;});
 const one=runCanary({provider:'groq',cfg:c1,env,approval:a1,now:NOW,
  fetcher:async()=>{started();await waiting;return success(marker(a1),c1.model);}});
 await start;
 const two=await runCanary({provider:'mistral',cfg:c2,env,approval:a2,now:NOW,
  fetcher:async()=>{throw Error('shared pool overlap');}});
 assert.equal(two.reason,'shared_pool_or_stop_admission');
 release();assert.equal((await one).status,'needs_review');
 assert.equal(sqlite.prepare('SELECT count(*) n FROM ghost_cloud_attempts').get().n,1);
});

test('quota exhaustion blocks a new canary without a model request',async()=>{
 const {env,sqlite}=setup();
 const cfg=config('groq',{requests_per_day:1});
 const a=approval('groq',cfg);
 assert.equal((await runCanary({provider:'groq',cfg,env,approval:a,now:NOW,
  fetcher:async()=>success(marker(a),cfg.model)})).status,'needs_review');
 const b=approval('groq',cfg,{canary_id:'canary-groq-other'});
 const result=await runCanary({provider:'groq',cfg,env,approval:b,now:NOW+2000,
  fetcher:async()=>{throw Error('quota bypass');}});
 assert.equal(result.reason,'shared_pool_or_stop_admission');
 assert.equal(sqlite.prepare('SELECT count(*) n FROM ghost_cloud_attempts').get().n,1);
});

test('HTTP429, model mismatch and malformed responses are never canary-verified',async()=>{
 for(const [reply,expected] of [
  [new Response('secret response',{status:429}),'rate_limited'],
  [success(marker(approval()),'other-model'),'model_mismatch'],
  [Response.json({model:config().model,choices:[{message:{content:'almost'},finish_reason:'stop'}]}),'canary_mismatch'],
  [new Response('{bad'),'transport_or_response_failure'],
  [new Response('x'.repeat(33000)),'transport_or_response_failure']
 ]){
  const {env,sqlite}=setup(),cfg=config(),a=approval();
  const out=await runCanary({provider:'groq',cfg,env,approval:a,now:NOW,fetcher:async()=>reply});
  assert.notEqual(out.status,'needs_review');assert.equal(out.reason,expected);
  assert.equal(out.canary_sha256,null);
  assert.equal(sqlite.prepare('SELECT output FROM ghost_cloud_attempts').get().output,null);
 }
});

test('canary cannot turn a disabled fleet on or approve a model output',async()=>{
 const {env,sqlite}=setup(),cfg=config(),a=approval();
 const out=await runCanary({provider:'groq',cfg,env,approval:a,now:NOW,
  fetcher:async()=>success(marker(a),cfg.model)});
 assert.equal(out.status,'needs_review');
 assert.equal(sqlite.prepare('SELECT enabled FROM ghost_cloud_control WHERE id=1').get().enabled,1);
 assert.equal(sqlite.prepare('SELECT human_review FROM ghost_cloud_attempts').get().human_review,'not_recorded');
});

test('denied canary cannot become ordinary work after its one-time approval expires',async()=>{
 const {env,sqlite}=setup(),cfg=config(),first=approval();
 assert.equal((await runCanary({provider:'groq',cfg,env,approval:first,now:NOW,
  fetcher:async()=>success(marker(first),cfg.model)})).status,'needs_review');
 const deniedApproval=approval('groq',cfg,{canary_id:'canary-groq-denied-later'});
 const denied=await runCanary({provider:'groq',cfg,env,approval:deniedApproval,now:NOW+1,
  fetcher:async()=>{throw Error('pool spacing must deny probe');}});
 assert.equal(denied.reason,'shared_pool_or_stop_admission');
 assert.equal(sqlite.prepare('SELECT kind FROM ghost_cloud_jobs WHERE id=?').get(deniedApproval.canary_id).kind,'canary');
 env.GHOST_FLEET_CONFIG=JSON.stringify({groq:{...cfg,canary_at:NOW,canary_sha256:'b'.repeat(64)}});
 let calls=0;
 const result=await tick(env,async()=>{calls++;return success(marker(deniedApproval),cfg.model);},NOW+120000);
 assert.equal(result.dispatched,0);assert.equal(calls,0);
 assert.equal(sqlite.prepare('SELECT count(*) n FROM ghost_cloud_attempts WHERE job_id=?').get(deniedApproval.canary_id).n,0);
});
