// Trusted-host helper: turn separately verified private provider evidence into
// a bounded GHOST_FLEET_CONFIG. No network, credential export or auto-renewal.
import { PROVIDERS, eligibility } from './runtime.mjs';

const DAY = 86_400_000;
const SHA = /^[0-9a-f]{64}$/;
const MODEL = /^[a-zA-Z0-9@][a-zA-Z0-9_./:@-]{0,199}$/;
const POOL = /^[a-z0-9][a-z0-9-]{0,149}$/;
const ROLES = new Set(['Walter', 'Mike', 'Jane', 'Jesse', 'Gale', 'Gus', 'Saul', 'Hank']);
const KINDS = new Set(['checklist', 'plan', 'code_review', 'research']);
const integer = (n, max) => Number.isSafeInteger(n) && n > 0 && n <= max;
const timestamp = n => Number.isSafeInteger(n) && n > 0;
const validSet = (items, allowed) => Array.isArray(items) && items.length > 0 &&
  new Set(items).size === items.length && items.every(x => allowed.has(x));

function validateEvidence(provider, evidence, now) {
  if (!evidence || typeof evidence !== 'object' || Array.isArray(evidence)) return 'not_attested';
  const { model, pool, billing, quota, canary, limits } = evidence;
  if (evidence.operator_approved !== true || !billing || billing.zero_cost !== true ||
      billing.commercial_use !== true || !SHA.test(billing.sha256 || '') ||
      !timestamp(billing.checked_at) || billing.checked_at > now || now - billing.checked_at > DAY) return 'billing_unverified';
  if (typeof model !== 'string' || !MODEL.test(model) || /(^|[/:-])(auto|latest)([/:-]|$)/i.test(model) ||
      typeof pool !== 'string' || !POOL.test(pool)) return 'model_or_pool_unverified';
  if (provider === 'openrouter' && !model.endsWith(':free')) return 'paid_route_denied';
  if (provider === 'huggingface' && !/:[a-z0-9-]+$/.test(model)) return 'unpinned_upstream';
  if (!quota || !SHA.test(quota.sha256 || '') || !timestamp(quota.checked_at) ||
      quota.checked_at > now || now - quota.checked_at > DAY ||
      !integer(quota.requests_remaining, Number.MAX_SAFE_INTEGER) ||
      !integer(quota.tokens_remaining, Number.MAX_SAFE_INTEGER) ||
      !timestamp(quota.reset_at) || quota.reset_at <= now) return 'quota_unverified';
  if (!canary || canary.live_verified !== true || !SHA.test(canary.sha256 || '') ||
      !timestamp(canary.at) || canary.at < Math.max(billing.checked_at, quota.checked_at) ||
      canary.at > now || canary.requested_model !== model || canary.actual_model !== model ||
      canary.capability_verified !== true) return 'canary_unverified';
  if (!limits || !integer(limits.requests_per_day, 144) ||
      limits.requests_per_day > quota.requests_remaining ||
      !integer(limits.tokens_per_day, 10_000_000) || limits.tokens_per_day > quota.tokens_remaining ||
      !integer(limits.min_interval_ms, DAY) || !integer(limits.max_input_bytes, 14_500) ||
      !integer(limits.max_output_tokens, 2_400) ||
      !validSet(limits.roles, ROLES) || !validSet(limits.kinds, KINDS)) return 'invalid_or_excessive_limits';
  // A generic successful canary cannot authorize every workload kind. Each
  // enabled kind must be explicitly covered by this exact-model attestation.
  // verified_kinds is private operator evidence, not an inferred capability.
  if (!validSet(canary.verified_kinds, KINDS) ||
      !limits.kinds.every(kind => canary.verified_kinds.includes(kind))) return 'canary_scope_unverified';
  const verifiedAt = Math.max(billing.checked_at, quota.checked_at);
  if (now - verifiedAt > DAY || now >= Math.min(verifiedAt + DAY, quota.reset_at)) return 'eligibility_expired';
  return null;
}

// Input is a private, operator-approved record, NOT evidence that this function
// independently queried a vendor. Never copy this record into a public repo.
// The env object remains in trusted host memory; no key is included in the result.
export async function compileFleetConfig(attestations, env, now = Date.now()) {
  if (!timestamp(now) || !attestations || typeof attestations !== 'object' ||
      Array.isArray(attestations) || !env || typeof env !== 'object') throw Error('invalid_input');
  for (const provider of Object.keys(attestations)) {
    if (!Object.hasOwn(PROVIDERS, provider)) throw Error('unknown_provider');
  }
  const config = {}, states = {}, pools = new Map(), conflictedPools = new Set();
  for (const provider of Object.keys(PROVIDERS)) {
    const a = attestations[provider];
    const reason = validateEvidence(provider, a, now);
    if (reason) { config[provider] = { enabled: false }; states[provider] = reason; continue; }
    const verifiedAt = Math.max(a.billing.checked_at, a.quota.checked_at);
    const material = JSON.stringify([provider, a.model, a.pool, a.billing.sha256,
      a.quota.sha256, a.canary.sha256,
      [...a.canary.verified_kinds].sort(), [...a.limits.kinds].sort(),
      verifiedAt, a.quota.reset_at]);
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(material));
    const evidenceDigest = Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, '0')).join('');
    const cfg = {
      enabled: true, model: a.model, pool: a.pool,
      zero_cost: true, commercial_use: true,
      evidence_sha256: evidenceDigest, verified_at: verifiedAt,
      valid_until: Math.min(verifiedAt + DAY, a.quota.reset_at),
      canary_sha256: a.canary.sha256, canary_at: a.canary.at,
      requests_per_day: a.limits.requests_per_day,
      tokens_per_day: a.limits.tokens_per_day,
      min_interval_ms: a.limits.min_interval_ms,
      max_input_bytes: a.limits.max_input_bytes,
      max_output_tokens: a.limits.max_output_tokens,
      roles: [...a.limits.roles], kinds: [...a.limits.kinds],
    };
    const runtimeReason = eligibility(provider, cfg, env, now);
    if (runtimeReason) { config[provider] = { enabled: false }; states[provider] = runtimeReason; continue; }
    const fingerprint = JSON.stringify([
      cfg.requests_per_day, cfg.tokens_per_day, cfg.min_interval_ms,
      a.quota.sha256, a.quota.reset_at,
    ]);
    if (conflictedPools.has(cfg.pool) || (pools.has(cfg.pool) && pools.get(cfg.pool) !== fingerprint)) {
      conflictedPools.add(cfg.pool);
      // Refuse the whole inconsistent shared account, not just the second route.
      for (const [other, value] of Object.entries(config)) {
        if (value.pool === cfg.pool) { config[other] = { enabled: false }; states[other] = 'conflicting_pool_evidence'; }
      }
      config[provider] = { enabled: false }; states[provider] = 'conflicting_pool_evidence';
      continue;
    }
    pools.set(cfg.pool, fingerprint);
    config[provider] = cfg; states[provider] = 'operator_attested_eligible';
  }
  return { config, states };
}
