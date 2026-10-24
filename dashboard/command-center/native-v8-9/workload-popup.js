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
  // Slot labels are intentionally NOT invented OmniRoute model identities.
  const MODELS=Array.from({length:9},(_,i)=>'MODEL '+String(i+1).padStart(2,'0'));
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
      <div class="wl-stat"><small>AI routes expected</small><b>9 <span style="font-size:11px;font-weight:400">/ unverified</span></b></div>
      <div class="wl-stat"><small>Recorded model calls · ${state.period}</small><b>${countText(grandTotal)}</b></div>
      <div class="wl-stat"><small>Runtime source</small><b style="font-size:12px">${state.demo?'SAMPLE DATA':'NOT CONNECTED'}</b></div>
    </div>`;
    const details=`<section class="wl-card">
      <h3>SELECTED PAIR / ${role[1].toUpperCase()} × ${model}</h3>
      <div class="wl-details">
        <div><div class="wl-kicker">Ghost employee</div><p><strong>${role[1]}</strong> · ${role[2]}</p><p>${state.demo?'Illustrative workload only':'No verified worker heartbeat or active job'}</p></div>
        <div><div class="wl-kicker">OmniRoute model slot</div><p><strong>${model}</strong> · actual model ID unknown</p><p>${state.demo?fmt(chosen)+' sample calls in selected period':'No measured requests, quota, cost or capacity'}</p></div>
      </div>
    </section>`;
    const header=`<div class="wl-toolbar">
      <span class="wl-kicker">OmniRoute / named employees / routing telemetry</span>
      <div class="wl-period" aria-label="Usage period">${['1H','24H','7D'].map(periodButton).join('')}</div>
    </div>
    <div class="wl-notice" role="status">
      <strong>${state.demo?'DEMONSTRATION — SYNTHETIC NUMBERS':'NO VERIFIED LIVE MODEL TELEMETRY'}</strong> ·
      ${state.demo?'All counts and illuminated routes are fabricated for layout testing. Nothing is running from this preview.':'The model catalog, worker heartbeat and inference receipts require an authenticated Mac data bridge. Unknown is not zero usage.'}
    </div>
    <div class="wl-toolbar"><div class="wl-actions" role="group" aria-label="Workload views">
      ${viewButton('matrix','EMPLOYEE × MODEL')}
      ${viewButton('models','9 MODELS')}
      ${viewButton('routing','ROUTING')}
    </div>
    <button type="button" class="wl-button" data-wl-demo aria-pressed="${state.demo}">${state.demo?'EXIT SAMPLE MODE':'VIEW SAMPLE LAYOUT'}</button></div>`;
    let visual='';
    if(state.view==='matrix'){
      visual=`<section class="wl-card">
        <h3>EMPLOYEE × AI MODEL / REQUEST ACTIVITY</h3>
        <div class="wl-matrix-scroll" tabindex="0" role="region" aria-label="Scrollable nine-model employee usage matrix">
          <table class="wl-matrix"><thead><tr><th scope="col">EMPLOYEE</th>${MODELS.map((m,j)=>`<th scope="col"><span title="OmniRoute model ID not yet verified">M${String(j+1).padStart(2,'0')}</span></th>`).join('')}</tr></thead>
          <tbody>${EMPLOYEES.map((emp,i)=>`<tr>
          <th scope="row"><button type="button" class="wl-row-select" data-wl-employee="${i}" aria-pressed="${state.employee===i}">${emp[1]}</button></th>
          ${MODELS.map((m,j)=>{
            const n=matrix?.[i]?.[j]??null;
            const value=n===null?'—':(n===0?'0':String(n));
            const selected=state.employee===i&&state.model===j;
            const alpha=n===null?0:Math.max(.2,Math.min(.95,n/(Math.max(...(totals.filter(Number.isFinite)))||1)));
            return `<td><button class="wl-cell" type="button" data-wl-cell="${i}-${j}" data-active="${n!==null&&n>0?'yes':'no'}" aria-pressed="${selected}" style="--wl-intensity:${alpha.toFixed(2)}" aria-label="${emp[1]}, model ${j+1}, ${n===null?'unverified':n+' sample calls'}">${value}</button></td>`;
          }).join('')}</tr>`).join('')}</tbody></table>
        </div>
        <div class="wl-scrollhint">SWIPE LEFT OR RIGHT FOR ALL NINE MODELS ↔</div>
        <div class="wl-key"><span>Blue intensity: relative calls (sample mode only)</span><span>— : no verified telemetry</span></div>
      </section>`;
    }else if(state.view==='models'){
      visual=`<section class="wl-card"><h3>OMNIROUTE / ALL NINE MODEL SLOTS</h3>
        <p class="wl-empty">Request share is not remaining quota or model capacity. Model identities and usage must come from verified OmniRoute receipts.</p>
        <div class="wl-models">${MODELS.map((m,j)=>{
           const v=totals[j],share=grandTotal?100*v/grandTotal:0;
           return `<button type="button" class="wl-model-entry" data-wl-model="${j}" aria-pressed="${state.model===j}">
             <span class="wl-row"><strong>${m}</strong><small>${state.demo?share.toFixed(1)+'% of sample calls':'UNVERIFIED'}</small></span>
             <span class="wl-meter" aria-hidden="true"><i style="--wl-share:${share.toFixed(1)}%"></i></span>
             <span class="wl-row"><small>${state.demo?fmt(v)+' sample requests':'Model ID / provider unknown'}</small><small>↗ INSPECT</small></span>
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
        <text x="421" y="${y+8}" font-size="11" fill="${state.model===j?'#e6f8ff':'#9acbea'}">M${String(j+1).padStart(2,'0')}</text>`}).join('');
      visual=`<section class="wl-card"><h3>SELECTED EMPLOYEE / ROUTE TO OMNIROUTE MODELS</h3>
      <div class="wl-route-layout"><div><div class="wl-kicker" style="margin-bottom:9px">Choose employee</div>
        <div class="wl-employees">${EMPLOYEES.map((emp,i)=>`<button type="button" data-wl-employee="${i}" aria-pressed="${state.employee===i}">${emp[1]}</button>`).join('')}</div></div>
        <div><svg class="wl-route-chart" viewBox="0 0 470 315" role="img" aria-label="Conceptual routing diagram. Only sample mode shows synthetic route activity.">
          ${left}${right}<circle cx="240" cy="143" r="38" fill="#10355c" stroke="#8ad6ff" stroke-width="2"/>
          <circle cx="240" cy="143" r="31" fill="none" stroke="#4d9bd5" stroke-dasharray="3 5"/>
          <text x="240" y="139" text-anchor="middle" font-size="13" fill="#f1fbff">OMNI</text><text x="240" y="153" text-anchor="middle" font-size="10" fill="#b1d9fa">ROUTE</text></svg></div>
      </div><p class="wl-empty">Routing connections are only illuminated in sample mode. Live edges will require authenticated inference receipts—not estimates from GitHub task claims.</p>
      </section>`;
    }
    return header+summary+visual+details;
  }
  function mount(container) {
    if(!container)return;
    container.replaceChildren();
    const root=document.createElement('div');
    root.id='rovor-workload-popup';
    const state={view:'matrix',period:'24H',demo:false,employee:0,model:0};
    const paint=()=>{root.innerHTML=makeUI(state)};
    root.addEventListener('click',ev=>{
      const b=ev.target.closest('button');
      if(!b||!root.contains(b))return;
      if(b.hasAttribute('data-wl-tab'))state.view=b.dataset.wlTab;
      else if(b.hasAttribute('data-wl-period'))state.period=b.dataset.wlPeriod;
      else if(b.hasAttribute('data-wl-demo'))state.demo=!state.demo;
      else if(b.hasAttribute('data-wl-employee'))state.employee=Number(b.dataset.wlEmployee);
      else if(b.hasAttribute('data-wl-model'))state.model=Number(b.dataset.wlModel);
      else if(b.hasAttribute('data-wl-cell')){
        const [r,m]=b.dataset.wlCell.split('-').map(Number);
        state.employee=r;state.model=m;
      }else return;
      // Keep the matrix's horizontal position and keyboard focus when a cell is
      // selected; re-rendering should not bounce mobile users back to model 01.
      const priorLeft=root.querySelector?.('.wl-matrix-scroll')?.scrollLeft ?? 0;
      const focusKey=Object.keys(b.dataset).find(key=>key.startsWith('wl'));
      const focusValue=focusKey?b.dataset[focusKey]:null;
      paint();
      const scroll=root.querySelector?.('.wl-matrix-scroll');
      if(scroll)scroll.scrollLeft=priorLeft;
      if(focusKey && root.querySelectorAll){
        const next=Array.from(root.querySelectorAll('button')).find(x=>x.dataset[focusKey]===focusValue);
        if(next?.focus)next.focus({preventScroll:true});
      }
    });
    container.append(root);
    paint();
  }
  window.ROVOR_WORKLOAD={mount};
})();