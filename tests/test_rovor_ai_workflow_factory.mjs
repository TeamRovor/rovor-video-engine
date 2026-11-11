import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {compileReviewedWorkflow,findOwnerPassedProposals} from '../tools/cloud_workflow_proposal_bridge.mjs';
import {publishReviewed} from '../tools/publish_reviewed_workflow_proposals.mjs';

const id='gc-'+'a'.repeat(48);
const name='rovor-mobile-hud-regression';
const content=JSON.stringify({
 workflow_id:name,
 name:'ROVOR Mobile HUD Regression',
 description:'Check the existing ROVOR HUD phone drawer and cloud review security on demand',
 template:'node-test',
 tests:['tests/test_hud_mobile_drawer_stability.mjs','tests/test_hud_private_review_page.mjs'],
 schedule:'manual'
});
const sha=x=>createHash('sha256').update(x,'utf8').digest('hex');
const digest=sha(content);
const token='r'.repeat(40);
const ownerRow={id,task_id:'cloud-walter-workflow-factory-20261110',
 employee:'Walter',kind:'plan',state:'needs_review',actual_model:'gemini-3.5-flash-lite',
 human_review:'passed',reviewed_at:Date.now()-1000,output_sha256:digest};
const status=items=>({
 source:'existing_cloudflare_hud_gemini_workforce',mac_required:false,
 site_review_ledger_synced:false,items
});
function http(items=[ownerRow],draftOverrides={}){
 const seen=[];
 const send=async(url,opts)=>{
  const path=new URL(url).pathname;
  seen.push({path,authorized:opts.headers.Authorization==='Bearer '+token});
  if(path==='/api/hud/workforce/status')return Response.json(status(items));
  if(path==='/api/hud/workforce/draft/'+id)
   return Response.json({id,state:'needs_review',human_review:'passed',
    output_sha256:digest,output:content,...draftOverrides});
  throw Error('unexpected_private_endpoint');
 };
 return {seen,send};
}
const env={
 GITHUB_REPOSITORY:'TeamRovor/rovor-video-engine',
 GITHUB_REF:'refs/heads/main',
 GITHUB_EVENT_NAME:'schedule',
 GITHUB_TOKEN:'g'.repeat(40),
 ROVOR_HUD_READER_TOKEN:token
};

