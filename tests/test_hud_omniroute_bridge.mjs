import http from 'node:http';import test from 'node:test';import assert from 'node:assert/strict';
import {normalize,normalizeOwned,createCollector,createBridge} from '../tools/hud_omniroute_bridge.mjs';
import {reduceProviderQuota} from '../tools/hud_verified_quota.mjs';
const catalog={data:Array.from({length:12},(_,i)=>({id:'provider/model-'+i,owned_by:'provider'})).concat({id:'rovor-fast',owned_by:'combo'})};
const usage={summary:{totalRequests:10,uniqueModels:2},byModel:[{rawModel:'model-0',provider:'provider',requests:7,totalTokens:70},{rawModel:'model-1',provider:'provider',requests:3,totalTokens:30}]};
test('full catalog, exact measured shares, unknown quota and unobserved usage',()=>{const d=normalize(catalog,usage);assert.equal(d.inventory_count,12);assert.equal(d.models.length,12);assert.equal(d.models[0].request_share_percent,70);assert.equal(d.models[2].requests,null);assert.equal(d.models[0].quota_used_percent,null);assert.equal(d.usage_coverage,'complete_aggregate');});
test('partial aggregates are labeled and ambiguous aliases never duplicate counts',()=>{const d=normalize({data:[{id:'a/m',owned_by:'x'},{id:'b/m',owned_by:'x'}]},{summary:{totalRequests:30,uniqueModels:55},byModel:[{rawModel:'m',provider:'x',requests:3,totalTokens:1}]});assert.equal(d.usage_coverage,'partial_top_50_or_unattributed');assert.equal(d.models.filter(m=>m.requests===3).length,1);assert.equal(d.models.filter(m=>m.requests===null).length,2);});
test('explicit zero is distinct from unavailable and raw secrets never leave reducer',()=>{const x=structuredClone(usage);x.secret='private';const d=normalize(catalog,x);assert(!JSON.stringify(d).includes('private'));assert.equal(normalize(catalog,{summary:{totalRequests:0,uniqueModels:0},byModel:[]}).request_count,0);assert.throws(()=>normalize(catalog,{}));});
test('duplicate, inconsistent and malformed rows fail closed',()=>{assert.throws(()=>normalize(catalog,{...usage,byModel:[usage.byModel[0],usage.byModel[0]]}));assert.throws(()=>normalize(catalog,{...usage,summary:{totalRequests:2,uniqueModels:2}}));assert.throws(()=>normalize({data:[]},usage));});
test('collector deduplicates concurrent reads, refreshes usage after 5s and catalog after 60s',async()=>{let now=100000,calls=[];const collect=createCollector(async p=>{calls.push(p);if(p==='/api/providers')return{connections:[{provider:'provider'}]};if(p.startsWith('/api/usage/analytics?'))return usage;if(p.startsWith('/api/usage/call-logs?'))return{logs:[]};return{records:[]};},{clock:()=>now});await Promise.all([collect('24h'),collect('24h')]);assert.equal(calls.length,4);assert(calls.some(p=>p.startsWith('/api/usage/call-logs?')));assert.equal(calls[3],'/api/usage/provider-limits');now+=6000;await collect('24h');assert.equal(calls.length,6);assert(calls[4].includes('endDate='));now+=60000;await collect('24h');assert.equal(calls.length,10);await assert.rejects(collect('bad'));});
test('HTTP pairing, auth, whitelist, no proxy, no stale fallback, no mutations',async t=>{let broken=false;const b=createBridge({collect:async()=>{if(broken)throw Error('SECRET');return normalize(catalog,usage);},hud:'<body>ROVOR</body>',adapter:'/* adapter */',pairCode:'pair-secret'});const port=await b.listen();t.after(()=>new Promise(r=>b.server.close(r)));const base='http://127.0.0.1:'+port;
assert.equal((await fetch(base+'/api/hud/omniroute')).status,401);
assert.equal(await new Promise((resolve,reject)=>{const req=http.get(base+'/',{headers:{Host:'evil.example'}},res=>{res.resume();resolve(res.statusCode)});req.on('error',reject)}),403);
assert.equal((await fetch(base+'/pair',{method:'POST',headers:{Origin:'https://evil.example'},body:'{"code":"pair-secret"}'})).status,403);
assert.equal((await fetch(base+'/pair',{method:'POST',headers:{Origin:base},body:JSON.stringify({code:'é'.repeat(11)})})).status,401);
const pair=await fetch(base+'/pair',{method:'POST',headers:{Origin:base},body:'{"code":"pair-secret"}'});assert.equal(pair.status,200);const cookie=pair.headers.get('set-cookie').split(';')[0];const headers={Cookie:cookie};
assert.equal((await fetch(base+'/pair',{method:'POST',headers:{Origin:base},body:'{"code":"pair-secret"}'})).status,401);
assert((await (await fetch(base+'/',{headers})).text()).includes('ROVOR_START_OMNIROUTE'));
const d=await (await fetch(base+'/api/hud/omniroute',{headers})).json();assert.equal(d.models.length,12);
assert.equal((await fetch(base+'/api/providers',{headers})).status,404);
assert.equal((await fetch(base+'/api/hud/omniroute',{method:'POST',headers})).status,405);
assert.equal((await fetch(base+'/api/hud/omniroute?period=bad',{headers})).status,400);
broken=true;const failed=await fetch(base+'/api/hud/omniroute',{headers});assert.equal(failed.status,503);assert(!(await failed.text()).includes('SECRET'));
});


