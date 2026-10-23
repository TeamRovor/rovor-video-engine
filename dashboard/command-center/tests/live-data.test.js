'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const shellDir = path.join(__dirname, '..');
const {deriveSnapshot,fetchGitHubSnapshot,escapeHtml,fileGroups} = require('../live-data.js');
const sha = 'a'.repeat(40);
const base = {
  version:1, tasks:[
    {id:'done',status:'done',title:'old',priority:4,owner:null,depends_on:[]},
    {id:'test',status:'active',title:'<img src=x onerror=alert(1)>',priority:1,owner:'Mac <owner>',depends_on:[]},
    {id:'ready',status:'ready',title:'Next',priority:2,owner:null,depends_on:['test']}
  ]
};
const rules = {version:1,tasks:{done:{lane:'operations',requires:[]},test:{lane:'coordination',requires:[]},ready:{lane:'integration',requires:['local-exec']}}};
const extraTree = {tree:[{type:'blob',path:'README.md'},{type:'blob',path:'coordination/tasks.json'},{type:'tree',path:'coordination'}],truncated:false};
const requests=[];
function response(value, status=200) {return {ok:status===200,status,json:async()=>value};}
function fakeFetch(url, opts) {
  requests.push(url);
  if(url.endsWith('/commits/main')) return Promise.resolve(response({sha}));
  if(url.includes('/coordination/tasks.json')) return Promise.resolve(response(base));
  if(url.includes('/coordination/work-routing.json')) return Promise.resolve(response(rules));
  if(url.includes('/git/trees/')) return Promise.resolve(response(extraTree));
  if(url.includes('/pulls?')) return Promise.resolve(response([{number:1},{number:2}]));
  throw Error('unknown '+url);
}
test('same exact commit used for task and route reads',async()=>{
  requests.length=0;
  const r=await fetchGitHubSnapshot({fetchImpl:fakeFetch,now:1780000000000,includeExtras:true});
  const urls=requests.filter(x=>x.includes('raw.githubusercontent.com'));
  assert.equal(urls.length,2);
  urls.forEach(x=>assert.match(x,new RegExp('/'+sha+'/coordination/')));
  assert.equal(r.snapshot.repo_snapshot.commit,sha);
  assert.equal(r.snapshot.repo_snapshot.tasks_total,3);
  assert.equal(r.snapshot.repo_snapshot.routing_coverage,'3/3');
  assert.equal(r.snapshot.repo_snapshot.files_total,2);
  assert.equal(r.snapshot.repo_snapshot.open_prs,2);
  assert.equal(r.snapshot.workers[0].name,'Mac <owner>');
  assert.equal(r.snapshot.workers[0].status,'claimed');
  assert.ok(requests.every(url=>!url.includes('token=')));
});
test('fallback PR and tree are marked partial but tasks stay live',async()=>{
  const previous=deriveSnapshot({commit:sha,queue:base,routes:rules,tree:extraTree,pulls:[{number:1}],now:1780000000000});
  const r=await fetchGitHubSnapshot({fetchImpl: async(url,opts)=>{
    if(url.includes('/git/trees')||url.includes('/pulls?')) return response({},403);
    return fakeFetch(url,opts);
  },previous,now:1780000005000,includeExtras:true});
  assert.equal(r.snapshot.repo_snapshot.tasks_total,3);
  assert.equal(r.snapshot.repo_snapshot.files_total,2);
  assert.equal(r.snapshot.repo_snapshot.open_prs,1);
  assert.equal(r.warnings.length,2);
});
test('critical queue fetch failure refuses new live snapshot',async()=>{
  await assert.rejects(fetchGitHubSnapshot({fetchImpl: async(url,opts)=>{
    if(url.endsWith('/coordination/tasks.json')) return response({},500);
    return fakeFetch(url,opts);
  },includeExtras:false}),/GitHub request failed/);
});
test('rejects invalid main SHA before fetching task files',async()=>{
  const called=[];
  await assert.rejects(fetchGitHubSnapshot({fetchImpl:async u=>{called.push(u);return response({sha:'main'});}}),/Invalid GitHub HEAD/);
  assert.equal(called.length,1);
});
test('reports routing mismatch rather than fabricating full coverage',()=>{
  const r=deriveSnapshot({commit:sha,queue:base,routes:{version:1,tasks:{test:{lane:'coordination'},extra:{lane:'coordination'}}},now:1780000000000});
  assert.deepEqual(r.route_health.missing,['done','ready']);
  assert.deepEqual(r.route_health.stale,['extra']);
  assert.equal(r.repo_snapshot.routing_coverage,'1/3');
});
test('rejects duplicate task IDs',()=>{
  assert.throws(()=>deriveSnapshot({commit:sha,queue:{tasks:[base.tasks[0],base.tasks[0]]},routes:rules,now:0}),/Duplicate GitHub/);
});
test('untrusted GitHub text is escaped before DOM injection',()=>{
  assert.equal(escapeHtml('<img src=x onerror="hack">'),'&lt;img src=x onerror=&quot;hack&quot;&gt;');
  assert.equal(escapeHtml('Owner & Sons'), 'Owner &amp; Sons');
});
test('fileGroup counts blobs, not directories',()=>{
  assert.deepEqual(fileGroups(extraTree),[{name:'(root)',count:1},{name:'coordination',count:1}]);
});
test('does not claim Mac workers are online',()=>{
  const r=deriveSnapshot({commit:sha,queue:base,routes:rules,now:0});
  assert.ok(r.workers.every(w=>!['online','running','healthy'].includes(w.status)));
  assert.match(r.notes.join(' '),/NOT presence/);
});
test('disabled extras avoid unnecessary rate-limit calls',async()=>{
  requests.length=0;
  await fetchGitHubSnapshot({fetchImpl:fakeFetch,includeExtras:false});
  assert.equal(requests.length,3);
});

test('iPad install manifest is standalone and scoped to the HUD directory',()=>{
  const manifest=JSON.parse(fs.readFileSync(path.join(shellDir,'manifest.webmanifest'),'utf8'));
  assert.equal(manifest.name,'ROVOR Command Center');
  assert.equal(manifest.display,'standalone');
  assert.equal(manifest.start_url,'./index.html');
  assert.equal(manifest.scope,'./');
  assert.ok(manifest.icons.some(icon=>icon.src==='./hud-icon.svg'));
});

test('service worker syntax is valid and excludes cross-origin live data from caching',()=>{
  const worker=fs.readFileSync(path.join(shellDir,'service-worker.js'),'utf8');
  assert.doesNotThrow(()=>new vm.Script(worker));
  assert.match(worker,/if \(url\.origin !== self\.location\.origin\) return;/);
  assert.match(worker,/Never cache GitHub API\/raw data/);
  assert.match(worker,/fetch\(request\)/);
  assert.match(worker,/cache\.put\(new Request\(request\.url\), copy\)/);
  assert.match(worker,/caches\.match\(new Request\(request\.url\)\)/);
});

test('HUD registers its shell service worker without requiring it for live operation',()=>{
  const app=fs.readFileSync(path.join(shellDir,'app.js'),'utf8');
  const html=fs.readFileSync(path.join(shellDir,'index.html'),'utf8');
  assert.match(app,/navigator\.serviceWorker\.register\('\.\/service-worker\.js'/);
  assert.match(app,/addEventListener\('offline'/);
  assert.match(app,/Device is offline; displayed data is not live/);
  assert.match(html,/rel="manifest" href="\.\/manifest\.webmanifest"/);
  assert.match(html,/apple-mobile-web-app-capable/);
});
