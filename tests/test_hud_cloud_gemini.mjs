import {test} from 'node:test';
import assert from 'node:assert/strict';
import {cloudGeminiChat,cloudGeminiModels,googleGeminiCatalog,
  validateGeminiChat,cloudGeminiUsage,selectGeminiForTask,FREE_GEMINI_MODELS,
  AUTO_GEMINI_MODEL,ownerApprovedModels} from '../integrations/hud-cloud/cloud-gemini-chat.mjs';
import {handle} from '../integrations/hud-cloud/worker.mjs';

const key='g'.repeat(38),reader='r'.repeat(40),writer='w'.repeat(40);
const day='2026-11-09',now=Date.parse('2026-11-09T06:00:00Z');
const model='gemini-3.1-flash-lite',fast='gemini-3.5-flash-lite',strong='gemini-3.8-flash';
const origin='https://hud.test';
const contents={model,messages:[{role:'user',content:'Say hello'}]};
const googleReply=()=>Response.json({
  candidates:[{content:{parts:[{text:'Hello via real model mock'}]},finishReason:'STOP'}],
  usageMetadata:{promptTokenCount:8,candidatesTokenCount:4}
});
function mockGoogle(ids=[model,fast,strong],reply=googleReply()){
  const calls=[];
  const send=async(url,options)=>{
    calls.push({url,options});
    assert.equal(options.headers['x-goog-api-key'],key);
    if(options.method==='GET'){
      assert.match(url,/^https:\/\/generativelanguage\.googleapis\.com\/v1beta\/models\?pageSize=100/);
      return Response.json({models:[
        ...ids.map(id=>({name:'models/'+id,supportedGenerationMethods:['generateContent']})),
        {name:'models/gemini-3.1-pro-preview',supportedGenerationMethods:['generateContent']},
        {name:'models/gemini-3.1-flash-image',supportedGenerationMethods:['generateContent']},
        {name:'models/text-embedding-004',supportedGenerationMethods:['embedContent']}
      ]});
    }
    assert.equal(options.method,'POST');
    assert.match(url,/^https:\/\/generativelanguage\.googleapis\.com\/v1beta\/models\/gemini-/);
    assert.equal(JSON.parse(options.body).generationConfig.maxOutputTokens,768);
    assert(!JSON.stringify(JSON.parse(options.body)).includes('tools'));
    return reply;
  };
  return {send,calls};
}
function db(){
  const budgets=new Map(),usage=new Map(),models=new Map();
  function getModel(day,model){
    const key=day+'|'+model;
    if(!models.has(key))models.set(key,{day,model,attempts:0,completed:0,
      failures:0,input_tokens:0,output_tokens:0,last_error_code:null});
    return models.get(key);
  }
  return {
    prepare(sql){return {
      bind(...a){return {
        async first(){
          if(sql.includes('hud_gemini_chat_budget')&&sql.includes('RETURNING')){
            const [bucket,max]=a;
            if((budgets.get(bucket)||0)>=max)return null;
            budgets.set(bucket,(budgets.get(bucket)||0)+1);
            return {attempts:budgets.get(bucket)};
          }
          if(sql.startsWith('SELECT attempts FROM hud_gemini_chat_budget'))
            return {attempts:budgets.get(a[0])||0};
          if(sql.startsWith('SELECT completed,input_tokens,output_tokens FROM hud_gemini_chat_usage'))
            return usage.get(a[0])||null;
          return null;
        },
        async all(){
          if(sql.includes('FROM hud_gemini_chat_model_usage'))
            return {results:[...models.values()].filter(m=>m.day===a[0])};
          return {results:[]};
        },
        async run(){
          if(sql.startsWith('INSERT INTO hud_gemini_chat_model_usage')){
            getModel(a[0],a[1]).attempts++;
          }else if(sql.startsWith('UPDATE hud_gemini_chat_model_usage SET failures')){
            const row=getModel(a[1],a[2]);row.failures++;row.last_error_code=a[0];
          }else if(sql.startsWith('UPDATE hud_gemini_chat_model_usage SET completed')){
            const row=getModel(a[2],a[3]);row.completed++;
            row.input_tokens+=a[0];row.output_tokens+=a[1];row.last_error_code=null;
          }else if(sql.startsWith('INSERT INTO hud_gemini_chat_usage')){
            const prev=usage.get(a[0])||{completed:0,input_tokens:0,output_tokens:0};
            usage.set(a[0],{completed:prev.completed+1,
              input_tokens:prev.input_tokens+a[1],output_tokens:prev.output_tokens+a[2]});
          }
          return {meta:{changes:1}};
        }
      }; }
    };}
    },
    async batch(statements){return Promise.all(statements.map(s=>s.run()));}
  };
}
const env=()=>({GEMINI_API_KEY:key,ROVOR_GEMINI_FREE_TIER_VERIFIED:'confirmed',DB:db()});

