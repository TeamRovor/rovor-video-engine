import test from 'node:test';
import assert from 'node:assert/strict';
import {parseChatRequest, buildStatusContext, createChat, CHAT_LIMITS} from '../tools/hud_chat.mjs';
import {createBridge, normalize} from '../tools/hud_omniroute_bridge.mjs';

const ALLOWED = ['rovor-spread-free-v1', 'groq/openai/gpt-oss-120b'];
const body = (extra = {}) => JSON.stringify({model: ALLOWED[0], messages: [{role: 'user', content: 'hi'}], ...extra});

test('chat requests accept only listed models and bounded user/assistant turns', () => {
  assert.equal(parseChatRequest(body(), ALLOWED).model, ALLOWED[0]);
  assert.equal(parseChatRequest(body({context: true}), ALLOWED).context, true);
  for (const bad of [
    'not json', '[]', body({model: 'openrouter/auto'}), body({model: '../x'}),
    body({messages: []}), body({messages: [{role: 'system', content: 'x'}]}),
    body({messages: [{role: 'assistant', content: 'x'}]}),
    body({messages: [{role: 'user', content: ' '}]}),
    body({messages: [{role: 'user', content: 'x'.repeat(CHAT_LIMITS.message + 1)}]}),
    body({messages: Array.from({length: CHAT_LIMITS.messages + 1}, () => ({role: 'user', content: 'x'}))}),
  ]) assert.throws(() => parseChatRequest(bad, ALLOWED), /./, String(bad).slice(0, 40));
});

test('status context is bounded and carries no ids, paths or keys', () => {
  const text = buildStatusContext({period: '24h', request_count: 5,
    workforce: {heartbeat: {available: true, recent: true, last_tick_dispatch: 'paced_wait'},
      employees: [{id: 'secret-id', name: 'Mike', status: 'queued', queued_jobs: 1, latest_job: {task: 'Research\nassignment', assigned_route: 'rovor-spread-free-v1'}}]},
    models: [{name: 'm', requests: 3}]});
  assert.match(text, /Mike: queued/);
  assert.match(text, /rovor-spread-free-v1/);
  assert(!text.includes('secret-id') && !/\n\n/.test(text));
  assert(buildStatusContext({workforce: {employees: Array.from({length: 12}, () => ({name: 'x'.repeat(500), status: 'y'.repeat(500)}))}}).length <= CHAT_LIMITS.contextChars);
  assert.match(buildStatusContext(null), /unavailable/);
});

function fakeFetch(calls, {fail = false} = {}) {
  return async (url, options = {}) => {
    calls.push({url, options});
    if (url.endsWith('/v1/models')) return Response.json({data: [{id: 'groq/openai/gpt-oss-120b', owned_by: 'groq'}, {id: 'rovor-spread-free-v1', owned_by: 'combo'}]});
    if (fail) return new Response('{}', {status: 500});
    return new Response('data: {"choices":[{"delta":{"content":"ok"}}]}\n\ndata: [DONE]\n\n', {status: 200});
  };
}

test('chat lists combos first, forces streaming, caps tokens, adds server-built context only when asked', async () => {
  const calls = [];
  const chat = createChat({apiKey: 'k'.repeat(10), fetchImpl: fakeFetch(calls), status: async () => ({workforce: {employees: [{name: 'Jane', status: 'queued'}]}})});
  assert.deepEqual(await chat.models(), ['rovor-spread-free-v1', 'groq/openai/gpt-oss-120b']);
  const r = await chat.respond(body({context: true, messages: [{role: 'user', content: 'hi'}]}), new AbortController().signal);
  assert.equal(r.status, 200); r.done();
  const sent = JSON.parse(calls.at(-1).options.body);
  assert.equal(sent.stream, true); assert.equal(sent.max_tokens, CHAT_LIMITS.maxTokens);
  assert.equal(sent.messages[0].role, 'system'); assert.match(sent.messages[0].content, /Jane: queued/);
  assert.equal(calls.at(-1).options.redirect, 'error');
  const plain = await chat.respond(body(), new AbortController().signal); plain.done();
  assert(!JSON.parse(calls.at(-1).options.body).messages[0].content.includes('Jane'));
});

