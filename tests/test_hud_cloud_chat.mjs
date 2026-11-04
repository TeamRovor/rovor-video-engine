import {test} from 'node:test';
import assert from 'node:assert/strict';
import {handle} from '../integrations/hud-cloud/worker.mjs';

const READER = 'r'.repeat(48), WRITER = 'w'.repeat(48);
const stream = text => new ReadableStream({start(c) { c.enqueue(new TextEncoder().encode(text)); c.close(); }});
const env = (ai = {run: async () => stream('data: {"response":"Hel"}\n\ndata: {"response":"lo"}\n\ndata: [DONE]\n\n')}) =>
  ({HUD_READER_TOKEN: READER, HUD_WRITER_TOKEN: WRITER, AI: ai, DB: {prepare: () => ({bind: () => ({first: async () => null})})}});
const post = (body, headers = {}) => new Request('https://hud.test/api/chat', {method: 'POST',
  headers: {'Content-Type': 'application/json', Origin: 'https://hud.test', Cookie: 'rovor_hud_reader=' + READER, ...headers}, body: JSON.stringify(body)});

test('chat requires reader auth and same origin', async () => {
  const body = {model: '@cf/meta/llama-3.1-8b-instruct', messages: [{role: 'user', content: 'hi'}]};
  assert.equal((await handle(post(body, {Cookie: ''}), env())).status, 401);
  assert.equal((await handle(post(body, {Origin: 'https://evil.test'}), env())).status, 403);
});

test('chat only allows listed models', async () => {
  const res = await handle(post({model: 'other', messages: [{role: 'user', content: 'hi'}]}), env());
  assert.equal(res.status, 400);
});

test('chat streams OpenAI-style deltas the HUD client understands', async () => {
  const res = await handle(post({model: '@cf/meta/llama-3.1-8b-instruct', context: true, messages: [{role: 'user', content: 'hi'}]}), env());
  assert.equal(res.status, 200);
  const text = await res.text();
  assert.match(text, /"content":"Hel"/);
  assert.match(text, /"content":"lo"/);
});

test('model list is served to the reader', async () => {
  const res = await handle(new Request('https://hud.test/api/chat/models', {headers: {Cookie: 'rovor_hud_reader=' + READER}}), env());
  assert.equal(res.status, 200);
  assert.ok((await res.json()).models.length >= 3);
});
