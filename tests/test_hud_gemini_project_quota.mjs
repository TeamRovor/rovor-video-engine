import test from 'node:test';
import assert from 'node:assert/strict';
import {readGoogleGeminiQuota,reduceGoogleMonitoringMetrics} from '../integrations/hud-cloud/gemini-cloud-monitoring.mjs';
const NOW=Date.parse('2026-10-28T04:40:00.000Z');
const project='gen-lang-client-0511388545';
const base={GEMINI_MONITOR_PROJECT:project,GEMINI_MONITOR_SERVICE_ACCOUNT_EMAIL:'observer@project.iam.gserviceaccount.com',
 GEMINI_MONITOR_SERVICE_ACCOUNT_KEY:'fake private test material'};
const point=(v,kind='usage',at=NOW)=>({interval:{startTime:new Date(at-60000).toISOString(),endTime:new Date(at).toISOString()},
 value:{int64Value:String(v)}});
const metric=(v,kind,model='gemini-3.1-flash-lite',name='GenerateRequestsPerMinute-FreeTier')=>({
 metric:{labels:{model,limit_name:name,method:kind==='usage'?'GenerateContent':undefined}},
 resource:{labels:{location:'global'}},points:[point(v,kind,NOW-10000)]
});
const docs=()=>[
 {timeSeries:[metric(15,'limit')]},{timeSeries:[metric(3,'usage')]},
 {timeSeries:[metric(250000,'limit')]},{timeSeries:[metric(100,'usage')]}
];
test('Google quota collector does nothing without independently scoped project identity',async()=>{
 let calls=0;
 const r=await readGoogleGeminiQuota({}, {fetcher:async()=>{calls++;throw Error('network must not be called');},now:NOW});
 assert.equal(r.status,'not_configured');assert.equal(calls,0);
});
test('verified Google model-labeled free tier quota gauges and deltas produce scoped samples, not remaining',()=>{
 const r=reduceGoogleMonitoringMetrics(docs(),NOW);
 assert.equal(r.length,2);
 assert.deepEqual(r.map(x=>x.unit),['requests','input_tokens']);
 assert.equal(r[0].model,'gemini-3.1-flash-lite');
 assert.equal(r[0].sampled_usage,3);assert.equal(r[0].limit,15);
 assert.equal(r[0].reset_at,null);assert.equal(r[0].scope,'google_project_sample');
 assert.equal(r[0].source,'google_cloud_monitoring_free_tier_project_metrics');
 assert.equal(Object.hasOwn(r[0],'remaining'),false);
});
test('collector polls only four official Cloud Monitoring GET metrics with scoped token, no inference or paid endpoint',async()=>{
 const paths=[];
 const reports=docs();
 const result=await readGoogleGeminiQuota(base,{
  now:NOW,tokenProvider:async()=> 'test-auth-token-at-least-20-characters',
  fetcher:async(url,options)=>{
   const u=new URL(url);paths.push(u);
   assert.equal(options.method,'GET');
   assert.equal(options.headers.Authorization,'Bearer test-auth-token-at-least-20-characters');
   assert.equal(u.hostname,'monitoring.googleapis.com');
   assert.equal(u.pathname,'/v3/projects/'+project+'/timeSeries');
   assert.match(u.searchParams.get('filter'),/^metric\.type = "generativelanguage\.googleapis\.com\/quota\/generate_content_free_tier_/);
   assert.ok(u.searchParams.get('filter').endsWith('/limit"')||u.searchParams.get('filter').endsWith('/usage"'));
   return Response.json(reports[paths.length-1]);
  }
 });
 assert.equal(paths.length,4);assert.equal(result.status,'sampled_project_quota');
 assert.equal(result.project,project);assert.equal(result.models.length,2);
 assert.equal(JSON.stringify(result).includes('test-auth-token'),false);
});
test('invalid, duplicate, stale, mismatched and unpaired samples fail closed',()=>{
 for(const change of [
  d=>d[1].timeSeries=[],
  d=>d[1].timeSeries[0].points[0].value.int64Value='-1',
  d=>d[0].timeSeries[0].points[0].value.int64Value='0',
  d=>d[1].timeSeries[0].metric.labels.model='gemini-other-model',
  d=>d[1].timeSeries[0].points[0].interval.endTime=new Date(NOW-800000).toISOString(),
  d=>d[1].timeSeries.push(structuredClone(d[1].timeSeries[0])),
  d=>d[1].timeSeries[0].points[0].value.int64Value='9999999999'
 ]){
  const d=docs();change(d);const r=reduceGoogleMonitoringMetrics(d,NOW);
  assert.equal(r.some(x=>x.unit==='requests'),false);
 }
 assert.throws(()=>reduceGoogleMonitoringMetrics([{},{}],NOW),/invalid_metric_response/);
});
test('permission errors return safely redacted status and never claim quota',async()=>{
 const result=await readGoogleGeminiQuota(base,{now:NOW,
  tokenProvider:async()=> 'test-auth-token-at-least-20-characters',
  fetcher:async()=>new Response('very private internal details',{status:403})});
 assert.deepEqual(result,{source:'google_cloud_monitoring',status:'permission_denied',models:[]});
});
test('pagination is never silently interpreted as comprehensive project metric readings',async()=>{
 const result=await readGoogleGeminiQuota(base,{now:NOW,
  tokenProvider:async()=> 'test-auth-token-at-least-20-characters',
  fetcher:async()=>Response.json({timeSeries:[],nextPageToken:'more'})});
 assert.equal(result.status,'metric_page_incomplete');
 assert.deepEqual(result.models,[]);
});
