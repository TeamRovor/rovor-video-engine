// Existing native Cloudflare clock -> private D1 inbox. No Actions runner,
// ChatGPT task, local Mac, model call, or new cron is needed for discovery.
import {githubAppConfigured,mintGithubReadToken,readGithubDiscovery} from './github-app.mjs';
import {discoverCandidates} from './discovery-candidates.mjs';
import {recordRepoCatchup} from './repo-catchup.mjs';
import {submitDiscovery,discoveryStatus,DAILY_AUTOMATED_LIMIT} from './discovery-inbox.mjs';
const HOUR=3600000;
const stopped=async(db,now)=>!(await db.prepare(`SELECT 1 AS ready FROM hud_cloud_workforce_control c
 JOIN hud_cloud_workforce_series s ON s.id=1 WHERE c.id=1 AND c.enabled=1 AND s.active=1 AND s.expires_at>?`).bind(now).first());
export async function nativeDiscoveryStatus(env){
 const configured=githubAppConfigured(env);
 const enabled=env.ROVOR_NATIVE_DISCOVERY_ENABLED==='true';
 try{
  const row=await env.DB.prepare('SELECT started_at,finished_at,result_state,discovery_key FROM hud_native_discovery_clock WHERE id=1').bind().first();
  const standing_ready=!(await stopped(env.DB,Date.now()));
  return {source:'rovor_native_github_discovery',configured,enabled,standing_ready,last_check:row??null,
    mac_required:false,chatgpt_required:false,github_actions_required:false};
 }catch{return {source:'rovor_native_github_discovery',configured,enabled,last_check:null,storage_unavailable:true,
    mac_required:false,chatgpt_required:false,github_actions_required:false};}
}
export async function nativeDiscoveryTick(env,now=Date.now(),send=fetch){
 if(env?.ROVOR_NATIVE_DISCOVERY_ENABLED!=='true'||!githubAppConfigured(env))return {state:'not_configured'};
 const db=env.DB;
 if(await stopped(db,now))return {state:'stopped'};
 const record=await discoveryStatus(db,now);
 if(record.status!==200)throw Error('discovery_store_unavailable');
 // The cap restricts new drafts, not an authorized hourly read-only proof.
 const draftBudgetReached=record.body.submitted_today>=DAILY_AUTOMATED_LIMIT;
 const lease=await db.prepare(`INSERT INTO hud_native_discovery_clock(id,started_at,result_state)
  VALUES(1,?,'checking') ON CONFLICT(id) DO UPDATE SET started_at=excluded.started_at,
  finished_at=NULL,result_state='checking',discovery_key=NULL
  WHERE hud_native_discovery_clock.started_at<=? RETURNING id`).bind(now,now-HOUR).first();
 if(!lease)return {state:'interval_not_due'};
 let state='github_read_unavailable',key=null;
 try{
  const token=await mintGithubReadToken(env,now,send);
  if(await stopped(db,Math.max(now,Date.now())))state='stopped';
  else{
   const data=await readGithubDiscovery(token,send);
   // The read-only catch-up is metadata-only and never blocks discovery.
   if(!await stopped(db,Math.max(now,Date.now())))await recordRepoCatchup(db,token,data,now,send);
   const seen=new Set(record.body.recent_keys);
   const picks=draftBudgetReached?[]:discoverCandidates(data,now).filter(x=>!seen.has(x.key)).slice(0,6);
   state=draftBudgetReached?'daily_draft_budget_reached':'no_new_evidence_backed_work';
   for(const pick of picks){
    if(await stopped(db,Math.max(now,Date.now()))){state='stopped';break;}
    const result=await submitDiscovery(db,pick,now);
    if(result.status===409)continue;
    if(result.status===429){state='daily_draft_budget_reached';break;}
    if(result.status!==202){state='discovery_store_unavailable';break;}
    key=pick.key;state='owner_review_draft_queued';break;
   }
  }
 }catch{state='github_read_unavailable';}
 const receipt=await db.prepare(`UPDATE hud_native_discovery_clock
  SET finished_at=?,result_state=?,discovery_key=? WHERE id=1 AND started_at=?`)
  .bind(Math.max(now,Date.now()),state,key,now).run();
 if(receipt.meta?.changes!==1)throw Error('native_discovery_receipt_unconfirmed');
 return {state,discovery_key:key};
}
