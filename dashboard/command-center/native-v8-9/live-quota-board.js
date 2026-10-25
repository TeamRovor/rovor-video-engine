/* Compact, read-only quota display for the existing Workload Distribution drawer. */
window.ROVOR_QUOTA_BOARD=(()=>{
const escapeHTML=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
const fmt=n=>typeof n==='number'&&Number.isFinite(n)?n.toLocaleString():'—';
const dateLabel=s=>s&&Number.isFinite(Date.parse(s))?new Date(s).toLocaleString([],{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):'Unknown';
function card(group,quota,models,live){
 const entries=live?quota.filter(x=>x.provider===group.provider):[];
 const unknownModels=(live?models:[]).filter(m=>m.provider===group.provider&&m.requests!==null&&!entries.some(q=>q.model_id===m.id||q.model_id===m.name)).slice(0,4);
 let rows=entries.slice(0,15).map(q=>{
   const pct=Math.min(100,Math.max(0,q.used_percent));
   return '<div class="rvq-model"><div class="rvq-line"><strong>'+escapeHTML(q.model_id)+'</strong><b>'+pct.toFixed(1)+'%</b></div><div class="rvq-track" role="progressbar" aria-label="Reported quota used" aria-valuenow="'+pct.toFixed(1)+'" aria-valuemin="0" aria-valuemax="100"><i style="width:'+pct.toFixed(1)+'%"></i></div><div class="rvq-line"><small>'+fmt(q.used)+' / '+fmt(q.total)+' '+escapeHTML(q.unit)+'</small><small>Reset: '+escapeHTML(dateLabel(q.reset_at))+'</small></div><div class="rvq-evidence">Provider cache · '+escapeHTML(dateLabel(q.fetched_at))+' · account '+fmt(q.account_slot)+'</div></div>';
 });
 for(const m of unknownModels)rows.push('<div class="rvq-model"><div class="rvq-line"><strong>'+escapeHTML(m.name)+'</strong><span class="rvq-unknown-label">LIMIT UNKNOWN</span></div><div class="rvq-track rvq-unknown" aria-label="Quota unavailable"></div><div class="rvq-line"><small>'+fmt(m.requests)+' recorded requests</small><small>Reset: Unknown</small></div></div>');
 if(!rows.length)rows=['<div class="rvq-model"><div class="rvq-line"><strong>No verified model allowance</strong><span class="rvq-unknown-label">UNKNOWN</span></div><div class="rvq-track rvq-unknown" aria-label="Quota unavailable"></div><div class="rvq-line"><small>Usage limit unavailable</small><small>Reset: Unknown</small></div></div>'];
 return '<article class="rvq-provider"><div class="rvq-top"><div><strong>'+escapeHTML(group.name||group.provider).toUpperCase()+'</strong><small>'+fmt(group.connection_count)+' connection(s) · '+fmt(group.enabled_count)+' enabled</small></div><span>'+entries.length+' reports</span></div><div class="rvq-scroll">'+rows.join('')+'</div></article>';
}
const css=`
#rovor-workload-popup .rvq-board{margin-top:8px}
#rovor-workload-popup .rvq-intro{display:flex;align-items:start;justify-content:space-between;gap:12px;flex-wrap:wrap}
#rovor-workload-popup .rvq-intro strong{font-size:11px;color:#bfefff;letter-spacing:.08em}
#rovor-workload-popup .rvq-intro p{font-size:11px;color:#91b6c9}
#rovor-workload-popup .rvq-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
#rovor-workload-popup .rvq-provider{min-width:0;border-radius:12px;border:1px solid #315b79;background:linear-gradient(140deg,#092e4b,#081726);overflow:hidden}
#rovor-workload-popup .rvq-top{display:flex;justify-content:space-between;align-items:start;gap:8px;padding:13px;background:rgba(59,144,194,.11)}
#rovor-workload-popup .rvq-top strong{display:block;color:#e3f8ff;font-size:12px;letter-spacing:.09em}
#rovor-workload-popup .rvq-top small{display:block;color:#9bbfd2;font-size:10px;margin-top:5px}
#rovor-workload-popup .rvq-top span{color:#9bdcff;font-size:10px;white-space:nowrap}
#rovor-workload-popup .rvq-scroll{max-height:246px;overflow:auto;padding:0 13px;scrollbar-width:thin}
#rovor-workload-popup .rvq-model{padding:13px 0;border-bottom:1px solid #294a60}
#rovor-workload-popup .rvq-model:last-child{border:0}
#rovor-workload-popup .rvq-line{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:0 0 8px}
#rovor-workload-popup .rvq-line strong{color:#e3f6fe;font-size:11px;overflow-wrap:anywhere;min-width:0}
#rovor-workload-popup .rvq-line b{color:#9edfff;font-size:12px;font-variant-numeric:tabular-nums}
#rovor-workload-popup .rvq-line small{font-size:10px;color:#b3ccdf}
#rovor-workload-popup .rvq-track{height:9px;border-radius:8px;background:#17344a;border:1px solid #37688a;overflow:hidden}
#rovor-workload-popup .rvq-track i{display:block;height:100%;background:linear-gradient(90deg,#287bb7,#77d6ff);border-radius:8px}
#rovor-workload-popup .rvq-unknown{background:repeating-linear-gradient(120deg,#163247 0 7px,#24455a 7px 10px)}
#rovor-workload-popup .rvq-unknown-label{font-size:9px;color:#adc1d0}
#rovor-workload-popup .rvq-evidence{color:#82a6b9;font-size:9px}
@media(max-width:740px){#rovor-workload-popup .rvq-grid{grid-template-columns:1fr}#rovor-workload-popup .rvq-scroll{max-height:200px}}
`;
function mount(){if(document.getElementById('rvq-style'))return;const s=document.createElement('style');s.id='rvq-style';s.textContent=css;document.head.append(s);}
function render(data,live){mount();const connections=Array.isArray(data?.connections)?data.connections:[];const quota=Array.isArray(data?.quota?.records)?data.quota.records:[];const models=Array.isArray(data?.models)?data.models:[];return '<section class="wl-card rvq-board"><div class="rvq-intro"><div><h3>MODEL LIMITS & RESET WINDOWS</h3><p>Actual provider-reported allowance when available · unverified limits remain unknown</p></div><strong>'+ (live?quota.length+' VERIFIED REPORTS':'NO FRESH CONNECTION')+'</strong></div><div class="rvq-grid">'+connections.map(g=>card(g,quota,models,live)).join('')+'</div><p class="wl-empty">Limits can be shared across models or accounts. Recorded requests are not remaining quota. No AI calls are made by this monitoring panel.</p></section>';}

function start(){
 let busy=false,last=null,updated=0;
 const slot=()=>[...document.querySelectorAll('#rovor-workload-popup .wl-card')].find(
   n=>!n.hidden&&n.querySelector('h3')?.textContent?.trim()==='YOUR OMNIROUTE CONNECTIONS');
 async function sync(){
   if(busy||document.hidden)return;
   const original=slot();if(!original)return;
   if(last&&Date.now()-updated<5000){original.outerHTML=render(last,true);return;}
   busy=true;
   let fresh=null;
   try{
     const response=await fetch('/api/hud/omniroute?period=24h',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(8000)});
     if(response.ok){
       const data=await response.json(),age=Date.now()-Date.parse(data.snapshot_at);
       if(data.source==='local_omniroute_read_only_bridge'&&Array.isArray(data.connections)&&Number.isFinite(age)&&age>=-5000&&age<=15000)fresh=data;
     }
   }catch{}
   finally{busy=false;}
   last=fresh;updated=Date.now();
   const target=slot();
   if(target)target.outerHTML=render(fresh,!!fresh);
 }
 const observer=new MutationObserver(()=>{if(slot())void sync();});
 observer.observe(document.body,{childList:true,subtree:true});
 void sync();
}
return {render,start};
})();
