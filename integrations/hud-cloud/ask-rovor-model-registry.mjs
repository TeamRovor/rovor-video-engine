/**
 * Ask ROVOR 2.0 — private, read-only model intelligence contract.
 *
 * This module makes NO network requests, model calls, provider reservations,
 * GitHub writes, STOP changes or claims of live inference. A trusted server must
 * obtain and authenticate private admission/quota/canary evidence before calling
 * it. Browser/model-supplied JSON is NEVER eligibility evidence.
 */
export const REGISTRY_SCHEMA_VERSION = 1;
export const PROVIDER_IDS = Object.freeze([
  'gemini', 'groq', 'mistral', 'nvidia', 'openrouter',
  'cohere', 'sambanova', 'cloudflare-ai', 'huggingface',
]);
export const TASK_FAMILIES = Object.freeze([
  'general', 'classification', 'code', 'reasoning', 'research',
  'creative', 'retrieval', 'multimodal', 'operations',
]);
export const REGISTRY_LIMITS = Object.freeze({
  catalogAgeMs: 30 * 60_000,
  eligibilityAgeMs: 24 * 60 * 60_000,
  canaryAgeMs: 24 * 60 * 60_000,
  quotaAgeMs: 5 * 60_000,
  reviewAgeMs: 30 * 24 * 60 * 60_000,
  minQualitySamples: 5,
  maxModelsPerProvider: 150,
  maxReviews: 2_000,
});
const PROVIDER_SET = new Set(PROVIDER_IDS);
const TASK_SET = new Set(TASK_FAMILIES);
const MODEL_ID = /^[A-Za-z0-9@][A-Za-z0-9._:/+@-]{0,199}$/;
const RECEIPT_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{7,119}$/;
const QUOTA_SCOPES = new Set(['account_model', 'project_model', 'organization_model']);
const validTime = value => Number.isSafeInteger(value) && value > 0;
const fresh = (at, now, maxAge) => validTime(at) && at <= now && now - at <= maxAge;
const safeID = id => typeof id === 'string' && MODEL_ID.test(id);
const keyFor = (provider, modelId) => JSON.stringify([provider, modelId]);
const scoreKey = (provider, id, task) => JSON.stringify([provider, id, task]);

// Editorial *hypotheses* keyed by exact provider/model IDs observed in the
// inventory audit. They are not benchmarks or permission to use those models.
// Unlisted models remain representable and can become eligible after evidence.
export const ADVISORY_CAPABILITIES = Object.freeze({
  gemini: Object.freeze({
    'models/gemini-3.1-flash-lite': ['classification', 'general', 'operations'],
    'models/gemini-2.5-flash': ['general', 'reasoning', 'research', 'creative'],
    'models/gemini-3.1-pro-preview': ['reasoning', 'research', 'code'],
  }),
  groq: Object.freeze({
    'openai/gpt-oss-20b': ['classification', 'general', 'operations', 'code'],
    'openai/gpt-oss-120b': ['reasoning', 'code', 'research'],
    'qwen/qwen3.8-27b': ['code', 'reasoning'],
  }),
  mistral: Object.freeze({
    'codestral-latest': ['code'],
    'mistral-large-4': ['reasoning', 'research', 'code'],
    'ministral-14b-latest': ['classification', 'general'],
  }),
  nvidia: Object.freeze({
    'deepseek-ai/deepseek-v4.1-flash': ['code', 'reasoning'],
    'google/gemma-4-31b-it': ['general', 'creative'],
  }),
  openrouter: Object.freeze({
    'cohere/north-mini-code:free': ['code'],
    'nvidia/nemotron-3-ultra-550b-a55b:free': ['reasoning', 'research', 'code'],
    'nvidia/nemotron-3.5-super-vl:free': ['multimodal', 'reasoning'],
    'nvidia/nemotron-3.5-lightning:free': ['classification', 'general'],
  }),
  cohere: Object.freeze({
    'command-a-plus-05-2026': ['retrieval', 'research', 'reasoning'],
    'command-r7b-12-2024': ['retrieval', 'classification'],
  }),
  sambanova: Object.freeze({
    'GLM-5.3': ['reasoning', 'code'],
    'MiniMax-M3.1-Flash': ['general', 'reasoning'],
    'gpt-oss-120b': ['reasoning', 'code'],
  }),
  'cloudflare-ai': Object.freeze({
    '@cf/meta/llama-3.1-8b-instruct': ['classification', 'general'],
  }),
  huggingface: Object.freeze({
    'Qwen/Qwen3.8-27B': ['code', 'reasoning'],
    'deepseek-ai/DeepSeek-V4.1-Flash': ['code', 'reasoning'],
  }),
});

/**
 * Strict, bounded intent envelope returned by a future first-pass LLM.
 * Does not contain authority to call any provider or execute any tool.
 */
