import './test_workforce_admission_guidance.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {handle} from '../integrations/hud-cloud/worker.mjs';
import {verifyPrivateReviewPage} from '../integrations/hud-cloud/verify-private-review-page.mjs';

const read=file=>readFileSync(new URL('../'+file,import.meta.url),'utf8');
const html=read('dashboard/command-center/native-v8-9/workforce-review.html');
const pageJS=read('dashboard/command-center/native-v8-9/workforce-review.js');
const chat=read('dashboard/command-center/native-v8-9/hud-chat.js');
const origin='https://rovor-hud-telemetry.rovordigital.workers.dev';
const token='r'.repeat(40),writer='w'.repeat(40);
const req=(path,headers={})=>new Request(origin+path,{headers});
function mockEnv(){
 const requests=[];
 const env={DB:{},HUD_READER_TOKEN:token,HUD_WRITER_TOKEN:writer,
  ASSETS:{async fetch(request){
   requests.push(new URL(request.url).pathname);
   const path=new URL(request.url).pathname;
   if(path==='/workforce-review')
    return new Response(html,{status:200,headers:{'Content-Type':'text/html; charset=utf-8'}});
   if(path==='/workforce-review.js')
    return new Response(pageJS,{status:200,headers:{'Content-Type':'application/javascript'}});
   throw Error('unexpected_private_asset');
  }}
 };
 return {requests,env};
}

