import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {runScheduledShift,readScheduledShifts} from '../integrations/ghost-cloud/scheduled-shift.mjs';

function setup({optIn = true, enabled = true} = {}) {
  const db = new DatabaseSync(':memory:');
  db.exec(fs.readFileSync(new URL('../integrations/ghost-cloud/scheduled-shift.sql', import.meta.url), 'utf8'));
  db.exec('CREATE TABLE ghost_cloud_control(id INTEGER PRIMARY KEY,enabled INTEGER NOT NULL)');
  db.exec('CREATE TABLE ghost_cloud_jobs(id TEXT PRIMARY KEY);CREATE TABLE ghost_cloud_attempts(job_id TEXT NOT NULL UNIQUE)');
  db.prepare('INSERT INTO ghost_cloud_control(id,enabled) VALUES(1,?)').run(enabled ? 1 : 0);
  const api = {
    prepare(query) {
      let statement = db.prepare(query);
      return {bind(...args) {
        return {
          first: async() => statement.get(...args),
          run: async() => ({meta: {changes: statement.run(...args).changes}}),
          all: async() => ({results: statement.all(...args)})
        };
      }};
    }
  };
  let ts = 1792900000000;
  let n = 0;
  return {db, env: {DB: api, ...(optIn ? {GHOST_CRON_OPT_IN: 'owner-approved-ghost-cron-v1'} : {})},
    clock: () => ++ts, newId: () => 'receipt-' + String(++n).padStart(16, '0')};
}

test('no opt-in writes nothing and calls no model or feed', async() => {
  const s=setup({optIn:false});let calls=0;
  const r=await runScheduledShift(s.env,{replenish:()=>{calls++;},tick:()=>{calls++;},clock:s.clock,newId:s.newId});
  assert.equal(r.status,'not_opted_in');assert.equal(calls,0);
  assert.equal(s.db.prepare('SELECT count(*) n FROM ghost_cloud_shift_runs').get().n,0);
});

test('STOP before replenishment prevents feed, tick and receipts show stopped',async()=>{
  const s=setup({enabled:false});let calls=0;
  const r=await runScheduledShift(s.env,{replenish:()=>{calls++;},tick:()=>{calls++;},clock:s.clock,newId:s.newId});
  assert.equal(r.status,'stopped');assert.equal(calls,0);
  assert.equal(s.db.prepare('SELECT status FROM ghost_cloud_shift_runs').get().status,'stopped');
});

test('replenishes approved packets before bounded dispatch; records actual counts',async()=>{
  const s=setup(),calls=[];
  const r=await runScheduledShift(s.env,{replenish:async()=>{calls.push('feed');return {queued:2,duplicates:1};},
    tick:async()=>{calls.push('tick');return {enabled:true,dispatched:2};},clock:s.clock,newId:s.newId});
  assert.deepEqual(calls,['feed','tick']);assert.equal(r.status,'dispatched');assert.equal(r.dispatched,2);
  const saved=s.db.prepare('SELECT queued,duplicates,dispatched,status,reason FROM ghost_cloud_shift_runs').get();
  assert.deepEqual({...saved},{queued:2,duplicates:1,dispatched:2,status:'dispatched',reason:null});
});

test('no fresh jobs yields an idle receipt, not a fabricated online worker',async()=>{
  const s=setup();const r=await runScheduledShift(s.env,{replenish:async()=>({queued:0,duplicates:9}),
    tick:async()=>({enabled:true,dispatched:0}),clock:s.clock,newId:s.newId});
  assert.equal(r.status,'idle');assert.equal(r.dispatched,0);
  assert.equal(r.reason,'no_unattempted_jobs');
});
test('idle shift distinguishes all ineligible routes from blocked unattempted work',async()=>{
  const s=setup();s.db.exec("INSERT INTO ghost_cloud_jobs(id) VALUES('ready')");
  const denied=Object.fromEntries(['groq','gemini','cloudflare-ai','mistral','nvidia','openrouter','sambanova','cohere','huggingface'].map(id=>[id,'not_configured']));
  const first=await runScheduledShift(s.env,{replenish:async()=>({queued:0,duplicates:0}),
    tick:async()=>({enabled:true,dispatched:0,denied}),clock:s.clock,newId:s.newId});
  assert.equal(first.status,'idle');assert.equal(first.reason,'no_eligible_providers');
  const second=await runScheduledShift(s.env,{replenish:async()=>({queued:0,duplicates:0}),
    tick:async()=>({enabled:true,dispatched:0,denied:{groq:'not_configured'}}),clock:s.clock,newId:s.newId});
  assert.equal(second.reason,'unattempted_jobs_not_dispatched');
  s.db.exec("INSERT INTO ghost_cloud_attempts(job_id) VALUES('ready')");
  const third=await runScheduledShift(s.env,{replenish:async()=>({queued:0,duplicates:1}),
    tick:async()=>({enabled:true,dispatched:0,denied}),clock:s.clock,newId:s.newId});
  assert.equal(third.reason,'no_unattempted_jobs');
  assert.deepEqual(s.db.prepare('SELECT reason FROM ghost_cloud_shift_runs ORDER BY started_at').all().map(x=>x.reason),
    ['no_eligible_providers','unattempted_jobs_not_dispatched','no_unattempted_jobs']);
});