test('owner-PASS model spec compiles only safe fixed GitHub Actions text',()=>{
 const plan=compileReviewedWorkflow(content,digest);
 assert.equal(plan.id,name);
 assert.equal(plan.schedule,'manual');
 assert.match(plan.yaml,/name: "ROVOR Mobile HUD Regression"/);
 assert.match(plan.yaml,/workflow_dispatch:/);
 assert.match(plan.yaml,/permissions:\n  contents: read/);
 assert.match(plan.yaml,/node --test tests\/test_hud_mobile_drawer_stability\.mjs/);
 assert.doesNotMatch(plan.yaml,/schedule:|secrets\.|contents: write|pull-requests: write|curl |bash |eval\(/);
 assert.equal(plan.yaml.split('run: |').length,2);
 assert.equal(plan.yaml.split('node --test').length,3);
});

test('cadence is bounded and controlled by reviewed JSON, never arbitrary cron',()=>{
 const data=JSON.parse(content);data.schedule='every-4-hours';
 const text=JSON.stringify(data);
 assert.match(compileReviewedWorkflow(text,sha(text)).yaml,/cron: "17 \*\/4 \* \* \*"/);
 data.schedule='@reboot';
 assert.throws(()=>compileReviewedWorkflow(JSON.stringify(data),sha(JSON.stringify(data))),
  /workflow_spec_not_allowlisted/);
});

test('model cannot inject shell, new actions, unsafe paths, extra keys, or tamper digest',()=>{
 const obj=JSON.parse(content);
 const bad=[
  {...obj,tests:['tests/../../../etc/passwd']},
  {...obj,tests:['tests/test_hud_mobile_drawer_stability.mjs; echo hi']},
  {...obj,tests:['.github/workflows/deploy-private-hud-cloudflare.yml']},
  {...obj,tests:['tests/test_hud_mobile_drawer_stability.mjs','tests/test_hud_mobile_drawer_stability.mjs']},
  {...obj,template:'run-shell'},
  {...obj,name:'ROVOR hello\npermissions: write-all'},
  {...obj,description:'Write to GitHub! ${{ secrets.GITHUB_TOKEN }}'},
  {...obj,run:'rm -rf /'},
  {...obj,schedule:'* * * * *'},
  {...obj,workflow_id:'../../.github/workflows/evil'},
 ];
 for(const proposal of bad){const text=JSON.stringify(proposal);
  assert.throws(()=>compileReviewedWorkflow(text,sha(text)),/workflow_spec_not_allowlisted/);
 }
 assert.throws(()=>compileReviewedWorkflow(content,'0'.repeat(64)),/private_draft_digest_mismatch/);
 assert.throws(()=>compileReviewedWorkflow('Here is your JSON:\n'+content,sha('Here is your JSON:\n'+content)),
  /workflow_spec_not_json/);
});

test('private D1 excludes FAIL, pending, wrong model and old task; only PASS is fetched',async()=>{
 const fail={...ownerRow,human_review:'failed'};
 const unchecked={...ownerRow,human_review:'not_recorded'};
 const wrong={...ownerRow,actual_model:'unknown'};
 const historical={...ownerRow,task_id:'cloud-gemini-website-offer-pilot-20261110'};
 for(const item of [fail,unchecked,wrong,historical]){
  const m=http([item]);
  assert.deepEqual(await findOwnerPassedProposals({readerToken:token,send:m.send}),[]);
  assert.equal(m.seen.length,1,'never fetch or expose unchecked draft');
 }
 const good=http();
 const list=await findOwnerPassedProposals({readerToken:token,send:good.send});
 assert.equal(list.length,1);
 assert.equal(list[0].receipt,digest);
 assert.deepEqual(good.seen.map(x=>x.path),['/api/hud/workforce/status','/api/hud/workforce/draft/'+id]);
 assert(good.seen.every(x=>x.authorized));
 const wrongDigest=http([ownerRow],{output_sha256:'0'.repeat(64)});
 await assert.rejects(()=>findOwnerPassedProposals({readerToken:token,send:wrongDigest.send}),
  /private_review_readback_invalid/);
});

test('scheduled publisher never touches GitHub when no owner-PASS proposal',async()=>{
 const calls=[];
 const work=await publishReviewed({env,send:http([]).send,
  git(...args){calls.push(args);return '';},
  read(){throw Error('must not read git');},
  write(){throw Error('must not write git');}
 });
 assert.equal(work.state,'no_owner_passed_workflow_proposal');
 assert.equal(work.created,0);
 assert.deepEqual(calls,[]);
});

test('owner approved spec creates review-only PR, not a workflow installation',async()=>{
 const calls=[],written=new Map();
 const result=await publishReviewed({env,send:http().send,
  git(cmd,args){
   calls.push([cmd,...args]);
   if(cmd==='git'&&args[0]==='ls-remote')return '';
   if(cmd==='git'&&args[0]==='status')return '';
   if(cmd==='gh')return 'https://github.com/TeamRovor/rovor-video-engine/pull/999';
   return '';
  },
  exists:()=>false,
  mkdir:()=>{},
  write(file,body){written.set(file,body);}
 });
 assert.equal(result.created,1);
 const path=[...written.keys()][0];
 assert.match(path,/coordination\/workflow-proposals\/rovor-mobile-hud-regression\.yml$/);
 assert.match(written.get(path),/node --test tests\/test_hud_private_review_page\.mjs/);
 assert(calls.some(([cmd,...args])=>cmd==='gh'&&args[0]==='pr'&&args[1]==='create'));
 assert(calls.some(([cmd,...args])=>cmd==='git'&&args[0]==='push'));
 assert(!calls.some(([cmd,...args])=>cmd==='git'&&args[0]==='push'&&args.includes('main')));
 assert(!calls.some(([cmd,...args])=>cmd==='gh'&&args.includes('merge')));
});

test('bridge runs continuously with no inference only on trusted main and production credentials',async()=>{
 const workflow=readFileSync(new URL('../.github/workflows/rovor-ai-workflow-factory.yml',import.meta.url),'utf8');
 assert.match(workflow,/cron: "11 \*\/2 \* \* \*"/);
 assert.match(workflow,/github\.ref == 'refs\/heads\/main'/);
 assert.match(workflow,/environment: rovor-hud-production/);
 assert.match(workflow,/contents: write\n      pull-requests: write/);
 assert.match(workflow,/ROVOR_HUD_READER_TOKEN: \$\{\{ secrets\.ROVOR_HUD_READER_TOKEN \}\}/);
 assert.doesNotMatch(workflow,/ROVOR_HUD_WRITER_TOKEN|GEMINI_API_KEY|ROVOR_WORKFORCE_ACTION|\.\/api\/hud\/workforce\/tick/);
 await assert.rejects(()=>publishReviewed({env:{...env,GITHUB_REF:'refs/heads/pull/1'},
  send:http().send}),/trusted_main_credentials_required/);
});

test('Walter is a new unapproved v2 task until explicit one-click owner authorization',()=>{
 const tasks=JSON.parse(readFileSync(new URL('../coordination/tasks.json',import.meta.url),'utf8')).tasks;
 const candidate=tasks.find(x=>x.id==='cloud-walter-workflow-factory-20261110');
 assert(candidate);
 assert.equal(candidate.cloud_inference.approved_for_cloud,false);
 assert.equal(candidate.cloud_inference.revision,'v2');
 assert.equal(candidate.cloud_inference.employee,'Walter');
 assert.equal(candidate.cloud_inference.kind,'plan');
 const y=readFileSync(new URL('../.github/workflows/run-walter-workflow-once.yml',import.meta.url),'utf8');
 assert.match(y,/name: RUN WALTER ONCE - propose GitHub workflow/);
 assert.match(y,/workflow_dispatch:/);
 assert.match(y,/approve_walter_workflow_draft:[\s\S]*?default: false/);
 assert.match(y,/ROVOR_WORKFORCE_ACTION: pilot_once/);
 assert.match(y,/ROVOR_WORKFORCE_TASK_ID: cloud-walter-workflow-factory-20261110/);
 assert.match(y,/ROVOR_WORKFORCE_REVISION: v2/);
 assert.match(y,/ROVOR_OWNER_CONFIRMS_NEW_TASK: \$\{\{ inputs\.approve_walter_workflow_draft \}\}/);
 assert.doesNotMatch(y,/ROVOR_OWNER_CONFIRMS_NEW_TASK: true|type: choice/);
});
