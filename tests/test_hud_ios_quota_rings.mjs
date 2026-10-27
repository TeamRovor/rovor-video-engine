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
 assert.equal((html.match(/role="img" aria-label="Provider quota unknown"/g)||[]).length,9);
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
test('small-screen rings have responsive widths',()=>{
 assert.match(source,/max-width:380px/);
 assert.match(source,/grid-template-columns:80px minmax\(0,1fr\)/);
});
