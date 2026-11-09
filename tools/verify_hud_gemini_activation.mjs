#!/usr/bin/env node
// GitHub-hosted verification of the EXISTING private Cloudflare HUD.
// One fixed, tiny, owner-dispatched Gemini canary; never re-submits or falls
// back to another provider and never logs keys, prompts or raw model output.
import {setTimeout as delay} from 'node:timers/promises';

const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';
const DIRECT=/^(?:gemini|google|google-ai-studio)[/:]gemini-(?:3\.1-flash-lite|2\.5-flash-lite)$/i;

export async function verifyGemini({reader,route,canary=true,send=fetch,pause=delay,log=console.log}){
  if(typeof reader!=='string'||reader.length<32||/[\r\n]/.test(reader))
    throw Error('private_reader_secret_not_configured');
  if(typeof route!=='string'||!DIRECT.test(route))throw Error('unverified_direct_gemini_route');
  async function request(resource,{body,method='GET'}={}){
    const result=await send(ORIGIN+resource,{
      method,redirect:'error',cache:'no-store',
      headers:{Authorization:'Bearer '+reader,Accept:'application/json',
        ...(body?{'Content-Type':'application/json',Origin:ORIGIN}:{})},
      ...(body?{body:JSON.stringify(body)}:{}),
      signal:AbortSignal.timeout(12000)
    });
    if(!result.ok)throw Error('private_hud_endpoint_unavailable_'+result.status);
    return result.json();
  }
  let catalog=null;
  for(let tries=0;tries<10;tries++){
    catalog=await request('/api/hud/chat/models');
    if(catalog.source==='omniroute_outbound_bridge'&&catalog.online===true
      &&Array.isArray(catalog.models)&&catalog.models.includes(route))break;
    if(tries<9)await pause(2000);
  }
  if(catalog?.online!==true||!catalog.models?.includes(route))
    throw Error('gemini_not_advertised_by_live_omniroute_relay');
  log('PASS: private HUD advertises an online exact Google Gemini route: '+route);
  if(!canary)return {route,available:true,inference_verified:false};
  const submitted=await request('/api/hud/chat/submit',{
    method:'POST',
    body:{model:route,messages:[{role:'user',content:'Reply with one short sentence confirming this Gemini connection test.'}]}
  });
  if(submitted.status!==undefined&&submitted.status!==202)throw Error('gemini_canary_not_queued');
  if(!/^[a-f0-9-]{36}$/i.test(submitted.job_id||''))throw Error('gemini_canary_missing_job_id');
  log('One bounded Gemini canary queued; no retries or second model request.');
  for(let tries=0;tries<45;tries++){
    await pause(2000);
    const status=await request('/api/hud/chat/status/'+encodeURIComponent(submitted.job_id));
    if(status.state==='failed')throw Error('gemini_canary_failed_'+String(status.error||'unknown').replace(/[^a-z0-9_-]/gi,'_').slice(0,70));
    if(status.state==='complete'){
      if(status.requested_model!==route||typeof status.output!=='string'||!status.output.trim())
        throw Error('gemini_canary_incomplete_or_route_mismatch');
      log('PASS: one real Ask ROVOR completion returned through the exact Gemini route.');
      log('Requested route verified; ultimate upstream fallback/model identity not independently attested.');
      return {route,available:true,inference_verified:true};
    }
  }
  throw Error('gemini_canary_timed_out_no_replay');
}

if(process.argv[1]&&import.meta.url===new URL('file://'+process.argv[1]).href){
  verifyGemini({
    reader:process.env.ROVOR_HUD_READER_TOKEN,
    route:process.env.ROVOR_GEMINI_ROUTE,
    canary:process.env.ROVOR_GEMINI_CANARY!=='false'
  }).catch(err=>{
    const message=String(err?.message||'verification_failed').replace(/[^a-z0-9_-]/gi,'_').slice(0,100);
    console.error('ROVOR GEMINI VERIFICATION FAILED: '+message);
    process.exitCode=1;
  });
}
