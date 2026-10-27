#!/usr/bin/env node
// Opt-in source composer for the EXISTING private HUD Site. Does not deploy,
// register a cron, move credentials, enable STOP, or touch the original HUD repo.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const SITE_ID = 'appgprj_6add1e2cc8c08191839344b34d7dbf50';
const END = 'export default {fetch: siteFetch};';
const IMPORT = "import {PROVIDERS,eligibility,tick,validateJob} from './runtime.mjs';";
const HASH = value => createHash('sha256').update(value).digest('hex');
const ownDir = path.dirname(fileURLToPath(import.meta.url));

export function bundleGhostSite(site, runtime, worker) {
  if (![site,runtime,worker].every(x => typeof x === 'string')) throw Error('invalid_source');
  const marker = '// ROVOR_GHOST_SITE_MOUNT_V1:' + HASH(runtime + '\0' + worker);
  if (site.includes('ROVOR_GHOST_SITE_MOUNT_V1:')) {
    if (!site.includes(marker)) throw Error('already_composed_different_source');
    return {code: site, changed: false, marker};
  }
  if (!site.trimEnd().endsWith(END) || site.split(END).length !== 2 || !site.includes('const siteFetch = createSitesHandler(')) throw Error('unexpected_hud_bundle');
  if (!worker.startsWith(IMPORT) || worker.split(IMPORT).length !== 2 || !worker.includes('export default {') || worker.split('export default {').length !== 2) throw Error('unexpected_ghost_worker');
  if (/\bimport\s|\bexport\s+default\b/.test(runtime)) throw Error('unexpected_ghost_runtime');
  const cleanRuntime = runtime.replace(/\bexport\s+(?=(?:const|function|async function)\s)/g, '');
  if (/\bexport\s/.test(cleanRuntime)) throw Error('unexpected_ghost_runtime');
  const cleanWorker = worker.replace(IMPORT, '').replace('export default {', 'return {');
  if (/\bimport\s|\bexport\s/.test(cleanWorker)) throw Error('unexpected_ghost_worker');
  const composed = site.slice(0,site.lastIndexOf(END)) + `\n${marker}\n` +
    `const ghostCloudWorker = (() => {\n${cleanRuntime}\n${cleanWorker}\n})();\n` +
    `export default {\n` +
    `  async fetch(request, env) {\n` +
    `    const route = new URL(request.url).pathname;\n` +
    `    if (route.startsWith('/api/ghost/')) {\n` +
    `      if (route === '/api/ghost/status' && request.method === 'GET') {\n` +
    `        const identity = request.headers.get('oai-authenticated-user-id');\n` +
    `        if (identity) {\n` +
    `          if (identity.length > 200) return Response.json({error:'site_identity_invalid'}, {status:401});\n` +
    `          if (typeof env.GHOST_READER_TOKEN !== 'string' || env.GHOST_READER_TOKEN.length < 32) return Response.json({error:'reader_unavailable'}, {status:503});\n` +
    `          const headers = new Headers(request.headers);\n` +
    `          headers.set('Authorization', 'Bearer ' + env.GHOST_READER_TOKEN);\n` +
    `          return ghostCloudWorker.fetch(new Request(request, {headers}), env);\n` +
    `        }\n` +
    `      }\n` +
    `      return ghostCloudWorker.fetch(request, env);\n` +
    `    }\n` +
    `    return siteFetch(request, env);\n` +
    `  },\n` +
    `  scheduled(event, env, ctx) {\n` +
    `    // Existing Site schedules do NOT activate ghost inference by accident.\n` +
    `    if (env.GHOST_CRON_OPT_IN !== 'owner-approved-ghost-cron-v1') return;\n` +
    `    return ghostCloudWorker.scheduled(event, env, ctx);\n` +
    `  }\n` +
    `};\n`;
  return {code:composed, changed:true, marker};
}

function safeFile(root, relative) {
  const filename = path.join(root, relative);
  if (path.isAbsolute(relative) || relative.split('/').includes('..')) throw Error('invalid_path');
  let current = root;
  for (const component of relative.split('/')) {
    current = path.join(current,component);
    if (fs.existsSync(current) && fs.lstatSync(current).isSymbolicLink()) throw Error('symlink_target');
  }
  return filename;
}

