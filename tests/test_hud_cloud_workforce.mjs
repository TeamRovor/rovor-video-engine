import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {generateKeyPairSync} from 'node:crypto';
import {intake,control,status,draft,review,tick} from '../integrations/hud-cloud/approved-workforce.mjs';
import worker,{handle} from '../integrations/hud-cloud/worker.mjs';
import {verifyWorkforce} from '../integrations/hud-cloud/verify-cloud-workforce.mjs';
import {planOwnerSelectedPilot,checkOperatorContext} from '../tools/cloud_gemini_workforce_control.mjs';

const now=Date.parse('2026-11-11T02:05:00.000Z');
const model='gemini-3.5-flash-lite';
const writer='w'.repeat(40),reader='r'.repeat(40);
const job={id:'gc-new-reviewable-job-v2',task_id:'new-owner-approved-pilot',
 employee:'Saul',kind:'research',title:'Draft a small website service brief',
 prompt:'Write one short, specific public small-business website brief for owner review.',
 source_commit:'a'.repeat(40),data_class:'public_repository'};
const packet={approval:'trusted_canonical_owner_approval_v1',revision:'v2',job};
const origin='https://rovor.example';
function setup(){
 const db=new DatabaseSync(':memory:');
 db.exec(readFileSync(new URL('../integrations/hud-cloud/schema.sql',import.meta.url),'utf8'));
 const DB={prepare(sql){
  const stmt=db.prepare(sql);let args=[];
  const handle={bind(...values){args=values;return handle;},
   async first(){return stmt.get(...args)||null;},
   async all(){return {results:stmt.all(...args)};},
   async run(){const result=stmt.run(...args);return {meta:{changes:Number(result.changes)}};}};
  return handle;
 },async batch(statements){db.exec('BEGIN');try{
  const rows=[];for(const stmt of statements)rows.push(await stmt.run());
  db.exec('COMMIT');return rows;
 }catch(e){db.exec('ROLLBACK');throw e;}}};
 const env={DB,GEMINI_API_KEY:'g'.repeat(38),
  ROVOR_GEMINI_FREE_TIER_VERIFIED:'confirmed',
  HUD_READER_TOKEN:reader,HUD_WRITER_TOKEN:writer};
 return {db,DB,env};
}
function approved(s){
 s.db.prepare('INSERT INTO hud_gemini_model_health(model,last_success_at,success_count) VALUES(?,?,1)')
  .run(model,now-1000);
}
function google(sendCalls,upstream=200){
 return async (url,options)=>{
  sendCalls.push({url,method:options.method});
  assert.match(url,/^https:\/\/generativelanguage\.googleapis\.com\/v1beta\/models/);
  if(options.method==='GET')return Response.json({models:[
   {name:'models/'+model,supportedGenerationMethods:['generateContent']}
  ]});
  assert.equal(options.method,'POST');
  assert.match(url,new RegExp(model.replaceAll('.','\\.')+':generateContent$'));
  assert.equal(options.headers['x-goog-api-key'],'g'.repeat(38));
  if(upstream!==200)return new Response('',{status:upstream});
  return Response.json({candidates:[{finishReason:'STOP',content:{parts:[
   {text:'A concrete proposed website brief for owner review.'}]}}],
   usageMetadata:{promptTokenCount:18,candidatesTokenCount:12}});
 };
}
const jsonRequest=(path,token,method='GET',body=null)=>new Request(origin+path,{
 method,headers:{...(token?{Authorization:'Bearer '+token}:{}),
  ...(body?{'Content-Type':'application/json'}:{}),
  ...(path==='/api/hud/workforce/review'?{Origin:origin}:{})},
 body:body?JSON.stringify(body):undefined
});

