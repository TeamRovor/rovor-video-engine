import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import worker, {handle, latest, sanitize} from '../integrations/hud-cloud/worker.mjs';
import {publishOnce, validateTarget} from '../tools/hud_telemetry_publisher.mjs';

const NOW = Date.parse('2026-10-24T20:00:00Z');
const WRITER = 'w'.repeat(48), READER = 'r'.repeat(48);
function sample(period = '24h', at = NOW) {
  return {source: 'local_omniroute_read_only_bridge', snapshot_at: new Date(at).toISOString(), period,
    request_count: 4, connection_count: 1, usage_coverage: 'complete_aggregate',
    models: [{id: 'model-a', name: 'model-a', provider: 'provider-a', requests: 4, tokens: 100, request_share_percent: 100}],
    connections: [{provider: 'provider-a', name: 'provider-a', connection_count: 1, enabled_count: 1}],
    workforce: {source: 'existing_worker_sqlite_read_only', unassigned_jobs: 2,
      heartbeat: {available: true, recent: true, age_seconds: 1, last_tick_dispatch: 'paced_wait'},
      employees: ['walter', 'mike', 'jane', 'jesse', 'gale', 'gus', 'saul', 'hank'].map(id => ({id, status: 'queued',
        queued_jobs: 1, running_jobs: 0, host_heartbeat: true, online_verified: false, latest_job: null}))}};
}
function environment() {
  const sql = new DatabaseSync(':memory:');
  sql.exec(fs.readFileSync(new URL('../integrations/hud-cloud/schema.sql', import.meta.url), 'utf8'));
  const DB = {prepare(query) {
    const stmt = sql.prepare(query); let args = [];
    const api = {bind(...values) { args = values; return api; },
      async first() { return stmt.get(...args) || null; },
      async all() { return {results: stmt.all(...args)}; },
      async run() { return {meta: {changes: Number(stmt.run(...args).changes)}}; }};
    return api;
  }, async batch(statements) {
    sql.exec('BEGIN');
    try { const results = []; for (const s of statements) results.push(await s.run()); sql.exec('COMMIT'); return results; }
    catch (e) { sql.exec('ROLLBACK'); throw e; }
  }};
  return {DB, HUD_WRITER_TOKEN: WRITER, HUD_READER_TOKEN: READER};
}
function request(route, {token = READER, method = 'GET', body} = {}) {
  return new Request('https://hud.example' + route, {method,
    headers: token ? {Authorization: 'Bearer ' + token, 'Content-Type': 'application/json'} : {},
    ...(body !== undefined ? {body: JSON.stringify(body)} : {})});
}
const ingest = (env, doc = sample(), now = NOW) => handle(request('/api/hud/ingest', {token: WRITER, method: 'POST', body: doc}), env, now);

