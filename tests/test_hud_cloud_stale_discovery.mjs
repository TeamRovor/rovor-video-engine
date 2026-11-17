import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {generateKeyPairSync} from 'node:crypto';
import {refreshRepoCatchup} from '../integrations/hud-cloud/repo-catchup.mjs';
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

test('in-flight repository catch-up cannot overwrite D1 proof after STOP or standing expiry',async()=>{
 const sha='a'.repeat(40);
 for(const mode of ['stopped','expired']){
  const s=setup(),clock=Date.now();
  s.sql.exec('UPDATE hud_cloud_workforce_control SET enabled=1');
  s.sql.prepare('UPDATE hud_cloud_workforce_series SET active=1,expires_at=?')
   .run(clock+7200000);
  const {privateKey}=generateKeyPairSync('rsa',{modulusLength:2048});
  const env={DB:s.DB,ROVOR_NATIVE_DISCOVERY_ENABLED:'true',ROVOR_GITHUB_APP_ID:'123',
   ROVOR_GITHUB_INSTALLATION_ID:'456',
   ROVOR_GITHUB_APP_PRIVATE_KEY:privateKey.export({type:'pkcs1',format:'pem'})};
  let invalidate=false,changed=false;
  const send=async(url,init)=>{
   assert.equal(init.redirect,'manual');
   if(url.endsWith('/app/installations/456/access_tokens'))
    return Response.json({token:'mock-installation-token-123456',
     expires_at:new Date(clock+3600000).toISOString(),
     permissions:{contents:'read',issues:'read',pull_requests:'read',actions:'read',metadata:'read'},
     repositories:[{full_name:'TeamRovor/rovor-video-engine'}]},{status:201});
   assert.equal(init.method,'GET');
   assert.equal(init.headers.Authorization,'Bearer mock-installation-token-123456');
   if(url.includes('/actions/runs?'))return Response.json({workflow_runs:[]});
   if(url.includes('/issues?')||url.includes('/pulls?'))return Response.json([]);
   if(url.endsWith('/commits?sha=main&per_page=4'))return Response.json([{sha}]);
   if(url.endsWith('/commits/'+sha+'?per_page=30')){
    if(invalidate){
     changed=true;
     if(mode==='stopped')s.sql.exec('UPDATE hud_cloud_workforce_control SET enabled=0');
     else s.sql.prepare('UPDATE hud_cloud_workforce_series SET expires_at=?').run(clock+900000);
    }
    return Response.json({sha,files:[]});
   }
   throw Error('unexpected GitHub endpoint');
  };
  const first=await refreshRepoCatchup(env,clock,send);
  assert.equal(first.status,200);
  assert.equal(first.body.state,'ready');
  const before=s.sql.prepare('SELECT observed_at,snapshot FROM hud_native_repo_catchup WHERE id=1').get();
  assert.equal(before.observed_at,clock);
  invalidate=true;
  const second=await refreshRepoCatchup(env,clock+900001,send);
  assert(changed,'STOP/expiry must occur while a GitHub GET is in flight');
  assert.equal(second.status,409,mode);
  assert.equal(second.body.state,'stopped',mode);
  const after=s.sql.prepare('SELECT checked_at,observed_at,state,snapshot FROM hud_native_repo_catchup WHERE id=1').get();
  assert.equal(after.checked_at,clock+900001);
  assert.equal(after.state,'read_unavailable');
  assert.equal(after.observed_at,before.observed_at);
  assert.equal(after.snapshot,before.snapshot,'retain last-good evidence, never publish late ready');
  assert.equal(s.sql.prepare('SELECT COUNT(*) n FROM hud_cloud_workforce_jobs').get().n,0);
 }
});
