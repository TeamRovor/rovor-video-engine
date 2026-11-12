import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {
  validateDeploymentSecrets, prepareConfig, assertGithubReleaseContext
} from '../integrations/hud-cloud/prepare-github-deploy.mjs';
import {verifyGithubHud, verifyPinnedRepoSource, verifyAnonymousTelemetry, verifyAdvancingReports, verifiedOrigin, hasNineProviderMeterAsset, summarizeGroqKeyCatalog} from '../integrations/hud-cloud/verify-github-deploy.mjs';
import {handle} from '../integrations/hud-cloud/worker.mjs';

const dir = new URL('../integrations/hud-cloud/', import.meta.url);
const template = readFileSync(new URL('wrangler.jsonc', dir), 'utf8');
const actualNineMeterAsset = readFileSync(new URL('../dashboard/command-center/native-v8-9/live-quota-board.js', import.meta.url), 'utf8');
const D1 = 'abcdefff-1111-2222-3333-0123456789ab';
const secrets = {CLOUDFLARE_API_TOKEN: 'cloudflare-scope-limited-token',
  CLOUDFLARE_ACCOUNT_ID: 'a'.repeat(32), ROVOR_HUD_D1_ID: D1,
  ROVOR_HUD_WRITER_TOKEN: 'w'.repeat(40), ROVOR_HUD_READER_TOKEN: 'r'.repeat(40)};

test('only the reviewed Worker-first PRIVATE config may receive the remote D1 id', () => {
  const config = prepareConfig(template, D1);
  assert.equal(config.name, 'rovor-hud-telemetry');
  assert.equal(config.d1_databases[0].database_id, D1);
  assert.equal(config.assets.run_worker_first, true);
  assert.equal(config.assets.binding, 'ASSETS');
  assert.equal(config.main, 'worker.mjs');
  assert.equal(template.includes(D1), false);
  assert.throws(() => prepareConfig(template, 'REPLACE_WITH_PROVISIONED_D1_ID'), /provisioned_d1/);
  const wrong = JSON.parse(template); wrong.assets.run_worker_first = false;
  assert.throws(() => prepareConfig(JSON.stringify(wrong), D1), /unreviewed_private/);
  wrong.assets.run_worker_first = true; wrong.name = 'public-hud';
  assert.throws(() => prepareConfig(JSON.stringify(wrong), D1), /unreviewed_private/);
});

test('release context and distinct credentials fail closed, no bypass with PR branch', () => {
  assert.equal(validateDeploymentSecrets(secrets), true);
  assert.equal(assertGithubReleaseContext({GITHUB_REF:'refs/heads/main',
    GITHUB_REPOSITORY:'TeamRovor/rovor-video-engine'}), true);
  assert.throws(() => assertGithubReleaseContext({GITHUB_REF:'refs/pull/44/merge',
    GITHUB_REPOSITORY:'TeamRovor/rovor-video-engine'}), /trusted_main/);
  assert.throws(() => validateDeploymentSecrets({...secrets,
    ROVOR_HUD_READER_TOKEN: secrets.ROVOR_HUD_WRITER_TOKEN}), /independent/);
  assert.throws(() => validateDeploymentSecrets({...secrets,
    ROVOR_HUD_D1_ID: 'REPLACE_WITH_PROVISIONED_D1_ID'}), /provisioned_d1/);
});

test('readback refuses insecure, redirected, userinfo or mixed-origin URLs', () => {
  assert.equal(verifiedOrigin('https://rovor-hud-telemetry.example.workers.dev/'),
    'https://rovor-hud-telemetry.example.workers.dev');
  for (const bad of ['http://hud.example','https://a:b@hud.example',
    'https://hud.example/file','https://hud.example/#token',
    'https://hud.example/?token=secret','https://127.0.0.1/']) {
    assert.throws(() => verifiedOrigin(bad), /invalid_private|public_https/);
  }
});

