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
test('small-screen rings have responsive widths',()=>{
 assert.match(source,/max-width:380px/);
 assert.match(source,/grid-template-columns:80px minmax\(0,1fr\)/);
});