test('Catalog is key-listed + free-text allowlisted, not a paid/imagery/embedding catalog',async()=>{
  const e=env(),g=mockGoogle([fast,strong,model,'gemini-3.1-pro-preview']);
  const cat=await googleGeminiCatalog(e,g.send);
  assert.deepEqual(cat.models,[strong,fast,model]);
  const listing=await cloudGeminiModels(e,g.send);
  assert.equal(listing.online,true);
  assert.equal(listing.mac_required,false);
  assert.deepEqual(listing.models,[AUTO_GEMINI_MODEL,strong,fast,model]);
  assert(listing.other_catalog_models>0);
  assert.equal((await cloudGeminiModels({},async()=>{throw Error('no calls');})).online,false);
  assert.equal(FREE_GEMINI_MODELS.includes('gemini-3.1-pro-preview'),false);
});

test('Unknown owner Free-tier model allowlist fails closed',async()=>{
  const e=env(),g=mockGoogle();
  e.ROVOR_GEMINI_FREE_MODELS=JSON.stringify([fast,'gemini-3.1-pro-preview']);
  assert.deepEqual(ownerApprovedModels(e),[]);
  assert.equal((await cloudGeminiModels(e,g.send)).online,false);
  assert.equal(g.calls.length,0);
  e.ROVOR_GEMINI_FREE_MODELS=JSON.stringify([fast]);
  assert.deepEqual((await cloudGeminiModels(e,g.send)).models,[AUTO_GEMINI_MODEL,fast]);
});

test('Google catalog pagination is required; cannot assume first 100 rows contain all models',async()=>{
  const e=env();let pages=0;
  const send=async(url)=>{
    pages++;
    if(pages===1)return Response.json({models:[{name:'models/'+model,supportedGenerationMethods:['generateContent']}],nextPageToken:'next'});
    assert(new URL(url).searchParams.get('pageToken')==='next');
    return Response.json({models:[{name:'models/'+fast,supportedGenerationMethods:['generateContent']}]});
  };
  const found=await googleGeminiCatalog(e,send);
  assert.equal(pages,2);
  assert.deepEqual(found.models,[fast,model]);
});

test('Only published Free-tier text models or smart free route accepted',()=>{
  assert.equal(validateGeminiChat(contents)[0].role,'user');
  assert.equal(validateGeminiChat({...contents,model:AUTO_GEMINI_MODEL})[0].role,'user');
  for(const wrong of ['@cf/google/gemma-3-12b-it','gemini-3.1-pro-preview',
    'rovor-fast-free-v1','gemini-3.1-flash-image'])
    assert.throws(()=>validateGeminiChat({...contents,model:wrong}),/invalid_gemini_chat/);
  assert.throws(()=>validateGeminiChat({...contents,messages:[{role:'user',content:'x'.repeat(4001)}]}),/invalid_gemini_chat/);
});

test('Smart chooses 3.8 Flash for coding and Flash-Lite for routine, never round robin',()=>{
  const allowed=[fast,strong,model];
  assert.equal(selectGeminiForTask({...contents,model:AUTO_GEMINI_MODEL},allowed),fast);
  assert.equal(selectGeminiForTask({model:AUTO_GEMINI_MODEL,
    messages:[{role:'user',content:'Debug this architecture and code'}]},allowed),strong);
  assert.equal(selectGeminiForTask({...contents,model},allowed),model);
  assert.equal(selectGeminiForTask({...contents,model:'gemini-3.5-flash'},allowed),null);
});

