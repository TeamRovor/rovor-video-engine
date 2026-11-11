import test from 'node:test';
import assert from 'node:assert/strict';
import {
  REGISTRY_SCHEMA_VERSION, PROVIDER_IDS, TASK_FAMILIES,
  createModelRegistry, selectModelRoutes, validateDispatcherIntent,
} from '../integrations/hud-cloud/ask-rovor-model-registry.mjs';

const NOW = Date.parse('2026-11-09T09:30:00.000Z');
const model = (provider, id, context_length = 131072) => ({provider, id, context_length});
const GEMINI = model('gemini', 'models/gemini-3.1-flash-lite');
const GROQ = model('groq', 'openai/gpt-oss-20b');
const OPENROUTER = model('openrouter', 'cohere/north-mini-code:free');
const catalog = (m, at = NOW-1000) => ({provider: m.provider, observed_at_ms: at,
  models: [{id: m.id, context_length: m.context_length, api_key: 'DONT_LEAK'}]});
const admission = (m, extra = {}) => ({
  provider: m.provider, model_id: m.id, dispatch_enabled: true, stop_requested: false,
  zero_cost: {verified: true, evidence_ref: 'private-proof-20261109',
    verified_at_ms: NOW - 60_000, valid_until_ms: NOW + 60_000},
  canary: {status: 'verified_success', resolved_model_id: m.id, completed_at_ms: NOW - 60_000},
  quota: {status: 'verified_available', scope: 'project_model', remaining_requests: 10,
    observed_at_ms: NOW - 20_000, reset_at_ms: NOW + 120_000},
  cooldown_until_ms: 0, ...extra,
});
const snapshot = (catalogs = [], admissions = [], reviews = []) =>
  createModelRegistry({catalogs, admissions, reviews, now_ms: NOW});
const entry = (registry, provider, id) =>
  registry.providers.find(p => p.provider === provider)?.models.find(m => m.id === id);
const reviewed = (m, task, outcome, n) => ({
  provider: m.provider, model_id: m.id, task_family: task, outcome,
  receipt_ref: `private-review-${m.provider}-${outcome}-${n}`, finished_at_ms: NOW - 100_000,
});

test('all nine slots are always present, while an empty catalog proves nothing', () => {
  const r = snapshot();
  assert.equal(r.schema_version, REGISTRY_SCHEMA_VERSION);
  assert.deepEqual(r.providers.map(x => x.provider), PROVIDER_IDS);
  assert.equal(r.counts.models, 0);
  assert.equal(r.counts.eligible_models, 0);
  assert(r.providers.every(x => x.catalog_status === 'unavailable'));
  assert.equal(selectModelRoutes(r, {task_family: 'code'}).reason, 'no_verified_eligible_models');
});

test('catalog discovery and model :free suffix cannot grant permission or quota', () => {
  const r = snapshot([catalog(OPENROUTER), catalog(GROQ)]);
  assert.equal(entry(r, OPENROUTER.provider, OPENROUTER.id).blocked_reason, 'no_private_admission');
  assert.equal(entry(r, GROQ.provider, GROQ.id).selectable, false);
  assert.equal(r.counts.eligible_models, 0);
});

test('a fully current privately supplied evidence packet can mark an exact model selectable', () => {
  const r = snapshot([catalog(GEMINI)], [admission(GEMINI)]);
  const chosen = selectModelRoutes(r, {task_family: 'classification'});
  assert.equal(chosen.status, 'ready');
  assert.deepEqual(chosen.routes, [{provider: GEMINI.provider, model_id: GEMINI.id}]);
  assert.equal(entry(r, GEMINI.provider, GEMINI.id).quota_scope, 'project_model');
  assert.equal(entry(r, GEMINI.provider, GEMINI.id).quota_remaining_requests, 10);
});

