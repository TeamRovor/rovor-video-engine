import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {DatabaseSync} from 'node:sqlite';
import {compileScheduledShift,composeScheduledShift} from '../integrations/ghost-cloud/compose-scheduled-shift.mjs';

const sourceDir=new URL('../integrations/ghost-cloud/',import.meta.url);
const shiftSource=fs.readFileSync(new URL('scheduled-shift.mjs',sourceDir),'utf8');
const feedSource=fs.readFileSync(new URL('approved-feed.mjs',sourceDir),'utf8');
const schema=fs.readFileSync(new URL('scheduled-shift.sql',sourceDir),'utf8');
const TAIL="export default {fetch:(request,env)=>__operations.fetch(request,env),scheduled(event,env,ctx){if(env.GHOST_CRON_OPT_IN==='owner-approved-ghost-cron-v1')return __cloud.worker.scheduled(event,env,ctx);}};";
const v2='// ROVOR_CLOUD_OPERATIONS_V1 testfixture\n'+
  "const __cloud = (() => { return {tick:async()=>({enabled:true,dispatched:0}),worker:{scheduled:()=>{throw Error('old_tick_called')}}};})();\n"+
  "const __operations = (() => {return {replenish:async()=>({queued:0,duplicates:0}),fetch:async()=>new Response('<html><body>Original ROVOR HUD</body></html>',{headers:{'Content-Type':'text/html'}})};})();\n"+
  TAIL+'\n';
