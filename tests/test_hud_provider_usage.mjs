import test from 'node:test';
import assert from 'node:assert/strict';
import {createCallLogCollector, HUD_PROVIDERS, pacificDay, reduceCallLogs} from '../tools/hud_provider_usage.mjs';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const NOW = Date.parse('2026-10-28T07:53:00Z');
const connections = HUD_PROVIDERS.map(provider => ({provider, isActive: true}));

test('Pacific RPD boundaries follow local midnight across daylight-saving time', () => {
  assert.deepEqual(pacificDay(Date.parse('2026-03-08T08:30:00Z')),
    {start: Date.parse('2026-03-08T08:00:00Z'), reset: Date.parse('2026-03-09T07:00:00Z')});
  assert.deepEqual(pacificDay(NOW), {start: Date.parse('2026-10-28T07:00:00Z'), reset: Date.parse('2026-10-29T07:00:00Z')});
});

test('rolling minute and Pacific-day counts deduplicate durable reports by call-log ID', () => {
  const rows = [
    {id:'g1', timestamp:new Date(NOW-30000).toISOString(), provider:'gemini', model:'gemini-2.5-flash', status:200, tokensIn:31, tokensOut:8},
    {id:'g2', timestamp:new Date(NOW-50000).toISOString(), provider:'google', model:'gemini-2.5-flash', status:429},
    {id:'g3', timestamp:new Date(NOW-70000).toISOString(), provider:'gemini', model:'gemini-2.5-pro', status:503, tokensIn:12},
    {id:'g4', timestamp:'2026-10-28T06:59:59Z', provider:'gemini', model:'gemini-2.5-pro', status:200, tokensIn:14},
  ];
  const usage = reduceCallLogs(connections, [...rows, rows[0]], {now:NOW});
  const gemini = usage.providers.find(p => p.provider === 'gemini');
  assert.equal(usage.providers.length, 9);
  assert.equal(gemini.attempts_rolling_minute, 2);
  assert.equal(gemini.successes_rolling_minute, 1);
  assert.equal(gemini.rate_limit_errors_rolling_minute, 1);
  assert.equal(gemini.failures_rolling_minute, 1);
  assert.equal(gemini.output_tokens_recorded_rolling_minute, 8);
  assert.equal(gemini.attempts_rolling_hour, 3);
  assert.equal(gemini.failures_rolling_hour, 2);
  assert.equal(gemini.attempts_pacific_day, 3);
  assert.equal(gemini.successes_pacific_day, 1);
  assert.equal(gemini.failures_pacific_day, 2);
  assert.equal(gemini.input_tokens_recorded_rolling_hour, 43);
  assert.equal(gemini.input_tokens_recorded_pacific_day, 43);
  assert.equal(gemini.output_tokens_recorded_pacific_day, 8);
  assert.equal(gemini.models.length, 2);
  assert.equal(gemini.employee_attribution, 'unknown');
  assert.equal('remaining' in gemini, false);
  assert.equal(usage.pacific_day_reset, '2026-10-29T07:00:00.000Z');
});

test('empty logs provide zero tracked requests while limits stay absent', () => {
  const usage = reduceCallLogs(connections, [], {now:NOW});
  const groq = usage.providers.find(p => p.provider === 'groq');
  assert.equal(groq.configured, true);
  assert.equal(groq.attempts_pacific_day, 0);
  assert.equal(groq.input_tokens_recorded_pacific_day, 0);
  assert.equal(groq.employee_attribution, 'unknown');
  assert.equal('limit' in groq, false);
});

test('collector rebuilds from durable logs after restart, deduplicates overlap, and marks stale reads', async () => {
  let now=NOW, calls=0, fails=false;
  const log={id:'r1',timestamp:new Date(NOW-30000).toISOString(),provider:'groq',model:'llama-3.3',status:200,tokensIn:9,tokensOut:3};
  const read=async path=>{
    assert.match(path,/^\/api\/usage\/call-logs\?/);
    const query=new URLSearchParams(path.split('?')[1]);
    assert.equal(query.get('since'),'2026-10-28T07:00:00.000Z');
    calls++;
    if(fails)throw Error('offline');
    return {logs:[log]};
  };
  const collect=createCallLogCollector(read,{clock:()=>now,cacheMs:1});
  const first=await collect(connections);
  assert.equal(first.providers.find(p=>p.provider==='groq').attempts_pacific_day,1);
  const restarted=createCallLogCollector(read,{clock:()=>now});
  assert.equal((await restarted(connections)).providers.find(p=>p.provider==='groq').attempts_pacific_day,1);
  assert.equal(calls,2);
  fails=true;now+=31000;
  const stale=await collect(connections);
  assert.equal(stale.freshness,'stale');
  assert.equal(stale.coverage,'stale');
  assert.equal(stale.providers.find(p=>p.provider==='groq').attempts_pacific_day,1);
});

