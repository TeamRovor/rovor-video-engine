#!/usr/bin/env node
// After each trusted main HUD deploy, read the EXISTING private Google Gemini
// catalog and model-specific D1 usage. No model request, key export, Mac,
// provider fallback, paid tier, or automatic retries.
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {appendFileSync} from 'node:fs';
const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';
const ALLOWED_REASONS=new Set([
  'free_project_or_key_unconfigured','owner_model_allowlist_invalid',
  'google_catalog_http_auth_denied','google_catalog_http_unavailable',
  'google_catalog_unavailable','google_catalog_redirect_denied',
  'no_approved_free_text_models_listed','catalog_listed_unverified_for_inference'
]);

export async function readLiveGemini({token,send=fetch}={}){
  if(typeof token!=='string'||token.length<32||/[\r\n]/.test(token))
    throw Error('private_reader_secret_missing');
  async function read(resource,authorized){
    const response=await send(ORIGIN+resource,{
      method:'GET',redirect:'manual',cache:'no-store',
      headers:authorized?{Authorization:'Bearer '+token,Accept:'application/json'}:{Accept:'application/json'},
      signal:AbortSignal.timeout(16000)
    });
    if(!authorized)return {status:response.status};
    if(response.status!==200)throw Error('gemini_private_endpoint_unavailable_'+response.status);
    const raw=await response.text();
    if(raw.length>50000)throw Error('gemini_private_response_too_large');
    try{return JSON.parse(raw)}catch{throw Error('gemini_private_response_invalid')}
  }
  const anon=await read('/api/hud/gemini/models',false);
  if(anon.status!==401)throw Error('gemini_catalog_not_private');
  const models=await read('/api/hud/gemini/models',true);
  if(models?.source!=='google_gemini_cloud_direct'||models.provider!=='google'||
     models.mac_required!==false||typeof models.online!=='boolean'||
     !Array.isArray(models.models)||!Array.isArray(models.directly_listed_models)||
     typeof models.discovery_reason!=='string'||!ALLOWED_REASONS.has(models.discovery_reason))
    throw Error('gemini_catalog_contract_invalid');
  if(models.online&&(models.models[0]!=='gemini-auto-free'||models.models.length<2||
      models.models.length!==models.directly_listed_models.length+1||
      models.models.slice(1).some((m,i)=>m!==models.directly_listed_models[i])))
    throw Error('gemini_catalog_contract_invalid');
  if(!models.online&&models.models.length!==0)
    throw Error('gemini_catalog_contract_invalid');
  const report={
    source:'existing_cloudflare_hud',mac_required:false,
    private_auth_verified:true,
    model_catalog_state:models.online?'key_listed_free_text_models':'not_ready',
    eligible_text_model_count:models.directly_listed_models.length,
    discovery_reason:models.discovery_reason,
    inference_proven:false,
    completed_today:null
  };
  if(models.online){
    const usage=await read('/api/hud/gemini/usage',true);
    if(usage?.source!=='cloud_gemini_direct'||!Array.isArray(usage.models)||
       !Number.isSafeInteger(usage.completed)||usage.completed<0)
      throw Error('gemini_model_usage_unavailable');
    report.completed_today=usage.completed;
    // Historical completed counts do not attest that today's deployed code
    // has successfully called Google; a separate one-shot canary does that.
  }
  return report;
}
function safeText(report){
  const lines=[
    '### Live Google Gemini — existing Cloudflare HUD',
    '',
    '| Check | Actual readback |',
    '|---|---|',
    '| Mac required | No |',
    '| Private Gemini API authorization | Verified (anonymous denied) |',
    '| Google key-model listing | '+(report.model_catalog_state==='key_listed_free_text_models'?'Available':'Not ready')+' |',
    '| Key-listed, owner-allowlisted Free-priced text models | '+report.eligible_text_model_count+' |',
    '| Readback condition | '+report.discovery_reason+' |',
    '| Completed cloud responses today in D1 | '+(report.completed_today===null?'Unknown':report.completed_today)+' |',
    '| New live inference proven by this check | No — read-only |',
    '',
    'Configured key and listed model are **not** proof of current project free billing, quota remaining or a successful model response.',
    'No model call was made in this readback.'
  ];
  return lines.join('\n')+'\n';
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  readLiveGemini({token:process.env.ROVOR_HUD_READER_TOKEN}).then(report=>{
    const summary=safeText(report);
    if(process.env.GITHUB_STEP_SUMMARY)appendFileSync(process.env.GITHUB_STEP_SUMMARY,summary);
    console.log(JSON.stringify(report));
    if(report.model_catalog_state!=='key_listed_free_text_models')
      console.warn('::warning title=Google Gemini not ready::The existing HUD cannot list a free-priced Google text model with its current Worker credentials. See the job summary; no inference ran.');
  }).catch(error=>{
    const allow=/^(private_reader_secret_missing|gemini_catalog_not_private|gemini_catalog_contract_invalid|gemini_model_usage_unavailable|gemini_private_response_(too_large|invalid)|gemini_private_endpoint_unavailable_[0-9]{3})$/;
    console.error('Google Gemini authenticated live readback FAILED: '+
      (allow.test(String(error?.message))?error.message:'private_readback_unavailable'));
    process.exitCode=1;
  });
}