test('private Worker serves tracked nine-meter script, but only to authenticated reader', async () => {
  const env = {DB: {}, HUD_READER_TOKEN: 'r'.repeat(40),
    HUD_WRITER_TOKEN: 'w'.repeat(40),
    ASSETS: {fetch: async req => {
      const path = new URL(req.url).pathname;
      return path === '/' ? new Response('<html><body>ROVOR_START_OMNIROUTE</body></html>',
        {headers:{'Content-Type':'text/html'}}) :
        path === '/live-quota-board.js' ?
          new Response('window.ROVOR_QUOTA_BOARD={}', {headers:{'Content-Type':'text/javascript'}}) :
          new Response('Not found', {status:404});
    }}};
  const send = (path, token) => handle(new Request('https://hud.example' + path, {
    headers: token ? {Authorization: 'Bearer ' + token} : {}
  }),env);
  assert.equal((await send('/hud-quota.js')).status,401);
  assert.equal((await send('/')).status,303);
  assert.equal((await send('/hud-quota.js',env.HUD_WRITER_TOKEN)).status,401);
  assert.equal((await send('/',env.HUD_READER_TOKEN)).status,200);
  const html = await (await send('/',env.HUD_READER_TOKEN)).text();
  assert.match(html, /<script src="\/hud-quota\.js"><\/script>/);
  assert.equal((await send('/hud-quota.js',env.HUD_READER_TOKEN)).status,200);
});

test('readback requires actual auth and live assets, not mere deploy success', async () => {
  const token='r'.repeat(40);
  let statusDocument={source:'cloud_hud_telemetry',connection:'never_received',snapshot:null};
  let statusReadCount=0;
  const fetchOK=async (url, opts) => {
    const path=new URL(url).pathname;
    const auth=opts.headers.Authorization === 'Bearer ' + token;
    if (!auth && path === '/') return new Response(null, {
      status:303,headers:{Location:'https://hud.example/login'}});
    if (!auth) return new Response('{}', {status:401});
    if (path === '/') return new Response('<html><body>ROVOR_START_OMNIROUTE<script src="/hud-quota.js"></script></body></html>');
    if (path === '/hud-quota.js')
      return new Response(actualNineMeterAsset, {headers:{'Content-Type':'text/javascript'}});
    if(path==='/api/hud/ideas')return Response.json({source:'private_rovor_idea_inbox',
      execution_authorized:false,mac_required:false,items:[]});
    if (path === '/api/hud/status') {
      if (statusDocument.connection !== 'fresh') return Response.json(statusDocument);
      statusReadCount++;
      const current = structuredClone(statusDocument);
      if (statusReadCount > 1) {
        current.received_at = new Date(Date.parse(statusDocument.received_at) + 10000).toISOString();
        current.snapshot.snapshot_at = new Date(Date.parse(statusDocument.snapshot.snapshot_at) + 10000).toISOString();
      }
      return Response.json(current);
    }
    return new Response('{}', {status:404});
  };
  await assert.rejects(() => verifyGithubHud({origin:'https://hud.example',readerToken:token,send:fetchOK}),
    /private_D1_telemetry_not_fresh/);
  const usageProviders = ['gemini','groq','openrouter','mistral','cloudflare','cohere','nvidia','sambanova','huggingface']
    .map(provider => ({provider,attempts_pacific_day:0,models:[]}));
  usageProviders[1].attempts_pacific_day=1;
  usageProviders[1].models=[{model_id:'connection-test',attempts_pacific_day:1}];
  usageProviders[2].attempts_pacific_day=1;
  usageProviders[2].models=[{model_id:'cohere/north-mini-code:free',attempts_pacific_day:1,successes_pacific_day:1}];
  statusDocument={source:'cloud_hud_telemetry',connection:'fresh',received_at:'2026-10-29T01:03:31.000Z',snapshot:{
    snapshot_at:'2026-10-29T01:03:30.000Z',connections:Array.from({length:9},(_,i)=>({provider:String(i)})),
    request_usage:{source:'omniroute_durable_call_logs',freshness:'fresh',providers:usageProviders}}};
  statusReadCount=0;
  const current = await verifyGithubHud({origin:'https://hud.example',readerToken:token,send:fetchOK,
    expectedQuotaAsset:actualNineMeterAsset,pause:async()=>{}});
  assert.equal(current.quota_asset_matches_checkout,true);
  const live = current;
  assert.equal(live.all_nine_usage_readback_verified,true);
  assert.equal(live.active_usage_providers,2);
  assert.equal(live.tracked_models,2);
  assert.equal(live.tracked_pacific_day_requests,2);
  assert.equal(live.inference_activity_providers,1);
  assert.equal(live.free_tagged_successful_inference_providers,1);
  assert.equal(live.successive_reports_verified,true);
  assert.deepEqual(live.report_timestamps,{
    first_received_at:'2026-10-29T01:03:31.000Z',second_received_at:'2026-10-29T01:03:41.000Z',
    first_snapshot_at:'2026-10-29T01:03:30.000Z',second_snapshot_at:'2026-10-29T01:03:40.000Z'});
  statusDocument.snapshot.request_usage.providers.pop();
  await assert.rejects(() => verifyGithubHud({origin:'https://hud.example',readerToken:token,send:fetchOK}),
    /private_D1_usage_readback_incomplete/);
  statusDocument={source:'cloud_hud_telemetry',connection:'never_received',snapshot:null};
  await assert.rejects(() => verifyGithubHud({origin:'https://hud.example',readerToken:token,
    expectedQuotaAsset:actualNineMeterAsset,send:async(url,opts)=>{
      if(opts.headers.Authorization && new URL(url).pathname==='/hud-quota.js')
        return new Response(actualNineMeterAsset+'\n// previous release');
      return fetchOK(url,opts);
    }}),/deployed_quota_asset_differs_from_checkout/);
  await assert.rejects(() => verifyGithubHud({origin:'https://hud.example',
    readerToken:token, send:async (url,opts) => {
      if (!opts.headers.Authorization && new URL(url).pathname==='/hud-quota.js')
        return new Response('PUBLIC', {status:200});
      return fetchOK(url,opts);
    }}), /anonymous_quota_asset/);
});

