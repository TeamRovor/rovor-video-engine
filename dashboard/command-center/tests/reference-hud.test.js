'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const markup = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const source = fs.readFileSync(path.join(root, 'reference-hud.js'), 'utf8');

function harness() {
  const elements = new Map();
  const listeners = {};
  const element = id => {
    if (!elements.has(id)) elements.set(id, { id, textContent:'', innerHTML:'', value:'',
      click(){this.clicked = true}, dispatchEvent(e){this.event=e}, setAttribute(){}, style:{},
      scrollIntoView(){this.scrolled=true} });
    return elements.get(id);
  };
  const document = {
    getElementById: element,
    querySelector: () => element('main'),
    addEventListener: (type, callback) => { listeners[type] = callback; },
    body: {dataset:{},classList:{contains:()=>false}}
  };
  const context = {document, setInterval(){}, Date, Event:class Event{constructor(type){this.type=type}}, 
    RovorLiveData:{escapeHtml: value => String(value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}};
  vm.runInNewContext(source, context, {filename:'reference-hud.js'});
  return {api:context.RovorReferenceHud, elements, element, listeners, document};
}

const snapshot = {
  generated_at:'2026-10-23T10:00:00Z',
  repo_snapshot:{tasks_total:4,tasks_status:{active:1,ready:1,blocked:1,done:1},
    routed_tasks:3,routing_coverage:'3/4',commit:'a'.repeat(40),open_prs:8},
  route_health:{complete:false},
  tasks:[
    {id:'running-claim',title:'Assigned != running',status:'active',owner:'Test person',priority:3},
    {id:'ready-job',title:'Ready work',status:'ready',priority:1},
    {id:'blocked-job',title:'Private host blocked',status:'blocked',priority:2},
    {id:'done-job',title:'Completed',status:'done',priority:1}
  ]
};

test('reference HUD owns the expected interactive panels, tabs, and source scripts',()=>{
  for(const id of ['activeTaskPreview','workloadBars','recentEvidence','healthFacts','coreSyncMode','tab-button-tasks','integrityPct','taskTable']) {
    assert.match(markup,new RegExp('id="'+id+'"'));
  }
  assert.match(markup,/reference-hud\.css/);
  assert.match(markup,/reference-hud\.js/);
  assert.ok(markup.indexOf('reference-hud.js') < markup.indexOf('app.js'), 'reference HUD must register before app render');
  assert.match(markup,/claimed does not mean running/i);
});

test('both visual assets are included in the install and fetch cache shell',()=>{
  const sw=fs.readFileSync(path.join(root, 'service-worker.js'),'utf8');
  assert.ok(sw.includes('reference-hud.css'));
  assert.ok(sw.includes('reference-hud.js'));
  assert.match(sw,/rovor-command-center-shell-v4/);
});

test('open counts, ordering and coverage use queue data, not decorative numbers',()=>{
  const {api} = harness();
  const result=api.model(snapshot,'live');
  assert.equal(result.openCount,3);
  assert.equal(result.counts.active,1);
  assert.equal(result.counts.done,1);
  assert.equal(result.coverage,'3/4');
  assert.equal(result.percent,75);
  assert.deepEqual(Array.from(result.tasks, t=>t.id),['running-claim','ready-job','blocked-job']);
});

test('snapshot state is never labeled live or a native Mac executor',()=>{
  const {api,element,document} = harness();
  api.render(snapshot,{syncMode:'snapshot',lastSuccess:null});
  assert.equal(element('headerConnection').textContent,'OFFLINE SNAPSHOT');
  assert.equal(element('coreSyncMode').textContent,'HISTORICAL SNAPSHOT');
  assert.match(element('healthFacts').innerHTML,/GitHub source<\/span><strong>NOT LIVE/);
  assert.match(element('healthFacts').innerHTML,/Mac execution<\/span><strong>NOT PROVEN/);
  assert.equal(element('activeTaskCount').textContent,'3 OPEN');
  assert.equal(document.body.dataset.sourceMode,'snapshot');
  assert.doesNotMatch(element('recentEvidence').innerHTML,/99% operational/i);
});

test('task cards escape untrusted titles and provide a real inspect-task action',()=>{
  const {api,element,listeners} = harness();
  const hostile = JSON.parse(JSON.stringify(snapshot));
  hostile.tasks[0].title='<img src=x onerror=alert(1)>';
  api.render(hostile,{syncMode:'live',lastSuccess:Date.now()});
  assert.doesNotMatch(element('activeTaskPreview').innerHTML,/<img /);
  assert.match(element('activeTaskPreview').innerHTML,/&lt;img /);
  assert.equal(element('headerConnection').textContent,'GITHUB VERIFIED');
  listeners.click({target:{closest:()=>({dataset:{taskId:'running-claim'}})}});
  assert.equal(element('tab-button-tasks').clicked,true);
  assert.equal(element('taskSearch').value,'running-claim');
  assert.equal(element('statusFilter').value,'all');
  assert.equal(element('taskSearch').event.type,'input');
  assert.equal(element('main').scrolled,true);
});