function mock() {
  const db=new DatabaseSync(':memory:');db.exec(schema);
  db.exec('CREATE TABLE ghost_cloud_control(id INTEGER PRIMARY KEY,enabled INTEGER NOT NULL)');
  db.exec('INSERT INTO ghost_cloud_control(id,enabled) VALUES(1,1)');
  return {db,env:{GHOST_CRON_OPT_IN:'owner-approved-ghost-cron-v1',DB:{
    prepare(query){
      const statement=db.prepare(query);
      return {first:async()=>statement.get(),bind(...args){return{
        run:async()=>({meta:{changes:statement.run(...args).changes}}),
        first:async()=>statement.get(...args),
        all:async()=>({results:statement.all(...args)})
      }}};
    }
  }}};
}
async function worker() {
  const compiled=compileScheduledShift(v2,shiftSource);
  const imported=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));
  return {compiled,handler:imported.default};
}
function req(path,{identity='owner',method='GET'}={}) {
  return new Request('https://private.chatgpt.site'+path,{method,headers:identity?{'oai-authenticated-user-id':identity}:{}});
}
function existing(t) {
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'rovor-site-shift-'));
  t.after(()=>fs.rmSync(dir,{force:true,recursive:true}));
  fs.mkdirSync(path.join(dir,'worker'),{recursive:true});
  fs.mkdirSync(path.join(dir,'dist/server'),{recursive:true});
  fs.mkdirSync(path.join(dir,'.openai'),{recursive:true});
  fs.mkdirSync(path.join(dir,'drizzle/meta'),{recursive:true});
  fs.writeFileSync(path.join(dir,'.openai/hosting.json'),JSON.stringify({project_id:'appgprj_6add1e2cc8c08191839344b34d7dbf50',d1:'DB'}));
  fs.writeFileSync(path.join(dir,'worker/index.js'),v2);
  fs.writeFileSync(path.join(dir,'dist/server/index.js'),v2);
  const entries=[{idx:0,version:'6',tag:'0000_hud_telemetry',breakpoints:true},{idx:1,version:'6',tag:'0001_cloud_operations',breakpoints:true}];
  for(const e of entries)fs.writeFileSync(path.join(dir,'drizzle',e.tag+'.sql'),'CREATE TABLE x'+e.idx+'(id TEXT);');
  fs.writeFileSync(path.join(dir,'drizzle/meta/_journal.json'),JSON.stringify({version:'7',dialect:'sqlite',entries}));
  return dir;
}
test('compiler uses one exact v2 suffix, retains original HUD and no duplicate entrypoint',()=>{
  const compiled=compileScheduledShift(v2,shiftSource);
  assert.equal(compiled.slice(0,v2.indexOf(TAIL)),v2.slice(0,v2.indexOf(TAIL)));
  assert.match(compiled,/ROVOR_CLOUD_SCHEDULED_SHIFT_V1 [a-f0-9]{64}/);
  assert.equal((compiled.match(/export default/g)||[]).length,1);
  assert.match(compiled,/__operations\.replenish/);assert.match(compiled,/__cloud\.tick/);
  assert.throws(()=>compileScheduledShift(compiled,shiftSource),/unexpected_existing_site_bundle/);
});
test('compiler refuses wrong Site or unexpected module shape',()=>{
  assert.throws(()=>compileScheduledShift('export default {}',shiftSource),/unexpected_existing_site_bundle/);
  assert.throws(()=>compileScheduledShift(v2,'export const dangerous = true;'),/unexpected_shift_module/);
});
test('production bundle embeds pinned approved feed without dynamic module imports',()=>{
  const compiled=compileScheduledShift(v2,shiftSource,feedSource);
  assert.match(compiled,/const __feed = \(\(\) => \{/);
  assert.match(compiled,/GHOST_FEED_COMMIT/);
  assert.match(compiled,/replenishApprovedJobs/);
  assert.doesNotMatch(compiled,/import\s*\(/);
  assert.doesNotMatch(compiled,/^import\s/m);
  assert.throws(()=>compileScheduledShift(v2,shiftSource,'export const hostile=1;'),/unexpected_approved_feed_source/);
});
test('canonical feed branch uses approved task allowlist instead of exhausted static packets',async()=>{
  const dangerous=v2.replace('replenish:async()=>({queued:0,duplicates:0})', "replenish:async()=>{throw Error('legacy_feed_called')}");
  const compiled=compileScheduledShift(dangerous,shiftSource,feedSource);
  const imported=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));
  const s=mock(),promises=[];
  s.env.GHOST_FEED_COMMIT='a'.repeat(40);
  s.env.GHOST_APPROVED_TASKS='[]';
  imported.default.scheduled({},s.env,{waitUntil:p=>promises.push(p)});
  await Promise.all(promises);
  const result=await (await imported.default.fetch(req('/api/ghost/shifts'),s.env)).json();
  assert.equal(result.runs.length,1);
  assert.equal(result.runs[0].status,'idle','empty approved feed is safe and does not call legacy fixed packets');
  assert.equal(result.runs[0].dispatched,0);
});
test('canonical feed misconfiguration fails closed instead of falling back to old packet intake',async()=>{
  const compiled=compileScheduledShift(v2,shiftSource,feedSource);
  const imported=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));
  const s=mock(),promises=[];
  s.env.GHOST_FEED_COMMIT='a'.repeat(40);
  delete s.env.GHOST_APPROVED_TASKS;
  imported.default.scheduled({},s.env,{waitUntil:p=>promises.push(p)});
  await Promise.all(promises);
  const result=await (await imported.default.fetch(req('/api/ghost/shifts'),s.env)).json();
  assert.equal(result.runs[0].status,'failed');
  assert.equal(result.runs[0].reason,'shift_operation_failed');
  assert.equal(result.runs[0].dispatched,0);
});
test('actual self-contained bundle exposes read-only identity-gated D1 schedule receipts',async()=>{
  const s=mock(),{handler}=await worker();
  assert.equal((await handler.fetch(req('/api/ghost/shifts',{identity:null}),s.env)).status,401);
  assert.equal((await handler.fetch(req('/api/ghost/shifts',{method:'POST'}),s.env)).status,405);
  let response=await handler.fetch(req('/api/ghost/shifts'),s.env);
  assert.equal(response.status,200);assert.deepEqual((await response.json()).runs,[]);
  const body=await handler.fetch(req('/'),s.env),html=await body.text();
  assert.equal(body.status,200);assert.match(html,/Original ROVOR HUD/);
  assert.match(html,/rovor-cloud-schedule-state/);
  assert.match(html,/CLOUD SCHEDULE OFFLINE/);assert.doesNotMatch(html,/private customer/i);
});
test('existing schedule hook now runs replenishment then one tick, not old tick',async()=>{
  const s=mock(),{handler}=await worker(),promises=[];
  handler.scheduled({},s.env,{waitUntil:p=>promises.push(p)});
  assert.equal(promises.length,1);
  await Promise.all(promises);
  const result=await (await handler.fetch(req('/api/ghost/shifts'),s.env)).json();
  assert.equal(result.runs.length,1);assert.equal(result.runs[0].status,'idle');
  assert.equal(result.runs[0].dispatched,0);
});
test('without opt-in the cloud schedule has no DB writes and no waitUntil',async()=>{
  const s=mock(),{handler}=await worker(),promises=[];
  delete s.env.GHOST_CRON_OPT_IN;
  handler.scheduled({},s.env,{waitUntil:p=>promises.push(p)});
  assert.equal(promises.length,0);
  assert.equal(s.db.prepare('SELECT count(*) n FROM ghost_cloud_shift_runs').get().n,0);
});
test('failed migration state is reported as unavailable, never healthy',async()=>{
  const s=mock(),{handler}=await worker();
  s.db.exec('DROP TABLE ghost_cloud_shift_runs');
  const response=await handler.fetch(req('/api/ghost/shifts'),s.env);
  assert.equal(response.status,503);assert.deepEqual(await response.json(),{error:'shift_ledger_unavailable'});
});
test('one-bundle composer dry-run leaves original staged v2 untouched',t=>{
  const dir=existing(t);
  const r=composeScheduledShift(dir);
  assert.equal(r.prepared,false);assert.equal(r.deployment_performed,false);
  assert.equal(r.cron_trigger_registered,false);assert.equal(r.models_enabled,false);
  assert.equal(fs.readFileSync(path.join(dir,'worker/index.js'),'utf8'),v2);
  assert.equal(fs.existsSync(path.join(dir,'drizzle/0002_cloud_scheduled_shift.sql')),false);
});
test('composer appends ONE schema-only migration and same Worker dist/source, no Site ID change',t=>{
  const dir=existing(t);
  const r=composeScheduledShift(dir,{apply:true});
  assert.equal(r.prepared,true);assert.equal(r.migration,'0002_cloud_scheduled_shift.sql');
  const out=fs.readFileSync(path.join(dir,'worker/index.js'),'utf8');
  assert.match(out,/ROVOR_CLOUD_SCHEDULED_SHIFT_V1/);
  assert.match(out,/const __feed = \(\(\) => \{/);
  assert.match(out,/GHOST_FEED_COMMIT/);
  assert.equal(out,fs.readFileSync(path.join(dir,'dist/server/index.js'),'utf8'));
  const manifest=JSON.parse(fs.readFileSync(path.join(dir,'.openai/hosting.json'),'utf8'));
  assert.equal(manifest.project_id,'appgprj_6add1e2cc8c08191839344b34d7dbf50');
  const journal=JSON.parse(fs.readFileSync(path.join(dir,'drizzle/meta/_journal.json'),'utf8'));
  assert.equal(journal.entries.length,3);
  assert.match(fs.readFileSync(path.join(dir,'drizzle/0002_cloud_scheduled_shift.sql'),'utf8'),/statement-breakpoint/);
  assert.throws(()=>composeScheduledShift(dir,{apply:true}),/unexpected_existing_site_bundle/);
});
test('mismatched existing dist bundle fails without modifying staged v2',t=>{
  const dir=existing(t);
  fs.writeFileSync(path.join(dir,'dist/server/index.js'),'Unreviewed');
  assert.throws(()=>composeScheduledShift(dir,{apply:true}),/site_bundle_mismatch/);
  assert.equal(fs.readFileSync(path.join(dir,'worker/index.js'),'utf8'),v2);
});
test('symlink redirection of migration folder is rejected without modifying original',t=>{
  const dir=existing(t),outside=fs.mkdtempSync(path.join(os.tmpdir(),'rovor-shift-outside-'));
  t.after(()=>fs.rmSync(outside,{force:true,recursive:true}));
  fs.renameSync(path.join(dir,'drizzle'),path.join(dir,'old-drizzle'));
  fs.symlinkSync(outside,path.join(dir,'drizzle'));
  assert.throws(()=>composeScheduledShift(dir,{apply:true}),/redirected_site/);
  assert.equal(fs.readdirSync(outside).length,0);
});