test('untrusted upstream catalog fields are never reflected in registry output', () => {
  const r = snapshot([catalog(GROQ)], [admission(GROQ)]);
  assert(!JSON.stringify(r).includes('DONT_LEAK'));
  assert(!JSON.stringify(r).includes('private-proof-20261109'));
  assert.equal(entry(r, GROQ.provider, GROQ.id).context_length, 131072);
});

test('expired catalogs and missing or future timestamps fail closed', () => {
  const stale = snapshot([catalog(GROQ, NOW - 31 * 60_000)], [admission(GROQ)]);
  assert.equal(entry(stale, GROQ.provider, GROQ.id).blocked_reason, 'catalog_stale_or_unavailable');
  const future = snapshot([catalog(GROQ, NOW + 1000)], [admission(GROQ)]);
  assert.equal(entry(future, GROQ.provider, GROQ.id).selectable, false);
});

test('STOP unknown, STOP asserted and dispatch disabled all prevent selection', () => {
  for (const [changes, expected] of [
    [{stop_requested: undefined}, 'stop_or_state_unknown'],
    [{stop_requested: true}, 'stop_or_state_unknown'],
    [{dispatch_enabled: false}, 'dispatch_disabled'],
  ]) {
    const r = snapshot([catalog(GROQ)], [admission(GROQ, changes)]);
    assert.equal(entry(r, GROQ.provider, GROQ.id).blocked_reason, expected);
  }
});

test('billing proof needs a private reference, current verification and short-lived expiry', () => {
  const original = admission(GROQ).zero_cost;
  for (const zero_cost of [
    {...original, verified: false},
    {...original, evidence_ref: 'x'},
    {...original, valid_until_ms: NOW - 1},
    {...original, verified_at_ms: NOW + 1000},
    {...original, valid_until_ms: NOW + 48 * 60 * 60_000},
  ]) {
    const r = snapshot([catalog(GROQ)], [admission(GROQ, {zero_cost})]);
    assert.equal(entry(r, GROQ.provider, GROQ.id).blocked_reason, 'zero_cost_unverified_or_expired');
  }
});

test('canary has to attest the same exact model and be recent', () => {
  for (const canary of [
    {status: 'verified_success', resolved_model_id: 'other-model', completed_at_ms: NOW - 100},
    {status: 'failed', resolved_model_id: GROQ.id, completed_at_ms: NOW - 100},
    {status: 'verified_success', resolved_model_id: GROQ.id, completed_at_ms: NOW - 30 * 60 * 60_000},
  ]) {
    const r = snapshot([catalog(GROQ)], [admission(GROQ, {canary})]);
    assert.equal(entry(r, GROQ.provider, GROQ.id).blocked_reason, 'canary_not_verified_for_exact_model');
  }
});

test('quota must be actual, current, scoped, positive and not past reset', () => {
  const original = admission(GROQ).quota;
  for (const quota of [
    {...original, status: 'unknown'},
    {...original, scope: 'unknown'},
    {...original, remaining_requests: 0},
    {...original, remaining_requests: null},
    {...original, observed_at_ms: NOW - 6 * 60_000},
    {...original, reset_at_ms: NOW},
  ]) {
    const r = snapshot([catalog(GROQ)], [admission(GROQ, {quota})]);
    assert.equal(entry(r, GROQ.provider, GROQ.id).blocked_reason, 'quota_unknown_stale_or_exhausted');
    assert.equal(entry(r, GROQ.provider, GROQ.id).quota_remaining_requests, null);
  }
});

test('provider cooldown blocks even with other current evidence', () => {
  const r = snapshot([catalog(GROQ)], [admission(GROQ, {cooldown_until_ms: NOW + 500})]);
  assert.equal(entry(r, GROQ.provider, GROQ.id).blocked_reason, 'cooldown_active_or_unknown');
});

test('duplicate private admissions block rather than take an arbitrary first or last proof', () => {
  const r = snapshot([catalog(GROQ)], [admission(GROQ), admission(GROQ)]);
  assert.equal(entry(r, GROQ.provider, GROQ.id).blocked_reason, 'conflicting_private_admission');
});

