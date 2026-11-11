#!/usr/bin/env node
// Only used inside the existing authenticated ROVOR HUD GitHub production job.
// Secrets are sent on stdout exclusively to the Wrangler secret-bulk pipe.
// The owner-authorized Gemini activation runs once on a specially marked,
// trusted-main merge. No key is read on pull_request or another provider's job.
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {githubAppCredentialIssue} from './github-app.mjs';

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
  // Bridge credential is server-to-server, never exposed to the HUD browser.
  // An absent credential leaves existing Site state and Worker secrets alone.
  if(env.ROVOR_GHOST_SERVICE_TOKEN){
    const key=env.ROVOR_GHOST_SERVICE_TOKEN;
    if(typeof key!=='string'||!/^[!-~]{32,1024}$/.test(key)||
       key===env.ROVOR_HUD_READER_TOKEN||key===env.ROVOR_HUD_WRITER_TOKEN)
      throw Error('invalid_private_secret_configuration');
    payload.GHOST_SITE_SERVICE_TOKEN=key;
  }
  if(env.ROVOR_HUD_OWNER_TOKEN){
    const owner=env.ROVOR_HUD_OWNER_TOKEN;
    if(typeof owner!=='string'||!/^[!-~]{32,200}$/.test(owner)||owner===env.ROVOR_HUD_READER_TOKEN||owner===env.ROVOR_HUD_WRITER_TOKEN)
      throw Error('invalid_private_secret_configuration');
    payload.HUD_OWNER_TOKEN=owner;
  }
  // Optional independent GitHub App credentials. Do not overwrite existing
  // Worker secrets with missing values or partially configured credentials.
  const app=['ROVOR_GITHUB_APP_ID','ROVOR_GITHUB_INSTALLATION_ID','ROVOR_GITHUB_APP_PRIVATE_KEY'];
  if(app.some(k=>env[k])){
    if(githubAppCredentialIssue(env))throw Error('invalid_private_secret_configuration');
    for(const k of app)payload[k]=env[k].trim();
  }
  if(['true','false'].includes(env.ROVOR_NATIVE_DISCOVERY_ENABLED))
    payload.ROVOR_NATIVE_DISCOVERY_ENABLED=env.ROVOR_NATIVE_DISCOVERY_ENABLED;
  if(['true','false'].includes(env.ROVOR_GITHUB_PATCH_ENABLED))payload.ROVOR_GITHUB_PATCH_ENABLED=env.ROVOR_GITHUB_PATCH_ENABLED;
  if(['true','false'].includes(env.ROVOR_GITHUB_PATCH_OWNER_REQUESTED))
    payload.ROVOR_GITHUB_PATCH_OWNER_REQUESTED=env.ROVOR_GITHUB_PATCH_OWNER_REQUESTED;
  // Persist the exact protected runner scope-check timestamp, including zero
  // when permission was denied, so no old proof can survive a failed rollout.
  if(env.ROVOR_GITHUB_PATCH_SCOPE_VERIFIED_AT!==undefined){
    const proof=env.ROVOR_GITHUB_PATCH_SCOPE_VERIFIED_AT;
    if(typeof proof!=='string'||!/^(0|[1-9][0-9]{12})$/.test(proof)||
      (env.ROVOR_GITHUB_PATCH_ENABLED==='true'&&proof==='0')||
      (env.ROVOR_GITHUB_PATCH_ENABLED!=='true'&&proof!=='0'))
      throw Error('invalid_private_secret_configuration');
    payload.ROVOR_GITHUB_PATCH_SCOPE_VERIFIED_AT=proof;
  }
  if(typeof env.ROVOR_GITHUB_PATCH_PATHS==='string'&&env.ROVOR_GITHUB_PATCH_PATHS.length<=3000&&env.ROVOR_GITHUB_PATCH_PATHS)
    payload.ROVOR_GITHUB_PATCH_PATHS=env.ROVOR_GITHUB_PATCH_PATHS;
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
