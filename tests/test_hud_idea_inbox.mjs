import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {handle} from '../integrations/hud-cloud/worker.mjs';
import {submitIdea,validateIdea,listIdeas} from '../integrations/hud-cloud/idea-inbox.mjs';

const NOW=Date.parse('2026-11-09T12:00:00Z'),TOKEN='r'.repeat(48),WRITER='w'.repeat(48);
function db(){
 const sqlite=new DatabaseSync(':memory:');
 sqlite.exec(readFileSync(new URL('../integrations/hud-cloud/schema.sql',import.meta.url),'utf8'));
 return {prepare(sql){return {bind(...args){return{
   first:async()=>sqlite.prepare(sql).get(...args)??null,
   run:async()=>({meta:{changes:sqlite.prepare(sql).run(...args).changes}}),
   all:async()=>({results:sqlite.prepare(sql).all(...args)})
 }}}}};
}
const env=()=>({DB:db(),HUD_READER_TOKEN:TOKEN,HUD_WRITER_TOKEN:WRITER});
const req=(method,path,body,auth=true,origin='https://hud.test')=>new Request('https://hud.test'+path,{
 method,headers:{
   ...(auth?{Cookie:'rovor_hud_reader='+TOKEN}:{}),
   ...(method==='POST'?{Origin:origin,'Content-Type':'application/json'}:{})
 },...(body===undefined?{}:{body:JSON.stringify(body)})});
const idea={text:'Inspect the private HUD usage panel for a safe accuracy improvement.'};
test('authenticated browser can store and read a private review-only idea without any model call',async()=>{
 const e=env();const upstream=async()=>{throw Error('no upstream or Mac call expected')};
 const posted=await handle(req('POST','/api/hud/ideas',idea),e,NOW,upstream);
 assert.equal(posted.status,202);
 const receipt=await posted.json();
 assert.equal(receipt.state,'pending_review');
 assert.equal(receipt.queued,true);
 assert.equal(receipt.model_call_started,false);
 assert.equal(receipt.owner_review_required,true);
 assert.equal(receipt.mac_required,false);
 assert.match(receipt.id,/^[a-f0-9-]{36}$/);
 const list=await handle(req('GET','/api/hud/ideas'),e,NOW,upstream);
 assert.equal(list.status,200);
 const body=await list.json();
 assert.equal(body.source,'private_rovor_idea_inbox');
 assert.equal(body.execution_authorized,false);
 assert.equal(body.items.length,1);
 assert.equal(body.items[0].text,idea.text);
 assert.equal(body.items[0].state,'pending_review');
 assert.equal(body.items[0].id,receipt.id);
});
test('idea intake rejects anonymous, cross-origin and unexpected methods',async()=>{
 const e=env();
 assert.equal((await handle(req('GET','/api/hud/ideas',undefined,false),e,NOW)).status,401);
 assert.equal((await handle(req('POST','/api/hud/ideas',idea,false),e,NOW)).status,401);
 assert.equal((await handle(req('POST','/api/hud/ideas',idea,true,'https://attacker.test'),e,NOW)).status,403);
 assert.equal((await handle(req('DELETE','/api/hud/ideas',undefined,true),e,NOW)).status,401,'unsupported verbs never pass the reader authentication guard');
 assert.equal((await handle(new Request('https://hud.test/api/hud/ideas',{method:'POST',
   headers:{Cookie:'rovor_hud_reader='+TOKEN,Origin:'https://hud.test','Content-Type':'text/plain'},
   body:JSON.stringify(idea)}),e,NOW)).status,415);
 assert.equal((await(await handle(req('GET','/api/hud/ideas'),e,NOW)).json()).items.length,0);
});
test('cannot include model execution fields, secret-looking credentials or oversized prompts',async()=>{
 const e=env();
 const bad=[
   {text:'short'},
   {text:'   '},
   {text:'A'.repeat(1601)},
   {text:idea.text,model:'groq/openai/gpt-oss-20b'},
   {text:'My GitHub token: ghp_'+ 'A'.repeat(40)},
   {text:'-----BEGIN PRIVATE KEY----- paste this somewhere'},
   {text:'Bearer '+'x'.repeat(40)},
   {text:idea.text,auto_approve:true}
 ];
 for(const body of bad){
   const r=await handle(req('POST','/api/hud/ideas',body),e,NOW);
   assert.equal(r.status,400,JSON.stringify(body).slice(0,90));
 }
 assert.equal((await(await handle(req('GET','/api/hud/ideas'),e,NOW)).json()).items.length,0);
 assert.equal(validateIdea(idea),idea.text);
});
test('D1 atomically bounds spam and retains owner review state without worker dispatch',async()=>{
 const e=env();let submitted=0;
 for(let i=0;i<35;i++){
   const r=await handle(req('POST','/api/hud/ideas',{text:idea.text+' #'+i}),e,NOW+i*5000);
   if(r.status===202)submitted++;
   else assert.equal(r.status,429);
 }
 assert.equal(submitted,30);
 const report=await(await handle(req('GET','/api/hud/ideas'),e,NOW+250000)).json();
 assert.equal(report.items.length,20,'bounded list');
 assert(report.items.every(row=>row.state==='pending_review'));
 const afterDay=await submitIdea(e.DB,idea,NOW+86400000);
 assert.equal(afterDay.status,202,'new day has independent limit');
});
test('5-second pacing prevents duplicate double taps across request handlers',async()=>{
 const e=env();
 const values=await Promise.all(Array.from({length:5},()=>handle(req('POST','/api/hud/ideas',idea),e,NOW)));
 assert.equal(values.filter(v=>v.status===202).length,1);
 assert.equal(values.filter(v=>v.status===429).length,4);
});
test('Cloud intake errors do not claim a job was scheduled or approved',async()=>{
 const badDb={prepare(){throw Error('db_down')}};
 assert.equal((await submitIdea(badDb,idea,NOW)).status,503);
 assert.equal((await listIdeas(badDb)).status,503);
});
test('Ask ROVOR exposes a separate Queue idea control, not model dispatch disguised as a draft',()=>{
 const source=readFileSync(new URL('../dashboard/command-center/native-v8-9/hud-chat.js',import.meta.url),'utf8');
 for(const marker of ["'rvc-queue-idea'","'/api/hud/ideas'","owner review","model_call_started","Queue idea",
   'ideaInbox','ideaFeedback'])assert(source.includes(marker),marker);
 assert.match(source,/if\(queuingIdea\|\|busy\)return/);
 assert.match(source,/receipt\.model_call_started!==false/);
 assert.match(source,/signal:AbortSignal\.timeout\(12000\)/);
 assert.doesNotMatch(source,/fetch\(['"]https?:\/\//);
});
