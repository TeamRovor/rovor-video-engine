// One-shot, cloud-capable approved task intake. No scheduler, model call, or Mac dependency.
// The canonical queue owns tasks; a private allowlist and immutable Git SHA gate admission.
import {validateJob} from './runtime.mjs';

const SHA=/^[a-f0-9]{40}$/;
const ID=/^[a-z0-9][a-z0-9-]{0,149}$/;
const REV=/^[a-z0-9][a-z0-9-]{0,39}$/;
const MAX_APPROVALS=9;
const MAX_SOURCE_BYTES=1048576;
const BASE='https://raw.githubusercontent.com/TeamRovor/rovor-video-engine/';
const utf8=new TextEncoder();

async function readBoundedJson(response) {
 if(!response.ok || !response.body)throw Error('source_unavailable');
 const reader=response.body.getReader();let total=0;const chunks=[];
 try {
  for(;;) {
   const {done,value}=await reader.read();if(done)break;
   total+=value.byteLength;if(total>MAX_SOURCE_BYTES)throw Error('source_too_large');
   chunks.push(value);
  }
 } finally {await reader.cancel().catch(()=>{});}
 const data=new Uint8Array(total);let offset=0;
 for(const part of chunks){data.set(part,offset);offset+=part.byteLength;}
 try{return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(data));}
 catch{throw Error('invalid_source_json');}
}

export async function fetchCanonicalQueue(commit,fetcher=fetch) {
 if(!SHA.test(commit))throw Error('invalid_source_commit');
 const paths=['coordination/tasks.json','coordination/work-routing.json'];
 const documents=await Promise.all(paths.map(async path=>{
  const response=await fetcher(BASE+commit+'/'+path,{method:'GET',redirect:'error',signal:AbortSignal.timeout(15000)});
  return readBoundedJson(response);
 }));
 return {tasks:documents[0],routing:documents[1]};
}

function checkApprovals(approvals) {
 if(!Array.isArray(approvals)||approvals.length>MAX_APPROVALS)throw Error('invalid_approvals');
 const seen=new Set();
 for(const item of approvals){
  if(!item||Object.keys(item).sort().join(',')!=='revision,task_id'||
    !ID.test(item.task_id)||!REV.test(item.revision)||seen.has(item.task_id))throw Error('invalid_approvals');
  seen.add(item.task_id);
 }
}

async function jobId(task,packet) {
 // Excludes the source commit: unrelated queue edits cannot replay unchanged work.
 const canonical=JSON.stringify([task.id,packet.revision,packet.employee,packet.kind,packet.prompt]);
 const digest=await crypto.subtle.digest('SHA-256',utf8.encode(canonical));
 return 'gc-'+Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('').slice(0,48);
}

export async function planApprovedJobs(tasks,routing,commit,approvals) {
 if(!SHA.test(commit))throw Error('invalid_source_commit');
 checkApprovals(approvals);
 if(!tasks||!Array.isArray(tasks.tasks)||!routing||typeof routing.tasks!=='object'||!routing.tasks)throw Error('invalid_canonical_queue');
 const byId=new Map();
 for(const task of tasks.tasks){
  if(!task||!ID.test(task.id)||byId.has(task.id))throw Error('invalid_canonical_queue');
  byId.set(task.id,task);
 }
 const jobs=[];
 for(const approval of approvals){
  const task=byId.get(approval.task_id);
  if(!task)throw Error('unknown_task');
  if(task.status!=='active'||typeof task.owner!=='string'||!task.owner.trim()||
     !Array.isArray(task.scopes)||!task.scopes.length)throw Error('task_not_claimed');
  const route=routing.tasks[task.id];
  if(!route||typeof route.lane!=='string'||!Array.isArray(route.requires))throw Error('task_unrouted');
  if(!Array.isArray(task.depends_on)||task.depends_on.some(id=>byId.get(id)?.status!=='done'))throw Error('task_dependency_blocked');
  const packet=task.cloud_inference;
  if(!packet||Object.keys(packet).sort().join(',')!=='approved_for_cloud,data_class,employee,kind,prompt,revision'||
     packet.approved_for_cloud!==true||packet.data_class!=='public_repository'||
     packet.revision!==approval.revision)throw Error('cloud_packet_not_approved');
  // The public queue is the only prompt source; private allowlist contains IDs, never text.
  const job=validateJob({id:await jobId(task,packet),employee:packet.employee,task_id:task.id,
   kind:packet.kind,title:task.title,prompt:packet.prompt,source_commit:commit,data_class:'public_repository'});
  jobs.push(job);
 }
 return jobs;
}

async function enabled(db) {
 if(!db?.prepare)throw Error('missing_database');
 return (await db.prepare('SELECT enabled FROM ghost_cloud_control WHERE id=1').first())?.enabled===1;
}

async function submitToExistingWriter(job,env) {
 if(typeof env.GHOST_WRITER_TOKEN!=='string'||env.GHOST_WRITER_TOKEN.length<32)throw Error('missing_writer_secret');
 const {default:worker}=await import('./worker.mjs');
 // Local in-process invocation; no new public endpoint or secret in a URL.
 const request=new Request('https://ghost.internal/api/ghost/jobs',{method:'POST',headers:{
  Authorization:'Bearer '+env.GHOST_WRITER_TOKEN,'Content-Type':'application/json'
 },body:JSON.stringify(job)});
 const response=await worker.fetch(request,env);
 if(response.status!==201&&response.status!==200)throw Error('writer_rejected');
 const data=await response.json();
 if(data.id!==job.id||!(data.queued===true||data.duplicate===true))throw Error('writer_invalid_receipt');
 return data;
}

export async function replenishApprovedJobs(env,{fetcher=fetch,submit=submitToExistingWriter}={}) {
 // STOP is persistent in D1. Recheck before every writer operation.
 if(!await enabled(env.DB))return {status:'stopped',queued:0,duplicates:0};
 const commit=env.GHOST_FEED_COMMIT;
 if(!SHA.test(commit||''))throw Error('invalid_source_commit');
 let approvals;
 try{approvals=JSON.parse(env.GHOST_APPROVED_TASKS||'');}
 catch{throw Error('invalid_approvals');}
 checkApprovals(approvals);
 if(!approvals.length)return {status:'empty',queued:0,duplicates:0};
 const {tasks,routing}=await fetchCanonicalQueue(commit,fetcher);
 const jobs=await planApprovedJobs(tasks,routing,commit,approvals);
 let queued=0,duplicates=0;
 for(const job of jobs){
  if(!await enabled(env.DB))return {status:'stopped',queued,duplicates};
  const receipt=await submit(job,env);
  if(receipt?.id!==job.id)throw Error('writer_invalid_receipt');
  if(receipt.queued===true)queued++;
  else if(receipt.duplicate===true)duplicates++;
  else throw Error('writer_invalid_receipt');
 }
 return {status:'complete',queued,duplicates};
}
