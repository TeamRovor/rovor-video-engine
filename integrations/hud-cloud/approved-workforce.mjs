import {prepareWalterReview,walterAcceptedSql} from './github-patch-gateway.mjs';
// Bounded, Mac-independent Gemini workforce lane in the existing Cloudflare HUD.
// This does NOT replace the original private Site or its separate D1/reviews.
// Only a trusted writer can submit GitHub-validated canonical public tasks.
// STOP starts closed; previously attempted jobs must never be re-enqueued.
import {validateJob} from '../ghost-cloud/runtime.mjs';
import {cloudGeminiChat,geminiModelEvidence} from './cloud-gemini-chat.mjs';
import {verifyDiscoveryJobFreshness} from './discovery-preflight.mjs';

const MODEL='gemini-3.5-flash-lite';
const MAX_DAILY=3;
const MAX_OUTPUT=12000;
const DAY=86400000;
const SERIES_DAYS=7;
const MAX_PENDING_REVIEWS=3;
const MAX_DISCOVERY_PREFLIGHTS_PER_TICK=3;
const DISCOVERY_KEY=/^(run|issue|pr)-[1-9][0-9]{0,11}$/;
const DISCOVERY_MAX_AGE=36*3600000;
const REPO='https://github.com/TeamRovor/rovor-video-engine';
const json=(value,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'no-store'}});
const validId=id=>typeof id==='string'&&/^[a-z0-9][a-z0-9-]{0,149}$/.test(id);
const verifiedCount=value=>typeof value==='string'&&/^(0|[1-9][0-9]{0,15})$/.test(value)&&Number.isSafeInteger(Number(value))?Number(value):null;
const digest=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),
 b=>b.toString(16).padStart(2,'0')).join('');

export async function intake(db,body,now=Date.now()){
 let job;
 try{
  if(!body||Object.keys(body).sort().join(',')!=='approval,job,revision'||
     body.approval!=='trusted_canonical_owner_approval_v1'||
     typeof body.revision!=='string'||!/^v(?:[2-9]|[1-9][0-9]+)$/.test(body.revision))
     throw Error('invalid');
  job=validateJob(body.job);
  if(!job.id.startsWith('gc-')||job.id.startsWith('gc-patch-src-')||job.prompt.length>4000||
     !Number.isSafeInteger(now)||now<=0)throw Error('invalid');
 }catch{return {status:400,body:{error:'canonical_approval_required'}};}
 try{
  const old=await db.prepare('SELECT * FROM hud_cloud_workforce_jobs WHERE id=?').bind(job.id).first();
  if(old){
   const unchanged=['employee','task_id','kind','title','prompt','source_commit']
     .every(k=>old[k]===job[k])&&old.revision===body.revision;
   return unchanged?{status:200,body:{id:job.id,duplicate:true,queued:false}}:
     {status:409,body:{error:'immutable_job_conflict'}};
  }
  const result=await db.prepare(`INSERT OR IGNORE INTO hud_cloud_workforce_jobs
   (id,task_id,employee,kind,title,prompt,source_commit,revision,created_at,state,human_review)
   VALUES (?,?,?,?,?,?,?,?,?,'queued','not_recorded')`)
   .bind(job.id,job.task_id,job.employee,job.kind,job.title,job.prompt,job.source_commit,body.revision,now).run();
  if(result.meta.changes!==1)return {status:409,body:{error:'immutable_job_conflict'}};
  return {status:201,body:{id:job.id,queued:true,mac_required:false,execution_started:false,
    owner_review_required:true}};
 }catch{return {status:503,body:{error:'private_workforce_store_unavailable'}};}
}

