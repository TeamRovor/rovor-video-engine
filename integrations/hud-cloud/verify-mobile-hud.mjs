#!/usr/bin/env node
// Authenticated, read-only proof that phone fixes are present on the EXISTING
// private Cloudflare HUD. No tokens, model calls, jobs or changes are logged.
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';
export async function verifyMobileHud({token,send=fetch,expectedCss}={}){
 if(typeof token!=='string'||token.length<32||/[\r\n]/.test(token))
  throw Error('private_reader_missing');
 async function get(pathname,authorized){
  return send(ORIGIN+pathname,{method:'GET',redirect:'manual',
   headers:authorized?{Authorization:'Bearer '+token}:{},
   cache:'no-store',signal:AbortSignal.timeout(12000)});
 }
 const anonymous=await get('/hud-mobile.css',false);
 if(anonymous.status!==401)throw Error('anonymous_mobile_style_exposed');
 const css=await get('/hud-mobile.css',true);
 if(css.status!==200)throw Error('mobile_style_private_http_'+css.status);
 if(await css.text()!==expectedCss)throw Error('deployed_mobile_css_differs_from_source');
 const root=await get('/',true);
 if(root.status!==200)throw Error('private_mobile_root_unavailable');
 const html=await root.text();
 if(!html.includes('function applySearchFilter()')||
    !html.includes('function paintPopup(force=false)')||
    !html.includes('lastLiveInteractionAt')||
    !html.includes('<link rel="stylesheet" href="/hud-mobile.css">'))
  throw Error('deployed_mobile_hud_has_old_scroll_logic');
 return {private_auth_verified:true,css_matches_source:true,
  native_mobile_search_stable:true,native_mobile_poll_scroll_guard:true,
  model_calls:0,stop_changes:0};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 verifyMobileHud({token:process.env.ROVOR_HUD_READER_TOKEN,
  expectedCss:readFileSync(new URL('../../dashboard/command-center/native-v8-9/hud-mobile.css',import.meta.url),'utf8')})
 .then(v=>console.log(JSON.stringify(v)))
 .catch(e=>{const code=String(e?.message||'mobile_hud_unavailable');
  console.error('Mobile HUD readback failed: '+(/^[a-z0-9_]{4,100}$/.test(code)?code:'mobile_hud_unavailable'));
  process.exitCode=1;
 });
}
