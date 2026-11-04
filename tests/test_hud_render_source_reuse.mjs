import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source=fs.readFileSync(
 new URL('../dashboard/command-center/native-v8-9/live-quota-board.js', import.meta.url),'utf8');

function load(){
 const intervals=[],pending=[];
 const board={hidden:false,classList:{contains:n=>n==='rvq-board'},querySelectorAll:()=>[],contains:()=>false,set outerHTML(h){board.html=h;}};
 const document={hidden:false,activeElement:null,getElementById:()=>({}),
  querySelectorAll:s=>s==='#rovor-workload-popup .wl-card'?[board]:[]};
 const snapshot=()=>({source:'local_omniroute_read_only_bridge',period:'24h',snapshot_at:new Date().toISOString(),
  connections:[{provider:'groq',name:'Groq',connection_count:1,enabled_count:1}]});
 const window={ROVOR_LIVE_OMNIROUTE_SNAPSHOT:snapshot};
 const fetch=async route=>{
  if(route==='/api/ghost/status')return {ok:true,json:async()=>({execution_source:'cloud_provider',observed_at:Date.now(),providers:[]})};
  return {ok:false};
 };
 vm.runInNewContext(source,{window,document,fetch,MutationObserver:class{observe(){}},
  setInterval:(fn,ms)=>{intervals.push({fn,ms});return 1;},
  Date,Math,Number,String,Array,Map,Set,Promise,AbortSignal,console});
 return {window,board,snapshot,pending};
}

test('popup repaint without sources reuses fresh sync results, then fails closed after 15s',async()=>{
 const {window,board,snapshot}=load();
 window.ROVOR_QUOTA_BOARD.start();
 await new Promise(r=>setImmediate(r));
 assert.match(board.html,/rvq-board/);
 const reused=window.ROVOR_QUOTA_BOARD.render(snapshot(),true);
 const explicit=window.ROVOR_QUOTA_BOARD.render(snapshot(),true,null,null,null,null);
 assert.notEqual(reused,explicit,'omitted sources reuse the last settled cloud ledger');
 const realNow=Date.now;
 Date.now=()=>realNow()+16000;
 try{
  const expired=window.ROVOR_QUOTA_BOARD.render(snapshot(),true);
  assert.equal(expired,explicit,'expired sources must never be reused');
 }finally{Date.now=realNow;}
});

test('quota records stay live across one 70-minute OmniRoute sync cycle but expire after 175 minutes',()=>{
 const {window}=load();
 const records=minutes=>({source:'local_omniroute_read_only_bridge',period:'24h',snapshot_at:new Date().toISOString(),
  connections:[{provider:'groq',name:'Groq',connection_count:1,enabled_count:1}],
  quota:{records:[{provider:'groq',account_slot:1,model_id:'groq/m',used:25,total:100,used_percent:25,unit:'requests',
   reset_at:null,fetched_at:new Date(Date.now()-minutes*60000).toISOString()}]}});
 const limits=html=>html.match(/Limit records: (\d+)/)[1];
 assert.equal(limits(window.ROVOR_QUOTA_BOARD.render(records(60),true,null,null,null,null)),'1');
 assert.equal(limits(window.ROVOR_QUOTA_BOARD.render(records(170),true,null,null,null,null)),'1');
 assert.equal(limits(window.ROVOR_QUOTA_BOARD.render(records(200),true,null,null,null,null)),'0');
});
