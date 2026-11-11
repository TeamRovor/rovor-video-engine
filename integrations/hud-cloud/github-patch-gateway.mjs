// ROVOR's first real independent write tool. A model may propose an exact
// one-file text replacement; only separately authorized, human-PASS'd output
// can be queued. Native cron never merges, deploys, executes code, or retries.
import {githubAppConfigured,mintGithubPatchToken} from './github-app.mjs';
const REPO='TeamRovor/rovor-video-engine',API='https://api.github.com/repos/'+REPO;
const SHA=/^[a-f0-9]{40}$/,DIGEST=/^[a-f0-9]{64}$/,ID=/^[a-z0-9][a-z0-9-]{0,149}$/;
const DAY=86400000,MAX_FILE=16384;
const utf8=new TextEncoder();
const exact=(value,keys)=>value&&typeof value==='object'&&!Array.isArray(value)&&
 Object.keys(value).sort().join(',')===keys;
const digest=async value=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',utf8.encode(value))),
 b=>b.toString(16).padStart(2,'0')).join('');
const result=(status,body)=>({status,body});
const safeText=(v,max)=>typeof v==='string'&&v.length>0&&utf8.encode(v).length<=max&&!v.includes('\0');
// A second hard boundary is independent of the owner-configured allowlist.
// First release is restricted to documentation, CSS and isolated production
// engine source. No auth, workflow, dependency, deployment or Core files.
function safePath(path){
 return typeof path==='string'&&path.length<=180&&/^[A-Za-z0-9][A-Za-z0-9_./-]+$/.test(path)&&
 !path.split('/').some(s=>!s||s==='.'||s==='..'||s.startsWith('.'))&&
 (/^(architecture|business|design)\/[A-Za-z0-9_./-]+\.md$/.test(path)||
 /^dashboard\/command-center\/native-v8-9\/(hud-mobile|workload-popup)\.css$/.test(path)||
 /^evan-engine\/[A-Za-z0-9_./-]+\.(py|mjs|js|ts|md)$/.test(path));
}
function pathPolicy(env){
 try{
  const list=JSON.parse(env.ROVOR_GITHUB_PATCH_PATHS||'[]');
  if(!Array.isArray(list)||!list.length||list.length>12||new Set(list).size!==list.length||
     list.some(p=>!safePath(p)))return [];
  return list;
 }catch{return [];}
}
function ready(env){return env?.ROVOR_GITHUB_PATCH_ENABLED==='true'&&githubAppConfigured(env)&&pathPolicy(env).length>0;}
export function parsePatch(raw,sourceCommit,env){
 if(!safeText(raw,12000)||!SHA.test(sourceCommit))throw Error('patch_proposal_invalid');
 let p;try{p=JSON.parse(raw);}catch{throw Error('patch_proposal_invalid');}
 if(!exact(p,'base_commit,change,summary,title,version')||p.version!==1||p.base_commit!==sourceCommit||
    !safeText(p.title,90)||/[\r\n\x00-\x1f]/.test(p.title)||
    !safeText(p.summary,700)||!exact(p.change,'after,before,blob_sha,path')||
    !pathPolicy(env).includes(p.change.path)||!SHA.test(p.change.blob_sha)||
    !safeText(p.change.before,4000)||!safeText(p.change.after,4000)||p.change.before===p.change.after)
  throw Error('patch_proposal_invalid');
 return p;
}
const gate=async(db)=>(await db.prepare('SELECT enabled FROM hud_cloud_workforce_control WHERE id=1').bind().first())?.enabled===1;
async function reviewedJob(db,id,hash){
 const job=await db.prepare(`SELECT id,source_commit,output,output_sha256,kind,human_review,state
  FROM hud_cloud_workforce_jobs WHERE id=?`).bind(id).first();
 if(!job||job.kind!=='code_review'||job.state!=='needs_review'||job.human_review!=='passed'||
    job.output_sha256!==hash||typeof job.output!=='string'||await digest(job.output)!==hash)
  throw Error('reviewed_patch_required');
 return job;
}
export async function queueGithubPatch(env,body,now=Date.now()){
 if(!ready(env))return result(503,{error:'github_patch_not_enabled'});
 if(!exact(body,'job_id,output_sha256')||!ID.test(body.job_id)||!DIGEST.test(body.output_sha256))
  return result(400,{error:'patch_authorization_invalid'});
 const db=env.DB;
 try{
  if(!await gate(db))return result(409,{error:'workforce_stopped'});
  const job=await reviewedJob(db,body.job_id,body.output_sha256);
  const proposal=parsePatch(job.output,job.source_commit,env);
  const branch='rovor/patch-'+(await digest(job.id)).slice(0,24);
  const row=await db.prepare(`INSERT INTO hud_github_patch_jobs
   (job_id,output_sha256,base_commit,path,branch,authorized_at,expires_at,state)
   SELECT ?,?,?,?,?,?,?,'queued' WHERE (SELECT enabled FROM hud_cloud_workforce_control WHERE id=1)=1
   ON CONFLICT(job_id) DO NOTHING RETURNING job_id`)
   .bind(job.id,job.output_sha256,job.source_commit,proposal.change.path,branch,now,now+DAY).first();
  if(!row)return result(409,{error:'patch_already_authorized_or_stopped'});
  return result(202,{job_id:job.id,state:'queued',branch,execution_started:false});
 }catch(e){return result(409,{error:['reviewed_patch_required','patch_proposal_invalid'].includes(e.message)?e.message:'patch_queue_unavailable'});}
}
export async function githubPatchStatus(env){
 try{
  const rows=await env.DB.prepare(`SELECT job_id,output_sha256,base_commit,path,branch,authorized_at,
   expires_at,started_at,finished_at,state,error_code,commit_sha,pr_number
   FROM hud_github_patch_jobs ORDER BY authorized_at DESC LIMIT 30`).all();
  return {source:'rovor_independent_github_patch',configured:ready(env),items:rows.results||[],
   mac_required:false,chatgpt_required:false,merges_allowed:false};
 }catch{return {source:'rovor_independent_github_patch',configured:false,items:[],storage_unavailable:true,merges_allowed:false};}
}
async function bounded(response,max=500000){
 if(!response.body)throw Error('github_response_missing');
 const r=response.body.getReader();let total=0;const chunks=[];
 try{for(;;){const {done,value}=await r.read();if(done)break;total+=value.byteLength;
  if(total>max)throw Error('github_response_too_large');chunks.push(value);}}
 finally{await r.cancel().catch(()=>{});}
 const data=new Uint8Array(total);let n=0;for(const c of chunks){data.set(c,n);n+=c.length;}
 return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(data));
}
function client(token,send){
 return async(path,method='GET',body=null)=>{
  const r=await send(API+path,{method,redirect:'manual',signal:AbortSignal.timeout(12000),
   headers:{Authorization:'Bearer '+token,Accept:'application/vnd.github+json',
    'X-GitHub-Api-Version':'2022-11-28','User-Agent':'ROVOR-Cloud-Executor',
    ...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});
  if(r.status!==(method==='GET'?200:201)){await r.body?.cancel();throw Error('github_operation_denied');}
  return bounded(r);
 };
}
export function replaceExact(text,before,after){
 if(!safeText(text,MAX_FILE))throw Error('patch_file_invalid');
 const at=text.indexOf(before);
 if(at<0||text.indexOf(before,at+1)!==-1)throw Error('patch_anchor_not_unique');
 const next=text.slice(0,at)+after+text.slice(at+before.length);
 if(!safeText(next,MAX_FILE)||next===text)throw Error('patch_file_invalid');
 return next;
}
async function event(db,job,step,reference,now){
 const r=await db.prepare('INSERT INTO hud_github_patch_events(job_id,step,reference,recorded_at) VALUES(?,?,?,?)')
  .bind(job,step,reference,now).run();
 if(r.meta?.changes!==1)throw Error('github_write_receipt_unconfirmed');
}
export async function githubPatchTick(env,now=Date.now(),send=fetch){
 if(!ready(env))return {state:'not_configured'};
 const db=env.DB;
 if(!await gate(db))return {state:'stopped'};
 // Interrupted claims never replay; unresolved external effects block new
 // writes until a human reconciles them. One patch attempt per rolling day.
 const claim=await db.prepare(`UPDATE hud_github_patch_jobs SET state='running',started_at=?
  WHERE job_id=(SELECT job_id FROM hud_github_patch_jobs WHERE state='queued' AND expires_at>?
    ORDER BY authorized_at,job_id LIMIT 1)
  AND (SELECT enabled FROM hud_cloud_workforce_control WHERE id=1)=1
  AND NOT EXISTS(SELECT 1 FROM hud_github_patch_jobs WHERE state IN ('running','uncertain'))
  AND NOT EXISTS(SELECT 1 FROM hud_github_patch_jobs WHERE started_at>?)
  RETURNING *`).bind(now,now,now-DAY).first();
 if(!claim)return {state:'idle_or_safety_limited'};
 let state='failed',error='patch_execution_failed',commitSha=null,prNumber=null,wrote=false;
 try{
  const check=async()=>{
   if(!await gate(db)||claim.expires_at<=Math.max(now,Date.now()))throw Error('patch_stopped_or_expired');
  };
  await check();
  const job=await reviewedJob(db,claim.job_id,claim.output_sha256);
  const p=parsePatch(job.output,claim.base_commit,env);
  if(p.change.path!==claim.path||claim.branch!=='rovor/patch-'+(await digest(job.id)).slice(0,24))
   throw Error('patch_proposal_invalid');
  const token=await mintGithubPatchToken(env,now,send),api=client(token,send);
  await check();
  const main=await api('/git/ref/heads/main');
  if(main.object?.sha!==claim.base_commit)throw Error('patch_base_stale');
  const base=await api('/git/commits/'+claim.base_commit);
  if(base.sha!==claim.base_commit||!SHA.test(base.tree?.sha))throw Error('github_base_invalid');
  const tree=await api('/git/trees/'+base.tree.sha+'?recursive=1');
  if(tree.sha!==base.tree.sha||tree.truncated!==false||!Array.isArray(tree.tree))throw Error('github_tree_invalid');
  const entry=tree.tree.find(x=>x.path===p.change.path);
  if(!entry||entry.type!=='blob'||entry.mode!=='100644'||entry.sha!==p.change.blob_sha)
   throw Error('patch_blob_mismatch');
  const blob=await api('/git/blobs/'+entry.sha);
  if(blob.sha!==entry.sha||blob.encoding!=='base64'||typeof blob.content!=='string'||
     !Number.isSafeInteger(blob.size)||blob.size<1||blob.size>MAX_FILE)throw Error('patch_file_invalid');
  const bytes=Uint8Array.from(atob(blob.content.replace(/\s/g,'')),c=>c.charCodeAt(0));
  if(bytes.length!==blob.size)throw Error('patch_file_invalid');
  const content=replaceExact(new TextDecoder('utf-8',{fatal:true}).decode(bytes),p.change.before,p.change.after);
  // Check current main again before the first external write, then never
  // follow a moving ref or overwrite an existing branch.
  await check();const latest=await api('/git/ref/heads/main');
  if(latest.object?.sha!==claim.base_commit)throw Error('patch_base_stale');
  await check();wrote=true;
  const newTree=await api('/git/trees','POST',{base_tree:base.tree.sha,
   tree:[{path:p.change.path,mode:'100644',type:'blob',content}]});
  if(!SHA.test(newTree.sha)||newTree.sha===base.tree.sha)throw Error('github_tree_invalid');
  await event(db,job.id,'tree',newTree.sha,Date.now());
  await check();
  const commit=await api('/git/commits','POST',{message:'ROVOR reviewed patch: '+p.title,tree:newTree.sha,parents:[claim.base_commit]});
  if(!SHA.test(commit.sha)||commit.tree?.sha!==newTree.sha||commit.parents?.length!==1||
     commit.parents[0].sha!==claim.base_commit)throw Error('github_commit_invalid');
  commitSha=commit.sha;await event(db,job.id,'commit',commitSha,Date.now());
  await check();
  const ref=await api('/git/refs','POST',{ref:'refs/heads/'+claim.branch,sha:commitSha});
  if(ref.ref!=='refs/heads/'+claim.branch||ref.object?.sha!==commitSha)throw Error('github_ref_invalid');
  await event(db,job.id,'branch',claim.branch,Date.now());
  await check();
  const pr=await api('/pulls','POST',{title:'ROVOR: '+p.title,head:claim.branch,base:'main',draft:true,
   body:'Owner-reviewed ROVOR patch. Source job '+job.id+'; output SHA-256 '+job.output_sha256+
    '.\n\n'+p.summary+'\n\nDraft only. Independent CI and human release approval required.'});
  if(!Number.isSafeInteger(pr.number)||pr.number<1||pr.draft!==true||pr.head?.sha!==commitSha||
     pr.head?.ref!==claim.branch||pr.base?.ref!=='main'||pr.base?.repo?.full_name!==REPO)
   throw Error('github_pull_invalid');
  prNumber=pr.number;await event(db,job.id,'draft_pr',String(prNumber),Date.now());
  state='opened';error=null;
 }catch(e){
  state=wrote?'uncertain':'failed';
  const allowed=['patch_stopped_or_expired','patch_proposal_invalid','patch_base_stale','patch_blob_mismatch',
   'patch_anchor_not_unique','patch_file_invalid','reviewed_patch_required','github_operation_denied','github_write_receipt_unconfirmed'];
  error=allowed.includes(e.message)?e.message:'patch_execution_unconfirmed';
 }
 const saved=await db.prepare(`UPDATE hud_github_patch_jobs SET state=?,error_code=?,finished_at=?,commit_sha=?,pr_number=?
  WHERE job_id=? AND state='running'`).bind(state,error,Math.max(now,Date.now()),commitSha,prNumber,claim.job_id).run();
 if(saved.meta?.changes!==1)throw Error('patch_terminal_receipt_unconfirmed');
 return {state,job_id:claim.job_id,pr_number:prNumber,commit_sha:commitSha};
}
