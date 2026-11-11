import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {intake,control,status,draft,review,tick} from '../integrations/hud-cloud/approved-workforce.mjs';
import {handle} from '../integrations/hud-cloud/worker.mjs';

const now=Date.parse('2026-11-11T02:05:00.000Z');
const model='gemini-3.5-flash-lite';
const writer='w'.repeat(40),reader='r'.repeat(40);
const job={id:'gc-new-reviewable-job-v2',task_id:'new-owner-approved-pilot',
 employee:'Saul',kind:'research',title:'Draft a small website service brief',
 prompt:'Write one short, specific public small-business website brief for owner review.',
 source_commit:'a'.repeat(40),data_class:'public_repository'};
const packet={approval:'trusted_canonical_owner_approval_v1',job};
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
 assert.equal((await intake(s.DB,{...packet,job:{...job,prompt:'A'.repeat(4001)}},now)).status,400);
 assert.equal((await intake(s.DB,packet,now)).status,201);
 assert.equal((await intake(s.DB,packet,now)).body.duplicate,true);
 assert.equal((await intake(s.DB,{...packet,job:{...job,title:'tampered'}},now)).status,409);
 const overview=(await status(s.DB)).body;
 assert.equal(overview.items[0].state,'queued');
 assert.equal(overview.items[0].human_review,'not_recorded');
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
 assert.equal((await tick(s.env,now+1000,google(calls))).body.dispatched,0);
 assert.equal(calls.filter(c=>c.method==='POST').length,1,'no completed-job replay');
 const first=await review(s.DB,{job_id:job.id,verdict:'passed'},now+2500);
 assert.equal(first.body.human_review,'passed');
 assert.equal(first.body.output_sha256,row.output_sha256);
 assert.equal((await review(s.DB,{job_id:job.id,verdict:'failed'},now+3500)).status,409);
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
 assert.equal((await review(s.DB,{job_id:job.id,verdict:'passed'},now+10)).status,409);
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
  {job_id:job.id,verdict:'passed'}),s.env,now)).status,401);
 assert.equal((await handle(jsonRequest('/api/hud/workforce/review',reader,'POST',
  {job_id:job.id,verdict:'passed'}),s.env,now)).status,409);
 assert.equal((await handle(jsonRequest('/api/hud/workforce/control',reader,'POST',
  {enabled:true}),s.env,now)).status,401);
 assert.equal((await handle(jsonRequest('/api/hud/workforce/control',writer,'POST',
  {enabled:true}),s.env,now)).status,200);
});
