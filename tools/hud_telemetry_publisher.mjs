#!/usr/bin/env node
// Reports the existing collectors outbound; never starts or changes a worker.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {setTimeout as delay} from 'node:timers/promises';
import {createCollector, createWorkerReader, isEntrypoint} from './hud_omniroute_bridge.mjs';

const run = promisify(execFile);
async function keychain(service) {
  if (process.platform !== 'darwin') return null;
  try { return (await run('/usr/bin/security', ['find-generic-password', '-s', service, '-w'], {timeout: 5000})).stdout.trim(); }
  catch { return null; }
}

export function validateTarget(value) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password || url.hash || url.search || (url.pathname !== '/' && url.pathname !== '')) throw Error('invalid_cloud_origin');
  return url.origin;
}

// Only the existing authenticated read-only OmniRoute telemetry endpoints.
export function isAllowedLocalReadPath(resource) {
  return resource === '/api/providers' ||
    resource === '/api/usage/provider-limits' ||
    (typeof resource === 'string' && (resource.startsWith('/api/usage/analytics?') || resource.startsWith('/api/usage/call-logs?')));
}

async function localReader() {
  const candidates = [process.env.OMNIROUTE_CLI, path.join(process.env.HOME || '', '.local/bin/omniroute'),
    ...String(process.env.PATH || '').split(path.delimiter).map(p => path.join(p, 'omniroute'))].filter(Boolean);
  let root;
  for (const candidate of candidates) {
    try {
      let dir = path.dirname(fs.realpathSync(candidate));
      for (let i = 0; i < 5; i++, dir = path.dirname(dir)) {
        if (fs.existsSync(path.join(dir, 'bin/cli/utils/cliToken.mjs'))) { root = dir; break; }
      }
      if (root) break;
    } catch {}
  }
  if (!root) throw Error('omniroute_cli_missing');
  const {getCliToken, CLI_TOKEN_HEADER} = await import(pathToFileURL(path.join(root, 'bin/cli/utils/cliToken.mjs')).href);
  const cliToken = await getCliToken();
  if (!cliToken) throw Error('omniroute_cli_auth_missing');
  const endpointKey = process.env.OMNIROUTE_API_KEY || await keychain('rovordigital.omniroute.endpoint');
  return async resource => {
    if (!isAllowedLocalReadPath(resource)) throw Error('path_denied');
    const headers = {[CLI_TOKEN_HEADER]: cliToken, Accept: 'application/json'};
    if (endpointKey) headers.Authorization = 'Bearer ' + endpointKey;
    const result = await fetch('http://127.0.0.1:20128' + resource, {headers, redirect: 'error', signal: AbortSignal.timeout(8000)});
    if (!result.ok) throw Error('local_gateway_unavailable');
    let size = 0; const chunks = [];
    for await (const chunk of result.body) {
      size += chunk.byteLength;
      if (size > 4 * 1024 * 1024) throw Error('local_response_too_large');
      chunks.push(Buffer.from(chunk));
    }
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  };
}

export async function publishOnce({origin, token, serviceToken, collect, workers, send = fetch}) {
  origin = validateTarget(origin);
  if (typeof token !== 'string' || token.length < 32 || token.length > 200 || /[\r\n]/.test(token)) throw Error('writer_token_missing');
  if (serviceToken !== undefined && (typeof serviceToken !== 'string' || !serviceToken || serviceToken.length > 4096 || /[\r\n]/.test(serviceToken))) throw Error('service_token_invalid');
  const workforce = await workers();
  for (const period of ['24h', '1h', '7d', '1m']) {
    const snapshot = {...await collect(period), workforce};
    const body = JSON.stringify(snapshot);
    if (Buffer.byteLength(body) > 32768) throw Error('snapshot_too_large');
    const result = await send(origin + '/api/hud/ingest', {method: 'POST', headers: {
      Authorization: 'Bearer ' + token, 'Content-Type': 'application/json',
      ...(serviceToken ? {'OAI-Sites-Authorization': 'Bearer ' + serviceToken} : {})}, body,
      redirect: 'error', signal: AbortSignal.timeout(10000)});
    if (!result.ok) throw Error('cloud_report_rejected');
    let acknowledgment;
    try { acknowledgment = await result.json(); } catch { throw Error('cloud_report_unconfirmed'); }
    if (acknowledgment?.accepted !== true) throw Error('cloud_report_unconfirmed');
  }
}

async function main() {
  const origin = validateTarget(process.env.ROVOR_HUD_ORIGIN);
  const token = process.env.ROVOR_HUD_WRITER_TOKEN || await keychain('rovordigital.hud.writer');
  const serviceToken = process.env.ROVOR_HUD_SERVICE_TOKEN || await keychain('rovordigital.hud.service') || undefined;
  const collect = createCollector(await localReader()), workers = createWorkerReader();
  const stop = new AbortController();
  for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, () => stop.abort());
  let failures = 0;
  do {
    try {
      await publishOnce({origin, token, serviceToken, collect, workers});
      failures = 0;
      console.log(new Date().toISOString() + ' HUD report delivered.');
    } catch {
      failures++;
      // No bodies, credentials, local paths or provider errors enter logs.
      console.error(new Date().toISOString() + ' HUD report unavailable. Retrying with backoff.');
      if (process.argv.includes('--once')) process.exitCode = 1;
    }
    if (process.argv.includes('--once') || stop.signal.aborted) break;
    try { await delay(Math.min(300000, 10000 * 2 ** Math.min(failures, 5)), undefined, {signal: stop.signal}); }
    catch { break; }
  } while (!stop.signal.aborted);
}

if (isEntrypoint(process.argv[1], import.meta.url)) main().catch(() => { console.error('HUD reporting requires a configured HTTPS origin, writer credential, and authenticated local OmniRoute.'); process.exitCode = 1; });
