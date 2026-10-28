import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createSitesHandler} from '../integrations/hud-cloud/sites-adapter.mjs';
import {bundleSitesWorker, buildSite} from '../integrations/hud-cloud/build-sites.mjs';
import {publishOnce} from '../tools/hud_telemetry_publisher.mjs';

const root = path.resolve(import.meta.dirname, '..');
const read = p => fs.readFileSync(path.join(root, p), 'utf8');
const html = read('dashboard/command-center/native-v8-9/index.html');
const quotaJS = read('dashboard/command-center/native-v8-9/live-quota-board.js');
const handler = createSitesHandler(html, quotaJS);
const emptyDB = {prepare() { return {bind() { return this; }, async first() { return null; }}; }};
const env = {DB: emptyDB, HUD_WRITER_TOKEN: 'w'.repeat(48)};
function req(route = '/', {identity, token, method = 'GET', body} = {}) {
  return new Request('https://private.chatgpt.site' + route, {method, headers: {
    ...(identity ? {'oai-authenticated-user-id': identity} : {}),
    ...(token ? {Authorization: 'Bearer ' + token} : {}),
    'Content-Type': 'application/json'}, ...(body !== undefined ? {body: JSON.stringify(body)} : {})});
}

test('private Site requires platform viewer identity, even with writer token', async () => {
  assert.equal((await handler(req(), env)).status, 401);
  assert.equal((await handler(req('/api/hud/status', {token: env.HUD_WRITER_TOKEN}), env)).status, 401);
});
test('platform viewer loads exact original HUD with same-origin live adapter and no viewing key', async () => {
  const response = await handler(req('/', {identity: 'owner-id'}), env);
  assert.equal(response.status, 200);
  const shown = await response.text();
  assert.ok(shown.startsWith(html.slice(0, 1000)));
  const injection = shown.slice(html.indexOf('</body>'), shown.indexOf('</body>'));
  assert.match(injection, /ROVOR_START_OMNIROUTE/);
  assert.equal(shown.replace(injection, ''), html);
  assert.equal(shown.includes(env.HUD_WRITER_TOKEN), false);
  assert.equal(response.headers.get('Set-Cookie'), null);
});
test('private Site serves original quota board only to authenticated viewers', async () => {
  const denied = await handler(req('/hud-quota.js'), env);
  assert.equal(denied.status, 401);
  const served = await handler(req('/hud-quota.js', {identity: 'owner-id'}), env);
  assert.equal(served.status, 200);
  assert.equal(served.headers.get('Cache-Control'), 'no-store');
  assert.match(served.headers.get('Content-Type'), /text\/javascript/);
  assert.equal(await served.text(), quotaJS);
  assert.equal((await handler(req('/hud-quota.js', {identity: 'owner-id', method: 'POST'}), env)).status, 405);
  const hud = await (await handler(req('/', {identity: 'owner-id'}), env)).text();
  assert.match(hud, /src="\/hud-quota.js"/);
  assert.match(hud, /ROVOR_QUOTA_BOARD\?\.start/);
});
test('platform viewer reads status without a bearer key or writer configuration', async () => {
  const response = await handler(req('/api/hud/status', {identity: 'owner-id'}), {DB: emptyDB});
  assert.equal(response.status, 200);
  assert.equal((await response.json()).connection, 'never_received');
});
test('platform identity does not authorize ingestion', async () => {
  const response = await handler(req('/api/hud/ingest', {identity: 'owner-id', method: 'POST', body: {}}), env);
  assert.equal(response.status, 401);
});
test('private Site MCP reader works with trusted identity and cannot dispatch jobs', async () => {
  const response = await handler(req('/mcp', {identity: 'owner-id', method: 'POST', body: {jsonrpc: '2.0', id: 1, method: 'tools/list'}}), env);
  assert.equal(response.status, 200);
  assert.deepEqual((await response.json()).result.tools.map(t => t.name), ['rovor_workforce_status']);
});
test('legacy key login is removed from private platform deployment', async () => {
  const response = await handler(req('/login', {identity: 'owner-id'}), env);
  assert.equal(response.status, 303);
  assert.equal(response.headers.get('Location'), 'https://private.chatgpt.site/');
});
test('self-contained bundle preserves original HUD and imports without dependencies', async () => {
  const core = read('integrations/hud-cloud/worker.mjs'), adapter = read('integrations/hud-cloud/sites-adapter.mjs');
  const a = bundleSitesWorker(core, adapter, html), b = bundleSitesWorker(core, adapter, html);
  assert.equal(a, b);
  const module = await import('data:text/javascript;base64,' + Buffer.from(a).toString('base64'));
  assert.equal(typeof module.default.fetch, 'function');
  const quota = await module.default.fetch(req('/api/hud/gemini/project-quota', {identity: 'owner-id'}), env);
  assert.equal(quota.status, 200);
  assert.equal((await quota.json()).status, 'not_configured');
  const response = await module.default.fetch(req('/', {identity: 'owner-id'}), env);
  assert.equal(response.status, 200);
  assert.ok((await response.text()).startsWith(html.slice(0, 1000)));
});
test('bundle refuses missing live adapter or unexpected source shapes', () => {
  const core = read('integrations/hud-cloud/worker.mjs'), adapter = read('integrations/hud-cloud/sites-adapter.mjs');
  assert.throws(() => bundleSitesWorker(core, adapter, '<body>Wrong HUD</body>'));
  assert.throws(() => bundleSitesWorker(core + '\n' + core, adapter, html));
});
test('build retains Site identity, declares MCP, includes schema, and is repeatable', t => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hud-site-test-'));
  t.after(() => fs.rmSync(dir, {recursive: true, force: true}));
  fs.mkdirSync(path.join(dir, '.openai'));
  fs.writeFileSync(path.join(dir, '.openai/hosting.json'), JSON.stringify({project_id: 'appgprj_test_fixture', d1: null, r2: null}));
  const first = buildSite(dir), code = fs.readFileSync(path.join(dir, 'dist/server/index.js'), 'utf8');
  assert.equal(first.project_id, 'appgprj_test_fixture');
  assert.equal(first.worker_bytes, Buffer.byteLength(code));
  const manifest = JSON.parse(fs.readFileSync(path.join(dir, '.openai/hosting.json'), 'utf8'));
  assert.deepEqual(manifest.capabilities, ['mcp']); assert.equal(manifest.d1.binding, 'DB');
  const sql = fs.readFileSync(path.join(dir, 'drizzle/0000_hud_telemetry.sql'), 'utf8');
  assert.match(sql, /CREATE TABLE IF NOT EXISTS hud_latest/); assert.match(sql, /statement-breakpoint/);
  assert.deepEqual(buildSite(dir), first);
  assert.equal(fs.readFileSync(path.join(dir, 'dist/server/index.js'), 'utf8'), code);
  assert.match(code, /ROVOR_QUOTA_BOARD/);
  assert.match(code, /All configured AI connections/);
});
test('build never rewrites a conflicting applied migration or existing build', t => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hud-site-migration-'));
  t.after(() => fs.rmSync(dir, {recursive: true, force: true}));
  fs.mkdirSync(path.join(dir, '.openai'));
  fs.writeFileSync(path.join(dir, '.openai/hosting.json'), JSON.stringify({project_id: 'appgprj_test_fixture'}));
  buildSite(dir);
  const migration = path.join(dir, 'drizzle/0000_hud_telemetry.sql');
  fs.writeFileSync(migration, 'Existing migration');
  fs.writeFileSync(path.join(dir, 'worker/index.js'), 'Previous reviewed source');
  assert.throws(() => buildSite(dir), /Existing migration differs/);
  assert.equal(fs.readFileSync(migration, 'utf8'), 'Existing migration');
  assert.equal(fs.readFileSync(path.join(dir, 'worker/index.js'), 'utf8'), 'Previous reviewed source');
});
test('publisher authenticates private Sites service access separately from ingestion', async () => {
  const sent = [];
  await publishOnce({origin: 'https://private.chatgpt.site', token: env.HUD_WRITER_TOKEN, serviceToken: 'private-service-token',
    workers: async () => ({}), collect: async period => ({period}),
    send: async (url, options) => {sent.push({url, options}); return Response.json({accepted: true});}});
  for (const s of sent) {
    assert.equal(s.url, 'https://private.chatgpt.site/api/hud/ingest');
    assert.equal(s.options.headers.Authorization, 'Bearer ' + env.HUD_WRITER_TOKEN);
    assert.equal(s.options.headers['OAI-Sites-Authorization'], 'Bearer private-service-token');
    assert.equal(s.options.redirect, 'error');
  }
  await assert.rejects(publishOnce({origin: 'https://private.chatgpt.site', token: env.HUD_WRITER_TOKEN, serviceToken: 'bad\r\nvalue'}), /service_token_invalid/);
});
