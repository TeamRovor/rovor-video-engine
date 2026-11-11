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
const jobs=byId('jobs'),message=byId('message'),state=byId('page-status');
const pending=byId('pending'),reviewed=byId('reviewed'),stop=byId('stop-state');
const refreshButton=byId('refresh');
const nativeClock=byId('native-clock'),nativeDetail=byId('native-detail'),standing=byId('standing-state');
const validTokens=n=>Number.isSafeInteger(n)&&n>=0;
const githubDiscoveryState=byId('github-discovery-state'),githubDiscoveryDetail=byId('github-discovery-detail');
async function refreshNativeDiscovery(){
 try{
  const data=await privateRequest('/api/hud/workforce/native-discovery');
  if(data.source!=='rovor_native_github_discovery'||typeof data.configured!=='boolean'||
     typeof data.enabled!=='boolean'||data.mac_required!==false||data.chatgpt_required!==false||
     data.github_actions_required!==false||data.storage_unavailable)throw Error('native_discovery_unavailable');
  const receipt=data.last_check;
  const verified=receipt&&['no_new_evidence_backed_work','owner_review_draft_queued'].includes(receipt.result_state)&&
   Number.isSafeInteger(receipt.finished_at)&&receipt.finished_at>0;
  const fresh=verified&&Date.now()-receipt.finished_at<7200000&&Date.now()>=receipt.finished_at;
  githubDiscoveryState.textContent=!data.configured?'NOT CONFIGURED':!data.enabled?'DISABLED':
   fresh?'READ VERIFIED':receipt?.result_state==='github_read_unavailable'?'READ FAILED':
   verified?'STALE RECEIPT':'AWAITING NATIVE CHECK';
  githubDiscoveryDetail.textContent=receipt&&Number.isSafeInteger(receipt.started_at)?
   'Native check '+formatTime(receipt.started_at)+' · '+String(receipt.result_state).slice(0,80).replaceAll('_',' '):
   'No native GitHub discovery receipt yet. No connection inferred from configuration alone.';
 }catch{githubDiscoveryState.textContent='UNAVAILABLE';githubDiscoveryDetail.textContent='Private D1 readback unavailable';}
}
const ownerSessionLabel=byId('owner-session'),ownerStart=byId('owner-start'),ownerStop=byId('owner-stop'),ownerActionStatus=byId('owner-action-status');
let ownerActive=false,ownerConfigured=false,ownerBusy=false,ownerStartArmed=false,patchConfigured=false;
function ownerButtons(data){
 ownerStart.disabled=ownerBusy||!ownerActive||data?.enabled!==false||
   !data?.items?.some(x=>x.human_review==='passed'&&x.actual_model==='gemini-3.5-flash-lite')||
   data.items.some(x=>['queued','running','uncertain'].includes(x.state));
 ownerStop.disabled=ownerBusy||!ownerActive||data?.enabled!==true;
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
  const current=patchPath.value;patchPath.textContent='';
  if(patchConfigured)for(const path of patch.allowed_paths){
   if(typeof path!=='string')continue;
   const option=make('option','',path);option.value=path;patchPath.append(option);
  }
  if([...patchPath.options].some(x=>x.value===current))patchPath.value=current;
 }catch{ownerSessionLabel.textContent='Owner session could not be verified';}
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
async function inspect(entry,card,inspectButton){
 inspectButton.disabled=true;inspectButton.textContent='Verifying private draft…';
 try{
  const draft=await privateRequest('/api/hud/workforce/draft/'+encodeURIComponent(entry.id));
  if(draft.id!==entry.id||draft.state!=='needs_review'||
     draft.human_review!=='not_recorded'||typeof draft.output!=='string'||
     !draft.output.trim()||draft.output.length>30000||
     draft.output_sha256!==entry.output_sha256||!SHA.test(draft.output_sha256))
   throw Error('invalid_draft_receipt');
  const hash=await digest(draft.output);
  if(hash!==entry.output_sha256)throw Error('private_digest_mismatch');
  const box=make('section','draft');
  box.append(make('h4','', 'VERIFIED PRIVATE DRAFT · '+entry.employee));
  const content=make('pre','',draft.output);
  box.append(content);
  box.append(make('div','digest','SHA-256 VERIFIED · '+hash));
  const choices=make('div','actions');
  const copy=actionButton('Copy draft',async()=>{
   try{await navigator.clipboard.writeText(draft.output);copy.textContent='Copied';}
   catch{copy.textContent='Copy unavailable';}
  });
  choices.append(copy);
  for(const verdict of ['passed','failed']){
   let armed=false,submitting=false;
   const human=verdict==='passed'?'PASS':'FAIL';
   const button=actionButton('Record '+human,async()=>{
    if(submitting)return;
    if(!armed){
     armed=true;
     button.textContent='Confirm '+human+' decision';
     announce('Confirm '+human+' on this exact verified draft. This decision is permanent.');
     return;
    }
    submitting=true;
    for(const control of choices.querySelectorAll('button'))control.disabled=true;
    announce('Saving your '+human+' decision to the existing private D1 ledger…');
    try{
     const saved=await privateRequest('/api/hud/workforce/review',{
      method:'POST',body:{job_id:entry.id,verdict,output_sha256:hash}
     });
     if(saved.id!==entry.id||saved.human_review!==verdict||saved.output_sha256!==hash)
      throw Error('private_review_readback_mismatch');
     // Re-read the authoritative D1 row, not just the HTTP 200 response.
     const check=await privateRequest('/api/hud/workforce/draft/'+encodeURIComponent(entry.id));
     if(check.human_review!==verdict||check.output_sha256!==hash)
      throw Error('private_review_readback_mismatch');
     announce('D1 CONFIRMED · '+entry.employee+' '+human+' saved · '+entry.id+
      '. No second model call or publication occurred.');
     await refresh(false);
    }catch(error){
     announce(errorMessage(error));
     submitting=false;armed=false;
     button.textContent='Record '+human;
     for(const control of choices.querySelectorAll('button'))control.disabled=false;
    }
   },verdict==='passed'?'approve':'reject');
   choices.append(button);
  }
  box.append(choices);card.append(box);
  inspectButton.remove();
  announce('Private model output and SHA-256 verified. Review the entire draft before deciding.');
 }catch(error){
  inspectButton.disabled=false;inspectButton.textContent='Retry private draft inspection';
  announce(errorMessage(error));
 }
}
async function refresh(clearNotice=true){
 refreshButton.disabled=true;
 if(clearNotice)announce('');
 message.textContent='Checking actual private D1 receipts…';
 try{
  const data=await privateRequest('/api/hud/workforce/status');
  if(data.source!=='existing_cloudflare_hud_gemini_workforce'||data.mac_required!==false||
     !Array.isArray(data.items)||data.items.length>50||
     typeof data.enabled!=='boolean'||data.site_review_ledger_synced!==false||
     data.items.some(entry=>!safeJob(entry)||Object.hasOwn(entry,'output')||Object.hasOwn(entry,'prompt')))
   throw Error('invalid_workforce_readback');
  latestWorkforce=data;
  await Promise.all([refreshOwner(),refreshNativeDiscovery()]);
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
  jobs.textContent='';
  const ordered=rows.slice().sort((a,b)=>{
   const ap=a.state==='needs_review'&&a.human_review==='not_recorded'?1:0;
   const bp=b.state==='needs_review'&&b.human_review==='not_recorded'?1:0;
   return bp-ap||((b.created_at||0)-(a.created_at||0));
  });
  if(!rows.length){
   jobs.append(make('div','job','No jobs recorded in this private Cloudflare D1 ledger yet.'));
  }
  for(const entry of ordered){
   const card=make('article','job');
   const header=make('div','job-header');
   const heading=make('div');
   heading.append(make('h3','',entry.employee+' · '+entry.title));
   heading.append(make('p','metadata','Requested at '+formatTime(entry.created_at)+
    ' · completed '+formatTime(entry.finished_at)));
   heading.append(make('p','metadata','Actual model: '+(entry.actual_model||'Not confirmed')));
   const exact=entry.provider==='google-gemini-cloud'&&validTokens(entry.tokens_input)&&validTokens(entry.tokens_output);
   heading.append(make('p','metadata',exact?
    'Exact provider usage: '+entry.tokens_input.toLocaleString()+' input · '+entry.tokens_output.toLocaleString()+' output tokens':
    'Exact job token usage: not recorded'));
   const awaiting=entry.state==='needs_review'&&entry.human_review==='not_recorded';
   const tag=make('span','state '+(awaiting?'wait':VERDICTS.has(entry.human_review)?'ok':''),
    awaiting?'AWAITING YOUR REVIEW':VERDICTS.has(entry.human_review)?
    'OWNER '+entry.human_review.toUpperCase():entry.state.toUpperCase());
   header.append(heading,tag);card.append(header);
   card.append(make('p','metadata','Immutable job ID: '+entry.id));
   if(entry.error_code)card.append(make('p','metadata','Execution outcome: '+entry.error_code));
   if(entry.state==='needs_review'&&SHA.test(entry.output_sha256||'')){
    card.append(make('p','digest','Private output receipt: '+entry.output_sha256));
    if(awaiting){
     const actions=make('div','actions');
     const inspectButton=actionButton('Open full draft and verify SHA-256',
      ()=>inspect(entry,card,inspectButton));
     actions.append(inspectButton);card.append(actions);
    }else if(ownerActive&&patchConfigured&&entry.human_review==='passed'&&entry.kind==='code_review'){
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
   }
   jobs.append(card);
  }
  message.textContent='D1 readback confirmed · '+pendingCount+' awaiting owner review · '+
   reviewedCount+' reviewed · cloud dispatch '+(data.enabled?'ENABLED':'STOPPED')+
   '. Models are not assumed online merely from their saved receipts.';
 }catch(error){
  message.textContent=errorMessage(error);
  pending.textContent='?';reviewed.textContent='?';stop.textContent='?';
  nativeClock.textContent='?';nativeDetail.textContent='Readback unavailable';standing.textContent='?';githubDiscoveryState.textContent='?';githubDiscoveryDetail.textContent='Readback unavailable';
  jobs.textContent='';latestWorkforce=null;ownerActive=false;ownerButtons(null);patchPanel.hidden=true;clearSourcePreview();
 }finally{refreshButton.disabled=false;}
}
refreshButton.addEventListener('click',()=>refresh());
refresh();
})();
