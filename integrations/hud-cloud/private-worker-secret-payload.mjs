#!/usr/bin/env node
// Only used inside the existing authenticated ROVOR HUD GitHub production job.
// Secrets are sent on stdout exclusively to the Wrangler secret-bulk pipe.
// The owner-authorized Gemini activation runs once on a specially marked,
// trusted-main merge. No key is read on pull_request or another provider's job.
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const validSecret=s=>typeof s==='string'&&s.length>=24&&s.length<=512&&!/[\s\x00-\x1f\x7f]/.test(s);
export function validateOneTimeGeminiActivation(env) {
  if(env.GEMINI_ACTIVATE_ONCE!=='true')return false;
  if(!validSecret(env.ROVOR_GEMINI_CLOUD_API_KEY))throw Error('owner_gemini_github_secret_missing_or_invalid');
  if(env.GITHUB_REPOSITORY!=='TeamRovor/rovor-video-engine' ||
     env.GITHUB_REF!=='refs/heads/main' ||
     env.GITHUB_EVENT_NAME!=='push')throw Error('gemini_activation_requires_trusted_main_push');
  return true;
}
export function buildHudSecretPayload(env) {
  // Existing private read/write credentials remain mandatory in prepare-github-deploy.mjs.
  const payload={
    HUD_WRITER_TOKEN:env.ROVOR_HUD_WRITER_TOKEN,
    HUD_READER_TOKEN:env.ROVOR_HUD_READER_TOKEN
  };
  for(const key of ['GROQ_HUD_API_KEY','GROQ_HUD_CHAT_ENABLED','GROQ_HUD_FREE_TIER_VERIFIED',
    'GROQ_HUD_EVIDENCE_SHA256','GROQ_HUD_VERIFIED_AT','GROQ_HUD_VALID_UNTIL','GROQ_HUD_DAILY_BUDGET']) {
    if(env[key])payload[key]=env[key];
  }
  if(validateOneTimeGeminiActivation(env)){
    // Owner expressly said this is their free Gemini project and authorized
    // exactly one benign cloud canary. This is not an independent billing attestation.
    payload.GEMINI_API_KEY=env.ROVOR_GEMINI_CLOUD_API_KEY;
    payload.ROVOR_GEMINI_FREE_TIER_VERIFIED='confirmed';
  }
  return payload;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  try{
    if(process.argv[2]==='--preflight'){
      validateOneTimeGeminiActivation(process.env);
      console.log('Owner-requested cloud Gemini activation gate checked; key value not shown.');
    }else if(process.argv.length===2){
      process.stdout.write(JSON.stringify(buildHudSecretPayload(process.env)));
    }else throw Error('unexpected_secret_payload_operation');
  }catch(error){
    const allow=new Set(['owner_gemini_github_secret_missing_or_invalid',
      'gemini_activation_requires_trusted_main_push','unexpected_secret_payload_operation']);
    console.error('ROVOR HUD secret installation refused: '+
      (allow.has(error.message)?error.message:'invalid_private_secret_configuration'));
    process.exitCode=1;
  }
}
