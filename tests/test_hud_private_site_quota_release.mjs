import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {
  replaceQuotaAsset, patchPrivateHudQuota
} from '../integrations/hud-cloud/patch-private-site-quota.mjs';

const SITE = 'appgprj_6add1e2cc8c08191839344b34d7dbf50';
const html = '<html><body>ROVOR_START_OMNIROUTE · original private HUD</body></html>';
const oldQuota = 'window.ROVOR_QUOTA_BOARD={start(){return true;}};';
const makeBundle = (quota = oldQuota) =>
  'const siteFetch = createSitesHandler(' +
  JSON.stringify(html) + ', ' + JSON.stringify(quota) + ');\n' +
  '// Keep all owner-private cloud operations and scheduled work unchanged.\n' +
  "const __privateSTOP = 'owner-control';\n" +
  "export default {fetch:(req,env)=>__operations.fetch(req,env)," +
  "scheduled:(event,env,ctx)=>__shift.runScheduledShift(env)};\n";

function fixture(t, opts = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'rovor-site-quota-'));
  t.after(() => fs.rmSync(root, {recursive: true, force: true}));
  for (const dir of ['.openai', 'worker', 'dist/server']) {
    fs.mkdirSync(path.join(root, dir), {recursive: true});
  }
  const manifest = JSON.stringify({project_id:opts.site || SITE,d1:'DB',private:true,
    sharing:'owner_only',allow_paid_routes:false});
  const bundle = makeBundle();
  fs.writeFileSync(path.join(root, '.openai/hosting.json'), manifest);
  fs.writeFileSync(path.join(root, 'worker/index.js'), bundle);
  fs.writeFileSync(path.join(root, 'dist/server/index.js'), bundle);
  return {root, manifest, bundle, source:path.join(root,'worker/index.js'),
    built:path.join(root,'dist/server/index.js')};
}

test('private Site quota patch only changes the embedded quota script', () => {
  const current = makeBundle();
  const patch = replaceQuotaAsset(current,
    fs.readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js',import.meta.url),'utf8'));
  assert.notEqual(patch.currentHash,patch.wantedHash);
  assert.match(patch.output,/rvq-ring/);
  assert.match(patch.output,/rvq-overview/);
  assert.match(patch.output,/__privateSTOP/);
  assert.match(patch.output,/__shift\.runScheduledShift/);
  assert.match(patch.output,/ROVOR_START_OMNIROUTE/);
  const next = replaceQuotaAsset(patch.output,
    fs.readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js',import.meta.url),'utf8'));
  assert.equal(next.unchanged,true);
  assert.equal(next.output,patch.output);
});

test('preview is read-only, then exact owner-approved SHA changes both bundles',t=>{
  const f=fixture(t);
  const preview=patchPrivateHudQuota(f.root);
  assert.equal(preview.project_id,SITE);
  assert.equal(preview.changed,true);
  assert.equal(preview.applied,false);
  assert.equal(fs.readFileSync(f.source,'utf8'),f.bundle);
  assert.equal(fs.readFileSync(f.built,'utf8'),f.bundle);
  assert.throws(()=>patchPrivateHudQuota(f.root,{apply:true}),/quota_revision_not_approved/);
  assert.throws(()=>patchPrivateHudQuota(f.root,{
    apply:true,expectCurrentSha256:'a'.repeat(64)
  }),/quota_revision_not_approved/);
  assert.equal(fs.readFileSync(f.source,'utf8'),f.bundle);
  const result=patchPrivateHudQuota(f.root,{
    apply:true,expectCurrentSha256:preview.current_quota_sha256
  });
  assert.equal(result.applied,true);
  assert.equal(fs.readFileSync(f.source,'utf8'),fs.readFileSync(f.built,'utf8'));
  assert.match(fs.readFileSync(f.source,'utf8'),/rvq-overview/);
  assert.match(fs.readFileSync(f.source,'utf8'),/__privateSTOP/);
  assert.equal(fs.readFileSync(path.join(f.root,'.openai/hosting.json'),'utf8'),f.manifest);
  assert.equal(patchPrivateHudQuota(f.root).changed,false);
});

test('mismatched Site ID, source drift and redirected worker always fail without rewrite',t=>{
  const f=fixture(t,{site:'appgprj_other'});
  assert.throws(()=>patchPrivateHudQuota(f.root),/wrong_site_or_database/);
  fs.writeFileSync(path.join(f.root,'.openai/hosting.json'),JSON.stringify({project_id:SITE,d1:'DB'}));
  fs.writeFileSync(f.built,'other code');
  assert.throws(()=>patchPrivateHudQuota(f.root),/site_source_build_drift/);
  assert.equal(fs.readFileSync(f.source,'utf8'),f.bundle);
  fs.rmSync(f.built);
  fs.symlinkSync(f.source,f.built);
  assert.throws(()=>patchPrivateHudQuota(f.root),/redirected_site_file/);
  assert.equal(fs.readFileSync(f.source,'utf8'),f.bundle);
});

test('unexpected Site format, missing existing quota board and unreviewed payload fail closed',()=>{
  assert.throws(()=>replaceQuotaAsset('export default {}','window.ROVOR_QUOTA_BOARD={}'),/unsupported_site_bundle/);
  assert.throws(()=>replaceQuotaAsset(makeBundle('nothing'),'window.ROVOR_QUOTA_BOARD={}'),/unexpected_hud_or_quota_asset/);
  assert.throws(()=>replaceQuotaAsset(makeBundle(),'window.ROVOR_QUOTA_BOARD={}'),/unreviewed_replacement_asset/);
  assert.throws(()=>replaceQuotaAsset(makeBundle(),'window.ROVOR_QUOTA_BOARD=rvq-overview rvq-ring /api/ghost/status ('),
    /SyntaxError|Unexpected|unexpected/i);
});
