#!/usr/bin/env node
// Opt-in exact Google Gemini route for the existing Mac Ask ROVOR relay.
// No inference, provider key export, paid fallback, or telemetry-agent edits.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {createChat} from './hud_chat.mjs';
import {localCliAuth} from './hud_chat_relay_client.mjs';

const exec=promisify(execFile);
const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';
const RELAY='com.rovor.hud-chat-relay';
const MODEL=/^(?:gemini|google|google-ai-studio)[/:](gemini-(?:3\.1-flash-lite|2\.5-flash-lite))$/i;

export function selectGeminiRoute(models){
  if(!Array.isArray(models))throw Error('model_catalog_unavailable');
  const exact=models.filter(id=>typeof id==='string'&&MODEL.test(id));
  for(const desired of ['gemini-3.1-flash-lite','gemini-2.5-flash-lite']){
    const choices=exact.filter(id=>MODEL.exec(id)[1].toLowerCase()===desired);
    if(choices.length>1)throw Error('ambiguous_gemini_direct_route');
    if(choices.length===1)return choices[0];
  }
  return null;
}
async function keychain(service){
  try{return (await exec('/usr/bin/security',['find-generic-password','-s',service,'-w'],{timeout:5000})).stdout.trim();}
  catch{return null;}
}
const PATCH=[
  "import os,plistlib,sys,tempfile",
  "target,route,origin=sys.argv[1:]",
  "if os.path.islink(target): raise SystemExit('refuse_redirected_launchagent')",
  "with open(target,'rb') as f: item=plistlib.load(f)",
  "if item.get('Label')!='com.rovor.hud-chat-relay': raise SystemExit('unexpected_launchagent')",
  "args=item.get('ProgramArguments')",
  "if not isinstance(args,list) or not any(isinstance(a,str) and a.endswith('/hud_chat_relay_client.mjs') for a in args): raise SystemExit('unexpected_chat_relay_program')",
  "env=item.get('EnvironmentVariables')",
  "if not isinstance(env,dict) or env.get('ROVOR_HUD_ORIGIN')!=origin: raise SystemExit('unexpected_private_hud_origin')",
  "current=[s.strip() for s in env.get('ROVOR_HUD_CHAT_FREE_MODELS','').split(',') if s.strip()]",
  "if route not in current:",
  "    env['ROVOR_HUD_CHAT_FREE_MODELS']=','.join(current+[route])",
  "    fd,tmp=tempfile.mkstemp(prefix='.rovor-chat-',suffix='.plist',dir=os.path.dirname(target))",
  "    try:",
  "        os.chmod(tmp,0o600)",
  "        with os.fdopen(fd,'wb') as out:",
  "            plistlib.dump(item,out)",
  "            out.flush()",
  "            os.fsync(out.fileno())",
  "        os.replace(tmp,target)",
  "    except:",
  "        try: os.unlink(tmp)",
  "        except OSError: pass",
  "        raise"
].join('\n');
export async function activate(){
  if(process.platform!=='darwin')throw Error('mac_only');
  const cliAuth=await localCliAuth();
  const apiKey=await keychain('rovordigital.omniroute.endpoint');
  if(!cliAuth&&!apiKey)throw Error('omniroute_gateway_auth_missing');
  const models=await createChat({apiKey,cliAuth,refreshCliAuth:localCliAuth}).models();
  const route=selectGeminiRoute(models);
  if(!route)throw Error('no_direct_gemini_flash_lite_route_in_omniroute_catalog');
  const plist=path.join(os.homedir(),'Library/LaunchAgents',RELAY+'.plist');
  let existing=null;
  try{existing=fs.lstatSync(plist);}catch(error){if(error.code!=='ENOENT')throw error;}
  if(existing?.isSymbolicLink())throw Error('refuse_redirected_launchagent');
  if(!existing){
    // Install only the separate chat relay after verifying a direct Google route.
    await exec('/bin/bash',[path.join(path.dirname(fileURLToPath(import.meta.url)),'install_hud_chat_relay.sh'),ORIGIN],{timeout:30000});
  }
  if(fs.lstatSync(plist).isSymbolicLink())throw Error('refuse_redirected_launchagent');
  await exec('python3',['-c',PATCH,plist,route,ORIGIN],{timeout:10000});
  // launchctl kickstart alone uses cached plist settings. Re-bootstrap the
  // same chat relay to load the owner-approved model list, not the HUD reporter.
  const domain='gui/'+process.getuid();
  try{await exec('/bin/launchctl',['bootout',domain+'/'+RELAY],{timeout:10000});}
  catch{/* The relay might be installed but not registered. */}
  await exec('/bin/launchctl',['bootstrap',domain,plist],{timeout:10000});
  await exec('/bin/launchctl',['kickstart','-k',domain+'/'+RELAY],{timeout:10000});
  console.log('Ask ROVOR Gemini route configured: '+route);
  console.log('No inference sent. Open Ask ROVOR > OmniRoute · Mac, then select this exact route.');
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  activate().catch(error=>{
    const allowed=['mac_only','omniroute_gateway_auth_missing','model_catalog_unavailable',
      'ambiguous_gemini_direct_route','no_direct_gemini_flash_lite_route_in_omniroute_catalog',
      'refuse_redirected_launchagent'];
    console.error('Gemini HUD activation unavailable: '+
      (allowed.includes(error?.message)?error.message:'setup_or_launchagent_failed')+
      '. No inference call was made.');
    process.exitCode=1;
  });
}