// Standing approval is independent from the transient one-shot pilot gate.
// A protected owner workflow must supply its exact checked-out main SHA, and
// D1 itself requires a previously human-PASS'd real Gemini draft.
export async function control(db,enabled,seriesCommit=null,now=Date.now()){
 if(typeof enabled!=='boolean'||(seriesCommit!==null&&
    (!enabled||typeof seriesCommit!=='string'||!/^[a-f0-9]{40}$/.test(seriesCommit)||
     !Number.isSafeInteger(now)||now<1)))
  return {status:400,body:{error:'invalid_control'}};
 try{
  if(!enabled){
   const results=await db.batch([
    db.prepare('UPDATE hud_cloud_workforce_series SET active=0 WHERE id=1').bind(),
    db.prepare('UPDATE hud_cloud_workforce_control SET enabled=0 WHERE id=1').bind(),
    db.prepare(`UPDATE hud_cloud_workforce_jobs SET state='failed',finished_at=?,
     error_code='stopped_before_claim' WHERE state='queued' AND (id LIKE 'gc-rec-%' OR id LIKE 'gc-patch-src-%' OR id LIKE 'wr-%')`).bind(now),
    // A separately authorized draft PR is also work: STOP permanently
    // revokes every *queued* approval. It cannot rearm on a later START.
    // Leave in-flight/uncertain rows intact for manual reconciliation.
    db.prepare(`UPDATE hud_github_patch_jobs SET state='failed',finished_at=?,
     error_code='stopped_before_github_write' WHERE state='queued'`).bind(now)
   ]);
   if(results.slice(0,2).some(r=>r.meta?.changes!==1)||
      results.slice(2).some(r=>typeof r.meta?.changes!=='number'))
    return {status:503,body:{error:'workforce_control_unavailable'}};
   return {status:200,body:{enabled:false,recurring_authorized:false}};
  }
  if(seriesCommit!==null){
   const until=now+SERIES_DAYS*DAY;
   const results=await db.batch([
    db.prepare(`UPDATE hud_cloud_workforce_series SET active=1,source_commit=?,
     approved_at=?,expires_at=?
     WHERE id=1 AND active=0
     AND (SELECT enabled FROM hud_cloud_workforce_control WHERE id=1)=0
     AND EXISTS(SELECT 1 FROM hud_cloud_workforce_jobs WHERE
       state='needs_review' AND human_review='passed' AND actual_model=?
       AND LENGTH(output_sha256)=64 AND reviewed_at>0)
     AND NOT EXISTS(SELECT 1 FROM hud_cloud_workforce_jobs WHERE
       state IN ('queued','running','uncertain'))`)
     .bind(seriesCommit,now,until,MODEL),
    db.prepare(`UPDATE hud_cloud_workforce_control SET enabled=1 WHERE id=1
      AND enabled=0 AND EXISTS(SELECT 1 FROM hud_cloud_workforce_series
        WHERE id=1 AND active=1 AND approved_at=? AND source_commit=?)`)
     .bind(now,seriesCommit)
   ]);
   if(results.some(r=>r.meta?.changes!==1))
    return {status:409,body:{error:'owner_pass_and_stopped_empty_queue_required'}};
   return {status:200,body:{enabled:true,recurring_authorized:true,expires_at:until}};
  }
  // Ordinary pilot gate is not permission to replenish recurring work.
  const result=await db.prepare('UPDATE hud_cloud_workforce_control SET enabled=1 WHERE id=1').bind().run();
  if(result.meta.changes!==1)return {status:503,body:{error:'workforce_control_unavailable'}};
  return {status:200,body:{enabled:true}};
 }catch{return {status:503,body:{error:'workforce_control_unavailable'}};}
}

async function seriesState(db){
 return db.prepare('SELECT active,source_commit,approved_at,expires_at FROM hud_cloud_workforce_series WHERE id=1').first();
}

