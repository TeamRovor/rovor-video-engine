/* The workload popup must keep refreshing after its first replacement. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');

let clock=Math.floor(Date.now()/60000)*60000,isBoard=false,writes=0,reads=0,dayReads=0,hourReads=0,minuteReads=0,intervals=[],observer,requests=1;
const slot={
 hidden:false,
 classList:{contains:label=>label==='rvq-board'&&isBoard},
 querySelector:key=>key==='h3'?{textContent:isBoard?'All configured AI connections':'YOUR OMNIROUTE CONNECTIONS'}:null,
 set outerHTML(value){
   assert.match(value,/All configured AI connections/);
   writes++;isBoard=true;
 },
 get outerHTML(){return '';}
};
class Clock extends Date{static now(){return clock;}}
class Observe{constructor(fn){observer=fn;}observe(){}}
const drawer={hidden:false};
const document={
 hidden:false,body:{},
 getElementById:id=>id==='screen'?drawer:({}),
 querySelectorAll:()=>[slot]
};
const fetch=async url=>{
 if(!String(url).includes('/api/hud/omniroute'))return {ok:false};
 reads++;
 const hour=String(url).includes('period=1h');
 const minute=String(url).includes('period=1m');
 if(minute)minuteReads++;else if(hour)hourReads++;else dayReads++;
 return {ok:true,json:async()=>({
   period:minute?'1m':hour?'1h':'24h',request_count:requests,usage_coverage:'complete_aggregate',
   models:[{provider:'groq',name:'openai/gpt-oss-120b',requests,tokens:10}],
   source:'local_omniroute_read_only_bridge',
   snapshot_at:new Date(clock).toISOString(),
   connections:[{provider:'groq',name:'groq',connection_count:1,enabled_count:1}],
   connection_slots:[{provider:'groq',account_slot:1,enabled:true}],
   quota:{records:[]},workforce:{employees:[]}
 })};
};
const context={window:{},document,fetch,MutationObserver:Observe,
 setInterval:(fn,ms)=>{assert.equal(ms,10000);intervals.push(fn);},
 AbortSignal,Date:Clock};
const source=fs.readFileSync(path.join(__dirname,'../dashboard/command-center/native-v8-9/live-quota-board.js'),'utf8');
vm.runInNewContext(source,context);
const board=context.window.ROVOR_QUOTA_BOARD;
const flush=()=>new Promise(resolve=>setImmediate(resolve));

(async()=>{
 board.start();
 await flush();await flush();
 assert.equal(reads,3);assert.equal(dayReads,1);assert.equal(hourReads,1);assert.equal(minuteReads,1);assert.equal(writes,2,'one immediate unknown-safe paint, one settled report');
 assert.equal(isBoard,true);
 assert.equal(intervals.length,1);
 board.start();
 assert.equal(intervals.length,1,'repeated start must not install multiple timers');
 observer();
 await flush();
 assert.equal(writes,2,'rendering itself must not trigger an observer loop');
 clock+=11000;
 intervals[0]();
 await flush();await flush();
 assert.equal(reads,6,'rendered panel must refresh 24h, 1h and 1m');
 assert.equal(writes,2,'identical visible evidence must not replace the board');
 requests=2;clock+=11000;intervals[0]();await flush();await flush();
 assert.equal(reads,9,'skipping an unchanged paint must not stop future polling');
 assert.equal(writes,3,'changed measured requests must replace the rendered board');
 // Once a validated 24h report is already in the main HUD, reuse it instead
 // of requesting exactly the same source from the server a second time.
 clock+=11000;
 context.window.ROVOR_LIVE_OMNIROUTE_SNAPSHOT=()=>({
   source:'local_omniroute_read_only_bridge',period:'24h',
   snapshot_at:new Date(clock).toISOString(),
   connections:[{provider:'groq',name:'groq',connection_count:1,enabled_count:1}],
   connection_slots:[{provider:'groq',account_slot:1,enabled:true}],
   quota:{records:[]}
 });
 intervals[0]();await flush();await flush();
 assert.equal(reads,11,'verified shared 24h snapshot avoids duplicate 24h polling; minute and hourly still fetched');
 assert.equal(dayReads,3);assert.equal(hourReads,4);assert.equal(minuteReads,4);
 assert.equal(writes,4,'shared telemetry still refreshes the rendered popup');
 document.hidden=true;clock+=11000;
 intervals[0]();await flush();
 assert.equal(reads,11,'hidden HUD must not poll');
 document.hidden=false;
 drawer.hidden=true;clock+=11000;
 intervals[0]();await flush();
 assert.equal(reads,11,'closed Workload drawer must not keep polling seven private endpoints');
 drawer.hidden=false;clock+=11000;
 board.refresh();board.refresh();
 await flush();await flush();
 assert.equal(reads,13,'reopening Workload immediately refreshes the two missing windows once');
 assert.equal(hourReads,5);assert.equal(minuteReads,5);
 assert.equal(dayReads,3,'reopen must reuse the valid shared 24h snapshot');
 console.log('HUD popup refresh, hidden-drawer suspension and immediate reopen: PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});

