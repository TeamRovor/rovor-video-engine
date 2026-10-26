// Additive source composer for EXISTING owner-private ROVOR Site v2.
// Requires the reviewed cloud operations bundle; never deploys or registers a new trigger.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const SITE='appgprj_6add1e2cc8c08191839344b34d7dbf50';
const OPT_IN='owner-approved-ghost-cron-v1';
const TAIL="export default {fetch:(request,env)=>__operations.fetch(request,env),scheduled(event,env,ctx){if(env.GHOST_CRON_OPT_IN==='owner-approved-ghost-cron-v1')return __cloud.worker.scheduled(event,env,ctx);}};";
const here=path.dirname(fileURLToPath(import.meta.url));
function safe(root,relative) {
  let current=root;if(fs.lstatSync(root).isSymbolicLink())throw Error('redirected_site');
  for(const part of relative.split('/')){
    current=path.join(current,part);
    if(fs.existsSync(current)&&fs.lstatSync(current).isSymbolicLink())throw Error('redirected_site');
  }
  return current;
}
function scheduleWidget() {
  const make=(tag,content)=>{const el=document.createElement(tag);el.textContent=content;return el;};
  let lastOk=null;
  async function poll(){
    if(document.hidden)return;
    const panel=document.getElementById('workloadPanel');if(!panel)return;
    let status=document.getElementById('rovor-cloud-schedule-state');
    if(!status){status=make('p','CLOUD SCHEDULE · connecting');status.id='rovor-cloud-schedule-state';status.className='wl-card';panel.prepend(status);}
    try{
      const response=await fetch('/api/ghost/shifts',{cache:'no-store',signal:AbortSignal.timeout(8000)});
      if(!response.ok)throw Error('offline');
      const report=await response.json();
      if(report?.source!=='cloud_schedule_receipts'||!Array.isArray(report.runs)||report.runs.length>20)throw Error('invalid');
      lastOk=Date.now();
      const run=report.runs[0];
      if(!run){status.textContent='CLOUD SCHEDULE · no recorded executions · model usage unknown';return;}
      if(!Number.isSafeInteger(run.started_at)||!Number.isSafeInteger(run.dispatched))throw Error('invalid');
      const recent=run.started_at<=Date.now()+60000&&Date.now()-run.started_at<=600000;
      const reasons={
        no_unattempted_jobs:'no new unattempted jobs in cloud queue',
        no_eligible_providers:'all nine provider routes ineligible',
        unattempted_jobs_not_dispatched:'unattempted jobs blocked by current admission or assignment'
      };
      const gates={
        no_matching_unattempted_job:'no compatible approved job',
        global_daily_safety_cap:'global daily safety limit reached',
        account_request_cap:'account request allowance exhausted',
        account_reserved_token_cap:'account reserved token allowance exhausted',
        account_inflight_claim:'another job is still claimed',
        account_minimum_interval:'waiting for account pacing window',
        account_retry_after:'provider Retry-After is active',
        failure_circuit_requires_review:'failure circuit requires review',
        claim_contention_or_unclassified_gate:'claim blocked; inspect private receipts'
      };
      const names=['groq','gemini','cloudflare-ai','mistral','nvidia','openrouter','sambanova','cohere','huggingface'];
      const found=names.find(p=>String(run.reason||'').startsWith('claim_'+p+'_'));
      const code=found?String(run.reason).slice(('claim_'+found+'_').length):'';
      const detail=found&&Object.hasOwn(gates,code)?found.toUpperCase()+' · '+gates[code]:null;
      const idleReason=run.status==='idle'?(detail?' · '+detail:
        Object.hasOwn(reasons,run.reason)?' · '+reasons[run.reason]:''):'';
      status.textContent='CLOUD SCHEDULE · '+(recent?'recent run':'last recorded run')+' '+new Date(run.started_at).toLocaleString()+
        ' · '+run.status+' · dispatched '+run.dispatched+idleReason+
        ' · execution records do not prove models online right now';
    }catch{
      status.textContent='CLOUD SCHEDULE OFFLINE · last confirmed check '+(lastOk?new Date(lastOk).toLocaleTimeString():'never')+' · no live model claim';
    }
  }
  poll();setInterval(poll,15000);document.addEventListener('visibilitychange',poll);
}
/** Fail-closed compiler: modifies no source except exact pre-approved default export. */
export function compileScheduledShift(v2Source,shiftSource,feedSource=null) {
  if(typeof v2Source!=='string'||typeof shiftSource!=='string'||
    !v2Source.includes('ROVOR_CLOUD_OPERATIONS_V1')||
    !v2Source.includes('const __cloud = (() =>')||
    !v2Source.includes('const __operations = (() =>')||
    v2Source.includes('ROVOR_CLOUD_SCHEDULED_SHIFT_V1')||
    v2Source.split(TAIL).length!==2||!v2Source.trimEnd().endsWith(TAIL))throw Error('unexpected_existing_site_bundle');
  if(!shiftSource.includes('export async function runScheduledShift(')||
    !shiftSource.includes('export async function readScheduledShifts('))throw Error('unexpected_shift_module');
  const moduleSource=shiftSource.replace(/^export (?=async function (?:runScheduledShift|readScheduledShifts)\b)/gm,'');
  if(/^\s*(?:import|export)\s/m.test(moduleSource))throw Error('unsupported_shift_import');
  // Embed the already-reviewed immutable-Git feed into the same self-contained
  // private Site bundle; no runtime import, new endpoint, or second scheduler.
  let feedBundle='const __feed = null;\n';
  if(feedSource!==null){
    const feedImport="import {validateJob} from './runtime.mjs';";
    const workerImport="const {default:worker}=await import('./worker.mjs');";
    if(typeof feedSource!=='string'||!feedSource.includes('\n'+feedImport+'\n')||!feedSource.includes(workerImport)||
      !feedSource.includes('export async function replenishApprovedJobs('))throw Error('unexpected_approved_feed_source');
    const body=feedSource.replace(feedImport,'const validateJob=__cloud.validateJob;')
      .replace(workerImport,'const worker=__cloud.worker;')
      .replace(/^export (?=async function (?:fetchCanonicalQueue|planApprovedJobs|replenishApprovedJobs)\b)/gm,'');
    if(/(^|\n)\s*(?:import|export)\s/.test(body)||/import\s*\(/.test(body))throw Error('unsupported_approved_feed_shape');
    feedBundle='const __feed = (() => {\n'+body+'\nreturn {replenishApprovedJobs};\n})();\n';
  }
  const tag=createHash('sha256').update(shiftSource+'\0'+(feedSource||'')).digest('hex');
  const ui='<script>('+scheduleWidget.toString()+')();</script>';
  const ending='\n// ROVOR_CLOUD_SCHEDULED_SHIFT_V1 '+tag+'\n'+
    'const __shift = (() => {\n'+moduleSource+'\nreturn {runScheduledShift,readScheduledShifts};\n})();\n'+
    feedBundle+
    'const __shiftUI = '+JSON.stringify(ui)+';\n'+
    'export default {\n'+
    "async fetch(request,env){\n"+
    " const url=new URL(request.url),route=url.pathname;\n"+
    " if(route==='/api/ghost/shifts'){\n"+
    "  const actor=request.headers.get('oai-authenticated-user-id');\n"+
    "  if(!actor||actor.length>200)return Response.json({error:'site_identity_required'},{status:401,headers:{'Cache-Control':'no-store'}});\n"+
    "  if(request.method!=='GET')return Response.json({error:'method_not_allowed'},{status:405,headers:{'Cache-Control':'no-store'}});\n"+
    "  try{return Response.json(await __shift.readScheduledShifts(env),{headers:{'Cache-Control':'no-store'}});}\n"+
    "  catch{return Response.json({error:'shift_ledger_unavailable'},{status:503,headers:{'Cache-Control':'no-store'}});}\n"+
    " }\n"+
    " const response=await __operations.fetch(request,env);\n"+
    " const actor=request.headers.get('oai-authenticated-user-id');\n"+
    " if(actor&&actor.length<=200&&request.method==='GET'&&['/','/index.html'].includes(route)&&response.ok&&\n"+
    "  (response.headers.get('Content-Type')||'').includes('text/html')){\n"+
    "   const html=await response.text();if(!html.includes('</body>'))return new Response(html,{status:response.status,headers:response.headers});\n"+
    "   const headers=new Headers(response.headers);headers.delete('Content-Length');\n"+
    "   return new Response(html.replace('</body>',__shiftUI+'</body>'),{status:response.status,headers});\n"+
    " }\n"+
    " return response;\n"+
    "},\n"+
    "scheduled(_event,env,ctx){\n"+
    ' if(env.GHOST_CRON_OPT_IN==='+JSON.stringify(OPT_IN)+')ctx.waitUntil(__shift.runScheduledShift(env,{replenish:env.GHOST_FEED_COMMIT?(__feed?__feed.replenishApprovedJobs:async()=>{throw Error("approved_feed_not_bundled")}):__operations.replenish,tick:__cloud.tick}));\n'+
    "}\n};\n";
  return v2Source.slice(0,v2Source.lastIndexOf(TAIL))+ending;
}
export function composeScheduledShift(directory,{apply=false,sourceDirectory=here}={}) {
  const root=path.resolve(directory),manifestPath=safe(root,'.openai/hosting.json');
  const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
  if(manifest.project_id!==SITE||manifest.d1!=='DB')throw Error('wrong_site_or_database');
  const worker=safe(root,'worker/index.js'),built=safe(root,'dist/server/index.js');
  const initial=fs.readFileSync(worker,'utf8');
  if(initial!==fs.readFileSync(built,'utf8'))throw Error('site_bundle_mismatch');
  const code=compileScheduledShift(initial,
    fs.readFileSync(path.join(sourceDirectory,'scheduled-shift.mjs'),'utf8'),
    fs.readFileSync(path.join(sourceDirectory,'approved-feed.mjs'),'utf8'));
  const journalPath=safe(root,'drizzle/meta/_journal.json'),journal=JSON.parse(fs.readFileSync(journalPath,'utf8'));
  if(journal.version!=='7'||journal.dialect!=='sqlite'||!Array.isArray(journal.entries)||
    journal.entries.length<2||journal.entries.length>9999||
    journal.entries.some((e,i)=>e.idx!==i||!/^\d{4}_[a-z0-9_]+$/.test(e.tag)||!fs.existsSync(safe(root,'drizzle/'+e.tag+'.sql')))||
    !journal.entries.some(e=>e.tag.endsWith('_cloud_operations'))||
    journal.entries.some(e=>e.tag.endsWith('_cloud_scheduled_shift')))throw Error('unexpected_migration_journal');
  // An existing Site may have the legacy review table without UNIQUE(attempt_id).
  // Stage the forward-only index BEFORE the scheduler migration so the
  // authenticated owner PASS/FAIL path cannot fail at SQL conflict resolution.
  // This only prepares local files; the real D1 migration needs a private
  // owner review of historical duplicate attempts before deployment.
  const hasReviewIndex=journal.entries.some(e=>
    e.tag.endsWith('_cloud_review_one_decision')||e.tag.endsWith('_owner_review_one_decision'));
  const reviewSource=fs.readFileSync(path.join(sourceDirectory,'migrations/owner-review-one-decision.sql'),'utf8');
  if(!reviewSource.includes('CREATE UNIQUE INDEX IF NOT EXISTS ghost_cloud_reviews_one_decision_per_attempt')||
     !reviewSource.includes('ON ghost_cloud_reviews(attempt_id)')||
     /(^|\n)\s*(INSERT|UPDATE|DELETE|DROP|ALTER)\b/i.test(reviewSource))throw Error('unexpected_review_schema');
  const shiftSource=fs.readFileSync(path.join(sourceDirectory,'scheduled-shift.sql'),'utf8');
  if(!shiftSource.includes('CREATE TABLE IF NOT EXISTS ghost_cloud_shift_runs')||
    /(^|\n)\s*(INSERT|UPDATE|DELETE|DROP|ALTER)\b/i.test(shiftSource))throw Error('unexpected_shift_schema');
  const nextTag=(suffix)=>String(journal.entries.length).padStart(4,'0')+'_'+suffix;
  const staged=[];
  if(!hasReviewIndex){
    const tag=nextTag('cloud_review_one_decision'),location=safe(root,'drizzle/'+tag+'.sql');
    if(fs.existsSync(location))throw Error('migration_collision');
    staged.push({tag,location,sql:reviewSource.replace(/;[ \t]*\n/g,';\n--> statement-breakpoint\n')});
    journal.entries.push({idx:journal.entries.length,version:'6',when:Date.now(),tag,breakpoints:true});
  }
  const tag=nextTag('cloud_scheduled_shift'),sqlPath=safe(root,'drizzle/'+tag+'.sql');
  if(fs.existsSync(sqlPath))throw Error('migration_collision');
  staged.push({tag,location:sqlPath,sql:shiftSource.replace(/;[ \t]*\n/g,';\n--> statement-breakpoint\n')});
  journal.entries.push({idx:journal.entries.length,version:'6',when:Date.now(),tag,breakpoints:true});
  if(apply){
    for(const m of staged)fs.writeFileSync(m.location,m.sql,{flag:'wx'});
    fs.writeFileSync(journalPath,JSON.stringify(journal,null,2)+'\n');
    fs.writeFileSync(worker,code);fs.writeFileSync(built,code);
  }
  return {project_id:SITE,prepared:apply,migration:tag+'.sql',
    review_migration:hasReviewIndex?'already_journaled':staged[0].tag+'.sql',
    migrations:staged.map(m=>m.tag+'.sql'),
    duplicate_review_preflight_required:true,
    worker_bytes:Buffer.byteLength(code),
    deployment_performed:false,cron_trigger_registered:false,models_enabled:false};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  if(!process.argv[2]||process.argv.slice(3).some(s=>s!=='--apply'))throw Error('Usage: compose-scheduled-shift.mjs EXISTING_SITE [--apply]');
  console.log(JSON.stringify(composeScheduledShift(process.argv[2],{apply:process.argv.includes('--apply')})));
}
