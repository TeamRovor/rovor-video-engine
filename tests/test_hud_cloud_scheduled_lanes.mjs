import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runCloudScheduledLanes} from '../integrations/hud-cloud/scheduled-lanes.mjs';

const worker=readFileSync(new URL('../integrations/hud-cloud/worker.mjs',import.meta.url),'utf8');
const defaultFns=()=>({
 maintain:async()=>{},discover:async()=>{},
 workforce:async()=>({status:200,body:{state:'idle_or_safety_limited',dispatched:0}}),
 record:async()=>{},refreshCatalogs:async()=>{},patch:async()=>{},
 clock:()=>1000
});
test('actual Cloudflare cron is wired to the isolated lanes without new scheduling or bypassing STOP',()=>{
 assert.match(worker,/import \{runCloudScheduledLanes\} from '\.\/scheduled-lanes\.mjs'/);
 assert.match(worker,/return runCloudScheduledLanes\(/);
 assert.match(worker,/discover:\(\)=>nativeDiscoveryTick\(env,Date\.now\(\)\)/);
 assert.match(worker,/workforce:startedAt=>workforceTick\(env,startedAt\)/);
 assert.match(worker,/recordNativeTick\(env\.DB,event\.scheduledTime,startedAt,finishedAt,result\)/);
 assert.match(worker,/if\(gate\?\.enabled===1\)await refreshCatalogBridge\(env,Date\.now\(\)\)/);
 assert.match(worker,/patch:\(\)=>githubPatchTick\(env,Date\.now\(\)\)/);
});

test('GitHub patch and catalog work start while a slow Gemini inference is pending',async()=>{
 const events=[];let releaseInference,startedInference;
 const inferenceReleased=new Promise(resolve=>{releaseInference=resolve;});
 const inferenceStarted=new Promise(resolve=>{startedInference=resolve;});
 const f=defaultFns();
 f.maintain=async()=>{events.push('maintain');};
 f.discover=async()=>{events.push('discover');};
 f.workforce=async()=>{events.push('workforce');startedInference();await inferenceReleased;
  return {status:200,body:{state:'needs_review',dispatched:1}};};
 f.refreshCatalogs=async()=>{events.push('catalog');};
 f.patch=async()=>{events.push('patch');};
 f.record=async(_start,_finish,result)=>{events.push('receipt');assert.equal(result.status,200);};
 const run=runCloudScheduledLanes(f);
 await inferenceStarted;
 assert(events.indexOf('discover')<events.indexOf('workforce'));
 assert(events.includes('maintain'));
 assert(events.includes('patch'));
 assert(events.includes('catalog'));
 assert(!events.includes('receipt'));
 releaseInference();
 assert.deepEqual(await run,{status:'completed'});
 assert(events.includes('receipt'));
});

test('Gemini tick transport crash still records a failed wakeup and runs independent patches',async()=>{
 const events=[];let saved;
 const f=defaultFns();
 f.workforce=async()=>{events.push('workforce');throw Error('Authorization: Bearer PRIVATE');};
 f.record=async(start,finished,response)=>{events.push('record');saved={start,finished,response};};
 f.patch=async()=>{events.push('patch');};
 f.refreshCatalogs=async()=>{events.push('catalog');};
 await assert.rejects(runCloudScheduledLanes(f),e=>{
  assert.equal(e.message,'scheduled_workforce_tick_failed');
  assert(!e.message.includes('PRIVATE'));
  return true;
 });
 assert.equal(saved.response.status,503);
 assert.deepEqual(saved.response.body,{error:'scheduled_workforce_tick_failed',dispatched:0,inference_completed:false});
 assert.equal(saved.start,1000);assert.equal(saved.finished,1000);
 assert(events.includes('patch'));assert(events.includes('catalog'));
});

test('native discovery failure cannot prevent next bounded tick, model-free catalog and GitHub worker',async()=>{
 const events=[],f=defaultFns();
 f.discover=async()=>{events.push('discover');throw Error('untrusted GitHub body SECRET');};
 f.workforce=async()=>{events.push('workforce');return {status:200,body:{dispatched:0}};};
 f.record=async()=>{events.push('receipt');};
 f.refreshCatalogs=async()=>{events.push('catalog');};
 f.patch=async()=>{events.push('patch');};
 await assert.rejects(runCloudScheduledLanes(f),/scheduled_native_discovery_failed/);
 assert.deepEqual(events.sort(),['catalog','discover','patch','receipt','workforce'].sort());
});

test('a rejected GitHub patch call does not erase workforce receipts or leak upstream error',async()=>{
 const f=defaultFns();let receipts=0;
 f.patch=async()=>{throw Error('authorization token private');};
 f.record=async()=>{receipts++;};
 await assert.rejects(runCloudScheduledLanes(f),e=>{
  assert.equal(e.message,'scheduled_github_patch_failed');return true;
 });
 assert.equal(receipts,1);
});
test('optional catalog telemetry failure remains nonfatal and never causes extra inference',async()=>{
 const f=defaultFns();let inference=0,records=0;
 f.workforce=async()=>{inference++;return {status:200,body:{dispatched:0}};};
 f.refreshCatalogs=async()=>{throw Error('provider rate limit');};
 f.record=async()=>{records++;};
 assert.equal((await runCloudScheduledLanes(f)).status,'completed');
 assert.equal(inference,1);assert.equal(records,1);
});

test('all required handlers must be explicit to avoid quietly skipping a safety lane',async()=>{
 const f=defaultFns();delete f.record;
 await assert.rejects(runCloudScheduledLanes(f),/scheduled_lanes_not_configured/);
});
