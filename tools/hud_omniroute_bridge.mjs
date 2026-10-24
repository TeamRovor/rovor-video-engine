#!/usr/bin/env node
/** Private read-only view of installed OmniRoute, serving the existing HUD.
 * No inference, database writes, arbitrary forwarding, or worker control.
 */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawn,spawnSync} from 'node:child_process';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const ID=/^[a-zA-Z0-9][a-zA-Z0-9._:/+@-]{0,199}$/;
const safeID=x=>typeof x==='string'&&ID.test(x)?x:null;
const count=x=>Number.isSafeInteger(x)&&x>=0?x:null;
const WINDOWS={'1h':3600000,'24h':86400000,'7d':604800000};
const same=(a,b)=>{if(typeof a!=='string'||typeof b!=='string')return false;const x=Buffer.from(a),y=Buffer.from(b);return x.length===y.length&&crypto.timingSafeEqual(x,y);};

export function normalize(catalog,analytics,{period='24h',now=Date.now(),start,end}={}){
  if(!Array.isArray(catalog?.data)||catalog.data.length>10000)throw Error('inventory_shape_unsupported');
  const models=new Map();
  for(const row of catalog.data){
    const id=safeID(row?.id);if(!id||row.owned_by==='combo')continue;
    models.set(id,{id,name:id,provider:safeID(row.owned_by),requests:null,tokens:null,request_share_percent:null,quota_used_percent:null});
  }
  if(!models.size)throw Error('inventory_empty');
  const rows=analytics?.byModel;
  const total=count(analytics?.summary?.totalRequests);
  const unique=count(analytics?.summary?.uniqueModels);
  if(!Array.isArray(rows)||rows.length>50||total===null||unique===null)throw Error('usage_shape_unsupported');
  let attributed=0;
  const grouped=new Map();
  for(const row of rows){
    const id=safeID(row?.rawModel)||safeID(row?.model);
    const provider=safeID(row?.provider),n=count(row?.requests),tokens=count(row?.totalTokens);
    if(!id||n===null||tokens===null)throw Error('usage_row_invalid');
    const key=provider+'\n'+id;
    if(grouped.has(key))throw Error('usage_row_duplicate');
    grouped.set(key,{id,provider,n,tokens});attributed+=n;
  }
  if(attributed>total)throw Error('usage_total_inconsistent');
  // /analytics returns its top 50; never turn missing rows into verified zero.
  const complete=unique<=rows.length&&attributed===total;
  const used=new Set();
  for(const {id,provider,n,tokens} of grouped.values()){
    const exact=provider?`${provider}/${id}`:id;
    let candidates=[...models.values()].filter(m=>m.id===exact);
    if(!candidates.length)candidates=[...models.values()].filter(m=>m.id===id);
    if(!candidates.length)candidates=[...models.values()].filter(m=>m.id.endsWith('/'+id)&&(!provider||m.provider===provider));
    // Ambiguous aliases are not duplicated into multiple filled bars.
    let target=candidates.length===1?candidates[0]:null;
    if(!target){const key=`usage:${provider||'unknown'}:${id}`;target={id:key,name:id,provider,inventory_member:false,requests:null,tokens:null,request_share_percent:null,quota_used_percent:null};models.set(key,target);}
    if(used.has(target.id))throw Error('usage_alias_collision');used.add(target.id);
    Object.assign(target,{requests:n,tokens,request_share_percent:total?100*n/total:0});
  }
  return {schema_version:1,source:'local_omniroute_read_only_bridge',snapshot_at:new Date(now).toISOString(),period,window_start:start,window_end:end,
    inventory_count:catalog.data.filter(r=>safeID(r?.id)&&r.owned_by!=='combo').reduce((s,r)=>s.add(r.id),new Set()).size,
    request_count:total,usage_coverage:complete?'complete_aggregate':'partial_top_50_or_unattributed',quota_state:'unknown_not_estimated',
    models:[...models.values()].sort((a,b)=>(b.requests??-1)-(a.requests??-1)||a.name.localeCompare(b.name)),
    semantics:'Completed recorded request share, not quota or active-worker load. Catalog presence is not a successful model test.'};
}

