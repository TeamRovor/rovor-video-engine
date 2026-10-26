'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '..', 'native', 'index.html'), 'utf8');
const head = html.split('<script>')[0];
const js = html.split('<script>')[1].split('</script>')[0];

test('all six instrument panels expose accessible local previews and expansion',()=>{
  const starts=['tasksPanel','workloadPanel','activityPanel','systemsList'];
  for(const id of starts) assert.match(head,new RegExp('id="'+id+'"[^>]+role="region"[^>]+tabindex="0"'));
  assert.ok((head.match(/class="panel-expand"/g)||[]).length===6);
  assert.match(head,/class="quota-details preview-scroll"/);
  assert.match(head,/class="feed-detail preview-scroll"/);
  assert.match(head,/scrollbar-width:thin/);
  assert.match(head,/overscroll-behavior:contain/);
  assert.match(head,/max-width:1100px\) and \(orientation:portrait/);
});

test('tasks and activity are not artificially restricted to five preview rows',()=>{
  assert.ok(!js.includes('.slice(0,5).forEach(x=>t.append(taskButton(x)))'));
  assert.ok(!js.includes('.slice(0,5);ordered.forEach'));
  assert.match(js,/Object\.entries\(previewPositions\)/);
  assert.match(js,/\.scrollTop=pos/);
});

test('expanded panels use same cinematic blue frame, with keyboard and motion safety',()=>{
  assert.match(head,/\.screen\{position:fixed;inset:0;display:flex;align-items:center;justify-content:center/);
  assert.match(head,/\.drawer\{isolation:isolate/);
  assert.match(head,/\.drawer-inner\{flex:1 1 auto;min-height:0;overflow-y:auto/);
  assert.match(head,/class="drawer-footnote"/);
  assert.match(head,/\.drawer \.drawer-footnote\{flex:0 0 auto;position:relative;padding:/);
  assert.ok(!head.includes('\\\\n\\n.drawer .drawer-footnote'),'Literal escape sequence must not disable footnote styling');
  assert.match(js,/const origin = source \|\| document\.activeElement/);
  assert.match(js,/prefers-reduced-motion: reduce/);
  assert.match(js,/focusAnimation=drawer\.animate/);
  assert.match(js,/if\(returnFocus\?\.isConnected\) returnFocus\.focus\(\)/);
  assert.ok(!html.includes('<div class="top-glyph"></div>'));
});

test('all repository telemetry remains read-only, pinned and never impersonates a Mac worker',()=>{
  assert.match(js,/coordination\/tasks\.json/);
  assert.match(js,/coordination\/work-routing\.json/);
  assert.match(js,/NOT MONITORED/);
  assert.match(js,/NOT CONNECTED/);
  assert.match(html,/A CLAIMED TASK IS NOT A RUNNING MAC WORKER/);
  assert.doesNotMatch(js,/method\s*:\s*['"](?:POST|PATCH|DELETE)['"]/i);
});
