import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {DatabaseSync} from 'node:sqlite';
import worker, {handle, latest, sanitize} from '../integrations/hud-cloud/worker.mjs';
import {publishOnce, validateTarget, isAllowedLocalReadPath} from '../tools/hud_telemetry_publisher.mjs';

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
  for (const period of ['1m', '1h', '24h', '7d']) assert.equal((await ingest(env, sample(period))).status, 200);
  const data = await (await handle(request('/api/hud/omniroute?period=1h'), env, NOW)).json();
  assert.equal(data.period, '1h'); assert.equal(data.snapshot_at, sample().snapshot_at); assert.equal(data.transport.connection, 'fresh');
  const minute=await (await handle(request('/api/hud/omniroute?period=1m'),env,NOW)).json();
  assert.equal(minute.period,'1m'); assert.equal(minute.transport.connection,'fresh');
  assert.equal((await latest(env.DB,'1m',NOW)).snapshot.request_count,4);
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
test('Mac dispatch counters reach private HUD, unknown or stale values remain unknown', async () => {
  const env = environment(), doc = sample();
  doc.workforce.dispatch = {
    status:'recent_scheduler_report',reason:'paced_wait',
    claims_last_24h:46,max_claims_24h:50,
    queued:1,running:0,needs_review:92,last_tick_executed:0,
    next_eligible_at: NOW / 1000 + 900,
    secret:'DO_NOT_EXPOSE'
  };
  assert.equal((await ingest(env,doc)).status,200);
  const received=await (await handle(request('/api/hud/omniroute'),env,NOW)).json();
  assert.equal(received.workforce.dispatch.reason,'paced_wait');
  assert.equal(received.workforce.dispatch.claims_last_24h,46);
  assert.equal(received.workforce.dispatch.needs_review,92);
  assert.equal(received.workforce.dispatch.last_tick_executed,0);
  assert.equal(JSON.stringify(received).includes('DO_NOT_EXPOSE'),false);
  const old=sample();old.workforce.dispatch={status:'unavailable_or_stale'};
  assert.equal(sanitize(old,NOW).workforce.dispatch.status,'unavailable_or_stale');
  old.workforce.dispatch=doc.workforce.dispatch;
  old.workforce.heartbeat.recent=false;
  assert.equal(sanitize(old,NOW).workforce.dispatch.status,'unavailable_or_stale');
  old.workforce.heartbeat.recent=true;
  old.workforce.dispatch.next_eligible_at = NOW / 1000 + 9999999;
  assert.throws(()=>sanitize(old,NOW));
  old.workforce.dispatch.next_eligible_at = null;
  old.workforce.dispatch.claims_last_24h='46';
  assert.throws(()=>sanitize(old,NOW));
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
  assert.equal(sent.length, 4);
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

test('persistent reporter admits cached provider-limit reads, never inference paths', () => {
  assert.equal(isAllowedLocalReadPath('/api/providers'), true);
  assert.equal(isAllowedLocalReadPath('/api/usage/provider-limits'), true);
  assert.equal(isAllowedLocalReadPath('/api/usage/analytics?range=all'), true);
  for (const path of ['/v1/chat/completions', '/api/usage/provider-limits/refresh',
    '/api/providers/write', '/api/usage/provider-limits?refresh=true']) {
    assert.equal(isAllowedLocalReadPath(path), false, path);
  }
});

test('private HUD retains authenticated cached quota limits and recomputes percent', async () => {
  const env = environment(), d = sample();
  d.quota = {source: 'omniroute_provider_limits_cache', freshness: 'recent_provider_cache',
    apiKey: 'DO_NOT_LEAK',
    records: [{provider: 'provider-a', account_slot: 1, model_id: 'model-a',
      used: 9, total: 12, used_percent: 3, remaining: 999, unit: 'requests',
      fetched_at: new Date(NOW - 20000).toISOString(), reset_at: new Date(NOW + 60000).toISOString(),
      evidence: 'recent_authenticated_local_provider_cache', scope: 'model_on_provider_account',
      raw_key: 'DO_NOT_LEAK'}]};
  assert.equal((await ingest(env, d)).status, 200);
  const read = await (await handle(request('/api/hud/omniroute'), env, NOW)).json();
  assert.equal(read.quota.records.length, 1);
  assert.equal(read.quota.records[0].used_percent, 75);
  assert.equal(read.quota.records[0].remaining, 3);
  assert.equal(read.quota.records[0].reset_at, new Date(NOW + 60000).toISOString());
  assert.equal(JSON.stringify(read).includes('DO_NOT_LEAK'), false);
  const pastReset = await (await handle(request('/api/hud/omniroute'), env, NOW + 61000)).json();
  assert.equal(pastReset.quota.records.length, 0);
  assert.equal(pastReset.quota.freshness, 'no_fresh_supported_limits');
  assert.equal((await latest(env.DB, '24h', NOW)).snapshot.quota.records.length, 1);
});

test('missing, malformed, cross-provider and expired quotas never produce fictional bars', () => {
  assert.equal(sanitize(sample(), NOW).quota.records.length, 0);
  const base = () => {
    const d = sample();
    d.quota = {source: 'omniroute_provider_limits_cache', records: [{
      provider: 'provider-a', account_slot: 1, model_id: 'model-a',
      used: 1, total: 10, unit: 'tokens',
      fetched_at: new Date(NOW - 5000).toISOString(), reset_at: null,
      evidence: 'recent_authenticated_local_provider_cache', scope: 'model_on_provider_account'
    }]};
    return d;
  };
  for (const alter of [
    d => d.quota.records[0].provider = 'unknown',
    d => d.quota.records[0].account_slot = 2,
    d => d.quota.records[0].total = 0,
    d => d.quota.records[0].used = 11,
    d => d.quota.records[0].unit = 'dollars',
    d => d.quota.records[0].evidence = 'unverified',
    d => d.quota.records.push({...d.quota.records[0]}),
    d => d.quota.records[0].fetched_at = 'not a date'
  ]) {
    const d = base(); alter(d); assert.throws(() => sanitize(d, NOW));
  }
  const d = base(); d.quota.records[0].reset_at = new Date(NOW - 1).toISOString();
  assert.equal(sanitize(d, NOW).quota.records.length, 0);
});

test('private receiver checks nine sanitized connection slots and rejects identity leakage',()=>{
  const d=sample();
  d.connection_count=9;
  d.connections=[{provider:'groq',name:'groq',connection_count:6,enabled_count:5},
    {provider:'mistral',name:'mistral',connection_count:3,enabled_count:2}];
  d.models=[];
  d.request_count=0;
  d.connection_slots=[
    ...Array.from({length:6},(_,i)=>({provider:'groq',account_slot:i+1,enabled:i<5})),
    ...Array.from({length:3},(_,i)=>({provider:'mistral',account_slot:i+1,enabled:i<2}))];
  const safe=sanitize(d,NOW);
  assert.equal(safe.connection_slots.length,9);
  assert.equal(safe.connection_slots.filter(s=>s.enabled).length,7);
  assert.equal(JSON.stringify(safe).includes('apiKey'),false);
  const tamper=change=>{const e=structuredClone(d);change(e);assert.throws(()=>sanitize(e,NOW));};
  tamper(e=>e.connection_slots[0].provider='unknown-provider');
  tamper(e=>e.connection_slots[0].account_slot=2);
  tamper(e=>e.connection_slots[0].enabled='true');
  tamper(e=>e.connection_slots[0].enabled=false);
  tamper(e=>e.connection_slots.pop());
  // Legacy reporter remains usable, but does not claim per-account enabled status.
  delete d.connection_slots;
  assert.equal(sanitize(d,NOW).connection_slots,null);
});

test('HUD reporter CLI executes rather than silently returning success', () => {
  const script = new URL('../tools/hud_telemetry_publisher.mjs', import.meta.url);
  const attempt = spawnSync(process.execPath, [script.pathname, '--once'], {
    encoding: 'utf8', timeout: 10000,
    env: {...process.env, ROVOR_HUD_ORIGIN: 'http://not-a-secure-site.invalid'}
  });
  assert.equal(attempt.error, undefined);
  assert.notEqual(attempt.status, 0,
    'An invalid upload origin must not silently return success');
  assert.match(attempt.stderr, /HUD reporting requires a configured HTTPS origin/);
  assert.doesNotMatch(attempt.stdout, /HUD report delivered/);
});


test('Gemini project monitoring is owner-reader-only and never sends inference when not configured',async()=>{
 const env=environment();
 for(const token of [null,WRITER]){
  assert.equal((await handle(request('/api/hud/gemini/project-quota',{token}),env,NOW)).status,401);
 }
 const result=await handle(request('/api/hud/gemini/project-quota'),env,NOW);
 assert.equal(result.status,200);
 assert.deepEqual(await result.json(),{source:'google_cloud_monitoring',status:'not_configured',models:[]});
 assert.equal((await handle(request('/api/hud/gemini/project-quota',{method:'POST',body:{}}),env,NOW)).status,405);
});
