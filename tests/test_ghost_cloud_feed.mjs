import test from 'node:test';
import assert from 'node:assert/strict';
import {fetchCanonicalQueue,planApprovedJobs,replenishApprovedJobs} from '../integrations/ghost-cloud/approved-feed.mjs';

const COMMIT='a'.repeat(40);
const approval={task_id:'public-task',revision:'v1'};
const packet={approved_for_cloud:true,data_class:'public_repository',employee:'Gale',kind:'research',prompt:'Research public Blender export compatibility; cite sources.',revision:'v1'};
const task=()=>({id:'public-task',title:'Public Blender compatibility research',status:'active',owner:'Walter / cloud approved research',
 scopes:['subsystem:public-blender-research'],depends_on:[],cloud_inference:{...packet}});
const queue=()=>({version:1,tasks:[task()]});
const routing=()=>({version:1,tasks:{'public-task':{lane:'integration',requires:['github-read']}}});
const plan=(q=queue(),r=routing(),a=[approval],commit=COMMIT)=>planApprovedJobs(q,r,commit,a);
const rejects=async (fn,code)=>assert.rejects(fn,new RegExp(code));
const env=()=>({DB:{prepare:()=>({first:async()=>({enabled:1})})},GHOST_FEED_COMMIT:COMMIT,GHOST_APPROVED_TASKS:JSON.stringify([approval])});
const fetcher=(q=queue(),r=routing(),calls=[])=>async url=>{
 calls.push(url);
 return Response.json(url.endsWith('/tasks.json')?q:r);
};

