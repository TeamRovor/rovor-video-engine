import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {planApprovedJobs} from '../integrations/ghost-cloud/approved-feed.mjs';

// Source-only acceptance: no hosted secrets, provider calls, Mac, D1, or inference.
const tasks=JSON.parse(readFileSync(new URL('../coordination/tasks.json',import.meta.url),'utf8'));
const routing=JSON.parse(readFileSync(new URL('../coordination/work-routing.json',import.meta.url),'utf8'));
const objectives=new Set(JSON.parse(readFileSync(new URL('../business/operating-plan.json',import.meta.url),'utf8')).priority_order);
const batch=['cloud-fleet-unblock-checklist-20261026','cloud-route-drift-recovery-20261026',
 'cloud-short-pilot-production-20261026','cloud-speech-cue-verification-20261026',
 'cloud-phone-ui-acceptance-20261026','cloud-site-conversion-audit-20261026',
 'cloud-outreach-qualification-20261026','cloud-usage-proof-audit-20261026',
 'cloud-review-to-deliverable-20261026'];
const old=new Set(['saul-cloud-inquiry-copy-20261025','cloud-website-delivery-map-20261025',
 'cloud-domain-launch-checks-20261025','cloud-phone-storyboard-20261025',
 'cloud-phone-readability-spec-20261025','cloud-portrait-landscape-handoff-20261025',
 'cloud-website-intake-fields-20261025','cloud-intake-field-microcopy-20261025',
 'cloud-website-launch-review-20261025']);
const approvals=batch.map(task_id=>({task_id,revision:'v1'}));
const sha='a'.repeat(40);
test('nine distinct new cloud packets are bounded, source-approved and correctly routed',()=>{
 assert.equal(batch.length,9);assert.equal(new Set(batch).size,9);
 for(const id of batch){
  assert.equal(old.has(id),false);
  const task=tasks.tasks.find(x=>x.id===id);
  assert.ok(task,id);assert.equal(task.status,'active');assert.ok(task.owner);
  assert.deepEqual(task.depends_on,[]);
  assert.equal(task.cloud_inference?.data_class,'public_repository');
  assert.equal(task.cloud_inference?.approved_for_cloud,true);
  assert.equal(task.cloud_inference?.revision,'v1');
  assert.ok(task.cloud_inference?.prompt?.length>90);
  assert.ok(task.cloud_inference.prompt.length<14500);
  assert.ok(routing.tasks[id]);assert.ok(Array.isArray(routing.tasks[id].requires));
  assert.ok(objectives.has(routing.tasks[id].objective),id);
  assert.ok(task.acceptance.includes('PASS/FAIL'),id);
 }
});
test('new approvals plan distinct, immutable, non-replaying draft IDs through production feed',async()=>{
 const jobs=await planApprovedJobs(tasks,routing,sha,approvals);
 const jobsAgain=await planApprovedJobs(tasks,routing,'b'.repeat(40),approvals);
 assert.equal(jobs.length,9);
 assert.equal(new Set(jobs.map(x=>x.id)).size,9);
 assert.deepEqual(jobs.map(x=>x.id),jobsAgain.map(x=>x.id));
 assert.deepEqual(new Set(jobs.map(x=>x.task_id)),new Set(batch));
 assert.ok(jobs.every(x=>x.data_class==='public_repository'));
});
test('an old approval cannot accidentally select this second batch',async()=>{
 const older=[...old].map(task_id=>({task_id,revision:'v1'}));
 const prior=await planApprovedJobs(tasks,routing,sha,older);
 const next=await planApprovedJobs(tasks,routing,sha,approvals);
 assert.equal(prior.length,9);assert.equal(next.length,9);
 assert.ok(prior.every(x=>!next.some(y=>y.id===x.id)));
});
