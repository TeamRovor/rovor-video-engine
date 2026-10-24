'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'native','index.html'),'utf8');

test('v8.6 is a standalone native interface with all images embedded',()=>{
 assert.match(html,/<!DOCTYPE html>/i);
 assert.match(html,/<title>ROVOR DIGITAL — Interactive HUD v8\.6/);
 assert.ok(html.length>1000000, 'Expected self-contained production artifact');
 assert.ok((html.match(/data:image\//g)||[]).length>=5,'Bundled artwork was lost');
 assert.doesNotMatch(html,/<(?:img|script|link)\b[^>]*(?:src|href)="(?:assets\/|\.\/)\b/i);
 assert.ok(!html.includes('<div class="top-glyph"></div>'),'Stray header glyph must stay removed');
 assert.match(html,/Stray top-glyph removed:/);
});
test('native controls are real elements and inline JavaScript is syntactically valid',()=>{
 for(const key of ['tasks','activity','systems','quota','media','dashboard','github','settings']){
   assert.ok(html.includes('data-view="'+key+'"'),'Missing native action '+key);
 }
 assert.match(html,/id="taskCount"/);
 assert.match(html,/aria-modal="true"/);
 assert.match(html,/window\.ROVOR_NATIVE/);
 assert.match(html,/coordination\/tasks\.json/);
 assert.match(html,/coordination\/work-routing\.json/);
 const matches=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
 assert.equal(matches.length,1);
 assert.doesNotThrow(()=>new vm.Script(matches[0][1],{filename:'native-v8.6.js'}));
});
test('root defaults to native without removing the older /exact/ rollback',()=>{
 const rootHtml=fs.readFileSync(path.join(root,'index.html'),'utf8');
 assert.match(rootHtml,/new URL\('\.\/native\/', location\.href\)/);
 assert.match(rootHtml,/url=\.\/native\//);
 assert.ok(rootHtml.indexOf('location.replace(next.href)')<rootHtml.indexOf('<link rel="stylesheet"'));
 assert.ok(fs.existsSync(path.join(root,'exact','index.html')));
});
