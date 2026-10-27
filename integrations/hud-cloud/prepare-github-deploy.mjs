#!/usr/bin/env node
// GitHub Actions is the owner of the standalone *private* HUD release.
// No ChatGPT Sites API, Mac, Codex, or provider inference required for release.
// CLI preflight is fail-closed, and never writes API tokens to source/config.
import {readFileSync, writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {verifiedOrigin} from './verify-github-deploy.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const D1_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const key = value => typeof value === 'string' && value.length >= 32 &&
  value.length <= 200 && !/[\s\x00-\x1f\x7f]/.test(value);

export function validateDeploymentSecrets(env) {
  if (typeof env.CLOUDFLARE_API_TOKEN !== 'string' || !env.CLOUDFLARE_API_TOKEN.trim() ||
      !/^[0-9a-f]{32}$/i.test(env.CLOUDFLARE_ACCOUNT_ID || ''))
    throw Error('cloudflare_deployment_credentials_missing');
  if (!key(env.ROVOR_HUD_WRITER_TOKEN) || !key(env.ROVOR_HUD_READER_TOKEN) ||
      env.ROVOR_HUD_WRITER_TOKEN === env.ROVOR_HUD_READER_TOKEN)
    throw Error('independent_hud_secrets_required');
  if (!D1_UUID.test(env.ROVOR_HUD_D1_ID || '')) throw Error('provisioned_d1_id_required');
  return true;
}

export function prepareConfig(text, databaseId) {
  const original = JSON.parse(text);
  if (original.name !== 'rovor-hud-telemetry' ||
      original.main !== 'worker.mjs' ||
      original.assets?.directory !== '../../dashboard/command-center/native-v8-9' ||
      original.assets?.binding !== 'ASSETS' || original.assets?.run_worker_first !== true ||
      original.d1_databases?.length !== 1 ||
      original.d1_databases[0].binding !== 'DB' ||
      original.d1_databases[0].database_name !== 'rovor-hud-telemetry' ||
      original.d1_databases[0].database_id !== 'REPLACE_WITH_PROVISIONED_D1_ID')
    throw Error('unreviewed_private_hud_deploy_configuration');
  if (!D1_UUID.test(databaseId || '')) throw Error('provisioned_d1_id_required');
  return {...original, d1_databases: [{...original.d1_databases[0], database_id: databaseId}]};
}

export function assertGithubReleaseContext(env) {
  if (env.GITHUB_REPOSITORY !== 'TeamRovor/rovor-video-engine' ||
      env.GITHUB_REF !== 'refs/heads/main')
    throw Error('private_hud_release_requires_trusted_main');
  return true;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    assertGithubReleaseContext(process.env);
    validateDeploymentSecrets(process.env);
    // Reject a release with no independent live URL to verify before any cloud write.
    verifiedOrigin(process.env.ROVOR_HUD_DEPLOY_ORIGIN);
    const prepared = prepareConfig(readFileSync(path.join(here, 'wrangler.jsonc'), 'utf8'),
      process.env.ROVOR_HUD_D1_ID);
    writeFileSync(path.join(here, 'wrangler.github.jsonc'), JSON.stringify(prepared, null, 2) + '\n',
      {flag: 'wx', mode: 0o600});
    console.log('ROVOR private HUD: trusted main + private DB + release credentials verified (redacted).');
  } catch (error) {
    console.error('ROVOR private HUD deploy refused: ' + error.message);
    process.exitCode = 1;
  }
}
