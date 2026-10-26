import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {PROVIDERS,eligibility,requestFor,infer,claim,tick,validateJob} from '../integrations/ghost-cloud/runtime.mjs';
import worker from '../integrations/ghost-cloud/worker.mjs';

const NOW=Date.now();
const cfg=(extra={})=>({enabled:true,model:'test-pinned-1',pool:'account-one',zero_cost:true,commercial_use:true,evidence_sha256:'a'.repeat(64),verified_at:NOW-1000,valid_until:NOW+3600000,canary_at:NOW-500,canary_sha256:'b'.repeat(64),requests_per_day:100,tokens_per_day:1000000,min_interval_ms:1,max_input_bytes:5000,max_output_tokens:512,roles:['Walter'],kinds:['research'],...extra});
const configFor=(p,extra={})=>cfg({pool:p,model:p==='openrouter'?'test/model:free':p==='huggingface'?'test/model:explicit-provider':'test-pinned-1',...extra});
function database(){
 const sqlite=new DatabaseSync(':memory:');sqlite.exec(readFileSync(new URL('../integrations/ghost-cloud/schema.sql',import.meta.url),'utf8'));
 const db={prepare(sql){let args=[];const stmt=sqlite.prepare(sql);const result={bind(...a){args=a;return result;},async first(){return stmt.get(...args)??null;},async all(){return {results:stmt.all(...args)};},async run(){const r=stmt.run(...args);return {meta:{changes:Number(r.changes)}};}};return result;}};
 return {db,sqlite};
}
function setup(config={groq:cfg()}){
 const {db,sqlite}=database();const env={DB:db,GHOST_FLEET_CONFIG:JSON.stringify(config),GHOST_READER_TOKEN:'r'.repeat(40),GHOST_WRITER_TOKEN:'w'.repeat(40),CLOUDFLARE_ACCOUNT_ID:'a'.repeat(32)};
 for(const [,key] of Object.values(PROVIDERS))env[key]='secret-value-never-returned';
 return {env,db,sqlite};
}
const job=(id,extra={})=>({id,employee:'Walter',task_id:'canonical-task',kind:'research',title:'Review public implementation',prompt:'Compare these two public interfaces.',source_commit:'c'.repeat(40),data_class:'public_repository',...extra});
function enqueue(sqlite,j){validateJob(j);sqlite.prepare('INSERT INTO ghost_cloud_jobs VALUES(?,?,?,?,?,?,?,?,?)').run(j.id,j.employee,j.task_id,j.kind,j.title,j.prompt,Buffer.byteLength(j.prompt),j.source_commit,NOW);}
function enable(sqlite){sqlite.exec('UPDATE ghost_cloud_control SET enabled=1');}
const success=(model='upstream-pinned-1')=>new Response(JSON.stringify({model,choices:[{message:{content:'Concrete draft for independent human review.'},finish_reason:'stop'}],usage:{prompt_tokens:9,completion_tokens:8}}),{headers:{'Content-Type':'application/json'}});
const api=(env,path,method='GET',value,writer=false)=>worker.fetch(new Request('https://private.example'+path,{method,headers:{Authorization:'Bearer '+(writer?env.GHOST_WRITER_TOKEN:env.GHOST_READER_TOKEN),'Content-Type':'application/json'},body:value===undefined?undefined:JSON.stringify(value)}),env);

test('all nine configured providers get their own fixed HTTPS endpoint and secret',()=>{
 const {env}=setup();assert.equal(Object.keys(PROVIDERS).length,9);
 for(const p of Object.keys(PROVIDERS)){
  const c=configFor(p);assert.equal(eligibility(p,c,env,NOW),null);
  const [url,init]=requestFor(p,c,env,'public task');assert.ok(url.startsWith('https://'));assert.equal(init.redirect,'manual');assert.equal(init.method,'POST');
  const body=JSON.parse(init.body);assert.equal(body.model,c.model);assert.equal(body.max_tokens,512);assert.equal(body.stream,false);
  assert.equal(init.headers.Authorization,'Bearer '+env[PROVIDERS[p][1]]);
 }
 const body=JSON.parse(requestFor('openrouter',configFor('openrouter'),env,'public task')[1].body);
 assert.deepEqual(body.provider,{allow_fallbacks:false,require_parameters:true,max_price:{prompt:0,completion:0}});
});

