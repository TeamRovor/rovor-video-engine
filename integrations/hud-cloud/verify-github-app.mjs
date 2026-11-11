#!/usr/bin/env node
// Deployment diagnostics only. Never output secrets, installation tokens,
// upstream response bodies, repository contents or private task data.
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {githubAppConfigured,githubAppCredentialIssue,mintGithubReadToken,readGithubDiscovery} from './github-app.mjs';
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
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const mode=process.argv[2];
 const task=mode==='--credentials'?verifyGithubCredentials(process.env):
  mode==='--worker'?verifyGithubWorker(process.env):Promise.reject(Error('invalid_verification_mode'));
 task.then(r=>console.log(JSON.stringify(r))).catch(e=>{
  const code=String(e?.message||'github_app_verification_unavailable');
  console.error('ROVOR independent GitHub verification: '+(/^[a-z0-9_]{3,90}$/.test(code)?code:'github_app_verification_unavailable'));
  process.exitCode=1;
 });
}
