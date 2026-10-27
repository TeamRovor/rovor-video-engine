import test from 'node:test';
import assert from 'node:assert/strict';
import {readGroqRpd, createCloudOperations} from '../integrations/ghost-cloud/site-operations.mjs';

const now = 1793074000000;
const good = () => new Headers({
 'x-ratelimit-limit-requests': '1000',
 'x-ratelimit-remaining-requests': '973',
 'x-ratelimit-reset-requests': '2m59.56s',
});
test('authenticated Groq request headers support an RPD meter and reset', () => {
 const result = readGroqRpd(good(), now);
 assert.deepEqual(result, {
  unit: 'requests_per_day', used: 27, limit: 1000,
  remaining: 973, resets_at: now + 179560, observed_at: now,
  source: 'authenticated_groq_rpd_response_headers',
  scope: 'provider_account'
 });
});
test('reject missing, malformed, reversed and unbounded quota headers', () => {
 const cases = [
  new Headers(),
  new Headers({...Object.fromEntries(good()), 'x-ratelimit-remaining-requests':'1001'}),
  new Headers({...Object.fromEntries(good()), 'x-ratelimit-limit-requests':'free'}),
  new Headers({...Object.fromEntries(good()), 'x-ratelimit-reset-requests':'tomorrow'}),
  new Headers({...Object.fromEntries(good()), 'x-ratelimit-reset-requests':'60h'}),
  new Headers({...Object.fromEntries(good()), 'x-ratelimit-reset-requests':'5s2m'}),
  new Headers({...Object.fromEntries(good()), 'x-ratelimit-reset-requests':'5m 2s'}),
 ];
 for(const headers of cases) assert.equal(readGroqRpd(headers,now),null);
});
test('never treat a catalog alone as quota or free-tier billing evidence', () => {
 const fromCatalog = {models:[{id:'openai/gpt-oss-20b'}]};
 assert.equal(readGroqRpd(fromCatalog,now),null);
 assert.equal(readGroqRpd(good(),Number.NaN),null);
});

test('provider inventory returns verified Groq request quota without claiming billing or inference', async () => {
 const cloud = {PROVIDERS:{groq:['https://api.groq.com/openai/v1/chat/completions','GROQ_API_KEY']}};
 const operations = createCloudOperations(async () => new Response(''), cloud);
 const env = {GROQ_API_KEY:'test-authenticated-slot-token'};
 const fetcher = async (url, options) => {
  assert.equal(url, 'https://api.groq.com/openai/v1/models');
  assert.equal(options.method, 'GET');
  return Response.json({data:[{id:'openai/gpt-oss-20b'}]}, {headers:good()});
 };
 const report = await operations.inventory(env,'groq',fetcher);
 assert.equal(report.status,'catalog_received');
 assert.equal(report.quota_verified,true);
 assert.equal(report.billing_verified,false);
 assert.equal(report.canary_verified,false);
 assert.equal(report.quota_observation.used,27);
 assert.equal(report.quota_observation.scope,'provider_account');
});
test('missing Groq headers remain unknown instead of fabricating a zero-percent meter', async () => {
 const cloud = {PROVIDERS:{groq:['https://api.groq.com/openai/v1/chat/completions','GROQ_API_KEY']}};
 const ops = createCloudOperations(async () => new Response(''),cloud);
 const report = await ops.inventory({GROQ_API_KEY:'test-authenticated-slot-token'},'groq',
  async () => Response.json({data:[{id:'openai/gpt-oss-20b'}]}));
 assert.equal(report.quota_verified,false);
 assert.equal(Object.hasOwn(report,'quota_observation'),false);
});