test('eligibility rejects missing, expired, costly, unpinned or unverified routes',()=>{
 const {env}=setup();
 for(const change of [{enabled:false},{zero_cost:false},{commercial_use:false},{model:'auto'},{valid_until:NOW},{verified_at:NOW-86400001},{canary_at:null},{evidence_sha256:''},{requests_per_day:0},{max_output_tokens:2401},{roles:['Admin']},{kinds:['execute_command']}])assert.ok(eligibility('groq',cfg(change),env,NOW));
 assert.equal(eligibility('groq',cfg(),{...env,GROQ_API_KEY:''},NOW),'missing_secret');
 assert.equal(eligibility('cloudflare-ai',cfg(),{...env,CLOUDFLARE_ACCOUNT_ID:'bad'},NOW),'missing_account');
 assert.equal(eligibility('openrouter',cfg(),env,NOW),'paid_route_denied');
 assert.equal(eligibility('huggingface',cfg(),env,NOW),'unpinned_upstream');
});

test('STOP defaults to disabled, so queued jobs cause zero inference',async()=>{
 const {env,sqlite}=setup();enqueue(sqlite,job('stop-default'));let called=0;
 assert.deepEqual(await tick(env,async()=>{called++;return success();},NOW),{enabled:false,dispatched:0});assert.equal(called,0);
});

test('all nine cloud routes invoke the mocked transport and retain distinct returned receipts',async()=>{
 const configs=Object.fromEntries(Object.keys(PROVIDERS).map(p=>[p,configFor(p)]));const {env,sqlite}=setup(configs);enable(sqlite);
 for(let i=0;i<9;i++)enqueue(sqlite,job('fleet-'+i));const seen=[];
 const result=await tick(env,async(url)=>{seen.push(url);return success();},NOW);
 assert.equal(result.dispatched,9);assert.equal(new Set(seen).size,9);
 const rows=sqlite.prepare('SELECT * FROM ghost_cloud_attempts').all();assert.equal(rows.length,9);
 assert.equal(new Set(rows.map(r=>r.provider)).size,9);
 for(const r of rows){assert.equal(r.status,'needs_review');assert.equal(r.actual_model,'upstream-pinned-1');assert.equal(r.tokens_input,9);assert.equal(r.human_review,'not_recorded');}
});

test('overlapping claims cannot execute one job twice or overlap a shared account',async()=>{
 const {db,sqlite}=setup();enable(sqlite);enqueue(sqlite,job('once'));enqueue(sqlite,job('later'));
 const rows=await Promise.all([claim(db,'groq',cfg(),NOW),claim(db,'mistral',cfg(),NOW)]);
 assert.equal(rows.filter(Boolean).length,1);assert.equal(sqlite.prepare('SELECT count(*) n FROM ghost_cloud_attempts').get().n,1);
});

test('rolling shared request and token reservations stop dispatch before limits',async()=>{
 for(const policy of [{requests_per_day:1},{tokens_per_day:1000}]){
  const c=cfg(policy),{env,sqlite}=setup({groq:c});enable(sqlite);enqueue(sqlite,job('budget-one'));enqueue(sqlite,job('budget-two'));
  const a=await tick(env,async()=>success(),NOW);assert.equal(a.dispatched,1);
  const b=await tick(env,async()=>{throw Error('must not call');},NOW+2);assert.equal(b.dispatched,0);
 }
});

test('model receives only a proportional eligible public task',async()=>{
 const {env,sqlite}=setup();enable(sqlite);enqueue(sqlite,job('wrong-role',{employee:'Jesse'}));enqueue(sqlite,job('large',{prompt:'x'.repeat(5001)}));enqueue(sqlite,job('correct'));
 assert.equal((await tick(env,async(_url,init)=>{assert.equal(JSON.parse(init.body).messages[0].content,job('correct').prompt);return success();},NOW)).dispatched,1);
 assert.equal(sqlite.prepare('SELECT job_id FROM ghost_cloud_attempts').get().job_id,'correct');
});

