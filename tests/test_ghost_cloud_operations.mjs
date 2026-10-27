import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import fs from 'node:fs';
import vm from 'node:vm';
import os from 'node:os';
import path from 'node:path';
import * as runtime from '../integrations/ghost-cloud/runtime.mjs';
import worker from '../integrations/ghost-cloud/worker.mjs';
import {runCanary} from '../integrations/ghost-cloud/canary-preflight.mjs';
import {createCloudOperations} from '../integrations/ghost-cloud/site-operations.mjs';
import {compileOperations,composeOperations} from '../integrations/ghost-cloud/compose-operations.mjs';

const root=new URL('../integrations/ghost-cloud/',import.meta.url);
const read=name=>fs.readFileSync(new URL(name,root),'utf8');
const reviewSchema="CREATE TABLE IF NOT EXISTS ghost_cloud_provider_checks(provider TEXT PRIMARY KEY,observed_at INTEGER NOT NULL,status TEXT NOT NULL,error_category TEXT);CREATE TABLE ghost_cloud_reviews(id TEXT PRIMARY KEY,attempt_id TEXT NOT NULL UNIQUE REFERENCES ghost_cloud_attempts(id),actor TEXT,verdict TEXT,output_sha256 TEXT,reviewed_at INTEGER);";
const baseSource=`function createSitesHandler(html){return async request=>{if(!request.headers.get('oai-authenticated-user-id'))return Response.json({error:'identity_required'},{status:401});if(new URL(request.url).pathname==='/mcp'){const rpc=await request.json();return Response.json({jsonrpc:'2.0',id:rpc.id,result:{tools:[{name:'rovor_workforce_status'}],content:[{type:'text',text:'never_received'}]}});}return new Response(html,{headers:{'Content-Type':'text/html'}});};}\nconst siteFetch = createSitesHandler('<html><body>Original HUD and logo</body></html>');\nexport default {fetch: siteFetch};\n`;
const j={id:'approved-job',employee:'Saul',task_id:'canonical-task',kind:'research',title:'Public source research',prompt:'Inspect this public service offer.',source_commit:'c'.repeat(40),data_class:'public_repository'};
function setup(){
 const db=new DatabaseSync(':memory:');db.exec(read('schema.sql'));db.exec(reviewSchema);
 const DB={prepare(text){const p=db.prepare(text);let args=[];const x={bind(...a){args=a;return x;},async first(){return p.get(...args)||null;},async all(){return {results:p.all(...args)};},async run(){return {meta:{changes:Number(p.run(...args).changes)}};}};return x;},async batch(items){db.exec('BEGIN');try{const result=[];for(const i of items)result.push(await i.run());db.exec('COMMIT');return result;}catch(e){db.exec('ROLLBACK');throw e;}}};
 const env={DB,GHOST_FLEET_CONFIG:'{}',GHOST_READER_TOKEN:'r'.repeat(40),GHOST_WRITER_TOKEN:'w'.repeat(40),GHOST_SERVICE_TOKEN:'s'.repeat(40),CLOUDFLARE_ACCOUNT_ID:'b'.repeat(32)};
 for(const [,key]of Object.values(runtime.PROVIDERS))env[key]='synthetic-provider-secret';
 const base=async request=>{if(new URL(request.url).pathname==='/mcp')return Response.json({jsonrpc:'2.0',id:1,result:{tools:[{name:'rovor_workforce_status'}],content:[{type:'text',text:'never_received'}]}});return new Response('<html><body>Original HUD and logo</body></html>',{headers:{'Content-Type':'text/html'}});};
 const cloud={...runtime,worker,canary:runCanary};const ops=createCloudOperations(base,cloud);
 return {env,db,ops,cloud};
}
const request=(route,{body,identity='owner',browser=false,serviceToken=null}={})=>new Request('https://private.example'+route,{method:body===undefined?'GET':'POST',headers:{...(identity?{'oai-authenticated-user-id':identity}:{}),'Content-Type':'application/json',...(serviceToken?{Authorization:'Bearer '+serviceToken}:{}),...(browser?{Origin:'https://private.example','Sec-Fetch-Site':'same-origin'}:{})},body:body===undefined?undefined:JSON.stringify(body)});
async function rpc(ops,env,name,args={}){const r=await ops.fetch(request('/mcp',{body:{jsonrpc:'2.0',id:1,method:'tools/call',params:{name,arguments:args}}}),env);const d=await r.json();return d.result?.isError?{isError:true}:JSON.parse(d.result.content[0].text);}
async function completed(s){s.env.GHOST_APPROVED_JOBS=JSON.stringify([j]);await s.ops.control(s.env,true);await s.ops.replenish(s.env);s.db.prepare("INSERT INTO ghost_cloud_attempts(id,job_id,provider,model,pool,started_at,finished_at,reserved_tokens,status,output,tokens_input,tokens_output) VALUES('attempt',?,'groq','requested','pool',1,2,100,'needs_review','A concrete private draft',7,9)").run(j.id);}

