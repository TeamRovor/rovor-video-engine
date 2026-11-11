import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const y=readFileSync(new URL('../.github/workflows/run-gus-once.yml',import.meta.url),'utf8');
const legacy=readFileSync(new URL('../.github/workflows/cloud-gemini-workforce.yml',import.meta.url),'utf8');
const operator=readFileSync(new URL('../tools/cloud_gemini_workforce_control.mjs',import.meta.url),'utf8');
const jobs=JSON.parse(readFileSync(new URL('../coordination/tasks.json',import.meta.url),'utf8')).tasks;

test('Run Gus once is a distinct manual trigger without the missing action dropdown',()=>{
 assert.match(y,/name: RUN GUS ONCE - Gemini cloud pilot/);
 assert.match(y,/workflow_dispatch:/);
 assert.doesNotMatch(y,/type:\s*choice\b|\binputs\.action\b/);
 assert.match(y,/approve_one_gus_job:/);
 assert.match(y,/type: boolean\s+required: true\s+default: false/);
 assert.match(legacy,/default: status/,'original status and STOP operations remain unchanged');
});

test('Fixed single-v2 identity, positive user consent, and protected main environment',()=>{
 assert.match(y,/ROVOR_WORKFORCE_ACTION: pilot_once/);
 assert.match(y,/ROVOR_WORKFORCE_TASK_ID: cloud-gemini-website-offer-pilot-20261110/);
 assert.match(y,/ROVOR_WORKFORCE_REVISION: v2/);
 assert.match(y,/ROVOR_OWNER_CONFIRMS_NEW_TASK: \$\{\{ inputs\.approve_one_gus_job \}\}/);
 assert.match(y,/github\.event_name == 'workflow_dispatch' && github\.ref == 'refs\/heads\/main'/);
 assert.match(y,/environment: rovor-hud-production/);
 assert.match(y,/if \[ "\$\{ROVOR_OWNER_CONFIRMS_NEW_TASK\}" != "true" \]; then/);
 assert.match(operator,/if\(!confirm\|\|/);
 assert.match(operator,/if\(before\.enabled!==false\)/);
 assert.match(operator,/finally\{[\s\S]*?await setEnabled\(false\)/);
 const task=jobs.find(x=>x.id==='cloud-gemini-website-offer-pilot-20261110');
 assert(task);
 assert.equal(task.status,'active');
 assert.equal(task.cloud_inference.revision,'v2');
 assert.equal(task.cloud_inference.approved_for_cloud,false,'workflow must not silently approve in source');
});