test('chat allows one reply at a time, rate-limits, and hides upstream errors', async () => {
  const calls = [];
  const chat = createChat({fetchImpl: fakeFetch(calls)});
  const first = await chat.respond(body(), new AbortController().signal);
  assert.equal((await chat.respond(body(), new AbortController().signal)).status, 429);
  first.done();
  for (let i = 0; i < CHAT_LIMITS.perMinute; i++) { const r = await chat.respond(body(), new AbortController().signal); if (r.status === 200) r.done(); }
  assert.equal((await chat.respond(body(), new AbortController().signal)).json.error, 'chat_rate_limited');
  const broken = createChat({fetchImpl: fakeFetch([], {fail: true})});
  const failed = await broken.respond(body(), new AbortController().signal);
  assert.equal(failed.status, 502); assert(!JSON.stringify(failed.json).includes('SECRET'));
  assert.equal((await broken.respond(body(), new AbortController().signal)).status, 502, 'a failed reply must free the slot');
});

test('bridge chat endpoint needs the paired cookie and same origin, and streams the reply', async () => {
  const catalog = {data: [{id: 'a/m', owned_by: 'a'}]};
  const usage = {summary: {totalRequests: 0, uniqueModels: 0}, byModel: []};
  const chat = createChat({fetchImpl: fakeFetch([])});
  const b = createBridge({collect: async () => normalize(catalog, usage), hud: '<body>HUD</body>', adapter: '', chat, chatAddon: '/*chat*/', pairCode: 'pair-secret'});
  const base = 'http://127.0.0.1:' + await b.listen();
  try {
    const post = (headers = {}, payload = body()) => fetch(base + '/api/chat', {method: 'POST', headers: {'Content-Type': 'application/json', ...headers}, body: payload});
    assert.equal((await post({Origin: base})).status, 401);
    const pair = await fetch(base + '/pair', {method: 'POST', headers: {Origin: base}, body: '{"code":"pair-secret"}'});
    const cookie = pair.headers.get('set-cookie').split(';')[0];
    assert.equal((await fetch(base + '/hud-chat.js')).status, 401);
    assert.equal(await (await fetch(base + '/hud-chat.js', {headers: {Cookie: cookie}})).text(), '/*chat*/');
    assert((await (await fetch(base + '/', {headers: {Cookie: cookie}})).text()).includes('/hud-chat.js'));
    assert.equal((await post({Cookie: cookie})).status, 403, 'no Origin header');
    assert.equal((await post({Cookie: cookie, Origin: 'https://evil.example'})).status, 403);
    assert.equal((await fetch(base + '/api/chat', {method: 'POST', headers: {Cookie: cookie, Origin: base, 'Content-Type': 'text/plain'}, body: body()})).status, 415);
    assert.equal((await post({Cookie: cookie, Origin: base}, 'x'.repeat(CHAT_LIMITS.bodyBytes + 10))).status, 413);
    assert.equal((await post({Cookie: cookie, Origin: base}, body({model: 'openrouter/auto'}))).status, 400);
    const ok = await post({Cookie: cookie, Origin: base});
    assert.equal(ok.status, 200); assert.match(ok.headers.get('content-type'), /event-stream/);
    assert.match(await ok.text(), /"content":"ok"/);
    assert.equal((await fetch(base + '/api/chat/models', {headers: {Cookie: cookie}})).status, 200);
    assert.equal((await fetch(base + '/api/chat', {headers: {Cookie: cookie}})).status, 404, 'GET on chat is not a route');
  } finally { b.server.close(); }
});

test('bridge without chat keeps POST closed', async () => {
  const b = createBridge({collect: async () => ({}), hud: '<body></body>', adapter: '', pairCode: 'p'});
  const base = 'http://127.0.0.1:' + await b.listen();
  try {
    const pair = await fetch(base + '/pair', {method: 'POST', headers: {Origin: base}, body: '{"code":"p"}'});
    const cookie = pair.headers.get('set-cookie').split(';')[0];
    assert.equal((await fetch(base + '/api/chat', {method: 'POST', headers: {Cookie: cookie, Origin: base, 'Content-Type': 'application/json'}, body: body()})).status, 405);
  } finally { b.server.close(); }
});