export function discoveryPrompt(key,priority){
 if(typeof key!=='string'||!DISCOVERY_KEY.test(key)||
    !Number.isInteger(priority)||priority<1||priority>100)throw Error('invalid_discovery_evidence');
 const [kind,num]=key.split('-');
 const link=REPO+(kind==='run'?'/actions/runs/':kind==='issue'?'/issues/':'/pull/')+num;
 const type=kind==='run'?'a failed main-branch CI run':kind==='issue'?
   'an open unassigned issue with an allowed defect label':'a stale open unassigned pull request';
 // Only numeric, allowlisted observation data is sent to the model. Never
 // pass raw discovery content, issue bodies, private code, logs or credentials.
 return 'ROVOR verified GitHub discovery: '+type+' (#'+num+'), priority '+priority+
  '/100, source '+link+'. You cannot browse this URL and have no source code or log contents. '+
  'Write a plain-English engineering report under 300 words with EXACTLY these five Markdown headings: '+
  '## Task and available evidence, ## Deliverable created, ## Potential benefit, '+
  '## Concerns and uncertainties, ## Recommended next step. '+
  'Task and available evidence: name the exact GitHub record and why it could matter to ROVOR. '+
  'Deliverable created: state you produced ONLY a written investigation plan. No code, tests, diagnosis, '+
  'merge or deployment were completed. Describe the concrete checks your plan proposes. '+
  'Potential benefit: explain a specific possible operational value, using conditional language; '+
  'never invent measured savings or claim the issue was fixed. '+
  'Concerns and uncertainties: explain two concrete limitations, especially that you could not read the '+
  'GitHub record contents, source files or logs and cannot verify the cause. Mention possible obsolescence. '+
  'Recommended next step: give one bounded read-only action and 2-3 specific checks for an engineer, '+
  'including the evidence needed before anyone attempts a fix. Define jargon and do not invent results. '+
  'Do not invent a diagnosis, command results, files or a completed fix; do not execute, publish, merge, '+ 
  'or request credentials. This is a draft only, pending human PASS/FAIL.';
}

// Refill only from fresh, already-recorded GitHub discovery evidence.
// One unique task per GitHub source across all activation windows; no catch-up
// or repeated inference about the same evidence. Limit review/backlog pressure.
export async function refillDiscovery(db,series,now){
 if(!series||series.active!==1||!/^[a-f0-9]{40}$/.test(series.source_commit||'')||
    !Number.isSafeInteger(series.approved_at)||series.approved_at>now||
    !Number.isSafeInteger(series.expires_at)||series.expires_at<=now)
  return {queued:false,reason:'standing_approval_inactive'};
 const row=await db.prepare(`SELECT discovery_key,priority FROM hud_auto_discovery_inbox d
   WHERE created_at>=? AND created_at<=?
   AND NOT EXISTS(SELECT 1 FROM hud_cloud_workforce_jobs j
     WHERE j.task_id='cloud-discovery-'||d.discovery_key)
   ORDER BY priority DESC,created_at DESC,discovery_key LIMIT 1`)
  .bind(now-DISCOVERY_MAX_AGE,now).first();
 if(!row)return {queued:false,reason:'no_fresh_unattempted_discovery'};
 if(!DISCOVERY_KEY.test(row.discovery_key||'')||!Number.isInteger(row.priority)||
    row.priority<1||row.priority>100)
  return {queued:false,reason:'invalid_discovery_evidence'};
 const key=row.discovery_key,taskId='cloud-discovery-'+key;
 const job=validateJob({
  id:'gc-rec-'+(await digest('rovor-discovery-v2:'+key)).slice(0,48),
  task_id:taskId,employee:'Mike',kind:'code_review',
  title:'Investigate verified GitHub discovery '+key,
  prompt:discoveryPrompt(key,row.priority),source_commit:series.source_commit,
  data_class:'public_repository'
 });
 const saved=await db.prepare(`INSERT OR IGNORE INTO hud_cloud_workforce_jobs
   (id,task_id,employee,kind,title,prompt,source_commit,revision,created_at,state,human_review)
   SELECT ?,?,?,?,?,?,?,?,?,'queued','not_recorded'
   WHERE (SELECT enabled FROM hud_cloud_workforce_control WHERE id=1)=1
   AND EXISTS(SELECT 1 FROM hud_cloud_workforce_series WHERE id=1
     AND active=1 AND approved_at=? AND source_commit=? AND expires_at>?)
   AND NOT EXISTS(SELECT 1 FROM hud_cloud_workforce_jobs WHERE state IN ('queued','running','uncertain'))
   AND NOT EXISTS(SELECT 1 FROM hud_cloud_workforce_jobs WHERE task_id=?)
   AND (SELECT COUNT(*) FROM hud_cloud_workforce_jobs WHERE state='needs_review'
      AND human_review='not_recorded' AND id NOT LIKE 'wr-%' AND NOT ${walterAcceptedSql})<?
   AND (SELECT COUNT(*) FROM hud_cloud_workforce_jobs WHERE started_at>=?)<?`)
  .bind(job.id,job.task_id,job.employee,job.kind,job.title,job.prompt,job.source_commit,'v2',now,
   series.approved_at,series.source_commit,now,job.task_id,MAX_PENDING_REVIEWS,now-DAY,MAX_DAILY).run();
 return {queued:saved.meta.changes===1,reason:saved.meta.changes===1?'fresh_discovery_queued':'queue_or_review_limit'};
}