test('STOP starts disabled, immutable canonical intake deduplicates, and public status hides prompts',async()=>{
 const s=setup();
 assert.equal((await status(s.DB)).body.enabled,false);
 assert.equal((await tick(s.env,now,()=>{throw Error('never call');})).body.state,'stopped');
 assert.equal((await intake(s.DB,{...packet,unknown:1},now)).status,400);
 assert.equal((await intake(s.DB,{...packet,revision:'v1'},now)).status,400,'already attempted v1 cannot be submitted');
 assert.equal((await intake(s.DB,{...packet,job:{...job,prompt:'A'.repeat(4001)}},now)).status,400);
 assert.equal((await intake(s.DB,packet,now)).status,201);
 assert.equal((await intake(s.DB,packet,now)).body.duplicate,true);
 assert.equal((await intake(s.DB,{...packet,job:{...job,title:'tampered'}},now)).status,409);
 assert.equal((await intake(s.DB,{...packet,revision:'v3'},now)).status,409);
 const overview=(await status(s.DB)).body;
 assert.equal(overview.items[0].state,'queued');
 assert.equal(overview.items[0].human_review,'not_recorded');
 assert.equal(overview.items[0].tokens_input,null);
 assert.equal(overview.items[0].tokens_output,null);
 assert(!JSON.stringify(overview).includes(job.prompt));
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM hud_cloud_workforce_jobs').get().n,1);
});

test('one real Gemini-model mock reply advances D1 and leaves exact private owner-review draft',async()=>{
 const s=setup();approved(s);
 await intake(s.DB,packet,now);await control(s.DB,true);
 const calls=[];
 const result=await tick(s.env,now,google(calls));
 assert.equal(result.status,200);
 assert.deepEqual({state:result.body.state,dispatched:result.body.dispatched,
  inference_completed:result.body.inference_completed},
 {state:'needs_review',dispatched:1,inference_completed:true});
 assert.equal(calls.filter(c=>c.method==='POST').length,1);
 const row=(await draft(s.DB,job.id)).body;
 assert.match(row.output,/concrete proposed website brief/);
 assert.match(row.output_sha256,/^[a-f0-9]{64}$/);
 assert.equal(row.human_review,'not_recorded');
 const usage=s.db.prepare('SELECT attempts,completed,input_tokens,output_tokens FROM hud_gemini_chat_model_usage WHERE model=?').get(model);
 assert.equal(usage.completed,1);
 assert.equal(usage.input_tokens,18);
 assert.equal(result.body.tokens_input,18);
 assert.equal(result.body.tokens_output,12);
 const exact=(await status(s.DB)).body.items.find(x=>x.id===job.id);
 assert.equal(exact.provider,'google-gemini-cloud');
 assert.equal(exact.requested_model,model);
 assert.equal(exact.tokens_input,18);
 assert.equal(exact.tokens_output,12);
 assert.equal(row.tokens_input,18);
 assert.equal(row.tokens_output,12);
 const exactRow=s.db.prepare('SELECT * FROM hud_cloud_workforce_usage WHERE job_id=?').get(job.id);
 assert.equal(exactRow.output_sha256,row.output_sha256);
 assert.equal(exactRow.actual_model,model);
 assert.equal((await tick(s.env,now+1000,google(calls))).body.dispatched,0);
 assert.equal(calls.filter(c=>c.method==='POST').length,1,'no completed-job replay');
 assert.equal((await review(s.DB,{job_id:job.id,verdict:'passed',output_sha256:'0'.repeat(64)},now+2400)).status,409);
 const first=await review(s.DB,{job_id:job.id,verdict:'passed',output_sha256:row.output_sha256},now+2500);
 assert.equal(first.body.human_review,'passed');
 assert.equal(first.body.output_sha256,row.output_sha256);
 assert.equal((await review(s.DB,{job_id:job.id,verdict:'failed',output_sha256:row.output_sha256},now+3500)).status,409);
 assert.equal((await draft(s.DB,job.id)).body.human_review,'passed');
});

test('unknown entitlement, missing canary and STOP cannot claim or spend',async()=>{
 const s=setup();await intake(s.DB,packet,now);
 await control(s.DB,true);
 const never=()=>{throw Error('no provider call allowed');};
 assert.equal((await tick(s.env,now,never)).body.state,'model_reply_evidence_missing');
 assert.equal(s.db.prepare('SELECT state FROM hud_cloud_workforce_jobs').get().state,'queued');
 approved(s);s.env.ROVOR_GEMINI_FREE_TIER_VERIFIED='unverified';
 assert.equal((await tick(s.env,now,never)).body.state,'free_tier_not_attested');
 await control(s.DB,false);
 assert.equal((await tick(s.env,now,never)).body.state,'stopped');
});

