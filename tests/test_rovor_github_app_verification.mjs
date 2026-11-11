import {test} from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync} from 'node:crypto';
import {githubAppCredentialIssue} from '../integrations/hud-cloud/github-app.mjs';
import {verifyGithubCredentials,verifyGithubWorker} from '../integrations/hud-cloud/verify-github-app.mjs';
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
 assert.equal(r.read_verified,true);assert.equal(calls.length,4);assert(!JSON.stringify(r).includes('token'));
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
