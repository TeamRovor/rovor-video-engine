#!/usr/bin/env node
// Upgrade the EXISTING registered private Site's already-installed ghost-cloud
// bundle without creating a second Site or replaying applied D1 migrations.
// Source preparation only. Real Sites publish/auth/readback remains separate.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {compileOperations} from './compose-operations.mjs';
import {compileScheduledShift} from './compose-scheduled-shift.mjs';

const SITE='appgprj_6add1e2cc8c08191839344b34d7dbf50';
const BASE_EXPORT='export default {fetch: siteFetch};';
const OPS_EXPORT="export default {fetch:(request,env)=>__operations.fetch(request,env),scheduled(event,env,ctx){if(env.GHOST_CRON_OPT_IN==='owner-approved-ghost-cron-v1')return __cloud.worker.scheduled(event,env,ctx);}};";
const ROOT=path.dirname(fileURLToPath(import.meta.url));
const hex=s=>createHash('sha256').update(s).digest('hex');
const occurrences=(s,needle)=>s.split(needle).length-1;

function safe(root,relative) {
 let current=root;
 if(fs.lstatSync(root).isSymbolicLink())throw Error('redirected_site');
 for(const part of relative.split('/')){
  current=path.join(current,part);
  // existsSync follows links and returns false for a dangling link.
  // lstatSync must be used to reject even a redirected missing target.
  try{if(fs.lstatSync(current).isSymbolicLink())throw Error('redirected_site');}
  catch(error){if(error?.code!=='ENOENT')throw error;}
 }
 return current;
}

export function upgradeSiteBundle(current,parts) {
 if(typeof current!=='string'||!current.trim()||!parts||
    ['runtime','worker','canary','operations','shift','feed'].some(k=>typeof parts[k]!=='string'))
  throw Error('invalid_site_upgrade_inputs');
 const tags=[...current.matchAll(/^\/\/ ROVOR_CLOUD_OPERATIONS_V1 ([a-f0-9]{64})$/gm)];
 if(tags.length!==1||occurrences(current,'ROVOR_CLOUD_OPERATIONS_V1')!==1)
  throw Error('existing_cloud_operations_marker_missing_or_ambiguous');
 const offset=tags[0].index;
 const base=current.slice(0,offset).trimEnd()+'\n'+BASE_EXPORT+'\n';
 if(!base.includes('const siteFetch = createSitesHandler(')||
    occurrences(base,BASE_EXPORT)!==1||
    occurrences(current,'const __cloud = (() => {')!==1||
    occurrences(current,'const __operations = (() => {')!==1||
    occurrences(current,'return createCloudOperations(siteFetch,__cloud);')!==1)
  throw Error('unexpected_existing_cloud_bundle_shape');
 const scheduled=occurrences(current,'ROVOR_CLOUD_SCHEDULED_SHIFT_V1')!==0;
 const shifted=[...current.matchAll(/^\/\/ ROVOR_CLOUD_SCHEDULED_SHIFT_V1 ([a-f0-9]{64})$/gm)];
 if(scheduled){
  const checks={
   marker:shifted.length===1,
   unique:occurrences(current,'ROVOR_CLOUD_SCHEDULED_SHIFT_V1')===1,
   after_operations:shifted.length===1&&shifted[0].index>=offset,
   shift_module:occurrences(current,'const __shift = (() => {')===1,
   shift_ui:occurrences(current,'const __shiftUI = ')===1,
   hosted_runner:occurrences(current,'if(__operations.installHostedShiftRunner){')===1,
   scheduler:occurrences(current,'scheduled(_event,env,ctx){')===1,
   ending:current.trimEnd().endsWith('}\n};')
  };
  const failed=Object.entries(checks).filter(([,ok])=>!ok).map(([name])=>name);
  if(failed.length)throw Error('unexpected_existing_scheduled_bundle_shape_'+failed.join('_'));
 } else if(!current.trimEnd().endsWith(OPS_EXPORT)){
  throw Error('unexpected_existing_operations_export');
 }
 const refreshed=compileOperations(base,parts.runtime,parts.worker,parts.canary,parts.operations);
 const next=scheduled?compileScheduledShift(refreshed,parts.shift,parts.feed):refreshed;
 if(next.slice(0,next.indexOf('// ROVOR_CLOUD_OPERATIONS_V1'))!==
    current.slice(0,offset))
  throw Error('existing_site_base_would_change');
 return {code:next,scheduled,source_sha256:hex(current),next_sha256:hex(next),
  changed:current!==next};
}

