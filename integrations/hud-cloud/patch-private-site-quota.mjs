#!/usr/bin/env node
// Guarded, in-place asset refresh for the EXISTING owner-private ROVOR Site.
// This does not publish the Site, run an inference, alter the D1 schema,
// reconfigure scheduled work, or alter authentication/sharing settings.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {createHash, randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const SITE = 'appgprj_6add1e2cc8c08191839344b34d7dbf50';
const CALL = 'const siteFetch = createSitesHandler(';
const ARGUMENTS = /^("(?:\\.|[^"\\])*"), ("(?:\\.|[^"\\])*")\);/;
const SHA = /^[a-f0-9]{64}$/;
const sha = content => createHash('sha256').update(content).digest('hex');

function trustedFile(root, relative) {
  if (fs.lstatSync(root).isSymbolicLink()) throw Error('redirected_site_root');
  let current = root;
  for (const part of relative.split('/')) {
    current = path.join(current, part);
    if (fs.lstatSync(current).isSymbolicLink()) throw Error('redirected_site_file');
  }
  if (!fs.statSync(current).isFile()) throw Error('not_a_site_file');
  return current;
}

export function replaceQuotaAsset(bundle, replacement) {
  if (typeof bundle !== 'string' || typeof replacement !== 'string' ||
      bundle.split(CALL).length !== 2) throw Error('unsupported_site_bundle');
  const start = bundle.indexOf(CALL) + CALL.length;
  const match = ARGUMENTS.exec(bundle.slice(start));
  if (!match) throw Error('unsupported_quota_bundle_shape');
  const hud = JSON.parse(match[1]);
  const previous = JSON.parse(match[2]);
  if (typeof hud !== 'string' || !hud.includes('ROVOR_START_OMNIROUTE') ||
      !hud.includes('</body>') || typeof previous !== 'string' ||
      !previous.includes('ROVOR_QUOTA_BOARD')) throw Error('unexpected_hud_or_quota_asset');
  if (!replacement.includes('window.ROVOR_QUOTA_BOARD=') ||
      !replacement.includes('rvq-overview') ||
      !replacement.includes('rvq-ring') ||
      !replacement.includes('/api/ghost/status')) throw Error('unreviewed_replacement_asset');
  // Syntax-only validation; never execute code in the private Site compiler.
  new vm.Script(replacement, {filename: 'hud-quota.js'});
  const currentHash = sha(previous);
  const wantedHash = sha(replacement);
  const quotaAt = start + match[1].length + 2; // JSON HTML, comma, space
  const output = bundle.slice(0, quotaAt) + JSON.stringify(replacement) +
    bundle.slice(quotaAt + match[2].length);
  if (output.replace(JSON.stringify(replacement), match[2]) !== bundle) {
    throw Error('unexpected_site_bundle_rewrite');
  }
  return {output, currentHash, wantedHash, unchanged: previous === replacement};
}

export function patchPrivateHudQuota(directory, {
  apply = false, expectCurrentSha256 = null, replacement = null
} = {}) {
  const root = path.resolve(directory);
  const manifest = JSON.parse(fs.readFileSync(trustedFile(root, '.openai/hosting.json'), 'utf8'));
  if (manifest.project_id !== SITE || !(manifest.d1 === 'DB' ||
      manifest.d1?.binding === 'DB')) throw Error('wrong_site_or_database');
  const source = trustedFile(root, 'worker/index.js');
  const built = trustedFile(root, 'dist/server/index.js');
  const sourceText = fs.readFileSync(source, 'utf8');
  if (sourceText !== fs.readFileSync(built, 'utf8')) throw Error('site_source_build_drift');
  const next = replacement ?? fs.readFileSync(
    new URL('../../dashboard/command-center/native-v8-9/live-quota-board.js', import.meta.url),
    'utf8');
  const patch = replaceQuotaAsset(sourceText, next);
  const result = {
    project_id: SITE,
    current_quota_sha256: patch.currentHash,
    proposed_quota_sha256: patch.wantedHash,
    changed: !patch.unchanged,
    applied: false
  };
  if (!apply || patch.unchanged) return result;
  if (typeof expectCurrentSha256 !== 'string' || !SHA.test(expectCurrentSha256) ||
      expectCurrentSha256 !== patch.currentHash) throw Error('quota_revision_not_approved');
  if (sourceText !== fs.readFileSync(source, 'utf8') ||
      sourceText !== fs.readFileSync(built, 'utf8')) throw Error('concurrent_site_edit');
  // Stage both equivalent bundles before replacing either. Roll back the first
  // file on a second rename failure, leaving the Site unpublished.
  const targets = [source, built];
  const staging = [];
  let changed = 0;
  try {
    for (const target of targets) {
      const temp = target + '.quota-' + randomUUID() + '.tmp';
      staging.push(temp);
      fs.writeFileSync(temp, patch.output, {flag: 'wx', mode: fs.statSync(target).mode});
    }
    for (let i = 0; i < targets.length; i++) {
      fs.renameSync(staging[i], targets[i]);
      changed++;
    }
    return {...result, applied: true};
  } catch (error) {
    // A failure is not a successful deployment or activation.
    for (let i = 0; i < changed; i++) {
      try { fs.writeFileSync(targets[i], sourceText); } catch {}
    }
    throw error;
  } finally {
    for (const temp of staging) {
      try { fs.rmSync(temp); } catch {}
    }
  }
}

const isCli = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isCli) {
  const args = process.argv.slice(2);
  const directory = args[0];
  const apply = args.includes('--apply');
  const idx = args.indexOf('--expect-current-sha256');
  if (!directory || args.some((arg, i) =>
    i > 0 && arg !== '--apply' && arg !== '--expect-current-sha256' && i !== idx + 1)) {
    throw Error('Usage: patch-private-site-quota.mjs EXISTING_SITE [--apply --expect-current-sha256 HASH]');
  }
  console.log(JSON.stringify(patchPrivateHudQuota(directory, {
    apply, expectCurrentSha256: idx >= 0 ? args[idx + 1] : null
  })));
}
