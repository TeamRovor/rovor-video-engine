// Owner-only review desk for the EXISTING authenticated Cloudflare HUD.
// No inference, STOP mutation, credential exposure, public publication or replay.
(function(){
'use strict';
const byId=id=>document.getElementById(id);
const make=(tag,className,text)=>{
 const node=document.createElement(tag);
 if(className)node.className=className;
 if(text!==undefined)node.textContent=String(text);
 return node;
};
const jobs=byId('jobs'),history=byId('history'),message=byId('message'),state=byId('page-status'),guidance=byId('inbox-guidance');
const deferred=new Set();
let refreshGeneration=0;
const pending=byId('pending'),reviewed=byId('reviewed'),stop=byId('stop-state');
const refreshButton=byId('refresh');
const nativeClock=byId('native-clock'),nativeDetail=byId('native-detail'),standing=byId('standing-state');
const validTokens=n=>Number.isSafeInteger(n)&&n>=0;
function admissionGuidance(admission,now=Date.now()){
 const unavailable='Workforce capacity details are unavailable or stale. Refresh to check why work is waiting.';
 if(!admission||admission.source!=='read_only_private_D1'||
    admission.provider_admission_verified_by_this_read!==false||
    !Number.isSafeInteger(admission.observed_at)||admission.observed_at>now||now-admission.observed_at>300000||
    !['queued_jobs','running_or_uncertain','pending_reviews','rolling_day_attempts',
      'rolling_day_limit','pending_review_limit','fresh_unattempted_discoveries'].every(k=>validTokens(admission[k]))||
    admission.rolling_day_limit<1||admission.pending_review_limit<1||
    !Array.isArray(admission.observed_constraints))return unavailable;
 const reasons={
  stop_closed:'STOP is active.',
  standing_authorization_inactive:'Recurring owner authorization is inactive.',
  running_or_uncertain_claim:'A running or uncertain job must finish or be reconciled before another starts.',
  rolling_day_attempt_limit:'The rolling 24-hour attempt limit is reached.',
  pending_review_limit:'The review queue is full; review a result to make room.',
  no_queued_job:'No job is queued.',
  no_fresh_unattempted_discovery:'No fresh, unattempted discovery is recorded.'
 };
 if(admission.observed_constraints.some(k=>!Object.hasOwn(reasons,k)))return unavailable;
 const parts=[`Latest workforce check: ${admission.rolling_day_attempts} of ${admission.rolling_day_limit} attempts in the last 24 hours; `+
  `${admission.pending_reviews} of ${admission.pending_review_limit} reviews waiting; ${admission.queued_jobs} jobs queued; `+
  `${admission.fresh_unattempted_discoveries} fresh discoveries.`];
 parts.push(...admission.observed_constraints.map(k=>reasons[k]));
 if(admission.observed_constraints.includes('rolling_day_attempt_limit')){
  const slot=admission.earliest_rolling_slot_at;
  parts.push(Number.isSafeInteger(slot)&&slot>admission.observed_at&&slot<=admission.observed_at+86400000?
   'Earliest daily slot: '+formatTime(slot)+'.':'The next daily slot is not verified.');
 }
 parts.push('These are observed queue limits. Provider checks still apply; a free slot does not guarantee execution.');
 return parts.join(' ');
}
const githubDiscoveryState=byId('github-discovery-state'),githubDiscoveryDetail=byId('github-discovery-detail');
async function refreshNativeDiscovery(){
 try{
  const data=await privateRequest('/api/hud/workforce/native-discovery');
  if(data.source!=='rovor_native_github_discovery'||typeof data.configured!=='boolean'||
     typeof data.enabled!=='boolean'||data.mac_required!==false||data.chatgpt_required!==false||
     data.github_actions_required!==false||data.storage_unavailable)throw Error('native_discovery_unavailable');
  const receipt=data.last_check;
  const verified=receipt&&['no_new_evidence_backed_work','owner_review_draft_queued','daily_draft_budget_reached'].includes(receipt.result_state)&&
   Number.isSafeInteger(receipt.finished_at)&&receipt.finished_at>0;
  const fresh=verified&&Date.now()-receipt.finished_at<7200000&&Date.now()>=receipt.finished_at;
  githubDiscoveryState.textContent=!data.configured?'NOT CONFIGURED':!data.enabled?'DISABLED':
   fresh?'READ VERIFIED':receipt?.result_state==='github_read_unavailable'?'READ FAILED':
   data.standing_ready===false?'STOP / OWNER AUTHORIZATION REQUIRED':
   verified?'STALE RECEIPT':'AWAITING NATIVE CHECK';
  githubDiscoveryDetail.textContent=receipt&&Number.isSafeInteger(receipt.started_at)?
   'Native check '+formatTime(receipt.started_at)+' · '+String(receipt.result_state).slice(0,80).replaceAll('_',' '):
   'No native GitHub discovery receipt yet. No connection inferred from configuration alone.';
 }catch{githubDiscoveryState.textContent='UNAVAILABLE';githubDiscoveryDetail.textContent='Private D1 readback unavailable';}
}
const ownerSessionLabel=byId('owner-session'),ownerStart=byId('owner-start'),ownerStop=byId('owner-stop'),ownerActionStatus=byId('owner-action-status');
const githubPatchReadiness=byId('github-patch-readiness');
let ownerActive=false,ownerConfigured=false,ownerBusy=false,ownerStartArmed=false,patchConfigured=false;
function ownerButtons(data){
 ownerStart.disabled=ownerBusy||!ownerActive||data?.enabled!==false||
   !data?.items?.some(x=>x.human_review==='passed'&&x.actual_model==='gemini-3.5-flash-lite')||
   data.items.some(x=>['queued','running','uncertain'].includes(x.state));
 ownerStop.disabled=ownerBusy||!ownerActive||data?.enabled!==true;
 byId('stop-fallback').hidden=ownerActive||data?.enabled!==true;
 byId('quick-control-note').textContent=data?.enabled===false?'Workforce is stopped.':data?.enabled===true?
  ownerActive?'Stop prevents new jobs from starting.':'To stop without an owner key, open GitHub, Run workflow, choose stop.':
  'Workforce status is unavailable.';
 if(ownerStart.disabled||!ownerStartArmed)ownerStart.textContent='Start recurring workforce';
}
let latestWorkforce=null,sourcePreview=null;
const patchPanel=byId('patch-preparation'),patchPath=byId('patch-path'),patchStart=byId('patch-start-line'),
 patchEnd=byId('patch-end-line'),patchBrief=byId('patch-brief'),patchPreviewButton=byId('patch-preview-button'),
 patchPreviewText=byId('patch-preview-text'),patchConsent=byId('patch-consent'),patchConsentLabel=byId('patch-consent-label'),
 patchTaskButton=byId('patch-task-button'),patchPreparationStatus=byId('patch-preparation-status');
let patchBusy=false;
function updatePatchButtons(){
 patchPreviewButton.disabled=patchBusy||!ownerActive||!patchConfigured||!patchPath.value;
 patchTaskButton.disabled=patchBusy||!ownerActive||!patchConfigured||!sourcePreview||!patchConsent.checked||
  latestWorkforce?.enabled!==true||!patchBrief.value.trim();
}
function clearSourcePreview(){
 sourcePreview=null;patchConsent.checked=false;patchConsentLabel.hidden=true;
 patchPreviewText.hidden=true;patchPreviewText.textContent='';updatePatchButtons();
}
for(const field of [patchPath,patchStart,patchEnd,patchBrief])field.addEventListener('input',clearSourcePreview);
patchConsent.addEventListener('change',updatePatchButtons);
patchPreviewButton.addEventListener('click',async()=>{
 if(patchBusy||!ownerActive)return;
 clearSourcePreview();patchBusy=true;updatePatchButtons();
 patchPreparationStatus.textContent='Reading pinned source; no inference…';
 try{
  const body={path:patchPath.value,start_line:Number(patchStart.value),end_line:Number(patchEnd.value)};
  const preview=await privateRequest('/api/hud/owner/patch-source',{method:'POST',body});
  if(preview.path!==body.path||preview.start_line!==body.start_line||preview.end_line!==body.end_line||
    typeof preview.snippet!=='string'||!SHA.test(preview.snippet_sha256)||
    await digest(preview.snippet)!==preview.snippet_sha256||preview.provider_called!==false||
    preview.job_created!==false||preview.github_written!==false)throw Error('source_preview_unconfirmed');
  if(patchPath.value!==body.path||Number(patchStart.value)!==body.start_line||
    Number(patchEnd.value)!==body.end_line)throw Error('source_selection_changed');
  sourcePreview=preview;patchPreviewText.textContent=preview.snippet;patchPreviewText.hidden=false;
  patchConsentLabel.hidden=false;patchPreparationStatus.textContent='Pinned '+preview.base_commit.slice(0,12)+
   ' · lines '+preview.start_line+'–'+preview.end_line+' of '+preview.total_lines+' · SHA-256 verified';
 }catch{patchPreparationStatus.textContent='Source preview unavailable or scope denied. Choose a smaller allowed excerpt.';}
 finally{patchBusy=false;updatePatchButtons();}
});
patchTaskButton.addEventListener('click',async()=>{
 if(patchTaskButton.disabled||!sourcePreview)return;
 const p=sourcePreview;patchBusy=true;updatePatchButtons();
 patchPreparationStatus.textContent='Saving exact owner-authorized source task…';
 try{
  const body={path:p.path,start_line:p.start_line,end_line:p.end_line,base_commit:p.base_commit,blob_sha:p.blob_sha,
    snippet_sha256:p.snippet_sha256,brief:patchBrief.value.trim(),confirm:'authorize_public_safe_patch_inference'};
  const saved=await privateRequest('/api/hud/owner/patch-task',{method:'POST',body});
  if(saved.state!=='queued'||!ID.test(saved.job_id)||saved.snippet_sha256!==p.snippet_sha256||
     saved.provider_called!==false||saved.github_written!==false)throw Error('patch_task_unconfirmed');
  clearSourcePreview();patchPreparationStatus.textContent='D1 CONFIRMED · queued '+saved.job_id+' · awaiting native tick.';
  await refresh(false);
 }catch{patchPreparationStatus.textContent='Task not confirmed. Preview again and inspect the queue before retrying.';clearSourcePreview();}
 finally{patchBusy=false;updatePatchButtons();}
});
async function refreshOwner(){
 ownerActive=false;ownerConfigured=false;patchConfigured=false;
 try{
  const session=await privateRequest('/api/hud/owner/session');
  ownerConfigured=session.configured===true;
  ownerActive=ownerConfigured&&session.owner_authenticated===true;
  ownerSessionLabel.textContent=ownerActive?'OWNER SESSION ACTIVE · private controls unlocked':
   ownerConfigured?'Viewing session only · sign in with owner key for decisions and controls':
   'Owner key not configured · protected GitHub fallback remains available';
  const patch=await privateRequest('/api/hud/workforce/github-patch');
  patchConfigured=patch.configured===true&&Array.isArray(patch.allowed_paths)&&patch.allowed_paths.length>0;
  const messages={
   disabled_by_owner:'GitHub draft PRs: disabled. Owner must enable ROVOR_GITHUB_PATCH_ENABLED in protected repository variables.',
   write_scope_unavailable:'GitHub draft PRs: requested, but the App lacks confirmed Contents + Pull requests write permission. The code-writing tool is locked; review and read-only discovery remain available.',
   app_credentials_missing:'GitHub draft PRs: GitHub App credentials are not configured.',
   allowlist_missing_or_invalid:'GitHub draft PRs: the owner must set an exact safe ROVOR_GITHUB_PATCH_PATHS allowlist.',
   configuration_complete_write_scope_unverified:'GitHub draft PRs: configured. Real write permissions must pass the protected deployment preflight; no live PR claimed.',
   status_unavailable:'GitHub draft PRs: private status unavailable.'
  };
  githubPatchReadiness.textContent=messages[patch.readiness]||'GitHub draft PRs: configuration has not been verified.';
  const current=patchPath.value;patchPath.textContent='';
  if(patchConfigured)for(const path of patch.allowed_paths){
   if(typeof path!=='string')continue;
   const option=make('option','',path);option.value=path;patchPath.append(option);
  }
  if([...patchPath.options].some(x=>x.value===current))patchPath.value=current;
 }catch{ownerSessionLabel.textContent='Owner session could not be verified';
  githubPatchReadiness.textContent='GitHub draft PRs: private configuration could not be verified.';}
 patchPanel.hidden=!(ownerActive&&patchConfigured);
 clearSourcePreview();ownerButtons(latestWorkforce);updatePatchButtons();
}
async function ownerControl(action){
 if(!ownerActive||ownerBusy)return;
 if(action==='start'&&!ownerStartArmed){
  ownerStartArmed=true;ownerStart.textContent='Confirm seven-day authorization';
  ownerActionStatus.textContent='Confirm to authorize future bounded triage, not an immediate inference.';
  return;
 }
 ownerBusy=true;ownerStartArmed=false;ownerButtons(latestWorkforce);
 ownerActionStatus.textContent='Saving private owner control…';
 try{
  const body=action==='start'?{action,confirm:'authorize_7_day_discovery'}:{action};
  const saved=await privateRequest('/api/hud/owner/workforce',{method:'POST',body});
  const check=await privateRequest('/api/hud/workforce/status');
  if(action==='start'&&(saved.enabled!==true||saved.recurring_authorized!==true||
     check.enabled!==true||check.recurring_execution_authorized!==true||
     check.standing_plan?.expires_at!==saved.expires_at))throw Error('owner_control_readback_mismatch');
  if(action==='stop'&&(saved.enabled!==false||check.enabled!==false||
     check.recurring_execution_authorized!==false))throw Error('owner_control_readback_mismatch');
  ownerActionStatus.textContent=action==='start'?'D1 CONFIRMED · recurring discovery authorized through '+formatTime(saved.expires_at):
   'D1 CONFIRMED · STOPPED · no new job claims';
 }catch{ownerActionStatus.textContent='Owner control not confirmed. Check current D1 state; do not assume it changed.';}
 finally{ownerBusy=false;await refresh(false);}
}
ownerStart.addEventListener('click',()=>ownerControl('start'));
ownerStop.addEventListener('click',()=>ownerControl('stop'));
const SHA=/^[a-f0-9]{64}$/;
const ID=/^[a-z0-9][a-z0-9-]{0,149}$/;
const VERDICTS=new Set(['passed','failed']);
function announce(value){state.textContent=value;}
async function privateRequest(path,{method='GET',body=null}={}){
 const headers=body===null?{}:{'Content-Type':'application/json'};
 const result=await fetch(path,{
  method,headers,credentials:'same-origin',cache:'no-store',
  ...(body===null?{}:{body:JSON.stringify(body)}),
  signal:AbortSignal.timeout(12000)
 });
 if(result.status===401)throw Error('private_login_required');
 if(result.status===403)throw Error('owner_session_required');
 if(!result.ok){
  if(result.status===409)throw Error('review_conflict_refresh_required');
  throw Error('private_request_http_'+result.status);
 }
 const value=await result.json();
 if(!value||typeof value!=='object'||Array.isArray(value))throw Error('invalid_private_json');
 return value;
}
function errorMessage(error){
 if(error.message==='owner_session_required')return 'Owner authorization required. Sign in with the separate owner key; no decision was confirmed.';
 if(error.message==='private_login_required')return 'Private sign-in required. Return to HUD and sign in; no review was changed.';
 if(error.message==='review_conflict_refresh_required')return 'Already reviewed or draft changed. Refresh private receipts before another decision.';
 return 'Private D1 could not confirm this operation. No new review is being claimed.';
}
function formatTime(value){
 if(!Number.isSafeInteger(value)||value<1)return 'Unknown';
 const date=new Date(value);return Number.isNaN(date.getTime())?'Unknown':date.toLocaleString();
}
async function digest(text){
 const bytes=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)));
 return Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
}
function safeJob(entry){
 return !!entry&&typeof entry==='object'&&ID.test(entry.id)&&
  typeof entry.title==='string'&&entry.title.length<=180&&
  typeof entry.employee==='string'&&entry.employee.length<=50&&
  ['queued','running','needs_review','failed','uncertain'].includes(entry.state)&&
  ['not_recorded','passed','failed'].includes(entry.human_review);
}
function actionButton(label,handler,extra=''){
 const b=make('button',extra,label);b.type='button';b.addEventListener('click',handler);return b;
}
// All labels are derived from the saved task kind/ID, not model claims.
// The source link is generated from the validated numeric discovery key.
function reviewContext(entry){
 const evidence=/^cloud-discovery-(run|issue|pr)-([1-9][0-9]{0,11})$/.exec(entry.task_id||'');
 if(evidence){
  const [,kind,num]=evidence;
  const title=kind==='run'?'Investigate a failed automated check':kind==='issue'?'Review a reported project issue':'Review an inactive code change';
  const why=kind==='run'?'An automated GitHub check failed. ROVOR prepared an investigation plan.':
   kind==='issue'?'GitHub recorded an open issue that may need attention. ROVOR prepared a review plan.':
   'An open pull request has been inactive. ROVOR prepared a review plan.';
  return {type:'Investigation plan',title,why,
   completed:'A saved investigation brief describing checks and recommended next steps. No code, fix, independent test run, deployment or pull request was produced by this job.',
   benefit:kind==='run'?'If the checks are specific and relevant, the plan could guide debugging and make deployments more reliable. This benefit has not been demonstrated.':
    kind==='issue'?'A useful plan could help prioritize and address a reported problem. No improvement has been demonstrated.':
    'A useful plan could help move a stuck code review forward. No change has been merged or measured.',
   concerns:'The model received a GitHub record category, number, priority and URL, not the actual code, error logs, issue text or pull request diff. It cannot verify a root cause. The problem might already be resolved.',
   decision:'Is this investigation useful enough to keep? You are not approving a fix or certifying that its suggested causes are correct.',
   next:'Keeping this saves your acceptance of the plan. No investigation, code change or publication is authorized by this decision.',
   url:'https://github.com/TeamRovor/rovor-video-engine/'+(kind==='run'?'actions/runs/':kind==='issue'?'issues/':'pull/')+num,
   evidenceKey:kind+'-'+num,evidenceLabel:(kind==='run'?'GitHub check ':kind==='issue'?'GitHub issue #':'Pull request #')+num,
   criteria:'Keep a plan that gives a sensible next action and is clear about what is still unknown. Reject generic advice, invented findings or work that no longer matters.'};
 }
 if(entry.id.startsWith('gc-patch-src-'))return {type:'Proposed code change',title:entry.title,
  why:'You approved a small source excerpt for the employee to propose an improvement.',
  completed:'A saved proposed replacement for one owner-selected code excerpt. No code was changed and no independent test or pull request was produced by this inference.',
  benefit:'If the proposed replacement is correct, it could improve the selected file. No performance, security or reliability improvement has been demonstrated.',
  concerns:'The model saw only a small excerpt, not the full application. The proposal may break surrounding code or introduce regressions and requires separate technical tests and approval.',
  decision:'Is the proposed change worth retaining for technical review? Do not keep it just because it has a verified receipt.',
  next:'Keeping the proposal does not change GitHub. Draft pull-request creation needs a separate owner authorization; a merge is not authorized.',
  criteria:'Reject if the proposal does not address your requested improvement. If the code is unclear, review later and ask for a technical explanation.'};
 const names={plan:'Work plan',checklist:'Checklist',research:'Research draft',code_review:'Engineering draft'};
 return {type:names[entry.kind]||'Employee draft',title:entry.title,
  why:'ROVOR completed the requested written task for your review.',
  completed:'A saved written draft for this task. External execution, implementation, publication and actual results have not been verified.',
  benefit:'If the draft is accurate and useful, it could help the team take the next step. No business impact has been demonstrated.',
  concerns:'The model-generated text may be incomplete, inaccurate, generic or outdated. Its claims and recommendations have not been independently validated.',
  decision:'Would you keep this result and use it for the task described?',
  next:'Keeping the draft records your approval of its usefulness. It does not publish it, execute a tool or start another model.',
  criteria:'Keep if it answers the request and is specific enough to use. Reject inaccurate, incomplete or irrelevant work.'};
}
// Explain verified job scope independently of model assertions. Do not
// infer a fix, return on investment, saved time or completed deployment.
function ownerFact(panel,label,value,kind=''){
 const item=make('section','owner-fact '+kind);
 item.append(make('h4','',label),make('p','',value));
 panel.append(item);
}
function ownerBrief(entry,context){
 const panel=make('section','owner-brief');
 panel.setAttribute('aria-label','What ROVOR did and why this review matters');
 panel.append(make('p','owner-brief-heading','YOUR REVIEW BRIEF · Based on the recorded job, not AI claims'));
 ownerFact(panel,'1. What ROVOR investigated',context.why);
 ownerFact(panel,'2. What it actually produced',context.completed);
 ownerFact(panel,'3. How it might benefit ROVOR',context.benefit,'benefit');
 ownerFact(panel,'4. Concerns and missing proof',context.concerns,'concern');
 ownerFact(panel,'5. What your PASS will do',context.next);
 return panel;
}
// Independent current source read, not an AI claim.
const evidenceMessages=Object.freeze({
 check_passed_now:'This original check now passes. The earlier failure may no longer need investigation.',
 newer_check_passed:'A newer run of the same automated check passed. The original problem may already be addressed; this does not prove its root cause was fixed.',
 check_failed:'The original check still records a failure. No later successful run was verified.',
 newer_check_failed:'A newer run of the same automated check failed too. This may still need attention.',
 check_in_progress:'GitHub reports the original check is in progress. Its outcome is not known yet.',
 check_other_outcome:'The check has a different outcome now. A successful fix is not verified.',
 issue_closed:'GitHub now reports this issue closed. It may no longer need attention.',
 issue_assigned:'This issue now has an assignee. Avoid duplicating someone else’s work.',
 issue_open:'GitHub still lists this issue as open.',
 pull_merged:'GitHub reports this pull request merged. This review may be obsolete.',
 pull_closed:'GitHub reports this pull request closed. This review may no longer be useful.',
 pull_open:'GitHub still lists this pull request as open.',
 checking:'Checking the current GitHub record…',
 unavailable:'Could not verify the latest GitHub state. Do not assume this problem is fixed or still active.',
 not_configured:'Independent GitHub evidence is not available.'
});
async function displayEvidence(entry,context,card,generation){
 if(!context.evidenceKey)return;
 const panel=make('div','source-status');
 panel.append(make('strong','','Current GitHub status'));
 const detail=make('p','','Checking whether this work is still relevant…');panel.append(detail);
 card.append(panel);
 try{
  const data=await privateRequest('/api/hud/workforce/evidence/'+encodeURIComponent(entry.id));
  if(generation!==refreshGeneration||!card.isConnected)return;
  if(data.source!=='rovor_private_review_evidence'||data.job_id!==entry.id||data.source_key!==context.evidenceKey||
    !Object.hasOwn(evidenceMessages,data.state)||data.model_called!==false||data.github_written!==false)
   throw Error('invalid_evidence');
  if(typeof data.title==='string'&&data.title&&data.title.length<=140)panel.querySelector('strong').textContent=data.title+' · Current GitHub status';
  detail.textContent=evidenceMessages[data.state];panel.dataset.evidenceState=data.state;
  if(['newer_check_passed','check_passed_now','issue_closed','pull_merged','pull_closed'].includes(data.state)){
   panel.append(make('p','source-decision-note','Potentially outdated: the original work may no longer need action. Review the current GitHub record before keeping this plan.'));
  }else panel.append(make('p','source-decision-note','This GitHub status is evidence of the record, not proof that the employee diagnosis or recommendation is correct.'));
  if(Number.isSafeInteger(data.related_id)&&data.related_id>0&&['newer_check_passed','newer_check_failed'].includes(data.state)){
   const link=make('a','','View newer check');link.href='https://github.com/TeamRovor/rovor-video-engine/actions/runs/'+data.related_id;
   link.target='_blank';link.rel='noreferrer';panel.append(link);
  }
  if(Number.isSafeInteger(data.finished_at)&&data.finished_at>0)panel.append(make('small','','Checked '+formatTime(data.finished_at)));
 }catch{if(generation===refreshGeneration&&card.isConnected)detail.textContent=evidenceMessages.unavailable;}
}
// Plain text only. No generated HTML, links or script execution. Preserve
// the full exact receipt, even when a future employee provides a short summary.
function renderOutput(output){
 const content=make('div','draft-output');
 let list=null;
 for(const line of output.split(/\r?\n/)){
  const clean=line.trim();
  const heading=/^#{1,4}\s+(.+)$/.exec(clean);
  const bullet=/^[-*]\s+(.+)$/.exec(clean);
  if(heading){list=null;content.append(make('h4','',heading[1]));}
  else if(bullet){if(!list){list=make('ul');content.append(list);}list.append(make('li','',bullet[1]));}
  else{list=null;content.append(make('p','',line||' '));}
 }
 return content;
}
function modelSections(output){
 // These are excerpts of an AI-written report, not verified facts. Support
 // earlier four-section drafts without attempting to invent missing sections.
 const current=['Task and available evidence','Deliverable created','Potential benefit',
  'Concerns and uncertainties','Recommended next step'];
 const earlier=['Bottom line','What was done','What is still unknown','Recommended next step'];
 const aliases=new Map([...current,...earlier].map(v=>[v.toLowerCase(),v]));
 const parsed=Object.create(null);let active=null;
 for(const line of output.split(/\r?\n/)){
  const match=/^#{1,4}\s+(.+?)\s*$/.exec(line.trim());
  if(match){
   active=aliases.get(match[1].toLowerCase())||null;
   if(active){if(Object.hasOwn(parsed,active))return null;parsed[active]='';}
  }else if(active)parsed[active]+=(parsed[active]?'\n':'')+line;
 }
 const group=[current,earlier].find(names=>names.every(k=>typeof parsed[k]==='string'&&
  parsed[k].trim().length>0&&parsed[k].length<=1800));
 return group?group.map(label=>({label,content:parsed[label].trim()})):null;
}
// The review brief is verified job metadata; these are literal excerpts
// supplied by the employee. Never present unverified model claims as fact.
function reportClaims(sections){
 const panel=make('section','report-claims');
 panel.setAttribute('aria-label','Employee proposed value, limitations and next steps');
 panel.append(make('p','report-claims-heading','FROM THE EMPLOYEE REPORT · NOT INDEPENDENTLY VERIFIED'));
 const lookup=new Map((sections||[]).map(({label,content})=>[label,content]));
 const current=lookup.has('Deliverable created');
 const fields=[
  ['Employee says it produced',current?lookup.get('Deliverable created'):lookup.get('What was done'),
    'No concrete deliverable was separately described.'],
  ['Specific benefit claimed',lookup.get('Potential benefit'),
    'No specific benefit was provided. The saved report does not establish business value.'],
  ['Risks or unknowns reported',current?lookup.get('Concerns and uncertainties'):lookup.get('What is still unknown'),
    'The employee did not provide a distinct concerns section. Missing risk discussion is itself a reason to review carefully.'],
  ['Employee suggests doing next',lookup.get('Recommended next step'),
    'The employee did not identify a specific next action.']
 ];
 for(const [label,content,missing] of fields){
  const section=make('div','report-claim'+(content?'':' missing'));
  section.append(make('h5','',label),make('p','',content||missing));
  panel.append(section);
 }
 if(!sections){
  panel.append(make('p','missing-report-warning','This result lacks a complete structured report. Its deliverable, potential benefit or concerns may be unclear. Review the original text before approving.'));
 }
 return panel;
}
function receiptDetails(entry,hash=null){
 const details=make('details','receipt-details');
 details.append(make('summary','',hash?'Technical details (receipt verified)':'Technical details'));
 details.append(make('p','metadata','Employee: '+entry.employee+' · model: '+(entry.actual_model||'Not confirmed')));
 details.append(make('p','metadata','Requested '+formatTime(entry.created_at)+' · completed '+formatTime(entry.finished_at)));
 const exact=entry.provider==='google-gemini-cloud'&&validTokens(entry.tokens_input)&&validTokens(entry.tokens_output);
 details.append(make('p','metadata',exact?'Exact provider usage: '+entry.tokens_input.toLocaleString()+' input · '+entry.tokens_output.toLocaleString()+' output tokens':'Exact job token usage: not recorded'));
 details.append(make('p','metadata','Immutable job ID: '+entry.id));
 if(entry.error_code)details.append(make('p','metadata','Execution outcome: '+entry.error_code));
 if(hash)details.append(make('p','digest','SHA-256 VERIFIED · '+hash));
 else if(SHA.test(entry.output_sha256||''))details.append(make('p','digest','Saved output receipt: '+entry.output_sha256));
 return details;
}
async function loadExactDraft(entry,expectedReview){
 const draft=await privateRequest('/api/hud/workforce/draft/'+encodeURIComponent(entry.id));
 if(draft.id!==entry.id||draft.state!=='needs_review'||draft.human_review!==expectedReview||
    typeof draft.output!=='string'||!draft.output.trim()||draft.output.length>30000||
    draft.output_sha256!==entry.output_sha256||!SHA.test(draft.output_sha256))throw Error('invalid_draft_receipt');
 const hash=await digest(draft.output);
 if(hash!==entry.output_sha256)throw Error('private_digest_mismatch');
 return {draft,hash};
}
async function inspect(entry,card,inspectButton,generation=refreshGeneration){
 inspectButton.disabled=true;inspectButton.textContent='Checking the saved work…';
 try{
  const {draft,hash}=await loadExactDraft(entry,entry.human_review);
  if(generation!==refreshGeneration||!card.isConnected)return;
  const oldWarning=card.querySelector('.draft-load-error');if(oldWarning)oldWarning.remove();
  const context=reviewContext(entry),box=make('section','draft');
  box.append(make('h4','','What '+entry.employee+' delivered'));
  box.append(make('p','employee-report-caution','This is the employee’s exact AI-generated report. Its proposed benefits, diagnoses and conclusions have not been independently verified.'));
  const sections=modelSections(draft.output);
  box.append(reportClaims(sections));
  if(sections){
   const summary=make('div','draft-summary');
   for(const {label,content} of sections){
    const p=make('p');p.append(make('strong','',label),document.createTextNode(content));summary.append(p);
   }
   box.append(summary);
   const full=make('details','draft-full');
   full.append(make('summary','','Read the complete employee report'),renderOutput(draft.output));box.append(full);
  }else box.append(renderOutput(draft.output));
  card.querySelector(':scope > .receipt-details')?.remove();
  box.append(receiptDetails(entry,hash));
  const choices=make('div','actions'),feedback=make('p','review-feedback');
  feedback.setAttribute('role','status');feedback.setAttribute('aria-live','polite');
  const copy=actionButton('Copy full result',async()=>{
   try{await navigator.clipboard.writeText(draft.output);copy.textContent='Copied';}
   catch{copy.textContent='Copy unavailable';}
  });
  const awaiting=entry.human_review==='not_recorded';
  if(awaiting){
   box.append(make('div','review-note',context.criteria+' '+context.next));
   let armedVerdict=null,submitting=false;
   const decisionButtons=[];
   const resetDecision=()=>{
    armedVerdict=null;
    for(const {button,label} of decisionButtons)button.textContent=label;
   };
   for(const verdict of ['passed','failed']){
    const human=verdict==='passed'?'PASS':'FAIL';
    const label=verdict==='passed'?'Keep this work (PASS)':'Reject this work (FAIL)';
    const button=actionButton(label,async()=>{
     if(submitting)return;
     if(armedVerdict!==verdict){
      resetDecision();armedVerdict=verdict;button.textContent='Confirm '+human+' decision';
      feedback.textContent=(verdict==='passed'?'Keep this exact result. ':'Reject this exact result. ')+'Your decision is permanent. Confirm or choose Review later.';
      return;
     }
     submitting=true;
     for(const control of choices.querySelectorAll('button'))control.disabled=true;
     feedback.textContent='Saving your decision…';
     try{
      const saved=await privateRequest('/api/hud/workforce/review',{
       method:'POST',body:{job_id:entry.id,verdict,output_sha256:hash}
      });
      if(saved.id!==entry.id||saved.human_review!==verdict||saved.output_sha256!==hash)
       throw Error('private_review_readback_mismatch');
      const check=await privateRequest('/api/hud/workforce/draft/'+encodeURIComponent(entry.id));
      if(check.human_review!==verdict||check.output_sha256!==hash)
       throw Error('private_review_readback_mismatch');
      deferred.delete(entry.id);
      announce(verdict==='passed'?'Work kept. Your PASS is saved. Nothing was published or executed.':'Work rejected. Your FAIL is saved. No retry was started.');
      await refresh(false);
     }catch(error){
      feedback.textContent=errorMessage(error);submitting=false;resetDecision();
      for(const control of choices.querySelectorAll('button'))control.disabled=false;
     }
    },verdict==='passed'?'approve':'reject');
    decisionButtons.push({button,label});choices.append(button);
   }
   const later=actionButton('Review later',()=>{
    if(submitting)return;
    resetDecision();deferred.add(entry.id);card.dataset.deferred='true';
    feedback.textContent='Left undecided. This work stays in your inbox. No PASS or FAIL was recorded.';
    choices.hidden=true;
    const resume=actionButton('Resume review',()=>{
     deferred.delete(entry.id);delete card.dataset.deferred;choices.hidden=false;resume.remove();feedback.textContent='';
     decisionButtons[0].button.focus();
    },'defer');
    box.append(resume);resume.focus();
   },'defer');
   choices.append(later,copy);
   if(deferred.has(entry.id)){
    card.dataset.deferred='true';choices.hidden=true;
    const resume=actionButton('Resume review',()=>{
     deferred.delete(entry.id);delete card.dataset.deferred;choices.hidden=false;resume.remove();feedback.textContent='';
     decisionButtons[0].button.focus();
    },'defer');
    box.append(resume);
    feedback.textContent='Left undecided. No PASS or FAIL recorded.';
   }
  }else choices.append(copy);
  box.append(choices,feedback);card.append(box);inspectButton.remove();
 }catch(error){
  if(generation!==refreshGeneration||!card.isConnected)return;
  inspectButton.disabled=false;inspectButton.textContent='Retry loading work';
  const warning=make('p','review-feedback',errorMessage(error));warning.setAttribute('role','status');
  const previous=card.querySelector('.draft-load-error');if(previous)previous.remove();
  warning.classList.add('draft-load-error');card.append(warning);
 }
}
async function refresh(clearNotice=true){
 const generation=++refreshGeneration;
 refreshButton.disabled=true;
 if(clearNotice)announce('');
 message.textContent='Loading your review inbox…';
 try{
  const data=await privateRequest('/api/hud/workforce/status');
  if(generation!==refreshGeneration)return;
  if(data.source!=='existing_cloudflare_hud_gemini_workforce'||data.mac_required!==false||
     !Array.isArray(data.items)||data.items.length>50||
     typeof data.enabled!=='boolean'||data.site_review_ledger_synced!==false||
     data.items.some(entry=>!safeJob(entry)||Object.hasOwn(entry,'output')||Object.hasOwn(entry,'prompt')))
   throw Error('invalid_workforce_readback');
  latestWorkforce=data;
  await Promise.all([refreshOwner(),refreshNativeDiscovery()]);
  if(generation!==refreshGeneration)return;
  const rows=data.items;
  const pendingCount=rows.filter(x=>x.state==='needs_review'&&x.human_review==='not_recorded').length;
  const reviewedCount=rows.filter(x=>VERDICTS.has(x.human_review)).length;
  pending.textContent=String(pendingCount);
  reviewed.textContent=String(reviewedCount);
  stop.textContent=data.enabled?'ENABLED':'STOPPED';
  stop.title=data.enabled?'New job claims permitted by STOP only (all provider and review gates still apply)':
   'New model job claims stopped; saved drafts remain available for review';
  const tick=data.native_schedule?.source==='cloudflare_scheduled_event'?data.native_schedule.last_tick:null;
  const validTick=tick&&Number.isSafeInteger(tick.scheduled_at)&&tick.scheduled_at>0&&
    typeof tick.result_state==='string'&&/^[a-z0-9_]{1,80}$/.test(tick.result_state);
  nativeClock.textContent=validTick?tick.result_state.replaceAll('_',' ').toUpperCase():'NO RECEIPT';
  nativeDetail.textContent=validTick?'Native event '+formatTime(tick.scheduled_at)+
   (tick.inference_completed===1?' · completed job':' · no completed inference'):'No native cron receipt recorded';
  standing.textContent=data.recurring_execution_authorized===true?'ARMED':'NOT ARMED';
  standing.title=data.recurring_execution_authorized===true?'Expires '+formatTime(data.standing_plan?.expires_at):
   'Recurring execution requires a reviewed PASS and standing owner authorization';
  const max=data.standing_plan?.max_pending_reviews;
  guidance.textContent=Number.isSafeInteger(max)&&max>0&&pendingCount>=max?
   'Your review queue is full. ROVOR pauses new recurring jobs until you review a result. You can leave any uncertain result undecided.':
   pendingCount>0?'Read the result and decide whether it is useful. Your decision does not run code or publish anything.':
   'You have no outstanding decisions. New work will appear here as it is completed.';
  guidance.textContent+=' '+admissionGuidance(data.admission);
  jobs.textContent='';history.textContent='';
  const pendingLoads=[],evidenceLoads=[];
  const ordered=rows.slice().sort((a,b)=>{
   const ap=a.state==='needs_review'&&a.human_review==='not_recorded'?1:0;
   const bp=b.state==='needs_review'&&b.human_review==='not_recorded'?1:0;
   return bp-ap||((b.created_at||0)-(a.created_at||0));
  });
  if(!pendingCount)jobs.append(make('div','job','You’re all caught up. No work needs a decision right now.'));
  if(!rows.some(x=>!(x.state==='needs_review'&&x.human_review==='not_recorded')))
   history.append(make('p','history-summary','No past reviews or other jobs yet.'));
  for(const entry of ordered){
   const card=make('article','job');
   const header=make('div','job-header');
   const heading=make('div'),context=reviewContext(entry);
   const awaiting=entry.state==='needs_review'&&entry.human_review==='not_recorded';
   heading.append(make('p','task-type',context.type+' · '+entry.employee));
   heading.append(make('h3','',context.title));
   if(context.evidenceLabel){
    const link=make('a','metadata',context.evidenceLabel);link.href=context.url;link.rel='noreferrer';link.target='_blank';heading.append(link);
   }
   const humanState=awaiting?'NEEDS DECISION':entry.human_review==='passed'?'KEPT · PASS':
    entry.human_review==='failed'?'REJECTED · FAIL':entry.state==='running'?'IN PROGRESS':
    entry.state==='queued'?'WAITING TO START':entry.state==='uncertain'?'NEEDS TECHNICAL CHECK':'NOT COMPLETED';
   const tag=make('span','state '+(awaiting?'wait':VERDICTS.has(entry.human_review)?'ok':''),humanState);
   header.append(heading,tag);card.append(header);
   if(awaiting){
    card.append(ownerBrief(entry,context));
    card.append(make('div','review-note','Your decision: '+context.decision));
    if(context.evidenceKey)evidenceLoads.push(()=>displayEvidence(entry,context,card,generation));
   }
   if(entry.state==='needs_review'&&SHA.test(entry.output_sha256||'')){
    const actions=make('div','actions');
    const inspectButton=actionButton(awaiting?'Load saved work':'View saved result',()=>inspect(entry,card,inspectButton,generation));
    actions.append(inspectButton);card.append(actions);
    if(awaiting)pendingLoads.push(()=>inspect(entry,card,inspectButton,generation));
    if(!awaiting)card.append(receiptDetails(entry));
    if(!awaiting&&ownerActive&&patchConfigured&&entry.human_review==='passed'&&entry.kind==='code_review'&&entry.id.startsWith('gc-patch-src-')){
     const actions=make('div','actions');
     const open=actionButton('Inspect reviewed patch',async()=>{
      open.disabled=true;
      try{
       const saved=await privateRequest('/api/hud/workforce/draft/'+encodeURIComponent(entry.id));
       if(saved.human_review!=='passed'||saved.output_sha256!==entry.output_sha256||
          typeof saved.output!=='string'||await digest(saved.output)!==entry.output_sha256)
        throw Error('private_digest_mismatch');
       const proposal=JSON.parse(saved.output);
       if(proposal.version!==1||!proposal.change||typeof proposal.change.path!=='string')
        throw Error('not_patch_proposal');
       const panel=make('section','draft');
       panel.append(make('h4','','EXACT REVIEWED PATCH · '+proposal.change.path));
       panel.append(make('pre','',saved.output));
       let armed=false;
       const authorize=actionButton('Authorize draft pull request',async()=>{
        if(!armed){armed=true;authorize.textContent='Confirm draft PR authorization';return;}
        authorize.disabled=true;
        try{
         const out=await privateRequest('/api/hud/owner/github-patch',{method:'POST',
          body:{job_id:entry.id,output_sha256:entry.output_sha256,confirm:'authorize_draft_pr'}});
         if(out.job_id!==entry.id||out.state!=='queued')throw Error('patch_queue_unconfirmed');
         announce('D1 CONFIRMED · reviewed patch queued for a native tick. No pull request has been opened yet.');
         authorize.textContent='Queued';
        }catch{announce('Patch queue not confirmed. Check the private receipt before authorizing again.');}
       },'approve');
       panel.append(authorize);card.append(panel);open.remove();
      }catch{announce('This accepted draft is not a valid reviewed patch proposal, or its exact receipt could not be verified.');open.disabled=false;}
     });
     actions.append(open);card.append(actions);
    }
   }else card.append(receiptDetails(entry));
   (awaiting?jobs:history).append(card);
  }
  // At most the three pending recurring drafts are loaded automatically;
  // manual review remains available for any additional historical job.
  for(const load of evidenceLoads.slice(0,3))void load();
  await Promise.all(pendingLoads.slice(0,3).map(load=>load()));
  if(generation!==refreshGeneration)return;
  message.textContent=pendingCount===1?'1 result needs your decision':pendingCount+' results need your decision';
 }catch(error){
  if(generation!==refreshGeneration)return;
  message.textContent=errorMessage(error);
  pending.textContent='?';reviewed.textContent='?';stop.textContent='?';
  nativeClock.textContent='?';nativeDetail.textContent='Readback unavailable';standing.textContent='?';githubDiscoveryState.textContent='?';githubDiscoveryDetail.textContent='Readback unavailable';
  jobs.textContent='';history.textContent='';guidance.textContent='Could not load the inbox. Try Refresh inbox.';latestWorkforce=null;ownerActive=false;ownerButtons(null);patchPanel.hidden=true;clearSourcePreview();
 }finally{if(generation===refreshGeneration)refreshButton.disabled=false;}
}
refreshButton.addEventListener('click',()=>refresh());
refresh();
})();