test('CLI starts through a linked directory and cannot silently exit before preflight',async()=>{
  const {mkdtempSync,symlinkSync,rmSync}=await import('node:fs');
  const {tmpdir}=await import('node:os');
  const {join,resolve}=await import('node:path');
  const {spawnSync}=await import('node:child_process');
  const dir=mkdtempSync(join(tmpdir(),'rovor-linked-start-'));
  try{
    symlinkSync(resolve('tools'),join(dir,'linked-tools'),'dir');
    for(const script of [resolve('tools/hud_omniroute_bridge.mjs'),join(dir,'linked-tools/hud_omniroute_bridge.mjs')]){
      const child=spawnSync(process.execPath,[script],{cwd:dir,env:{...process.env,HOME:dir,PATH:'',OMNIROUTE_CLI:''},encoding:'utf8',timeout:5000});
      assert.equal(child.status,1,'Missing gateway/CLI must visibly fail, not silently skip main');
      assert.match(child.stderr,/HUD bridge could not connect/);
    }
  }finally{rmSync(dir,{recursive:true,force:true});}
});


test('published HUD origin pairs for snapshot-only bearer access; other origins and scopes denied',async t=>{
 const origin='https://teamrovor.github.io';
 const b=createBridge({collect:async()=>normalize(catalog,usage),hud:'<body>HUD</body>',adapter:'',pairCode:'read-only-pair'});
 const port=await b.listen();t.after(()=>new Promise(r=>b.server.close(r)));const base='http://127.0.0.1:'+port;
 const pre=await fetch(base+'/api/hud/omniroute',{method:'OPTIONS',headers:{Origin:origin,'Access-Control-Request-Headers':'authorization','Sec-Fetch-Site':'cross-site'}});
 assert.equal(pre.status,204);assert.equal(pre.headers.get('access-control-allow-origin'),origin);
 assert.equal((await fetch(base+'/pair/external',{method:'POST',headers:{Origin:'https://evil.example'},body:JSON.stringify({code:'read-only-pair'})})).status,403);
 const paired=await fetch(base+'/pair/external',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({code:'read-only-pair'})});assert.equal(paired.status,200);
 const data=await paired.json();assert.equal(data.scope,'read_hud_snapshot');assert.equal(paired.headers.get('set-cookie'),null);
 const headers={Origin:origin,Authorization:'Bearer '+data.token};
 const res=await fetch(base+'/api/hud/omniroute',{headers});assert.equal(res.status,200);assert.equal((await res.json()).inventory_count,12);
 assert.equal((await fetch(base+'/hud-live.js',{headers})).status,401);
 assert.equal((await fetch(base+'/api/hud/omniroute',{headers:{Origin:'https://evil.example',Authorization:'Bearer '+data.token}})).status,403);
 assert.equal((await fetch(base+'/api/hud/omniroute',{method:'POST',headers})).status,405);
 assert.equal((await fetch(base+'/pair/external',{method:'POST',headers:{Origin:origin},body:JSON.stringify({code:'read-only-pair'})})).status,401);
});


test('owned inventory uses configured connections and measured models, never advertised catalog',()=>{
 const configured={connections:[{provider:'provider',email:'private@example.com',apiKey:'SECRET'},{provider:'provider',isActive:false},{provider:'gemini'}]};
 const d=normalizeOwned(configured,usage);
 assert.equal(d.connection_count,3);assert.equal(d.connections.length,2);assert.equal(d.connections[0].enabled_count,1);assert.equal(d.models.length,2);
 assert(!JSON.stringify(d).includes('SECRET'));assert(!JSON.stringify(d).includes('private@example.com'));
 const zero=normalizeOwned(configured,{summary:{totalRequests:0,uniqueModels:0},byModel:[]});assert.equal(zero.models.length,0);assert.equal(zero.connection_count,3);
 const other=normalizeOwned({connections:[{provider:'gemini'}]},usage);assert.equal(other.models.length,0);assert.equal(other.connection_count,1);
 assert.throws(()=>normalizeOwned({},usage));
});


test('worker reader caches bounded private helper output and fails closed',async()=>{
 const {createWorkerReader}=await import('../tools/hud_omniroute_bridge.mjs');let calls=0,now=10000;
 const read=createWorkerReader(async()=>{calls++;return {stdout:JSON.stringify({source:'existing_worker_sqlite_read_only',employees:Array.from({length:8},()=>({}))})};},()=>now);
 await read();await read();assert.equal(calls,1);now+=6000;await read();assert.equal(calls,2);
 const bad=createWorkerReader(async()=>{throw Error('PRIVATE_FAILURE')});const result=await bad();assert.equal(result.source,'worker_state_unavailable');assert(!JSON.stringify(result).includes('PRIVATE_FAILURE'));
});

test('quota report only counts recent active account limits and verified resets',()=>{
 const now=Date.parse('2026-10-25T08:00:00Z');
 const p={connections:[{provider:'groq',id:'id-1',isActive:true,secret:'hidden'},{provider:'gemini',id:'id-2',isActive:false}]};
 const caches={'id-1':{fetchedAt:'2026-10-25T07:55:00Z',quotas:{
   modelA:{used:3,total:10,unit:'requests',resetAt:'2026-10-26T12:00:00Z'},
   invalid:{used:20,total:10}
 }},'id-2':{fetchedAt:'2026-10-25T07:55:00Z',quotas:{ignored:{used:2,total:10}}}};
 const r=reduceProviderQuota(p,{caches},{now});
 assert.equal(r.records.length,1);
 assert.equal(r.records[0].used_percent,30);
 assert.equal(r.records[0].reset_at,'2026-10-26T12:00:00.000Z');
 assert.equal(JSON.stringify(r).includes('hidden'),false);
 assert.equal(reduceProviderQuota(p,{}, {now}).records.length,0);
});
