/* ROVOR Workload — cloud-first preview and shell.
 * Read-only. Live evidence is supplied by the private same-origin quota board.
 * No synthetic usage, local bridge pairing, device recovery or worker control.
 */
(() => {
  'use strict';
  const PROVIDERS=[
    ['gemini','Gemini'],['groq','Groq'],['cloudflare-ai','Cloudflare AI'],
    ['mistral','Mistral'],['nvidia','NVIDIA'],['openrouter','OpenRouter'],
    ['sambanova','SambaNova'],['cohere','Cohere'],['huggingface','Hugging Face']
  ];
  const EMPLOYEES=['Walter','Mike','Jane','Jesse','Gale','Gus','Saul','Hank'];
  let tab='providers',evidence=null;
  const roots=new Set();
  const escapeText=s=>String(s??'').replace(/[&<>"']/g,c=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
  function paint(root) {
    const providers=tab==='providers',names=providers?PROVIDERS:EMPLOYEES;
    const labels=names.slice(0,4).map((row,i)=>{
      const id=providers?row[0]:row.toLowerCase(),name=providers?row[1]:row;
      let signal='Not verified';
      if(providers&&id==='gemini'&&Number.isSafeInteger(evidence?.geminiModels))
        signal=evidence.geminiModels+' listed · '+(evidence.geminiVerified??0)+' verified';
      else if(providers&&id==='groq'&&evidence?.groqReady===true)
        signal='Cloud configured · receipt required';
      else if(providers&&evidence?.privateCloudFresh===true)
        signal='See cloud admission';
      const label=escapeText(name);
      return '<button type="button" class="wl-compact-row" data-cloud-row="'+i+
        '" aria-label="Open live '+label+' details"><span class="wl-compact-name">'+label+
        '</span><span class="wl-compact-status">'+escapeText(signal)+
        '</span><span class="wl-compact-value">›</span></button>';
    }).join('');
    root.innerHTML='<div class="wl-compact-tabs" role="group" aria-label="Cloud workload preview">'+
      '<button type="button" data-cloud-tab="providers" aria-pressed="'+providers+'">PROVIDERS <small>09</small></button>'+
      '<button type="button" data-cloud-tab="employees" aria-pressed="'+(!providers)+'">EMPLOYEES <small>08</small></button></div>'+
      '<div class="wl-compact-meta" role="status"><span class="wl-compact-dot"></span> '+
      (evidence?'PRIVATE CLOUD READBACK · '+(evidence.privateCloudFresh?'RECEIVED':'NOT VERIFIED'):
        'CLOUD READBACK · CHECKING')+
      '<span>NO ASSUMED ACTIVITY</span></div><div class="wl-compact-items">'+labels+'</div>'+
      '<div class="wl-compact-foot">'+(providers?'9 provider families':'8 named worker roles')+
      ' · LIVE RECEIPTS ONLY <button type="button" data-cloud-open>VIEW WORKLOAD ↗</button></div>';
  }
  function mountPreview(container,openDetails) {
    if(!container)return;
    container.replaceChildren();
    const root=document.createElement('div');root.className='wl-compact';
    roots.add(root);
    root.addEventListener('click',event=>{
      const button=event.target?.closest?.('button');
      if(!button||!root.contains(button))return;
      if(button.hasAttribute('data-cloud-tab')){
        tab=button.getAttribute('data-cloud-tab')==='employees'?'employees':'providers';
        for(const item of roots)paint(item);
      }else if(button.hasAttribute('data-cloud-row')||button.hasAttribute('data-cloud-open')){
        if(typeof openDetails==='function')openDetails();
      }
    });
    container.append(root);
    paint(root);
  }
  function mount(container) {
    if(!container)return;
    container.replaceChildren();
    const root=document.createElement('div');root.id='rovor-workload-popup';
    root.innerHTML='<section class="wl-card" data-rovor-cloud-placeholder="true">'+
      '<span class="wl-kicker">ROVOR DIGITAL / LIVE CLOUD OPERATIONS</span>'+
      '<h3>Workload Distribution</h3><p class="wl-empty" role="status">Loading authenticated cloud provider, quota, job and review evidence…</p>'+
      '<p class="wl-empty">No activity will be assumed when a source is unavailable. '+
      'The live cloud dashboard replaces this loading view once its readback finishes.</p></section>';
    container.append(root);
    window.ROVOR_QUOTA_BOARD?.startCloud?.();
  }
  function setCloudSummary(summary) {
    evidence=summary&&typeof summary==='object'?{
      geminiModels:Number.isSafeInteger(summary.geminiModels)?summary.geminiModels:null,
      geminiVerified:Number.isSafeInteger(summary.geminiVerified)?summary.geminiVerified:null,
      groqReady:summary.groqReady===true,
      privateCloudFresh:summary.privateCloudFresh===true
    }:null;
    for(const root of roots)if(root.isConnected!==false)paint(root);
  }
  function resetPopup(){tab='providers';}
  window.ROVOR_WORKLOAD={mount,mountPreview,resetPopup,setCloudSummary};
})();
