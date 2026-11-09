#!/usr/bin/env node
// One strictly bounded, non-replayed direct Google Gemini canary against the
// EXISTING private Cloudflare HUD. Uses key-listed, owner-attested Free-tier
// text models; does not depend on Mac, trust catalog-only results, or change
// other providers, tasks, approvals or scheduling.
const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';
const PREFERENCE=['gemini-3.5-flash-lite','gemini-3.1-flash-lite',
  'gemini-3.8-flash','gemini-2.5-flash-lite','gemini-3.5-flash','gemini-2.5-flash'];

async function read(path,token) {
  return fetch(ORIGIN+path,{method:'GET',redirect:'manual',cache:'no-store',
    headers:token?{Authorization:'Bearer '+token}:{},
    signal:AbortSignal.timeout(16000)});
}
async function main(){
  const token=process.env.ROVOR_HUD_READER_TOKEN;
  if(typeof token!=='string'||token.length<32)throw Error('reader_credential_missing');
  const anonymous=await read('/api/hud/gemini/models',null);
  if(anonymous.status!==401)throw Error('gemini_catalog_not_private');
  const result=await read('/api/hud/gemini/models',token);
  if(!result.ok)throw Error('gemini_cloud_catalog_unavailable');
  const catalog=await result.json();
  if(catalog.source!=='google_gemini_cloud_direct'||catalog.online!==true||
     catalog.mac_required!==false||!Array.isArray(catalog.models)||catalog.models.length<2||
     !catalog.models.includes('gemini-auto-free'))
    throw Error('gemini_cloud_not_armed_or_live_catalog_unavailable');
  const selected=process.env.ROVOR_GEMINI_TEST_MODEL;
  const model=selected ? (PREFERENCE.includes(selected)&&catalog.models.includes(selected)?selected:null) :
    PREFERENCE.find(id=>catalog.models.includes(id));
  if(!model)throw Error('no_approved_key_listed_free_text_model_for_canary');
  const before=await read('/api/hud/gemini/usage',token);
  if(!before.ok)throw Error('private_gemini_usage_unavailable');
  const prior=await before.json();
  const completedBefore=prior.models?.find(m=>m.model===model)?.completed||0;
  if(!Array.isArray(prior.models)||prior.source!=='cloud_gemini_direct')
    throw Error('per_model_usage_schema_not_ready');
  console.log('Verified private HUD lists '+(catalog.models.length-1)+
    ' approved project-listed text models. One model selected for canary.');
  const r=await fetch(ORIGIN+'/api/hud/gemini/chat',{
    method:'POST',redirect:'manual',
    headers:{Authorization:'Bearer '+token,'Content-Type':'application/json',Origin:ORIGIN},
    body:JSON.stringify({model,messages:[{role:'user',
      content:'Respond in one short sentence confirming this is a Gemini connection test.'}]}),
    signal:AbortSignal.timeout(40000)
  });
  if(!r.ok){
    let reason='unknown';
    try{reason=(await r.json()).error||reason;}catch{}
    throw Error('gemini_canary_failed_'+r.status+'_'+String(reason).replace(/[^a-z0-9_-]/gi,'_').slice(0,55));
  }
  if(r.headers.get('X-ROVOR-Provider')!=='google-gemini-cloud'||
     r.headers.get('X-ROVOR-Requested-Model')!==model||
     r.headers.get('X-ROVOR-Resolved-Model')!==model)
    throw Error('wrong_gemini_route_receipt');
  const output=await r.text();
  if(!output.includes('data: [DONE]')||!/"content":"[^"]{1,}/.test(output))
    throw Error('gemini_no_completed_response');
  const after=await read('/api/hud/gemini/usage',token);
  if(!after.ok)throw Error('private_model_usage_readback_failed');
  const usage=await after.json();
  if(usage.source!=='cloud_gemini_direct'||usage.mac_required!==false||
     usage.completed<=prior.completed||
     !Array.isArray(usage.models)||
     !usage.models.some(m=>m.model===model&&m.completed>completedBefore))
    throw Error('per_model_receipt_not_advanced');
  console.log('PASS: one real Google Gemini reply through '+model+
    '; project-wide and per-model private D1 counters advanced. No Mac.');
  console.log('No proof of remaining external quota or billing tier beyond owner attestation.');
}
main().catch(error=>{
  console.error('Google Gemini cloud reply NOT VERIFIED: '+
    String(error?.message||'verification_error').replace(/[^a-z0-9_-]/gi,'_').slice(0,125));
  process.exitCode=1;
});