test('private routes require platform identity; no browser credentials are embedded',async()=>{
 const {env,ops}=setup();assert.equal((await ops.fetch(request('/api/ghost/status',{identity:null}),env)).status,401);
 const page=await (await ops.fetch(request('/'),env)).text();assert.match(page,/Original HUD and logo/);assert.match(page,/CLOUD EMPLOYEES/);
 for(const secret of [env.GHOST_READER_TOKEN,env.GHOST_WRITER_TOKEN,env.GROQ_API_KEY])assert.ok(!page.includes(secret));
 assert.match(page,/output.textContent=j.output/);
});
test('status describes nine configured but unverified providers without fake usage',async()=>{
 const {env,ops}=setup();const data=await (await ops.fetch(request('/api/ghost/status'),env)).json();
 assert.equal(data.providers.length,9);assert.equal(data.enabled,false);assert.deepEqual(data.attempts,[]);
 for(const p of data.providers){assert.equal(p.credentials_configured,true);assert.equal(p.admission,'disabled_pending_verification');assert.equal(p.online_verified,false);}
});
test('control can initialize schema-only singleton and private packets deduplicate',async()=>{
 const {env,db,ops}=setup();db.exec('DELETE FROM ghost_cloud_control');
 env.GHOST_APPROVED_JOBS=JSON.stringify([j]);assert.equal((await ops.replenish(env)).status,'stopped');
 assert.deepEqual(await rpc(ops,env,'rovor_cloud_control',{enabled:true}),{enabled:true});
 assert.deepEqual(await rpc(ops,env,'rovor_cloud_replenish'),{queued:1,duplicates:0});
 assert.deepEqual(await rpc(ops,env,'rovor_cloud_replenish'),{queued:0,duplicates:1});
 assert.equal(db.prepare('SELECT count(*) n FROM ghost_cloud_jobs').get().n,1);
});
test('packets come only from trusted config and are validated before any enqueue',async()=>{
 const {env,db,ops}=setup();await ops.control(env,true);
 assert.equal((await rpc(ops,env,'rovor_cloud_replenish',{prompt:'injected'})).isError,true);
 env.GHOST_APPROVED_JOBS=JSON.stringify([j,{...j,id:'private',data_class:'private_client'}]);
 await assert.rejects(ops.replenish(env));assert.equal(db.prepare('SELECT count(*) n FROM ghost_cloud_jobs').get().n,0);
});
test('cloud tick and canaries remain disabled without actual server-side eligibility',async()=>{
 const {env,ops}=setup();assert.deepEqual(await rpc(ops,env,'rovor_cloud_tick'),{enabled:false,dispatched:0});
 assert.deepEqual(await rpc(ops,env,'rovor_cloud_canary',{canary_id:'canary-groq-example'}),{status:'denied',reason:'private_approval_missing'});
 assert.equal((await rpc(ops,env,'rovor_cloud_canary',{canary_id:'canary-groq-example',approval:{execute_once:true}})).isError,true);
});
test('status includes job IDs and measured tokens while omitting draft text',async()=>{
 const s=setup();await completed(s);const result=await s.ops.status(s.env);
 assert.equal(result.attempts[0].job_id,j.id);assert.equal(result.attempts[0].tokens_input,7);assert.equal(result.attempts[0].human_review,'not_recorded');
 assert.ok(!JSON.stringify(result).includes('A concrete private draft'));
 const out=await (await s.ops.fetch(request('/api/ghost/jobs/'+j.id),s.env)).json();assert.equal(out.output,'A concrete private draft');
});
test('owner review backlog remains accessible after newer activity fills the 50-row sample',async()=>{
 const s=setup();await completed(s);
 const addJob=s.db.prepare('INSERT INTO ghost_cloud_jobs(id,employee,task_id,kind,title,prompt,input_bytes,source_commit,created_at) VALUES(?,?,?,?,?,?,?,?,?)');
 const addAttempt=s.db.prepare("INSERT INTO ghost_cloud_attempts(id,job_id,provider,model,pool,started_at,finished_at,reserved_tokens,status,output,tokens_input,tokens_output) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)");
 for(let i=0;i<55;i++){
  const id='recent-'+i;
  addJob.run(id,'Saul',id,'research','Public status check','public',6,'a'.repeat(40),100+i);
  addAttempt.run('attempt-'+i,id,'groq','requested','pool',100+i,100+i,100,'failed',null,0,0);
 }
 const data=await s.ops.status(s.env);
 assert.equal(data.attempts.length,50);
 assert.equal(data.attempts.some(a=>a.job_id===j.id),false);
 assert.equal(data.review_queue.pending_count,1);
 assert.equal(data.review_queue.oldest_finished_at,2);
 assert.equal(data.review_queue.items[0].job_id,j.id);
 assert.equal(data.review_queue.items[0].human_review,'not_recorded');
 assert.ok(!JSON.stringify(data).includes('A concrete private draft'));
 const page=await (await s.ops.fetch(request('/'),s.env)).text();
 assert.match(page,/OWNER REVIEW QUEUE/);
 assert.match(page,/drafts require explicit PASS or FAIL/);
 assert.equal((await s.ops.fetch(request('/api/ghost/review',{body:{job_id:j.id,verdict:'passed'},browser:true}),s.env)).status,200);
 const after=await s.ops.status(s.env);
 assert.equal(after.review_queue.pending_count,0);
 assert.deepEqual(after.review_queue.items,[]);
});
test('review queue count is exact while payload stays bounded at 50 metadata-only entries',async()=>{
 const s=setup();await completed(s);
 const addJob=s.db.prepare('INSERT INTO ghost_cloud_jobs(id,employee,task_id,kind,title,prompt,input_bytes,source_commit,created_at) VALUES(?,?,?,?,?,?,?,?,?)');
 const addAttempt=s.db.prepare("INSERT INTO ghost_cloud_attempts(id,job_id,provider,model,pool,started_at,finished_at,reserved_tokens,status,output,tokens_input,tokens_output) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)");
 for(let i=0;i<55;i++){
  const id='pending-'+i;
  addJob.run(id,'Saul',id,'research','Public reviewable work','public',6,'a'.repeat(40),100+i);
  addAttempt.run('attempt-'+i,id,'groq','requested','pool',100+i,100+i,100,'needs_review','private draft '+i,0,0);
 }
 const data=await s.ops.status(s.env);
 assert.equal(data.review_queue.pending_count,56);
 assert.equal(data.review_queue.items.length,50);
 assert.equal(data.review_queue.items[0].job_id,j.id);
 assert.equal(data.review_queue.items.at(-1).job_id,'pending-48');
 assert.equal(data.review_queue.oldest_finished_at,2);
 assert.ok(!JSON.stringify(data).includes('private draft'));
});
test('PASS/FAIL requires explicit owner-browser request and creates a digest-bound audit trail',async()=>{
 const s=setup();await completed(s);
 const body={job_id:j.id,verdict:'passed'};
 assert.equal((await s.ops.fetch(request('/api/ghost/review',{body}),s.env)).status,403);
 assert.equal((await s.ops.fetch(request('/api/ghost/review',{body,browser:true,identity:null}),s.env)).status,401);
 assert.equal((await s.ops.fetch(request('/api/ghost/review',{body,browser:true}),s.env)).status,200);
 assert.equal(s.db.prepare('SELECT human_review FROM ghost_cloud_attempts').get().human_review,'passed');
 const row=s.db.prepare('SELECT * FROM ghost_cloud_reviews').get();assert.equal(row.actor,'owner');assert.match(row.output_sha256,/^[a-f0-9]{64}$/);
 assert.equal((await s.ops.fetch(request('/api/ghost/review',{body:{...body,verdict:'failed'},browser:true}),s.env)).status,409);
 assert.equal(s.db.prepare('SELECT count(*) n FROM ghost_cloud_reviews').get().n,1);
 assert.equal(s.db.prepare('SELECT human_review FROM ghost_cloud_attempts').get().human_review,'passed');
});
test('model responses cannot mark an empty canary as human approved',async()=>{
 const s=setup();await completed(s);s.db.exec('UPDATE ghost_cloud_attempts SET output=NULL');
 assert.equal((await s.ops.fetch(request('/api/ghost/review',{body:{job_id:j.id,verdict:'passed'},browser:true}),s.env)).status,409);
 assert.equal(s.db.prepare('SELECT human_review FROM ghost_cloud_attempts').get().human_review,'not_recorded');
});
test('owner inventory checks refresh the exact provider HUD health row without claiming inference or quota',async t=>{
 const {env,db,ops}=setup();
 let deny=false,seen=0;
 t.mock.method(globalThis,'fetch',async(url,options)=>{
  seen++;assert.equal(url,'https://generativelanguage.googleapis.com/v1beta/openai/models');
  assert.equal(options.method,'GET');assert.equal(options.redirect,'manual');
  return deny?new Response('private upstream error body',{status:403}):
   Response.json({models:[{name:'models/gemini-2.5-flash'}],secret:'never displayed'});
 });
 const initial=await ops.status(env);
 assert.equal(initial.providers.find(p=>p.provider==='gemini').last_check,null);
 const fresh=await rpc(ops,env,'rovor_provider_inventory',{provider:'gemini'});
 assert.equal(fresh.status,'catalog_received');assert.equal(fresh.models.length,1);
 assert.equal(fresh.quota_verified,false);assert.equal(fresh.billing_verified,false);
 const after=await ops.status(env),provider=after.providers.find(p=>p.provider==='gemini');
 assert.equal(provider.last_check.status,'catalog_received');
 assert.equal(provider.last_check.observed_at,fresh.observed_at);
 assert.equal(provider.admission,'disabled_pending_verification');
 deny=true;
 const unavailable=await rpc(ops,env,'rovor_provider_inventory',{provider:'gemini'});
 assert.equal(unavailable.status,'http_403');
 const stored=await ops.status(env);
 assert.equal(stored.providers.find(p=>p.provider==='gemini').last_check.status,'http_403');
 assert.equal(db.prepare('SELECT count(*) AS n FROM ghost_cloud_provider_checks').get().n,1);
 assert.equal(seen,2);
 assert.equal(JSON.stringify(stored).includes('private upstream error body'),false);
});