export function validateDispatcherIntent(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input) ||
      Object.keys(input).sort().join(',') !== 'complexity,needs_review,schema_version,task_family')
    throw Error('intent_shape_invalid');
  if (input.schema_version !== 1 || !TASK_SET.has(input.task_family) ||
      !['simple', 'moderate', 'complex'].includes(input.complexity) ||
      typeof input.needs_review !== 'boolean') throw Error('intent_values_invalid');
  return Object.freeze({
    schema_version: 1, task_family: input.task_family,
    complexity: input.complexity, needs_review: input.needs_review,
  });
}

function proofFailure(admission, id, now) {
  if (!admission) return 'no_private_admission';
  if (admission.stop_requested !== false) return 'stop_or_state_unknown';
  if (admission.dispatch_enabled !== true) return 'dispatch_disabled';
  const b = admission.zero_cost;
  if (!b || b.verified !== true || !RECEIPT_ID.test(b.evidence_ref ?? '') ||
      !fresh(b.verified_at_ms, now, REGISTRY_LIMITS.eligibilityAgeMs) ||
      !validTime(b.valid_until_ms) || b.valid_until_ms <= now ||
      b.valid_until_ms - b.verified_at_ms > REGISTRY_LIMITS.eligibilityAgeMs)
    return 'zero_cost_unverified_or_expired';
  const canary = admission.canary;
  if (!canary || canary.status !== 'verified_success' ||
      canary.resolved_model_id !== id ||
      !fresh(canary.completed_at_ms, now, REGISTRY_LIMITS.canaryAgeMs))
    return 'canary_not_verified_for_exact_model';
  const quota = admission.quota;
  if (!quota || quota.status !== 'verified_available' ||
      !QUOTA_SCOPES.has(quota.scope) ||
      !Number.isSafeInteger(quota.remaining_requests) || quota.remaining_requests <= 0 ||
      !fresh(quota.observed_at_ms, now, REGISTRY_LIMITS.quotaAgeMs) ||
      !validTime(quota.reset_at_ms) || quota.reset_at_ms <= now)
    return 'quota_unknown_stale_or_exhausted';
  if (admission.cooldown_until_ms != null &&
      (!Number.isSafeInteger(admission.cooldown_until_ms) || admission.cooldown_until_ms > now))
    return 'cooldown_active_or_unknown';
  return null;
}

/**
 * Pure snapshot. `catalogs`, `admissions` and `reviews` MUST be sourced by a
 * trusted authenticated server, NOT a browser or the first-pass LLM.
 * Extra upstream properties (including secrets) are discarded.
 */
export function createModelRegistry({catalogs = [], admissions = [], reviews = [], now_ms = Date.now()} = {}) {
  if (!validTime(now_ms) || !Array.isArray(catalogs) || !Array.isArray(admissions) ||
      !Array.isArray(reviews) || catalogs.length > 9 || admissions.length > 1_350 ||
      reviews.length > REGISTRY_LIMITS.maxReviews) throw Error('registry_input_invalid');

  const catalogMap = new Map();
  for (const catalog of catalogs) {
    if (!catalog || !PROVIDER_SET.has(catalog.provider) || catalogMap.has(catalog.provider) ||
        !Array.isArray(catalog.models) || catalog.models.length > REGISTRY_LIMITS.maxModelsPerProvider)
      throw Error('catalog_invalid');
    catalogMap.set(catalog.provider, catalog);
  }
  const evidence = new Map(), conflicts = new Set();
  for (const item of admissions) {
    if (!item || !PROVIDER_SET.has(item.provider) || !safeID(item.model_id))
      throw Error('admission_invalid');
    const key = keyFor(item.provider, item.model_id);
    if (evidence.has(key)) conflicts.add(key);
    else evidence.set(key, item);
  }

  const feedback = new Map(), receiptIds = new Set();
  for (const review of reviews) {
    if (!review || !PROVIDER_SET.has(review.provider) || !safeID(review.model_id) ||
        !TASK_SET.has(review.task_family) || !['accepted', 'rejected'].includes(review.outcome) ||
        !RECEIPT_ID.test(review.receipt_ref ?? '') ||
        !fresh(review.finished_at_ms, now_ms, REGISTRY_LIMITS.reviewAgeMs) ||
        receiptIds.has(review.receipt_ref)) continue;
    receiptIds.add(review.receipt_ref);
    const k = scoreKey(review.provider, review.model_id, review.task_family);
    const old = feedback.get(k) || {accepted: 0, rejected: 0};
    old[review.outcome]++;
    feedback.set(k, old);
  }

  const providers = PROVIDER_IDS.map(provider => {
    const catalog = catalogMap.get(provider);
    const catalogFresh = catalog && fresh(catalog.observed_at_ms, now_ms, REGISTRY_LIMITS.catalogAgeMs);
    const ids = new Set(), models = [];
    for (const source of catalog?.models || []) {
      const id = source?.id;
      if (!safeID(id) || ids.has(id)) continue;
      ids.add(id);
      const key = keyFor(provider, id);
      const admission = evidence.get(key);
      const blocked_reason = !catalogFresh ? 'catalog_stale_or_unavailable' :
        conflicts.has(key) ? 'conflicting_private_admission' : proofFailure(admission, id, now_ms);
      const byTask = {};
      for (const task of TASK_FAMILIES) {
        const observed = feedback.get(scoreKey(provider, id, task));
        if (observed) {
          const samples = observed.accepted + observed.rejected;
          byTask[task] = {samples, accepted: observed.accepted,
            accepted_rate: samples >= REGISTRY_LIMITS.minQualitySamples ? observed.accepted / samples : null};
        }
      }
      models.push({provider, id,
        context_length: Number.isSafeInteger(source?.context_length) && source.context_length > 0 &&
          source.context_length <= 10_000_000 ? source.context_length : null,
        advisory_task_families: Object.hasOwn(ADVISORY_CAPABILITIES[provider], id)
          ? [...ADVISORY_CAPABILITIES[provider][id]] : [],
        measured_quality_by_task: byTask,
        selectable: blocked_reason === null,
        blocked_reason,
        quota_scope: blocked_reason === null ? admission.quota.scope : null,
        quota_remaining_requests: blocked_reason === null ? admission.quota.remaining_requests : null,
        quota_reset_at_ms: blocked_reason === null ? admission.quota.reset_at_ms : null,
      });
    }
    return {provider, catalog_status: !catalog ? 'unavailable' : catalogFresh ? 'recent' : 'stale',
      models, eligible_count: models.filter(m => m.selectable).length};
  });
  return {schema_version: REGISTRY_SCHEMA_VERSION, generated_at_ms: now_ms,
    source: 'trusted_private_inputs_required', providers,
    counts: {providers: providers.length, models: providers.reduce((n,p) => n+p.models.length,0),
      eligible_models: providers.reduce((n,p) => n+p.eligible_count,0)}};
}

