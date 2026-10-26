import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';
import {bundleGhostSite,composeSite,planSite} from '../integrations/ghost-cloud/site-composition.mjs';

const site="const siteFetch = createSitesHandler('<html>original HUD</html>');\nfunction createSitesHandler(html) {return () => new Response(html);}\nexport default {fetch: siteFetch};\n";
const runtime=`export const PROVIDERS = {groq:['url','GROQ_API_KEY']};\nexport function eligibility() {return null;}\nexport async function tick(env) {env.tickCount++;return {dispatched:0};}\nexport function validateJob(x) {return x;}\n`;
const ghost=`import {PROVIDERS,eligibility,tick,validateJob} from './runtime.mjs';\nexport default {async fetch(request,env) {const url=new URL(request.url);if(url.pathname==='/api/ghost/status') return Response.json({source:'ghost', auth:request.headers.get('Authorization')==='Bearer '+env.GHOST_READER_TOKEN});return new Response('ghost', {status:401});},scheduled(event,env,ctx){ctx.waitUntil(tick(env));}};\n`;
const schema=`CREATE TABLE IF NOT EXISTS ghost_cloud_control(id INTEGER PRIMARY KEY);\nCREATE TABLE IF NOT EXISTS ghost_cloud_attempts(id TEXT PRIMARY KEY);\n`;
const originalJournal={version:'7',dialect:'sqlite',entries:[{idx:0,version:'6',when:1792838400000,tag:'0000_hud_telemetry',breakpoints:true}]};
function fixture() {
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'rovor-site-compose-'));
 const src=path.join(dir,'ghost-source');fs.mkdirSync(src);
 for(const [file,body] of [['runtime.mjs',runtime],['worker.mjs',ghost],['schema.sql',schema]])fs.writeFileSync(path.join(src,file),body);
 for(const p of ['.openai','worker','dist/server','drizzle/meta'])fs.mkdirSync(path.join(dir,p),{recursive:true});
 fs.writeFileSync(path.join(dir,'.openai/hosting.json'),JSON.stringify({project_id:'appgprj_6add1e2cc8c08191839344b34d7dbf50',static:false,d1:{binding:'DB'}}));
 for(const p of ['worker/index.js','dist/server/index.js'])fs.writeFileSync(path.join(dir,p),site);
 fs.writeFileSync(path.join(dir,'drizzle/0000_hud_telemetry.sql'),'CREATE TABLE hud_latest(id INTEGER);\n');
 fs.writeFileSync(path.join(dir,'drizzle/meta/_journal.json'),JSON.stringify(originalJournal));
 return {dir,src,cleanup:()=>fs.rmSync(dir,{recursive:true,force:true})};
}

