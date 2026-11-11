import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const src=readFileSync(new URL('../dashboard/command-center/native-v8-9/hud-chat.js',import.meta.url),'utf8');

function streamHarness(){
  const callbacks=new Map(),renders=[];let next=0;
  const code=src.slice(src.indexOf('  function paintChatLog('),src.indexOf('  function renderText('));
  const {createStreamPainter,paintChatLog}=vm.runInNewContext(code+'\n({createStreamPainter,paintChatLog})',{
    requestAnimationFrame:fn=>{callbacks.set(++next,fn);return next;},
    cancelAnimationFrame:id=>callbacks.delete(id)
  });
  const log={scrollHeight:1000,clientHeight:400,scrollTop:600},node={};
  const painter=createStreamPainter(log,node,(target,text)=>{
    assert.equal(target,node);renders.push(text);log.scrollHeight+=100;
  });
  return {log,painter,renders,callbacks,paintChatLog,frame(){
    for(const [id,fn] of [...callbacks]){callbacks.delete(id);fn();}
  }};
}
test('stream bursts paint once per animation frame and use the latest accumulated reply',()=>{
  const s=streamHarness();
  for(let i=1;i<=100;i++)s.painter.queue('x'.repeat(i));
  assert.equal(s.callbacks.size,1);assert.equal(s.renders.length,0);
  s.frame();assert.deepEqual(s.renders,['x'.repeat(100)]);
  assert.equal(s.log.scrollTop,s.log.scrollHeight);
  s.painter.queue('next frame');assert.equal(s.callbacks.size,1);
  s.frame();assert.equal(s.renders.length,2);
});
test('scrolling away before the next paint is respected through streaming and completion',()=>{
  const s=streamHarness();s.painter.queue('partial');
  s.log.scrollTop=120;s.frame();assert.equal(s.log.scrollTop,120);
  s.painter.queue('more');s.frame();assert.equal(s.log.scrollTop,120);
  s.painter.finish('complete');assert.equal(s.log.scrollTop,120);
  s.paintChatLog(s.log,()=>{s.log.scrollHeight+=100;s.log.scrollTop=9999;});
  assert.equal(s.log.scrollTop,120,'history rebuild preserves the reading position');
  assert.match(src,/painter\.finish\(reply\);[\s\S]*?redraw\(true\)/);
  assert.match(src,/painter\.cancel\(\);\s*paintChatLog\(log,\(\)=>renderText\(bubble,message\)\)/);
});
test('finishing flushes the latest full reply even without a frame and cancels the pending callback',()=>{
  const s=streamHarness();s.painter.queue('partial');
  s.painter.finish('final formatted reply');
  assert.equal(s.callbacks.size,0);assert.deepEqual(s.renders,['final formatted reply']);
  s.frame();assert.equal(s.renders.length,1);
});
test('cancelling a pending stream prevents obsolete content from painting over an error',()=>{
  const s=streamHarness();s.painter.queue('obsolete reply');s.painter.cancel();s.painter.cancel();
  s.frame();assert.equal(s.callbacks.size,0);assert.equal(s.renders.length,0);
  assert.match(src,/finally\{painter\.cancel\(\)/);
});

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
  assert.match(src,/repoRow\.hidden=false/); // cloud models can explicitly attach one source
  assert.match(src,/repoSelect\.disabled=b/);
});

function taskPlanner(seed=null){
  const window={};
  const document={readyState:'loading',addEventListener(){}};
  const localStorage={getItem(key){return key==='rovor_chat_route_receipts_v1'&&seed?JSON.stringify(seed):null;}};
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


test('route strengths and weaknesses are labeled as hints, not invented rankings or quotas',()=>{
  assert.match(src,/modelEvidenceHint/);
  assert.match(src,/Name-only task clues/);
  assert.match(src,/Weaknesses unknown until tested/);
  assert.match(src,/Not enough recent confirmed local receipts/);
  assert.match(src,/free quota\/reset and actual fallback unverified/);
  assert.match(src,/recordReceipt\(model,'complete'/);
  assert.match(src,/recordReceipt\(target,'complete'/);
  assert.match(src,/end-to-end time includes queue/);
});

test('task routing uses real, recent per-model receipt reliability only with sufficient evidence',()=>{
  const catalog=['groq/fast:free','mistral/fast:free'],question='Give a quick answer';
  assert.equal(taskPlanner()(question,catalog).routes[0],'groq/fast:free');
  const now=Date.now();
  const evidence={
    'groq/fast:free':{ok:0,failed:5,elapsed:0,last:now},
    'mistral/fast:free':{ok:5,failed:0,elapsed:9000,last:now},
  };
  assert.equal(taskPlanner(evidence)(question,catalog).routes[0],'mistral/fast:free');
  evidence['groq/fast:free'].last=now-8*86400000;
  evidence['mistral/fast:free'].last=now-8*86400000;
  assert.equal(taskPlanner(evidence)(question,catalog).routes[0],'groq/fast:free',
    'stale performance observations must not influence choices');
});

