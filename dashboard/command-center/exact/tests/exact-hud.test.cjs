'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const base=path.resolve(__dirname,'..');
const file=name=>fs.readFileSync(path.join(base,name));
const str=name=>file(name).toString('utf8');

test('original PNG is a real unmodified 1672x941 visual reference',()=>{
 const image=file('reference.png');
 assert.ok(image.length>2_000_000);
 assert.equal(image.subarray(0,8).toString('hex'),'89504e470d0a1a0a');
 assert.equal(image.readUInt32BE(16),1672);
 assert.equal(image.readUInt32BE(20),941);
 const alternate=file('reference-blue.webp');
 assert.equal(alternate.toString('ascii',0,4),'RIFF');
 assert.equal(alternate.toString('ascii',8,12),'WEBP');
});
test('visual artwork is enhanced by actual interactive controls',()=>{
 const html=str('index.html');
 assert.match(html,/src="reference\.png"/);
 assert.ok((html.match(/class="hotspot/g)||[]).length>=11);
 for(const name of ['tasks','resources','activity','systems','quota','media','command','github','settings'])
   assert.ok(html.includes('data-view="'+name+'"'),'missing '+name);
 for(const id of ['referenceArt','overlay','drawerContent','sourceStatus','refresh','commandButton','fullScreen'])
   assert.ok(html.includes('id="'+id+'"'),'missing '+id);
 assert.match(html,/illustrative, not live system measurements/i);
});
test('GitHub data is bound to an exact verified commit; no fake host presence',()=>{
 const script=str('app.js');
 assert.match(script,/api\.github\.com\/repos/);
 assert.match(script,/raw\.githubusercontent\.com/);
 assert.match(script,/commit.*sha|head\.sha/);
 assert.match(script,/\/coordination\/tasks\.json/);
 assert.match(script,/\/coordination\/work-routing\.json/);
 assert.match(script,/setInterval\(\(\)=>verify\(\),300000\)/);
 assert.match(script,/task claim is not a live computer session/i);
 assert.ok(!/Authorization:|Bearer [A-Za-z0-9]/.test(script));
});
test('offline worker is scoped to static same-origin assets only',()=>{
 const sw=str('service-worker.js');
 assert.match(sw,/new URL\(req\.url\)\.origin!==self\.location\.origin/);
 assert.ok(sw.includes("'./reference.png'"));
 assert.ok(sw.includes("'./reference-blue.webp'"));
 assert.ok(!sw.includes('api.github.com'));
 assert.ok(!sw.includes('raw.githubusercontent.com'));
});