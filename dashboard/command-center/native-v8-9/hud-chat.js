/* Ask ROVOR: owner-private multi-model interface. A chat response is never proof of employee dispatch. */
(function(){
  if(window.ROVOR_HUD_CHAT)return;
  const KEY='rovor_hud_chat_v1',SESSIONS_KEY='rovor_chat_sessions_v2',MAX_KEPT=30;
  const PROMPTS=['Develop three visual campaign concepts','Review this code and suggest improvements','Create a high-end creative brief','Break down my project into clear steps'];
  const PROVIDERS=[['gemini','Google Gemini'],['mistral','Mistral'],['nvidia','NVIDIA'],['cohere','Cohere'],['sambanova','SambaNova'],['cloudflare-ai','Cloudflare Workers AI'],['groq','Groq'],['openrouter','OpenRouter'],['huggingface','Hugging Face']];
  // Group only by explicit route prefixes. A :free name or configured key
  // alone does not prove a live free entitlement or successful inference.
  function routeGroup(id){
    if(id.startsWith('rovor-'))return 'Owner-approved OmniRoute combos';
    const prefix=id.split('/')[0].toLowerCase();
    const aliases={google:'gemini',gemini:'gemini',cloudflare:'cloudflare-ai',
      'cloudflare-ai':'cloudflare-ai',hf:'huggingface',huggingface:'huggingface'};
    const provider=aliases[prefix]||prefix;
    const match=PROVIDERS.find(([key])=>key===provider);
    return match?match[1]+' · Mac-advertised chat routes':'Other eligible routes (provider unverified)';
  }
  const AUTO_ROUTE='__rovor_smart_route__';
  // Lightweight selection heuristics, NOT measured rankings or quota claims.
  // Choices are confined to the Mac's currently advertised free-eligible routes.
  function planRoutes(prompt, allowed, selection=AUTO_ROUTE, {allowTeam=false} = {}) {
    const routes=[...new Set((Array.isArray(allowed)?allowed:[]).filter(
      id=>typeof id==='string'&&id!==AUTO_ROUTE&&id.length<201))].slice(0,100);
    if(!routes.length)return {routes:[],reason:'No eligible OmniRoute routes reported',error:'No currently advertised routes. Check the Mac bridge.'};
    const text=String(prompt||'').toLowerCase();
    if(selection&&selection!==AUTO_ROUTE){
      if(!routes.includes(selection))return {routes:[],reason:'Manual route unavailable',error:'Selected model is no longer available.'};
      return {routes:[selection],reason:'Manual route · explicitly selected',mode:'manual'};
    }
    const providerPattern=[
      ['gemini',/\b(?:gemini|google ai)\b/i],['mistral',/\bmistral\b/i],
      ['nvidia',/\b(?:nvidia|nemotron)\b/i],['cohere',/\bcohere\b/i],
      ['sambanova',/\bsambanova\b|\bsamba nova\b/i],
      ['cloudflare-ai',/\bcloudflare\b/i],['groq',/\bgroq\b/i],
      ['openrouter',/\bopenrouter\b|\bopen router\b/i],
      ['huggingface',/\bhugging\s*face\b|\bhuggingface\b/i]
    ];
    const named=providerPattern.filter(([,re])=>re.test(text)).map(([p])=>p);
    if(named.length>2||/\b(?:all (?:nine|9|providers|models)|every (?:provider|model))\b/i.test(text))
      return {routes:[],reason:'Request exceeds per-message safeguard',error:'At most two distinct model routes per request. Please split this into smaller requests.'};
    const providerOf=id=>{
      const prefix=id.split('/')[0].toLowerCase();
      if(['gemini','google'].includes(prefix))return 'gemini';
      if(['cloudflare','cloudflare-ai'].includes(prefix))return 'cloudflare-ai';
      if(['hf','huggingface'].includes(prefix))return 'huggingface';
      return prefix;
    };
    const category= /\b(?:code|coding|test|bug|fix|github|repo|repository|debug|script|refactor|typescript|python|javascript)\b/i.test(text)?'code'
      :/\b(?:analy[sz]e|reason|research|strategy|architecture|complex|plan|compare|review)\b/i.test(text)?'reason'
      :/\b(?:fast|quick|simple|short|summari[sz]e)\b/i.test(text)?'speed'
      :/\b(?:design|creative|caption|campaign|copy|art|story|brand)\b/i.test(text)?'creative':'general';
    const score=id=>{
      const value=id.toLowerCase(),provider=providerOf(id);
      let points=0;
      if(category==='code')points+=/code|coder|devstral|qwen|deepseek/i.test(value)?7:0;
      if(category==='reason')points+=/reason|nemotron|gemini|mistral|deepseek|120b/i.test(value)?6:0;
      if(category==='speed')points+=/fast|flash|lite|small|mini|groq/i.test(value)?5:0;
      if(category==='creative')points+=/gemini|mistral|creative|flash/i.test(value)?4:0;
      if(value.startsWith('rovor-'))points+=2; // Explicitly approved combos, not proof of actual upstream.
      if(value.endsWith(':free'))points+=1;
      if(provider==='groq'&&category==='speed')points+=2;
      const evidence=localEvidence(id);
      if(evidence){
        // Modest reliability tiebreaker only after >=3 real completion receipts.
        // No synthetic accuracy, tokens, price or quota scores.
        points+=Math.round(3*(evidence.ok-evidence.failed)/(evidence.ok+evidence.failed));
      }
      return points;
    };
    const sorted=[...routes].sort((a,b)=>score(b)-score(a)||a.localeCompare(b));
    const explicit=[];
    for(const provider of named.slice(0,allowTeam?2:1)){
      const route=sorted.find(id=>providerOf(id)===provider&&!explicit.includes(id));
      if(!route)return {routes:[],reason:'Explicit provider unavailable',
        error:provider+' was requested but has no advertised free-eligible route. Nothing was sent; select a different provider or check OmniRoute.'};
      explicit.push(route);
    }
    const comparison= /\b(?:compare|contrast|second opinion|double.check|cross.check|debate|two models|multiple models|different perspectives|independent review)\b/i.test(text);
    const substantial= /\b(?:audit|investigate|diagnose|architecture|root cause|security review|test plan|analyze thoroughly|complex implementation|refactor)\b/i.test(text)
      || (text.length>=220&&['code','reason'].includes(category));
    // Task-aware extra inference is strictly opt-in. Two permitted requests
    // are executed sequentially, not as uncontrolled fan-out or round robin.
    if(named.length>1&&!allowTeam)return {routes:[],reason:'Team confirmation required',
      error:'You named multiple providers. Enable two-model review to send to both; nothing was sent.'};
    const desired=allowTeam&&(comparison||substantial||named.length>1)?2:1;
    const chosen=[...explicit];
    while(chosen.length<desired){
      const distinct=sorted.find(id=>!chosen.includes(id)&&!chosen.some(existing=>providerOf(existing)===providerOf(id)));
      const candidate=distinct||sorted.find(id=>!chosen.includes(id));
      if(!candidate)break;
      chosen.push(candidate);
    }
    if(!chosen.length)return {routes:[],reason:'No eligible route',error:'No eligible models were available for this request.'};
    return {routes:chosen,mode:'smart',category,
      reason:named.length?'Named provider preference · heuristic route choice'
        :chosen.length===2?'Optional two-model review · independent requests with separate receipts'
        :'Task-aware route hint · '+category+' · unbenchmarked; no quota guarantee'};
  }
  window.ROVOR_ROUTE_PLANNER={plan:planRoutes};
  // Keep only completion/failure receipts on this device, never prompt text
  // or provider secrets. These observations measure chat reliability, not
  // intelligence, quality, provider quota or isolated inference latency.
  const STATS_KEY='rovor_chat_route_receipts_v1',STATS_MAX_AGE=7*86400000;
  const routeStats=Object.create(null);
  try{
    const saved=JSON.parse(localStorage.getItem(STATS_KEY)||'{}');
    if(saved&&typeof saved==='object'&&!Array.isArray(saved)){
      for(const [id,v] of Object.entries(saved).slice(0,60)){
        if(typeof id!=='string'||!v||Date.now()-v.last>STATS_MAX_AGE)continue;
        if(Number.isSafeInteger(v.ok)&&Number.isSafeInteger(v.failed)&&
          v.ok>=0&&v.failed>=0&&v.ok+v.failed<=1000&&Number.isFinite(v.elapsed)&&v.elapsed>=0&&Number.isFinite(v.last))routeStats[id]=v;
      }
    }
  }catch{}
  function localEvidence(id){
    const v=Object.hasOwn(routeStats,id)?routeStats[id]:null;
    return v&&Date.now()-v.last<STATS_MAX_AGE&&v.ok+v.failed>=3?v:null;
  }
  function recordReceipt(id,outcome,elapsedMs){
    if(typeof id!=='string'||id===AUTO_ROUTE||
      !['complete','failed'].includes(outcome))return;
    const now=Date.now(),was=localEvidence(id)||routeStats[id];
    const old=was&&now-was.last<STATS_MAX_AGE?was:{ok:0,failed:0,elapsed:0};
    const item={ok:old.ok+(outcome==='complete'?1:0),
      failed:old.failed+(outcome==='failed'?1:0),
      elapsed:old.elapsed+(outcome==='complete'&&Number.isFinite(elapsedMs)?Math.max(0,elapsedMs):0),
      last:now};
    if(item.ok+item.failed>1000)return;
    routeStats[id]=item;
    try{
      const recent=Object.entries(routeStats).sort((a,b)=>b[1].last-a[1].last).slice(0,60);
      localStorage.setItem(STATS_KEY,JSON.stringify(Object.fromEntries(recent)));
    }catch{}
  }
  function modelEvidenceHint(id){
    if(id===AUTO_ROUTE)return 'Task-aware name heuristics only · always check model eligibility';
    const name=id.toLowerCase(),hints=[];
    if(/coder|code|codestral|devstral|qwen2\.5-coder/.test(name))hints.push('coding');
    if(/reason|deepseek-r1|nemotron|gpt-oss-120b/.test(name))hints.push('reasoning');
    if(/flash|fast|lite|small|mini/.test(name))hints.push('quick-response');
    if(/vision|multimodal|[-/]vl\b/.test(name))hints.push('visual-model name; this chat sends text only');
    const evidence=localEvidence(id);
    const observed=evidence?'This device: '+evidence.ok+'/'+(evidence.ok+evidence.failed)+' confirmed replies over 7 days; end-to-end time includes queue'
      :'Not enough recent confirmed local receipts';
    return 'Name-only task clues: '+(hints.join(', ')||'none verified')+
      ' · Weaknesses unknown until tested; free quota/reset and actual fallback unverified. '+observed+'.';
  }
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
  let history=[],busy=false,controller=null,ready=false,source='gemini',currentId=null;
  let sessions=[];
  try{sessions=JSON.parse(localStorage.getItem(SESSIONS_KEY)||'[]').filter(s=>s&&typeof s.id==='string'&&Array.isArray(s.history)).slice(0,16);}catch{}
  if(sessions.length){currentId=sessions[0].id;history=sessions[0].history;}else{
    currentId=crypto.randomUUID();sessions=[{id:currentId,title:'New conversation',source:'gemini',model:null,history:[]}];
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
    document.head.append(el('style',{textContent:`
#rvc .rvc-receipt{font:600 10px/1.5 system-ui;letter-spacing:.07em;color:#86b7d8;margin:8px 0 2px;overflow-wrap:anywhere}
#rvc .rvc-err .rvc-receipt{color:#f6b8b8}
#rvc .rvc-copy{align-self:flex-start;display:inline-flex;justify-content:center;align-items:center;min-height:36px;margin-top:7px;background:#08233e;color:#bfe6ff;border:1px solid #2d648e;border-radius:8px;padding:6px 10px;font-size:12px}
@media(max-width:760px){#rvc .rvc-copy{min-height:44px}}
`}));

    document.head.append(el('style',{textContent:`
#rvc .rvc-model-slot{display:flex;align-items:center;gap:7px;flex:1;min-width:0;max-width:465px}
#rvc .rvc-model-slot select{width:100%;min-width:0;max-width:none!important}
#rvc .rvc-model-browse{flex:0 0 44px;min-width:44px;min-height:44px;background:#103f69;border:1px solid #3c7eac;border-radius:11px;font-size:24px;line-height:1;color:#d5eeff}
#rvc .rvc-model-sheet[hidden]{display:none!important}
#rvc .rvc-model-sheet{position:absolute;z-index:12;inset:0;display:flex;align-items:center;justify-content:center;padding:20px;background:#010915dc;backdrop-filter:blur(7px)}
#rvc .rvc-model-sheet-card{width:min(580px,100%);max-height:min(670px,90%);display:flex;flex-direction:column;min-height:0;padding:20px;background:linear-gradient(155deg,#092442,#031222);border:1px solid #3c749e;border-radius:17px;box-shadow:0 20px 70px #000b}
#rvc .rvc-model-sheet-header{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:14px}
#rvc .rvc-model-sheet-header strong{font-size:17px;color:#edf8ff;letter-spacing:-.02em}
#rvc .rvc-model-sheet-close{min-height:44px;padding:9px 15px;border-radius:10px}
#rvc .rvc-model-search{width:100%;min-height:48px;font:16px/1.5 system-ui!important;background:#05182c;color:#ecf7ff;padding:12px 14px;border:1px solid #3a739f;border-radius:11px;outline-offset:2px}
#rvc .rvc-model-sheet-info{margin:9px 0 14px;color:#8fb2cd;font-size:11px;line-height:1.5}
#rvc .rvc-model-rows{overflow-y:auto;overscroll-behavior:contain;min-height:0;display:flex;flex-direction:column;gap:18px}
#rvc .rvc-model-group{display:flex;flex-direction:column;gap:7px}
#rvc .rvc-model-group h3{font-size:10px;letter-spacing:.16em;color:#8bbbdc;margin:0 0 2px;text-transform:uppercase}
#rvc .rvc-model-option{display:block;width:100%;text-align:left;padding:12px 14px;min-height:55px;background:#071d35;border:1px solid #294e72;border-radius:10px;color:#e2f2ff;overflow-wrap:anywhere;font-size:12px}
#rvc .rvc-model-option[aria-current=true]{background:#123d62;border-color:#62adcf}
#rvc .rvc-model-option small{display:block;color:#88aeca;font-size:10px;margin-top:3px}
#rvc .rvc-model-empty{font-size:13px;color:#9fbed6;padding:16px 6px}
@media(max-width:760px){
  #rvc header .rvc-model-slot{grid-area:model;width:100%;max-width:none;min-width:0}
  #rvc header .rvc-model-slot select{width:100%}
  #rvc .rvc-model-sheet{padding:0;align-items:flex-end}
  #rvc .rvc-model-sheet-card{width:100%;max-height:min(75dvh,650px);border-radius:20px 20px 0 0;padding:18px 15px max(15px,env(safe-area-inset-bottom))}
  #rvc .rvc-model-rows{padding-bottom:10px}
}
`}));
    const fab=el('button',{id:'rvc-fab',type:'button',textContent:'ASK ROVOR',title:'Chat with your models and check on your employees'});
    fab.setAttribute('aria-expanded','false');fab.setAttribute('aria-controls','rvc');
    const sourceSelect=el('select',{id:'rvc-source',className:'rvc-source'});
    sourceSelect.setAttribute('aria-label','Inference source');
    for(const [value,label] of [['gemini','Google Gemini · Cloud'],['groq','Groq · Cloud Direct'],['cloudflare','Cloudflare AI'],['omniroute','OmniRoute · optional Mac']]) sourceSelect.append(el('option',{value,textContent:label}));
    const select=el('select',{id:'rvc-model',className:'rvc-model'});select.setAttribute('aria-label','Model');
    const modelBrowse=el('button',{type:'button',className:'rvc-model-browse',textContent:'⌕',title:'Search available models',disabled:true});
    modelBrowse.setAttribute('aria-label','Search available models');
    modelBrowse.setAttribute('aria-expanded','false');
    const modelSlot=el('div',{className:'rvc-model-slot'},select,modelBrowse);
    const modelSheet=el('div',{className:'rvc-model-sheet',hidden:true});
    const modelSheetTitle=el('strong',{textContent:'Choose a model'});
    const modelSheetClose=el('button',{type:'button',className:'rvc-model-sheet-close',textContent:'Close'});
    modelSheetClose.setAttribute('aria-label','Close model browser');
    const modelSheetHeader=el('div',{className:'rvc-model-sheet-header'},modelSheetTitle,modelSheetClose);
    const modelSearch=el('input',{type:'search',className:'rvc-model-search',placeholder:'Search a model or provider',maxLength:100});
    modelSearch.setAttribute('aria-label','Search models and providers');
    const modelSheetInfo=el('p',{className:'rvc-model-sheet-info',textContent:'Only Mac-advertised free-eligible routes are selectable. Listing a route does not prove remaining quota or a completed reply.'});
    const modelRows=el('div',{className:'rvc-model-rows'});
    document.head.append(el('style',{textContent:`
#rvc .rvc-model-notready{border:1px dashed #294966;background:#06162a;padding:9px 12px;border-radius:9px;color:#91b1cc;font-size:11px;line-height:1.5}
@media(max-width:760px){#rvc .rvc-model-notready{font-size:12px;padding:12px}}
`}));

    modelSheet.append(el('div',{className:'rvc-model-sheet-card'},modelSheetHeader,modelSearch,modelSheetInfo,modelRows));
    const stateLabel=el('div',{className:'rvc-state',textContent:'Checking available models…'});
    stateLabel.setAttribute('role','status');
    stateLabel.setAttribute('aria-live','polite');
    const refreshButton=el('button',{type:'button',className:'rvc-refresh',textContent:'↻ Check',title:'Refresh model availability and provider telemetry'});
    refreshButton.setAttribute('aria-label','Refresh model availability and provider status');
    const connectionBar=el('div',{className:'rvc-connection-bar'},stateLabel,refreshButton);
    document.head.append(el('style',{textContent:`
#rvc .rvc-connection-bar{display:flex;align-items:center;gap:8px;background:#071b30;border-bottom:1px solid #1b4467;min-width:0}
#rvc .rvc-connection-bar .rvc-state{flex:1;min-width:0;border:0;overflow-wrap:anywhere}
#rvc .rvc-connection-bar .rvc-refresh{flex-shrink:0;margin-right:12px;background:#0b3151;border:1px solid #3a7fad;border-radius:9px;color:#c1e5ff;font-size:12px;min-height:38px;padding:6px 11px}
#rvc .rvc-connection-bar .rvc-refresh:focus-visible{outline:2px solid #90d6ff}
@media(max-width:760px){#rvc .rvc-connection-bar .rvc-refresh{margin-right:10px;font-size:12px;min-width:72px}}
`}));

    // Separate Mac telemetry from model availability. Historical provider
    // connections are not proof of running inference or fresh quotas.
    const providerDetails=el('details',{className:'rvc-provider-inspect'});
    const providerSummary=el('summary',{textContent:'OMNIROUTE PROVIDERS · CHECKING TELEMETRY'});
    const providerList=el('div',{className:'rvc-provider-list'});
    providerDetails.append(providerSummary,providerList);
    document.head.append(el('style',{textContent:`
#rvc .rvc-provider-inspect{flex-shrink:0;border-bottom:1px solid #1d4264;background:#05152a;color:#a4c8e6}
#rvc .rvc-provider-inspect>summary{cursor:pointer;padding:9px 18px;font-size:11px;letter-spacing:.07em;list-style:revert;touch-action:manipulation}
#rvc .rvc-provider-inspect>summary:focus-visible{outline:2px solid #85cbff;outline-offset:-2px}
#rvc .rvc-provider-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:7px;max-height:160px;overflow:auto;padding:0 12px 12px}
#rvc .rvc-provider-item{padding:8px 10px;background:#091f39;border:1px solid #234869;border-radius:9px;font-size:12px}
#rvc .rvc-provider-item small{display:block;color:#8daec8;font-size:10px;margin-top:3px}
@media(max-width:760px){#rvc .rvc-provider-list{grid-template-columns:repeat(2,minmax(0,1fr));max-height:128px}#rvc .rvc-provider-inspect>summary{padding:8px 12px;font-size:10px}}
`}));
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
    // Owners may explicitly attach one curated source excerpt from their
    // local origin/main Git mirror. Source is read only and never grants PR,
    // push, repository-token or employee dispatch permissions to the model.
    const repoSelect=el('select',{id:'rvc-repo-file',className:'rvc-repo-file'});
    repoSelect.setAttribute('aria-label','Attach a GitHub repository source file to this prompt');
    const repoOptions=[
      ['','No repository file attached'],
      ['coordination/TASK-INTAKE.md','Tasks & routing · documentation'],
      ['integrations/hud-cloud/ASK-ROVOR-SETUP.md','Ask ROVOR · setup'],
      ['integrations/hud-cloud/worker.mjs','HUD cloud backend'],
      ['integrations/hud-cloud/verify-github-deploy.mjs','GitHub deployment verification'],
      ['dashboard/command-center/native-v8-9/hud-chat.js','Ask ROVOR interface'],
      ['dashboard/command-center/native-v8-9/live-quota-board.js','Usage & quota dashboard'],
      ['tools/hud_chat.mjs','OmniRoute chat gateway'],
      ['.github/workflows/deploy-private-hud-cloudflare.yml','HUD deployment workflow']
    ];
    repoOptions.forEach(([value,label])=>repoSelect.append(el('option',{value,textContent:label})));
    const repoNote=el('small',{className:'rvc-repo-note',
      textContent:'Optional GitHub source · local origin/main snapshot. A selected excerpt is sent to your model; no repository write access.'});
    const repoRow=el('div',{className:'rvc-repo-row'},
      el('label',{textContent:'GitHub source',htmlFor:'rvc-repo-file'}),repoSelect,repoNote);
    document.head.append(el('style',{textContent:`
#rvc .rvc-repo-row{display:flex;align-items:center;flex-wrap:wrap;gap:7px;padding:3px 1px 9px;color:#a4c5df;font:12px/1.35 system-ui}
#rvc .rvc-repo-row label{font-weight:700;color:#b5dcf7}
#rvc .rvc-repo-file{flex:1;min-width:170px;max-width:370px;background:#061b30;color:#dfedfa;border:1px solid #2e5f85;border-radius:9px;padding:7px 10px;font-size:16px!important}
#rvc .rvc-repo-note{font-size:10px;color:#84a9c5;flex-basis:100%;line-height:1.4}
#rvc .rvc-repo-row[hidden]{display:none!important}
@media(max-width:760px){#rvc .rvc-repo-row{gap:5px;padding-bottom:6px}#rvc .rvc-repo-row label{font-size:11px}#rvc .rvc-repo-note{font-size:10px}}
`}));
    const teamInput=el('input',{type:'checkbox',id:'rvc-team-review'});
    teamInput.setAttribute('aria-label','Allow task-aware review using up to two free-eligible model routes');
    const teamRow=el('div',{className:'rvc-team-row'},
      el('label',{htmlFor:'rvc-team-review'},teamInput,'  Two-model review when useful'),
      el('small',{textContent:'Two model calls may share your prompt and selected GitHub source with different free-model providers. Separate receipts; no paid routing.'}));
    document.head.append(el('style',{textContent:`
#rvc .rvc-team-row{display:flex;align-items:center;flex-wrap:wrap;gap:5px 11px;padding:4px 0;color:#a9c9e3}
#rvc .rvc-team-row label{display:flex;align-items:center;gap:8px;font:600 12px/1.4 system-ui;cursor:pointer}
#rvc .rvc-team-row input{appearance:auto;-webkit-appearance:checkbox;width:18px;height:18px;accent-color:#4aa7e5;flex-shrink:0}
#rvc .rvc-team-row small{font:10px/1.4 system-ui;color:#82abc9;flex:1;min-width:170px}
#rvc .rvc-team-row[hidden]{display:none!important}
@media(max-width:760px){#rvc .rvc-team-row small{flex-basis:100%;font-size:10px}}
`}));
    const routingNote=el('div',{className:'rvc-routing-note',textContent:'Choose a model, or use Smart routing to select from Mac-advertised routes.'});
    routingNote.setAttribute('role','status');
    document.head.append(el('style',{textContent:`
#rvc .rvc-routing-note{background:#061b30;border:1px solid #204968;border-radius:9px;padding:8px 11px;color:#a9cde7;font:500 11px/1.5 system-ui;overflow-wrap:anywhere}
#rvc .rvc-routing-note[data-error=true]{border-color:#885c61;color:#ffc4c4}
#rvc .rvc-routing-note:not([data-error=true])::before{content:'✦ ';color:#7ed2ff}
@media(max-width:760px){#rvc .rvc-routing-note{font-size:11px;max-height:70px;overflow:auto}}
`}));
    const form=el('form',{},input,send,stop);
    const panel=el('section',{id:'rvc'},
      el('aside',{className:'rvc-sidebar'},el('div',{className:'rvc-brand'},'R O V O R',
        el('small',{},'MULTI-MODEL INTELLIGENCE')),newChat,el('div',{className:'rvc-label'},'CONVERSATIONS'),sessionsList,
        el('small',{},'Conversation history is stored on this device. Model text is not proof of employee execution.')),
      el('div',{className:'rvc-main'},
        el('header',{},mobileMenu,el('strong',{textContent:'ASK ROVOR'}),sourceSelect,modelSlot,clear,close),
        connectionBar,providerDetails,log,
        el('footer',{},teamRow,repoRow,routingNote,el('div',{className:'rvc-context-note',textContent:'A routing plan does not start work. Send submits at most two eligible routes; completion requires receipts.'}),form)));
    panel.setAttribute('aria-label','ROVOR chat');
    const sideBackdrop=el('button',{type:'button',className:'rvc-side-backdrop'});
    sideBackdrop.setAttribute('aria-label','Close conversation history');
    panel.append(sideBackdrop,modelSheet);
    sideBackdrop.onclick=()=>{panel.dataset.sideOpen='false';};
    document.body.append(fab,panel);

    // A deliberately separate route browser keeps the chat composer uncluttered.
    // Selection is explicit and never starts inference or changes providers.
    function closeModelSheet(){
      modelSheet.hidden=true;
      modelBrowse.setAttribute('aria-expanded','false');
      modelSearch.blur();
    }
    function renderModelSheet(){
      modelRows.textContent='';
      const query=modelSearch.value.trim().toLowerCase();
      const options=Array.from(select.options).filter(o=>o.value&&
        (o.value.toLowerCase().includes(query)||(o.parentElement?.label||'').toLowerCase().includes(query)));
      if(!options.length){
        modelRows.append(el('p',{className:'rvc-model-empty',textContent:sourceSelect.value==='omniroute'?'No matching local route. Refresh the optional Mac bridge.':'No cloud route available. Check the private cloud model configuration.'}));
      }
      const groups=new Map();
      for(const option of options){
        const group=option.parentElement?.tagName==='OPTGROUP'?option.parentElement.label:'Other models';
        if(!groups.has(group)){
          const container=el('div',{className:'rvc-model-group'});
          container.append(el('h3',{textContent:group}));
          groups.set(group,container);modelRows.append(container);
        }
        const isSelected=option.value===select.value;
        const button=el('button',{type:'button',className:'rvc-model-option',textContent:option.value});
        button.setAttribute('aria-current',String(isSelected));
        const help=el('small',{textContent:isSelected?'Selected route':'Select this available route'});
        button.append(help);
        button.append(el('small',{textContent:modelEvidenceHint(option.value)}));
        button.onclick=()=>{
          select.value=option.value;
          select.dispatchEvent(new Event('change',{bubbles:true}));
          closeModelSheet();
        };
        groups.get(group).append(button);
      }
      // All nine provider families are visible; missing routes cannot be clicked.
      if(sourceSelect.value==='omniroute'&&!query){
        const existing=new Set(groups.keys());
        for(const [,label] of PROVIDERS){
          if(existing.has(label+' · Mac-advertised chat routes'))continue;
          const section=el('div',{className:'rvc-model-group'});
          section.append(el('h3',{textContent:label}),
            el('div',{className:'rvc-model-notready',textContent:'No free-eligible route advertised. Provider access, allowance or admission needs verification.'}));
          modelRows.append(section);
        }
      }
    }
    modelBrowse.onclick=()=>{
      if(busy||!ready)return;
      modelSearch.value='';
      renderModelSheet();
      modelSheet.hidden=false;
      modelBrowse.setAttribute('aria-expanded','true');
      modelSearch.focus({preventScroll:true});
    };
    modelSearch.oninput=renderModelSheet;
    modelSheetClose.onclick=closeModelSheet;
    modelSheet.onclick=e=>{if(e.target===modelSheet)closeModelSheet();};
    modelSearch.onkeydown=e=>{if(e.key==='Escape'){e.preventDefault();closeModelSheet();}};
    const add=(cls,text,meta=null)=>{
      const n=el('div',{className:'rvc-msg '+cls});
      const inner=el('div',{className:'rvc-message-body'});renderText(inner,text);n.append(inner);
      if(meta&&meta.role==='assistant'&&meta.outcome){
        const receipt=el('div',{className:'rvc-receipt'});
        const state=meta.outcome==='complete'?'REPLY RECEIVED':meta.outcome==='failed'?'NOT COMPLETED':'UNVERIFIED';
        const provider=meta.platform==='omniroute'?'OMNIROUTE REQUEST':'CLOUDFLARE AI';
        const route=typeof meta.model==='string'?meta.model.slice(0,80):'Unknown route';
        receipt.textContent=state+' · '+provider+' · '+route;
        if(meta.outcome==='complete'&&meta.repo_file&&meta.platform==='omniroute')
          receipt.textContent+=' · READ-ONLY GIT SNAPSHOT '+String(meta.repo_file).slice(0,100);
        if(meta.receipt&&/^[a-f0-9-]{36}$/i.test(meta.receipt))receipt.title='Private job receipt '+meta.receipt+' (this is a local copy of its last known result)';
        n.append(receipt);
        if(meta.outcome==='complete'){
          const copy=el('button',{className:'rvc-copy',type:'button',textContent:'Copy response'});
          copy.setAttribute('aria-label','Copy this model response');
          copy.onclick=async()=>{
            try{await navigator.clipboard.writeText(meta.content);copy.textContent='Copied';}
            catch{copy.textContent='Copy unavailable';}
          };
          n.append(copy);
        }
      }
      log.append(n);log.scrollTop=log.scrollHeight;return inner;
    };
    const drawSessions=()=>{
      sessionsList.textContent='';
      sessions.forEach(s=>{const b=el('button',{type:'button',textContent:s.title, title:s.title});
        b.setAttribute('aria-current',String(s.id===currentId));
        b.onclick=()=>{if(busy)return;save();currentId=s.id;history=s.history.slice();panel.dataset.sideOpen='false';sourceSelect.value=['cloudflare','gemini','omniroute'].includes(s.source)?s.source:'gemini';load();redraw();drawSessions();};
        sessionsList.append(b);});
    };
    const welcome=()=>{
      const chips=el('div',{className:'rvc-chips'});
      PROMPTS.forEach(q=>chips.append(el('button',{type:'button',textContent:q,onclick:()=>{
        // A suggestion is a draft, never an implicit model execution.
        input.value=q;input.dispatchEvent(new Event('input',{bubbles:true}));
        if(!window.matchMedia('(pointer:coarse)').matches)input.focus({preventScroll:true});
      }})));
      const n=el('div',{className:'rvc-welcome'},el('h2',{},'Intelligence, your way.'),
        el('p',{},'Choose a model and receive a real answer. Chat alone does not start employee jobs.'),chips);log.append(n);
    };
    const redraw=()=>{log.textContent='';if(!history.length)welcome();history.forEach(m=>add(m.role==='user'?'rvc-user':m.outcome==='failed'?'rvc-err':'rvc-bot',m.content,m));};
    let pendingJob=null,cancelConfirmed=false,multiPending=[];
    const setBusy=b=>{busy=b;send.disabled=b||!ready;stop.hidden=!b;input.disabled=b;select.disabled=b;sourceSelect.disabled=b;modelBrowse.disabled=b||!ready;refreshButton.disabled=b;repoSelect.disabled=b||sourceSelect.value!=='omniroute';teamInput.disabled=b||sourceSelect.value!=='omniroute';
      // Don't re-open the software keyboard after a delayed response on iOS.
      if(!b&&panel.dataset.open==='true'&&!window.matchMedia('(pointer:coarse)').matches)input.focus({preventScroll:true});
    };
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
    let priorOverflow=null,autoRefresh=null;
    const toggle=open=>{
      panel.dataset.open=String(open);
      if(!open){panel.dataset.sideOpen='false';closeModelSheet();}
      fab.setAttribute('aria-expanded',String(open));
      if(open){
        priorOverflow=document.body.style.overflow;
        document.body.style.overflow='hidden';
        // Recover automatically if the Mac bridge appears after the HUD opens.
        // Avoid interrupting typing, in-flight jobs or the model browser.
        clearInterval(autoRefresh);
        autoRefresh=setInterval(()=>{
          if(panel.dataset.open!=='true'||busy||!modelSheet.hidden||input.value.trim())return;
          load();refreshProviderInventory();
        },30000);
      }else{
        clearInterval(autoRefresh);autoRefresh=null;
        document.body.style.overflow=priorOverflow??'';
        priorOverflow=null;
        input.blur();
      }
      syncVisualViewport();
      // Avoid opening the iOS keyboard the moment the app launches.
      // Desktop typing remains one-step with autofocus.
      if(open){load();refreshProviderInventory();if(!window.matchMedia('(max-width:760px)').matches)input.focus({preventScroll:true});}
    };

    async function refreshProviderInventory(){
      if(panel.dataset.open!=='true')return;
      if(sourceSelect.value!=='omniroute'){
        if(sourceSelect.value==='groq'){
          try{
            const response=await fetch('/api/chat/groq/status',{credentials:'same-origin',cache:'no-store'});
            if(!response.ok)throw Error('cloud_status_unavailable');
            const data=await response.json();
            if(panel.dataset.open!=='true')return;
            providerSummary.textContent='CLOUD GROQ · '+(data.ready?'CONFIGURED':'NOT VERIFIED')+' · NO MAC REQUIRED';
            providerList.textContent='';
            const chip=el('div',{className:'rvc-provider-item',textContent:'Groq · GPT-OSS 20B'});
            chip.append(el('small',{textContent:'Cloud calls admitted today: '+(Number.isSafeInteger(data.locally_admitted_today)?data.locally_admitted_today:'unknown')+
              ' · Last cloud completion: '+(data.last_cloud_completion_at?new Date(data.last_cloud_completion_at).toLocaleString():'none recorded')+' · Provider quota unknown'}));
            providerList.append(chip);
          }catch{providerSummary.textContent='CLOUD GROQ STATUS UNAVAILABLE · NO MAC REQUIRED';providerList.textContent='';}
        }else{
          providerSummary.textContent='CLOUD INFERENCE · '+sourceSelect.value.toUpperCase()+' · NO MAC REQUIRED';
          providerList.textContent='';
          providerList.append(el('div',{className:'rvc-provider-item',textContent:'This cloud source runs without your Mac. Local OmniRoute telemetry is separate.'}));
        }
        return;
      }
      try{
        const reply=await fetch('/api/hud/omniroute?period=24h',{credentials:'same-origin',cache:'no-store'});
        if(!reply.ok)throw Error('telemetry_unavailable');
        const data=await reply.json();
        if(panel.dataset.open!=='true')return;
        const rows=Array.isArray(data?.connections)?data.connections.filter(p=>typeof p?.provider==='string').slice(0,20):[];
        const time=Date.parse(data?.snapshot_at);
        const fresh=data?.transport?.connection==='fresh'&&Number.isFinite(time)&&Date.now()-time<=15000;
        const date=Number.isFinite(time)?new Date(time).toLocaleString(): 'unknown date';
        providerSummary.textContent=rows.length+' CONFIGURED CONNECTIONS · '+(fresh?'RECENT TELEMETRY':'STALE / NOT LIVE')+' · '+date;
        providerList.textContent='';
        if(!rows.length){providerList.append(el('div',{className:'rvc-provider-item',textContent:'No provider evidence. This does not mean there are zero connections.'}));return;}
        for(const item of rows){
          const count=Number.isSafeInteger(item.enabled_count)?item.enabled_count:0;
          const label=String(item.name||item.provider).slice(0,48);
          const chip=el('div',{className:'rvc-provider-item',textContent:label});
          chip.append(el('small',{textContent:count+' configured enabled · '+(fresh?'model access unverified':'last report stale')}));
          providerList.append(chip);
        }
      }catch{
        providerSummary.textContent='PROVIDER INVENTORY UNAVAILABLE · NO LIVE VERIFICATION';
        providerList.textContent='';
      }
    }
    let loadEpoch=0;
    async function load(){
      const epoch=++loadEpoch, requestedSource=sourceSelect.value;
      ready=false;send.disabled=true;modelBrowse.disabled=true;closeModelSheet();stateLabel.textContent='Checking '+requestedSource+' model availability…';
      try{
        const omni=requestedSource==='omniroute';
        const catalogPath=omni?'/api/hud/chat/models':requestedSource==='gemini'?'/api/hud/gemini/models':'/api/chat/models';
        const r=await fetch(catalogPath,{credentials:'same-origin',cache:'no-store'});
        if(!r.ok)throw Error('catalog_unavailable');
        const info=await r.json(),models=requestedSource==='groq'?(Array.isArray(info.models)?info.models.filter(id=>id==='groq/openai/gpt-oss-20b'):[]):info.models;
        if(epoch!==loadEpoch)return; // Ignore a slow catalog from the previous provider tab.
        if(((omni||requestedSource==='gemini')&&info.online!==true)||!Array.isArray(models)||!models.length)throw Error('catalog_unavailable');
        select.textContent='';
        if(omni){
          const smart=el('optgroup',{label:'ROVOR task routing'});
          smart.append(el('option',{value:AUTO_ROUTE,textContent:'✦ Smart routing · by task'}));
          select.append(smart);
        }
        // Native grouped selection remains fully keyboard and touch accessible.
        const groups=new Map();
        for(const id of models){
          if(typeof id!=='string')continue;
          const group=omni?routeGroup(id):requestedSource==='gemini'?'Google Gemini · cloud direct':requestedSource==='groq'?'Groq · cloud direct':'Cloudflare AI hosted routes';
          if(!groups.has(group)){const optgroup=el('optgroup',{label:group});groups.set(group,optgroup);select.append(optgroup);}
          groups.get(group).append(el('option',{value:id,textContent:id}));
        }
        if(!select.options.length)throw Error('catalog_unavailable');
        const preferred=sessions.find(s=>s.id===currentId)?.model;
        const saved=localStorage.getItem(KEY+'_model_'+requestedSource);
        if(preferred&&(models.includes(preferred)||(omni&&preferred===AUTO_ROUTE)))select.value=preferred;
        else if(saved&&(models.includes(saved)||(omni&&saved===AUTO_ROUTE)))select.value=saved;
        else if(omni)select.value=AUTO_ROUTE;
        stateLabel.textContent=omni?('Mac bridge reported · '+select.options.length+' allowed routes · confirm a reply to verify use · optional local execution'):
          requestedSource==='gemini'?'Google Gemini cloud route ready · project free-tier attested; remaining quota unknown':
          requestedSource==='groq'?'Groq cloud route available · no Mac required · remaining quota unverified':
          ('Cloudflare AI · '+select.options.length+' hosted models listed · allowance unverified');
        modelSheetInfo.textContent=omni
          ?'Mac-advertised chat routes only. Free-tagged model routes and Owner-allowlisted model routes still need live inference and free-quota checks.'
          :requestedSource==='gemini'?'Direct Google Gemini cloud API; Mac not required. Free-tier project must remain Free. Google may use Free-tier content to improve services.':requestedSource==='groq'?'Direct Groq cloud API; Mac not required. Requires current owner-verified free-tier approval. Quota remaining is unknown.':'Cloudflare-hosted inference is separate from OmniRoute. Its allowance is not guaranteed.';
        ready=true;send.disabled=false;modelBrowse.disabled=false;updatePlan();
      }catch{
        if(epoch!==loadEpoch)return;
        modelBrowse.disabled=true;select.textContent='';select.append(el('option',{value:'',textContent:'No models available'}));
        updatePlan();
        stateLabel.textContent=sourceSelect.value==='omniroute'?
          'Optional Mac bridge unavailable · use cloud Gemini or Cloudflare AI.':
          sourceSelect.value==='gemini'?'Cloud Gemini unavailable · cloud key/free-tier configuration required.':
          sourceSelect.value==='groq'?'Cloud Groq unavailable · cloud key/free-tier configuration required.':
          'Cloudflare AI unavailable · no hosted model routes confirmed.';
      }
    }
    function currentPlan(message=input.value.trim()){
      if(sourceSelect.value!=='omniroute')return {routes:select.value?[select.value]:[],reason:sourceSelect.value==='gemini'?'Google Gemini cloud · direct model, no Mac':sourceSelect.value==='groq'?'Groq cloud · direct model, no Mac':'Cloudflare AI · hosted model'};
      return planRoutes(message,Array.from(select.options).map(o=>o.value),select.value,{allowTeam:teamInput.checked});
    }
    function updatePlan(){
      const plan=currentPlan();
      routingNote.dataset.error=String(!!plan.error);
      routingNote.textContent=plan.error
        ?plan.error
        :plan.routes.length
          ?(plan.routes.length===2?'Two-model review: ':'Selected route: ')+plan.routes.join(' + ')+' · '+plan.reason
          :'No available route. Check the Mac connection.';
      if(!busy)send.disabled=!ready||!!plan.error||!plan.routes.length;
      return plan;
    }
    input.addEventListener('input',()=>{if(!busy)updatePlan();});
    teamInput.addEventListener('change',()=>{if(!busy)updatePlan();});
    refreshButton.onclick=()=>{if(!busy){load();refreshProviderInventory();}};
    sourceSelect.onchange=()=>{if(!busy){
      repoRow.hidden=sourceSelect.value!=='omniroute';repoSelect.disabled=repoRow.hidden;
      teamRow.hidden=sourceSelect.value!=='omniroute';teamInput.disabled=teamRow.hidden;
      const active=sessions.find(s=>s.id===currentId);
      if(active){active.source=sourceSelect.value;active.model=null;save();}
      load();refreshProviderInventory();updatePlan();
    }};
    select.onchange=()=>{
      const active=sessions.find(s=>s.id===currentId);
      if(active){active.source=sourceSelect.value;active.model=select.value;save();}
      try{localStorage.setItem(KEY+'_model_'+sourceSelect.value,select.value);}catch{}
      updatePlan();
    };

    // Two independent, explicitly submitted model requests. Each has its own
    // private receipt; the Mac may execute them sequentially (not parallel).
    // Never claim both responded unless both receipts actually completed.
    async function askBoth(text,plan){
      const routes=plan.routes.slice(0,2);
      const attachedSource=repoSelect.value;
      const thread=sessions.find(s=>s.id===currentId);
      if(thread){thread.source='omniroute';thread.model=AUTO_ROUTE;}
      history.push({role:'user',content:text});add('rvc-user',text);
      if(thread?.title==='New conversation')thread.title=text.replace(/\s+/g,' ').slice(0,55);
      save();drawSessions();
      const bubble=add('rvc-bot','Preparing two sequential model calls · no model calls confirmed');
      multiPending=[];pendingJob=null;cancelConfirmed=false;controller=new AbortController();setBusy(true);
      const signal=controller.signal;
      const messages=history.filter(m=>m.role==='user'||(m.role==='assistant'&&m.outcome==='complete'))
        .slice(-5).map(m=>({role:m.role,content:m.content.slice(0,5500)}));
      const outcomes=new Map();
      const show=()=>{
        const status=routes.map(id=>id+': '+(outcomes.get(id)||'Preparing request')).join('\n');
        renderText(bubble,status);
      };
      async function runOne(model,firstResult=null){
        // The second model reviews the first *confirmed* response, rather
        // than blindly repeating the same prompt. Never accept a failed or
        // partial receipt as input to a verification step.
        const reviewMessage=firstResult?.state==='complete'
          ?('Independent critical review. Original task: '+text.slice(0,1500)+
            '\nFirst model draft ('+firstResult.model+'): '+firstResult.reply.slice(0,3000)+
            '\nIdentify weaknesses, factual uncertainty, and a concrete improved answer. Do not claim GitHub edits or tool execution.')
          :null;
        const safeMessages=reviewMessage
          ?[{role:'user',content:reviewMessage}]
          :messages.map(item=>({...item,content:item.content.slice(0,5500)}));
        const payload={model,context:false,messages:safeMessages};
        if(attachedSource)payload.repo_file=attachedSource;
        let jobId=null;
        const attemptStarted=Date.now();
        try{
          const posted=await fetch('/api/hud/chat/submit',{method:'POST',credentials:'same-origin',
            signal,headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
          const ack=await posted.json().catch(()=>({}));
          if(posted.status!==202||!ack.job_id)throw Error(ack.error||'request_not_accepted');
          jobId=ack.job_id;
          const pending={id:jobId,model,phase:'queued'};
          multiPending.push(pending);
          outcomes.set(model,firstResult?.state==='complete'?'Review queued; Mac claim not yet confirmed':'Queued; Mac claim not yet confirmed');show();
          stop.textContent='Cancel queued requests / stop waiting';
          for(let i=0;i<105;i++){
            if(signal.aborted)throw Error('stopped_waiting');
            await new Promise(resolve=>setTimeout(resolve,1250));
            if(signal.aborted)throw Error('stopped_waiting');
            const check=await fetch('/api/hud/chat/status/'+encodeURIComponent(jobId),
              {credentials:'same-origin',signal,cache:'no-store'});
            if(!check.ok)throw Error('receipt_unavailable');
            const item=await check.json();
            if(item.state==='queued'){pending.phase='queued';continue;}
            if(item.state==='running'){
              pending.phase='running';
              outcomes.set(model,'Claimed by Mac; awaiting reply');
              show();continue;
            }
            if(item.state==='complete'&&typeof item.output==='string'&&item.output.trim()){
              if(item.requested_model!==model)throw Error('receipt_route_mismatch');
              pending.phase='complete';recordReceipt(model,'complete',Date.now()-attemptStarted);
              outcomes.set(model,'Reply confirmed');show();
              return {state:'complete',model,reply:item.output,receipt:jobId};
            }
            if(item.state==='failed'){
              if(pending.phase==='running')recordReceipt(model,'failed',Date.now()-attemptStarted);
              throw Error(item.error||'relay_failed');
            }
            throw Error('invalid_receipt');
          }
          throw Error('no_completion_receipt');
        }catch(error){
          const message=error.name==='AbortError'?'stopped_waiting':String(error.message||'unverified');
          outcomes.set(model,'Not confirmed: '+message);show();
          return {state:'failed',model,reason:message,receipt:jobId};
        }
      }
      try{
        // The Mac bridge is a single bounded executor. Parallel submissions
        // can leave the second request queued until its D1 lease expires.
        // Serialize at most two calls; the second runs only if the first is
        // resolved, and both retain independent provider receipts.
        const results=[];
        for(const route of routes){
          if(signal.aborted){
            results.push({state:'failed',model:route,reason:'stopped_before_submit',receipt:null});
            continue;
          }
          results.push(await runOne(route,results[0]||null));
        }
        const successes=results.filter(item=>item.state==='complete').length;
        // Each model's reply remains independently attributed; no generated
        // "consensus" is fabricated if only one model completed.
        for(const result of results){
          const item=result.state==='complete'
            ?{role:'assistant',content:result.reply,platform:'omniroute',model:result.model,
               repo_file:attachedSource||null,receipt:result.receipt,outcome:'complete',recordedAt:Date.now()}
            :{role:'assistant',content:'No confirmed reply: '+result.reason,platform:'omniroute',
               model:result.model,receipt:result.receipt,outcome:'failed',recordedAt:Date.now()};
          history.push(item);
        }
        if(successes===2)
          stateLabel.textContent='TWO REPLIES CONFIRMED · requested routes independently recorded; upstream fallback unverified';
        else
          stateLabel.textContent=successes+' / 2 REPLIES CONFIRMED · failed routes are not counted as completed';
        save();redraw();
      }finally{
        multiPending=[];pendingJob=null;controller=null;setBusy(false);updatePlan();
      }
    }
    async function ask(text){
      if(!ready||busy)return;
      const platform=sourceSelect.value,plan=currentPlan(text);
      if(plan.error||!plan.routes.length){
        stateLabel.textContent='NO REQUEST SENT · '+(plan.error||'No eligible route');
        return;
      }
      if(platform==='omniroute'&&plan.routes.length>1)return askBoth(text,plan);
      const target=plan.routes[0],attachedSource=platform==='omniroute'?repoSelect.value:'';
      const thread=sessions.find(s=>s.id===currentId);if(thread){thread.source=platform;thread.model=target;}
      history.push({role:'user',content:text});add('rvc-user',text);
      const active=sessions.find(s=>s.id===currentId);
      if(active?.title==='New conversation')active.title=text.replace(/\s+/g,' ').slice(0,55);
      save();drawSessions();
      const bubble=add('rvc-bot','Preparing request · no model call confirmed');
      const singleStarted=Date.now();
      let reply='';pendingJob=null;cancelConfirmed=false;setBusy(true);stop.textContent='Stop waiting';controller=new AbortController();
      const signal=controller.signal;
      try{
        const payload={model:target,context:false,messages:history.filter(m=>m.role==='user'||(m.role==='assistant'&&m.outcome==='complete')).slice(-5).map(m=>({role:m.role,content:m.content.slice(0,5500)}))};
        if(attachedSource)payload.repo_file=attachedSource;
        if(platform==='omniroute'){
          const posted=await fetch('/api/hud/chat/submit',{method:'POST',credentials:'same-origin',signal,
            headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
          const ack=await posted.json().catch(()=>({}));
          if(posted.status!==202||!ack.job_id)throw Error(ack.error||'request_not_accepted');
          pendingJob={id:ack.job_id,phase:'queued'};
          stop.textContent='Cancel queued request';
          renderText(bubble,'HUD received request · queued, not yet executed');
          for(let i=0;i<100;i++){
            await new Promise(done=>setTimeout(done,1300));
            if(signal.aborted)throw Error('stopped_waiting');
            const r=await fetch('/api/hud/chat/status/'+encodeURIComponent(ack.job_id),{credentials:'same-origin',cache:'no-store',signal});
            if(!r.ok)throw Error('receipt_unavailable');
            const result=await r.json();
            if(result.state==='queued'){pendingJob.phase='queued';stop.textContent='Cancel queued request';if(i%4===0)renderText(bubble,'Queued · waiting for Mac bridge to claim');continue;}
            if(result.state==='running'){pendingJob.phase='running';stop.textContent='Stop waiting';if(i%4===0)renderText(bubble,'Claimed by Mac · waiting for actual model response');continue;}
            if(result.state==='complete'&&typeof result.output==='string'){
              if(result.requested_model!==target)throw Error('receipt_route_mismatch');
              recordReceipt(target,'complete',Date.now()-singleStarted);
              reply=result.output;break;
            }
            if(result.state==='failed'){
              if(pendingJob?.phase==='running')recordReceipt(target,'failed',Date.now()-singleStarted);
              throw Error(result.error||'relay_failed');
            }
            throw Error('invalid_receipt');
          }
          if(!reply)throw Error('no_completion_receipt');
        }else{
          const cloudEndpoint=platform==='gemini'?'/api/hud/gemini/chat':'/api/chat';
          const r=await fetch(cloudEndpoint,{method:'POST',credentials:'same-origin',signal,headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
          if(!r.ok){const err=await r.json().catch(()=>({}));throw Error(err.error||'cloud_chat_unavailable');}
          if(!r.body)throw Error('empty_stream');
          const reader=r.body.getReader(),dec=new TextDecoder();let buf='',completed=false;
          for(;;){
            const {done,value}=await reader.read();if(done)break;
            buf+=dec.decode(value,{stream:true});
            let i;while((i=buf.indexOf('\n'))>=0){
              const line=buf.slice(0,i).trim();buf=buf.slice(i+1);
              if(line==='data: [DONE]'){completed=true;continue;}
              if(!line.startsWith('data:'))continue;
              try{const piece=JSON.parse(line.slice(5).trim()).choices?.[0]?.delta?.content;
                if(typeof piece==='string'){reply+=piece;renderText(bubble,reply);log.scrollTop=log.scrollHeight;}}
              catch{}
            }
          }
          if(!reply)throw Error('empty_response');
          if(!completed)throw Error('incomplete_stream');
        }
        renderText(bubble,reply);
        history.push({role:'assistant',content:reply,platform,model:target,repo_file:platform==='omniroute'?(attachedSource||null):null,receipt:pendingJob?.id||null,outcome:'complete',recordedAt:Date.now()});save();
        redraw();
        stateLabel.textContent=platform==='omniroute'?
          'RESPONSE CONFIRMED · requested route '+target+' · actual upstream identity not separately attested':
          platform==='gemini'?'GOOGLE GEMINI CLOUD RESPONSE RECEIVED · Mac not required · not an employee action':'CLOUD MODEL RESPONSE RECEIVED · not an employee or Mac action';
      }catch(e){
        const messages={
          omniroute_offline:'The Mac bridge is offline. No model call was confirmed.',
          relay_timeout:'No receipt from Mac. A completed model call was not verified.',
          stopped_waiting:'You stopped waiting. If the Mac already claimed the request, it might still finish.',
          user_cancelled:'Request cancelled before the Mac claimed it. No inference started for this request.',
          chat_busy:'The private queue is full. No new model call was confirmed.',
          model_not_available:'Route unavailable or not verified eligible for free use.',
          receipt_route_mismatch:'Receipt route differs from the requested route. Reply cannot be verified.',
          chat_rate_limited:'The request limit has been reached.',
        };
        const message=cancelConfirmed?messages.user_cancelled:(messages[e.message]|| (e.name==='AbortError'?messages.stopped_waiting:('No confirmed model reply: '+(e.message||'unknown'))));
        renderText(bubble,message);bubble.parentElement.className='rvc-msg rvc-err';
        stateLabel.textContent='NO COMPLETION CONFIRMED · '+message;
        // Keep failures in local conversation history, but never send their
        // text to the next model as if it were an assistant answer.
        history.push({role:'assistant',content:message,platform,model:target,receipt:pendingJob?.id||null,outcome:'failed',recordedAt:Date.now()});save();
        redraw();
      }finally{pendingJob=null;controller=null;setBusy(false);updatePlan();}
    }

    repoRow.hidden=sourceSelect.value!=='omniroute';repoSelect.disabled=repoRow.hidden;
    teamRow.hidden=sourceSelect.value!=='omniroute';teamInput.disabled=teamRow.hidden;
    form.onsubmit=e=>{e.preventDefault();const text=input.value.trim();if(!text||busy||!ready)return;input.value='';ask(text);};
    // Touch keyboards use Return for a newline. Sending always needs an
    // explicit tap; desktop keyboards retain Enter to send / Shift+Enter newline.
    const touchCompose=window.matchMedia('(pointer:coarse)').matches;
    input.placeholder=touchCompose?'Message an available model…':'Message… Enter to send · Shift+Enter for newline';
    input.onkeydown=e=>{
      if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&!window.matchMedia('(pointer:coarse)').matches){
        e.preventDefault();form.requestSubmit();
      }
    };
    stop.onclick=async()=>{
      if(!controller)return;
      if(multiPending.length){
        stop.disabled=true;
        let cancelled=0,unverified=0;
        const queued=multiPending.filter(job=>job.phase==='queued');
        for(const job of queued){
          try{
            const response=await fetch('/api/hud/chat/cancel/'+encodeURIComponent(job.id),{
              method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:'{}'
            });
            const result=await response.json().catch(()=>({}));
            if(response.status===200&&result.cancelled===true){job.phase='cancelled';cancelled++;}
            else unverified++;
          }catch{unverified++;}
        }
        stateLabel.textContent='STOP WAITING · '+cancelled+' queued cancellation(s) confirmed; '+unverified+
          ' could not be cancelled; running inference may continue';
        controller.abort(); // Stops polling only; Mac inference already claimed may finish.
        stop.disabled=false;
        return;
      }
      if(pendingJob?.phase==='queued'){
        stop.disabled=true;
        try{
          const r=await fetch('/api/hud/chat/cancel/'+encodeURIComponent(pendingJob.id),{
            method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},
            body:'{}',cache:'no-store'
          });
          const result=await r.json().catch(()=>({}));
          if(r.status===200&&result.cancelled===true){
            cancelConfirmed=true;
            controller.abort();
            return;
          }
          if(r.status===409){
            pendingJob.phase='running';
            stop.textContent='Stop waiting';
            stateLabel.textContent='CANCELLATION TOO LATE · checking the actual result';
            return;
          }
          stateLabel.textContent='CANCELLATION NOT VERIFIED · still checking request status';
        }catch{stateLabel.textContent='CANCELLATION FAILED · still checking request status';}
        finally{stop.disabled=false;}
        return;
      }
      controller.abort(); // Already running: only stops this device waiting.
    };
    clear.onclick=()=>{if(busy)return;history=[];save();redraw();};
    newChat.onclick=()=>{if(busy)return;save();panel.dataset.sideOpen='false';currentId=crypto.randomUUID();history=[];
      sessions.unshift({id:currentId,title:'New conversation',source:sourceSelect.value,model:select.value||null,history:[]});sessions=sessions.slice(0,16);
      save();drawSessions();redraw();if(!window.matchMedia('(pointer:coarse)').matches)input.focus({preventScroll:true});};
    drawSessions();
    mobileMenu.onclick=()=>{panel.dataset.sideOpen=String(panel.dataset.sideOpen!=='true');};
    close.onclick=()=>toggle(false);fab.onclick=()=>toggle(panel.dataset.open!=='true');
    document.addEventListener('keydown',e=>{
      if(e.key!=='Escape'||panel.dataset.open!=='true')return;
      if(!modelSheet.hidden){closeModelSheet();return;}
      if(panel.dataset.sideOpen==='true'){panel.dataset.sideOpen='false';return;}
      toggle(false);
    });
    redraw();
  }
  window.ROVOR_HUD_CHAT={start:()=>{if(!document.getElementById('rvc'))build();}};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>window.ROVOR_HUD_CHAT.start());else window.ROVOR_HUD_CHAT.start();
})();
