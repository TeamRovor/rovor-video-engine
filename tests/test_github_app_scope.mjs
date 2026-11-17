import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,webcrypto} from 'node:crypto';
import {mintGithubPatchToken,mintGithubReadToken} from '../integrations/hud-cloud/github-app.mjs';

const now=Date.now();
const {privateKey}=generateKeyPairSync('rsa',{modulusLength:2048});
const env={
 ROVOR_GITHUB_APP_ID:'123456',
 ROVOR_GITHUB_INSTALLATION_ID:'456789',
 ROVOR_GITHUB_APP_PRIVATE_KEY:privateKey.export({type:'pkcs8',format:'pem'})
};
const repo={full_name:'TeamRovor/rovor-video-engine'};
const response=(permissions,repositories)=>({
 token:'x'.repeat(24),expires_at:new Date(now+3600000).toISOString(),
 permissions,...(repositories===undefined?{}:{repositories})
});
function sender(payload,permissions){
 return async(url,options)=>{
  assert.equal(url,'https://api.github.com/app/installations/456789/access_tokens');
  assert.equal(options.method,'POST');
  assert.equal(options.redirect,'manual');
  assert.deepEqual(JSON.parse(options.body),{
   repositories:['rovor-video-engine'],permissions
  });
  return new Response(JSON.stringify(payload),{status:201,headers:{'content-type':'application/json'}});
 };
}
const patch={contents:'write',pull_requests:'write'};
const read={contents:'read',issues:'read',pull_requests:'read',actions:'read'};
test('exact named repository scope permits pinned write and read tokens',async()=>{
 const old=globalThis.crypto;globalThis.crypto=webcrypto;
 try{
  assert.equal(await mintGithubPatchToken(env,now,sender(response(patch,[repo]),patch)),'x'.repeat(24));
  assert.equal(await mintGithubReadToken(env,now,sender(response(read,[repo]),read)),'x'.repeat(24));
 }finally{globalThis.crypto=old;}
});
for(const [name,repositories] of [
 ['missing repository proof',undefined],
 ['empty repository proof',[]],
 ['different repository',[{full_name:'TeamRovor/other'}]],
 ['additional repository',[repo,{full_name:'TeamRovor/other'}]],
 ['unidentified repository',[{}]]
]){
 test('rejects '+name+' for write scope',async()=>{
  const old=globalThis.crypto;globalThis.crypto=webcrypto;
  try{
   await assert.rejects(mintGithubPatchToken(env,now,sender(response(patch,repositories),patch)),
    /github_installation_token_scope_invalid/);
  }finally{globalThis.crypto=old;}
 });
}
test('rejects missing repository evidence for read scope too',async()=>{
 const old=globalThis.crypto;globalThis.crypto=webcrypto;
 try{
  await assert.rejects(mintGithubReadToken(env,now,sender(response(read,undefined),read)),
   /github_installation_token_scope_invalid/);
 }finally{globalThis.crypto=old;}
});