test('429 respects retry-after across new jobs in a shared pool',async()=>{
 const {env,sqlite}=setup();enable(sqlite);enqueue(sqlite,job('limited'));enqueue(sqlite,job('replacement'));
 await tick(env,async()=>new Response('private vendor error',{status:429,headers:{'Retry-After':'120'}}),NOW);
 assert.equal((await tick(env,async()=>{throw Error('not due');},NOW+1000)).dispatched,0);
 assert.equal((await tick(env,async()=>success(),NOW+121000)).dispatched,1);
 assert.equal(sqlite.prepare("SELECT error_code FROM ghost_cloud_attempts WHERE job_id='limited'").get().error_code,'rate_limited');
});

test('network uncertainty and stale running claims never replay their jobs',async()=>{
 const {env,db,sqlite}=setup();enable(sqlite);enqueue(sqlite,job('uncertain'));
 await tick(env,async()=>{throw Error('secret-containing transport failure');},NOW);
 assert.equal((await tick(env,async()=>{throw Error('replayed');},NOW+200000)).dispatched,0);
 assert.equal(sqlite.prepare('SELECT status,error_code FROM ghost_cloud_attempts').get().status,'uncertain');
 enqueue(sqlite,job('interrupted'));await claim(db,'groq',cfg(),NOW+200001);
 await tick(env,async()=>{throw Error('replayed');},NOW+400002);
 assert.equal(sqlite.prepare("SELECT error_code FROM ghost_cloud_attempts WHERE job_id='interrupted'").get().error_code,'interrupted_attempt');
});

test('blank, truncated, tool-call, oversized or malformed responses never count as work',async()=>{
 const {env}=setup();
 const replies=[{choices:[{message:{content:''},finish_reason:'stop'}]},{choices:[{message:{content:'partial'},finish_reason:'length'}]},{choices:[{message:{tool_calls:[{}]},finish_reason:'tool_calls'}]}, {choices:[{message:{content:'x'.repeat(32769)},finish_reason:'stop'}]}];
 for(const r of replies){const out=await infer('groq',cfg(),env,'public',async()=>Response.json(r),NOW);assert.equal(out.status,'failed');assert.equal(out.output,undefined);}
 for(const body of ['{', 'x'.repeat(131073)]){const out=await infer('groq',cfg(),env,'public',async()=>new Response(body),NOW);assert.equal(out.status,'uncertain');}
});

test('unknown usage and actual upstream stay unknown',async()=>{
 const {env}=setup();const out=await infer('groq',cfg(),env,'public',async()=>Response.json({choices:[{message:{content:'A concrete output.'},finish_reason:'stop'}]}),NOW);
 assert.equal(out.status,'needs_review');assert.equal(out.actual_model,null);assert.equal(out.tokens_input,null);assert.equal(out.tokens_output,null);
});

test('job boundary rejects private classification, arbitrary operations and additional fields',()=>{
 for(const change of [{data_class:'client_private'},{kind:'shell'},{id:'../private'},{prompt:'x'.repeat(14501)},{prompt:' '},{source_commit:'main'},{approved:true}])assert.throws(()=>validateJob(job('invalid',change)));
});

test('reader/writer separation, STOP control and immutable enqueue',async()=>{
 const {env,sqlite}=setup();assert.equal((await worker.fetch(new Request('https://private.example/api/ghost/status'),env)).status,401);
 assert.equal((await api(env,'/api/ghost/jobs','POST',job('new'))).status,401);
 assert.equal((await api(env,'/api/ghost/status','GET',undefined,true)).status,401);
 assert.equal((await api(env,'/api/ghost/jobs','POST',job('new'),true)).status,201);
 assert.equal((await api(env,'/api/ghost/jobs','POST',job('new'),true)).status,200);
 assert.equal((await api(env,'/api/ghost/jobs','POST',job('new',{prompt:'changed'}),true)).status,409);
 assert.equal((await api(env,'/api/ghost/control','POST',{enabled:true},true)).status,200);
 assert.equal(sqlite.prepare('SELECT enabled FROM ghost_cloud_control').get().enabled,1);
 assert.equal((await api({...env,GHOST_READER_TOKEN:env.GHOST_WRITER_TOKEN},'/api/ghost/status')).status,401);
});

