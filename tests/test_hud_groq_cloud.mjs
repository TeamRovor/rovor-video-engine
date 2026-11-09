import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {handle} from '../integrations/hud-cloud/worker.mjs';
import {groqCloudReady,GROQ_CLOUD_ROUTE} from '../integrations/hud-cloud/groq-cloud-chat.mjs';
const NOW=Date.parse('2026-11-09T04:00:00Z');
const R='r'.repeat(48),W='w'.repeat(48);
function db(){
  const sqlite=new DatabaseSync(':memory:');
  sqlite.exec(readFileSync(new URL('../integrations/hud-cloud/schema.sql',import.meta.url),'utf8'));
  return {prepare(sql){return{bind(...a){return{
    first:async()=>sqlite.prepare(sql).get(...a)??null,
    run:async()=>({meta:{changes:sqlite.prepare(sql).run(...a).changes}})
  }} }}};
}
function env(ready=true){
  return {DB:db(),HUD_READER_TOKEN:R,HUD_WRITER_TOKEN:W,
    ...(ready?{
      GROQ_HUD_CHAT_ENABLED:'true',GROQ_HUD_FREE_TIER_VERIFIED:'true',
      GROQ_HUD_API_KEY:'mock-private-key-more-than-sixteen',
      GROQ_HUD_EVIDENCE_SHA256:'a'.repeat(64),
      GROQ_HUD_VERIFIED_AT:String(NOW-1000),GROQ_HUD_VALID_UNTIL:String(NOW+3600000),
      GROQ_HUD_DAILY_BUDGET:'2'
    }:{})};
}
const req=(path,method='GET',body)=>new Request('https://hud.test'+path,{
  method,headers:{Cookie:'rovor_hud_reader='+R,Origin:'https://hud.test','Content-Type':'application/json'},
  ...(body?{body:JSON.stringify(body)}:{})});
const prompt={model:GROQ_CLOUD_ROUTE,messages:[{role:'user',content:'Reply with GROQ_CONNECTED.'}]};
const upstream=async(url,opts)=>{
  assert.equal(url,'https://api.groq.com/openai/v1/chat/completions');
  assert.equal(JSON.parse(opts.body).model,'openai/gpt-oss-20b');
  assert.equal(JSON.parse(opts.body).stream,false);
  return Response.json({model:'openai/gpt-oss-20b',choices:[{finish_reason:'stop',
    message:{role:'assistant',content:'GROQ_CONNECTED'}}],
    usage:{prompt_tokens:77,completion_tokens:47}});
};
test('Groq stays unavailable without cloud key and current owner eligibility evidence',async()=>{
  const e=env(false);assert.equal(groqCloudReady(e,NOW),false);
  const models=await (await handle(req('/api/chat/models'),e,NOW)).json();
  assert(!models.models.includes(GROQ_CLOUD_ROUTE));
  const res=await handle(req('/api/chat','POST',prompt),e,NOW,async()=>{throw Error('network must not be used')});
  assert.equal(res.status,503);
  assert.equal((await res.json()).error,'groq_free_eligibility_unverified_or_expired');
});
test('Private Cloud Groq works while Mac and Cloudflare AI bindings are absent',async()=>{
  const e=env();
  assert.equal(groqCloudReady(e,NOW),true);
  const models=await(await handle(req('/api/chat/models'),e,NOW)).json();
  assert(models.models.includes(GROQ_CLOUD_ROUTE));
  const first=await handle(req('/api/chat','POST',prompt),e,NOW,upstream);
  assert.equal(first.status,200);
  assert.match(await first.text(),/GROQ_CONNECTED/);
  const data=await(await handle(req('/api/chat/groq/status'),e,NOW)).json();
  assert.equal(data.mac_required,false);assert.equal(data.locally_admitted_today,1);
  assert.equal(data.last_prompt_tokens,77);
  const throttled=await handle(req('/api/chat','POST',prompt),e,NOW+1000,async()=>{throw Error('must not call upstream')});
  assert.equal(throttled.status,429);
  const second=await handle(req('/api/chat','POST',prompt),e,NOW+4000,upstream);
  assert.equal(second.status,200);
  const exhausted=await handle(req('/api/chat','POST',prompt),e,NOW+8000,async()=>{throw Error('must not call upstream')});
  assert.equal(exhausted.status,429);
});
test('Groq cloud auth, origin, expiry and model identity fail closed',async()=>{
  const e=env();
  const denied=await handle(new Request('https://hud.test/api/chat',{method:'POST',headers:{Origin:'https://hud.test'},body:JSON.stringify(prompt)}),e,NOW,upstream);
  assert.equal(denied.status,401);
  const cross=await handle(new Request('https://hud.test/api/chat',{method:'POST',
    headers:{Origin:'https://other.test',Cookie:'rovor_hud_reader='+R},body:JSON.stringify(prompt)}),e,NOW,upstream);
  assert.equal(cross.status,403);
  const expired=await handle(req('/api/chat','POST',prompt),e,NOW+3600000,async()=>{throw Error('must not call upstream')});
  assert.equal(expired.status,503);
  let called=0;
  const mismatch=await handle(req('/api/chat','POST',prompt),e,NOW,async()=>{
    called++;return Response.json({model:'other-model',choices:[{finish_reason:'stop',message:{content:'hello'}}],usage:{prompt_tokens:1,completion_tokens:1}});
  });
  assert.equal(mismatch.status,502);assert.equal(called,1);
});
test('No unapproved upstream tools, retry, or private credentials in cloud replies',async()=>{
  const e=env();let count=0;
  const res=await handle(req('/api/chat','POST',prompt),e,NOW,async(url,opts)=>{
    count++;const data=JSON.parse(opts.body);assert.equal(data.tool_choice,'none');
    assert.equal(opts.headers.Authorization,'Bearer '+e.GROQ_HUD_API_KEY);
    return Response.json({model:'openai/gpt-oss-20b',choices:[{finish_reason:'stop',message:{content:'ok'}}],usage:{prompt_tokens:2,completion_tokens:1}});
  });
  assert.equal(res.status,200);assert.equal(count,1);
  assert(!(await res.text()).includes(e.GROQ_HUD_API_KEY));
});