test('one explicitly approved active canonical public task produces an immutable-source job',async()=>{
 const [job]=await plan();assert.equal(job.employee,'Gale');assert.equal(job.kind,'research');
 assert.equal(job.source_commit,COMMIT);assert.equal(job.data_class,'public_repository');
 assert.match(job.id,/^gc-[a-f0-9]{48}$/);
});
test('unchanged task has same job ID after unrelated commit',async()=>{
 const [a]=await plan(),[b]=await plan(queue(),routing(),[approval],'b'.repeat(40));
 assert.equal(a.id,b.id);assert.notEqual(a.source_commit,b.source_commit);
});
test('explicit revision and private approval change creates a new ID',async()=>{
 const q=queue();q.tasks[0].cloud_inference.revision='v2';
 const [old]=await plan(),[newer]=await plan(q,routing(),[{task_id:'public-task',revision:'v2'}]);
 assert.notEqual(old.id,newer.id);
});
test('empty private allowlist emits no jobs',async()=>assert.deepEqual(await plan(queue(),routing(),[]),[]));
test('unknown task rejected',async()=>rejects(()=>plan(queue(),routing(),[{task_id:'unknown',revision:'v1'}]),'unknown_task'));
test('completed tasks cannot be requeued',async()=>{const q=queue();q.tasks[0].status='done';await rejects(()=>plan(q),'task_not_claimed');});
test('task requires real active owner and scope',async()=>{const q=queue();q.tasks[0].owner='';await rejects(()=>plan(q),'task_not_claimed');});
test('missing canonical routing blocks dispatch',async()=>rejects(()=>plan(queue(),{tasks:{}}),'task_unrouted'));
test('unresolved canonical dependency blocks dispatch',async()=>{
 const q=queue();q.tasks[0].depends_on=['unresolved'];await rejects(()=>plan(q),'task_dependency_blocked');
});
test('private data class is rejected',async()=>{const q=queue();q.tasks[0].cloud_inference.data_class='private';await rejects(()=>plan(q),'cloud_packet_not_approved');});
test('no explicit cloud approval means no dispatch',async()=>{const q=queue();q.tasks[0].cloud_inference.approved_for_cloud=false;await rejects(()=>plan(q),'cloud_packet_not_approved');});
test('approval revision mismatch fails closed',async()=>rejects(()=>plan(queue(),routing(),[{task_id:'public-task',revision:'v2'}]),'cloud_packet_not_approved'));
test('duplicate private approvals rejected',async()=>rejects(()=>plan(queue(),routing(),[approval,approval]),'invalid_approvals'));
test('more than nine approvals rejected before dispatch',async()=>rejects(()=>plan(queue(),routing(),Array.from({length:10},(_,i)=>({task_id:'task-'+i,revision:'v1'}))),'invalid_approvals'));
test('unknown role and unsafe kind rejected by existing worker job contract',async()=>{
 const q=queue();q.tasks[0].cloud_inference.employee='Fake';await rejects(()=>plan(q),'invalid_job');
});
test('oversized prompt rejected by existing worker contract',async()=>{
 const q=queue();q.tasks[0].cloud_inference.prompt='a'.repeat(14501);await rejects(()=>plan(q),'invalid_job');
});
test('commit must be exact immutable 40-hex SHA',async()=>rejects(()=>plan(queue(),routing(),[approval],'main'),'invalid_source_commit'));
test('fetches both canonical files at one pinned commit, with no mutable refs',async()=>{
 const urls=[];await fetchCanonicalQueue(COMMIT,fetcher(queue(),routing(),urls));
 assert.deepEqual(urls,[
  'https://raw.githubusercontent.com/TeamRovor/rovor-video-engine/'+COMMIT+'/coordination/tasks.json',
  'https://raw.githubusercontent.com/TeamRovor/rovor-video-engine/'+COMMIT+'/coordination/work-routing.json'
 ]);
});
test('persistent STOP prevents source fetch and all enqueue',async()=>{
 const e=env();e.DB.prepare=()=>({first:async()=>({enabled:0})});let calls=0;
 const result=await replenishApprovedJobs(e,{fetcher:async()=>{calls++;throw Error('unexpected');},submit:async()=>{calls++;throw Error('unexpected');}});
 assert.equal(result.status,'stopped');assert.equal(calls,0);
});
test('real queue feed invokes existing writer adapter and returns factual counts',async()=>{
 const e=env(),jobs=[];
 const result=await replenishApprovedJobs(e,{fetcher:fetcher(),submit:async job=>{jobs.push(job);return {id:job.id,queued:true};}});
 assert.deepEqual(result,{status:'complete',queued:1,duplicates:0});assert.equal(jobs[0].task_id,'public-task');
});
test('idempotent duplicate receipts are counted, not replayed',async()=>{
 const result=await replenishApprovedJobs(env(),{fetcher:fetcher(),submit:async job=>({id:job.id,duplicate:true})});
 assert.deepEqual(result,{status:'complete',queued:0,duplicates:1});
});
test('STOP activated after source read blocks submission',async()=>{
 let reads=0,submits=0;const e=env();e.DB.prepare=()=>({first:async()=>({enabled:++reads===1?1:0})});
 const result=await replenishApprovedJobs(e,{fetcher:fetcher(),submit:async()=>{submits++;throw Error('unexpected');}});
 assert.equal(result.status,'stopped');assert.equal(submits,0);
});
test('bad source JSON fails without writing any job',async()=>{
 let writes=0;await rejects(()=>replenishApprovedJobs(env(),{fetcher:async()=>new Response('not-json'),submit:async()=>{writes++;}}),'invalid_source_json');
 assert.equal(writes,0);
});
test('source transport errors fail without writes',async()=>{
 let writes=0;await rejects(()=>replenishApprovedJobs(env(),{fetcher:async()=>new Response('missing',{status:404}),submit:async()=>{writes++;}}),'source_unavailable');
 assert.equal(writes,0);
});
test('unverified writer receipt is not accepted',async()=>{
 await rejects(()=>replenishApprovedJobs(env(),{fetcher:fetcher(),submit:async()=>({queued:true,id:'wrong'})}),'writer_invalid_receipt');
});
test('empty allowlist performs no remote fetch',async()=>{
 const e=env();e.GHOST_APPROVED_TASKS='[]';let calls=0;
 const result=await replenishApprovedJobs(e,{fetcher:async()=>{calls++;},submit:async()=>{calls++;}});
 assert.equal(result.status,'empty');assert.equal(calls,0);
});

const SERIES_START='2026-11-10T00:00:00.000Z';
const SERIES_END='2026-11-11T00:00:00.000Z';
const SERIES_NOW=Date.parse(SERIES_START);
const seriesApproval={
 approval:'owner_approved_recurring_cloud_inference_v1',
 task_id:'public-task',revision:'v1',cadence_minutes:60,max_runs:24,
 starts_at:SERIES_START,expires_at:SERIES_END
};
function recurringFixture(){
 const q=queue();
 q.tasks[0].cloud_inference.prompt='Review public status for {{RUN_WINDOW_UTC}}; state uncertainty explicitly.';
 const e=env();e.GHOST_APPROVED_TASKS='[]';
 e.GHOST_APPROVED_SERIES=JSON.stringify([seriesApproval]);
 const jobs=new Map(),attempted=new Set(),writes=[];
 e.DB.prepare=(query)=>({
  first:async()=>({enabled:1}),
  bind(...args){return{first:async()=>{
   if(query.startsWith('SELECT id FROM ghost_cloud_jobs'))return jobs.has(args[0])?{id:args[0]}:null;
   if(query.includes('FROM ghost_cloud_jobs j'))return [...jobs.values()].some(
    j=>j.task_id===args[0]&&!attempted.has(j.id))?{pending:1}:null;
   throw Error('unexpected_recurring_query');
  }};}
 });
 const submit=async job=>{
  writes.push(job);
  if(jobs.has(job.id))return {id:job.id,duplicate:true};
  jobs.set(job.id,job);return {id:job.id,queued:true};
 };
 const call=now=>replenishApprovedJobs(e,{fetcher:fetcher(q),submit,now});
 return {e,q,jobs,attempted,writes,call};
}