test('fixed-endpoint GET inventory returns bounded public model metadata only',async()=>{
 const {env,ops}=setup();let calls=0;
 const result=await ops.inventory(env,'openrouter',async(url,opts)=>{calls++;assert.equal(url,'https://openrouter.ai/api/v1/models');assert.equal(opts.method,'GET');assert.equal(opts.redirect,'manual');return Response.json({data:[{id:'known/free:free',pricing:{prompt:'0',completion:'0'}},{id:'paid/model',pricing:{prompt:'1',completion:'1'}},{id:'unknown:free',pricing:{prompt:null,completion:null}}],secret:'must not return'});});
 assert.equal(calls,1);assert.deepEqual(result.models.map(m=>m.id),['known/free:free']);assert.equal(result.billing_verified,false);assert.equal(result.quota_verified,false);assert.ok(!JSON.stringify(result).includes('must not return'));
 await assert.rejects(ops.inventory(env,'https://attacker.invalid',async()=>{throw Error();}));
});
test('inventory errors do not leak key or vendor body',async()=>{
 const {env,ops}=setup();const result=await ops.inventory(env,'groq',async()=>new Response('sensitive upstream',{status:403}));
 assert.deepEqual(result,{provider:'groq',status:'http_403'});
});
test('MCP discovery adds cloud actions but no human-review writer',async()=>{
 const {env,ops}=setup();const r=await ops.fetch(request('/mcp',{body:{jsonrpc:'2.0',id:1,method:'tools/list'}}),env);const doc=await r.json();
 assert.equal(doc.result.tools.length,7);assert.ok(doc.result.tools.some(t=>t.name==='rovor_cloud_tick'));
 assert.ok(!doc.result.tools.some(t=>/review|pass|fail/.test(t.name)));
 const legacy=await ops.fetch(request('/mcp',{body:{jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'rovor_workforce_status',arguments:{period:'24h'}}}}),env);
 assert.equal((await legacy.json()).result.content.length,2);
});
test('actual module sources compile into executable ESM and preserve private base auth',async()=>{
 const code=compileOperations(baseSource,read('runtime.mjs'),read('worker.mjs'),read('canary-preflight.mjs'),read('site-operations.mjs'));
 const mod=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
 const {env}=setup();assert.equal((await mod.default.fetch(request('/api/ghost/status',{identity:null}),env)).status,401);
 const result=await (await mod.default.fetch(request('/api/ghost/status'),env)).json();assert.equal(result.providers.length,9);
 const html=await (await mod.default.fetch(request('/'),env)).text();assert.match(html,/Original HUD and logo/);assert.match(html,/CLOUD EMPLOYEES/);
 let scheduled=false;mod.default.scheduled({},env,{waitUntil(){scheduled=true;}});assert.equal(scheduled,false);
 assert.throws(()=>compileOperations(code,read('runtime.mjs'),read('worker.mjs'),read('canary-preflight.mjs'),read('site-operations.mjs')),/unexpected_base_site/);
});
test('composer preserves applied migrations, emits schema-only SQL and string DB binding',()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'rovor-operations-'));
 try{
  for(const name of ['.openai','dist/.openai','dist/server','worker','drizzle/meta'])fs.mkdirSync(path.join(dir,name),{recursive:true});
  fs.writeFileSync(path.join(dir,'.openai/hosting.json'),JSON.stringify({project_id:'appgprj_6add1e2cc8c08191839344b34d7dbf50',d1:'DB',capabilities:['mcp']}));
  for(const name of ['worker/index.js','dist/server/index.js'])fs.writeFileSync(path.join(dir,name),baseSource);
  const prior='CREATE TABLE existing_hud(id INTEGER);\n';fs.writeFileSync(path.join(dir,'drizzle/0000_hud.sql'),prior);
  fs.writeFileSync(path.join(dir,'drizzle/meta/_journal.json'),JSON.stringify({version:'7',dialect:'sqlite',entries:[{idx:0,tag:'0000_hud'}]}));
  assert.equal(composeOperations(dir).applied,false);assert.equal(fs.existsSync(path.join(dir,'drizzle/0001_cloud_operations.sql')),false);
  const result=composeOperations(dir,{apply:true});assert.equal(result.deployment_performed,false);
  assert.equal(JSON.parse(fs.readFileSync(path.join(dir,'dist/.openai/hosting.json'),'utf8')).d1,'DB');
  assert.equal(fs.readFileSync(path.join(dir,'drizzle/0000_hud.sql'),'utf8'),prior);
  const migration=fs.readFileSync(path.join(dir,'drizzle/0001_cloud_operations.sql'),'utf8');assert.match(migration,/statement-breakpoint/);assert.doesNotMatch(migration,/(^|\n)\s*(INSERT|UPDATE|DELETE|DROP|ALTER)\b/);
   assert.match(migration,/ghost_cloud_reviews \(id TEXT PRIMARY KEY,attempt_id TEXT NOT NULL UNIQUE REFERENCES ghost_cloud_attempts\(id\)/);
  const db=new DatabaseSync(':memory:');db.exec(migration);assert.equal(db.prepare('SELECT count(*) n FROM ghost_cloud_control').get().n,0);db.close();
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

test('forward-only review index repairs legacy schema and preserves first immutable decision',()=>{
 const schema=read('migrations/owner-review-one-decision.sql');
 const db=new DatabaseSync(':memory:');
 try{
  db.exec('CREATE TABLE ghost_cloud_attempts(id TEXT PRIMARY KEY);CREATE TABLE ghost_cloud_reviews(id TEXT PRIMARY KEY,attempt_id TEXT NOT NULL REFERENCES ghost_cloud_attempts(id),actor TEXT NOT NULL,verdict TEXT NOT NULL,output_sha256 TEXT NOT NULL,reviewed_at INTEGER NOT NULL)');
  const sql='INSERT INTO ghost_cloud_reviews(id,attempt_id,actor,verdict,output_sha256,reviewed_at) VALUES(?,?,?,?,?,?) ON CONFLICT(attempt_id) DO NOTHING';
  assert.throws(()=>db.prepare(sql),/ON CONFLICT clause/);
  db.exec(schema);
  db.prepare('INSERT INTO ghost_cloud_attempts VALUES(?)').run('attempt-1');
  const insert=db.prepare(sql);
  assert.equal(insert.run('review-pass','attempt-1','owner','passed','a'.repeat(64),1).changes,1);
  assert.equal(insert.run('review-fail','attempt-1','owner','failed','b'.repeat(64),2).changes,0);
  assert.equal(db.prepare('SELECT count(*) AS n FROM ghost_cloud_reviews').get().n,1);
  assert.deepEqual({...db.prepare('SELECT verdict,output_sha256 FROM ghost_cloud_reviews').get()},{verdict:'passed',output_sha256:'a'.repeat(64)});
  assert.doesNotThrow(()=>db.exec(schema));
 }finally{db.close();}
 const corrupted=new DatabaseSync(':memory:');
 try{
  corrupted.exec('CREATE TABLE ghost_cloud_attempts(id TEXT PRIMARY KEY);CREATE TABLE ghost_cloud_reviews(id TEXT PRIMARY KEY,attempt_id TEXT NOT NULL REFERENCES ghost_cloud_attempts(id),actor TEXT NOT NULL,verdict TEXT NOT NULL,output_sha256 TEXT NOT NULL,reviewed_at INTEGER NOT NULL)');
  corrupted.prepare('INSERT INTO ghost_cloud_attempts VALUES(?)').run('same');
  corrupted.prepare('INSERT INTO ghost_cloud_reviews VALUES(?,?,?,?,?,?)').run('one','same','owner','passed','a'.repeat(64),1);
  corrupted.prepare('INSERT INTO ghost_cloud_reviews VALUES(?,?,?,?,?,?)').run('two','same','owner','failed','b'.repeat(64),2);
  assert.throws(()=>corrupted.exec(schema),/UNIQUE constraint failed/);
  assert.equal(corrupted.prepare('SELECT count(*) AS n FROM ghost_cloud_reviews').get().n,2);
 }finally{corrupted.close();}
});

test('embedded HUD client hides stale agent cards after a failed or invalid live status request',async()=>{
 const s=setup();await completed(s);
 const page=await (await s.ops.fetch(request('/'),s.env)).text();
 const start=page.indexOf('<script>'),end=page.indexOf('</script>',start);
 const script=start>=0&&end>start?page.slice(start+8,end):null;
 assert.ok(script,'private HUD injects its live module');
 class Element {
  constructor(tag){this.tag=tag;this.id='';this.children=[];this.parent=null;this.textContent='';this.className='';this.style={};this.hidden=false;}
  append(...items){for(const item of items){item.remove();item.parent=this;this.children.push(item);}}
  prepend(...items){for(const item of items.reverse()){item.remove();item.parent=this;this.children.unshift(item);}}
  remove(){if(this.parent){const i=this.parent.children.indexOf(this);if(i>=0)this.parent.children.splice(i,1);this.parent=null;}}
  replaceWith(item){if(!this.parent)return;const parent=this.parent,i=parent.children.indexOf(this);item.remove();parent.children[i]=item;item.parent=parent;this.parent=null;}
 }
 const root=new Element('root'),workload=new Element('div'),activity=new Element('div');
 workload.id='workloadPanel';activity.id='activityPanel';root.append(workload,activity);
 const find=(node,id)=>node.id===id?node:node.children.map(child=>find(child,id)).find(Boolean)||null;
 const document={hidden:false,createElement:tag=>new Element(tag),getElementById:id=>find(root,id),addEventListener(){}};
 let tick,mode='ok',reads=0;const snapshot=await s.ops.status(s.env);
 const fetch=async()=>{reads++;if(mode==='offline')throw Error('network_down');
  if(mode==='invalid')return {ok:true,json:async()=>({providers:[],attempts:[]})};
  return {ok:true,json:async()=>snapshot};
 };
 vm.runInNewContext(script,{document,fetch,MutationObserver:class{observe(){}},setInterval:fn=>{tick=fn;},AbortSignal,console});
 const settled=()=>new Promise(resolve=>setImmediate(resolve));
 await settled();
 assert.equal(reads,1);
 assert.ok(document.getElementById('rovor-cloud-live'),'real status shows recorded receipts');
 assert.ok(document.getElementById('rovor-cloud-results'));
 const visible=(node)=>[node.textContent,...node.children.flatMap(visible)].join(' ');
 assert.match(visible(document.getElementById('rovor-cloud-results')),/OWNER REVIEW QUEUE · 1 PENDING/);
 assert.match(document.getElementById('rovor-cloud-link-state').textContent,/CLOUD LEDGER REACHABLE/);
 assert.match(document.getElementById('rovor-cloud-link-state').textContent,/reachability does not prove agents online/);
 mode='offline';await tick();await settled();
 assert.equal(document.getElementById('rovor-cloud-live'),null,'old agent cards disappear on connection loss');
 assert.equal(document.getElementById('rovor-cloud-results'),null,'old result cards disappear on connection loss');
 assert.match(document.getElementById('rovor-cloud-link-state').textContent,/CLOUD TELEMETRY OFFLINE/);
 mode='ok';await tick();await settled();assert.ok(document.getElementById('rovor-cloud-live'));
 mode='invalid';await tick();await settled();
 assert.equal(document.getElementById('rovor-cloud-results'),null,'malformed successful HTTP response fails closed');
 assert.match(document.getElementById('rovor-cloud-link-state').textContent,/cached AI activity hidden/);
});

test('approved packet, real dispatcher, returned usage and explicit owner review form a complete loop',async()=>{
 const s=setup(),now=Date.now();s.env.GHOST_APPROVED_JOBS=JSON.stringify([j]);
 s.env.GHOST_FLEET_CONFIG=JSON.stringify({groq:{enabled:true,model:'pinned-model',pool:'verified-pool',zero_cost:true,commercial_use:true,
  evidence_sha256:'a'.repeat(64),verified_at:now-1000,valid_until:now+3600000,canary_sha256:'b'.repeat(64),canary_at:now-500,
  requests_per_day:3,tokens_per_day:10000,min_interval_ms:1000,max_input_bytes:1000,max_output_tokens:128,roles:['Saul'],kinds:['research']}});
 let requests=0;s.cloud.tick=env=>runtime.tick(env,async()=>{requests++;return Response.json({model:'actual-upstream',choices:[{message:{content:'Specific reviewable output from the simulated provider.'},finish_reason:'stop'}],usage:{prompt_tokens:11,completion_tokens:13}});});
 await rpc(s.ops,s.env,'rovor_cloud_control',{enabled:true});await rpc(s.ops,s.env,'rovor_cloud_replenish');
 assert.equal((await rpc(s.ops,s.env,'rovor_cloud_tick')).dispatched,1);assert.equal(requests,1);
 const status=await rpc(s.ops,s.env,'rovor_cloud_workforce_status');assert.equal(status.attempts[0].human_review,'not_recorded');assert.equal(status.attempts[0].actual_model,'actual-upstream');assert.equal(status.attempts[0].tokens_output,13);
 assert.equal((await s.ops.fetch(request('/api/ghost/review',{body:{job_id:j.id,verdict:'passed'},browser:true}),s.env)).status,200);
 assert.equal((await s.ops.status(s.env)).attempts[0].human_review,'passed');
 await rpc(s.ops,s.env,'rovor_cloud_replenish');await rpc(s.ops,s.env,'rovor_cloud_tick');assert.equal(requests,1);
});

test('service route never performs inference or reads private status without independent service authorization',async()=>{
 const s=setup();s.env.GHOST_APPROVED_JOBS=JSON.stringify([j]);await s.ops.control(s.env,true);
 for(const operation of ['status','inventory','shift']){
  for(const options of [{},{identity:null},{serviceToken:s.env.GHOST_WRITER_TOKEN},{serviceToken:s.env.GHOST_READER_TOKEN},{serviceToken:'wrong'}]){
   const result=await s.ops.fetch(request('/api/ghost/service',{body:{operation},...options}),s.env);
   assert.equal(result.status,401,'unauthorized '+operation);
  }
 }
 assert.equal(s.db.prepare('SELECT COUNT(*) AS n FROM ghost_cloud_jobs').get().n,0);
 assert.equal(s.db.prepare('SELECT COUNT(*) AS n FROM ghost_cloud_attempts').get().n,0);
 const token=s.env.GHOST_SERVICE_TOKEN;
 assert.equal((await s.ops.fetch(request('/api/ghost/service',{identity:null,body:{operation:'status'},serviceToken:token}),s.env)).status,200);
 assert.equal((await s.ops.fetch(request('/api/ghost/service',{identity:null,body:{operation:'review'},serviceToken:token}),s.env)).status,400);
 delete s.env.GHOST_SERVICE_TOKEN;
 assert.equal((await s.ops.fetch(request('/api/ghost/service',{body:{operation:'shift'},serviceToken:token}),s.env)).status,401);
});
test('authenticated private service shift is still constrained by STOP and refuses review',async()=>{
 const s=setup();
 const r=await s.ops.fetch(request('/api/ghost/service',{identity:null,body:{operation:'shift'},serviceToken:s.env.GHOST_SERVICE_TOKEN}),s.env);
 assert.equal(r.status,200);
 const d=await r.json();assert.equal(d.intake.status,'stopped');
 assert.equal(s.db.prepare('SELECT count(*) n FROM ghost_cloud_attempts').get().n,0);
 assert.equal((await s.ops.fetch(request('/api/ghost/service',{identity:null,body:{operation:'review'},serviceToken:s.env.GHOST_SERVICE_TOKEN}),s.env)).status,400);
});
test('service credential must be distinct from reader and writer tokens',async()=>{
 const s=setup(),token=s.env.GHOST_SERVICE_TOKEN;
 for(const reused of [s.env.GHOST_READER_TOKEN,s.env.GHOST_WRITER_TOKEN]){
  s.env.GHOST_SERVICE_TOKEN=reused;
  assert.equal((await s.ops.fetch(request('/api/ghost/service',{body:{operation:'status'},serviceToken:reused}),s.env)).status,401);
 }
 s.env.GHOST_SERVICE_TOKEN=token;
 assert.equal((await s.ops.fetch(request('/api/ghost/service',{body:{operation:'status'},serviceToken:token}),s.env)).status,200);
});


test('cloud status exposes bounded read-only per-provider dispatch reasons',async()=>{
 const s=setup();
 const status=await s.ops.status(s.env);
 assert.equal(status.providers.length,9);
 assert.equal(status.providers.find(p=>p.provider==='groq').dispatch_gate.state,'ineligible');
 assert.equal(status.providers.find(p=>p.provider==='groq').dispatch_gate.reason,'not_configured');
 assert.equal(status.providers.find(p=>p.provider==='gemini').dispatch_gate.reason,'not_configured');
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM ghost_cloud_attempts').get().n,0);
 const html=await (await s.ops.fetch(request('/'),s.env)).text();
 assert.match(html,/current claim gate/);
 const serialized=JSON.stringify(status);
 assert.ok(!serialized.includes(s.env.GROQ_API_KEY));
 assert.ok(!serialized.includes(s.env.GHOST_WRITER_TOKEN));
 assert.ok(!serialized.includes('Inspect this public service offer.'));
});

test('hosted service shift uses the same canonical approved feeder as scheduled cron',async()=>{
 const s=setup();await s.ops.control(s.env,true);
 s.env.GHOST_APPROVED_JOBS=JSON.stringify([j]);
 s.env.GHOST_FEED_COMMIT='f'.repeat(40);
 await assert.rejects(s.ops.replenish(s.env),/canonical_feed_bundle_missing/);
 assert.equal(s.db.prepare('SELECT count(*) n FROM ghost_cloud_jobs').get().n,0);
 let called=0;
 s.ops.installApprovedFeeder({replenishApprovedJobs:async env=>{
  assert.equal(env,s.env);called++;return {status:'complete',queued:0,duplicates:0};
 }});
 assert.throws(()=>s.ops.installApprovedFeeder({replenishApprovedJobs:async()=>({queued:0})}),/canonical_feed_already_registered/);
 const response=await s.ops.fetch(request('/api/ghost/service',{
  body:{operation:'shift'},identity:null,serviceToken:s.env.GHOST_SERVICE_TOKEN
 }),s.env);
 assert.equal(response.status,200);
 const receipt=await response.json();
 assert.equal(receipt.intake.queued,0);
 assert.equal(receipt.result.dispatched,0);
 assert.equal(called,1);
 assert.equal(s.db.prepare('SELECT count(*) n FROM ghost_cloud_jobs').get().n,0,
  'spent fixed packets must not silently return on canonical feed path');
});

test('hosted authenticated service shifts use registered durable runner only',async()=>{
 const s=setup();await s.ops.control(s.env,true);
 let invoked=0;
 s.ops.installHostedShiftRunner(async env=>{
  assert.equal(env,s.env);invoked++;
  return {intake:{queued:0,duplicates:0},result:{enabled:true,dispatched:0,denied:{}},
    shift:{id:'hosted-shift-1',status:'idle',reason:'no_unattempted_jobs'},observed_at:Date.now()};
 });
 assert.throws(()=>s.ops.installHostedShiftRunner(async()=>({})),/hosted_shift_already_registered/);
 const operation={operation:'shift'};
 const denied=await s.ops.fetch(request('/api/ghost/service',{body:operation,identity:null}),s.env);
 assert.equal(denied.status,401);
 assert.equal(invoked,0);
 const ok=await s.ops.fetch(request('/api/ghost/service',{
  body:operation,identity:null,serviceToken:s.env.GHOST_SERVICE_TOKEN
 }),s.env);
 assert.equal(ok.status,200);
 const body=await ok.json();
 assert.equal(body.shift.status,'idle');
 assert.equal(body.shift.reason,'no_unattempted_jobs');
 assert.equal(body.result.dispatched,0);
 assert.equal(invoked,1);
});
