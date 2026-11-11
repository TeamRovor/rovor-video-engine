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

export async function repoCatchupStatus(env,now=Date.now()){
 try{
  const row=await env.DB.prepare('SELECT checked_at,observed_at,state,snapshot FROM hud_native_repo_catchup WHERE id=1').bind().first();
  let snapshot=null;
  if(typeof row?.snapshot==='string')snapshot=JSON.parse(row.snapshot);
  const recorded=row?.observed_at;
  const snapshot_freshness=!snapshot||!Number.isSafeInteger(recorded)||recorded>now?'unavailable':
    now-recorded<=7200000?'fresh':'stale';
  return {source:'rovor_private_repo_catchup',state:row?.state??'not_checked',
   checked_at:row?.checked_at??null,observed_at:row?.observed_at??null,
   snapshot,snapshot_freshness,private_reader_required:true,model_called:false,repository_written:false,
   mac_required:false,chatgpt_required:false};
 }catch{return {source:'rovor_private_repo_catchup',state:'storage_unavailable',
   snapshot_freshness:'unavailable',private_reader_required:true,model_called:false,repository_written:false,
   mac_required:false,chatgpt_required:false};}
}
