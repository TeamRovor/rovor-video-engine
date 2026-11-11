import {test} from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync} from 'node:crypto';
import {githubAppCredentialIssue} from '../integrations/hud-cloud/github-app.mjs';
import {verifyGithubCredentials,verifyGithubWorker,verifyGithubPatchPermissions,inspectGithubPatchCapability,resolveOptionalPatchDeployment,verifyGithubPatchWorker} from '../integrations/hud-cloud/verify-github-app.mjs';
import {buildHudSecretPayload} from '../integrations/hud-cloud/private-worker-secret-payload.mjs';
const NOW=Date.now(),pem=generateKeyPairSync('rsa',{modulusLength:2048}).privateKey.export({type:'pkcs1',format:'pem'});
const env={ROVOR_GITHUB_APP_ID:'123',ROVOR_GITHUB_INSTALLATION_ID:'456',ROVOR_GITHUB_APP_PRIVATE_KEY:pem,
 ROVOR_NATIVE_DISCOVERY_ENABLED:'true',ROVOR_HUD_READER_TOKEN:'r'.repeat(40)};
test('credentials verification only mints scoped token and reads fixed repo, never exposes response content',async()=>{
 let calls=[];
 const r=await verifyGithubCredentials(env,async(url,init)=>{
  calls.push({url,method:init.method});assert.equal(init.redirect,'manual');
  if(url.endsWith('/access_tokens')){
   assert.deepEqual(JSON.parse(init.body),{repositories:['rovor-video-engine'],permissions:{contents:'read',issues:'read',pull_requests:'read',actions:'read'}});
   return Response.json({token:'mock-installation-token-not-for-output',expires_at:new Date(NOW+3600000).toISOString(),
    permissions:{contents:'read',issues:'read',pull_requests:'read',actions:'read',metadata:'read'}},{status:201});
  }
  assert.equal(init.method,'GET');assert(url.startsWith('https://api.github.com/repos/TeamRovor/rovor-video-engine/'));
  return Response.json(url.includes('/actions/runs')?{workflow_runs:[]}:[{body:'never output private contents'}]);
 },NOW);
 assert.equal(r.read_verified,true);assert.equal(calls.length,5);assert(!JSON.stringify(r).includes('token'));
 assert(!JSON.stringify(r).includes('private contents'));
});
test('missing, incomplete and denied credentials fail closed with no raw error',async()=>{
 const no=async()=>{throw Error('no request');};
 assert.equal((await verifyGithubCredentials({},no,NOW)).configured,false);
 await assert.rejects(()=>verifyGithubCredentials({ROVOR_NATIVE_DISCOVERY_ENABLED:'true'},no,NOW),/github_app_id_missing/);
 await assert.rejects(()=>verifyGithubCredentials(env,async()=>new Response('private upstream content',{status:401}),NOW),/github_installation_token_denied/);
});
test('private Worker configuration is distinct from native read receipt',async()=>{
 const base={source:'rovor_native_github_discovery',configured:true,enabled:true,last_check:null,
  mac_required:false,chatgpt_required:false,github_actions_required:false};
 const mock=data=>async(url,init)=>{
  assert(url.endsWith('/api/hud/workforce/native-discovery'));
  assert.equal(init.method,'GET');
  return init.headers.Authorization?Response.json(data):new Response(null,{status:401});
 };
 const a=await verifyGithubWorker(env,mock(base),NOW);assert.equal(a.native_github_read_verified,false);
 const b=await verifyGithubWorker(env,mock({...base,last_check:{started_at:NOW-2000,finished_at:NOW-1000,result_state:'no_new_evidence_backed_work'}}),NOW);
 assert.equal(b.native_github_read_verified,true);
 const capped=await verifyGithubWorker(env,mock({...base,standing_ready:true,last_check:{started_at:NOW-2000,finished_at:NOW-1000,result_state:'daily_draft_budget_reached'}}),NOW);
 assert.equal(capped.native_github_read_verified,true);assert.equal(capped.standing_ready,true);
 const blocked=await verifyGithubWorker(env,mock({...base,standing_ready:false}),NOW);
 assert.equal(blocked.native_github_read_verified,false);assert.equal(blocked.standing_ready,false);
 await assert.rejects(()=>verifyGithubWorker(env,mock({...base,enabled:false}),NOW),/not_enabled/);
});