test('private D1 readback rejects repeated report timestamps', async () => {
  const first={received_at:'2026-10-29T01:03:31.000Z',snapshot:{
    snapshot_at:'2026-10-29T01:03:30.000Z',
    request_usage:{source:'omniroute_durable_call_logs',freshness:'fresh',
      providers:Array.from({length:9},(_,i)=>({provider:String(i)}))}}};
  await assert.rejects(() => verifyAdvancingReports(async()=>({
    ...first,connection:'fresh'}),first,{attempts:2,pause:async()=>{},intervalMs:0}),
    /private_D1_reports_not_advancing/);
});

test('release readback checks the current shipped quota asset without coupling to copywriting', async () => {
  assert.equal(hasNineProviderMeterAsset(actualNineMeterAsset), true);
  // The last deploy failed because this grammar string was made dynamic.
  assert.equal(actualNineMeterAsset.includes("' Mac requests / 24h'"), false);
  assert.equal(hasNineProviderMeterAsset(actualNineMeterAsset.replaceAll('Mac request', 'Observed call')), true);
  for (const required of ['function overviewSlot(', 'function usageRing(',
    'function macActivity(', 'function modelActivity(', 'rvq-observed-model',
    'QUOTA UNKNOWN', 'window.ROVOR_QUOTA_BOARD=']) {
    assert.equal(hasNineProviderMeterAsset(actualNineMeterAsset.replaceAll(required,'REMOVED_CONTRACT_MARKER')), false,
      'missing functional marker must fail closed: '+required);
  }
  assert.equal(hasNineProviderMeterAsset('window.ROVOR_QUOTA_BOARD={}; rvq-overview rvq-ring Mac requests / 24h'), false);
});

test('authenticated readback still rejects an asset without model activity', async () => {
  const token='r'.repeat(40);
  const send=async (url, opts) => {
    const resource=new URL(url).pathname;
    const auth=opts.headers.Authorization === 'Bearer ' + token;
    if (!auth && resource === '/') return new Response(null, {status:303,
      headers:{Location:'https://hud.example/login'}});
    if (!auth) return new Response('{}',{status:401});
    if (resource === '/') return new Response('<body>ROVOR_START_OMNIROUTE<script src="/hud-quota.js"></script></body>');
    if (resource === '/hud-quota.js') return new Response(actualNineMeterAsset.replace('function modelActivity(', 'function missingActivity('));
    return Response.json({source:'cloud_hud_telemetry',connection:'stale',snapshot:null});
  };
  await assert.rejects(() => verifyGithubHud({origin:'https://hud.example',readerToken:token,send}),
    /nine_provider_meter_asset_missing/);
});

