#!/usr/bin/env node
// Trusted GitHub production environment operator for the EXISTING Cloudflare HUD.
// No arbitrary prompt, paid model, Site auth bypass, or old v1 task replay.
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {planApprovedJobs} from '../integrations/ghost-cloud/approved-feed.mjs';
const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';
const MODEL='gemini-3.5-flash-lite';
const validToken=s=>typeof s==='string'&&s.length>=32&&!/[\r\n]/.test(s);
const reader=process.env.ROVOR_HUD_READER_TOKEN;
const writer=process.env.ROVOR_HUD_WRITER_TOKEN;
const sha=process.env.GITHUB_SHA;
const operation=process.env.ROVOR_WORKFORCE_ACTION;
const taskId=process.env.ROVOR_WORKFORCE_TASK_ID||'';
const revision=process.env.ROVOR_WORKFORCE_REVISION||'';
const confirm=process.env.ROVOR_OWNER_CONFIRMS_NEW_TASK==='true';
const reporter=message=>console.log('ROVOR protected Gemini workforce: '+message);

async function api(path,{method='GET',write=false,body=null}={}){
 const credential=write?writer:reader;
 if(!validToken(credential))throw Error('independent_production_credential_missing');
 const r=await fetch(ORIGIN+path,{method,redirect:'manual',cache:'no-store',
  headers:{Authorization:'Bearer '+credential,
   ...(body===null?{}:{'Content-Type':'application/json'})},
  ...(body===null?{}:{body:JSON.stringify(body)}),
  signal:AbortSignal.timeout(45000)});
 if(r.status!==200&&r.status!==201)throw Error('private_http_'+r.status);
 const raw=await r.text();
 if(raw.length>65000)throw Error('private_reply_too_large');
 let parsed;try{parsed=JSON.parse(raw);}catch{throw Error('invalid_private_reply');}
 return parsed;
}
async function setEnabled(value){
 const out=await api('/api/hud/workforce/control',
  {method:'POST',write:true,body:{enabled:value}});
 if(out.enabled!==value)throw Error('stop_control_readback_mismatch');
}

// Owner confirmation comes from an explicit protected workflow_dispatch, not
// a source flag or an AI-generated "approval". The candidate stays unapproved
// in git. Only this one in-memory copy is approved for a single exact job.
export async function planOwnerSelectedPilot(tasks,routing,commit,taskId,revision){
 if(!Array.isArray(tasks?.tasks))throw Error('canonical_queue_invalid');
 const candidate=tasks.tasks.find(t=>t.id===taskId);
 if(!candidate||candidate.cloud_inference?.revision!==revision||
    candidate.cloud_inference?.approved_for_cloud!==false||
    candidate.cloud_inference?.data_class!=='public_repository')
  throw Error('new_unapproved_canonical_candidate_required');
 const selected={...candidate,cloud_inference:{
  ...candidate.cloud_inference,approved_for_cloud:true
 }};
 const canonical={...tasks,tasks:tasks.tasks.map(t=>t===candidate?selected:t)};
 const [job]=await planApprovedJobs(canonical,routing,commit,[{task_id:taskId,revision}]);
 if(!job||job.prompt.length>4000||job.id.startsWith('gc-rec-'))
  throw Error('new_canonical_packet_incompatible_with_pinned_gemini');
 return job;
}

