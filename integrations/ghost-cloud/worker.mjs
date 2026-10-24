import {PROVIDERS,eligibility,tick,validateJob} from './runtime.mjs';

const json=(value,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
async function authorized(request,env,writer) {
 const read=env.GHOST_READER_TOKEN,write=env.GHOST_WRITER_TOKEN;
 if(typeof read!=='string'||typeof write!=='string'||read.length<32||write.length<32||read===write)return false;
 const expected=writer?write:read,actual=request.headers.get('Authorization');
 if(!actual||actual.length>1024)return false;
 const hash=s=>crypto.subtle.digest('SHA-256',new TextEncoder().encode(s));
 const a=new Uint8Array(await hash(actual)),b=new Uint8Array(await hash('Bearer '+expected));
 let diff=0;for(let i=0;i<a.length;i++)diff|=a[i]^b[i];return diff===0;
}
async function body(request) {
 if(!request.headers.get('Content-Type')?.startsWith('application/json'))throw Error('invalid_body');
 const reader=request.body?.getReader();if(!reader)throw Error('invalid_body');
 const chunks=[];let size=0;
 try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>32768)throw Error('invalid_body');chunks.push(value);}}
 finally{await reader.cancel().catch(()=>{});}
 const buffer=new Uint8Array(size);let at=0;for(const chunk of chunks){buffer.set(chunk,at);at+=chunk.length;}
 return JSON.parse(new TextDecoder().decode(buffer));
}

export default {
 async scheduled(_event,env,ctx){ctx.waitUntil(tick(env));},
 async fetch(request,env){
  const url=new URL(request.url),writer=request.method==='POST';
  if(!await authorized(request,env,writer))return json({error:'unauthorized'},401);
  if(!env.DB)return json({error:'missing_database'},503);
  try{
   if(request.method==='GET'&&url.pathname==='/api/ghost/status'){
    const now=Date.now();let config;try{config=JSON.parse(env.GHOST_FLEET_CONFIG||'{}');}catch{return json({error:'invalid_fleet_config'},503);}
    const providers=Object.keys(PROVIDERS).map(provider=>({provider,configured_model:config[provider]?.model??null,admission:eligibility(provider,config[provider],env,now)??'eligible',online_verified:false}));
    const control=await env.DB.prepare('SELECT enabled FROM ghost_cloud_control WHERE id=1').first();
    const {results}=await env.DB.prepare(`SELECT a.id,a.provider,a.model requested_model,a.actual_model,a.started_at,a.finished_at,a.status,a.error_code,a.tokens_input,a.tokens_output,a.retry_after,a.human_review,j.employee,j.task_id,j.title
     FROM ghost_cloud_attempts a JOIN ghost_cloud_jobs j ON a.job_id=j.id ORDER BY a.started_at DESC LIMIT 50`).all();
    return json({schema_version:1,execution_source:'cloud_provider',observed_at:now,enabled:control?.enabled===1,providers,attempts:results});
   }
   if(request.method==='GET'&&/^\/api\/ghost\/jobs\/[a-z0-9][a-z0-9-]{0,149}$/.test(url.pathname)){
    const id=url.pathname.split('/').at(-1);
    const row=await env.DB.prepare('SELECT status,output,error_code,human_review FROM ghost_cloud_attempts WHERE job_id=?').bind(id).first();
    return row?json(row):json({error:'not_found'},404);
   }
   if(request.method==='POST'&&url.pathname==='/api/ghost/control'){
    const value=await body(request);if(Object.keys(value).length!==1||typeof value.enabled!=='boolean')throw Error('invalid_control');
    await env.DB.prepare('UPDATE ghost_cloud_control SET enabled=? WHERE id=1').bind(value.enabled?1:0).run();
    return json({enabled:value.enabled});
   }
   if(request.method==='POST'&&url.pathname==='/api/ghost/jobs'){
    const j=validateJob(await body(request));
    const existing=await env.DB.prepare('SELECT * FROM ghost_cloud_jobs WHERE id=?').bind(j.id).first();
    const fields=['employee','task_id','kind','title','prompt','source_commit'];
    if(existing){return fields.every(k=>existing[k]===j[k])?json({id:j.id,duplicate:true}):json({error:'job_id_conflict'},409);}
    const result=await env.DB.prepare(`INSERT OR IGNORE INTO ghost_cloud_jobs(id,employee,task_id,kind,title,prompt,input_bytes,source_commit,created_at) VALUES(?,?,?,?,?,?,?,?,?)`).bind(j.id,j.employee,j.task_id,j.kind,j.title,j.prompt,new TextEncoder().encode(j.prompt).length,j.source_commit,Date.now()).run();
    if(result.meta.changes!==1)return json({error:'job_id_conflict'},409);
    return json({id:j.id,queued:true},201);
   }
   return json({error:'not_found'},404);
  }catch{return json({error:'invalid_request_or_storage_failure'},400);}
 }
};
