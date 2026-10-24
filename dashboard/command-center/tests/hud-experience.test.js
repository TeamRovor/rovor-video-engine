'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
const sw=fs.readFileSync(path.join(root,'service-worker.js'),'utf8');
const style=fs.readFileSync(path.join(root,'hud-experience.css'),'utf8');
const source=fs.readFileSync(path.join(root,'hud-experience.js'),'utf8');
const earth=require('../orbital-earth.js');
const commands=require('../hud-experience.js');

test('kinetic HUD uses bundled scripts and accessible working controls, not images alone',()=>{
  for(const id of ['earthCanvas','reactorStage','coreAction','hudCommandDialog','hudCommandSearch','hudCommandResults','hudDrawer','hudDrawerTitle','hudDrawerBody','earthSpeedBtn','earthPauseBtn','earthResetBtn','hudCommandBtn','hudFullscreenBtn','routingInspectBtn','hudHelpBtn']) {
    assert.match(html,new RegExp('id="'+id+'"'),id+' missing');
  }
  for(const file of ['orbital-earth.js','hud-experience.js','hud-experience.css']) {
    assert.ok(html.includes(file),'Missing inclusion '+file);
    assert.ok(sw.includes("'./"+file+"'"),'Not cached for offline shell '+file);
  }
  assert.ok(html.indexOf('orbital-earth.js')<html.indexOf('hud-experience.js'));
  assert.ok(html.indexOf('hud-experience.js')<html.indexOf('app.js'));
  assert.match(sw,/rovor-command-center-shell-v5/);
  assert.match(html,/aria-modal="true"/);
  assert.match(style,/prefers-reduced-motion:reduce/);
  assert.ok(!source.includes('https://cdn.') && !source.includes('https://unpkg.com') && !source.includes('https://cdnjs.'));
});

test('Earth texture is deterministic, recognises land and produces ocean/land contrast',()=>{
  assert.equal(earth.DEFAULT_REVOLUTION_SECONDS,220);
  assert.equal(earth.isLand(-110,43,.5),true);
  assert.equal(earth.isLand(-150,0,.5),false);
  assert.equal(earth.isLand(130,-24,.5),true);
  assert.equal(earth.createRenderer(null),null);
  let result;
  const ctx={createImageData:(w,h)=>({width:w,height:h,data:new Uint8ClampedArray(w*h*4)}),
    putImageData:(img)=>{result=img}};
  const doc={createElement:()=>({width:0,height:0,getContext:(name)=>name==='2d'?ctx:null})};
  const map=earth.createTexture(doc,64,32);
  assert.equal(map.width,64);assert.equal(map.height,32);
  const pixels=new Set();
  for(let i=0;i<result.data.length;i+=4)pixels.add(result.data[i]+','+result.data[i+1]+','+result.data[i+2]);
  assert.ok(pixels.size>30,'Earth texture should contain varied terrain, not a static blue circle');
});

test('Command palette exposes navigation and safe read-only operations',()=>{
  const tasks=[{id:'blocked-host',title:'Verify Mac connector',status:'blocked'},
    {id:'done-thing',title:'Old complete task',status:'done'}];
  const list=commands.commands({tasks});
  const titles=list.map(x=>x.title);
  assert.ok(titles.includes('Open Dashboard'));
  assert.ok(titles.includes('Open GitHub'));
  assert.ok(titles.includes('Refresh GitHub'));
  assert.ok(titles.includes('Verify Mac connector'));
  assert.ok(!titles.includes('Old complete task'));
  assert.ok(list.filter(x=>x.kind==='view').length===5);
  assert.ok(!list.some(x=>/start worker|publish social|send email|delete/i.test(x.title)));
});

test('keyboard, reduced motion, and renderer lifecycle are wired',()=>{
  assert.match(source,/event\.metaKey/);
  assert.match(source,/event\.ctrlKey/);
  assert.match(source,/event\.key==='Escape'/);
  assert.match(source,/setPointerCapture/);
  assert.match(source,/getElementById\('statusFilter'\)/);
  assert.match(source,/data-filter-status/);
  const engine=fs.readFileSync(path.join(root,'orbital-earth.js'),'utf8');
  assert.match(engine,/document\.hidden|doc\?\.hidden/);
  assert.match(engine,/cancelAnimationFrame/);
  assert.match(engine,/prefers-reduced-motion: reduce/);
  assert.match(engine,/webglcontextlost|createRenderer/);
  assert.match(engine,/DEFAULT_REVOLUTION_SECONDS/);
  assert.match(engine,/earth-blue-marble\\.png/);
  assert.match(engine,/earth-night\\.png/);
  assert.match(engine,/uNightMap/);
  assert.match(engine,/uHasNight/);
  assert.match(sw,/IMAGE_ASSETS/);
  assert.ok(sw.includes('earth-blue-marble.png'));
  assert.ok(sw.includes('earth-night.png'));
});
