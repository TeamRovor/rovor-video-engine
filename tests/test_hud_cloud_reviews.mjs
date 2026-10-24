import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {reviewLink, reviewFromIssueEvent, validateOwnerReview, latestOwnerReviews} from '../integrations/hud-cloud/cloud-reviews.mjs';
import {saveOwnerReview} from '../integrations/hud-cloud/record-cloud-review.mjs';
import {describeCloudShift} from '../integrations/hud-cloud/cloud-activity.mjs';
import {verifyCloudEvidence} from '../integrations/hud-cloud/verify-cloud-activity.mjs';
const receipt = JSON.parse(fs.readFileSync(new URL('../coordination/cloud-shifts/walter-pr184.json', import.meta.url), 'utf8'));
const NOW = Date.parse('2026-10-25T00:00:00Z');
function event(decision='pass', number=200) {
  const url = new URL(reviewLink(receipt, decision));
  return {action:'opened',repository:{full_name:'TeamRovor/rovor-video-engine'}, sender:{login:'TeamRovor',type:'User'},
    issue:{number,title:url.searchParams.get('title'),body:url.searchParams.get('body'),user:{login:'TeamRovor',type:'User'},
      html_url:'https://github.com/TeamRovor/rovor-video-engine/issues/'+number,created_at:'2026-10-24T23:00:00Z',performed_via_github_app:null}};
}
test('PASS and FAIL controls require an actual native GitHub owner submission',()=>{
  for(const decision of ['pass','fail']) {
    const url=new URL(reviewLink(receipt,decision));assert.equal(url.origin,'https://github.com');
    const r=reviewFromIssueEvent(event(decision),[receipt],NOW);
    assert.equal(r.decision,decision);assert.equal(r.author,'TeamRovor');
    assert.match(describeCloudShift(receipt,r),new RegExp(decision.toUpperCase()+' saved by owner'));
  }
});
test('non-owner, bot, app-authored and edited issues cannot approve outputs',()=>{
  for(const change of [e=>e.sender.login='other',e=>e.issue.user.login='other',e=>e.sender.type='Bot',
    e=>e.issue.performed_via_github_app={id:1},e=>e.action='edited',e=>e.repository.full_name='other/repo']) {
    const e=event();change(e);assert.equal(reviewFromIssueEvent(e,[receipt],NOW),null);
  }
});
test('reviews bind to the exact output commit and cannot change hidden subject or title',()=>{
  for(const change of [e=>e.issue.title='ROVOR review: FAIL '+receipt.id,e=>e.issue.body=e.issue.body.replaceAll(receipt.commit_sha,'b'.repeat(40)),
    e=>e.issue.body+='\n'+e.issue.body,e=>e.issue.created_at='2026-10-23T00:00:00Z']) {
    const e=event();change(e);assert.throws(()=>reviewFromIssueEvent(e,[receipt],NOW));
  }
});
test('new owner decision supersedes an old one without rewriting its record',()=>{
  const pass=reviewFromIssueEvent(event('pass',200),[receipt],NOW),fail=reviewFromIssueEvent(event('fail',201),[receipt],NOW);
  assert.equal(latestOwnerReviews([fail,pass],[receipt],NOW)[0].decision,'fail');assert.equal(pass.decision,'pass');
  assert.throws(()=>latestOwnerReviews([pass,pass],[receipt],NOW));
});
test('reason stays plain bounded data',()=>{
  const e=event('fail');e.issue.body=e.issue.body.replace('Reason:\n\n','Reason:\nFix the output, <script>plain text</script>\n');
  assert.match(reviewFromIssueEvent(e,[receipt],NOW).reason,/<script>/);
  e.issue.body=e.issue.body.replace('Fix the output, <script>plain text</script>','x'.repeat(1001));
  assert.throws(()=>reviewFromIssueEvent(e,[receipt],NOW));
});
test('unknown subjects, forged identities and untrusted issue links fail closed',()=>{
  const r=reviewFromIssueEvent(event(),[receipt],NOW);
  for(const change of [r=>r.author='worker',r=>r.commit_sha='c'.repeat(40),r=>r.issue_url='https://evil.example',r=>r.decision='approved']) {
    const copy={...r};change(copy);assert.throws(()=>validateOwnerReview(copy,[receipt],NOW));
  }
});
test('ledger saves one immutable decision and publishes the actual commit',async()=>{
  const review=reviewFromIssueEvent(event(),[receipt],NOW),calls=[];
  const sha=await saveOwnerReview(review,async(method,resource,body)=>{calls.push({method,resource,body});
    return method==='GET'?{status:404,body:{}}:{status:201,body:{commit:{sha:'a'.repeat(40)}}};});
  assert.equal(sha,'a'.repeat(40));assert.equal(calls[1].method,'PUT');
  assert.deepEqual(JSON.parse(Buffer.from(calls[1].body.content,'base64').toString('utf8')),review);
});
test('duplicate delivery is idempotent and cannot overwrite another review',async()=>{
  const review=reviewFromIssueEvent(event(),[receipt],NOW),content=Buffer.from(JSON.stringify(review,null,2)+'\n').toString('base64');
  assert.equal(await saveOwnerReview(review,async(_,resource)=>resource.startsWith('/contents/')?{status:200,body:{content}}:{status:200,body:{sha:'a'.repeat(40)}}),'a'.repeat(40));
  await assert.rejects(saveOwnerReview(review,async()=>({status:200,body:{content:Buffer.from('{}').toString('base64')}})),/immutable/);
});
test('ledger retries bounded create conflicts and preserves permission failures',async()=>{
  const review=reviewFromIssueEvent(event(),[receipt],NOW);let writes=0;
  assert.equal(await saveOwnerReview(review,async(method)=>method==='GET'?{status:404,body:{}}:++writes<2?{status:409,body:{}}:{status:201,body:{commit:{sha:'a'.repeat(40)}}}),'a'.repeat(40));
  assert.equal(writes,2);
  await assert.rejects(saveOwnerReview(review,async()=>({status:403,body:{}})),/denied/);
});
test('completed cloud work can await owner review before its PR is merged',async()=>{
  const pending={...receipt,commit_sha:'b'.repeat(40)};
  const pr={state:'open',merged:false,head:{sha:pending.commit_sha},html_url:pending.artifact_url,created_at:'2026-10-24T21:44:00Z'};
  const run={status:'completed',conclusion:'success',head_sha:pending.commit_sha,html_url:pending.checks_url,repository:{full_name:'TeamRovor/rovor-video-engine'}};
  assert.equal(await verifyCloudEvidence(pending,async p=>p.startsWith('/pulls/')?pr:run,NOW),pending.id);
});