export function createCollector(read,{clock=Date.now}={}){
  const cache=new Map(),pending=new Map();let inventory=null,inventoryAt=0;
  return async period=>{
    if(!WINDOWS[period])throw Error('period_invalid');const now=clock();
    if(cache.has(period)&&now-cache.get(period).fetched<5000)return cache.get(period).value;
    if(pending.has(period))return pending.get(period);
    const task=(async()=>{
      if(!inventory||now-inventoryAt>60000){inventory=await read('/v1/models');inventoryAt=now;}
      const end=new Date(Math.floor(now/5000)*5000).toISOString(),start=new Date(Date.parse(end)-WINDOWS[period]).toISOString();
      // Explicit moving boundaries avoid OmniRoute's 60-second analytics cache.
      const usage=await read('/api/usage/analytics?range=all&startDate='+encodeURIComponent(start)+'&endDate='+encodeURIComponent(end));
      const value=normalize(inventory,usage,{period,now:clock(),start,end});cache.set(period,{fetched:clock(),value});return value;
    })();pending.set(period,task);try{return await task;}finally{pending.delete(period);}
  };
}

export function createBridge({collect,hud,adapter,pairCode=crypto.randomBytes(32).toString('hex'),port=0,clock=Date.now}){
  const sessions=new Map(),allowedHosts=new Set();let pairingOpen=true;
  const reply=(res,status,body,type='application/json',extra={})=>{res.writeHead(status,{'Content-Type':type,'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','Content-Security-Policy':"frame-ancestors 'none'; base-uri 'none'",...extra});res.end(body);};
  const denied=res=>reply(res,401,JSON.stringify({error:'pairing_required'}));
  const server=http.createServer(async(req,res)=>{
    const host=req.headers.host;if(!allowedHosts.has(host))return reply(res,403,'{}');
    if(req.headers['sec-fetch-site']==='cross-site')return reply(res,403,'{}');
    const url=new URL(req.url,'http://'+host);
    const cookie=String(req.headers.cookie||'').split(';').map(s=>s.trim()).find(s=>s.startsWith('rovor_hud='))?.slice(10);
    const authenticated=cookie&&sessions.has(cookie)&&sessions.get(cookie)>clock();
    if(url.pathname==='/pair'&&req.method==='POST'){
      const origin=req.headers.origin;
      if(!['http://'+host,'https://'+host].includes(origin))return reply(res,403,'{}');
      if(Number(req.headers['content-length']||0)>256)return reply(res,413,'{}');
      let body='';try{for await(const chunk of req){body+=chunk;if(body.length>256){reply(res,413,'{}');return;}}}catch{return;}
      let supplied;try{supplied=JSON.parse(body).code;}catch{return denied(res);}
      if(!pairingOpen||!same(supplied,pairCode))return denied(res);
      pairingOpen=false;const session=crypto.randomBytes(32).toString('hex');sessions.set(session,clock()+7*86400000);
      const secure=host.endsWith('.trycloudflare.com')?'; Secure':'';
      return reply(res,200,'{"paired":true}','application/json',{'Set-Cookie':`rovor_hud=${session}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800${secure}`});
    }
    if(req.method!=='GET')return reply(res,405,'{}',undefined,{'Allow':'GET'});
    if(url.pathname==='/'&&!authenticated){
      const login=`<!doctype html><meta name="viewport" content="width=device-width"><title>Pair ROVOR HUD</title><body style="background:#020916;color:#bde5ff;font:16px system-ui;padding:32px"><h1>ROVOR · Connect HUD</h1><p id="status">Pairing this device…</p><script>(async()=>{let code=new URLSearchParams(location.hash.slice(1)).get('pair');history.replaceState(null,'','/');if(!code){document.getElementById('status').textContent='Open the private pairing link printed on your Mac.';return}try{const r=await fetch('/pair',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code})});document.getElementById('status').textContent=r.ok?'Connected. Opening HUD…':'Pairing failed or link already used.';if(r.ok)location.reload()}catch{document.getElementById('status').textContent='Connection failed.'}})();</script>`;
      return reply(res,200,login,'text/html');
    }
    if(!authenticated)return denied(res);
    if(url.pathname==='/')return reply(res,200,hud.replace('</body>','<script src="/hud-live.js"></script></body>'),'text/html');
    if(url.pathname==='/hud-live.js')return reply(res,200,adapter,'text/javascript');
    if(url.pathname==='/api/hud/omniroute'){
      const period=url.searchParams.get('period')||'24h';if(!WINDOWS[period])return reply(res,400,'{"error":"period_invalid"}');
      try{return reply(res,200,JSON.stringify(await collect(period)));}catch{return reply(res,503,'{"error":"omniroute_unavailable_or_unauthorized"}');}
    }
    return reply(res,404,'{}');
  });
  server.requestTimeout=10000;server.headersTimeout=10000;
  return {server,pairCode,allowedHosts,async listen(){await new Promise((r,j)=>{server.once('error',j);server.listen(port,'127.0.0.1',r)});const address=server.address();allowedHosts.add('127.0.0.1:'+address.port);allowedHosts.add('localhost:'+address.port);return address.port;}};
}