test('upstream 429 becomes a nonreplayed failed attempt; no invented completed draft',async()=>{
 const s=setup();approved(s);await intake(s.DB,packet,now);await control(s.DB,true);
 const calls=[];
 const result=await tick(s.env,now,google(calls,429));
 assert.equal(result.body.dispatched,1);
 assert.equal(result.body.state,'failed');
 assert.equal((await draft(s.DB,job.id)).body.output,null);
 assert.equal((await review(s.DB,{job_id:job.id,verdict:'passed',output_sha256:'0'.repeat(64)},now+10)).status,409);
 assert.equal((await tick(s.env,now+5000,google(calls))).body.dispatched,0);
 assert.equal(calls.filter(c=>c.method==='POST').length,1);
});

test('new workforce endpoints distinguish writer, reader and owner same-origin review',async()=>{
 const s=setup();
 assert.equal((await handle(jsonRequest('/api/hud/workforce/status',null),s.env,now)).status,401);
 assert.equal((await handle(jsonRequest('/api/hud/workforce/intake',reader,'POST',packet),s.env,now)).status,401);
 assert.equal((await handle(jsonRequest('/api/hud/workforce/intake',writer,'POST',packet),s.env,now)).status,201);
 assert.equal((await handle(jsonRequest('/api/hud/workforce/status',reader),s.env,now)).status,200);
 assert.equal((await handle(jsonRequest('/api/hud/workforce/draft/'+job.id,reader),s.env,now)).status,200);
 assert.equal((await handle(jsonRequest('/api/hud/workforce/review',writer,'POST',
  {job_id:job.id,verdict:'passed',output_sha256:'0'.repeat(64)}),s.env,now)).status,401);
 assert.equal((await handle(jsonRequest('/api/hud/workforce/review',reader,'POST',
  {job_id:job.id,verdict:'passed',output_sha256:'0'.repeat(64)}),s.env,now)).status,409);
 assert.equal((await handle(jsonRequest('/api/hud/workforce/control',reader,'POST',
  {enabled:true}),s.env,now)).status,401);
 assert.equal((await handle(jsonRequest('/api/hud/workforce/control',writer,'POST',
  {enabled:true}),s.env,now)).status,200);
});

test('existing native Cloudflare cron honors STOP and runs at most one approved Gemini job',async t=>{
 const s=setup();
 const calls=[];
 t.mock.method(globalThis,'fetch',google(calls));
 await intake(s.DB,packet,Date.now()-2000);
 // Cron is a no-op while STOP is closed, even with a queued job.
 const scheduledAt=Date.now()-1000;
 await worker.scheduled({scheduledTime:scheduledAt},s.env);
 const first=(await status(s.DB)).body.native_schedule.last_tick;
 assert.equal(first.scheduled_at,scheduledAt);
 assert.equal(first.result_state,'stopped');
 assert.equal(first.dispatch_reported,0);
 assert.equal(first.inference_completed,0);
 assert.equal(calls.length,0);
 assert.equal((await draft(s.DB,job.id)).body.state,'queued');
 s.db.prepare('INSERT INTO hud_gemini_model_health(model,last_success_at,success_count) VALUES(?,?,1)')
  .run(model,Date.now()-1000);
 await control(s.DB,true);
 await worker.scheduled({scheduledTime:scheduledAt+1},s.env);
 const result=(await draft(s.DB,job.id)).body;
 assert.equal(result.state,'needs_review');
 assert.match(result.output_sha256,/^[a-f0-9]{64}$/);
 assert.equal(calls.filter(x=>x.method==='POST').length,1);
 await worker.scheduled({scheduledTime:scheduledAt+2},s.env);
 assert.equal(calls.filter(x=>x.method==='POST').length,1,'cron never replays a completed task');
 const observed=(await status(s.DB)).body.native_schedule.recent_ticks;
 assert.equal(observed.length,3);
 const completion=observed.find(x=>x.inference_completed===1);
 assert.equal(completion.job_id,job.id);
 assert.equal(completion.result_state,'needs_review');
 assert.equal(completion.dispatch_reported,1);
 assert.equal(observed.filter(x=>x.dispatch_reported===1).length,1);
 assert(!JSON.stringify(observed).includes(job.prompt));
 assert(!JSON.stringify(observed).includes(result.output));
 await handle(jsonRequest('/api/hud/workforce/tick',writer,'POST'),s.env,Date.now(),google(calls));
 assert.equal((await status(s.DB)).body.native_schedule.recent_ticks.length,3,'manual tick never impersonates native clock');
 await control(s.DB,false);
});

