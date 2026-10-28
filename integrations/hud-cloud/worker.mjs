import {readGoogleGeminiQuota} from './gemini-cloud-monitoring.mjs';
// Private telemetry only: no inference, job dispatch, or Mac control.
const PERIODS = new Set(['1m', '1h', '24h', '7d']);
// Private read-only short cache: never store access tokens, raw Google responses or credentials.
let geminiQuotaCache=null,geminiQuotaPending=null;
async function cachedGeminiQuota(env,now=Date.now()){
 if(geminiQuotaCache&&now-geminiQuotaCache.at<60000)return geminiQuotaCache.value;
 if(geminiQuotaPending)return geminiQuotaPending;
 const pending=readGoogleGeminiQuota(env,{now}).then(value=>{
   // Unconfigured/permission error state retries sooner than healthy readings.
   geminiQuotaCache={at:now,value};return value;
 }).finally(()=>{geminiQuotaPending=null;});
 geminiQuotaPending=pending;return pending;
}

const ROLES = new Set(['walter', 'mike', 'jane', 'jesse', 'gale', 'gus', 'saul', 'hank']);
const LIMIT = 32768;
const LOGIN = `<!doctype html><meta name="viewport" content="width=device-width"><title>ROVOR HUD sign in</title>
<body style="background:#020916;color:#bde5ff;font:16px system-ui;padding:32px"><h1>ROVOR · HUD</h1>
<p>Sign in to view private usage and employee reports on this device.</p>
<form id="login"><label>HUD viewing key <input id="key" type="password" autocomplete="current-password" required></label> <button>Sign in</button></form>
<p id="status" role="status"></p><script>document.getElementById('login').onsubmit=async e=>{e.preventDefault();const key=document.getElementById('key');try{const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:key.value})});key.value='';if(r.ok)location.replace('/');else document.getElementById('status').textContent='Sign-in failed.'}catch{document.getElementById('status').textContent='Connection unavailable.'}}</script>`;
const CLOUD_START = `<script src="/hud-quota.js"></script><script>document.getElementById('connectOmniRoute')?.remove();window.ROVOR_OMNIROUTE_REQUEST=(resource,opts)=>fetch(resource,{...opts,credentials:'same-origin'});window.ROVOR_START_OMNIROUTE?.();window.ROVOR_QUOTA_BOARD?.start?.();</script>`;
const response = (status, body) => Response.json(body, {status, headers: {
  'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'no-referrer',
}});
const fail = () => { throw Error('invalid_snapshot'); };
const integer = x => Number.isSafeInteger(x) && x >= 0 ? x : fail();
const optional = x => x == null ? null : integer(x);
const label = (x, max = 200) => typeof x === 'string' && x.length <= max && !/[\u0000-\u001f]/.test(x) ? x : fail();
const nullableLabel = x => x == null ? null : label(x);
const flag = x => typeof x === 'boolean' ? x : fail();
const ratio = x => x == null ? null : typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 100 ? x : fail();


