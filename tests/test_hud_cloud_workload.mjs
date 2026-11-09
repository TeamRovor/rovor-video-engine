import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const quotaJS=readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js',import.meta.url),'utf8');
const workerJS=readFileSync(new URL('../integrations/hud-cloud/worker.mjs',import.meta.url),'utf8');
const popup=readFileSync(new URL('../dashboard/command-center/native-v8-9/workload-popup.js',import.meta.url),'utf8');
function board(){
  const context={window:{},document:{getElementById:()=>({})},
    Date,Math,Number,String,Array,Map,Set,Object};
  runInNewContext(quotaJS,context);
  return context.window.ROVOR_QUOTA_BOARD;
}
test('cloud-only mode represents exactly nine families; missing evidence is unknown not offline or zero',()=>{
  const html=board().renderCloudDashboard({});
  assert.equal((html.match(/class="rvq-v2-provider rvq-overview-tile"/g)||[]).length,9);
  assert.equal((html.match(/role="img" aria-label="Provider quota unknown"/g)||[]).length,9);
  assert.match(html,/PRIVATE CLOUD WORKFORCE · STATUS NOT VERIFIED/);
  assert.match(html,/WORKFORCE ELIGIBLE/);
  assert.match(html,/GEMINI VERIFIED/);
  assert.match(html,/INSTRUMENT RULES/);
  assert.doesNotMatch(html,/LAST MAC REPORT|LaunchAgent|Mac telemetry|Mac bridge|Open Terminal|cached inventory only/i);
});
test('Gemini actual local D1 reservations do not masquerade as account-wide Google rate limit',()=>{
  const now=Date.now();
  const catalog={source:'google_gemini_cloud_direct',online:true,
    directly_listed_models:['gemini-3.1-flash-lite','gemini-3.5-flash'],
    model_evidence:[{model:'gemini-3.1-flash-lite',verification:'verified_recent_reply',
      last_verified_at:new Date(now-1000).toISOString()},
      {model:'gemini-3.5-flash',verification:'listed_unverified'}]};
  const usage={source:'cloud_gemini_direct',scope:'this_hud_direct_api_only',
    observed_at:new Date(now).toISOString(),attempts:3,completed:2,
    daily_local_cap:12,daily_local_remaining:9,daily_local_reset_at:new Date(now+86400000).toISOString(),
    models:[{model:'gemini-3.1-flash-lite',attempts:3,completed:2,failures:1,input_tokens:41,output_tokens:12}]};
  const html=board().renderCloudDashboard({geminiCatalog:catalog,geminiUsage:usage});
  assert.match(html,/1 \/ 2/);
  assert.match(html,/2<\/strong>/);
  assert.match(html,/3 \/ 12/);
  assert.match(html,/9 remaining · LOCAL HUD SAFETY CAP/);
  assert.match(html,/VERIFIED 7D/);
  assert.match(html,/LISTED ONLY/);
  assert.match(html,/Google account RPM \/ TPM \/ RPD unknown/);
  assert.doesNotMatch(html,/Google (?:account |project )?remaining(?: requests)?[: ]+9\b/i);
  assert.equal((html.match(/class="rvq-v2-provider rvq-overview-tile"/g)||[]).length,9);
});
test('unsafe private provider model strings are escaped in the cloud view',()=>{
  const now=Date.now();
  const dirty='<img src=x onerror=alert(1)>';
  const cloud={execution_source:'cloud_provider',observed_at:now,
    providers:[{provider:'mistral',credentials_configured:true,admission:'eligible',
      dispatch_gate:{reason:dirty}}],
    attempts:[]};
  const html=board().renderCloudDashboard({cloud});
  assert(!html.includes(dirty));
  assert.match(html,/&lt;img src=x onerror=alert\(1\)&gt;/);
  assert.match(html,/ELIGIBLE · RECEIPT REQUIRED/);
  assert.match(html,/OWNER PASS \/ FAIL/);
  assert.match(html,/OPEN PRIVATE OWNER REVIEW QUEUE/);
  assert.match(html,/0 returned drafts awaiting review/);
  assert.match(html,/This sample is not the complete private owner queue/);
});
test('invalid, stale or contradictory quota source never fills a ring',()=>{
  const now=Date.now();
  const cloud={execution_source:'cloud_provider',observed_at:now,
    providers:[{provider:'nvidia',admission:'eligible',quota:{status:'verified',observed_at:now,
      used:4,limit:3,unit:'requests'}}],attempts:[]};
  const html=board().renderCloudDashboard({cloud});
  assert.match(html,/NVIDIA/);
  assert.match(html,/Allowance unknown/);
  assert.doesNotMatch(html,/4 \/ 3/);
});
test('active boot and cloud polling never touch archived local endpoints',()=>{
  const start=quotaJS.slice(quotaJS.indexOf('function startCloud(){'),quotaJS.indexOf('function captureState(root){'));
  assert(start.includes("'/api/ghost/status'"));
  assert(start.includes("'/api/hud/gemini/models'"));
  assert(start.includes("'/api/hud/gemini/usage'"));
  assert(start.includes("'/api/chat/groq/status'"));
  assert(!start.includes("'/api/hud/omniroute'"));
  assert(!start.includes('/pair/external'));
  assert.match(workerJS,/ROVOR_QUOTA_BOARD\?\.startCloud\?\.\(\)/);
  assert.doesNotMatch(workerJS.match(/const CLOUD_START = [^\n]+/)[0],/ROVOR_START_OMNIROUTE/);
  assert.doesNotMatch(popup,/Mac|LaunchAgent|omniroute|simulatedCounts|LAST REPORT/i);
});