test('Gus review desk is private, anonymous deep links redirect to same-origin sign in',async()=>{
 const {env,requests}=mockEnv();
 const res=await handle(req('/workforce-review.html'),env);
 assert.equal(res.status,303);
 assert.equal(res.headers.get('location'),origin+'/login?next=%2Fworkforce-review.html');
 assert.deepEqual(requests,[],'anonymous request cannot fetch private asset');
 const script=await handle(req('/workforce-review.js'),env);
 assert.equal(script.status,401);
 assert.deepEqual(requests,[]);
 const login=await handle(req('/login?next=%2Fworkforce-review.html'),env);
 const markup=await login.text();
 assert.equal(login.status,200);
 assert.match(markup,/get\('next'\)==='\/workforce-review\.html'/);
 assert.match(markup,/\?\'\/workforce-review\.html\':\'\/\'/);
});

test('Authenticated private reader cookie serves standalone review, with no injected chat code',async()=>{
 const {env,requests}=mockEnv();
 const fromCookie=await handle(req('/workforce-review.html',{
  Cookie:'rovor_hud_reader='+encodeURIComponent(token)}),env);
 assert.equal(fromCookie.status,200);
 assert.equal(fromCookie.headers.get('cache-control'),'no-store');
 assert.equal(fromCookie.headers.get('x-frame-options'),'DENY');
 assert.match(fromCookie.headers.get('content-security-policy'),/script-src 'self'/);
 const rendered=await fromCookie.text();
 assert.equal(rendered,html);
 assert.doesNotMatch(rendered,/ROVOR_START_OMNIROUTE|CLOUD_START|GEMINI_API_KEY|HUD_READER_TOKEN/);
 const authenticatedScript=await handle(req('/workforce-review.js',{
  Authorization:'Bearer '+token}),env);
 assert.equal(authenticatedScript.status,200);
 assert.equal(await authenticatedScript.text(),pageJS);
 assert.deepEqual(requests,['/workforce-review','/workforce-review.js']);
});

test('Private review JS verifies exact output SHA-256 before immutable user PASS or FAIL',()=>{
 assert.match(html,/<script type="module" src="\/workforce-review\.js"><\/script>/);
 assert.match(html,/name="robots" content="noindex,nofollow,noarchive"/);
 assert.match(pageJS,/crypto\.subtle\.digest\('SHA-256'/);
 assert.match(pageJS,/hash!==entry\.output_sha256/);
 assert.match(pageJS,/Confirm '\+human\+' decision'/);
 assert.match(pageJS,/body:\{job_id:entry\.id,verdict,output_sha256:hash\}/);
 assert.match(pageJS,/saved\.output_sha256!==hash/);
 assert.match(pageJS,/check\.human_review!==verdict\|\|check\.output_sha256!==hash/);
 assert.match(pageJS,/stop\.textContent=data\.enabled\?'ENABLED':'STOPPED'/);
 assert.doesNotMatch(pageJS,/\.innerHTML\s*=|\beval\(|\/api\/hud\/workforce\/(tick|intake|control)/);
});

test('Existing Ask ROVOR shows real D1 pending count and an obvious review link only on Cloudflare host',()=>{
 assert.match(chat,/className:'rvc-review-link',href:'\/workforce-review\.html'/);
 assert.match(chat,/window\.location\.hostname==='rovor-hud-telemetry\.rovordigital\.workers\.dev'/);
 assert.match(chat,/data\.items\.filter\(x=>x\.state==='needs_review'/);
 assert.match(chat,/REVIEW '\+count\+' CLOUD DRAFT'/);
 assert.match(chat,/if\(open\)\{load\(\);refreshProviderInventory\(\);void refreshReviewShortcut\(\);/);
});

test('Post-deploy verifier refuses stale review assets and proves anonymous auth denial',async()=>{
 const headers={ContentType:'text/html'};
 const send=async(url,options)=>{
  const path=new URL(url).pathname;
  const auth=!!options.headers.Authorization;
  if(path==='/workforce-review.html'&&!auth)
   return new Response(null,{status:303,headers:{
    Location:origin+'/login?next=%2Fworkforce-review.html'}});
  if(path==='/workforce-review.js'&&!auth)
   return Response.json({error:'unauthorized'},{status:401});
  if(path==='/workforce-review.html')
   return new Response(html,{status:200,headers:{
    'Cache-Control':'no-store',
    'Content-Security-Policy':"default-src 'none'; script-src 'self'"
   }});
  if(path==='/workforce-review.js')
   return new Response(pageJS,{status:200,headers:{'Content-Type':'application/javascript'}});
  throw Error('unsupported_test_path');
 };
 const proof=await verifyPrivateReviewPage({origin,readerToken:token,
  send,expectedHtml:html,expectedScript:pageJS});
 assert.deepEqual(proof,{private_auth_verified:true,
  anonymous_review_denied:true,deployed_html_matches_checkout:true,
  deployed_review_logic_matches_checkout:true,model_calls:0,review_decisions:0});
 await assert.rejects(()=>verifyPrivateReviewPage({
  origin,readerToken:token,send,expectedHtml:html+' stale',expectedScript:pageJS}),
  /review_page_source_mismatch/);
 await assert.rejects(()=>verifyPrivateReviewPage({
  origin,readerToken:token,send,expectedHtml:html,expectedScript:pageJS+' stale'}),
  /review_script_source_mismatch/);
 await assert.rejects(()=>verifyPrivateReviewPage({
  origin,readerToken:'wrong',send,expectedHtml:html,expectedScript:pageJS}),
  /private_review_deploy_credentials_invalid/);
});

test('review desk exposes native scheduler evidence and exact per-job usage without fabricating activity',()=>{
 assert.match(html,/id="native-clock"/);
 assert.match(html,/id="standing-state"/);
 assert.match(pageJS,/data\.native_schedule\?\.source==='cloudflare_scheduled_event'/);
 assert.match(pageJS,/NO RECEIPT/);
 assert.match(pageJS,/no completed inference/);
 assert.match(pageJS,/validTokens\(entry\.tokens_input\)&&validTokens\(entry\.tokens_output\)/);
 assert.match(pageJS,/Exact job token usage: not recorded/);
 assert.match(html,/start-cloud-workforce\.yml/);
 assert.doesNotMatch(pageJS,/\/api\/hud\/workforce\/(tick|intake|control)/);
});

test('review is decision-first, full exact drafts remain available and defer is not a verdict',()=>{
 assert.match(html,/Review inbox/);
 assert.match(html,/Keep this work/);
 assert.match(html,/Reject this work/);
 assert.match(html,/Past reviews/);
 assert.match(html,/Workforce status &amp; advanced controls/);
 assert(html.indexOf('id="jobs"')<html.indexOf('id="history"'));
 assert.match(pageJS,/loadExactDraft\(entry,entry\.human_review\)/);
 assert.match(pageJS,/pendingLoads\.slice\(0,3\)/);
 assert.match(pageJS,/No PASS or FAIL was recorded/);
 assert.match(pageJS,/No code, fix, independent test run, deployment or pull request was produced/);
 assert.match(pageJS,/Read the complete employee report/);
 assert.match(pageJS,/document\.createTextNode\(content\)/);
 assert.doesNotMatch(pageJS,/\.innerHTML\s*=|insertAdjacentHTML|document\.write\(/);
});

test('plain-language owner brief makes provenance, value, concerns and approval limits explicit',()=>{
 assert.match(pageJS,/What ROVOR investigated/);
 assert.match(pageJS,/What it actually produced/);
 assert.match(pageJS,/How it might benefit ROVOR/);
 assert.match(pageJS,/Concerns and missing proof/);
 assert.match(pageJS,/What your PASS will do/);
 assert.match(pageJS,/not the actual code, error logs, issue text or pull request diff/);
 assert.match(pageJS,/This benefit has not been demonstrated/);
 assert.match(pageJS,/potentially outdated|Potentially outdated/);
 assert.match(pageJS,/employee’s exact AI-generated report/);
 assert.match(html,/PASS never certifies a fix or deploys code/);
 assert.match(pageJS,/const group=\[current,earlier\]/);
 assert.match(read('integrations/hud-cloud/approved-workforce.mjs'),/## Concerns and uncertainties/);
});

test('owner review page includes truthful native GitHub write readiness without asserting live PR delivery',()=>{
 assert.match(html,/id="github-patch-readiness"/);
 assert.match(pageJS,/configuration_complete_write_scope_unverified/);
 assert.match(pageJS,/write permissions must pass the protected deployment preflight/);
});

test('specific reported benefit, risks and next step are extracted as unverified employee claims',()=>{
 assert.match(pageJS,/FROM THE EMPLOYEE REPORT · NOT INDEPENDENTLY VERIFIED/);
 assert.match(pageJS,/Specific benefit claimed/);
 assert.match(pageJS,/Risks or unknowns reported/);
 assert.match(pageJS,/Employee suggests doing next/);
 assert.match(pageJS,/No specific benefit was provided/);
 assert.match(pageJS,/complete structured report/);
 assert.match(pageJS,/box\.append\(reportClaims\(sections\)\)/);
 assert.match(pageJS,/section\.append\(make\('h5','',label\),make\('p','',content\|\|missing\)\)/);
 assert.doesNotMatch(pageJS,/\.innerHTML\s*=|insertAdjacentHTML/);
});

test('superseded preflight jobs are explained without claiming inference, approval or changed code',()=>{
 assert.match(pageJS,/SKIPPED · OUTDATED/);
 assert.match(pageJS,/discovery_no_longer_actionable/);
 assert.match(pageJS,/No provider tokens were spent on this job/);
 assert.match(pageJS,/no owner decision is needed/);
 assert.match(pageJS,/A later START will not replay this item/);
 assert.match(pageJS,/entry\.started_at==null&&entry\.actual_model==null/);
});

test('first GitHub draft PR progress uses verified scope and real D1 PR, not configuration alone',()=>{
 assert.match(html,/First autonomous GitHub draft PR/);
 assert.match(html,/id="first-pr-state"/);
 assert.match(html,/No automatic merge or release/);
 assert.match(pageJS,/write_scope_verified_at_deployment/);
 assert.match(pageJS,/A previous GitHub write has an uncertain outcome/);
 assert.match(pageJS,/An engineering proposal awaits PASS or FAIL/);
 assert.match(pageJS,/An actual ROVOR draft PR is recorded/);
 assert.match(pageJS,/rolling_day_attempt_limit/);
 const first=html.indexOf('<section id="patch-preparation"');
 const advanced=html.indexOf('Workforce status &amp; advanced controls');
 assert(first>advanced);
 const endAdvanced=html.indexOf('</details>',advanced);
 assert(first>endAdvanced,'source builder must no longer be hidden in advanced controls');
 assert.doesNotMatch(pageJS,/\.innerHTML\s*=|insertAdjacentHTML/);
});