/**
 * Deterministic policy-constrained recommendation — never an invocation.
 * A manual model request is exact and never silently substituted. No rotation.
 */
export function selectModelRoutes(registry, {
  task_family, manual = null, allow_second_model_review = false,
} = {}) {
  if (!registry || registry.schema_version !== REGISTRY_SCHEMA_VERSION ||
      !Array.isArray(registry.providers) || !TASK_SET.has(task_family) ||
      typeof allow_second_model_review !== 'boolean')
    return {status: 'blocked', reason: 'selection_input_invalid', routes: []};
  const all = registry.providers.flatMap(p => Array.isArray(p.models) ? p.models : []);
  if (manual !== null) {
    if (!manual || !PROVIDER_SET.has(manual.provider) || !safeID(manual.model_id))
      return {status: 'blocked', reason: 'manual_model_invalid', routes: []};
    const match = all.find(m => m.provider === manual.provider && m.id === manual.model_id);
    if (!match || !match.selectable)
      return {status: 'blocked', reason: match?.blocked_reason || 'manual_model_unavailable', routes: []};
    return {status: 'ready', reason: 'exact_manual_selection', routes: [{provider: match.provider, model_id: match.id}]};
  }
  const eligible = all.filter(m => m.selectable);
  if (!eligible.length) return {status: 'blocked', reason: 'no_verified_eligible_models', routes: []};
  // Catalog presence does not establish task capability. Avoid choosing a
  // random eligible model when no exact-ID or measured fit exists.
  const quality = model => model.measured_quality_by_task?.[task_family]?.accepted_rate ?? null;
  const advisory = model => model.advisory_task_families.includes(task_family);
  const candidates = eligible.filter(m => advisory(m) || (quality(m) !== null && quality(m) > 0));
  if (!candidates.length) return {status: 'blocked', reason: 'no_task_capable_eligible_models', routes: []};
  const rank = model => {
    const q = quality(model);
    // Current owner-reviewed PASS/FAIL evidence can correct weak editorial
    // task-fit hypotheses; no self-reported model-quality percentages.
    return (advisory(model) ? 1 : 0) + (q === null ? 0 : 2 * (q - 0.5));
  };
  candidates.sort((a,b) => rank(b)-rank(a) ||
    a.provider.localeCompare(b.provider) || a.id.localeCompare(b.id));
  const chosen = [candidates[0]];
  if (allow_second_model_review) {
    const second = candidates.find(m => m.provider !== chosen[0].provider);
    if (second) chosen.push(second);
  }
  return {status: 'ready', reason: 'verified_eligibility_then_task_fit_and_owner_review',
    routes: chosen.map(m => ({provider: m.provider, model_id: m.id}))};
}
