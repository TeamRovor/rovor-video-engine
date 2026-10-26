import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const code=readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js',import.meta.url),'utf8');
function board(){
 const window={};
 // The pure renderer only calls mount(); report an existing style tag to avoid
 // injecting CSS in the Node test environment.
 const document={getElementById:()=>({})};
 runInNewContext(code,{window,document,Date,Number,String,Array,Math});
 return window.ROVOR_QUOTA_BOARD;
}
const data={
 source:'local_omniroute_read_only_bridge',snapshot_at:new Date().toISOString(),
 usage_coverage:'complete_aggregate',
 connections:[{provider:'openrouter',name:'openrouter',connection_count:1,enabled_count:1},
              {provider:'groq',name:'groq',connection_count:1,enabled_count:1}],
 connection_slots:[{provider:'openrouter',account_slot:1,enabled:true},{provider:'groq',account_slot:1,enabled:true}],
 models:[{provider:'openrouter',name:'cohere/north-mini-code:free',requests:8,tokens:500}],
 quota:{records:[]},
 workforce:{employees:[{name:'Jane',status:'draft_ready_for_human_review',
   latest_job:{task:'Local storyboard notes',assigned_route:'rovor-fast-free-v1',actual_model:null}}]}
};
const cloud=()=>({
 execution_source:'cloud_provider',observed_at:Date.now(),
 providers:[
  {provider:'openrouter',admission:'eligible',recorded_24h:{requests:2},quota:{status:'verified',
   used:2,limit:50,resets_at:Date.now()+3600000,observed_at:Date.now(),unit:'requests'}},
  {provider:'groq',admission:'disabled_pending_verification',recorded_24h:null}],
 attempts:[
  {provider:'openrouter',employee:'Hank',title:'Website launch rubric',
   actual_model:'cohere/north-mini-code:free',status:'needs_review',
   human_review:'not_recorded',tokens_input:126,tokens_output:1288,finished_at:Date.now()-120000},
  {provider:'openrouter',employee:'Saul',title:'Approved inquiry copy',
   actual_model:'cohere/north-mini-code:free',status:'needs_review',
   human_review:'pass',tokens_input:142,tokens_output:184,finished_at:Date.now()-240000},
  {provider:'groq',employee:'Gus',title:'Failed canary',
   actual_model:null,requested_model:'model-requested',status:'failed',human_review:'not_recorded',
   tokens_input:null,tokens_output:null,finished_at:Date.now()-600000}
 ]
});
test('existing popup renders provider-attributed job history, owner review and tokens without claiming live execution',()=>{
 const html=board().render(data,true,cloud());
 assert.match(html,/Website launch rubric/);
 assert.match(html,/Employee: Hank/);
 assert.match(html,/126 input \/ 1,288 output tokens/);
 assert.match(html,/No owner PASS\/FAIL recorded/);
 assert.match(html,/Approved inquiry copy/);
 assert.match(html,/PASS — owner reviewed/);
 assert.match(html,/Failed canary/);
 assert.match(html,/requested model-requested/);
 assert.match(html,/Actual model: unverified/);
 assert.match(html,/OmniRoute attributed model requests \(24h\): 8/);
 assert.match(html,/Local Mac employee jobs/);
 assert.match(html,/Local storyboard notes/);
 assert.match(html,/actual upstream provider\/model not independently attributed/);
 assert.doesNotMatch(html,/Verified running now: YES/);
});
test('missing receipts do not invent provider jobs and untrusted job text is escaped',()=>{
 const c=cloud();
 c.attempts=[{provider:'openrouter',title:'<img src=x onerror=alert(1)>',
  employee:'<script>test</script>',status:'needs_review',human_review:'not_recorded'}];
 const html=board().render(data,true,c);
 assert.match(html,/&lt;img src=x onerror=alert\(1\)&gt;/);
 assert.match(html,/&lt;script&gt;test&lt;\/script&gt;/);
 assert.doesNotMatch(html,/<img src=x/);
 assert.match(html,/No recorded cloud inference jobs for this provider/);
});
test('stale or disconnected cloud evidence cannot be presented as fresh jobs',()=>{
 const stale=cloud();stale.observed_at=Date.now()-3600000;
 const html=board().render(data,true,stale);
 assert.doesNotMatch(html,/Website launch rubric/);
 assert.match(html,/CLOUD JOB HISTORY · unavailable/);
});
