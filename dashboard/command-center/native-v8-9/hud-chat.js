/* Ask ROVOR: owner-private multi-model interface. A chat response is never proof of employee dispatch. */
(function(){
  if(window.ROVOR_HUD_CHAT)return;
  const KEY='rovor_hud_chat_v1',SESSIONS_KEY='rovor_chat_sessions_v2',MAX_KEPT=30;
  const PROMPTS=['Develop three visual campaign concepts','Review this code and suggest improvements','Create a high-end creative brief','Break down my project into clear steps'];
  const css=`
#rvc-fab{position:fixed;right:18px;bottom:18px;z-index:2147483000;background:#06233d;color:#bde5ff;border:1px solid #2f7fb8;border-radius:999px;padding:11px 18px;font:600 13px system-ui;letter-spacing:.08em;cursor:pointer;box-shadow:0 4px 18px #0008}
#rvc-fab:hover,#rvc-fab:focus-visible{background:#0b3a63;outline:2px solid #7cc8ff}
#rvc{position:fixed;right:18px;bottom:70px;z-index:2147483000;width:min(440px,calc(100vw - 24px));height:min(640px,calc(100vh - 100px));display:none;flex-direction:column;background:#020916;color:#d6eeff;border:1px solid #2f7fb8;border-radius:12px;box-shadow:0 10px 40px #000a;font:14px/1.45 system-ui}
#rvc[data-open=true]{display:flex}
#rvc header{display:flex;gap:8px;align-items:center;padding:10px 12px;border-bottom:1px solid #12385a}
#rvc header strong{letter-spacing:.1em;font-size:12px;color:#7cc8ff;white-space:nowrap}
#rvc select{flex:1;min-width:0;background:#06233d;color:#d6eeff;border:1px solid #2f7fb8;border-radius:6px;padding:5px}
#rvc button{background:#0b3a63;color:#d6eeff;border:1px solid #2f7fb8;border-radius:6px;padding:5px 10px;cursor:pointer;font:inherit}
#rvc button:disabled{opacity:.5;cursor:default}
#rvc button:focus-visible,#rvc select:focus-visible,#rvc textarea:focus-visible{outline:2px solid #7cc8ff}
#rvc-log{flex:1;overflow:auto;padding:12px;display:flex;flex-direction:column;gap:10px}
.rvc-msg{max-width:92%;padding:8px 11px;border-radius:10px;white-space:pre-wrap;word-break:break-word}
.rvc-user{align-self:flex-end;background:#0b3a63}
.rvc-bot{align-self:flex-start;background:#071a2e;border:1px solid #12385a}
.rvc-err{align-self:flex-start;background:#3a0b14;border:1px solid #8a2a3a}
.rvc-msg pre{margin:6px 0;padding:8px;background:#010510;border-radius:6px;overflow:auto;white-space:pre}
.rvc-chips{display:flex;flex-wrap:wrap;gap:6px}
.rvc-chips button{font-size:12px;border-radius:999px}
#rvc footer{border-top:1px solid #12385a;padding:8px 10px;display:flex;flex-direction:column;gap:6px}
#rvc footer label{font-size:12px;color:#8fb8d8;display:flex;gap:6px;align-items:center}
#rvc form{display:flex;gap:6px}
#rvc textarea{flex:1;resize:none;height:44px;background:#06233d;color:#d6eeff;border:1px solid #2f7fb8;border-radius:6px;padding:6px;font:inherit}
@media (max-width:700px){#rvc{right:6px;bottom:64px;width:calc(100vw - 12px)}}
@media (prefers-reduced-motion:no-preference){#rvc[data-open=true]{animation:rvcin .12s ease-out}@keyframes rvcin{from{opacity:0;transform:translateY(6px)}}}`;
  const el=(tag,props={},...kids)=>{const n=document.createElement(tag);Object.assign(n,props);for(const k of kids)n.append(k);return n;};
  let history=[],busy=false,controller=null,ready=false,source='omniroute',currentId=null;
  let sessions=[];
  try{sessions=JSON.parse(localStorage.getItem(SESSIONS_KEY)||'[]').filter(s=>s&&typeof s.id==='string'&&Array.isArray(s.history)).slice(0,16);}catch{}
  if(sessions.length){currentId=sessions[0].id;history=sessions[0].history;}else{
    currentId=crypto.randomUUID();sessions=[{id:currentId,title:'New conversation',history:[]}];
  }
  // Prior single-chat history remains on this device but new sessions have isolated histories.
  const save=()=>{try{
    const active=sessions.find(s=>s.id===currentId);if(active)active.history=history.slice(-MAX_KEPT);
    localStorage.setItem(SESSIONS_KEY,JSON.stringify(sessions.slice(0,16)));
  }catch{}};

  function renderText(node,text){
    node.textContent='';
    text.split(/(```[\s\S]*?(?:```|$))/g).forEach(part=>{
      if(part.startsWith('```')){const code=part.replace(/^```[^\n]*\n?/,'').replace(/```$/,'');node.append(el('pre',{textContent:code}));}
      else if(part)node.append(document.createTextNode(part));
    });
  }

  function build(){
    document.head.append(el('style',{textContent:css+"\n#rvc .rvc-mobile-menu{display:none}\n@media(max-width:760px){\n#rvc .rvc-mobile-menu{display:block;background:#10375d;color:#e3f5ff;border:1px solid #2e70a0;border-radius:8px;padding:5px 9px;flex-shrink:0}\n#rvc .rvc-sidebar{display:flex!important;position:absolute;z-index:5;left:0;top:0;bottom:0;width:min(84vw,300px);transform:translateX(-110%);transition:transform .18s ease;box-shadow:10px 0 30px #000b}\n#rvc[data-side-open=true] .rvc-sidebar{transform:translateX(0)}\n#rvc header strong{display:none}\n#rvc header .rvc-close{padding:6px 7px}\n#rvc header .rvc-source{max-width:120px}\n}\n"+"\n#rvc{inset:2.2vh 2vw!important;right:2vw!important;bottom:2.2vh!important;width:auto!important;height:auto!important;max-height:none!important;max-width:none!important;background:linear-gradient(150deg,#020817,#071a32 70%,#030c1d)!important;border:1px solid #316c9d!important;border-radius:18px!important;box-shadow:0 24px 90px #000e,0 0 50px #1b76c033!important;overflow:hidden!important;grid-template-columns:250px minmax(0,1fr)!important;padding:0!important}\n#rvc[data-open=true]{display:grid!important}\n#rvc *,#rvc *:before{box-sizing:border-box}\n#rvc .rvc-sidebar{min-width:0;background:linear-gradient(180deg,#071d36,#030c1b);padding:20px 12px;border-right:1px solid #275174;display:flex;flex-direction:column;gap:14px;overflow:hidden}\n#rvc .rvc-brand{color:#c5ecff;font-weight:800;font-size:14px;letter-spacing:.22em;padding:7px}\n#rvc .rvc-brand small{display:block;font-size:9px;font-weight:500;letter-spacing:.12em;color:#83accb;margin-top:4px}\n#rvc .rvc-sidebar .rvc-new{padding:11px;background:#103b62;border:1px solid #3877a9;color:#e3f6ff;text-align:left;border-radius:11px}\n#rvc .rvc-sidebar small{color:#7fa6c5;line-height:1.5;font-size:11px}\n#rvc .rvc-sessions{overflow:auto;flex:1;min-height:0;display:flex;flex-direction:column;gap:6px}\n#rvc .rvc-sessions button{border-radius:10px;text-align:left;padding:11px;background:transparent;color:#91b7d2;border:1px solid transparent;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}\n#rvc .rvc-sessions button[aria-current=true]{background:#10375c;color:#effaff;border-color:#3679ae}\n#rvc .rvc-main{display:flex;flex-direction:column;min-height:0;min-width:0}\n#rvc header{min-height:67px;background:#07192e;padding:11px 20px;gap:11px}\n#rvc header strong{font-size:13px;color:#e6f7ff;letter-spacing:.15em}\n#rvc select{padding:9px;background:#0b2947;color:#e7f6ff;border:1px solid #316c9c;border-radius:10px;font-size:12px}\n#rvc .rvc-source{max-width:160px}\n#rvc .rvc-model{max-width:370px}\n#rvc .rvc-state{padding:8px 19px;font-size:11px;color:#83add1;background:#071b30;border-bottom:1px solid #1b4467}\n#rvc #rvc-log{padding:30px max(20px,calc((100% - 750px)/2));gap:22px}\n#rvc .rvc-msg{max-width:800px;width:100%;font-size:14px;line-height:1.65;background:transparent!important;border:0!important;padding:0!important}\n#rvc .rvc-msg:before{display:block;font-size:10px;letter-spacing:.14em;font-weight:750;color:#83bdef;margin-bottom:8px}\n#rvc .rvc-user:before{content:'YOU'}\n#rvc .rvc-bot:before{content:'ROVOR · MODEL RESPONSE'}\n#rvc .rvc-user{align-self:stretch}\n#rvc .rvc-user .rvc-message-body{padding:14px 18px;background:#0d2e4d;border:1px solid #2d577a;border-radius:12px}\n#rvc .rvc-bot .rvc-message-body{padding:0 5px;color:#dfebf8}\n#rvc .rvc-err{background:transparent!important;align-self:stretch;color:#ffb8bd}\n#rvc .rvc-err:before{content:'REQUEST NOT CONFIRMED';display:block;color:#e8a6a8;font-size:10px;letter-spacing:.14em;margin-bottom:8px}\n#rvc footer{padding:12px max(16px,calc((100% - 750px)/2)) 18px;background:linear-gradient(0deg,#020b19,#07172a)}\n#rvc form{border:1px solid #3272a2;background:#09233e;border-radius:12px;padding:9px;align-items:flex-end}\n#rvc textarea{height:62px;max-height:160px;min-width:0;background:transparent;border:0;outline:none!important;color:#edf9ff}\n#rvc form button[type=submit]{background:#2581c4;border-color:#62aeec;color:white;padding:10px 16px;font-weight:700}\n#rvc .rvc-context-note{color:#85a6c1;font-size:10px;text-align:center}\n#rvc .rvc-chips button{padding:10px 13px;background:#0d2c49;border:1px solid #27557b;border-radius:11px}\n#rvc .rvc-welcome{max-width:600px;text-align:center;margin:auto}\n#rvc .rvc-welcome h2{font-size:clamp(25px,3vw,37px);font-weight:650;letter-spacing:-.045em;margin:0 0 10px;color:#effaff}\n#rvc .rvc-welcome p{color:#92b6d4}\n#rvc-fab{background:linear-gradient(135deg,#164c7a,#05172c);border-color:#6cc1fc;color:#eaf8ff;box-shadow:0 0 28px #188bd54c}\n@media(max-width:760px){#rvc{inset:0!important;width:100%!important;height:100dvh!important;border:0!important;border-radius:0!important;grid-template-columns:minmax(0,1fr)!important}#rvc .rvc-sidebar{display:none!important}#rvc header{padding:calc(env(safe-area-inset-top) + 10px) 11px 10px;gap:6px;min-height:62px}#rvc header strong{font-size:11px}#rvc select{font-size:11px;padding:6px}#rvc .rvc-source{width:100px;max-width:100px}#rvc .rvc-model{min-width:0}#rvc .rvc-state{padding:8px 12px}#rvc #rvc-log{padding:18px 14px}#rvc footer{padding:10px 12px calc(env(safe-area-inset-bottom) + 12px)}#rvc .rvc-msg{max-width:100%}}\n"}));
    // Safari zooms the page when focusing form controls whose font-size is
    // below 16px. Keep native pinch-zoom available; do not change viewport meta.
    const iosTypeAndKeyboardCSS = `
#rvc select, #rvc textarea, #rvc input, #rvc .rvc-source, #rvc .rvc-model {
  font-size:16px!important;
  -webkit-text-size-adjust:100%;
}
#rvc textarea { line-height:1.5!important; -webkit-appearance:none; appearance:none; border-radius:8px; }
#rvc .rvc-main { min-height:0; overflow:hidden; }
#rvc #rvc-log { min-height:0; overscroll-behavior:contain; -webkit-overflow-scrolling:touch; }
#rvc footer { flex-shrink:0; }
@media(max-width:760px) {
  #rvc[data-open=true] { top:var(--rvc-vv-top,0px)!important;
    height:var(--rvc-vv-height,100dvh)!important; bottom:auto!important; }
  #rvc header { min-height:55px; }
  #rvc .rvc-main { height:100%; }
  #rvc form { flex-shrink:0; }
  #rvc textarea { font-size:16px!important; min-height:40px; }
  #rvc select { font-size:16px!important; }
  #rvc footer { padding-bottom:calc(env(safe-area-inset-bottom,0px) + 9px); }
}
`;
    document.head.append(el('style',{textContent:iosTypeAndKeyboardCSS}));

    // Mobile controls occupy two deliberate rows, not a cramped desktop header.
    // All editable fields remain >=16px to prevent Safari's focus auto-zoom.
    const polishedMobileCSS = `
#rvc button,#rvc select{touch-action:manipulation}
#rvc .rvc-side-backdrop{display:none}
#rvc textarea{font-size:16px!important}
#rvc .rvc-mobile-menu,#rvc header button,#rvc .rvc-sessions button{min-width:42px;min-height:42px}
@media(min-width:761px) and (max-width:1100px){
  #rvc{grid-template-columns:210px minmax(0,1fr)!important;inset:1vh 1vw!important}
  #rvc header{gap:8px;padding:10px 12px}
  #rvc .rvc-model{flex:1;min-width:0;max-width:none}
}
@media(max-width:760px){
  #rvc{width:100vw!important;right:0!important;left:0!important;max-height:var(--rvc-vv-height,100dvh)!important}
  #rvc .rvc-main{min-width:0;min-height:0}
  #rvc header{
    display:grid!important;
    grid-template-columns:44px minmax(0,1fr) 44px 44px;
    grid-template-areas:"menu source clear close" "model model model model";
    align-items:center;gap:7px!important;
    padding:calc(env(safe-area-inset-top) + 7px) 12px 9px!important;
    min-height:0!important;
  }
  #rvc header strong{display:none!important}
  #rvc .rvc-mobile-menu{grid-area:menu;display:flex!important;align-items:center;justify-content:center;font-size:19px;padding:0!important}
  #rvc .rvc-source{grid-area:source;max-width:none!important;width:100%!important;min-width:0!important}
  #rvc .rvc-model{grid-area:model;width:100%!important;max-width:none!important;min-width:0!important}
  #rvc header button:not(.rvc-mobile-menu):not(.rvc-close){grid-area:clear}
  #rvc header .rvc-close{grid-area:close;min-width:42px!important}
  #rvc select{font-size:16px!important;padding:8px!important;min-height:42px}
  #rvc .rvc-sidebar{
    display:flex!important;position:absolute!important;
    width:min(315px,86vw);height:100%;z-index:6;
    top:0;left:0;bottom:0;padding-top:calc(env(safe-area-inset-top) + 14px);
    transform:translateX(-110%);transition:transform .18s ease;
    box-shadow:12px 0 32px #000a;
  }
  #rvc[data-side-open=true] .rvc-sidebar{transform:translateX(0)}
  #rvc .rvc-side-backdrop{display:none}
  #rvc[data-side-open=true] .rvc-side-backdrop{display:block;position:absolute;z-index:5;inset:0;width:100%;height:100%;border:0!important;border-radius:0!important;background:#0009}
  #rvc .rvc-state{padding:7px 12px!important;font-size:11px;line-height:1.4;overflow-wrap:anywhere}
  #rvc #rvc-log{flex:1;min-height:0;padding:15px 14px!important}
  #rvc footer{padding:8px 12px max(10px,env(safe-area-inset-bottom))!important;flex-shrink:0}
  #rvc footer form{gap:7px;padding:6px 7px}
  #rvc footer textarea{font-size:16px!important;min-height:46px;height:48px;max-height:120px}
}
@media(prefers-reduced-motion:reduce){#rvc .rvc-sidebar{transition:none!important}}
`;
    document.head.append(el('style',{textContent:polishedMobileCSS}));
    const fab=el('button',{id:'rvc-fab',type:'button',textContent:'ASK ROVOR',title:'Chat with your models and check on your employees'});
    fab.setAttribute('aria-expanded','false');fab.setAttribute('aria-controls','rvc');
    const sourceSelect=el('select',{id:'rvc-source',className:'rvc-source'});
    sourceSelect.setAttribute('aria-label','Inference source');
    for(const [value,label] of [['omniroute','OmniRoute · Mac'],['cloudflare','Cloudflare AI']]) sourceSelect.append(el('option',{value,textContent:label}));
    const select=el('select',{id:'rvc-model',className:'rvc-model'});select.setAttribute('aria-label','Model');
    const stateLabel=el('div',{className:'rvc-state',textContent:'Checking available models…'});
    const sessionsList=el('div',{className:'rvc-sessions'});
    const newChat=el('button',{type:'button',className:'rvc-new',textContent:'＋  New conversation'});
    const clear=el('button',{type:'button',textContent:'Clear',title:'Clear this conversation'});
    const mobileMenu=el('button',{type:'button',className:'rvc-mobile-menu',textContent:'☰',title:'Open conversations'});
    mobileMenu.setAttribute('aria-label','Open conversations');
    const close=el('button',{type:'button',textContent:'✕',title:'Close (Esc)'});close.setAttribute('aria-label','Close chat');
    const log=el('div',{id:'rvc-log'});log.setAttribute('role','log');log.setAttribute('aria-live','polite');
    const context=el('input',{type:'checkbox',checked:true,id:'rvc-ctx'});
    const input=el('textarea',{placeholder:'Message… (Enter to send, Shift+Enter for a new line)'});input.setAttribute('aria-label','Message');
    const send=el('button',{type:'submit',textContent:'Send'});
    const stop=el('button',{type:'button',textContent:'Stop waiting',hidden:true});
    const form=el('form',{},input,send,stop);
    const panel=el('section',{id:'rvc'},
      el('aside',{className:'rvc-sidebar'},el('div',{className:'rvc-brand'},'R O V O R',
        el('small',{},'MULTI-MODEL INTELLIGENCE')),newChat,el('div',{className:'rvc-label'},'CONVERSATIONS'),sessionsList,
        el('small',{},'Conversation history is stored on this device. Model text is not proof of employee execution.')),
      el('div',{className:'rvc-main'},
        el('header',{},mobileMenu,el('strong',{textContent:'ASK ROVOR'}),sourceSelect,select,clear,close),
        stateLabel,log,
        el('footer',{},el('div',{className:'rvc-context-note',textContent:'An accepted chat request is not a completed task. Only a confirmed model response counts.'}),form)));
    panel.setAttribute('aria-label','ROVOR chat');
    const sideBackdrop=el('button',{type:'button',className:'rvc-side-backdrop'});
    sideBackdrop.setAttribute('aria-label','Close conversation history');
    panel.append(sideBackdrop);
    sideBackdrop.onclick=()=>{panel.dataset.sideOpen='false';};
    document.body.append(fab,panel);

    const add=(cls,text)=>{const n=el('div',{className:'rvc-msg '+cls});const inner=el('div',{className:'rvc-message-body'});renderText(inner,text);n.append(inner);log.append(n);log.scrollTop=log.scrollHeight;return inner;};
    const drawSessions=()=>{
      sessionsList.textContent='';
      sessions.forEach(s=>{const b=el('button',{type:'button',textContent:s.title, title:s.title});
        b.setAttribute('aria-current',String(s.id===currentId));
        b.onclick=()=>{if(busy)return;save();currentId=s.id;history=s.history.slice();panel.dataset.sideOpen='false';redraw();drawSessions();};
        sessionsList.append(b);});
    };
    const welcome=()=>{
      const chips=el('div',{className:'rvc-chips'});
      PROMPTS.forEach(q=>chips.append(el('button',{type:'button',textContent:q,onclick:()=>{input.value=q;form.requestSubmit();}})));
      const n=el('div',{className:'rvc-welcome'},el('h2',{},'Intelligence, your way.'),
        el('p',{},'Choose a model and receive a real answer. Chat alone does not start employee jobs.'),chips);log.append(n);
    };
    const redraw=()=>{log.textContent='';if(!history.length)welcome();history.forEach(m=>add(m.role==='user'?'rvc-user':'rvc-bot',m.content));};
    const setBusy=b=>{busy=b;send.disabled=b||!ready;stop.hidden=!b;input.disabled=b;select.disabled=b;sourceSelect.disabled=b;if(!b)input.focus();};
    const syncVisualViewport=()=>{
      // On iOS the keyboard resizes the visual rather than the layout viewport.
      // Constrain the fullscreen dialog above the keyboard without browser zoom.
      if(!window.visualViewport)return;
      const vv=window.visualViewport;
      const mobile=window.matchMedia('(max-width:760px)').matches;
      if(mobile&&panel.dataset.open==='true'){
        panel.style.setProperty('--rvc-vv-top',Math.max(0,vv.offsetTop)+'px');
        panel.style.setProperty('--rvc-vv-height',Math.max(260,vv.height)+'px');
        // Preserve the message scroll position while the keyboard animates.
      }else{
        panel.style.removeProperty('--rvc-vv-top');
        panel.style.removeProperty('--rvc-vv-height');
      }
    };
    window.visualViewport?.addEventListener('resize',syncVisualViewport);
    window.visualViewport?.addEventListener('scroll',syncVisualViewport);
    window.addEventListener('orientationchange',syncVisualViewport);
    let priorOverflow=null;
    const toggle=open=>{
      panel.dataset.open=String(open);
      if(!open)panel.dataset.sideOpen='false';
      fab.setAttribute('aria-expanded',String(open));
      if(open){
        priorOverflow=document.body.style.overflow;
        document.body.style.overflow='hidden';
      }else{
        document.body.style.overflow=priorOverflow??'';
        priorOverflow=null;
        input.blur();
      }
      syncVisualViewport();
      // Avoid opening the iOS keyboard the moment the app launches.
      // Desktop typing remains one-step with autofocus.
      if(open){load();if(!window.matchMedia('(max-width:760px)').matches)input.focus({preventScroll:true});}
    };

    async function load(){
      ready=false;send.disabled=true;stateLabel.textContent='Checking '+sourceSelect.value+' model availability…';
      try{
        const omni=sourceSelect.value==='omniroute';
        const r=await fetch(omni?'/api/hud/chat/models':'/api/chat/models',{credentials:'same-origin',cache:'no-store'});
        if(!r.ok)throw Error('catalog_unavailable');
        const info=await r.json(),models=info.models;
        if((omni&&info.online!==true)||!Array.isArray(models)||!models.length)throw Error('catalog_unavailable');
        select.textContent='';models.forEach(m=>select.append(el('option',{value:m,textContent:m})));
        const saved=localStorage.getItem(KEY+'_model_'+sourceSelect.value);
        if(saved&&models.includes(saved))select.value=saved;
        stateLabel.textContent=omni?'OMNIROUTE BRIDGE ONLINE · verified free routes · Mac must remain connected':
          'CLOUDFLARE AI · separate cloud models · usage depends on your provider allowance';
        ready=true;send.disabled=false;
      }catch{
        select.textContent='';select.append(el('option',{value:'',textContent:'No models available'}));
        stateLabel.textContent=sourceSelect.value==='omniroute'?
          'OMNIROUTE OFFLINE · connect the outbound Mac bridge; no inference is available here yet':
          'CLOUDFLARE UNAVAILABLE · this source has no configured accessible models';
      }
    }
    sourceSelect.onchange=()=>{if(!busy)load();};
    select.onchange=()=>{try{localStorage.setItem(KEY+'_model_'+sourceSelect.value,select.value);}catch{}};

    async function ask(text){
      if(!ready||busy)return;
      const target=select.value,platform=sourceSelect.value;
      history.push({role:'user',content:text});add('rvc-user',text);
      const active=sessions.find(s=>s.id===currentId);
      if(active?.title==='New conversation')active.title=text.replace(/\s+/g,' ').slice(0,55);
      save();drawSessions();
      const bubble=add('rvc-bot','Preparing request · no model call confirmed');
      let reply='';setBusy(true);controller=new AbortController();
      const signal=controller.signal;
      try{
        const payload={model:target,context:false,messages:history.slice(-5)};
        if(platform==='omniroute'){
          const posted=await fetch('/api/hud/chat/submit',{method:'POST',credentials:'same-origin',signal,
            headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
          const ack=await posted.json().catch(()=>({}));
          if(posted.status!==202||!ack.job_id)throw Error(ack.error||'request_not_accepted');
          renderText(bubble,'HUD received request · queued, not yet executed');
          for(let i=0;i<100;i++){
            await new Promise(done=>setTimeout(done,1300));
            if(signal.aborted)throw Error('stopped_waiting');
            const r=await fetch('/api/hud/chat/status/'+encodeURIComponent(ack.job_id),{credentials:'same-origin',cache:'no-store',signal});
            if(!r.ok)throw Error('receipt_unavailable');
            const result=await r.json();
            if(result.state==='queued'){if(i%4===0)renderText(bubble,'Queued · waiting for Mac bridge to claim');continue;}
            if(result.state==='running'){if(i%4===0)renderText(bubble,'Claimed by Mac · waiting for actual model response');continue;}
            if(result.state==='complete'&&typeof result.output==='string'){
              reply=result.output;break;
            }
            if(result.state==='failed')throw Error(result.error||'relay_failed');
            throw Error('invalid_receipt');
          }
          if(!reply)throw Error('no_completion_receipt');
        }else{
          const r=await fetch('/api/chat',{method:'POST',credentials:'same-origin',signal,headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
          if(!r.ok){const err=await r.json().catch(()=>({}));throw Error(err.error||'cloud_chat_unavailable');}
          if(!r.body)throw Error('empty_stream');
          const reader=r.body.getReader(),dec=new TextDecoder();let buf='';
          for(;;){
            const {done,value}=await reader.read();if(done)break;
            buf+=dec.decode(value,{stream:true});
            let i;while((i=buf.indexOf('\n'))>=0){
              const line=buf.slice(0,i).trim();buf=buf.slice(i+1);
              if(!line.startsWith('data:'))continue;
              try{const piece=JSON.parse(line.slice(5).trim()).choices?.[0]?.delta?.content;
                if(typeof piece==='string'){reply+=piece;renderText(bubble,reply);log.scrollTop=log.scrollHeight;}}
              catch{}
            }
          }
          if(!reply)throw Error('empty_response');
        }
        renderText(bubble,reply);
        history.push({role:'assistant',content:reply});save();
        stateLabel.textContent=platform==='omniroute'?
          'RESPONSE CONFIRMED · requested route '+target+' · actual upstream identity not separately attested':
          'CLOUDFLARE AI RESPONSE RECEIVED · not an OmniRoute or employee action';
      }catch(e){
        const messages={
          omniroute_offline:'The Mac bridge is offline. No model call was confirmed.',
          relay_timeout:'No receipt from Mac. A completed model call was not verified.',
          stopped_waiting:'You stopped waiting. If the Mac already claimed the request, it might still finish.',
          chat_busy:'The private queue is full. No new model call was confirmed.',
          model_not_available:'Route unavailable or not verified eligible for free use.',
          chat_rate_limited:'The request limit has been reached.',
        };
        const message=messages[e.message]||('No confirmed model reply: '+(e.message||'unknown'));
        renderText(bubble,message);bubble.parentElement.className='rvc-msg rvc-err';
        stateLabel.textContent='NO COMPLETION CONFIRMED · '+message;
        if(reply){history.push({role:'assistant',content:reply});save();}
      }finally{controller=null;setBusy(false);}
    }

    form.onsubmit=e=>{e.preventDefault();const text=input.value.trim();if(!text||busy||!ready)return;input.value='';ask(text);};
    input.onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();form.requestSubmit();}};
    stop.onclick=()=>controller?.abort();
    clear.onclick=()=>{if(busy)return;history=[];save();redraw();};
    newChat.onclick=()=>{if(busy)return;save();panel.dataset.sideOpen='false';currentId=crypto.randomUUID();history=[];
      sessions.unshift({id:currentId,title:'New conversation',history:[]});sessions=sessions.slice(0,16);
      save();drawSessions();redraw();input.focus();};
    drawSessions();
    mobileMenu.onclick=()=>{panel.dataset.sideOpen=String(panel.dataset.sideOpen!=='true');};
    close.onclick=()=>toggle(false);fab.onclick=()=>toggle(panel.dataset.open!=='true');
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&panel.dataset.open==='true')toggle(false);});
    redraw();
  }
  window.ROVOR_HUD_CHAT={start:()=>{if(!document.getElementById('rvc'))build();}};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>window.ROVOR_HUD_CHAT.start());else window.ROVOR_HUD_CHAT.start();
})();