export function upgradeRegisteredSite(directory,{apply=false,expectedSourceSha256=null,sourceDirectory=ROOT}={}) {
 const root=path.resolve(directory),manifestPath=safe(root,'.openai/hosting.json');
 const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
 if(manifest.project_id!==SITE||
    !(manifest.d1==='DB'||manifest.d1?.binding==='DB'))
  throw Error('wrong_site_or_database');
 const worker=safe(root,'worker/index.js');
 const dist=safe(root,'dist/server/index.js');
 const current=fs.readFileSync(worker,'utf8');
 if(current!==fs.readFileSync(dist,'utf8'))throw Error('site_bundle_mismatch');
 const journalPath=safe(root,'drizzle/meta/_journal.json');
 const journal=JSON.parse(fs.readFileSync(journalPath,'utf8'));
 if(journal.version!=='7'||journal.dialect!=='sqlite'||!Array.isArray(journal.entries)||
    !journal.entries.length||journal.entries.length>9999||
    journal.entries.some((e,i)=>e.idx!==i||!/^\d{4}_[a-z0-9_]+$/.test(e.tag)||
      !fs.existsSync(safe(root,'drizzle/'+e.tag+'.sql')))||
    !journal.entries.some(e=>e.tag.endsWith('_cloud_operations')))
  throw Error('existing_site_migration_journal_invalid');
 const scheduled=current.includes('ROVOR_CLOUD_SCHEDULED_SHIFT_V1');
 if(scheduled&&!journal.entries.some(e=>e.tag.endsWith('_cloud_scheduled_shift')))
  throw Error('scheduled_shift_migration_not_journaled');
 const read=name=>fs.readFileSync(path.join(sourceDirectory,name),'utf8');
 const result=upgradeSiteBundle(current,{
  runtime:read('runtime.mjs'),worker:read('worker.mjs'),
  canary:read('canary-preflight.mjs'),operations:read('site-operations.mjs'),
  shift:read('scheduled-shift.mjs'),feed:read('approved-feed.mjs')
 });
 if(apply){
  if(!/^[a-f0-9]{64}$/.test(expectedSourceSha256||''))
   throw Error('pinned_source_digest_required');
  if(expectedSourceSha256!==result.source_sha256)
   throw Error('existing_site_source_changed');
  if(fs.readFileSync(worker,'utf8')!==current||
     fs.readFileSync(dist,'utf8')!==current)
   throw Error('existing_site_changed_during_upgrade');
  if(result.changed){
   fs.writeFileSync(worker,result.code,'utf8');
   fs.writeFileSync(dist,result.code,'utf8');
   if(fs.readFileSync(worker,'utf8')!==result.code||
      fs.readFileSync(dist,'utf8')!==result.code)
    throw Error('upgraded_site_readback_mismatch');
  }
 }
 return {project_id:SITE,scheduled_shift_preserved:result.scheduled,
  original_sha256:result.source_sha256,next_sha256:result.next_sha256,
  source_changed:result.changed,prepared:apply,
  migrations_created:0,credentials_changed:false,stop_changed:false,
  provider_activation_performed:false,deployed:false,site_publish_required:true};
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const [directory,...args]=process.argv.slice(2);
 const apply=args.includes('--apply');
 const pinned=args.find(x=>x.startsWith('--expect-source-sha256='));
 if(!directory||args.some(x=>x!=='--apply'&&!x.startsWith('--expect-source-sha256='))||
    args.filter(x=>x.startsWith('--expect-source-sha256=')).length>1)
  throw Error('Usage: upgrade-existing-site.mjs REGISTERED_SITE_CHECKOUT [--apply --expect-source-sha256=64_HEX_DIGEST]');
 const result=upgradeRegisteredSite(directory,{
  apply,expectedSourceSha256:pinned?.split('=')[1]||null
 });
 console.log(JSON.stringify(result));
}