// Record actual scheduled events only, not HTTP/manual ticks. A tick's
// dispatch report is not a separate proof of provider inference.
export async function recordNativeTick(db,scheduledAt,startedAt,finishedAt,result){
 if(!Number.isSafeInteger(scheduledAt)||scheduledAt<=0||
    !Number.isSafeInteger(startedAt)||startedAt<=0||
    !Number.isSafeInteger(finishedAt)||finishedAt<startedAt)
  throw Error('native_tick_timestamp_invalid');
 const state=result?.body?.state||result?.body?.error;
 const safeState=typeof state==='string'&&/^[a-z0-9_]{1,80}$/.test(state)?state:'unconfirmed';
 const dispatch=result?.body?.dispatched===1?1:0;
 const job=validId(result?.body?.id)?result.body.id:null;
 const completed=dispatch===1&&job!==null&&safeState==='needs_review'&&
  result?.status===200&&result?.body?.inference_completed===true?1:0;
 const code=Number.isInteger(result?.status)&&result.status>=100&&result.status<=599?result.status:503;
 const row=await db.prepare(`INSERT INTO hud_cloud_workforce_native_ticks
  (id,scheduled_at,started_at,finished_at,result_state,http_status,dispatch_reported,job_id,inference_completed)
  VALUES (?,?,?,?,?,?,?,?,?)`).bind(crypto.randomUUID(),scheduledAt,startedAt,finishedAt,
   safeState,code,dispatch,job,completed).run();
 if(row.meta?.changes!==1)throw Error('native_tick_receipt_unconfirmed');
}

