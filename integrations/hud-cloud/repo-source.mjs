// Reviewed source excerpts only. Cloudflare serves a frozen, commit-pinned
// bundle from its private deployment assets; no GitHub API token or Mac needed.
// A model never gains tool calls, repository writes, or access to arbitrary paths.
export const REPO_SOURCE_FILES=Object.freeze([
 'coordination/TASK-INTAKE.md',
 'integrations/hud-cloud/ASK-ROVOR-SETUP.md',
 'integrations/hud-cloud/worker.mjs',
 'integrations/hud-cloud/verify-github-deploy.mjs',
 'dashboard/command-center/native-v8-9/hud-chat.js',
 'dashboard/command-center/native-v8-9/live-quota-board.js',
 'tools/hud_chat.mjs',
 '.github/workflows/deploy-private-hud-cloudflare.yml'
]);
const SHA=/^[a-f0-9]{40}$/;
const MAX_EXCERPT=1800;
const MAX_BUNDLE=24000;
const DENIED=Object.freeze({status:400,body:{error:'repo_source_not_permitted'}});
export function createRepoSnapshot(commit,readSource){
 if(!SHA.test(commit)||typeof readSource!=='function')throw Error('invalid_repo_snapshot');
 const files={};
 for(const path of REPO_SOURCE_FILES){
   const content=readSource(path);
   if(typeof content!=='string'||!content.length||content.length>250000)
     throw Error('repo_source_invalid');
   const excerpt=content.slice(0,MAX_EXCERPT);
   // A prebuilt source excerpt is *data*, never instructions for the model.
   files[path]={text:excerpt,truncated:excerpt.length<content.length};
 }
 const value={source:'reviewed_github_checkout',commit,mac_required:false,files};
 if(JSON.stringify(value).length>MAX_BUNDLE)throw Error('repo_snapshot_too_large');
 return value;
}
export function selectRepoSnapshot(snapshot,path){
 if(!REPO_SOURCE_FILES.includes(path))return DENIED;
 if(!snapshot||snapshot.source!=='reviewed_github_checkout'||
     !SHA.test(snapshot.commit)||snapshot.mac_required!==false||
     !snapshot.files||typeof snapshot.files!=='object'||Array.isArray(snapshot.files))
   return {status:503,body:{error:'repo_snapshot_unavailable'}};
 const entry=snapshot.files[path];
 if(!entry||typeof entry.text!=='string'||!entry.text.length||
     entry.text.length>MAX_EXCERPT||typeof entry.truncated!=='boolean')
   return {status:503,body:{error:'repo_snapshot_unavailable'}};
 return {status:200,body:{source:snapshot.source,repo:'TeamRovor/rovor-video-engine',
   path,commit:snapshot.commit,text:entry.text,truncated:entry.truncated,
   fetched_live:false,can_write:false,mac_required:false}};
}
export async function getRepoSource(env,request,path){
 if(!REPO_SOURCE_FILES.includes(path))return DENIED;
 if(!env?.ASSETS?.fetch)return {status:503,body:{error:'repo_snapshot_unavailable'}};
 let asset;
 try{
   asset=await env.ASSETS.fetch(new Request(new URL('/rovor-repo-source.json',request.url),{method:'GET',redirect:'manual'}));
   if(asset.status!==200)return {status:503,body:{error:'repo_snapshot_unavailable'}};
   const raw=await asset.text();
   if(!raw||raw.length>MAX_BUNDLE)return {status:503,body:{error:'repo_snapshot_unavailable'}};
   return selectRepoSnapshot(JSON.parse(raw),path);
 }catch{return {status:503,body:{error:'repo_snapshot_unavailable'}};}
}
