'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const read=n=>fs.readFileSync(path.join(root,n),'utf8');
const html=read('index.html');
const css=read('electric-blue-theme.css');
const app=read('app.js');
const worker=read('service-worker.js');

test('Blue-only theme loads after all legacy styles and is part of offline shell',()=>{
  const files=['styles.css','reference-hud.css','hud-experience.css','cinematic-layout.css','electric-blue-theme.css'];
  const positions=files.map(name=>html.indexOf('href="'+name+'"'));
  positions.forEach((n,i)=>assert.ok(n>0,files[i]));
  positions.slice(1).forEach((n,i)=>assert.ok(n>positions[i],'Must load last: '+files[i+1]));
  assert.ok(worker.includes("'./electric-blue-theme.css'"));
  assert.match(worker,/electric-blue-theme\\.css/);
  assert.match(worker,/rovor-command-center-shell-v7/);
});

test('No green indicators in blue theme, including live source and claimed work',()=>{
  for (const required of [
    'body[data-source-mode="live"] .header-status-led',
    'body[data-source-mode="live"] .source-live-pill::before',
    '.status-light.active', '.status-light.ok', '.evidence-dot.verified',
    '.task-state.active', '.pill.verified', '.sync-pill.live',
    '.workload-fill.active', '.header-status-led'
  ]) assert.ok(css.includes(required),'Missing override for '+required);
  assert.doesNotMatch(css,/#[0-9a-f]{6}[^\n]*(?:green|lime)/i);
  assert.match(css,/--green:#90d7ff/);
  assert.match(css,/background:#62baff!important/);
});

test('Alert and offline states remain explicit and distinguishable in blue-only palette',()=>{
  for(const selector of ['.status-light.blocked','.pill.blocked','.sync-pill.error','.sync-pill.snapshot','body[data-source-mode="error"] .header-status']) {
    assert.ok(css.includes(selector),'Missing safety state style '+selector);
  }
  assert.match(css,/border:1px dashed/);
  assert.match(css,/\.warning-box\{border-style:dashed!important\}/);
  assert.ok(app.includes("'SYNC FAILED'"));
  assert.ok(app.includes("'OFFLINE SNAPSHOT'"));
  assert.ok(app.includes("'LIVE GITHUB'"));
  assert.doesNotMatch(app,/blocked:'#ff8da5'/);
  assert.match(app,/blocked:'#aac0e4'/);
});

test('No fake metrics or new polling logic were added for theme change',()=>{
  assert.match(app,/REFRESH_MS = 180000/);
  assert.match(app,/EXTRAS_MS = 900000/);
  assert.ok(!css.includes('fetch('));
  assert.ok(!css.includes('SYSTEMS ONLINE'));
});