export async function checkOperatorContext(e){
 if(e.GITHUB_REPOSITORY!=='TeamRovor/rovor-video-engine'||
    e.GITHUB_REF!=='refs/heads/main'||
    e.GITHUB_EVENT_NAME!=='workflow_dispatch')
  throw Error('owner_workflow_requires_trusted_main_dispatch');
 if(!validToken(e.ROVOR_HUD_READER_TOKEN)||!validToken(e.ROVOR_HUD_WRITER_TOKEN)||
   e.ROVOR_HUD_READER_TOKEN===e.ROVOR_HUD_WRITER_TOKEN)
  throw Error('independent_production_credential_missing');
 return true;
}
async function main(){
 await checkOperatorContext(process.env);
 if(!['status','pilot_once','enable_schedule','stop'].includes(operation))
  throw Error('unknown_owner_operation');
 if(operation==='status'){
  const data=await api('/api/hud/workforce/status');
  if(data.source!=='existing_cloudflare_hud_gemini_workforce')throw Error('wrong_private_ledger');
  reporter(JSON.stringify({enabled:data.enabled,job_count:data.items.length,
   review_pending:data.items.filter(x=>x.state==='needs_review'&&x.human_review==='not_recorded').length,
   successful_owner_reviews:data.items.filter(x=>x.human_review==='passed').length}));
  return;
 }
 if(operation==='stop'){
  await setEnabled(false);
  reporter('STOP saved to original Cloudflare D1; no new approved job will be claimed.');
  return;
 }
 const before=await api('/api/hud/workforce/status');
 if(before.source!=='existing_cloudflare_hud_gemini_workforce')throw Error('wrong_private_ledger');
 if(operation==='enable_schedule'){
  if(!confirm)throw Error('explicit_owner_approval_required');
  if(!before.items.some(x=>x.human_review==='passed'&&x.actual_model===MODEL))
   throw Error('first_reviewed_pilot_pass_required');
  if(before.items.some(x=>x.state==='uncertain'||x.state==='running'))
   throw Error('unresolved_provider_attempt_requires_review');
  await setEnabled(true);
  reporter('Cloudflare native 5-minute cron enabled. Existing STOP and model admission remain in force.');
  return;
 }
 // Initial pilot: one newly approved revision; all previously attempted v1
 // canonical tasks are excluded. No new prompt originates from workflow inputs.
 if(!confirm||!/^[a-z0-9][a-z0-9-]{0,149}$/.test(taskId)||
    !/^v(?:[2-9]|[1-9][0-9]+)$/.test(revision)||!/^[a-f0-9]{40}$/.test(sha||''))
  throw Error('new_owner_approved_v2_canonical_task_required');
 if(before.enabled!==false)throw Error('pause_existing_scheduled_work_before_pilot');
 if(before.items.some(x=>['queued','running','uncertain'].includes(x.state)))
  throw Error('resolve_existing_cloud_queue_before_pilot');
 const catalog=await api('/api/hud/gemini/models');
 if(catalog.source!=='google_gemini_cloud_direct'||
    !catalog.model_evidence?.some(x=>x.model===MODEL&&x.verification==='verified_recent_reply'))
  throw Error('no_recent_pinned_gemini_model_receipt');
 const tasks=JSON.parse(readFileSync('coordination/tasks.json','utf8'));
 const routing=JSON.parse(readFileSync('coordination/work-routing.json','utf8'));
 const job=await planOwnerSelectedPilot(tasks,routing,sha,taskId,revision);
 const receipt=await api('/api/hud/workforce/intake',{method:'POST',write:true,
  body:{approval:'trusted_canonical_owner_approval_v1',job,revision}});
 if(receipt.id!==job.id||receipt.queued!==true||receipt.duplicate===true)
  throw Error('job_not_new_or_duplicate_replay_denied');
 let run;
 try{
  await setEnabled(true);
  run=await api('/api/hud/workforce/tick',{method:'POST',write:true});
 }finally{
  // Always force STOP even if enabling or inference reports an ambiguous error.
  await setEnabled(false);
 }
 if(run.id!==job.id||run.dispatched!==1||run.state!=='needs_review')
  throw Error('pilot_no_reviewable_model_receipt_'+String(run.state||'unknown').slice(0,40));
 const after=await api('/api/hud/workforce/status');
 const saved=after.items.find(x=>x.id===job.id);
 if(after.enabled!==false||saved?.state!=='needs_review'||saved.human_review!=='not_recorded'||
    saved.actual_model!==MODEL||!/^[a-f0-9]{64}$/.test(saved.output_sha256||''))
  throw Error('private_review_readback_mismatch');
 reporter('PASS: one new owner-approved canonical task returned a pinned Gemini draft with exact private D1 receipt. STOP restored; owner PASS/FAIL pending in Ask ROVOR.');
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))
 main().catch(error=>{const message=String(error?.message||'owner_operation_failed');
  // Error messages are fixed codes; do not print untrusted provider bodies.
  const safe=/^[a-z0-9_]{3,90}$/.test(message)?message:'owner_operation_failed';
  console.error('ROVOR protected Gemini workforce: '+safe);process.exitCode=1;});
