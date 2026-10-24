'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const page=fs.readFileSync(path.join(root,'workforce','index.html'),'utf8');
const app=page.match(/<script>([\s\S]*?)<\/script>/)?.[1];
const homepage=fs.readFileSync(path.join(root,'index.html'),'utf8');
const queue=JSON.parse(fs.readFileSync(path.join(root,'..','..','coordination','tasks.json'),'utf8'));
const bootstrap=JSON.parse(fs.readFileSync(path.join(root,'..','..','coordination','ghost-role-bootstrap.json'),'utf8'));
const policy=JSON.parse(fs.readFileSync(path.join(root,'..','..','coordination','ghost-provider-policy.json'),'utf8'));

test('Workforce HUD has real standalone native interactive source and six scrollable instruments',()=>{
 assert.ok(page.includes('<!doctype html>'));
 assert.ok(app&&app.length>14000);
 assert.doesNotThrow(()=>new vm.Script(app,{filename:'workforce/index.js'}));
 for(const id of ['queue','machine','timeline','fleet','models','results']){
  assert.match(page,new RegExp('id="'+id+'Preview"'));
  assert.match(page,new RegExp('id="'+id+'Cue"'));
 }
 assert.match(page,/overscroll-behavior:contain;touch-action:pan-y/);
 assert.match(page,/aria-modal="true"/);
 assert.match(page,/prefers-reduced-motion:reduce/);
});

test('Workforce rosters and 104-item development queue are source-grounded and separate from runtime jobs',()=>{
 assert.equal(queue.version,1);
 assert.ok(queue.tasks.length>50);
 assert.ok(bootstrap.roles.length>=7);
 const ids=bootstrap.roles.map(x=>x.id);
 for(const id of ['mike','jane','jesse','gale','gus','saul','hank']){
  assert.ok(ids.includes(id),id);
  assert.ok(app.includes("'"+id+"'"),id);
 }
 assert.match(app,/GitHub development tasks/);
 assert.match(page,/NOT runtime jobs/);
 assert.match(page,/Mac.*OmniRoute/);
 assert.match(page,/EXECUTION LINK: NOT VERIFIED/);
 assert.match(app,/state\.mode='unverified';state\.sha=null;state\.tasks=\[\]/);
});

test('Never send privileged commands or store keys: drafts are local and require explicit private controller',()=>{
 assert.equal(policy.control_plane.cloud_scheduler_enabled,false);
 assert.match(page,/APPROVE & QUEUE — UNAVAILABLE/);
 assert.match(page,/queue\.disabled=true/);
 assert.match(app,/local_draft_not_queued/);
 assert.match(app,/external_effects_authorized:false/);
 assert.match(app,/paid_fallback_authorized:false/);
 assert.match(page,/Do not enter passwords, API keys or client secrets/);
 assert.doesNotMatch(app,/method:\s*['"]POST|Authorization:\s*['"]Bearer/);
 assert.doesNotMatch(app,/localStorage|sessionStorage/);
 assert.doesNotMatch(app,/http:\/\/127\.0\.0\.1|http:\/\/localhost/);
});

test('GitHub queue and routing data share one verified commit SHA; unknown stays unverified',()=>{
 assert.match(app,/API\+'\/commits\/main'/);
 assert.match(app,/raw\.githubusercontent\.com/);
 assert.match(app,/Promise\.all\(paths\.map\(p=>getRaw\(p,sha,ctrl\.signal\)\)\)/);
 assert.match(app,/\^\[a-f0-9\]\{40\}\$/);
 assert.match(app,/if\(tasks\.version!==1/);
 assert.match(app,/state\.mode='verified';state\.sha=sha/);
 assert.match(app,/state\.mode='unverified';state\.sha=null;state\.tasks=\[\]/);
 assert.match(app,/15\*60\*1000/);
});

test('Homepage keeps native v8.9 as default, with opt-in Workforce deep link and both rollbacks',()=>{
 assert.match(homepage,/workforce\s*=\s*new URLSearchParams\(location\.search\)/);
 assert.match(homepage,/workforce \? '\.\/workforce\/' : '\.\/native-v8-9\/'/);
 assert.ok(fs.existsSync(path.join(root,'native','index.html')));
 assert.ok(fs.existsSync(path.join(root,'exact','index.html')));
 assert.equal((page.match(/data-detail="/g)||[]).length>=9,true);
});

test('Workforce HUD uses the actual ROVOR mark rather than a generic letter',()=>{
 const style=fs.readFileSync(path.join(root,'workforce','responsive-brand.css'),'utf8');
 assert.match(page,/class="brand-lockup"[^>]*href="\.\.\/"/);
 assert.equal((page.match(/src="\.\.\/rovor-mark\.svg"/g)||[]).length,2);
 assert.match(page,/class="core-logo"/);
 assert.doesNotMatch(page,/<div class="mark"><b>R<\/b>/);
 assert.doesNotMatch(page,/<div class="center-core"><strong>R<\/strong>/);
 assert.match(style,/\.brand-lockup img/);
 assert.match(style,/\.center-core \.core-logo/);
 assert.ok(fs.existsSync(path.join(root,'rovor-mark.svg')),'Authentic logo asset missing');
});

test('Workforce responsive modules preserve approved portrait and landscape geometry',()=>{
 const style=fs.readFileSync(path.join(root,'workforce','responsive-brand.css'),'utf8');
 assert.match(page,/href="\.\/responsive-brand\.css"/);
 assert.match(style,/@media\(min-width:901px\) and \(orientation:landscape\) and \(min-height:650px\)/);
 assert.match(style,/grid-template-columns:minmax\(0,1fr\) minmax\(0,1\.22fr\) minmax\(0,1fr\)/);
 assert.match(style,/@media\(orientation:portrait\) and \(min-width:700px\) and \(max-width:1100px\)/);
 assert.match(style,/grid-template-areas:"center center" "left right"/);
 assert.match(style,/@media\(max-width:699px\)/);
 assert.match(style,/grid-template-columns:repeat\(5,minmax\(0,1fr\)\)/);
 assert.match(style,/overscroll|scrollbar-gutter:stable/);
 assert.match(style,/\.center-nav\{position:absolute;bottom:/);
 assert.match(style,/overflow:hidden/);
});