test('each bad credential has a precise nonsecret diagnostic; harmless surrounding whitespace is normalized',()=>{
 assert.equal(githubAppCredentialIssue({...env,ROVOR_GITHUB_APP_ID:'Iv1.example'}),'github_app_id_must_be_numeric_not_client_id');
 assert.equal(githubAppCredentialIssue({...env,ROVOR_GITHUB_INSTALLATION_ID:'https://github.com/settings/installations/456'}),'github_installation_id_must_be_numeric');
 assert.equal(githubAppCredentialIssue({...env,ROVOR_GITHUB_APP_PRIVATE_KEY:'SHA256:mock-fingerprint'}),'github_private_key_is_fingerprint_not_pem');
 assert.equal(githubAppCredentialIssue({...env,ROVOR_GITHUB_APP_PRIVATE_KEY:'partial key'}),'github_private_key_requires_complete_pem');
 assert.equal(githubAppCredentialIssue({...env,ROVOR_GITHUB_APP_ID:' 123\n',ROVOR_GITHUB_INSTALLATION_ID:'456\n',ROVOR_GITHUB_APP_PRIVATE_KEY:'\n'+pem+'\n'}),null);
});

test('patch write admission verifies the exact downscoped repo token and makes no GitHub repository write',async()=>{
 const patch={...env,ROVOR_GITHUB_PATCH_ENABLED:'true',
  ROVOR_GITHUB_PATCH_PATHS:JSON.stringify(['architecture/roadmap.md'])};
 const calls=[];
 const proof=await verifyGithubPatchPermissions(patch,async(url,init)=>{
  calls.push({url,method:init.method});
  assert.equal(url,'https://api.github.com/app/installations/456/access_tokens');
  assert.equal(init.method,'POST');assert.equal(init.redirect,'manual');
  assert.deepEqual(JSON.parse(init.body),{repositories:['rovor-video-engine'],
   permissions:{contents:'write',pull_requests:'write'}});
  return Response.json({token:'mock-patch-token-at-least-twenty-chars',
   expires_at:new Date(NOW+3600000).toISOString(),
   permissions:{contents:'write',pull_requests:'write',metadata:'read'},
   repositories:[{full_name:'TeamRovor/rovor-video-engine'}]},{status:201});
 },NOW);
 assert.equal(proof.write_scope_verified,true);assert.equal(proof.repository_written,false);
 assert.equal(proof.allowed_path_count,1);assert.equal(calls.length,1);
 assert(!JSON.stringify(proof).includes('mock-patch-token'));
});
test('patch verifier distinguishes disabled, absent allowlist, rejected and under-scoped permissions',async()=>{
 const no=async()=>{throw Error('token endpoint must not be called');};
 assert.equal((await verifyGithubPatchPermissions(env,no,NOW)).reason,'patch_disabled');
 const enabled={...env,ROVOR_GITHUB_PATCH_ENABLED:'true'};
 await assert.rejects(()=>verifyGithubPatchPermissions(enabled,no,NOW),/github_patch_allowed_paths_missing_or_invalid/);
 const allowed={...enabled,ROVOR_GITHUB_PATCH_PATHS:'["architecture/roadmap.md"]'};
 await assert.rejects(()=>verifyGithubPatchPermissions(allowed,async()=>new Response('do not log upstream content',{status:403}),NOW),/github_patch_write_scope_unconfirmed/);
 await assert.rejects(()=>verifyGithubPatchPermissions(allowed,async()=>Response.json({
  token:'mock-patch-token-at-least-twenty-chars',expires_at:new Date(NOW+3600000).toISOString(),
  permissions:{contents:'read',pull_requests:'write',metadata:'read'}},{status:201}),NOW),/github_patch_write_scope_invalid/);
 await assert.rejects(()=>verifyGithubPatchPermissions({...enabled,ROVOR_GITHUB_APP_ID:''},no,NOW),/github_patch_app_credentials_missing/);
});