test('mount preserves original HUD and serves only namespaced ghost routes',async()=>{
 const {code,changed}=bundleGhostSite(site,runtime,ghost);assert.equal(changed,true);
 assert.ok(code.includes('original HUD'));assert.ok(code.includes('ROVOR_GHOST_SITE_MOUNT_V1'));
 const mod=await import('data:text/javascript,'+encodeURIComponent(code));
 const env={GHOST_READER_TOKEN:'r'.repeat(40),GHOST_WRITER_TOKEN:'w'.repeat(40),tickCount:0};
 const hud=await mod.default.fetch(new Request('https://private.example/'),env);
 assert.match(await hud.text(),/original HUD/);
 const denied=await mod.default.fetch(new Request('https://private.example/api/ghost/jobs/x'),env);assert.equal(denied.status,401);
 const browser=await mod.default.fetch(new Request('https://private.example/api/ghost/status',{headers:{'oai-authenticated-user-id':'verified'}}),env);
 assert.equal(browser.status,200);assert.deepEqual(await browser.json(),{source:'ghost',auth:true});
 const unauth=await mod.default.fetch(new Request('https://private.example/api/ghost/status'),env);
 assert.equal(unauth.status,200);assert.equal((await unauth.json()).auth,false); // fixture only: real ghost worker rejects this
 mod.default.scheduled({},env,{waitUntil(p){void p;}});assert.equal(env.tickCount,0);
 const enabledEnv={...env,GHOST_CRON_OPT_IN:'owner-approved-ghost-cron-v1'};
 mod.default.scheduled({}, enabledEnv, {waitUntil(p){void p;}});
 assert.equal(enabledEnv.tickCount,1);
});
test('unknown source shape, wrong source hash and extra imports fail closed',()=>{
 assert.throws(()=>bundleGhostSite('export default {};',runtime,ghost),/unexpected_hud_bundle/);
 assert.throws(()=>bundleGhostSite(site,runtime,ghost+'\nimport x from "bad";'),/unexpected_ghost_worker/);
 const first=bundleGhostSite(site,runtime,ghost);
 assert.equal(bundleGhostSite(first.code,runtime,ghost).changed,false);
 assert.throws(()=>bundleGhostSite(first.code,runtime+'//new',ghost),/different_source/);
});
test('dry-run preserves both worker copies, existing migration and journal',()=>{
 const f=fixture();try{
  const before=fs.readFileSync(path.join(f.dir,'drizzle/meta/_journal.json'),'utf8');
  const result=composeSite(f.dir,{sourceDirectory:f.src});
  assert.equal(result.applied,false);assert.equal(result.migration,'0001_ghost_cloud.sql');
  assert.equal(fs.readFileSync(path.join(f.dir,'worker/index.js'),'utf8'),site);
  assert.equal(fs.readFileSync(path.join(f.dir,'drizzle/meta/_journal.json'),'utf8'),before);
  assert.equal(fs.existsSync(path.join(f.dir,'drizzle/0001_ghost_cloud.sql')),false);
 }finally{f.cleanup();}
});
test('apply appends migration and mounts same Worker without overwriting original migration; idempotent',()=>{
 const f=fixture();try{
  const result=composeSite(f.dir,{sourceDirectory:f.src,apply:true});
  assert.equal(result.applied,true);assert.equal(result.deployment_performed,false);
  assert.equal(fs.readFileSync(path.join(f.dir,'drizzle/0000_hud_telemetry.sql'),'utf8'),'CREATE TABLE hud_latest(id INTEGER);\n');
  const journal=JSON.parse(fs.readFileSync(path.join(f.dir,'drizzle/meta/_journal.json'),'utf8'));
  assert.equal(journal.entries.length,2);assert.equal(journal.entries[1].tag,'0001_ghost_cloud');
  assert.equal(fs.readFileSync(path.join(f.dir,'worker/index.js'),'utf8'),fs.readFileSync(path.join(f.dir,'dist/server/index.js'),'utf8'));
  const again=composeSite(f.dir,{sourceDirectory:f.src,apply:true});
  assert.equal(again.already_composed,true);assert.equal(again.applied,false);
 }finally{f.cleanup();}
});
test('wrong registered Site, DB binding, mismatched copies and migration collision reject before write',()=>{
 for(const change of [
  f=>fs.writeFileSync(path.join(f.dir,'.openai/hosting.json'),JSON.stringify({project_id:'wrong',d1:{binding:'DB'}})),
  f=>fs.writeFileSync(path.join(f.dir,'.openai/hosting.json'),JSON.stringify({project_id:'appgprj_6add1e2cc8c08191839344b34d7dbf50',d1:{binding:'OTHER'}})),
  f=>fs.writeFileSync(path.join(f.dir,'dist/server/index.js'),'different'),
  f=>fs.writeFileSync(path.join(f.dir,'drizzle/0001_ghost_cloud.sql'),'collision')
 ]){const f=fixture();try{change(f);assert.throws(()=>planSite(f.dir,{sourceDirectory:f.src}));assert.equal(fs.readFileSync(path.join(f.dir,'worker/index.js'),'utf8'),site);}finally{f.cleanup();}}
});
test('schema collision and existing ghost migration changes reject',()=>{
 const f=fixture();try{
  fs.writeFileSync(path.join(f.src,'schema.sql'),schema+'DROP TABLE hud_latest;');
  assert.throws(()=>planSite(f.dir,{sourceDirectory:f.src}),/unexpected_ghost_schema/);
  fs.writeFileSync(path.join(f.src,'schema.sql'),schema);
  composeSite(f.dir,{sourceDirectory:f.src,apply:true});
  fs.writeFileSync(path.join(f.src,'schema.sql'),schema+'-- new\n');
  assert.throws(()=>planSite(f.dir,{sourceDirectory:f.src}),/existing_ghost_migration_differs/);
 }finally{f.cleanup();}
});
test('symlinked worker target refuses mutation',()=>{
 const f=fixture();try{
  fs.unlinkSync(path.join(f.dir,'worker/index.js'));
  fs.symlinkSync(path.join(f.dir,'dist/server/index.js'),path.join(f.dir,'worker/index.js'));
  assert.throws(()=>composeSite(f.dir,{sourceDirectory:f.src,apply:true}),/symlink_target/);
 }finally{f.cleanup();}
});