test('HUD status exposes factual provider receipts without prompts, drafts or secrets',async()=>{
 const {env,sqlite}=setup();enable(sqlite);enqueue(sqlite,job('tracked'));await tick(env,async()=>success(),NOW);
 const response=await api(env,'/api/ghost/status'),text=await response.text(),data=JSON.parse(text);
 assert.equal(response.status,200);assert.equal(data.providers.length,9);assert.equal(data.attempts.length,1);assert.equal(data.attempts[0].tokens_input,9);
 for(const p of data.providers)assert.equal(p.online_verified,false);
 for(const privateValue of [job('tracked').prompt,'Concrete draft for independent human review.','secret-value-never-returned',env.GHOST_READER_TOKEN])assert.ok(!text.includes(privateValue));
 assert.equal((await (await api(env,'/api/ghost/jobs/tracked')).json()).output,'Concrete draft for independent human review.');
});

test('conflicting shared pool policy is rejected before inference',async()=>{
 const {env,sqlite}=setup({groq:cfg(),mistral:cfg({requests_per_day:2})});enable(sqlite);enqueue(sqlite,job('conflict'));
 await assert.rejects(tick(env,async()=>{throw Error('must not dispatch');},NOW),/conflicting_pool_limits/);
});

test('three failed attempts pause that pool while another provider takes fresh work',async()=>{
 const {env,sqlite}=setup({groq:cfg()});enable(sqlite);
 for(let i=0;i<5;i++)enqueue(sqlite,job('circuit-'+i));
 for(let i=0;i<3;i++)assert.equal((await tick(env,async()=>new Response('error',{status:503}),NOW+i*200)).dispatched,1);
 assert.equal((await tick(env,async()=>{throw Error('circuit not open');},NOW+1000)).dispatched,0);
 env.GHOST_FLEET_CONFIG=JSON.stringify({groq:cfg(),mistral:cfg({pool:'other-account'})});
 assert.equal((await tick(env,async()=>success(),NOW+1200)).dispatched,1);
 assert.equal(sqlite.prepare("SELECT count(*) n FROM ghost_cloud_attempts WHERE provider='groq'").get().n,3);
});

test('STOP during a fleet tick prevents subsequent provider calls',async()=>{
 const {env,sqlite}=setup({groq:cfg(),mistral:cfg({pool:'other-account'})});enable(sqlite);
 enqueue(sqlite,job('stop-first'));enqueue(sqlite,job('stop-second'));let requests=0;
 await tick(env,async()=>{requests++;sqlite.exec('UPDATE ghost_cloud_control SET enabled=0');return success();},NOW);
 assert.equal(requests,1);assert.equal(sqlite.prepare('SELECT count(*) n FROM ghost_cloud_attempts').get().n,1);
});

test('simultaneous scheduled ticks share the durable account lock',async()=>{
 const {env,sqlite}=setup();enable(sqlite);enqueue(sqlite,job('concurrent-first'));enqueue(sqlite,job('concurrent-second'));let requests=0;
 const fetcher=async()=>{requests++;await Promise.resolve();return success();};
 await Promise.all([tick(env,fetcher,NOW),tick(env,fetcher,NOW)]);assert.equal(requests,1);
});

test('global rolling-day emergency ceiling prevents a 145th claim',async()=>{
 const {db,sqlite}=setup();enable(sqlite);enqueue(sqlite,job('global-limit'));
 const insert=sqlite.prepare("INSERT INTO ghost_cloud_attempts(id,job_id,provider,model,pool,started_at,reserved_tokens,status) VALUES(?,?,?,?,?,?,?,'needs_review')");
 for(let i=0;i<144;i++){enqueue(sqlite,job('old-'+i));insert.run('id-'+i,'old-'+i,'other','other','other',NOW-1000,1);}
 assert.equal(await claim(db,'groq',cfg(),NOW),null);
});