test('429s are counted without inventing Retry-After or account-wide remaining', () => {
  const usage=reduceCallLogs(connections,[{id:'429',timestamp:new Date(NOW-1000).toISOString(),provider:'nvidia_nim',model:'nim-model',status:429}],{now:NOW});
  const nvidia=usage.providers.find(p=>p.provider==='nvidia');
  assert.equal(nvidia.rate_limit_errors_rolling_minute,1);
  assert.equal(nvidia.attempts_pacific_day,1);
  assert.equal(nvidia.employee_attribution,'unknown');
  assert.equal('pacific_day_reset' in nvidia,false);
  assert.equal('remaining' in nvidia,false);
});

test('durable Retry-After values become timestamps and unknown tokens remain partial', () => {
  const usage=reduceCallLogs(connections,[{id:'429-delay',timestamp:new Date(NOW-1000).toISOString(),provider:'groq',model:'llama',status:429,retry_after:120}],{now:NOW});
  const groq=usage.providers.find(p=>p.provider==='groq');
  assert.equal(groq.retry_after_at,new Date(NOW+119000).toISOString());
  assert.equal(groq.models[0].last_rate_limit_at,new Date(NOW-1000).toISOString());
  assert.equal(groq.models[0].retry_after_at,new Date(NOW+119000).toISOString());
  assert.equal(groq.input_tokens_recorded_rolling_minute,null);
  assert.equal(groq.input_tokens_coverage_rolling_minute,'partial');
});

test('OmniRoute native nested token receipts are counted by model and provider', () => {
  const usage=reduceCallLogs(connections,[{id:'native',timestamp:new Date(NOW-1000).toISOString(),provider:'openrouter',model:'vendor/free:model',requestedModel:'openrouter/vendor/free:model',status:200,tokens:{in:852,out:2840}}],{now:NOW});
  const openrouter=usage.providers.find(p=>p.provider==='openrouter');
  assert.equal(openrouter.successes_rolling_minute,1);
  assert.equal(openrouter.input_tokens_recorded_rolling_minute,852);
  assert.equal(openrouter.output_tokens_recorded_rolling_minute,2840);
  assert.equal(openrouter.models[0].model_id,'vendor/free:model');
});

test('configured Cloudflare AI gateway alias maps into the ninth provider counter', () => {
  const usage=reduceCallLogs([{provider:'cloudflare-ai'}],[{id:'cf',timestamp:new Date(NOW-1000).toISOString(),provider:'cloudflare-ai',model:'connection-test',status:200,tokens:{in:0,out:0}}],{now:NOW});
  const cloudflare=usage.providers.find(p=>p.provider==='cloudflare');
  assert.equal(cloudflare.configured,true);
  assert.equal(cloudflare.attempts_rolling_minute,1);
  assert.equal(cloudflare.models[0].model_id,'connection-test');
});

test('existing neon quota board displays all nine tracked providers and keeps unknown quotas explicit', () => {
  const window={},document={getElementById:()=>({}),createElement:()=>({})};
  const source=readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js',import.meta.url),'utf8');
  vm.runInNewContext(source,{window,document,Date,Math,Number,String,Array,Map});
  const data={connections:HUD_PROVIDERS.map(provider=>({provider,name:provider,connection_count:1,enabled_count:1})),
    connection_slots:HUD_PROVIDERS.map((provider,i)=>({provider,account_slot:1,enabled:true})),
    request_usage:reduceCallLogs(connections,[{id:'x',timestamp:new Date(NOW-1000).toISOString(),provider:'gemini',model:'gemini-2.5-flash',status:429},{id:'test',timestamp:new Date(NOW-2000).toISOString(),provider:'openrouter',model:'connection-test',status:200,tokens:{in:0,out:0}}],{now:NOW}),quota:{records:[]}};
  const html=window.ROVOR_QUOTA_BOARD.render(data,true);
  assert.equal((html.match(/class="rvq-provider"/g)||[]).length,9);
  assert.match(html,/OMNIROUTE TRACKED USAGE/);
  assert.match(html,/Account-wide remaining: UNKNOWN/);
  assert.match(html,/1 HTTP 429/);
  assert.match(html,/Employee: unknown|employee: unknown/);
  assert.match(html,/QUOTA UNKNOWN/);
  assert.match(html,/CAPACITY: UNKNOWN/);
  assert.match(html,/connection test, not inference receipt/);
});
