import test from 'node:test';
import assert from 'node:assert/strict';
import {evaluateAlerts, createNotifier} from '../tools/hud_alerts.mjs';

const data = {quota: {records: [{provider: 'groq', used_percent: 91, remaining: 9}, {provider: 'x', used_percent: 10, remaining: 90}]},
  workforce: {heartbeat: {available: true, recent: false}}};

test('alerts fire only for near-limit providers and stalled workers', () => {
  assert.deepEqual(evaluateAlerts(data).map(a => a.key), ['quota:groq:', 'workers:stalled']);
  assert.deepEqual(evaluateAlerts({}), []);
  assert.deepEqual(evaluateAlerts({workforce: {heartbeat: {available: false, recent: false}}}), []);
});

test('notifier respects cooldown, re-arms after recovery, retries after a failed send', async () => {
  let now = 0, fail = true; const sent = [];
  const run = createNotifier({clock: () => now, cooldownMs: 1000, notify: async a => { if (fail) throw Error('x'); sent.push(a.key); }});
  assert.deepEqual(await run(data), []); fail = false;
  assert.equal((await run(data)).length, 2);
  assert.equal((await run(data)).length, 0);
  await run({}); assert.equal((await run(data)).length, 2);
});
