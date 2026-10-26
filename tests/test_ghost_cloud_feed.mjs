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
