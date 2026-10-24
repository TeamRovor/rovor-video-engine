'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'native','index.html'),'utf8');
const js=html.split('<script>')[1]?.split('</script>')[0];

test('native v8.8 adds real overflow cues without altering dashboard cards',()=>{
  assert.match(html,/<title>ROVOR DIGITAL — Interactive HUD v8\.8/);
  assert.ok((html.match(/class="panel-expand"/g)||[]).length===6);
  assert.match(html,/\.panel\.preview-has-more > \.panel-content::after/);
  assert.match(js,/const canScroll=node\.scrollHeight>node\.clientHeight\+4/);
  assert.match(js,/classList\.toggle\('preview-has-more',canScroll&&remaining>5\)/);
  assert.match(js,/addEventListener\('scroll',\(\)=>updatePreviewCue\(node\),\{passive:true\}\)/);
  assert.match(js,/window\.addEventListener\('resize',\(\)=>requestAnimationFrame\(updateAllPreviewCues\)/);
  assert.ok(!html.includes('<div class="top-glyph"></div>'));
});

test('refresh preserves positions for every preview and rediscovers overflow',()=>{
  assert.ok(html.includes('id="quotaPreview"'));
  assert.ok(html.includes('id="sourcePreview"'));
  assert.match(js,/const beforeRefreshPositions=Object\.fromEntries/);
  for(const id of ['tasksPanel','workloadPanel','activityPanel','systemsList','quotaPreview','sourcePreview']){
    assert.ok(js.includes("'"+id+"'"),id);
  }
  assert.match(js,/for\(const \[id,pos\] of Object\.entries\(beforeRefreshPositions\)\)/);
  assert.match(js,/if\(state\.mode==='verified'\)/);
  assert.match(js,/requestAnimationFrame\(updateAllPreviewCues\)/);
});

test('GitHub is read-only and inline application remains valid',()=>{
  assert.ok(js);
  assert.doesNotThrow(()=>new vm.Script(js,{filename:'native-v8.8.js'}));
  assert.match(js,/coordination\/tasks\.json/);
  assert.match(js,/coordination\/work-routing\.json/);
  assert.match(html,/A CLAIMED TASK IS NOT A RUNNING MAC WORKER/);
  assert.doesNotMatch(js,/method\s*:\s*['"](?:POST|PATCH|DELETE)['"]/i);
});
