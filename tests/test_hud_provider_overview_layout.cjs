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
 assert.match(boardSource,/\.rvq-overview-name\{[^\\n]*font:700 12px/);
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
