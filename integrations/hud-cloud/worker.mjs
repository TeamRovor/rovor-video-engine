// Private telemetry only: no inference, job dispatch, or Mac control.
const PERIODS = new Set(['1h', '24h', '7d']);
const ROLES = new Set(['walter', 'mike', 'jane', 'jesse', 'gale', 'gus', 'saul', 'hank']);
const LIMIT = 32768;
const LOGIN = `<!doctype html><meta name="viewport" content="width=device-width"><title>ROVOR HUD sign in</title>
<body style="background:#020916;color:#bde5ff;font:16px system-ui;padding:32px"><h1>ROVOR · HUD</h1>
<p>Sign in to view private usage and employee reports on this device.</p>
<form id="login"><label>HUD viewing key <input id="key" type="password" autocomplete="current-password" required></label> <button>Sign in</button></form>
<p id="status" role="status"></p><script>document.getElementById('login').onsubmit=async e=>{e.preventDefault();const key=document.getElementById('key');try{const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:key.value})});key.value='';if(r.ok)location.replace('/');else document.getElementById('status').textContent='Sign-in failed.'}catch{document.getElementById('status').textContent='Connection unavailable.'}}</script>`;
const CLOUD_START = `<script>document.getElementById('connectOmniRoute')?.remove();window.ROVOR_OMNIROUTE_REQUEST=(resource,opts)=>fetch(resource,{...opts,credentials:'same-origin'});window.ROVOR_START_OMNIROUTE?.();</script>`;
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
    quota_state: 'unknown_not_estimated', models, connections,
    workforce: {source: workforce.source, employees, unassigned_jobs: optional(workforce.unassigned_jobs),
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
    snapshot: JSON.parse(row.body)};
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
