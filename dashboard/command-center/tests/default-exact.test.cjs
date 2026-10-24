'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const read=(name)=>fs.readFileSync(path.join(root,name),'utf8');

test('main ROVOR HUD redirects before any old style or script executes',()=>{
 const html=read('index.html');
 assert.match(html,/location\.replace\(next\.href\)/);
 assert.match(html,/new URL\('\.\/exact\/', location\.href\)/);
 assert.match(html,/<noscript><meta http-equiv="refresh" content="0;url=\.\/exact\/" \/><\/noscript>/);
 assert.ok(html.indexOf('location.replace(next.href)')<html.indexOf('<link rel="stylesheet"'),'redirect should run before old CSS');
});

test('exact image is first render; buttons and verified inspector still work',()=>{
 const html=read('exact/index.html');
 const app=read('exact/app.js');
 const style=read('exact/style.css');
 for(const id of ['referenceArt','overlay','drawerContent','sourceStatus','refresh','commandButton','fullScreen']){
   assert.ok(html.includes('id="'+id+'"'),'missing '+id);
 }
 assert.match(html,/src="reference\.png"/);
 assert.match(style,/\.immersive \.atmosphere\{display:none\}/);
 assert.ok(html.match(/class="hotspot/g)?.length>=11);
 assert.match(app,/coordination\/tasks\.json/);
 assert.match(app,/coordination\/work-routing\.json/);
 assert.match(app,/state\.mode='verified'/);
 assert.match(app,/task claim is not a live computer session/i);
});

test('exact PWA assets exist and never cache private or dynamic GitHub data',()=>{
 const html=read('exact/index.html');
 const script=read('exact/app.js');
 const sw=read('exact/service-worker.js');
 const manifest=JSON.parse(read('exact/manifest.webmanifest'));
 assert.match(html,/manifest\.webmanifest/);
 assert.match(script,/navigator\.serviceWorker\.register/);
 assert.match(sw,/\/exact\//);
 assert.match(sw,/reference\.png/);
 assert.doesNotMatch(sw,/api\.github\.com|raw\.githubusercontent\.com/);
 assert.equal(manifest.scope,'./');
 assert.equal(manifest.display,'standalone');
});

test('widescreen launches pixel-identical reference view without extra toolbar',()=>{
 const app=read('exact/app.js');
 const css=read('exact/style.css');
 assert.ok(app.includes("immersive:window.matchMedia('(min-width: 1024px) and (min-aspect-ratio: 3/2)').matches"));
 assert.ok(css.includes('.immersive .utility,.immersive .bottom-status,.immersive .mobile-nav{display:none!important}'));
 assert.ok(css.includes('.immersive .atmosphere{display:none}'));
 assert.ok(css.includes('width:min(100vw,calc(100svh * 1672 / 941))'));
 assert.ok(app.includes("event.key.toLowerCase()==='i'"));
 assert.ok(app.includes('state.immersive=false;applySettings()'));
});
