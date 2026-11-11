import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {compileOperations} from '../integrations/ghost-cloud/compose-operations.mjs';
import {compileScheduledShift} from '../integrations/ghost-cloud/compose-scheduled-shift.mjs';
import {upgradeSiteBundle,upgradeRegisteredSite} from '../integrations/ghost-cloud/upgrade-existing-site.mjs';

const root=new URL('../integrations/ghost-cloud/',import.meta.url);
const read=name=>fs.readFileSync(new URL(name,root),'utf8');
const modules={
 runtime:read('runtime.mjs'),worker:read('worker.mjs'),
 canary:read('canary-preflight.mjs'),operations:read('site-operations.mjs'),
 shift:read('scheduled-shift.mjs'),feed:read('approved-feed.mjs')
};
const OLD_RUNTIME=modules.runtime+'\n// previous Site runtime generation\n';
const BASE="function createSitesHandler(html){return request=>Response.json({html});}\n"+
 "const siteFetch = createSitesHandler('Original private ROVOR HUD');\n"+
 'export default {fetch: siteFetch};\n';
const compile=runtime=>compileOperations(BASE,runtime,modules.worker,modules.canary,modules.operations);
const oldOperations=compile(OLD_RUNTIME);
const newOperations=compile(modules.runtime);
const oldScheduled=compileScheduledShift(oldOperations,modules.shift,modules.feed);
const newScheduled=compileScheduledShift(newOperations,modules.shift,modules.feed);
const sha=s=>createHash('sha256').update(s).digest('hex');

function checkout(t,source=oldScheduled,{scheduleMigration=true}={}) {
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'rovor-existing-site-upgrade-'));
 t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
 for(const dir of ['.openai','worker','dist/server','drizzle/meta'])
  fs.mkdirSync(path.join(directory,dir),{recursive:true});
 fs.writeFileSync(path.join(directory,'.openai/hosting.json'),
  JSON.stringify({project_id:'appgprj_6add1e2cc8c08191839344b34d7dbf50',d1:'DB'}));
 const tags=['0000_hud_telemetry','0001_cloud_operations'];
 if(scheduleMigration)tags.push('0002_cloud_scheduled_shift');
 const journal={version:'7',dialect:'sqlite',
  entries:tags.map((tag,idx)=>({idx,tag,version:'6',breakpoints:true}))};
 for(const tag of tags)fs.writeFileSync(path.join(directory,'drizzle',tag+'.sql'),
  'CREATE TABLE IF NOT EXISTS sample_'+tag.replaceAll('-','_')+' (id INTEGER);\n');
 fs.writeFileSync(path.join(directory,'drizzle/meta/_journal.json'),
  JSON.stringify(journal,null,2)+'\n');
 fs.writeFileSync(path.join(directory,'worker/index.js'),source);
 fs.writeFileSync(path.join(directory,'dist/server/index.js'),source);
 return directory;
}

test('in-place upgrade refreshes an already-composed nine-provider Site without changing original HUD',()=>{
 const result=upgradeSiteBundle(oldOperations,modules);
 assert.equal(result.scheduled,false);
 assert.equal(result.changed,true);
 assert.equal(result.code,newOperations);
 assert(result.code.includes("Original private ROVOR HUD"));
 assert.equal(result.source_sha256,sha(oldOperations));
 assert.equal(result.next_sha256,sha(newOperations));
 const repeat=upgradeSiteBundle(result.code,modules);
 assert.equal(repeat.changed,false,'repeat compilation must be byte-identical');
});

test('in-place upgrade retains existing native scheduled shifts and immutable feeder',()=>{
 const result=upgradeSiteBundle(oldScheduled,modules);
 assert.equal(result.scheduled,true);
 assert.equal(result.code,newScheduled);
 assert(result.code.includes('if(__feed)__operations.installApprovedFeeder(__feed)'));
 assert(result.code.includes('installHostedShiftRunner'));
 assert(result.code.includes('rovor_catalog_refresh'));
});

