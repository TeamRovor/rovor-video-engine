'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const vm=require('node:vm');
const base=path.resolve(__dirname,'../exact');
const html=fs.readFileSync(path.join(base,'index.html'),'utf8');
const png=fs.readFileSync(path.join(base,'reference.png'));
const blue=fs.readFileSync(path.join(base,'reference-blue.webp'));

test('exact screenshot asset is byte-identical to user supplied 1672x941 reference',()=>{
  assert.equal(crypto.createHash('sha256').update(png).digest('hex'),
    '92a78f6cf5accf33b3bfd7fcb71c059aea3fc75ea21d3e8405d8963714fdeb59');
  assert.ok(png.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])));
  assert.equal(png.readUInt32BE(16),1672);assert.equal(png.readUInt32BE(20),941);
  assert.equal(crypto.createHash('sha256').update(blue).digest('hex'),
    'ccf57bb6e0f2a8d37379cb4e9d6dd427771b9a7a41012ec6451b774283f1c8e9');
});

test('all pictured panels and dock controls are actual accessible HTML buttons',()=>{
  assert.equal((html.match(/class="hotspot(?: [^"]+)?"/g)||[]).length,13);
  for(const key of ['tasks','resources','activity','systems','quota','media','dashboard','github','settings','command']){
    assert.ok(html.includes('data-view="'+key+'"'),key);
  }
  assert.match(html,/aria-modal="true"/);
  assert.match(html,/REFERENCE-ACCURATE VISUAL LAYER/);
  assert.match(html,/VISUALS ≠ LIVE TELEMETRY|visuals|source-status/i);
  assert.match(html,/src="reference.png"/);
});

test('interactive source script is syntactically valid and read-only GitHub-pinned',()=>{
  const script=html.match(/<script>([\s\S]+?)<\/script>/);
  assert.ok(script,'inline interactive script required');
  assert.doesNotThrow(()=>new vm.Script(script[1]));
  assert.match(script[1],/\/commits\/main/);
  assert.match(script[1],/coordination\/tasks\.json/);
  assert.match(script[1],/coordination\/work-routing\.json/);
  assert.match(script[1],/180000/);
  assert.match(script[1],/state\.mode='verified'/);
  assert.match(script[1],/state\.mode='error'/);
  assert.match(script[1],/NOT PROVEN BY GITHUB/);
  assert.match(script[1],/API quota|API QUOTA/);
  assert.doesNotMatch(script[1],/fetch\([^)]*POST|method:\s*['"]POST/);
});

test('immersive display preserves exact image, disabling painterly animation',()=>{
  assert.match(html,/\.immersive \.atmosphere\{display:none\}/);
  assert.match(html,/\.immersive \.stage\{/);
  assert.match(html,/1672\s*\/\s*941/);
  assert.match(html,/id="immersiveButton"/);
});
