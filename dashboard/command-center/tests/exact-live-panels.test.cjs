'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const base=path.resolve(__dirname,'../exact');
const read=(name)=>fs.readFileSync(path.join(base,name),'utf8');
const html=read('index.html');
const css=read('live-panels.css');
const js=read('live-panels.js');
const app=read('app.js');
const sw=read('service-worker.js');

test('Original visual reference remains the initial 1:1 image and overlays are opt-in',()=>{
  assert.match(html,/id="referenceArt" src="reference\.png"/);
  assert.match(html,/id="livePanels" class="live-panels" hidden/);
  assert.match(html,/id="liveDataButton" aria-pressed="false"/);
  assert.match(css,/\.live-panels\[hidden\]\{display:none!important\}/);
  assert.match(css,/\.telemetry-tasks\{left:3\.3%;top:16\.7%/);
  assert.match(css,/\.telemetry-health\{left:70\.1%;top:15%/);
  assert.ok(html.indexOf('<script src="app.js">')<html.indexOf('<script src="live-panels.js">'));
  assert.match(css,/@media\(max-width:580px\)/);
});

test('Extra panels use the existing SHA-verified state, without independent polling',()=>{
  assert.match(js,/const root = window\.ROVOR_HUD/);
  assert.match(js,/s\.mode === 'verified'/);
  assert.match(js,/rovor:source/);
  assert.doesNotMatch(js,/fetch\s*\(/);
  assert.doesNotMatch(js,/setInterval|setTimeout/);
  assert.doesNotMatch(js,/authorization|apikey|private[_-]?key/i);
  assert.match(app,/new CustomEvent\('rovor:source'/);
  assert.match(app,/coordination\/tasks\.json/);
  assert.match(app,/coordination\/work-routing\.json/);
});

test('Panels never mark private executor, camera or provider quota online',()=>{
  assert.match(js,/NOT VERIFIED/);
  assert.match(js,/NOT MONITORED/);
  assert.match(js,/NOT CONNECTED/);
  assert.match(js,/NO VERIFIED LIVE DATA/);
  assert.match(js,/Mac hardware usage/);
  assert.doesNotMatch(js,/99% OPERATIONAL|98% REMAINING|196,032 \/ 200,000/);
});

test('PWA updates offline HTML and data-layer shell, but does not cache raw GitHub',()=>{
  assert.match(sw,/rovor-exact-hud-shell-v4/);
  assert.ok(sw.includes("'./live-panels.js'"));
  assert.ok(sw.includes("'./live-panels.css'"));
  assert.ok(sw.includes("'./earth-motion.css'"));
  assert.match(read('earth-motion.css'),/earth-surface-turn 240s/);
  assert.match(read('earth-motion.css'),/prefers-reduced-motion/);
  assert.match(html,/id="earthMotion" hidden/);
  assert.match(app,/earthMotion:false/);
  assert.match(app,/id="earthMotionMode"/);
  assert.match(sw,/live-panels\\.js/);
  assert.match(sw,/live-panels\\.css/);
  assert.doesNotMatch(sw,/api\.github\.com|raw\.githubusercontent\.com/);
});

test('Panel toggle initially hidden, and verified event never creates API calls',()=>{
  const els={};
  const docsListeners={};
  let calls=0;
  function node(tag='div'){
    return {tagName:tag.toUpperCase(),children:[],dataset:{},style:{},attrs:{},hidden:false,
      classList:{toggle(){}},setAttribute(k,v){this.attrs[k]=v;},
      append(...n){this.children.push(...n)},
      replaceChildren(...n){this.children=n},
      addEventListener(type,cb){this.listeners[type]=cb;},listeners:{},
      textContent:'',click(){this.clicked=true;}};
  }
  const dom={body:node('body'),createElement:node,
    getElementById(id){if(!els[id])els[id]=node();return els[id];},
    addEventListener(type,cb){docsListeners[type]=cb;},
    querySelector(){return null},querySelectorAll(){return []}
  };
  const state={mode:'verified',sha:'a'.repeat(40),tasks:[],missing:[],stale:[],rateLimit:20,rateReset:null,lastVerified:0};
  const window={ROVOR_HUD:{state,openView:()=>{calls++;}}};
  const vmContext={window,document:dom,requestAnimationFrame:(cb)=>cb(),Event:class Event {}};
  vm.runInNewContext(js,vmContext);
  assert.equal(els.livePanels.hidden,true);
  assert.equal(els.liveDataButton.attrs['aria-pressed'],'false');
  els.liveDataButton.listeners.click();
  assert.equal(els.livePanels.hidden,false);
  assert.equal(els.liveDataButton.attrs['aria-pressed'],'true');
  assert.equal(els.livePanels.children[0].children[1].children.length,1);
  docsListeners['rovor:source']();
  assert.equal(calls,0);
  assert.equal(els.livePanels.dataset.status,'verified');
  state.mode='error';
  docsListeners['rovor:source']();
  assert.equal(els.livePanels.dataset.status,'unverified');
  assert.ok(els.livePanels.children[0].children[1].children.some(x=>x.textContent==='NO VERIFIED LIVE DATA'));
});