test('new v2 business candidate remains unapproved in git, but an owner-selected dispatch scopes just its exact job',async()=>{
 const tasks=JSON.parse(readFileSync(new URL('../coordination/tasks.json',import.meta.url),'utf8'));
 const routing=JSON.parse(readFileSync(new URL('../coordination/work-routing.json',import.meta.url),'utf8'));
 const id='cloud-gemini-website-offer-pilot-20261110';
 const source=tasks.tasks.find(t=>t.id===id);
 assert.equal(source.cloud_inference.revision,'v2');
 assert.equal(source.cloud_inference.approved_for_cloud,false);
 const commit='c'.repeat(40);
 const selected=await planOwnerSelectedPilot(tasks,routing,commit,id,'v2');
 assert.equal(selected.employee,'Gus');
 assert.equal(selected.kind,'plan');
 assert.equal(selected.task_id,id);
 assert.equal(selected.source_commit,commit);
 assert.match(selected.id,/^gc-[a-f0-9]{48}$/);
 assert.equal(source.cloud_inference.approved_for_cloud,false,'no source-side approval mutation');
 await assert.rejects(()=>planOwnerSelectedPilot(tasks,routing,commit,id,'v1'),
   /new_unapproved_canonical_candidate_required/);
 await assert.rejects(()=>planOwnerSelectedPilot(tasks,routing,commit,'saul-cloud-inquiry-copy-20261025','v1'),
   /new_unapproved_canonical_candidate_required/);
 assert.equal(await checkOperatorContext({GITHUB_REPOSITORY:'TeamRovor/rovor-video-engine',
  GITHUB_REF:'refs/heads/main',GITHUB_EVENT_NAME:'workflow_dispatch',
  ROVOR_HUD_READER_TOKEN:reader,ROVOR_HUD_WRITER_TOKEN:writer}),true);
 await assert.rejects(()=>checkOperatorContext({GITHUB_REPOSITORY:'TeamRovor/rovor-video-engine',
  GITHUB_REF:'refs/heads/main',GITHUB_EVENT_NAME:'push',
  ROVOR_HUD_READER_TOKEN:reader,ROVOR_HUD_WRITER_TOKEN:writer}),
  /owner_workflow_requires_trusted_main_dispatch/);
});

test('persistent STOP flipped after atomic claim prevents upstream Gemini request and never replays',async()=>{
 const s=setup();
 approved(s);await intake(s.DB,packet,now);await control(s.DB,true);
 const original=s.DB.prepare.bind(s.DB);
 let stoppedAfterClaim=false;
 s.DB.prepare=sql=>{
  const statement=original(sql);
  if(!sql.startsWith("UPDATE hud_cloud_workforce_jobs SET state='running'"))return statement;
  return {bind(...values){
   const bound=statement.bind(...values);
   return {...bound,async first(){
    const row=await bound.first();
    if(row){s.db.prepare('UPDATE hud_cloud_workforce_control SET enabled=0 WHERE id=1').run();
      stoppedAfterClaim=true;}
    return row;
   }};
  }};
 };
 const never=()=>{throw Error('STOP must prevent upstream inference');};
 const attempt=await tick(s.env,now,never);
 assert.equal(stoppedAfterClaim,true);
 assert.equal(attempt.status,200);
 assert.equal(attempt.body.state,'stopped_after_claim');
 assert.equal(attempt.body.dispatched,0);
 assert.equal(s.db.prepare('SELECT state FROM hud_cloud_workforce_jobs WHERE id=?').get(job.id).state,'failed');
 assert.equal(s.db.prepare('SELECT error_code FROM hud_cloud_workforce_jobs WHERE id=?').get(job.id).error_code,'stopped_after_claim');
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM hud_gemini_chat_model_usage').get().n,0);
 await control(s.DB,true);
 const second=await tick(s.env,now+1000,never);
 assert.equal(second.body.dispatched,0,'STOP-aborted job is permanently consumed');
});

test('GitHub owner pilot form pre-fills only a new unapproved candidate and never defaults to inference',()=>{
 const workflow=readFileSync(new URL('../.github/workflows/cloud-gemini-workforce.yml',import.meta.url),'utf8');
 assert.match(workflow,/task_id:[\s\S]*?default: cloud-gemini-website-offer-pilot-20261110/);
 assert.match(workflow,/revision:[\s\S]*?default: v2/);
 assert.match(workflow,/action:[\s\S]*?default: status/);
 assert.match(workflow,/confirm_owner_approval:[\s\S]*?default: false/);
 const operator=readFileSync(new URL('../tools/cloud_gemini_workforce_control.mjs',import.meta.url),'utf8');
 assert.match(operator,/available_unapproved_candidates:ownerCandidates/);
 assert.match(operator,/requires_explicit_owner_selection:true/);
});