export async function status(db,now=Date.now()){
 try{
  const gate=await db.prepare('SELECT enabled FROM hud_cloud_workforce_control WHERE id=1').first();
  if(!gate)return {status:503,body:{error:'workforce_control_unavailable'}};
  const plan=await seriesState(db);
  const ticks=await db.prepare(`SELECT scheduled_at,started_at,finished_at,result_state,
   http_status,dispatch_reported,job_id,inference_completed
   FROM hud_cloud_workforce_native_ticks ORDER BY started_at DESC,id DESC LIMIT 12`).all();
  const counts=await db.prepare(`SELECT
    COALESCE(SUM(CASE WHEN state='queued' THEN 1 ELSE 0 END),0) queued,
    COALESCE(SUM(CASE WHEN state IN ('running','uncertain') THEN 1 ELSE 0 END),0) in_flight,
    COALESCE(SUM(CASE WHEN state='needs_review' AND human_review='not_recorded' AND id NOT LIKE 'wr-%' AND NOT ${walterAcceptedSql} THEN 1 ELSE 0 END),0) pending_review,
    COALESCE(SUM(CASE WHEN started_at>=? THEN 1 ELSE 0 END),0) rolling_attempts,
    MIN(CASE WHEN started_at>=? THEN started_at ELSE NULL END) oldest_attempt
    FROM hud_cloud_workforce_jobs`).bind(now-DAY,now-DAY).first();
  const fresh=await db.prepare(`SELECT COUNT(*) n FROM hud_auto_discovery_inbox d
    WHERE d.created_at>=? AND d.created_at<=?
    AND NOT EXISTS(SELECT 1 FROM hud_cloud_workforce_jobs j
      WHERE j.task_id='cloud-discovery-'||d.discovery_key)`).bind(now-DISCOVERY_MAX_AGE,now).first();
  const recurring=gate.enabled===1&&plan?.active===1&&plan.expires_at>now;
  const observed=[];
  if(gate.enabled!==1)observed.push('stop_closed');
  if(!recurring)observed.push('standing_authorization_inactive');
  if(counts.in_flight>0)observed.push('running_or_uncertain_claim');
  if(counts.rolling_attempts>=MAX_DAILY)observed.push('rolling_day_attempt_limit');
  if(counts.pending_review>=MAX_PENDING_REVIEWS)observed.push('pending_review_limit');
  if(counts.queued===0)observed.push('no_queued_job');
  if(fresh.n===0)observed.push('no_fresh_unattempted_discovery');
  const nextSlot=counts.rolling_attempts>=MAX_DAILY&&Number.isSafeInteger(counts.oldest_attempt)
    ?counts.oldest_attempt+DAY:null;
  const rows=await db.prepare(`SELECT j.id,j.task_id,j.employee,j.kind,j.title,j.source_commit,j.created_at,
    j.started_at,j.finished_at,j.state,j.actual_model,j.output_sha256,j.human_review,j.reviewed_at,j.error_code,
    w.error_code AS walter_verdict,w.state AS walter_state,w.id AS walter_id,w.output AS walter_reason,
    u.provider,u.requested_model,u.tokens_input,u.tokens_output
    FROM hud_cloud_workforce_jobs j LEFT JOIN hud_cloud_workforce_usage u
    ON u.job_id=j.id AND u.output_sha256=j.output_sha256 AND u.actual_model=j.actual_model
    LEFT JOIN hud_cloud_workforce_jobs w ON w.id='wr-'||j.id AND w.revision=j.output_sha256
    WHERE j.id NOT LIKE 'wr-%' ORDER BY j.created_at DESC LIMIT 50`).all();
  return {status:200,body:{source:'existing_cloudflare_hud_gemini_workforce',
    mac_required:false,enabled:gate.enabled===1,configured_model:MODEL,
    recurring_execution_authorized:recurring,
    admission:{source:'read_only_private_D1',observed_at:now,
      queued_jobs:counts.queued,running_or_uncertain:counts.in_flight,
      pending_reviews:counts.pending_review,rolling_day_attempts:counts.rolling_attempts,
      rolling_day_limit:MAX_DAILY,pending_review_limit:MAX_PENDING_REVIEWS,
      fresh_unattempted_discoveries:fresh.n,
      earliest_rolling_slot_at:nextSlot,
      observed_constraints:observed,provider_admission_verified_by_this_read:false},
    standing_plan:{active:plan?.active===1&&plan.expires_at>now,
      expires_at:plan?.active===1?plan.expires_at:null,
      source:'fresh_github_discovery',max_attempts_per_rolling_day:MAX_DAILY,
      max_pending_reviews:MAX_PENDING_REVIEWS},items:rows.results||[],
    native_schedule:{source:'cloudflare_scheduled_event',recent_ticks:ticks.results||[],
      last_tick:(ticks.results||[])[0]||null},
    task_source:'trusted_approved_canonical_queue',
    site_review_ledger_synced:false}};
 }catch{return {status:503,body:{error:'private_workforce_store_unavailable'}};}
}

export async function draft(db,id){
 if(!validId(id))return {status:400,body:{error:'invalid_job_id'}};
 try{
  const row=await db.prepare(`SELECT j.id,j.employee,j.title,j.state,j.output,j.output_sha256,
    j.human_review,j.reviewed_at,u.provider,u.requested_model,u.tokens_input,u.tokens_output
    FROM hud_cloud_workforce_jobs j LEFT JOIN hud_cloud_workforce_usage u
    ON u.job_id=j.id AND u.output_sha256=j.output_sha256 AND u.actual_model=j.actual_model
    WHERE j.id=?`).bind(id).first();
  return row?{status:200,body:row}:{status:404,body:{error:'job_not_found'}};
 }catch{return {status:503,body:{error:'private_workforce_store_unavailable'}};}
}

