// Private, metadata-only checkpoint for employees to catch up on main.
// Cloudflare D1 retains a last-good read when GitHub becomes unavailable.
// No source bodies, commit messages, provider inference or repository writes.
import {githubAppConfigured,mintGithubReadToken,readGithubDiscovery,readGithubCommitCatchup} from './github-app.mjs';
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
  const changed=await db.prepare("INSERT INTO hud_native_repo_catchup (id,checked_at,observed_at,state,snapshot) VALUES(1,?,?,?,?) ON CONFLICT(id) DO UPDATE SET checked_at=excluded.checked_at,state=excluded.state,observed_at=CASE WHEN excluded.state='ready' THEN excluded.observed_at ELSE hud_native_repo_catchup.observed_at END,snapshot=CASE WHEN excluded.state='ready' THEN excluded.snapshot ELSE hud_native_repo_catchup.snapshot END WHERE hud_native_repo_catchup.checked_at<=excluded.checked_at")
   .bind(now,state==='ready'?now:null,state,body?JSON.stringify(body):null).run();
  if(changed.meta?.changes!==1)throw Error('catchup_receipt_missing');
 }catch{return {state:'storage_unavailable'};}
 return {state,head_sha:body?.head_sha??null};
}
// Explicit writer-only, rate-limited metadata refresh used for one bounded
// production proof and the existing native clock. No discovery intake, model,
// source forwarding, patch authorization, or GitHub repository writes.
const REFRESH_INTERVAL=15*60000;
async function standingReady(db,now){
 const row=await db.prepare("SELECT 1 ready FROM hud_cloud_workforce_control c JOIN hud_cloud_workforce_series s ON s.id=1 WHERE c.id=1 AND c.enabled=1 AND s.active=1 AND s.expires_at>?")
  .bind(now).first();
 return row?.ready===1;
}
export async function refreshRepoCatchup(env,now=Date.now(),send=fetch){
 const reply=(status,state)=>({status,body:{state,model_called:false,repository_written:false}});
 if(!env?.DB||env.ROVOR_NATIVE_DISCOVERY_ENABLED!=='true'||!githubAppConfigured(env))
  return reply(503,'not_configured');
 try{
  if(!await standingReady(env.DB,now))return reply(409,'stopped');
  // A durable D1 singleton is the lease. An interrupted attempt must not
  // replay until the minimum interval has elapsed.
  const claim=await env.DB.prepare("INSERT INTO hud_native_repo_catchup(id,checked_at,state) VALUES(1,?,'read_unavailable') ON CONFLICT(id) DO UPDATE SET checked_at=excluded.checked_at,state='read_unavailable' WHERE hud_native_repo_catchup.checked_at<=? RETURNING id")
   .bind(now,now-REFRESH_INTERVAL).first();
  if(!claim)return reply(200,'interval_not_due');
  const token=await mintGithubReadToken(env,now,send);
  if(!await standingReady(env.DB,Math.max(now,Date.now())))return reply(409,'stopped');
  const discovery=await readGithubDiscovery(token,send);
  if(!await standingReady(env.DB,Math.max(now,Date.now())))return reply(409,'stopped');
  const result=await recordRepoCatchup(env.DB,token,discovery,now,send);
  return reply(result.state==='storage_unavailable'?503:200,result.state);
 }catch{return reply(503,'read_unavailable');}
}

// D1 is durable evidence storage, not a trusted API response schema. Never
// echo arbitrary saved JSON, even to an authenticated private HUD reader.
const COMMIT_SHA=/^[a-f0-9]{40}$/;
const MAX_SNAPSHOT_CHARS=16000;
const positiveId=value=>Number.isSafeInteger(value)&&value>0;
const unique=values=>new Set(values).size===values.length;
const validIds=values=>Array.isArray(values)&&values.length<=8&&
 values.every(positiveId)&&unique(values);
const validPath=value=>typeof value==='string'&&value.length>0&&value.length<=200&&
 !/[\u0000-\u001f\u007f]/.test(value);

