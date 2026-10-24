'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const read=name=>fs.readFileSync(path.join(root,name),'utf8');
const markup=read('index.html');
const css=read('cinematic-layout.css');
const sw=read('service-worker.js');
const js=read('cinematic-layout.js');

test('reference cockpit fits a defined 16:9 screen and keeps true data panel semantics',()=>{
  for(const part of ['ACTIVE TASKS','TASK DISTRIBUTION','RECENT ACTIVITY','SYSTEM HEALTH','GITHUB ANALYTICS','SOURCE FEED']){
    assert.ok(markup.includes(part),part);
  }
  for(const id of ['hudToolsBtn','hudTools','sourceFeedMode','sourceFeedState','sourceFeedCommit','hudWorkspaceClose']){
    assert.ok(markup.includes('id="'+id+'"'),id);
  }
  assert.match(css,/grid-template-rows:76px 25px minmax\(0,1fr\) 72px 28px/);
  assert.match(css,/height:100svh/);
  assert.match(css,/\.reference-console\s*\{/);
  assert.match(css,/\.reactor-core::after/);
  assert.match(css,/mask:url\("\.\/rovor-mark\.svg"\)/);
  assert.match(css,/body\.hud-workspace-open main\{display:block!important\}/);
  assert.match(css,/@media \(max-width:759px\)/);
  assert.ok(!markup.includes('99% OPERATIONAL'),'Never fake screenshot telemetry');
  assert.ok(!markup.includes('196,032 / 200,000'),'Never fake screenshot API quotas');
});

test('the verified GitHub data layer remains intact and no new API polling is introduced',()=>{
  const app=read('app.js');
  assert.match(app,/RovorCinematicHUD\.refresh\(state\.raw,state\)/);
  assert.match(app,/REFRESH_MS = 180000/);
  assert.match(app,/EXTRAS_MS = 900000/);
  assert.match(js,/RovorCinematicHUD=\{refresh,syncWorkspace,setTools\}/);
  assert.ok(!js.includes('fetch('));
  assert.ok(!js.includes('localStorage'));
});

test('service worker installs actual cockpit files while preserving opt-in planet imagery',()=>{
  assert.ok(sw.includes("'./cinematic-layout.css'"));
  assert.ok(sw.includes("'./cinematic-layout.js'"));
  assert.match(sw,/shell-v6/);
  assert.ok(sw.includes('earth-blue-marble.png'));
  assert.ok(sw.includes('earth-night.png'));
});

test('tools open and close, source status never claims stale data is live, and workspaces close',()=>{
  const els={};
  const listeners={};
  const classes=new Set();
  const body={classList:{
    contains:n=>classes.has(n),
    toggle:(n,force)=>{const val=force??!classes.has(n);if(val)classes.add(n);else classes.delete(n);return val;}
  },dataset:{}};
  const item=id=>{
    if(!els[id]) els[id]={id,hidden:false,attrs:{},dataset:{},listeners:{},textContent:'',
      setAttribute(n,v){this.attrs[n]=v;},addEventListener(n,fn){this.listeners[n]=fn;},
      click(){if(id==='tab-button-overview'){tab.dataset.tab='overview';classes.delete('hud-workspace-open');}},
    };
    return els[id];
  };
  const tab={dataset:{tab:'overview'},getAttribute:()=> 'true'};
  const nav=item('tabbar');
  const doc={body,
    getElementById:item,
    querySelector(s){return s==='.tabbar'?nav:s.includes('[role="tab"]')?tab:null;},
    addEventListener(n,fn){listeners[n]=fn;}
  };
  const env={document:doc,requestAnimationFrame:fn=>fn()};
  vm.runInNewContext(js,env);
  const hud=env.RovorCinematicHUD;
  assert.ok(hud);
  assert.equal(item('hudTools').inert,true);
  hud.setTools(true);
  assert.equal(item('hudTools').inert,false);
  assert.equal(item('hudToolsBtn').attrs['aria-expanded'],'true');
  hud.setTools(false);
  assert.equal(item('hudToolsBtn').attrs['aria-expanded'],'false');
  hud.refresh({repo_snapshot:{commit:'123456789abcDEF'}},{syncMode:'live'});
  assert.equal(item('sourceFeedMode').textContent,'LIVE GITHUB');
  assert.equal(item('sourceFeedCommit').textContent,'SHA 123456789abc');
  hud.refresh({repo_snapshot:{commit:'123456789abcDEF'}},{syncMode:'snapshot'});
  assert.equal(item('sourceFeedMode').textContent,'HISTORICAL');
  assert.equal(body.dataset.cockpitConnected,'false');
  tab.dataset.tab='tasks';
  hud.syncWorkspace();
  assert.ok(classes.has('hud-workspace-open'));
  assert.equal(item('hudWorkspaceClose').hidden,false);
  tab.dataset.tab='overview';
  hud.syncWorkspace();
  assert.ok(!classes.has('hud-workspace-open'));
  assert.equal(item('hudWorkspaceClose').hidden,true);
});
