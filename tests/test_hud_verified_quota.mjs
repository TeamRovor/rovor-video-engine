import test from 'node:test';
import assert from 'node:assert/strict';
import {reduceProviderQuota} from '../tools/hud_verified_quota.mjs';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const now=Date.parse('2026-10-25T08:00:00Z');
const providers={connections:[
  {id:'account-1',provider:'groq',isActive:true,apiKey:'DO_NOT_COPY'},
  {id:'disabled',provider:'openrouter',isActive:false},
  {id:'account-3',provider:'gemini',isActive:true}
]};
test('only fresh authenticated account evidence generates percentages and reset dates',()=>{
  const data={caches:{
    'account-1':{fetchedAt:'2026-10-25T07:55:00Z',quotas:{
      modelA:{used:25,total:100,unit:'requests',resetAt:'2026-10-26T00:00:00Z'},
      modelB:{used:0,total:10,unit:'tokens'}
    }},
    'disabled':{fetchedAt:'2026-10-25T07:55:00Z',quotas:{no:{used:5,total:10}}},
    stranger:{fetchedAt:'2026-10-25T07:55:00Z',quotas:{no:{used:5,total:10}}},
    'account-3':{fetchedAt:'2026-10-24T01:00:00Z',quotas:{stale:{used:5,total:10}}}
  }};
  const d=reduceProviderQuota(providers,data,{now});
  assert.equal(d.records.length,2);
  assert.equal(d.records[0].used_percent,25);
  assert.equal(d.records[0].reset_at,'2026-10-26T00:00:00.000Z');
  assert.equal(d.records[1].reset_at,null);
  assert.equal(d.records[1].used_percent,0);
  assert.equal(JSON.stringify(d).includes('DO_NOT_COPY'),false);
});
test('invalid or missing denominators are not presented as 0 percent',()=>{
  const invalid={caches:{'account-1':{fetchedAt:'2026-10-25T07:59:00Z',quotas:{
    negative:{used:-1,total:10},over:{used:15,total:10},
    empty:{used:0,total:0},wrong:{used:'1',total:10}
  }}}};
  assert.equal(reduceProviderQuota(providers,invalid,{now}).records.length,0);
  assert.equal(reduceProviderQuota(providers,{}, {now}).freshness,'unavailable');
});
test('existing drawer quota board remains nine-connection grouped and escaped',()=>{
  const window={};
  const document={getElementById:()=>({})};
  const source=readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js',import.meta.url),'utf8');
  vm.runInNewContext(source,{window,document,Date,Math,Number,String,Array});
  const conns=Array.from({length:9},(_,i)=>({provider:'p'+i,name:i===0?'<untrusted>':'p'+i,connection_count:1,enabled_count:1}));
  const html=window.ROVOR_QUOTA_BOARD.render({connections:conns,quota:{records:[{provider:'p0',model_id:'modelX',used:25,total:100,used_percent:25,unit:'requests',reset_at:'2030-01-01T00:00:00Z',fetched_at:new Date().toISOString(),account_slot:1}]},models:[]},true);
  assert.equal((html.match(/class="rvq-provider"/g)||[]).length,9);
  assert.match(html,/25\.0%/);
  assert.match(html,/RESET WINDOW/);
  assert.match(html,/LIMIT/);
  assert(!html.includes('<untrusted>'));
  assert(html.includes('&lt;untrusted&gt;'));
});

test('expired reset hides cached percentage until a newer quota is observed',()=>{
  const doc={caches:{'account-1':{
    fetchedAt:'2026-10-25T07:58:00Z',
    quotas:{
      justExpired:{used:7,total:10,unit:'requests',resetAt:'2026-10-25T08:00:00Z'},
      alreadyExpired:{used:7,total:10,unit:'requests',resetAt:'2026-10-25T07:59:00Z'},
      stillOpen:{used:3,total:10,unit:'requests',resetAt:'2026-10-25T08:01:00Z'}
    }
  }}};
  const rows=reduceProviderQuota(providers,doc,{now}).records;
  assert.deepEqual(rows.map(row=>row.model_id),['stillOpen']);
  assert.equal(rows[0].used_percent,30);
  assert.equal(reduceProviderQuota(providers,doc,{now:now+61000}).records.length,0);
  // A newer provider report with a future window restores trustworthy bars.
  doc.caches['account-1'].fetchedAt='2026-10-25T08:02:00Z';
  doc.caches['account-1'].quotas.stillOpen.resetAt='2026-10-26T00:00:00Z';
  assert.equal(reduceProviderQuota(providers,doc,{now:now+180000}).records.length,1);
});