test('moving model aliases never pass an otherwise complete private admission', () => {
  for (const m of [
    model('mistral','codestral-latest'),
    model('gemini','models/gemini-flash-latest'),
    model('groq','openai/gpt-oss-auto'),
    model('huggingface','Qwen/Qwen3.8-27B:auto'),
  ]) {
    const r = snapshot([catalog(m)], [admission(m)]);
    assert.equal(entry(r,m.provider,m.id).blocked_reason,'unpinned_model_alias');
    assert.equal(selectModelRoutes(r,{task_family:'code',
      manual:{provider:m.provider,model_id:m.id}}).status,'blocked');
  }
});

test('OpenRouter must use the exact :free identity and Hugging Face needs a pinned upstream', () => {
  const paid = model('openrouter','cohere/north-mini-code');
  const free = model('openrouter','cohere/north-mini-code:free');
  const automatic = model('huggingface','Qwen/Qwen3.8-27B');
  const pinned = model('huggingface','Qwen/Qwen3.8-27B:provider-a');
  const r = snapshot([catalog(paid),catalog(automatic)],
    [admission(paid),admission(automatic)]);
  assert.equal(entry(r,paid.provider,paid.id).blocked_reason,'openrouter_free_route_required');
  assert.equal(entry(r,automatic.provider,automatic.id).blocked_reason,'huggingface_upstream_required');
  const allowed=snapshot([catalog(free),catalog(pinned)],[admission(free),admission(pinned)]);
  assert.equal(entry(allowed,free.provider,free.id).selectable,true);
  assert.equal(entry(allowed,pinned.provider,pinned.id).selectable,true);
});

test('manual exact model selection never silently substitutes a different model', () => {
  const r = snapshot([catalog(GROQ), catalog(OPENROUTER)], [admission(GROQ)]);
  const picked = selectModelRoutes(r, {task_family:'code', manual:{provider:OPENROUTER.provider,model_id:OPENROUTER.id}});
  assert.equal(picked.status, 'blocked');
  assert.equal(picked.reason, 'no_private_admission');
  assert.deepEqual(picked.routes, []);
  assert.equal(selectModelRoutes(r, {task_family:'code', manual:{provider:GROQ.provider,model_id:GROQ.id}}).routes.length,1);
});

test('optional second-model review chooses a different provider, never uncontrolled fanout', () => {
  const r = snapshot([catalog(GEMINI), catalog(GROQ), catalog(OPENROUTER)],
    [admission(GEMINI), admission(GROQ), admission(OPENROUTER)]);
  const one = selectModelRoutes(r, {task_family:'classification'});
  assert.equal(one.routes.length, 1);
  const two = selectModelRoutes(r, {task_family:'classification',allow_second_model_review:true});
  assert.equal(two.routes.length, 2);
  assert.notEqual(two.routes[0].provider,two.routes[1].provider);
});

test('measured quality is reported only after five unique owner-review receipts', () => {
  const groqReviews = Array.from({length: 4}, (_,i) => reviewed(GROQ, 'classification', 'accepted', i));
  const r1 = snapshot([catalog(GROQ)], [admission(GROQ)], groqReviews);
  assert.equal(entry(r1, GROQ.provider, GROQ.id).measured_quality_by_task.classification.accepted_rate, null);
  const r2 = snapshot([catalog(GROQ)], [admission(GROQ)], [...groqReviews, groqReviews[0], reviewed(GROQ,'classification','rejected',5)]);
  assert.equal(entry(r2, GROQ.provider, GROQ.id).measured_quality_by_task.classification.samples, 5);
  assert.equal(entry(r2, GROQ.provider, GROQ.id).measured_quality_by_task.classification.accepted_rate, 0.8);
});

