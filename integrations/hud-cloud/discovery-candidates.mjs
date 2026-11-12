// Shared pure discovery ranking: no platform, credentials, or network access.
const REPO='TeamRovor/rovor-video-engine';
const HOUR=3600000,DAY=86400000;
const safeInteger=n=>Number.isSafeInteger(n)&&n>=1;
const within=(raw,now,maxAge)=>{
  const at=typeof raw==='string'?Date.parse(raw):NaN;
  return Number.isFinite(at)&&at<=now&&now-at>=0&&now-at<=maxAge;
};
const candidate=(key,priority,text)=>({key,priority,text});
const allowedLabels=new Set(['security','bug','regression','accessibility','hud','reliability']);
 // A tracked owner-prioritized issue should not disappear merely because its
 // GitHub labels were never assigned. Priority comes only from a short,
 // anchored title prefix; untrusted title/body text is NEVER passed to a model.
 // This lane creates review-only D1 drafts and cannot execute GitHub changes.
function titlePriority(title){
 if(typeof title!=='string'||title.length>180)return null;
 const match=/^P([01]):\s+\S/i.exec(title);
 return match?Number(match[1]):null;
}
function labelsOf(issue){
 return (Array.isArray(issue?.labels)?issue.labels:[])
   .map(l=>typeof l==='string'?l:l?.name)
   .filter(l=>typeof l==='string').map(l=>l.toLowerCase());
}
export function discoverCandidates({runs=[],successes=[],issues=[],pulls=[]},now=Date.now()){
 if(!Array.isArray(runs)||!Array.isArray(successes)||!Array.isArray(issues)||!Array.isArray(pulls))
   throw Error('discovery_input_invalid');
 const choices=[];
 for(const r of runs.slice(0,50)){
   if(!safeInteger(r?.id)||r.head_branch!=='main'||r.conclusion!=='failure'||
     !['push','workflow_dispatch'].includes(r.event)||
     !within(r.created_at,now,36*HOUR)||
     typeof r.name!=='string'||/autonomous work discovery/i.test(r.name))continue;
   // Skip an old automatic check only when a later comparable success is known.
   const rAt=Date.parse(r.created_at);
   if(r.event==='push'&&safeInteger(r.workflow_id)&&successes.slice(0,50).some(x=>
    x?.conclusion==='success'&&x.head_branch==='main'&&x.event==='push'&&
    x.workflow_id===r.workflow_id&&safeInteger(x.id)&&within(x.created_at,now,36*HOUR)&&
    (Date.parse(x.created_at)>rAt||x.id===r.id)))continue;
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
   const severity=titlePriority(issue.title);
   if(!kind&&severity===null)continue;
   const labelPriority=kind==='security'?88:kind==='regression'||kind==='bug'?78:kind==='reliability'?72:kind==='accessibility'?67:kind==='hud'?58:0;
   const priority=Math.max(labelPriority,severity===0?90:severity===1?76:0);
   const category=kind||('P'+severity+' priority');
   choices.push(candidate('issue-'+issue.number,priority,
     '[ROVOR-DISCOVERY:issue-'+issue.number+'] Review existing unassigned '+category+
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