test('each of nine connection slots renders separately even when providers repeat',()=>{
  const window={},document={getElementById:()=>({})};
  const source=readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js',import.meta.url),'utf8');
  vm.runInNewContext(source,{window,document,Date,Math,Number,String,Array,Map});
  const connections=[{provider:'groq',name:'Groq',connection_count:4,enabled_count:3},
    {provider:'mistral',name:'Mistral',connection_count:3,enabled_count:2},
    {provider:'openrouter',name:'OpenRouter',connection_count:2,enabled_count:2}];
  const slots=connections.flatMap(g=>Array.from({length:g.connection_count},(_,i)=>({
    provider:g.provider,account_slot:i+1,enabled:i+1<=g.enabled_count
  })));
  const quota={records:[{provider:'groq',account_slot:3,model_id:'actual-model',
    used:20,total:100,used_percent:20,unit:'requests',reset_at:'2030-01-01T00:00:00Z',fetched_at:new Date().toISOString()}]};
  const html=window.ROVOR_QUOTA_BOARD.render({connections,connection_slots:slots,quota,snapshot_at:'2026-10-25T20:01:00Z'},true);
  assert.equal((html.match(/class="rvq-provider"/g)||[]).length,9);
  assert.equal((html.match(/aria-label="Reported quota used"/g)||[]).length,1);
  assert.match(html,/Enabled according to gateway: 7 \/ 9/);
  assert.match(html,/DISABLED/);
  assert.match(html,/QUOTA UNKNOWN/);
  assert(!html.includes('apiKey'));
  const offline=window.ROVOR_QUOTA_BOARD.render({connections,connection_slots:slots},false);
  assert.equal((offline.match(/class="rvq-provider"/g)||[]).length,9);
  // Missing fresh Mac telemetry is not evidence that any individual provider went offline.
  assert.match(offline,/MAC REPORT STALE/);
  assert(!offline.includes('20.0%'));
  const legacy=window.ROVOR_QUOTA_BOARD.render({connections,quota},true);
  assert.match(legacy,/ENABLEMENT UNKNOWN/);
  assert.match(legacy,/Unknown/);
});

test('private cloud admission and verified cloud quota remain separate from gateway quota',()=>{
  const window={},document={getElementById:()=>({})};
  const source=readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js',import.meta.url),'utf8');
  vm.runInNewContext(source,{window,document,Date,Math,Number,String,Array,Map});
  const ts=Date.now();
  const providers=Array.from({length:9},(_,i)=>({
    provider:i===0?'openrouter':'provider'+i,
    credentials_configured:true,admission:i===0?'eligible':'disabled_pending_verification',
    online_verified:false,last_check:{status:'catalog_received'},
    recorded_24h:i===0?{requests:11}:null,
    quota:i===0?{status:'verified',observed_at:ts,used:6,limit:50,unit:'requests',resets_at:ts+3600000}:null
  }));
  const cloud={execution_source:'cloud_provider',observed_at:ts,providers};
  // Cloud ledger can still report the nine configured provider identities when Mac is off.
  const cloudOnly=window.ROVOR_QUOTA_BOARD.render(null,false,cloud);
  assert.equal((cloudOnly.match(/class="rvq-provider"/g)||[]).length,9);
  assert.match(cloudOnly,/CLOUD LEDGER ONLY/);
  assert.match(cloudOnly,/CLOUD ROUTE NOT ELIGIBLE/);
  assert.match(cloudOnly,/Verified cloud limit/);
  assert.match(cloudOnly,/6 \/ 50 requests/);
  assert.match(cloudOnly,/12.0/);
  assert.match(cloudOnly,/NOT VERIFIED/);
  const gateway={
    connections:[{provider:'openrouter',name:'openrouter',connection_count:1,enabled_count:1}],
    quota:{records:[{provider:'openrouter',account_slot:1,model_id:'providerCache',
      used:0,total:50,used_percent:0,unit:'provider units',reset_at:new Date(ts+3600000).toISOString(),
      fetched_at:new Date(ts).toISOString()}]}
  };
  const combined=window.ROVOR_QUOTA_BOARD.render(gateway,true,cloud);
  assert.match(combined,/0.0%/);
  assert.match(combined,/12.0/);
  assert.match(combined,/OMNIROUTE CACHED REPORT/);
  assert.match(combined,/CLOUD WORKFORCE \/ SEPARATE SOURCE/);
  assert.equal((combined.match(/role="progressbar"/g)||[]).length,3);
  const expired=structuredClone(cloud);expired.providers[0].quota.resets_at=ts-1;
  const noCloudLimit=window.ROVOR_QUOTA_BOARD.render(null,false,expired);
  assert(!noCloudLimit.includes('6 / 50 requests'));
  assert.match(noCloudLimit,/Cloud quota and reset: unknown/);
});


