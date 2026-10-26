/* Offline UI regression: receipts must show correct provider/employee and stay escaped. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const hudPath=path.join(__dirname,'../dashboard/command-center/native-v8-9/live-quota-board.js');
const context={
  window:{},
  document:{getElementById:()=>({})},
};
vm.runInNewContext(fs.readFileSync(hudPath,'utf8'),context,{filename:hudPath});
const render=context.window.ROVOR_QUOTA_BOARD.render;
assert.equal(typeof render,'function');

const now=Date.now();
const data={
  source:'local_omniroute_read_only_bridge',
  snapshot_at:new Date(now).toISOString(),
  connections:[
    {provider:'groq',name:'groq',connection_count:1,enabled_count:1},
    {provider:'openrouter',name:'openrouter',connection_count:1,enabled_count:1}
  ],
  connection_slots:[
    {provider:'groq',account_slot:1,enabled:true},
    {provider:'openrouter',account_slot:1,enabled:true}
  ],
  quota:{records:[]},
  workforce:{dispatch:{status:'recent_scheduler_report',reason:'paced_wait',claims_last_24h:46,max_claims_24h:50,queued:1,running:0,needs_review:92,last_tick_executed:0,next_eligible_at:Math.floor(now/1000)+900},employees:[
    {id:'mike',name:'Mike',status:'pending_or_failed_review',
     queued_jobs:0,running_jobs:0,online_verified:false,
     latest_job:{task:'Investigate scheduler pacing',
                 assigned_route:'rovor-fast-free-v1'}}
  ]}
};
const cloud={
  execution_source:'cloud_provider',observed_at:now,
  providers:[
    {provider:'groq',admission:'eligible',recorded_24h:{requests:1}},
    {provider:'openrouter',admission:'eligible',recorded_24h:{requests:0}}
  ],
  attempts:[
    {id:'receipt1',provider:'groq',employee:'Jane',
     title:'Draft safe blog checklist',status:'needs_review',
     actual_model:'openai/gpt-oss-20b',
     tokens_input:14,tokens_output:12,
     started_at:now - 1000,human_review:'not_recorded'},
    {id:'receipt2',provider:'groq',employee:'Gale',
     title:'<img src=x onerror=alert(1)>',status:'needs_review',
     requested_model:'openai/gpt-oss-120b',
     tokens_input:12,tokens_output:20,
     started_at:now - 2000,human_review:'approved'}
  ]
};
const html=render(data,true,cloud);
assert.match(html,/Draft safe blog checklist/);
assert.match(html,/Mac workforce \/ local job history/);
assert.match(html,/Investigate scheduler pacing/);
assert.match(html,/Running not verified/);
assert.match(html,/Reason: paced wait/);
assert.match(html,/46 \\/ 50 claims in 24h/);
assert.match(html,/Needs review 92/);
const old=render({...data,workforce:{...data.workforce,dispatch:{status:'unavailable_or_stale'}}},true,cloud);
assert.ok(!old.includes('46 / 50 claims in 24h'));
assert.match(old,/No recent verified pacing counters available/);
assert.ok(!html.includes('Mike is online'));

assert.match(html,/Jane/);
assert.match(html,/14 in \/ 12 out/);
assert.match(html,/AWAITING HUMAN REVIEW/);
assert.match(html,/PASS RECORDED/);
assert.match(html,/&lt;img src=x onerror=alert\(1\)&gt;/);
assert.ok(!html.includes('<img src=x onerror'));
const groq=html.split('CONNECTION 01')[1].split('CONNECTION 02')[0];
const openrouter=html.split('CONNECTION 02')[1];
assert.ok(groq.includes('Draft safe blog checklist'));
assert.ok(!openrouter.includes('Draft safe blog checklist'),
  'Do not assign Groq work to another provider');
assert.match(openrouter,/No recorded cloud inference job for this provider/);
const stale=render(data,true,{...cloud,observed_at:now-60000});
assert.ok(!stale.includes('Draft safe blog checklist'),
  'Stale cloud inference receipts must not be presented as fresh');
console.log('HUD per-provider cloud receipt attribution: PASS');