test('recurring series requires an explicit private opt-in and an approved public template',async()=>{
 const s=recurringFixture();delete s.e.GHOST_APPROVED_SERIES;
 let calls=0;
 const output=await replenishApprovedJobs(s.e,{now:SERIES_NOW,fetcher:async()=>{calls++;throw Error('unexpected');}});
 assert.equal(output.status,'empty');assert.equal(calls,0);
 s.e.GHOST_APPROVED_SERIES=JSON.stringify([seriesApproval]);
 s.q.tasks[0].cloud_inference.prompt='Regular non-templated output';
 await rejects(()=>s.call(SERIES_NOW),'recurring_template_missing');
 assert.equal(s.writes.length,0);
});

test('hourly approved recurring work is idempotent, bounded and never backfills missed slots',async()=>{
 const s=recurringFixture();
 const first=await s.call(SERIES_NOW+2000);
 assert.deepEqual(first,{status:'complete',queued:1,duplicates:0});
 const job=s.writes[0];
 assert.match(job.id,/^gc-rec-[a-f0-9]{48}$/);
 assert.match(job.prompt,/2026-11-10T00:00:00.000Z/);
 assert.equal(job.data_class,'public_repository');
 assert.equal((await s.call(SERIES_NOW+5000)).duplicates,1);
 assert.deepEqual(await s.call(SERIES_NOW+HOUR_MS),{status:'complete',queued:0,duplicates:0},
  'stalled prior window prevents unbounded pending backlog');
 s.attempted.add(job.id);
 assert.equal((await s.call(SERIES_NOW+HOUR_MS)).queued,1);
 assert.notEqual(s.writes.at(-1).id,job.id);
 assert.match(s.writes.at(-1).prompt,/2026-11-10T01:00:00.000Z/);
 s.attempted.add(s.writes.at(-1).id);
 assert.equal((await s.call(SERIES_NOW+22*HOUR_MS)).queued,1,
  'offline hours are not automatically replayed');
 assert.equal((await s.call(Date.parse(SERIES_END))).queued,0);
 assert.equal(s.jobs.size,3);
});
const HOUR_MS=3600000;

test('recurring series invalid intent, bounds, or overly broad approvals fail before any job',async()=>{
 const s=recurringFixture();
 for(const change of [
  {approval:'not-explicit'},
  {cadence_minutes:1},
  {max_runs:169},
  {starts_at:'not-a-date'},
  {expires_at:'2026-11-25T00:00:00.000Z'},
  {revision:'v2'},
 ]){
  s.e.GHOST_APPROVED_SERIES=JSON.stringify([{...seriesApproval,...change}]);
  await rejects(()=>s.call(SERIES_NOW),change.revision?'cloud_packet_not_approved':'invalid_recurring_approvals');
 }
 assert.equal(s.writes.length,0);
});

test('recurring work cannot exceed the existing nine-packet shift budget',async()=>{
 const s=recurringFixture();
 s.e.GHOST_APPROVED_TASKS=JSON.stringify(Array.from({length:9},(_,i)=>({task_id:'a'+i,revision:'v1'})));
 let calls=0;
 await rejects(()=>replenishApprovedJobs(s.e,{now:SERIES_NOW,fetcher:async()=>{calls++;throw Error('unexpected');}}),
  'too_many_approved_packets');
 assert.equal(calls,0);
});

test('persistent STOP also prevents recurring work without reading any public source',async()=>{
 const s=recurringFixture();
 s.e.DB.prepare=()=>({first:async()=>({enabled:0})});
 let calls=0;
 const output=await replenishApprovedJobs(s.e,{now:SERIES_NOW,fetcher:async()=>{calls++;throw Error('unexpected');},
  submit:async()=>{calls++;throw Error('unexpected');}});
 assert.equal(output.status,'stopped');assert.equal(calls,0);
});