test('informational GitHub patch capability probe proves write-token scope but cannot enable executor or edit repository',async()=>{
 const calls=[];
 const result=await inspectGithubPatchCapability(env,async(url,init)=>{
  calls.push({url,method:init.method});
  assert.equal(url,'https://api.github.com/app/installations/456/access_tokens');
  assert.equal(init.method,'POST');assert.equal(init.redirect,'manual');
  assert.deepEqual(JSON.parse(init.body),{repositories:['rovor-video-engine'],
   permissions:{contents:'write',pull_requests:'write'}});
  return Response.json({token:'mock-temporary-token-long-enough',
   expires_at:new Date(NOW+3600000).toISOString(),
   permissions:{contents:'write',pull_requests:'write',metadata:'read'},
   repositories:[{full_name:'TeamRovor/rovor-video-engine'}]},{status:201});
 },NOW);
 assert.equal(result.write_scope_available,true);assert.equal(result.patch_executor_enabled,false);
 assert.equal(result.repository_written,false);assert.equal(calls.length,1);
 assert(!JSON.stringify(result).includes('mock-temporary-token'));
});
test('informational GitHub patch capability probe fails closed without secrets or fatal deployment failure',async()=>{
 const no=async()=>{throw Error('must not be called');};
 assert.deepEqual(await inspectGithubPatchCapability({},no,NOW),
  {write_scope_available:false,reason:'app_not_configured',repository_written:false});
 const denied=await inspectGithubPatchCapability(env,async()=>new Response('private upstream error', {status:403}),NOW);
 assert.deepEqual(denied,{write_scope_available:false,reason:'write_scope_unavailable',repository_written:false});
 assert(!JSON.stringify(denied).includes('private upstream'));
});

test('optional release mode fails closed on denied write token without blocking read-only work',async()=>{
 const requested={...env,ROVOR_GITHUB_PATCH_ENABLED:'true',
  ROVOR_GITHUB_PATCH_PATHS:'["architecture/roadmap.md"]'};
 const denied=await resolveOptionalPatchDeployment(requested,
  async()=>new Response('upstream private error',{status:403}),NOW);
 assert.deepEqual(denied,{requested:true,effective_enabled:false,write_scope_verified:false,
  reason:'write_scope_unavailable',repository_written:false});
 assert(!JSON.stringify(denied).includes('upstream private'));
 const effective={...requested,ROVOR_GITHUB_PATCH_ENABLED:String(denied.effective_enabled),
  ROVOR_GITHUB_PATCH_OWNER_REQUESTED:String(denied.requested),
  ROVOR_HUD_WRITER_TOKEN:'w'.repeat(40)};
 const payload=buildHudSecretPayload(effective);
 assert.equal(payload.ROVOR_GITHUB_PATCH_ENABLED,'false');
 assert.equal(payload.ROVOR_GITHUB_PATCH_OWNER_REQUESTED,'true');
 assert.equal((await resolveOptionalPatchDeployment(env,async()=>{throw Error('unexpected token call')},NOW)).reason,'owner_disabled');
});
test('optional release mode enables writes only after exact downscoped token proof',async()=>{
 const requested={...env,ROVOR_GITHUB_PATCH_ENABLED:'true',
  ROVOR_GITHUB_PATCH_PATHS:'["architecture/roadmap.md"]'};
 let requests=0;
 const result=await resolveOptionalPatchDeployment(requested,async(url,options)=>{
  requests++;assert.equal(options.method,'POST');
  assert.deepEqual(JSON.parse(options.body).permissions,{contents:'write',pull_requests:'write'});
  return Response.json({token:'safe-mock-temp-token-very-long-1234567890',
   expires_at:new Date(NOW+3600000).toISOString(),
   permissions:{contents:'write',pull_requests:'write',metadata:'read'},
   repositories:[{full_name:'TeamRovor/rovor-video-engine'}]},{status:201});
 },NOW);
 assert.equal(result.effective_enabled,true);
 assert.equal(result.write_scope_verified,true);
 assert.equal(result.repository_written,false);
 assert.equal(requests,1);
});


