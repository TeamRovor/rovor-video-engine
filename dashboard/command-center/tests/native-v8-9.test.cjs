'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const base=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(base,'native-v8-9','index.html'),'utf8');
test('v8.9 native UI is self-contained and previous versions remain accessible',()=>{
 assert.match(html,/ROVOR DIGITAL — Interactive HUD v8\.9/);
 assert.ok(html.length>1200000,'Missing embedded visual assets');
 assert.ok((html.match(/data:image\//g)||[]).length>=5);
 assert.ok(!html.includes('<div class="top-glyph"></div>'));
 assert.ok(fs.existsSync(path.join(base,'native','index.html')),'Missing v8.5 rollback');
 assert.ok(fs.existsSync(path.join(base,'exact','index.html')),'Missing exact-image rollback');
});
test('all six cards are real scroll regions with an affordance and summary-count switch',()=>{
 for(const id of ['tasksPanel','workloadPanel','activityPanel','systemsList','quotaPreview','sourcePreview']){
   assert.match(html,new RegExp('id="'+id+'"'));
 }
 assert.match(html,/role="region"/);
 assert.match(html,/class="panel-body preview-scroll"/);
 assert.match(html,/id="taskScopeButton"/);
 assert.match(html,/preview-has-more/);
 assert.match(html,/SCROLL  ↓/);
 assert.match(html,/\.task-entry\s*\{[^}]*flex-shrink:\s*0/s);
 assert.match(html,/min-height:\s*40px/);
 assert.match(html,/min-height:\s*44px/);
});
test('focus modules match cockpit style and preserve scroll positions',()=>{
 assert.match(html,/\.drawer\{isolation:isolate;/);
 assert.match(html,/\.screen\{position:fixed;/);
 assert.match(html,/previewPositions/);
 assert.match(html,/aria-modal="true"/);
 assert.match(html,/Escape/);
 assert.match(html,/prefers-reduced-motion:reduce/);
 assert.match(html,/coordination\/tasks\.json/);
 assert.match(html,/coordination\/work-routing\.json/);
 assert.match(html,/state\.mode='verified'/);
 const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
 const inline=scripts.filter(m=>!m[0].includes(' src='));
 assert.equal(inline.length,1,'original native HUD must retain exactly one inline application script');
 assert.equal(scripts.length,2,'only one scoped external workload popup script is permitted');
 assert.match(html,/<script src="\.\/workload-popup\.js"><\/script>/);
 assert.doesNotThrow(()=>new vm.Script(inline[0][1]));
});
test('new route is default but older pages still exist',()=>{
 const home=fs.readFileSync(path.join(base,'index.html'),'utf8');
 assert.match(home,/workforce \? '\.\/workforce\/' : '\.\/native-v8-9\/'/);
 assert.match(home,/new URLSearchParams\(location\.search\)/);
 assert.match(home,/url=\.\/native-v8-9\//);
});
