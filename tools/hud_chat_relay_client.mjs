#!/usr/bin/env node
// Outbound-only bridge between the private Cloudflare HUD and installed OmniRoute.
// Never accepts inbound Mac traffic, stores provider secrets in the browser,
// creates background work on its own, or replays a failed inference.
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {createChat, CHAT_LIMITS} from './hud_chat.mjs';
import {validateTarget} from './hud_telemetry_publisher.mjs';
import {isEntrypoint} from './hud_omniroute_bridge.mjs';

const exec = promisify(execFile);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function fromKeychain(service) {
  if (process.platform !== 'darwin') return null;
  try { return (await exec('/usr/bin/security', ['find-generic-password','-s',service,'-w'],
    {timeout:5000})).stdout.trim(); } catch { return null; }
}
const explicit = /^([A-Za-z0-9][A-Za-z0-9._:/+@-]{0,199})$/;
export function eligibleModels(models, approved = []) {
  if (!Array.isArray(models)) return [];
  const allow = new Set(approved.filter(x => explicit.test(x)));
  // Explicit OpenRouter :free routes and owner-named free combos are eligible.
  // Models with unrestricted IDs require owner-verifiable zero-cost allowlisting.
  // An account or API key alone is never a free entitlement.
  return [...new Set(models.filter(id => explicit.test(id) &&
    (id.endsWith(':free') || /^rovor-[a-z0-9-]+-free-v[0-9]+$/.test(id) || allow.has(id))))].slice(0,100);
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
  let raw='',output='';
  try {
    for (;;) {
      const {done,value}=await reader.read();
      if (done) break;
      raw+=decoder.decode(value,{stream:true});
      let pos;
      while ((pos=raw.indexOf('\n'))>=0) {
        const line=raw.slice(0,pos).trim();raw=raw.slice(pos+1);
        output+=readEvents(line);
        if (output.length>16000) throw Error('response_too_large');
      }
    }
    output+=readEvents(raw);
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
export async function runRelay({origin,writerKey,chat,stop,send=fetch,interval=2500,approved=[]}) {
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
        const result=await executeClaim(chat,job,stop,available);
        // Result submission may be repeated; it never repeats the inference call.
        for (let n=0;n<2;n++) {
          try {await post('/api/hud/chat/result/'+encodeURIComponent(job.id),result);break;}
          catch {if (n===0) await sleep(1000);}
        }
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
  if (!apiKey) throw Error('omniroute_endpoint_key_missing');
  const approved=String(process.env.ROVOR_HUD_CHAT_FREE_MODELS||'').split(',').map(s=>s.trim()).filter(Boolean);
  const chat=createChat({apiKey});
  const stop=new AbortController();
  for (const sig of ['SIGINT','SIGTERM']) process.once(sig,()=>stop.abort());
  console.log('ROVOR outbound chat bridge starting; only verified free route IDs are offered.');
  await runRelay({origin,writerKey,chat,stop:stop.signal,approved});
}
if (isEntrypoint(process.argv[1],import.meta.url)) main().catch(e=>{
  console.error('Ask ROVOR bridge not started: '+String(e.message||e).replace(/Bearer\s+\S+/g,'Bearer [redacted]'));
  process.exitCode=1;
});
