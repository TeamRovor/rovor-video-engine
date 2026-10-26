/* ROVOR visual-reference HUD: art is illustrative; data is pinned to GitHub SHA. */
(() => {
 'use strict';
 const REPO='TeamRovor/rovor-video-engine';
 const API=`https://api.github.com/repos/${REPO}`;
 const RAW=`https://raw.githubusercontent.com/${REPO}`;
 const $=id=>document.getElementById(id);
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const state={immersive:window.matchMedia('(min-width: 1024px) and (min-aspect-ratio: 3/2)').matches,mode:'unverified',tasks:[],routes:{},sha:'',lastVerified:0,rateLimit:null,rateReset:null,view:'dashboard',motion:true,earthMotion:false,artMode:'exact',busy:false,focus:null,dialogOrigin:null,commandSearch:'',lastError:''};
 const statuses=['active','ready','blocked','done'];
 const title={tasks:'ACTIVE TASKS',resources:'RESOURCE USAGE',activity:'RECENT ACTIVITY',systems:'SYSTEM HEALTH',quota:'API QUOTA',media:'MEDIA / SOURCE FEED',github:'GITHUB CONTROL',settings:'HUD SETTINGS',command:'COMMAND CORE',dashboard:'DASHBOARD',task:'TASK INSPECTOR'};
 const taskUrl=id=>`https://github.com/${REPO}/blob/${state.sha||'main'}/coordination/tasks.json`;
 function cacheStatus(){
   const b=$('sourceStatus');b.classList.toggle('verified',state.mode==='verified');b.classList.toggle('failed',state.mode==='error');
   b.textContent=state.mode==='verified'?'GITHUB VERIFIED':state.mode==='loading'?'VERIFYING SOURCE…':'SOURCE UNVERIFIED';
   $('lastVerified').textContent=state.mode==='verified'?`SHA ${state.sha.slice(0,10)} · ${new Date(state.lastVerified).toLocaleTimeString()}`:'Live data unavailable';
 }
 function safeQueue(payload){
   if(!payload||!Array.isArray(payload.tasks))throw new Error('Invalid GitHub task queue');
   const ids=new Set();
   return payload.tasks.map(t=>{
     if(!t||typeof t.id!=='string'||!t.id||ids.has(t.id)||!statuses.includes(t.status))throw new Error('Unexpected task in queue');
     ids.add(t.id);return {id:t.id,title:String(t.title||t.id),status:t.status,priority:Number.isFinite(t.priority)?t.priority:999,
       owner:typeof t.owner==='string'?t.owner:'',updated_at:typeof t.updated_at==='string'?t.updated_at:'',
       next_action:typeof t.next_action==='string'?t.next_action:'',blocker:typeof t.blocker==='string'?t.blocker:'',
       depends_on:Array.isArray(t.depends_on)?t.depends_on.filter(x=>typeof x==='string'):[]};
   });
 }
 async function requestJson(url,signal){
   const response=await fetch(url,{cache:'no-store',signal,headers:{Accept:'application/json'}});
   if(!response.ok)throw new Error(`GitHub unavailable (${response.status})`);
   if(url===`${API}/commits/main`){const remaining=response.headers.get('x-ratelimit-remaining');state.rateLimit=/^\d+$/.test(remaining||'')?Number(remaining):null;const reset=response.headers.get('x-ratelimit-reset');state.rateReset=/^\d+$/.test(reset||'')?Number(reset)*1000:null;}
   return response.json();
 }
 async function verify({manual=false}={}){
   if(state.busy)return;
   if(!manual&&document.hidden)return;
   state.busy=true;state.mode='loading';cacheStatus();
   const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),12000);
   try{
      const head=await requestJson(`${API}/commits/main`,controller.signal);
      if(!/^[a-f\d]{40}$/i.test(head?.sha||''))throw new Error('Source identity could not be verified');
      const sha=head.sha;
      const [queue,routing]=await Promise.all([
        requestJson(`${RAW}/${sha}/coordination/tasks.json`,controller.signal),
        requestJson(`${RAW}/${sha}/coordination/work-routing.json`,controller.signal)
      ]);
      if(!routing||!routing.tasks||typeof routing.tasks!=='object'||Array.isArray(routing.tasks))throw new Error('Routing source unavailable');
      const tasks=safeQueue(queue);
      const ids=new Set(tasks.map(t=>t.id));
      const missing=tasks.filter(t=>!(t.id in routing.tasks));
      const stale=Object.keys(routing.tasks).filter(id=>!ids.has(id));
      state.tasks=tasks;state.routes=routing.tasks;state.sha=sha;state.missing=missing;state.stale=stale;
      state.lastVerified=Date.now();state.lastError='';state.mode='verified';
   }catch(error){state.lastError=error?.name==='AbortError'?'Request timed out':String(error.message||error);state.mode='error';}
   finally{clearTimeout(timeout);state.busy=false;cacheStatus();document.dispatchEvent(new CustomEvent('rovor:source',{detail:{mode:state.mode,verified:state.mode==='verified'}}));if(!$('overlay').hidden)renderView();}
 }
 const fmtDate=v=>{const d=new Date(v);return isNaN(d.getTime())?'Not recorded':d.toLocaleString()};
 function counts(){const c=Object.fromEntries(statuses.map(k=>[k,0]));state.tasks.forEach(t=>c[t.status]++);return c;}
 function tag(status){return `<span class="tag ${esc(status)}">${esc(status.toUpperCase())}</span>`;}
 function warn(msg){return `<div class="alert">${esc(msg)}</div>`;}
 function stats(){const c=counts();return `<div class="stat-grid">${statuses.map(k=>`<div class="data-card"><small>${esc(k.toUpperCase())}</small><strong>${c[k]}</strong></div>`).join('')}</div>`;}
 function dataGate(){if(state.mode!=='verified')return warn('LIVE GITHUB DATA NOT VERIFIED. The background graphic contains example numbers only, not live worker activity. '+(state.lastError?'Reason: '+state.lastError:''));return '';}
 function renderTasks(){
   const c=counts();const base=state.tasks.filter(t=>t.status!=='done');
   const header=`${dataGate()}<div class="data-card"><h2>GitHub task queue ${state.mode==='verified'?'— SHA '+esc(state.sha.slice(0,12)):'— source unavailable'}</h2><p>Claimed or assigned work does not mean an employee is running. Example counts in the artwork are illustrative.</p>${state.mode==='verified'?`<div class="big-number">${base.length} <small>open</small></div>`:''}</div>`;
   if(state.mode!=='verified')return header;
   return header+stats()+`<div class="filterbar"><input type="search" id="taskSearch" aria-label="Search task title and ID" placeholder="Search tasks" value="${esc(state.taskFilter||'')}"><select id="taskFilter" aria-label="Filter task status"><option value="open">All open</option><option value="active">Claimed</option><option value="ready">Ready</option><option value="blocked">Blocked</option><option value="done">Done</option></select></div><div id="taskResults" aria-live="polite"></div>`;
 }
 function renderTaskResults(){let q=(state.taskFilter||'').toLowerCase().trim(),status=state.taskStatus||'open';const filtered=state.tasks.filter(t=>(status==='open'?t.status!=='done':t.status===status)&&(!q||`${t.title} ${t.id} ${t.owner}`.toLowerCase().includes(q))).sort((a,b)=>(statuses.indexOf(a.status)-statuses.indexOf(b.status))||(a.priority-b.priority)||(a.title.localeCompare(b.title)));
   const container=$('taskResults');if(!container)return;container.innerHTML=`<p class="subdued">${filtered.length} matching tasks</p>`+filtered.slice(0,75).map(t=>`<button type="button" class="task-row" data-task="${esc(t.id)}"><strong>${esc(t.title)}</strong><span>${tag(t.status)} · ${esc(t.id)} · P${t.priority}</span></button>`).join('');
   if(filtered.length>75)container.insertAdjacentHTML('beforeend','<p class="subdued">Showing first 75; refine the search for more.</p>');
 }
 function renderTask(t){return `<div class="data-card"><h2>${esc(t.title)}</h2><p>${tag(t.status)}</p><div class="kv"><span>Task ID</span><strong>${esc(t.id)}</strong></div><div class="kv"><span>Owner assignment</span><strong>${esc(t.owner||'Unclaimed')}</strong></div><div class="kv"><span>Priority</span><strong>${t.priority}</strong></div><div class="kv"><span>Updated</span><strong>${esc(fmtDate(t.updated_at))}</strong></div><div class="kv"><span>Dependencies</span><strong>${esc(t.depends_on.join(', ')||'None')}</strong></div></div>${t.next_action?`<div class="data-card"><h2>Next action</h2><p>${esc(t.next_action)}</p></div>`:''}${t.blocker?warn(t.blocker):''}${warn('A task claim is not a live computer session. This HUD cannot start a private Mac worker.')}<div class="buttons"><button data-view="tasks">← Task queue</button><a href="${taskUrl(t.id)}" target="_blank" rel="noopener noreferrer">View source ↗</a></div>`;}
 function renderResources(){if(state.mode!=='verified')return dataGate()+warn('CPU, GPU, memory and storage from the reference image are illustrative; no Mac hardware telemetry is connected.');const c=counts();const total=state.tasks.length;return `<div class="data-card"><h2>GitHub workload distribution</h2><p>These bars are task statuses, not CPU/GPU utilization. Hardware telemetry is unavailable.</p></div>`+statuses.map(k=>`<div class="data-card"><div class="kv"><span>${esc(k.toUpperCase())}</span><strong>${c[k]} / ${total}</strong></div><div class="bar"><i style="width:${total?100*c[k]/total:0}%"></i></div></div>`).join('')+warn('Host CPU, GPU, RAM and storage: NOT CONNECTED.');}
 function renderActivity(){if(state.mode!=='verified')return dataGate();const sorted=state.tasks.filter(t=>t.updated_at).sort((a,b)=>new Date(b.updated_at)-new Date(a.updated_at)).slice(0,15);return `<div class="data-card"><h2>Verified GitHub queue timestamps</h2><p>These records come from task metadata, not from a fabricated rendering log or camera feed.</p><div class="kv"><span>Verified HEAD</span><strong>${esc(state.sha.slice(0,12))}</strong></div><div class="kv"><span>Checked</span><strong>${esc(fmtDate(state.lastVerified))}</strong></div></div>`+sorted.map(t=>`<button class="task-row" data-task="${esc(t.id)}"><strong>${esc(t.title)}</strong><span>${esc(fmtDate(t.updated_at))} · ${esc(t.status.toUpperCase())}</span></button>`).join('');}
 function renderSystems(){const verified=state.mode==='verified';const missing=state.missing?.length||0,stale=state.stale?.length||0;return `<div class="data-card"><h2>What is actually verified?</h2><div class="kv"><span>GitHub queue</span><strong>${verified?'Verified source SHA':'NOT VERIFIED'}</strong></div><div class="kv"><span>Routing map</span><strong>${verified?(missing||stale?'ISSUES REPORTED':'COMPLETE'):'UNVERIFIED'}</strong></div><div class="kv"><span>Native Mac executor</span><strong>NOT PROVEN BY GITHUB</strong></div><div class="kv"><span>OmniRoute HTTP</span><strong>NOT MONITORED HERE</strong></div><div class="kv"><span>Video rendering</span><strong>NOT MONITORED HERE</strong></div></div>`+(verified?`<div class="data-card"><h2>Route coverage</h2><div class="big-number">${state.tasks.length-missing} / ${state.tasks.length}</div><p>${missing} missing, ${stale} stale routing rules</p></div>`:'')+warn('The screenshot’s “99% OPERATIONAL” and green online dots are decorative reference data, NOT actual system health.');}
 function renderQuota(){return `<div class="data-card"><h2>GitHub API rate-limiting</h2><p>This is the only remotely measured provider-limit information potentially exposed to this static page.</p><div class="kv"><span>Remaining (when readable)</span><strong>${state.rateLimit===null?'Not exposed':state.rateLimit}</strong></div><div class="kv"><span>Reset (when readable)</span><strong>${state.rateReset?esc(fmtDate(state.rateReset)):'Not exposed'}</strong></div></div>`+warn('The reference image’s “98% REMAINING”, 200,000 requests, and graph are sample artwork. OmniRoute and paid-provider quotas are NOT connected to this page.');}
 function renderMedia(){return `<div class="data-card"><h2>ROVOR video engine</h2><p>The visual “LIVE FEED” is illustration only. There is no accessible camera or verified live video stream.</p></div><div class="buttons"><a href="https://github.com/${REPO}/tree/main/evan-engine" target="_blank" rel="noopener noreferrer">Video-engine source ↗</a><a href="https://github.com/${REPO}/pulls" target="_blank" rel="noopener noreferrer">Pull requests ↗</a></div>`+warn('Video output, Final Cut, Moho, Blender and Mac runtime require separately authenticated local/worker connections.');}
 function renderGithub(){return `${dataGate()}<div class="data-card"><h2>GitHub source of truth</h2><div class="kv"><span>Repository</span><strong>${REPO}</strong></div><div class="kv"><span>Verified commit</span><strong>${state.sha?esc(state.sha.slice(0,16)):'Unavailable'}</strong></div><div class="kv"><span>Last check</span><strong>${state.lastVerified?esc(fmtDate(state.lastVerified)):'None'}</strong></div><div class="kv"><span>Task records</span><strong>${state.mode==='verified'?state.tasks.length:'Unverified'}</strong></div></div><div class="buttons"><a href="https://github.com/${REPO}" target="_blank" rel="noopener noreferrer">Repository ↗</a><a href="https://github.com/${REPO}/actions" target="_blank" rel="noopener noreferrer">Workflows ↗</a><a href="https://github.com/${REPO}/pulls" target="_blank" rel="noopener noreferrer">PRs ↗</a><button id="exportSnapshot">Export verified JSON</button></div>`;}
 function renderSettings(){return `<div class="data-card"><h2>Visual fidelity</h2><p>Exact image is the unmodified reference art, with interactive zones drawn over the original panel positions.</p><label class="toggle"><span>Exactly match the image (including its original green sample indicators)</span><input id="exactMode" type="checkbox" ${state.artMode==='exact'?'checked':''}></label><label class="toggle"><span>Immersive 1:1 edge-to-edge view (press I to exit)</span><input id="immersiveMode" type="checkbox" ${state.immersive?'checked':''}></label><label class="toggle"><span>Verified live data inside picture panels (L, desktop)</span><input id="liveOverlayMode" type="checkbox" ${window.ROVOR_LIVE_PANELS?.enabled?'checked':''}></label><label class="toggle"><span>Slow Earth rotation (optional: modifies the exact static artwork)</span><input id="earthMotionMode" type="checkbox" ${state.earthMotion?'checked':''}></label><label class="toggle"><span>Subtle orbit / Earth lighting motion</span><input id="motionMode" type="checkbox" ${state.motion?'checked':''}></label></div><div class="data-card"><h2>Display</h2><div class="buttons"><button id="fullScreenDrawer">Toggle fullscreen</button><button id="reloadData">Verify GitHub</button></div></div><p class="credits">Illustrative reference image provided in this conversation. Source of actual status: ${REPO} public GitHub data. Sample values are never treated as verified measurements.</p>`;}
 function renderCommands(){return `<div class="data-card"><h2>Interactive ROVOR command center</h2><p>Click a command or enter a task ID/title. Press Esc to exit.</p><div class="filterbar"><input id="commandSearch" type="search" aria-label="Search commands and tasks" placeholder="Search commands or task titles…" value="${esc(state.commandSearch||'')}"></div></div><div id="commandsList"></div>`;}
 function renderCommandResults(){const q=(state.commandSearch||'').toLowerCase().trim();const sections=[['tasks','Tasks'],['resources','Resources'],['activity','Activity'],['systems','System health'],['quota','API quota'],['media','Media'],['github','GitHub'],['settings','Settings']].filter(x=>!q||x.join(' ').toLowerCase().includes(q));const tasks=state.mode==='verified'?state.tasks.filter(t=>t.status!=='done'&&`${t.id} ${t.title}`.toLowerCase().includes(q)).slice(0,16):[];const list=$('commandsList');if(!list)return;list.innerHTML=sections.map(([id,label])=>`<button type="button" class="task-row" data-view="${id}"><strong>${esc(label)}</strong><span>Open HUD panel ↗</span></button>`).join('')+tasks.map(t=>`<button type="button" class="task-row" data-task="${esc(t.id)}"><strong>${esc(t.title)}</strong><span>${esc(t.id)} · ${esc(t.status)}</span></button>`).join('')||'<p class="subdued">No matching commands.</p>';}
 function renderView(){const view=state.view;const panel=$('drawerContent');$('drawerTitle').textContent=title[view]||'ROVOR CONTROL';$('drawerSubtitle').textContent=state.mode==='verified'?'Live source verified against one pinned GitHub commit':'Source is not currently verified — artwork is illustrative';
   const renderer={tasks:renderTasks,resources:renderResources,activity:renderActivity,systems:renderSystems,quota:renderQuota,media:renderMedia,github:renderGithub,settings:renderSettings,command:renderCommands};
   panel.innerHTML=view==='task'&&state.selectedTask?renderTask(state.selectedTask):(renderer[view]||renderCommands)();
   if(view==='tasks'){if($('taskFilter'))$('taskFilter').value=state.taskStatus||'open';renderTaskResults();}
   if(view==='command')renderCommandResults();
 }
 function openView(view){if(view==='dashboard'){close();return;}state.view=view;state.dialogOrigin=document.activeElement;$('overlay').hidden=false;document.body.style.overflow='hidden';renderView();$('closeDrawer').focus();}
 function openTask(id){const task=state.tasks.find(t=>t.id===id);if(!task)return;state.selectedTask=task;state.view='task';renderView();}
 function close(){if($('overlay').hidden)return;$('overlay').hidden=true;document.body.style.overflow='';state.dialogOrigin?.focus?.();}
 function applySettings(){document.body.classList.toggle('immersive',state.immersive);document.body.classList.toggle('motion-off',!state.motion);document.body.classList.toggle('earth-motion-on',state.earthMotion&&state.motion);const earth=$('earthMotion');if(earth)earth.hidden=!(state.earthMotion&&state.motion);$('referenceArt').src=state.artMode==='exact'?'reference.png':'reference-blue.webp';}
 function exportData(){if(state.mode!=='verified')return;const output={source:'GitHub pinned',repository:REPO,sha:state.sha,verifiedAt:new Date(state.lastVerified).toISOString(),tasks:state.tasks,routingCoverage:{missing:state.missing.map(t=>t.id),stale:state.stale}};const blob=new Blob([JSON.stringify(output,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`ROVOR_verified_${state.sha.slice(0,9)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 document.addEventListener('click',event=>{
   if(event.target.closest('[data-close],#closeDrawer')){close();return;}
   const t=event.target.closest('[data-task]');if(t){openTask(t.dataset.task);return;}
   const view=event.target.closest('[data-view]');if(view){openView(view.dataset.view);return;}
   if(event.target.closest('#refresh,#refreshDrawer,#reloadData')){verify({manual:true});return;}
   if(event.target.closest('#commandButton')){openView('command');return;}
   if(event.target.closest('#immersiveButton')){state.immersive=!state.immersive;applySettings();return;}
   if(event.target.closest('#fullScreen,#fullScreenDrawer')){if(document.fullscreenElement)document.exitFullscreen?.();else document.documentElement.requestFullscreen?.().catch(()=>{});return;}
   if(event.target.closest('#exportSnapshot')){exportData();return;}
 });
 document.addEventListener('input',event=>{
   if(event.target.id==='taskSearch'){state.taskFilter=event.target.value;renderTaskResults();}
   if(event.target.id==='commandSearch'){state.commandSearch=event.target.value;renderCommandResults();}
   if(event.target.id==='immersiveMode'){state.immersive=event.target.checked;applySettings();}
   if(event.target.id==='exactMode'){state.artMode=event.target.checked?'exact':'blue';applySettings();}
   if(event.target.id==='motionMode'){state.motion=event.target.checked;applySettings();}
   if(event.target.id==='earthMotionMode'){state.earthMotion=event.target.checked;applySettings();}
   if(event.target.id==='liveOverlayMode'){window.ROVOR_LIVE_PANELS?.setEnabled(event.target.checked);}
 });
 document.addEventListener('change',event=>{if(event.target.id==='taskFilter'){state.taskStatus=event.target.value;renderTaskResults();}});
 document.addEventListener('keydown',event=>{
   if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();openView('command');return;}
   if(event.key==='Escape'){if(!$('overlay').hidden){close();return;}if(state.immersive){state.immersive=false;applySettings();}return;}
   if(event.key.toLowerCase()==='i'&&document.activeElement?.tagName!=='INPUT'&&$('overlay').hidden){state.immersive=!state.immersive;applySettings();return;}
   if(document.activeElement?.matches('input,textarea,select')||$('overlay').hidden===false)return;
   if(/^[1-5]$/.test(event.key)){event.preventDefault();openView(['dashboard','tasks','media','github','settings'][Number(event.key)-1]);}
 });
 $('overlay').addEventListener('keydown',event=>{if(event.key!=='Tab')return;const els=[...$('overlay').querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled])')].filter(el=>el.getClientRects().length);if(!els.length)return;const first=els[0],last=els[els.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}});
 document.addEventListener('visibilitychange',()=>document.body.classList.toggle('motion-off',!state.motion||document.hidden));
 applySettings();cacheStatus();verify();setInterval(()=>verify(),300000);
 if (typeof navigator!=='undefined' && 'serviceWorker' in navigator && location.protocol==='https:') {
   navigator.serviceWorker.register('./service-worker.js', {scope:'./'}).catch(()=>{});
 }
 window.ROVOR_HUD={state,verify,openView};
})();
