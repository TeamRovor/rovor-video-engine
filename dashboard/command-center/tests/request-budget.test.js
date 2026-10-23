'use strict';
/* Deterministic one-hour browser simulation for the ACTUAL merged Command Center. */
const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const Live=require('../live-data.js');
const SCRIPT=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8');
const SHA='a'.repeat(40);
const BASE=Date.parse('2026-10-23T00:00:00Z');

function harness() {
  let now=BASE, hidden=false, failNextHead=false;
  const calls=[], elements=new Map(), events=new Map(), intervals=[];
  function el(id) {
    if (!elements.has(id)) {
      elements.set(id,{
        id,innerHTML:'',textContent:'',className:'',title:'',disabled:false,
        value:id==='statusFilter'?'all':'',style:{},
        classList:{add(){},remove(){},toggle(){}},
        addEventListener(event,cb){events.set(id+':'+event,cb);}
      });
    }
    return elements.get(id);
  }
  const document={
    getElementById:el,
    querySelectorAll(){return [];},
    addEventListener(event,cb){events.set('document:'+event,cb);},
    get hidden(){return hidden;}
  };
  const task={id:'real-task',title:'Router proof',status:'active',
    priority:1,owner:'CI test-only owner',depends_on:[],next_action:'Check actual work'};
  const queue={version:1,tasks:[task]};
  const routes={version:1,tasks:{'real-task':{lane:'coordination',requires:['hosted-ci']}}};
  const response=(body,status=200)=>({ok:status===200,status,json:async()=>body});
  async function fetch(url) {
    calls.push(String(url));
    if(url==='snapshot.json')return {ok:false,status:404};
    if(url.endsWith('/commits/main')) {
      if(failNextHead){failNextHead=false;return response({},403);}
      return response({sha:SHA});
    }
    if(url.includes('/coordination/tasks.json'))return response(queue);
    if(url.includes('/coordination/work-routing.json'))return response(routes);
    if(url.includes('/git/trees/'))return response({tree:[],truncated:false});
    if(url.includes('/pulls?'))return response([]);
    throw Error('unexpected URL '+url);
  }
  class ClockDate extends Date {
    constructor(...args) {super(...(args.length?args:[now]));}
    static now(){return now;}
  }
  const context={RovorLiveData:Live,document,fetch,Date:ClockDate,
    setInterval:(cb,delay)=>{intervals.push({cb,delay});return intervals.length;},
    setTimeout:()=>{},console};
  vm.runInNewContext(SCRIPT,context,{filename:'dashboard/command-center/app.js',timeout:5000});
  async function settle(){for(let k=0;k<35;k++) await Promise.resolve();}
  return {
    calls,el,events,intervals,settle,
    setHidden(value){hidden=value;},
    failNextHead(){failNextHead=true;},
    async initial(){await settle();assert.equal(intervals.length,1);},
    async elapse(minutes){const ticker=intervals[0];assert.ok(ticker);
      assert.ok(minutes*60000%ticker.delay===0);
      for(let passed=ticker.delay;passed<=minutes*60000;passed+=ticker.delay){
        now=BASE+passed;ticker.cb();await settle();
      }
    },
    async tickAfter(minutes){now+=minutes*60000;intervals[0].cb();await settle();}
  };
}
function restCalls(urls){return urls.filter(x=>x.startsWith('https://api.github.com/'))}
function rawCalls(urls){return urls.filter(x=>x.startsWith('https://raw.githubusercontent.com/'))}

test('actual Command Center fetches both queue files pinned to the exact SHA',async()=>{
  const page=harness();await page.initial();
  const urls=rawCalls(page.calls);
  assert.equal(urls.length,2);
  assert.ok(urls.every(url=>url.includes('/'+SHA+'/coordination/')));
  assert.equal(page.el('syncState').textContent,'LIVE GITHUB');
  assert.equal(page.el('metrics').innerHTML.includes('Router proof'),false);
  assert.ok(page.el('taskTable').innerHTML.includes('Router proof'));
});

test('actual Command Center stays below unauthenticated REST API hourly budget',async(t)=>{
  const page=harness();await page.initial();await page.elapse(60);
  const rest=restCalls(page.calls), raw=rawCalls(page.calls);
  t.diagnostic('Observed '+rest.length+' GitHub REST requests and '+raw.length+' pinned raw reads in 60 simulated minutes.');
  assert.ok(rest.length<=40,
    'Command Center consumed '+rest.length+' REST calls in 60 simulated minutes, '
    +'leaving inadequate headroom for a 60/hour IP allowance');
  assert.ok(raw.length>=42,'Pinned queue+routes must keep updating during the hour');
  assert.equal(page.el('syncState').textContent,'LIVE GITHUB');
});

test('hidden tab does not continue hitting GitHub API',async()=>{
  const page=harness();await page.initial();
  const prior=page.calls.length;
  page.setHidden(true);
  await page.elapse(60);
  assert.equal(page.calls.length,prior);
  page.setHidden(false);
  const handler=page.events.get('document:visibilitychange');
  assert.ok(handler);
  handler();await page.settle();
  assert.ok(page.calls.length>prior);
});

test('manual refresh does not query expensive optional endpoints each time',async()=>{
  const page=harness();await page.initial();
  const prior=page.calls.length;
  const handler=page.events.get('refreshBtn:click');assert.ok(handler);
  handler();await page.settle();
  const newCalls=page.calls.slice(prior);
  assert.equal(restCalls(newCalls).length,1);
  assert.equal(rawCalls(newCalls).length,2);
  assert.equal(newCalls.filter(url=>url.includes('/pulls?')).length,0);
});

test('main app source cannot send GitHub write commands or embed credentials',()=>{
  assert.doesNotMatch(SCRIPT,/gh[pousr]_[a-zA-Z0-9]{20,}/);
  assert.doesNotMatch(SCRIPT,/method\s*:\s*['"](?:POST|PUT|PATCH|DELETE)['"]/i);
});

test('failed critical refresh visibly downgrades live data to a stale snapshot',async()=>{
  const page=harness();await page.initial();
  assert.equal(page.el('syncState').textContent,'LIVE GITHUB');
  page.failNextHead();
  const handler=page.events.get('refreshBtn:click');assert.ok(handler);
  handler();await page.settle();
  assert.equal(page.el('syncState').textContent,'OFFLINE SNAPSHOT');
  assert.match(page.el('syncDetails').textContent,/HTTP 403/);
  assert.ok(page.el('taskTable').innerHTML.includes('Router proof'));
});
