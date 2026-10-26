'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const path = require('node:path');
const root = path.resolve(__dirname, '..', 'exact');
const html = fs.readFileSync(path.join(root,'index.html'),'utf8');
const css = fs.readFileSync(path.join(root,'style.css'),'utf8');
const js = fs.readFileSync(path.join(root,'app.js'),'utf8');

test('the immersive reference is the original pixel-exact PNG, not a recreated layout',()=>{
 const bytes=fs.readFileSync(path.join(root,'reference.png'));
 assert.equal(bytes.subarray(0,8).toString('hex'),'89504e470d0a1a0a');
 assert.equal(bytes.readUInt32BE(16),1672);
 assert.equal(bytes.readUInt32BE(20),941);
 assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),
 '92a78f6cf5accf33b3bfd7fcb71c059aea3fc75ea21d3e8405d8963714fdeb59');
 assert.match(html,/id="referenceArt" src="reference.png"/);
 assert.match(css,/aspect-ratio:1672\/941/);
 assert.match(css,/\.immersive \.atmosphere\{display:none\}/);
});

test('the image remains interactive and keeps a warning outside the artwork',()=>{
 const views=['tasks','resources','activity','systems','quota','media','command','dashboard','github','settings'];
 for (const view of views) assert.ok(html.includes('data-view="'+view+'"'),view+' hit area missing');
 assert.match(html,/id="sourceStatus"/);
 assert.match(html,/VISUALS ≠ LIVE TELEMETRY|example task counts, health, quotas/i);
 assert.match(js,/function openView\(view\)/);
 assert.match(js,/function renderView\(\)/);
 assert.match(js,/Escape/);
 assert.match(js,/event\.metaKey/);
 assert.match(js,/event\.ctrlKey/);
 assert.match(js,/state\.artMode==='exact'\?'reference\.png':'reference-blue\.webp'/);
});

test('GitHub data is pinned to one validated revision with modest polling',()=>{
 assert.match(js,/\/commits\/main/);
 assert.match(js,/\^\[a-f\\d\]\{40\}\$/i);
 assert.ok(js.includes('/coordination/tasks.json'));
 assert.ok(js.includes('/coordination/work-routing.json'));
 assert.match(js,/const \[queue,routing\]=await Promise\.all/);
 assert.match(js,/setInterval\(\(\)=>verify\(\),300000\)/);
 assert.match(js,/if\(!manual&&document\.hidden\)return/);
 assert.match(js,/A task claim is not a live computer session/);
 assert.doesNotMatch(js,/authorization:\s*['"]/i);
 assert.doesNotMatch(html,/data-action="start-worker"/);
});
