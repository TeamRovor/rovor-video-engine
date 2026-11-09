import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {handle} from '../integrations/hud-cloud/worker.mjs';
import {validateDiscovery,submitDiscovery,discoveryStatus,DAILY_AUTOMATED_LIMIT} from '../integrations/hud-cloud/discovery-inbox.mjs';
const NOW=Date.parse('2026-11-09T14:00:00Z'),READER='r'.repeat(48),WRITER='w'.repeat(48);
const uuid=i=>String(i).padStart(8,'0')+'-1234-1234-1234-123456789abc';
function db(){
 const sqlite=new DatabaseSync(':memory:');
 sqlite.exec(readFileSync(new URL('../integrations/hud-cloud/schema.sql',import.meta.url),'utf8'));
 return {prepare(sql){return {bind(...v){return {
   first:async()=>sqlite.prepare(sql).get(...v)??null,
   all:async()=>({results:sqlite.prepare(sql).all(...v)}),
   run:async()=>({meta:{changes:sqlite.prepare(sql).run(...v).changes}})
 }}}}};
}
const env=()=>({DB:db(),HUD_READER_TOKEN:READER,HUD_WRITER_TOKEN:WRITER});
const idea=i=>({key:'run-'+(100+i),priority:95,
 text:'[ROVOR-DISCOVERY:run-'+(100+i)+'] Investigate failed GitHub CI evidence and propose a reviewed fix.'});
const request=(method,path,body,token=WRITER)=>new Request('https://hud.test'+path,{
 method,headers:{Authorization:'Bearer '+token,...(body?{'Content-Type':'application/json'}:{})},
 ...(body?{body:JSON.stringify(body)}:{})});
test('writer can store one durable non-executing finding and reader can see it privately',async()=>{
 const e=env();
 const posted=await handle(request('POST','/api/hud/discovery',idea(1)),e,NOW);
 assert.equal(posted.status,202);
 const receipt=await posted.json();
 assert.equal(receipt.state,'pending_review');
 assert.equal(receipt.source,'autonomous_discovery');
 assert.equal(receipt.owner_review_required,true);
 assert.equal(receipt.model_call_started,false);
 assert.equal(receipt.execution_authorized,false);
 const list=await handle(request('GET','/api/hud/ideas',undefined,READER),e,NOW);
 assert.equal(list.status,200);
 const data=await list.json();
 assert.equal(data.items.length,1);
 assert.equal(data.items[0].source,'autonomous_discovery');
 assert.equal(data.items[0].state,'pending_review');
 assert.equal(data.items[0].id,receipt.id);
 assert.match(data.items[0].text,/run-101/);
});
test('reader credentials never authorize the unattended discovery writer endpoint',async()=>{
 const e=env();
 for(const path of ['/api/hud/discovery','/api/hud/discovery/status']){
  const method=path.endsWith('/status')?'GET':'POST';
  const r=await handle(request(method,path,method==='POST'?idea(2):undefined,READER),e,NOW);
  assert.equal(r.status,401);
  const anon=await handle(request(method,path,method==='POST'?idea(2):undefined,''),e,NOW);
  assert.equal(anon.status,401);
 }
 assert.equal((await handle(request('GET','/api/hud/discovery/status'),e,NOW)).status,200);
 assert.equal((await(await handle(request('GET','/api/hud/ideas',undefined,READER),e,NOW)).json()).items.length,0);
});
test('each GitHub evidence key has an immutable review receipt even after inbox pages change',async()=>{
 const e=env(),entry=idea(3);
 let first=await submitDiscovery(e.DB,entry,NOW,()=>uuid(1));
 assert.equal(first.status,202);
 let repeated=await submitDiscovery(e.DB,entry,NOW+86400000,()=>uuid(2));
 assert.equal(repeated.status,409);
 assert.equal(repeated.body.state,'already_recorded');
 const status=await discoveryStatus(e.DB,NOW+86400000);
 assert.equal(status.status,200);
 assert(status.body.recent_keys.includes('run-103'));
 assert.equal(status.body.submitted_today,0,'duplicate does not charge a different day');
});
test('global six-per-UTC-day limit persists and resets with next day',async()=>{
 const e=env();
 assert.equal(DAILY_AUTOMATED_LIMIT,6);
 for(let i=0;i<6;i++)assert.equal((await submitDiscovery(e.DB,idea(i+10),NOW+i*1000,()=>uuid(10+i))).status,202);
 const exceeded=await submitDiscovery(e.DB,idea(20),NOW+30000,()=>uuid(20));
 assert.equal(exceeded.status,429);
 assert.equal(exceeded.body.error,'daily_discovery_budget_reached');
 assert.equal((await discoveryStatus(e.DB,NOW+30000)).body.submitted_today,6);
 assert.equal((await submitDiscovery(e.DB,idea(20),NOW+86400000,()=>uuid(21))).status,202);
 assert.equal((await discoveryStatus(e.DB,NOW+86400000)).body.submitted_today,1);
 const all=await(await handle(request('GET','/api/hud/ideas',undefined,READER),e,NOW+86400000)).json();
 assert.equal(all.items.length,7);
 assert(all.items.every(x=>x.state==='pending_review'));
});
test('concurrent runners cannot exceed six accepted proposals or duplicate one evidence key',async()=>{
 const e=env();
 const results=await Promise.all(Array.from({length:20},(_,i)=>
   submitDiscovery(e.DB,idea(200+i),NOW,()=>uuid(200+i))));
 assert.equal(results.filter(x=>x.status===202).length,6);
 assert.equal(results.filter(x=>x.status===429).length,14);
 const same=await Promise.all(Array.from({length:5},(_,i)=>
   submitDiscovery(e.DB,idea(200),NOW+1000,()=>uuid(400+i))));
 assert(same.every(x=>x.status===409));
 assert.equal((await discoveryStatus(e.DB,NOW)).body.submitted_today,6);
});
test('malformed and credential-looking findings are rejected before database writes',async()=>{
 const e=env(),bad=[
 {text:'[ROVOR-DISCOVERY:run-1] work',key:'../.env',priority:90},
 {...idea(40),priority:0},{...idea(40),model:'free'},
 {...idea(40),text:'arbitrary ungrounded story'},
 {...idea(40),text:'[ROVOR-DISCOVERY:run-140] Bearer '+ 's'.repeat(40)},
 {...idea(40),key:'issue-55'},{...idea(40),key:'run-0'}
 ];
 for(const value of bad){
  assert.equal(validateDiscovery(value),null);
  assert.equal((await handle(request('POST','/api/hud/discovery',value),e,NOW)).status,400);
 }
 assert.equal((await discoveryStatus(e.DB,NOW)).body.submitted_today,0);
});
test('missing D1 table fails closed instead of silently using visible inbox count',async()=>{
 const e=env(),unavailable={prepare(){throw Error('missing_d1_schema')}};
 assert.equal((await submitDiscovery(unavailable,idea(1),NOW)).status,503);
 assert.equal((await discoveryStatus(unavailable,NOW)).status,503);
 assert.equal((await handle(request('POST','/api/hud/discovery',idea(9)),{...e,DB:unavailable},NOW)).status,503);
});
