/** Aggregate durable OmniRoute call-log metadata. Never reads request bodies. */
export const HUD_PROVIDERS = ['gemini', 'groq', 'openrouter', 'mistral', 'cloudflare', 'cohere', 'nvidia', 'sambanova', 'huggingface'];
const aliases = new Map([
  ['google', 'gemini'], ['google-ai-studio', 'gemini'], ['google_ai_studio', 'gemini'],
  ['cloudflare-ai', 'cloudflare'], ['cloudflare_workers-ai', 'cloudflare'], ['cloudflare-workers-ai', 'cloudflare'], ['cloudflare_workers_ai', 'cloudflare'], ['cloudflareworkersai', 'cloudflare'],
  ['nvidia-nim', 'nvidia'], ['nvidia_nim', 'nvidia'], ['hugging-face', 'huggingface'], ['hugging_face', 'huggingface'],
]);
const safeText = x => typeof x === 'string' && x.length <= 200 && !/[\u0000-\u001f]/.test(x) ? x : null;
const integer = x => Number.isSafeInteger(x) && x >= 0 ? x : null;
const providerKey = value => {
  if (typeof value !== 'string') return null;
  const key = value.trim().toLowerCase();
  const normalized = aliases.get(key) || key;
  return HUD_PROVIDERS.includes(normalized) ? normalized : null;
};

