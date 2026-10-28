/* ROVOR Digital: truthful per-provider quota instruments in the EXISTING HUD drawer.
 * No model calls, worker mutations, invented limits, or guessed reset times.
 */
window.ROVOR_QUOTA_BOARD=(()=>{
'use strict';
const expandedSlots=new Set();
const expandedProviders=new Set();
let overviewFilter='all'; // Retain user choice while telemetry refreshes.
// Keep UI inspection state independent of whichever legacy module redraws the popup.
function listenForQuotaInteraction(){
 if(typeof document.addEventListener!=='function')return;
 // Disclosures survive the existing 10-second read-only refresh.
 document.addEventListener('click',event=>{
   const summary=event.target?.closest?.('summary');
   if(!summary)return;
   const section=summary.parentElement;
   const key=section?.closest?.('[data-rvq-slot]')?.getAttribute('data-rvq-slot');
   if(!key)return;
   const set=section.classList.contains('rvq-provider-details')?expandedProviders:
     section.classList.contains('rvq-more')?expandedSlots:null;
   if(!set)return;
   if(section.open)set.delete(key);else set.add(key);
 },true);
 document.addEventListener('click',event=>{
   const tile=event.target?.closest?.('a[data-rvq-open-slot]');
   const board=tile?.closest?.('.rvq-board');
   if(!board)return;
   event.preventDefault();
   const key=tile.getAttribute('data-rvq-open-slot');
   const provider=[...board.querySelectorAll('[data-rvq-slot]')].find(
     card=>card.getAttribute('data-rvq-slot')===key);
   const detail=provider?.querySelector('.rvq-provider-details');
   if(!detail)return;
   detail.open=true;
   expandedProviders.add(key);
   detail.querySelector('summary')?.focus({preventScroll:true});
   provider.scrollIntoView?.({block:'start',behavior:'auto'});
 });
 // Filtering never alters the order or availability of full provider reports.
 document.addEventListener('click',event=>{
   const button=event.target?.closest?.('button[data-rvq-filter]');
   const board=button?.closest?.('.rvq-board');
   if(!board)return;
   overviewFilter=button.getAttribute('data-rvq-filter')==='attention'?'attention':'all';
   const tiles=[...board.querySelectorAll('.rvq-overview-tile')];
   let visible=0;
   for(const tile of tiles){
     tile.hidden=overviewFilter==='attention'&&tile.getAttribute('data-rvq-attention')!=='true';
     if(!tile.hidden)visible++;
   }
   for(const b of board.querySelectorAll('button[data-rvq-filter]'))
     b.setAttribute('aria-pressed',String(b.getAttribute('data-rvq-filter')===overviewFilter));
   const note=board.querySelector('.rvq-filter-note');
   if(note)note.textContent=overviewFilter==='attention'
      ?'Showing '+visible+' connections with setup or human-review gates'
      :'Showing all '+tiles.length+' configured connections';
 });
 // Navigate only the current HUD drawer; avoid modifying the private Site URL.
 document.addEventListener('click',event=>{
   const link=event.target?.closest?.('.rvq-jump-nav a');
   const board=link?.closest?.('.rvq-board');
   if(!board)return;
   const id=link.getAttribute('href')?.slice(1);
   const target=id?[...board.querySelectorAll('[id]')].find(el=>el.id===id):null;
   if(!target)return;
   event.preventDefault();
   target.scrollIntoView?.({block:'start',behavior:'auto'});
 });
}


const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>typeof n==='number'&&Number.isFinite(n)?n.toLocaleString():'—';
const pretty=s=>{
 const key=String(s||'').toLowerCase().replace(/[^a-z0-9]/g,'');
 return ({google:'Google AI Studio',gemini:'Gemini',groq:'Groq',nvidia:'NVIDIA NIM',openrouter:'OpenRouter',mistral:'Mistral',cloudflare:'Cloudflare Workers AI',cloudflareworkersai:'Cloudflare Workers AI',cloudflareai:'Cloudflare Workers AI',sambanova:'SambaNova',cohere:'Cohere',huggingface:'Hugging Face'})[key]||String(s||'Provider').replace(/[-_]/g,' ');
};
const prettyTime=s=>{
 const t=Date.parse(s||'');if(!Number.isFinite(t))return 'Not reported';
 return new Date(t).toLocaleString([],{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});
};
const resetText=s=>{
 const t=Date.parse(s||'');if(!Number.isFinite(t))return 'Not reported';
 if(t<=Date.now())return 'Time passed · awaiting update';
 const min=Math.ceil((t-Date.now())/60000);
 return prettyTime(s)+' · '+(min>=1440?Math.floor(min/1440)+'d '+Math.ceil((min%1440)/60)+'h':min>=60?Math.floor(min/60)+'h '+min%60+'m':min+'m')+' left';
};
// Pure presentation of an authenticated, already-vetted percentage.
// A provider with missing or contradictory evidence receives NO filled ring.
function usageRing(percent,label,kind='quota'){
 if(percent===null){
  return '<div class="rvq-ring rvq-ring-unknown" role="img" aria-label="Provider quota unknown">'+
   '<div class="rvq-ring-core"><strong>—</strong><small>UNKNOWN</small></div></div>';
 }
 const pct=percent.toFixed(1);
 return '<div class="rvq-ring'+(kind==='activity'?' rvq-ring-traffic':'')+'" role="progressbar" aria-label="'+esc(label)+
  '" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+pct+
  '" aria-valuetext="'+pct+(kind==='activity'?' percent of recorded Mac requests':' percent of verified allowance used')+'" style="--rvq-angle:'+pct+'%">'+
  '<div class="rvq-ring-core"><strong>'+pct+'%</strong><small>'+(kind==='activity'?'TRAFFIC':'USED')+'</small></div></div>';
}
function meter(q){
 const used=q?.used,total=q?.total;
 if(!Number.isSafeInteger(used)||!Number.isSafeInteger(total)||
    total<=0||used<0||used>total||
    (q.used_percent!==undefined&&
      (!Number.isFinite(q.used_percent)||Math.abs(q.used_percent-100*used/total)>0.11)))
   return unknownModel(q);
 const pct=100*used/total;
 const remaining=total-used;
 return '<div class="rvq-model"><div class="rvq-model-head"><div class="rvq-model-name">'+esc(q.model_id)+'</div></div>'+
  '<div class="rvq-ring-layout">'+usageRing(pct,'Reported quota used')+
  '<div class="rvq-ring-copy">'+
  '<div><span class="rvq-info-label">REMAINING ALLOWANCE</span><strong>'+fmt(remaining)+' / '+fmt(total)+' '+esc(q.unit)+'</strong></div>'+
  '<div><span class="rvq-info-label">RESET WINDOW</span><strong>'+esc(resetText(q.reset_at))+'</strong></div>'+
  '<div class="rvq-evidence">OMNIROUTE CACHED REPORT · '+esc(prettyTime(q.fetched_at))+' · Account '+fmt(q.account_slot)+'</div>'+
  '</div></div></div>';
}
function unknownModel(m){
 return '<div class="rvq-model"><div class="rvq-model-head"><div class="rvq-model-name">'+
  esc(m?.model_id||m?.name||'Model allowance unavailable')+
  '</div><div class="rvq-unknown-tag">UNVERIFIED</div></div>'+
  '<div class="rvq-ring-layout">'+usageRing(null)+
  '<div class="rvq-ring-copy">'+
  '<div><span class="rvq-info-label">REMAINING ALLOWANCE</span><strong>Unknown</strong></div>'+
  '<div><span class="rvq-info-label">RESET WINDOW</span><strong>Not reported</strong></div>'+
  (typeof m?.requests==='number'?'<div class="rvq-evidence">'+fmt(m.requests)+' recorded requests · not quota usage</div>':'')+
  '</div></div></div>';
}
// One card per configured connection, not one card per provider family.
// Public telemetry has only safe per-provider account ordinals; no keys or IDs.
// Separate authenticated cloud-ledger evidence; do NOT mix with local OmniRoute cache.
// Cloud provider admission/verification may be disabled even when the local gateway has a key.
function cloudEvidence(p){
 if(!p)return '<div class="rvq-cloud">CLOUD EXECUTION · not connected to private ledger</div>';
 const eligible=p.admission==='eligible';
 const recorded=Number.isSafeInteger(p.recorded_24h?.requests)?p.recorded_24h.requests:null;
 const state=eligible?'ELIGIBLE · execution still requires receipts':'CLOUD ROUTE NOT ELIGIBLE';
 const check=p.last_check?.status?esc(String(p.last_check.status).replaceAll('_',' ')):'Not checked';
 const result=['<div class="rvq-cloud"><strong>CLOUD WORKFORCE / SEPARATE SOURCE</strong><span>'+state+'</span>',
   '<span>Provider catalog check: '+check+'</span>',
   '<span>Recorded cloud requests (24h): '+(recorded===null?'Not reported':fmt(recorded))+'</span>',
   '<span>Verified running now: '+(p.online_verified===true?'YES':'NOT VERIFIED')+'</span>'];
 const gates={
  not_configured:'No verified cloud route configuration',
  missing_secret:'Cloud credential unavailable',
  unpinned_model:'Exact model is not pinned',
  eligibility_unverified:'Free-use eligibility not verified',
  eligibility_expired:'Provider eligibility evidence expired',
  canary_unverified:'Model canary not verified',
  invalid_limits:'Account limits are not verified',
  missing_account:'Provider account metadata is missing',
  paid_route_denied:'Paid model blocked',
  unpinned_upstream:'Upstream provider not pinned',
  global_stop:'Dispatch paused by owner',
  no_matching_unattempted_job:'No eligible approved task for this model',
  global_daily_safety_cap:'Global daily safety cap reached',
  account_request_cap:'Account request allowance reached',
  account_reserved_token_cap:'Reserved token allowance reached',
  account_inflight_claim:'Another job is still claimed',
  account_minimum_interval:'Waiting for rate-limit pacing interval',
  account_retry_after:'Provider Retry-After still active',
  failure_circuit_requires_review:'Failure circuit requires human review',
  claim_contention_or_unclassified_gate:'Claim contention or unknown gate',
  claim_conditions_met_unverified:'Claim gates appear open; inference not verified'
 };
 const gate=p.dispatch_gate;
 const gateMessage=gate&&Object.hasOwn(gates,gate.reason)?gates[gate.reason]:'Not reported';
 const eta=Number(gate?.next_eligible_at);
 const future=Number.isSafeInteger(eta)&&eta>Date.now()&&eta<Date.now()+30*86400000;
 result.push('<span>Next cloud claim · '+esc(gateMessage)+(future?' · eligible after '+esc(new Date(eta).toLocaleString()):'')+' · read-only assessment</span>');
 const q=p.quota;
 const time=Number(q?.observed_at);
 const active=q?.status==='verified'&&Number.isFinite(time)&&time<=Date.now()+300000&&time>Date.now()-90*60000;
 const used=Number(q?.used),limit=Number(q?.limit);
 const reset=q?.resets_at==null?null:new Date(q.resets_at);
 if(active&&Number.isSafeInteger(used)&&Number.isSafeInteger(limit)&&limit>0&&used>=0&&used<=limit&&
    (reset===null||(Number.isFinite(reset.getTime())&&reset.getTime()>Date.now()))){
   const pct=Math.max(0,Math.min(100,100*used/limit)).toFixed(1);
   result.push('<div class="rvq-cloud-ring-layout">'+
     usageRing(100*used/limit,'Verified cloud ledger quota used')+
     '<div class="rvq-cloud-ring-copy"><span>Verified cloud limit · '+fmt(used)+' / '+fmt(limit)+' '+esc(q.unit||'units')+'</span>'+
     '<span>Cloud reset: '+esc(reset?resetText(reset.toISOString()):'Not reported')+'</span>'+
     '<span>Independent cloud account limit · not OmniRoute cached usage</span></div></div>');
 }else result.push('<span>Cloud quota and reset: unknown / not currently verified</span>');
 // Private Site cloud minute-limit reports are distinct from Mac telemetry.
 // Never claim these are organization-wide totals or reset evidence.
 if(p.provider==='mistral'&&Array.isArray(p.minute_rate_limits)){
  const valid=p.minute_rate_limits.filter(q=>
    q?.status==='verified'&&q.source==='authenticated_mistral_inference_minute_headers'&&
    q.scope==='model_on_provider_account'&&['requests','tokens'].includes(q.unit)&&
    typeof q.model==='string'&&/^[a-zA-Z0-9@][a-zA-Z0-9_./:@-]{0,199}$/.test(q.model)&&
    Number.isSafeInteger(q.observed_at)&&q.observed_at<=Date.now()+5000&&
    q.observed_at>=Date.now()-60000&&
    Number.isSafeInteger(q.used)&&q.used>=0&&Number.isSafeInteger(q.limit)&&
    q.limit>0&&q.used<=q.limit&&q.remaining===q.limit-q.used).slice(0,8);
  for(const q of valid){
   result.push('<div class="rvq-cloud-ring-layout">'+usageRing(100*q.used/q.limit,
     'Verified Mistral model minute '+q.unit+' used')+
     '<div class="rvq-cloud-ring-copy"><span>'+esc(q.model)+' · '+esc(q.unit)+
     ' per minute: '+fmt(q.used)+' / '+fmt(q.limit)+' used</span>'+
     '<span>Authenticated inference headers · '+esc(new Date(q.observed_at).toLocaleTimeString())+
     ' · reset not reported · never billing proof</span></div></div>');
  }
  if(!valid.length)result.push('<span>Mistral authenticated minute limits: unverified or expired</span>');
 }
 result.push('</div>');return result.join('');
}

function jobReceipts(provider,attempts){
 // Only trusted same-origin cloud ledger receipts; never attribute the local
 // Mac's anonymous per-provider traffic to an employee without an exact join.
 const history=attempts.filter(a=>a&&a.provider===provider&&typeof a.status==='string')
   .sort((a,b)=>(Number(b.started_at)||0)-(Number(a.started_at)||0));
 const short=v=>esc(String(v??'Not reported').slice(0,120));
 if(!history.length)return '<div class="rvq-jobs"><strong>PROVIDER JOBS / VERIFIED CLOUD RECEIPTS</strong><p>No recorded cloud inference job for this provider. Connection alone does not establish active work.</p></div>';
 const list=history.slice(0,6).map(a=>{
   const started=Number(a.started_at),date=Number.isFinite(started)&&started>0?
     new Date(started).toLocaleString([],{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):'Unreported';
   const input=Number.isSafeInteger(a.tokens_input)&&a.tokens_input>=0?a.tokens_input:null;
   const output=Number.isSafeInteger(a.tokens_output)&&a.tokens_output>=0?a.tokens_output:null;
   const approved=a.human_review==='passed',rejected=a.human_review==='failed';
   const review=approved?'PASS RECORDED':rejected?'FAIL RECORDED':'AWAITING HUMAN REVIEW';
   return '<li class="rvq-job"><div class="rvq-job-top"><span>'+short(a.employee||'Unassigned')+'</span><span>'+short(a.status.replaceAll('_',' '))+'</span></div>'+
     '<div class="rvq-job-title">'+short(a.title||a.task_id||'Untitled job')+'</div>'+
     '<div class="rvq-job-meta">'+short(a.actual_model||a.requested_model||'Model unreported')+' · '+short(date)+'</div>'+
     '<div class="rvq-job-meta">Tokens '+(input===null||output===null?'unreported':fmt(input)+' in / '+fmt(output)+' out')+' · '+review+'</div></li>';
 }).join('');
 return '<div class="rvq-jobs"><strong>PROVIDER JOBS / VERIFIED CLOUD RECEIPTS</strong>'+
    '<p>'+fmt(history.length)+' recorded provider-attributed attempt'+(history.length===1?'':'s')+
    ' · actual job history, not proof of current execution</p>'+
    '<ol class="rvq-job-list" aria-label="Recent provider jobs">'+list+'</ol>'+
    (history.length>6?'<p>Showing six most recent of '+fmt(history.length)+'</p>':'')+
    '<p>Account-slot attribution requires a separate receipt; human review controls are not connected here.</p></div>';
}

const CLOUD_ROSTER=['Walter','Mike','Jane','Jesse','Gale','Gus','Saul','Hank'];
// Employee meters are shares of returned, receipt-attributed cloud attempts,
// never percentages of provider quota or proof an employee is running now.
function cloudEmployeeUsage(attempts,fresh){
 const now=Date.now(), start=now-86400000;
 const employees=new Map(CLOUD_ROSTER.map(name=>[name.toLowerCase(),{name,receipts:0,failed:0,passed:0,tokensIn:0,tokensOut:0,incompleteTokens:0,last:null}]));
 let measured=0, unattributed=0;
 const seen=new Set();
 if(fresh)for(const a of attempts){
   if(!a||typeof a!=='object'||typeof a.status!=='string')continue;
   const when=Number(a.started_at);
   if(!Number.isSafeInteger(when)||when<start||when>now+300000)continue;
   // Canaries test a route; they are not employee deliverables.
   if(String(a.job_id||'').startsWith('canary-')||
      String(a.title||'').startsWith('PROVIDER CANARY'))continue;
   if(typeof a.id!=='string'||!a.id||seen.has(a.id))continue;
   seen.add(a.id);
   const entry=employees.get(String(a.employee||'').trim().toLowerCase());
   if(!entry){unattributed++;continue;}
   entry.receipts++;measured++;
   if(a.status==='failed')entry.failed++;
   if(a.human_review==='passed')entry.passed++;
   if(Number.isSafeInteger(a.tokens_input)&&a.tokens_input>=0&&
      Number.isSafeInteger(a.tokens_output)&&a.tokens_output>=0){
     entry.tokensIn+=a.tokens_input;
     entry.tokensOut+=a.tokens_output;
   }else entry.incompleteTokens++;
   if(!entry.last||when>entry.last.when)
     entry.last={when,provider:String(a.provider||'Unknown'),model:typeof a.actual_model==='string'?a.actual_model:'Model unreported'};
 }
 const rows=[...employees.values()].map(e=>{
   const pct=measured?100*e.receipts/measured:0;
   const visual=fresh&&measured&&e.receipts?
     '<div class="rvq-track" role="progressbar" aria-label="Share of returned cloud receipts for '+esc(e.name)+'" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+pct.toFixed(1)+'"><i style="width:'+pct.toFixed(1)+'%"></i></div>':
     '<div class="rvq-track rvq-unknown" role="img" aria-label="No measured receipt share"></div>';
   const label=!fresh?'DATA DISCONNECTED':!measured?'NO RECEIPT SAMPLE':e.receipts?fmt(e.receipts)+' RECEIPT'+(e.receipts===1?'':'S'):'NO ATTRIBUTED RECEIPT';
   const tokens=e.receipts?
     fmt(e.tokensIn)+' in / '+fmt(e.tokensOut)+' out'+(e.incompleteTokens?' · partial token reporting':''):
     'Tokens unreported';
   const latest=e.last?esc(e.last.provider.slice(0,70))+' · '+esc(e.last.model.slice(0,100)):'No recorded provider/model assignment';
   return '<li class="rvq-emp-row"><div class="rvq-emp-top"><strong>'+esc(e.name)+'</strong><span>'+label+'</span></div>'+
     visual+'<div class="rvq-emp-facts"><span>'+(measured&&e.receipts?pct.toFixed(1)+'% of attributed receipt sample':'Share unknown')+
     '</span><span>'+tokens+'</span></div><div class="rvq-emp-last">'+latest+
     (e.receipts?' · '+fmt(e.failed)+' failed · '+fmt(e.passed)+' passed review':'')+'</div></li>';
 }).join('');
 return '<section class="rvq-cloud-staff"><div class="rvq-emp-head"><div><span class="rvq-eyebrow">VERIFIED CLOUD LEDGER / LAST 24H</span><h4>Employee model usage</h4></div><span class="rvq-status">'+(fresh?fmt(measured)+' ATTRIBUTED RECEIPTS':'LEDGER DISCONNECTED')+'</span></div>'+
   '<p>Eight employee slots. Bars show each employee’s share of the returned cloud receipt sample, not quota utilization, total 24h requests, or proof of active execution. Canary probes excluded. '+(unattributed?fmt(unattributed)+' other returned receipts have no matching employee.':'')+'</p>'+
   '<ul class="rvq-emp-grid">'+rows+'</ul></section>';
}

// Source-authentic, complete 24-hour Mac request usage. A connection is not
// proof of requests; zero means zero ONLY when the complete aggregate is fresh.
// The public gateway usage model is provider-wide, not account-slot-attributed.
function macActivity(data,live,period='24h'){
 if(!live||data?.period!==period||data?.usage_coverage!=='complete_aggregate'||
    !Array.isArray(data.models)||!Number.isSafeInteger(data.request_count)||
    data.request_count<0)return null;
 let total=0;
 const groups=new Map();
 for(const model of data.models){
   if(!model||typeof model.provider!=='string'||
      !Number.isSafeInteger(model.requests)||model.requests<0||
      !Number.isSafeInteger(model.tokens)||model.tokens<0)return null;
   total+=model.requests;
   if(!Number.isSafeInteger(total))return null;
   const old=groups.get(model.provider)||{requests:0,tokens:0,models:[]};
   old.requests+=model.requests;old.tokens+=model.tokens;
   if(!Number.isSafeInteger(old.requests)||!Number.isSafeInteger(old.tokens))return null;
   // Preserve the gateway's actual routed model name. Model names can have
   // upstream-provider prefixes even when the billed gateway is OpenRouter.
   old.models.push({name:String(model.name||model.id||'Model unreported').slice(0,160),
     requests:model.requests,tokens:model.tokens});
   groups.set(model.provider,old);
 }
 // Partial, inconsistent or mismatched aggregates must never produce fake
 // per-provider zeros or percentages.
 if(total!==data.request_count)return null;
 return {total,groups};
}
function providerActivity(activity,provider){
 if(!activity)return null;
 const found=activity.groups.get(provider)||{requests:0,tokens:0,models:[]};
 return {...found,share:activity.total?100*found.requests/activity.total:0};
}
function activityLabel(activity,live){
 if(!live||!activity)return '<div class="rvq-activity rvq-unreported">MAC 24H REQUESTS · not currently verified</div>';
 return '<div class="rvq-activity">MAC 24H PROVIDER TOTAL · <strong>'+fmt(activity.requests)+
   ' request'+(activity.requests===1?'':'s')+'</strong> · '+fmt(activity.tokens)+' reported tokens'+
   '<span>Per-provider aggregate; not an account-slot counter or remaining quota</span></div>';
}

// Recorded model traffic is independently measured. These percentages show
// only relative request activity *inside this gateway provider*, never upstream
// free-tier quota or individual OmniRoute account/key usage.
function modelActivity(activity,provider,hourly,minute){
 if(!activity)return '<div class="rvq-model-activity rvq-activity-unverified">MODEL REQUESTS · gateway aggregate unverified</div>';
 if(!activity.models.length)return '<div class="rvq-model-activity"><strong>RECORDED MODELS / 24H</strong><p>No recorded model requests through '+esc(pretty(provider))+' in this complete 24-hour aggregate.</p></div>';
 const list=activity.models.slice().sort((a,b)=>b.requests-a.requests||a.name.localeCompare(b.name)).map(m=>{
   const pct=activity.requests?100*m.requests/activity.requests:0;
   const formatted=pct.toFixed(1);
   const inHour=hourly?.models.find(h=>h.name===m.name);
   const inMinute=minute?.models.find(h=>h.name===m.name);
   const lastMinute=minute?'<div class="rvq-observed-model-minute">LAST MINUTE · '+fmt(inMinute?.requests??0)+' request'+((inMinute?.requests??0)===1?'':'s')+' · '+fmt(inMinute?.tokens??0)+' reported tokens</div>':'';
   const oneHour=hourly?'<div class="rvq-observed-model-hour">LAST HOUR · '+fmt(inHour?.requests??0)+' request'+((inHour?.requests??0)===1?'':'s')+' · '+fmt(inHour?.tokens??0)+' reported tokens</div>':'';
   return '<li class="rvq-observed-model"><div class="rvq-observed-model-top"><span>'+esc(m.name)+'</span><strong>'+fmt(m.requests)+' request'+(m.requests===1?'':'s')+'</strong></div>'+
     '<div class="rvq-track" role="progressbar" aria-label="Recorded model request share within '+esc(pretty(provider))+'" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+formatted+'" aria-valuetext="'+formatted+' percent of '+esc(pretty(provider))+' recorded requests"><i style="width:'+formatted+'%"></i></div>'+
     '<div class="rvq-observed-model-meta">'+fmt(m.tokens)+' reported tokens · '+formatted+'% of this gateway provider\'s requests</div>'+lastMinute+oneHour+'</li>';
 }).join('');
 return '<div class="rvq-model-activity"><strong>RECORDED MODELS / 24H</strong><p>Observed gateway model traffic; upstream names do not establish direct account usage or remaining quota.</p>'+
   '<ul class="rvq-observed-models">'+list+'</ul></div>';
}
function hourLabel(hourly,live){
 if(!live||!hourly)return '<div class="rvq-hourly rvq-hourly-unknown">LAST HOUR · independently verified data unavailable</div>';
 return '<div class="rvq-hourly">LAST HOUR · <strong>'+fmt(hourly.requests)+' request'+(hourly.requests===1?'':'s')+'</strong> · '+fmt(hourly.tokens)+' reported tokens'+
  '<span>Separate complete 1h gateway window · not a rate-limit or quota percentage</span></div>';
}
// Explicit owner-supplied organization capacity snapshot (Oct 27, 2026).
// This is NOT a live rate-limit cache, a measured usage denominator, nor a
// verification that any listed model is free, currently routable, or billable.
// Do not merge these references into quota.records or filled circular meters.
const MISTRAL_OWNER_LIMITS=[
 ['codestral-2508',625000,2.08],
 ['labs-leanstral-1-5-1',5000000,0.63],
 ['ministral-14b-2512',937500,0.50],
 ['ministral-3b-2512',1300000,12.50],
 ['ministral-8b-2512',625000,3.13],
 ['mistral-medium-latest',20000,1.00],
 ['mistral-large-2512',250000,1.00],
 ['mistral-small-2603',20000,1.00],
 ['mistral-large-4',20000,0.83]
];
// Groq screenshot supplied by the owner on Oct 27, 2026: organization
// BASE limits, not a current-project override or live remaining balance.
// Do not treat this reference as billing or fresh authenticated quota telemetry.
const GROQ_OWNER_BASE_LIMITS=Object.freeze({
 model:'openai/gpt-oss-20b',rpm:30,rpd:1000,tpm:8000,tpd:200000
});
function groqLimitReferences(provider){
 if(provider!=='groq')return '';
 const q=GROQ_OWNER_BASE_LIMITS;
 return '<section class="rvq-mistral-reference" aria-label="Owner-supplied Groq organization base rate limits">'+
  '<strong>GROQ · ORGANIZATION BASE LIMITS (OWNER SNAPSHOT)</strong>'+
  '<p>Observed October 27, 2026 · Model '+esc(q.model)+
  '. Per-project overrides may differ. These are capacity ceilings, not live consumed/remaining or an authenticated quota observation.</p>'+
  '<table><thead><tr><th>Requests/min</th><th>Requests/day</th><th>Tokens/min</th><th>Tokens/day</th></tr></thead><tbody>'+
  '<tr><td>'+fmt(q.rpm)+'</td><td>'+fmt(q.rpd)+'</td><td>'+fmt(q.tpm)+'</td><td>'+fmt(q.tpd)+'</td></tr></tbody></table>'+
  '<p>The live request/token figures above include only observed OmniRoute traffic; other account usage is not measured. No verified remaining-quota percentage or reset is asserted.</p></section>';
}
// Owner-supplied Google AI Studio Free tier project rate-limits view.
// It displays 28-day PEAK observed use, not current balance or a live quota
// API. Model display names are NOT stable API model IDs. No new model route,
// commercial eligibility, quota record or provider health is implied.
const GEMINI_OWNER_FREE_LIMITS=[
 ['Gemini 3.8 Flash',5,250000,20],
 ['Gemini 2.5 Flash',5,250000,20],
 ['Gemini 2.5 Flash Lite',10,250000,20],
 ['Gemini 3 Flash',5,250000,20],
 ['Gemini 3.1 Flash Lite',15,250000,500],
 ['Gemini 3.5 Flash Lite',15,250000,500],
 ['Gemini 3.6 Flash',5,250000,20]
];
const GEMINI_OWNER_OTHER_LIMITS=[
 ['Gemma 4 26B',30,16000,14400],
 ['Gemma 4 31B',30,16000,14400],
 ['Gemini Embedding 1',100,30000,1000],
 ['Gemini Embedding 2',100,30000,1000]
];
// Google project-level observed DELTA sample + GAUGE capacity are separate
// pieces of evidence. They do NOT certify instant remaining quota or a reset.
function geminiProjectMonitoring(provider,doc){
 if(provider!=='gemini')return '';
 if(!doc||doc.source!=='google_cloud_monitoring')return '<p>Gemini project quota monitoring · not connected</p>';
 const status=String(doc.status||'unavailable');
 const base='<section class="rvq-mistral-reference" aria-label="Google-authenticated Gemini project quota samples">'+
  '<strong>GEMINI PROJECT · AUTHENTICATED GOOGLE MONITORING</strong>';
 const fresh=doc.status==='sampled_project_quota'&&Number.isSafeInteger(doc.observed_at)&&
   doc.observed_at>=Date.now()-120000&&doc.observed_at<=Date.now()+10000&&
   Array.isArray(doc.models)&&doc.models.length<=40;
 if(!fresh)return base+'<p>'+esc(status.replaceAll('_',' '))+
  ' · project monitoring is not an authenticated live remaining-quota reading yet.</p></section>';
 const samples=doc.models.filter(q=>q?.source==='google_cloud_monitoring_free_tier_project_metrics'&&
   q.scope==='google_project_sample'&&typeof q.model==='string'&&
   /^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,149}$/.test(q.model)&&
   typeof q.limit_name==='string'&&/^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,149}$/.test(q.limit_name)&&
   ['requests','input_tokens'].includes(q.unit)&&
   Number.isSafeInteger(q.limit)&&q.limit>0&&
   Number.isSafeInteger(q.sampled_usage)&&q.sampled_usage>=0&&q.sampled_usage<=q.limit&&
   Number.isSafeInteger(q.sample_started_at)&&Number.isSafeInteger(q.sample_ended_at)&&
   q.sample_started_at<q.sample_ended_at&&
   q.sample_ended_at<=Date.now()+10000&&Date.now()-q.sample_ended_at<=300000
 ).slice(0,12);
 if(!samples.length)return base+'<p>Google response has no valid fresh model samples. Quota remains unknown.</p></section>';
 const rows=samples.map(q=>
   '<tr><td>'+esc(q.model)+'</td><td>'+esc(q.limit_name)+'</td><td>'+esc(q.unit)+'</td>'+
   '<td>'+fmt(q.sampled_usage)+'</td><td>'+fmt(q.limit)+'</td></tr>').join('');
 return base+'<p>Verified project-level free-tier observations from Google Cloud Monitoring, which may lag by 150 seconds or more. Sampled usage is a historical interval; it is NOT the current remaining balance. No inferred reset or unearned online status.</p>'+
  '<table><thead><tr><th>Model</th><th>Limit name</th><th>Unit</th><th>Last sampled use</th><th>Reported limit</th></tr></thead><tbody>'+
  rows+'</tbody></table></section>';
}
function geminiLimitReferences(provider){
 if(provider!=='gemini')return '';
 const trs=rows=>rows.map(([name,rpm,tpm,rpd])=>
  '<tr><td>'+esc(name)+'</td><td>'+fmt(rpm)+'</td><td>'+fmt(tpm)+'</td><td>'+fmt(rpd)+'</td></tr>').join('');
 return '<section class="rvq-mistral-reference" aria-label="Owner-supplied Gemini project Free tier capacity references">'+
  '<strong>GEMINI · FREE TIER PROJECT LIMITS (OWNER SNAPSHOT)</strong>'+
  '<p>Observed October 27, 2026 · Default Gemini Project · Google AI Studio. These are project-scoped rate-limit ceilings, not remaining balance, current usage, direct model availability or free/commercial-use proof for OmniRoute routes.</p>'+
  '<table><thead><tr><th>Text-out model</th><th>Requests/min</th><th>Tokens/min</th><th>Requests/day</th></tr></thead><tbody>'+
   trs(GEMINI_OWNER_FREE_LIMITS)+'</tbody></table>'+
  '<details><summary>Other usable categories in this project snapshot</summary>'+
   '<table><thead><tr><th>Other model</th><th>Requests/min</th><th>Tokens/min</th><th>Requests/day</th></tr></thead><tbody>'+
   trs(GEMINI_OWNER_OTHER_LIMITS)+'</tbody></table>'+
   '<p>Gemma and embedding categories are not automatically interchangeable with Gemini text-out inference.</p></details>'+
  '<p>28-day peak for Gemini 3.8 Flash: 3 / 5 RPM, 51 / 250,000 TPM, 4 / 20 RPD. This is NOT current remaining quota. Models showing 0 / 0 have no positive allowance in the selected view.</p>'+
  '<p>Project-wide consumption outside OmniRoute is not included in gateway activity. No limit percentages, resets, worker status or verified billing are invented from this reference.</p></section>';
}
function mistralLimitReferences(provider,activity){
 if(provider!=='mistral')return '';
 const recorded=activity?.models||[];
 const historical=recorded.filter(m=>!MISTRAL_OWNER_LIMITS.some(row=>row[0]===m.name));
 const cells=MISTRAL_OWNER_LIMITS.map(([name,tpm,rps])=>
   '<tr><td>'+esc(name)+'</td><td>'+fmt(tpm)+'</td><td>'+Number(rps).toFixed(2)+'</td></tr>').join('');
 return '<section class="rvq-mistral-reference" aria-label="Owner supplied Mistral rate limit reference">'+
   '<strong>MISTRAL ORGANIZATION LIMITS · OWNER SNAPSHOT</strong>'+
   '<p>Observed October 27, 2026 · Global. TPM and RPS are per-model capacity settings, not measured consumption, available quota, free-tier eligibility, or reset times. They may change.</p>'+
   '<table><thead><tr><th>Model</th><th>Tokens/min</th><th>Requests/sec</th></tr></thead><tbody>'+cells+'</tbody></table>'+
   (historical.length?'<p class="rvq-limit-mismatch">Recorded model without a supplied matching limit: '+historical.map(m=>esc(m.name)).join(', ')+'. No limit or quota percentage assigned.</p>':'')+
   '<p>Live Mistral usage above is OmniRoute-only. Organization-wide used/remaining still requires verified API telemetry.</p></section>';
}
function minuteLabel(minute,live){
 if(!live||!minute)return '<div class="rvq-minute rvq-minute-unknown">LIVE LAST MINUTE · independently verified data unavailable</div>';
 return '<div class="rvq-minute">LIVE LAST MINUTE · <strong>'+fmt(minute.requests)+' request'+(minute.requests===1?'':'s')+'</strong> · '+fmt(minute.tokens)+' reported tokens'+
  '<span>Rolling 60-second OmniRoute sample · not Mistral organization-wide usage or remaining quota</span></div>';
}
function card(group,quota,live,index,slot,cloud,attempts,activity,hourly,minute,geminiProject=null){
 const entries=live&&slot.enabled!==false?quota.filter(q=>q.provider===group.provider&&q.account_slot===slot.account_slot&&
   (!q.reset_at||Date.parse(q.reset_at)>Date.now())):[];
 const rows=entries.map(meter);
 if(!rows.length)rows.push(unknownModel(null));
 const first=rows.slice(0,2).join('');
 const key=group.provider+':'+slot.account_slot;
 const extra=rows.length>2?'<details class="rvq-more"'+(expandedSlots.has(key)?' open':'')+'><summary>Show '+(rows.length-2)+' more model'+(rows.length===3?'':'s')+'</summary>'+rows.slice(2).join('')+'</details>':'';
 const state=!live?'TELEMETRY STALE':slot.enabled===false?'DISABLED':slot.enabled===true?'GATEWAY ENABLED · PROVIDER UNVERIFIED':'ENABLEMENT UNKNOWN';
 const evidence=entries.length?'LIMITS REPORTED':'QUOTA UNKNOWN';
 const name=pretty(group.name||group.provider);
 // The full original per-provider report is retained, now under one accessible disclosure.
 return '<article class="rvq-provider" data-rvq-slot="'+esc(key)+'"><details class="rvq-provider-details"'+(expandedProviders.has(key)?' open':'')+'><summary class="rvq-provider-head"><span class="rvq-provider-icon">'+esc(name.slice(0,1).toUpperCase())+'</span><span class="rvq-provider-ident"><span class="rvq-provider-index">CONNECTION '+String(index+1).padStart(2,'0')+' / '+esc(name)+'</span><span class="rvq-provider-name">'+esc(name)+' · Slot '+fmt(slot.account_slot)+'</span><span class="rvq-provider-connection">'+state+'</span></span><span class="rvq-provider-status'+(entries.length?' rvq-reported':'')+'">'+evidence+'</span></summary>'+
  '<div class="rvq-provider-content">'+activityLabel(activity,live)+minuteLabel(minute,live)+hourLabel(hourly,live)+modelActivity(activity,group.provider,hourly,minute)+mistralLimitReferences(group.provider,activity)+groqLimitReferences(group.provider)+geminiLimitReferences(group.provider)+geminiProjectMonitoring(group.provider,geminiProject)+first+extra+cloudEvidence(cloud)+jobReceipts(group.provider,attempts)+'</div></details></article>';
}
// Nine-provider glance cards are a visualization of one explicitly labeled
// validated quota source per slot. They never sum Mac and cloud counters.
const ACTION_GATES=new Set(['missing_secret','unpinned_model','eligibility_unverified','eligibility_expired','canary_unverified','invalid_limits','missing_account','paid_route_denied','unpinned_upstream','failure_circuit_requires_review']);
const needsSetupReview=p=>ACTION_GATES.has(p?.dispatch_gate?.reason);
function overviewSlot(slot,quota,live,cloud,index,activity,hourly,minute){
 const local=live&&slot.enabled!==false?quota.find(q=>q.provider===slot.group.provider&&
   q.account_slot===slot.account_slot&&Number.isSafeInteger(q.used)&&
   Number.isSafeInteger(q.total)&&q.total>0&&q.used>=0&&q.used<=q.total&&
   (q.used_percent===undefined||
    (Number.isFinite(q.used_percent)&&Math.abs(q.used_percent-100*q.used/q.total)<=0.11))):null;
 const cq=cloud?.quota;
 const observed=Number(cq?.observed_at),limit=Number(cq?.limit),used=Number(cq?.used);
 const reset=cq?.resets_at;
 const verified=!local&&cq?.status==='verified'&&Number.isFinite(observed)&&
   observed>Date.now()-90*60000&&observed<=Date.now()+300000&&
   Number.isSafeInteger(used)&&Number.isSafeInteger(limit)&&limit>0&&used>=0&&used<=limit&&
   (reset===null||reset===undefined||(Number.isSafeInteger(reset)&&reset>Date.now()));
 const pct=local?100*local.used/local.total:verified?100*used/limit:null;
 const evidence=local?'MAC QUOTA CACHE':verified?'CLOUD LIMIT':'QUOTA UNKNOWN';
 const name=pretty(slot.group.name||slot.group.provider);
 const traffic=activity?usageRing(activity.share,'Mac 24-hour recorded request share for '+name,'activity'):'';
 const attention=needsSetupReview(cloud);
 return '<a class="rvq-overview-tile" href="#rvq-reports" data-rvq-attention="'+String(attention)+'"'+(overviewFilter==='attention'&&!attention?' hidden':'')+' data-rvq-open-slot="'+esc(slot.group.provider+':'+slot.account_slot)+'" aria-label="View '+esc(name)+' connection '+fmt(slot.account_slot)+' full report · '+evidence+(attention?' · setup or review required':'')+'">'+
   '<span class="rvq-overview-name">'+esc(name)+'</span>'+
   // Prioritize the real 24h usage ring in each of the nine connection tiles.
   // Unknown account quota remains a separate visible ring; never present traffic as quota.
   '<div class="rvq-overview-rings">'+(activity?'<span class="rvq-overview-ring-group">'+traffic+'<span class="rvq-ring-label">MAC TRAFFIC</span></span>':'')+'<span class="rvq-overview-ring-group">'+usageRing(pct,evidence+' for '+name)+'<span class="rvq-ring-label">QUOTA USED</span></span></div>'+
   (attention?'<span class="rvq-overview-alert">SETUP / REVIEW</span>':'')+
   '<span class="rvq-overview-source">'+evidence+'</span>'+
   '<span class="rvq-overview-requests">'+(activity?fmt(activity.requests)+' Mac request'+(activity.requests===1?'':'s')+' / 24h':'Mac requests unverified')+'</span>'+
   '<span class="rvq-overview-intervals"><span class="rvq-overview-hourly">'+(hourly?fmt(hourly.requests)+' / 1h':'1h unverified')+'</span>'+
   '<span class="rvq-overview-minute">'+(minute?fmt(minute.requests)+' / 1m':'1m unverified')+'</span></span><span class="rvq-overview-drill">VIEW DETAILS</span></a>';
}
function dispatchInfo(workforce,live){
 const d=live?workforce?.dispatch:null;
 if(d?.status!=='recent_scheduler_report')
  return '<div class="rvq-dispatch">SCHEDULER STATUS · No recent verified pacing counters available</div>';
 const counts=Number.isSafeInteger(d.claims_last_24h)&&Number.isSafeInteger(d.max_claims_24h)?
   fmt(d.claims_last_24h)+' / '+fmt(d.max_claims_24h)+' claims in 24h':'Allowance not reported';
 const queued=Number.isSafeInteger(d.queued)?fmt(d.queued):'Unknown';
 const review=Number.isSafeInteger(d.needs_review)?fmt(d.needs_review):'Unknown';
 const completed=Number.isSafeInteger(d.last_tick_executed)?fmt(d.last_tick_executed):'Unknown';
 const when=Number(d.next_eligible_at);
 const next=Number.isFinite(when)&&when>0?
   (when*1000>Date.now()?'Next eligible '+new Date(when*1000).toLocaleString([],{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):
    'Last eligibility time passed · waiting for a new worker report'):'Next eligible time not reported';
 const reason=String(d.reason||'unknown').replaceAll('_',' ').slice(0,80);
 return '<div class="rvq-dispatch"><strong>MAC WORKER / VERIFIED SCHEDULER REPORT</strong>'+
  '<div class="rvq-dispatch-stats"><span>Reason: '+esc(reason)+'</span><span>'+counts+
  '</span><span>Queued '+queued+'</span><span>Needs review '+review+
  '</span><span>Executed last tick '+completed+'</span></div>'+
  '<p>'+esc(next)+' · scheduler heartbeat, not proof of model activity</p></div>';
}
function localEmployeeSection(workforce,live){
 const employees=live&&Array.isArray(workforce?.employees)&&workforce.employees.length<=20?
   workforce.employees:[];
 if(!employees.length)return '<section class="rvq-staff"><h4>Mac employee snapshot</h4><p>Fresh employee job data unavailable; provider receipts above come from a separate cloud ledger.</p></section>';
 const rows=employees.map(e=>{
   const job=e?.latest_job;
   const counts='Queued '+fmt(e?.queued_jobs)+' · Running '+fmt(e?.running_jobs);
   const title=job?.task?esc(String(job.task).slice(0,120)):'No attributed job';
   const route=job?.assigned_route?' · Route '+esc(String(job.assigned_route).slice(0,100)):'';
   const verified=e?.online_verified===true?'Verified online':'Running not verified';
   return '<li class="rvq-staff-row"><div class="rvq-job-top"><strong>'+
     esc(String(e?.name||e?.id||'Unassigned').slice(0,80))+'</strong><span>'+
     esc(String(e?.status||'Unknown').replaceAll('_',' ').slice(0,60))+'</span></div>'+
     '<div class="rvq-job-title">'+title+'</div><div class="rvq-job-meta">'+counts+route+
     '</div><div class="rvq-job-meta">'+verified+' · actual upstream model receipt not linked</div></li>';
 }).join('');
 return '<section class="rvq-staff"><h4>Mac workforce / local job history</h4>'+
  '<p>Latest assigned employee jobs. Past draft records do not prove current execution.</p>'+
  dispatchInfo(workforce,live)+
  '<ul class="rvq-staff-list">'+rows+'</ul></section>';
}
const css=`
#rovor-workload-popup .rvq-review-entry{display:grid;gap:7px;margin:0 0 14px;padding:12px 14px;border:1px solid rgba(99,183,227,.45);border-radius:9px;background:rgba(6,36,65,.75);color:#b0d7ea;font:12px/1.45 system-ui}
#rovor-workload-popup .rvq-review-entry strong{color:#e1f7ff;font-size:12px}
#rovor-workload-popup .rvq-review-entry p{margin:0}
#rovor-workload-popup .rvq-review-entry a{color:#77d5ff;font-weight:700;text-decoration:underline;text-underline-offset:3px}

#rovor-workload-popup .rvq-board{margin:8px 0 20px!important;padding:20px!important;background:linear-gradient(160deg,rgba(4,24,47,.96),rgba(2,12,28,.96))!important;border:1px solid rgba(79,169,221,.36)!important;border-radius:15px!important;color:#e6f6ff}
#rovor-workload-popup .rvq-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;flex-wrap:wrap;margin-bottom:17px}
#rovor-workload-popup .rvq-eyebrow{color:#7bcaff;font:600 10px system-ui;letter-spacing:.18em}
#rovor-workload-popup .rvq-heading{font:600 clamp(19px,2.4vw,26px)/1.22 system-ui;margin:5px 0 6px;color:#f2fcff;letter-spacing:.01em}
#rovor-workload-popup .rvq-sub{color:#a0c3d8;font:12px/1.5 system-ui;margin:0;max-width:560px}
#rovor-workload-popup .rvq-status{flex:none;padding:8px 10px;border:1px solid rgba(105,189,236,.36);background:rgba(48,122,173,.13);border-radius:7px;color:#bcecff;font:700 10px system-ui;letter-spacing:.09em}
#rovor-workload-popup .rvq-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0 0 18px}
#rovor-workload-popup .rvq-stat{padding:12px 13px;background:rgba(10,46,75,.65);border:1px solid rgba(93,164,206,.25);border-radius:10px;min-width:0}
#rovor-workload-popup .rvq-stat-label{display:block;color:#8fb9d1;font:700 10px system-ui;letter-spacing:.12em;margin-bottom:8px}
#rovor-workload-popup .rvq-stat-value{display:block;color:#f2fbff;font:600 19px/1.3 system-ui;overflow-wrap:anywhere}
#rovor-workload-popup .rvq-stat-value.rvq-small{font-size:13px;min-height:25px}
#rovor-workload-popup .rvq-stat-secondary{display:block;color:#98bdd5;font:10px/1.4 system-ui;margin-top:5px}
#rovor-workload-popup .rvq-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;align-items:start}
#rovor-workload-popup .rvq-provider{min-width:0;background:linear-gradient(145deg,rgba(13,48,77,.88),rgba(5,25,44,.95));border:1px solid rgba(90,164,204,.38);border-radius:12px;overflow:hidden;box-shadow:inset 0 1px rgba(153,219,252,.07)}
#rovor-workload-popup .rvq-provider-head{display:flex;align-items:center;gap:10px;padding:12px 14px;cursor:pointer;list-style:none}
#rovor-workload-popup .rvq-provider-head::-webkit-details-marker{display:none}
#rovor-workload-popup .rvq-provider-head:focus-visible{outline:2px solid #a9e1ff;outline-offset:-3px}
#rovor-workload-popup .rvq-provider-head:after{content:'+';font:700 19px system-ui;color:#a9dcff;flex:none}
#rovor-workload-popup .rvq-provider-details[open]>.rvq-provider-head{border-bottom:1px solid rgba(95,175,213,.22)}
#rovor-workload-popup .rvq-provider-details[open]>.rvq-provider-head:after{content:'−'}
#rovor-workload-popup .rvq-provider-name{display:block;margin:3px 0 2px;color:#ecfaff;font:700 14px/1.32 system-ui;overflow-wrap:anywhere}
#rovor-workload-popup .rvq-provider-connection{display:block;color:#9ec5d8;font:11px/1.4 system-ui}
#rovor-workload-popup .rvq-provider-icon{display:grid;place-items:center;flex:none;width:36px;height:36px;border-radius:9px;border:1px solid rgba(116,205,255,.49);background:radial-gradient(circle at 30% 25%,#236b9e,#0b3154);color:#eafaff;font:700 16px system-ui}
#rovor-workload-popup .rvq-provider-ident{min-width:0;flex:1}
#rovor-workload-popup .rvq-provider-index{display:block;color:#8bb7ce;font:700 9px system-ui;letter-spacing:.13em}
#rovor-workload-popup .rvq-provider-ident h4{margin:3px 0 2px;color:#ecfaff;font:700 14px/1.32 system-ui;overflow-wrap:anywhere}
#rovor-workload-popup .rvq-provider-ident p{margin:0;color:#9ec5d8;font:11px system-ui}
#rovor-workload-popup .rvq-provider-status{border:1px solid rgba(138,167,183,.35);background:rgba(80,113,134,.12);color:#b2cbd9;border-radius:5px;padding:6px;font:700 9px system-ui;letter-spacing:.06em;white-space:nowrap;text-align:center}
#rovor-workload-popup .rvq-provider-status.rvq-reported{color:#9ce0ff;border-color:rgba(89,185,235,.5);background:rgba(54,150,204,.14)}
#rovor-workload-popup .rvq-provider-content{padding:0 15px 5px}
#rovor-workload-popup .rvq-model{padding:15px 0 13px;border-bottom:1px solid rgba(110,181,217,.16)}
#rovor-workload-popup .rvq-model:last-child{border-bottom:0}
#rovor-workload-popup .rvq-cloud{display:grid;gap:7px;padding:12px 0 13px;border-top:1px solid rgba(111,193,231,.23);font:11px/1.5 system-ui;color:#a8cce3}
#rovor-workload-popup .rvq-cloud strong{color:#94d5ff;font-size:10px;letter-spacing:.09em}
#rovor-workload-popup .rvq-cloud .rvq-track{height:8px}
#rovor-workload-popup .rvq-jobs{display:grid;gap:6px;border-top:1px solid rgba(111,193,231,.23);padding:12px 0 14px;color:#99bdd3;font:11px/1.5 system-ui}
#rovor-workload-popup .rvq-jobs>strong{font:700 10px system-ui;letter-spacing:.09em;color:#95daff}
#rovor-workload-popup .rvq-jobs p{margin:2px 0;color:#9fc2d7}

#rovor-workload-popup .rvq-cloud-staff{margin:16px 0;padding:14px;border:1px solid rgba(99,183,227,.38);border-radius:12px;background:linear-gradient(160deg,rgba(9,41,70,.95),rgba(4,23,43,.98));color:#afcddd}
#rovor-workload-popup .rvq-emp-head{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:9px}
#rovor-workload-popup .rvq-emp-head h4{font:700 15px system-ui;margin:4px 0 0;color:#d4f2ff}
#rovor-workload-popup .rvq-cloud-staff>p{font:11px/1.6 system-ui;color:#9cbfd4;margin:10px 0 14px}
#rovor-workload-popup .rvq-emp-grid{list-style:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin:0;padding:0}
#rovor-workload-popup .rvq-emp-row{padding:12px;min-width:0;border:1px solid rgba(101,170,211,.27);border-radius:9px;background:rgba(3,24,45,.76)}
#rovor-workload-popup .rvq-emp-top,.rvq-emp-facts{display:flex;justify-content:space-between;align-items:start;gap:9px;flex-wrap:wrap}
#rovor-workload-popup .rvq-emp-top{color:#d4f3ff;font:700 11px system-ui;margin-bottom:9px}
#rovor-workload-popup .rvq-emp-top span{font:700 9px system-ui;letter-spacing:.05em;color:#8bbbd7}
#rovor-workload-popup .rvq-emp-facts{color:#a8d1e9;font:10px/1.5 system-ui;margin-top:8px}
#rovor-workload-popup .rvq-emp-last{color:#88b1ca;font:10px/1.5 system-ui;margin-top:6px;overflow-wrap:anywhere}
@media(max-width:650px){#rovor-workload-popup .rvq-emp-grid{grid-template-columns:1fr}}

#rovor-workload-popup .rvq-staff{margin-top:16px;padding:14px;border:1px solid rgba(90,164,204,.38);border-radius:12px;background:rgba(6,29,51,.94);color:#a3c8dc}
#rovor-workload-popup .rvq-staff>h4{margin:0 0 6px;color:#c7eeff;font:700 14px system-ui}
#rovor-workload-popup .rvq-staff>p{margin:0 0 12px;font:11px/1.5 system-ui}
#rovor-workload-popup .rvq-dispatch{margin:4px 0 12px;padding:11px 12px;border:1px solid rgba(87,175,224,.4);border-radius:9px;background:rgba(9,46,77,.65);color:#acd5ee;font:11px/1.6 system-ui}
#rovor-workload-popup .rvq-dispatch>strong{font:700 10px system-ui;letter-spacing:.09em;color:#a5e2ff}
#rovor-workload-popup .rvq-dispatch-stats{display:flex;gap:8px 16px;flex-wrap:wrap;margin:9px 0}
#rovor-workload-popup .rvq-dispatch-stats>span{color:#d6f2ff}
#rovor-workload-popup .rvq-dispatch>p{margin:7px 0 0;color:#9cbed4}
#rovor-workload-popup .rvq-staff-list{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;max-height:280px;overflow-y:auto;overscroll-behavior:contain}
#rovor-workload-popup .rvq-staff-row{padding:10px;border:1px solid rgba(90,164,204,.24);border-radius:9px;min-width:0;font:11px/1.5 system-ui}
@media(max-width:650px){#rovor-workload-popup .rvq-staff-list{grid-template-columns:1fr}}
#rovor-workload-popup .rvq-job-list{list-style:none;padding:0;margin:5px 0;max-height:235px;overflow:auto;overscroll-behavior:contain;scrollbar-color:#327baf #082b46;scrollbar-width:thin}
#rovor-workload-popup .rvq-job{padding:9px 0;border-top:1px solid rgba(110,181,217,.16)}
#rovor-workload-popup .rvq-job-top{display:flex;gap:9px;justify-content:space-between;flex-wrap:wrap;color:#8ad4ff;font-weight:600}
#rovor-workload-popup .rvq-job-title{margin:5px 0;color:#e3f6ff;font-weight:600;overflow-wrap:anywhere}
#rovor-workload-popup .rvq-job-meta{color:#9abed3;font-size:10px;overflow-wrap:anywhere}

/* Compact iOS-style rings: gateway request share and verified quota are distinct. */
#rovor-workload-popup .rvq-ring-layout,#rovor-workload-popup .rvq-cloud-ring-layout{display:grid;grid-template-columns:96px minmax(0,1fr);gap:13px;align-items:center}
#rovor-workload-popup .rvq-ring{--rvq-angle:0%;position:relative;display:grid;place-items:center;width:96px;height:96px;border-radius:50%;flex:none;background:conic-gradient(from -90deg,#69d8ff 0 var(--rvq-angle),#183c59 var(--rvq-angle) 100%);box-shadow:0 0 0 1px rgba(116,207,250,.3),0 0 15px rgba(46,143,211,.15)}
#rovor-workload-popup .rvq-ring:before{content:"";position:absolute;inset:11px;border-radius:50%;background:#071e35;box-shadow:inset 0 0 0 1px rgba(111,182,223,.2)}
#rovor-workload-popup .rvq-ring-core{position:relative;z-index:1;display:flex;flex-direction:column;align-items:center;gap:4px;line-height:1}
#rovor-workload-popup .rvq-ring-core strong{color:#f0fbff;font:700 18px/1 system-ui;font-variant-numeric:tabular-nums;white-space:nowrap}
#rovor-workload-popup .rvq-ring-core small{color:#9ccbe7;font:700 8px/1 system-ui;letter-spacing:.11em}
#rovor-workload-popup .rvq-ring-unknown{background:repeating-conic-gradient(from -90deg,#315b78 0deg 10deg,#142e46 10deg 20deg);box-shadow:0 0 0 1px rgba(116,207,250,.15)}
#rovor-workload-popup .rvq-ring-unknown .rvq-ring-core strong{color:#afc8d7;font-size:22px}
#rovor-workload-popup .rvq-ring-copy,#rovor-workload-popup .rvq-cloud-ring-copy{min-width:0;display:grid;gap:9px;color:#d9f3ff;font:11px/1.45 system-ui;overflow-wrap:anywhere}
#rovor-workload-popup .rvq-ring-copy strong{display:block;color:#d9f3ff;font:600 11px/1.5 system-ui}
#rovor-workload-popup .rvq-ring-copy .rvq-evidence{margin:0}
#rovor-workload-popup .rvq-cloud-ring-layout{margin-top:10px;padding:9px 0;grid-template-columns:76px minmax(0,1fr)}
#rovor-workload-popup .rvq-cloud-ring-layout .rvq-ring{width:76px;height:76px;box-shadow:0 0 0 1px rgba(116,207,250,.25)}
#rovor-workload-popup .rvq-cloud-ring-layout .rvq-ring:before{inset:9px}
#rovor-workload-popup .rvq-cloud-ring-layout .rvq-ring-core strong{font-size:15px}
#rovor-workload-popup .rvq-cloud-ring-layout .rvq-ring-core small{font-size:7px}
@media(max-width:380px){#rovor-workload-popup .rvq-ring-layout{grid-template-columns:80px minmax(0,1fr);gap:9px}#rovor-workload-popup .rvq-ring-layout .rvq-ring{width:80px;height:80px}#rovor-workload-popup .rvq-ring-layout .rvq-ring:before{inset:9px}#rovor-workload-popup .rvq-ring-layout .rvq-ring-core strong{font-size:15px}#rovor-workload-popup .rvq-ring-layout .rvq-ring-core small{font-size:7px}}
/* Visible nine-slot quota dashboard above verbose evidence panels. */
#rovor-workload-popup .rvq-overview{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:0 0 15px}
#rovor-workload-popup .rvq-overview-tile{min-width:0;display:flex;flex-direction:column;align-items:center;justify-content:start;gap:8px;padding:12px 8px 11px;text-decoration:none;cursor:pointer;touch-action:manipulation;border:1px solid rgba(83,159,211,.4);border-radius:11px;background:linear-gradient(145deg,#0c304e,#051b32);text-align:center}
#rovor-workload-popup .rvq-overview-tile[hidden]{display:none!important}
#rovor-workload-popup .rvq-overview-alert{border:1px solid #9ab9e8;padding:4px 7px;color:#e7f4ff;background:#1a3e60;font:700 9px system-ui;letter-spacing:.07em}
#rovor-workload-popup .rvq-overview-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 12px}
#rovor-workload-popup .rvq-overview-controls button{min-height:44px;padding:8px 12px;background:#0a2948;color:#b9dbef;border:1px solid #3d779f;cursor:pointer;font:700 11px system-ui}
#rovor-workload-popup .rvq-overview-controls button[aria-pressed="true"]{background:#185784;color:#f0faff;border-color:#a2dfff}
#rovor-workload-popup .rvq-overview-controls button:focus-visible{outline:2px solid #d5f2ff;outline-offset:2px}
#rovor-workload-popup .rvq-filter-note{font:11px/1.4 system-ui;color:#94c4e5}
#rovor-workload-popup .rvq-overview-rings{display:flex;justify-content:center;align-items:flex-start;gap:7px;flex-wrap:wrap}
#rovor-workload-popup .rvq-overview-ring-group{display:flex;flex-direction:column;align-items:center;gap:5px}
#rovor-workload-popup .rvq-ring-label{color:#a9cde7;font:700 9px/1.25 system-ui;letter-spacing:.04em}
#rovor-workload-popup .rvq-overview .rvq-ring-traffic{width:48px;height:48px;opacity:.84}
#rovor-workload-popup .rvq-overview .rvq-ring-traffic:before{inset:7px}
#rovor-workload-popup .rvq-overview .rvq-ring-traffic .rvq-ring-core strong{font-size:11px}
#rovor-workload-popup .rvq-overview .rvq-ring-traffic .rvq-ring-core small{font-size:6px}
#rovor-workload-popup .rvq-overview-tile:hover,#rovor-workload-popup .rvq-overview-tile:focus-visible{border-color:#b9eaff;outline:2px solid #87c9fa;outline-offset:1px;background:#103b60}
#rovor-workload-popup .rvq-overview-drill{color:#a9dfff;font:700 10px/1.35 system-ui;letter-spacing:.05em;margin-top:auto}
#rovor-workload-popup .rvq-source-notes{margin-top:12px;color:#9bc4dd;font:11px/1.55 system-ui}
#rovor-workload-popup .rvq-source-notes summary{cursor:pointer;color:#a9e5ff;padding:8px 0}
#rovor-workload-popup .rvq-source-notes p{margin:6px 0}
#rovor-workload-popup .rvq-jump-nav{display:flex;flex-wrap:wrap;gap:7px;margin:10px 0 14px}
#rovor-workload-popup .rvq-jump-nav a{display:inline-flex;align-items:center;min-height:44px;padding:9px 12px;border:1px solid rgba(92,178,233,.48);background:#0b2949;color:#c7edff;text-decoration:none;font:700 11px system-ui;letter-spacing:.04em}
#rovor-workload-popup .rvq-jump-nav a:hover,#rovor-workload-popup .rvq-jump-nav a:focus-visible{outline:2px solid #8ccffc;outline-offset:1px}
#rovor-workload-popup .rvq-details-heading{color:#b9e8ff;font:700 12px/1.5 system-ui;letter-spacing:.1em;margin:20px 0 9px}
#rovor-workload-popup .rvq-overview-requests{color:#d4efff;font:700 11px/1.35 system-ui;text-align:center}
#rovor-workload-popup .rvq-overview-intervals{display:flex;justify-content:center;gap:7px;flex-wrap:wrap;width:100%}
#rovor-workload-popup .rvq-overview-hourly{color:#9bdfff;font:700 10px/1.35 system-ui;text-align:center}
#rovor-workload-popup .rvq-overview-minute{color:#b3edff;font:700 10px/1.35 system-ui;text-align:center}
#rovor-workload-popup .rvq-activity{margin:12px 0 0;color:#a2d9fa;font:700 10px/1.5 system-ui;letter-spacing:.03em}
#rovor-workload-popup .rvq-activity strong{color:#e6faff}
#rovor-workload-popup .rvq-activity span{display:block;color:#8ba9bc;font:10px/1.4 system-ui;letter-spacing:0}
#rovor-workload-popup .rvq-mistral-reference{margin:12px 0;padding:10px;border:1px solid rgba(105,189,236,.33);border-radius:9px;background:rgba(2,24,43,.66);color:#a7d5ed;font:10px/1.5 system-ui}
#rovor-workload-popup .rvq-mistral-reference>strong{display:block;font:700 10px/1.4 system-ui;color:#9ee0ff;letter-spacing:.06em}
#rovor-workload-popup .rvq-mistral-reference p{margin:7px 0;color:#a4c8dc}
#rovor-workload-popup .rvq-mistral-reference table{width:100%;border-collapse:collapse;font:10px/1.5 system-ui}
#rovor-workload-popup .rvq-mistral-reference th,#rovor-workload-popup .rvq-mistral-reference td{padding:5px 3px;border-bottom:1px solid rgba(101,168,208,.2);text-align:left;overflow-wrap:anywhere}
#rovor-workload-popup .rvq-mistral-reference th{color:#a6dfff;font-weight:700}
#rovor-workload-popup .rvq-mistral-reference .rvq-limit-mismatch{color:#f0c5a4}
#rovor-workload-popup .rvq-activity.rvq-unreported{color:#8ba9bc}
 #rovor-workload-popup .rvq-minute{margin:8px 0;color:#a1e6ff;font:700 10px/1.5 system-ui}
#rovor-workload-popup .rvq-minute strong{color:#ecfbff}
#rovor-workload-popup .rvq-minute span{display:block;color:#89afc3;font:10px/1.4 system-ui}
#rovor-workload-popup .rvq-minute-unknown{color:#93b1c1}
#rovor-workload-popup .rvq-observed-model-minute{color:#bdeaff;font:600 10px/1.4 system-ui;margin-top:4px}
#rovor-workload-popup .rvq-hourly{margin:7px 0;color:#bbdff2;font:700 10px/1.5 system-ui;letter-spacing:.02em}
#rovor-workload-popup .rvq-hourly strong{color:#e6faff}
#rovor-workload-popup .rvq-hourly span{display:block;color:#8ba9bc;font:10px/1.4 system-ui;letter-spacing:0}
#rovor-workload-popup .rvq-hourly-unknown{color:#8ba9bc}
#rovor-workload-popup .rvq-observed-model-hour{color:#98d9ff;font:600 10px/1.4 system-ui;margin-top:3px}
#rovor-workload-popup .rvq-model-activity{margin:11px 0 3px;padding:12px 0;border-bottom:1px solid rgba(110,181,217,.16);font:11px/1.5 system-ui;color:#9bc6dc}
#rovor-workload-popup .rvq-model-activity>strong{font:700 10px system-ui;letter-spacing:.1em;color:#a7e5ff}
#rovor-workload-popup .rvq-model-activity>p{margin:6px 0 9px;color:#9bbbd0}
#rovor-workload-popup .rvq-observed-models{list-style:none;padding:0;margin:8px 0 0;display:grid;gap:12px}
#rovor-workload-popup .rvq-observed-model{min-width:0}
#rovor-workload-popup .rvq-observed-model-top{display:flex;justify-content:space-between;flex-wrap:wrap;gap:5px;color:#d8f2ff;font:600 11px/1.5 system-ui;overflow-wrap:anywhere}
#rovor-workload-popup .rvq-observed-model-top>strong{white-space:nowrap;color:#a9d7ef}
#rovor-workload-popup .rvq-observed-model .rvq-track{height:7px;margin:5px 0}
#rovor-workload-popup .rvq-observed-model-meta{color:#8fb6cd;font:10px/1.4 system-ui}
#rovor-workload-popup .rvq-overview-name{color:#d8f2ff;font:700 12px/1.35 system-ui;min-height:32px;max-width:100%;overflow-wrap:anywhere}
#rovor-workload-popup .rvq-overview .rvq-ring{width:68px;height:68px}
#rovor-workload-popup .rvq-overview .rvq-ring:before{inset:9px}
#rovor-workload-popup .rvq-overview .rvq-ring-core strong{font-size:12px}
#rovor-workload-popup .rvq-overview .rvq-ring-core small{font-size:9px}
#rovor-workload-popup .rvq-overview .rvq-ring-unknown .rvq-ring-core strong{font-size:18px}
#rovor-workload-popup .rvq-overview-source{color:#91c3dd;font:700 10px/1.3 system-ui;letter-spacing:.03em;overflow-wrap:anywhere}
@media(max-width:1150px){#rovor-workload-popup .rvq-overview{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:650px){
 #rovor-workload-popup .rvq-overview{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-bottom:11px}
 #rovor-workload-popup .rvq-overview-tile{padding:10px 6px;gap:6px}
 #rovor-workload-popup .rvq-overview-name{min-height:0;font-size:12px}
 #rovor-workload-popup .rvq-overview-source{font-size:10px}
 #rovor-workload-popup .rvq-head{margin-bottom:8px;gap:6px}
 #rovor-workload-popup .rvq-head .rvq-sub{display:none}
 #rovor-workload-popup .rvq-board>.rvq-sub{font-size:10px;margin-bottom:8px!important}
 #rovor-workload-popup .rvq-stats{gap:5px;margin-bottom:9px}
 #rovor-workload-popup .rvq-stat{padding:8px 9px}
 #rovor-workload-popup .rvq-stat-label{font-size:8px;margin-bottom:4px}
 #rovor-workload-popup .rvq-stat-value{font-size:15px}
}
#rovor-workload-popup .rvq-model-head{display:flex;justify-content:space-between;align-items:start;gap:10px;margin-bottom:12px}
#rovor-workload-popup .rvq-model-name{font:600 12px/1.42 system-ui;color:#d7efff;overflow-wrap:anywhere;min-width:0}
#rovor-workload-popup .rvq-percent{color:#c5efff;font:700 19px/1 system-ui;white-space:nowrap;font-variant-numeric:tabular-nums}
#rovor-workload-popup .rvq-percent span{font:700 9px system-ui;color:#91bfdb;margin-left:4px}
#rovor-workload-popup .rvq-unknown-tag{font:700 9px system-ui;color:#a6c2d2;letter-spacing:.07em;white-space:nowrap}
#rovor-workload-popup .rvq-track{display:block;height:10px;background:#102a42;border:1px solid #356888;border-radius:9px;overflow:hidden}
#rovor-workload-popup .rvq-track>i{display:block;height:100%;border-radius:9px;background:linear-gradient(90deg,#236ca6,#64ccff);box-shadow:0 0 11px rgba(90,205,255,.6)}
#rovor-workload-popup .rvq-track.rvq-near-limit>i{background:linear-gradient(90deg,#b16f37,#ffca6a)}
#rovor-workload-popup .rvq-unknown{background:repeating-linear-gradient(120deg,#142f45 0 7px,#285069 7px 10px)}
#rovor-workload-popup .rvq-model-info{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
#rovor-workload-popup .rvq-info-label{display:block;color:#82adc9;font:700 9px system-ui;letter-spacing:.11em;margin-bottom:5px}
#rovor-workload-popup .rvq-model-info strong{display:block;color:#d9f3ff;font:600 11px/1.5 system-ui;overflow-wrap:anywhere}
#rovor-workload-popup .rvq-evidence{margin-top:12px;color:#83a8bf;font:10px/1.4 system-ui}
#rovor-workload-popup .rvq-evidence span{margin:0 2px}
#rovor-workload-popup .rvq-more{border-top:1px solid rgba(126,190,219,.2)}
#rovor-workload-popup .rvq-more summary{cursor:pointer;padding:14px 0;color:#8dd7ff;font:600 11px system-ui}
#rovor-workload-popup .rvq-more summary:focus-visible{outline:2px solid #7dccfa;outline-offset:2px}
#rovor-workload-popup .rvq-footnote{font:11px/1.6 system-ui;color:#98bfd3;margin:16px 1px 0}
@media(max-width:800px){#rovor-workload-popup .rvq-grid{grid-template-columns:1fr}#rovor-workload-popup .rvq-stats{grid-template-columns:repeat(2,minmax(0,1fr))}#rovor-workload-popup .rvq-stat:last-child{grid-column:1/-1}}
@media(max-width:500px){#rovor-workload-popup .rvq-board{padding:13px!important}#rovor-workload-popup .rvq-provider-head{padding:13px 11px;gap:8px}#rovor-workload-popup .rvq-provider-status{max-width:105px;white-space:normal}#rovor-workload-popup .rvq-provider-content{padding:0 12px 4px}#rovor-workload-popup .rvq-head{gap:10px}#rovor-workload-popup .rvq-stat{padding:10px}#rovor-workload-popup .rvq-stat-value{font-size:17px}#rovor-workload-popup .rvq-model-info{gap:7px}}
`;
function mount(){
 if(document.getElementById('rvq-style'))return;
 listenForQuotaInteraction();
 const s=document.createElement('style');s.id='rvq-style';s.textContent=css;document.head.append(s);
}
function render(data,live,cloud=null,hourly=null,minute=null,geminiProject=null){
 mount();
 const cloudFresh=cloud?.execution_source==='cloud_provider'&&Number.isFinite(cloud.observed_at)&&
   Math.abs(Date.now()-cloud.observed_at)<=15000&&Array.isArray(cloud.providers)&&cloud.providers.length<=20;
 const cloudProviders=cloudFresh?new Map(cloud.providers.filter(p=>p&&typeof p.provider==='string').map(p=>[p.provider,p])):new Map();
 const cloudAttempts=cloudFresh&&Array.isArray(cloud.attempts)&&cloud.attempts.length<=500?cloud.attempts:[];
 // When the Mac is off, cloud provider credentials and past gateway inventory
 // remain distinguishable: this is NOT a live Mac connection.
 const connections=Array.isArray(data?.connections)?data.connections:
   cloudFresh?cloud.providers.filter(p=>p?.credentials_configured===true&&typeof p.provider==='string')
     .map(p=>({provider:p.provider,name:p.provider,connection_count:1,enabled_count:0})) : [];
 const activity=macActivity(data,live);
 // The one-hour aggregate has its own signed report and completeness gate.
 // Do not derive it from the rolling 24h percentage or cached history.
 const hourActivity=macActivity(hourly,live,'1h');
 const minuteActivity=macActivity(minute,live,'1m');
 const quota=live&&Array.isArray(data?.quota?.records)?data.quota.records.filter(q=>{const t=Date.parse(q?.fetched_at||'');const age=Date.now()-t;return Number.isFinite(age)&&age>=-5000&&age<=900000&&(!q.reset_at||Date.parse(q.reset_at)>Date.now());}):[];
 // Sanitized slot status is optional to preserve compatibility with older Mac reporters.
 // Never infer which specific account is enabled from a provider-level enabled count.
 const observedSlots=Array.isArray(data?.connection_slots)?data.connection_slots:null;
 const bySlot=observedSlots?new Map(observedSlots.map(s=>[s.provider+':'+s.account_slot,s])):null;
 const slots=[];
 for(const group of connections){
   const count=Math.max(0,Math.min(100,Number(group.connection_count)||0));
   for(let n=1;n<=count;n++){
     const evidence=bySlot?.get(group.provider+':'+n);
     slots.push({group,account_slot:n,enabled:typeof evidence?.enabled==='boolean'?evidence.enabled:null});
   }
 }
 const resets=quota.map(q=>Date.parse(q.reset_at||'')).filter(t=>Number.isFinite(t)&&t>Date.now());
 const next=resets.length?new Date(Math.min(...resets)).toISOString():null;
 const enabled=live&&observedSlots?slots.filter(s=>s.enabled===true).length:null;
 const coverage=live?new Set(quota.map(q=>q.provider+':'+q.account_slot)).size:null;
 const attentionCount=slots.filter(slot=>needsSetupReview(cloudProviders.get(slot.group.provider))).length;
 if(!attentionCount)overviewFilter='all';
 const summary='<div class="rvq-stats"><div class="rvq-stat"><span class="rvq-stat-label">REPORTED CONNECTION SLOTS</span><strong class="rvq-stat-value">'+fmt(slots.length)+'</strong></div>'+
 '<div class="rvq-stat"><span class="rvq-stat-label">PROVIDERS WITH MAC LIMIT DATA</span><strong class="rvq-stat-value">'+(coverage===null?'—':fmt(coverage)+' / '+fmt(slots.length))+'</strong><span class="rvq-stat-secondary">Limit records: '+(live?fmt(quota.length):'—')+'</span></div>'+
 '<div class="rvq-stat"><span class="rvq-stat-label">NEXT REPORTED RESET</span><strong class="rvq-stat-value rvq-small">'+esc(prettyTime(next))+'</strong></div></div>';
 const checked=data?.snapshot_at&&Number.isFinite(Date.parse(data.snapshot_at))?' · gateway inventory observed '+esc(prettyTime(data.snapshot_at)):'';
 return '<section class="wl-card rvq-board"><div class="rvq-head"><div><span class="rvq-eyebrow">ROVOR DIGITAL / OMNIROUTE INTELLIGENCE</span><h3 class="rvq-heading">All configured AI connections</h3><p class="rvq-sub">Nine provider connections, exact recorded traffic, and verified quotas, kept separate. Tap a provider for the complete technical report.</p></div><span class="rvq-status">'+(live?'FRESH OMNIROUTE INVENTORY':cloudFresh?'CLOUD LEDGER ONLY':slots.length?'MAC REPORT STALE':'NO FRESH REPORT')+'</span></div>'+
 '<nav class="rvq-jump-nav" aria-label="Workload dashboard sections"><a href="#rvq-connections">CONNECTIONS</a><a href="#rvq-review">REVIEW</a><a href="#rvq-team">WORKERS</a><a href="#rvq-reports">REPORTS</a></nav>'+
 summary+'<p class="rvq-sub" style="margin:0 0 12px">Enabled according to gateway: '+(enabled===null?'Unknown':fmt(enabled)+' / '+fmt(slots.length))+checked+'. Gateway quota cache and verified cloud ledger limits are separate scopes; do not add their counters.</p>'+
 (slots.length?(attentionCount?'<div class="rvq-overview-controls" role="group" aria-label="Provider filter"><button type="button" data-rvq-filter="all" aria-pressed="'+(overviewFilter==='all')+'">ALL '+fmt(slots.length)+'</button><button type="button" data-rvq-filter="attention" aria-pressed="'+(overviewFilter==='attention')+'">SETUP / REVIEW '+fmt(attentionCount)+'</button><span class="rvq-filter-note" aria-live="polite">'+(overviewFilter==='attention'?'Showing '+fmt(attentionCount)+' connections with setup or human-review gates':'Showing all '+fmt(slots.length)+' configured connections')+'</span></div>':'')+'<div id="rvq-connections" class="rvq-overview" aria-label="Configured provider overview. Select any provider for its complete report">'+slots.map((slot,i)=>overviewSlot(slot,quota,live,cloudProviders.get(slot.group.provider),i,providerActivity(activity,slot.group.provider),providerActivity(hourActivity,slot.group.provider),providerActivity(minuteActivity,slot.group.provider))).join('')+'</div>':'')+
 '<div id="rvq-review" class="rvq-review-entry"><strong>OWNER PASS / FAIL REVIEWS</strong>'+
 '<p>This Cloudflare usage viewer is read-only and cannot save owner decisions. Open your existing owner-private Site to view drafts and record PASS or FAIL; controls appear after the draft loads.</p>'+
 '<a href="https://rovor-private-hud.mm98z652cq.chatgpt.site/" target="_blank" rel="noopener noreferrer">Open authenticated owner review queue</a></div>'+
 '<div id="rvq-team">'+cloudEmployeeUsage(cloudAttempts,cloudFresh)+localEmployeeSection(data?.workforce,live)+'</div>'+
 '<h4 class="rvq-details-heading">PROVIDER REPORTS · EXPAND ANY PROVIDER</h4>'+
 '<div id="rvq-reports" class="rvq-grid">'+(slots.length?slots.map((slot,i)=>card(slot.group,quota,live,i,slot,cloudProviders.get(slot.group.provider),cloudAttempts,providerActivity(activity,slot.group.provider),providerActivity(hourActivity,slot.group.provider),providerActivity(minuteActivity,slot.group.provider),geminiProject)).join(''):'<p class="rvq-sub">No configured provider inventory received. Connect the existing private telemetry reporter; nine connections cannot be inferred from setup history.</p>')+'</div>'+
 '<details class="rvq-source-notes"><summary>DATA SOURCES & VERIFICATION RULES</summary><p>Connection slots are anonymous positions in the latest OmniRoute inventory, not stable identities across reordering. Mac traffic percentages are shares of recorded provider requests, NOT quota usage. Local quota rings are cached gateway limits; separate cloud quota rings require recent verified ledger evidence. Cloud admission can be disabled even if a local connection is enabled. No inference is initiated here. Unknown or expired resets are never guessed.</p></details></section>';
}
// Preserve owner inspection context even when live evidence must be refreshed.
function captureState(root){
 const board=root?.classList?.contains('rvq-board')?root:root?.querySelector?.('.rvq-board');
 if(!board||typeof board.querySelectorAll!=='function')return null;
 const cards=[...board.querySelectorAll('[data-rvq-slot]')];
 const state={details:[],scrolls:[],focused:null};
 for(const card of cards){
  const key=card.getAttribute('data-rvq-slot');
  const details=[...card.querySelectorAll('details')];
  details.forEach((d,i)=>{
   if(d.open)state.details.push({key,index:i});
  });
  const scrolls=[...card.querySelectorAll('.rvq-job-list')];
  scrolls.forEach((list,i)=>{if(list.scrollTop)state.scrolls.push({key,index:i,top:list.scrollTop})});
 }
 const other=[...board.querySelectorAll('.rvq-staff-list,.rvq-emp-grid')];
 other.forEach((node,i)=>{if(node.scrollTop)state.scrolls.push({key:'$other',index:i,top:node.scrollTop})});
 const active=document.activeElement;
 if(active&&board.contains(active)){
  if(active.matches?.('button[data-rvq-filter]'))state.focusedFilter=active.getAttribute('data-rvq-filter');
  const card=active.closest('[data-rvq-slot]');
  if(card&&active.tagName==='SUMMARY'){
   const details=[...card.querySelectorAll('details')];
   state.focused={key:card.getAttribute('data-rvq-slot'),index:details.indexOf(active.parentElement)};
  }
 }
 return state;
}
function restoreState(root,state){
 if(!state)return;
 const board=root?.classList?.contains('rvq-board')?root:root?.querySelector?.('.rvq-board');
 if(!board||typeof board.querySelectorAll!=='function')return;
 const cards=[...board.querySelectorAll('[data-rvq-slot]')];
 const getCard=key=>cards.find(card=>card.getAttribute('data-rvq-slot')===key);
 for(const item of state.details){
  const d=getCard(item.key)?.querySelectorAll('details')[item.index];
  if(d)d.open=true;
 }
 for(const item of state.scrolls){
  const els=item.key==='$other'?[...board.querySelectorAll('.rvq-staff-list,.rvq-emp-grid')]:
    [...(getCard(item.key)?.querySelectorAll('.rvq-job-list')||[])];
  if(els[item.index])els[item.index].scrollTop=item.top;
 }
 if(state.focusedFilter){
  const button=[...board.querySelectorAll('button[data-rvq-filter]')].find(b=>b.getAttribute('data-rvq-filter')===state.focusedFilter);
  button?.focus({preventScroll:true});
 }
 if(state.focused){
  const d=getCard(state.focused.key)?.querySelectorAll('details')[state.focused.index];
  d?.querySelector('summary')?.focus({preventScroll:true});
 }
}
let started=false;
function start(){
 if(started)return;
 started=true;
 let busy=false,last=null,lastInventory=null,lastCloud=null,lastHourly=null,lastMinute=null,updated=0;
 const isOriginal=n=>n.querySelector('h3')?.textContent?.trim()==='YOUR OMNIROUTE CONNECTIONS';
 // After first render the heading changes, so the old placeholder selector
 // cannot find the board again. Keep the replacement selectable for live sync.
 const slot=()=>[...document.querySelectorAll('#rovor-workload-popup .wl-card')].find(
   n=>!n.hidden&&(n.classList.contains('rvq-board')||isOriginal(n)));
 async function sync(){
   if(busy||document.hidden)return;
   const original=slot();if(!original)return;
   if(Date.now()-updated<5000){
     if(!original.classList.contains('rvq-board')){
       const state=captureState(original);
       original.outerHTML=render(last||lastInventory,!!last,lastCloud,lastHourly,lastMinute);
       restoreState(slot(),state);
     }
     return;
   }
   busy=true;
   // Serialize the complete two-source refresh, not just the local gateway fetch.
   // A slow cloud ledger read must not overlap another scheduled refresh.
   try {
   let fresh=null;
   // The main 24h HUD view has already fetched and validated this report.
   // Reuse it rather than make a second network request every ten seconds.
   const shared=window.ROVOR_LIVE_OMNIROUTE_SNAPSHOT?.();
   if(shared?.source==='local_omniroute_read_only_bridge'&&shared.period==='24h'&&
      Array.isArray(shared.connections)){
     const age=Date.now()-Date.parse(shared.snapshot_at);
     if(Number.isFinite(age)&&age>=-5000&&age<=15000)fresh=shared;
   }
   if(!fresh)try{
     const response=await fetch('/api/hud/omniroute?period=24h',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(8000)});
     if(response.ok){
       const data=await response.json(),age=Date.now()-Date.parse(data.snapshot_at);
       if(data.source==='local_omniroute_read_only_bridge'&&Array.isArray(data.connections)&&Number.isFinite(age)&&age>=-5000&&age<=15000)fresh=data;
     }
   }catch{}
   // Independently fetch the 1h report. A stale or incomplete 1h report
   // must not generate a zero-activity claim, even with fresh 24h inventory.
   let hourly=null;
   if(fresh)try{
     const response=await fetch('/api/hud/omniroute?period=1h',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(8000)});
     if(response.ok){
       const data=await response.json(),age=Date.now()-Date.parse(data.snapshot_at);
       if(data.source==='local_omniroute_read_only_bridge'&&data.period==='1h'&&
          Number.isFinite(age)&&age>=-5000&&age<=15000)hourly=data;
     }
   }catch{}
   // Read an actual rolling 60-second gateway aggregate. No model call is
   // initiated and zero is only shown when all model rows are accounted for.
   let minute=null;
   if(fresh)try{
     const response=await fetch('/api/hud/omniroute?period=1m',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(8000)});
     if(response.ok){
       const data=await response.json(),age=Date.now()-Date.parse(data.snapshot_at);
       if(data.source==='local_omniroute_read_only_bridge'&&data.period==='1m'&&
          Number.isFinite(age)&&age>=-5000&&age<=15000)minute=data;
     }
   }catch{}
   // Preserve only the last known provider/slot inventory through outages.
   // Never retain or display stale quota percentages as live.
   if(fresh)lastInventory={connections:fresh.connections,connection_slots:fresh.connection_slots,snapshot_at:fresh.snapshot_at};
   // Private same-origin cloud ledger is a separate read-only source.
   // Do not cache it through disconnects as a fresh state.
   let cloud=null;
   try{
     const response=await fetch('/api/ghost/status',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(8000)});
     if(response.ok){
       const d=await response.json();
       if(d?.execution_source==='cloud_provider'&&Number.isFinite(d.observed_at)&&
          Math.abs(Date.now()-d.observed_at)<=15000&&Array.isArray(d.providers)&&d.providers.length<=20)cloud=d;
     }
   }catch{}
   let geminiProject=null;
   // Site and Cloudflare readers are same-origin; the original private Site
   // may not have this optional route and must show no project samples.
   try{
    const response=await fetch('/api/hud/gemini/project-quota',{
     credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(8000)});
    if(response.ok){
     const item=await response.json();
     if(item?.source==='google_cloud_monitoring'&&typeof item.status==='string')geminiProject=item;
    }
   }catch{}
   lastCloud=cloud;last=fresh;lastHourly=hourly;lastMinute=minute;updated=Date.now();
   const target=slot();if(target){
     const state=captureState(target);
     target.outerHTML=render(fresh||lastInventory,!!fresh,cloud,hourly,minute,geminiProject);
     restoreState(slot(),state);
   }
   } finally {
     busy=false;
   }
 }
 // Only the original placeholder triggers a new observer sync. Otherwise
 // rendering into the observed subtree could create an infinite event loop.
 const observer=new MutationObserver(()=>{
   if([...document.querySelectorAll('#rovor-workload-popup .wl-card')].some(
       n=>!n.hidden&&isOriginal(n)))void sync();

 });
 observer.observe(document.body,{childList:true,subtree:true});
 // Refresh the EXISTING popup even after its original heading was replaced.
 // Do not poll or render when the document is hidden or popup is absent.
 setInterval(()=>{if(slot())void sync();},10000);
 void sync();
}
return {render,start,captureState,restoreState};
})();
