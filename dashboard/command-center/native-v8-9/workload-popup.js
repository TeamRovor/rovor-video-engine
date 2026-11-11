/* Embedded module for the existing native v8.9 Workload Distribution focus popup.
   No requests, dispatch, keys, storage, or runtime-worker claims. */
(() => {
  'use strict';
  const EMPLOYEES=[
    ['walter','Walter','Supervisor'],['mike','Mike','Mac systems'],
    ['jane','Jane','Final Cut'],['jesse','Jesse','Moho 2D'],
    ['gale','Gale','Blender 3D'],['gus','Gus','Operations'],
    ['saul','Saul','Marketing'],['hank','Hank','Quality']
  ];
  // Owner-published Mac observation, not a live connection or inference proof.
  const OBSERVATION={at:'2026-10-24T09:53:41.264Z',connections:9,
    evidence:'https://github.com/TeamRovor/rovor-video-engine/pull/137#issuecomment-6382848776',
    inventoryEvidence:'https://github.com/TeamRovor/rovor-video-engine/pull/137#issuecomment-6382529114',
    claims:31,outcomes:[['Review-ready drafts',10],['Not review-ready',12],['Pending / failed review',8],['Running then',1]]};
  const MODEL_IDS=['openrouter/cohere/north-mini-code:free','openrouter/nvidia/nemotron-3-ultra-550b-a55b:free','openrouter/nvidia/nemotron-3.5-super-vl:free'];
  const MODELS=['North Mini Code','Nemotron 3 Ultra','Nemotron 3.5 Super VL'];
  const ROUTES=[['Code','Fast'],['Code','Reason'],['Fast','Reason','Vision']];
  const observedTime=()=>new Date(OBSERVATION.at).toLocaleString('en-US',{timeZone:'America/Chicago',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
  const outcomeBars=()=>`<section class="wl-card wl-outcomes"><h3>LAST MAC REPORT / 31 JOB CLAIMS</h3>
    <p class="wl-empty">${observedTime()} · historical owner-shared report, not current activity. Claims are attempts; review-ready drafts still need approval.</p>
    ${OBSERVATION.outcomes.map(([label,n])=>`<div class="wl-outcome"><span>${label}</span><span class="wl-meter"><i style="--wl-share:${(100*n/OBSERVATION.claims).toFixed(1)}%"></i></span><strong>${n} / 31</strong></div>`).join('')}
    <p class="wl-empty">Live link missing · per-model attribution missing · quota unknown. Nine provider connections do not establish nine working models.</p>
    <a class="wl-evidence" href="${OBSERVATION.evidence}" target="_blank" rel="noopener">Open recorded Mac evidence ↗</a></section>`;
  const htmlEscape=value=>String(value).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const fmt=n=>Number(n).toLocaleString('en-US');
  const periodScale={ '1H':1,'24H':6,'7D':19 };
  function simulatedCounts(period) {
    const factor=periodScale[period];
    return EMPLOYEES.map((_,i)=>MODELS.map((_,j)=>{
      const base=((i*13+j*7+3)%17);
      return (base<3?0:(base+((i+j)%5)))*factor;
    }));
  }
  function makeUI(state){
    const matrix=state.demo?simulatedCounts(state.period):null;
    const totals=MODELS.map((_,j)=>matrix?matrix.reduce((n,row)=>n+row[j],0):null);
    const grandTotal=state.demo?totals.reduce((a,b)=>a+b,0):null;
    const role=EMPLOYEES[state.employee];
    const model=MODELS[state.model];
    const chosen=matrix?.[state.employee]?.[state.model]??null;
    const countText=n=>n===null?'—':fmt(n);
    const viewButton=(id,name)=>`<button type="button" class="wl-button" data-wl-tab="${id}" aria-pressed="${state.view===id}">${name}</button>`;
    const periodButton=id=>`<button type="button" class="wl-button" data-wl-period="${id}" aria-pressed="${state.period===id}">${id}</button>`;
    const summary=`<div class="wl-summary">
      <div class="wl-stat"><small>Distinct routed models · last report</small><b>3 <span style="font-size:11px;font-weight:400">/ 9 connections reported</span></b></div>
      <div class="wl-stat"><small>Recorded model calls · ${state.period}</small><b>${countText(grandTotal)}</b></div>
      <div class="wl-stat"><small>Runtime source</small><b style="font-size:12px">${state.demo?'SAMPLE DATA':'NOT CONNECTED'}</b></div>
    </div>`;
    const details=`<section class="wl-card">
      <h3>SELECTED PAIR / ${role[1].toUpperCase()} × ${model}</h3>
      <div class="wl-details">
        <div><div class="wl-kicker">Ghost employee</div><p><strong>${role[1]}</strong> · ${role[2]}</p><p>${state.demo?'Illustrative workload only':'No verified worker heartbeat or active job'}</p></div>
        <div><div class="wl-kicker">Reported OmniRoute model</div><p><strong>${model}</strong></p><p class="wl-model-id">${MODEL_IDS[state.model]}</p><p>Routes: ${ROUTES[state.model].join(" / ")}</p><p>${state.demo?fmt(chosen)+' sample calls in selected period':'No measured requests, quota, cost or capacity'}</p></div>
      </div>
    </section>`;
    const header=`<div class="wl-toolbar">
      <span class="wl-kicker">OmniRoute / named employees / routing telemetry</span>
      ${state.view==='outcomes'?'':`<div class="wl-period" aria-label="Usage period">${['1H','24H','7D'].map(periodButton).join('')}</div>`}
    </div>
    <div class="wl-notice" role="status">
      <strong>${state.demo?'DEMONSTRATION — SYNTHETIC NUMBERS':'NO VERIFIED LIVE MODEL TELEMETRY'}</strong> ·
      ${state.demo?'All counts and illuminated routes are fabricated for layout testing. Nothing is running from this preview.':'Model names below come from the last Mac report. Live heartbeat and per-model inference receipts are not connected. Unknown is not zero usage.'}
    </div>
    <div class="wl-toolbar"><div class="wl-actions" role="group" aria-label="Workload views">
      ${viewButton('outcomes','JOB OUTCOMES')}${viewButton('matrix','EMPLOYEE × MODEL')}
      ${viewButton('models','3 REPORTED MODELS')}
      ${viewButton('routing','ROUTING')}
    </div>
    <button type="button" class="wl-button" data-wl-demo aria-pressed="${state.demo}">${state.demo?'EXIT SAMPLE MODE':'VIEW SAMPLE LAYOUT'}</button></div>`;
    let visual='';
    if(state.view==='outcomes'){visual=outcomeBars();}else if(state.view==='matrix'){
      visual=`<section class="wl-card">
        <h3>EMPLOYEE × AI MODEL / REQUEST ACTIVITY</h3>
        <div class="wl-scrollhint">SWIPE LEFT OR RIGHT FOR MODEL NAMES ↔</div>
        <div class="wl-matrix-scroll" tabindex="0" role="region" aria-label="Scrollable employee model usage matrix">
          <table class="wl-matrix"><thead><tr><th scope="col">EMPLOYEE</th>${MODELS.map((m,j)=>`<th scope="col"><span title="${MODEL_IDS[j]}">${htmlEscape(m)}</span></th>`).join('')}</tr></thead>
          <tbody>${EMPLOYEES.map((emp,i)=>`<tr>
          <th scope="row"><button type="button" class="wl-row-select" data-wl-employee="${i}" aria-pressed="${state.employee===i}">${emp[1]}</button></th>
          ${MODELS.map((m,j)=>{
            const n=matrix?.[i]?.[j]??null;
            const value=n===null?'—':(n===0?'0':String(n));
            const selected=state.employee===i&&state.model===j;
            const alpha=n===null?0:Math.max(.2,Math.min(.95,n/(Math.max(...(totals.filter(Number.isFinite)))||1)));
            return `<td><button class="wl-cell" type="button" data-wl-cell="${i}-${j}" data-active="${n!==null&&n>0?'yes':'no'}" aria-pressed="${selected}" style="--wl-intensity:${alpha.toFixed(2)}" aria-label="${emp[1]}, ${htmlEscape(m)}, ${n===null?'unverified':n+' sample calls'}">${value}</button></td>`;
          }).join('')}</tr>`).join('')}</tbody></table>
        </div>
        <div class="wl-key"><span>Blue intensity: relative calls (sample mode only)</span><span>— : no verified telemetry</span></div>
      </section>`;
    }else if(state.view==='models'){
      visual=`<section class="wl-card"><h3>OMNIROUTE / REPORTED MODEL IDENTITIES</h3>
        <p class="wl-empty">Request share is not remaining quota or model capacity. Names and routes were reported on ${observedTime()}; request counts and remaining quota are unavailable. Six additional model identities have not been established.</p>
        <div class="wl-models">${MODELS.map((m,j)=>{
           const v=totals[j],share=grandTotal?100*v/grandTotal:0;
           return `<button type="button" class="wl-model-entry" data-wl-model="${j}" aria-pressed="${state.model===j}">
             <span class="wl-row"><strong>${m}</strong><small>${state.demo?share.toFixed(1)+'% of sample calls':'NO USAGE RECEIPTS'}</small></span>
             ${state.demo?`<span class="wl-meter" aria-hidden="true"><i style="--wl-share:${share.toFixed(1)}%"></i></span>`:''}
             <span class="wl-row"><small>${state.demo?fmt(v)+' sample requests':htmlEscape(MODEL_IDS[j])}</small><small>↗ INSPECT</small></span>
           </button>`}).join('')}</div></section>`;
    }else{
      // Static SVG is driven only by explicit sample mode. Unverified routes are intentionally unlit.
      const left=EMPLOYEES.map((emp,i)=>{
        const y=24+i*34,selected=state.employee===i;
        return `<text x="18" y="${y+4}" font-size="11" fill="${selected?'#e6f8ff':'#80b1dc'}">${emp[1]}</text>
        <line x1="92" y1="${y}" x2="205" y2="143" stroke="${state.demo&&selected?'#8cd6ff':'#38577a'}" stroke-width="${selected?2:1}" stroke-dasharray="${state.demo&&selected?'none':'3 6'}" opacity="${state.demo&&selected?0.9:0.3}"/>`}).join('');
      const right=MODELS.map((m,j)=>{
        const y=16+j*33;
        const active=state.demo&&matrix[state.employee][j]>0;
        return `<line x1="275" y1="143" x2="400" y2="${y+4}" stroke="${active?'#8cd6ff':'#38577a'}" stroke-width="${active?2:1}" stroke-dasharray="${active?'none':'3 6'}" opacity="${active?0.8:0.25}"/>
        <circle cx="407" cy="${y+4}" r="7" fill="${active?'#257bbf':'#0c2748'}" stroke="#73b8e9"/>
        <text x="421" y="${y+8}" font-size="11" fill="${state.model===j?'#e6f8ff':'#9acbea'}">${htmlEscape(m)}</text>`}).join('');
      visual=`<section class="wl-card"><h3>SELECTED EMPLOYEE / ROUTE TO OMNIROUTE MODELS</h3>
      <div class="wl-route-layout"><div><div class="wl-kicker" style="margin-bottom:9px">Choose employee</div>
        <div class="wl-employees">${EMPLOYEES.map((emp,i)=>`<button type="button" data-wl-employee="${i}" aria-pressed="${state.employee===i}">${emp[1]}</button>`).join('')}</div></div>
        <div><svg class="wl-route-chart" viewBox="0 0 610 315" role="img" aria-label="Conceptual routing diagram. Only sample mode shows synthetic route activity.">
          ${left}${right}<circle cx="240" cy="143" r="38" fill="#10355c" stroke="#8ad6ff" stroke-width="2"/>
          <circle cx="240" cy="143" r="31" fill="none" stroke="#4d9bd5" stroke-dasharray="3 5"/>
          <text x="240" y="139" text-anchor="middle" font-size="13" fill="#f1fbff">OMNI</text><text x="240" y="153" text-anchor="middle" font-size="10" fill="#b1d9fa">ROUTE</text></svg></div>
      </div><p class="wl-empty">Routing connections are only illuminated in sample mode. Live edges will require authenticated inference receipts—not estimates from GitHub task claims.</p>
      </section>`;
    }
    return header+summary+visual+(state.view==='outcomes'?'':details);
  }

  // Workload Distribution card content only. The parent panel dimensions and
  // existing ROVOR HUD frame are untouched.
  let compactPick=null;
  let retainedPopup=null;
  // Real, authenticated nine-provider request-log preview. This never claims
  // provider quota, a valid free-model entitlement or live inference admission.
  // The local gateway is optional; the fixed identities remain readable with
  // the Mac powered off, while all unsupported counters become UNKNOWN.
  const HOME_PROVIDERS=[
    ['gemini','Gemini'],['groq','Groq'],['nvidia','NVIDIA'],
    ['mistral','Mistral'],['cloudflare','Cloudflare'],['openrouter','OpenRouter'],
    ['cohere','Cohere'],['sambanova','SambaNova'],['huggingface','Hugging Face']
  ];
  let previewRoot=null,previewPaint=null,previewTimer=null;
  let previewBusy=false,previewSnapshot=null,previewCheckedAt=0;
  let compactTab='providers';
  const homeCount=n=>Number.isSafeInteger(n)&&n>=0&&n<=1000000000?n:null;
  function readHomeUsage(doc,now=Date.now()){
    const usage=doc?.request_usage;
    const observed=Date.parse(usage?.observed_at||'');
    const snapshotAt=Date.parse(doc?.snapshot_at||'');
    if(doc?.source!=='local_omniroute_read_only_bridge'||doc.period!=='24h'||
       doc?.transport?.connection!=='fresh'||
       usage?.source!=='omniroute_durable_call_logs'||usage.freshness!=='fresh'||
       !['complete','partial'].includes(usage.coverage)||
       !Number.isFinite(observed)||observed>now+5000||now-observed>30000||
       !Number.isFinite(snapshotAt)||snapshotAt>now+5000||now-snapshotAt>30000||
       !Array.isArray(usage.providers)||usage.providers.length!==HOME_PROVIDERS.length)
      return null;
    const valid=new Set(HOME_PROVIDERS.map(x=>x[0])),seen=new Set(),providers=[];
    for(const item of usage.providers){
      if(!item||!valid.has(item.provider)||seen.has(item.provider)||
         typeof item.configured!=='boolean')return null;
      const attempts=homeCount(item.attempts_pacific_day);
      const successes=homeCount(item.successes_pacific_day);
      if(attempts===null||successes===null||successes>attempts)return null;
      seen.add(item.provider);
      providers.push({id:item.provider,attempts,successes,configured:item.configured});
    }
    if(seen.size!==HOME_PROVIDERS.length)return null;
    return {observed_at:observed,coverage:usage.coverage,providers,
      active:providers.filter(x=>x.attempts>0).length,
      attempts:providers.reduce((n,x)=>n+x.attempts,0),
      successes:providers.reduce((n,x)=>n+x.successes,0)};
  }
  async function refreshHomeUsage(){
    if(previewBusy||document.hidden===true||!previewRoot||previewRoot.isConnected===false)return;
    previewBusy=true;
    try{
      const response=await fetch('/api/hud/omniroute?period=24h',{
        credentials:'same-origin',cache:'no-store',
        signal:typeof AbortSignal!=='undefined'&&typeof AbortSignal.timeout==='function'
          ?AbortSignal.timeout(8000):undefined
      });
      previewSnapshot=response.ok?readHomeUsage(await response.json()):null;
    }catch{previewSnapshot=null;}
    finally{
      previewCheckedAt=Date.now();
      previewBusy=false;
      if(previewRoot&&previewRoot.isConnected!==false)previewPaint?.();
    }
  }
  function mountPreview(container,openDetails){
    if(!container)return;
    container.replaceChildren();
    const root=document.createElement('div');
    root.className='wl-compact wl-live-home';
    previewRoot=root;
    const paint=()=>{
      if(previewRoot!==root||root.isConnected===false)return;
      const recent=previewSnapshot&&Date.now()-previewCheckedAt<=90000?previewSnapshot:null;
      const providers=new Map(recent?.providers?.map(x=>[x.id,x])||[]);
      const header=recent?'LIVE LOG · '+(recent.coverage==='partial'?'PARTIAL COVERAGE':'9 PROVIDERS'):
        previewCheckedAt?'TELEMETRY UNAVAILABLE · NOT ZERO':'CHECKING PRIVATE TELEMETRY';
      const summary=recent?'<span>'+recent.active+' / 9 WITH CALLS</span><span>'+recent.attempts.toLocaleString()+' ATTEMPTS</span><span>'+recent.successes.toLocaleString()+' LOGGED SUCCESSES</span>':
        '<span>9 PROVIDERS TRACKED</span><span>USAGE UNKNOWN</span>';
      const entries=compactTab==='providers'?HOME_PROVIDERS.map(([id,label])=>{
        const item=providers.get(id);
        const amount=item?item.attempts.toLocaleString()+' CALLS':'UNKNOWN';
        const result=item?(item.attempts?item.successes.toLocaleString()+' LOGGED SUCCESSES':'NO LOGGED CALLS'):'NO FRESH RECEIPT';
        return '<button type="button" class="wl-home-provider" data-wl-compact-provider="'+id+
          '" aria-label="'+label+', '+amount+', open complete workload reports">'+
          '<strong>'+label+'</strong><span>'+amount+'</span><small>'+result+'</small></button>';
      }).join(''):EMPLOYEES.map(role=>'<button type="button" class="wl-compact-row" data-wl-compact-employee="'+role[0]+
        '" aria-label="'+role[1]+', open workforce reports">'+
        '<span class="wl-compact-name">'+role[1]+'</span><span class="wl-compact-status">INSPECT IN WORKLOAD</span>'+
        '<span class="wl-compact-value">›</span></button>').join('');
      const markup='<div class="wl-compact-tabs" role="group" aria-label="Workload preview type">'+
        '<button type="button" data-wl-compact-tab="providers" aria-pressed="'+(compactTab==='providers')+
        '">PROVIDERS <small>09</small></button><button type="button" data-wl-compact-tab="employees" aria-pressed="'+(compactTab==='employees')+
        '">EMPLOYEES <small>08</small></button></div>'+
        '<div class="wl-home-meta"><span class="wl-compact-dot" aria-hidden="true"></span><span>'+header+
        '</span><button type="button" data-wl-refresh aria-label="Refresh private provider activity">REFRESH</button></div>'+
        '<div class="wl-home-summary" aria-label="Logged activity, not provider quota">'+summary+'</div>'+
        '<div class="'+(compactTab==='providers'?'wl-home-provider-grid':'wl-compact-items wl-home-employee-list')+'">'+entries+'</div>'+
        '<div class="wl-home-foot"><span>REQUEST LOG ≠ QUOTA OR VERIFIED MODEL ADMISSION</span>'+
        '<button type="button" data-wl-open-report>OPEN FULL WORKLOAD ›</button></div>';
      if(root.innerHTML!==markup){
        const focused=document.activeElement&&root.contains(document.activeElement)
          ?document.activeElement.getAttribute('data-wl-compact-tab')||
            document.activeElement.getAttribute('data-wl-compact-provider')||
            document.activeElement.getAttribute('data-wl-refresh'):null;
        root.innerHTML=markup;
        if(focused){
          const buttons=[...root.querySelectorAll('button')];
          buttons.find(x=>x.getAttribute('data-wl-compact-tab')===focused||
            x.getAttribute('data-wl-compact-provider')===focused||
            (focused===''&&x.hasAttribute('data-wl-refresh')))?.focus({preventScroll:true});
        }
      }
    };
    previewPaint=paint;
    root.addEventListener('click',event=>{
      const target=event.target.closest('button');
      if(!target||!root.contains(target))return;
      if(target.hasAttribute('data-wl-refresh')){
        previewCheckedAt=0;
        void refreshHomeUsage();
      }else if(target.hasAttribute('data-wl-compact-tab')){
        compactTab=target.dataset.wlCompactTab;
        paint();
      }else if(target.hasAttribute('data-wl-compact-provider')||
        target.hasAttribute('data-wl-compact-employee')||
        target.hasAttribute('data-wl-open-report')){
        compactPick={view:'outcomes'};
        if(typeof openDetails==='function')openDetails();
      }
    });
    container.append(root);
    paint();
    if(!previewTimer){
      previewTimer=setInterval(()=>{
        if(previewRoot&&previewRoot.isConnected!==false&&document.hidden!==true)
          void refreshHomeUsage();
      },60000);
      document.addEventListener('visibilitychange',()=>{
        if(document.hidden!==true&&previewRoot?.isConnected!==false&&
          Date.now()-previewCheckedAt>15000)void refreshHomeUsage();
      });
    }
    if(!previewSnapshot||Date.now()-previewCheckedAt>15000)void refreshHomeUsage();
  }
  function mount(container) {
    if(!container)return;
    const carriedLeft=container.querySelector?.('.wl-matrix-scroll')?.scrollLeft??0;
    container.replaceChildren();
    const root=document.createElement('div');
    root.id='rovor-workload-popup';
    const state=retainedPopup
      ? {...retainedPopup}
      : {view:'outcomes',period:'24H',demo:false,employee:0,model:0};
    if(compactPick)Object.assign(state,compactPick);
    compactPick=null;
    const paint=()=>{
      const previousLeft=root.querySelector?.('.wl-matrix-scroll')?.scrollLeft??0;
      retainedPopup={...state};
      root.innerHTML=makeUI(state);
      const nextScroll=root.querySelector?.('.wl-matrix-scroll');
      if(nextScroll)nextScroll.scrollLeft=previousLeft;
    };
    root.addEventListener('click',ev=>{
      const b=ev.target.closest('button');
      if(!b||!root.contains(b))return;
      if(b.hasAttribute('data-wl-tab'))state.view=b.dataset.wlTab;
      else if(b.hasAttribute('data-wl-period'))state.period=b.dataset.wlPeriod;
      else if(b.hasAttribute('data-wl-demo')){state.demo=!state.demo;if(state.view==='outcomes')state.view='models';}
      else if(b.hasAttribute('data-wl-employee'))state.employee=Number(b.dataset.wlEmployee);
      else if(b.hasAttribute('data-wl-model'))state.model=Number(b.dataset.wlModel);
      else if(b.hasAttribute('data-wl-cell')){
        const [r,m]=b.dataset.wlCell.split('-').map(Number);
        state.employee=r;state.model=m;
      }else return;
      paint();
    });
    container.append(root);
    paint();
    const matrix=root.querySelector?.('.wl-matrix-scroll');
    if(matrix)matrix.scrollLeft=carriedLeft;
  }
  function resetPopup(){retainedPopup=null;}
  window.ROVOR_WORKLOAD={mount,mountPreview,resetPopup,readHomeUsage};
})();