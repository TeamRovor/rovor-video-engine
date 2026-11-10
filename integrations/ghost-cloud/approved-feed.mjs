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

// Optional recurring inference requires a SEPARATE explicit private owner approval.
// A one-shot approval never implies permission to run again.
const SERIES_APPROVAL='owner_approved_recurring_cloud_inference_v1';
const SERIES_WINDOW='{{RUN_WINDOW_UTC}}';
const HOUR=3600000;
function checkSeries(series,now) {
 if(!Array.isArray(series)||series.length>MAX_APPROVALS||
    !Number.isSafeInteger(now)||now<0)throw Error('invalid_recurring_approvals');
 const seen=new Set();
 for(const item of series){
  if(!item||Object.keys(item).sort().join(',')!==
      'approval,cadence_minutes,expires_at,max_runs,revision,starts_at,task_id'||
     item.approval!==SERIES_APPROVAL||!ID.test(item.task_id)||!REV.test(item.revision)||
     ![60,1440].includes(item.cadence_minutes)||
     !Number.isSafeInteger(item.max_runs)||item.max_runs<1||item.max_runs>168||
     typeof item.starts_at!=='string'||typeof item.expires_at!=='string'||
     seen.has(item.task_id))throw Error('invalid_recurring_approvals');
  const start=Date.parse(item.starts_at),end=Date.parse(item.expires_at);
  const interval=item.cadence_minutes*60000;
  if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||
     new Date(start).toISOString()!==item.starts_at||
     new Date(end).toISOString()!==item.expires_at||
     start<0||start%interval!==0||end<=start||
     end-start>7*24*HOUR||
     end>start+item.max_runs*interval)throw Error('invalid_recurring_approvals');
  seen.add(item.task_id);
 }
}
async function planRecurringJobs(tasks,routing,commit,series,now) {
 const jobs=[];
 for(const approval of series){
  const start=Date.parse(approval.starts_at),end=Date.parse(approval.expires_at);
  if(now<start||now>=end)continue; // Never catch up missed slots.
  const interval=approval.cadence_minutes*60000;
  const slot=Math.floor((now-start)/interval);
  if(slot>=approval.max_runs)continue;
  const [base]=await planApprovedJobs(tasks,routing,commit,
    [{task_id:approval.task_id,revision:approval.revision}]);
  if(!base.prompt.includes(SERIES_WINDOW))throw Error('recurring_template_missing');
  const windowStart=new Date(start+slot*interval).toISOString();
  const prompt=base.prompt.replaceAll(SERIES_WINDOW,windowStart);
  // The same task/window has the same ID even after unrelated source changes;
  // changed content then conflicts rather than silently replaying.
  const key=JSON.stringify([base.task_id,approval.starts_at,slot]);
  const digest=await crypto.subtle.digest('SHA-256',utf8.encode(key));
  const id='gc-rec-'+Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('').slice(0,48);
  jobs.push(validateJob({...base,id,prompt,data_class:'public_repository'}));
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

export async function replenishApprovedJobs(env,{fetcher=fetch,submit=submitToExistingWriter,now=Date.now()}={}) {
 // STOP is persistent in D1. Recheck before every writer operation.
 if(!await enabled(env.DB))return {status:'stopped',queued:0,duplicates:0};
 const commit=env.GHOST_FEED_COMMIT;
 if(!SHA.test(commit||''))throw Error('invalid_source_commit');
 let approvals,series;
 try{
  approvals=JSON.parse(env.GHOST_APPROVED_TASKS||'[]');
  series=JSON.parse(env.GHOST_APPROVED_SERIES||'[]');
 }catch{throw Error('invalid_approvals');}
 checkApprovals(approvals);checkSeries(series,now);
 if(approvals.length+series.length>MAX_APPROVALS)throw Error('too_many_approved_packets');
 if(!approvals.length&&!series.length)return {status:'empty',queued:0,duplicates:0};
 const {tasks,routing}=await fetchCanonicalQueue(commit,fetcher);
 const jobs=[...await planApprovedJobs(tasks,routing,commit,approvals),
   ...await planRecurringJobs(tasks,routing,commit,series,now)];
 let queued=0,duplicates=0;
 for(const job of jobs){
  if(!await enabled(env.DB))return {status:'stopped',queued,duplicates};
  if(job.id.startsWith('gc-rec-')){
   // A stalled provider cannot create an unlimited backlog of hourly work.
   // The current slot is idempotent, and an older unattempted slot blocks
   // newer slots for the SAME canonical task until it is attempted.
   const prior=await env.DB.prepare('SELECT id FROM ghost_cloud_jobs WHERE id=?').bind(job.id).first();
   if(prior){duplicates++;continue;}
   const pending=await env.DB.prepare(
     "SELECT 1 AS pending FROM ghost_cloud_jobs j WHERE j.task_id=? AND j.id LIKE 'gc-rec-%' "+
     "AND NOT EXISTS(SELECT 1 FROM ghost_cloud_attempts a WHERE a.job_id=j.id) LIMIT 1"
   ).bind(job.task_id).first();
   if(pending)continue;
  }
  const receipt=await submit(job,env);
  if(receipt?.id!==job.id)throw Error('writer_invalid_receipt');
  if(receipt.queued===true)queued++;
  else if(receipt.duplicate===true)duplicates++;
  else throw Error('writer_invalid_receipt');
 }
 return {status:'complete',queued,duplicates};
}
