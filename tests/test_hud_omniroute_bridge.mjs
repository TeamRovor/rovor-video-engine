import http from 'node:http';import test from 'node:test';import assert from 'node:assert/strict';
import {normalize,createCollector,createBridge} from '../tools/hud_omniroute_bridge.mjs';
const catalog={data:Array.from({length:12},(_,i)=>({id:'provider/model-'+i,owned_by:'provider'})).concat({id:'rovor-fast',owned_by:'combo'})};
const usage={summary:{totalRequests:10,uniqueModels:2},byModel:[{rawModel:'model-0',provider:'provider',requests:7,totalTokens:70},{rawModel:'model-1',provider:'provider',requests:3,totalTokens:30}]};
test('full catalog, exact measured shares, unknown quota and unobserved usage',()=>{const d=normalize(catalog,usage);assert.equal(d.inventory_count,12);assert.equal(d.models.length,12);assert.equal(d.models[0].request_share_percent,70);assert.equal(d.models[2].requests,null);assert.equal(d.models[0].quota_used_percent,null);assert.equal(d.usage_coverage,'complete_aggregate');});
test('partial aggregates are labeled and ambiguous aliases never duplicate counts',()=>{const d=normalize({data:[{id:'a/m',owned_by:'x'},{id:'b/m',owned_by:'x'}]},{summary:{totalRequests:30,uniqueModels:55},byModel:[{rawModel:'m',provider:'x',requests:3,totalTokens:1}]});assert.equal(d.usage_coverage,'partial_top_50_or_unattributed');assert.equal(d.models.filter(m=>m.requests===3).length,1);assert.equal(d.models.filter(m=>m.requests===null).length,2);});
test('explicit zero is distinct from unavailable and raw secrets never leave reducer',()=>{const x=structuredClone(usage);x.secret='private';const d=normalize(catalog,x);assert(!JSON.stringify(d).includes('private'));assert.equal(normalize(catalog,{summary:{totalRequests:0,uniqueModels:0},byModel:[]}).request_count,0);assert.throws(()=>normalize(catalog,{}));});
test('duplicate, inconsistent and malformed rows fail closed',()=>{assert.throws(()=>normalize(catalog,{...usage,byModel:[usage.byModel[0],usage.byModel[0]]}));assert.throws(()=>normalize(catalog,{...usage,summary:{totalRequests:2,uniqueModels:2}}));assert.throws(()=>normalize({data:[]},usage));});
test('collector deduplicates concurrent reads, refreshes usage after 5s and catalog after 60s',async()=>{let now=100000,calls=[];const collect=createCollector(async p=>{calls.push(p);return p==='/v1/models'?catalog:usage;},{clock:()=>now});await Promise.all([collect('24h'),collect('24h')]);assert.equal(calls.length,2);now+=6000;await collect('24h');assert.equal(calls.length,3);assert(calls[2].includes('endDate='));now+=60000;await collect('24h');assert.equal(calls.length,5);await assert.rejects(collect('bad'));});
test('HTTP pairing, auth, whitelist, no proxy, no stale fallback, no mutations',async t=>{let broken=false;const b=createBridge({collect:async()=>{if(broken)throw Error('SECRET');return normalize(catalog,usage);},hud:'<body>ROVOR</body>',adapter:'/* adapter */',pairCode:'pair-secret'});const port=await b.listen();t.after(()=>new Promise(r=>b.server.close(r)));const base='http://127.0.0.1:'+port;
assert.equal((await fetch(base+'/api/hud/omniroute')).status,401);
assert.equal(await new Promise((resolve,reject)=>{const req=http.get(base+'/',{headers:{Host:'evil.example'}},res=>{res.resume();resolve(res.statusCode)});req.on('error',reject)}),403);
assert.equal((await fetch(base+'/pair',{method:'POST',headers:{Origin:'https://evil.example'},body:'{"code":"pair-secret"}'})).status,403);
assert.equal((await fetch(base+'/pair',{method:'POST',headers:{Origin:base},body:JSON.stringify({code:'é'.repeat(11)})})).status,401);
const pair=await fetch(base+'/pair',{method:'POST',headers:{Origin:base},body:'{"code":"pair-secret"}'});assert.equal(pair.status,200);const cookie=pair.headers.get('set-cookie').split(';')[0];const headers={Cookie:cookie};
assert.equal((await fetch(base+'/pair',{method:'POST',headers:{Origin:base},body:'{"code":"pair-secret"}'})).status,401);
assert((await (await fetch(base+'/',{headers})).text()).includes('/hud-live.js'));
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
