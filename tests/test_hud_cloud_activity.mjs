import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {validateCloudReceipt, validateCloudFeed, describeCloudShift} from '../integrations/hud-cloud/cloud-activity.mjs';
import {compileCloudActivity, injectCloudActivity, buildCloudActivity} from '../integrations/hud-cloud/build-cloud-activity.mjs';
import {verifyCloudEvidence} from '../integrations/hud-cloud/verify-cloud-activity.mjs';

const root = path.resolve(import.meta.dirname, '..');
const receipt = () => JSON.parse(fs.readFileSync(path.join(root, 'coordination/cloud-shifts/walter-pr184.json'), 'utf8'));
const NOW = Date.parse('2026-10-25T00:00:00Z');
const html = fs.readFileSync(path.join(root, 'dashboard/command-center/native-v8-9/index.html'), 'utf8');

test('actual cloud receipt remains historical and upstream usage stays unknown', () => {
  const r = validateCloudReceipt(receipt(), NOW);
  assert.equal(r.commit_sha, 'd1145fe1ced42d1cdb30b421d40fb352d8541b36');
  assert.equal(r.model, null); assert.equal(r.tokens, null);
  assert.match(describeCloudShift(r), /COMPLETED/); assert.match(describeCloudShift(r), /Human review not recorded/);
  assert.equal(describeCloudShift(r).includes('ONLINE'), false);
  assert.equal(validateCloudReceipt(r, NOW + 86400000).completed_at, r.completed_at);
});
test('unrecognized roles, source types and fabricated usage or approval fail closed', () => {
  for (const change of [r => r.employee = 'Unknown', r => r.execution_source = 'omniroute', r => r.model = 'guessed',
    r => r.tokens = 100, r => r.human_review = 'approved', r => r.private_prompt = 'secret']) {
    const r = receipt(); change(r); assert.throws(() => validateCloudReceipt(r, NOW));
  }
});
test('receipts require exact trusted repository evidence and source ordering', () => {
  for (const change of [r => r.artifact_url = 'https://evil.example/', r => r.checks_url = 'javascript:alert(1)',
    r => r.commit_sha = 'unverified', r => r.started_at = '2026-10-25T00:00:00Z',
    r => r.observed_at = '2026-10-26T00:00:00Z', r => r.summary = 'x'.repeat(401),
    r => r.completed_at = 'not a date']) {
    const r = receipt(); change(r); assert.throws(() => validateCloudReceipt(r, NOW));
  }
});
test('feed compilation deduplicates, orders and caps records without re-clocking jobs', () => {
  const rows = Array.from({length: 205}, (_, i) => ({...receipt(), id: 'walter-job-' + i,
    completed_at: new Date(Date.parse(receipt().completed_at) + i * 1000).toISOString(), observed_at: new Date(NOW).toISOString()}));
  const feed = compileCloudActivity(rows, NOW);
  assert.equal(feed.receipts.length, 200); assert.equal(feed.receipts[0].id, 'walter-job-204');
  assert.equal(feed.generated_at, new Date(NOW).toISOString());
  assert.notEqual(feed.receipts[0].completed_at, feed.generated_at);
  assert.throws(() => compileCloudActivity([receipt(), receipt()], NOW));
});
test('client rejects malformed, oversized and future feeds', () => {
  const feed = compileCloudActivity([receipt()], NOW);
  assert.throws(() => validateCloudFeed({...feed, source: 'live_model_usage'}, NOW));
  assert.throws(() => validateCloudFeed({...feed, generated_at: '2026-10-26T00:00:00Z'}, NOW));
  assert.throws(() => validateCloudFeed({...feed, receipts: Array(201).fill(receipt())}, NOW));
});
test('artifact adds only a module hook to the exact original HUD and is idempotent', () => {
  const output = injectCloudActivity(html);
  const hook = '<script type="module" src="./cloud-activity.mjs"></script>\n';
  assert.equal(output.replace(hook, ''), html);
  assert.equal(injectCloudActivity(output), output);
  assert.throws(() => injectCloudActivity('<body>Different design</body>'));
});
test('Pages artifact contains a bounded valid feed, module and original design', t => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hud-cloud-activity-'));
  t.after(() => fs.rmSync(dir, {recursive: true, force: true}));
  fs.mkdirSync(path.join(dir, 'native-v8-9'));
  fs.writeFileSync(path.join(dir, 'native-v8-9/index.html'), html);
  const original = fs.readFileSync(path.join(root, 'dashboard/command-center/native-v8-9/index.html'), 'utf8');
  const result = buildCloudActivity(dir, NOW); assert.ok(result.receipts >= 1);
  const feed = JSON.parse(fs.readFileSync(path.join(dir, 'native-v8-9/cloud-activity.json'), 'utf8'));
  assert.equal(validateCloudFeed(feed, NOW).receipts[0].employee, 'Walter');
  assert.ok(fs.existsSync(path.join(dir, 'native-v8-9/cloud-activity.mjs')));
  assert.equal(fs.readFileSync(path.join(root, 'dashboard/command-center/native-v8-9/index.html'), 'utf8'), original);
});
function evidence() {
  const r = receipt();
  return {pr: {merged: true, merge_commit_sha: r.commit_sha, html_url: r.artifact_url,
    merged_at: '2026-10-24T21:44:47Z', head: {sha: 'b'.repeat(40)}},
    run: {status: 'completed', conclusion: 'success', html_url: r.checks_url,
      repository: {full_name: 'TeamRovor/rovor-video-engine'}, head_sha: 'b'.repeat(40)}};
}
test('publisher reads back matching merged PR and successful checks on its source revision', async () => {
  const e = evidence(), calls = [];
  assert.equal(await verifyCloudEvidence(receipt(), async resource => {calls.push(resource); return resource.startsWith('/pulls/') ? e.pr : e.run;}, NOW), 'walter-pr184');
  assert.deepEqual(calls, ['/pulls/184', '/actions/runs/40135524309']);
});
test('publisher refuses source claims with missing merges, wrong commits or unsuccessful unrelated CI', async () => {
  for (const change of [e => e.pr.merged = false, e => e.pr.merge_commit_sha = 'c'.repeat(40),
    e => e.pr.merged_at = '2026-10-24T23:00:00Z', e => e.run.conclusion = 'failure',
    e => e.run.head_sha = 'c'.repeat(40), e => e.run.repository.full_name = 'other/repo']) {
    const e = evidence(); change(e);
    await assert.rejects(verifyCloudEvidence(receipt(), async resource => resource.startsWith('/pulls/') ? e.pr : e.run, NOW));
  }
});
test('untrusted links are rejected before any evidence request', async () => {
  let calls = 0;
  await assert.rejects(verifyCloudEvidence({...receipt(), artifact_url: 'https://evil.example'}, async () => {calls++;}, NOW));
  assert.equal(calls, 0);
});
