/* Loaded only by the authenticated local HUD bridge, never the public Pages HUD. */
window.ROVOR_START_OMNIROUTE=()=>{
  'use strict';
  const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const employees=['Walter','Mike','Jane','Jesse','Gale','Gus','Saul','Hank'];
  let selectedEmployee='';
  let snapshot=null,problem='Connecting to OmniRoute…',period='24h',tab='models',filter='',selected='',inFlight=false;
  let previewHost,previewOpen,popupHost,timer;
  const fresh=()=>snapshot&&Date.now()-Date.parse(snapshot.snapshot_at)<15000;
  const stamp=()=>snapshot?new Date(snapshot.snapshot_at).toLocaleTimeString():'—';
  const stateLabel=()=>fresh()?'CONNECTED · '+stamp():snapshot?'STALE · '+stamp():problem;
  const models=()=>(snapshot?.models||[]).filter(m=>m.requests!==null);
  const connections=()=>snapshot?.connections||[];
  const workers=()=>employees.map(name=>snapshot?.workforce?.employees?.find(e=>e.id===name.toLowerCase())||{id:name.toLowerCase(),name,status:'unknown',latest_job:null});
  const readable=x=>String(x||'unknown').replaceAll('_',' ');
  const workerCards=()=>workers().map(e=>{const j=e.latest_job;return `<section class="wl-card" style="${selectedEmployee===e.id?'border-color:#bceaff':''}"><h3>${esc(e.name)} · ${esc(readable(fresh()?e.status:'unknown'))}</h3><p class="wl-empty">${j?.current?'Recorded current work':'Latest recorded work'}: ${esc(j?.task||'No attributed worker record')}</p><p class="wl-empty">Assigned route: ${esc(j?.assigned_route||'Unknown')}<br>Configured model: ${esc(j?.configured_model||'Unknown')}<br>Actual upstream model: ${esc(j?.actual_model||'Not identified by receipt')}<br>Updated: ${j?.updated_at?esc(new Date(j.updated_at*1000).toLocaleString()):'Unknown'}<br>Queued: ${number(e.queued_jobs)} · Recorded running: ${number(e.running_jobs)}</p></section>`}).join('');
  const number=n=>n===null||n===undefined?'—':Number(n).toLocaleString();
  const meter=m=>fresh()&&m.requests!==null?`<span class="wl-meter" role="meter" aria-label="Share of recorded requests, not remaining quota" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${m.request_share_percent}"><i style="--wl-share:${m.request_share_percent}%"></i></span>`:'<small>Usage unavailable</small>';
  const linkState=()=>`<div class="wl-notice" role="status"><strong>${esc(stateLabel())}</strong><br>Read-only OmniRoute connection · polls every 5 seconds while open. Connections refresh every minute. Bars show share of recorded requests in ${period}; remaining quota and active jobs are separate, currently unavailable.</div>`;
  function paintPreview(){
    if(!previewHost?.isConnected)return;
    const scroll=previewHost.querySelector('.wl-compact-items')?.scrollTop||0;
    previewHost.innerHTML=`<div class="wl-compact"><div class="wl-compact-tabs"><button type="button" data-live-tab="models" aria-pressed="${tab==='models'}">OMNIROUTE <small>${snapshot?.connection_count??models().length}</small></button><button type="button" data-live-tab="employees" aria-pressed="${tab==='employees'}">EMPLOYEES <small>08</small></button></div><div class="wl-compact-meta">${esc(stateLabel())}</div><div class="wl-compact-items">${tab==='models'&&connections().length?connections().map(g=>`<button type="button" class="wl-compact-row" data-live-details><span class="wl-compact-name">${esc(g.name)}</span><span class="wl-compact-status">${g.connection_count} configured · ${models().filter(m=>m.provider===g.provider).length} used models</span></button>`).join(''):tab==='models'?models().map(m=>`<button type="button" class="wl-compact-row" data-live-model="${esc(m.id)}" style="grid-template-columns:minmax(0,1fr) minmax(30px,.7fr) 35px"><span class="wl-compact-name" title="${esc(m.id)}">${esc(m.name)}</span><span class="wl-compact-track" aria-hidden="true"><i style="display:block;height:100%;background:#86cfff;width:${fresh()&&m.request_share_percent!==null?m.request_share_percent:0}%"></i></span><span class="wl-compact-value">${fresh()&&m.request_share_percent!==null?Math.round(m.request_share_percent)+'%':'—'}</span></button>`).join(''):workers().map(e=>`<button type="button" class="wl-compact-row" data-live-employee="${e.id}"><span class="wl-compact-name">${esc(e.name)}</span><span class="wl-compact-status">${esc(readable(fresh()?e.status:'unknown'))}</span><span>↗</span></button>`).join('')}</div><div class="wl-compact-foot">${fresh()?number(snapshot.request_count)+' RECORDED REQUESTS · '+period:'AWAITING FRESH MEASUREMENTS'} <span>↗ DETAILS</span></div></div>`;
    previewHost.querySelector('.wl-compact-items').scrollTop=scroll;
  }
  function paintPopup(){
    if(!popupHost?.isConnected||document.getElementById('screen')?.hidden)return;
    const scroll=popupHost.querySelector('.wl-model-scroll')?.scrollTop||0;
    const focused=document.activeElement?.getAttribute('data-live-search')!==null&&document.activeElement?.hasAttribute('data-live-search');
    const cursor=focused?document.activeElement.selectionStart:0;
    const footnote=document.querySelector('.drawer-footnote');if(footnote)footnote.textContent='READ-ONLY OMNIROUTE · '+stateLabel()+' · REQUEST SHARE IS NOT REMAINING QUOTA OR LIVE WORKER LOAD.';
    const list=models().filter(m=>(m.name+' '+m.provider).toLowerCase().includes(filter.toLowerCase()));
    popupHost.innerHTML=`<div id="rovor-workload-popup">${linkState()}<div class="wl-toolbar"><button class="wl-button" data-live-tab="models">OMNIROUTE</button><button class="wl-button" data-live-tab="employees">EMPLOYEES</button><div class="wl-period">${['1h','24h','7d'].map(p=>`<button class="wl-button" data-live-period="${p}" aria-pressed="${period===p}">${p.toUpperCase()}</button>`).join('')}</div><div class="wl-kicker">${snapshot?.connection_count??'—'} configured connections · ${models().length} recorded models · ${snapshot?.usage_coverage==='complete_aggregate'?'complete aggregate':'partial / unknown coverage'}</div></div>${tab==='employees'?`<div class="wl-notice">Mac heartbeat: ${snapshot?.workforce?.heartbeat?.age_seconds??'unknown'} seconds ago · ${esc(readable(snapshot?.workforce?.heartbeat?.last_tick_dispatch))}. ${snapshot?.workforce?.unassigned_jobs??'Unknown'} jobs lack employee attribution. This is host heartbeat, not proof each employee is online.</div><div class="wl-employees-live">${workerCards()}</div>`:''}<input class="tool-input" data-live-search aria-label="Find model" placeholder="Find your model…" value="${esc(filter)}"><section class="wl-card"><h3>YOUR OMNIROUTE CONNECTIONS</h3>${connections().map(g=>`<p class="wl-empty">${esc(g.name)} · ${g.connection_count} configured · ${g.enabled_count} enabled</p>`).join('')||'<p class="wl-empty">Restart the Mac bridge to load your configured connections.</p>'}</section><section class="wl-card"><h3>MEASURED MODEL REQUESTS / ${period.toUpperCase()}</h3><p class="wl-empty">${number(snapshot?.request_count)} recorded requests. Models without attributable rows stay unknown rather than showing an invented zero. Only recorded models matched to your configured providers are listed; unused model identities are not guessed.</p><div class="wl-model-scroll" tabindex="0" style="max-height:44vh;overflow:auto"><div class="wl-models">${list.map(m=>`<button type="button" class="wl-model-entry" data-live-model="${esc(m.id)}" aria-pressed="${selected===m.id}"><span class="wl-row"><strong>${esc(m.name)}</strong><small>${fresh()?number(m.requests):'—'} requests</small></span>${meter(m)}<span class="wl-row"><small>${fresh()&&m.request_share_percent!==null?m.request_share_percent.toFixed(1)+'% of recorded requests':'No current attribution'}</small><small>${fresh()?number(m.tokens):'—'} tokens</small></span></button>`).join('')||'<p class="wl-empty">No matching model records available.</p>'}</div></div></section><section class="wl-card"><h3>QUOTA / EMPLOYEE STATUS</h3><p class="wl-empty">Provider limits and quota resets remain unavailable. Employee cards use worker records separately; configured models are not proof of an actual upstream model. Request-share bars do not represent quota remaining. No model calls are made by this HUD.</p></section></div>`;
    popupHost.querySelector('.wl-model-scroll').scrollTop=scroll;
    if(tab==='employees'){popupHost.querySelector('[data-live-search]').hidden=true;for(const card of popupHost.querySelectorAll('.wl-card'))if(!card.closest('.wl-employees-live'))card.hidden=true;}
    if(focused){const input=popupHost.querySelector('[data-live-search]');input.focus();input.setSelectionRange(cursor,cursor);}
  }
  function mountPreview(host,open){previewHost=host;previewOpen=open;paintPreview();}
  function mount(host){popupHost=host;paintPopup();}
  function redraw(){paintPreview();paintPopup();}
  async function poll(){
    if(inFlight||document.hidden)return;
    inFlight=true;
    try{
      const response=await (window.ROVOR_OMNIROUTE_REQUEST||fetch)('/api/hud/omniroute?period='+period,{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(10000)});
      if(!response.ok)throw Error('OmniRoute unavailable or pairing expired');
      const data=await response.json();
      if(data.source!=='local_omniroute_read_only_bridge'||data.period!==period||!Array.isArray(data.models)||data.models.length>10050||!Number.isFinite(Date.parse(data.snapshot_at)))throw Error('Invalid telemetry');
      const age=Date.now()-Date.parse(data.snapshot_at);if(age>15000||age< -5000)throw Error('Stale telemetry');
      snapshot=data;problem='';
    }catch{snapshot=null;problem='DISCONNECTED · no fresh usage';}
    finally{inFlight=false;redraw();clearTimeout(timer);timer=setTimeout(poll,5000);}
  }
  document.addEventListener('click',event=>{
    const b=event.target.closest('[data-live-tab],[data-live-period],[data-live-model],[data-live-details],[data-live-employee]');if(!b)return;
    if(b.dataset.liveTab){tab=b.dataset.liveTab;redraw();}
    else if(b.dataset.livePeriod){period=b.dataset.livePeriod;snapshot=null;redraw();poll();}
    else{if(b.dataset.liveEmployee){selectedEmployee=b.dataset.liveEmployee;tab='employees';}if(b.dataset.liveModel)selected=b.dataset.liveModel;if(b.closest('#workloadPanel'))previewOpen?.();else paintPopup();}
  });
  document.addEventListener('input',event=>{if(event.target.hasAttribute('data-live-search')){filter=event.target.value;paintPopup();}});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});
  window.ROVOR_WORKLOAD={mountPreview,mount,resetPopup(){popupHost=null;filter='';selected='';}};
  mountPreview(document.getElementById('workloadPanel'),()=>window.ROVOR_NATIVE.open('workload'));
  poll();
};
