import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {selectPreflightJob} from '../integrations/hud-cloud/approved-workforce.mjs';

const NOW=Date.parse('2026-11-11T02:05:00.000Z');
function setup(){
 const sql=new DatabaseSync(':memory:');
 sql.exec(readFileSync(new URL('../integrations/hud-cloud/schema.sql',import.meta.url),'utf8'));
 const DB={prepare(query){
  const statement=sql.prepare(query);let values=[];
  const bound={bind(...args){values=args;return bound;},
   async first(){return statement.get(...values)||null;},
   async run(){return {meta:{changes:Number(statement.run(...values).changes)}};}};
  return bound;
 }};
 const add=(num,order)=>{
  sql.prepare(`INSERT INTO hud_cloud_workforce_jobs
   (id,task_id,employee,kind,title,prompt,source_commit,revision,created_at,state,human_review)
   VALUES(?,?,?,?,?,?,?,?,?,'queued','not_recorded')`).run(
   'gc-rec-proof-'+num,'cloud-discovery-issue-'+num,'Mike','code_review',
   'Inspect public issue '+num,'Investigate GitHub metadata for owner review',
   'a'.repeat(40),'v2',NOW+order);
 };
 return {sql,DB,add};
}

test('one shift discards stale evidence and continues to an actionable candidate',async()=>{
 const s=setup();s.add(2345,0);s.add(2346,1);
 const checked=[];
 const result=await selectPreflightJob(s.DB,null,NOW+1000,async taskId=>{
  checked.push(taskId);return {state:taskId.endsWith('2345')?'stale':'actionable'};
 });
 assert.equal(result.next?.id,'gc-rec-proof-2346');
 assert.equal(result.staleDiscarded,1);
 assert.equal(result.blocked,null);
 assert.deepEqual(checked,['cloud-discovery-issue-2345','cloud-discovery-issue-2346']);
 const stale=s.sql.prepare('SELECT state,error_code,started_at FROM hud_cloud_workforce_jobs WHERE id=?').get('gc-rec-proof-2345');
 assert.equal(stale.state,'failed');
 assert.equal(stale.error_code,'discovery_no_longer_actionable');
 assert.equal(stale.started_at,null);
 const next=s.sql.prepare('SELECT state,started_at FROM hud_cloud_workforce_jobs WHERE id=?').get(result.next.id);
 assert.equal(next.state,'queued');assert.equal(next.started_at,null);
});

test('at most three stale discoveries are consumed per shift without claiming inference',async()=>{
 const s=setup();
 for(const [i,num] of [2345,2346,2347,2348].entries())s.add(num,i);
 let checked=0;
 const result=await selectPreflightJob(s.DB,null,NOW+1000,async()=>{checked++;return {state:'stale'};});
 assert.equal(result.next,null);
 assert.equal(result.staleDiscarded,3);
 assert.equal(result.blocked.state,'discovery_no_longer_actionable');
 assert.equal(result.blocked.dispatched,0);
 assert.equal(checked,3);
 assert.equal(s.sql.prepare("SELECT COUNT(*) n FROM hud_cloud_workforce_jobs WHERE state='failed'").get().n,3);
 assert.equal(s.sql.prepare("SELECT COUNT(*) n FROM hud_cloud_workforce_jobs WHERE state='queued'").get().n,1);
 assert.equal(s.sql.prepare("SELECT COUNT(*) n FROM hud_cloud_workforce_jobs WHERE started_at IS NOT NULL").get().n,0);
});

test('unavailable evidence leaves selected work queued and never authorizes a claim',async()=>{
 const s=setup();s.add(2345,0);s.add(2346,1);
 const result=await selectPreflightJob(s.DB,null,NOW+1000,async taskId=>
  ({state:taskId.endsWith('2345')?'stale':'unavailable'}));
 assert.equal(result.next,null);
 assert.equal(result.blocked.state,'discovery_source_unverified');
 assert.equal(result.blocked.dispatched,0);
 assert.equal(result.staleDiscarded,1);
 assert.equal(s.sql.prepare("SELECT state FROM hud_cloud_workforce_jobs WHERE id='gc-rec-proof-2346'").get().state,'queued');
 assert.equal(s.sql.prepare("SELECT COUNT(*) n FROM hud_cloud_workforce_jobs WHERE started_at IS NOT NULL").get().n,0);
});

test('empty queue remains safely idle',async()=>{
 const s=setup();
 const result=await selectPreflightJob(s.DB,null,NOW,()=>{throw Error('not called');});
 assert.equal(result.next,null);
 assert.equal(result.blocked.state,'idle_or_safety_limited');
 assert.equal(result.staleDiscarded,0);
});
