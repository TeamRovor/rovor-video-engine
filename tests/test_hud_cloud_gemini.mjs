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
function mockGoogle(ids=[model,fast,strong],replyStatus=200){
  const calls=[];
  const send=async(url,options)=>{
    calls.push({url,options});
    assert.equal(options.headers['x-goog-api-key'],key);
    assert.equal(options.redirect,'manual','Cloudflare Workers accepts manual redirect handling, not error');
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
    const selected=url.split('/models/')[1]?.split(':')[0];
    assert.equal(JSON.parse(options.body).generationConfig.maxOutputTokens,selected?.endsWith('-lite')?1024:2048);
    assert(!JSON.stringify(JSON.parse(options.body)).includes('tools'));
    return replyStatus===429?new Response('',{status:429}):googleReply();
  };
  return {send,calls};
}
function db(){
  const budgets=new Map(),usage=new Map(),models=new Map(),health=new Map();
  function getModel(day,model){
    const key=day+'|'+model;
    if(!models.has(key))models.set(key,{day,model,attempts:0,completed:0,
      failures:0,input_tokens:0,output_tokens:0,last_error_code:null});
    return models.get(key);
  }
  return {
    prepare(sql){return {
      async all(){
        if(sql.startsWith('SELECT model,last_success_at'))return {results:[...health.values()]};
        return {results:[]};
      },
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
          if(sql.startsWith('SELECT model,MAX(day)')){
            const out=new Map();
            for(const m of models.values())if(m.day>=a[0]&&m.completed>0&&(!out.has(m.model)||out.get(m.model).last_day<m.day))
              out.set(m.model,{model:m.model,last_day:m.day});
            return {results:[...out.values()]};
          }
          if(sql.startsWith('SELECT model,last_success_at'))return {results:[...health.values()]};
          if(sql.includes('FROM hud_gemini_chat_model_usage'))
            return {results:[...models.values()].filter(m=>m.day===a[0])};
          return {results:[]};
        },
        async run(){
          if(sql.startsWith('INSERT INTO hud_gemini_model_health')){
            if(sql.includes('last_success_at')){
              const [model,at]=a;const old=health.get(model)||{model,success_count:0};
              health.set(model,{...old,last_success_at:at,success_count:old.success_count+1,
                cooldown_until:null,last_failure_code:null});
            }else if(sql.includes('last_rate_limited_at')){
              const [model,at,until,failed,code]=a;
              health.set(model,{...(health.get(model)||{model,success_count:0}),
                last_rate_limited_at:at,cooldown_until:until,last_failure_at:failed,last_failure_code:code});
            }
          }else if(sql.startsWith('INSERT INTO hud_gemini_chat_model_usage')){
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
    };},
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
  assert(FREE_GEMINI_MODELS.includes('gemini-3.7-flash'));
  assert(FREE_GEMINI_MODELS.includes('gemini-3.6-flash'));
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

test('One smart request uses a recently verified reply, never a merely catalog-listed strong model',async()=>{
  const e=env(),g=mockGoogle();
  const first=await cloudGeminiChat({...contents,model:strong},e,now,g.send);
  assert.equal(first.status,200);
  const r=await cloudGeminiChat({model:AUTO_GEMINI_MODEL,
    messages:[{role:'user',content:'Debug my GitHub code'}]},e,now+1000,g.send);
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
  const e=env(),g=mockGoogle([model],429);
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

test('Google catalogue redirect is denied before any model becomes available',async()=>{
  const e=env();let calls=0;
  const send=async(url,opts)=>{
    calls++;assert.equal(opts.redirect,'manual');assert.equal(opts.method,'GET');
    return new Response(null,{status:302,headers:{Location:'https://not-google.example/steal'}});
  };
  const catalog=await googleGeminiCatalog(e,send);
  assert.equal(calls,1);
  assert.equal(catalog.available,false);
  assert.equal(catalog.reason,'google_catalog_redirect_denied');
  const result=await cloudGeminiChat(contents,e,now,send);
  assert.equal(result.status,503);
  assert.equal(calls,2);
});

test('One Google inference redirect fails closed, records failure, and never replays',async()=>{
  const e=env();let outbound=0;
  const google=mockGoogle();
  const send=async(url,opts)=>{
    if(opts.method==='GET')return google.send(url,opts);
    outbound++;
    assert.equal(opts.redirect,'manual');
    return new Response(null,{status:302,headers:{Location:'https://not-google.example/steal'}});
  };
  const result=await cloudGeminiChat(contents,e,now,send);
  assert.equal(result.status,502);
  assert.equal((await result.json()).error,'gemini_upstream_redirect_denied');
  assert.equal(outbound,1);
  const usage=await (await cloudGeminiUsage(e,now)).json();
  assert.equal(usage.completed,0);
  assert.equal(usage.models.find(x=>x.model===model).failures,1);
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


test('Smart routing declines unseen models without a provider call or hidden fallback',async()=>{
  const e=env(),g=mockGoogle();
  const r=await cloudGeminiChat({...contents,model:AUTO_GEMINI_MODEL},e,now,g.send);
  assert.equal(r.status,409);
  assert.equal((await r.json()).error,'gemini_auto_requires_recent_verified_model');
  assert.equal(g.calls.filter(x=>x.options.method==='POST').length,0);
});
test('Recently verified one model promotes only that model, and exact metrics separate local from Google quota',async()=>{
  const e=env(),g=mockGoogle();
  const response=await cloudGeminiChat(contents,e,now,g.send);
  assert.equal(response.status,200);
  const listing=await cloudGeminiModels(e,g.send,now+2000);
  assert.equal(listing.verified_model_count,1);
  const verified=listing.model_evidence.find(x=>x.model===model);
  assert.equal(verified.verification,'verified_recent_reply');
  assert.equal(verified.last_verified_at,new Date(now).toISOString());
  assert.equal(listing.model_evidence.find(x=>x.model===strong).verification,'listed_unverified');
  const u=await (await cloudGeminiUsage(e,now+2000)).json();
  assert.equal(u.scope,'this_hud_direct_api_only');
  assert.equal(u.daily_local_remaining,11);
  assert.equal(u.minute_local_remaining,1);
  assert.equal(u.local_cap_time_zone,'UTC');
  assert.equal(u.quota_remaining,'not_verified_provider_wide');
  assert.equal(u.local_attempts_include_reservations_not_only_provider_calls,true);
});
test('Google 429 records cooldown and prevents follow-up spend or inaccurate available label',async()=>{
  const e=env(),g=mockGoogle([model],429);
  const one=await cloudGeminiChat(contents,e,now,g.send);
  assert.equal(one.status,429);
  const two=await cloudGeminiChat(contents,e,now+1000,g.send);
  assert.equal(two.status,429);
  assert.equal((await two.json()).error,'gemini_model_cooldown_active');
  assert.equal(g.calls.filter(x=>x.options.method==='POST').length,1);
  const listing=await cloudGeminiModels(e,g.send,now+1000);
  const evidence=listing.model_evidence.find(x=>x.model===model);
  assert.equal(evidence.verification,'provider_cooldown');
  assert.equal(evidence.cooldown_until,new Date(now+3600000).toISOString());
  const usage=await (await cloudGeminiUsage(e,now+1000)).json();
  assert.equal(usage.attempts,1);
  assert.equal(usage.completed,0);
  assert.equal(usage.models.find(x=>x.model===model).failures,1);
});
test('Missing Google token metadata never reports precise zero tokens or verified completion',async()=>{
  const e=env(),g=mockGoogle();
  const send=async(url,opts)=>opts.method==='GET'?g.send(url,opts):Response.json({
    candidates:[{content:{parts:[{text:'Good reply'}]},finishReason:'STOP'}]
  });
  const r=await cloudGeminiChat(contents,e,now,send);
  assert.equal(r.status,502);
  assert.equal((await r.json()).error,'gemini_token_usage_unverified');
  const u=await (await cloudGeminiUsage(e,now)).json();
  assert.equal(u.completed,0);
  assert.equal(u.models[0].last_error_code,'invalid_response');
});
test('Expired real model verification does not silently enable Smart Gemini',async()=>{
  const e=env(),g=mockGoogle();
  const prior=now-9*86400000;
  const first=await cloudGeminiChat({...contents,model:strong},e,prior,g.send);
  assert.equal(first.status,200);
  const next=await cloudGeminiChat({...contents,model:AUTO_GEMINI_MODEL},e,now,g.send);
  assert.equal(next.status,409);
  assert.equal((await next.json()).error,'gemini_auto_requires_recent_verified_model');
});

test('Non-429 Google HTTP denials are precise, redacted per-model D1 failures with no retries',async()=>{
  for(const [status,code] of [
    [400,'google_400_request_rejected'],
    [401,'google_401_auth_denied'],
    [403,'google_403_access_denied'],
    [404,'google_404_model_unavailable'],
    [503,'google_5xx_service_error']
  ]){
    const e=env(),g=mockGoogle();let calls=0;
    const send=async(url,options)=>{
      if(options.method==='GET')return g.send(url,options);
      calls++;
      return new Response('PRIVATE UPSTREAM BODY MUST NEVER LEAK',{status});
    };
    const r=await cloudGeminiChat(contents,e,now,send);
    assert.equal(r.status,502);
    assert.equal((await r.json()).error,code);
    assert.equal(calls,1);
    const u=await(await cloudGeminiUsage(e,now)).json();
    assert.equal(u.completed,0);
    assert.equal(u.attempts,1);
    assert.equal(u.models.find(x=>x.model===model)?.last_error_code,code);
    assert.doesNotMatch(JSON.stringify(u),/PRIVATE UPSTREAM BODY/);
  }
});
