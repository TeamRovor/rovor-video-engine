import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js',import.meta.url),'utf8');
function board() {
 const window={},document={getElementById:()=>({})};
 vm.runInNewContext(source,{window,document,Date,Math,Number,String,Array,Map});
 return window.ROVOR_QUOTA_BOARD;
}
const providers=['groq','gemini','cloudflare-ai','mistral','nvidia','openrouter','sambanova','cohere','huggingface'];
function cloud(){
 return {execution_source:'cloud_provider',observed_at:Date.now(),
  providers:providers.map(provider=>({provider,credentials_configured:true,
    admission:provider==='groq'?'eligible':'disabled_pending_verification',online_verified:false}))};
}
test('nine disconnected slots show unknown rings instead of zero quota',()=>{
 const html=board().render(null,false,cloud());
 assert.equal((html.match(/class="rvq-provider"/g)||[]).length,9);
 assert.equal((html.match(/role="img" aria-label="Provider quota unknown"/g)||[]).length,18);
 assert.equal((html.match(/class="rvq-overview-tile"/g)||[]).length,9);
 assert.equal((html.match(/role="progressbar" aria-label="Reported quota used"/g)||[]).length,0);
 assert.match(html,/Unknown/);
 assert.doesNotMatch(html,/0.0%/);
});
test('verified local quota shows circular 25 percent plus 75 remaining',()=>{
 const html=board().render({
  connections:[{provider:'groq',name:'Groq',connection_count:1,enabled_count:1}],
  connection_slots:[{provider:'groq',account_slot:1,enabled:true}],
  quota:{records:[{provider:'groq',account_slot:1,model_id:'model-a',used:25,total:100,
   used_percent:25,unit:'requests',fetched_at:new Date().toISOString(),
   reset_at:new Date(Date.now()+3600000).toISOString()}]}},true);
 assert.match(html,/aria-label="Reported quota used"/);
 assert.equal((html.match(/class="rvq-overview-tile"/g)||[]).length,1);
 assert.match(html,/aria-valuetext="25.0 percent of verified allowance used"/);
 assert.match(html,/--rvq-angle:25.0%/);
 assert.match(html,/75 \/ 100 requests/);
 assert.match(html,/RESET WINDOW/);
});
test('contradictory cache percentage is unverified',()=>{
 const html=board().render({
  connections:[{provider:'groq',name:'Groq',connection_count:1,enabled_count:1}],
  connection_slots:[{provider:'groq',account_slot:1,enabled:true}],
  quota:{records:[{provider:'groq',account_slot:1,model_id:'model-b',used:50,total:100,
   used_percent:0,unit:'requests',fetched_at:new Date().toISOString(),
   reset_at:new Date(Date.now()+3600000).toISOString()}]}},true);
 assert.match(html,/UNVERIFIED/);
 assert.doesNotMatch(html,/50.0%/);
});
test('verified cloud quota displays separate usage ring; expired evidence does not',()=>{
 const data=cloud();const p=data.providers.find(x=>x.provider==='openrouter');
 p.quota={status:'verified',observed_at:Date.now(),used:6,limit:50,unit:'requests',resets_at:Date.now()+3600000};
 const html=board().render(null,false,data);
 assert.match(html,/Verified cloud limit/);
 assert.match(html,/--rvq-angle:12.0%/);
 assert.match(html,/Independent cloud account limit/);
 p.quota.resets_at=Date.now()-5000;
 const expired=board().render(null,false,data);
 assert.doesNotMatch(expired,/--rvq-angle:12.0%/);
 assert.match(expired,/Cloud quota and reset: unknown/);
});
test('all nine configured providers show measured Mac requests separately from quota',()=>{
 const rows=[{provider:'openrouter',name:'OpenRouter',connection_count:1,enabled_count:1},
   {provider:'mistral',name:'Mistral',connection_count:1,enabled_count:1},
   ...providers.filter(p=>!['openrouter','mistral'].includes(p)).map(provider=>({
     provider,name:provider,connection_count:1,enabled_count:1}))];
 const data={source:'local_omniroute_read_only_bridge',period:'24h',
   snapshot_at:new Date().toISOString(),usage_coverage:'complete_aggregate',
   request_count:4,connections:rows,
   connection_slots:rows.map(g=>({provider:g.provider,account_slot:1,enabled:true})),
   models:[{provider:'openrouter',requests:3,tokens:120},
           {provider:'mistral',requests:1,tokens:10}],quota:{records:[]}};
 const html=board().render(data,true,cloud());
 assert.equal((html.match(/class="rvq-overview-tile"/g)||[]).length,9);
 assert.equal((html.match(/percent of recorded Mac requests/g)||[]).length,9);
 // The visible first meter is actual traffic, not an alarming UNKNOWN quota ring.
 const ringHead=html.slice(html.indexOf('class="rvq-overview-tile"'),
   html.indexOf('class="rvq-overview-tile"')+1500);
 assert(ringHead.indexOf('percent of recorded Mac requests')>=0);
 assert(ringHead.indexOf('Provider quota unknown')>=0);
 assert(ringHead.indexOf('percent of recorded Mac requests')<ringHead.indexOf('Provider quota unknown'));
 assert.match(html,/--rvq-angle:75\.0%/);
 assert.match(html,/--rvq-angle:25\.0%/);
 assert.match(html,/--rvq-angle:0\.0%/);
 assert.match(html,/3 Mac requests \/ 24h/);
 assert.match(html,/0 Mac requests \/ 24h/);
 assert.match(html,/120 reported tokens/);
 assert.match(html,/Per-provider aggregate; not an account-slot counter or remaining quota/);
 assert.equal((html.match(/role="img" aria-label="Provider quota unknown"/g)||[]).length,18);
});
test('no fabricated zero requests when 24-hour completeness is absent',()=>{
 const snapshot={period:'24h',request_count:8,usage_coverage:'partial',
   connections:[{provider:'openrouter',name:'OpenRouter',connection_count:1,enabled_count:1}],
   models:[{provider:'openrouter',requests:7,tokens:15}],quota:{records:[]}};
 let html=board().render(snapshot,true);
 assert.match(html,/Mac requests unverified/);
 assert.doesNotMatch(html,/7 Mac requests \/ 24h/);
 snapshot.usage_coverage='complete_aggregate'; // still inconsistent aggregate
 html=board().render(snapshot,true);
 assert.match(html,/Mac requests unverified/);
 assert.doesNotMatch(html,/percent of recorded Mac requests/);
});