test('reader cannot upload, writer cannot read, no anonymous data', async () => {
  const env = environment();
  for (const r of [request('/api/hud/status', {token: null}), request('/api/hud/status', {token: WRITER}),
    request('/api/hud/ingest', {method: 'POST', body: sample()})]) assert.equal((await handle(r, env, NOW)).status, 401);
});
test('shared or absent credentials fail closed', async () => {
  const env = environment(); env.HUD_READER_TOKEN = WRITER;
  assert.equal((await handle(request('/api/hud/status', {token: WRITER}), env, NOW)).status, 503);
  env.HUD_READER_TOKEN = ''; assert.equal((await handle(request('/api/hud/status', {token: ''}), env, NOW)).status, 401);
});
test('empty service explicitly says never received', async () => {
  assert.equal((await latest(environment().DB, '24h', NOW)).connection, 'never_received');
});
test('stores all periods separately and existing HUD response preserves source timestamp', async () => {
  const env = environment();
  for (const period of ['1h', '24h', '7d']) assert.equal((await ingest(env, sample(period))).status, 200);
  const data = await (await handle(request('/api/hud/omniroute?period=1h'), env, NOW)).json();
  assert.equal(data.period, '1h'); assert.equal(data.snapshot_at, sample().snapshot_at); assert.equal(data.transport.connection, 'fresh');
});
test('closure and restart preserve reports through durable database, stale report remains stale', async () => {
  const env = environment(); await ingest(env);
  const reopened = {...env};
  const data = await (await handle(request('/api/hud/status'), reopened, NOW + 60000)).json();
  assert.equal(data.connection, 'stale'); assert.equal(data.age_seconds, 60); assert.equal(data.snapshot.request_count, 4);
  assert.equal(data.snapshot.workforce.employees[0].online_verified, false);
});
test('old upload and duplicate cannot overwrite current state or refresh receipt time', async () => {
  const env = environment(); await ingest(env);
  assert.equal((await (await ingest(env, sample(), NOW + 5000)).json()).accepted, false);
  const old = sample('24h', NOW - 1000); old.request_count = 99;
  assert.equal((await (await ingest(env, old, NOW + 5000)).json()).accepted, false);
  const data = await latest(env.DB, '24h', NOW + 60000);
  assert.equal(data.received_at, new Date(NOW).toISOString()); assert.equal(data.snapshot.request_count, 4);
});
test('rejects stale and future source clocks', async () => {
  for (const age of [-5001, 120001]) assert.equal((await ingest(environment(), sample('24h', NOW - age))).status, 400);
});
test('history deduplicates minute, excludes other periods, prunes after 24 hours', async () => {
  const env = environment(); await ingest(env); await ingest(env, sample('24h', NOW + 1000), NOW + 1000);
  await ingest(env, sample('1h', NOW + 61000), NOW + 61000);
  let data = await (await handle(request('/api/hud/history'), env, NOW + 61000)).json(); assert.equal(data.snapshots.length, 1);
  const tomorrow = NOW + 86460000; await ingest(env, sample('24h', tomorrow), tomorrow);
  data = await (await handle(request('/api/hud/history'), env, tomorrow)).json(); assert.equal(data.snapshots.length, 1);
  assert.equal(data.snapshots[0].snapshot.snapshot_at, new Date(tomorrow).toISOString());
});
test('allowlist removes private fields including nested workforce output', () => {
  const doc = sample(); doc.api_key = 'secret'; doc.workforce.private_path = '/secret'; doc.models[0].prompt = 'secret';
  doc.workforce.employees[0].output = 'secret';
  assert.equal(JSON.stringify(sanitize(doc, NOW)).includes('secret'), false);
});
test('rejects malformed counts, ratios, duplicates and employee role substitution', () => {
  const changes = [d => d.request_count = -1, d => d.models[0].tokens = '10', d => d.models[0].request_share_percent = 101,
    d => d.models.push(d.models[0]), d => d.workforce.employees[0].id = 'unknown',
    d => d.workforce.employees[1].id = 'walter', d => d.workforce.employees[0].online_verified = 'yes',
    d => d.connection_count = 9, d => d.models[0].requests = 8];
  for (const change of changes) { const d = sample(); change(d); assert.throws(() => sanitize(d, NOW)); }
});
test('missing worker evidence remains unavailable rather than inventing employees', async () => {
  const d = sample(); d.workforce = {source: 'worker_state_unavailable', employees: [], heartbeat: {available: false}};
  assert.deepEqual(sanitize(d, NOW).workforce.employees, []);
});
test('untrusted huge bodies and invalid periods are rejected', async () => {
  const env = environment();
  assert.equal((await handle(request('/api/hud/ingest', {token: WRITER, method: 'POST', body: {x: 'x'.repeat(40000)}}), env, NOW)).status, 400);
  assert.equal((await handle(request('/api/hud/status?period=forever'), env, NOW)).status, 400);
});
test('read-only MCP returns evidence and staleness without dispatch tools', async () => {
  const env = environment(); await ingest(env);
  const rpc = async (method, params) => (await handle(request('/mcp', {method: 'POST', body: {jsonrpc: '2.0', id: 1, method, params}}), env, NOW + 60000)).json();
  const list = await rpc('tools/list'); assert.deepEqual(list.result.tools.map(t => t.name), ['rovor_workforce_status']);
  const call = await rpc('tools/call', {name: 'rovor_workforce_status', arguments: {period: '24h'}});
  assert.equal(JSON.parse(call.result.content[0].text).connection, 'stale');
  assert.equal((await rpc('tools/call', {name: 'run_job'})).error.code, -32601);
});
test('publisher uses only pinned HTTPS ingest, no cookies or redirects, exact evidence', async () => {
  const sent = [];
  await publishOnce({origin: 'https://hud.example', token: WRITER, collect: async p => sample(p), workers: async () => sample().workforce,
    send: async (url, options) => { sent.push({url, options}); return new Response('{}'); }});
  assert.equal(sent.length, 3);
  for (const {url, options} of sent) {
    assert.equal(url, 'https://hud.example/api/hud/ingest'); assert.equal(options.redirect, 'error');
    assert.equal(options.headers.Authorization, 'Bearer ' + WRITER); assert.equal(JSON.parse(options.body).snapshot_at, sample().snapshot_at);
  }
  for (const value of ['http://hud.example', 'https://hud.example/#secret', 'https://a:b@hud.example', 'https://hud.example/path', 'https://hud.example/?token=secret']) assert.throws(() => validateTarget(value));
});
test('publisher stops after rejection, does not retry or call models within one cycle', async () => {
  let sends = 0;
  await assert.rejects(publishOnce({origin: 'https://hud.example', token: WRITER, collect: async p => sample(p), workers: async () => sample().workforce,
    send: async () => { sends++; return new Response('{}', {status: 503}); }}));
  assert.equal(sends, 1);
});
test('Worker fetch entrypoint does not mistake execution context for the clock', async () => {
  const env = environment();
  assert.equal((await worker.fetch(request('/api/hud/status'), env, {waitUntil() {}})).status, 200);
});
test('browser sign-in requires same origin, sets private cookie, and reads without pairing links', async () => {
  const env = environment(); await ingest(env);
  const login = origin => handle(new Request('https://hud.example/login', {method: 'POST', headers: {'Content-Type': 'application/json', Origin: origin}, body: JSON.stringify({token: READER})}), env, NOW);
  assert.equal((await login('https://evil.example')).status, 403);
  const result = await login('https://hud.example'); assert.equal(result.status, 204);
  const cookie = result.headers.get('Set-Cookie'); assert.match(cookie, /Secure; HttpOnly; SameSite=Strict/);
  const view = await handle(new Request('https://hud.example/api/hud/status', {headers: {Cookie: cookie.split(';')[0]}}), env, NOW);
  assert.equal(view.status, 200); assert.equal((await view.json()).connection, 'fresh');
  const post = await handle(new Request('https://hud.example/mcp', {method: 'POST', headers: {Cookie: cookie.split(';')[0]}, body: '{}'}), env, NOW);
  assert.equal(post.status, 401);
});
test('original HUD is served behind authentication with automatic same-origin telemetry', async () => {
  const env = environment(); env.ASSETS = {fetch: async () => new Response('<html><body>Original HUD</body></html>', {headers: {'Content-Type': 'text/html'}})};
  assert.equal((await handle(request('/', {token: null}), env, NOW)).status, 303);
  const html = await (await handle(request('/'), env, NOW)).text();
  assert.match(html, /Original HUD/); assert.match(html, /ROVOR_START_OMNIROUTE/); assert.match(html, /credentials:'same-origin'/);
  assert.equal(html.includes(READER), false); assert.equal(html.includes(WRITER), false);
});