// Explicit output projection: unknown source keys and nested metadata never
// leave the private D1 boundary. Inconsistent receipts are unavailable, not
// partial evidence that agents can mistake for a complete repository scan.
export function projectRepoCatchupSnapshot(value){
 if(!value||typeof value!=='object'||Array.isArray(value))return null;
 const {head_sha,recent_commit_shas,scanned_commit_count,commit_file_counts,
  changed_paths,changed_paths_truncated,failed_run_ids,recent_success_run_ids,
  open_issue_numbers,open_pr_numbers}=value;
 if(!Array.isArray(recent_commit_shas)||recent_commit_shas.length<1||
    recent_commit_shas.length>4||recent_commit_shas.some(sha=>!COMMIT_SHA.test(sha))||
    !unique(recent_commit_shas)||head_sha!==recent_commit_shas[0]||
    scanned_commit_count!==recent_commit_shas.length||
    !Array.isArray(commit_file_counts)||commit_file_counts.length!==scanned_commit_count||
    commit_file_counts.some((entry,i)=>!entry||typeof entry!=='object'||Array.isArray(entry)||
      entry.sha!==recent_commit_shas[i]||!Number.isSafeInteger(entry.files_observed)||
      entry.files_observed<0||entry.files_observed>30||
      typeof entry.paths_truncated!=='boolean')||
    !Array.isArray(changed_paths)||changed_paths.length>24||
    changed_paths.some(path=>!validPath(path))||!unique(changed_paths)||
    typeof changed_paths_truncated!=='boolean'||
    (commit_file_counts.some(entry=>entry.paths_truncated)&&!changed_paths_truncated)||
    !validIds(failed_run_ids)||!validIds(recent_success_run_ids)||
    !validIds(open_issue_numbers)||!validIds(open_pr_numbers))return null;
 return {head_sha,recent_commit_shas:[...recent_commit_shas],scanned_commit_count,
  commit_file_counts:commit_file_counts.map(entry=>({
    sha:entry.sha,files_observed:entry.files_observed,paths_truncated:entry.paths_truncated})),
  changed_paths:[...changed_paths],changed_paths_truncated,
  failed_run_ids:[...failed_run_ids],recent_success_run_ids:[...recent_success_run_ids],
  open_issue_numbers:[...open_issue_numbers],open_pr_numbers:[...open_pr_numbers]};
}
export async function repoCatchupStatus(env,now=Date.now()){
 try{
  const row=await env.DB.prepare('SELECT checked_at,observed_at,state,snapshot FROM hud_native_repo_catchup WHERE id=1').bind().first();
  const stored=typeof row?.snapshot==='string'?row.snapshot:null;
  let snapshot=null;
  if(stored!==null&&stored.length<=MAX_SNAPSHOT_CHARS){
   try{snapshot=projectRepoCatchupSnapshot(JSON.parse(stored));}catch{}
  }
  const snapshotInvalid=stored!==null&&snapshot===null;
  const checked=positiveId(row?.checked_at)?row.checked_at:null;
  const recorded=!snapshotInvalid&&positiveId(row?.observed_at)?row.observed_at:null;
  const snapshot_freshness=!snapshot||recorded===null||recorded>now?'unavailable':
    now-recorded<=7200000?'fresh':'stale';
  const state=snapshotInvalid?'snapshot_invalid':
    ['ready','read_unavailable'].includes(row?.state)?row.state:
    row?'unavailable':'not_checked';
  return {source:'rovor_private_repo_catchup',state,
   checked_at:checked,observed_at:recorded,
   snapshot,snapshot_freshness,
   // The GitHub reader fetches at most eight IDs per resource family.
   // These are bounded evidence samples, never an exhaustive PR inventory.
   open_pr_count_is_total:false,private_reader_required:true,model_called:false,repository_written:false,
   mac_required:false,chatgpt_required:false};
 }catch{return {source:'rovor_private_repo_catchup',state:'storage_unavailable',
   snapshot_freshness:'unavailable',open_pr_count_is_total:false,
   private_reader_required:true,model_called:false,repository_written:false,
   mac_required:false,chatgpt_required:false};}
}
