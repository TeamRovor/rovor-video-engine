#!/usr/bin/env node
// No inference or quota attestation. Tests only whether the existing private
// GitHub environment key can read the pinned Groq model catalogue. Never
// print provider credentials, raw bodies, tokens, headers or network errors.
const ENDPOINT='https://api.groq.com/openai/v1/models';
const MODEL='openai/gpt-oss-20b';

export async function checkGroqCatalogueKey(key,fetcher=fetch){
  if(typeof key!=='string'||key.length<16)return {connection:'no_key_configured',http_status:null,model_listed:null};
  let response;
  try {
    response=await fetcher(ENDPOINT,{method:'GET',redirect:'error',
      headers:{Authorization:'Bearer '+key,Accept:'application/json'},
      signal:AbortSignal.timeout(7000)});
  } catch(error){
    return {connection:error?.name==='TimeoutError'?'timeout':'network_error',
      http_status:null,model_listed:null};
  }
  const status=response.status;
  if(!response.ok){
    try{await response.body?.cancel();}catch{}
    return {connection:status===401||status===403?'auth_rejected':status===429?'rate_limited':'http_error',
      http_status:status,model_listed:null};
  }
  try {
    const raw=await response.text();
    if(raw.length>192000)return {connection:'catalog_invalid',http_status:status,model_listed:null};
    const data=JSON.parse(raw);
    if(!Array.isArray(data?.data)||data.data.length>300||
      !data.data.every(row=>row&&typeof row.id==='string'&&row.id.length<=200))
      return {connection:'catalog_invalid',http_status:status,model_listed:null};
    return {connection:'catalog_received',http_status:status,model_listed:data.data.some(row=>row.id===MODEL)};
  } catch {
    return {connection:'catalog_invalid',http_status:status,model_listed:null};
  }
}

if(process.argv[1]&&import.meta.url===new URL('file://'+process.argv[1]).href){
  checkGroqCatalogueKey(process.env.GROQ_HUD_API_KEY).then(result=>{
    console.log('Groq read-only GitHub runner diagnostic: '+JSON.stringify(result));
    console.log('This does not prove Free-tier billing or a successful inference request.');
  }).catch(()=>{console.log('Groq read-only GitHub runner diagnostic: unavailable');});
}
