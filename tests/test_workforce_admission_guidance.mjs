import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const source=readFileSync(new URL('../dashboard/command-center/native-v8-9/workforce-review.js',import.meta.url),'utf8');
const start=source.indexOf('function admissionGuidance(');
assert(start>=0);
const end=source.indexOf('\nconst githubDiscoveryState=',start);
assert(end>start);
const guidance=runInNewContext(source.slice(start,end)+'\nadmissionGuidance',{
 validTokens:n=>Number.isSafeInteger(n)&&n>=0,
 formatTime:n=>new Date(n).toISOString()
});
const now=1794381600000;
const snapshot={source:'read_only_private_D1',observed_at:now,
 provider_admission_verified_by_this_read:false,queued_jobs:0,running_or_uncertain:0,
 pending_reviews:2,rolling_day_attempts:3,rolling_day_limit:3,pending_review_limit:3,
 fresh_unattempted_discoveries:1,earliest_rolling_slot_at:now+3600000,
 observed_constraints:['rolling_day_attempt_limit','no_queued_job']};

test('owner sees observed daily cap, exact counts and earliest slot without promise of execution',()=>{
 const text=guidance(snapshot,now);
 assert.match(text,/3 of 3 attempts/);
 assert.match(text,/2 of 3 reviews waiting; 0 jobs queued; 1 fresh discoveries/);
 assert.match(text,/rolling 24-hour attempt limit is reached/);
 assert.match(text,/Earliest daily slot: 2026-11-11T08:20:00.000Z/);
 assert.match(text,/No job is queued/);
 assert.match(text,/does not guarantee execution/);
 assert(source.includes("guidance.textContent+=' '+admissionGuidance(data.admission)"));
});
test('all independently observed wait conditions remain visible together',()=>{
 const text=guidance({...snapshot,pending_reviews:3,running_or_uncertain:1,
  fresh_unattempted_discoveries:0,observed_constraints:['stop_closed',
   'standing_authorization_inactive','running_or_uncertain_claim','pending_review_limit',
   'no_fresh_unattempted_discovery']},now);
 for(const pattern of [/STOP is active/,/authorization is inactive/,/uncertain job/,
   /review queue is full/,/No fresh, unattempted discovery/])assert.match(text,pattern);
 assert.doesNotMatch(text,/Earliest daily slot/);
});
test('missing, stale, future, malformed and untrusted snapshots cannot imply readiness',()=>{
 for(const value of [null,{}, {...snapshot,observed_at:now-300001},
  {...snapshot,observed_at:now+1},{...snapshot,source:'legacy_site'},
  {...snapshot,provider_admission_verified_by_this_read:true},
  {...snapshot,rolling_day_limit:0},{...snapshot,pending_reviews:-1},
  {...snapshot,queued_jobs:'0'},{...snapshot,observed_constraints:['<script>']},
  {...snapshot,observed_constraints:null}])assert.match(guidance(value,now),/unavailable or stale/);
});
test('invalid slot stays unknown and an empty list of constraints never claims provider readiness',()=>{
 for(const slot of [null,now-1,now+86400001,'tomorrow'])
  assert.match(guidance({...snapshot,earliest_rolling_slot_at:slot},now),/next daily slot is not verified/);
 const text=guidance({...snapshot,observed_constraints:[],rolling_day_attempts:0},now);
 assert.match(text,/Provider checks still apply/);
 assert.doesNotMatch(text,/Earliest daily slot|ready to run|will run/);
});