// A cached quota is provider evidence, not an inferred request-share limit.
// Keep only approved fields; never forward connection IDs, credentials or raw responses.
const QUOTA_ID = /^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,199}$/;
const QUOTA_UNITS = new Set(['requests', 'tokens', 'credits', 'units', 'percent', 'provider units']);
const quotaIdentifier = x => typeof x === 'string' && QUOTA_ID.test(x) ? x : fail();
const quotaAmount = x => typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 1e15 ? x : fail();
const quotaDate = x => {
  const parsed = typeof x === 'string' ? Date.parse(x) : NaN;
  return Number.isFinite(parsed) && parsed > 0 && parsed < Date.UTC(2100, 0, 1) ? parsed : fail();
};
function sanitizeQuota(input, connections, now) {
  const configured = connections.reduce((n, c) => n + c.connection_count, 0);
  const empty = {source: 'omniroute_provider_limits_cache', freshness: 'unavailable',
    records: [], counts: {configured, with_limits: 0}, checked_at: new Date(now).toISOString()};
  if (input == null) return empty; // Older reporters have no quota support.
  if (input.source !== empty.source || !Array.isArray(input.records) || input.records.length > 100) fail();
  const available = new Map(connections.map(c => [c.provider, c.connection_count]));
  const seen = new Set(), records = [];
  for (const r of input.records) {
    const provider = quotaIdentifier(r?.provider), model_id = quotaIdentifier(r?.model_id);
    const account_slot = integer(r.account_slot);
    if (!account_slot || account_slot > (available.get(provider) || 0)) fail();
    const key = JSON.stringify([provider, account_slot, model_id]);
    if (seen.has(key)) fail();
    seen.add(key);
    if (r.evidence !== 'recent_authenticated_local_provider_cache' ||
        r.scope !== 'model_on_provider_account' || !QUOTA_UNITS.has(r.unit)) fail();
    const total = quotaAmount(r.total), used = quotaAmount(r.used);
    if (!total || used > total) fail();
    const fetched = quotaDate(r.fetched_at);
    if (fetched > now + 300000 || fetched < now - 5400000) continue;
    const reset = r.reset_at == null ? null : quotaDate(r.reset_at);
    // Never show a previous window's remaining allowance as current.
    if (reset !== null && (reset <= now || reset < fetched)) continue;
    records.push({provider, account_slot, model_id, used, total,
      remaining: total - used, used_percent: 100 * used / total,
      unit: r.unit, fetched_at: new Date(fetched).toISOString(),
      reset_at: reset === null ? null : new Date(reset).toISOString(),
      evidence: r.evidence, scope: r.scope});
  }
  return {source: empty.source,
    freshness: records.length ? 'recent_provider_cache' : 'no_fresh_supported_limits',
    records, counts: {configured, with_limits: new Set(records.map(r => r.provider + ':' + r.account_slot)).size},
    checked_at: new Date(now).toISOString()};
}
function expireQuota(snapshot, now) {
  if (!snapshot?.quota?.records) return snapshot;
  snapshot.quota.records = snapshot.quota.records.filter(r => !r.reset_at || Date.parse(r.reset_at) > now);
  snapshot.quota.counts.with_limits =
    new Set(snapshot.quota.records.map(r => r.provider + ':' + r.account_slot)).size;
  snapshot.quota.freshness = snapshot.quota.records.length ? 'recent_provider_cache' : 'no_fresh_supported_limits';
  return snapshot;
}

const USAGE_PROVIDERS = new Set(['gemini', 'groq', 'openrouter', 'mistral', 'cloudflare', 'cohere', 'nvidia', 'sambanova', 'huggingface']);
const USAGE_STATES = new Set(['fresh', 'stale', 'unavailable']);
const USAGE_COVERAGE = new Set(['complete', 'partial', 'stale', 'unavailable']);
const USAGE_PERIODS = ['rolling_minute', 'rolling_hour', 'pacific_day'];
function sanitizeRequestUsage(input, now) {
  const empty = {source: 'omniroute_durable_call_logs', freshness: 'unavailable', coverage: 'unavailable',
    observed_at: new Date(now).toISOString(), rolling_window_start: null, pacific_day_start: null, pacific_day_reset: null, providers: []};
  if (input == null) return empty;
  if (input.source !== empty.source || !USAGE_STATES.has(input.freshness) || !USAGE_COVERAGE.has(input.coverage) ||
      !Array.isArray(input.providers) || input.providers.length !== USAGE_PROVIDERS.size) fail();
  const date = value => {
    const time = Date.parse(value);
    if (!Number.isFinite(time) || time > now + 26 * 60 * 60 * 1000 || time < now - 26 * 60 * 60 * 1000) fail();
    return new Date(time).toISOString();
  };
  const count = value => value == null ? null : integer(value);
  const tokenCoverage = value => ['complete', 'partial', 'unknown'].includes(value) ? value : fail();
  const counters = value => Object.fromEntries(USAGE_PERIODS.flatMap(period => [
    ['attempts_' + period, integer(value['attempts_' + period])],
    ['successes_' + period, integer(value['successes_' + period])],
    ['failures_' + period, integer(value['failures_' + period])],
    ['rate_limit_errors_' + period, integer(value['rate_limit_errors_' + period])],
    ...['input', 'output'].flatMap(kind => [
      [kind + '_tokens_recorded_' + period, count(value[kind + '_tokens_recorded_' + period])],
      [kind + '_tokens_coverage_' + period, tokenCoverage(value[kind + '_tokens_coverage_' + period])]])
  ]));
  const seen = new Set();
  const providers = input.providers.map(p => {
    const provider = label(p?.provider);
    if (!USAGE_PROVIDERS.has(provider) || seen.has(provider)) fail();
    seen.add(provider);
    if (!Array.isArray(p.models) || p.models.length > 500) fail();
    const modelIDs = new Set();
    const models = p.models.map(m => {
      const model_id = label(m?.model_id);
      if (modelIDs.has(model_id)) fail();
      modelIDs.add(model_id);
      return {model_id, ...counters(m), last_rate_limit_at: m.last_rate_limit_at == null ? null : date(m.last_rate_limit_at),
        retry_after_at: m.retry_after_at == null ? null : date(m.retry_after_at)};
    });
    return {provider, configured: flag(p.configured), ...counters(p), last_rate_limit_at: p.last_rate_limit_at == null ? null : date(p.last_rate_limit_at),
      retry_after_at: p.retry_after_at == null ? null : date(p.retry_after_at), employee_attribution: p.employee_attribution === 'unknown' ? 'unknown' : fail(), models};
  });
  if (seen.size !== USAGE_PROVIDERS.size) fail();
  return {source: empty.source, freshness: input.freshness, coverage: input.coverage, observed_at: date(input.observed_at),
    rolling_window_start: date(input.rolling_window_start), pacific_day_start: date(input.pacific_day_start),
    pacific_day_reset: date(input.pacific_day_reset), providers};
}