test('within the same task capability, measured PASS/FAIL evidence can affect selection', () => {
  const feedback = [
    ...Array.from({length:5},(_,i)=>reviewed(GROQ,'classification','accepted',i)),
    ...Array.from({length:5},(_,i)=>reviewed(GEMINI,'classification','rejected',i)),
  ];
  const r = snapshot([catalog(GEMINI),catalog(GROQ)], [admission(GEMINI),admission(GROQ)], feedback);
  const picked = selectModelRoutes(r,{task_family:'classification'});
  assert.equal(picked.routes[0].provider,'groq');
});

test('malformed, oversized and duplicate catalogs are rejected', () => {
  assert.throws(()=>snapshot([catalog(GROQ),catalog(GROQ)]),/catalog_invalid/);
  assert.throws(()=>snapshot([{provider:'untrusted',models:[]}]),/catalog_invalid/);
  assert.throws(()=>snapshot([{provider:'groq',models:Array(151).fill({id:GROQ.id})}]),/catalog_invalid/);
  assert.throws(()=>snapshot([catalog(GROQ)], [{provider:'groq',model_id:'../unsafe'}]),/admission_invalid/);
  assert.equal(snapshot([{provider:'groq',models:[{id:'bad\nmodel'}]}]).counts.models, 0);
});

test('future dispatcher intent is strict and cannot inject tools, keys or model calls', () => {
  const valid = {schema_version:1,task_family:'code',complexity:'complex',needs_review:true};
  assert.deepEqual(validateDispatcherIntent(valid),valid);
  assert(TASK_FAMILIES.includes('code'));
  for (const invalid of [
    {...valid,tool_call:'git push --force'},
    {...valid,model:'paid-model'},
    {...valid,task_family:'run_shell'},
    {...valid,complexity:'critical!'},
    {...valid,needs_review:'yes'},
    [], null,
  ]) assert.throws(()=>validateDispatcherIntent(invalid),/intent_/);
});

test('invalid task and selector shape fail without an inference call', () => {
  const r = snapshot([catalog(GROQ)], [admission(GROQ)]);
  assert.equal(selectModelRoutes(r,{task_family:'execute-shell'}).status,'blocked');
  assert.equal(selectModelRoutes(r,{task_family:'code',allow_second_model_review:'true'}).status,'blocked');
});

test('prototype-like model names never inherit Object prototype capabilities', () => {
  const r = snapshot([{provider:'groq',observed_at_ms:NOW-1000,
    models:[{id:'constructor'},{id:'toString'},{id:'__proto__'}]}]);
  const found = r.providers.find(p=>p.provider==='groq').models;
  assert.equal(found.length,2,'invalid underscore-prefixed ID discarded');
  assert(found.every(m => m.advisory_task_families.length===0 && !m.selectable));
});

test('automatic routing refuses an unrelated specialist even when its billing is verified', () => {
  const r = snapshot([catalog(GROQ)],[admission(GROQ)]);
  assert.equal(selectModelRoutes(r,{task_family:'multimodal'}).reason,'no_task_capable_eligible_models');
  assert.equal(selectModelRoutes(r,{task_family:'retrieval',allow_second_model_review:true}).routes.length,0);
  assert.equal(selectModelRoutes(r,{task_family:'classification'}).status,'ready');
});

test('second-model review selects only independently eligible specialists for the task', () => {
  const r = snapshot([catalog(GROQ),catalog(OPENROUTER)], [admission(GROQ),admission(OPENROUTER)]);
  const plan = selectModelRoutes(r,{task_family:'classification',allow_second_model_review:true});
  assert.equal(plan.status,'ready');
  assert.deepEqual(plan.routes,[{provider:'groq',model_id:'openai/gpt-oss-20b'}]);
});

test('multiple owner-review rejections can override an initial weak capability preference', () => {
  const failures = Array.from({length:5},(_,i)=>reviewed(GROQ,'classification','rejected',i));
  const r = snapshot([catalog(GROQ),catalog(GEMINI)], [admission(GROQ),admission(GEMINI)], failures);
  assert.equal(selectModelRoutes(r,{task_family:'classification'}).routes[0].provider,'gemini');
});
