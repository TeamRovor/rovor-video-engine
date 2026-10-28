'use strict';
// Regression protection for the existing ROVOR native UI and the compact
// provider experience. This fixture does NOT call inference or use credentials.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const boardSource=fs.readFileSync(path.join(__dirname,'../dashboard/command-center/native-v8-9/live-quota-board.js'),'utf8');
const workload=fs.readFileSync(path.join(__dirname,'../dashboard/command-center/native-v8-9/workload-popup.css'),'utf8');
const providers=['groq','gemini','cloudflare-ai','mistral','nvidia','openrouter','sambanova','cohere','huggingface'];
function render(data,live,cloud=null) {
 const window={}, document={getElementById:()=>({})};
 vm.runInNewContext(boardSource,{window,document,Date,Math,Number,String,Array,Map,Set});
 return window.ROVOR_QUOTA_BOARD.render(data,live,cloud);
}
function nine() {
 return providers.map(provider=>({provider,name:provider,connection_count:1,enabled_count:1}));
}

test('compact nine-provider rings remain readable at desktop, tablet and phone widths',()=>{
 assert.match(boardSource,/\.rvq-overview\{display:grid;grid-template-columns:repeat\(5,minmax\(0,1fr\)\)/);
 assert.match(boardSource,/@media\(max-width:1150px\)\{#rovor-workload-popup \.rvq-overview\{grid-template-columns:repeat\(3,minmax\(0,1fr\)\)\}\}/);
 assert.match(boardSource,/@media\(max-width:650px\)\{[\s\S]*?\.rvq-overview\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
 assert.match(boardSource,/\.rvq-overview \.rvq-ring\{width:68px;height:68px\}/);
 assert.match(boardSource,/\.rvq-overview-name\{[^\n]*font:700 12px/);
 assert.match(boardSource,/\.rvq-overview-tile:hover,.*\.rvq-overview-tile:focus-visible/);
});

test('all nine original provider reports stay present and accessible in collapsible sections',()=>{
 const cloud={execution_source:'cloud_provider',observed_at:Date.now(),
  providers:providers.map(provider=>({provider,credentials_configured:true,admission:'disabled_pending_verification',online_verified:false}))};
 const html=render(null,false,cloud);
 assert.equal((html.match(/class="rvq-overview-tile"/g)||[]).length,9);
 assert.equal((html.match(/class="rvq-provider"/g)||[]).length,9);
 assert.equal((html.match(/class="rvq-provider-details"/g)||[]).length,9);
 assert.equal((html.match(/data-rvq-open-slot="/g)||[]).length,9);
 assert.equal((html.match(/role="img" aria-label="Provider quota unknown"/g)||[]).length,18);
 assert.match(html,/id="rvq-connections"/);
 assert.match(html,/id="rvq-review"/);
 assert.match(html,/id="rvq-team"/);
 assert.match(html,/id="rvq-reports"/);
 assert.match(html,/OWNER PASS \/ FAIL REVIEWS/);
 assert.match(html,/DATA SOURCES & VERIFICATION RULES/);
 assert.match(html,/NO FRESH REPORT|CLOUD LEDGER ONLY/);
});

test('one provider with actual Mac limit receipts is not nine verified providers',()=>{
 const now=new Date();
 const data={
  source:'local_omniroute_read_only_bridge',period:'24h',snapshot_at:now.toISOString(),
  connections:nine(),connection_slots:providers.map(provider=>({provider,account_slot:1,enabled:true})),
  quota:{records:[{provider:'openrouter',account_slot:1,model_id:'free_daily',used:10,total:50,
     used_percent:20,unit:'requests',fetched_at:now.toISOString(),
     reset_at:new Date(now.getTime()+3600000).toISOString()}]},models:[]
 };
 const html=render(data,true);
 assert.match(html,/PROVIDERS WITH MAC LIMIT DATA/);
 assert.match(html,/1 \/ 9/);
 assert.match(html,/Limit records: 1/);
 assert.match(html,/--rvq-angle:20.0%/);
 assert.match(html,/aria-label="Provider quota unknown"/);
 assert.doesNotMatch(html,/GATEWAY ENABLED · ACTIVE MODEL/);
});

test('stale telemetry is not described as proof a provider is offline',()=>{
 const html=render({connections:nine(),quota:{records:[]}},false);
 assert.match(html,/MAC REPORT STALE/);
 assert.match(html,/TELEMETRY STALE/);
 assert.doesNotMatch(boardSource,/!live\?'DISCONNECTED'/);
});

test('workload preview buttons and rows stay finger-sized without losing the design',()=>{
 assert.match(workload,/#workloadPanel \.wl-compact-tabs button\{[^\n]*min-height:44px/);
 assert.match(workload,/#workloadPanel \.wl-compact-row\{[^\n]*min-height:44px/);
 assert.match(workload,/#workloadPanel \.wl-compact-status\{font-size:11px/);
 assert.match(workload,/#workloadPanel \.wl-compact-name\{white-space:normal;[^\n]*font-size:12px/);
 assert.match(workload,/#rovor-workload-popup \.wl-period \.wl-button\{min-height:44px/);
});

test('traffic and allowance instruments use different visual hierarchy',()=>{
 const now=new Date().toISOString();
 const data={source:'local_omniroute_read_only_bridge',period:'24h',
  snapshot_at:now,request_count:1,usage_coverage:'complete_aggregate',
  connections:nine(),models:[{provider:'groq',name:'test',requests:1,tokens:12}],
  quota:{records:[]}};
 const html=render(data,true);
 assert.match(html,/MAC TRAFFIC/);
 assert.match(html,/QUOTA USED/);
 assert.match(html,/class="rvq-ring rvq-ring-traffic"/);
 assert.match(html,/Provider quota unknown/);
 assert.match(boardSource,/\.rvq-overview \.rvq-ring-traffic\{width:48px;height:48px/);
});

test('attention filter covers fresh actionable gates without treating idle or stale as blocked',()=>{
 const now=Date.now();
 const cloud={execution_source:'cloud_provider',observed_at:now,providers:providers.map(provider=>({
  provider,credentials_configured:true,dispatch_gate:{reason:provider==='groq'?'missing_secret':provider==='openrouter'?'paid_route_denied':'no_matching_unattempted_job'}
 }))};
 const html=render(null,false,cloud);
 assert.match(html,/SETUP \/ REVIEW 1/);
 assert.match(html,/data-rvq-filter="attention"/);
 assert.equal((html.match(/data-rvq-attention="true"/g)||[]).length,1);
 assert.equal((html.match(/data-rvq-attention="false"/g)||[]).length,8);
 assert.match(boardSource,/\.rvq-overview-controls button\{min-height:44px/);
 const old=render(null,false,{...cloud,observed_at:now-3600000});
 assert.doesNotMatch(old,/SETUP \/ REVIEW 1/);
 assert.doesNotMatch(old,/data-rvq-attention="true"/);
});

test('the original bundled workload preview remains explicitly unverified rather than live',()=>{
 const js=fs.readFileSync(path.join(__dirname,'../dashboard/command-center/native-v8-9/workload-popup.js'),'utf8');
 assert.match(js,/Owner-published Mac observation, not a live connection or inference proof/);
 assert.match(js,/LAST REPORT/);
 assert.match(js,/USAGE UNKNOWN/);
 assert.match(js,/No live link/);
 assert.match(js,/Live link missing/);
 assert.match(js,/NO VERIFIED LIVE MODEL TELEMETRY/);
});

test('different model allowances are never conflated into one provider-wide ring',()=>{
 const now=Date.now(),stamp=new Date(now).toISOString();
 const a={provider:'groq',account_slot:1,model_id:'model-a',used:5,total:20,used_percent:25,
   unit:'requests',fetched_at:stamp,reset_at:new Date(now+3600000).toISOString()};
 const data={connections:[{provider:'groq',name:'groq',connection_count:1,enabled_count:1}],
   quota:{records:[a,{...a,model_id:'model-b',used:2,total:10,used_percent:20}]}};
 const html=render(data,true);
 const tile=html.slice(html.indexOf('class="rvq-overview-tile"'),html.indexOf('id="rvq-review"'));
 assert.match(tile,/MULTIPLE MODEL LIMITS/);
 assert.match(tile,/2 separate limits/);
 assert.doesNotMatch(tile,/role="progressbar"/);
 assert.match(html,/model-a/);
 assert.match(html,/model-b/);
 const one=render({...data,quota:{records:[a]}},true);
 assert.match(one,/MAC MODEL LIMIT/);
 assert.match(one,/MODEL · model-a/);
 assert.match(html,/25\.0%/);
 assert.match(html,/20\.0%/);
});

test('fresh private review receipts give a truthful sample, not a claimed queue total',()=>{
 const now=Date.now();
 const cloud={execution_source:'cloud_provider',observed_at:now,
  providers:providers.map(provider=>({provider,credentials_configured:true})),
  attempts:[
   {id:'r1',provider:'groq',status:'needs_review',human_review:'not_recorded',started_at:now-1000,employee:'Mike',title:'Audit draft'},
   {id:'r1',provider:'groq',status:'needs_review',human_review:'not_recorded',started_at:now-1000,employee:'Mike',title:'Duplicated draft'},
   {id:'r2',provider:'groq',status:'needs_review',human_review:'passed',started_at:now-2000,title:'Approved draft'},
   {id:'r3',provider:'groq',status:'needs_review',human_review:'not_recorded',started_at:now-3000,job_id:'canary-test',title:'Canary draft'}
  ]};
 const html=render(null,false,cloud);
 const review=html.slice(html.indexOf('id="rvq-review"'),html.indexOf('id="rvq-team"'));
 assert.match(html,/REVIEW · 1\\+/);
 assert.match(review,/1 returned cloud receipt awaiting PASS \/ FAIL/);
 assert.match(review,/Audit draft/);
 assert.doesNotMatch(review,/Duplicated draft|Canary draft|Approved draft/);
 assert.match(review,/not the complete private owner queue/);
 const stale=render(null,false,{...cloud,observed_at:now-600000});
 assert.match(stale,/No fresh private cloud review sample/);
 const incomplete=render(null,false,{...cloud,attempts:undefined});
 assert.match(incomplete,/No fresh private cloud review sample/);
 assert.doesNotMatch(stale,/REVIEW · 1/);
});

test('cloud verification gates stay distinct from Mac and paid-route safety',()=>{
 const cloud={execution_source:'cloud_provider',observed_at:Date.now(),
  providers:[
   {provider:'groq',credentials_configured:true,admission:'eligibility_expired'},
   {provider:'openrouter',credentials_configured:true,admission:'disabled_pending_verification'},
   {provider:'gemini',credentials_configured:true,admission:'eligible',dispatch_gate:{reason:'paid_route_denied'}}
  ]};
 const html=render(null,false,cloud);
 assert.match(html,/CLOUD ELIGIBILITY EXPIRED/);
 assert.match(html,/CLOUD VERIFICATION PENDING/);
 assert.match(html,/SETUP \/ REVIEW 2/);
 assert.equal((html.match(/data-rvq-attention="true"/g)||[]).length,2);
 assert.equal((html.match(/data-rvq-attention="false"/g)||[]).length,1);
});
