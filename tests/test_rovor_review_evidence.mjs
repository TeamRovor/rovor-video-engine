import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {generateKeyPairSync} from 'node:crypto';
import {readGithubReviewEvidence} from '../integrations/hud-cloud/github-app.mjs';
import {reviewEvidence} from '../integrations/hud-cloud/review-evidence.mjs';
import {handle} from '../integrations/hud-cloud/worker.mjs';
const NOW=Date.now(),TOKEN='mock-scoped-token-123456789',READER='r'.repeat(40),WRITER='w'.repeat(40);
const original={id:123,workflow_id:99,head_branch:'main',event:'push',status:'completed',conclusion:'failure',name:'HUD deployment',created_at:new Date(NOW-20000).toISOString()};
const newer={...original,id:456,conclusion:'success',created_at:new Date(NOW-1000).toISOString()};
function fake(calls,run=original,latest=[newer]){
 return async(url,init)=>{
  calls.push({url,method:init.method});assert.equal(init.redirect,'manual');
  if(url.endsWith('/access_tokens'))return Response.json({token:TOKEN,expires_at:new Date(NOW+3600000).toISOString(),permissions:{contents:'read',issues:'read',pull_requests:'read',actions:'read',metadata:'read'}},{status:201});
  assert.equal(init.headers.Authorization,'Bearer '+TOKEN);assert.equal(init.method,'GET');
  if(url.endsWith('/actions/runs/123'))return Response.json(run);
  if(url.includes('/actions/workflows/99/runs?'))return Response.json({workflow_runs:latest});
  if(url.endsWith('/issues/9'))return Response.json({number:9,state:'closed',title:'Closed issue',body:'private body never copied'});
  if(url.endsWith('/pulls/8'))return Response.json({number:8,state:'closed',merged:true,title:'Merged pull request'});
  throw Error('unexpected URL');
 };
}
test('later comparable success is evidence, not a claimed repair; unrelated or manual runs cannot supersede',async()=>{
 const calls=[];
 assert.deepEqual(await readGithubReviewEvidence(TOKEN,'run-123',fake(calls)),{state:'newer_check_passed',title:'HUD deployment',related_id:456});
 assert.equal(calls.length,2);
 assert.equal((await readGithubReviewEvidence(TOKEN,'run-123',fake([],original,[{...newer,workflow_id:98}]))).state,'check_failed');
 assert.equal((await readGithubReviewEvidence(TOKEN,'run-123',fake([],{...original,event:'workflow_dispatch'}))).state,'check_failed');
 assert.equal((await readGithubReviewEvidence(TOKEN,'run-123',fake([],{...original,conclusion:'success'}))).state,'check_passed_now');
 assert.equal((await readGithubReviewEvidence(TOKEN,'issue-9',fake([]))).state,'issue_closed');
 assert.equal((await readGithubReviewEvidence(TOKEN,'pr-8',fake([]))).state,'pull_merged');
 await assert.rejects(()=>readGithubReviewEvidence(TOKEN,'../secrets',fake([])));
});
function setup(){
 const sqlite=new DatabaseSync(':memory:');sqlite.exec(readFileSync(new URL('../integrations/hud-cloud/schema.sql',import.meta.url),'utf8'));
 const DB={prepare(sql){const st=sqlite.prepare(sql);let a=[];const h={bind(...v){a=v;return h;},first:async()=>st.get(...a)??null,run:async()=>({meta:{changes:st.run(...a).changes}})};return h;}};
 sqlite.prepare("INSERT INTO hud_cloud_workforce_jobs(id,task_id,employee,kind,title,prompt,source_commit,revision,created_at,state,human_review) VALUES(?,?,?,?,?,?,?,?,?,'needs_review','not_recorded')").run('gc-review-one','cloud-discovery-run-123','Mike','code_review','Draft','private', 'a'.repeat(40),'v2',NOW);
 const pem=generateKeyPairSync('rsa',{modulusLength:2048}).privateKey.export({type:'pkcs1',format:'pem'});
 return {sqlite,env:{DB,HUD_READER_TOKEN:READER,HUD_WRITER_TOKEN:WRITER,ROVOR_GITHUB_APP_ID:'1',ROVOR_GITHUB_INSTALLATION_ID:'2',ROVOR_GITHUB_APP_PRIVATE_KEY:pem}};
}
test('exact pending job cache prevents repeats, anonymous access and arbitrary lookups',async()=>{
 const {env,sqlite}=setup(),calls=[],send=fake(calls);
 const url='https://hud.test/api/hud/workforce/evidence/gc-review-one';
 assert.equal((await handle(new Request(url),env)).status,401);
 assert.equal((await reviewEvidence(env,'other-job',NOW,send)).status,404);assert.equal(calls.length,0);
 const a=await reviewEvidence(env,'gc-review-one',NOW,send);
 assert.equal(a.body.state,'newer_check_passed');assert.equal(calls.length,3);
 const b=await reviewEvidence(env,'gc-review-one',NOW+1000,send);
 assert.deepEqual(b,a);assert.equal(calls.length,3);
 assert.equal(a.body.model_called,false);assert.equal(a.body.github_written,false);
 assert(!JSON.stringify(a).includes(TOKEN));
 assert.equal(sqlite.prepare('SELECT human_review FROM hud_cloud_workforce_jobs').get().human_review,'not_recorded');
 sqlite.exec("UPDATE hud_cloud_workforce_jobs SET human_review='passed',reviewed_at=1");
 assert.equal((await reviewEvidence(env,'gc-review-one',NOW+2000,send)).status,404);
});
