/* ROVOR HUD chat: local, paired-browser only. Model output is rendered as text, never HTML. */
(function(){
  if(window.ROVOR_HUD_CHAT)return;
  const KEY='rovor_hud_chat_v1',MAX_KEPT=30;
  const PROMPTS=['What are my employees doing right now?','Which providers are getting close to limits?','Summarize what needs my review.','Which model should I use for coding?'];
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
  let history=[],busy=false,controller=null,ready=false;
  try{history=JSON.parse(localStorage.getItem(KEY)||'[]').filter(m=>m&&(m.role==='user'||m.role==='assistant')&&typeof m.content==='string').slice(-MAX_KEPT);}catch{}
  const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(history.slice(-MAX_KEPT)));}catch{}};

  function renderText(node,text){
    node.textContent='';
    text.split(/(```[\s\S]*?(?:```|$))/g).forEach(part=>{
      if(part.startsWith('```')){const code=part.replace(/^```[^\n]*\n?/,'').replace(/```$/,'');node.append(el('pre',{textContent:code}));}
      else if(part)node.append(document.createTextNode(part));
    });
  }

  function build(){
    document.head.append(el('style',{textContent:css}));
    const fab=el('button',{id:'rvc-fab',type:'button',textContent:'ASK ROVOR',title:'Chat with your models and check on your employees'});
    fab.setAttribute('aria-expanded','false');fab.setAttribute('aria-controls','rvc');
    const select=el('select',{id:'rvc-model'});select.setAttribute('aria-label','Model');
    const clear=el('button',{type:'button',textContent:'Clear',title:'Clear this conversation'});
    const close=el('button',{type:'button',textContent:'✕',title:'Close (Esc)'});close.setAttribute('aria-label','Close chat');
    const log=el('div',{id:'rvc-log'});log.setAttribute('role','log');log.setAttribute('aria-live','polite');
    const context=el('input',{type:'checkbox',checked:true,id:'rvc-ctx'});
    const input=el('textarea',{placeholder:'Message… (Enter to send, Shift+Enter for a new line)'});input.setAttribute('aria-label','Message');
    const send=el('button',{type:'submit',textContent:'Send'});
    const stop=el('button',{type:'button',textContent:'Stop',hidden:true});
    const form=el('form',{},input,send,stop);
    const panel=el('section',{id:'rvc'},
      el('header',{},el('strong',{textContent:'ROVOR CHAT'}),select,clear,close),log,
      el('footer',{},el('label',{},context,'Include live HUD status (employees, usage)'),form));
    panel.setAttribute('aria-label','ROVOR chat');
    document.body.append(fab,panel);

    const add=(cls,text)=>{const n=el('div',{className:'rvc-msg '+cls});renderText(n,text);log.append(n);log.scrollTop=log.scrollHeight;return n;};
    const welcome=()=>{
      const chips=el('div',{className:'rvc-chips'});
      PROMPTS.forEach(q=>chips.append(el('button',{type:'button',textContent:q,onclick:()=>{input.value=q;form.requestSubmit();}})));
      const n=el('div',{className:'rvc-msg rvc-bot'},'Ask a model anything, or ask what your employees and providers are up to.',chips);log.append(n);
    };
    const redraw=()=>{log.textContent='';if(!history.length)welcome();history.forEach(m=>add(m.role==='user'?'rvc-user':'rvc-bot',m.content));};
    const setBusy=b=>{busy=b;send.disabled=b;stop.hidden=!b;input.disabled=b;select.disabled=b;if(!b)input.focus();};
    const toggle=open=>{panel.dataset.open=String(open);fab.setAttribute('aria-expanded',String(open));if(open){load();input.focus();}};

    async function load(){
      if(ready)return;
      try{
        const r=await fetch('/api/chat/models',{credentials:'same-origin'});if(!r.ok)throw 0;
        const {models}=await r.json();if(!Array.isArray(models)||!models.length)throw 0;
        select.textContent='';models.forEach(m=>select.append(el('option',{value:m,textContent:m})));
        const saved=localStorage.getItem(KEY+'_model');if(saved&&models.includes(saved))select.value=saved;
        ready=true;
      }catch{add('rvc-err','Could not load your models. Make sure OmniRoute is running, then reopen this panel.');}
    }
    select.onchange=()=>{try{localStorage.setItem(KEY+'_model',select.value);}catch{}};

    async function ask(text){
      history.push({role:'user',content:text});add('rvc-user',text);save();
      const bubble=add('rvc-bot','…');let reply='';setBusy(true);controller=new AbortController();
      try{
        const r=await fetch('/api/chat',{method:'POST',credentials:'same-origin',signal:controller.signal,headers:{'Content-Type':'application/json'},
          body:JSON.stringify({model:select.value,context:context.checked,messages:history.slice(-20)})});
        if(!r.ok){const err=await r.json().catch(()=>({}));throw Error(({chat_busy:'Another reply is still running.',chat_rate_limited:'Slow down a little: too many messages this minute.',model_not_available:'That model is not available right now.',chat_upstream_failed:'The model could not answer. Try another model or the rovor-spread-free-v1 combo.'})[err.error]||'The chat service could not answer.');}
        const reader=r.body.getReader(),dec=new TextDecoder();let buf='';
        for(;;){
          const {done,value}=await reader.read();if(done)break;
          buf+=dec.decode(value,{stream:true});
          let i;while((i=buf.indexOf('\n'))>=0){
            const line=buf.slice(0,i).trim();buf=buf.slice(i+1);
            if(!line.startsWith('data:'))continue;const data=line.slice(5).trim();if(data==='[DONE]')continue;
            try{const piece=JSON.parse(data).choices?.[0]?.delta?.content;if(typeof piece==='string'){reply+=piece;renderText(bubble,reply);log.scrollTop=log.scrollHeight;}}catch{}
          }
        }
        if(!reply)throw Error('The model returned an empty reply. Try another model.');
        history.push({role:'assistant',content:reply});save();
      }catch(e){
        if(e.name==='AbortError'){if(reply){history.push({role:'assistant',content:reply});save();}else bubble.remove();}
        else{if(reply){history.push({role:'assistant',content:reply});save();}bubble.className='rvc-msg rvc-err';renderText(bubble,e.message||'Chat failed.');if(history[history.length-1]?.role==='user')history.pop(),save();}
      }finally{controller=null;setBusy(false);}
    }

    form.onsubmit=e=>{e.preventDefault();const text=input.value.trim();if(!text||busy||!ready)return;input.value='';ask(text);};
    input.onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();form.requestSubmit();}};
    stop.onclick=()=>controller?.abort();
    clear.onclick=()=>{if(busy)controller?.abort();history=[];save();redraw();};
    close.onclick=()=>toggle(false);fab.onclick=()=>toggle(panel.dataset.open!=='true');
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&panel.dataset.open==='true')toggle(false);});
    redraw();
  }
  window.ROVOR_HUD_CHAT={start:()=>{if(!document.getElementById('rvc'))build();}};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>window.ROVOR_HUD_CHAT.start());else window.ROVOR_HUD_CHAT.start();
})();