export async function review(db,body,now=Date.now()){
 if(!body||Object.keys(body).sort().join(',')!=='job_id,output_sha256,verdict'||
    !validId(body.job_id)||!['passed','failed'].includes(body.verdict)||
    typeof body.output_sha256!=='string'||!/^[a-f0-9]{64}$/.test(body.output_sha256))
  return {status:400,body:{error:'invalid_review'}};
 try{
  const result=await db.prepare(`UPDATE hud_cloud_workforce_jobs
    SET human_review=?,reviewed_at=?
    WHERE id=? AND state='needs_review' AND human_review='not_recorded'
      AND output_sha256=? AND LENGTH(output_sha256)=64
    RETURNING id,human_review,output_sha256,reviewed_at`)
   .bind(body.verdict,now,body.job_id,body.output_sha256).first();
  if(!result)return {status:409,body:{error:'already_reviewed_or_not_reviewable'}};
  return {status:200,body:{id:result.id,human_review:result.human_review,
   output_sha256:result.output_sha256,reviewed_at:result.reviewed_at}};
 }catch{return {status:503,body:{error:'private_workforce_review_unavailable'}};}
}

// Independently testable bounded D1 discovery selection. Freshness checks are
// supplied by the server, never by a model or browser. No inference runs here.
export async function selectPreflightJob(db,plan,now,checkFreshness){
 const deadline=Number.isSafeInteger(now)&&now>0;
 if(!deadline||typeof checkFreshness!=='function')throw Error('invalid_preflight_context');
 let next=null,staleDiscarded=0,lastStaleId=null;
 for(let check=0;check<MAX_DISCOVERY_PREFLIGHTS_PER_TICK;check++){
  if(plan?.active===1)await refillDiscovery(db,plan,now);
  const candidate=await db.prepare(`SELECT id,task_id FROM hud_cloud_workforce_jobs
    WHERE state='queued'
    AND (id NOT LIKE 'gc-patch-src-%' OR EXISTS(SELECT 1 FROM hud_github_patch_task_sources s WHERE s.job_id=hud_cloud_workforce_jobs.id))
    AND NOT EXISTS(SELECT 1 FROM hud_cloud_workforce_jobs WHERE state IN ('running','uncertain'))
    AND (SELECT COUNT(*) FROM hud_cloud_workforce_jobs WHERE started_at>=?)<?
    ORDER BY CASE WHEN id LIKE 'wr-%' THEN 0 ELSE 1 END,created_at,id LIMIT 1`).bind(now-DAY,MAX_DAILY).first();
  if(!candidate)break;
  if(!candidate.id.startsWith('gc-rec-')){next=candidate;break;}
  const evidence=await checkFreshness(candidate.task_id);
  if(evidence?.state==='unavailable')return {next:null,staleDiscarded,blocked:{
   state:'discovery_source_unverified',dispatched:0,inference_completed:false,
   stale_discarded:staleDiscarded}};
  if(evidence?.state==='actionable'){next=candidate;break;}
  const removed=await db.prepare(`UPDATE hud_cloud_workforce_jobs
   SET state='failed',finished_at=?,error_code='discovery_no_longer_actionable'
   WHERE id=? AND state='queued'`).bind(now,candidate.id).run();
  if(removed.meta?.changes!==1)return {next:null,staleDiscarded,blocked:{
   state:'idle_or_safety_limited',dispatched:0}};
  staleDiscarded++;lastStaleId=candidate.id;
 }
 if(!next)return {next:null,staleDiscarded,blocked:staleDiscarded?{
  state:'discovery_no_longer_actionable',dispatched:0,id:lastStaleId,
  inference_completed:false,stale_discarded:staleDiscarded}:{
  state:'idle_or_safety_limited',dispatched:0}};
 return {next,staleDiscarded,blocked:null};
}