function migrationPlan(dir, schema) {
  if (!schema.includes('CREATE TABLE IF NOT EXISTS ghost_cloud_control') || !schema.includes('CREATE TABLE IF NOT EXISTS ghost_cloud_attempts') || /\b(?:DROP|ALTER)\s+TABLE\b/i.test(schema) || /\bhud_\w+/i.test(schema)) throw Error('unexpected_ghost_schema');
  const journalFile = safeFile(dir,'drizzle/meta/_journal.json');
  const journalBefore = fs.readFileSync(journalFile,'utf8');
  const journal = JSON.parse(journalBefore);
  if (journal.version !== '7' || journal.dialect !== 'sqlite' || !Array.isArray(journal.entries) || !journal.entries.length) throw Error('invalid_journal');
  for (let i=0;i<journal.entries.length;i++) {
    const entry=journal.entries[i];
    if (entry.idx !== i || typeof entry.tag !== 'string' || !/^\d{4}_[a-z0-9_]+$/.test(entry.tag)) throw Error('invalid_journal');
    if (!fs.existsSync(safeFile(dir,`drizzle/${entry.tag}.sql`))) throw Error('missing_existing_migration');
  }
  const migration = schema.trim().replace(/;\s*(?=(?:CREATE|INSERT)\b)/g, ';\n--> statement-breakpoint\n') + '\n';
  const existing = journal.entries.find(e=>e.tag.endsWith('_ghost_cloud'));
  if (existing) {
    const filename=safeFile(dir,`drizzle/${existing.tag}.sql`);
    if (fs.readFileSync(filename,'utf8') !== migration) throw Error('existing_ghost_migration_differs');
    return {journalFile, journal, journalBefore, migration, migrationFile:filename, changed:false};
  }
  const index=journal.entries.length;
  if (index>9999) throw Error('migration_index_exhausted');
  const tag=String(index).padStart(4,'0')+'_ghost_cloud';
  const migrationFile=safeFile(dir,`drizzle/${tag}.sql`);
  // SQL may already have been written when a previous apply was interrupted.
  // Resume only if every byte matches the exact expected migration.
  const migrationBefore=fs.existsSync(migrationFile) ? fs.readFileSync(migrationFile,'utf8') : null;
  if (migrationBefore!==null && migrationBefore!==migration) throw Error('migration_path_collision');
  journal.entries.push({idx:index,version:'6',when:1792886400000,tag,breakpoints:true});
  return {journalFile,journal,journalBefore,migration,migrationFile,migrationBefore,changed:true};
}

export function planSite(directory, {sourceDirectory=ownDir}={}) {
  const dir=path.resolve(directory);
  const manifest=JSON.parse(fs.readFileSync(safeFile(dir,'.openai/hosting.json'),'utf8'));
  if (manifest.project_id !== SITE_ID || manifest.static === true || manifest.d1?.binding !== 'DB') throw Error('wrong_existing_private_site');
  const workerFile=safeFile(dir,'worker/index.js'), distFile=safeFile(dir,'dist/server/index.js');
  const workerBefore=fs.readFileSync(workerFile,'utf8');
  const distBefore=fs.readFileSync(distFile,'utf8');
  const runtime=fs.readFileSync(path.join(sourceDirectory,'runtime.mjs'),'utf8');
  const ghost=fs.readFileSync(path.join(sourceDirectory,'worker.mjs'),'utf8');
  const schema=fs.readFileSync(path.join(sourceDirectory,'schema.sql'),'utf8');
  let site=workerBefore;
  if (workerBefore!==distBefore) {
    // Interrupted write: accept only the exact original/composed source pair.
    const workerNew=workerBefore.includes('ROVOR_GHOST_SITE_MOUNT_V1:');
    const distNew=distBefore.includes('ROVOR_GHOST_SITE_MOUNT_V1:');
    if (workerNew===distNew) throw Error('site_bundle_mismatch');
    const original=workerNew ? distBefore : workerBefore;
    const staged=workerNew ? workerBefore : distBefore;
    if (bundleGhostSite(original,runtime,ghost).code!==staged) throw Error('site_bundle_mismatch');
    site=original;
  }
  const bundle=bundleGhostSite(site,runtime,ghost);
  const migration=migrationPlan(dir,schema);
  if (!bundle.changed && migration.changed) throw Error('composed_without_migration');
  return {project_id:SITE_ID,workerFile,distFile,workerBefore,distBefore,
    bundle,migration,changed:bundle.changed || migration.changed};
}

function atomicWrite(file, content) {
  const temp=file+'.rovor-stage-'+process.pid;
  try {fs.writeFileSync(temp,content,{flag:'wx'});fs.renameSync(temp,file);}
  finally {if(fs.existsSync(temp))fs.unlinkSync(temp);}
}

// Resume is permitted only for exact expected bytes, never divergent owner edits.
function writePlanned(file, before, desired) {
  if (fs.existsSync(file) && fs.lstatSync(file).isSymbolicLink()) throw Error('symlink_target');
  const current=fs.existsSync(file) ? fs.readFileSync(file,'utf8') : null;
  if (current===desired) return false;
  if (current!==before) throw Error('source_changed_during_apply');
  atomicWrite(file,desired);
  return true;
}

export function composeSite(directory,{sourceDirectory=ownDir,apply=false,afterWrite}={}) {
  const plan=planSite(directory,{sourceDirectory});
  if (apply && plan.changed) {
    const put=(file,before,desired,stage)=>{
      if (writePlanned(file,before,desired) && typeof afterWrite==='function') afterWrite(stage);
    };
    if (plan.migration.changed) {
      put(plan.migration.migrationFile,plan.migration.migrationBefore,plan.migration.migration,'migration_sql');
      put(plan.migration.journalFile,plan.migration.journalBefore,
        JSON.stringify(plan.migration.journal,null,2)+'\n','migration_journal');
    }
    if (plan.bundle.changed) {
      put(plan.workerFile,plan.workerBefore,plan.bundle.code,'worker');
      put(plan.distFile,plan.distBefore,plan.bundle.code,'dist_worker');
    }
  }
  return {project_id:plan.project_id,source_only:true,applied:apply && plan.changed,
    already_composed:!plan.changed,migration:path.basename(plan.migration.migrationFile),
    ghost_routes:'/api/ghost/*',cron_registered:false,provider_secrets_provisioned:false,
    deployment_performed:false};
}

if (process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  if (!process.argv[2] || process.argv.slice(2).some(x=>x!=='--apply' && x!==process.argv[2])) throw Error('Usage: node site-composition.mjs EXISTING_SITE_DIRECTORY [--apply]');
  console.log(JSON.stringify(composeSite(process.argv[2],{apply:process.argv.includes('--apply')})));
}
