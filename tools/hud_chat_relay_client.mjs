#!/usr/bin/env node
// Outbound-only bridge between the private Cloudflare HUD and installed OmniRoute.
// Never accepts inbound Mac traffic, stores provider secrets in the browser,
// creates background work on its own, or replays a failed inference.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {createChat, CHAT_LIMITS} from './hud_chat.mjs';
import {readRepoContext} from './hud_chat_repo_context.mjs';
import {validateTarget} from './hud_telemetry_publisher.mjs';
import {isEntrypoint} from './hud_omniroute_bridge.mjs';

const exec = promisify(execFile);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function fromKeychain(service) {
  if (process.platform !== 'darwin') return null;
  try { return (await exec('/usr/bin/security', ['find-generic-password','-s',service,'-w'],
    {timeout:5000})).stdout.trim(); } catch { return null; }
}
// Reuse the CLI session authentication needed by the installed local
// OmniRoute gateway. Reads only the installed package; never prints a token.
export async function localCliAuth() {
  const candidates=[process.env.OMNIROUTE_CLI,
    path.join(process.env.HOME||'', '.local/bin/omniroute'),
    ...String(process.env.PATH||'').split(path.delimiter).map(dir=>path.join(dir,'omniroute'))].filter(Boolean);
  let root=null;
  for(const candidate of candidates) {
    try {
      let dir=path.dirname(fs.realpathSync(candidate));
      for(let i=0;i<5;i++,dir=path.dirname(dir)){
        if(fs.existsSync(path.join(dir,'bin/cli/utils/cliToken.mjs'))){root=dir;break;}
      }
      if(root)break;
    }catch{}
  }
  if(!root)return null;
  try {
    const {getCliToken,CLI_TOKEN_HEADER}=await import(pathToFileURL(path.join(root,'bin/cli/utils/cliToken.mjs')).href);
    const token=await getCliToken();
    if(typeof token!=='string'||!token||typeof CLI_TOKEN_HEADER!=='string')return null;
    return {header:CLI_TOKEN_HEADER,token};
  }catch{return null;}
}
const explicit = /^([A-Za-z0-9][A-Za-z0-9._:/+@-]{0,199})$/;
export function eligibleModels(models, approved = []) {
  if (!Array.isArray(models)) return [];
  const allow = new Set(approved.filter(x => explicit.test(x)));
  // Explicit provider :free routes are eligible by identity; all other models,
  // including combo aliases, require an owner-verified zero-cost allowlist.
  // An account or API key alone is never a free entitlement.
  return [...new Set(models.filter(id => explicit.test(id) &&
    (id.endsWith(':free') || allow.has(id))))].slice(0,100);
}
export function readEvents(text) {
  const parts = text.split(/\r?\n/);
  let output='';
  for (const line of parts) {
    if (!line.startsWith('data:')) continue;
    const data = line.slice(5).trim();
    if (data === '[DONE]') continue;
    try {
      const piece=JSON.parse(data)?.choices?.[0]?.delta?.content;
      if (typeof piece==='string') output+=piece;
    } catch {}
    if (output.length > 16000) throw Error('response_too_large');
  }
  return output;
}
async function collectStream(stream) {
  const reader=stream.getReader(),decoder=new TextDecoder();
  let raw='',output='',complete=false;
  try {
    for (;;) {
      const {done,value}=await reader.read();
      if (done) break;
      raw+=decoder.decode(value,{stream:true});
      let pos;
      while ((pos=raw.indexOf('\n'))>=0) {
        const line=raw.slice(0,pos).trim();raw=raw.slice(pos+1);
        if (line==='data: [DONE]') complete=true;
        if (!complete) output+=readEvents(line);
        if (output.length>16000) throw Error('response_too_large');
      }
    }
    if (raw.trim()==='data: [DONE]') complete=true;
    else if (!complete) output+=readEvents(raw);
    // A dropped connection with partial tokens must not become a success receipt.
    if (!complete) throw Error('incomplete_stream');
    return output;
  } finally {reader.releaseLock();}
}
export async function executeClaim(chat, job, signal, allowed = null) {
  if (!job || typeof job.id!=='string' || typeof job.request!=='object' ||
      job.model!==job.request.model || (Array.isArray(allowed) && !allowed.includes(job.model)))
    return {state:'failed',error:'model_not_available'};
  let result;
  try { result=await chat.respond(JSON.stringify(job.request),signal); }
  catch { return {state:'failed',error:'chat_upstream_unavailable'}; }
  if (result.status!==200 || !result.stream) {
    return {state:'failed',error:result.json?.error==='chat_rate_limited' ? 'chat_rate_limited'
      : result.json?.error==='model_not_available' ? 'model_not_available' : 'chat_upstream_failed'};
  }
  try {
    const output=await collectStream(result.stream);
    return output.trim() ? {state:'complete',output} : {state:'failed',error:'chat_upstream_failed'};
  } catch(e) {
    return {state:'failed',error:e.message==='response_too_large'?'response_too_large':'chat_upstream_failed'};
  } finally {result.done();}
}
export async function runRelay({origin,writerKey,chat,stop,send=fetch,interval=2500,approved=[],heartbeatIntervalMs=12000}) {
  origin=validateTarget(origin);
  if (typeof writerKey!=='string'||writerKey.length<32||writerKey.length>200) throw Error('writer_key_missing');
  const post=async (resource,body) => {
    const answer=await send(origin+resource,{method:'POST',redirect:'error',
      headers:{Authorization:'Bearer '+writerKey,'Content-Type':'application/json'},
      body:JSON.stringify(body),signal:AbortSignal.timeout(12000)});
    if (!answer.ok) throw Error('private_chat_relay_unavailable');
    return answer.json();
  };
  while (!stop?.aborted) {
    try {
      const available=eligibleModels(await chat.models(),approved);
      await post('/api/hud/chat/bridge',{models:available});
      const {job}=await post('/api/hud/chat/claim',{});
      if (job) {
        // Keep the actual Mac bridge heartbeat alive while a slow free model
        // is answering. Without this the HUD incorrectly reports OFFLINE after
        // 45 seconds, even though the Mac is still executing the claimed job.
        let pulseBusy=false;
        const pulse=setInterval(async()=>{
          if(stop?.aborted || pulseBusy)return;
          pulseBusy=true;
          try{await post('/api/hud/chat/bridge',{models:available});}
          catch{/* A transient telemetry failure is not evidence that inference stopped. */}
          finally{pulseBusy=false;}
        },heartbeatIntervalMs);
        pulse.unref?.();
        try {
          // Match D1's bounded running lease. A hung provider call is aborted,
          // not retried or represented as completed background work.
          const callSignal=stop ? AbortSignal.any([stop,AbortSignal.timeout(100000)]) : AbortSignal.timeout(100000);
          const result=await executeClaim(chat,job,callSignal,available);
          // Result submission may be repeated; it never repeats the inference call.
          for(let n=0;n<2;n++){
            try{await post('/api/hud/chat/result/'+encodeURIComponent(job.id),result);break;}
            catch{if(n===0)await sleep(1000);}
          }
        } finally {clearInterval(pulse);}
      }
    } catch {
      // Never output prompt, provider endpoint, credentials or private results.
      console.error(new Date().toISOString()+' Ask ROVOR bridge offline or unavailable.');
      await sleep(5000);
    }
    if (!stop?.aborted) await sleep(interval);
  }
}
async function main() {
  const origin=validateTarget(process.env.ROVOR_HUD_ORIGIN);
  const writerKey=process.env.ROVOR_HUD_WRITER_TOKEN||await fromKeychain('rovordigital.hud.writer');
  const apiKey=process.env.OMNIROUTE_API_KEY||await fromKeychain('rovordigital.omniroute.endpoint');
  const cliAuth=await localCliAuth();
  if (!apiKey && !cliAuth) throw Error('omniroute_gateway_auth_missing');
  const approved=String(process.env.ROVOR_HUD_CHAT_FREE_MODELS||'').split(',').map(s=>s.trim()).filter(Boolean);
  const chat=createChat({apiKey,cliAuth,repositoryContext:readRepoContext});
  const stop=new AbortController();
  for (const sig of ['SIGINT','SIGTERM']) process.once(sig,()=>stop.abort());
  console.log('ROVOR outbound chat bridge starting; only verified free route IDs are offered.');
  await runRelay({origin,writerKey,chat,stop:stop.signal,approved});
}
if (isEntrypoint(process.argv[1],import.meta.url)) main().catch(e=>{
  console.error('Ask ROVOR bridge not started: '+String(e.message||e).replace(/Bearer\s+\S+/g,'Bearer [redacted]'));
  process.exitCode=1;
});
