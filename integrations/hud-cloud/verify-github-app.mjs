#!/usr/bin/env node
// Deployment diagnostics only. Never output secrets, installation tokens,
// upstream response bodies, repository contents or private task data.
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {appendFileSync} from 'node:fs';
import {setTimeout as delay} from 'node:timers/promises';
import {githubAppConfigured,githubAppCredentialIssue,mintGithubReadToken,mintGithubPatchToken,readGithubDiscovery} from './github-app.mjs';
import {githubPatchConfiguration} from './github-patch-gateway.mjs';
const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';
const names=['ROVOR_GITHUB_APP_ID','ROVOR_GITHUB_INSTALLATION_ID','ROVOR_GITHUB_APP_PRIVATE_KEY'];
export async function verifyGithubCredentials(env,send=fetch,now=Date.now()){
 const supplied=names.filter(k=>!!env[k]).length;
 const requested=env.ROVOR_NATIVE_DISCOVERY_ENABLED==='true';
 if(!supplied&&!requested)return {configured:false,read_verified:false,reason:'not_configured'};
 const issue=githubAppCredentialIssue(env);
 if(issue)throw Error(issue);
 let token;
 try{token=await mintGithubReadToken(env,now,send);}catch(e){
  const code=String(e?.message||'');
  if(['github_installation_token_denied','github_installation_token_scope_invalid','github_app_key_invalid'].includes(code))throw Error(code);
  throw Error('github_app_authentication_unconfirmed');
 }
 try{await readGithubDiscovery(token,send);}catch{throw Error('github_app_repository_read_unconfirmed');}
 return {configured:true,read_verified:true,read_only:true,repository:'TeamRovor/rovor-video-engine',native_discovery_requested:requested};
}
// Read-only permission preflight for the optional native draft-PR executor.
// Minting an installation token is NOT a repository write; it verifies the
// precise one-repository Contents + Pull requests write scope without ever
// returning the token, sending source to a model, or modifying a branch.
export async function verifyGithubPatchPermissions(env,send=fetch,now=Date.now()){
 const cfg=githubPatchConfiguration(env);
 if(!cfg.requested)return {patch_requested:false,write_scope_verified:false,reason:'patch_disabled'};
 if(!cfg.credentials_configured)throw Error('github_patch_app_credentials_missing');
 if(!cfg.allowed_path_count)throw Error('github_patch_allowed_paths_missing_or_invalid');
 try{await mintGithubPatchToken(env,now,send);}catch(e){
  throw Error(e?.message==='github_installation_token_scope_invalid'
   ?'github_patch_write_scope_invalid':'github_patch_write_scope_unconfirmed');
 }
 return {patch_requested:true,write_scope_verified:true,
  repo:'TeamRovor/rovor-video-engine',scoped_permissions:'contents_write_pull_requests_write',
  allowed_path_count:cfg.allowed_path_count,repository_written:false};
}
// Optional write scope is independently verified for every deployment.
 // If permissions are unavailable, deploy the read-only HUD and force the
 // actual Worker PATCH_ENABLED=false. This never grants or assumes write
 // permission; the owner request remains distinguishable in private status.