test('live verifier tolerates short rollout gaps but never accepts anonymous exposure', async () => {
  let tries = 0, sleeps = 0;
  const read = async () => new Response(null, {status: ++tries < 3 ? 503 : 401});
  assert.equal(await verifyAnonymousTelemetry(read, {attempts: 4,
    pause: async () => {sleeps++;},intervalMs:0}), true);
  assert.equal(tries,3);
  assert.equal(sleeps,2);
  let exposedTries = 0;
  await assert.rejects(() => verifyAnonymousTelemetry(async () => {
    exposedTries++;return new Response('EXPOSED', {status:200});
  }, {attempts:4,pause:async()=>{}}),/anonymous_telemetry_exposed_http_200/);
  assert.equal(exposedTries,1);
  await assert.rejects(() => verifyAnonymousTelemetry(async () =>
    new Response('No route', {status:404}), {attempts:2,pause:async()=>{}}),
    /anonymous_telemetry_not_verified_http_404/);
  await assert.rejects(() => verifyAnonymousTelemetry(async () =>
    new Response(null, {status:302,headers:{Location:'/login'}}),
    {attempts:4,pause:async()=>{}}), /anonymous_telemetry_unexpected_http_302/);
  await assert.rejects(() => verifyAnonymousTelemetry(async () => {
    throw new TypeError('network_error');
  },{attempts:2,pause:async()=>{}}),/anonymous_telemetry_not_verified_transport_unavailable/);
});

test('Approved HUD main pushes auto-deploy only after safety checks, without exposing PR secrets', () => {
  const workflow=readFileSync(new URL('../.github/workflows/deploy-private-hud-cloudflare.yml',import.meta.url),'utf8');
  assert.match(workflow, /github.ref == 'refs\/heads\/main'/);
  assert.match(workflow, /github.event_name == 'push'/);
  assert.match(workflow, /github.event_name == 'workflow_dispatch'/);
  assert.match(workflow, /push:\s*\n\s*branches: \[main\]/);
  assert.match(workflow, /needs: safety-tests/);
  assert.match(workflow, /environment: rovor-hud-production/);
  assert.match(workflow, /concurrency:/);
  assert.match(workflow, /cancel-in-progress: false/);
  assert.doesNotMatch(workflow, /ROVOR_HUD_GITHUB_AUTO_DEPLOY/);
  assert.doesNotMatch(workflow, /\n  verify-existing:/);
  assert.match(workflow, /wrangler d1 execute DB --remote/);
  assert.match(workflow, /wrangler deploy --config wrangler.github.jsonc/);
  assert.match(workflow, /verify-github-deploy\.mjs/);
  assert.doesNotMatch(workflow, /ChatGPT Site.*deploy/);
});


