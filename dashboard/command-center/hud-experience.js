/* Interactive ROVOR command console: readable public data, guarded UI-only actions. */
(function (root,factory) {
  const api=factory(root);
  if (typeof module==='object' && module.exports) module.exports=api;
  root.RovorExperience=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(root) {
  'use strict';
  const VIEWS=[
    {id:'overview',label:'Dashboard',hint:'Overview and priorities'},
    {id:'tasks',label:'Tasks',hint:'Search and filter work queue'},
    {id:'systems',label:'Systems',hint:'Verified capability boundaries'},
    {id:'repo',label:'GitHub',hint:'Repository map and source revision'},
    {id:'workers',label:'Workers',hint:'Assignments, not presence'}
  ];
  const SOURCE='https://github.com/TeamRovor/rovor-video-engine/blob/main/coordination/tasks.json';
  let snapshot=null,syncMode='loading',earth=null,previousFocus=null;
  let dialog=null,drawer=null,search=null,commandList=null,drawerBody=null,drawerTitle=null;
  let speedIndex=0,localPaused=false;
  const speeds=[{label:'SLOW',value:0.5},{label:'NORMAL',value:1},{label:'FAST',value:2}];
  function findTask(id) {
    const tasks=snapshot?.tasks||snapshot?.open_tasks||[];
    return tasks.find(t=>t.id===id)||null;
  }
  function commands(data) {
    const list=VIEWS.map(v=>({id:'view-'+v.id,title:'Open '+v.label,detail:v.hint,kind:'view',value:v.id}));
    list.push(
      {id:'refresh',title:'Refresh GitHub',detail:'Verify latest pinned queue',kind:'button',value:'refreshBtn'},
      {id:'motion',title:'Toggle HUD motion',detail:'Honor reduced motion settings',kind:'button',value:'motionBtn'},
      {id:'focus',title:'Toggle focus view',detail:'Reduce layout distractions',kind:'button',value:'focusBtn'},
      {id:'export',title:'Export verified snapshot',detail:'Includes source state and timestamp',kind:'button',value:'exportBtn'},
      {id:'fullscreen',title:'Toggle full screen',detail:'Browser permitting',kind:'fullscreen',value:''}
    );
    const tasks=(data?.tasks||data?.open_tasks||[]).filter(t=>t.status!=='done').slice(0,35);
    tasks.forEach(t=>list.push({id:'task-'+t.id,title:t.title||t.id,detail:t.id+' · '+(t.status||'unknown'),kind:'task',value:t.id}));
    return list;
  }
  function activeOverlay(){return dialog&&!dialog.hidden?dialog:drawer&&!drawer.hidden?drawer:null;}
  function showOverlay(node) {
    closeOverlay();
    previousFocus=document.activeElement;
    node.hidden=false;
    document.body.classList.add('hud-overlay-open');
  }
  function closeOverlay(){
    if(dialog)dialog.hidden=true;
    if(drawer)drawer.hidden=true;
    document.body.classList.remove('hud-overlay-open');
    if(previousFocus && typeof previousFocus.focus==='function')previousFocus.focus();
    previousFocus=null;
  }
  function navigate(view,taskId) {
    const tab=document.getElementById('tab-button-'+view);
    if(!tab)return;
    tab.click();
    if(view==='tasks'&&taskId) {
      const input=document.getElementById('taskSearch'),select=document.getElementById('statusFilter');
      if(select)select.value='all';
      if(input){input.value=taskId;input.dispatchEvent(new Event('input',{bubbles:true}));}
    }
    document.querySelector('main')?.scrollIntoView({behavior:motionAllowed()?'smooth':'instant',block:'start'});
    pulse(view);
  }
  function motionAllowed(){
    return !document.body.classList.contains('motion-paused') && !root.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
  }
  function pulse(name){
    const stage=document.getElementById('reactorStage');
    if(!stage||!motionAllowed())return;
    stage.classList.remove('hud-reactor-pulse');
    void stage.offsetWidth;
    stage.classList.add('hud-reactor-pulse');
  }
  function fullscreen(){
    if(document.fullscreenElement)return document.exitFullscreen?.().catch(()=>{});
    return document.documentElement.requestFullscreen?.().catch(()=>{});
  }
  function run(command) {
    if(!command)return;
    closeOverlay();
    if(command.kind==='view')navigate(command.value);
    else if(command.kind==='task')showTask(command.value);
    else if(command.kind==='button')document.getElementById(command.value)?.click();
    else if(command.kind==='fullscreen')fullscreen();
  }
  function renderCommands(value=''){
    if(!commandList)return;
    const term=value.trim().toLowerCase();
    const list=commands(snapshot).filter(x=>!term||[x.title,x.detail].join(' ').toLowerCase().includes(term)).slice(0,25);
    commandList.replaceChildren();
    if(!list.length){const empty=document.createElement('p');empty.className='muted';empty.textContent='No matching commands or tasks';commandList.append(empty);return;}
    list.forEach((c,i)=>{
      const button=document.createElement('button');
      button.type='button';button.className='hud-command-result';button.dataset.commandIndex=String(i);
      const left=document.createElement('span');left.textContent=c.title;
      const right=document.createElement('small');right.textContent=c.detail;
      button.append(left,right);
      button.addEventListener('click',()=>run(c));
      commandList.append(button);
    });
    commandList.firstElementChild?.classList.add('selected');
  }
  function showPalette(){
    if(!dialog)return;
    showOverlay(dialog);
    if(search){search.value='';renderCommands();search.focus();}
  }
  function addLine(parent,label,value){
    const row=document.createElement('div');row.className='hud-detail-row';
    const left=document.createElement('span');left.textContent=label;
    const right=document.createElement('strong');right.textContent=value===undefined||value===null?'Not available':String(value);
    row.append(left,right);parent.append(row);
  }
  function appendAction(parent,title,onClick){
    const button=document.createElement('button');button.type='button';button.className='hud-btn';button.textContent=title;
    button.addEventListener('click',onClick);parent.append(button);
  }
  function showTask(id){
    const task=findTask(id);
    if(!drawer||!task)return;
    showOverlay(drawer);drawerTitle.textContent=task.title||task.id;drawerBody.replaceChildren();
    addLine(drawerBody,'Task ID',task.id);
    addLine(drawerBody,'State',(task.status||'unknown').toUpperCase()+' · GitHub record only');
    addLine(drawerBody,'Priority',task.priority??'Not assigned');
    addLine(drawerBody,'Owner',task.owner||'Unclaimed');
    addLine(drawerBody,'Dependencies',(task.depends_on||[]).join(', ')||'None');
    if(task.next_action)addLine(drawerBody,'Next action',task.next_action);
    const warning=document.createElement('p');warning.className='hud-detail-warning';
    warning.textContent='A task claim is not proof of live execution. This dashboard cannot start a private computer worker.';
    drawerBody.append(warning);
    const actions=document.createElement('div');actions.className='hud-drawer-actions';
    appendAction(actions,'Locate in queue',()=>{closeOverlay();navigate('tasks',id);});
    appendAction(actions,'View GitHub source',()=>root.open?.(SOURCE,'_blank','noopener'));
    drawerBody.append(actions);
    drawer.querySelector('.hud-close')?.focus();
    pulse('task');
  }
  function showSystem(name){
    const system=(snapshot?.systems||[]).find(s=>s.name===name);
    if(!drawer||!system)return;
    showOverlay(drawer);drawerTitle.textContent=system.name;drawerBody.replaceChildren();
    addLine(drawerBody,'Declared state',(system.state||'unknown').toUpperCase());
    addLine(drawerBody,'Source',syncMode==='live'?'Latest verified GitHub snapshot':'Historical / unverified snapshot');
    const p=document.createElement('p');p.className='hud-detail-description';p.textContent=system.summary||'No description';drawerBody.append(p);
    const w=document.createElement('p');w.className='hud-detail-warning';w.textContent='This is capability classification from repository source, not a live host ping.';drawerBody.append(w);
    const actions=document.createElement('div');actions.className='hud-drawer-actions';
    appendAction(actions,'View system boundaries',()=>{closeOverlay();navigate('systems');});
    drawerBody.append(actions);drawer.querySelector('.hud-close')?.focus();
    pulse('system');
  }
  function showRouting(){
    if(!drawer||!snapshot)return;
    showOverlay(drawer);drawerTitle.textContent='Routing integrity';drawerBody.replaceChildren();
    const s=snapshot.repo_snapshot||{},h=snapshot.route_health||{};
    addLine(drawerBody,'Coverage',s.routing_coverage||'Unknown');
    addLine(drawerBody,'Routing rules',s.routing_rules);
    addLine(drawerBody,'Missing routes',(h.missing||[]).join(', ')||'None reported');
    addLine(drawerBody,'Obsolete routes',(h.stale||[]).join(', ')||'None reported');
    addLine(drawerBody,'Sync',syncMode==='live'?'GitHub verified':syncMode.toUpperCase());
    const actions=document.createElement('div');actions.className='hud-drawer-actions';
    appendAction(actions,'Open GitHub details',()=>{closeOverlay();navigate('repo');});
    drawerBody.append(actions);drawer.querySelector('.hud-close')?.focus();
  }
  function showHelp(){
    if(!drawer)return;
    showOverlay(drawer);drawerTitle.textContent='Command shortcuts';drawerBody.replaceChildren();
    [['Ctrl / ⌘ + K','Open command console'],['1 – 5','Navigate dashboard views'],['?','Show this shortcut guide'],['Esc','Close current panel'],['← / → while Earth focused','Rotate Earth manually']].forEach(x=>addLine(drawerBody,x[0],x[1]));
    drawer.querySelector('.hud-close')?.focus();
  }
  function setEarthPaused(next){
    localPaused=!!next;earth?.setPaused(localPaused);
    const btn=document.getElementById('earthPauseBtn');
    if(btn){btn.textContent=localPaused?'Resume Earth':'Pause Earth';btn.setAttribute('aria-pressed',String(localPaused));}
  }
  function setEarthSpeed(next){
    speedIndex=((next % speeds.length)+speeds.length)%speeds.length;
    earth?.setSpeed(speeds[speedIndex].value);
    const btn=document.getElementById('earthSpeedBtn');
    if(btn)btn.textContent='Earth · '+speeds[speedIndex].label;
  }
  function handleKey(event){
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();showPalette();return;}
    if(event.key==='Escape'&&activeOverlay()){event.preventDefault();closeOverlay();return;}
    const target=event.target,typing=/^(input|textarea|select)$/i.test(target?.tagName||'')||target?.isContentEditable;
    if(typing||event.altKey||event.metaKey||event.ctrlKey||activeOverlay())return;
    if(event.key==='?'){event.preventDefault();showHelp();return;}
    if(/^[1-5]$/.test(event.key)){event.preventDefault();navigate(VIEWS[Number(event.key)-1].id);return;}
    if((event.key==='ArrowLeft'||event.key==='ArrowRight')&&target?.id==='coreAction'){
      event.preventDefault();earth?.nudge(event.key==='ArrowRight'?12:-12);
    }
  }
  function render(data,state){
    snapshot=data;syncMode=state?.syncMode||'loading';
    const nav=document.querySelector('.tabbar');
    if(nav)nav.dataset.verified=syncMode==='live'?'true':'false';
  }
  function setup(){
    if(typeof document==='undefined')return;
    earth=root.RovorEarth?.boot(document,root)||null;
    dialog=document.getElementById('hudCommandDialog');
    drawer=document.getElementById('hudDrawer');
    search=document.getElementById('hudCommandSearch');
    commandList=document.getElementById('hudCommandResults');
    drawerTitle=document.getElementById('hudDrawerTitle');
    drawerBody=document.getElementById('hudDrawerBody');
    document.getElementById('hudCommandBtn')?.addEventListener('click',showPalette);
    document.getElementById('coreAction')?.addEventListener('click',showPalette);
    document.getElementById('hudFullscreenBtn')?.addEventListener('click',fullscreen);
    document.getElementById('hudHelpBtn')?.addEventListener('click',showHelp);
    document.getElementById('earthPauseBtn')?.addEventListener('click',()=>setEarthPaused(!localPaused));
    document.getElementById('earthSpeedBtn')?.addEventListener('click',()=>setEarthSpeed(speedIndex+1));
    document.getElementById('earthResetBtn')?.addEventListener('click',()=>earth?.reset());
    document.getElementById('routingInspectBtn')?.addEventListener('click',showRouting);
    search?.addEventListener('input',()=>renderCommands(search.value));
    search?.addEventListener('keydown',event=>{
      const entries=[...commandList.querySelectorAll('.hud-command-result')];
      const active=entries.findIndex(x=>x.classList.contains('selected'));
      if(event.key==='ArrowDown'||event.key==='ArrowUp'){
        event.preventDefault();if(entries.length){entries.forEach(x=>x.classList.remove('selected'));
          const next=(active+(event.key==='ArrowDown'?1:entries.length-1))%entries.length;
          entries[next].classList.add('selected');entries[next].scrollIntoView({block:'nearest'});}
      }
      if(event.key==='Enter'){event.preventDefault();entries[active<0?0:active]?.click();}
    });
    document.addEventListener('keydown',handleKey);
    document.addEventListener('click',event=>{
      if(event.target.closest('[data-hud-close]')){closeOverlay();return;}
      const task=event.target.closest('[data-task-id]');
      if(task){showTask(task.dataset.taskId);return;}
      const system=event.target.closest('[data-system-name]');
      if(system){showSystem(system.dataset.systemName);return;}
      if(event.target.closest('[data-hud-routing]'))showRouting();
    });
    document.querySelectorAll('.hud-overlay').forEach(overlay=>overlay.addEventListener('keydown',event=>{
      if(event.key!=='Tab')return;
      const focusable=[...overlay.querySelectorAll('button:not([disabled]), input:not([disabled]), a[href]')];
      if(!focusable.length)return;
      const first=focusable[0],last=focusable[focusable.length-1];
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    }));
    setEarthSpeed(0);setEarthPaused(false);
  }
  setup();
  return {commands,findTask,render,showTask,showSystem,setEarthPaused,setEarthSpeed,showRouting,showPalette};
});