test('standing plan requires separate owner PASS, then native ticks refill fresh GitHub work without manual launches',async()=>{
 const s=setup(),commit='b'.repeat(40);
 approved(s);
 // A writer cannot arm a recurring plan using a one-shot permit alone.
 assert.equal((await control(s.DB,true,commit,now)).status,409);
 assert.equal((await status(s.DB)).body.enabled,false);
 await intake(s.DB,packet,now-2000);
 await control(s.DB,true);
 const pilotCalls=[];
 await tick(s.env,now,google(pilotCalls));
 const completed=(await draft(s.DB,job.id)).body;
 assert.equal(completed.state,'needs_review');
 await control(s.DB,false);
 assert.equal((await control(s.DB,true,commit,now+1000)).status,409);
 assert.equal((await review(s.DB,{job_id:job.id,verdict:'passed',
  output_sha256:completed.output_sha256},now+1000)).status,200);
 const started=await control(s.DB,true,commit,now+2000);
 assert.equal(started.status,200);
 assert.equal(started.body.recurring_authorized,true);
 assert.equal(started.body.expires_at,now+2000+7*86400000);
 // Trusted discovery records contain untrusted text; never send that body
 // to Gemini, and never permit a proposal to decide its own approval.
 const insert=s.db.prepare(`INSERT INTO hud_auto_discovery_inbox
   (id,discovery_key,day_id,created_at,content,priority,state)
   VALUES (?,?,?,?,?,?,'pending_review')`);
 insert.run('disc-1','run-1234',Math.floor(now/86400000),now,
  'untrusted discovery text: NEVER SEND TO MODEL',95);
 insert.run('disc-2','issue-1235',Math.floor(now/86400000),now,
  'private data must never be copied',75);
 insert.run('disc-stale','run-9999',Math.floor(now/86400000)-3,now-3*86400000,
  'stale evidence',100);
 const calls=[],githubCalls=[];
 const pem=generateKeyPairSync('rsa',{modulusLength:2048}).privateKey.export({type:'pkcs1',format:'pem'});
 Object.assign(s.env,{ROVOR_GITHUB_APP_ID:'123',ROVOR_GITHUB_INSTALLATION_ID:'456',
  ROVOR_GITHUB_APP_PRIVATE_KEY:pem});
 const send=async(url,options)=>{
   if(url.startsWith('https://api.github.com/')){
    githubCalls.push(url);assert.equal(options.redirect,'manual');
    if(url.endsWith('/access_tokens'))return Response.json({
     token:'test-scoped-installation-token-123456789',
     permissions:{contents:'read',issues:'read',pull_requests:'read',actions:'read',metadata:'read'},
     expires_at:new Date(now+1800000).toISOString()
    },{status:201});
    assert.equal(options.method,'GET');
    if(url.endsWith('/actions/runs/1234'))return Response.json({
     id:1234,name:'Expected CI',head_branch:'main',event:'workflow_dispatch',
     conclusion:'failure',status:'completed',created_at:new Date(now-1000).toISOString()
    });
    if(url.endsWith('/issues/1235'))return Response.json({
     number:1235,state:'open',labels:[{name:'bug'}],assignees:[],title:'Bounded issue'
    });
    throw Error('unexpected GitHub fetch');
   }
   if(options.method==='POST'){
    assert(!options.body.includes('NEVER SEND TO MODEL'));
    assert(!options.body.includes('private data must never be copied'));
    assert.match(options.body,/ROVOR verified GitHub discovery/);
    assert.match(options.body,/You cannot browse this URL/);
   }
   return google(calls)(url,options);
 };
 const first=await tick(s.env,now+61000,send);
 assert.equal(first.body.state,'needs_review');
 assert.match(first.body.id,/^gc-rec-[a-f0-9]{48}$/);
 const saved=s.db.prepare('SELECT * FROM hud_cloud_workforce_jobs WHERE id=?').get(first.body.id);
 assert.equal(saved.task_id,'cloud-discovery-run-1234');
 assert.equal(saved.employee,'Mike');
 assert.equal(saved.source_commit,commit);
 assert.equal(saved.human_review,'not_recorded');
 assert.match(saved.prompt,/actions\/runs\/1234/);
 assert(!saved.prompt.includes('NEVER SEND TO MODEL'));
 const next=await tick(s.env,now+121000,send);
 assert.equal(next.body.state,'needs_review');
 assert.notEqual(next.body.id,first.body.id);
 assert.equal(s.db.prepare('SELECT task_id FROM hud_cloud_workforce_jobs WHERE id=?').get(next.body.id).task_id,
  'cloud-discovery-issue-1235');
 const noMore=await tick(s.env,now+181000,send);
 assert.equal(noMore.body.dispatched,0);
 assert.equal(calls.filter(c=>c.method==='POST').length,2);
 assert.equal(githubCalls.length,4,'each discovery uses one scoped token and one fixed metadata read');
 assert.equal(s.db.prepare("SELECT COUNT(*) n FROM hud_cloud_workforce_jobs WHERE id LIKE 'gc-rec-%'").get().n,2);
 // STOP disarms standing approval; new discoveries cannot run on a transient
 // one-shot permit. The consumed discovery keys remain immutable.
 await control(s.DB,false);
 assert.equal(s.db.prepare('SELECT active FROM hud_cloud_workforce_series WHERE id=1').get().active,0);
 insert.run('disc-3','pr-2345',Math.floor(now/86400000),now+180000,'new evidence',55);
 await control(s.DB,true);
 const stoppedSeries=await tick(s.env,now+241000,send);
 assert.equal(stoppedSeries.body.dispatched,0);
 assert.equal(s.db.prepare("SELECT COUNT(*) n FROM hud_cloud_workforce_jobs WHERE id LIKE 'gc-rec-%'").get().n,2);
});

