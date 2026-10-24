'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const vm=require('node:vm');
const base=path.resolve(__dirname,'../exact');
const html=fs.readFileSync(path.join(base,'index.html'),'utf8');
const js=fs.readFileSync(path.join(base,'app.js'),'utf8');
const css=fs.readFileSync(path.join(base,'style.css'),'utf8');
const png=fs.readFileSync(path.join(base,'reference.png'));
const blue=fs.readFileSync(path.join(base,'reference-blue.webp'));

test('reference asset is byte-identical to 1672x941 target',()=>{
 assert.equal(crypto.createHash('sha256').update(png).digest('hex'),
   '92a78f6cf5accf33b3bfd7fcb71c059aea3fc75ea21d3e8405d8963714fdeb59');
 assert.ok(png.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])));
 assert.equal(png.readUInt32BE(16),1672);assert.equal(png.readUInt32BE(20),941);
 assert.equal(crypto.createHash('sha256').update(blue).digest('hex'),
   'ccf57bb6e0f2a8d37379cb4e9d6dd427771b9a7a41012ec6451b774283f1c8e9');
});

test('every pictured panel, control and navigation item is interactive',()=>{
 assert.equal((html.match(/class="hotspot(?: [^"]+)?"/g)||[]).length,13);
 for(const key of ['tasks','resources','activity','systems','quota','media','dashboard','github','settings','command']) {
   assert.ok(html.includes('data-view="'+key+'"'),key);
 }
 assert.match(html,/aria-modal="true"/);
 assert.match(html,/REFERENCE-ACCURATE VISUAL LAYER/);
 assert.match(html,/sourceStatus/);
 assert.match(html,/src="reference.png"/);
 assert.match(html,/src="app.js"/);
 assert.match(html,/href="style.css"/);
});

test('external interactive script is valid and pinned to one GitHub commit',()=>{
 assert.doesNotThrow(()=>new vm.Script(js));
 assert.match(js,/\/commits\/main/);
 assert.match(js,/coordination\/tasks\.json/);
 assert.match(js,/coordination\/work-routing\.json/);
 assert.match(js,/setInterval\(\(\)=>verify\(\),300000\)/);
 assert.match(js,/state\.mode='verified'/);
 assert.match(js,/state\.mode='error'/);
 assert.match(js,/task claim is not a live computer session/i);
 assert.match(js,/API quota|API QUOTA/);
 assert.doesNotMatch(js,/fetch\([^)]*POST|method:\s*['"]POST/i);
});

test('immersive display preserves reference pixels without overlay animation',()=>{
 assert.match(css,/\.immersive \.atmosphere\{display:none\}/);
 assert.match(css,/\.immersive \.stage\{/);
 assert.match(css,/1672\s*\/\s*941/);
 assert.match(html,/id="immersiveButton"/);
 assert.doesNotMatch(html,/class="illustrative"/);
});
