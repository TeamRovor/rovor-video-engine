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
     started_at:now - 2000,human_review:'passed'}
  ]
};
const html=render(data,true,cloud);
assert.match(html,/Draft safe blog checklist/);
assert.match(html,/Mac workforce \/ local job history/);
assert.match(html,/Investigate scheduler pacing/);
assert.match(html,/Running not verified/);
assert.match(html,/Reason: paced wait/);
assert.ok(html.includes('46 / 50 claims in 24h'));
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


/* In the existing popup, employee bars must represent receipts only, never quota. */
const providerNames=['groq','gemini','cloudflare-ai','mistral','nvidia','openrouter','sambanova','cohere','huggingface'];
const receiptNow=Date.now();
const employeeCloud={
  execution_source:'cloud_provider',observed_at:receiptNow,
  providers:providerNames.map(provider=>({provider,credentials_configured:true,admission:'disabled_pending_verification'})),
  attempts:[
    {id:'w1',job_id:'work-1',employee:'Walter',provider:'groq',status:'needs_review',
      started_at:receiptNow-2000,tokens_input:15,tokens_output:40,actual_model:'openai/gpt-oss-20b'},
    {id:'w1',job_id:'work-1',employee:'Walter',provider:'groq',status:'needs_review',
      started_at:receiptNow-2000,tokens_input:15,tokens_output:40},
    {id:'w2',job_id:'work-2',employee:'Walter',provider:'groq',status:'needs_review',
      started_at:receiptNow-4000,tokens_input:20,tokens_output:60,actual_model:'<svg onload=alert(1)>'},
    {id:'j1',job_id:'work-3',employee:'Jane',provider:'openrouter',status:'failed',
      started_at:receiptNow-1000,tokens_input:12,tokens_output:10},
    {id:'canary',job_id:'canary-groq-owner',title:'PROVIDER CANARY (not task output)',
      employee:'Jesse',provider:'groq',status:'needs_review',started_at:receiptNow-500},
    {id:'old',job_id:'work-old',employee:'Gale',provider:'groq',status:'needs_review',
      started_at:receiptNow-86400001,tokens_input:30,tokens_output:40},
    {id:'unassigned',job_id:'unknown',employee:'Anonymous',provider:'groq',status:'needs_review',
      started_at:receiptNow-3000,tokens_input:25,tokens_output:10}
  ]
};
const employeeBoard=render(null,false,employeeCloud);
assert.match(employeeBoard,/Employee model usage/);
assert.match(employeeBoard,/3 ATTRIBUTED RECEIPTS/);
assert.equal((employeeBoard.match(/class="rvq-emp-row"/g)||[]).length,8);
assert.match(employeeBoard,/66\.7% of attributed receipt sample/);
assert.match(employeeBoard,/33\.3% of attributed receipt sample/);
assert.match(employeeBoard,/35 in \/ 100 out/);
assert.match(employeeBoard,/12 in \/ 10 out/);
assert.match(employeeBoard,/1 failed/);
assert.match(employeeBoard,/1 other returned receipts have no matching employee/);
assert.match(employeeBoard,/&lt;svg onload=alert\(1\)&gt;/);
assert.ok(!employeeBoard.includes('<svg onload='));
const staleEmployee=render(null,false,{...employeeCloud,observed_at:receiptNow-90000});
assert.match(staleEmployee,/LEDGER DISCONNECTED/);
assert.doesNotMatch(staleEmployee,/3 ATTRIBUTED RECEIPTS/);
assert.doesNotMatch(staleEmployee,/35 in \/ 100 out/);
console.log('HUD cloud employee usage meters: PASS');
