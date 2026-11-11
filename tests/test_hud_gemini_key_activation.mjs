import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {buildHudSecretPayload,validateOneTimeGeminiActivation}
  from '../integrations/hud-cloud/private-worker-secret-payload.mjs';

const base={
  ROVOR_HUD_READER_TOKEN:'r'.repeat(48),
  ROVOR_HUD_WRITER_TOKEN:'w'.repeat(48),
  GROQ_HUD_API_KEY:'g'.repeat(48),
  GROQ_HUD_CHAT_ENABLED:'false',
  GITHUB_REPOSITORY:'TeamRovor/rovor-video-engine',
  GITHUB_REF:'refs/heads/main',
  GITHUB_EVENT_NAME:'push',
  ROVOR_GEMINI_CLOUD_API_KEY:'AIza'+'A'.repeat(35)
};

test('Ordinary HUD deployments preserve other providers without installing new Gemini keys',()=>{
  const env={...base,GEMINI_ACTIVATE_ONCE:'false'};
  const secrets=buildHudSecretPayload(env);
  assert.equal(secrets.HUD_READER_TOKEN,env.ROVOR_HUD_READER_TOKEN);
  assert.equal(secrets.HUD_WRITER_TOKEN,env.ROVOR_HUD_WRITER_TOKEN);
  assert.equal(secrets.GROQ_HUD_API_KEY,env.GROQ_HUD_API_KEY);
  assert.equal(secrets.GROQ_HUD_CHAT_ENABLED,'false');
  assert.equal(Object.hasOwn(secrets,'GEMINI_API_KEY'),false);
  assert.equal(Object.hasOwn(secrets,'ROVOR_GEMINI_FREE_TIER_VERIFIED'),false);
});

test('One owner-marked trusted-main push installs Gemini using existing secret and retains HUD auth',()=>{
  const env={...base,GEMINI_ACTIVATE_ONCE:'true'};
  assert.equal(validateOneTimeGeminiActivation(env),true);
  const secrets=buildHudSecretPayload(env);
  assert.equal(secrets.GEMINI_API_KEY,env.ROVOR_GEMINI_CLOUD_API_KEY);
  assert.equal(secrets.ROVOR_GEMINI_FREE_TIER_VERIFIED,'confirmed');
  assert.equal(secrets.HUD_READER_TOKEN,env.ROVOR_HUD_READER_TOKEN);
  assert.equal(secrets.GROQ_HUD_API_KEY,env.GROQ_HUD_API_KEY);
  assert(!JSON.stringify(Object.keys(secrets)).includes(env.ROVOR_GEMINI_CLOUD_API_KEY));
});

test('No secret and malformed key fail before an owner-triggered production write',()=>{
  for(const key of ['',undefined,'not-valid','\n'+'A'.repeat(40),'A'.repeat(530)]){
    const e={...base,GEMINI_ACTIVATE_ONCE:'true',ROVOR_GEMINI_CLOUD_API_KEY:key};
    assert.throws(()=>validateOneTimeGeminiActivation(e),/owner_gemini_github_secret_missing_or_invalid/);
    assert.throws(()=>buildHudSecretPayload(e),/owner_gemini_github_secret_missing_or_invalid/);
  }
});

test('Untrusted or wrong-trigger context cannot activate Google key',()=>{
  for(const override of [
    {GITHUB_REF:'refs/heads/feature'}, {GITHUB_EVENT_NAME:'pull_request'},
    {GITHUB_REPOSITORY:'unauthorized/clone'}
  ]){
    const e={...base,GEMINI_ACTIVATE_ONCE:'true',...override};
    assert.throws(()=>buildHudSecretPayload(e),/gemini_activation_requires_trusted_main_push/);
  }
});

test('one-shot Gemini verifier demands a fresh challenged response and exact private D1 readback',()=>{
  const src=readFileSync(new URL('../integrations/hud-cloud/verify-cloud-gemini.mjs',import.meta.url),'utf8');
  assert.match(src,/randomBytes\(8\)\.toString\('hex'\)/);
  assert.match(src,/including this exact token: '\+challenge/);
  assert.match(src,/output\.includes\(challenge\)/);
  assert.match(src,/X-ROVOR-Resolved-Model/);
  assert.match(src,/per_model_receipt_not_advanced/);
  assert.doesNotMatch(src,/retry\s*\(/);
});

test('Existing deployment workflow gates activation to one marked main merge and a single canary',()=>{
  const yaml=readFileSync(new URL('../.github/workflows/deploy-private-hud-cloudflare.yml',import.meta.url),'utf8');
  assert.match(yaml,/GEMINI_ACTIVATE_ONCE:[^\n]*github\.event_name == 'push'[^\n]*\[gemini-activate-once\]/);
  assert.match(yaml,/if: env\.GEMINI_ACTIVATE_ONCE == 'true'[\s\S]*?node private-worker-secret-payload\.mjs --preflight/);
  assert.match(yaml,/node private-worker-secret-payload\.mjs \|[\r\n ]+wrangler secret bulk/);
  assert.match(yaml,/if: env\.GEMINI_ACTIVATE_ONCE == 'true'[\r\n ]+run: node verify-cloud-gemini\.mjs/);
  const checks=yaml.match(/run: node verify-cloud-gemini\.mjs/g)||[];
  assert.equal(checks.length,1);
  assert.doesNotMatch(yaml,/runs-on: \[self-hosted/);
});