test('reports exact read-only no-dispatch blockers without replay or private fields',async()=>{
 // A scheduled wakeup with no compatible job must not masquerade as work.
 const none=setup();enable(none.sqlite);
 const empty=await tick(none.env,async()=>{throw Error('unexpected inference');},NOW);
 assert.equal(empty.dispatched,0);
 assert.equal(empty.blocked.groq.reason,'no_matching_unattempted_job');

 const roles=setup();enable(roles.sqlite);
 enqueue(roles.sqlite,job('not-walter',{employee:'Saul'}));
 const mismatch=await tick(roles.env,async()=>{throw Error('unexpected inference');},NOW);
 assert.equal(mismatch.blocked.groq.reason,'no_matching_unattempted_job');
 assert.equal(roles.sqlite.prepare('SELECT COUNT(*) n FROM ghost_cloud_attempts').get().n,0);

 const wait=setup({groq:cfg({min_interval_ms:60000})});enable(wait.sqlite);
 enqueue(wait.sqlite,job('interval-first'));enqueue(wait.sqlite,job('interval-second'));
 assert.equal((await tick(wait.env,async()=>success(),NOW)).dispatched,1);
 const waiting=await tick(wait.env,async()=>{throw Error('cooldown must not infer');},NOW+1);
 assert.deepEqual(waiting.blocked.groq,{reason:'account_minimum_interval',next_eligible_at:NOW+60000});
 assert.equal(wait.sqlite.prepare('SELECT COUNT(*) n FROM ghost_cloud_attempts').get().n,1);

 const requests=setup({groq:cfg({requests_per_day:1})});enable(requests.sqlite);
 enqueue(requests.sqlite,job('request-first'));enqueue(requests.sqlite,job('request-second'));
 assert.equal((await tick(requests.env,async()=>success(),NOW)).dispatched,1);
 assert.equal((await tick(requests.env,async()=>{throw Error('request cap');},NOW+2)).blocked.groq.reason,'account_request_cap');

 const budget=setup({groq:cfg({tokens_per_day:1000})});enable(budget.sqlite);
 enqueue(budget.sqlite,job('tokens-first'));enqueue(budget.sqlite,job('tokens-second'));
 assert.equal((await tick(budget.env,async()=>success(),NOW)).dispatched,1);
 assert.equal((await tick(budget.env,async()=>{throw Error('token cap');},NOW+2)).blocked.groq.reason,'account_reserved_token_cap');

 const limited=setup();enable(limited.sqlite);
 enqueue(limited.sqlite,job('retry-first'));enqueue(limited.sqlite,job('retry-second'));
 assert.equal((await tick(limited.env,async()=>new Response('',{status:429,headers:{'Retry-After':'120'}}),NOW)).dispatched,1);
 const cooldown=await tick(limited.env,async()=>{throw Error('retry-after');},NOW+1000);
 assert.deepEqual(cooldown.blocked.groq,{reason:'account_retry_after',next_eligible_at:NOW+120000});
 assert.ok(!JSON.stringify(cooldown.blocked).includes('secret-value-never-returned'));

 const circuit=setup();enable(circuit.sqlite);
 for(let i=0;i<4;i++)enqueue(circuit.sqlite,job('failure-'+i));
 for(let i=0;i<3;i++)assert.equal((await tick(circuit.env,async()=>new Response('fail',{status:503}),NOW+i*200)).dispatched,1);
 const tripped=await tick(circuit.env,async()=>{throw Error('circuit');},NOW+1000);
 assert.equal(tripped.blocked.groq.reason,'failure_circuit_requires_review');
 assert.equal(circuit.sqlite.prepare('SELECT COUNT(*) n FROM ghost_cloud_attempts').get().n,3);
});
