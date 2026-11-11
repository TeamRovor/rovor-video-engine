import test from 'node:test';
import assert from 'node:assert/strict';
import { compileFleetConfig } from '../integrations/ghost-cloud/eligibility-config.mjs';
import { PROVIDERS, eligibility } from '../integrations/ghost-cloud/runtime.mjs';
const NOW = 1_800_000_000_000;
const HEX = 'a'.repeat(64);
const env = Object.fromEntries(Object.entries(PROVIDERS).map(([p, [, k]]) => [k, p + '-secret-1234567890']));
env.CLOUDFLARE_ACCOUNT_ID = 'b'.repeat(32);
const sample = (provider = 'groq') => {
  const model = provider === 'openrouter' ? 'vendor/model:free' :
    provider === 'huggingface' ? 'vendor/model:upstream' : 'vendor/model';
  return {
    operator_approved: true, model, pool: provider + '-account',
    billing: { zero_cost: true, commercial_use: true, sha256: HEX, checked_at: NOW - 1000 },
    quota: { sha256: HEX, checked_at: NOW - 900, requests_remaining: 10, tokens_remaining: 50000, reset_at: NOW + 3600000 },
    canary: { live_verified: true, sha256: HEX, at: NOW - 500, requested_model: model, actual_model: model, capability_verified: true },
    limits: { requests_per_day: 8, tokens_per_day: 40000, min_interval_ms: 601000, max_input_bytes: 4000, max_output_tokens: 500, roles: ['Walter', 'Hank'], kinds: ['plan', 'code_review'] },
  };
};

test('all nine attestations compile to existing runtime-eligible bounded config', async () => {
  const all = Object.fromEntries(Object.keys(PROVIDERS).map(p => [p, sample(p)]));
  const { config, states } = await compileFleetConfig(all, env, NOW);
  assert.equal(Object.keys(config).length, 9);
  for (const p of Object.keys(PROVIDERS)) {
    assert.equal(states[p], 'operator_attested_eligible', p);
    assert.equal(eligibility(p, config[p], env, NOW), null, p);
    assert.equal(config[p].valid_until, NOW + 3600000);
    assert.equal(JSON.stringify(config[p]).includes('secret'), false);
  }
});
test('missing provider stays disabled; no nine-way inference implied', async () => {
  const { config, states } = await compileFleetConfig({ groq: sample() }, env, NOW);
  assert.equal(config.groq.enabled, true);
  assert.equal(config.gemini.enabled, false);
  assert.equal(states.gemini, 'not_attested');
});
test('unknown provider fails closed', async () => {
  await assert.rejects(compileFleetConfig({ unlisted: sample() }, env, NOW), /unknown_provider/);
});
test('billing or operator approval absent never enables', async () => {
  for (const mutate of [a => { a.operator_approved = false; }, a => { a.billing.zero_cost = false; }, a => { a.billing.commercial_use = false; }, a => { a.billing.sha256 = 'x'; }, a => { a.billing.checked_at = NOW - 86400001; }]) {
    const a = sample(); mutate(a);
    assert.equal((await compileFleetConfig({ groq: a }, env, NOW)).config.groq.enabled, false);
  }
});
test('quota missing, expired, exhausted or inflated never enables', async () => {
  for (const mutate of [a => { a.quota.checked_at = NOW - 86400001; }, a => { a.quota.requests_remaining = 0; }, a => { a.quota.tokens_remaining = 0; }, a => { a.limits.requests_per_day = 11; }, a => { a.limits.tokens_per_day = 50001; }, a => { a.quota.reset_at = NOW; }]) {
    const a = sample(); mutate(a);
    assert.equal((await compileFleetConfig({ groq: a }, env, NOW)).config.groq.enabled, false);
  }
});
test('canary must be live, newer, exact-model and capability-verified', async () => {
  for (const mutate of [a => { a.canary.live_verified = false; }, a => { a.canary.at = NOW - 5000; }, a => { a.canary.actual_model = 'other'; }, a => { a.canary.requested_model = 'other'; }, a => { a.canary.capability_verified = false; }]) {
    const a = sample(); mutate(a);
    assert.equal((await compileFleetConfig({ groq: a }, env, NOW)).config.groq.enabled, false);
  }
});
test('runtime rejects missing host secret and unpinned routes', async () => {
  const missing = { ...env }; delete missing.GROQ_API_KEY;
  assert.equal((await compileFleetConfig({ groq: sample() }, missing, NOW)).config.groq.enabled, false);
  const a = sample('openrouter'); a.model = 'vendor/paid'; a.canary.requested_model = a.canary.actual_model = a.model;
  assert.equal((await compileFleetConfig({ openrouter: a }, env, NOW)).config.openrouter.enabled, false);
  const h = sample('huggingface'); h.model = 'vendor/model'; h.canary.requested_model = h.canary.actual_model = h.model;
  assert.equal((await compileFleetConfig({ huggingface: h }, env, NOW)).config.huggingface.enabled, false);
});
test('shared pool conflicting quotas disables all routes', async () => {
  const a = sample('groq'), b = sample('gemini'), c = sample('mistral');
  b.pool = a.pool; b.quota.sha256 = 'b'.repeat(64); c.pool = a.pool;
  const { config, states } = await compileFleetConfig({ groq: a, gemini: b, mistral: c }, env, NOW);
  for (const p of ['groq', 'gemini', 'mistral']) {
    assert.equal(config[p].enabled, false);
    assert.equal(states[p], 'conflicting_pool_evidence');
  }
});
test('identical shared pool caps and evidence are allowed', async () => {
  const a = sample('groq'), b = sample('gemini'); b.pool = a.pool;
  const { config } = await compileFleetConfig({ groq: a, gemini: b }, env, NOW);
  assert.equal(config.groq.enabled, true); assert.equal(config.gemini.enabled, true);
});
test('invalid scope, stale evidence and future canary never enable', async () => {
  for (const mutate of [a => { a.limits.roles = ['Fake']; }, a => { a.limits.kinds = ['shell']; }, a => { a.canary.at = NOW + 1; }, a => { a.billing.checked_at = NOW + 1; }, a => { a.model = 'auto'; }]) {
    const a = sample(); mutate(a);
    assert.equal((await compileFleetConfig({ groq: a }, env, NOW)).config.groq.enabled, false);
  }
});

test('verified external allowance larger than local cap is safely bounded', async () => {
  const a = sample();
  a.quota.requests_remaining = 1000;
  a.quota.tokens_remaining = 20000000;
  const { config, states } = await compileFleetConfig({ groq: a }, env, NOW);
  assert.equal(states.groq, 'operator_attested_eligible');
  assert.equal(config.groq.requests_per_day, 8);
  assert.equal(config.groq.tokens_per_day, 40000);
});
