import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
test('one-model verification workflow is manual-only, GitHub hosted and requires explicit Free-tier approval',()=>{
  const y=read('.github/workflows/verify-gemini-model-coverage.yml');
  assert.match(y,/workflow_dispatch:/);
  assert.doesNotMatch(y,/\n  schedule:|\n  push:|self-hosted|macOS/);
  assert.match(y,/default: audit_only/);
  assert.match(y,/if: inputs\.mode == 'verify_one_model'/);
  assert.match(y,/ROVOR_CANARY_FREE_CONFIRMED/);
  assert.match(y,/rovor-hud-production/);
  assert.match(y,/verify-cloud-gemini\.mjs/);
  assert.match(y,/GITHUB_STEP_SUMMARY/);
  assert.doesNotMatch(y,/GEMINI_API_KEY|GHOST_WRITER_TOKEN|wrangler deploy|cloudflare secret bulk/);
});
test('no model discovery or quota code may hardcode an external remaining estimate',()=>{
  const src=read('integrations/hud-cloud/cloud-gemini-chat.mjs');
  const usage=src.slice(src.indexOf('export async function cloudGeminiUsage'),src.indexOf('async function reserve'));
  assert.match(usage,/quota_remaining:'not_verified_provider_wide'/);
  assert.match(usage,/daily_local_remaining:/);
  assert.match(usage,/minute_local_remaining:/);
  assert.match(usage,/local_cap_time_zone:'UTC'/);
  assert.match(src,/gemini_auto_requires_recent_verified_model/);
  assert.match(src,/gemini_model_cooldown_active/);
  assert.doesNotMatch(src,/method:'(?:GET|POST)',redirect:'error'/i);
});
test('D1 forward-only health evidence schema contains no prompts or keys',()=>{
  const schema=read('integrations/hud-cloud/schema.sql');
  assert.match(schema,/CREATE TABLE IF NOT EXISTS hud_gemini_model_health/);
  const block=schema.slice(schema.indexOf('CREATE TABLE IF NOT EXISTS hud_gemini_model_health'));
  assert.match(block,/last_success_at INTEGER/);
  assert.match(block,/cooldown_until INTEGER/);
  assert.doesNotMatch(block,/prompt TEXT|api_key|private_key|output TEXT|billing_spent/);
});
test('single trusted-main Gemini 3.8 canary marker selects only its exact allowed model',()=>{
  const y=read('.github/workflows/deploy-private-hud-cloudflare.yml');
  assert.match(y,/GEMINI_ACTIVATE_ONCE:/);
  assert.match(y,/\[gemini-verify-3\.8-flash\]/);
  assert.match(y,/ROVOR_GEMINI_TEST_MODEL:/);
  assert.match(y,/&& 'gemini-3\.8-flash' \|\| ''/);
  assert.match(y,/github\.event_name == 'push'/);
  assert.match(y,/verify-cloud-gemini\.mjs/);
});
