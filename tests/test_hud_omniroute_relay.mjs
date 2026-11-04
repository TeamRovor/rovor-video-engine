import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {handle} from '../integrations/hud-cloud/worker.mjs';
import {RELAY, cleanCatalog, cleanReply} from '../integrations/hud-cloud/omniroute-chat-relay.mjs';
import {eligibleModels,executeClaim,readEvents} from '../tools/hud_chat_relay_client.mjs';

const NOW=Date.parse('2026-11-04T05:00:00.000Z');
const READER='r'.repeat(48),WRITER='w'.repeat(48);
const MODEL='openrouter/example:free';
const body={model:MODEL,messages:[{role:'user',content:'Reply with exactly: hello'}],context:false};
const id='51b4eb65-578e-4e9c-83a9-34d578f15ed3';

function mockDB() {
  const sqlite=new DatabaseSync(':memory:');
  sqlite.exec(readFileSync(new URL('../integrations/hud-cloud/schema.sql',import.meta.url),'utf8'));
  return {
    sqlite,
    prepare(sql) { return {
      bind(...args) {
        return {
          first: async ()=>sqlite.prepare(sql).get(...args)??null,
          run: async ()=>({meta:{changes:sqlite.prepare(sql).run(...args).changes}}),
          all: async ()=>({results:sqlite.prepare(sql).all(...args)})
        };
      }
    }; }
  };
}
function request(path,method='GET',role='reader',payload=null,{origin=true}={}) {
  const headers={};
  if(role==='reader') headers.Cookie='rovor_hud_reader='+READER;
  if(role==='writer') headers.Authorization='Bearer '+WRITER;
  if(origin) headers.Origin='https://hud.test';
  if(payload!==null) headers['Content-Type']='application/json';
  return new Request('https://hud.test'+path,{method,headers,
    ...(payload!==null?{body:JSON.stringify(payload)}:{})});
}
const environment = () => ({DB:mockDB(),HUD_READER_TOKEN:READER,HUD_WRITER_TOKEN:WRITER});
const call=(env,path,method='GET',role='reader',payload=null,time=NOW,extra={})=>
  handle(request(path,method,role,payload,extra),env,time);

test('private relay refuses anonymous, cross-origin, and wrong-privilege requests',async()=>{
  const env=environment();
  assert.equal((await call(env,'/api/hud/chat/models','GET','none')).status,401);
  assert.equal((await call(env,'/api/hud/chat/bridge','POST','reader',{models:[MODEL]})).status,401);
  assert.equal((await call(env,'/api/hud/chat/claim','POST','reader',{})).status,401);
  assert.equal((await call(env,'/api/hud/chat/bridge','POST','writer',{models:[MODEL]})).status,200);
  assert.equal((await call(env,'/api/hud/chat/models')).status,200);
  assert.equal((await call(env,'/api/hud/chat/submit','POST','reader',body,NOW,{origin:false})).status,403);
  assert.equal((await call(env,'/api/hud/chat/submit','POST','writer',body)).status,401 /* writer cannot read/submit via reader token */);
  assert.equal((await call(env,'/api/hud/chat/claim','POST','none',{})).status,401);
});

test('complete chat relay roundtrip has a true receipt; no replay or forged completion',async()=>{
  const env=environment();
  const initial=await (await call(env,'/api/hud/chat/models')).json();
  assert.equal(initial.online,false);
  assert.deepEqual(initial.models,[]);
  assert.equal((await call(env,'/api/hud/chat/submit','POST','reader',body)).status,503);
  assert.equal((await call(env,'/api/hud/chat/bridge','POST','writer',{models:[MODEL]})).status,200);
  const catalog=await (await call(env,'/api/hud/chat/models')).json();
  assert.equal(catalog.online,true);assert.deepEqual(catalog.models,[MODEL]);
  const denied=await call(env,'/api/hud/chat/submit','POST','reader',{...body,model:'groq/paid-model'});
  assert.equal(denied.status,400);
  const accepted=await call(env,'/api/hud/chat/submit','POST','reader',body);
  assert.equal(accepted.status,202);
  const {job_id}=await accepted.json();
  assert.match(job_id,/^[0-9a-f-]{36}$/);
  let status=await (await call(env,'/api/hud/chat/status/'+job_id)).json();
  assert.equal(status.state,'queued');assert.equal(status.output,null);
  assert.equal((await call(env,'/api/hud/chat/result/'+job_id,'POST','writer',{state:'complete',output:'forged before claim'})).status,409);
  const claimed=await (await call(env,'/api/hud/chat/claim','POST','writer',{})).json();
  assert.equal(claimed.job.id,job_id);
  assert.deepEqual(claimed.job.request,body);
  status=await (await call(env,'/api/hud/chat/status/'+job_id)).json();
  assert.equal(status.state,'running');
  assert.equal((await call(env,'/api/hud/chat/result/'+job_id,'POST','reader',{state:'complete',output:'no'})).status,401);
  const done=await call(env,'/api/hud/chat/result/'+job_id,'POST','writer',{state:'complete',output:'hello'});
  assert.equal(done.status,200);
  status=await (await call(env,'/api/hud/chat/status/'+job_id)).json();
  assert.equal(status.state,'complete');assert.equal(status.output,'hello');
  assert.equal(status.model_attribution,'requested_model_only');
  assert.equal((await call(env,'/api/hud/chat/result/'+job_id,'POST','writer',{state:'complete',output:'replacement'})).status,409);
  assert.equal((await (await call(env,'/api/hud/chat/claim','POST','writer',{})).json()).job,null);
  const stored=env.DB.sqlite.prepare('SELECT request_body,output FROM hud_chat_jobs WHERE id=?').get(job_id);
  assert.equal(stored.request_body,null);assert.equal(stored.output,'hello');
});

