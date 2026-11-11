#!/usr/bin/env node
// Read-only production proof for the EXISTING owner-private Cloudflare D1.
// No model calls, task submissions, STOP changes or review decisions.
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';

export async function verifyWorkforce({token,send=fetch}={}){
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
 const exact=data.items.filter(x=>x.provider==='google-gemini-cloud'&&
    Number.isSafeInteger(x.tokens_input)&&x.tokens_input>=0&&
    Number.isSafeInteger(x.tokens_output)&&x.tokens_output>=0).length;
 return {source:'existing_cloudflare_hud',private_auth_verified:true,
  writer_only_tick_verified:true,model:data.configured_model,
  enabled:data.enabled,recorded_jobs:data.items.length,
  pending_reviews:data.items.filter(x=>x.state==='needs_review'&&x.human_review==='not_recorded').length,
  passed_reviews:data.items.filter(x=>x.human_review==='passed').length,
  recurring_authorized:data.recurring_execution_authorized===true,
  native_tick_observed:tick!==null,last_native_tick_at:tick?new Date(tick.scheduled_at).toISOString():null,
  last_native_tick_state:tick?.result_state??null,last_native_inference_completed:tick?.inference_completed===1,
  exact_job_token_receipts:exact,
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
    '. This read makes no model request and does not sync the private ChatGPT Site.\n'));
  }
 }).catch(e=>{const reason=String(e?.message||'workforce_readback_unavailable');
  console.error('ROVOR cloud workforce readback FAILED: '+
   (/^[a-z0-9_]{3,120}$/.test(reason)?reason:'workforce_readback_unavailable'));
  process.exitCode=1;});
}
