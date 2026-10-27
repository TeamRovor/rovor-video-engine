import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source=fs.readFileSync(
 new URL('../dashboard/command-center/native-v8-9/live-quota-board.js', import.meta.url),'utf8');

test('slow cloud ledger request never starts a second overlapping refresh',async()=>{
 const pending=[],intervals=[];
 let paints=0,localCalls=0;
 const board={
  hidden:false,
  classList:{contains:name=>name==='rvq-board'},
  querySelectorAll:()=>[],
  contains:()=>false,
  set outerHTML(html){assert.match(html,/rvq-board/);paints++;}
 };
 const document={
  hidden:false,activeElement:null,
  getElementById:()=>({}),
  querySelectorAll:selector=>selector==='#rovor-workload-popup .wl-card'?[board]:[]
 };
 const snapshot=()=>({
  source:'local_omniroute_read_only_bridge',
  period:'24h',
  snapshot_at:new Date().toISOString(),
  connections:[{provider:'groq',name:'Groq',connection_count:1,enabled_count:1}]
 });
 const window={ROVOR_LIVE_OMNIROUTE_SNAPSHOT:snapshot};
 const fetch=route=>{
  if(route==='/api/hud/omniroute?period=24h'){localCalls++;throw Error('duplicate gateway request');}
  assert.equal(route,'/api/ghost/status');
  return new Promise(resolve=>pending.push(resolve));
 };
 const MutationObserver=class{observe(){}};
 vm.runInNewContext(source,{window,document,fetch,MutationObserver,
  setInterval:(fn,ms)=>{intervals.push({fn,ms});return 1;},
  Date,Math,Number,String,Array,Map,Set,AbortSignal,
  console});
 window.ROVOR_QUOTA_BOARD.start();
 assert.equal(pending.length,1,'first cloud read should begin');
 assert.equal(intervals.length,1);
 assert.equal(intervals[0].ms,10000);
 // Simulate two scheduler firings while the first cloud request is stalled.
 intervals[0].fn();
 intervals[0].fn();
 assert.equal(pending.length,1,'only one cloud read may be in flight');
 assert.equal(localCalls,0,'validated 24h gateway snapshot should be reused');
 pending[0]({ok:true,json:async()=>({
  execution_source:'cloud_provider',observed_at:Date.now(),providers:[]
 })});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(paints,1,'only the first settled read paints the popup');
});