export async function resolveOptionalPatchDeployment(env,send=fetch,now=Date.now()){
 const requested=env.ROVOR_GITHUB_PATCH_ENABLED==='true';
 if(!requested)return {requested:false,effective_enabled:false,write_scope_verified:false,
  reason:'owner_disabled',repository_written:false};
 try{
  await verifyGithubPatchPermissions(env,send,now);
  return {requested:true,effective_enabled:true,write_scope_verified:true,
   reason:'scoped_token_verified',repository_written:false};
 }catch{
  return {requested:true,effective_enabled:false,write_scope_verified:false,
   reason:'write_scope_unavailable',repository_written:false};
 }
}
// Informational, credential-safe capability check: a short-lived downscoped
// installation token is minted and discarded without GitHub repository writes.
// Missing write permissions are reported, never taken as approval or enabled.
export async function inspectGithubPatchCapability(env,send=fetch,now=Date.now()){
 if(!githubAppConfigured(env))return {write_scope_available:false,reason:'app_not_configured',repository_written:false};
 try{await mintGithubPatchToken(env,now,send);}catch{
  return {write_scope_available:false,reason:'write_scope_unavailable',repository_written:false};
 }
 return {write_scope_available:true,reason:'scoped_token_verified',
  permissions:'contents_write_pull_requests_write',repository:'TeamRovor/rovor-video-engine',
  repository_written:false,patch_executor_enabled:env.ROVOR_GITHUB_PATCH_ENABLED==='true'};
}
export async function verifyGithubWorker(env,send=fetch,now=Date.now()){
 const token=env.ROVOR_HUD_READER_TOKEN;
 if(typeof token!=='string'||token.length<32||/[\r\n]/.test(token))throw Error('private_reader_secret_missing');
 const endpoint=ORIGIN+'/api/hud/workforce/native-discovery';
 const get=auth=>send(endpoint,{method:'GET',redirect:'manual',cache:'no-store',signal:AbortSignal.timeout(12000),
  headers:auth?{Authorization:'Bearer '+token}:{}});
 const anon=await get(false);
 if(anon.status!==401)throw Error('native_discovery_not_private');
 const reply=await get(true);
 if(reply.status!==200)throw Error('native_discovery_readback_unavailable');
 const raw=await reply.text();
 if(raw.length>8000)throw Error('native_discovery_readback_invalid');
 let data;try{data=JSON.parse(raw);}catch{throw Error('native_discovery_readback_invalid');}
 if(data.source!=='rovor_native_github_discovery'||typeof data.configured!=='boolean'||
    typeof data.enabled!=='boolean'||data.mac_required!==false||data.chatgpt_required!==false||
    data.github_actions_required!==false||data.storage_unavailable)throw Error('native_discovery_readback_invalid');
 if(githubAppConfigured(env)&&!data.configured)throw Error('github_app_worker_credentials_missing');
 if(env.ROVOR_NATIVE_DISCOVERY_ENABLED==='true'&&!data.enabled)throw Error('github_native_discovery_not_enabled');
 if(env.ROVOR_NATIVE_DISCOVERY_ENABLED==='false'&&data.enabled)throw Error('github_native_discovery_not_disabled');
 const last=data.last_check;
 if(last!==null&&(!Number.isSafeInteger(last?.started_at)||last.started_at<1||
  typeof last.result_state!=='string'||!/^[a-z0-9_]{1,80}$/.test(last.result_state)||
  (last.finished_at!==null&&(!Number.isSafeInteger(last.finished_at)||last.finished_at<last.started_at))))
  throw Error('native_discovery_receipt_invalid');
 const verified=!!last&&['owner_review_draft_queued','no_new_evidence_backed_work','daily_draft_budget_reached'].includes(last.result_state)&&
  Number.isSafeInteger(last.finished_at)&&last.finished_at<=now&&now-last.finished_at<7200000;
 return {private_auth_verified:true,configured:data.configured,enabled:data.enabled,
  standing_ready:typeof data.standing_ready==='boolean'?data.standing_ready:null,
  native_github_read_verified:verified,last_native_check_at:last?new Date(last.started_at).toISOString():null,
  last_native_result:last?.result_state??null,mac_required:false,chatgpt_required:false,github_actions_required:false};
}
// Live readback only. A deployed endpoint without a completed hourly checkpoint
// must never be presented as proof that an employee caught up on GitHub.
export async function verifyDeployedRepoCatchup(env,send=fetch){
 const token=env?.ROVOR_HUD_READER_TOKEN;
 if(typeof token!=='string'||token.length<32||/[\r\n]/.test(token))throw Error('private_reader_secret_missing');
 const url=ORIGIN+'/api/hud/workforce/repo-catchup';
 const get=authenticated=>send(url,{method:'GET',redirect:'manual',cache:'no-store',
  signal:AbortSignal.timeout(12000),headers:authenticated?{Authorization:'Bearer '+token}:{}});
 if((await get(false)).status!==401)throw Error('repo_catchup_anonymous_exposure');
 const r=await get(true);
 if(r.status!==200)throw Error('repo_catchup_private_status_unavailable');
 const raw=await r.text();
 if(raw.length>8000)throw Error('repo_catchup_status_invalid');
 let doc;try{doc=JSON.parse(raw);}catch{throw Error('repo_catchup_status_invalid');}
 if(doc?.source!=='rovor_private_repo_catchup'||
  !['not_checked','ready','read_unavailable'].includes(doc.state)||
  doc.private_reader_required!==true||doc.model_called!==false||doc.repository_written!==false||
  doc.mac_required!==false||doc.chatgpt_required!==false)throw Error('repo_catchup_status_invalid');
 const s=doc.snapshot,validSha=x=>typeof x==='string'&&/^[a-f0-9]{40}$/.test(x);
 if(s!==null){
  if(!s||!validSha(s.head_sha)||!Array.isArray(s.recent_commit_shas)||
   s.recent_commit_shas.length<1||s.recent_commit_shas.length>4||
   s.recent_commit_shas.some(x=>!validSha(x))||s.recent_commit_shas[0]!==s.head_sha||
   !Array.isArray(s.changed_paths)||s.changed_paths.length>24||
   s.changed_paths.some(x=>typeof x!=='string'||x.length>200||x.length<1)||
   !['failed_run_ids','recent_success_run_ids','open_issue_numbers','open_pr_numbers'].every(k=>
    Array.isArray(s[k])&&s[k].length<=8&&s[k].every(n=>Number.isSafeInteger(n)&&n>0))||
   typeof s.changed_paths_truncated!=='boolean')throw Error('repo_catchup_status_invalid');
 }
 if(doc.state==='ready'&&!s)throw Error('repo_catchup_status_invalid');
 return {private_auth_verified:true,state:doc.state,checkpoint_present:!!s,
  head_sha:s?.head_sha??null,recent_commit_count:s?.recent_commit_shas.length??0,
  changed_path_count:s?.changed_paths.length??0,model_called:false,repository_written:false};
}