function localDate(now, dayOffset = 0) {
  const parts = new Intl.DateTimeFormat('en-US', {timeZone: 'America/Los_Angeles', year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts(new Date(now));
  const fields = Object.fromEntries(parts.filter(p => p.type !== 'literal').map(p => [p.type, Number(p.value)]));
  const date = new Date(Date.UTC(fields.year, fields.month - 1, fields.day + dayOffset));
  return {year: date.getUTCFullYear(), month: date.getUTCMonth() + 1, day: date.getUTCDate()};
}

function pacificMidnight(now, dayOffset = 0) {
  const {year, month, day} = localDate(now, dayOffset);
  const target = Date.UTC(year, month - 1, day);
  let guess = target + 8 * 60 * 60 * 1000;
  const formatter = new Intl.DateTimeFormat('en-US', {timeZone: 'America/Los_Angeles', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'});
  for (let i = 0; i < 3; i++) {
    const fields = Object.fromEntries(formatter.formatToParts(new Date(guess)).filter(p => p.type !== 'literal').map(p => [p.type, Number(p.value)]));
    const represented = Date.UTC(fields.year, fields.month - 1, fields.day, fields.hour, fields.minute, fields.second);
    guess += target - represented;
  }
  return guess;
}

export function pacificDay(now = Date.now()) {
  return {start: pacificMidnight(now), reset: pacificMidnight(now, 1)};
}

function projectCallLog(row) {
  const id = safeText(row?.id);
  const timestamp = Date.parse(row?.createdAt ?? row?.timestamp ?? row?.ts ?? '');
  const provider = providerKey(row?.provider ?? row?.providerId);
  const model = safeText(row?.model ?? row?.modelId ?? row?.requested_model ?? row?.requestedModel);
  const status = integer(row?.status ?? row?.statusCode);
  if (!id || !Number.isFinite(timestamp) || !provider || status === null) return null;
  const input = integer(row?.tokens?.in ?? row?.tokensIn ?? row?.tokens_input ?? row?.promptTokens);
  const output = integer(row?.tokens?.out ?? row?.tokensOut ?? row?.tokens_output ?? row?.completionTokens);
  const retry = row?.retryAfter ?? row?.retry_after;
  const retryNumber = typeof retry === 'number' ? retry : typeof retry === 'string' && /^\d+(?:\.\d+)?$/.test(retry) ? Number(retry) : null;
  const retryAfter = retryNumber !== null ? (retryNumber < 1e9 ? timestamp + retryNumber * 1000 : retryNumber < 1e11 ? retryNumber * 1000 : retryNumber) : safeTime(retry);
  return {id, timestamp, provider, model, status, input, output, retryAfter};
}

const WINDOWS = {rolling_minute: 60000, rolling_hour: 3600000, pacific_day: Infinity};
const safeTime = x => {
  if (typeof x === 'number') return Number.isFinite(x) ? x : null;
  if (typeof x !== 'string') return null;
  const parsed = Date.parse(x);
  return Number.isFinite(parsed) ? parsed : null;
};
function blankCounters() {
  const result = {models: new Map(), last_rate_limit_at: null, retry_after_at: null};
  for (const period of Object.keys(WINDOWS)) Object.assign(result, {
    ['attempts_' + period]: 0, ['successes_' + period]: 0, ['failures_' + period]: 0,
    ['rate_limit_errors_' + period]: 0, ['input_tokens_recorded_' + period]: 0,
    ['output_tokens_recorded_' + period]: 0, ['input_tokens_coverage_' + period]: 'complete',
    ['output_tokens_coverage_' + period]: 'complete'});
  return result;
}
function add(counters, event, period) {
  counters['attempts_' + period]++;
  if (event.status >= 200 && event.status < 300) counters['successes_' + period]++;
  else counters['failures_' + period]++;
  if (event.status === 429) {
    counters['rate_limit_errors_' + period]++;
    counters.last_rate_limit_at = Math.max(counters.last_rate_limit_at || 0, event.timestamp);
    if (event.retryAfter !== null) counters.retry_after_at = Math.max(counters.retry_after_at || 0, event.retryAfter);
  }
  for (const kind of ['input', 'output']) {
    const value = event[kind], field = kind + '_tokens_recorded_' + period;
    if (value === null) counters[kind + '_tokens_coverage_' + period] = 'partial';
    else counters[field] += value;
  }
}
function serialiseCounters(counters) {
  const {models, ...rest} = counters;
  for (const kind of ['input', 'output']) for (const period of Object.keys(WINDOWS)) {
    const value = kind + '_tokens_recorded_' + period;
    if (rest[value] === 0 && rest[kind + '_tokens_coverage_' + period] === 'partial') rest[value] = null;
  }
  return rest;
}

export function reduceCallLogs(connections, events, {now = Date.now(), freshness = 'fresh', coverage = 'complete', source = 'omniroute_durable_call_logs', observedAt = now} = {}) {
  const {start, reset} = pacificDay(now), minuteStart = now - 60000, hourStart = now - 3600000;
  const configured = new Set((connections || []).map(c => providerKey(c?.provider)).filter(Boolean));
  const rows = Array.isArray(events) ? events : [];
  const providers = HUD_PROVIDERS.map(provider => {
    const total = blankCounters(), unique = new Set();
    for (const raw of rows) {
      const event = typeof raw?.timestamp === 'number' ? raw : projectCallLog(raw);
      if (!event || event.provider !== provider || event.timestamp < start || event.timestamp > now || unique.has(event.id)) continue;
      unique.add(event.id);
      const daily = event.timestamp >= start;
      const periods = [
        ...(event.timestamp > minuteStart ? ['rolling_minute'] : []),
        ...(event.timestamp > hourStart ? ['rolling_hour'] : []),
        ...(daily ? ['pacific_day'] : []),
      ];
      for (const period of periods) add(total, event, period);
      const model_id = event.model;
      if (!model_id) continue;
      const model = total.models.get(model_id) || {model_id, ...blankCounters()};
      for (const period of periods) add(model, event, period);
      total.models.set(model_id, model);
    }
    const providerOutput = serialiseCounters(total);
    return {provider, configured: configured.has(provider), ...providerOutput,
      last_rate_limit_at: total.last_rate_limit_at ? new Date(total.last_rate_limit_at).toISOString() : null,
      retry_after_at: total.retry_after_at && total.retry_after_at > now ? new Date(total.retry_after_at).toISOString() : null,
      employee_attribution: 'unknown', models: [...total.models.values()].map(m => ({model_id: m.model_id, ...serialiseCounters(m)}))};
  });
  return {source, freshness, coverage, observed_at: new Date(observedAt).toISOString(),
    rolling_window_start: new Date(minuteStart).toISOString(), pacific_day_start: new Date(start).toISOString(),
    pacific_day_reset: new Date(reset).toISOString(), providers};
}

function rowsFrom(document) {
  const rows = Array.isArray(document) ? document : document?.logs ?? document?.items ?? document?.data;
  if (!Array.isArray(rows) || rows.length > 1000) throw Error('call_logs_shape_unsupported');
  return rows;
}

export function createCallLogCollector(read, {clock = Date.now, pageSize = 200, maxPages = 100, cacheMs = 5000} = {}) {
  let events = new Map(), fetchedAt = 0, lastSuccessAt = 0, coverage = 'unavailable', dayStart = null, pending = null;
  return async connections => {
    const now = clock(), day = pacificDay(now);
    if (pending) { try { await pending; } catch {} }
    if (!lastSuccessAt || now - fetchedAt >= cacheMs || day.start !== dayStart) {
      pending = (async () => {
        const since = day.start !== dayStart || !lastSuccessAt ? day.start : Math.max(day.start, fetchedAt - 300000);
        const next = day.start === dayStart ? events : new Map();
        let nextCoverage = 'complete', offset = 0;
        for (let page = 0; page < maxPages; page++) {
          const query = new URLSearchParams({limit: String(pageSize), offset: String(offset), since: new Date(since).toISOString()});
          const rows = rowsFrom(await read('/api/usage/call-logs?' + query));
          for (const raw of rows) {
            const event = projectCallLog(raw);
            if (!event) { nextCoverage = 'partial'; continue; }
            if (event.timestamp >= day.start && event.timestamp <= now) next.set(event.id, event);
          }
          offset += rows.length;
          if (rows.length < pageSize) break;
          if (page === maxPages - 1) nextCoverage = 'partial';
        }
        for (const [id, event] of next) if (event.timestamp < day.start) next.delete(id);
        events = next; coverage = nextCoverage; dayStart = day.start; fetchedAt = clock(); lastSuccessAt = fetchedAt;
      })();
      try { await pending; } catch { if (!lastSuccessAt) coverage = 'unavailable'; }
      finally { pending = null; }
    }
    const isStale = !lastSuccessAt || now - lastSuccessAt > 30000;
    return reduceCallLogs(connections, [...events.values()], {now, observedAt: lastSuccessAt || now,
      freshness: isStale ? (lastSuccessAt ? 'stale' : 'unavailable') : 'fresh',
      coverage: isStale ? (lastSuccessAt ? 'stale' : 'unavailable') : coverage});
  };
}
