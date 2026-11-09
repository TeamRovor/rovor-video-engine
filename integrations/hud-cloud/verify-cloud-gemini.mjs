#!/usr/bin/env node
// Verify the live EXISTING Cloudflare HUD without any Mac runner or OmniRoute.
// Exactly one benign Google Gemini request; no fallbacks or retries.
const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';
const MODEL='gemini-3.1-flash-lite';
async function read(path,token){
  const r=await fetch(ORIGIN+path,{method:'GET',redirect:'manual',cache:'no-store',
    headers:token?{Authorization:'Bearer '+token}:{},
    signal:AbortSignal.timeout(12000)});
  return r;
}
async function main(){
  const token=process.env.ROVOR_HUD_READER_TOKEN;
  if(typeof token!=='string'||token.length<32)throw Error('reader_credential_missing');
  const anonymous=await read('/api/hud/gemini/models',null);
  if(anonymous.status!==401)throw Error('gemini_catalog_not_private');
  const catalog=await read('/api/hud/gemini/models',token);
  if(!catalog.ok)throw Error('gemini_cloud_catalog_unavailable');
  const models=await catalog.json();
  if(models.source!=='google_gemini_cloud_direct'||models.online!==true||
    models.mac_required!==false||models.models.length!==1||models.models[0]!==MODEL)
    throw Error('cloud_gemini_not_configured');
  const before=await read('/api/hud/gemini/usage',token);
  if(!before.ok)throw Error('private_gemini_usage_unavailable');
  const prior=await before.json();
  console.log('Verified existing private HUD: Google Gemini cloud route, no Mac required.');
  const r=await fetch(ORIGIN+'/api/hud/gemini/chat',{
    method:'POST',redirect:'manual',
    headers:{Authorization:'Bearer '+token,'Content-Type':'application/json',Origin:ORIGIN},
    body:JSON.stringify({model:MODEL,messages:[{role:'user',content:'Respond in one short sentence to confirm that Google Gemini cloud chat works.'}]}),
    signal:AbortSignal.timeout(40000)});
  if(!r.ok){
    let detail='unknown';
    try{detail=(await r.json()).error||detail;}catch{}
    throw Error('cloud_gemini_canary_failed_'+r.status+'_'+String(detail).replace(/[^a-z0-9_-]/gi,'_').slice(0,60));
  }
  if(r.headers.get('X-ROVOR-Provider')!=='google-gemini-cloud'||
     r.headers.get('X-ROVOR-Requested-Model')!==MODEL)
    throw Error('wrong_cloud_provider_receipt');
  const payload=await r.text();
  if(!payload.includes('data: [DONE]')||!/"content":"[^"]{1,}/.test(payload))
    throw Error('no_completed_gemini_response');
  const after=await read('/api/hud/gemini/usage',token);
  if(!after.ok)throw Error('gemini_receipt_readback_failed');
  const usage=await after.json();
  if(usage.source!=='cloud_gemini_direct'||usage.model!==MODEL||
     usage.mac_required!==false||usage.completed<=prior.completed)
    throw Error('gemini_completed_receipt_not_persisted');
  console.log('PASS: Google Gemini answered in existing Ask ROVOR cloud API; D1 completed receipt advanced. No Mac.');
  console.log('Reported free-tier project is owner-attested, not a real-time billing/quota proof.');
}
main().catch(e=>{
  console.error('Gemini cloud activation NOT VERIFIED: '+String(e?.message||'unknown').slice(0,180));
  process.exitCode=1;
});