// Bound and allowlist scheduler counters received from the Mac. This is
// diagnostic evidence only and does not authorize dispatch or infer success.
function sanitizeDispatch(input, now, recentHeartbeat) {
  if (!recentHeartbeat || input == null) return {status:'unavailable_or_stale'};
  if (typeof input !== 'object' || Array.isArray(input)) fail();
  if (input.status === 'unavailable_or_stale') return {status:'unavailable_or_stale'};
  if (input.status !== 'recent_scheduler_report') fail();
  const reasons = new Set(['paced_wait','rolling_quota','eligible',
    'no_queued_work','existing_work_running','stop_requested',
    'failure_circuit_requires_review',
    'independent_pool_capacity_checked_per_claim','unknown']);
  if (!reasons.has(input.reason)) fail();
  const numberOrNull = (value, max) => {
    if (value == null) return null;
    const n = integer(value);
    if (n > max) fail();
    return n;
  };
  const next = input.next_eligible_at;
  let next_eligible_at = null;
  if (next != null) {
    if (typeof next !== 'number' || !Number.isFinite(next) ||
        next < now / 1000 - 86400 || next > now / 1000 + 172800) fail();
    next_eligible_at = next;
  }
  return {status: 'recent_scheduler_report', reason: input.reason,
    claims_last_24h: numberOrNull(input.claims_last_24h,100000),
    max_claims_24h: numberOrNull(input.max_claims_24h,100000),
    queued: numberOrNull(input.queued,100000),
    running: numberOrNull(input.running,100000),
    needs_review: numberOrNull(input.needs_review,100000),
    last_tick_executed: numberOrNull(input.last_tick_executed,9),
    next_eligible_at};
}