test('expired standing plan automatically closes STOP gate before dispatch',async()=>{
 const s=setup();
 approved(s);
 await intake(s.DB,packet,now);
 await control(s.DB,true);
 await tick(s.env,now,google([]));
 const completed=(await draft(s.DB,job.id)).body;
 await control(s.DB,false);
 await review(s.DB,{job_id:job.id,verdict:'passed',
  output_sha256:completed.output_sha256},now+1000);
 const armed=await control(s.DB,true,'c'.repeat(40),now+2000);
 assert.equal(armed.status,200);
 const calls=[];
 const expired=await tick(s.env,armed.body.expires_at,google(calls));
 assert.equal(expired.body.state,'standing_approval_expired');
 assert.equal(expired.body.dispatched,0);
 assert.equal(calls.length,0);
 assert.equal((await status(s.DB)).body.enabled,false);
 assert.equal(s.db.prepare('SELECT active FROM hud_cloud_workforce_series WHERE id=1').get().active,0);
});

test('writer-only control requires pinned source and owner PASS for standing approval',async()=>{
 const s=setup();
 const body={enabled:true,recurring_source_commit:'c'.repeat(40)};
 assert.equal((await handle(jsonRequest('/api/hud/workforce/control',reader,'POST',body),s.env,now)).status,401);
 const rejected=await handle(jsonRequest('/api/hud/workforce/control',writer,'POST',body),s.env,now);
 assert.equal(rejected.status,409);
 assert.equal((await handle(jsonRequest('/api/hud/workforce/control',writer,'POST',
  {...body,recurring_source_commit:'main'}),s.env,now)).status,400);
});

test('historical and failed workforce jobs never inherit aggregate provider token counts',async()=>{
 const s=setup();approved(s);
 await intake(s.DB,packet,now);
 s.db.prepare("UPDATE hud_cloud_workforce_jobs SET state='needs_review',actual_model=?,output_sha256=? WHERE id=?").run(model,'a'.repeat(64),job.id);
 s.db.prepare('INSERT INTO hud_gemini_chat_usage(day,completed,input_tokens,output_tokens) VALUES(?,1,1000,2000)').run('2026-11-11');
 const historical=(await status(s.DB)).body.items[0];
 assert.equal(historical.tokens_input,null);
 assert.equal(historical.tokens_output,null);
 assert.equal(historical.provider,null);
 assert.equal((await draft(s.DB,job.id)).body.tokens_input,null);
});