// Read-only check of the deployed private owner's approval gate. The GitHub
// App write scope does not grant a human owner session. No owner credential,
// cookie, verdict, model request, or repository mutation occurs here.
export async function verifyDeployedOwnerSession(env,send=fetch){
 const token=env?.ROVOR_HUD_READER_TOKEN;
 if(typeof token!=='string'||token.length<32||/[\r\n]/.test(token))throw Error('private_reader_secret_missing');
 const url=ORIGIN+'/api/hud/owner/session';
 const get=auth=>send(url,{method:'GET',redirect:'manual',cache:'no-store',
  signal:AbortSignal.timeout(12000),headers:auth?{Authorization:'Bearer '+token}:{}});
 const anon=await get(false);
 if(anon.status!==401)throw Error('owner_session_anonymous_exposure');
 const live=await get(true);
 if(live.status!==200)throw Error('owner_session_status_unavailable');
 const raw=await live.text();
 if(raw.length>1000)throw Error('owner_session_status_invalid');
 let data;try{data=JSON.parse(raw);}catch{throw Error('owner_session_status_invalid');}
 if(typeof data?.configured!=='boolean'||data.owner_authenticated!==false||
    Object.keys(data).sort().join(',')!=='configured,owner_authenticated')
  throw Error('owner_session_status_invalid');
 return {private_auth_verified:true,owner_session_configured:data.configured,
  owner_approval_authorized_by_this_read:false,repository_written:false};
}
// Verify the *deployed* private Worker after secret-bulk, not merely the
// permission returned to GitHub's runner. No model requests or repository writes.
// The exact single-repository App scope is checked separately by --patch-effective.
export async function verifyGithubPatchWorker(env,send=fetch,{attempts=5,pause=delay,intervalMs=2000}={}){
 const token=env?.ROVOR_HUD_READER_TOKEN;
 if(typeof token!=='string'||token.length<32||/[\r\n]/.test(token))throw Error('private_reader_secret_missing');
 if(!Number.isInteger(attempts)||attempts<1||attempts>8)throw Error('invalid_patch_readback_attempts');
 const expectedEnabled=env.ROVOR_GITHUB_PATCH_ENABLED==='true';
 const expectedProof=env.ROVOR_GITHUB_PATCH_SCOPE_VERIFIED_AT;
 const enforceProof=expectedProof!==undefined;
 if(enforceProof&&(!/^(0|[1-9][0-9]{12})$/.test(expectedProof)||
    (expectedEnabled&&expectedProof==='0')||(!expectedEnabled&&expectedProof!=='0')))
  throw Error('expected_patch_scope_attestation_invalid');
 let expectedPaths=[];
 if(expectedEnabled){
  try{expectedPaths=JSON.parse(env.ROVOR_GITHUB_PATCH_PATHS||'[]');}catch{}
  if(!Array.isArray(expectedPaths)||!expectedPaths.length||expectedPaths.length>12||
     expectedPaths.some(x=>typeof x!=='string')||new Set(expectedPaths).size!==expectedPaths.length)
    throw Error('expected_patch_allowlist_invalid');
 }
 const url=ORIGIN+'/api/hud/workforce/github-patch';
 const get=authorized=>send(url,{method:'GET',redirect:'manual',cache:'no-store',
  signal:AbortSignal.timeout(12000),headers:authorized?{Authorization:'Bearer '+token}:{}});
 for(let attempt=0;attempt<attempts;attempt++){
  const anonymous=await get(false);
  if(anonymous.status!==401)throw Error('github_patch_anonymous_access_not_denied');
  const live=await get(true);
  if(live.status!==200){
   if(attempt===attempts-1)throw Error('github_patch_worker_readback_unavailable');
   await pause(intervalMs);continue;
  }
  const raw=await live.text();
  if(raw.length>60000)throw Error('github_patch_worker_readback_invalid');
  let data;try{data=JSON.parse(raw);}catch{throw Error('github_patch_worker_readback_invalid');}
  if(data?.source!=='rovor_independent_github_patch'||typeof data.configured!=='boolean'||
     data.merges_allowed!==false||data.mac_required!==false||data.chatgpt_required!==false||
     !Array.isArray(data.allowed_paths)||data.allowed_paths.length>12||
     !Array.isArray(data.items)||data.items.length>30||data.storage_unavailable)
    throw Error('github_patch_worker_readback_invalid');
  const proofMatches=!enforceProof||(expectedEnabled?
   data.readiness==='write_scope_verified_at_deployment'&&
   data.write_scope_verified_at===Number(expectedProof):
   data.write_scope_verified_at===null);
  if(data.configured===expectedEnabled&&proofMatches&&
     JSON.stringify(data.allowed_paths)===JSON.stringify(expectedPaths))
   return {private_auth_verified:true,configured:data.configured,
    deployment_write_scope_readback_verified:enforceProof&&expectedEnabled,
    allowed_path_count:data.allowed_paths.length,allowlist_matches_deployment:true,
    permitted_action:'owner_approved_draft_pr_only',merges_allowed:false,
    repository_written_by_verifier:false};
  if(attempt===attempts-1)throw Error('github_patch_worker_config_mismatch');
  await pause(intervalMs);
 }
 throw Error('github_patch_worker_readback_unavailable');
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const mode=process.argv[2];
 const task=mode==='--credentials'?verifyGithubCredentials(process.env):
  mode==='--worker'?verifyGithubWorker(process.env):
  mode==='--patch'?verifyGithubPatchPermissions(process.env):
  mode==='--patch-worker'?verifyGithubPatchWorker(process.env):
  mode==='--owner-session'?verifyDeployedOwnerSession(process.env):
  mode==='--repo-catchup'?verifyDeployedRepoCatchup(process.env):
  mode==='--patch-capability'?inspectGithubPatchCapability(process.env):
  mode==='--patch-effective'?(async()=>{
   const effective=await resolveOptionalPatchDeployment(process.env);
   const destination=process.env.GITHUB_ENV;
   if(typeof destination!=='string'||!path.isAbsolute(destination)||/[\r\n]/.test(destination))
    throw Error('github_actions_environment_missing');
   appendFileSync(destination,'ROVOR_GITHUB_PATCH_ENABLED='+String(effective.effective_enabled)+'\n'+
    'ROVOR_GITHUB_PATCH_OWNER_REQUESTED='+String(effective.requested)+'\n'+
    // Evidence that this deployment obtained a single-repository write token.
    // This is NOT evidence of a successful draft PR or indefinite permissions.
    'ROVOR_GITHUB_PATCH_SCOPE_VERIFIED_AT='+(effective.effective_enabled?Date.now():0)+'\n');
   return effective;
  })():Promise.reject(Error('invalid_verification_mode'));
 task.then(r=>console.log(JSON.stringify(r))).catch(e=>{
  const code=String(e?.message||'github_app_verification_unavailable');
  console.error('ROVOR independent GitHub verification: '+(/^[a-z0-9_]{3,90}$/.test(code)?code:'github_app_verification_unavailable'));
  process.exitCode=1;
 });
}