export function sanitize(doc, now = Date.now()) {
  if (doc?.source !== 'local_omniroute_read_only_bridge' || !PERIODS.has(doc.period)) fail();
  const observed = Date.parse(doc.snapshot_at);
  if (!Number.isFinite(observed) || observed < now - 120000 || observed > now + 5000) fail();
  if (!Array.isArray(doc.models) || doc.models.length > 50 || !Array.isArray(doc.connections) || doc.connections.length > 100) fail();
  const models = doc.models.map(m => ({id: label(m.id), name: label(m.name), provider: nullableLabel(m.provider),
    requests: optional(m.requests), tokens: optional(m.tokens), request_share_percent: ratio(m.request_share_percent), quota_used_percent: null}));
  if (new Set(models.map(m => m.id)).size !== models.length) fail();
  const connections = doc.connections.map(c => ({provider: label(c.provider), name: label(c.name),
    connection_count: integer(c.connection_count), enabled_count: integer(c.enabled_count)}));
  if (new Set(connections.map(c => c.provider)).size !== connections.length || connections.some(c => c.enabled_count > c.connection_count)) fail();
  // New reporters expose one sanitized status per configured account, never IDs,
  // labels, API keys, or endpoint credentials. Older reporters omit this field.
  const connection_slots = doc.connection_slots == null ? null : (() => {
    if (!Array.isArray(doc.connection_slots) || doc.connection_slots.length > 100) fail();
    const seen = new Set(), counts = new Map(), enabled = new Map();
    const available = new Map(connections.map(c => [c.provider, c]));
    const slots = doc.connection_slots.map(s => {
      const provider = label(s?.provider), account_slot = integer(s?.account_slot), active = flag(s?.enabled);
      const group = available.get(provider);
      if (!group || account_slot < 1 || account_slot > group.connection_count) fail();
      const key = provider + ':' + account_slot;
      if (seen.has(key)) fail();
      seen.add(key);
      counts.set(provider, (counts.get(provider) || 0) + 1);
      if (active) enabled.set(provider, (enabled.get(provider) || 0) + 1);
      return {provider, account_slot, enabled: active};
    });
    if (slots.length !== connections.reduce((n,c)=>n+c.connection_count,0)) fail();
    for (const g of connections) {
      if ((counts.get(g.provider) || 0) !== g.connection_count || (enabled.get(g.provider) || 0) !== g.enabled_count) fail();
    }
    return slots;
  })();
  const workforce = doc.workforce;
  if (!workforce || !Array.isArray(workforce.employees) || workforce.employees.length > 8) fail();
  if (!['existing_worker_sqlite_read_only', 'worker_state_unavailable'].includes(workforce.source)) fail();
  const employees = workforce.employees.map(e => {
    if (!ROLES.has(e.id)) fail();
    const j = e.latest_job;
    return {id: e.id, name: e.id[0].toUpperCase() + e.id.slice(1), status: label(e.status),
      queued_jobs: integer(e.queued_jobs), running_jobs: integer(e.running_jobs),
      host_heartbeat: flag(e.host_heartbeat), online_verified: flag(e.online_verified),
      latest_job: j == null ? null : {state: label(j.state), task: label(j.task, 300),
        updated_at: typeof j.updated_at === 'number' && Number.isFinite(j.updated_at) && j.updated_at >= 0 ? j.updated_at : fail(),
        assigned_route: nullableLabel(j.assigned_route), configured_model: nullableLabel(j.configured_model),
        actual_model: nullableLabel(j.actual_model), model_attribution: label(j.model_attribution), current: flag(j.current)}};
  });
  if (new Set(employees.map(e => e.id)).size !== employees.length) fail();
  if (workforce.source === 'existing_worker_sqlite_read_only' && employees.length !== 8) fail();
  const h = workforce.heartbeat || {};
  const snapshot = {schema_version: 1, source: doc.source, snapshot_at: new Date(observed).toISOString(), period: doc.period,
    request_count: integer(doc.request_count), connection_count: integer(doc.connection_count), inventory_count: models.length,
    usage_coverage: ['complete_aggregate', 'partial_top_50_or_unattributed'].includes(doc.usage_coverage) ? doc.usage_coverage : fail(),
    quota_state: 'unknown_not_estimated', models, connections, connection_slots, quota: sanitizeQuota(doc.quota, connections, now),
    request_usage: sanitizeRequestUsage(doc.request_usage, now),
    workforce: {source: workforce.source, employees, unassigned_jobs: optional(workforce.unassigned_jobs),
      dispatch: sanitizeDispatch(workforce.dispatch, now, h.recent === true),
      heartbeat: {available: flag(h.available), recent: h.recent === true, age_seconds: optional(h.age_seconds),
        last_tick_dispatch: nullableLabel(h.last_tick_dispatch)}}};
  if (connections.reduce((n, c) => n + c.connection_count, 0) !== snapshot.connection_count) fail();
  if (models.reduce((n, m) => n + (m.requests || 0), 0) > snapshot.request_count) fail();
  if (new TextEncoder().encode(JSON.stringify(snapshot)).length > LIMIT) fail();
  return snapshot;
}

async function authorized(request, secret) {
  if (typeof secret !== 'string' || secret.length < 32) return false;
  const supplied = request.headers.get('Authorization') || '';
  if (supplied.length > 256) return false;
  const digest = async value => new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value)));
  const [a, b] = await Promise.all([digest(supplied), digest('Bearer ' + secret)]);
  let different = 0;
  for (let i = 0; i < a.length; i++) different |= a[i] ^ b[i];
  return different === 0;
}