test('STOP after feeding prevents any tick',async()=>{
  const s=setup(),calls=[];
  const r=await runScheduledShift(s.env,{replenish:async()=>{calls.push('feed');s.db.exec('UPDATE ghost_cloud_control SET enabled=0 WHERE id=1');return {queued:1,duplicates:0};},
    tick:async()=>{calls.push('tick');return {enabled:true,dispatched:1};},clock:s.clock,newId:s.newId});
  assert.deepEqual(calls,['feed']);assert.equal(r.status,'stopped');assert.equal(r.dispatched,0);
});

test('malformed receipts fail closed and do not call providers',async()=>{
  const s=setup();let called=false;
  const r=await runScheduledShift(s.env,{replenish:async()=>({queued:100,duplicates:0}),
    tick:()=>{called=true;},clock:s.clock,newId:s.newId});
  assert.equal(called,false);assert.equal(r.status,'failed');assert.equal(r.reason,'invalid_feed_receipt');
});

test('exceptions do not store secret-bearing error text',async()=>{
  const s=setup();
  const r=await runScheduledShift(s.env,{replenish:async()=>({queued:1,duplicates:0}),
    tick:async()=>{throw Error('Authorization: Bearer SECRET_123 and private customer prompt');},clock:s.clock,newId:s.newId});
  assert.equal(r.status,'failed');assert.equal(r.reason,'shift_operation_failed');
  assert.equal(JSON.stringify(s.db.prepare('SELECT * FROM ghost_cloud_shift_runs').all()).includes('SECRET_123'),false);
});

test('readback never invents model/provider data and remains bounded',async()=>{
  const s=setup();await runScheduledShift(s.env,{replenish:async()=>({queued:1,duplicates:0}),tick:async()=>({enabled:true,dispatched:0}),clock:s.clock,newId:s.newId});
  const result=await readScheduledShifts(s.env,2);
  assert.equal(result.source,'cloud_schedule_receipts');assert.equal(result.runs.length,1);
  assert.deepEqual(Object.keys(result.runs[0]).sort(),['dispatched','duplicates','finished_at','id','queued','reason','started_at','status'].sort());
  await assert.rejects(readScheduledShifts(s.env,999),/invalid_shift_read/);
});

test('two separate schedule fires have distinct persisted IDs; no assumed progress',async()=>{
  const s=setup();for(let i=0;i<2;i++)await runScheduledShift(s.env,{replenish:async()=>({queued:0,duplicates:0}),tick:async()=>({enabled:true,dispatched:0}),clock:s.clock,newId:s.newId});
  assert.equal(s.db.prepare('SELECT count(*) n FROM ghost_cloud_shift_runs').get().n,2);
  assert.equal(s.db.prepare("SELECT sum(dispatched) n FROM ghost_cloud_shift_runs").get().n,0);
});

test('STOP during approved-feed read remains stopped, not a false failure',async()=>{
  const s=setup();let called=false;
  const r=await runScheduledShift(s.env,{replenish:async()=>({status:'stopped',queued:0}),
    tick:async()=>{called=true;},clock:s.clock,newId:s.newId});
  assert.equal(r.status,'stopped');assert.equal(called,false);
});

test('invalid downstream tick receipt records failure without imaginary dispatch',async()=>{
  const s=setup();const r=await runScheduledShift(s.env,{replenish:async()=>({queued:1,duplicates:0}),
    tick:async()=>({enabled:true,dispatched:15}),clock:s.clock,newId:s.newId});
  assert.equal(r.status,'failed');assert.equal(r.dispatched,0);assert.equal(r.reason,'invalid_tick_receipt');
});
