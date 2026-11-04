import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {eligibleModels,readEvents,executeClaim} from '../tools/hud_chat_relay_client.mjs';
import {cleanCatalog,cleanReply,catalog,enqueue,RELAY} from '../integrations/hud-cloud/omniroute-chat-relay.mjs';
import {handle} from '../integrations/hud-cloud/worker.mjs';

const READER='r'.repeat(48), WRITER='w'.repeat(48), URL='https://hud.test';
const authReader = {Cookie:'rovor_hud_reader='+READER};
const authWriter = {Authorization:'Bearer '+WRITER};
const env=db=>({DB:db,HUD_READER_TOKEN:READER,HUD_WRITER_TOKEN:WRITER});
const db={
  prepare(){return {bind(){return {first:async()=>null,run:async()=>({meta:{changes:0}})};}};}
};
const req=(path,method='GET',headers={},body)=>new Request(URL+path,{method,headers:{...headers,...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});

test('only approved free routes are advertised, not arbitrary catalog entries',()=>{
  const listed=['rovor-fast-free-v1','groq/openai/gpt-oss-120b',
    'openrouter/meta-llama/llama-3.3:free','openrouter/auto','provider/premium'];
  assert.deepEqual(eligibleModels(listed),['rovor-fast-free-v1','openrouter/meta-llama/llama-3.3:free']);
  assert.deepEqual(eligibleModels(listed,['groq/openai/gpt-oss-120b']),[
    'rovor-fast-free-v1','groq/openai/gpt-oss-120b','openrouter/meta-llama/llama-3.3:free']);
  assert(!eligibleModels(listed,['provider/not-in-catalog']).includes('provider/not-in-catalog'));
});
test('catalog enforces exact names, limits and fresh heartbeat',async()=>{
  assert.deepEqual(cleanCatalog({models:['a/model:free','a/model:free']}),['a/model:free']);
  assert.throws(()=>cleanCatalog({models:['../../credentials']}),/invalid_chat_catalog/);
  assert.throws(()=>cleanCatalog({models:Array(101).fill('a')}),/invalid_chat_catalog/);
  assert.deepEqual(await catalog(db,Date.now()),{online:false,models:[],last_seen_at:null});
});
test('reply schema rejects any unapproved state or oversized output',()=>{
  assert.deepEqual(cleanReply({state:'complete',output:'ok'}),{state:'complete',output:'ok',error:null});
  assert.throws(()=>cleanReply({state:'running',output:'fake'}),/invalid_chat_result/);
  assert.throws(()=>cleanReply({state:'complete',output:'x'.repeat(RELAY.maxReplyChars+1)}),/invalid_chat_result/);
});
test('Mac relay collects OpenAI SSE completion text, not status claims',async()=>{
  const stream=new ReadableStream({start(c){
    const enc=new TextEncoder();
    c.enqueue(enc.encode('data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'));
    c.enqueue(enc.encode('data: {"choices":[{"delta":{"content":" from model"}}]}\n\ndata: [DONE]\n\n'));
    c.close();
  }});
  const chat={respond:async()=>({status:200,stream,done(){}})};
  const answer=await executeClaim(chat,{id:'ok',model:'a:free',request:{model:'a:free',messages:[{role:'user',content:'hi'}]}},new AbortController().signal);
  assert.deepEqual(answer,{state:'complete',output:'Hello from model'});
  assert.equal(readEvents('data: {"choices":[{"delta":{"content":"test"}}]}'),'test');
});
test('writer and reader credentials are strictly separated',async()=>{
  assert.equal((await handle(req('/api/hud/chat/bridge','POST',{...authReader,Origin:URL},{models:[]}),env(db))).status,401);
  assert.equal((await handle(req('/api/hud/chat/claim','POST',{...authReader,Origin:URL},{}),env(db))).status,401);
  assert.equal((await handle(req('/api/hud/chat/models','GET',authWriter),env(db))).status,401);
  assert.equal((await handle(req('/api/hud/chat/models','GET',authReader),env(db))).status,200);
  assert.equal((await handle(req('/api/hud/chat/submit','POST',{...authReader,Origin:'https://evil.test'},{}),env(db))).status,403);
  assert.equal((await handle(req('/api/hud/chat/submit','POST',{...authReader,Origin:URL},{model:'premium',messages:[{role:'user',content:'test'}]}),env(db))).status,503);
  const report=await handle(req('/api/hud/chat/bridge','POST',{...authWriter,Origin:URL},{models:['a:free']}),env(db));
  assert.equal(report.status,200);
});

test('iPhone/iPad form controls prevent Safari auto-zoom without disabling accessibility zoom',()=>{
  const script=readFileSync(new globalThis.URL('../dashboard/command-center/native-v8-9/hud-chat.js',import.meta.url),'utf8');
  const html=readFileSync(new globalThis.URL('../dashboard/command-center/native-v8-9/index.html',import.meta.url),'utf8');
  assert.match(script, /#rvc select, #rvc textarea, #rvc input/);
  assert.match(script, /font-size:16px!important/);
  assert.match(script, /window\.visualViewport\?\.addEventListener\('resize',syncVisualViewport\)/);
  assert.match(script, /--rvc-vv-height/);
  assert.doesNotMatch(html, /user-scalable\s*=\s*no|maximum-scale\s*=\s*1/i);
  assert.doesNotMatch(script, /user-scalable\s*=\s*no|maximum-scale\s*=\s*1/i);
});
