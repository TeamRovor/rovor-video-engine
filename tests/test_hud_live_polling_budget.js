/* Independent regression for draft dashboard PR #73. No real GitHub calls.
 * Re-run against the updated 3-minute polling / pinned raw-content implementation. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const test = require('node:test');

const HTML = fs.readFileSync(path.join(__dirname, '..', 'dashboard', 'index.html'), 'utf8');
const SCRIPT = HTML.match(/<script>([\s\S]*?)<\/script>/i);
assert.ok(SCRIPT, 'Standalone HUD must have one readable inline app script');

async function simulate(minutes, limit = Infinity) {
  const nodes = new Map(), listeners = new Map(), timers = [], calls = [], restCalls = [];
  let clock = 0;
  const sha = 'a'.repeat(40);
  const tasks = {version: 1, tasks: [
    {id: 'test-ready', status: 'ready', title: 'Real task', priority: 1, owner: null, depends_on: []}
  ]};
  const routing = {version: 1, tasks: {'test-ready': {lane:'coordination',requires:[]}}};
  const file = obj => {
    const raw = Buffer.from(JSON.stringify(obj), 'utf8');
    return {type:'file',encoding:'base64',size:raw.length,content:raw.toString('base64')};
  };
  function element(id) {
    if (!nodes.has(id)) {
      nodes.set(id, {
        id, value:id==='statusFilter'?'all':'', innerHTML:'', textContent:'',
        className:'', disabled:false, title:'',
        classList:{toggle(){},add(){},remove(){}},
        addEventListener(event, callback) { listeners.set(id + ':' + event, callback); }
      });
    }
    return nodes.get(id);
  }
  const fetch = async url => {
    const address=String(url);
    calls.push(address);
    const isRest=address.startsWith('https://api.github.com/');
    if (isRest) {
      restCalls.push(address);
      if (restCalls.length > limit) return {ok:false,status:403,json:async()=>({})};
    }
    let body, rawText=null;
    if (address.includes('/commits?')) body=[{sha}];
    else if (address.includes('/contents/coordination/tasks.json?ref=')) body=file(tasks);
    else if (address.includes('/contents/coordination/work-routing.json?ref=')) body=file(routing);
    else if (address.includes('/pulls?')) body=[];
    else if (address.includes('raw.githubusercontent.com/TeamRovor/rovor-video-engine/'+sha+'/coordination/tasks.json')) rawText=JSON.stringify(tasks);
    else if (address.includes('raw.githubusercontent.com/TeamRovor/rovor-video-engine/'+sha+'/coordination/work-routing.json')) rawText=JSON.stringify(routing);
    else throw new Error('Unexpected external request: ' + address);
    return {ok:true,status:200,json:async()=>rawText===null?body:JSON.parse(rawText),text:async()=>rawText===null?JSON.stringify(body):rawText};
  };
  class ClockDate extends Date {
    constructor(...args) { super(...(args.length ? args : [clock])); }
    static now() {return clock;}
  }
  const context={
    document:{getElementById:element},
    fetch, setInterval(fn, ms) {timers.push({fn, ms}); return timers.length;},
    Date:ClockDate, atob:s=>Buffer.from(s,'base64').toString('binary'),
    decodeURIComponent, escape, console
  };
  vm.runInNewContext(SCRIPT[1],context,{filename:'dashboard/index.html',timeout:5000});
  async function settle() {
    // The script chains two asynchronous fetch rounds plus Promise.all.
    for (let i=0;i<20;i++) await Promise.resolve();
  }
  await settle();
  assert.equal(timers.length,1,'Expected exactly one automatic sync interval');
  for(let elapsed=timers[0].ms;elapsed<=minutes*60000;elapsed+=timers[0].ms) {
    clock=elapsed;
    timers[0].fn();
    await settle();
  }
  return {calls, restCalls, nodes, listeners, sha, interval:timers[0].ms};
}

test('pinned-commit queue and route reads use identical immutable SHA', async () => {
  const result=await simulate(0);
  assert.equal(result.nodes.get('connection').textContent,'ONLINE');
  const pinned=result.calls.filter(url=>/coordination\/(?:tasks|work-routing)\.json/.test(url));
  assert.equal(pinned.length,2);
  assert.ok(pinned.every(url=>url.includes('?ref=' + result.sha) ||
    url.includes('/' + result.sha + '/coordination/')));
  const rawReads=result.calls.filter(url=>url.includes('raw.githubusercontent.com'));
  assert.ok(rawReads.length===0 || rawReads.length===2,
    'Queue and routing must use one transport strategy, not mix API and raw reads');
  assert.ok(result.nodes.get('tasks').innerHTML.includes('Real task'));
});

test('one hour of unattended HUD polling stays within a 60-request public API budget', async () => {
  const result=await simulate(60);
  // GitHub's typical unauthenticated REST allowance is 60 requests/hour/IP.
  // Shared public IPs make headroom desirable; 60 is only an upper bound.
  assert.ok(result.restCalls.length<=60,
    'HUD used '+result.restCalls.length+' unauthenticated REST calls in 60 min; '
    +'default 60/hour public API budget exhausted. '
    +'Use pinned raw GitHub content or slower REST polling.');
});

test('an exhausted API budget never continues claiming LIVE data',async () => {
  const result=await simulate(25,5);
  assert.ok(result.restCalls.length>5,'Test must actually trigger simulated REST 403');
  assert.equal(result.nodes.get('connection').textContent,'STALE / ERROR');
  assert.ok(result.nodes.get('notice').textContent.includes('Sync failed'));
});

test('dashboard never embeds a token or mutating API request', () => {
  assert.doesNotMatch(SCRIPT[1],/Authorization\s*[:=]|gh[pousr]_[A-Za-z0-9]{20,}/i);
  assert.doesNotMatch(SCRIPT[1],/method\s*:\s*['"](?:POST|PATCH|PUT|DELETE)['"]/i);
});
