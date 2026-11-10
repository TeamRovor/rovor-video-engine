#!/usr/bin/env node
// Autonomous read-only GitHub work discovery -> owner-private idea inbox.
// A discovery is a draft, NEVER permission to call a model, claim another
// worker's task, push code, review its own output or merge into main.
import {pathToFileURL} from 'node:url';
import path from 'node:path';

const REPO='TeamRovor/rovor-video-engine';
const API='https://api.github.com/repos/'+REPO;
const HUD='https://rovor-hud-telemetry.rovordigital.workers.dev';
const HOUR=3600000,DAY=86400000;
export const MAX_AUTOMATED_DRAFTS_PER_UTC_DAY=6;
// GitHub runs/PR list documents can be large (~0.5-0.9 MB at 40-50 items).
// The fail-closed JSON parser accepts 400k characters per response. Request
// small pages instead of letting otherwise healthy hourly discovery abort.
export const DISCOVERY_PER_PAGE=8;
export const MAX_DUPLICATE_PROBES_PER_RUN=6;

const safeInteger=n=>Number.isSafeInteger(n)&&n>=1;
const within=(raw,now,maxAge)=>{
  const at=typeof raw==='string'?Date.parse(raw):NaN;
  return Number.isFinite(at)&&at<=now&&now-at>=0&&now-at<=maxAge;
};
const candidate=(key,priority,text)=>({key,priority,text});
const allowedLabels=new Set(['security','bug','regression','accessibility','hud','reliability']);
function labelsOf(issue){
 return (Array.isArray(issue?.labels)?issue.labels:[])
   .map(l=>typeof l==='string'?l:l?.name)
   .filter(l=>typeof l==='string').map(l=>l.toLowerCase());
}
export function discoverCandidates({runs=[],issues=[],pulls=[]},now=Date.now()){
 if(!Array.isArray(runs)||!Array.isArray(issues)||!Array.isArray(pulls))
   throw Error('discovery_input_invalid');
 const choices=[];
 for(const r of runs.slice(0,50)){
   if(!safeInteger(r?.id)||r.head_branch!=='main'||r.conclusion!=='failure'||
     !['push','workflow_dispatch'].includes(r.event)||
     !within(r.created_at,now,36*HOUR)||
     typeof r.name!=='string'||/autonomous work discovery/i.test(r.name))continue;
   choices.push(candidate('run-'+r.id,95,
     '[ROVOR-DISCOVERY:run-'+r.id+'] Investigate failed main-branch CI run #'+r.id+
     ' at https://github.com/'+REPO+'/actions/runs/'+r.id+
     '. Reproduce the failure, identify its root cause, and propose a minimal regression test and fix.'+
     ' Inspect task ownership before taking action. This is a proposal, not an approved job.'));
 }
 for(const issue of issues.slice(0,60)){
   if(!safeInteger(issue?.number)||issue?.pull_request||issue?.state!=='open'||
     !within(issue.updated_at,now,7*DAY)||
     (Array.isArray(issue.assignees)&&issue.assignees.length>0))continue;
   const tags=labelsOf(issue);
   const kind=tags.find(l=>allowedLabels.has(l));
   if(!kind)continue;
   const priority=kind==='security'?88:kind==='regression'||kind==='bug'?78:kind==='reliability'?72:kind==='accessibility'?67:58;
   choices.push(candidate('issue-'+issue.number,priority,
     '[ROVOR-DISCOVERY:issue-'+issue.number+'] Review existing unassigned '+kind+
     ' issue #'+issue.number+' at https://github.com/'+REPO+'/issues/'+issue.number+
     '. Verify the report and check the canonical task queue for ownership and duplicates.'+
     ' Propose a concrete, testable correction, without claiming or modifying the issue.'));
 }
 for(const pr of pulls.slice(0,50)){
   if(!safeInteger(pr?.number)||pr?.draft===true||pr?.state!=='open'||
     (Array.isArray(pr.assignees)&&pr.assignees.length>0))continue;
   const updated=Date.parse(pr.updated_at||'');
   if(!Number.isFinite(updated)||updated>now-5*DAY||updated<now-180*DAY)continue;
   choices.push(candidate('pr-'+pr.number,42,
     '[ROVOR-DISCOVERY:pr-'+pr.number+'] Review stale open PR #'+pr.number+
     ' at https://github.com/'+REPO+'/pull/'+pr.number+
     '. Check current ownership, CI failures, relevance, and merge conflicts.'+
     ' Recommend a specific next step. Do not take over the PR or merge without owner approval.'));
 }
 const dedup=new Map();
 for(const item of choices){const old=dedup.get(item.key);
   if(!old||item.priority>old.priority)dedup.set(item.key,item);}
 return [...dedup.values()].sort((a,b)=>b.priority-a.priority||a.key.localeCompare(b.key));
}
function legitHudOrigin(value){return !value||value===HUD;}
async function fetchJSON(url,headers,send){
 let res;
 try{res=await send(url,{method:'GET',redirect:'manual',cache:'no-store',
   headers,signal:AbortSignal.timeout(12000)});}
 catch{throw Error('discovery_read_unavailable');}
 if(res.status!==200)throw Error('discovery_read_unavailable');
 let data;try{const raw=await res.text();if(raw.length>400000)throw Error('size');data=JSON.parse(raw);}
 catch{throw Error('discovery_read_invalid');}
 return data;
}
export async function runDiscovery({env=process.env,send=fetch,now=Date.now()}={}){
 if(!safeInteger(now)||!legitHudOrigin(env.ROVOR_HUD_DEPLOY_ORIGIN))
   throw Error('discovery_configuration_invalid');
 if(typeof env.GITHUB_TOKEN!=='string'||env.GITHUB_TOKEN.length<16||
    typeof env.ROVOR_HUD_WRITER_TOKEN!=='string'||env.ROVOR_HUD_WRITER_TOKEN.length<32)
   return {state:'credentials_unavailable',queued:false};
 const gitHeaders={Authorization:'Bearer '+env.GITHUB_TOKEN,
   Accept:'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'};
 const hudHeaders={Authorization:'Bearer '+env.ROVOR_HUD_WRITER_TOKEN,
   Accept:'application/json'};
 const [runData,issueData,pullData,record]=await Promise.all([
   fetchJSON(API+'/actions/runs?status=failure&per_page='+DISCOVERY_PER_PAGE+'',gitHeaders,send),
   fetchJSON(API+'/issues?state=open&per_page='+DISCOVERY_PER_PAGE+'',gitHeaders,send),
   fetchJSON(API+'/pulls?state=open&per_page='+DISCOVERY_PER_PAGE+'',gitHeaders,send),
   fetchJSON(HUD+'/api/hud/discovery/status',hudHeaders,send)
 ]);
 if(!Array.isArray(runData?.workflow_runs)||!Array.isArray(issueData)||
    !Array.isArray(pullData)||record?.source!=='private_rovor_discovery'||
    record.execution_authorized!==false||record.mac_required!==false||
    record.daily_limit!==MAX_AUTOMATED_DRAFTS_PER_UTC_DAY||
    !Number.isSafeInteger(record.submitted_today)||record.submitted_today<0||
    !Array.isArray(record.recent_keys)||record.recent_keys.length>500)
   throw Error('discovery_source_invalid');
 if(record.submitted_today>=MAX_AUTOMATED_DRAFTS_PER_UTC_DAY)
   return {state:'daily_draft_budget_reached',queued:false,inspected:true};
 const seen=new Set(record.recent_keys);
 const choices=discoverCandidates({runs:runData.workflow_runs,issues:issueData,pulls:pullData},now);
 // D1 still rejects duplicates if an old key fell out of the bounded
 // readback. Bound retries so stale PRs cannot flood the private Worker.
 let probeCount=0;
 for(const pick of choices){
   if(seen.has(pick.key))continue;
   if(probeCount>=MAX_DUPLICATE_PROBES_PER_RUN)
     return {state:'duplicate_probe_budget_reached',queued:false,inspected:true};
   probeCount++;
   let res;
   try{
     res=await send(HUD+'/api/hud/discovery',{
       method:'POST',redirect:'manual',cache:'no-store',
       headers:{...hudHeaders,'Content-Type':'application/json'},
       body:JSON.stringify({key:pick.key,priority:pick.priority,text:pick.text}),
       signal:AbortSignal.timeout(12000)});
   }catch{throw Error('discovery_submission_unconfirmed');}
   if(res.status===409)continue;
   if(res.status===429)return {state:'daily_draft_budget_reached',queued:false,inspected:true};
   if(res.status!==202)throw Error('discovery_submission_unconfirmed');
   let receipt;try{receipt=await res.json();}catch{throw Error('discovery_receipt_invalid');}
   if(receipt?.state!=='pending_review'||receipt.source!=='autonomous_discovery'||
      receipt.execution_authorized!==false||receipt.owner_review_required!==true||
      receipt.model_call_started!==false||receipt.mac_required!==false||
      receipt.queued!==true||!/^[a-f0-9-]{36}$/i.test(receipt.id||''))
     throw Error('discovery_receipt_invalid');
   return {state:'owner_review_draft_queued',queued:true,kind:pick.key.split('-')[0],
     priority:pick.priority,model_call_started:false,execution_authorized:false,mac_required:false};
 }
 return {state:'no_new_evidence_backed_work',queued:false,inspected:true};
}
if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
 runDiscovery().then(r=>{
   // Only preapproved response fields; private HUD content and keys never log.
   console.log('ROVOR cloud discovery: '+JSON.stringify(r));
 }).catch(e=>{
   const known=new Set(['discovery_configuration_invalid','discovery_read_unavailable',
     'discovery_read_invalid','discovery_source_invalid','discovery_submission_unconfirmed',
     'discovery_receipt_invalid']);
   console.error('ROVOR cloud discovery failed: '+(known.has(e?.message)?e.message:'unavailable'));
   process.exitCode=1;
 });
}
