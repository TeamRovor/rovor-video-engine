/* 16:9 ROVOR cockpit controls. Presentation only; source data comes from app.js. */
(function(root) {
  'use strict';
  const doc=root.document;
  if(!doc)return;
  const toolsButton=doc.getElementById('hudToolsBtn');
  const menu=doc.getElementById('hudTools');
  const closeButton=doc.getElementById('hudWorkspaceClose');
  const nav=doc.querySelector('.tabbar');
  function setTools(open) {
    doc.body.classList.toggle('hud-tools-open',!!open);
    toolsButton?.setAttribute('aria-expanded',String(!!open));
    if(menu)menu.inert=!open;
  }
  function syncWorkspace() {
    const current=doc.querySelector('[role="tab"][aria-selected="true"]');
    const open=!!current && current.dataset.tab!=='overview';
    doc.body.classList.toggle('hud-workspace-open',open);
    if(closeButton)closeButton.hidden=!open;
    if(open)setTools(false);
  }
  function openDashboard(){
    doc.getElementById('tab-button-overview')?.click();
    syncWorkspace();
  }
  function refresh(snapshot,state) {
    if(!doc.getElementById('sourceFeedState'))return;
    const live=state?.syncMode==='live';
    const mode=state?.syncMode||'loading';
    const commit=snapshot?.repo_snapshot?.commit;
    doc.getElementById('sourceFeedMode').textContent=live?'LIVE GITHUB':mode==='snapshot'?'HISTORICAL':mode==='error'?'DISCONNECTED':'VERIFYING';
    doc.getElementById('sourceFeedState').textContent=live?'Pinned source verified':mode==='snapshot'?'Offline snapshot, not live':mode==='error'?'GitHub unreachable':'Connecting to GitHub';
    doc.getElementById('sourceFeedCommit').textContent=commit?'SHA '+String(commit).slice(0,12):'Source SHA unavailable';
    doc.body.dataset.cockpitConnected=live?'true':'false';
  }
  toolsButton?.addEventListener('click',()=>setTools(!doc.body.classList.contains('hud-tools-open')));
  doc.addEventListener('click',event=>{
    if(!doc.body.classList.contains('hud-tools-open'))return;
    if(event.target.closest('#hudTools,#hudToolsBtn'))return;
    setTools(false);
  });
  menu?.addEventListener('click',event=>{
    if(event.target.closest('button'))setTools(false);
  });
  nav?.addEventListener('click',event=>{
    if(event.target.closest('[role="tab"]'))syncWorkspace();
  });
  nav?.addEventListener('keydown',event=>{
    if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'].includes(event.key)) {
      root.requestAnimationFrame?.(syncWorkspace);
    }
  });
  closeButton?.addEventListener('click',openDashboard);
  doc.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&doc.body.classList.contains('hud-tools-open'))setTools(false);
    if(!event.metaKey&&!event.ctrlKey&&!event.altKey&&!event.shiftKey&&/^[1-5]$/.test(event.key)) {
      root.requestAnimationFrame?.(syncWorkspace);
    }
  });
  // An inactive menu must not capture focus through an invisible overlay.
  setTools(false);
  syncWorkspace();
  root.RovorCinematicHUD={refresh,syncWorkspace,setTools};
})(typeof globalThis!=='undefined'?globalThis:this);
