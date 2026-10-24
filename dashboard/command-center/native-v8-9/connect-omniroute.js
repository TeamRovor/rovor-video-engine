/* Connect the published HUD to a narrowly authorized private Mac snapshot bridge. */
(()=>{
 const KEY='rovor-private-hud-link-v1';
 let saved=null;try{saved=JSON.parse(sessionStorage.getItem(KEY));}catch{}
 const trusted=url=>url.protocol==='https:'&&/^[a-z0-9-]+\.trycloudflare\.com$/.test(url.hostname)&&!url.username&&!url.password&&!url.port;
 function connectionForm(){
  window.ROVOR_NATIVE.open('workload');
  const host=document.getElementById('drawerBody');
  host.innerHTML='<div id="rovor-workload-popup"><section class="wl-card"><h3>CONNECT OMNIROUTE</h3><p class="wl-empty">Paste the private bridge link printed on your Mac. This connects live usage to this existing HUD address. The Mac bridge must stay running.</p><form id="omniConnectForm"><input class="tool-input" id="omniBridgeLink" type="password" autocomplete="off" aria-label="Private Mac bridge link" placeholder="Private bridge link"><button class="wl-button" type="submit">CONNECT TO THIS HUD</button><button class="wl-button" type="button" id="omniDisconnect">DISCONNECT</button></form><p class="wl-empty" id="omniConnectStatus" role="status"></p></section></div>';
  document.getElementById('omniDisconnect').onclick=()=>{sessionStorage.removeItem(KEY);location.reload()};
  document.getElementById('omniConnectForm').onsubmit=async event=>{
   event.preventDefault();const status=document.getElementById('omniConnectStatus');status.textContent='Connecting…';
   try{
    const url=new URL(document.getElementById('omniBridgeLink').value.trim());
    const code=new URLSearchParams(url.hash.slice(1)).get('pair');
    if(!trusted(url)||!/^[a-f0-9]{64}$/.test(code||''))throw Error();
    document.getElementById('omniBridgeLink').value='';
    const res=await fetch(url.origin+'/pair/external',{method:'POST',credentials:'omit',headers:{'Content-Type':'application/json'},body:JSON.stringify({code}),signal:AbortSignal.timeout(15000)});
    const data=await res.json();if(!res.ok||data.scope!=='read_hud_snapshot'||!/^[a-f0-9]{64}$/.test(data.token||''))throw Error();
    sessionStorage.setItem(KEY,JSON.stringify({origin:url.origin,token:data.token,expires:data.expires_at}));location.reload();
   }catch{status.textContent='Could not connect. Use a fresh unused link from the updated Mac bridge. Keep its Terminal running.';}
  };
 }
 const button=document.createElement('button');button.type='button';button.textContent='LINK';button.title='Connect OmniRoute';button.setAttribute('aria-label','Connect OmniRoute');button.id='connectOmniRoute';
 button.style.cssText='font:inherit;font-size:9px;color:#bfeaff;background:#081a30;border:1px solid #568fbc;padding:5px;cursor:pointer';button.onclick=connectionForm;
 document.getElementById('workloadPanel').closest('.panel').querySelector('.panel-header').append(button);
 if(saved){
  try{
   if(!trusted(new URL(saved.origin))||!/^[a-f0-9]{64}$/.test(saved.token)||Date.parse(saved.expires)<=Date.now())throw Error();
   window.ROVOR_OMNIROUTE_REQUEST=(resource,opts)=>fetch(saved.origin+resource,{...opts,credentials:'omit',headers:{Authorization:'Bearer '+saved.token}});
   window.ROVOR_START_OMNIROUTE();button.textContent='LINKED';
  }catch{sessionStorage.removeItem(KEY);}
 }
})();