test('deployment readback validates the exact Ask ROVOR release even while Mac telemetry is stale', async () => {
  const token='r'.repeat(40), currentChat = readFileSync(new URL('../dashboard/command-center/native-v8-9/hud-chat.js',import.meta.url),'utf8');
  const report={source:'cloud_hud_telemetry',connection:'stale',received_at:'2026-10-28T00:38:25.840Z',
    snapshot:{snapshot_at:'2026-10-28T00:38:25.577Z',
      connections:Array.from({length:9},(_,i)=>({provider:String(i),connection_count:1}))}};
  function createSend({publicChat=false,oldChat=false,oldBackend=false,publicCatalog=false,publicIdeas=false,oldIdeas=false,publicRepo=false,oldRepo=false}={}){
    return async(url,opts)=>{
      const resource=new URL(url).pathname;
      const authenticated=opts.headers.Authorization==='Bearer '+token;
      if(!authenticated){
        if(resource==='/')return new Response(null,{status:303,headers:{Location:'https://hud.example/login'}});
        if(publicChat&&resource==='/hud-chat.js')return new Response('EXPOSED',{status:200});
        if(publicCatalog&&resource==='/api/hud/chat/models')return Response.json({models:['EXPOSED']});
        if(publicIdeas&&resource==='/api/hud/ideas')return Response.json({items:[{text:'EXPOSED'}]});
        if(publicRepo&&resource==='/api/hud/github/source')return Response.json({text:'EXPOSED'});
        return Response.json({error:'unauthorized'},{status:401});
      }
      if(resource==='/')return new Response('<html><body>ROVOR_START_OMNIROUTE<script src="/hud-quota.js"></script></body></html>');
      if(resource==='/hud-quota.js')return new Response(actualNineMeterAsset);
      if(resource==='/hud-chat.js')return new Response(oldChat?'old-release':currentChat);
      if(resource==='/api/hud/chat/models')return oldBackend?Response.json({error:'not_found'},{status:404}):Response.json({source:'omniroute_outbound_bridge',online:false,models:[]});
      if(resource==='/api/chat/groq/status')return Response.json({source:'cloud_direct_groq',
        mac_required:false,credentials_present:true,ready:false,
        catalog:{source:'groq_api_models_catalog',state:'catalog_received',model_present:true,
          requests_per_day:{unit:'requests',window:'day',limit:1000,remaining:975,reset_at:null},
          tokens_per_minute:{unit:'tokens',window:'minute',limit:8000,remaining:7470,reset_at:null}}});
      if(resource==='/api/hud/github/source')return oldRepo?Response.json({error:'not_found'},{status:404}):
        Response.json({source:'reviewed_github_checkout',repo:'TeamRovor/rovor-video-engine',
          path:'coordination/TASK-INTAKE.md',commit:'a'.repeat(40),
          text:'Reviewed source excerpt for testing',truncated:false,
          can_write:false,fetched_live:false,mac_required:false});
      if(resource==='/api/hud/ideas')return oldIdeas?Response.json({error:'not_found'},{status:404}):
        Response.json({source:'private_rovor_idea_inbox',execution_authorized:false,mac_required:false,items:[]});
      if(resource==='/api/hud/status')return Response.json(report);
      return Response.json({error:'not_found'},{status:404});
    };
  }
  const input={origin:'https://hud.example',readerToken:token,expectedQuotaAsset:actualNineMeterAsset,
    expectedChatAsset:currentChat,requireLiveTelemetry:false,pause:async()=>{}};
  const result=await verifyGithubHud({...input,send:createSend()});
  assert.equal(result.deployment_verified,true);
  assert.equal(result.private_idea_inbox_verified,true);
  const withRepo=await verifyGithubHud({...input,send:createSend(),expectedRepoCommit:'a'.repeat(40)});
  assert.equal(withRepo.reviewed_repo_source_verified,true);
  await assert.rejects(()=>verifyGithubHud({...input,send:createSend({publicRepo:true}),expectedRepoCommit:'a'.repeat(40)}),
    /anonymous_repo_source_exposed/);
  await assert.rejects(()=>verifyGithubHud({...input,send:createSend({oldRepo:true}),expectedRepoCommit:'a'.repeat(40)}),
    /private_repo_source_unavailable/);
  await assert.rejects(()=>verifyGithubHud({...input,send:createSend(),expectedRepoCommit:'b'.repeat(40)}),
    /private_repo_source_invalid/);
  assert.equal(result.private_auth_verified,true);
  assert.equal(result.chat_asset_matches_checkout,true);
  assert.equal(result.chat_model_endpoint_verified,true);
  assert.equal(result.mac_telemetry_verified,false);
  assert.equal(result.successive_reports_verified,false);
  assert.equal(result.telemetry_connection,'stale');
  assert.equal(result.active_usage_providers,null); // Unknown, not a fabricated zero
  assert.equal(result.tracked_pacific_day_requests,null);
  const withGroq=await verifyGithubHud({...input,send:createSend(),expectGroqKeyCatalog:true});
  assert.equal(withGroq.cloud_groq_key_catalog.catalogue_status,'catalog_received');
  assert.equal(withGroq.cloud_groq_key_catalog.model_in_catalog,true);
  assert.deepEqual(withGroq.cloud_groq_key_catalog.requests_per_day,{limit:1000,remaining:975,reset_at:null});
  assert.equal(withGroq.cloud_groq_key_catalog.billing_verified,false);
  assert.equal(withGroq.cloud_groq_key_catalog.inference_verified,false);
  await assert.rejects(()=>verifyGithubHud({...input,send:createSend({oldChat:true})}),
    /deployed_chat_asset_differs_from_checkout/);
  await assert.rejects(()=>verifyGithubHud({...input,send:createSend({publicChat:true})}),
    /anonymous_chat_asset_was_not_denied/);
  await assert.rejects(()=>verifyGithubHud({...input,send:createSend({publicCatalog:true})}),
    /anonymous_chat_model_catalog_was_not_denied/);
  await assert.rejects(()=>verifyGithubHud({...input,send:createSend({publicIdeas:true})}),
    /anonymous_idea_inbox_exposed/);
  await assert.rejects(()=>verifyGithubHud({...input,send:createSend({oldIdeas:true})}),
    /private_idea_inbox_unavailable/);
  await assert.rejects(()=>verifyGithubHud({...input,send:createSend({oldBackend:true})}),
    /private_chat_model_endpoint_unavailable/);
  await assert.rejects(()=>verifyGithubHud({...input,requireLiveTelemetry:true,send:createSend()}),
    /private_D1_telemetry_not_fresh/);
});

