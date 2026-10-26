# Cloud activation review: denied canary must never become production work

**P1: block PR192 activation until canary jobs are isolated.**

Reviewed PR192 head: `9eb62a44b3ca7617a098d3ac613ee7f8b230eafe`.
Runtime source: PR188 merge `14def7f853fc08c84bb59578a53048dfd4f1cb97`.
Review status: reproduced and minimal patch tested offline; existing owner's
source branch is unchanged. No saved human PASS, model calls, secrets or
cloud deployment occurred.

## Failure and effect

`runCanary()` inserts a `ghost_cloud_jobs` row with normal kind `checklist`
**before** attempting atomic quota/concurrency admission. When that admission
fails, the function returns denied but leaves the unattempted job behind.
Production `tick()` later finds that normal Walter/checklist row and calls
inference. It does not recheck the canary's one-time approval, marker or exact
returned model. The denied probe can therefore run after approval expiry and
appear as a normal needs_review draft.

Offline reproduction used real in-memory SQLite, a busy synthetic Groq pool,
an explicit 15-minute probe approval, and the production dispatcher one hour
later. No real key or network request was used.

Before the patch:

```json
{"initial":{"status":"denied","reason":"shared_pool_or_stop_admission","provider":"groq"},"later_dispatched":1,"calls_after_expired_approval":1,"receipt":{"job_id":"canary-groq-denied-once","status":"needs_review"}}
```

After the proposed patch:

```json
{"initial":{"status":"denied","reason":"shared_pool_or_stop_admission","provider":"groq"},"later_dispatched":0,"calls_after_expired_approval":0}
```

## Minimal candidate correction

The accompanying `ghost-cloud-canary-pr192.patch` changes only the inserted
kind from `checklist` to reserved `canary`. Production eligibility permits
only checklist, plan, code_review and research; it cannot select this kind.
The direct canary admission remains unchanged, and the consumed ID remains
immutable. This preserves failed/denied evidence without replaying a probe,
removing rows or modifying the existing runtime owner's files.

Validated candidate commands on macOS Node24.22.0:

```sh
node --test tests/test_ghost_cloud.mjs tests/test_ghost_cloud_canary_preflight.mjs
# 27 passed, zero failed/skipped; real SQL, mocked provider transport.
git apply --reverse --check coordination/reviews/ghost-cloud-canary-pr192.patch
# Passed against the patched isolated local copy.
```

The existing PR192 owner must apply the patch on a new revision, add the
cross-dispatch regression to its suite, obtain fresh hosted checks and retain
actual human review requirements. This report does not merge another owner's
branch or mark the candidate installed.

## Reproducer

On the exact PR192 source, run the following with Node24 from the repository
root (for example save to a temporary root-level .mjs). The final assertion
expects the corrected behavior; it fails on the reviewed unpatched source.
Synthetic credentials and mocked fetch are intentional.

```javascript
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {runCanary} from './integrations/ghost-cloud/canary-preflight.mjs';
import {tick} from './integrations/ghost-cloud/runtime.mjs';
const now=Date.now(),s=new DatabaseSync(':memory:');
s.exec(readFileSync('integrations/ghost-cloud/schema.sql','utf8'));
const DB={prepare(sql){let a=[];const p=s.prepare(sql);const x={bind(...v){a=v;return x},async first(){return p.get(...a)||null},async run(){return {meta:{changes:Number(p.run(...a).changes)}}}};return x}};
s.exec('UPDATE ghost_cloud_control SET enabled=1');
const cfg={enabled:true,model:'pinned-test-model',pool:'test-pool',zero_cost:true,commercial_use:true,evidence_sha256:'a'.repeat(64),verified_at:now-1000,valid_until:now+7200000,canary_at:now-500,canary_sha256:'b'.repeat(64),requests_per_day:50,tokens_per_day:100000,min_interval_ms:100,max_input_bytes:5000,max_output_tokens:64,roles:['Walter'],kinds:['checklist']};
const env={DB,GROQ_API_KEY:'synthetic-secret-for-offline-test',GHOST_FLEET_CONFIG:JSON.stringify({groq:cfg})};
s.prepare('INSERT INTO ghost_cloud_jobs VALUES(?,?,?,?,?,?,?,?,?)').run('existing','Walter','test-task','checklist','existing','public',6,'c'.repeat(40),now);
s.prepare("INSERT INTO ghost_cloud_attempts(id,job_id,provider,model,pool,started_at,reserved_tokens,status) VALUES('prior','existing','groq','pinned-test-model','test-pool',?,100,'running')").run(now);
const approval={execute_once:true,zero_spend_verified:true,commercial_terms_verified:true,quota_verified:true,provider:'groq',model:cfg.model,evidence_sha256:cfg.evidence_sha256,canary_id:'canary-groq-denied-once',task_id:'test-task',source_commit:'c'.repeat(40),approved_at:now,expires_at:now+900000,remaining_requests:50,remaining_tokens:100000};
let externalCalls=0;
const denied=await runCanary({provider:'groq',cfg,env,approval,now,clock:()=>now,fetcher:async()=>{externalCalls++;throw Error('unexpected')}});
s.exec("UPDATE ghost_cloud_attempts SET status='needs_review' WHERE id='prior'");
const later=await tick(env,async()=>{externalCalls++;return Response.json({model:cfg.model,choices:[{message:{content:'unapproved late canary output'},finish_reason:'stop'}]})},now+3600000);
const receipt=s.prepare("SELECT job_id,status FROM ghost_cloud_attempts WHERE job_id='canary-groq-denied-once'").get();
console.log(JSON.stringify({initial:denied,later_dispatched:later.dispatched,calls_after_expired_approval:externalCalls,receipt}));
if(denied.reason!=='shared_pool_or_stop_admission'||externalCalls!==0||receipt!==undefined)throw Error('reproduction changed');
```

## Other activation blockers verified this session

The existing private Site `appgprj_6add1e2cc8c08191839344b34d7dbf50` still
reports version zero and no live URL. The registered source host
`git.chatgpt-team.site` still fails DNS resolution in this execution environment.
PR189, PR191, PR192, PR193 and PR194 remain open; their isolated tests do not
establish deployed composition or nine working providers. The private-HUD
owner's scope remains reserved. No duplicate Site, cloud credential migration,
provider billing attestation, live canary, cron activation or current HUD
model-usage claim is authorized by this report.
