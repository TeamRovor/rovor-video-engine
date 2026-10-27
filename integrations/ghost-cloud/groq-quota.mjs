/** Parse Groq's authenticated response headers as RPD evidence only.
 * This is not proof of free billing, commercial rights, or current inference.
 */
export function readGroqRpd(headers, observedAt = Date.now()) {
  if (!headers || typeof headers.get !== 'function' ||
      !Number.isSafeInteger(observedAt) || observedAt <= 0) return null;
  const integer = key => {
    const text = headers.get(key);
    return typeof text === 'string' && /^(0|[1-9][0-9]{0,8})$/.test(text)
      ? Number(text) : null;
  };
  const limit = integer('x-ratelimit-limit-requests');
  const remaining = integer('x-ratelimit-remaining-requests');
  if (limit === null || limit < 1 || remaining === null || remaining > limit) return null;
  const reset = headers.get('x-ratelimit-reset-requests');
  if (typeof reset !== 'string' || reset.length > 48) return null;
  const multipliers = {d: 86400000, h: 3600000, m: 60000, s: 1000};
  const rank = {d: 4, h: 3, m: 2, s: 1};
  const chunks = /(\d+(?:\.\d+)?)([dhms])/g;
  let found, end = 0, lastRank = 5, milliseconds = 0;
  while ((found = chunks.exec(reset)) !== null) {
    if (found.index !== end || rank[found[2]] >= lastRank) return null;
    const part = Number(found[1]);
    if (!Number.isFinite(part)) return null;
    milliseconds += part * multipliers[found[2]];
    end = chunks.lastIndex;
    lastRank = rank[found[2]];
  }
  if (!end || end !== reset.length || milliseconds <= 0 ||
      milliseconds > 2 * 86400000 || !Number.isFinite(milliseconds)) return null;
  const resetsAt = observedAt + Math.ceil(milliseconds);
  if (!Number.isSafeInteger(resetsAt)) return null;
  return {
    unit: 'requests_per_day',
    used: limit - remaining,
    limit,
    remaining,
    resets_at: resetsAt,
    observed_at: observedAt,
    source: 'authenticated_groq_rpd_response_headers',
    scope: 'provider_account'
  };
}
