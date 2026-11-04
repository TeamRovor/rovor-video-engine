import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const src=readFileSync(new URL('../dashboard/command-center/native-v8-9/hud-chat.js',import.meta.url),'utf8');

test('Ask ROVOR keeps iOS focus controls at Safari-safe 16px and preserves pinch zoom',()=>{
  assert.match(src, /iosTypeAndKeyboardCSS/);
  assert.match(src, /#rvc select, #rvc textarea, #rvc input[^{]*\{\s*font-size:16px!important;/);
  assert.match(src, /#rvc select\{font-size:16px!important;/);
  assert.doesNotMatch(src,/user-scalable\s*=\s*no|maximum-scale\s*=\s*1/);
});

test('mobile chat adjusts to visible iPhone viewport when keyboard appears',()=>{
  for(const marker of [
    'window.visualViewport','--rvc-vv-height','--rvc-vv-top',
    "addEventListener('resize',syncVisualViewport)",
    "addEventListener('orientationchange',syncVisualViewport)",
    "input.focus({preventScroll:true})",
    "const polishedMobileCSS =",
  ]) assert(src.includes(marker),marker);
  assert.match(src, /#rvc\[data-open=true\] \{ top:var\(--rvc-vv-top/);
  assert.match(src, /height:var\(--rvc-vv-height/);
});

test('responsive iPhone and tablet preserve model selection, closing and history access',()=>{
  for(const marker of [
    'grid-template-areas:"menu source clear close" "model model model model"',
    'grid-area:model','grid-area:source','data-side-open=true',
    'rvc-side-backdrop','max-width:1100px','max-width:760px',
    'const sideBackdrop=','document.body.style.overflow',
  ]) assert(src.includes(marker),marker);
});

test('Ask ROVOR is a private chat, not a silently running employee scheduler',()=>{
  assert(src.includes('/api/hud/chat/models'));
  assert(src.includes('/api/hud/chat/submit'));
  assert(src.includes('/api/hud/chat/status/'));
  assert(src.includes("'omniroute'"));
  assert(src.includes('No confirmed model reply'));
  assert.doesNotMatch(src,/fetch\(['"]https?:\/\//);
});


test('failed response is retained locally but never sent to a subsequent model as context',()=>{
  assert.match(src,/outcome:'failed'/);
  assert.match(src,/outcome:'complete'/);
  assert.match(src,/history\.filter\(m=>m\.role==='user'\|\|\(m\.role==='assistant'&&m\.outcome==='complete'\)\)/);
  assert.match(src,/rvc-receipt/);
  assert.match(src,/Copy response/);
  assert.match(src,/cancelConfirmed/);
  assert.match(src,/api\/hud\/chat\/cancel\//);
});


test('Ask ROVOR shows nine-provider inventory with explicit freshness and never treats enabled as verified',()=>{
  assert.match(src,/refreshProviderInventory/);
  assert.match(src,/\/api\/hud\/omniroute\?period=24h/);
  assert.match(src,/STALE \/ NOT LIVE/);
  assert.match(src,/PROVIDER INVENTORY UNAVAILABLE/);
  assert.match(src,/model access unverified/);
  assert.match(src,/rvc-provider-inspect/);
  assert.match(src,/Mac bridge reported · /);
  assert.match(src,/allowed routes · confirm a reply to verify use/);
  assert.match(src,/Free-tagged model routes/);
  assert.match(src,/Owner-allowlisted model routes/);
  assert.match(src,/refreshButton.onclick/);
  assert.match(src,/rvc-connection-bar/);
  assert.match(src,/Refresh model availability and provider status/);
});


test('Ask ROVOR GitHub source is explicit, read-only, and touch-safe on phone, iPad and desktop',()=>{
  assert.match(src,/rvc-repo-file/);
  assert.match(src,/GitHub source/);
  assert.match(src,/repoSelect\.value/);
  assert.match(src,/if\(attachedSource\)payload\.repo_file=attachedSource/);
  assert.match(src,/no repository write access/i);
  assert.match(src,/rvc-repo-file\{[^}]*font-size:16px!important/);
  assert.match(src,/repoRow\.hidden=sourceSelect\.value!=='omniroute'/);
  assert.match(src,/repoSelect\.disabled=b\|\|sourceSelect\.value!=='omniroute'/);
});

function taskPlanner(){
  const window={};
  const document={readyState:'loading',addEventListener(){}};
  const localStorage={getItem(){return null;}};
  vm.runInNewContext(src,{window,document,localStorage,
    crypto:{randomUUID:()=> '123e4567-e89b-42d3-a456-426614174000'}},
    {timeout:1200});
  assert.equal(typeof window.ROVOR_ROUTE_PLANNER?.plan,'function');
  return window.ROVOR_ROUTE_PLANNER.plan;
}
test('Ask ROVOR Smart routes one routine code prompt using only Mac-advertised eligible IDs',()=>{
  const plan=taskPlanner()('Fix this Python coding bug',[
    'groq/small:free','openrouter/qwen-coder:free','rovor-fast-free-v1'
  ]);
  assert.equal(plan.routes.length,1);
  assert.equal(plan.routes[0],'openrouter/qwen-coder:free');
  assert.match(plan.reason,/Task-aware route hint/);
  assert.match(src,/const AUTO_ROUTE='__rovor_smart_route__'/);
  assert.match(src,/routePreview|routingNote/);
});
test('natural language can request two distinct provider routes with separate receipts',()=>{
  const plan=taskPlanner()('Ask Groq and Gemini to independently review this design',[
    'groq/fast:free','gemini/flash:free','rovor-fast-free-v1'],'__rovor_smart_route__',{allowTeam:true});
  assert.equal(plan.routes.length,2);
  assert.equal(plan.routes.join(','),'gemini/flash:free,groq/fast:free' /* provider list is fixed-order */);
  assert.match(src,/async function askBoth\(/);
  assert.doesNotMatch(src,/Promise\.all\(routes\.map\(runOne\)\)/,
    'single Mac executor cannot reliably finish two simultaneous D1 leases');
  assert.match(src,/for\(const route of routes\)/);
  assert.match(src,/await runOne\(route,results\[0\]\|\|null\)/);
  assert.match(src,/second model reviews the first/i);
  assert.match(src,/Independent critical review/);
  assert.match(src,/for\(const result of results\)/);
  assert.match(src,/REPLIES CONFIRMED/);
});
test('named provider absent, all-nine fanout, or stale manual ID fails before submitting a job',()=>{
  const plan=taskPlanner();
  const routes=['groq/fast:free','openrouter/other:free'];
  assert.match(plan('Ask NVIDIA to fix the code',routes).error,/nvidia.*no advertised/i);
  assert.match(plan('Ask all nine providers',routes).error,/At most two/);
  assert.match(plan('quick answer',routes,'mistral/paid').error,/no longer available/);
  assert.equal(plan('quick answer',routes,'groq/fast:free').routes.join(','),'groq/fast:free');
  assert.match(plan('Ask Groq and OpenRouter',routes).error,/Enable two-model review/);
  assert.equal(plan('Compare two approaches',routes).routes.length,1);
  assert.equal(plan('Compare two approaches',routes,'__rovor_smart_route__',{allowTeam:true}).routes.length,2);
});
test('a model only appears callable when it is present in the Mac chat catalog',()=>{
  const plan=taskPlanner();
  assert.equal(plan('Ask Groq',[]).routes.length,0);
  assert.match(plan('Ask Groq',[]).error,/No currently advertised routes/);
  assert.match(src,/actual upstream identity not separately attested/);
  assert.doesNotMatch(src,/auto[\s-]*switch to paid/i);
});

test('two-model orchestration requires an explicit opt-in and remains mobile safe',()=>{
  assert.match(src,/rvc-team-review/);
  assert.match(src,/Two-model review when useful/);
  assert.match(src,/teamInput\.checked/);
  assert.match(src,/teamInput\.disabled=b\|\|sourceSelect\.value!=='omniroute'/);
  assert.match(src,/teamRow\.hidden=sourceSelect\.value!=='omniroute'/);
  assert.match(src,/rvc-team-row/);
  assert.match(src,/width:18px;height:18px/);
  assert.match(src,/No model calls confirmed|no model calls confirmed/);
  assert.match(src,/No confirmed reply/);
  assert.match(src,/stop\.onclick=async/);
});
