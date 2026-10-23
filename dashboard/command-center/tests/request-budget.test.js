'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');
const Live = require('../live-data.js');

const APP = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');
const SHA = 'a'.repeat(40);
const queue = {version:1,tasks:[
  {id:'qa-active',status:'active',title:'QA active task',priority:1,owner:'QA owner',depends_on:[]},
  {id:'qa-ready',status:'ready',title:'QA ready task',priority:2,owner:null,depends_on:[]}
]};
const routes = {version:1,tasks:{
  'qa-active':{lane:'coordination',requires:[]},
  'qa-ready':{lane:'integration',requires:[]}
}};
const tree = {tree:[
  {type:'blob',path:'README.md'},
  {type:'blob',path:'coordination/tasks.json'},
  {type:'blob',path:'coordination/work-routing.json'}
],truncated:false};
const pulls = [{number:10},{number:11}];

async function simulateHour({restLimit=Infinity,minutes=60}={}) {
  const elements = new Map(), listeners = new Map(), timers = [], requests = [], restRequests = [];
  let clock = 0;
  function element(id) {
    if (!elements.has(id)) {
      elements.set(id,{
        id,value:id==='statusFilter'?'all':'',textContent:'',innerHTML:'',className:'',
        disabled:false,title:'',dataset:{},style:{},
        classList:{add(){},remove(){},toggle(){}},
        addEventListener(name,fn){listeners.set(id+':'+name,fn);}
      });
    }
    return elements.get(id);
  }
  const fetch = async (url) => {
    const address=String(url);
    requests.push({url:address,time:clock});
    if (address === 'snapshot.json') return {ok:false,status:404,json:async()=>null};
    const isRest=address.startsWith('https://api.github.com/');
    if (isRest) {
      restRequests.push({url:address,time:clock});
      if (restRequests.length>restLimit) return {ok:false,status:403,json:async()=>({message:'rate limited'})};
    }
    let body;
    if (address.endsWith('/commits/main')) body={sha:SHA};
    else if (address.includes('/coordination/tasks.json')) body=queue;
    else if (address.includes('/coordination/work-routing.json')) body=routes;
    else if (address.includes('/git/trees/')) body=tree;
    else if (address.includes('/pulls?')) body=pulls;
    else throw new Error('Unexpected request: '+address);
    return {ok:true,status:200,json:async()=>body};
  };
  class ClockDate extends Date {
    constructor(...args){super(...(args.length?args:[clock]));}
    static now(){return clock;}
  }
  const document={
    hidden:false,
    getElementById:element,
    querySelectorAll(){return [];},
    addEventListener(){},
    createElement(){return {click(){},set href(v){},set download(v){}};}
  };
  const context={
    RovorLiveData:Live,document,fetch,Date:ClockDate,
    setInterval(fn,ms){timers.push({fn,ms});return timers.length;},
    setTimeout(){return 1;},
    Blob:class Blob{constructor(parts,opts){this.parts=parts;this.opts=opts;}},
    URL:{createObjectURL(){return 'blob:mock';},revokeObjectURL(){}},
    console
  };
  vm.runInNewContext(APP,context,{filename:'dashboard/command-center/app.js',timeout:5000});
  async function settle(){for(let i=0;i<80;i++)await Promise.resolve();}
  await settle();
  assert.equal(timers.length,1,'actual app should install one refresh timer');
  assert.equal(timers[0].ms,180000,'actual app refreshes every three minutes');
  for(let elapsed=timers[0].ms;elapsed<=minutes*60000;elapsed+=timers[0].ms){
    clock=elapsed;
    timers[0].fn();
    await settle();
  }
  return {elements,requests,restRequests,timers,sha:SHA};
}

test('actual Command Center app stays within unauthenticated REST budget over one simulated hour',async t=>{
  const r=await simulateHour();
  t.diagnostic('Observed '+r.restRequests.length+' GitHub REST requests over 60 simulated minutes.');
  assert.ok(r.restRequests.length<=60,
    'Command Center used '+r.restRequests.length+' REST requests in one simulated hour; expected <=60.');
  assert.equal(r.elements.get('syncState').textContent,'LIVE GITHUB');
  assert.equal(r.elements.get('prCount').textContent,2);
});

test('actual app pins both raw queue and route reads to the same immutable SHA',async()=>{
  const r=await simulateHour({minutes:9});
  const raw=r.requests.filter(x=>x.url.includes('raw.githubusercontent.com'));
  assert.ok(raw.length>=2);
  assert.equal(raw.length%2,0,'queue and routes should be fetched as pairs');
  assert.ok(raw.every(x=>x.url.includes('/'+r.sha+'/coordination/')));
  for(let i=0;i<raw.length;i+=2){
    assert.notEqual(raw[i].url.split('/').pop(),raw[i+1].url.split('/').pop(),
      'each pair should contain distinct queue and routing files');
    assert.equal(raw[i].url.split('/').slice(0,-1).join('/'),
                 raw[i+1].url.split('/').slice(0,-1).join('/'),
                 'paired files must share the exact SHA-pinned directory');
  }
});

test('REST budget exhaustion stops claiming live GitHub state and shows explicit fallback',async()=>{
  const r=await simulateHour({restLimit:5,minutes:12});
  assert.ok(r.restRequests.length>5,'simulation should force a REST 403');
  assert.equal(r.elements.get('syncState').textContent,'OFFLINE SNAPSHOT');
  assert.match(r.elements.get('syncDetails').textContent,/GitHub sync failed/);
});

test('Command Center source has no embedded browser credential or write method',()=>{
  assert.doesNotMatch(APP,/Authorization\s*[:=]|gh[pousr]_[A-Za-z0-9]{20,}/i);
  assert.doesNotMatch(APP,/method\s*:\s*['"](?:POST|PATCH|PUT|DELETE)['"]/i);
});