test('deployed patch executor is private, enabled and exactly confined to approved paths',async()=>{
 const config={...env,ROVOR_GITHUB_PATCH_ENABLED:'true',
  ROVOR_GITHUB_PATCH_PATHS:'["architecture/ROVOR-AUTONOMOUS-DISCOVERY.md"]'};
 const seen=[];
 const read=async(url,opts)=>{
  assert.equal(url,'https://rovor-hud-telemetry.rovordigital.workers.dev/api/hud/workforce/github-patch');
  assert.equal(opts.method,'GET');assert.equal(opts.redirect,'manual');
  seen.push(opts.headers.Authorization?'reader':'anonymous');
  return opts.headers.Authorization?Response.json({source:'rovor_independent_github_patch',
   configured:true,readiness:'configuration_complete_write_scope_unverified',
   allowed_paths:['architecture/ROVOR-AUTONOMOUS-DISCOVERY.md'],items:[],
   mac_required:false,chatgpt_required:false,merges_allowed:false}):new Response(null,{status:401});
 };
 const proof=await verifyGithubPatchWorker(config,read,{attempts:2,pause:async()=>{}});
 assert.deepEqual(seen,['anonymous','reader']);
 assert.equal(proof.configured,true);assert.equal(proof.allowlist_matches_deployment,true);
 assert.equal(proof.repository_written_by_verifier,false);
 assert.equal(proof.merges_allowed,false);
 assert(!JSON.stringify(proof).includes(config.ROVOR_HUD_READER_TOKEN));
});

test('deployed patch checker rejects public exposure and unauthorized scope expansion',async()=>{
 const config={...env,ROVOR_GITHUB_PATCH_ENABLED:'true',ROVOR_GITHUB_PATCH_PATHS:'["architecture/roadmap.md"]'};
 const snapshot={source:'rovor_independent_github_patch',configured:true,
  allowed_paths:['architecture/roadmap.md','evan-engine/src/unsafe.js'],items:[],
  mac_required:false,chatgpt_required:false,merges_allowed:false};
 const fetcher=async(_url,options)=>options.headers.Authorization?Response.json(snapshot):new Response(null,{status:401});
 await assert.rejects(()=>verifyGithubPatchWorker(config,fetcher,{attempts:2,pause:async()=>{}}),/github_patch_worker_config_mismatch/);
 let authCount=0;
 await assert.rejects(()=>verifyGithubPatchWorker(config,async(_url,options)=>{
  authCount++;return Response.json(snapshot);
 }),/github_patch_anonymous_access_not_denied/);
 assert.equal(authCount,1);
 const disabled={...config,ROVOR_GITHUB_PATCH_ENABLED:'false'};
 const good=await verifyGithubPatchWorker(disabled,async(_url,options)=>options.headers.Authorization?
  Response.json({...snapshot,configured:false,allowed_paths:[]}):new Response(null,{status:401}),
  {attempts:1,pause:async()=>{}});
 assert.equal(good.configured,false);assert.equal(good.allowed_path_count,0);
});

test('deployed patch checker retries only bounded propagation mismatch, not security failure',async()=>{
 const config={...env,ROVOR_GITHUB_PATCH_ENABLED:'true',ROVOR_GITHUB_PATCH_PATHS:'["architecture/roadmap.md"]'};
 let authenticated=0,retries=0;
 const r=await verifyGithubPatchWorker(config,async(_url,options)=>{
  if(!options.headers.Authorization)return new Response(null,{status:401});
  authenticated++;
  return Response.json({source:'rovor_independent_github_patch',configured:authenticated>1,
   allowed_paths:authenticated>1?['architecture/roadmap.md']:[],items:[],
   mac_required:false,chatgpt_required:false,merges_allowed:false});
 },{attempts:2,pause:async()=>{retries++}});
 assert.equal(r.configured,true);assert.equal(authenticated,2);assert.equal(retries,1);
});