test('asset deployment reports degraded rather than false live when two fresh Mac reports do not advance',async()=>{
  const token='r'.repeat(40), currentChat=readFileSync(new URL('../dashboard/command-center/native-v8-9/hud-chat.js',import.meta.url),'utf8');
  const providers=Array.from({length:9},(_,i)=>({provider:String(i),attempts_pacific_day:0,models:[]}));
  const status={source:'cloud_hud_telemetry',connection:'fresh',received_at:'2026-11-04T06:00:00.000Z',
    snapshot:{snapshot_at:'2026-11-04T06:00:00.000Z',connections:Array.from({length:9},(_,i)=>({provider:String(i)})),
      request_usage:{source:'omniroute_durable_call_logs',freshness:'fresh',providers}}};
  const send=async(url,opts)=>{
    const path=new URL(url).pathname;
    if(!opts.headers.Authorization){
      if(path==='/')return new Response(null,{status:303,headers:{Location:'https://hud.example/login'}});
      return new Response('',{status:401});
    }
    if(path==='/')return new Response('<body>ROVOR_START_OMNIROUTE<script src="/hud-quota.js"></script></body>');
    if(path==='/hud-quota.js')return new Response(actualNineMeterAsset);
    if(path==='/hud-chat.js')return new Response(currentChat);
    if(path==='/api/hud/chat/models')return Response.json({source:'omniroute_outbound_bridge',online:false,models:[]});
    if(path==='/api/hud/ideas')return Response.json({source:'private_rovor_idea_inbox',
      execution_authorized:false,mac_required:false,items:[]});
    if(path==='/api/hud/status')return Response.json(status);
    return new Response('',{status:404});
  };
  const props={origin:'https://hud.example',readerToken:token,expectedQuotaAsset:actualNineMeterAsset,
    expectedChatAsset:currentChat,send,pause:async()=>{}};
  const degraded=await verifyGithubHud({...props,requireLiveTelemetry:false});
  assert.equal(degraded.deployment_verified,true);
  assert.equal(degraded.mac_telemetry_verified,false);
  assert.equal(degraded.all_nine_usage_readback_verified,false);
  await assert.rejects(()=>verifyGithubHud(props),/private_D1_reports_not_advancing/);
});

test('readback Groq response summary whitelists only catalog/limits and rejects forged readiness',()=>{
 const base={source:'cloud_direct_groq',mac_required:false,credentials_present:true,
   catalog:{source:'groq_api_models_catalog',state:'auth_rejected',model_present:null}};
 const s=summarizeGroqKeyCatalog({...base,GROQ_HUD_API_KEY:'SHOULD_NEVER_LEAK'});
 assert.equal(s.catalogue_status,'auth_rejected');
 assert.equal(s.model_in_catalog,null);
 assert(!JSON.stringify(s).includes('SHOULD_NEVER_LEAK'));
 assert.throws(()=>summarizeGroqKeyCatalog({...base,mac_required:true}),/groq_catalog_readback_invalid/);
 assert.throws(()=>summarizeGroqKeyCatalog({...base,catalog:{...base.catalog,state:'magically_free'}}),/groq_catalog_readback_invalid/);
});