test('production verifier distinguishes actual scheduled inference from historical manual receipts and identifies observed limits',async()=>{
 const makeJob=(id,started,review='not_recorded')=>({id,state:'needs_review',human_review:review,
   provider:'google-gemini-cloud',requested_model:model,actual_model:model,output_sha256:'a'.repeat(64),
   tokens_input:10,tokens_output:20,started_at:started,finished_at:started+100});
 const native=makeJob('gc-native',now-1000),manual=makeJob('gc-manual',now-2000,'passed');
 const missing=makeJob('gc-no-receipt',now-3000);delete missing.output_sha256;
 const event={scheduled_at:now-1100,started_at:now-1100,finished_at:now-800,result_state:'needs_review',
  http_status:200,dispatch_reported:1,job_id:native.id,inference_completed:1};
 const idle={...event,scheduled_at:now-500,started_at:now-500,finished_at:now-400,result_state:'idle_or_safety_limited',dispatch_reported:0,job_id:null,inference_completed:0};
 const body={source:'existing_cloudflare_hud_gemini_workforce',mac_required:false,enabled:true,configured_model:model,
  site_review_ledger_synced:false,recurring_execution_authorized:true,
  standing_plan:{max_attempts_per_rolling_day:3,max_pending_reviews:2},items:[native,manual,missing],
  native_schedule:{source:'cloudflare_scheduled_event',last_tick:idle,recent_ticks:[idle,event,{...event,job_id:missing.id}]}};
 const mock=async(url,init)=>init.method==='POST'||!init.headers.Authorization?new Response(null,{status:401}):Response.json(body);
 const proof=await verifyWorkforce({token:reader,send:mock,now});
 assert.equal(proof.exact_job_token_receipts,2);assert.equal(proof.native_inference_receipts_matched,1);
 assert.equal(proof.last_native_inference_completed,false);assert.equal(proof.inference_proven_by_this_read,false);
 assert.deepEqual(proof.admission_snapshot.observed_constraints,['rolling_day_attempt_limit','pending_review_limit','no_queued_job']);
 assert.equal(proof.admission_snapshot.oldest_observed_attempt_expires_at,new Date(now-3000+86400000).toISOString());
 assert(!JSON.stringify(proof).includes(native.id));
});


test('read-only private workforce admission shows exact D1 limits, reset and fresh discovery without claiming model eligibility',async()=>{
 const s=setup();
 await control(s.DB,true);
 for(let i=0;i<3;i++){
  const item={...job,id:'gc-admission-'+i,task_id:'admission-'+i};
  assert.equal((await intake(s.DB,{...packet,job:item},now)).status,201);
  s.db.prepare("UPDATE hud_cloud_workforce_jobs SET state='failed',started_at=?,finished_at=?,error_code='test_only' WHERE id=?")
   .run(now-5000+i*1000,now-4900+i*1000,item.id);
 }
 let result=(await status(s.DB,now)).body;
 assert.equal(result.admission.rolling_day_attempts,3);
 assert.equal(result.admission.queued_jobs,0);
 assert.equal(result.admission.fresh_unattempted_discoveries,0);
 assert.equal(result.admission.earliest_rolling_slot_at,now-5000+86400000);
 assert.deepEqual(result.admission.observed_constraints,[
  'standing_authorization_inactive','rolling_day_attempt_limit','no_queued_job','no_fresh_unattempted_discovery']);
 assert.equal(result.admission.provider_admission_verified_by_this_read,false);
 const discovery='run-999991';
 s.db.prepare("INSERT INTO hud_auto_discovery_inbox(id,discovery_key,day_id,created_at,content,priority,state) VALUES(?,?,?,?,?,?,'pending_review')")
  .run('00000000-0000-4000-8000-000000000001',discovery,Math.floor(now/86400000),now,
    '[ROVOR-DISCOVERY:'+discovery+'] verified main failure',90);
 result=(await status(s.DB,now)).body;
 assert.equal(result.admission.fresh_unattempted_discoveries,1);
 assert(!result.admission.observed_constraints.includes('no_fresh_unattempted_discovery'));
 assert(!JSON.stringify(result).includes('GEMINI_API_KEY'));
 result=(await status(s.DB,now+86400001)).body;
 assert.equal(result.admission.rolling_day_attempts,0);
 assert.equal(result.admission.earliest_rolling_slot_at,null);
 assert(!result.admission.observed_constraints.includes('rolling_day_attempt_limit'));
});