async function installedReader(){
  const candidates=[process.env.OMNIROUTE_CLI,path.join(process.env.HOME||'','.local/bin/omniroute'),...String(process.env.PATH||'').split(path.delimiter).map(p=>path.join(p,'omniroute'))].filter(Boolean);
  let root;
  for(const file of candidates){try{let dir=path.dirname(fs.realpathSync(file));for(let i=0;i<5;i++,dir=path.dirname(dir)){if(fs.existsSync(path.join(dir,'bin/cli/api.mjs'))){root=dir;break;}}if(root)break;}catch{}}
  if(!root)throw Error('installed_omniroute_cli_not_found');
  const {getCliToken,CLI_TOKEN_HEADER}=await import(pathToFileURL(path.join(root,'bin/cli/utils/cliToken.mjs')).href);
  const token=await getCliToken();if(!token)throw Error('local_cli_auth_unavailable');
  let endpointKey=process.env.OMNIROUTE_API_KEY;
  if(!endpointKey&&process.platform==='darwin'){
    const p=spawnSync('/usr/bin/security',['find-generic-password','-s','rovordigital.omniroute.endpoint','-w'],{encoding:'utf8',timeout:5000});if(p.status===0)endpointKey=p.stdout.trim();
  }
  return async resource=>{
    if(resource!=='/v1/models'&&!resource.startsWith('/api/usage/analytics?'))throw Error('read_path_denied');
    const headers={'Accept':'application/json',[CLI_TOKEN_HEADER]:token};if(endpointKey)headers.Authorization='Bearer '+endpointKey;
    const r=await fetch('http://127.0.0.1:20128'+resource,{headers,redirect:'error',signal:AbortSignal.timeout(8000)});
    if(!r.ok)throw Error('gateway_read_failed');
    if(Number(r.headers.get('content-length')||0)>4*1024*1024)throw Error('gateway_response_oversized');
    let body='';for await(const chunk of r.body){body+=Buffer.from(chunk).toString('utf8');if(body.length>4*1024*1024)throw Error('gateway_response_oversized');}return JSON.parse(body);
  };
}

async function main(){
  const remote=process.argv.includes('--remote');
  const reader=await installedReader(),collect=createCollector(reader);
  const first=await collect('24h');
  const bridge=createBridge({collect,port:20129,hud:fs.readFileSync(path.join(ROOT,'dashboard/command-center/native-v8-9/index.html'),'utf8'),adapter:fs.readFileSync(path.join(ROOT,'dashboard/command-center/native-v8-9/live-omniroute.js'),'utf8')});
  const port=await bridge.listen();
  console.log(`OmniRoute connected: ${first.inventory_count} catalog model IDs; ${first.request_count} recorded requests in 24h. Quota remains unknown unless independently measured.`);
  let tunnel;
  if(remote){
    tunnel=spawn('cloudflared',['tunnel','--url','http://127.0.0.1:'+port,'--no-autoupdate'],{stdio:['ignore','ignore','pipe']});
    tunnel.on('error',()=>{console.log('cloudflared unavailable. Local link only; no software installed.');console.log(`http://127.0.0.1:${port}/#pair=${bridge.pairCode}`)});
    let printed=false,buffer='';tunnel.stderr.on('data',chunk=>{buffer=(buffer+chunk.toString()).slice(-8192);const url=buffer.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com/);if(url&&!printed){printed=true;bridge.allowedHosts.add(new URL(url[0]).host);console.log('PRIVATE PHONE PAIRING LINK (one use): '+url[0]+'/#pair='+bridge.pairCode);}});
    tunnel.on('exit',()=>{console.log('Remote tunnel stopped. Remote live sync is unavailable.');});
  }else console.log(`PRIVATE LOCAL PAIRING LINK (one use): http://127.0.0.1:${port}/#pair=${bridge.pairCode}`);
  for(const sig of ['SIGINT','SIGTERM'])process.on(sig,()=>{tunnel?.kill();bridge.server.close(()=>process.exit(0));});
}
export function isEntrypoint(argvPath=process.argv[1],moduleUrl=import.meta.url){
  try{return !!argvPath&&fs.realpathSync(argvPath)===fs.realpathSync(fileURLToPath(moduleUrl));}catch{return false;}
}
if(isEntrypoint())main().catch(()=>{console.error('HUD bridge could not connect. Check that OmniRoute is running on this Mac, local CLI authentication works, and the saved endpoint key can list models. No worker or authentication settings were changed.');process.exitCode=1;});