test('stale or failed bridges do not advertise models or leave prompts indefinitely',async()=>{
  const env=environment();
  await call(env,'/api/hud/chat/bridge','POST','writer',{models:[MODEL]});
  assert.equal((await (await call(env,'/api/hud/chat/models','GET','reader',null,NOW+RELAY.heartbeatMs+1)).json()).online,false);
  const added=await call(env,'/api/hud/chat/submit','POST','reader',body);
  const {job_id}=await added.json();
  assert.equal((await (await call(env,'/api/hud/chat/status/'+job_id,'GET','reader',null,NOW+RELAY.queuedMs+5)).json()).state,'failed');
  assert.equal(env.DB.sqlite.prepare('SELECT request_body FROM hud_chat_jobs WHERE id=?').get(job_id).request_body,null);
  const later=await call(env,'/api/hud/chat/status/'+job_id,'GET','reader',null,NOW+RELAY.queuedMs+RELAY.retainMs+200);
  assert.equal(later.status,404);
});

test('relay validates unsafe catalogs and oversized/forged results',()=>{
  assert.deepEqual(cleanCatalog({models:[MODEL,MODEL]}),[MODEL]);
  for(const list of [[MODEL,'other?route'],Array(101).fill(MODEL)])assert.throws(()=>cleanCatalog({models:list}));
  assert.deepEqual(cleanReply({state:'complete',output:'ok'}),{state:'complete',output:'ok',error:null});
  assert.throws(()=>cleanReply({state:'complete',output:'x'.repeat(16001)}));
  assert.throws(()=>cleanReply({state:'failed',error:'internal_error'}));
});

test('Mac route selection requires explicit free IDs or owner allowlist',()=>{
  assert.deepEqual(eligibleModels([
    'openrouter/example:free','rovor-fast-free-v1','openrouter/example:free',
    'groq/some-model','openrouter/auto','invalid?model'
  ]),['openrouter/example:free']);
  assert(eligibleModels(['groq/some-model'],['groq/some-model']).includes('groq/some-model'));
  assert(eligibleModels(['rovor-fast-free-v1'],['rovor-fast-free-v1']).includes('rovor-fast-free-v1'));
  assert.equal(eligibleModels(['rovor-fast-free-v1']).length,0, 'combo names alone do not prove free-only routing');
  assert(!eligibleModels(['groq/some-model']).includes('groq/some-model'));
  assert.equal(eligibleModels(['groq/some-model'],['other']).length,0);
});

test('Mac cannot claim completed model inference unless it received real streaming content',async()=>{
  let calls=0,freed=0;
  const txt='data: {"choices":[{"delta":{"content":"Hello "}}]}\n\ndata: {"choices":[{"delta":{"content":"world"}}]}\n\ndata: [DONE]\n\n';
  const stream=new ReadableStream({start(controller){controller.enqueue(new TextEncoder().encode(txt));controller.close();}});
  const chat={respond:async()=>{calls++;return {status:200,stream,done:()=>freed++};}};
  const result=await executeClaim(chat,{id,model:MODEL,request:body},new AbortController().signal);
  assert.deepEqual(result,{state:'complete',output:'Hello world'});
  assert.equal(calls,1);assert.equal(freed,1);
  assert.deepEqual(await executeClaim(chat,{id,model:'different',request:body},new AbortController().signal),{state:'failed',error:'model_not_available'});
  assert.equal(calls,1);
  assert.equal(readEvents('data: {"choices":[{"delta":{"content":"hi"}}]}\n\ndata: [DONE]'),'hi');
});
