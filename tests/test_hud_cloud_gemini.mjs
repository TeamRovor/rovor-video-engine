import {test} from 'node:test';
import assert from 'node:assert/strict';
import {cloudGeminiChat,cloudGeminiModels,validateGeminiChat,cloudGeminiUsage} from '../integrations/hud-cloud/cloud-gemini-chat.mjs';
import {handle} from '../integrations/hud-cloud/worker.mjs';

const key='g'.repeat(38),READER='r'.repeat(40),WRITER='w'.repeat(40);
const model='gemini-3.1-flash-lite',origin='https://hud.test';
function db(){
  const counts=new Map(),usage=new Map();
  return {prepare(sql){
    return {bind(...args){
      return {
        async first(){
          if(sql.includes('hud_gemini_chat_budget')&&sql.includes('RETURNING')){
            const [bucket,max]=args;
            const count=counts.get(bucket)||0;
            if(count>=max)return null;
            counts.set(bucket,count+1);
            return {attempts:count+1};
          }
          if(sql.includes('SELECT attempts FROM hud_gemini_chat_budget'))
            return {attempts:counts.get(args[0])||0};
          if(sql.includes('SELECT completed,input_tokens,output_tokens FROM hud_gemini_chat_usage'))
            return usage.get(args[0])||null;
          return null;
        },
        async run(){
          if(sql.includes('hud_gemini_chat_usage')){
            const [day,input,output]=args;
            const previous=usage.get(day)||{completed:0,input_tokens:0,output_tokens:0};
            usage.set(day,{completed:previous.completed+1,
              input_tokens:previous.input_tokens+input,output_tokens:previous.output_tokens+output});
          }
          return {meta:{changes:1}};
        }
      };
    }};
  }};
}
const env=()=>({GEMINI_API_KEY:key,ROVOR_GEMINI_FREE_TIER_VERIFIED:'confirmed',DB:db()});
const body={model,messages:[{role:'user',content:'Say hello'}]};
const googleResult=()=>Response.json({candidates:[{content:{parts:[{text:'Hello via Google'}]},finishReason:'STOP'}],
  usageMetadata:{promptTokenCount:8,candidatesTokenCount:4}});

test('Cloud Google Gemini stays disabled without key AND free-tier confirmation',()=>{
  assert.equal(cloudGeminiModels({}).online,false);
  assert.deepEqual(cloudGeminiModels({GEMINI_API_KEY:key}).models,[]);
  assert.deepEqual(cloudGeminiModels(env()).models,[model]);
  assert.equal(cloudGeminiModels(env()).mac_required,false);
});
test('Only single fixed direct model and bounded text conversations accepted',()=>{
  assert.equal(validateGeminiChat(body)[0].role,'user');
  for(const wrong of ['@cf/google/gemma-3-12b-it','gemini-3.1-pro-preview',
    'rovor-fast-free-v1','gemini-2.5-flash-lite'])
    assert.throws(()=>validateGeminiChat({...body,model:wrong}),/invalid_gemini_chat/);
  assert.throws(()=>validateGeminiChat({...body,messages:[{role:'user',content:'x'.repeat(4001)}]}),/invalid/);
});
test('Cloud chat sends one Google request, no Mac, records tokens and emits completed SSE',async()=>{
  const e=env();let calls=0;
  const send=async(url,init)=>{
    calls++;assert.equal(url,'https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent');
    assert.equal(init.headers['x-goog-api-key'],key);
    const doc=JSON.parse(init.body);
    assert.equal(doc.contents[0].role,'user');assert(!JSON.stringify(doc).includes('tools'));
    return googleResult();
  };
  const r=await cloudGeminiChat(body,e,Date.parse('2026-11-09T06:00:00Z'),send);
  assert.equal(r.status,200);
  assert.equal(r.headers.get('X-ROVOR-Provider'),'google-gemini-cloud');
  assert.match(await r.text(),/data: \[DONE\]/);
  assert.equal(calls,1);
  const usage=await cloudGeminiUsage(e,Date.parse('2026-11-09T06:00:00Z'));
  const j=await usage.json();assert.equal(j.completed,1);
  assert.equal(j.input_tokens,8);assert.equal(j.output_tokens,4);
});
test('D1 minute cap refuses third call without provider inference',async()=>{
  const e=env();let calls=0;
  const send=async()=>{calls++;return googleResult();};
  for(let i=0;i<3;i++) {
    const r=await cloudGeminiChat(body,e,Date.parse('2026-11-09T06:00:00Z')+i*1000,send);
    assert.equal(r.status,i<2?200:429);
  }
  assert.equal(calls,2);
});
test('No retries when Google returns 429, no invented completion',async()=>{
  const r=await cloudGeminiChat(body,env(),Date.parse('2026-11-09T06:00:00Z'),async()=>new Response('',{status:429}));
  assert.equal(r.status,429);assert.equal((await r.json()).error,'gemini_provider_rate_limited');
});
test('Existing HUD denies anonymous access and cross-site Gemini prompts',async()=>{
  const e={...env(),HUD_READER_TOKEN:READER,HUD_WRITER_TOKEN:WRITER};
  const get=(path,headers={})=>new Request(origin+path,{headers});
  const post=(o,headers={})=>new Request(origin+'/api/hud/gemini/chat',{
    method:'POST',headers:{Authorization:'Bearer '+READER,'Content-Type':'application/json',Origin:o,...headers},
    body:JSON.stringify(body)});
  assert.equal((await handle(get('/api/hud/gemini/models'),e)).status,401);
  assert.equal((await handle(get('/api/hud/gemini/models',{Authorization:'Bearer '+READER}),e)).status,200);
  assert.equal((await handle(post('https://evil.test'),e)).status,403);
  assert.equal((await handle(post(origin,{Authorization:'Bearer wrong'}),e)).status,401);
});
