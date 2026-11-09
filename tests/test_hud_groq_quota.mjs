import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {handle} from '../integrations/hud-cloud/worker.mjs';
import {groqRateHeaders} from '../integrations/hud-cloud/groq-quota-monitor.mjs';
const NOW=Date.parse('2026-11-09T06:30:00Z');
const R='r'.repeat(40),W='w'.repeat(40);
function database(){
  const sqlite=new DatabaseSync(':memory:');
  sqlite.exec(readFileSync(new URL('../integrations/hud-cloud/schema.sql',import.meta.url),'utf8'));
  return {prepare(sql){return {bind(...values){return{
    first:async()=>sqlite.prepare(sql).get(...values)??null,
    run:async()=>({meta:{changes:sqlite.prepare(sql).run(...values).changes}})
  }}}}};
}
function e(key=true){
  return {DB:database(),HUD_READER_TOKEN:R,HUD_WRITER_TOKEN:W,
    ...(key?{GROQ_HUD_API_KEY:'PRIVATE-MOCK-GROQ-KEY-NOT-REAL'}:{})};
}
function req(url='/api/chat/groq/status?refresh=1',auth=true){
  return new Request('https://hud.test'+url,{headers:auth?{Cookie:'rovor_hud_reader='+R}:{}});
}
function headers(){
  return {'x-ratelimit-limit-requests':'1000','x-ratelimit-remaining-requests':'975',
    'x-ratelimit-reset-requests':'2m59.56s',
    'x-ratelimit-limit-tokens':'8000','x-ratelimit-remaining-tokens':'7470',
    'x-ratelimit-reset-tokens':'7.66s'};
}
function catalog(){
  return Response.json({data:[{id:'openai/gpt-oss-20b'},{id:'openai/gpt-oss-120b'}]},{headers:headers()});
}
test('Read-only Groq catalogue probes once per minute and reports real header scopes',async()=>{
  const env=e();let calls=0;
  const fetcher=async(url,options)=>{
    calls++;assert.equal(url,'https://api.groq.com/openai/v1/models');
    assert.equal(options.method,'GET');assert.equal(options.headers.Authorization,'Bearer '+env.GROQ_HUD_API_KEY);
    assert.equal(options.redirect,'manual');
    assert(!options.body,'never sends prompts');return catalog();
  };
  const first=await handle(req(),env,NOW,fetcher);
  assert.equal(first.status,200);
  const doc=await first.json();
  assert.equal(doc.mac_required,false);
  assert.equal(doc.ready,false,'catalogue must never substitute for private free-plan attestation');
  assert.equal(doc.catalog.state,'catalog_received');
  assert.equal(doc.catalog.model_present,true);
  assert.equal(doc.catalog.requests_per_day.limit,1000);
  assert.equal(doc.catalog.requests_per_day.remaining,975);
  assert.equal(doc.catalog.requests_per_day.used,25);
  assert.equal(doc.catalog.tokens_per_minute.limit,8000);
  assert.equal(doc.catalog.tokens_per_minute.remaining,7470);
  assert.equal(doc.catalog.requests_per_day.reset_at,new Date(NOW+179560).toISOString());
  assert.equal(doc.catalog.tokens_per_minute.reset_at,new Date(NOW+7660).toISOString());
  assert.equal(doc.catalog.scope,'Groq API response headers; billing unknown');
  const second=await handle(req(),env,NOW+30000,async()=>{throw Error('must not probe again before 60s')});
  assert.equal(second.status,200);assert.equal(calls,1);
  const stale=await(await handle(req('/api/chat/groq/status'),env,NOW+125000,async()=>{throw Error('no upstream without explicit refresh')})).json();
  assert.equal(stale.catalog.state,'stale');
  assert.equal(stale.catalog.requests_per_day,null,'expired quota must never look live');
  assert.equal(stale.catalog.model_present,null);
});
test('Missing keys and viewer auth fail closed without any Groq request',async()=>{
  let calls=0;const fetcher=async()=>{calls++;throw Error('unapproved call')};
  const missing=await(await handle(req(),e(false),NOW,fetcher)).json();
  assert.equal(missing.credentials_present,false);
  assert.equal(missing.catalog.state,'not_checked');
  const forbidden=await handle(req('/api/chat/groq/status?refresh=1',false),e(),NOW,fetcher);
  assert.equal(forbidden.status,401);assert.equal(calls,0);
});
test('Provider 401 never counts as verified model access or free inference',async()=>{
  const env=e();
  const result=await(await handle(req(),env,NOW,async()=>new Response('denied',{status:401}))).json();
  assert.equal(result.catalog.state,'auth_rejected');
  assert.equal(result.catalog.model_present,null);
  assert.equal(result.catalog.requests_per_day,null);
  assert.equal(result.ready,false);
});
test('Bad or partial headers cannot produce fabricated account usage',()=>{
  const bad=new Headers({'x-ratelimit-limit-requests':'1000',
    'x-ratelimit-remaining-requests':'9999',
    'x-ratelimit-reset-requests':'unverified',
    'x-ratelimit-limit-tokens':'8000'});
  const m=groqRateHeaders(bad,NOW);
  assert.equal(m.requests_per_day,null);
  assert.equal(m.tokens_per_minute,null);
});
test('Concurrent authenticated refreshes share a D1 lease, never fan out',async()=>{
  const env=e();let calls=0;
  const upstream=async()=>{calls++;return catalog()};
  const results=await Promise.all(Array.from({length:5},()=>handle(req(),env,NOW,upstream)));
  assert.equal(calls,1);assert(results.every(r=>r.status===200));
});

test('Groq catalogue never follows credential-bearing redirects',async()=>{
  const env=e();
  const data=await(await handle(req(),env,NOW,async(url,options)=>{
    assert.equal(options.redirect,'manual');
    return new Response(null,{status:302,headers:{Location:'https://not-groq.example/steal'}});
  })).json();
  assert.equal(data.catalog.state,'upstream_error');
  assert.equal(data.catalog.model_present,null);
  assert.equal(data.catalog.requests_per_day,null);
});
test('All cloud-provider fetch requests use the Cloudflare-supported manual redirect mode',()=>{
  for(const path of ['groq-cloud-chat.mjs','groq-quota-monitor.mjs',
    'cloud-gemini-chat.mjs','gemini-cloud-monitoring.mjs']){
    const src=readFileSync(new URL('../integrations/hud-cloud/'+path,import.meta.url),'utf8');
    // Scan executable source only; a comment explaining a forbidden mode
    // must not falsely fail the regression, while actual fetch code still does.
    const executable=src.split('\n').filter(line=>!line.trimStart().startsWith('//')).join('\n');
    assert.doesNotMatch(executable,/redirect\s*:\s*['"]error['"]/);
  }
});