test('pinned release tolerates old valid asset during rollout but never relaxes privacy or exact commit',async()=>{
 const expected='b'.repeat(40),old='a'.repeat(40);
 let reads=0,waits=0;
 const valid=commit=>Response.json({source:'reviewed_github_checkout',repo:'TeamRovor/rovor-video-engine',
  path:'coordination/TASK-INTAKE.md',commit,text:'bounded source',truncated:false,fetched_live:false,can_write:false,mac_required:false});
 const read=async(path,auth)=>auth?valid(++reads<3?old:expected):new Response(null,{status:401});
 assert.equal(await verifyPinnedRepoSource(read,expected,{pause:async()=>{waits++;}}),true);
 assert.equal(reads,3);assert.equal(waits,2);
 await assert.rejects(()=>verifyPinnedRepoSource(async(path,auth)=>auth?valid(old):new Response(null,{status:401}),expected,
  {attempts:2,pause:async()=>{}}),/commit_mismatch/);
 let exposed=0;
 await assert.rejects(()=>verifyPinnedRepoSource(async()=>{exposed++;return valid(expected)},expected,
  {pause:async()=>{}}),/anonymous_repo_source_exposed/);
 assert.equal(exposed,1);
});


test('protected Worker deployment passes the existing Site catalog service key without adding a public variable',()=>{
 const workflow=readFileSync(new URL('../.github/workflows/deploy-private-hud-cloudflare.yml',import.meta.url),'utf8');
 assert.match(workflow,/^\s{6}ROVOR_GHOST_SERVICE_TOKEN: \$\{\{ secrets\.ROVOR_GHOST_SERVICE_TOKEN \}\}$/m);
 assert.match(workflow,/node private-worker-secret-payload\.mjs \|/);
 assert.match(workflow,/wrangler secret bulk --config wrangler\.github\.jsonc/);
 const payload=readFileSync(new URL('../integrations/hud-cloud/private-worker-secret-payload.mjs',import.meta.url),'utf8');
 assert.match(payload,/payload\.GHOST_SITE_SERVICE_TOKEN=key/);
 assert.match(payload,/key===env\.ROVOR_HUD_READER_TOKEN\|\|key===env\.ROVOR_HUD_WRITER_TOKEN/);
});


// Preserve existing secret-precedence while also accepting the exact ROVOR_CLOUD_*
// aliases used by the protected release environment. Never log secret values.
test('seven optional provider catalog keys remain wired from protected Actions to Worker secrets',()=>{
 const workflow=readFileSync(new URL('../.github/workflows/deploy-private-hud-cloudflare.yml',import.meta.url),'utf8');
 const payload=readFileSync(new URL('../integrations/hud-cloud/private-worker-secret-payload.mjs',import.meta.url),'utf8');
 const expected={
  MISTRAL:'ROVOR_MISTRAL_API_KEY || secrets.MISTRAL_API_KEY || secrets.ROVOR_CLOUD_MISTRAL_API_KEY',
  NVIDIA:'ROVOR_NVIDIA_API_KEY || secrets.NVIDIA_API_KEY || secrets.ROVOR_CLOUD_NVIDIA_API_KEY',
  COHERE:'ROVOR_COHERE_API_KEY || secrets.COHERE_API_KEY || secrets.ROVOR_CLOUD_COHERE_API_KEY',
  SAMBANOVA:'ROVOR_SAMBANOVA_API_KEY || secrets.SAMBANOVA_API_KEY || secrets.ROVOR_CLOUD_SAMBANOVA_API_KEY',
  OPENROUTER:'ROVOR_OPENROUTER_API_KEY || secrets.OPENROUTER_API_KEY || secrets.ROVOR_CLOUD_OPENROUTER_API_KEY',
  HUGGINGFACE:'ROVOR_HUGGINGFACE_API_KEY || secrets.HUGGINGFACE_API_KEY || secrets.ROVOR_CLOUD_HUGGINGFACE_API_KEY',
  CLOUDFLARE_AI:'ROVOR_CLOUDFLARE_AI_API_KEY || secrets.ROVOR_CLOUD_CLOUDFLARE_AI_API_KEY'
 };
 for(const [provider,value] of Object.entries(expected)){
  const from='ROVOR_CLOUD_'+provider+'_API_KEY';
  const line='      '+from+': '+'$'+'{{ secrets.'+value+' }}';
  assert(workflow.split(line).length===2,'missing or duplicated protected '+provider+' mapping');
  assert(payload.includes("['"+from+"','"+provider+"_API_KEY']"),
   'missing server-side Worker secret binding for '+provider);
 }
 assert(!payload.includes('payload.CLOUDFLARE_AI_API_KEY=env.CLOUDFLARE_API_TOKEN'),
  'deployment token is never a provider key');
});
