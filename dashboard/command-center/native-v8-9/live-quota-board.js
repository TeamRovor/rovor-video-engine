/* ROVOR Digital: truthful per-provider quota instruments in the EXISTING HUD drawer.
 * No model calls, worker mutations, invented limits, or guessed reset times.
 */
window.ROVOR_QUOTA_BOARD=(()=>{
'use strict';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>typeof n==='number'&&Number.isFinite(n)?n.toLocaleString():'—';
const pretty=s=>{
 const key=String(s||'').toLowerCase().replace(/[^a-z0-9]/g,'');
 return ({google:'Google AI Studio',gemini:'Gemini',groq:'Groq',nvidia:'NVIDIA NIM',openrouter:'OpenRouter',mistral:'Mistral',cloudflare:'Cloudflare Workers AI',cloudflareworkersai:'Cloudflare Workers AI',sambanova:'SambaNova',cohere:'Cohere',huggingface:'Hugging Face'})[key]||String(s||'Provider').replace(/[-_]/g,' ');
};
const prettyTime=s=>{
 const t=Date.parse(s||'');if(!Number.isFinite(t))return 'Not reported';
 return new Date(t).toLocaleString([],{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});
};
const resetText=s=>{
 const t=Date.parse(s||'');if(!Number.isFinite(t))return 'Not reported';
 if(t<=Date.now())return 'Time passed · awaiting update';
 const min=Math.ceil((t-Date.now())/60000);
 return prettyTime(s)+' · '+(min>=1440?Math.floor(min/1440)+'d '+Math.ceil((min%1440)/60)+'h':min>=60?Math.floor(min/60)+'h '+min%60+'m':min+'m')+' left';
};
function meter(q){
 const pct=Math.max(0,Math.min(100,Number(q.used_percent)||0));
 const left=Math.max(0,Number(q.total)-Number(q.used));
 const caution=pct>=90?' rvq-near-limit':'';
 return '<div class="rvq-model"><div class="rvq-model-head"><div class="rvq-model-name">'+esc(q.model_id)+'</div><div class="rvq-percent">'+pct.toFixed(1)+'%<span> USED</span></div></div>'+
 '<div class="rvq-track'+caution+'" role="progressbar" aria-label="Reported quota used" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+pct.toFixed(1)+'"><i style="width:'+pct.toFixed(1)+'%"></i></div>'+
 '<div class="rvq-model-info"><div><span class="rvq-info-label">REMAINING ALLOWANCE</span><strong>'+fmt(left)+' / '+fmt(q.total)+' '+esc(q.unit)+'</strong></div><div><span class="rvq-info-label">RESET WINDOW</span><strong>'+esc(resetText(q.reset_at))+'</strong></div></div>'+
 '<div class="rvq-evidence">OMNIROUTE CACHED REPORT <span>·</span> '+esc(prettyTime(q.fetched_at))+' <span>·</span> Account '+fmt(q.account_slot)+'</div></div>';
}
function unknownModel(m){
 return '<div class="rvq-model"><div class="rvq-model-head"><div class="rvq-model-name">'+esc(m?.name||'Model allowance unavailable')+'</div><div class="rvq-unknown-tag">UNVERIFIED</div></div>'+
 '<div class="rvq-track rvq-unknown" role="img" aria-label="Provider quota unknown"></div>'+
 '<div class="rvq-model-info"><div><span class="rvq-info-label">REMAINING ALLOWANCE</span><strong>Unknown</strong></div><div><span class="rvq-info-label">RESET WINDOW</span><strong>Not reported</strong></div></div>'+
 (typeof m?.requests==='number'?'<div class="rvq-evidence">'+fmt(m.requests)+' recorded requests · not quota usage</div>':'')+'</div>';
}
function card(group,quota,models,live,index){
 const entries=live?quota.filter(q=>q.provider===group.provider):[];
 const seen=new Set(entries.flatMap(q=>[q.model_id,q.provider+'/'+q.model_id]));
 const unmatched=(live?models:[]).filter(m=>m.provider===group.provider&&m.requests!==null&&!seen.has(m.id)&&!seen.has(m.name));
 const rows=[...entries.map(meter),...unmatched.map(unknownModel)];
 if(!rows.length)rows.push(unknownModel(null));
 const first=rows.slice(0,2).join('');
 const extra=rows.length>2?'<details class="rvq-more"><summary>Show '+(rows.length-2)+' more model'+(rows.length===3?'':'s')+'</summary>'+rows.slice(2).join('')+'</details>':'';
 const status=entries.length?'LIMITS REPORTED':'QUOTA UNKNOWN';
 return '<article class="rvq-provider"><div class="rvq-provider-head"><div class="rvq-provider-icon">'+esc(pretty(group.name||group.provider).slice(0,1).toUpperCase())+'</div><div class="rvq-provider-ident"><span class="rvq-provider-index">PROVIDER '+String(index+1).padStart(2,'0')+'</span><h4>'+esc(pretty(group.name||group.provider))+'</h4><p>'+fmt(group.connection_count)+' configured connection'+(group.connection_count===1?'':'s')+'</p></div><div class="rvq-provider-status'+(entries.length?' rvq-reported':'')+'">'+status+'</div></div>'+
 '<div class="rvq-provider-content">'+first+extra+'</div></article>';
}
const css=\`
#rovor-workload-popup .rvq-board{margin:8px 0 20px!important;padding:20px!important;background:linear-gradient(160deg,rgba(4,24,47,.96),rgba(2,12,28,.96))!important;border:1px solid rgba(79,169,221,.36)!important;border-radius:15px!important;color:#e6f6ff}
#rovor-workload-popup .rvq-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;flex-wrap:wrap;margin-bottom:17px}
#rovor-workload-popup .rvq-eyebrow{color:#7bcaff;font:600 10px system-ui;letter-spacing:.18em}
#rovor-workload-popup .rvq-heading{font:600 clamp(19px,2.4vw,26px)/1.22 system-ui;margin:5px 0 6px;color:#f2fcff;letter-spacing:.01em}
#rovor-workload-popup .rvq-sub{color:#a0c3d8;font:12px/1.5 system-ui;margin:0;max-width:560px}
#rovor-workload-popup .rvq-status{flex:none;padding:8px 10px;border:1px solid rgba(105,189,236,.36);background:rgba(48,122,173,.13);border-radius:7px;color:#bcecff;font:700 10px system-ui;letter-spacing:.09em}
#rovor-workload-popup .rvq-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:0 0 18px}
#rovor-workload-popup .rvq-stat{padding:12px 13px;background:rgba(10,46,75,.65);border:1px solid rgba(93,164,206,.25);border-radius:10px;min-width:0}
#rovor-workload-popup .rvq-stat-label{display:block;color:#8fb9d1;font:700 10px system-ui;letter-spacing:.12em;margin-bottom:8px}
#rovor-workload-popup .rvq-stat-value{display:block;color:#f2fbff;font:600 19px/1.3 system-ui;overflow-wrap:anywhere}
#rovor-workload-popup .rvq-stat-value.rvq-small{font-size:13px;min-height:25px}
#rovor-workload-popup .rvq-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;align-items:start}
#rovor-workload-popup .rvq-provider{min-width:0;background:linear-gradient(145deg,rgba(13,48,77,.88),rgba(5,25,44,.95));border:1px solid rgba(90,164,204,.38);border-radius:12px;overflow:hidden;box-shadow:inset 0 1px rgba(153,219,252,.07)}
#rovor-workload-popup .rvq-provider-head{display:flex;align-items:center;gap:10px;padding:15px;border-bottom:1px solid rgba(95,175,213,.22)}
#rovor-workload-popup .rvq-provider-icon{display:grid;place-items:center;flex:none;width:36px;height:36px;border-radius:9px;border:1px solid rgba(116,205,255,.49);background:radial-gradient(circle at 30% 25%,#236b9e,#0b3154);color:#eafaff;font:700 16px system-ui}
#rovor-workload-popup .rvq-provider-ident{min-width:0;flex:1}
#rovor-workload-popup .rvq-provider-index{display:block;color:#8bb7ce;font:700 9px system-ui;letter-spacing:.13em}
#rovor-workload-popup .rvq-provider-ident h4{margin:3px 0 2px;color:#ecfaff;font:700 14px/1.32 system-ui;overflow-wrap:anywhere}
#rovor-workload-popup .rvq-provider-ident p{margin:0;color:#9ec5d8;font:11px system-ui}
#rovor-workload-popup .rvq-provider-status{border:1px solid rgba(138,167,183,.35);background:rgba(80,113,134,.12);color:#b2cbd9;border-radius:5px;padding:6px;font:700 9px system-ui;letter-spacing:.06em;white-space:nowrap;text-align:center}
#rovor-workload-popup .rvq-provider-status.rvq-reported{color:#9ce0ff;border-color:rgba(89,185,235,.5);background:rgba(54,150,204,.14)}
#rovor-workload-popup .rvq-provider-content{padding:0 15px 5px}
#rovor-workload-popup .rvq-model{padding:15px 0 13px;border-bottom:1px solid rgba(110,181,217,.16)}
#rovor-workload-popup .rvq-model:last-child{border-bottom:0}
#rovor-workload-popup .rvq-model-head{display:flex;justify-content:space-between;align-items:start;gap:10px;margin-bottom:12px}
#rovor-workload-popup .rvq-model-name{font:600 12px/1.42 system-ui;color:#d7efff;overflow-wrap:anywhere;min-width:0}
#rovor-workload-popup .rvq-percent{color:#c5efff;font:700 19px/1 system-ui;white-space:nowrap;font-variant-numeric:tabular-nums}
#rovor-workload-popup .rvq-percent span{font:700 9px system-ui;color:#91bfdb;margin-left:4px}
#rovor-workload-popup .rvq-unknown-tag{font:700 9px system-ui;color:#a6c2d2;letter-spacing:.07em;white-space:nowrap}
#rovor-workload-popup .rvq-track{display:block;height:10px;background:#102a42;border:1px solid #356888;border-radius:9px;overflow:hidden}
#rovor-workload-popup .rvq-track>i{display:block;height:100%;border-radius:9px;background:linear-gradient(90deg,#236ca6,#64ccff);box-shadow:0 0 11px rgba(90,205,255,.6)}
#rovor-workload-popup .rvq-track.rvq-near-limit>i{background:linear-gradient(90deg,#b16f37,#ffca6a)}
#rovor-workload-popup .rvq-unknown{background:repeating-linear-gradient(120deg,#142f45 0 7px,#285069 7px 10px)}
#rovor-workload-popup .rvq-model-info{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}
#rovor-workload-popup .rvq-info-label{display:block;color:#82adc9;font:700 9px system-ui;letter-spacing:.11em;margin-bottom:5px}
#rovor-workload-popup .rvq-model-info strong{display:block;color:#d9f3ff;font:600 11px/1.5 system-ui;overflow-wrap:anywhere}
#rovor-workload-popup .rvq-evidence{margin-top:12px;color:#83a8bf;font:10px/1.4 system-ui}
#rovor-workload-popup .rvq-evidence span{margin:0 2px}
#rovor-workload-popup .rvq-more{border-top:1px solid rgba(126,190,219,.2)}
#rovor-workload-popup .rvq-more summary{cursor:pointer;padding:14px 0;color:#8dd7ff;font:600 11px system-ui}
#rovor-workload-popup .rvq-more summary:focus-visible{outline:2px solid #7dccfa;outline-offset:2px}
#rovor-workload-popup .rvq-footnote{font:11px/1.6 system-ui;color:#98bfd3;margin:16px 1px 0}
@media(max-width:800px){#rovor-workload-popup .rvq-grid{grid-template-columns:1fr}#rovor-workload-popup .rvq-stats{grid-template-columns:repeat(2,minmax(0,1fr))}#rovor-workload-popup .rvq-stat:last-child{grid-column:1/-1}}
@media(max-width:500px){#rovor-workload-popup .rvq-board{padding:13px!important}#rovor-workload-popup .rvq-provider-head{padding:13px 11px;gap:8px}#rovor-workload-popup .rvq-provider-status{max-width:105px;white-space:normal}#rovor-workload-popup .rvq-provider-content{padding:0 12px 4px}#rovor-workload-popup .rvq-head{gap:10px}#rovor-workload-popup .rvq-stat{padding:10px}#rovor-workload-popup .rvq-stat-value{font-size:17px}#rovor-workload-popup .rvq-model-info{gap:7px}}
\`;
function mount(){
 if(document.getElementById('rvq-style'))return;
 const s=document.createElement('style');s.id='rvq-style';s.textContent=css;document.head.append(s);
}
function render(data,live){
 mount();
 const connections=Array.isArray(data?.connections)?data.connections:[];
 const quota=live&&Array.isArray(data?.quota?.records)?data.quota.records:[];
 const models=live&&Array.isArray(data?.models)?data.models:[];
 const resets=quota.map(q=>Date.parse(q.reset_at||'')).filter(t=>Number.isFinite(t)&&t>Date.now());
 const next=resets.length?new Date(Math.min(...resets)).toISOString():null;
 const summary='<div class="rvq-stats"><div class="rvq-stat"><span class="rvq-stat-label">CONFIGURED CONNECTIONS</span><strong class="rvq-stat-value">'+fmt(connections.reduce((a,g)=>a+(Number(g.connection_count)||0),0))+'</strong></div>'+
 '<div class="rvq-stat"><span class="rvq-stat-label">LIMIT REPORTS</span><strong class="rvq-stat-value">'+(live?quota.length:'—')+'</strong></div>'+
 '<div class="rvq-stat"><span class="rvq-stat-label">NEXT REPORTED RESET</span><strong class="rvq-stat-value rvq-small">'+esc(prettyTime(next))+'</strong></div></div>';
 return '<section class="wl-card rvq-board"><div class="rvq-head"><div><span class="rvq-eyebrow">ROVOR DIGITAL / OMNIROUTE INTELLIGENCE</span><h3 class="rvq-heading">Capacity & reset windows</h3><p class="rvq-sub">Your configured AI providers, their reported model allowances, and the next quota reset — without estimated usage.</p></div><span class="rvq-status">'+(live?'TELEMETRY CONNECTED':'DATA UNAVAILABLE')+'</span></div>'+
 summary+'<div class="rvq-grid">'+connections.map((g,i)=>card(g,quota,models,live,i)).join('')+'</div>'+
 '<p class="rvq-footnote">A connected provider is not proof that inference works. Limits are cached OmniRoute reports and may be shared by several models. Missing limits and reset times remain unknown. The separate request-share chart is not quota usage.</p></section>';
}
function start(){
 let busy=false,last=null,updated=0;
 const slot=()=>[...document.querySelectorAll('#rovor-workload-popup .wl-card')].find(
   n=>!n.hidden&&n.querySelector('h3')?.textContent?.trim()==='YOUR OMNIROUTE CONNECTIONS');
 async function sync(){
   if(busy||document.hidden)return;
   const original=slot();if(!original)return;
   if(last&&Date.now()-updated<5000){original.outerHTML=render(last,true);return;}
   busy=true;let fresh=null;
   try{
     const response=await fetch('/api/hud/omniroute?period=24h',{credentials:'same-origin',cache:'no-store',signal:AbortSignal.timeout(8000)});
     if(response.ok){
       const data=await response.json(),age=Date.now()-Date.parse(data.snapshot_at);
       if(data.source==='local_omniroute_read_only_bridge'&&Array.isArray(data.connections)&&Number.isFinite(age)&&age>=-5000&&age<=15000)fresh=data;
     }
   }catch{}finally{busy=false;}
   last=fresh;updated=Date.now();
   const target=slot();if(target)target.outerHTML=render(fresh,!!fresh);
 }
 const observer=new MutationObserver(()=>{if(slot())void sync();});
 observer.observe(document.body,{childList:true,subtree:true});void sync();
}
return {render,start};
})();