test('Direct model call records actual per-model and project-wide token receipt',async()=>{
  const e=env(),g=mockGoogle();
  const r=await cloudGeminiChat(contents,e,now,g.send);
  assert.equal(r.status,200);
  assert.equal(r.headers.get('X-ROVOR-Provider'),'google-gemini-cloud');
  assert.equal(r.headers.get('X-ROVOR-Resolved-Model'),model);
  assert.match(await r.text(),/data: \[DONE\]/);
  assert.equal(g.calls.filter(x=>x.options.method==='POST').length,1);
  const u=await cloudGeminiUsage(e,now);
  const data=await u.json();
  assert.equal(data.completed,1);
  assert.equal(data.models.find(m=>m.model===model).completed,1);
  assert.equal(data.models.find(m=>m.model===model).input_tokens,8);
  assert.equal(data.models.find(m=>m.model===model).output_tokens,4);
});

test('One smart request resolves a listed model only, exposing its exact route',async()=>{
  const e=env(),g=mockGoogle();
  const r=await cloudGeminiChat({model:AUTO_GEMINI_MODEL,
    messages:[{role:'user',content:'Debug my GitHub code'}]},e,now,g.send);
  assert.equal(r.status,200);
  assert.equal(r.headers.get('X-ROVOR-Requested-Model'),AUTO_GEMINI_MODEL);
  assert.equal(r.headers.get('X-ROVOR-Resolved-Model'),strong);
  assert(g.calls.find(c=>c.options.method==='POST').url.endsWith('/'+strong+':generateContent'));
});

test('D1 project-wide minute limit refuses a third call across different models',async()=>{
  const e=env(),g=mockGoogle();
  for(const [i,route] of [model,fast,strong].entries()){
    const r=await cloudGeminiChat({...contents,model:route},e,now+i*1000,g.send);
    assert.equal(r.status,i<2?200:429);
  }
  assert.equal(g.calls.filter(x=>x.options.method==='POST').length,2);
});

test('A listed model may still be denied; no fallback or fake completion',async()=>{
  const e=env(),g=mockGoogle([model],new Response('',{status:429}));
  const r=await cloudGeminiChat(contents,e,now,g.send);
  assert.equal(r.status,429);
  assert.equal((await r.json()).error,'gemini_provider_rate_limited');
  assert.equal(g.calls.filter(x=>x.options.method==='POST').length,1);
  const u=await (await cloudGeminiUsage(e,now)).json();
  assert.equal(u.completed,0);
  assert.equal(u.models[0].failures,1);
  assert.equal(u.models[0].last_error_code,'provider_429');
});

test('An unlisted model is never attempted, even when published as Free tier',async()=>{
  const e=env(),g=mockGoogle([fast]);
  const r=await cloudGeminiChat(contents,e,now,g.send);
  assert.equal(r.status,409);
  assert.equal(g.calls.filter(x=>x.options.method==='POST').length,0);
});

test('Existing HUD denies anonymous and cross-site Gemini requests',async()=>{
  // Deliberately omit fake Google key, so auth tests cannot make a real outbound call.
  const e={DB:db(),HUD_READER_TOKEN:reader,HUD_WRITER_TOKEN:writer};
  const get=(path,headers={})=>new Request(origin+path,{headers});
  const post=(o,headers={})=>new Request(origin+'/api/hud/gemini/chat',{
    method:'POST',headers:{Authorization:'Bearer '+reader,'Content-Type':'application/json',Origin:o,...headers},
    body:JSON.stringify(contents)});
  assert.equal((await handle(get('/api/hud/gemini/models'),e)).status,401);
  assert.equal((await handle(get('/api/hud/gemini/models',{Authorization:'Bearer '+reader}),e)).status,200);
  assert.equal((await handle(post('https://evil.test'),e)).status,403);
  assert.equal((await handle(post(origin,{Authorization:'Bearer wrong'}),e)).status,401);
});