test('stale GitHub issue is discarded before any Gemini tokens, remains consumed after START',async()=>{
 const s=setup();approved(s);await control(s.DB,true);
 s.db.prepare(`INSERT INTO hud_cloud_workforce_jobs
  (id,task_id,employee,kind,title,prompt,source_commit,revision,created_at,state,human_review)
  VALUES(?,?,?,?,?,?,?,?,?,'queued','not_recorded')`)
  .run('gc-rec-stale-issue','cloud-discovery-issue-2345','Mike','code_review',
  'Old issue investigation','Only numeric issue context','a'.repeat(40),'v2',now);
 const pem=generateKeyPairSync('rsa',{modulusLength:2048}).privateKey.export({type:'pkcs1',format:'pem'});
 Object.assign(s.env,{ROVOR_GITHUB_APP_ID:'123',ROVOR_GITHUB_INSTALLATION_ID:'456',ROVOR_GITHUB_APP_PRIVATE_KEY:pem});
 let github=0,provider=0;
 const send=async(url,options)=>{
  if(url.startsWith('https://generativelanguage.googleapis.com')){provider++;throw Error('stale work must not infer');}
  github++;
  if(url.endsWith('/access_tokens'))return Response.json({
   token:'mock-installation-token-safely-scoped',expires_at:new Date(now+3600000).toISOString(),
   permissions:{contents:'read',issues:'read',pull_requests:'read',actions:'read',metadata:'read'}
  },{status:201});
  assert(url.endsWith('/issues/2345'));
  assert.equal(options.method,'GET');
  return Response.json({number:2345,title:'Closed issue',state:'closed'});
 };
 const checked=await tick(s.env,now+1000,send);
 assert.equal(checked.body.state,'discovery_no_longer_actionable');assert.equal(checked.body.dispatched,0);
 assert.equal(checked.body.inference_completed,false);
 assert.equal(provider,0);assert.equal(github,2);
 const receipt=s.db.prepare("SELECT state,started_at,error_code FROM hud_cloud_workforce_jobs WHERE id='gc-rec-stale-issue'").get();
 assert.equal(receipt.state,'failed');assert.equal(receipt.started_at,null);
 assert.equal(receipt.error_code,'discovery_no_longer_actionable');
 assert.equal((await tick(s.env,now+2000,async()=>{throw Error('never replay');})).body.state,'idle_or_safety_limited');
});
test('GitHub timeout or missing App leaves the queued job and daily inference budget intact',async()=>{
 const s=setup();approved(s);await control(s.DB,true);
 s.db.prepare(`INSERT INTO hud_cloud_workforce_jobs
  (id,task_id,employee,kind,title,prompt,source_commit,revision,created_at,state,human_review)
  VALUES(?,?,?,?,?,?,?,?,?,'queued','not_recorded')`)
  .run('gc-rec-unverified-issue','cloud-discovery-issue-2346','Mike','code_review',
  'Issue review','Only numeric issue context','a'.repeat(40),'v2',now);
 let network=0;
 const missing=await tick(s.env,now+1000,async()=>{network++;throw Error('never call without app');});
 assert.equal(missing.body.state,'discovery_source_unverified');
 assert.equal(network,0);
 const pem=generateKeyPairSync('rsa',{modulusLength:2048}).privateKey.export({type:'pkcs1',format:'pem'});
 Object.assign(s.env,{ROVOR_GITHUB_APP_ID:'123',ROVOR_GITHUB_INSTALLATION_ID:'456',ROVOR_GITHUB_APP_PRIVATE_KEY:pem});
 const outage=await tick(s.env,now+2000,async(url)=>{network++;throw Error('simulated GitHub network outage');});
 assert.equal(outage.body.state,'discovery_source_unverified');
 assert.equal(outage.body.dispatched,0);assert.equal(outage.body.inference_completed,false);
 assert.equal(network,1);
 const row=s.db.prepare("SELECT state,started_at,finished_at FROM hud_cloud_workforce_jobs WHERE id='gc-rec-unverified-issue'").get();
 assert.equal(row.state,'queued');assert.equal(row.started_at,null);assert.equal(row.finished_at,null);
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM hud_cloud_workforce_jobs WHERE started_at IS NOT NULL').get().n,0);
});