test('all nine enabled providers show real gateway traffic and observed routed models',()=>{
 const rows=providers.map(provider=>({provider,name:provider,connection_count:1,enabled_count:1}));
 const models=[
   {provider:'openrouter',name:'cohere/north-mini-code:free',requests:41,tokens:140957},
   {provider:'openrouter',name:'nvidia/nemotron-3.5-super-vl:free',requests:7,tokens:20812},
   {provider:'mistral',name:'devstral-latest',requests:1,tokens:0},
   {provider:'groq',name:'openai/gpt-oss-120b',requests:1,tokens:108},
   {provider:'cloudflare-ai',name:'qwen2.5-coder-32b-instruct',requests:1,tokens:36}
 ];
 const data={source:'local_omniroute_read_only_bridge',period:'24h',
   snapshot_at:new Date().toISOString(),usage_coverage:'complete_aggregate',
   request_count:51,connections:rows,
   connection_slots:rows.map(({provider})=>({provider,account_slot:1,enabled:true})),
   models,quota:{records:[]}};
 const html=board().render(data,true);
 assert.equal((html.match(/class="rvq-provider"/g)||[]).length,9);
 assert.equal((html.match(/class="rvq-overview-tile"/g)||[]).length,9);
 assert.equal((html.match(/class="rvq-observed-model"/g)||[]).length,5);
 assert.match(html,/cohere\/north-mini-code:free/);
 assert.match(html,/nvidia\/nemotron-3\.5-super-vl:free/);
 assert.match(html,/41 requests/);
 assert.match(html,/140,957 reported tokens/);
 assert.match(html,/85\.4% of this gateway provider's requests/);
 assert.match(html,/No recorded model requests through Cohere/);
 assert.match(html,/No recorded model requests through NVIDIA NIM/);
 assert.equal((html.match(/aria-label="Provider quota unknown"/g)||[]).length,18);
 // OpenRouter-routed upstream Cohere/NVIDIA models are not direct Cohere/NVIDIA key usage.
 assert.match(html,/upstream names do not establish direct account usage/);
});

test('incomplete model analytics show neither made-up per-model activity nor false zero',()=>{
 const data={source:'local_omniroute_read_only_bridge',period:'24h',
   request_count:20,usage_coverage:'partial_top_50_or_unattributed',
   connections:[{provider:'groq',name:'groq',connection_count:1,enabled_count:1}],
   models:[{provider:'groq',name:'gpt-oss-120b',requests:3,tokens:10}],
   quota:{records:[]}};
 const html=board().render(data,true);
 assert.match(html,/MODEL REQUESTS · gateway aggregate unverified/);
 assert.equal((html.match(/class="rvq-observed-model"/g)||[]).length,0);
 assert.doesNotMatch(html,/3 requests/);
});

test('recorded model names are escaped and percent is never fabricated as quota',()=>{
 const data={source:'local_omniroute_read_only_bridge',period:'24h',
   request_count:2,usage_coverage:'complete_aggregate',
   connections:[{provider:'openrouter',name:'openrouter',connection_count:1,enabled_count:1}],
   models:[{provider:'openrouter',name:'<img src=x onerror=alert(1)>',requests:2,tokens:20}],
   quota:{records:[]}};
 const html=board().render(data,true);
 assert.doesNotMatch(html,/<img src=x/);
 assert.match(html,/&lt;img src=x onerror=alert\(1\)&gt;/);
 assert.match(html,/percent of OpenRouter recorded requests/);
 assert.match(html,/QUOTA UNKNOWN/);
});


test('nine gateway connections show independent 24h and 1h measured totals',()=>{
 const rows=providers.map(provider=>({provider,name:provider,connection_count:1,enabled_count:1}));
 const daily={source:'local_omniroute_read_only_bridge',period:'24h',
   snapshot_at:new Date().toISOString(),request_count:6,usage_coverage:'complete_aggregate',
   connections:rows,connection_slots:rows.map(x=>({provider:x.provider,account_slot:1,enabled:true})),
   models:[{provider:'openrouter',name:'cohere/north-mini-code:free',requests:5,tokens:100},
     {provider:'groq',name:'openai/gpt-oss-120b',requests:1,tokens:10}],
   quota:{records:[]}};
 const hourly={source:'local_omniroute_read_only_bridge',period:'1h',
   snapshot_at:new Date().toISOString(),request_count:2,usage_coverage:'complete_aggregate',
   models:[{provider:'openrouter',name:'cohere/north-mini-code:free',requests:2,tokens:33}]};
 const html=board().render(daily,true,null,hourly);
 assert.equal((html.match(/class="rvq-overview-tile"/g)||[]).length,9);
 assert.match(html,/5 Mac requests \/ 24h/);
 assert.match(html,/2 \/ 1h/);
 assert.match(html,/LAST HOUR · <strong>2 requests<\/strong> · 33 reported tokens/);
 assert.match(html,/LAST HOUR · <strong>0 requests<\/strong> · 0 reported tokens/);
 assert.match(html,/LAST HOUR · 2 requests · 33 reported tokens/);
 assert.match(html,/LAST HOUR · 0 requests · 0 reported tokens/);
 assert.match(html,/1h.*quota percentage/i);
 // The 1h counter never fills any previously unknown quota ring.
 assert.equal((html.match(/aria-label="Provider quota unknown"/g)||[]).length,18);
});
test('missing and inconsistent 1h reports never become false zero usage',()=>{
 const rows=[{provider:'groq',name:'groq',connection_count:1,enabled_count:1}];
 const daily={period:'24h',request_count:1,usage_coverage:'complete_aggregate',
   connections:rows,connection_slots:[{provider:'groq',account_slot:1,enabled:true}],
   models:[{provider:'groq',name:'openai/gpt-oss-120b',requests:1,tokens:10}],
   quota:{records:[]}};
 const partial={period:'1h',request_count:2,usage_coverage:'partial_top_50_or_unattributed',
   models:[{provider:'groq',name:'openai/gpt-oss-120b',requests:1,tokens:5}]};
 let html=board().render(daily,true,null,partial);
 assert.match(html,/1h unverified/);
 assert.match(html,/LAST HOUR · independently verified data unavailable/);
 assert.doesNotMatch(html,/LAST HOUR · 0 requests/);
 partial.usage_coverage='complete_aggregate';
 html=board().render(daily,true,null,partial); // total mismatch still must fail closed
 assert.match(html,/1h unverified/);
 partial.request_count=1;
 partial.period='24h'; // wrong period
 html=board().render(daily,true,null,partial);
 assert.match(html,/1h unverified/);
 html=board().render(daily,false,null,{...partial,period:'1h'});
 assert.match(html,/1h unverified/);
});
test('one-hour model names are escaped and never mistaken for direct upstream API-key traffic',()=>{
 const daily={period:'24h',request_count:1,usage_coverage:'complete_aggregate',
   connections:[{provider:'openrouter',name:'openrouter',connection_count:1,enabled_count:1}],
   models:[{provider:'openrouter',name:'<unsafe>',requests:1,tokens:5}],quota:{records:[]}};
 const hourly={period:'1h',request_count:1,usage_coverage:'complete_aggregate',
   models:[{provider:'openrouter',name:'<unsafe>',requests:1,tokens:3}]};
 const html=board().render(daily,true,null,hourly);
 assert.match(html,/&lt;unsafe&gt;/);
 assert.doesNotMatch(html,/<unsafe>/);
 assert.match(html,/LAST HOUR · 1 request · 3 reported tokens/);
 assert.match(html,/not an account-slot counter or remaining quota/);
});

test('Mistral owner limits appear as dated capacity references, not as measured quotas',()=>{
 const rows=[{provider:'mistral',name:'mistral',connection_count:1,enabled_count:1},
  {provider:'openrouter',name:'openrouter',connection_count:1,enabled_count:1}];
 const data={period:'24h',usage_coverage:'complete_aggregate',request_count:1,
  connections:rows,connection_slots:rows.map(r=>({provider:r.provider,account_slot:1,enabled:true})),
  models:[{name:'devstral-latest',provider:'mistral',requests:1,tokens:0}],quota:{records:[]}};
 const html=board().render(data,true);
 assert.equal((html.match(/class="rvq-mistral-reference"/g)||[]).length,1);
 assert.match(html,/MISTRAL ORGANIZATION LIMITS · OWNER SNAPSHOT/);
 assert.match(html,/Observed October 27, 2026 · Global/);
 assert.match(html,/codestral-2508<\/td><td>625,000<\/td><td>2.08/);
 assert.match(html,/mistral-medium-latest<\/td><td>20,000<\/td><td>1.00/);
 assert.match(html,/devstral-latest/);
 assert.match(html,/Recorded model without a supplied matching limit/);
 assert.match(html,/Organization-wide used\/remaining still requires verified API telemetry/);
 assert.equal((html.match(/aria-label="Provider quota unknown"/g)||[]).length,4);
 assert.doesNotMatch(html,/625,000[^<]*remaining/i);
 assert.equal((html.match(/class="rvq-overview-tile"/g)||[]).length,2);
});
test('Mistral model reference never leaks into another provider or invents a percent',()=>{
 const data={period:'24h',usage_coverage:'complete_aggregate',request_count:1,
  connections:[{provider:'openrouter',name:'openrouter',connection_count:1,enabled_count:1}],
  models:[{name:'mistral-medium-latest',provider:'openrouter',requests:1,tokens:12}],
  quota:{records:[]}};
 const html=board().render(data,true);
 assert.doesNotMatch(html,/MISTRAL ORGANIZATION LIMITS/);
 assert.doesNotMatch(html,/625,000/);
 assert.match(html,/QUOTA UNKNOWN/);
 const noReport=board().render({...data,request_count:2},true);
 assert.match(noReport,/Mac requests unverified/);
 assert.doesNotMatch(noReport,/MISTRAL ORGANIZATION LIMITS/);
});

test('small-screen rings have responsive widths',()=>{
 assert.match(source,/max-width:380px/);
 assert.match(source,/grid-template-columns:80px minmax\(0,1fr\)/);
});
