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

test('service worker serves same-origin shell from cache offline and leaves cross-origin data untouched',async()=>{
  const worker=fs.readFileSync(path.join(shellDir,'service-worker.js'),'utf8');
  const origin='https://hud.example.test';
  const stored=new Map();
  let fetchCalls=0;
  let fetchHandler;
  const requestUrl=request=>typeof request==='string'?request:request.url;
  const cache={
    addAll:async()=>{},
    put:async(request,response)=>{stored.set(requestUrl(request),response);},
    match:async request=>stored.get(requestUrl(request))
  };
  const cacheApi={
    open:async()=>cache,
    keys:async()=>['rovor-command-center-shell-v1'],
    match:async request=>stored.get(requestUrl(request))
  };
  const self={
    location:{origin},
    clients:{claim:async()=>{}},
    skipWaiting:async()=>{},
    addEventListener:(name,handler)=>{if(name==='fetch')fetchHandler=handler;}
  };
  vm.runInNewContext(worker,{self,caches:cacheApi,URL,Request,Response,fetch:async()=>{fetchCalls++;throw Error('offline');}});
  const shellUrl=origin+'/dashboard/command-center/styles.css';
  stored.set(shellUrl,new Response('cached shell'));
  let shellResponse;
  fetchHandler({request:new Request(shellUrl),respondWith:promise=>{shellResponse=promise;}});
  assert.equal(await (await shellResponse).text(),'cached shell');
  assert.equal(fetchCalls,1);
  let crossOriginHandled=false;
  fetchHandler({request:new Request('https://raw.githubusercontent.com/TeamRovor/rovor-video-engine/main/snapshot.json'),respondWith:()=>{crossOriginHandled=true;}});
  assert.equal(crossOriginHandled,false);
  assert.equal(fetchCalls,1);
});

test('service worker precache list points only to existing local shell assets',()=>{
  const worker=fs.readFileSync(path.join(shellDir,'service-worker.js'),'utf8');
  const match=worker.match(/const SHELL = \[([\s\S]*?)\];/);
  assert.ok(match,'service worker shell list should exist');
  const assets=[...match[1].matchAll(/'([^']+)'/g)].map(item=>item[1]);
  assert.ok(assets.length>=7,'shell should include core app files and install metadata');
  for(const asset of assets){
    assert.ok(!/^https?:\/\//i.test(asset),asset+' must remain same-origin');
    assert.ok(fs.existsSync(path.join(shellDir,asset)),asset+' must exist or install-time cache.addAll will fail');
  }
});

test('service worker install precaches the shell and activation removes only obsolete HUD caches',async()=>{
  const worker=fs.readFileSync(path.join(shellDir,'service-worker.js'),'utf8');
  const handlers={};
  let precached=[];
  let skipped=false;
  let claimed=false;
  const deleted=[];
  const cache={addAll:async assets=>{precached=assets.slice();}};
  const self={
    location:{origin:'https://hud.example.test'},
    clients:{claim:async()=>{claimed=true;}},
    skipWaiting:async()=>{skipped=true;},
    addEventListener:(name,handler)=>{handlers[name]=handler;}
  };
  const cacheApi={
    open:async()=>cache,
    keys:async()=>['rovor-command-center-shell-v0','unrelated-cache','rovor-command-center-shell-v1'],
    delete:async key=>{deleted.push(key);return true;}
  };
  vm.runInNewContext(worker,{self,caches:cacheApi,URL,Request,Response,fetch});
  let installPromise;
  handlers.install({waitUntil:promise=>{installPromise=promise;}});
  await installPromise;
  assert.ok(skipped,'install should activate the new worker promptly');
  assert.ok(precached.includes('./index.html'));
  assert.ok(precached.includes('./app.js'));
  assert.ok(precached.includes('./manifest.webmanifest'));
  let activatePromise;
  handlers.activate({waitUntil:promise=>{activatePromise=promise;}});
  await activatePromise;
  assert.deepEqual(deleted,['rovor-command-center-shell-v0']);
  assert.ok(claimed,'activation should claim existing HUD clients');
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
