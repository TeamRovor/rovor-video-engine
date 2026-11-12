#!/usr/bin/env node
// Private, reader-authenticated, read-only production release proof.
// No provider calls, inference, STOP, keys, prompts, D1 mutations or approvals.
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {CATALOG_PROVIDERS} from './cloud-provider-catalog-bridge.mjs';
const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';
const URL=ORIGIN+'/api/hud/provider-catalogs';
const statuses=new Set([
 'never_checked','bridge_unconfigured','site_auth_denied','upstream_unavailable',
 'invalid_contract','site_receipt_missing','site_readback_mismatch','catalog_received'
]);
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
export async function verifyCatalogBridge(token,send=fetch,{attempts=5,pause=delay}={}){
 if(typeof token!=='string'||token.length<32||/[\r\n]/.test(token))throw Error('reader_secret_missing');
 if(!Number.isInteger(attempts)||attempts<1||attempts>8)throw Error('invalid_attempt_count');
 const get=auth=>send(URL,{method:'GET',redirect:'manual',
  headers:auth?{Authorization:'Bearer '+token}:{},
  cache:'no-store',signal:AbortSignal.timeout(12000)});
 for(let attempt=0;attempt<attempts;attempt++){
  let anonymous,live;
  try{
   anonymous=await get(false);
   if(anonymous.status!==401)throw Error('catalog_bridge_anonymous_access_not_denied');
   live=await get(true);
  }catch(error){
   if(error?.message==='catalog_bridge_anonymous_access_not_denied')throw error;
   if(attempt===attempts-1)throw Error('catalog_bridge_readback_unavailable');
   await pause(2000);continue;
  }
  if(live.status!==200){
   if(attempt===attempts-1)throw Error('catalog_bridge_readback_unavailable');
   await pause(2000);continue;
  }
  let data;
  try{
   const raw=await live.text();
   if(raw.length>25000)throw Error();
   data=JSON.parse(raw);
  }catch{throw Error('catalog_bridge_readback_invalid');}
  if(data?.source!=='cloudflare_site_catalog_bridge'||data.mac_required!==false||
    data.provider_count!==9||data.inference_online_verified_count!==0||
    !Array.isArray(data.providers)||data.providers.length!==9||
    !Number.isInteger(data.site_d1_verified_count)||
    data.site_d1_verified_count<0||data.site_d1_verified_count>9||
    !Number.isInteger(data.direct_catalog_received_count)||
    data.direct_catalog_received_count<0||data.direct_catalog_received_count>9)
   throw Error('catalog_bridge_readback_invalid');
  for(let i=0;i<9;i++){
   const row=data.providers[i];
   if(row?.provider!==CATALOG_PROVIDERS[i]||!statuses.has(row.status)||
      !['fresh','stale_or_unavailable'].includes(row.freshness)||
      typeof row.site_d1_verified!=='boolean'||
      !['original_site','direct_provider'].includes(row.catalog_source)||
      (row.catalog_source==='direct_provider'&&row.site_d1_verified!==false)||
      (row.direct_setup_blocker!==null&&
       !['no_provider_key','missing_account'].includes(row.direct_setup_blocker))||
      (row.catalog_source==='direct_provider'&&row.direct_setup_blocker!==null)||
      (row.direct_error_category!==null&&
       !['transport_unavailable','provider_auth_denied','provider_rate_limited',
        'provider_http_unavailable','invalid_catalog_body','invalid_catalog_shape',
        'no_provider_key','missing_account','unknown_provider'].includes(row.direct_error_category))||
      row.free_billing_verified!==false||row.quota_verified!==false||
      row.canary_verified!==false||row.inference_online_verified!==false||
      !Array.isArray(row.models)||row.models.length>20||
      row.models.some(m=>typeof m!=='string'||m.length>200)||
      row.model_count!==row.models.length)
    throw Error('catalog_bridge_readback_invalid');
  }
  const verified=data.providers.filter(p=>p.site_d1_verified&&p.freshness==='fresh').length;
  if(verified!==data.site_d1_verified_count)throw Error('catalog_bridge_readback_invalid');
  const direct=data.providers.filter(p=>p.catalog_source==='direct_provider'&&
   p.freshness==='fresh'&&p.status==='catalog_received').length;
  if(direct!==data.direct_catalog_received_count)
   throw Error('catalog_bridge_readback_invalid');
  // Only public-safe states. Never print keys, model IDs or private outputs.
  return {private_auth_verified:true,provider_slots:9,
   checked_provider_slots:data.providers.filter(p=>p.checked_at!==null).length,
   fresh_provider_slots:data.providers.filter(p=>p.freshness==='fresh').length,
   catalog_check_states:Object.fromEntries(data.providers.map(p=>[p.provider,p.status])),
   recent_site_d1_catalog_receipts:verified,
   direct_provider_catalog_receipts:direct,
   catalog_sources:Object.fromEntries(data.providers.map(p=>[p.provider,p.catalog_source])),
   direct_error_categories:Object.fromEntries(data.providers.map(p=>[p.provider,p.direct_error_category])),
   direct_setup_blockers:Object.fromEntries(data.providers.map(p=>[p.provider,p.direct_setup_blocker])),
   verified_online_inference_providers:0,
   catalog_only:true,mac_required:false};
 }
 throw Error('catalog_bridge_readback_unavailable');
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const report=await verifyCatalogBridge(process.env.ROVOR_HUD_READER_TOKEN);
  console.log(JSON.stringify(report));
 }catch(error){
  const allowed=['reader_secret_missing','invalid_attempt_count',
   'catalog_bridge_anonymous_access_not_denied',
   'catalog_bridge_readback_unavailable','catalog_bridge_readback_invalid'];
  console.error('ROVOR cloud catalog verification: '+
   (allowed.includes(error.message)?error.message:'catalog_bridge_readback_unavailable'));
  process.exitCode=1;
 }
}