export async function tick(env,now=Date.now(),send=fetch){
 const db=env?.DB;
 if(!db)return {status:503,body:{error:'private_workforce_store_unavailable'}};
 try{
  const gate=await db.prepare('SELECT enabled FROM hud_cloud_workforce_control WHERE id=1').first();
  if(gate?.enabled!==1)return {status:200,body:{state:'stopped',dispatched:0}};
  const plan=await seriesState(db);
  if(plan?.active===1&&plan.expires_at<=now){
   const closed=await control(db,false);
   return {status:closed.status,body:{state:closed.status===200?'standing_approval_expired':'stop_receipt_unconfirmed',dispatched:0}};
  }
  if(env.ROVOR_GEMINI_FREE_TIER_VERIFIED!=='confirmed'||!env.GEMINI_API_KEY)
   return {status:200,body:{state:'free_tier_not_attested',dispatched:0}};
  // The first real live canary produced a recent per-model D1 completion.
  // A catalogue listing or owner boolean alone is insufficient to run jobs.
  const evidence=await geminiModelEvidence(db,now);
  if(evidence.get(MODEL)?.verification!=='verified_recent_reply')
   return {status:200,body:{state:'model_reply_evidence_missing',dispatched:0}};
  await db.prepare(`UPDATE hud_cloud_workforce_jobs AS w SET state='failed',finished_at=?,error_code='owner_review_recorded'
    WHERE state='queued' AND id LIKE 'wr-%' AND EXISTS(SELECT 1 FROM hud_cloud_workforce_jobs j
    WHERE j.id=w.task_id AND j.human_review!='not_recorded')`).bind(now).run();
  const picked=await selectPreflightJob(db,plan,now,taskId=>
   verifyDiscoveryJobFreshness(env,taskId,now,send));
  if(picked.blocked)return {status:200,body:picked.blocked};
  const next=picked.next,staleDiscarded=picked.staleDiscarded;
  const claim=await db.prepare(`UPDATE hud_cloud_workforce_jobs SET state='running',started_at=?
    WHERE id=? AND state='queued'
    AND (id NOT LIKE 'gc-patch-src-%' OR EXISTS(SELECT 1 FROM hud_github_patch_task_sources s WHERE s.job_id=hud_cloud_workforce_jobs.id))
    AND (SELECT enabled FROM hud_cloud_workforce_control WHERE id=1)=1
    AND NOT EXISTS(SELECT 1 FROM hud_cloud_workforce_jobs WHERE state IN ('running','uncertain'))
    AND (SELECT COUNT(*) FROM hud_cloud_workforce_jobs WHERE started_at>=?)<?
    RETURNING id,prompt`).bind(now,next.id,now-DAY,MAX_DAILY).first();
  if(!claim)return {status:200,body:{state:'idle_or_safety_limited',dispatched:0}};
  // STOP can change while admission reads model health or D1 claims the job.
  // Re-read the persistent gate AFTER claiming, immediately before inference.
  // A stopped claim is permanently consumed, never replayed or sent upstream.
  const lastGate=await db.prepare('SELECT enabled FROM hud_cloud_workforce_control WHERE id=1').first();
  if(lastGate?.enabled!==1){
   const aborted=await db.prepare(`UPDATE hud_cloud_workforce_jobs
    SET state='failed',finished_at=?,error_code='stopped_after_claim'
    WHERE id=? AND state='running'`).bind(Date.now(),claim.id).run();
   if(aborted.meta.changes!==1)return {status:503,body:{state:'stop_receipt_unconfirmed',dispatched:0}};
   return {status:200,body:{state:'stopped_after_claim',dispatched:0,
    id:claim.id,model:null,inference_completed:false}};
  }
  // After the durable claim, NO retry even if upstream response is uncertain.
  let state='uncertain',error_code='no_verified_response',output=null,actual_model=null,output_sha256=null;
 let tokensInput=null,tokensOutput=null;
  try{
   const response=await cloudGeminiChat({model:MODEL,messages:[{role:'user',content:claim.prompt}]},
    env,now,send);
   if(!response.ok){
    state='failed';error_code='gemini_http_'+response.status;
   }else if(response.headers.get('X-ROVOR-Provider')!=='google-gemini-cloud'||
      response.headers.get('X-ROVOR-Requested-Model')!==MODEL||
      response.headers.get('X-ROVOR-Resolved-Model')!==MODEL){
    error_code='wrong_model_or_provider_receipt';
   }else{
    tokensInput=verifiedCount(response.headers.get('X-ROVOR-Input-Tokens'));
    tokensOutput=verifiedCount(response.headers.get('X-ROVOR-Output-Tokens'));
    if(tokensInput===null||tokensOutput===null)throw Error('missing_exact_token_receipt');
    const wire=await response.text();
    if(wire.length>MAX_OUTPUT*2||!wire.includes('data: [DONE]'))throw Error('incomplete_reply');
    const chunks=[];
    for(const line of wire.split('\n')){
     if(!line.startsWith('data: ' )||line==='data: [DONE]')continue;
     const delta=JSON.parse(line.slice(6))?.choices?.[0]?.delta?.content;
     if(typeof delta==='string')chunks.push(delta);
    }
    const combined=chunks.join('');
    if(!combined.trim()||combined.length>MAX_OUTPUT)throw Error('invalid_reply');
    output=combined;actual_model=MODEL;output_sha256=await digest(output);
    state='needs_review';error_code=null;
    if(claim.id.startsWith('wr-'))error_code=/^ACCEPT\r?\n[^\r\n]{8,800}$/u.test(output.trim())?'walter_accepted':'walter_escalated';
   }
  }catch{state='uncertain';error_code='response_or_receipt_uncertain';}
  const finishedAt=Date.now();
  const finish=db.prepare(`UPDATE hud_cloud_workforce_jobs
    SET state=?,finished_at=?,actual_model=?,output=?,output_sha256=?,error_code=?
    WHERE id=? AND state='running'`)
    .bind(state,finishedAt,actual_model,output,output_sha256,error_code,claim.id);
  if(state==='needs_review'){
   // One atomic D1 batch binds the verified usage to the exact output digest.
   // Never infer per-job tokens from the project's cumulative counters.
   const receipt=db.prepare(`INSERT INTO hud_cloud_workforce_usage
    (job_id,output_sha256,provider,requested_model,actual_model,tokens_input,tokens_output,recorded_at)
    SELECT id,output_sha256,'google-gemini-cloud',?,?,?,?,?
    FROM hud_cloud_workforce_jobs WHERE id=? AND state='needs_review'
     AND output_sha256=? AND finished_at=?`)
    .bind(MODEL,MODEL,tokensInput,tokensOutput,finishedAt,claim.id,output_sha256,finishedAt);
   let review=null;
   try{review=await prepareWalterReview(env,claim.id,output,output_sha256,finishedAt);}catch{/* Keep Mike’s receipt available for human review. */}
   const results=await db.batch(review?[finish,receipt,review]:[finish,receipt]);
   if(results.slice(0,2).some(x=>x.meta?.changes!==1))
    return {status:503,body:{state:'receipt_unconfirmed',dispatched:1}};
  }else{
   const result=await finish.run();
   if(result.meta.changes!==1)return {status:503,body:{state:'receipt_unconfirmed',dispatched:1}};
  }
  return {status:200,body:{state,dispatched:1,id:claim.id,
   model:state==='needs_review'?MODEL:null,owner_review_required:state==='needs_review',
   ...(state==='needs_review'?{provider:'google-gemini-cloud',tokens_input:tokensInput,tokens_output:tokensOutput}:{}),
   inference_completed:state==='needs_review',stale_discarded:staleDiscarded}};
 }catch{return {status:503,body:{state:'runtime_or_store_unavailable',dispatched:0}};}
}
