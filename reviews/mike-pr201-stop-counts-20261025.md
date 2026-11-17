# Mike review: PR201 drops partial feed counts on STOP

Status: reproducible source finding; scheduler source unchanged by this review.

Reviewed PR201 head `595ab826d8da971314629ff3f80b3ee49f1b2e47`.

## P2 — Already queued jobs disappear from the shift receipt

In `integrations/ghost-cloud/scheduled-shift.mjs:27-32`, the `feed.status === 'stopped'` branch sets the status but skips copying `queued` and `duplicates`. Both counters therefore remain zero when the final D1 row is written.

The proposed `replenishApprovedJobs` implementation at PR191 head `142eb00cedd3a03dc9a279184faaa40b886aa8e0` returns `{status:'stopped', queued, duplicates}` when STOP is observed between submissions. Those counters can be nonzero. This is a valid partial-feed outcome, not a fabricated malformed provider reply.

An offline real-SQLite reproduction queued two synthetic jobs and returned one duplicate before STOP. The saved shift row lost both counts:

```json
{"feed":{"status":"stopped","queued":2,"duplicates":1},"saved":{"status":"stopped","queued":0,"duplicates":0,"dispatched":0},"tick_calls":0,"synthetic_jobs":2}
```

Dispatch correctly stops. The defect is inaccurate activity evidence: a HUD can report no queued work even though jobs remain in the durable queue. This finding does not establish live inference or a deployed defect.

## Bounded correction for the scheduler owner

Validate and preserve the bounded feed counters before branching on its stopped status. Keep STOP authoritative: do not call tick after the feeder reports stopped. Add a regression for a stopped feed with nonzero queued/duplicate counts; assert exact persisted counts, stopped status and zero tick calls. Do not weaken count validation or replay existing jobs.

The scheduler source is owned by another participant. This review does not edit it, submit owner PASS/FAIL, merge or deploy.

## Verification

- Node24.22.1, Linux: all 11 existing scheduler tests passed on the reviewed source.
- The existing stopped-feed fixture only returns `queued:0`, so it misses partial progress.
- Actual hosted scheduler baseline run [40167203600](https://github.com/TeamRovor/rovor-video-engine/actions/runs/40167203600) succeeded at `535f18c16cb95eac4d0ac3749a208cab30a78180`. The reviewed later head changes coordination; its native runtime and private operations checks also read back successful. The new partial-STOP reproduction was local only.
- No network/provider requests, real drafts, private inputs, native Mac actions or external messages were used.

## Reproduce

From a checkout of the exact PR201 head, run this with Node24 (`node --input-type=module`). It uses an in-memory database and injected synthetic feed only:

```javascript
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import {runScheduledShift} from './integrations/ghost-cloud/scheduled-shift.mjs';
const sql=new DatabaseSync(':memory:');
sql.exec(readFileSync(new URL('./integrations/ghost-cloud/scheduled-shift.sql',import.meta.url),'utf8'));
sql.exec('CREATE TABLE ghost_cloud_control(id INTEGER PRIMARY KEY,enabled INTEGER NOT NULL); INSERT INTO ghost_cloud_control VALUES(1,1); CREATE TABLE synthetic_queue(id TEXT PRIMARY KEY)');
const DB={prepare(query){const stmt=sql.prepare(query);return {bind(...args){return {first:async()=>stmt.get(...args),run:async()=>stmt.run(...args),all:async()=>({results:stmt.all(...args)})};}};}};
let tickCalls=0;
const feed={status:'stopped',queued:2,duplicates:1};
const result=await runScheduledShift({DB,GHOST_CRON_OPT_IN:'owner-approved-ghost-cron-v1'},{
  replenish:async()=>{sql.exec("INSERT INTO synthetic_queue VALUES('one'),('two'); UPDATE ghost_cloud_control SET enabled=0 WHERE id=1");return feed;},
  tick:async()=>{tickCalls++;return {enabled:true,dispatched:0};},
  clock:()=>1792900000000,newId:()=> 'review-repro-00000001'
});
const saved=sql.prepare('SELECT status,queued,duplicates,dispatched FROM ghost_cloud_shift_runs').get();
assert.equal(result.status,'stopped');assert.equal(tickCalls,0);
assert.equal(sql.prepare('SELECT count(*) n FROM synthetic_queue').get().n,2);
assert.equal(saved.queued,0);assert.equal(saved.duplicates,0);
console.log(JSON.stringify({feed,saved,tick_calls:tickCalls,synthetic_jobs:2}));
```