test('cloud claim gate is displayed without fabricating limits or online status',()=>{
  const window={},document={getElementById:()=>({})};
  const source=readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js',import.meta.url),'utf8');
  vm.runInNewContext(source,{window,document,Date,Math,Number,String,Array,Map});
  const cloud={execution_source:'cloud_provider',observed_at:Date.now(),providers:[
    {provider:'groq',admission:'eligible',credentials_configured:true,online_verified:false,
      dispatch_gate:{provider:'groq',state:'blocked',reason:'account_request_cap'}},
    {provider:'gemini',admission:'disabled_pending_verification',credentials_configured:true,online_verified:false,
      dispatch_gate:{provider:'gemini',state:'ineligible',reason:'not_configured'}}
  ]};
  for(let i=2;i<9;i++)cloud.providers.push({provider:'provider'+i,admission:'disabled_pending_verification',credentials_configured:true,online_verified:false});
  const html=window.ROVOR_QUOTA_BOARD.render(null,false,cloud);
  assert.match(html,/Account request allowance reached/);
  assert.match(html,/No verified cloud route configuration/);
  assert.match(html,/NOT VERIFIED/);
  assert.match(html,/Cloud quota and reset: unknown/);
  assert.doesNotMatch(html,/Verified cloud limit/);
  const poisoned=structuredClone(cloud);
  poisoned.providers[0].dispatch_gate.reason='<img src=x onerror=alert(1)>';
  const noLeak=window.ROVOR_QUOTA_BOARD.render(null,false,poisoned);
  assert.doesNotMatch(noLeak,/<img src=x/);
  assert.match(noLeak,/Next cloud claim · Not reported/);
});


test('reviewed cloud jobs display canonical passed and failed states',()=>{
 const window={},document={getElementById:()=>({})};
 const source=readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js',import.meta.url),'utf8');
 vm.runInNewContext(source,{window,document,Date,Math,Number,String,Array,Map});
 const ps=['groq','gemini','cloudflare-ai','mistral','nvidia','openrouter','sambanova','cohere','huggingface'];
 const cloud={execution_source:'cloud_provider',observed_at:Date.now(),
  providers:ps.map(provider=>({provider,credentials_configured:true,admission:'disabled_pending_verification',online_verified:false})),
  attempts:[
   {provider:'groq',employee:'Walter',title:'Owner accepted',human_review:'passed',status:'needs_review',started_at:Date.now()-3000},
   {provider:'groq',employee:'Jane',title:'Owner rejected',human_review:'failed',status:'needs_review',started_at:Date.now()-2000},
   {provider:'groq',employee:'Gale',title:'Not reviewed',human_review:'not_recorded',status:'needs_review',started_at:Date.now()-1000}
  ]
 };
 const html=window.ROVOR_QUOTA_BOARD.render(null,false,cloud);
 assert.match(html,/Owner accepted/);
 assert.match(html,/Owner rejected/);
 assert.match(html,/PASS RECORDED/);
 assert.match(html,/FAIL RECORDED/);
 assert.equal((html.match(/AWAITING HUMAN REVIEW/g)||[]).length,1);
});


test('stale local quota cache cannot masquerade as fresh gateway usage',()=>{
 const window={},document={getElementById:()=>({})};
 const source=readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js',import.meta.url),'utf8');
 vm.runInNewContext(source,{window,document,Date,Math,Number,String,Array,Map});
 const now=Date.now();
 const snapshot={connections:[{provider:'openrouter',name:'OpenRouter',connection_count:1,enabled_count:1}],
  connection_slots:[{provider:'openrouter',account_slot:1,enabled:true}],
  snapshot_at:new Date(now).toISOString(),
  quota:{records:[{provider:'openrouter',account_slot:1,model_id:'free_daily',used:15,total:50,used_percent:30,
    unit:'requests',reset_at:new Date(now+3600000).toISOString(),
    fetched_at:new Date(now-3600000).toISOString()}]}};
 const stale=window.ROVOR_QUOTA_BOARD.render(snapshot,true);
 assert.match(stale,/QUOTA UNKNOWN/);
 assert.doesNotMatch(stale,/30\.0%/);
 assert.doesNotMatch(stale,/LIMITS REPORTED/);
 snapshot.quota.records[0].fetched_at=new Date(now).toISOString();
 const fresh=window.ROVOR_QUOTA_BOARD.render(snapshot,true);
 assert.match(fresh,/30\.0%/);
 assert.match(fresh,/LIMITS REPORTED/);
 delete snapshot.quota.records[0].fetched_at;
 const missing=window.ROVOR_QUOTA_BOARD.render(snapshot,true);
 assert.match(missing,/QUOTA UNKNOWN/);
 assert.doesNotMatch(missing,/30\.0%/);
});