async function boundedJSON(request) {
  if (Number(request.headers.get('Content-Length') || 0) > LIMIT) fail();
  if (!request.body) fail();
  const reader = request.body.getReader();
  const chunks = []; let size = 0;
  try {
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > LIMIT) { await reader.cancel(); fail(); }
      chunks.push(value);
    }
    const bytes = new Uint8Array(size); let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
  } finally { reader.releaseLock(); }
}

export async function latest(db, period, now = Date.now()) {
  if (!PERIODS.has(period)) throw Error('period_invalid');
  const row = await db.prepare('SELECT * FROM hud_latest WHERE period = ?').bind(period).first();
  if (!row) return {source: 'cloud_hud_telemetry', connection: 'never_received', snapshot: null};
  const age = Math.max(0, now - row.observed_at);
  return {source: 'cloud_hud_telemetry', connection: age <= 15000 ? 'fresh' : 'stale',
    received_at: new Date(row.received_at).toISOString(), age_seconds: Math.floor(age / 1000),
    snapshot: expireQuota(JSON.parse(row.body), now)};
}

export async function handle(request, env, now = Date.now()) {
  const url = new URL(request.url);
  if (url.pathname === '/login') {
    if (request.method === 'GET') return new Response(LOGIN, {headers: {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store'}});
    if (request.method !== 'POST') return response(405, {error: 'method_not_allowed'});
    if (request.headers.get('Origin') !== url.origin) return response(403, {error: 'origin_denied'});
    let token;
    try { token = (await boundedJSON(request)).token; } catch { return response(400, {error: 'invalid_login'}); }
    if (typeof token !== 'string' || !await authorized({headers: new Headers({Authorization: 'Bearer ' + token})}, env.HUD_READER_TOKEN)) return response(401, {error: 'unauthorized'});
    if (env.HUD_WRITER_TOKEN === env.HUD_READER_TOKEN) return response(503, {error: 'service_not_configured'});
    return new Response(null, {status: 204, headers: {'Cache-Control': 'no-store',
      'Set-Cookie': 'rovor_hud_reader=' + encodeURIComponent(token) + '; Path=/; Max-Age=604800; Secure; HttpOnly; SameSite=Strict'}});
  }
  const ingest = url.pathname === '/api/hud/ingest';
  let authRequest = request;
  if (!ingest && request.method === 'GET' && !request.headers.has('Authorization')) {
    try {
      const cookie = String(request.headers.get('Cookie') || '').split(';').map(c => c.trim()).find(c => c.startsWith('rovor_hud_reader='));
      if (cookie) authRequest = {headers: new Headers({Authorization: 'Bearer ' + decodeURIComponent(cookie.slice(17))})};
    } catch {}
  }
  if (!await authorized(authRequest, ingest ? env.HUD_WRITER_TOKEN : env.HUD_READER_TOKEN)) {
    if (request.method === 'GET' && (url.pathname === '/' || url.pathname === '/index.html')) return Response.redirect(url.origin + '/login', 303);
    return response(401, {error: 'unauthorized'});
  }
  // Misconfiguration must not turn viewer credentials into writer credentials.
  if (env.HUD_WRITER_TOKEN === env.HUD_READER_TOKEN || !env.DB) return response(503, {error: 'service_not_configured'});
  try {
    if (ingest && request.method === 'POST') {
      let doc;
      try { doc = sanitize(await boundedJSON(request), now); } catch { return response(400, {error: 'invalid_snapshot'}); }
      const observed = Date.parse(doc.snapshot_at), body = JSON.stringify(doc);
      const statements = [env.DB.prepare(`INSERT INTO hud_latest (period, observed_at, received_at, body) VALUES (?, ?, ?, ?)
        ON CONFLICT(period) DO UPDATE SET observed_at=excluded.observed_at, received_at=excluded.received_at, body=excluded.body
        WHERE excluded.observed_at > hud_latest.observed_at`).bind(doc.period, observed, now, body)];
      if (doc.period === '24h') {
        statements.push(env.DB.prepare(`INSERT INTO hud_history (minute, observed_at, received_at, body)
          SELECT ?, ?, ?, ? WHERE EXISTS (SELECT 1 FROM hud_latest WHERE period='24h' AND observed_at=?)
          ON CONFLICT(minute) DO NOTHING`).bind(Math.floor(observed / 60000), observed, now, body, observed));
        statements.push(env.DB.prepare('DELETE FROM hud_history WHERE minute < ?').bind(Math.floor((now - 86400000) / 60000)));
      }
      const results = await env.DB.batch(statements);
      return response(200, {accepted: results[0].meta.changes > 0, observed_at: doc.snapshot_at});
    }
    if (ingest) return response(405, {error: 'method_not_allowed'});
    // Standalone Cloudflare host: map the original Site quota URL to the
    // *tracked* GitHub asset. The owner-private ChatGPT Site adapter still
    // owns this same URL separately, so neither hosting path breaks.
    if (request.method === 'GET' && url.pathname === '/hud-quota.js' && env.ASSETS) {
      return env.ASSETS.fetch(new Request(new URL('/live-quota-board.js', url.origin), request));
    }
    if (url.pathname === '/api/hud/gemini/project-quota') {
      if (request.method !== 'GET') return response(405, {error: 'method_not_allowed'});
      // Reader auth has already been validated; NEVER expose secrets or proxy arbitrary URLs.
      return response(200, await cachedGeminiQuota(env, now));
    }
    if (request.method === 'GET' && ['/api/hud/status', '/api/hud/omniroute'].includes(url.pathname)) {
      const period = url.searchParams.get('period') || '24h';
      if (!PERIODS.has(period)) return response(400, {error: 'period_invalid'});
      const result = await latest(env.DB, period, now);
      if (url.pathname.endsWith('/status')) return response(200, result);
      // Existing HUD keeps its original timestamp and refuses stale live meters.
      return result.snapshot ? response(200, {...result.snapshot, transport: {connection: result.connection, received_at: result.received_at}})
        : response(503, {error: 'no_report_received'});
    }
    if (request.method === 'GET' && url.pathname === '/api/hud/history') {
      const rows = await env.DB.prepare('SELECT observed_at, received_at, body FROM hud_history WHERE minute >= ? ORDER BY minute DESC LIMIT 120')
        .bind(Math.floor((now - 86400000) / 60000)).all();
      return response(200, {source: 'cloud_hud_telemetry', snapshots: rows.results.map(r => ({received_at: new Date(r.received_at).toISOString(), snapshot: JSON.parse(r.body)}))});
    }
    if (request.method === 'POST' && url.pathname === '/mcp') {
      let rpc; try { rpc = await boundedJSON(request); } catch { return response(400, {error: 'invalid_json'}); }
      const reply = result => response(200, {jsonrpc: '2.0', id: rpc.id ?? null, result});
      if (rpc.method === 'server/discover') return reply({supportedVersions: ['2026-07-28'], capabilities: {tools: {}}});
      if (rpc.method === 'initialize') return reply({protocolVersion: '2025-03-26', capabilities: {tools: {}}, serverInfo: {name: 'rovor-hud', version: '1.0.0'}});
      if (rpc.method === 'notifications/initialized') return new Response(null, {status: 204});
      if (rpc.method === 'tools/list') return reply({tools: [{name: 'rovor_workforce_status', description: 'Read recorded OmniRoute usage and employee evidence, including last contact and staleness. Does not establish human approval or ongoing inference.', inputSchema: {type: 'object', properties: {period: {type: 'string', enum: [...PERIODS]}}, additionalProperties: false}}]});
      if (rpc.method === 'tools/call' && rpc.params?.name === 'rovor_workforce_status') {
        const args = rpc.params.arguments || {}, period = args.period || '24h';
        if (!PERIODS.has(period) || Object.keys(args).some(k => k !== 'period')) return reply({isError: true, content: [{type: 'text', text: 'Invalid period'}]});
        return reply({content: [{type: 'text', text: JSON.stringify(await latest(env.DB, period, now))}]});
      }
      return response(200, {jsonrpc: '2.0', id: rpc.id ?? null, error: {code: -32601, message: 'Method not found'}});
    }
    if (request.method === 'GET' && env.ASSETS && !url.pathname.startsWith('/api/') && url.pathname !== '/mcp') {
      const asset = await env.ASSETS.fetch(request);
      if ((asset.headers.get('Content-Type') || '').includes('text/html')) {
        const html = await asset.text();
        if (!html.includes('</body>')) return response(503, {error: 'hud_asset_invalid'});
        return new Response(html.replace('</body>', CLOUD_START + '</body>'), {status: asset.status,
          headers: {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'}});
      }
      return asset;
    }
    return response(404, {error: 'not_found'});
  } catch { return response(503, {error: 'telemetry_store_unavailable'}); }
}

export default {fetch(request, env) { return handle(request, env); }};
