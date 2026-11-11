// Private, metadata-only checkpoint for employees to catch up on main.
// Cloudflare D1 retains a last-good read when GitHub becomes unavailable.
// No source bodies, commit messages, provider inference or repository writes.
import {readGithubCommitCatchup} from './github-app.mjs';
const countable=rows=>Array.isArray(rows)?rows:[];
const ids=(rows,predicate)=>countable(rows).filter(predicate).map(x=>x.id??x.number)
 .filter(x=>Number.isSafeInteger(x)&&x>0).slice(0,8);
export async function recordRepoCatchup(db,token,discovery,now=Date.now(),send=fetch){
 let state='read_unavailable',body=null;
 try{
  const commits=await readGithubCommitCatchup(token,send);
  body={...commits,
   failed_run_ids:ids(discovery?.runs,x=>x?.conclusion==='failure'&&x.head_branch==='main'),
   recent_success_run_ids:ids(discovery?.successes,x=>x?.conclusion==='success'&&x.head_branch==='main'),
   open_issue_numbers:ids(discovery?.issues,x=>x?.state==='open'&&!x.pull_request),
   open_pr_numbers:ids(discovery?.pulls,x=>x?.state==='open')};
  state='ready';
 }catch{}
 try{
  const changed=await db.prepare("INSERT INTO hud_native_repo_catchup (id,checked_at,observed_at,state,snapshot) VALUES(1,?,?,?,?) ON CONFLICT(id) DO UPDATE SET checked_at=excluded.checked_at,state=excluded.state,observed_at=CASE WHEN excluded.state='ready' THEN excluded.observed_at ELSE hud_native_repo_catchup.observed_at END,snapshot=CASE WHEN excluded.state='ready' THEN excluded.snapshot ELSE hud_native_repo_catchup.snapshot END")
   .bind(now,state==='ready'?now:null,state,body?JSON.stringify(body):null).run();
  if(changed.meta?.changes!==1)throw Error('catchup_receipt_missing');
 }catch{return {state:'storage_unavailable'};}
 return {state,head_sha:body?.head_sha??null};
}
export async function repoCatchupStatus(env){
 try{
  const row=await env.DB.prepare('SELECT checked_at,observed_at,state,snapshot FROM hud_native_repo_catchup WHERE id=1').bind().first();
  let snapshot=null;
  if(typeof row?.snapshot==='string')snapshot=JSON.parse(row.snapshot);
  return {source:'rovor_private_repo_catchup',state:row?.state??'not_checked',
   checked_at:row?.checked_at??null,observed_at:row?.observed_at??null,
   snapshot,private_reader_required:true,model_called:false,repository_written:false,
   mac_required:false,chatgpt_required:false};
 }catch{return {source:'rovor_private_repo_catchup',state:'storage_unavailable',
   private_reader_required:true,model_called:false,repository_written:false,
   mac_required:false,chatgpt_required:false};}
}
