#!/usr/bin/env node
// Read-only production proof for the EXISTING owner-private Cloudflare D1.
// No model calls, task submissions, STOP changes or review decisions.
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';

export async function verifyWorkforce({token,send=fetch,now=Date.now()}={}){
 if(typeof token!=='string'||token.length<32||/[\r\n]/.test(token))
  throw Error('private_reader_secret_missing');
 async function request(resource,authenticated,method='GET'){
  const response=await send(ORIGIN+resource,{method,redirect:'manual',cache:'no-store',
   headers:authenticated?{Authorization:'Bearer '+token}:{},
   signal:AbortSignal.timeout(12000)});
  return response;
 }
 const anon=await request('/api/hud/workforce/status',false);
 if(anon.status!==401)throw Error('anonymous_workforce_exposed');
 const anonTick=await request('/api/hud/workforce/tick',false,'POST');
 if(anonTick.status!==401)throw Error('anonymous_workforce_tick_not_denied');
 const readerTick=await request('/api/hud/workforce/tick',true,'POST');
 if(readerTick.status!==401)throw Error('reader_workforce_tick_not_denied');
 const reply=await request('/api/hud/workforce/status',true);
 if(reply.status!==200)throw Error('workforce_private_D1_unavailable_'+reply.status);
 const raw=await reply.text();
 if(raw.length>60000)throw Error('workforce_status_too_large');
 let data;try{data=JSON.parse(raw);}catch{throw Error('workforce_status_invalid');}
 if(data?.source!=='existing_cloudflare_hud_gemini_workforce'||
    data.mac_required!==false||typeof data.enabled!=='boolean'||
    data.configured_model!=='gemini-3.5-flash-lite'||
    data.site_review_ledger_synced!==false||!Array.isArray(data.items)||data.items.length>50||
    data.items.some(x=>typeof x.id!=='string'||typeof x.state!=='string'||
      !['not_recorded','passed','failed'].includes(x.human_review)||
      Object.hasOwn(x,'prompt')||Object.hasOwn(x,'output')))
  throw Error('workforce_private_D1_contract_invalid');
 const schedule=data.native_schedule;
 if(schedule?.source!=='cloudflare_scheduled_event'||!Array.isArray(schedule.recent_ticks)||
    schedule.recent_ticks.length>12)throw Error('native_schedule_readback_invalid');
 const tick=schedule.last_tick;
 if(tick!==null&&(!Number.isSafeInteger(tick?.scheduled_at)||tick.scheduled_at<=0||
    typeof tick.result_state!=='string'||!/^[a-z0-9_]{1,80}$/.test(tick.result_state)||
    ![0,1].includes(tick.inference_completed)||![0,1].includes(tick.dispatch_reported)))
  throw Error('native_schedule_receipt_invalid');
 const exactItems=data.items.filter(x=>x.provider==='google-gemini-cloud'&&
    x.requested_model===data.configured_model&&x.actual_model===data.configured_model&&
    typeof x.output_sha256==='string'&&/^[a-f0-9]{64}$/.test(x.output_sha256)&&
    Number.isSafeInteger(x.tokens_input)&&x.tokens_input>=0&&
    Number.isSafeInteger(x.tokens_output)&&x.tokens_output>=0);
 // Correlate scheduled receipts to the exact persisted job rather than counting
 // manual pilots or a scheduler's uncorroborated dispatch flag as autonomy.
 const nativeMatches=schedule.recent_ticks.filter(t=>t?.inference_completed===1&&
    t.dispatch_reported===1&&t.result_state==='needs_review'&&t.http_status===200&&
    Number.isSafeInteger(t.scheduled_at)&&t.scheduled_at>0&&
    Number.isSafeInteger(t.started_at)&&Number.isSafeInteger(t.finished_at)&&
    exactItems.some(j=>j.id===t.job_id&&j.state==='needs_review'&&
      Number.isSafeInteger(j.started_at)&&Number.isSafeInteger(j.finished_at)&&
      t.started_at<=j.started_at&&j.started_at<=j.finished_at&&j.finished_at<=t.finished_at));
 // The latest 50 visible jobs are NOT a complete rolling-day ledger. Trust only
 // the server-computed admission snapshot after validating its exact contract.
 // Never infer capacity, reset time, or recurring readiness from recent rows.
 const admission=data.admission;
 const nonnegative=n=>Number.isSafeInteger(n)&&n>=0;
 const counters=['queued_jobs','running_or_uncertain','pending_reviews','rolling_day_attempts',
  'rolling_day_limit','pending_review_limit','fresh_unattempted_discoveries'];
 if(!admission||admission.source!=='read_only_private_D1'||
    admission.provider_admission_verified_by_this_read!==false||
    typeof data.recurring_execution_authorized!=='boolean'||
    !Number.isSafeInteger(admission.observed_at)||admission.observed_at>now+120000||
    now-admission.observed_at>300000||
    counters.some(k=>!nonnegative(admission[k]))||
    admission.rolling_day_limit<1||admission.pending_review_limit<1||
    !Array.isArray(admission.observed_constraints)||
    admission.observed_constraints.some(x=>typeof x!=='string')||
    new Set(admission.observed_constraints).size!==admission.observed_constraints.length)
  throw Error('workforce_admission_readback_invalid');
 const reasons=[
  !data.enabled?'stop_closed':null,
  !data.recurring_execution_authorized?'standing_authorization_inactive':null,
  admission.running_or_uncertain>0?'running_or_uncertain_claim':null,
  admission.rolling_day_attempts>=admission.rolling_day_limit?'rolling_day_attempt_limit':null,
  admission.pending_reviews>=admission.pending_review_limit?'pending_review_limit':null,
  admission.queued_jobs===0?'no_queued_job':null,
  admission.fresh_unattempted_discoveries===0?'no_fresh_unattempted_discovery':null
 ].filter(Boolean);
 if(admission.observed_constraints.length!==reasons.length||
    reasons.some(x=>!admission.observed_constraints.includes(x)))
  throw Error('workforce_admission_readback_inconsistent');
 const slot=admission.earliest_rolling_slot_at;
 if(reasons.includes('rolling_day_attempt_limit')?
    !Number.isSafeInteger(slot)||slot<=admission.observed_at||
     slot>admission.observed_at+86400000:
    slot!==null)
  throw Error('workforce_admission_readback_inconsistent');
 const exact=exactItems.length;
 return {source:'existing_cloudflare_hud',private_auth_verified:true,
  writer_only_tick_verified:true,model:data.configured_model,
  enabled:data.enabled,recorded_jobs:data.items.length,
  pending_reviews:admission.pending_reviews,
  passed_reviews:data.items.filter(x=>x.human_review==='passed').length,
  recurring_authorized:data.recurring_execution_authorized===true,
  native_tick_observed:tick!==null,last_native_tick_at:tick?new Date(tick.scheduled_at).toISOString():null,
  last_native_tick_state:tick?.result_state??null,last_native_inference_completed:tick?.inference_completed===1,
  exact_job_token_receipts:exact,
  native_inference_receipts_matched:new Set(nativeMatches.map(t=>t.job_id)).size,
  admission_snapshot:{source:admission.source,observed_at:new Date(admission.observed_at).toISOString(),
    items_truncated:data.items.length===50,queued_jobs_observed:admission.queued_jobs,
    running_or_uncertain_observed:admission.running_or_uncertain,
    pending_reviews_observed:admission.pending_reviews,
    rolling_day_attempts_observed:admission.rolling_day_attempts,
    rolling_day_attempt_limit:admission.rolling_day_limit,
    pending_review_limit:admission.pending_review_limit,
    fresh_unattempted_discoveries_observed:admission.fresh_unattempted_discoveries,
    oldest_observed_attempt_expires_at:slot===null?null:new Date(slot).toISOString(),
    observed_constraints:admission.observed_constraints},
  inference_proven_by_this_read:false,site_review_ledger_synced:false};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 verifyWorkforce({token:process.env.ROVOR_HUD_READER_TOKEN}).then(r=>{
  console.log(JSON.stringify(r));
  if(process.env.GITHUB_STEP_SUMMARY){
   import('node:fs').then(({appendFileSync})=>appendFileSync(process.env.GITHUB_STEP_SUMMARY,
    '### ROVOR approved Gemini cloud workforce — authenticated D1 readback\n'+
    'Private model: '+r.model+'; STOP gate '+(r.enabled?'enabled':'disabled')+
    '; recorded job receipts '+r.recorded_jobs+'; owner-review pending '+r.pending_reviews+
    '; native clock '+(r.native_tick_observed?r.last_native_tick_at+' / '+r.last_native_tick_state:'not yet observed')+
    '; exact job token receipts '+r.exact_job_token_receipts+
    '; matching native inference receipts '+r.native_inference_receipts_matched+
    '; admission snapshot '+JSON.stringify(r.admission_snapshot)+
    '. This read makes no model request and does not sync the private ChatGPT Site.\n'));
  }
 }).catch(e=>{const reason=String(e?.message||'workforce_readback_unavailable');
  console.error('ROVOR cloud workforce readback FAILED: '+
   (/^[a-z0-9_]{3,120}$/.test(reason)?reason:'workforce_readback_unavailable'));
  process.exitCode=1;});
}
