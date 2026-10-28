#!/usr/bin/env node
// Post-deploy checks use the deployed origin, never a GitHub source claim.
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {readFileSync} from 'node:fs';
import {setTimeout as delay} from 'node:timers/promises';

export function verifiedOrigin(raw) {
  if (typeof raw !== 'string') throw Error('explicit_private_hud_origin_required');
  let url;
  try { url = new URL(raw); } catch { throw Error('invalid_private_hud_origin'); }
  if (url.protocol !== 'https:' || !url.hostname || url.username || url.password ||
      url.hash || url.search || (url.pathname !== '/' && url.pathname !== ''))
    throw Error('invalid_private_hud_origin');
  if (['localhost','127.0.0.1','0.0.0.0'].includes(url.hostname) ||
      url.hostname.endsWith('.localhost')) throw Error('public_https_origin_required');
  return url.origin;
}


export async function verifyAnonymousTelemetry(read, {attempts = 9, pause = delay, intervalMs = 3000} = {}) {
  if (!Number.isSafeInteger(attempts) || attempts < 1 || attempts > 20)
    throw Error('invalid_anonymous_verification_attempts');
  let last = 'unavailable';
  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      const result = await read('/api/hud/status', false);
      if (result.status === 401) return true;
      if (result.status === 200) throw Error('anonymous_telemetry_exposed_http_200');
      // Retry only the transient statuses expected during Workers routing.
      // 3xx and 403 fail immediately instead of claiming app-level auth.
      if (result.status !== 404 && result.status !== 429 && result.status < 500)
        throw Error('anonymous_telemetry_unexpected_http_' + result.status);
      last = 'http_' + result.status;
    } catch (error) {
      if (error.message?.startsWith('anonymous_telemetry_')) throw error;
      last = 'transport_unavailable';
    }
    if (attempt < attempts) await pause(intervalMs);
  }
  throw Error('anonymous_telemetry_not_verified_' + last);
}

// Verify the structural telemetry UI contract, not a copywriting sentence.
// Singular/plural labels, localization and explanatory wording can change
// without removing the nine connection meters or their model activity views.
export function hasNineProviderMeterAsset(js) {
  return typeof js === 'string' && [
    'window.ROVOR_QUOTA_BOARD=',
    'function overviewSlot(',
    'function usageRing(',
    'function macActivity(',
    'function modelActivity(',
    'rvq-overview-tile',
    'rvq-observed-model',
    'QUOTA UNKNOWN',
    'function render(data,live,cloud=null'
  ].every(marker => js.includes(marker));
}

export async function verifyGithubHud({origin, readerToken, send = fetch, expectedQuotaAsset = null}) {
  origin = verifiedOrigin(origin);
  if (typeof readerToken !== 'string' || readerToken.length < 32)
    throw Error('readback_credentials_missing');
  const read = (resource, authorized) => send(origin + resource, {
    method: 'GET', redirect: 'manual', cache: 'no-store',
    headers: authorized ? {Authorization: 'Bearer ' + readerToken} : {},
    signal: AbortSignal.timeout(12000)
  });

  // Cloudflare's initial route/secret rollout can briefly answer 404/5xx.
  // Never treat a 200 or redirect as private and never request any private
  // body in this probe. After retry exhaustion, report the actual HTTP code.
  await verifyAnonymousTelemetry(read);

  const anonymousScript = await read('/hud-quota.js', false);
  if (anonymousScript.status !== 401) throw Error('anonymous_quota_asset_was_not_denied');
  const anonymousRoot = await read('/', false);
  if (anonymousRoot.status !== 303 ||
      !new URL(anonymousRoot.headers.get('Location') || '/', origin).href.startsWith(origin + '/login'))
    throw Error('anonymous_private_root_not_redirected');
  const root = await read('/', true);
  if (root.status !== 200) throw Error('authenticated_original_hud_unavailable');
  const html = await root.text();
  if (!html.includes('ROVOR_START_OMNIROUTE') ||
      !html.includes('<script src="/hud-quota.js"></script>'))
    throw Error('original_hud_or_quota_bootstrap_missing');
  const script = await read('/hud-quota.js', true);
  if (script.status !== 200) throw Error('authenticated_quota_asset_unavailable');
  const js = await script.text();
  if (!hasNineProviderMeterAsset(js))
    throw Error('nine_provider_meter_asset_missing');
  if (expectedQuotaAsset !== null && js !== expectedQuotaAsset)
    throw Error('deployed_quota_asset_differs_from_checkout_run_deployment');
  const status = await read('/api/hud/status?period=24h', true);
  if (status.status !== 200) throw Error('private_D1_status_unavailable');
  const telemetry = await status.json();
  if (telemetry.source !== 'cloud_hud_telemetry' ||
      !['fresh','stale','never_received'].includes(telemetry.connection))
    throw Error('private_D1_contract_invalid');
  return {private_auth_verified: true, original_hud_verified: true,
    quota_board_verified: true, database_api_verified: true,
    quota_asset_matches_checkout: expectedQuotaAsset === null ? null : true,
    telemetry_connection: telemetry.connection,
    providers_observed: Array.isArray(telemetry.snapshot?.connections)
      ? telemetry.snapshot.connections.length : 0,
    all_nine_live_verified: telemetry.connection === 'fresh' &&
      Array.isArray(telemetry.snapshot?.connections) &&
      telemetry.snapshot.connections.length === 9};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  verifyGithubHud({origin: process.env.ROVOR_HUD_DEPLOY_ORIGIN,
    readerToken: process.env.ROVOR_HUD_READER_TOKEN,
    expectedQuotaAsset: readFileSync(new URL('../../dashboard/command-center/native-v8-9/live-quota-board.js', import.meta.url), 'utf8')})
    .then(result => console.log(JSON.stringify(result)))
    .catch(error => {console.error('Private HUD release readback failed: ' + error.message);
      process.exitCode = 1;});
}
