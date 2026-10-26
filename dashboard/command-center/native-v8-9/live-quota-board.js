/* ROVOR Digital: truthful per-provider quota instruments in the EXISTING HUD drawer.
 * No model calls, worker mutations, invented limits, or guessed reset times.
 */
window.ROVOR_QUOTA_BOARD=(()=>{
'use strict';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>typeof n==='number'&&Number.isFinite(n)?n.toLocaleString():'—';
const pretty=s=>{
 const key=String(s||'').toLowerCase().replace(/[^a-z0-9]/g,'');
 return ({google:'Google AI Studio',gemini:'Gemini',groq:'Groq',nvidia:'NVIDIA NIM',openrouter:'OpenRouter',mistral:'Mistral',cloudflare:'Cloudflare Workers AI',cloudflareworkersai:'Cloudflare Workers AI',sambanova:'SambaNova',cohere:'Cohere',huggingface:'Hugging Face'})[key]||String(s||'Provider').replace(/[-_]/g,' ');
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
function meter(q){
 const pct=Math.max(0,Math.min(100,Number(q.used_percent)||0));
 const left=Math.max(0,Number(q.total)-Number(q.used));
 const caution=pct>=90?' rvq-near-limit':'';
 return '<div class="rvq-model"><div class="rvq-model-head"><div class="rvq-model-name">'+esc(q.model_id)+'</div><div class="rvq-percent">'+pct.toFixed(1)+'%<span> USED</span></div></div>'+
 '<div class="rvq-track'+caution+'" role="progressbar" aria-label="Reported quota used" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+pct.toFixed(1)+'"><i style="width:'+pct.toFixed(1)+'%"></i></div>'+
 '<div class="rvq-model-info"><div><span class="rvq-info-label">REMAINING ALLOWANCE</span><strong>'+fmt(left)+' / '+fmt(q.total)+' '+esc(q.unit)+'</strong></div><div><span class="rvq-info-label">RESET WINDOW</span><strong>'+esc(resetText(q.reset_at))+'</strong></div></div>'+
 '<div class="rvq-evidence">OMNIROUTE CACHED REPORT <span>·</span> '+esc(prettyTime(q.fetched_at))+' <span>·</span> Account '+fmt(q.account_slot)+'</div></div>';
}
function unknownModel(m){
 return '<div class="rvq-model"><div class="rvq-model-head"><div class="rvq-model-name">'+esc(m?.name||'Model allowance unavailable')+'</div><div class="rvq-unknown-tag">UNVERIFIED</div></div>'+
 '<div class="rvq-track rvq-unknown" role="img" aria-label="Provider quota unknown"></div>'+
 '<div class="rvq-model-info"><div><span class="rvq-info-label">REMAINING ALLOWANCE</span><strong>Unknown</strong></div><div><span class="rvq-info-label">RESET WINDOW</span><strong>Not reported</strong></div></div>'+
 (typeof m?.requests==='number'?'<div class="rvq-evidence">'+fmt(m.requests)+' recorded requests · not quota usage</div>':'')+'</div>';
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
 const q=p.quota;
 const time=Number(q?.observed_at);
 const active=q?.status==='verified'&&Number.isFinite(time)&&time<=Date.now()+300000&&time>Date.now()-90*60000;
 const used=Number(q?.used),limit=Number(q?.limit);
 const reset=q?.resets_at==null?null:new Date(q.resets_at);
 if(active&&Number.isSafeInteger(used)&&Number.isSafeInteger(limit)&&limit>0&&used>=0&&used<=limit&&
    (reset===null||(Number.isFinite(reset.getTime())&&reset.getTime()>Date.now()))){
   const pct=Math.max(0,Math.min(100,100*used/limit)).toFixed(1);
   result.push('<span>Verified cloud limit · '+fmt(used)+' / '+fmt(limit)+' '+esc(q.unit||'units')+'</span>');
   result.push('<div class="rvq-track" role="progressbar" aria-label="Verified cloud ledger quota used" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+pct+'"><i style="width:'+pct+'%"></i></div>');
   result.push('<span>Cloud reset: '+esc(reset?resetText(reset.toISOString()):'Not reported')+'</span>');
 }else result.push('<span>Cloud quota and reset: unknown / not currently verified</span>');
 result.push('</div>');return result.join('');
}

function jobHistory(cloud,attempts,provider){
 if(!cloud)return '<div class="rvq-jobs rvq-jobs-unavailable">CLOUD JOB HISTORY · unavailable (connection not verified)</div>';
 const rows=Array.isArray(attempts)?attempts.filter(a=>a&&a.provider===provider).slice(0,15):[];
 const pending=rows.filter(a=>a.status==='needs_review'&&a.human_review!=='pass'&&a.human_review!=='fail').length;
 const summary='CLOUD JOBS · '+fmt(rows.length)+' recent receipt'+(rows.length===1?'':'s')+(pending?' · '+fmt(pending)+' awaiting review':'');
 if(!rows.length)return '<div class="rvq-jobs"><strong>'+summary+'</strong><p>No recorded cloud inference jobs for this provider. Connection or model-catalog checks are not jobs.</p></div>';
 const items=rows.map(a=>{
  const model=typeof a.actual_model==='string'&&a.actual_model.trim()? 'Actual model: '+esc(a.actual_model):
   'Actual model: unverified'+(typeof a.requested_model==='string'&&a.requested_model?' · requested '+esc(a.requested_model):'');
  const when=Number.isFinite(a.finished_at)?a.finished_at:Number.isFinite(a.started_at)?a.started_at:null;
  const time=when&&Number.isFinite(when)&&when>0?prettyTime(new Date(when).toISOString()):'Time unavailable';
  const used=Number.isSafeInteger(a.tokens_input)&&a.tokens_input>=0&&Number.isSafeInteger(a.tokens_output)&&a.tokens_output>=0?
   fmt(a.tokens_input)+' input / '+fmt(a.tokens_output)+' output tokens':'Token counts unverified';
  const review=a.human_review==='pass'?'PASS — owner reviewed':
   a.human_review==='fail'?'FAIL — owner reviewed':'No owner PASS/FAIL recorded';
  return '<li class="rvq-job"><div class="rvq-job-head"><strong>'+esc(a.title||a.task_id||'Untitled job')+'</strong><span>'+esc(a.status||'status unknown').replaceAll('_',' ')+'</span></div>'+
   '<div class="rvq-job-meta">Employee: '+esc(a.employee||'Unattributed')+' · '+esc(time)+'</div>'+
   '<div class="rvq-job-meta">'+model+'</div>'+
   '<div class="rvq-job-meta">'+esc(used)+' · '+esc(review)+'</div></li>';
 }).join('');
 return '<details class="rvq-jobs"><summary>'+summary+'</summary><ol class="rvq-job-list">'+items+'</ol><p class="rvq-job-note">Historical inference receipts, not proof the provider is executing a job now. PASS/FAIL can only be recorded through authorized review controls.</p></details>';
}
function gatewayUsage(data,live,provider){
 if(!live||!Array.isArray(data?.models))return '';
 const models=data.models.filter(m=>m&&m.provider===provider&&Number.isSafeInteger(m.requests)&&m.requests>=0);
 if(!models.length)return '<div class="rvq-usage">OmniRoute model usage: no attributed requests in the reported model data.</div>';
 const count=models.reduce((sum,m)=>sum+m.requests,0);
 const tokens=models.every(m=>Number.isSafeInteger(m.tokens)&&m.tokens>=0)?
  ' · '+fmt(models.reduce((sum,m)=>sum+m.tokens,0))+' recorded tokens':' · tokens not fully reported';
 const coverage=data.usage_coverage==='complete_aggregate'?'':' · partial model coverage';
 return '<div class="rvq-usage">OmniRoute attributed model requests (24h): '+fmt(count)+tokens+coverage+'</div>';
}
function unattributedWorkers(data,live){
 if(!live||!Array.isArray(data?.workforce?.employees))return '';
 const employees=data.workforce.employees.filter(e=>e&&e.latest_job).slice(0,12);
 if(!employees.length)return '';
 const entries=employees.map(e=>'<li class="rvq-job"><strong>'+esc(e.name||e.id||'Worker')+'</strong> · '+esc(e.status||'status unknown').replaceAll('_',' ')+
  '<div class="rvq-job-meta">'+esc(e.latest_job?.title||e.latest_job?.task||'Job title unavailable')+'</div>'+
  '<div class="rvq-job-meta">Configured route: '+esc(e.latest_job?.assigned_route||'unknown')+' · actual upstream provider/model not independently attributed</div></li>').join('');
 return '<details class="rvq-unattributed"><summary>Local Mac employee jobs · '+fmt(employees.length)+' latest records (provider unverified)</summary>'+
  '<ol class="rvq-job-list">'+entries+'</ol><p class="rvq-job-note">Local SQLite receipts cannot be assigned to a specific provider without the upstream request receipt; they are never counted as cloud-provider jobs.</p></details>';
}

function card(group,quota,live,index,slot,cloud,attempts,data){
 const entries=live&&slot.enabled!==false?quota.filter(q=>q.provider===group.provider&&q.account_slot===slot.account_slot&&
   (!q.reset_at||Date.parse(q.reset_at)>Date.now())):[];
 const rows=entries.map(meter);
 if(!rows.length)rows.push(unknownModel(null));
 const first=rows.slice(0,2).join('');
 const extra=rows.length>2?'<details class="rvq-more"><summary>Show '+(rows.length-2)+' more model'+(rows.length===3?'':'s')+'</summary>'+rows.slice(2).join('')+'</details>':'';
 const state= !live?'DISCONNECTED':slot.enabled===false?'DISABLED':slot.enabled===true?'ENABLED · NOT TESTED':'ENABLEMENT UNKNOWN';
 const evidence=entries.length?'LIMITS REPORTED':'QUOTA UNKNOWN';
 return '<article class="rvq-provider"><div class="rvq-provider-head"><div class="rvq-provider-icon">'+esc(pretty(group.name||group.provider).slice(0,1).toUpperCase())+'</div><div class="rvq-provider-ident"><span class="rvq-provider-index">CONNECTION '+String(index+1).padStart(2,'0')+' / '+esc(pretty(group.name||group.provider))+'</span><h4>'+esc(pretty(group.name||group.provider))+' · Slot '+fmt(slot.account_slot)+'</h4><p>'+state+'</p></div><div class="rvq-provider-status'+(entries.length?' rvq-reported':'')+'">'+evidence+'</div></div>'+
 '<div class="rvq-provider-content">'+first+extra+gatewayUsage(data,live,group.provider)+cloudEvidence(cloud)+jobHistory(cloud,attempts,group.provider)+'</div></article>';
}
const css=`
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
#rovor-workload-popup .rvq-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;align-items:start}
#rovor-workload-popup .rvq-provider{min-width:0;background:linear-gradient(145deg,rgba(13,48,77,.88),rgba(5,25,44,.95));border:1px solid rgba(90,164,204,.38);border-radius:12px;overflow:hidden;box-shadow:inset 0 1px rgba(153,219,252,.07)}
#rovor-workload-popup .rvq-provider-head{display:flex;align-items:center;gap:10px;padding:15px;border-bottom:1px solid rgba(95,175,213,.22)}
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
#rovor-workload-popup .rvq-jobs{padding:12px 0;border-top:1px solid rgba(111,193,231,.25);color:#a8cce3;font:11px/1.55 system-ui}
#rovor-workload-popup .rvq-jobs>summary,#rovor-workload-popup .rvq-unattributed>summary{cursor:pointer;color:#a0ddff;font-weight:700;list-style-position:inside}
#rovor-workload-popup .rvq-jobs p{margin:8px 0}
#rovor-workload-popup .rvq-jobs-unavailable{opacity:.8}
#rovor-workload-popup .rvq-usage{padding:12px 0;color:#c8e9fc;font:11px/1.5 system-ui}
#rovor-workload-popup .rvq-job-list{list-style:none;margin:10px 0 0;padding:0;max-height:260px;overflow-y:auto}
#rovor-workload-popup .rvq-job{padding:11px 3px;border-bottom:1px solid rgba(111,193,231,.17);overflow-wrap:anywhere}
#rovor-workload-popup .rvq-job-head{display:flex;justify-content:space-between;gap:10px;color:#def4ff}
#rovor-workload-popup .rvq-job-head>span{flex:none;color:#9fcbdf;text-transform:uppercase;font-size:9px;letter-spacing:.03em}
#rovor-workload-popup .rvq-job-meta{margin-top:5px;color:#a2c3d5;font-size:10px}
#rovor-workload-popup .rvq-job-note{font:10px/1.5 system-ui;color:#8eb9cf}
#rovor-workload-popup .rvq-unattributed{margin:12px 0;padding:13px 16px;border:1px solid rgba(100,178,215,.3);border-radius:9px;color:#bddfee}
#rovor-workload-popup .rvq-footnote{font:11px/1.6 system-ui;color:#98bfd3;margin:16px 1px 0}
@media(max-width:800px){#rovor-workload-popup .rvq-grid{grid-template-columns:1fr}#rovor-workload-popup .rvq-stats{grid-template-columns:repeat(2,minmax(0,1fr))}#rovor-workload-popup .rvq-stat:last-child{grid-column:1/-1}}
@media(max-width:500px){#rovor-workload-popup .rvq-board{padding:13px!important}#rovor-workload-popup .rvq-provider-head{padding:13px 11px;gap:8px}#rovor-workload-popup .rvq-provider-status{max-width:105px;white-space:normal}#rovor-workload-popup .rvq-provider-content{padding:0 12px 4px}#rovor-workload-popup .rvq-head{gap:10px}#rovor-workload-popup .rvq-stat{padding:10px}#rovor-workload-popup .rvq-stat-value{font-size:17px}#rovor-workload-popup .rvq-model-info{gap:7px}}
`;
function mount(){
 if(document.getElementById('rvq-style'))return;
 const s=document.createElement('style');s.id='rvq-style';s.textContent=css;document.head.append(s);
}
function render(data,live,cloud=null){
 mount();
 const cloudFresh=cloud?.execution_source==='cloud_provider'&&Number.isFinite(cloud.observed_at)&&
   Math.abs(Date.now()-cloud.observed_at)<=15000&&Array.isArray(cloud.providers)&&cloud.providers.length<=20;
 const cloudProviders=cloudFresh?new Map(cloud.providers.filter(p=>p&&typeof p.provider==='string').map(p=>[p.provider,p])):new Map();
 // When the Mac is off, cloud provider credentials and past gateway inventory
 // remain distinguishable: this is NOT a live Mac connection.
 const connections=Array.isArray(data?.connections)?data.connections:
   cloudFresh?cloud.providers.filter(p=>p?.credentials_configured===true&&typeof p.provider==='string')
     .map(p=>({provider:p.provider,name:p.provider,connection_count:1,enabled_count:0})) : [];
 const quota=live&&Array.isArray(data?.quota?.records)?data.quota.records.filter(q=>!q.reset_at||Date.parse(q.reset_at)>Date.now()):[];
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
 const summary='<div class="rvq-stats"><div class="rvq-stat"><span class="rvq-stat-label">REPORTED CONNECTION SLOTS</span><strong class="rvq-stat-value">'+fmt(slots.length)+'</strong></div>'+
 '<div class="rvq-stat"><span class="rvq-stat-label">LIMIT REPORTS</span><strong class="rvq-stat-value">'+(live?quota.length:'—')+'</strong></div>'+
 '<div class="rvq-stat"><span class="rvq-stat-label">NEXT REPORTED RESET</span><strong class="rvq-stat-value rvq-small">'+esc(prettyTime(next))+'</strong></div></div>';
 const checked=data?.snapshot_at&&Number.isFinite(Date.parse(data.snapshot_at))?' · gateway inventory observed '+esc(prettyTime(data.snapshot_at)):'';
 return '<section class="wl-card rvq-board"><div class="rvq-head"><div><span class="rvq-eyebrow">ROVOR DIGITAL / OMNIROUTE INTELLIGENCE</span><h3 class="rvq-heading">All configured AI connections</h3><p class="rvq-sub">Each configured connection gets its own status and quota/reset meter. Actual inference is unverified without a model execution receipt.</p></div><span class="rvq-status">'+(live?'FRESH OMNIROUTE INVENTORY':cloudFresh?'CLOUD LEDGER ONLY':'REPORT DISCONNECTED')+'</span></div>'+
 summary+'<p class="rvq-sub" style="margin:0 0 12px">Enabled according to gateway: '+(enabled===null?'Unknown':fmt(enabled)+' / '+fmt(slots.length))+checked+'. Gateway quota cache and verified cloud ledger limits are separate scopes; do not add their counters.</p>'+
 '<div class="rvq-grid">'+(slots.length?slots.map((s,i)=>card(s.group,quota,live,i,s,cloudProviders.get(s.group.provider),cloudFresh?cloud.attempts:[],data)).join(''):'<p class="rvq-sub">No configured provider inventory received. Connect the existing private telemetry reporter; nine connections cannot be inferred from setup history.</p>')+'</div>'+unattributedWorkers(data,live)+
 '<p class="rvq-footnote">Connection slots are anonymous positions in the latest OmniRoute inventory, not stable identities across reordering. Local quota bars are cached gateway limits; separate cloud bars require recent verified ledger evidence. Cloud admission can be disabled even if a local connection is enabled. No inference is initiated here. Unknown or expired resets are never guessed.</p></section>';
}
let started=false;
function start(){
 if(started)return;started=true;
 let busy=false,last=null,lastInventory=null,lastCloud=null,updated=0;
 const originalSlot=()=>[...document.querySelectorAll('#rovor-workload-popup .wl-card')].find(
   n=>!n.hidden&&n.querySelector('h3')?.textContent?.trim()==='YOUR OMNIROUTE CONNECTIONS');
 // Once render() replaces the original card, keep finding the mounted quota board.
 const slot=()=>originalSlot()||[...document.querySelectorAll('#rovor-workload-popup .rvq-board')].find(n=>!n.hidden);
 async function sync(){
   if(busy||document.hidden)return;
   const original=slot();if(!original)return;
   if(last&&Date.now()-updated<5000){original.outerHTML=render(last,true,lastCloud);return;}
   busy=true;let fresh=null;
   try{
     const response=await fetch('/api/hud/omniroute?period=24h',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(8000)});
     if(response.ok){
       const data=await response.json(),age=Date.now()-Date.parse(data.snapshot_at);
       if(data.source==='local_omniroute_read_only_bridge'&&Array.isArray(data.connections)&&Number.isFinite(age)&&age>=-5000&&age<=15000)fresh=data;
     }
   }catch{}finally{busy=false;}
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
   lastCloud=cloud;last=fresh;updated=Date.now();
   const target=slot();if(target)target.outerHTML=render(fresh||lastInventory,!!fresh,cloud);
 }
 // Observe the *original* panel only; watching our replacement would cause
 // MutationObserver -> render -> MutationObserver feedback loops.
 const observer=new MutationObserver(()=>{if(originalSlot())void sync();});
 observer.observe(document.body,{childList:true,subtree:true});
 // Re-query the mounted board on each tick: a one-shot observer never refetches
 // changing usage, even if the private telemetry endpoint stays fresh.
 setInterval(()=>{if(slot())void sync();},5000);
 void sync();
}
return {render,start};
})();