test('unknown or tampered Site execution wrappers cannot be silently overwritten',()=>{
 const incorrect=[
  BASE,
  oldOperations.replace('const __operations = (() => {','const __operations = hacked()'),
  oldOperations.replace('ROVOR_CLOUD_OPERATIONS_V1','ROVOR_CLOUD_OPERATIONS_FAKE'),
  oldOperations+'\n// ROVOR_CLOUD_OPERATIONS_V1 '+'b'.repeat(64),
  oldScheduled.replace('scheduled(_event,env,ctx){','scheduled(notApproved,env,ctx){'),
  oldScheduled.replace('if(__operations.installHostedShiftRunner){','if(true){')
 ];
 for(const bad of incorrect)
  assert.throws(()=>upgradeSiteBundle(bad,modules),
   'unrecognized wrapper must be rejected, not replaced');
});

test('on-disk Site upgrade requires pin and preserves all migration journal bytes',t=>{
 const dir=checkout(t);
 const currentJournal=fs.readFileSync(path.join(dir,'drizzle/meta/_journal.json'),'utf8');
 const dry=upgradeRegisteredSite(dir);
 assert.equal(dry.prepared,false);
 assert.equal(dry.source_changed,true);
 assert.equal(dry.deployed,false);
 assert.equal(dry.migrations_created,0);
 assert.equal(fs.readFileSync(path.join(dir,'worker/index.js'),'utf8'),oldScheduled);
 assert.throws(()=>upgradeRegisteredSite(dir,{apply:true}),/pinned_source_digest_required/);
 assert.throws(()=>upgradeRegisteredSite(dir,{apply:true,expectedSourceSha256:'0'.repeat(64)}),
  /existing_site_source_changed/);
 const applied=upgradeRegisteredSite(dir,{apply:true,expectedSourceSha256:sha(oldScheduled)});
 assert.equal(applied.prepared,true);
 assert.equal(applied.scheduled_shift_preserved,true);
 assert.equal(applied.provider_activation_performed,false);
 assert.equal(applied.deployed,false);
 assert.equal(applied.site_publish_required,true);
 assert.equal(fs.readFileSync(path.join(dir,'worker/index.js'),'utf8'),newScheduled);
 assert.equal(fs.readFileSync(path.join(dir,'dist/server/index.js'),'utf8'),newScheduled);
 assert.equal(fs.readFileSync(path.join(dir,'drizzle/meta/_journal.json'),'utf8'),currentJournal);
 const again=upgradeRegisteredSite(dir,{apply:true,expectedSourceSha256:sha(newScheduled)});
 assert.equal(again.source_changed,false);
});

test('reject wrong registered Site, missing migration and source/dist disagreement',t=>{
 const dir=checkout(t);
 const manifest=path.join(dir,'.openai/hosting.json');
 fs.writeFileSync(manifest,JSON.stringify({project_id:'not-owner-site',d1:'DB'}));
 assert.throws(()=>upgradeRegisteredSite(dir),/wrong_site_or_database/);
 fs.writeFileSync(manifest,JSON.stringify({
  project_id:'appgprj_6add1e2cc8c08191839344b34d7dbf50',d1:'DB'}));
 fs.writeFileSync(path.join(dir,'dist/server/index.js'),'not reviewed');
 assert.throws(()=>upgradeRegisteredSite(dir),/site_bundle_mismatch/);
 fs.writeFileSync(path.join(dir,'dist/server/index.js'),oldScheduled);
 fs.unlinkSync(path.join(dir,'drizzle/0002_cloud_scheduled_shift.sql'));
 assert.throws(()=>upgradeRegisteredSite(dir),/existing_site_migration_journal_invalid/);
});

test('reject scheduled bundle without its journaled migration and symlink redirection',t=>{
 const dir=checkout(t,oldScheduled,{scheduleMigration:false});
 assert.throws(()=>upgradeRegisteredSite(dir),/scheduled_shift_migration_not_journaled/);
 const other=checkout(t,oldOperations);
 const outside=fs.mkdtempSync(path.join(os.tmpdir(),'rovor-site-target-'));
 t.after(()=>fs.rmSync(outside,{recursive:true,force:true}));
 fs.unlinkSync(path.join(other,'worker/index.js'));
 fs.symlinkSync(path.join(outside,'replaced.js'),path.join(other,'worker/index.js'));
 assert.throws(()=>upgradeRegisteredSite(other),/redirected_site/);
 assert.deepEqual(fs.readdirSync(outside),[]);
});