// Runs against the exact current source on GitHub CI; synthetic fixtures remain
// useful for local/offline tests without fetching any private Site checkout.
const repoRoot=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const hudCore=path.join(repoRoot,'integrations/hud-cloud/worker.mjs');
test('actual HUD+ghost source composes into valid executable ESM with appended real schema', {skip:!fs.existsSync(hudCore)},async()=>{
 const f=fixture();try {
  const {bundleSitesWorker}=await import('../integrations/hud-cloud/build-sites.mjs');
  const hud=bundleSitesWorker(
   fs.readFileSync(hudCore,'utf8'),
   fs.readFileSync(path.join(repoRoot,'integrations/hud-cloud/sites-adapter.mjs'),'utf8'),
   fs.readFileSync(path.join(repoRoot,'dashboard/command-center/native-v8-9/index.html'),'utf8'));
  for(const p of ['worker/index.js','dist/server/index.js'])fs.writeFileSync(path.join(f.dir,p),hud);
  const result=composeSite(f.dir,{sourceDirectory:path.join(repoRoot,'integrations/ghost-cloud'),apply:true});
  assert.equal(result.applied,true);
  const compiled=path.join(f.dir,'worker/index.js');
  const parsed=spawnSync(process.execPath,['--check',compiled],{encoding:'utf8',timeout:10000});
  assert.equal(parsed.status,0,parsed.stderr);
  const liveModule=await import(pathToFileURL(compiled).href);
  const env={GHOST_READER_TOKEN:'r'.repeat(40),GHOST_WRITER_TOKEN:'w'.repeat(40),
    GHOST_FLEET_CONFIG:'{}',DB:{prepare(){return {first:async()=>({enabled:0}),all:async()=>({results:[]})};}}};
  const denied=await liveModule.default.fetch(new Request('https://private.example/api/ghost/status'),env);
  assert.equal(denied.status,401);
  const status=await liveModule.default.fetch(new Request('https://private.example/api/ghost/status',
    {headers:{'oai-authenticated-user-id':'owner'}}),env);
  assert.equal(status.status,200);
  const doc=await status.json();
  assert.equal(doc.execution_source,'cloud_provider');
  assert.equal(doc.providers.length,9);
  assert.equal(doc.enabled,false);
  assert.equal(doc.attempts.length,0);
  const writerDenied=await liveModule.default.fetch(new Request('https://private.example/api/ghost/control',
    {method:'POST',headers:{'Content-Type':'application/json'},body:'{\"enabled\":true}'}),env);
  assert.equal(writerDenied.status,401);
  let scheduled=0;liveModule.default.scheduled({},env,{waitUntil(){scheduled++;}});
  assert.equal(scheduled,0);
  const source=fs.readFileSync(compiled,'utf8');
  assert.ok(source.includes('ROVOR_GHOST_SITE_MOUNT_V1'));
  assert.ok(source.includes('window.ROVOR_START_OMNIROUTE'));
  const migration=fs.readFileSync(path.join(f.dir,'drizzle/0001_ghost_cloud.sql'),'utf8');
  assert.match(migration,/--> statement-breakpoint/);
  assert.match(migration,/ghost_cloud_attempts/);
  assert.equal(composeSite(f.dir,{sourceDirectory:path.join(repoRoot,'integrations/ghost-cloud')}).already_composed,true);
 }finally{f.cleanup();}
});
