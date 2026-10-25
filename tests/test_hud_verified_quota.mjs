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
  const html=window.ROVOR_QUOTA_BOARD.render({connections:conns,quota:{records:[{provider:'p0',model_id:'modelX',used:25,total:100,used_percent:25,unit:'requests',reset_at:'2026-10-26T00:00:00Z',fetched_at:'2026-10-25T07:55:00Z',account_slot:1}]},models:[]},true);
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
