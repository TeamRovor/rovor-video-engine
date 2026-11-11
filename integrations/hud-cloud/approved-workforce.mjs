// Bounded, Mac-independent Gemini workforce lane in the existing Cloudflare HUD.
// This does NOT replace the original private Site or its separate D1/reviews.
// Only a trusted writer can submit GitHub-validated canonical public tasks.
// STOP starts closed; previously attempted jobs must never be re-enqueued.
import {validateJob} from '../ghost-cloud/runtime.mjs';
import {cloudGeminiChat,geminiModelEvidence} from './cloud-gemini-chat.mjs';

const MODEL='gemini-3.5-flash-lite';
const MAX_DAILY=3;
const MAX_OUTPUT=12000;
const json=(value,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'no-store'}});
const validId=id=>typeof id==='string'&&/^[a-z0-9][a-z0-9-]{0,149}$/.test(id);
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
  if(!job.id.startsWith('gc-')||job.prompt.length>4000||
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

export async function control(db,enabled){
 if(typeof enabled!=='boolean')return {status:400,body:{error:'invalid_control'}};
 try{
  const result=await db.prepare('UPDATE hud_cloud_workforce_control SET enabled=? WHERE id=1')
   .bind(enabled?1:0).run();
  if(result.meta.changes!==1)return {status:503,body:{error:'workforce_control_unavailable'}};
  return {status:200,body:{enabled}};
 }catch{return {status:503,body:{error:'workforce_control_unavailable'}};}
}

export async function status(db){
 try{
  const gate=await db.prepare('SELECT enabled FROM hud_cloud_workforce_control WHERE id=1').first();
  if(!gate)return {status:503,body:{error:'workforce_control_unavailable'}};
  const rows=await db.prepare(`SELECT id,task_id,employee,kind,title,source_commit,created_at,
    started_at,finished_at,state,actual_model,output_sha256,human_review,reviewed_at,error_code
    FROM hud_cloud_workforce_jobs ORDER BY created_at DESC LIMIT 50`).all();
  return {status:200,body:{source:'existing_cloudflare_hud_gemini_workforce',
    mac_required:false,enabled:gate.enabled===1,configured_model:MODEL,
    recurring_execution_authorized:gate.enabled===1,items:rows.results||[],
    task_source:'trusted_approved_canonical_queue',
    site_review_ledger_synced:false}};
 }catch{return {status:503,body:{error:'private_workforce_store_unavailable'}};}
}

export async function draft(db,id){
 if(!validId(id))return {status:400,body:{error:'invalid_job_id'}};
 try{
  const row=await db.prepare(`SELECT id,employee,title,state,output,output_sha256,
    human_review,reviewed_at FROM hud_cloud_workforce_jobs WHERE id=?`).bind(id).first();
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

export async function tick(env,now=Date.now(),send=fetch){
 const db=env?.DB;
 if(!db)return {status:503,body:{error:'private_workforce_store_unavailable'}};
 try{
  const gate=await db.prepare('SELECT enabled FROM hud_cloud_workforce_control WHERE id=1').first();
  if(gate?.enabled!==1)return {status:200,body:{state:'stopped',dispatched:0}};
  if(env.ROVOR_GEMINI_FREE_TIER_VERIFIED!=='confirmed'||!env.GEMINI_API_KEY)
   return {status:200,body:{state:'free_tier_not_attested',dispatched:0}};
  // The first real live canary produced a recent per-model D1 completion.
  // A catalogue listing or owner boolean alone is insufficient to run jobs.
  const evidence=await geminiModelEvidence(db,now);
  if(evidence.get(MODEL)?.verification!=='verified_recent_reply')
   return {status:200,body:{state:'model_reply_evidence_missing',dispatched:0}};
  const claim=await db.prepare(`UPDATE hud_cloud_workforce_jobs SET state='running',started_at=?
    WHERE id=(SELECT id FROM hud_cloud_workforce_jobs WHERE state='queued'
      ORDER BY created_at,id LIMIT 1)
    AND (SELECT enabled FROM hud_cloud_workforce_control WHERE id=1)=1
    AND NOT EXISTS(SELECT 1 FROM hud_cloud_workforce_jobs WHERE state='running')
    AND (SELECT COUNT(*) FROM hud_cloud_workforce_jobs WHERE started_at>=?)<?
    RETURNING id,prompt`).bind(now,now-86400000,MAX_DAILY).first();
  if(!claim)return {status:200,body:{state:'idle_or_safety_limited',dispatched:0}};
  // After the durable claim, NO retry even if upstream response is uncertain.
  let state='uncertain',error_code='no_verified_response',output=null,actual_model=null,output_sha256=null;
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
   }
  }catch{state='uncertain';error_code='response_or_receipt_uncertain';}
  const result=await db.prepare(`UPDATE hud_cloud_workforce_jobs
    SET state=?,finished_at=?,actual_model=?,output=?,output_sha256=?,error_code=?
    WHERE id=? AND state='running'`)
    .bind(state,Date.now(),actual_model,output,output_sha256,error_code,claim.id).run();
  if(result.meta.changes!==1)return {status:503,body:{state:'receipt_unconfirmed',dispatched:1}};
  return {status:200,body:{state,dispatched:1,id:claim.id,
   model:state==='needs_review'?MODEL:null,owner_review_required:state==='needs_review',
   inference_completed:state==='needs_review'}};
 }catch{return {status:503,body:{state:'runtime_or_store_unavailable',dispatched:0}};}
}
